from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    parse_mode: str = "Markdown"


@dataclass
class WalletConfig:
    private_key: Optional[str] = None
    auto_create: bool = False


@dataclass
class RiskConfig:
    order_size: float = 50.0
    fee_cap: float = 0.01
    gas_cap_gwei: float = 150.0
    min_balance: float = 10.0
    settlement_poll_seconds: int = 30


@dataclass
class BotConfig:
    api_base_url: str = "https://clob.polymarket.com"
    market_limit: int = 200
    price_ceiling: float = 1.0
    min_edge: float = 0.02
    auto_execute: bool = False
    dry_run: bool = False
    liquidity_threshold: float = 50.0

    telegram: Optional[TelegramConfig] = None
    wallet: WalletConfig = WalletConfig()
    risk: RiskConfig = RiskConfig()


def load_config() -> BotConfig:
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")

    telegram = None
    if telegram_token and telegram_chat_id:
        telegram = TelegramConfig(bot_token=telegram_token, chat_id=telegram_chat_id)

    wallet_private_key = os.getenv("WALLET_PRIVATE_KEY")
    wallet_auto_create = os.getenv("WALLET_AUTO_CREATE", "false").lower() == "true"

    risk = RiskConfig(
        order_size=float(os.getenv("ORDER_SIZE", 50.0)),
        fee_cap=float(os.getenv("FEE_CAP", 0.01)),
        gas_cap_gwei=float(os.getenv("GAS_CAP_GWEI", 150.0)),
        min_balance=float(os.getenv("MIN_BALANCE", 10.0)),
        settlement_poll_seconds=int(os.getenv("SETTLEMENT_POLL_SECONDS", 30)),
    )

    return BotConfig(
        api_base_url=os.getenv("POLYMARKET_API", "https://clob.polymarket.com"),
        market_limit=int(os.getenv("POLYMARKET_MARKET_LIMIT", 200)),
        price_ceiling=float(os.getenv("POLYMARKET_PRICE_CEILING", 1.0)),
        min_edge=float(os.getenv("POLYMARKET_MIN_EDGE", 0.02)),
        auto_execute=os.getenv("AUTO_EXECUTE", "false").lower() == "true",
        dry_run=os.getenv("DRY_RUN", "false").lower() == "true",
        liquidity_threshold=float(os.getenv("LIQUIDITY_THRESHOLD", 50.0)),
        telegram=telegram,
        wallet=WalletConfig(private_key=wallet_private_key, auto_create=wallet_auto_create),
        risk=risk,
    )
