---
name: nepse-timemachine
description: >-
  NEPSE Historical Replay. Uses a saved NEPSE ORB plan and a learner-provided
  multi-session 1m/5m candle CSV to replay historical setups and generate
  repeatable bootstrap paths from earlier complete sessions. Reports target,
  stop, neither, closing-price ranges and gross R with a conservative stop-first
  rule when both levels fall in one bar. It is offline and not a forecast.
argument-hint: "[saved NEPSE plan JSON] [multi-session candle CSV]"
---

# NEPSE Time Machine

This offline tool has two distinct outputs: the result of the same ORB rule on
complete prior sessions, and simulated paths resampled from those sessions.
The simulation uses only candle history the learner supplies. It does not
fetch market data, and its estimates are not forecasts.

It keeps the original Time Machine's historical outcomes and repeatable
simulated paths, but uses only supplied NEPSE sessions and makes no forecast.

First save a dated ORB plan from `/nepse-exit`, then provide at least 20 full
prior sessions plus the plan date's completed entry candle:

```bash
python3 nepse_tools/cli.py timemachine \
  --plan trader/nepse-plan.json \
  --candles /path/to/NABIL-multi-session-5m.csv \
  --replays 10000 --seed 19 --window 2 \
  --write trader/nepse-replay.json
```

The CSV needs `timestamp,open,high,low,close` and optional `volume`. Timestamps
label candle starts and naive times mean NPT. The default assumed session is
11:00-15:00 NPT; verify the current exchange hours and use `--session-open`
and `--session-close` when appropriate. A complete 5m session has 48 aligned
bars under that assumption. Incomplete prior sessions are skipped.

## What the replay does

- Checks that the plan is for NEPSE, is long-only, is ORB, and has an entry
  candle that matches the supplied data.
- Uses full prior sessions only, strictly before the plan's date, for its
  bootstrap pool and historical replay.
- Replays the first completed close above the opening-range high.
- Uses the plan's `or-mid`, `or-low`, or custom percentage-distance stop rule
  and the target R encoded by its entry, stop, and target.
- Counts a candle that touches stop and target as a stop first.
- Defaults to 10,000 deterministic paths with seed 19; repeat with the same
  data, seed, and settings to reproduce the output.
- Prints sample size, historical outcomes, bootstrap percentages, closing
  price percentiles, and average gross R.

Use `--until HH:MM` to cut off the replay before the assumed session close.
`--replays`, `--seed`, `--window` and `--min-sessions` are configurable. The
minimum is 20 complete prior sessions unless the user deliberately changes it.

## Beginner handholding

Explain the difference between historical outcomes and the resampled paths.
Point out the number of complete sessions, any skipped sessions, and how the
stop rule was translated. Walk through one historical entry and its stop and
target. Ask whether the data is the same symbol, interval, and session the
learner intended.

Small or biased samples are fragile. Bootstrap paths re-use observed candles;
they cannot create a real distribution of future events. News, halts, gaps,
liquidity and market structure can differ from the sample.

## Limitations

The simulation samples bar-to-bar price ratios by approximate time-of-day
slot. It is not tick replay, a market-impact model, or a guarantee of fills.
It does not model fees, tax, settlement, circuit breakers, dividends, missing
announcements or slippage. Custom stops are represented in the historical
replay as a percentage distance from each historical entry.

## Safety

Never describe an output percentage as the chance that a trade will win. Say
that this is a repeatable resampling exercise on supplied history, not a
prediction. No order is created or sent. This is education, not financial
advice.
