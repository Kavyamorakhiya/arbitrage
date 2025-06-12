# exchanges/coinbase.py

from exchanges.base import ExchangeFetcher
from datetime import datetime, timezone
from typing import Optional, Tuple
import ccxt.pro
import asyncio
import logging
import traceback

# logger = logging.getLogger(__name__)
logger = logging.getLogger("cex_dex_arbitrage.exchanges.coinbase")

# class CoinbaseFetcher(ExchangeFetcher):
#     def __init__(self, pair: str):
#         super().__init__("Coinbase", pair)
#         self.exchange = ccxt.pro.coinbase()

#     async def connect(self):
#         async def listener():
#             while True:
#                 try:
#                     # logger.debug(f"[Coinbase] Connecting WebSocket for {self.pair}...")
#                     ticker = await self.exchange.watch_ticker(self.pair)
#                     self.latest_price = ticker["last"]
#                     self.connected = True
#                     # logger.debug(f"[Coinbase] Latest price for {self.pair}: {self.latest_price}")
#                 except Exception as e:
#                     self.connected = False
#                     logger.error(f"[WebSocket] Coinbase error ({self.pair}): {e}")
#                     logger.debug(traceback.format_exc())
#                     await asyncio.sleep(self._reconnect_interval)

#         asyncio.create_task(listener())

#     async def get_price(self) -> Optional[Tuple[float, datetime]]:
#         if self.latest_price is not None:
#             return self.latest_price, datetime.now(timezone.utc)
#         return None, None

#     async def get_order_book(self, limit: int = 100) -> Optional[Tuple[dict, datetime]]:
#         """
#         This Function is for fetching the order book for the given pair. 

#         The order book contains the top bids and asks and even timestamp
#         That data can be used for future arbitrage calculations.       
#         """
#         try:
#             order_book = await self.exchange.watch_order_book(self.pair, limit=limit)
#             logger.debug(f"[Coinbase] Order book for {self.pair}:")
#             logger.debug(f"\tAsks: {order_book['asks'][:5]}")
#             logger.debug(f"\tBids: {order_book['bids'][:5]}")
#             return order_book
#         except Exception as e:
#             logger.error(f"[WebSocket] Coinbase order book error ({self.pair}): {e}")
#             logger.debug(traceback.format_exc())
#             return None

        
class CoinbaseFetcher(ExchangeFetcher):
    def __init__(self, pairs: list[str]):
        # We’ll ignore ExchangeFetcher.pair entirely and just use self.pairs.
        super().__init__("Coinbase", "MULTI")
        self.exchange = ccxt.pro.coinbase()
        self.connected = False
        self._reconnect_interval = 5  # seconds
        self.latest_prices: dict[str, float] = {}
        self.pairs = pairs

    async def connect(self):
        """Continuously listen to Coinbase WebSocket and update latest prices."""
        async def listener():
            while True:
                try:
                    # Bulk‐subscribe once
                    tickers = await self.exchange.watch_tickers(self.pairs)
                    # Update our local cache
                    for symbol, ticker in tickers.items():
                        price = ticker["last"]
                        ts_ms = ticker["timestamp"]
                        # logger.debug(f"[Coinbase] Raw ticker info for {symbol}: {ticker}")
                        # self.latest_data[symbol] = (price, ts_ms)
                        # logger.debug(f"[Coinbase] Latest price for {symbol}: {price} at raw : {ts_ms} \n converted:{datetime.fromtimestamp(ts_ms / 1000, timezone.utc)}")
                        self.latest_prices[symbol] = ticker["last"]
                    self.connected = True
                except Exception as e:
                    self.connected = False
                    logger.error(f"[WebSocket] Coinbase error: {e}")
                    await asyncio.sleep(self._reconnect_interval)

        # Fire off the single listener task
        asyncio.create_task(listener())

    async def get_price(self, symbol: str) -> Optional[Tuple[float, datetime]]:
        """Return latest price for a given symbol + timestamp."""
        price = self.latest_prices.get(symbol)
        if price is not None:
            return price, datetime.now(timezone.utc)
        return None, None

