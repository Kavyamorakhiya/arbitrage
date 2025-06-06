#  core/arbitrage_runner.py

from core.trade_simulator import simulate_entry_trade, simulate_exit_trade
from datetime import datetime, timezone
from typing import Dict, List
import asyncio
from rich.console import Console
from rich.table import Table
from rich.live import Live

async def run_arbitrage_for_all_pairs(matrix, db_logger):
    console = Console()
    SPREAD_THRESHOLD = 0.05
    PERCENT_THRESHOLD = 0.40
    CONVERGENCE_THRESHOLD = 0.10

    open_positions: Dict[str, dict] = {}
    paper_trades: List[dict] = []

    async def build_table():
        table = Table(title="📈 Live Price Monitor")
        table.add_column("Exchange", justify="left", style="cyan", no_wrap=True)
        table.add_column("Price", justify="right", style="green")
        table.add_column("Timestamp", justify="right", style="white")

        best_buy = None
        best_sell = None
        best_spread = 0

        for pair, fetchers in matrix.fetchers.items():
            prices = []
            for fetcher in fetchers:
                try:
                    result = await fetcher.get_price()
                    if result:
                        price, ts = result
                        if price is not None:
                            prices.append((fetcher.name, price, ts.strftime("%H:%M:%S")))
                except:
                    continue

            if len(prices) < 2:
                continue

            prices.sort(key=lambda x: x[1])
            await db_logger.log_prices(pair, prices)
            low_name, low_price, _ = prices[0]
            high_name, high_price, _ = prices[-1]
            spread = high_price - low_price
            spread_pct = (spread / low_price) * 100

            table.add_section()
            table.add_row(f"[bold white]{pair} Prices[/bold white]", "", "")
            for name, price, ts_str in prices:
                table.add_row(name, f"{price:.4f}", ts_str)
            table.add_section()
            table.add_row(
                f"[bold white]{pair} Min/Max[/bold white]",
                f"{low_name} @ {low_price:.2f}, {high_name} @ {high_price:.2f}",
                "",
            )
            table.add_row(
                f"[bold white]{pair} Spread[/bold white]",
                f"{spread:.4f} ({spread_pct:.2f}%)",
                ""
            )

            # ENTRY
            if spread >= SPREAD_THRESHOLD and spread_pct >= PERCENT_THRESHOLD and pair not in open_positions:
                position = simulate_entry_trade(
                    buy_price=low_price,
                    sell_price=high_price,
                    trade_amount_usdc=1000.0,
                    fee_percent=0.1,
                    slippage_percent=0.05
                )
                position.update({
                    "entry_time": datetime.now(timezone.utc),
                    "pair": pair,
                    "buy_exchange": low_name,
                    "sell_exchange": high_name,
                    "entry_spread": spread_pct,
                    "buy_price": low_price,
                    "sell_price": high_price
                })
                open_positions[pair] = position

                console.log(f"[bold green]ENTRY:[/bold green] {pair} | BUY on {low_name} @ {low_price:.2f}, SHORT on {high_name} @ {high_price:.2f} | Spread: {spread_pct:.2f}%")

                # net_profit, gross_profit = simulate_exit_trade(position, low_price, high_price)
                await db_logger.log_opportunity(
                    pair, low_name, low_price, high_name, high_price,
                    spread, spread_pct, prices
                )

            # EXIT
            elif pair in open_positions and spread_pct <= CONVERGENCE_THRESHOLD:
                position = open_positions[pair]

                def get_price(name):
                    for ex, pr, _ in prices:
                        if ex == name:
                            return pr
                    return None

                exit_buy = get_price(position["buy_exchange"])
                exit_sell = get_price(position["sell_exchange"])

                if exit_buy and exit_sell:
                    net_profit, gross_profit = simulate_exit_trade(position, exit_buy, exit_sell)
                    duration = (datetime.now(timezone.utc) - position["entry_time"]).total_seconds()
                    paper_trades.append({
                        "pair": pair,
                        "entry_spread": position["entry_spread"],
                        "net_profit": net_profit,
                        "duration_sec": duration,
                        "buy_exchange": position["buy_exchange"],
                        "sell_exchange": position["sell_exchange"]
                    })
                    console.log(f"[bold red]EXIT:[/bold red] {pair} | NP: ${net_profit:.2f} | Duration: {duration:.1f}s | Converged.")

                    await db_logger.log_trade(
                        timestamp=position["entry_time"],
                        pair=pair,
                        buy_exchange=position["buy_exchange"],
                        buy_price=position["buy_price"],
                        sell_exchange=position["sell_exchange"],
                        sell_price=position["sell_price"],
                        spread=position["sell_price"] - position["buy_price"],
                        spread_pct=position["entry_spread"],
                        net_profit=net_profit,
                        gross_profit=gross_profit,
                        event_type="EXIT",
                        close_timestamp=datetime.now(timezone.utc),
                        exit_buy_price=exit_buy,
                        exit_sell_price=exit_sell,
                        duration_seconds=int(duration),
                        decision_reason="spread_converged",
                        metadata=None
                    )

                    del open_positions[pair]

        # Display open positions
        if open_positions:
            table.add_section()
            table.add_row("[bold magenta]Open Positions[/bold magenta]", "", "")
            for pair, pos in open_positions.items():
                duration = (datetime.now(timezone.utc) - pos["entry_time"]).total_seconds()
                table.add_row(
                    f"{pair} (open)",
                    f"{pos['entry_spread']:.2f}%",
                    f"{duration:.1f}s"
                )
                table.add_row(
                    f"↳ Buy on {pos['buy_exchange']}",
                    f"{pos['buy_price']:.2f}",
                    ""
                )
                table.add_row(
                    f"↳ Short on {pos['sell_exchange']}",
                    f"{pos['sell_price']:.2f}",
                    ""
                )

        # Print summary every N trades
        if len(paper_trades) > 0 and len(paper_trades) % 5 == 0:
            total_np = sum(t["net_profit"] for t in paper_trades)
            console.log(f"[bold blue]PAPER TRADE SUMMARY:[/bold blue] {len(paper_trades)} trades | Total Net Profit: ${total_np:.2f}")

        return table


    with Live(await build_table(), refresh_per_second=4, console=console) as live:
        while True:
            table = await build_table()
            live.update(table)
            await asyncio.sleep(0.2)

