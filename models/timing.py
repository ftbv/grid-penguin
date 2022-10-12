# A class that can be used as a stopwatch to time execution duration

from datetime import datetime


class Timing:
    """
    Timing class
    """

    def __init__(self, start: bool = True) -> None:
        self._spent: float = 0
        self._running = False
        self.started_at: float = 0
        if start:
            self.start()

    def start(self) -> None:
        if self._running:
            return

        self.started_at = datetime.now().timestamp()
        self._running = True

    def stop(self) -> None:
        if self._running:
            self._spent += datetime.now().timestamp() - self.started_at
            self._running = False

    def restart(self) -> None:
        self._running = False
        self._spent = 0
        self.start()

    def get(self) -> float:
        if not self._running:
            return self._spent

        return self._spent + datetime.now().timestamp() - self.started_at
