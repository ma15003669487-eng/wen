# Polymarket Arbitrage Bot

This repository provides a minimal end-to-end Polymarket arbitrage bot that:

1. Pulls current markets from the Polymarket CLOB API.
2. Detects yes/no pairs whose combined price is below 1 (configurable edge and liquidity filters).
3. Alerts a Telegram channel when an opportunity is found with inline buttons.
4. Prompts for manual confirmation in-chat (or runs fully automatic) before placing orders.
5. Executes a signed Polymarket CLOB order and records position/settlement metadata.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# one-click start
python start.py
```

The bot loads settings from environment variables and will prompt before executing any detected opportunity unless `AUTO_EXECUTE=true`.

## Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `POLYMARKET_API` | Base URL for the Polymarket API | `https://clob.polymarket.com` |
| `POLYMARKET_MARKET_LIMIT` | Number of markets to request | `200` |
| `POLYMARKET_PRICE_CEILING` | Maximum allowed yes+no cost | `1.0` |
| `POLYMARKET_MIN_EDGE` | Minimum edge (1 - cost) required | `0.02` |
| `LIQUIDITY_THRESHOLD` | Minimum liquidity/volume filter | `50.0` |
| `TELEGRAM_BOT_TOKEN` | Bot token used for Telegram alerts | — |
| `TELEGRAM_CHAT_ID` | Chat ID for Telegram alerts | — |
| `AUTO_EXECUTE` | Execute without manual confirmation | `false` |
| `DRY_RUN` | Skip actual trade calls, return payload only | `false` |
| `WALLET_PRIVATE_KEY` | Hex private key for the trading wallet | — |
| `WALLET_AUTO_CREATE` | Set to `true` to create a new wallet if no key is supplied | `false` |
| `ORDER_SIZE` | Total notional to split across YES/NO legs | `50.0` |
| `FEE_CAP` | Maximum acceptable taker fee before skipping | `0.01` |
| `GAS_CAP_GWEI` | Maximum acceptable gas price (gwei) | `150` |
| `MIN_BALANCE` | Minimum USDC balance required to trade | `10` |
| `SETTLEMENT_POLL_SECONDS` | Poll interval for marking positions settled | `30` |

## Manual vs automatic execution
- With `AUTO_EXECUTE=false` (default) the bot pushes the opportunity to Telegram and waits for inline confirmation (Confirm/Reject/Auto) before executing.
- With `AUTO_EXECUTE=true` opportunities are executed immediately after notification.

## Wallet handling
- Provide `WALLET_PRIVATE_KEY` to use an existing wallet.
- Set `WALLET_AUTO_CREATE=true` to generate a throwaway wallet if no key is provided. The generated private key is logged—store it securely if you want to reuse it.

## Extending execution
`TradeExecutor` now signs payloads and posts to the Polymarket `/orders` CLOB endpoint. You can harden the flow by:
- Replacing the simple string serialization with EIP-712 typed-data signing from the official Polymarket schema.
- Wiring on-chain gas estimation and funding flows for the trading network you target.
- Extending the `PositionTracker` to pull settlement state from Polymarket instead of time-based marking.

