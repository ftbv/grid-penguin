# add CHP as a child class of producer
# instead of an independent thing from grid
import numpy as np
from typing import Optional

from ..producer import Producer
from util import math_functions


class CHP(Producer):
    """CHP unit is the type of the producer"""

    def __init__(
        self,
        CHPPreset,
        blocks: int,  # number of time steps
        heat_capacity: float = 4181.3,  # in J/kg/K # for the water
        temp_upper_bound=120,
        pump_efficiency: float = 0.9,
        density=963,
        control_with_temp: bool = False,
        production_costs: Optional[np.ndarray] = None,  # in EUR/J
        energy_unit_conversion: int = 10 ** 6,
        id: Optional[int] = None,
    ):
        super(CHP, self).__init__(
            blocks,
            id,
            heat_capacity,  # in J/kg/K # for the water
            temp_upper_bound,
            pump_efficiency,
            density,
            control_with_temp,
            energy_unit_conversion,
        )
        if CHPPreset["CHPType"] == "keypts":
            self.operation_region = np.array(
                math_functions.points_sort_clockwise(CHPPreset["OperationRegion"])
            )
            self.cost_array = np.array(CHPPreset["FuelCost"])
        else:
            raise Exception("CHP type not supported")

        self.efficiency = CHPPreset["Efficiency"]
        self.rampQ = CHPPreset["MaxRampRateQ"]
        self.rampE = CHPPreset["MaxRampRateE"]
        self.rampT = CHPPreset["MaxRampRateTemp"]

        self.maxQ = max(self.operation_region[:, 0])
        self.maxE = max(self.operation_region[:, 1])

        self.e_price = np.zeros(self.blocks, dtype=float)

        self.E, self.cost, self.profit = None, None, None
        self.production_cost, self.ramp_cost, self.pump_electricity_cost = None, None, None
        self.hisQ, self.hisE, self.hisT = None, None, None

    def clear(self):
        super(CHP, self).clear()
        self.E = np.full(self.blocks, np.nan, dtype=float)
        self.cost = np.full(self.blocks, np.nan, dtype=float)
        self.profit = np.full(self.blocks, np.nan, dtype=float)
        self.production_cost = np.full(self.blocks, np.nan, dtype=float)
        self.ramp_cost = np.full(self.blocks, np.nan, dtype=float)
        self.pump_electricity_cost = np.full(self.blocks, np.nan, dtype=float)
        self.hisQ, self.hisE, self.hisT = None, None, None

    def preset(self, hisQ, hisE, hisT):
        self.hisQ = hisQ
        self.hisE = hisE
        self.hisT = hisT

    def solve(self):
        # violation of CHP has 4 additional keys:
        # key1: 'Q ramp(%)' how much the change of Q exceed the limit, in percentage
        # key2: 'E ramp(%)' how much the change of E exceed the limit, in percentage
        # key3: 'temp ramp(degree)' how much the change of temp exceed the limit, in degree celsius
        # key4: 'operation region(bool)' true if operate outside of operation region
        flag = 0
        # self.E[self.current_step] = e_prod
        if self.current_step > 0:
            px_q = self.q[self.current_step - 1]
            px_e = self.E[self.current_step - 1]
            px_temp = self.temp[1, self.current_step - 1]
        else:
            px_q = self.hisQ
            px_e = self.hisE
            px_temp = self.hisT

        self.violations["Q ramp(%)"][self.current_step] = self.check_ramp(
            self.q[self.current_step],
            px_q,
            self.rampQ,
            self.maxQ,
        )
        self.violations["E ramp(%)"][self.current_step] = self.check_ramp(
            self.E[self.current_step],
            px_e,
            self.rampE,
            self.maxE,
        )
        self.violations["temp ramp(degree)"][self.current_step] = self.check_ramp(
            self.temp[1, self.current_step],
            px_temp,
            self.rampT,
        )

        self.violations["operation region(bool)"][
            self.current_step
        ] = math_functions.check_point_in_polygon(
            [self.q[self.current_step], self.E[self.current_step]],
            self.operation_region,
        )

        self.production_costs[self.current_step] = (
            self.q[self.current_step] * self.cost_array[0]
            + self.E[self.current_step] * self.cost_array[1]
        )

        self.ramp_cost[self.current_step] = 0
        self.pump_electricity_cost[self.current_step] = (
            self.pump_power[self.current_step] * self.e_price[self.current_step]
        )
        self.cost[self.current_step] = (
            self.production_costs[self.current_step]
            + self.ramp_cost[self.current_step]
            + self.pump_electricity_cost[self.current_step]
        )
        self.profit[self.current_step] = (
            self.E[self.current_step] * self.e_price[self.current_step]
        )

    def get_margin(self, level_time: int = 0) -> dict:
        margin = super(CHP, self).get_margin(level_time)

        if level_time == 0:
            margin["cost"]["production_cost"] = np.sum(
                self.production_costs[: self.current_step]
            )
            margin["cost"]["ramp_cost"] = np.sum(self.ramp_cost[: self.current_step])
            margin["profit"] = np.sum(self.profit[: self.current_step])
        elif level_time == 1:
            margin["cost"]["production_cost"] = self.production_costs[
                : self.current_step
            ]
            margin["cost"]["ramp_cost"] = self.ramp_cost[: self.current_step]
            margin["profit"] = self.profit[: self.current_step]
        elif level_time == 2:
            margin["cost"]["production_cost"] = self.production_costs[
                self.current_step - 1
            ]
            margin["cost"]["ramp_cost"] = self.ramp_cost[self.current_step - 1]
            margin["profit"] = self.profit[self.current_step - 1]

        return margin

    # if range is provided, calculated with percentage limit, otherwise absolute limit
    def check_ramp(self, x, px, limit, range=1):
        if px is None:
            return False
        elif (limit > 0) & (px > 0) & (abs(x - px) / range > limit):
            return abs(x - px) / range - limit
        else:
            return False
