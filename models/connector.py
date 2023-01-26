# A node that combines multiple edges from one side and a single from the other

from typing import Optional
from .node import Node

import numpy as np  # type: ignore


class Connector(Node):
    """
    A connector node consists of a single edge in one direction
    and one or more in the other.
    """

    def __init__(
        self,
        blocks: int,
        slots: tuple,
        id: Optional[int] = None,
        default_valve_position: Optional[float] = None,  # within (0,1)
    ) -> None:
        super().__init__(
            id=id,
            slots=slots,
            blocks=blocks,
        )

        def_valve = np.nan
        if default_valve_position is not None:
            def_valve = default_valve_position

        self.valve_position = np.full(self.blocks, def_valve, dtype=float)
        self.entry_step_global = None

    def set_mass_flow_in_direction(self, slot: int, mass_flow: float, direction: bool) -> None:
        """
        Called from supply downstream or return upstream to inform this node
        about the mass flow in the coming step.

        The direction determines the slot number of successive edges
        and has a value of either False (flow from main edge to side edges)
        or True (flow from side edges to main edge).
        """
        self.mass_flow[slot, self.current_step] = mass_flow

        if slot == 0:
            self.set_mass_flow_split(mass_flow, direction)
        else:
            self.set_mass_flow_joint(slot, direction)

    def set_mass_flow_split(self, mass_flow: float, direction: bool):
        """
        Secondary mass flow is calculated and all secondary edges are added
        to the list of solvable_objects
        """
        pos = self.valve_position[self.current_step]
        assert not np.isnan(pos)
        self.mass_flow[1:, self.current_step] = pos * mass_flow

        for i in range(1, len(self.slots)):
            self.solvable_callback(
                self.edges[i], int(direction), self.mass_flow[i, self.current_step]
            )

        self.pressure[:, self.current_step] = self.edges[0].pressure[
            1-direction, self.current_step
        ]

    def set_mass_flow_joint(self, slot: int, direction: bool):
        """
        Main mass flow is calculated as the sum of mass flows corresponding to the
        side edges.
        """
        self.pressure[slot, self.current_step] = self.edges[slot].pressure[
            int(direction), self.current_step
        ]

        if not any(np.isnan(self.mass_flow[1:, self.current_step])):
            propelled_mass_flow = np.sum(self.mass_flow[1:, self.current_step])

            self.mass_flow[0, self.current_step] = propelled_mass_flow
            self.pressure[:, self.current_step] = max(
                self.pressure[1:, self.current_step]
            ) if direction == 0 else min(
                self.pressure[1:, self.current_step])

            # the main edge is added to the list _solvable_objects of the object grid.
            self.solvable_callback(self.edges[0], 1 - direction, propelled_mass_flow)
