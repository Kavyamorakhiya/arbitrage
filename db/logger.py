from datetime import datetime, date, timezone
from typing import List, Tuple, Dict
import sys
version = sys.version_info
if sys.version_info >= (3, 10):
    PricesType = List[Tuple[str, float, datetime | str]]
else:
    from typing import Union
    PricesType = List[Tuple[str, float, Union[datetime, str]]]
import traceback
import logging
import asyncio
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


# logger = logging.getLogger(__name__)
logger = logging.getLogger("cex_dex_arbitrage.db.logger")

# SQL for creating tables
CREATE_TRADE_LOG = """
CREATE TABLE IF NOT EXISTS trade_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    pair TEXT NOT NULL,
    buy_exchange TEXT NOT NULL,
    buy_price NUMERIC(18,4) NOT NULL,
    sell_exchange TEXT NOT NULL,
    sell_price NUMERIC(18,4) NOT NULL,
    spread NUMERIC(18,4),
    spread_pct NUMERIC(6,4),
    net_profit NUMERIC(18,4),
    gross_profit NUMERIC(18,4),
    event_type TEXT NOT NULL DEFAULT 'ENTRY',
    close_timestamp TIMESTAMPTZ,
    exit_buy_price NUMERIC(18,4),
    exit_sell_price NUMERIC(18,4),
    duration_seconds INTEGER,
    decision_reason TEXT,
    metadata JSONB
);
"""

CREATE_ARBITRAGE_OPPORTUNITIES = """
CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    pair TEXT NOT NULL,
    buy_exchange TEXT NOT NULL,
    buy_price NUMERIC(18,4) NOT NULL,
    sell_exchange TEXT NOT NULL,
    sell_price NUMERIC(18,4) NOT NULL,
    spread NUMERIC(18,4),
    spread_pct NUMERIC(6,4)
);
"""

CREATE_EXCHANGE_PRICES = """
CREATE TABLE IF NOT EXISTS exchange_prices (
    id SERIAL PRIMARY KEY,
    pair TEXT NOT NULL,
    exchange_name TEXT NOT NULL,
    price NUMERIC(18,4) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    arbitrage_id INTEGER REFERENCES arbitrage_opportunities(id) ON DELETE SET NULL
);
"""

def ensure_database(dbname, user, password, host, port):
    conn = psycopg2.connect(dbname='postgres', user=user, password=password, host=host, port=port)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(f"CREATE DATABASE {dbname}")
        print(f"Database '{dbname}' created.")
    cur.close()
    conn.close()

async def ensure_tables(pool):
    async with pool.acquire() as conn:
        await conn.execute(CREATE_ARBITRAGE_OPPORTUNITIES)
        await conn.execute(CREATE_EXCHANGE_PRICES)
        await conn.execute(CREATE_TRADE_LOG)

