# exchanges/hyperliquid.py
from exchanges.base import ExchangeFetcher
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict
import websockets
import traceback
import ccxt.pro
import logging
import asyncio
import json

# logger = logging.getLogger(__name__)
logger = logging.getLogger("cex_dex_arbitrage.exchanges.hyperliquid")

# class HyperliquidFetcher(ExchangeFetcher):
#     def __init__(self, pair: str):
#         super().__init__("Hyperliquid", pair)
#         self.exchange = ccxt.pro.hyperliquid({'enableRateLimit': True})
#         self.market_id = None

#     async def initialize(self):
#         await self.exchange.load_markets()
#         available_markets = list(self.exchange.markets.keys())

#         base, quote = self.pair.split('/')
#         if quote != 'USDC':
#             raise ValueError(f"[Hyperliquid] Unsupported quote currency: {quote}. Only USDC is supported.")

#         # Direct match
#         if self.pair in available_markets:
#             market = self.exchange.market(self.pair)
        
#         # Try matching on base/quote pattern
#         else:
#             # Look for markets that start with the base token and end in 'USDC'
#             possible_matches = [m for m in available_markets if m.startswith(f"{base}/USDC")]

#             if not possible_matches:
#                 raise ValueError(f"[Hyperliquid] Market not found for pair: {self.pair}")
            
#             # If there's a clear match, take it
#             best_match = possible_matches[0]  # Pick the first match or apply a better heuristic
#             logger.warning(f"[Hyperliquid] Pair '{self.pair}' not found. Using closest match: '{best_match}'")

#             self.pair = best_match
#             market = self.exchange.market(self.pair)

#         self.market_id = market['symbol']
#         logger.info(f"[Hyperliquid] Initialized market_id: {self.market_id}")


#     async def connect(self):
#         async def listener():
#             while True:
#                 try:
#                     if not self.market_id:
#                         await self.initialize()

#                     ticker = await self.exchange.watch_ticker(self.market_id)
#                     self.latest_price = ticker["last"]
#                     self.connected = True
#                     # logger.debug(f"[Hyperliquid] Latest price for {self.market_id}: {self.latest_price}")
#                 except Exception as e:
#                     self.connected = False
#                     logger.error(f"[WebSocket] Hyperliquid error ({self.market_id}): {e}")
#                     logger.debug(traceback.format_exc())
#                     await asyncio.sleep(self._reconnect_interval)

#         asyncio.create_task(listener())

#     async def get_order_book(self, limit: int = 100) -> Optional[Tuple[dict, datetime]]:
#         """
#         Fetches the order book for the given pair.
#         Returns top bids and asks with a timestamp.
#         """
#         try:
#             if not self.market_id:
#                 await self.initialize()

#             order_book = await self.exchange.watch_order_book(self.market_id, limit=limit)
#             logger.debug(f"[Hyperliquid] Order book for {self.market_id}:")
#             logger.debug(f"\tAsks: {order_book['asks'][:5]}")
#             logger.debug(f"\tBids: {order_book['bids'][:5]}")
#             return order_book, datetime.now(timezone.utc)
#         except Exception as e:
#             logger.error(f"[WebSocket] Hyperliquid order book error ({self.market_id}): {e}")
#             logger.debug(traceback.format_exc())
#             return None


class HyperliquidFetcher(ExchangeFetcher):
    def __init__(self, pairs: List[str]):
        # super should now take name + list of pairs
        super().__init__("Hyperliquid", "MULTI")
        self.pairs = pairs
        # ccxt.pro client for Hyperliquid
        self.exchange = ccxt.pro.hyperliquid({'enableRateLimit': True})
        # map from your “BASE/USDC” → actual exchange.market symbol
        self.pair_to_market: Dict[str, str] = {}
        self._initialized = False
        self.latest_prices: dict[str, float] = {}

    async def initialize(self):
        """Load markets once and build pair→market_id mapping."""
        await self.exchange.load_markets()
        logger.debug(f"[Hyperliquid] Loaded markets: {self.exchange.markets.keys()}")
        available = self.exchange.markets.keys()

        for pair in self.pairs:
            base, quote = pair.split('/')
            if quote != 'USDC':
                raise ValueError(f"[Hyperliquid] Unsupported quote: {quote}")

            if pair in available:
                market_id = self.exchange.market(pair)['symbol']
            else:
                # fallback: any market that starts with “BASE/USDC”
                candidates = [m for m in available if m.startswith(f"{base}/USDC")]
                if not candidates:
                    raise ValueError(f"[Hyperliquid] No market found for {pair}")
                market_id = self.exchange.market(candidates[0])['symbol']
                logger.warning(f"[Hyperliquid] Using '{candidates[0]}' for requested {pair}")

            self.pair_to_market[pair] = market_id

        self._initialized = True
        logger.info(f"[Hyperliquid] Initialized markets: {self.pair_to_market}")

    async def connect(self):
        """Single background task to keep self.latest_prices updated."""
        async def _listener():
            while True:
                try:
                    if not self._initialized:
                        await self.initialize()

                    # Try bulk‐subscribe if supported
                    try:
                        tickers = await self.exchange.watch_tickers(list(self.pair_to_market.values()))
                        for pair, mkt in self.pair_to_market.items():
                            info = tickers.get(mkt)
                            if info:
                                # logger.debug(f"[Hyperliquid] Raw ticker info for {pair}: {info}")
                                price = info["last"]
                                ts_ms = info["timestamp"]
                                # self.latest_data[symbol] = (price, ts_ms)
                                # logger.debug(f"[Hyperliquid] Latest price for {pair}: {price} at raw : {ts_ms} \n converted:{datetime.fromtimestamp(ts_ms / 1000, timezone.utc)}")
                                self.latest_prices[pair] = info['last']

                    # Fallback to individual watch_ticker calls
                    except AttributeError:
                        tasks = [self.exchange.watch_ticker(mkt) for mkt in self.pair_to_market.values()]
                        results = await asyncio.gather(*tasks)
                        for ticker in results:
                            mkt = ticker['symbol']
                            # reverse‐lookup your original pair
                            pair = next(p for p, mid in self.pair_to_market.items() if mid == mkt)
                            self.latest_prices[pair] = ticker['last']

                    self.connected = True

                except Exception as e:
                    self.connected = False
                    logger.error(f"[Hyperliquid] WebSocket error: {e}")
                    logger.debug(traceback.format_exc())
                    await asyncio.sleep(self._reconnect_interval)

        asyncio.create_task(_listener())

    async def get_price(self, symbol: str) -> Optional[Tuple[float, datetime]]:
        """
        Just like BinanceFetcher: return (price, timestamp) for a given pair.
        """
        price = self.latest_prices.get(symbol)
        if price is not None:
            return price, datetime.now(timezone.utc)
        return None, None

