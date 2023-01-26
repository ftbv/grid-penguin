# Nodes and edges are child classes of this GridObject

from typing import Optional, Callable


class GridObject:
    _object_counter: int = 0
    _current_step: int = 0
    _safety_check = True

    def __init__(
        self,
        id: Optional[int] = None,
    ) -> None:
        if id is None:
            self.id = GridObject._object_counter
            GridObject._object_counter += 1
        else:
            self.id = id

        self.solvable_callback, self.interval_length = None, None

    def add_to_grid(
        self,
        solvable_callback: Callable[["GridObject", int, float], None],
        interval_length: int,  # in sec
    ) -> None:
        """
        Function solvable_callback of the superclass GridObject is initialized with the parameter function
        solvable of the class Grid when adding nodes and edges to the grid.
        """
        self.solvable_callback = solvable_callback
        self.interval_length = interval_length

    def set_mass_flow(self, slot: int, mass_flow: float) -> None:
        raise Exception("Should be implemented by child class")

    @property
    def current_step(self) -> int:
        return GridObject._current_step

    def clear(self) -> None:
        """
        To be overridden by child class
        """

    def debug(self, csv: bool = False) -> None:
        """
        To be overridden by child class
        """

    @staticmethod
    def increase_step() -> None:
        GridObject._current_step += 1

    @staticmethod
    def reset_step() -> None:
        """
        Sets time-step of the grid object on zero.
        """
        GridObject._current_step = 0
