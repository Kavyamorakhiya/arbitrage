#  bot.py

import asyncio
import asyncpg
import aiohttp
import logging

# Env
import os
from dotenv import load_dotenv
load_dotenv("settings.env")

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "ramanujan")
DB_NAME = os.getenv("DB_NAME", "arbitrage")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))

# Exchange Fetchers
# Cex
from exchanges.binance import BinanceFetcher
from exchanges.coinbase import CoinbaseFetcher
from exchanges.kraken import KrakenFetcher
from exchanges.kucoin import KucoinFetcher
from exchanges.gateio import GateIo
from exchanges.bybit import BybitFetcher
# Dex
from exchanges.jupiter import JupiterFetcher
from exchanges.hyperliquid import HyperliquidFetcher

# Core Modules
from core.market_matrix import MarketMatrix, shutdown
from core.arbitrage_runner import run_arbitrage_for_all_pairs

# Database Logger
from db.logger import DatabaseLogger, ensure_database, ensure_tables 

async def setup_database():
        ensure_database(DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)
        pool = await asyncpg.create_pool(user=DB_USER, password=DB_PASSWORD, database=DB_NAME, host=DB_HOST, port=DB_PORT)
        await ensure_tables(pool)
        return pool
# --- Main entry ---
async def main():

    db_pool = await setup_database()
        
    db_logger = DatabaseLogger(db_pool)

    try:
        async with aiohttp.ClientSession() as session:
            matrix = MarketMatrix()
            # Add more pairs as needed
            pairs = ["ETH/USDT"] # Future Update : Add this to config file

            for pair in pairs:
                # Initialize CEX fetchers
                binance = BinanceFetcher(pair)
                await binance.connect()
                # await binance.get_order_book(pair)  # For Future use
                matrix.add_fetcher(pair, binance)

                coinbase = CoinbaseFetcher(pair)
                await coinbase.connect()
                matrix.add_fetcher(pair, coinbase)

                kraken = KrakenFetcher(pair)
                await kraken.connect()
                matrix.add_fetcher(pair, kraken)

                kucoin = KucoinFetcher(pair)
                await kucoin.connect()
                matrix.add_fetcher(pair, kucoin)

                gateio = GateIo(pair)
                await gateio.connect()
                matrix.add_fetcher(pair, gateio)

                # Uncomment if you are not US based.
                # bybit = BybitFetcher(pair) # Note : In US the bybit is not working for n reasons.
                # await bybit.connect()
                # matrix.add_fetcher(pair, bybit)

                # Initialize DEX fetchers
                fetcher = await JupiterFetcher.create(session, pair)
                matrix.add_fetcher(pair, fetcher)

                # Initialize Hyperliquid WebSocket fetcher
                hyperliquid_ws = HyperliquidFetcher(pair)
                await hyperliquid_ws.connect()
                matrix.add_fetcher(pair, hyperliquid_ws)

            await run_arbitrage_for_all_pairs(matrix, db_logger)
    finally:
        await shutdown(matrix)
        await db_logger.close()
        await db_pool.close()
        logging.info("Shutting down all exchanges and WebSockets.")



if __name__ == "__main__":
    asyncio.run(main())
