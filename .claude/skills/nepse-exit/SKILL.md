---
name: nepse-exit
description: >-
  NEPSE Exit Planner. Calculates NPR risk per share and a target from a
  completed NEPSE entry result plus a stop method the learner selects, or from
  entry and stop prices they supply. It can write a standardized paper plan for
  the NEPSE replay and budget tools. It does not pick a trade, predict price,
  model costs, or place an order. Use for hypothetical exit arithmetic only.
argument-hint: "[--from-entry entry.json] [--stop-method or-mid|or-low|custom]"
---

# NEPSE Exit Planner

This tool calculates arithmetic from a user's inputs. It does not decide that
a stop is appropriate. With an ORB entry result, the default practice stop is
the opening-range midpoint. The user can instead choose the range low or enter
a custom stop. A level setup needs a custom stop.

It preserves the original exit planner's entry-stop-target math and plan
handoff, adapted to learner-selected NPR levels with no live position tracking.

Create a plan from the entry helper's JSON result:

```bash
python3 nepse_tools/cli.py entry check DEMO \
  --candles nepse_tools/examples/candles/DEMO.csv \
  --as-of "2026-11-13 11:20" --write /tmp/nepse-entry.json

python3 nepse_tools/cli.py exit --from-entry /tmp/nepse-entry.json \
  --stop-method or-mid --target-r 1 --write trader/nepse-plan.json
```

Or calculate from prices the learner supplies:

```bash
python3 nepse_tools/cli.py exit DEMO \
  --entry 105 --stop 99 --target-r 2 --write trader/nepse-plan.json
```

## Plan fields

The saved JSON carries `market: NEPSE`, `currency: NPR`, symbol, date and
entry time if available, setup, interval, opening range, entry, stop, target,
risk per share, target R and stop method. The plan is marked practice-only and
`order_placed: false`. `/nepse-budget` can read this file; `/nepse-timemachine`
can replay an ORB plan when the user provides enough historical candles.

A manual plan without a date and entry close time is useful for arithmetic but
cannot be used for historical replay. Use `--from-entry` to preserve the
entry's session and candle details.

## Steps for beginners

1. Confirm the symbol, entry value, and whether the entry came from a completed
   candle or a hypothetical price.
2. Explain the stop method in simple terms. The midpoint and range low are
   examples for practice, not recommended levels.
3. Show risk per share as entry minus stop for this long-only calculation.
4. Explain that the target is entry plus risk times the chosen R multiple.
5. Read back the saved levels and ask whether the learner understands them.
6. State which costs and market mechanics are not included.

A stop can be crossed in a gap or fast market. The calculation assumes a fill
at the stop level and does not guarantee one.

## Restrictions

The CLI supports long practice plans only. Prices are NPR. It does not model
NEPSE tick sizes, fees, tax, settlement, circuit breakers, liquidity, partial
fills, slippage, or broker/TMS requirements. Check those with an authoritative
source before any real decision. It cannot submit, cancel, or monitor an order.

## Safety

Do not present a target as expected, likely, or guaranteed. Do not tell the
learner to buy, sell, or hold. A saved plan is not an approval or a signal.
No broker connection is used and no order was placed. This is education, not
financial advice.
