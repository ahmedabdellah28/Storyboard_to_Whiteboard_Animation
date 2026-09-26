import time
import random
from typing import Callable, TypeVar, Any, Optional
from .logging import log

T = TypeVar("T")

class RetryManager:
    """Handles transient execution failures with exponential backoff and jitter."""
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_sec: float = 1.5,
        backoff_multiplier: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay_sec = initial_delay_sec
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter

    def execute(
        self,
        func: Callable[..., T],
        operation_name: str = "Operation",
        *args: Any,
        **kwargs: Any
    ) -> T:
        delay = self.initial_delay_sec
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                err_str = str(e)
                log.warn(f"{operation_name} failed attempt {attempt}/{self.max_retries}: {err_str}")
                
                if attempt >= self.max_retries:
                    break

                sleep_time = delay
                if self.jitter:
                    sleep_time = delay * random.uniform(0.8, 1.2)
                
                time.sleep(sleep_time)
                delay *= self.backoff_multiplier

        log.error(f"{operation_name} failed permanently after {self.max_retries} attempts.")
        raise last_exception if last_exception else RuntimeError(f"{operation_name} failed")
