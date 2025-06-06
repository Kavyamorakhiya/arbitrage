# exchanges/hyperliquid.py
from exchanges.base import ExchangeFetcher
from datetime import datetime, timezone
from typing import Optional, Tuple
import traceback
import aiohttp
import logging
import json
import time
import os

# logger = logging.getLogger(__name__)
logger = logging.getLogger("cex_dex_arbitrage.exchanges.jupiter")

TOKEN_CACHE_FILE = r"token_info_cache.json"
# Need to understand this better.
TRADE_AMOUNT = 10.0  # Default trade amount in USDC



async def get_jupiter_pair_info(session: aiohttp.ClientSession, pair: str, trade_amount: float = 10.0):
    input_symbol, output_symbol = pair.upper().split('/')
    # logger.debug(f"Fetching Jupiter pair info for {pair}...")
    logger.debug(f"[Jupiter] Input symbol: {input_symbol}, Output symbol: {output_symbol}")
    # Load cache
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, 'r') as f:
            token_cache = json.load(f)
    else:
        token_cache = {}

    if input_symbol in token_cache and output_symbol in token_cache:
        input_token = token_cache[input_symbol]
        output_token = token_cache[output_symbol]
    else:
        try:
            async with session.get("https://lite-api.jup.ag/tokens/v1/tagged/verified") as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Non-200 response: {resp.status}, body: {text[:200]}")

                token_data = await resp.json()
                print(token_data)
                if not isinstance(token_data, list):
                    raise TypeError(f"Unexpected response format (not a list): {token_data}")

                for token in token_data:
                    symbol = token.get('symbol', '').upper()
                    mint = token.get('address') or token.get('mint')
                    decimals = token.get('decimals')
                    if symbol and mint and decimals is not None:
                        token_cache[symbol] = {
                            'mint': mint,
                            'decimals': decimals
                        }

                with open(TOKEN_CACHE_FILE, 'w') as f:
                    json.dump(token_cache, f, indent=2)

                input_token = token_cache.get(input_symbol)
                output_token = token_cache.get(output_symbol)

                if not input_token or not output_token:
                    raise ValueError(f"Invalid token symbol(s): {input_symbol} or {output_symbol}")

        except Exception as e:
            logging.error(f"Error fetching token list: {e}")
            return None

    input_mint = input_token['mint']
    output_mint = output_token['mint']
    input_decimals = input_token['decimals']
    amount = str(int(trade_amount * 10**input_decimals))

    return {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": amount,
        "inputDecimals": input_decimals,
        "outputDecimals": output_token['decimals']
    }



class JupiterFetcher(ExchangeFetcher):
    def __init__(self, session: aiohttp.ClientSession, pair: str, inputMint: str, outputMint: str, amount: str):
        super().__init__("Jupiter", pair)
        self.session = session
        self.inputMint = inputMint
        self.outputMint = outputMint
        self.amount = amount
        self.slippageBps = 50  # 0.5% slippage
        self._cooldown = 0.2
        self._last_call = 0

    @classmethod
    async def create(cls, session: aiohttp.ClientSession, pair: str):
        # Replace BTC with WBTC before token lookup
        normalized_pair = pair.upper().replace("BTC", "WBTC")

        info = await get_jupiter_pair_info(session, normalized_pair)
        if info is None:
            raise RuntimeError(f"Failed to initialize JupiterFetcher for pair: {pair}")
        return cls(session, normalized_pair, info['inputMint'], info['outputMint'], info['amount'])

    async def get_price(self) -> Optional[Tuple[float, datetime]]:
        now = time.time()
        if now - self._last_call < self._cooldown:
            # logging.debug(f"[Jupiter] Cooldown active, skipping price fetch for {self.pair}")
            return None, None
        try:
            async with self.session.get("https://quote-api.jup.ag/v6/quote", params={
                "inputMint": self.inputMint,
                "outputMint": self.outputMint,
                "amount": self.amount,
                "slippageBps": self.slippageBps
            }) as response:
                data = await response.json()
                out_amount = float(data['outAmount'])
                price = out_amount / (10 ** 6) / TRADE_AMOUNT
                self.latest_price = price
                self._last_call = now
                # logging.info(f"Jupiter price for {self.pair}: {price:.4f} USDC")
                return price, datetime.now(timezone.utc)
        except Exception:
            # logging.error(f"Error fetching price from Jupiter for {self.pair}: {traceback.format_exc()}")
            return None, None
