from typing import Optional
from datetime import datetime, timezone

# --- Base Trader ---
class ExchangeTrader:
    """
    Base class for executing trades on exchange.
    Intended to be subclassed with exchange-specific implementations.
    """

    def __init__(self, name: str, pair: str):
        """
        :param name: Name of the exchange (e.g., 'Binance')
        :param pair: Trading pair (e.g., 'BTC/USDT')
        """
        self.name = name
        self.pair = pair
        self.connected = False
        self._reconnect_interval = 5  # Retry interval for connection in seconds

    async def connect(self):
        """
        Connect to the exchange (e.g., authenticate or start session).
        Override in subclasses.
        """
        raise NotImplementedError("connect() must be implemented by subclass.")

    async def buy(self, amount: float, price: Optional[float] = None) -> dict:
        """
        Place a buy order.

        :param amount: Amount of base currency to buy.
        :param price: Limit price (if None, execute market order).
        :return: Order confirmation data as dict.
        """
        raise NotImplementedError("buy() must be implemented by subclass.")

    async def sell(self, amount: float, price: Optional[float] = None) -> dict:
        """
        Place a sell order.

        :param amount: Amount of base currency to sell.
        :param price: Limit price (if None, execute market order).
        :return: Order confirmation data as dict.
        """
        raise NotImplementedError("sell() must be implemented by subclass.")

    async def get_balance(self, asset: str) -> Optional[float]:
        """
        Get the balance of a specific asset.

        :param asset: Asset symbol (e.g., 'BTC', 'USDT')
        :return: Current available balance.
        """
        raise NotImplementedError("get_balance() must be implemented by subclass.")

    async def get_open_orders(self) -> list:
        """
        Retrieve currently open (active) orders.

        :return: List of open orders.
        """
        return []
    
    async def get_trade_history(self) -> list:
        """
        Retrieve trade history for the trading pair.

        :return: List of past trades.
        """
        return []

    def _timestamp(self) -> datetime:
        """Utility to get current UTC timestamp."""
        return datetime.now(timezone.utc)