class DatabaseLogger:
    def __init__(self, db_pool, flush_interval: float = 10):
        self.db_pool = db_pool
        self.flush_interval = flush_interval
        self.arb_buffer = []    # List[Dict], where each dict has keys: timestamp, pair, buy_…, prices=list[(name,price,raw_ts)]
        self.price_buffer = []  # List[Tuple[pair, exchange_name, price, raw_ts, arbitrage_id]]
        self.trade_buffer = []
        self.lock = asyncio.Lock()
        self._flush_task = asyncio.create_task(self._flush_loop())
    
    async def log_opportunity(
        self,
        pair: str,
        buy_exchange: str,
        buy_price: float,
        sell_exchange: str,
        sell_price: float,
        spread: float,
        spread_pct: float,
        prices: PricesType
    ):
        """
        `prices` is a list of (exchange_name, price, ts), where ts might be a datetime or a "HH:MM:SS" string.
        We convert each `ts` to a datetime here, then store a list of (name, price, raw_ts).
        """
        if not prices:
            logger.warning(f"No prices provided for {pair} arbitrage opportunity.")
            return

        # Convert each ts → raw_ts as a datetime.datetime in UTC
        converted_prices: List[Tuple[str, float, datetime]] = []
        for name, price, ts in prices:
            if isinstance(ts, str):
                # parse "HH:MM:SS" as today’s date in UTC
                t = datetime.strptime(ts, "%H:%M:%S").time()
                raw_ts = datetime.combine(date.today(), t, tzinfo=timezone.utc)
            else:
                # assume ts is already a datetime
                raw_ts = ts
            converted_prices.append((name, price, raw_ts))

        async with self.lock:
            self.arb_buffer.append({
                # The timestamp of *when* we detected this opportunity
                "timestamp": datetime.now(tz=timezone.utc),
                "pair": pair,
                "buy_exchange": buy_exchange,
                "buy_price": buy_price,
                "sell_exchange": sell_exchange,
                "sell_price": sell_price,
                "spread": spread,
                "spread_pct": spread_pct,
                # A list of (exchange_name, price, raw_ts) for logger into exchange_prices
                "prices": converted_prices
            })

    async def log_prices(
        self,
        pair: str,
        prices: PricesType
    ):
        """
        For simple price logger (no arbitrage), same idea: convert ts → datetime if needed.
        """
        async with self.lock:
            for name, price, ts in prices:
                if isinstance(ts, str):
                    t = datetime.strptime(ts, "%H:%M:%S").time()
                    raw_ts = datetime.combine(date.today(), t, tzinfo=timezone.utc)
                else:
                    raw_ts = ts
                # Append a tuple matching the INSERT: (pair, exchange_name, price, timestamp, arbitrage_id=None)
                self.price_buffer.append((pair, name, price, raw_ts, None))
    
    async def log_trade(
        self,
        timestamp: datetime,
        pair: str,
        buy_exchange: str,
        buy_price: float,
        sell_exchange: str,
        sell_price: float,
        spread: float,
        spread_pct: float,
        net_profit: float,
        gross_profit: float,
        event_type: str = 'ENTRY',
        close_timestamp: datetime = None,
        exit_buy_price: float = None,
        exit_sell_price: float = None,
        duration_seconds: int = None,
        decision_reason: str = None,
        metadata: Dict = None
    ):
        async with self.lock:
            self.trade_buffer.append((
                timestamp, pair, buy_exchange, buy_price,
                sell_exchange, sell_price, spread, spread_pct,
                net_profit, gross_profit, event_type,
                close_timestamp, exit_buy_price, exit_sell_price,
                duration_seconds, decision_reason, metadata
            ))


    async def _flush_loop(self):
        while True:
            await asyncio.sleep(self.flush_interval)
            if len(self.arb_buffer) + len(self.price_buffer) > 500:
                logger.debug("Large buffer detected, flushing early.")
            await self.flush()

    async def flush(self):
        async with self.lock:
            # Nothing to write?
            if not self.arb_buffer and not self.price_buffer:
                return

            try:
                async with self.db_pool.acquire() as conn:
                    async with conn.transaction():
                        # 1) Insert every arbitrage opportunity and collect its new arb_id
                        for arb in self.arb_buffer:
                            arb_id = await conn.fetchval(
                                """
                                INSERT INTO arbitrage_opportunities (
                                    timestamp, pair, buy_exchange, buy_price,
                                    sell_exchange, sell_price, spread, spread_pct
                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                                RETURNING id
                                """,
                                arb["timestamp"],
                                arb["pair"],
                                arb["buy_exchange"],
                                arb["buy_price"],
                                arb["sell_exchange"],
                                arb["sell_price"],
                                arb["spread"],
                                arb["spread_pct"]
                            )


                            # 2) For each (exchange_name, price, raw_ts) in this arbitrage,
                            #    buffer rows into price_buffer with this arb_id
                            for name, price, raw_ts in arb["prices"]:
                                self.price_buffer.append(
                                    (arb["pair"], name, price, raw_ts, arb_id)
                                )
                        # Uncomment this if you want to insert prices immediately
                        # 3) Now insert *all* buffered prices (including those just added above)
                        # count the rows length of exchange_prices. If table exchange_prices has more than 500 rows then skip
                        row_count = await conn.execute(
                            """
                            SELECT COUNT(*) FROM exchange_prices
                        """)
                        if row_count > 500:
                            pass
                        else:
                            await conn.executemany(
                                """
                              INSERT INTO exchange_prices
                                (pair, exchange_name, price, timestamp, arbitrage_id)
                              VALUES ($1, $2, $3, $4, $5)
                            """,
                            self.price_buffer
                        )
                        # 4) Insert all buffered trades
                        if self.trade_buffer:
                            await conn.executemany(
                                """
                                INSERT INTO trade_log (
                                    timestamp, pair, buy_exchange, buy_price,
                                    sell_exchange, sell_price, spread, spread_pct,
                                    net_profit, gross_profit, event_type,
                                    close_timestamp, exit_buy_price, exit_sell_price,
                                    duration_seconds, decision_reason, metadata
                                ) VALUES (
                                    $1, $2, $3, $4,
                                    $5, $6, $7, $8,
                                    $9, $10, $11,
                                    $12, $13, $14,
                                    $15, $16, $17
                                )
                                """,
                                self.trade_buffer
                            )
            except Exception as e:
                logger.error(f"Error flushing data to database: {e}")
                logger.debug(traceback.format_exc())

            finally:
                # Whether success or failure, clear both buffers
                self.arb_buffer.clear()
                self.price_buffer.clear()
                self.trade_buffer.clear()

    async def close(self):
        # Flush any remaining data, then cancel the background task
        await self.flush()
        self._flush_task.cancel()
        try:
            await self._flush_task
        except asyncio.CancelledError:
            pass
