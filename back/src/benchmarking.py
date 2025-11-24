import time
from typing import Dict, Optional


class StageTimer:
    """Timer for measuring execution time of different emulation stages.

    Usage:
        timer = StageTimer()

        with timer.stage("topology_creation"):
            # ... topology creation code ...
            pass

        with timer.stage("network_start"):
            # ... network start code ...
            pass

        results = timer.as_dict()
        # Returns: {"topology_creation": 1.234, "network_start": 0.567, ...}
    """

    def __init__(self):
        self._stage_times: Dict[str, float] = {}
        self._current_stage: Optional[str] = None
        self._stage_start: Optional[float] = None

    def stage(self, name: str):
        """Context manager for timing a stage.

        Args:
            name: Name of the stage to time

        Returns:
            Context manager that times the stage
        """
        return _StageContext(self, name)

    def _start_stage(self, name: str) -> None:
        if self._current_stage is not None:
            raise RuntimeError(
                f"Cannot start stage '{name}' while stage '{self._current_stage}' is running"
            )
        self._current_stage = name
        self._stage_start = time.time()

    def _end_stage(self, name: str) -> None:
        if self._current_stage != name:
            raise RuntimeError(
                f"Cannot end stage '{name}', current stage is '{self._current_stage}'"
            )
        if self._stage_start is None:
            raise RuntimeError(f"Stage '{name}' was not started")

        elapsed = time.time() - self._stage_start
        self._stage_times[name] = elapsed
        self._current_stage = None
        self._stage_start = None

    def as_dict(self) -> Dict[str, float]:
        """Return all stage timings as a dictionary.

        Returns:
            Dictionary mapping stage names to elapsed times in seconds
        """
        return self._stage_times.copy()

    def total_time(self) -> float:
        """Return total time across all stages.

        Returns:
            Total elapsed time in seconds
        """
        return sum(self._stage_times.values())


class _StageContext:
    def __init__(self, timer: StageTimer, name: str):
        self._timer = timer
        self._name = name

    def __enter__(self):
        self._timer._start_stage(self._name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._timer._end_stage(self._name)
        return False
