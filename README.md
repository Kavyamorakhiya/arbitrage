# CEX-DEX Arbitrage Bot (Phase 1)

This bot simulates arbitrage opportunities between centralized exchanges (CEX) and decentralized exchanges (DEX) (e.g., Jupiter Aggregator and Hyperliquid) for crypto trading pairs such as SOL/USDC.

## 🔧 Features

- Real-time price aggregation from multiple CEXs (Binance, Coinbase, Kraken, Kucoin, Bybit) and DEXs (Jupiter, Hyperliquid)
- To add more exchanges, simply implement the class `ExchangeFetcher`.
- To add more trading pairs, modify the `pairs` list in `arbitrage_bot.py`.
- Except Jupiter, all exchanges use WebSocket for live updates.
- Trade simulation with slippage and fee modeling
- Live CLI dashboard with dynamic updates (using rich)
- Persistent PostgreSQL logging of:
  - Exchange prices (with timestamp)
  - Arbitrage opportunities
- Asynchronous architecture with resilient WebSocket streaming and REST fallback

## 📦 Installation

1. Clone the repository:

```bash
cd cex_dex_arbitrage
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Set up the PostgreSQL database:

Create the following schema manually or via migration tools:

```sql
CREATE TABLE arbitrage_opportunities (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ,
  pair TEXT,
  buy_exchange TEXT,
  buy_price NUMERIC,
  sell_exchange TEXT,
  sell_price NUMERIC,
  spread NUMERIC,
  spread_pct NUMERIC,
  net_profit NUMERIC,
  gross_profit NUMERIC
);

CREATE TABLE exchange_prices (
  id SERIAL PRIMARY KEY,
  pair TEXT,
  exchange_name TEXT,
  price NUMERIC,
  timestamp TIMESTAMPTZ,
  arbitrage_id INTEGER REFERENCES arbitrage_opportunities(id)
);
```

## ⚙️ Configuration

1. Configure your PostgreSQL DB credentials inside `main()` in `arbitrage_bot.py`:

```python
db_pool = await asyncpg.create_pool(
    user="postgres",
    password="your_password",
    database="arbitrage",
    host="localhost",
    port=5432
)
```

2. Modify default trading pair, thresholds, and fees in `arbitrage_bot.py`:

```python
SPREAD_THRESHOLD = 0.05       # $0.05 min spread
PERCENT_THRESHOLD = 0.10      # 0.10% min arbitrage %
TRADE_AMOUNT = 10             # USDC amount used for simulations
```

## ▶️ Running the Bot

```bash
python arbitrage_bot.py
```

The CLI will display:
- Latest prices per exchange
- Best buy/sell combinations
- Detected arbitrage spreads (gross/net)
- Simulated profits

## 🧾 Output Example

```
Exchange         Price      Timestamp
Binance          144.32     12:01:05
Coinbase         144.30     12:01:05
Kraken           144.31     12:01:05
Jupiter          144.56     12:01:05
Hyperliquid      144.29     12:01:05

BEST BUY         Hyperliquid @ 144.29
BEST SELL        Jupiter     @ 144.56
SPREAD           0.27 (0.19%)
Potential GP     $1.75
Potential NP     $1.11
```

##  Data Persistence

All arbitrage opportunities and price snapshots are logged to a PostgreSQL database for historical analysis and future dashboards.

##  Limitations

- Simulates trades only (no real execution)
- CEX pairs must match exchange format (e.g., SOL/USDC, not SOL-USDC)
- Some pair not matches the format (e.g., BTC) may not be supported in jup it has to use (WBTC) instead.

##  Roadmap (Future Phases)

-  Trade execution engine (CEX/DEX integration)
-  Strategy customization (latency arbitrage, triangular arb, etc.)