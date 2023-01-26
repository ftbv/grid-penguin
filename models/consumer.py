# A node that consumes a preset amount of energy (through a heat exchanger)

from typing import Optional
import numpy as np  # type: ignore
from .heat_exchanger import HeatExchanger
from .node import Node


class Consumer(Node):
    """
    A consumer consists of a heat exchanger, with the primary side having
    two slots. The secondary side supply and return temperatures are predefined
    """

    def __init__(
        self,
        demand: np.ndarray,  # in W
        id: Optional[int] = None,
        heat_capacity: float = 4181.3,  # in J/kg/K
        max_mass_flow_p: float = 300,
        surface_area: float = 10,  # in m^2
        heat_transfer_q: float = 0.8,  # See Palsson 1999 p45
        heat_transfer_k: float = 50000,  # See Palsson 1999 p51
        heat_transfer_k_max: float = None,
        demand_capacity: float = None, # in MW
        min_supply_temp: float = 0,
        pressure_load=100000,  # [Pa] https://www.euroheat.org/wp-content/uploads/2008/04/Euroheat-Power-Guidelines-District-Heating-Substations-2008.pdf ?
        setpoint_t_supply_s: float = 70,
        t_return_s: float = 45,
        energy_unit_conversion=10 ** 6,
        interpolation_values: dict[float, dict[float, float]] = None
    ) -> None:
        super().__init__(
            id=id,
            slots=("Supply", "Return"),
            blocks=demand.shape[0],
        )

        

        self.heat_exchanger = HeatExchanger(heat_capacity,
                                            max_mass_flow_p, surface_area,
                                            heat_transfer_q, heat_transfer_k,
                                            heat_transfer_k_max, demand_capacity)

        if interpolation_values is not None:
            self.heat_exchanger.add_interpolation_values(interpolation_values)

        self.pressure_load = pressure_load
        # The HX has a physical lower requirement of the temperature, however,
        # in reality we might not want to go that far. Instead, we will set some artificial bound.
        self.min_supply_temp_artificial_bound = min_supply_temp
        self.setpoint_t_supply_s = setpoint_t_supply_s
        self.t_return_s = t_return_s
        self.energy_unit_conversion = energy_unit_conversion
        self.demand = demand
        # the _demand and _q is demand in W, instead of MW, and they are private variables
        # that should not be called outside.
        self._demand_in_W = demand * self.energy_unit_conversion
        """
        minimum_t_supply_p is minimum possible supply inlet temperature
        sufficient to meet the heat demand for maximum primary mass flow.
        """

        self.minimum_t_supply_p = np.array(
            list(
                map(
                    lambda block: self.heat_exchanger.minimum_t_supply_p(
                        q=self._demand_in_W[block],
                        t_supply_s=self.setpoint_t_supply_s,
                        mass_flow_p=max_mass_flow_p,
                        mass_flow_s=self._demand_in_W[block]
                        / (
                            heat_capacity * (self.setpoint_t_supply_s - self.t_return_s)
                        ),
                        demand = demand[block],
                    ),
                    range(self.blocks),
                )
            )
        )

        self.minimum_t_supply_p[
            self.minimum_t_supply_p < min_supply_temp
        ] = min_supply_temp
        self.s_supply_temp = np.full(
            self.blocks, np.nan, dtype=float
        )  # secondary supply network inlet temperature

        self.alpha, self.pressure = None, None

    def clear(self) -> None:
        blocks = self.blocks
        self.q = np.full(blocks, np.nan, dtype=float)  # heat demand in MW
        self._q_in_W = np.full(blocks, np.nan, dtype=float)  # heat demand in W
        self.alpha = np.full(blocks, np.nan, dtype=float)
        self._clear()
        self.pressure = np.full(
            (self.blocks, 2), (self.pressure_load, 0), dtype=float
        ).T
        self.entry_step_global = np.full(blocks, np.nan, dtype=float)
        self.real_time_delay = np.full(blocks, np.nan, dtype=float) # delay from producer to consumer

    def update_demand(
        self,
        demand: np.ndarray,
    ) -> None:
        self.demand = demand
        self._demand_in_W = demand * self.energy_unit_conversion
        self.minimum_t_supply_p = np.array(
            list(
                map(
                    lambda block: self.heat_exchanger.minimum_t_supply_p(  # bound
                        q=self._demand_in_W[block],
                        t_supply_s=self.setpoint_t_supply_s,
                        mass_flow_p=self.heat_exchanger.max_mass_flow_p,
                        mass_flow_s=self._demand_in_W[block]
                        / (
                            self.heat_exchanger.heat_capacity
                            * (self.setpoint_t_supply_s - self.t_return_s)
                        ),
                        demand = demand[block],
                    ),
                    range(self.blocks),
                )
            )
        )

        self.minimum_t_supply_p[
            self.minimum_t_supply_p < self.min_supply_temp_artificial_bound
        ] = self.min_supply_temp_artificial_bound

    def get_outlet_temp(self, slot: int) -> float:
        """
        Is called from downstream to get the average outlet temperature in the
        coming step.
        """
        assert slot == 1

        outlet_temp = self.temp[1, self.current_step]
        if self._safety_check:
            assert not np.isnan(outlet_temp)

        return outlet_temp, self.entry_step_global[self.current_step]

    def set_mass_flow(self, slot: int, mass_flow: float) -> None:
        """
        Called from supply downstream or return upstream to inform this node
        that the downstream edge wants to consume the provided plug at provided
        mass flow.
        """
        raise Exception("set_mass_flow should not be called on a consumer")

    def solve(self) -> None:
        """
        Plugs of the water chunks are reversed, and heat loss equation is applied depending on the
        entry step of the water chunk. Then, chunks are iterated until the mass pushed outside of the pipe
        doesn't become equal to the possible mass stored inside the pipe.

        Secondary side mass flow is calculated based on the heat demand as input, and constant temperatures
        of the secondary network: constant setpoint supply temperature, and constant return temperature.
        """

        mass_flow_s = self._demand_in_W[self.current_step] / (
            self.heat_exchanger.heat_capacity * (self.setpoint_t_supply_s - self.t_return_s)
        )
        # output temperature of supply network
        sup_temp_mass_bundle = self.edges[0].get_outlet_temp_mass_bundle()
        total_time = 0
        consumed_mass = []
        t_supply_p_list = []
        t_return_p_list = []
        t_supply_s_list = []
        entry_steps_global = []

        self.violations["supply temp"][self.current_step] = 0
        for t_supply_p, mass, entry_step_global in sup_temp_mass_bundle:
            if t_supply_p < self.minimum_t_supply_p[self.current_step]:
                self.violations["supply temp"][self.current_step] = min(
                    t_supply_p - self.minimum_t_supply_p[self.current_step],
                    self.violations["supply temp"][self.current_step],
                )

            (
                mass_flow_p,  # primary mass flow
                t_return_p,  # inlet temperature of the return primary grid
                t_supply_s,  # inlet temperature of the supply secondary grid
                q,
            ) = self.heat_exchanger.solve(
                t_supply_p=t_supply_p,
                setpoint_t_supply_s=self.setpoint_t_supply_s,
                t_return_s=self.t_return_s,
                # Customer demand should be lower than what his pump allows.
                # Therefore, secondary mass flow can be very high
                mass_flow_s=mass_flow_s,
                demand=self.demand[self.current_step],
            )

            t_supply_p_list.append(t_supply_p)
            t_return_p_list.append(t_return_p)
            t_supply_s_list.append(t_supply_s)
            entry_steps_global.append(entry_step_global)
            """
            Function solve() is called in every time-step. Here, we try to estimate 
            a consumed mass during that time-step.
            """

            if (mass / mass_flow_p + total_time) < self.interval_length:
                consumed_mass.append(mass)
                total_time += mass / mass_flow_p
            else:
                consumed_mass.append(mass_flow_p * (self.interval_length - total_time))
                break
        # average outlet temperature of the primary supply side network
        t_supply_p = np.sum(
            np.array(t_supply_p_list) * np.array(consumed_mass)
        ) / np.sum(consumed_mass)
        # average inlet temperature of the primary return side network
        t_return_p = np.sum(
            np.array(t_return_p_list) * np.array(consumed_mass)
        ) / np.sum(consumed_mass)
        # average inlet temperature of the secondary supply side network
        t_supply_s = np.sum(
            np.array(t_supply_s_list) * np.array(consumed_mass)
        ) / np.sum(consumed_mass)
        mass_flow_p = np.sum(consumed_mass) / self.interval_length

        entry_step_global = np.sum(
            np.array(entry_steps_global) * np.array(consumed_mass)
        )/ np.sum(consumed_mass)
        """Problematic part"""
        if (mass_flow_p == 0) & (t_supply_p <= self.t_return_s):
            mass_flow_p = self.heat_exchanger.max_mass_flow_p
            t_return_p = t_supply_p

        self.mass_flow[0, self.current_step] = mass_flow_p
        self.mass_flow[1, self.current_step] = mass_flow_p
        self.temp[0, self.current_step] = t_supply_p
        self.temp[1, self.current_step] = t_return_p
        self._q_in_W[self.current_step] = (
            mass_flow_p * (t_supply_p - t_return_p) * self.heat_exchanger.heat_capacity
        )  # what is actually delivered to the consumer

        self.q[self.current_step] = (
            self._q_in_W[self.current_step] / self.energy_unit_conversion
        )
        self.s_supply_temp[self.current_step] = t_supply_s
        self.alpha[self.current_step] = (t_return_p - self.t_return_s) / (
            t_supply_p - self.t_return_s
        )

        self.entry_step_global[self.current_step] = entry_step_global
        self.real_time_delay[self.current_step] = self.current_step - entry_step_global

        if not np.isnan(self.violations["supply temp"][self.current_step]):
            self.violations["heat delivered"][self.current_step] = (
            	round(self.q[self.current_step] - self.demand[self.current_step],3)
            )

        self.solvable_callback(self.edges[0], 1, mass_flow_p)
        self.solvable_callback(self.edges[1], 0, mass_flow_p)

        return None

    def debug(self, csv: bool = False) -> None:
        data = []
        for block in range(0, self.blocks):
            debug_values = [
                        "{:.0f}".format(self.q[block]),
                        "{:.0f}".format(self.demand[block] - self.q[block]),
                        "{:,.5f}".format(self.minimum_t_supply_p[block]),
                        "{:.2f}".format(self.alpha[block]),
                    ]
            if csv:
                debug_values[2] = "{:.1f}".format(self.minimum_t_supply_p[block]),

            data.append(debug_values)

        super()._debug(
            csv,
            ["Q (W)", "Unfulfilled Q (W)", "Minimum supply temp (ºC)", "Alpha"],
            data,
        )

    def unfulfilled_demand(self, up_to_step: Optional[int]) -> float:
        if up_to_step is None:
            last_step = self.blocks
        else:
            last_step = up_to_step + 1

        return (
            np.sum(self.demand[0:last_step] - self.q[0:last_step])
            * self.interval_length
            / 3600  # in MWh
        )


    @property
    def type_name(self) -> str:
        return "Consumer"

    @property
    def is_supply(self) -> bool:
        return False

