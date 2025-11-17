from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .polymarket_client import PolymarketClient


@dataclass
class ArbitrageOpportunity:
    market_id: str
    question: str
    yes_price: float
    no_price: float
    edge: float
    volume: Optional[float]

    @property
    def summary(self) -> str:
        return (
            f"{self.question}\n"
            f"yes: {self.yes_price:.4f}, no: {self.no_price:.4f}, cost: {self.cost:.4f}, edge: {self.edge:.2%}"
        )

    @property
    def cost(self) -> float:
        return self.yes_price + self.no_price


class ArbitrageEngine:
    def __init__(self, client: PolymarketClient, price_ceiling: float = 1.0, min_edge: float = 0.02, liquidity_threshold: float = 50.0) -> None:
        self.client = client
        self.price_ceiling = price_ceiling
        self.min_edge = min_edge
        self.liquidity_threshold = liquidity_threshold

    def find_opportunities(self, limit: int = 200) -> List[ArbitrageOpportunity]:
        markets = self.client.fetch_markets(limit=limit)
        opportunities: List[ArbitrageOpportunity] = []

        for market in markets:
            prices = self.client.extract_yes_no_prices(market)
            if prices is None:
                continue

            cost = PolymarketClient.worst_case_cost(prices)
            if cost >= self.price_ceiling:
                continue

            edge = 1 - cost
            if edge < self.min_edge:
                continue

            volume = self._extract_liquidity(market)
            if volume is not None and volume < self.liquidity_threshold:
                continue

            opportunities.append(
                ArbitrageOpportunity(
                    market_id=str(market.get("id")),
                    question=market.get("question") or market.get("title") or "Unknown market",
                    yes_price=prices["yes"],
                    no_price=prices["no"],
                    edge=edge,
                    volume=volume,
                )
            )

        return sorted(opportunities, key=lambda o: o.edge, reverse=True)

    @staticmethod
    def _extract_liquidity(market: Dict) -> Optional[float]:
        liquidity = market.get("liquidity") or market.get("volume24h") or market.get("volume")
        if liquidity is None:
            return None
        try:
            return float(liquidity)
        except (TypeError, ValueError):
            return None
