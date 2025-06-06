from trades.base import ExchangeTrader
from typing import Optional, Literal, Dict, Any
import ccxt.pro
import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv('settings.env')

class BinanceTrader(ExchangeTrader):
    """
    Binance-specific implementation of ExchangeTrader for executing trades.
    Supports both spot and futures trading.
    """

    def __init__(self, pair: str, market_type: Literal['spot', 'future'] = 'spot'):
        super().__init__("Binance", pair)
        self.market_type = market_type
        
        # Choose correct API keys based on market type
        if market_type == 'spot':
            api_key = os.getenv('BINANCE_TESTNET_API_KEY')
            secret_key = os.getenv('BINANCE_TESTNET_SECRET_KEY')
        else:  # futures
            api_key = os.getenv('BINANCE_FUTURES_TESTNET_API_KEY') or os.getenv('BINANCE_TESTNET_API_KEY')
            secret_key = os.getenv('BINANCE_FUTURES_TESTNET_SECRET_KEY') or os.getenv('BINANCE_TESTNET_SECRET_KEY')
        
        # Initialize exchange with testnet configuration
        self.exchange = ccxt.pro.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'sandbox': True,  # Enable testnet
            'enableRateLimit': True,
            'options': {
                'defaultType': market_type,
            }
        })
        
        self.latest_price = None
        self.is_connected = False
        self.position_info = None
        self._watch_tasks = []

    async def connect(self):
        """Connect to Binance WebSocket and start price streaming"""
        try:
            # Test connection with a simple API call
            await self.exchange.load_markets()
            
            # Start watching ticker for price updates
            ticker_task = asyncio.create_task(self._watch_ticker())
            self._watch_tasks.append(ticker_task)
            
            # For futures, also watch positions
            if self.market_type == 'future':
                position_task = asyncio.create_task(self._watch_positions())
                self._watch_tasks.append(position_task)
            
            self.is_connected = True
            print(f"Connected to Binance {self.market_type} testnet for {self.pair}")
            
        except Exception as e:
            print(f"Failed to connect to Binance: {e}")
            raise

    async def _watch_ticker(self):
        """Watch ticker for real-time price updates"""
        try:
            while self.is_connected:
                ticker = await self.exchange.watch_ticker(self.pair)
                self.latest_price = ticker['last']
                await asyncio.sleep(0.1)  # Small delay to prevent overloading
        except Exception as e:
            if self.is_connected:  # Only log if we're still supposed to be connected
                print(f"Error watching ticker: {e}")

    async def _watch_positions(self):
        """Watch positions for futures trading"""
        try:
            while self.is_connected and self.market_type == 'future':
                positions = await self.exchange.watch_positions()
                # Filter for current pair
                for position in positions:
                    if position['symbol'] == self.pair:
                        self.position_info = position
                        break
                await asyncio.sleep(0.1)  # Small delay to prevent overloading
        except Exception as e:
            if self.is_connected:  # Only log if we're still supposed to be connected
                print(f"Error watching positions: {e}")

    async def buy(self, amount: float, price: Optional[float] = None, 
                  leverage: Optional[int] = None) -> dict:
        """Execute buy order"""
        try:
            # Set leverage for futures
            if self.market_type == 'future' and leverage:
                await self.set_leverage(leverage)
            
            if price is None:
                # Market order
                order = await self.exchange.create_market_buy_order(
                    self.pair, 
                    amount
                )
            else:
                # Limit order
                order = await self.exchange.create_limit_buy_order(
                    self.pair, 
                    amount, 
                    price
                )
            
            print(f"Buy order executed: {order['id']}")
            return order
            
        except Exception as e:
            print(f"Error executing buy order: {e}")
            return {'error': str(e)}

    async def sell(self, amount: float, price: Optional[float] = None, 
                   leverage: Optional[int] = None) -> dict:
        """Execute sell order"""
        try:
            # Set leverage for futures
            if self.market_type == 'future' and leverage:
                await self.set_leverage(leverage)
            
            if price is None:
                # Market order
                order = await self.exchange.create_market_sell_order(
                    self.pair, 
                    amount
                )
            else:
                # Limit order
                order = await self.exchange.create_limit_sell_order(
                    self.pair, 
                    amount, 
                    price
                )
            
            print(f"Sell order executed: {order['id']}")
            return order
            
        except Exception as e:
            print(f"Error executing sell order: {e}")
            return {'error': str(e)}

    async def set_leverage(self, leverage: int) -> dict:
        """Set leverage for futures trading"""
        try:
            if self.market_type != 'future':
                return {'error': 'Leverage only available for futures'}
            
            result = await self.exchange.set_leverage(leverage, self.pair)
            print(f"Leverage set to {leverage}x for {self.pair}")
            return result
            
        except Exception as e:
            print(f"Error setting leverage: {e}")
            return {'error': str(e)}

    async def set_margin_mode(self, margin_mode: Literal['isolated', 'cross']) -> dict:
        """Set margin mode for futures trading"""
        try:
            if self.market_type != 'future':
                return {'error': 'Margin mode only available for futures'}
            
            result = await self.exchange.set_margin_mode(margin_mode, self.pair)
            print(f"Margin mode set to {margin_mode} for {self.pair}")
            return result
            
        except Exception as e:
            print(f"Error setting margin mode: {e}")
            return {'error': str(e)}

    async def get_position(self) -> Optional[Dict[str, Any]]:
        """Get current position for futures trading"""
        try:
            if self.market_type != 'future':
                return None
            
            # Return cached position info if available
            if self.position_info:
                return self.position_info
            
            positions = await self.exchange.fetch_positions([self.pair])
            return positions[0] if positions else None
            
        except Exception as e:
            print(f"Error fetching position: {e}")
            return None

    async def close_position(self, side: Literal['long', 'short']) -> dict:
        """Close position for futures trading"""
        try:
            if self.market_type != 'future':
                return {'error': 'Position closing only available for futures'}
            
            position = await self.get_position()
            if not position:
                return {'error': 'No position found'}
            
            # Check for position size using the correct key
            position_size = position.get('contracts', 0) or position.get('size', 0)
            if position_size == 0:
                return {'error': 'No open position to close'}
            
            # Determine order side to close position
            order_side = 'sell' if side == 'long' else 'buy'
            amount = abs(position_size)
            
            # Create market order to close position
            if order_side == 'sell':
                order = await self.exchange.create_market_sell_order(self.pair, amount)
            else:
                order = await self.exchange.create_market_buy_order(self.pair, amount)
            
            print(f"Position closed: {order['id']}")
            return order
            
        except Exception as e:
            print(f"Error closing position: {e}")
            return {'error': str(e)}

    async def get_balance(self, asset: str) -> Optional[float]:
        """Get balance for specific asset"""
        try:
            balance = await self.exchange.fetch_balance()
            
            if asset in balance:
                return balance[asset]['free']
            else:
                print(f"Asset {asset} not found in balance")
                return None
                
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return None

    async def get_open_orders(self) -> list:
        """Get all open orders for the trading pair"""
        try:
            orders = await self.exchange.fetch_open_orders(self.pair)
            return orders
            
        except Exception as e:
            print(f"Error fetching open orders: {e}")
            return []

    async def cancel_order(self, order_id: str) -> dict:
        """Cancel specific order"""
        try:
            result = await self.exchange.cancel_order(order_id, self.pair)
            print(f"Order {order_id} cancelled")
            return result
            
        except Exception as e:
            print(f"Error cancelling order: {e}")
            return {'error': str(e)}

    async def get_order_status(self, order_id: str) -> dict:
        """Get status of specific order"""
        try:
            order = await self.exchange.fetch_order(order_id, self.pair)
            return order
            
        except Exception as e:
            print(f"Error fetching order status: {e}")
            return {'error': str(e)}

    async def get_current_price(self) -> Optional[float]:
        """Get current market price"""
        try:
            if self.latest_price:
                return self.latest_price
            
            ticker = await self.exchange.fetch_ticker(self.pair)
            return ticker['last']
            
        except Exception as e:
            print(f"Error fetching current price: {e}")
            return None

    async def get_funding_rate(self) -> Optional[float]:
        """Get funding rate for futures trading"""
        try:
            if self.market_type != 'future':
                return None
            
            funding_rate = await self.exchange.fetch_funding_rate(self.pair)
            return funding_rate['fundingRate']
            
        except Exception as e:
            print(f"Error fetching funding rate: {e}")
            return None

    async def close(self):
        """Close connection and cleanup"""
        try:
            self.is_connected = False
            
            # Cancel all watch tasks
            for task in self._watch_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            self._watch_tasks.clear()
            
            # Close the exchange connection
            if self.exchange:
                await self.exchange.close()
            
            print("Binance connection closed")
            
        except Exception as e:
            print(f"Error closing connection: {e}")

    def __del__(self):
        """Destructor to ensure connection is closed"""
        if hasattr(self, 'exchange') and self.exchange and self.is_connected:
            try:
                # Create a new event loop if none exists
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                if not loop.is_closed():
                    loop.create_task(self.close())
            except:
                pass
