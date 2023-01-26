# A node that combines incoming edges into a single outgoing edge

from typing import Optional
from .connector import Connector

import numpy as np  # type: ignore


class Junction(Connector):
    """
    A junction node consists of input slots and one output slot.
    The number of input slots is an input variable.
    """

    def __init__(
        self,
        blocks: int,
        in_slots_number: int = 2,
        id: Optional[int] = None,
        default_valve_position: Optional[float] = None,  # within (0,1)
    ) -> None:
        slots = ["Out"]
        for i in range(1, in_slots_number + 1):
            slots.append("In %s" % i)
        slots = tuple(slots)

        super().__init__(
            id=id,
            slots=slots,
            blocks=blocks,
            default_valve_position=default_valve_position
        )

    def get_outlet_temp(self, slot: int) -> float:
        """
        Is called from downstream to get the average outlet temperature in the
        coming step.
        """
        assert slot == 0

        mass_flows_in = self.mass_flow[1:, self.current_step]
        if not any(np.isnan(mass_flows_in)):
            if np.sum(self.mass_flow[1:, self.current_step]) == 0:
                pos = np.zeros(len(self.slots) - 1)
                pos[0] = 1
            else:
                pos = self.mass_flow[1:, self.current_step] / np.sum(
                    self.mass_flow[1:, self.current_step]
                )
        else:
            # supply, pos should be pre-set
            pos = self.valve_position[self.current_step]
            assert not np.isnan(pos)

        entry_step_global = []
        for i in range(1, len(self.slots)):
            self.temp[i, self.current_step], e_s_g = self.edges[i].get_outlet_temp()
            entry_step_global.append(e_s_g)

        self.temp[0, self.current_step] = np.sum(
            pos * self.temp[1:, self.current_step]
        )
        self.entry_step_global = np.sum(
            pos*np.array(entry_step_global)
        )

        return self.temp[0, self.current_step], self.entry_step_global

    def set_mass_flow(self, slot: int, mass_flow: float) -> None:
        """
        Called from supply downstream or return upstream to inform this node
        about the mass flow in the coming step
        """
        super().set_mass_flow_in_direction(slot, mass_flow, True)
