from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from eth_account import Account

logger = logging.getLogger(__name__)


@dataclass
class Wallet:
    address: str
    private_key: str

    def sign_payload(self, payload: str) -> str:
        from eth_account.messages import encode_defunct

        message = encode_defunct(text=payload)
        signed = Account.sign_message(message, private_key=self.private_key)
        return signed.signature.hex()


class WalletManager:
    def __init__(self, private_key: Optional[str] = None, auto_create: bool = False) -> None:
        self.private_key = private_key
        self.auto_create = auto_create

    def load_or_create(self) -> Wallet:
        if self.private_key:
            account = Account.from_key(self.private_key)
            logger.info("Loaded wallet", extra={"address": account.address})
            return Wallet(address=account.address, private_key=self.private_key)

        if not self.auto_create:
            raise RuntimeError("No private key provided and auto_create is disabled.")

        account = Account.create()
        self.private_key = account.key.hex()
        logger.info("Created new wallet", extra={"address": account.address})
        return Wallet(address=account.address, private_key=self.private_key)
