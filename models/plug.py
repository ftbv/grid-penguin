# A plug of water


class Plug:
    def __init__(
        self,
        mass: float,
        entry_step: float,
        entry_temp: float,
    ) -> None:
        self.entry_step = entry_step
        self.mass = mass
        self.entry_temp = entry_temp
