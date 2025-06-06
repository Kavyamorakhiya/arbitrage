# # python -m tests.test_arbitrage_logic
# import asyncio
# import os
# import sys
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# from trades.binance import BinanceTrader

# async def spot_trading_example():
#     """Example of spot trading"""
#     print("=== SPOT TRADING EXAMPLE ===")
    
#     # Initialize spot trader
#     spot_trader = BinanceTrader("BTC/USDT", market_type="spot")
    
#     try:
#         # Connect to exchange
#         await spot_trader.connect()
        
#         # Get current price
#         price = await spot_trader.get_current_price()
#         print(f"Current BTC/USDT price: ${price}")
        
#         # Get balance
#         usdt_balance = await spot_trader.get_balance("USDT")
#         btc_balance = await spot_trader.get_balance("BTC")
#         print(f"USDT Balance: {usdt_balance}")
#         print(f"BTC Balance: {btc_balance}")
        
#         # Place limit buy order
#         buy_order = await spot_trader.buy(amount=0.001, price=price * 0.99)
#         print(f"Buy order: {buy_order}")
        
#         # Wait a bit then cancel order
#         await asyncio.sleep(5)
#         if 'id' in buy_order:
#             cancel_result = await spot_trader.cancel_order(buy_order['id'])
#             print(f"Cancel result: {cancel_result}")
        
#         # Place market sell order (if you have BTC)
#         if btc_balance and btc_balance > 0.001:
#             sell_order = await spot_trader.sell(amount=0.001)
#             print(f"Sell order: {sell_order}")
        
#     finally:
#         await spot_trader.close()

# async def futures_trading_example():
#     """Example of futures trading"""
#     print("\n=== FUTURES TRADING EXAMPLE ===")
    
#     # Initialize futures trader
#     futures_trader = BinanceTrader("BTC/USDT", market_type="future")
    
#     try:
#         # Connect to exchange
#         await futures_trader.connect()
        
#         # Set leverage
#         await futures_trader.set_leverage(10)
        
#         # Set margin mode to isolated
#         await futures_trader.set_margin_mode("isolated")
        
#         # Get current price
#         price = await futures_trader.get_current_price()
#         print(f"Current BTC/USDT futures price: ${price}")
        
#         # Get funding rate
#         funding_rate = await futures_trader.get_funding_rate()
#         print(f"Funding rate: {funding_rate}")
        
#         # Get balance
#         usdt_balance = await futures_trader.get_balance("USDT")
#         print(f"USDT Balance: {usdt_balance}")
        
#         # Place long position (buy)
#         long_order = await futures_trader.buy(amount=0.01, leverage=10)
#         print(f"Long order: {long_order}")
        
#         # Check position
#         await asyncio.sleep(2)
#         position = await futures_trader.get_position()
#         print(f"Current position: {position}")
        
#         # Close position
#         if position and position['size'] > 0:
#             close_result = await futures_trader.close_position("long")
#             print(f"Position closed: {close_result}")
        
#     finally:
#         await futures_trader.close()

# async def arbitrage_example():
#     """Example of simple arbitrage monitoring"""
#     print("\n=== ARBITRAGE MONITORING EXAMPLE ===")
    
#     spot_trader = BinanceTrader("BTC/USDT", market_type="spot")
#     futures_trader = BinanceTrader("BTC/USDT", market_type="future")
    
#     try:
#         # Connect both traders
#         await spot_trader.connect()
#         await futures_trader.connect()
        
#         # Monitor price difference for 30 seconds
#         start_time = asyncio.get_event_loop().time()
#         while asyncio.get_event_loop().time() - start_time < 30:
#             spot_price = await spot_trader.get_current_price()
#             futures_price = await futures_trader.get_current_price()
            
#             if spot_price and futures_price:
#                 price_diff = futures_price - spot_price
#                 price_diff_pct = (price_diff / spot_price) * 100
                
