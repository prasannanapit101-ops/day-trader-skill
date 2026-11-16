---
name: nepse-risk
description: >-
  NEPSE Risk Check. Compares proposed long BUY order arithmetic with personal
  NPR limits in a config JSON, including per-trade loss, daily loss, available
  cash, trade count and minimum reward/risk. Requires positive user-supplied
  limits and paper_only true. It does not certify NEPSE or broker rules, fetch
  balances, or approve a real order. Use before creating a NEPSE paper ticket.
argument-hint: "[orders JSON] [your risk config JSON]"
---

# NEPSE Risk Check

This checks user-entered numbers against the learner's own practice limits.
It is not a legal, exchange, settlement, or broker-compliance check. The
checker only supports long BUY entries and stays paper-only.

Copy the example config to a private working folder, then replace all zero
limits with the learner's own values. Zero limits are intentionally rejected:

```bash
cp nepse_tools/config.example.json trader/nepse-config.json
python3 nepse_tools/cli.py risk \
  --orders trader/nepse-orders.json \
  --config trader/nepse-config.json \
  --daily-loss 0 --trades-today 0
```

Required positive config values are `cash_npr` (or `account_npr`),
`max_loss_per_trade_npr`, `max_daily_loss_npr`, `max_trades_per_day`, and
`min_reward_risk`. `round_trip_fee_per_share_npr` may be zero. Keep
`paper_only` set to `true` and `allow_short` set to `false`.

## What is checked

- Quantity is a positive whole number of shares.
- Side is BUY, and entry, stop, and target are positive with stop below entry
  and target above entry.
- Planned loss, including a configured fee estimate, fits the per-trade cap.
- Proposed cost fits the configured available cash.
- Reward/risk meets the user's threshold.
- Realized loss plus earlier PASS proposals stays inside the daily loss cap.
- The count of prior trades plus accepted proposed orders stays inside the
  user's daily trade limit.

`PASS` means only that these numbers fit the supplied limits. `BLOCK` explains
which arithmetic rule failed. It does not check existing positions, pending
orders, current prices, actual fees, fills or daily trading history.

## Important manual inputs

`--daily-loss` is realized loss already incurred today, in NPR. `--trades-today`
is the number of trades already taken. The tool does not keep a portfolio or
risk ledger; update these values yourself each time. Cash should be the amount
actually available, not a total account value already committed elsewhere.

## Beginner handholding

Show `quantity x (entry - stop + fee estimate)` in plain language. Ask the
learner to verify every number, the cash available, realized loss, and trade
count. Explain that a PASS is not permission to trade. If any required config
field is missing or zero, stop and ask for the user's own limit rather than
choosing one for them.

## Safety

The tool does not model NEPSE fees unless supplied, tax, settlement, circuits,
price bands, tick sizes, liquidity, TMS validations or broker restrictions.
It does not fetch current prices or balances. It never creates or sends an
order. Do not call PASS a recommendation or a trade approval. This is practice,
not financial advice.
