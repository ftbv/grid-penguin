# A node that splits an incoming edge into outgoing edges

from typing import Optional
from .connector import Connector
import numpy as np  # type: ignore


class Branch(Connector):
    """
    A branch node consists of one input slot and output slots.
    The number of output slots is an input variable.
    """

    def __init__(
        self,
        blocks: int,
        out_slots_number: int = 2,
        id: Optional[int] = None,
        default_valve_position: Optional[float] = None,  # within (0,1)
    ) -> None:
        slots = ["In"]
        for i in range(1, out_slots_number + 1):
            slots.append("Out %s" % i)
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
        assert slot != 0

        if np.isnan(self.temp[slot, self.current_step]):

            outlet_temp, entry_step_global = self.edges[0].get_outlet_temp()
            self.temp[:, self.current_step] = outlet_temp
            self.entry_step_global = entry_step_global
        else:
            outlet_temp = self.temp[slot, self.current_step]
            entry_step_global = self.entry_step_global

        return outlet_temp, entry_step_global

    def set_mass_flow(self, slot: int, mass_flow: float) -> None:
        """
        Called from supply downstream or return upstream to inform this node
        about the mass flow in the coming step
        """
        super().set_mass_flow_in_direction(slot, mass_flow, False)
