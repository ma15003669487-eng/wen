from __future__ import annotations

import logging
from typing import Optional

import requests

from .arbitrage import ArbitrageOpportunity
from .config import TelegramConfig

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, config: TelegramConfig) -> None:
        self.config = config

    def send_opportunity(self, opportunity: ArbitrageOpportunity, order_size: float) -> Optional[int]:
        message = self._format_message(opportunity, order_size)
        logger.info("Sending alert to Telegram", extra={"market": opportunity.market_id})
        url = f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage"
        response = requests.post(
            url,
            json={
                "chat_id": self.config.chat_id,
                "text": message,
                "parse_mode": self.config.parse_mode,
                "reply_markup": {
                    "inline_keyboard": [
                        [
                            {"text": "✅ 执行", "callback_data": f"confirm:{opportunity.market_id}"},
                            {"text": "❌ 放弃", "callback_data": f"reject:{opportunity.market_id}"},
                        ],
                        [
                            {"text": "⚙️ 自动执行", "callback_data": f"auto:{opportunity.market_id}"}
                        ],
                    ]
                },
            },
            timeout=10,
        )
        if not response.ok:
            logger.warning("Failed to send Telegram message", extra={"status": response.status_code, "body": response.text})
            return None
        return response.json().get("result", {}).get("message_id")

    def await_confirmation(self, message_id: int, market_id: str, timeout_seconds: int = 90) -> Optional[bool]:
        """Polls for an inline keyboard response. Returns True/False or None on timeout."""
        url = f"https://api.telegram.org/bot{self.config.bot_token}/getUpdates"
        last_update_id: Optional[int] = None
        elapsed = 0

        while elapsed < timeout_seconds:
            params = {"timeout": 10}
            if last_update_id:
                params["offset"] = last_update_id + 1
            response = requests.get(url, params=params, timeout=15)
            if response.ok:
                data = response.json()
                for update in data.get("result", []):
                    last_update_id = update.get("update_id", last_update_id)
                    callback = update.get("callback_query")
                    if not callback:
                        continue
                    msg = callback.get("message") or {}
                    if msg.get("message_id") != message_id:
                        continue
                    data_val = callback.get("data", "")
                    requests.post(
                        f"https://api.telegram.org/bot{self.config.bot_token}/answerCallbackQuery",
                        json={"callback_query_id": callback.get("id"), "text": "已收到"},
                        timeout=10,
                    )
                    if data_val.startswith("confirm"):
                        return True
                    if data_val.startswith("reject"):
                        return False
                    if data_val.startswith("auto"):
                        return True
            elapsed += 10

        logger.info("No Telegram confirmation received; falling back to local prompt")
        return None

    @staticmethod
    def _format_message(opportunity: ArbitrageOpportunity, order_size: float) -> str:
        return (
            f"*Arbitrage opportunity found!*\n"
            f"Market: `{opportunity.market_id}`\n"
            f"{opportunity.question}\n"
            f"Yes price: {opportunity.yes_price:.4f}\n"
            f"No price: {opportunity.no_price:.4f}\n"
            f"Cost: {opportunity.cost:.4f}\n"
            f"Edge: {opportunity.edge:.2%}\n"
            f"Liquidity: {opportunity.volume or 'n/a'}\n"
            f"Order size: {order_size}"
        )
