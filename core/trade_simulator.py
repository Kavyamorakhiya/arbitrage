#  core/trade_simulator.py
# core/trade_simulator.py

from typing import Dict, Tuple


def simulate_entry_trade(
    buy_price: float,
    sell_price: float,
    trade_amount_usdc: float,
    fee_percent: float,
    slippage_percent: float
) -> Dict:
    """
    Simulates entering a position with a buy and sell on different exchanges.

    Returns a dictionary containing:
        - entry_units
        - effective buy/sell prices
        - original prices
        - fee and slippage factors
    """
    fee = fee_percent / 100
    slip = slippage_percent / 100

    eff_buy = buy_price * (1 + fee + slip)
    eff_sell = sell_price * (1 - fee - slip)

    units = trade_amount_usdc / eff_buy

    return {
        "entry_units": units,
        "entry_eff_buy": eff_buy,
        "entry_eff_sell": eff_sell,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "fee": fee,
        "slippage": slip
    }


def simulate_exit_trade(
    position: Dict,
    close_buy_price: float,
    close_sell_price: float
) -> Tuple[float, float]:
    """
    Simulates exiting a position and calculates:
        - Net profit (after fees/slippage)
        - Gross profit (before fees/slippage)

    Parameters:
        position: dict from simulate_entry_trade() + trade metadata
        close_buy_price: market price at exit on buy side
        close_sell_price: market price at exit on sell side

    Returns:
        net_profit: float
        gross_profit: float
    """
    units = position["entry_units"]
    fee = position["fee"]
    slip = position["slippage"]

    close_eff_sell = close_sell_price * (1 - fee - slip)
    close_eff_buy = close_buy_price * (1 + fee + slip)

    forward_profit = units * (close_eff_sell - position["entry_eff_buy"])
    reverse_loss = units * (close_eff_buy - position["entry_eff_sell"])

    net_profit = forward_profit - reverse_loss
    gross_profit = (close_sell_price - position["buy_price"]) * units

    print("\n----- TRADE EXIT DEBUG -----")
    print(f"Entry eff buy: {position['entry_eff_buy']:.4f}")
    print(f"Entry eff sell: {position['entry_eff_sell']:.4f}")
    print(f"Exit eff buy: {close_eff_buy:.4f}")
    print(f"Exit eff sell: {close_eff_sell:.4f}")
    print(f"Units traded: {units:.6f}")
    print(f"Forward profit: {forward_profit:.2f}")
    print(f"Reverse loss: {reverse_loss:.2f}")
    print(f"Net profit: {net_profit:.2f}")
    print("-----------------------------\n")

    return round(net_profit, 4), round(gross_profit, 4)
