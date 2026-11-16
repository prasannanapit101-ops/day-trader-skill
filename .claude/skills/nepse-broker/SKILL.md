---
name: nepse-broker
description: >-
  NEPSE Paper Ticket Builder. Formats one hypothetical BUY or owned-share SELL
  from a user's JSON into a readable NPR ticket and optional JSON file. It
  refuses a sell quantity above the user's stated whole-share ownership. It
  has no TMS, broker connector, login, or execution function; every ticket is
  explicitly NOT PLACED. Use only to review a draft paper ticket.
argument-hint: "[one proposed NEPSE order JSON]"
---

# NEPSE Paper Ticket Builder

This is not a broker integration. It formats one order for inspection and
cannot log in to a Trading Management System, submit, cancel, or amend an order.
The output is always marked `PAPER TICKET ONLY - NOT PLACED`.

It keeps the original broker workflow's human-readable ticket review while
removing broker execution, account access, credentials, and order state.

Use the proposed order JSON from `/nepse-budget`:

```bash
python3 nepse_tools/cli.py broker \
  --order trader/nepse-orders.json \
  --write trader/nepse-paper-ticket.json
```

The JSON must contain one order with `symbol`, `side` (`BUY` or `SELL`), a
positive whole-share `quantity`, and an NPR `limit_price` or `entry`. A SELL
must also provide `owned_shares`; this tool will not create a short position.

## Review steps

1. Confirm that the learner requested a paper ticket, not a real order.
2. Read back the symbol, side, whole-share quantity, and NPR limit price.
3. If relevant, confirm `/nepse-risk` checked the exact same numbers.
4. Explain any validation error. Do not silently alter price, size, or side.
5. Save the paper JSON only if the learner wants a practice artifact.

## What is not supported

There is no TMS, broker, connector, session cookie, password, API key, or
account balance access. The command has no network client. It does not check
whether a ticker is tradable, the current market price, circuit levels, price
increments, order validity, settlement, fees, or buying power.

A paper ticket is a description of user-supplied values, not an order accepted
by an exchange. Never tell the user a ticket was sent, filled, or approved.
If they ask to place a real order, state that this NEPSE skill cannot do that
and direct them to their official broker interface themselves.

## Beginner handholding

Explain BUY and SELL from the user's perspective. Confirm that owned shares
are shares the learner actually holds, not a number guessed by the tool. A
sell ticket may be for a practice example only. Ask before writing any file.

## A useful beginner check

Compare the proposed limit price with a quote the learner has verified
separately. The ticket command does not obtain that quote and cannot say
whether the order would be accepted or filled. A matching risk-check result
also does not replace the learner's own review.

## Safety

Never ask for or store broker credentials in chat or these files. Do not
connect this workflow to U.S. broker tools. No order is sent or monitored.
This is a learning artifact, not financial advice or brokerage service.