#                 print(f"Spot: ${spot_price:.2f} | Futures: ${futures_price:.2f} | "
#                       f"Diff: ${price_diff:.2f} ({price_diff_pct:.3f}%)")
                
#                 # Simple arbitrage opportunity detection
#                 if abs(price_diff_pct) > 0.1:  # 0.1% threshold
#                     print(f"🚨 ARBITRAGE OPPORTUNITY: {price_diff_pct:.3f}%")
            
#             await asyncio.sleep(1)
    
#     finally:
#         await spot_trader.close()
#         await futures_trader.close()

# async def main():
#     """Run all examples"""
#     await spot_trading_example()
#     await futures_trading_example()
#     await arbitrage_example()

# if __name__ == "__main__":
#     asyncio.run(main())
import random
import pandas as pd
import matplotlib.pyplot as plt

def is_trade_profitable(entry_buy, entry_sell, exit_buy, exit_sell, fee_percent, slippage_percent, trade_amount_usdc=10000):
    fee = fee_percent / 100
    slip = slippage_percent / 100
    total_cost = fee + slip

    entry_eff_buy = entry_buy * (1 + total_cost)
    entry_eff_sell = entry_sell * (1 - total_cost)
    exit_eff_buy = exit_buy * (1 + total_cost)
    exit_eff_sell = exit_sell * (1 - total_cost)

    units = trade_amount_usdc / entry_eff_buy
    forward_profit = units * (exit_eff_sell - entry_eff_buy)
    reverse_loss = units * (exit_eff_buy - entry_eff_sell)
    net_profit = forward_profit - reverse_loss

    return {
        "entry_spread_pct": ((entry_sell / entry_buy) - 1) * 100,
        "exit_spread_pct": ((exit_sell / exit_buy) - 1) * 100,
        "net_profit": net_profit,
        "net_profit_pct": (net_profit / trade_amount_usdc) * 100,
        "is_profitable": net_profit > 0
    }

def run_realistic_trade_simulation(
    n=10000,
    min_entry_spread=0.35,
    min_exit_spread=0.10,
    trade_amount_usdc=1000,
    max_exit_attempts=5
):
    total_trades = 0
    profitable_trades = 0
    net_profit_total = 0
    results = []

    for _ in range(n):
        base_price = random.uniform(100, 200)
        entry_vol = random.uniform(-0.0025, 0.0025)
        adjusted_entry_price = base_price * (1 + entry_vol)
        entry_spread = random.uniform(min_entry_spread, min_entry_spread + 0.4) / 100
        entry_buy = adjusted_entry_price
        entry_sell = adjusted_entry_price * (1 + entry_spread)

        # Ensure entry meets min spread
        if ((entry_sell / entry_buy) - 1) * 100 < min_entry_spread:
            continue

        # Randomized fee/slippage per trade
        fee = random.uniform(0.09, 0.11)
        slip = random.uniform(0.04, 0.06)

        # Multi-exit attempts - track best possible outcome
        best_trade = None
        best_profit = float('-inf')
        exit_spread_list = []

        for _ in range(max_exit_attempts):
            exit_base = base_price + random.uniform(-2, 2)
            market_vol = random.uniform(0.7, 1.3)
            exit_spread = (random.uniform(min_exit_spread, min_exit_spread + 0.3) * market_vol) / 100
            exit_buy = exit_base
            exit_sell = exit_base * (1 + exit_spread)

            exit_spread_list.append((exit_sell / exit_buy - 1) * 100)

            if ((exit_sell / exit_buy) - 1) * 100 >= min_exit_spread:
                trade = is_trade_profitable(entry_buy, entry_sell, exit_buy, exit_sell, fee, slip, trade_amount_usdc)
                trade.update({
                    "entry_buy": entry_buy,
                    "entry_sell": entry_sell,
                    "exit_buy": exit_buy,
                    "exit_sell": exit_sell,
                    "fee": fee,
                    "slippage": slip,
                    "exit_spread_real": (exit_sell / exit_buy - 1) * 100,
                    "exit_spread_attempts": exit_spread_list.copy()
                })
                if trade["net_profit"] > best_profit:
                    best_trade = trade
                    best_profit = trade["net_profit"]

        if best_trade:
            results.append(best_trade)
            total_trades += 1
            if best_trade["is_profitable"]:
                profitable_trades += 1
                net_profit_total += best_trade["net_profit"]

    avg_net_profit = net_profit_total / total_trades if total_trades > 0 else 0
    success_rate = profitable_trades / total_trades * 100 if total_trades > 0 else 0

    return {
        "total_valid_trades": total_trades,
        "profitable_trades": profitable_trades,
        "success_rate_pct": round(success_rate, 2),
        "avg_net_profit": round(avg_net_profit, 4),
        "avg_net_profit_pct": round((avg_net_profit / trade_amount_usdc) * 100, 4),
        "sample_results": results
    }

