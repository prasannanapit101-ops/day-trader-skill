---
name: nepse-budget
description: >-
  NEPSE Budget Manager. Calculates a whole-share hypothetical quantity in NPR
  using the user's available cash, maximum planned loss, entry, and stop. It
  can read the saved NEPSE exit plan and write a proposed order JSON that the
  risk checker can inspect, but it never submits an order. Fees are excluded
  unless the learner supplies an estimate. Use for practice sizing only.
argument-hint: "[NEPSE plan JSON] [capital NPR] [maximum loss NPR]"
---

# NEPSE Budget Manager

This is whole-share sizing arithmetic, not a recommendation. It caps the
quantity by both the learner's stated maximum loss and available cash. To
continue the NEPSE practice workflow, pass the plan made by `/nepse-exit`:

```bash
python3 nepse_tools/cli.py budget \
  --plan trader/nepse-plan.json \
  --capital 100000 --max-loss 1200 \
  --round-trip-fee-per-share 0 --write trader/nepse-orders.json
```

You can also give a symbol, entry, and stop directly:

```bash
python3 nepse_tools/cli.py budget DEMO \
  --capital 100000 --max-loss 1200 --entry 105 --stop 99 --target-r 1
```

The example numbers are for arithmetic demonstration only. Never copy them
as a personal budget or risk limit.

## Calculation

Risk per share is the entry-stop distance plus the learner's optional round-
trip fee estimate per share. The risk cap is `floor(max_loss / risk_per_share)`.
The cash cap is `floor(capital / entry)`. The lower whole-share amount is the
practice size. Cash sizing is gross of buy fees; only the supplied fee estimate
is included in stop-risk arithmetic.

When `--write` is used, the JSON contains one proposed long BUY with symbol,
quantity, entry, stop, target, gross value, and planned loss. It is marked
`PROPOSED - NOT PLACED`. `/nepse-risk` can read that file. No broker is called.

## Steps for a beginner

1. Ask the learner to state their own available cash and maximum loss in NPR.
2. Confirm the entry and stop are hypothetical values they chose.
3. Explain why the stop distance is multiplied by share quantity.
4. Show the risk-limited and cash-limited share counts separately.
5. Name any costs omitted from the calculation and ask the learner to verify
   commission, taxes and other charges from their own broker.
6. If the final size is zero, stop. Do not widen the stop or raise the budget
   to force a nonzero answer.

## Limitations

The tool does not know available cash in a user's actual TMS account. The user
must enter cash that is genuinely available after existing commitments. It
does not model tick sizes, fees unless supplied, tax, settlement, partial
fills, slippage, price limits or broker constraints. A share count fitting
these inputs does not make a trade suitable.

## Safety

Never choose an individual's risk budget. A size calculation is not a buy
signal, and `PROPOSED` does not mean approved. No order is submitted. The
original U.S.-market budget tool is not for NPR. This is educational arithmetic,
not financial advice.
