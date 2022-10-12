# A node that models a heat transfer station (connecting a primary and a secondary grid)

from typing import Optional
import numpy as np  # type: ignore

from .heat_exchanger import HeatExchanger
from .node import Node


class Transfer(Node):
    """
    A transfer consists of a heat exchanger, with both sides having
    two slots.
    """

    def __init__(
        self,
        blocks: int,
        id: Optional[int] = None,
        heat_capacity: float = 4181.3,  # in J/kg/K
        max_mass_flow_p: float = 1600,
        surface_area: float = 10,  # in m^2
        heat_transfer_q: float = 0.8,  # See Palsson 1999 p45
        heat_transfer_k: float = 50000,  # See Palsson 1999 p51
    ) -> None:
        super().__init__(
            id=id,
            slots=("Supply 1", "Return 1", "Supply 2", "Return 2"),
            blocks=blocks,
        )
        self.heat_exchanger = HeatExchanger(heat_capacity,
                                            max_mass_flow_p, surface_area,
                                            heat_transfer_q, heat_transfer_k)

        self.opt_temp = np.full(blocks, 75, dtype=float)

    def clear(self) -> None:
        blocks = self.blocks

        temp = np.stack(
            [
                np.full(blocks, np.nan, dtype=float),
                np.full(blocks, np.nan, dtype=float),
                self.opt_temp,
                np.full(blocks, np.nan, dtype=float),
            ]
        )

        self.q = np.full(blocks, np.nan, dtype=float)

        self._clear(temp=temp)

    def get_outlet_temp(self, slot: int) -> float:
        """
        Is called from downstream to get the average outlet temperature in the
        coming step.
        """
        assert slot == 1 or slot == 2

        if slot == 2:
            self.temp[0, self.current_step] = self.edges[0].get_outlet_temp()

            """
            We'd like to assure here that the outlet temp is as least as high
            as the secondary inlet temp, only we do not know that temp yet, as
            on the secondary side, outlet temps are not based on estimated
            mass flows, but actual mass flows as calculated by consumers.
            """
            self.temp[2, self.current_step] = min(
                self.opt_temp[self.current_step],
                self.temp[0, self.current_step],
            )

            return self.temp[2, self.current_step]

        # primary return
        assert not np.isnan(self.temp[1, self.current_step])
        return self.temp[1, self.current_step]

    def set_mass_flow(self, slot: int, mass_flow: float) -> None:
        """
        Called from supply downstream or return upstream to inform this node
        that the downstream edge wants to consume the provided plug at provided
        mass flow.
        """
        assert slot == 2 or slot == 3

        # write slot 3 mass flow for the first call and check on second
        if np.isnan(self.mass_flow[3, self.current_step]):
            self.mass_flow[3, self.current_step] = mass_flow
        else:
            assert mass_flow == self.mass_flow[3, self.current_step]

        if slot == 3:
            return

        self.temp[3, self.current_step] = self.edges[3].get_outlet_temp()

        if self.temp[3, self.current_step] > self.temp[2, self.current_step]:
            self.debug()
            raise Exception(
                "Transfer {} expected a t_supply_s of {:.1f} ºC, "
                " but t_return_s was higher ({:.1f} ºC).".format(
                    self.id,
                    self.temp[2, self.current_step],
                    self.temp[3, self.current_step],
                )
            )
            # secondary supply
        (mass_flow_p, t_return_p, t_supply_s, q,) = self.heat_exchanger.solve(
            t_supply_p=self.temp[0, self.current_step],
            setpoint_t_supply_s=self.temp[2, self.current_step],
            t_return_s=self.temp[3, self.current_step],
            mass_flow_s=mass_flow
        )

        self.mass_flow[0, self.current_step] = mass_flow_p
        self.mass_flow[1, self.current_step] = mass_flow_p
        self.mass_flow[2, self.current_step] = mass_flow
        self.mass_flow[3, self.current_step] = mass_flow
        self.temp[1, self.current_step] = t_return_p
        self.q[self.current_step] = q

        if self.temp[2, self.current_step] != t_supply_s:
            self.debug()
            raise Exception(
                "Transfer {} cannot fulfill t_supply_s of {:.1f} ºC, "
                " {:.1f} ºC is the maximum. Improve transfer characteristics?".format(
                    self.id,
                    self.temp[2, self.current_step],
                    t_supply_s,
                )
            )

        self.solvable_callback(self.edges[0], 1, mass_flow_p)
        self.solvable_callback(self.edges[1], 0, mass_flow_p)

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
