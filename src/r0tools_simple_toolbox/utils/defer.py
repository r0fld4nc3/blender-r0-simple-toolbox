import time
from typing import Any, Callable, Dict, Optional

import bpy


class DeferredTimerManager:
    def __init__(self):
        self._timers: Dict[str, Dict[str, Any]] = {}

    def schedule(
        self,
        func: Callable,
        args=(),
        kwargs=None,
        delay: float = 0.1,
        min_interval: float = 0.0,
        timer_id: Optional[str] = None,
    ):
        """
        Schedule a function to run after a delay.

        Args:
            func: Function to execute
            delay: Initial delay in seconds
            min_interval: Minimum time between executions (0 = no limit)
            timer_id: Unique identifier (defaults to function name)

        Returns:
            bool: True if scheduled, False if already pending or throttled
        """

        if kwargs is None:
            kwargs = {}

        timer_id = timer_id or f"{func.__name__}_{id(args)}_{id(kwargs)}"

        if timer_id not in self._timers:
            self._timers[timer_id] = {
                "func": func,
                "args": args,
                "kwargs": kwargs,
                "pending": False,
                "last_run": 0,
                "min_interval": min_interval,
            }

        timer_info = self._timers[timer_id]

        if timer_info["pending"]:
            return False

        # Check minimum interval
        if min_interval > 0:
            time_since_last = time.time() - timer_info["last_run"]
            if time_since_last < min_interval:
                return False

        # Wrapper function
        def wrapper():
            if timer_id not in self._timers:
                return None

            result = timer_info["func"](*timer_info["args"], **timer_info["kwargs"])

            # Update state
            timer_info["pending"] = False
            timer_info["last_run"] = time.time()

            return result if isinstance(result, (int, float)) else None

        # Schedule
        timer_info["pending"] = True
        bpy.app.timers.register(wrapper, first_interval=delay)
        return True

    def is_pending(self, timer_id: str) -> bool:
        return self._timers.get(timer_id, {}).get("pending", False)

    def clear(self, timer_id: str):
        if timer_id in self._timers:
            del self._timers[timer_id]

    def clear_all(self):
        self._timers.clear()


# Global instance
timer_manager = DeferredTimerManager()


# Decorator
def deferred(delay: float = 0.1, min_interval: float = 0.0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            def executor():
                result = func(*args, **kwargs)

                return result if isinstance(result, (int, float)) else None

            timer_manager.schedule(
                executor, args=args, kwargs=kwargs, delay=delay, min_interval=min_interval, timer_id=func.__name__
            )

        return wrapper

    return decorator
