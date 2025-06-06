#  core/market_matrix.py

from exchanges.base import ExchangeFetcher
from typing import Dict, List

# --- Matrix to organize fetchers ---
class MarketMatrix:
    def __init__(self):
        self.fetchers: Dict[str, List[ExchangeFetcher]] = {}

    def add_fetcher(self, pair: str, fetcher: ExchangeFetcher):
        if pair not in self.fetchers:
            self.fetchers[pair] = []
        self.fetchers[pair].append(fetcher)
    
# --- Shutdown ---
async def shutdown(matrix: MarketMatrix):
    for fetchers in matrix.fetchers.values():
        for fetcher in fetchers:
            if hasattr(fetcher, 'exchange'):
                await fetcher.exchange.close()