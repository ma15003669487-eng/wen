from __future__ import annotations

import logging
import time
from typing import Dict, Optional

import requests

from .arbitrage import ArbitrageOpportunity
from .positions import Position, PositionTracker
from .wallet import Wallet

logger = logging.getLogger(__name__)


class TradeExecutor:
    def __init__(self, api_base_url: str = "https://clob.polymarket.com") -> None:
        self.api_base_url = api_base_url.rstrip("/")

    def fetch_balance(self, wallet: Wallet) -> Optional[float]:
        try:
            response = requests.get(
                f"{self.api_base_url}/wallets/{wallet.address}/balances", params={"token": "USDC"}, timeout=15
            )
            if not response.ok:
                return None
            data = response.json()
            balances = data.get("balances") or data
            if isinstance(balances, dict):
                return float(balances.get("USDC", 0))
            return None
        except requests.RequestException:
            return None

    def fetch_fee_rate(self) -> Optional[float]:
        try:
            response = requests.get(f"{self.api_base_url}/fees", timeout=10)
            if response.ok:
                data = response.json()
                return float(data.get("taker", data.get("maker", 0)))
        except requests.RequestException:
            return None
        return None

    def fetch_gas_price(self) -> Optional[float]:
        try:
            response = requests.get(f"{self.api_base_url}/gas", timeout=10)
            if response.ok:
                data = response.json()
                return float(data.get("maxFeePerGas", data.get("standard", 0)))
        except requests.RequestException:
            return None
        return None

    def execute(
        self,
        opportunity: ArbitrageOpportunity,
        wallet: Wallet,
        dry_run: bool = False,
        order_size: float = 50.0,
        fee_cap: float = 0.01,
        gas_cap_gwei: float = 150.0,
        min_balance: float = 10.0,
        tracker: Optional[PositionTracker] = None,
    ) -> Dict:
        payload = self._build_order_payload(opportunity, order_size, wallet)

        logger.info(
            "Preparing arbitrage execution",
            extra={"market": opportunity.market_id, "wallet": wallet.address, "dry_run": dry_run},
        )

        balance = self.fetch_balance(wallet)
        if balance is not None and balance < min_balance:
            logger.warning("Insufficient balance", extra={"balance": balance, "min_balance": min_balance})
            return {"status": "insufficient_balance", "balance": balance}

        fee_rate = self.fetch_fee_rate()
        if fee_rate is not None and fee_rate > fee_cap:
            logger.warning("Fee cap exceeded", extra={"fee_rate": fee_rate, "fee_cap": fee_cap})
            return {"status": "fee_cap_exceeded", "fee_rate": fee_rate}

        gas_price = self.fetch_gas_price()
        if gas_price is not None and gas_price > gas_cap_gwei:
            logger.warning("Gas cap exceeded", extra={"gas_price": gas_price, "gas_cap": gas_cap_gwei})
            return {"status": "gas_cap_exceeded", "gas_price": gas_price}

        if dry_run:
            return {"status": "dry_run", "payload": payload}

        url = f"{self.api_base_url}/orders"
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()

        tx_hash = result.get("txHash") or result.get("hash")
        if tracker and tx_hash:
            tracker.record(
                Position(
                    market_id=opportunity.market_id,
                    side="neutral",
                    size=order_size,
                    price=opportunity.cost,
                    tx_hash=tx_hash,
                    status="submitted",
                )
            )
            self._await_settlement(tracker, opportunity.market_id, tx_hash)

        return result

    @staticmethod
    def _build_order_payload(opportunity: ArbitrageOpportunity, order_size: float, wallet: Wallet) -> Dict:
        half_size = order_size / 2
        expiration = int(time.time()) + 600
        unsigned = {
            "orders": [
                {
                    "side": "buy",
                    "price": opportunity.yes_price,
                    "size": half_size,
                    "market": opportunity.market_id,
                    "outcome": "YES",
                    "expiration": expiration,
                    "maker": wallet.address,
                },
                {
                    "side": "buy",
                    "price": opportunity.no_price,
                    "size": half_size,
                    "market": opportunity.market_id,
                    "outcome": "NO",
                    "expiration": expiration,
                    "maker": wallet.address,
                },
            ],
        }
        serialized = str(unsigned)
        signature = wallet.sign_payload(serialized)
        unsigned["signature"] = signature
        return unsigned

    @staticmethod
    def _await_settlement(tracker: PositionTracker, market_id: str, tx_hash: str, timeout: int = 300) -> None:
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(5)
        tracker.update_status(tx_hash, "pending_settlement")
