# A node that produces energy to bring the incoming water to a definable supply temperature

from typing import Optional
import numpy as np  # type: ignore
from .node import Node


class Producer(Node):
    def __init__(
        self,
        blocks: int,  # number of time steps
        id: Optional[int] = None,
        heat_capacity: float = 4181.3,  # in J/kg/K # for the water
        temp_upper_bound=120,
        pump_efficiency: float = 0.9,
        density=963,
        control_with_temp: bool = False,
        energy_unit_conversion: int = 10 ** 6,
    ) -> None:
        super().__init__(
            id=id,
            slots=("Return", "Supply"),
            blocks=blocks,
        )

        self.control_with_temp = control_with_temp
        self.temp_upper_bound = temp_upper_bound
        self.heat_capacity = heat_capacity
        self.pump_efficiency = pump_efficiency

        self.density = density  # kg/m^3
        self.energy_unit_conversion = energy_unit_conversion

        self.production_costs, self.pump_power = None, None
        self.virtual_temp_sup = None

    def clear(self) -> None:
        blocks = self.blocks

        self.production_costs = np.full(blocks, np.nan, dtype=float)
        self.q = np.full(blocks, np.nan, dtype=float)  # heat produced in MW
        self._q_in_W = np.full(blocks, np.nan, dtype=float)  # heat produced in W
        self.pump_power = np.full(blocks, np.nan, dtype=float)  # in MW
        self.virtual_temp_sup = np.full(blocks, np.nan, dtype=float)

        self._clear()

    def get_outlet_temp(
        self,
        slot: int,
        mass_flow: float,
    ) -> float:
        """
        Is called from downstream to get the average outlet temperature in the
        coming step.
        """
        assert slot == 1
        if self.control_with_temp:
            entry_step_global = self.current_step
            return self.temp[1, self.current_step], entry_step_global

        else:
            temp = (
                    self.q[self.current_step]
                    * self.energy_unit_conversion
                    / mass_flow
                    / self.heat_capacity
            )

            if self.current_step != 0:
                try:
                    temp += self.edges[0].get_outlet_temp()
                except AssertionError:
                    print(
                        "Warning, when producer is controlled with q and water reaches consumer at the same time step,"
                        + "simulation will not be accurate. Try use smaller time interval or control with."
                    )
                    temp += self.temp[0, self.current_step - 1]

            else:
                "Used by tabular RL"
                temp += self.edges[0].get_outlet_temp()

                if (mass_flow is None) or np.isnan(mass_flow):
                    temp = self.edges[1].initial_plug_cache[0].entry_temp

        entry_step_global = self.current_step # counting of entry step global starts from producer
        return min(temp, self.temp_upper_bound), entry_step_global

    def set_mass_flow(self, slot: int, mass_flow: float) -> None:
        """
        Called from supply downstream or return upstream to inform this node
        about the mass flow in the coming step
        """

        if slot == 1:
            self.mass_flow[0, self.current_step] = mass_flow
            self.mass_flow[1, self.current_step] = mass_flow
            self.temp[0, self.current_step], _ = self.edges[0].get_outlet_temp()
            # Set either temp or q, depending on control_with_temp
            self.set_temp_or_q(mass_flow)

            outlet_pressure = self.edges[1].pressure[0, self.current_step]
            inlet_pressure = self.edges[0].pressure[1, self.current_step]

            if self._safety_check:
                assert (not np.isnan(inlet_pressure)) & (not np.isnan(outlet_pressure))
            self.pressure[1, self.current_step] = outlet_pressure
            self.pressure[0, self.current_step] = inlet_pressure

            self.pump_power[self.current_step] = (
                    (outlet_pressure - inlet_pressure)
                    * mass_flow
                    / (self.density * self.pump_efficiency)
                ) / self.energy_unit_conversion

        assert self.mass_flow[1, self.current_step] == mass_flow


    def set_temp_or_q(self, mass_flow: float):
        """
        Sets the q value based on the current temperature, if the control is done with temperature.
        Otherwise, sets temperature based on the current q value.
        """

        if self.control_with_temp:
            q = (
                    self.mass_flow[1, self.current_step]
                    * (self.temp[1, self.current_step] - self.temp[0, self.current_step])
                    * self.heat_capacity
            )

            self._q_in_W[self.current_step] = q
            self.q[self.current_step] = q / (10 ** 6)
        else:
            self._q_in_W[self.current_step] = self.q[self.current_step] * 10 ** 6
            temp = (
                    self._q_in_W[self.current_step] / mass_flow / self.heat_capacity
                    + self.temp[0, self.current_step]
            )

            self.virtual_temp_sup[self.current_step] = temp
            self.temp[1, self.current_step] = min(temp, self.temp_upper_bound)

            self.violations["supply temp"][self.current_step] = max(
                0, temp - self.temp_upper_bound
            )

    def solve(
        self,
    ) -> None:
        pass

    def get_margin(self, level_time: int = 0) -> dict:
        margin = {"cost": {}, "profit": {}}
        if level_time == 0:
            margin["cost"]["pump"] = np.sum(self.pump_power[: self.current_step])
        elif level_time == 1:
            margin["cost"]["pump"] = self.pump_power[: self.current_step]
        elif level_time == 2:
            margin["cost"]["pump"] = self.pump_power[self.current_step - 1]

        return margin

    def debug(self, csv: bool = False) -> None:
        if csv:
            data = [
                [
                    "{:.0f}".format(d),
                ]
                for d in self.q
            ]
        else:
            data = [
                [
                    "{:,.0f}".format(d),
                ]
                for d in self.q
            ]

        super()._debug(
            csv,
            ["Q"],
            data,
        )

    @property
    def type_name(self) -> str:
        return "Producer"

    @property
    def is_supply(self) -> bool:
        return True
