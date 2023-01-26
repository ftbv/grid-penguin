# A plug of water


class Plug:
    def __init__(
        self,
        mass: float,
        entry_step: int,
        entry_temp: float,
        entry_step_global: float, # the entry step of this plug into the supply grid. aka. leaving the producer
    ) -> None:
        self.entry_step = int(entry_step)
        self.mass = mass
        self.entry_temp = entry_temp
        self.entry_step_global = entry_step_global
