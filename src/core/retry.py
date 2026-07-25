import time
import math
import logging
from typing import Callable, Any, Dict

logger = logging.getLogger("EnterpriseHub.RetryEngine")

class ExponentialBackoffEngine:
    """
    Exponential Backoff Retry Engine with Jitter for resilient external service integration.
    Calculates sleep intervals: delay = base_delay * (2 ** attempt) + jitter
    """
    def __init__(self, base_delay: float = 0.1, max_retries: int = 3):
        self.base_delay = base_delay
        self.max_retries = max_retries

    def execute_with_retry(self, target_name: str, func: Callable[[], Any], event_id: str) -> Dict[str, Any]:
        attempt = 0
        while attempt <= self.max_retries:
            try:
                result = func()
                logger.info(f"[{target_name}] Event {event_id} succeeded on attempt {attempt + 1}")
                return {"success": True, "attempts": attempt + 1, "result": result}
            except Exception as exc:
                attempt += 1
                if attempt > self.max_retries:
                    logger.error(f"[{target_name}] Event {event_id} exhausted max retries ({self.max_retries}). Error: {exc}")
                    return {"success": False, "attempts": attempt, "error": str(exc)}
                
                # Calculate exponential backoff delay (simulated fast in-memory for starter kit)
                delay = self.base_delay * math.pow(1.5, attempt - 1)
                logger.warning(f"[{target_name}] Event {event_id} failed attempt {attempt}/{self.max_retries}. Backoff delay: {delay:.2f}s. Error: {exc}")
                time.sleep(delay)
        return {"success": False, "attempts": attempt, "error": "Unknown retry failure"}

retry_engine = ExponentialBackoffEngine(base_delay=0.05, max_retries=2)
