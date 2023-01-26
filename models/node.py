# The parent class of all node types

from typing import Tuple, List, TYPE_CHECKING, Optional
import numpy as np  # type: ignore
from beautifultable import BeautifulTable  # type: ignore
import os
from functools import cached_property
from collections import defaultdict
from .grid_object import GridObject
from .plug import Plug

if TYPE_CHECKING:
    from .edge import Edge


class Node(GridObject):
    """
    A node consist of 2 slots to connect edges to and keeps track of mass flow,
    temperature and energy
    """

    def __init__(
        self,
        slots: Tuple[str, ...],
        blocks: int,
        id: Optional[int] = None,
    ) -> None:
        super().__init__(id=id)

        self.blocks = blocks
        self.slots = slots
        self.edges = None
        self.q, self._q_in_W = None, None
        self.entry_step_global = None

    def clear(self) -> None:
        self._clear()

    def _clear(
        self,
        temp: Optional[np.ndarray] = None,
        mass_flow: Optional[np.ndarray] = None,
    ) -> None:
        super().clear()

        blocks = self.blocks
        slots = len(self.slots)

        if temp is None:
            self.temp = np.full((slots, blocks), np.nan, dtype=float)
        else:
            self.temp = temp

        if mass_flow is None:
            self.mass_flow = np.full((slots, blocks), np.nan, dtype=float)
        else:
            self.mass_flow = mass_flow

        self.plugs: List[Optional[Plug]] = [None] * slots

        self.violations = defaultdict(lambda: np.full(blocks, np.nan, dtype=np.float))
        """
        consumer violations:
           key1: 'supply temp' (only negative value) is the minimal temp from the bundle,
                  that is lower than min_supply_temp
           key2: 'heat delivered' (only negative value) is only non-nan value if key1 is non-nan.
                  producer violations:
           key1: 'supply temp' (only positive value and only exit when control with heat)
                  represents whether the producer over-produces heat and heats up the water to
                  physically impossible or undesired temperature
           additional keys: check specific producer modules for additional keys
        """

        self.pressure = np.full((slots, blocks), np.nan, dtype=float)

    def link(self, edges: Tuple["Edge", ...]) -> None:
        assert len(edges) == len(self.slots)
        self.edges = edges

    def get_outlet_temp(self, slot: int) -> float:
        """
        Is called from downstream to get the average outlet temperature in the
        coming step.
        """
        raise Exception("Should be implemented by child class")

    def set_mass_flow(self, slot: int, mass_flow: float) -> None:
        """
        Called from supply downstream or return upstream to inform this node
        about the mass flow in the coming step
        """
        raise Exception("Should be implemented by child class")

    def solve(self) -> None:
        """
        Used for Consumers and for the CHP unit
        """
        raise Exception("Should be implemented by child class")

    def debug(self, csv: bool = False) -> None:
        self._debug(csv=csv)

    def _debug(
        self,
        csv: bool,
        additional_headers: List[str] = [],
        additional_data: List[List[str]] = [],
    ) -> None:
        print("{} {}".format(type(self).__name__, self.id))

        column_headers = ["Time block"]
        for slot in self.slots:
            column_headers += [
                "{}: Temp (°C)".format(slot),
                "{}: Mass flow (kg/s)".format(slot),
            ]

        column_headers += additional_headers

        if csv:
            print(",".join(column_headers))
        else:
            ts = os.get_terminal_size()
            table = BeautifulTable(
                max_width=ts.columns - 1,
                default_alignment=BeautifulTable.ALIGN_RIGHT,
            )

            table.column_headers = column_headers

        for time in range(
            0,
            self.blocks,
        ):
            row = ["{}".format(time)]
            for i in range(0, len(self.slots)):
                row += [
                    "{:.2f}".format(self.temp[i, time]),
                    "{:.0f}".format(self.mass_flow[i, time]),
                ]
            if len(additional_headers) > 0:
                row += additional_data[time]

            if csv:
                print(",".join(row))
            else:
                table.append_row(row)

        if not csv:
            print(table)

    def unfulfilled_demand(self, up_to_step: Optional[int]) -> float:
        return 0

    @property
    def costs(self) -> float:
        return 0

    @property
    def type_name(self) -> str:
        raise Exception("Should be implemented by child class")

    @cached_property
    def is_supply(self) -> bool:
        # upstream edge should always come first
        if self.__class__.__name__ == "Junction":
            for edge in self.edges[1:]:
                return edge.is_supply

        else:
            for edge in self.edges:
                return edge.is_supply
