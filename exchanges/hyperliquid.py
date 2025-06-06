# exchanges/hyperliquid.py
from exchanges.base import ExchangeFetcher
from datetime import datetime, timezone
from typing import Optional, Tuple
import websockets
import traceback
import logging
import asyncio
import json

# logger = logging.getLogger(__name__)
logger = logging.getLogger("cex_dex_arbitrage.exchanges.hyperliquid")


class HyperliquidFetcher(ExchangeFetcher):
    def __init__(self, pair: str):
        super().__init__("Hyperliquid", pair)
        self.latest_price: Optional[float] = None
        self.ws_url = "wss://api.hyperliquid.xyz/ws"
        self.connected = False
        self._reconnect_interval = 5  # seconds

    async def connect(self):
        async def listener():
            while True:
                try:
                    # logger.debug(f"[Hyperliquid] Connecting WebSocket for {self.pair}...")
                    async with websockets.connect(self.ws_url) as ws:
                        subscription_message = {
                            "method": "subscribe",
                            "subscription": {
                                "type": "l2Book",
                                # "coin": "BTC",
                                "pair": self.pair.replace("/", "-").upper(),
                            }
                        }
                        await ws.send(json.dumps(subscription_message))
                        self.connected = True
                        response = await ws.recv()
                        # logger.debug(f"[Hyperliquid] Subscription response: {response}")

                        # logger.debug(f"[Hyperliquid] Connected and subscribed for {self.pair}")
                        async for message in ws:
                            # logger.debug(f"[Hyperliquid] Raw message: {message}")  # moved to top
                            data = json.loads(message)

                            if data.get("channel") == "l2Book":
                                book_data = data.get("data", {})
                                levels = book_data.get("levels", [])
                                if isinstance(levels, list) and len(levels) >= 2:
                                    bids = levels[0]
                                    asks = levels[1]
                                    if bids and asks:
                                        best_bid = float(bids[0]["px"])
                                        best_ask = float(asks[0]["px"])
                                        self.latest_price = (best_bid + best_ask) / 2
                                        # logger.debug(f"[Hyperliquid] Latest price for {self.pair}: {self.latest_price:.4f}")


                except Exception as e:
                    self.connected = False
                    logger.error(f"[WebSocket] Hyperliquid error ({self.pair}): {e}, {traceback.format_exc()}")
                    logger.info(f"[WebSocket] Reconnecting in {self._reconnect_interval} seconds...")
                    await asyncio.sleep(self._reconnect_interval)

        asyncio.create_task(listener())

    async def get_price(self) -> Optional[Tuple[float, datetime]]:
        return self.latest_price,  datetime.now(timezone.utc)