# ---- RUN SIMULATION ----
summary = run_realistic_trade_simulation(n=10000, min_entry_spread=0.35, min_exit_spread=0.10)

# ---- DATAFRAME FOR ANALYSIS ----
df = pd.DataFrame(summary['sample_results'])

print("="*60)
print("  TRADE SIMULATION SUMMARY")
print("="*60)
print(f"Total Valid Trades     : {summary['total_valid_trades']}")
print(f"Profitable Trades      : {summary['profitable_trades']}")
print(f"Success Rate (%)       : {summary['success_rate_pct']}")
print(f"Avg Net Profit         : {summary['avg_net_profit']:.4f} USDC")
print(f"Avg Net Profit (%)     : {summary['avg_net_profit_pct']:.4f} %")
print("="*60)
print("Descriptive statistics of main columns:")
print(df[['net_profit', 'entry_spread_pct', 'exit_spread_pct', 'fee', 'slippage']].describe())
print("="*60)

# ---- HISTOGRAM: Net Profit ----
plt.figure()
df['net_profit'].hist(bins=50)
plt.title('Distribution of Net Profit per Trade')
plt.xlabel('Net Profit (USDC)')
plt.ylabel('Frequency')
plt.show()

# ---- NET PROFIT vs ENTRY SPREAD ----
plt.figure()
plt.scatter(df['entry_spread_pct'], df['net_profit'], alpha=0.3)
plt.title('Net Profit vs. Entry Spread (%)')
plt.xlabel('Entry Spread (%)')
plt.ylabel('Net Profit (USDC)')
plt.show()

# ---- NET PROFIT vs EXIT SPREAD ----
plt.figure()
plt.scatter(df['exit_spread_pct'], df['net_profit'], alpha=0.3)
plt.title('Net Profit vs. Exit Spread (%)')
plt.xlabel('Exit Spread (%)')
plt.ylabel('Net Profit (USDC)')
plt.show()

# ---- Success Rate by Entry Spread Bin ----
df['entry_spread_bin'] = pd.cut(df['entry_spread_pct'], bins=[0.35, 0.5, 0.6, 0.7, 0.8, 1.0, 2.0])
success_by_bin = df.groupby('entry_spread_bin')['is_profitable'].mean()
print("Success rate by entry spread bin:")
print(success_by_bin)

plt.figure()
success_by_bin.plot(kind='bar')
plt.title('Success Rate by Entry Spread Bin')
plt.ylabel('Success Rate')
plt.xlabel('Entry Spread (%)')
plt.show()

# ---- CORRELATION TABLE ----
print("="*60)
print("Correlation matrix for main variables:")
print(df[['net_profit', 'entry_spread_pct', 'exit_spread_pct', 'fee', 'slippage']].corr())
print("="*60)

# ---- EXPORT TO CSV (OPTIONAL) ----
df.to_csv('trade_sim_results.csv', index=False)
print("Results exported to 'trade_sim_results.csv'.")


