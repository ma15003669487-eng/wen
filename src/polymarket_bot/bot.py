from __future__ import annotations

import logging
from typing import Optional

from .arbitrage import ArbitrageEngine, ArbitrageOpportunity
from .config import BotConfig, load_config
from .executor import TradeExecutor
from .notifier import TelegramNotifier
from .polymarket_client import PolymarketClient
from .positions import PositionTracker
from .wallet import WalletManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def run_bot(config: Optional[BotConfig] = None) -> None:
    cfg = config or load_config()
    client = PolymarketClient(api_base_url=cfg.api_base_url)
    engine = ArbitrageEngine(
        client=client,
        price_ceiling=cfg.price_ceiling,
        min_edge=cfg.min_edge,
        liquidity_threshold=cfg.liquidity_threshold,
    )
    executor = TradeExecutor(api_base_url=cfg.api_base_url)
    wallet_manager = WalletManager(private_key=cfg.wallet.private_key, auto_create=cfg.wallet.auto_create)
    wallet = wallet_manager.load_or_create()
    notifier = TelegramNotifier(cfg.telegram) if cfg.telegram else None
    tracker = PositionTracker()

    opportunities = engine.find_opportunities(limit=cfg.market_limit)
    if not opportunities:
        logger.info("No arbitrage opportunities found")
        return

    for opportunity in opportunities:
        _handle_opportunity(opportunity, notifier, executor, wallet, tracker, cfg)


def _handle_opportunity(
    opportunity: ArbitrageOpportunity,
    notifier: Optional[TelegramNotifier],
    executor: TradeExecutor,
    wallet,
    tracker: PositionTracker,
    cfg: BotConfig,
) -> None:
    logger.info("Opportunity: %s", opportunity.summary)
    if notifier:
        message_id = notifier.send_opportunity(opportunity, order_size=cfg.risk.order_size)
    else:
        message_id = None

    should_execute = cfg.auto_execute
    if not should_execute:
        if notifier and message_id:
            decision = notifier.await_confirmation(message_id, opportunity.market_id)
            should_execute = decision is True
            if decision is None:
                answer = input("Execute this opportunity? (y/N): ")
                should_execute = answer.strip().lower() == "y"
        else:
            answer = input("Execute this opportunity? (y/N): ")
            should_execute = answer.strip().lower() == "y"

    if not should_execute:
        logger.info("Skipped execution by user choice")
        return

    result = executor.execute(
        opportunity,
        wallet,
        dry_run=cfg.dry_run,
        order_size=cfg.risk.order_size,
        fee_cap=cfg.risk.fee_cap,
        gas_cap_gwei=cfg.risk.gas_cap_gwei,
        min_balance=cfg.risk.min_balance,
        tracker=tracker,
    )
    logger.info("Execution result", extra={"result": result})


if __name__ == "__main__":
    run_bot()
