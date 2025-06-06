
from datetime import datetime, timezone
from typing import Optional, Tuple

# --- Base Fetcher ---
class ExchangeFetcher:
    def __init__(self, name: str, pair: str):
        self.name = name
        self.pair = pair
        self.latest_price: Optional[float] = None
        self.connected = False
        self._reconnect_interval = 5  # default retry time in seconds

    async def connect(self):
        """Start WebSocket or background task, if applicable."""
        pass

    async def get_price(self) -> Optional[Tuple[float, datetime]]:
        if self.latest_price is not None:
            return self.latest_price, datetime.now(timezone.utc)
        return None, None
