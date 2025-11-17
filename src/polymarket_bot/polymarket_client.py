from __future__ import annotations

import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class PolymarketClient:
    def __init__(self, api_base_url: str = "https://clob.polymarket.com") -> None:
        self.api_base_url = api_base_url.rstrip("/")

    def fetch_markets(self, limit: int = 200) -> List[Dict]:
        url = f"{self.api_base_url}/markets"
        params = {"limit": limit, "active": True}
        logger.debug("Requesting markets", extra={"url": url, "params": params})
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        # The API returns an object with "data" key in most versions.
        if isinstance(data, dict) and "data" in data:
            markets = data["data"]
        else:
            markets = data
        logger.info("Fetched %s markets", len(markets))
        return markets

    @staticmethod
    def extract_yes_no_prices(market: Dict) -> Optional[Dict[str, float]]:
        outcomes = market.get("outcomes") or market.get("tokens") or []
        if not isinstance(outcomes, list) or len(outcomes) < 2:
            return None

        prices: Dict[str, float] = {}
        for outcome in outcomes:
            name = outcome.get("name") or outcome.get("outcome")
            price = outcome.get("bestBid") or outcome.get("price") or outcome.get("best_bid")
            if name and price is not None:
                prices[name.lower()] = float(price)

        yes_price = prices.get("yes")
        no_price = prices.get("no")
        if yes_price is None or no_price is None:
            return None

        return {"yes": yes_price, "no": no_price}

    @staticmethod
    def worst_case_cost(prices: Dict[str, float]) -> float:
        return prices["yes"] + prices["no"]
