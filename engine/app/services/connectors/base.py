import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter using time.sleep."""

    def __init__(self, requests_per_second: float = 2.0):
        self._interval = 1.0 / requests_per_second
        self._last_request: float = 0.0

    def wait(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self._interval:
            time.sleep(self._interval - elapsed)
        self._last_request = time.monotonic()


class BaseConnector(ABC):
    """Interface that all data source connectors must implement."""

    def __init__(self, credentials: dict):
        self.credentials = credentials

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify that the credentials are valid and the source is reachable."""

    @abstractmethod
    def fetch_data(
        self,
        data_type: str,
        since: datetime | None = None,
    ) -> pd.DataFrame:
        """Pull data from the source and return a canonical-schema DataFrame.

        Args:
            data_type: One of 'orders', 'customers', 'products', 'reviews'.
            since: If provided, only fetch records updated after this timestamp
                   (for incremental sync).
        """

    @abstractmethod
    def get_available_data_types(self) -> list[str]:
        """Return the list of data types this connector can provide."""