if __name__ == '__main__':
    heat_capacity = 4181.3
    max_mass_flow_p = 805
    surface_area = 400
    heat_transfer_q = 0.8
    heat_transfer_k = 5 * 10 ** 6 / 400 * (400 ** (-0.8) + 400 ** (-0.8))
    heat_transfer_k_max = None
    demand_capacity = None
    hx = HeatExchanger(heat_capacity,
                        max_mass_flow_p, surface_area,
                        heat_transfer_q, heat_transfer_k,
                        heat_transfer_k_max, demand_capacity)


    ts_supply_p = np.arange(200)/50+70
    mass_flows_p = []
    qs = []
    for t_supply_p in ts_supply_p:
        demand = 14.51*10**6
        # t_supply_p = 72
        setpoint_t_supply_s = 70
        t_return_s = 45
        mass_flow_s = demand / (
                heat_capacity * (setpoint_t_supply_s - t_return_s)
            )
        (
            mass_flow_p,  # primary mass flow
            t_return_p,  # inlet temperature of the return primary grid
            t_supply_s,  # inlet temperature of the supply secondary grid
            q,
        ) = hx.solve(
            t_supply_p=t_supply_p,
            setpoint_t_supply_s=setpoint_t_supply_s,
            t_return_s=t_return_s,
            # Customer demand should be lower than what his pump allows.
            # Therefore, secondary mass flow can be very high
            mass_flow_s=mass_flow_s,
            demand=demand,
        )
        mass_flows_p.append(mass_flow_p)
        qs.append(q)

    qs = np.array(qs)
    ts_supply_p = np.array(ts_supply_p)
    mass_flows_p = np.array(mass_flows_p)
    idx1 = (qs < 14.51*10**6 - 0.01*10**6)
    idx1[np.argmin(idx1)] = 1
    idx2 = (qs >= 14.51*10**6 - 0.01*10**6)
    import matplotlib.pyplot as plt 
    plt.plot(ts_supply_p[idx1],mass_flows_p[idx1], c='r', label='demand not satisfied')
    plt.plot(ts_supply_p[idx2],mass_flows_p[idx2], c='b', label='demand satisfied')
    plt.xlabel("supply temp")
    plt.ylabel("mass flow")
    plt.legend()
    plt.show()