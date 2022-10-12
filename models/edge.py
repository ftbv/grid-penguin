# An edge connects two nodes

import copy

from typing import Optional, List, Tuple, TYPE_CHECKING
import math
import numpy as np  # type: ignore
from beautifultable import BeautifulTable  # type: ignore
import os
from functools import cached_property
from collections import defaultdict

from .producer import Producer
from .grid_object import GridObject
from .plug import Plug
from .timing import Timing

if TYPE_CHECKING:
    from .node import Node


timing = Timing(start=False)


class Edge(GridObject):
    def __init__(
        self,
        blocks: int,
        diameter: float,  # in meters
        length: float,  # in meters
        thermal_resistance: float,  # in k*m/W
        plugs_in_pipe: List[Plug] = [],  # first one is newest!
        historical_t_in: Optional[float] = None,  # in ºC
        id: Optional[int] = None,
        heat_capacity: float = 4181.3,  # in J/kg/K
        density: float = 963,  # in kg/m^3
        t_ground: float = 10,  # °C
        max_flow_speed=10,  # m/s
        min_flow_speed=0,
        friction_coefficient=1.29 * np.sqrt(2),  # (kg*m)^-1
        energy_unit_conversion: int = 10 ** 6,
    ) -> None:
        super().__init__(id=id)

        self.blocks = blocks
        self.nodes: Tuple[Tuple[Node, int], Tuple[Node, int]]
        self.diameter = diameter
        surface = Edge.diameter_to_surface(diameter)  # cross-section
        self.surface = surface
        self.density = density
        self.max_flow_speed = max_flow_speed
        self.min_flow_speed = min_flow_speed
        self._mass_in_pipe = length * surface * density
        self.friction_coefficient = friction_coefficient
        self.energy_unit_conversion = energy_unit_conversion

        if historical_t_in is None:  # initialization with historical temperature
            self.initial_plug_cache = plugs_in_pipe  # first one is newest!
            mass_in_pipe: float = 0
            for plug in plugs_in_pipe:
                mass_in_pipe += plug.mass

            assert mass_in_pipe == self._mass_in_pipe
        else:
            """
            Initial plug is the plug of mass equal to the mass of the pipe, and with historical temperature.
            """
            self.initial_plug_cache = [
                Plug(
                    mass=self._mass_in_pipe,
                    entry_step=-1,
                    entry_temp=historical_t_in,
                )
            ]

        self.heat_capacity = heat_capacity
        """
        The Thermal Time Constant is a measurement of the time required for
        the  thermistor to respond to a change in the ambient temperature.  The
        technical definition of Thermal Time Constant is, "The time required for
        a thermistor to change 63.2% of the total difference between its initial
        and final body temperature when subjected to a step function change in
        temperature, under zero power conditions

        In other words, when the measurement object suddenly changes from 100°C
        to ０°C, the device recognises the measurement object at 36.8°C after
        tau_thermal seconds
        """
        self.thermal_resistance = thermal_resistance
        self._thermal_time_constant = Edge.thermal_time_constant(  # heat loss equation
            surface,
            heat_capacity,
            density,
            thermal_resistance,
        )  # in m/s

        self.t_ground = t_ground

        self.temp, self.actual_outlet_temp, self.mass_flow, self.flow_speed = None, None, None, None
        self.plug_cache, self.plug_cache_saver, self.pressure = None, None, None
        self.delay_matrix, self.heat_loss, self.heat_in_pipe, self.violations, self.nodes = None, None, None, None, None

    def clear(self) -> None:
        super().clear()
        self.temp = np.full((2, self.blocks), np.nan, dtype=float)
        """
        The purpose of actual outlet temperature is that, if the outlet temperature is
        initially calculated in get_outlet_temp() with a inaccurate mass flow, it will deviate
        from the actual outlet temperature. And we want to keep that info for debugging
        """
        self.actual_outlet_temp = np.full(self.blocks, np.nan, dtype=float)
        self.mass_flow = np.full((2, self.blocks), np.nan, dtype=float)
        self.flow_speed = np.full(self.blocks, np.nan, dtype=float)
        # plug_cache: the actual plugs in the pipe at the current time step
        self.plug_cache = copy.deepcopy(self.initial_plug_cache)
        # plug_cache_saver: saving all plugs in the pipe in past time steps
        self.plug_cache_saver = [copy.deepcopy(self.initial_plug_cache)]
        self.pressure = np.full((2, self.blocks), np.nan, dtype=float)
        extended_blocks = len(self.initial_plug_cache) + self.blocks
        """
        delay_matrix: recording the water goes out at a time step, at which previous
        time steps it goes into the pipe and the composition. The size of the matrix [m.n]:
        m is the total time step number. n is total time step plus number of initial plugs.
        For example, suppose there is one initial plug,
        if delay_matrix[5,0] = 0.6 and delay_matrix[5,1] = 0.4,
        it means that for water goes out at time step5, 60% comes from the initial plug,
        and 40% goes in at time step 0.
        """
        self.delay_matrix = np.full((self.blocks, extended_blocks), np.nan, dtype=float)
        self.heat_loss = np.full(self.blocks, 0, dtype=float)
        self.heat_in_pipe = np.full(self.blocks, 0, dtype=float)

        self.violations = defaultdict(
            lambda: np.full(self.blocks, np.nan, dtype=np.float)
        )
        # edge violation only contains one key: 'flow speed'

    def link(
        self,
        nodes: Tuple[Tuple["Node", int], Tuple["Node", int]],
    ) -> None:
        self.nodes = nodes

    def reset_initial_plugs(self, plugs_in_pipe):
        self.initial_plug_cache = plugs_in_pipe  # first one is newest!
        mass_in_pipe: float = 0
        for plug in plugs_in_pipe:
            mass_in_pipe += plug.mass

        assert mass_in_pipe == self._mass_in_pipe

    def get_outlet_temp(self) -> float:
        """
        Called from down-stream to get the average outlet temperature in the
        coming step. On the primary side, we do not yet know the mass_flow, so
        have to estimate it. Right now, we use the mass flow of the previous
        step.
        """

        if not np.isnan(self.temp[1, self.current_step]):
            # return side of the grid
            return self.temp[1, self.current_step]

        outlet_temp: float = 0

        if self.current_step == 0:
            expected_mass = 0
        else:
            expected_mass = (
                self.interval_length * self.mass_flow[0, self.current_step - 1]
            )

        fulfilled: float = 0

        for plug in reversed(self.plug_cache):

            if expected_mass - fulfilled >= plug.mass:
                fulfilled += plug.mass
                consuming = plug.mass
            else:
                consuming = expected_mass - fulfilled
                fulfilled = expected_mass

            plug_temp = self.get_plug_temp(self.current_step - plug.entry_step, plug.entry_temp)

            if expected_mass == 0:
                outlet_temp = plug_temp
            elif consuming > 0:
                outlet_temp += plug_temp * (consuming / expected_mass)

            if fulfilled >= expected_mass:
                break

        if fulfilled < expected_mass:
            consuming = expected_mass - fulfilled
            (inlet_node, inlet_slot) = self.nodes[0]
            if not issubclass(type(inlet_node), Producer):
                entry_temp = inlet_node.get_outlet_temp(inlet_slot)
            else:
                entry_temp = inlet_node.get_outlet_temp(
                    inlet_slot, self.mass_flow[0, self.current_step - 1]
                )

            # no decay, as inlet time step equals outlet step
            outlet_temp += entry_temp * (consuming / expected_mass)
        self.temp[1, self.current_step] = outlet_temp

        return outlet_temp

    def get_outlet_temp_mass_bundle(self):
        """
        Applies heat loss equation according to the Newton's cooling law on  reversed plugs from the pipe.
        """

        bundle = []
        for plug in reversed(self.plug_cache):
            tau_c = (self.current_step - plug.entry_step) * self.interval_length
            exp_tau = math.exp(-tau_c / self._thermal_time_constant)

            outlet_temp = self.t_ground + (plug.entry_temp - self.t_ground) * exp_tau
            bundle.append([outlet_temp, plug.mass])

        (inlet_node, inlet_slot) = self.nodes[0]
        if not issubclass(type(inlet_node), Producer):
            entry_temp = inlet_node.get_outlet_temp(inlet_slot)
        else:
            entry_temp = inlet_node.get_outlet_temp(
                inlet_slot, self.mass_flow[0, self.current_step - 1]
            )

        bundle.append([entry_temp, np.inf])

        return bundle

    def set_mass_flow(self, slot: int, mass_flow: float) -> None:
        """
        Called from supply downstream or return upstream to inform this edge
        about the mass flow in the coming step.
        """
        self.calculate_heat_loss_and_heat_in_pipe()

        """
        Flow speed at the current time-step is calculated 
        based on the mass flow sent as the function parameter.
        """
        self.flow_speed[self.current_step] = mass_flow / self.surface / self.density

        self.violations["flow speed"][self.current_step] = np.maximum(
            self.flow_speed[self.current_step] - self.max_flow_speed, 0
        ) + np.minimum(self.flow_speed[self.current_step] - self.min_flow_speed, 0)

        consumed_mass = self.interval_length * mass_flow
        """
        Depends on whether edge is the supply or return, inlet node will be 
        producer or consumer (for the grid with one consumer and one producer).
        """
        (inlet_node, inlet_slot) = self.nodes[0]
        if not issubclass(type(inlet_node), Producer):
            entry_temp = inlet_node.get_outlet_temp(inlet_slot)
        else:
            entry_temp = inlet_node.get_outlet_temp(inlet_slot, mass_flow)
        """
        Newly created plug is added to the beginning of the plug list. 
        Therefore, the sum of plug's mass exceeds 
        the total possible amount of water in the pipe.
        """
        self.plug_cache.insert(
            0,
            Plug(
                mass=consumed_mass,
                entry_step=self.current_step,
                entry_temp=entry_temp,
            ),
        )
        self.heat_in_pipe[self.current_step] += (
            consumed_mass
            * entry_temp
            * self.heat_capacity
            / self.energy_unit_conversion
        )

        actual_outlet_temp, delay_arr = self.push_plugs_outside(consumed_mass)

        """
        Actual outlet temperature is calculated as the weighted sum of temperatures of plugs that are
        pushed outside of the pipe. The weight of the plug is proportional to 
        the mass of the pushed out plug divided with the mass of newly inserted plug.
        """
        self.actual_outlet_temp[self.current_step] = actual_outlet_temp
        self.delay_matrix[self.current_step] = delay_arr
        """
        Depends on whether edge is the supply or return, outlet node will be 
        consumer or producer (for the grid with one consumer and one producer).
        For the grid with one producer and one consumer, outlet nodes are always on slot 1.
        """
        (outlet_node, outlet_slot) = self.nodes[1]
        if slot == 1:
            # "For the grid with one producer and one consumer, supply edge has the slot 1."
            self.solvable_callback(inlet_node, inlet_slot, mass_flow)
            # if the temp is still nan, it means get_outlet_temp_mass_bundle() is called instead
            # of get_outlet_temp(). And in this case there is no inaccuracy in outlet temp.
            if np.isnan(self.temp[1, self.current_step]):
                self.temp[1, self.current_step] = actual_outlet_temp
        else:
            # "For the grid with one producer and one consumer, return edge has the slot 0."
            self.solvable_callback(outlet_node, outlet_slot, mass_flow)
            # temperature at the outlet of the edge
            self.temp[1, self.current_step] = actual_outlet_temp

        self.mass_flow[:, self.current_step] = mass_flow

        # temperature at the inlet of the edge
        self.temp[0, self.current_step] = entry_temp
        self.plug_cache_saver.append(copy.deepcopy(self.plug_cache))

        inlet_pressure = inlet_node.pressure[inlet_slot, self.current_step]
        outlet_pressure = outlet_node.pressure[outlet_slot, self.current_step]

        assert (not np.isnan(inlet_pressure)) | (not np.isnan(outlet_pressure))
        if (not np.isnan(inlet_pressure)) & (not np.isnan(outlet_pressure)):
            assert (
                abs(
                    abs(outlet_pressure - inlet_pressure)
                    - self.friction_coefficient * mass_flow ** 2
                )
                < 0.001
            )

        if not np.isnan(inlet_pressure):
            """
            For the grid with one consumer and one producer, this is applicable for the return edge.
            """
            self.pressure[0, self.current_step] = inlet_pressure
            self.pressure[1, self.current_step] = (
                inlet_pressure - self.friction_coefficient * mass_flow ** 2
            )

        else:
            """
            For the grid with one consumer and one producer, else condition is applicable for the supply edge.
            """
            self.pressure[1, self.current_step] = outlet_pressure
            self.pressure[0, self.current_step] = (
                outlet_pressure + self.friction_coefficient * mass_flow ** 2
            )

        return None

    def calculate_heat_loss_and_heat_in_pipe(self):
        """
        Loop through the plugs present in the pipe, starting from the most recent inserted Plug,
        and calculate the heat loss, and temperature of the plug after the heat loss, and heat present
        in the pipe after the heat loss.
        """
        heat_loss = 0
        heat_in_pipe = 0

        for plug in self.plug_cache:
            tau_c_p = (
                    max(self.current_step - plug.entry_step - 1, 0) * self.interval_length
            )
            tau_c = (self.current_step - plug.entry_step) * self.interval_length
            exp_tau_diff = math.exp(-tau_c_p / self._thermal_time_constant) - math.exp(
                -tau_c / self._thermal_time_constant
            )
            temp_diff = (plug.entry_temp - self.t_ground) * exp_tau_diff
            heat_loss += temp_diff * self.heat_capacity * plug.mass
            current_temp = self.t_ground + (plug.entry_temp - self.t_ground) * math.exp(
                -tau_c / self._thermal_time_constant
            )
            heat_in_pipe += current_temp * plug.mass * self.heat_capacity

        """
        After looping through all plugs present in the pipe in the current time-step, we calculate
        heat loss and heat in pipe in the current time step.
        """
        self.heat_loss[self.current_step] = heat_loss / self.energy_unit_conversion
        self.heat_in_pipe[self.current_step] = (
                heat_in_pipe / self.energy_unit_conversion
        )

    def push_plugs_outside(self, consumed_mass: float):
        actual_outlet_temp: float = 0
        fulfilled: float = 0
        hist_blocks = len(self.initial_plug_cache)
        delay_arr = np.zeros(hist_blocks + self.blocks)
        """
         Push the plugs of water outside of the pipe, so that the total mass of plugs in the pipe
         matches total possible amount mass of water [kg] in the pipe.
        """
        for i in reversed(range(len(self.plug_cache))):
            plug = self.plug_cache[i]

            if consumed_mass - fulfilled >= plug.mass:
                self.plug_cache.pop()
                fulfilled += plug.mass
                consuming = plug.mass

            else:
                plug.mass -= consumed_mass - fulfilled
                consuming = consumed_mass - fulfilled
                fulfilled = consumed_mass

            if consuming > 0:
                delay_arr[hist_blocks + plug.entry_step] = consuming / consumed_mass
                plug_outlet_temp = self.get_plug_temp(self.current_step - plug.entry_step, plug.entry_temp)
                actual_outlet_temp += plug_outlet_temp * (consuming / consumed_mass)
                self.heat_in_pipe[self.current_step] -= (
                        consuming
                        * plug_outlet_temp
                        * self.heat_capacity
                        / self.energy_unit_conversion
                )

            if fulfilled >= consumed_mass:
                break

        assert fulfilled >= consumed_mass

        return actual_outlet_temp, delay_arr

    def get_plugs_condition(self, time):
        conditions = []
        for plug in self.plug_cache_saver[time]:
            t = time - plug.entry_step - 1
            current_temp = self.get_plug_temp(t, plug.entry_temp)

            conditions.append(
                [
                    round(plug.mass, 2),
                    round(current_temp, 2),
                    round(plug.entry_temp, 2),
                    plug.entry_step,
                ]
            )

        return conditions

    def get_plug_temp(self, time: int, plug_entry_temp: int):
        tau_c = time * self.interval_length
        exp_tau = math.exp(-tau_c / self._thermal_time_constant)

        return self.t_ground + (plug_entry_temp - self.t_ground) * exp_tau

    def set_initial_plugs(self, plug_state):
        self.initial_plug_cache = []
        max_entry_step = plug_state[0][-1]

        for mass, _, temp, entry_step in plug_state:
            self.initial_plug_cache.append(
                Plug(
                    mass=mass,
                    entry_step=-1 + entry_step - max_entry_step,
                    entry_temp=temp,
                )
            )

    def debug(self, csv: bool = False) -> None:
        print("{} {}".format(type(self).__name__, self.id))

        ts = os.get_terminal_size()
        table = BeautifulTable(
            maxwidth=ts.columns - 1,
            default_alignment=BeautifulTable.ALIGN_RIGHT,
        )
        column_headers = [
            "Time block",
            "Temp in (°C)",
            "Temp out provided (°C)",
            "Temp out error (°C)",
            "Mass flow (kg/s)",
        ]

        table.column_headers = column_headers

        for opt_time in range(
            0,
            self.blocks,
        ):
            row = [
                "{}".format(opt_time),
                "{:.2f}".format(self.temp[0, opt_time]),
                "{:.2f}".format(self.temp[1, opt_time]),
                "{:.2f}".format(
                    self.temp[1, opt_time] - self.actual_outlet_temp[opt_time]
                ),
                "{:.2f}".format(self.mass_flow[0, opt_time]),
            ]

            table.append_row(row)

        print(table)

        np.set_printoptions(precision=1, linewidth=150)

        # Drop historical output
        print_plugs = self.delay_matrix
        print(print_plugs / np.sum(print_plugs, 0))

    @property
    def costs(self) -> float:
        return 0

    @property
    def delay_loss_matrix(self) -> np.ndarray:
        hist_len = len(self.initial_plug_cache)
        delay_loss_matrix = np.full(
            (self.blocks, self.blocks),
            0.0,
            dtype=float,
        )
        for i in range(0, self.blocks):
            for j in range(0, self.blocks):
                if self.delay_matrix[i, j + hist_len] > 0:
                    tau_c = (j + hist_len - i) * self.interval_length
                    exp_tau = math.exp(-tau_c / self._thermal_time_constant)
                    delay_loss_matrix[i, j] = 1 / exp_tau
                else:
                    delay_loss_matrix[i, j] = 0.0

        return delay_loss_matrix

    @cached_property
    def is_supply(self) -> bool:
        for node, slot in self.nodes:
            if slot == 1:
                return node.is_supply
        raise Exception

    @staticmethod
    def thermal_time_constant(
        surface: float,
        heat_capacity: float,
        density: float,
        thermal_resistance: float,
    ) -> float:
        """
        For the pipe diameter=0.5958 [m^2], heat_capacity=4182[J/(kg*K)], density=963[kg/m^3]
        and thermal_resistance = 1.36[m*K/W], value of thermal time constant is 1526748.152 [J/W=s]
        """
        return surface * heat_capacity * density * thermal_resistance  # in J/K

    @staticmethod
    def diameter_to_surface(diameter: float) -> float:
        """
        Calculate surface area of the pipe
        """
        return math.pi * (diameter / 2) ** 2
