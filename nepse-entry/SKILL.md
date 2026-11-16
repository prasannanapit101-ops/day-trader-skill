---
name: nepse-entry
description: >-
  NEPSE Entry Practice. Checks a completed opening-range or user-supplied
  level condition from a one-session 1m/5m OHLCV CSV, with naive timestamps
  interpreted in Nepal time, and explains whether a candle close qualified.
  It is offline practice only: no live feed, no order, and no buy recommendation.
  Use when a beginner asks to practice a NEPSE entry and can share candles.
argument-hint: "[symbol] [one-session candle CSV] [setup orb|level]"
---

# NEPSE Entry Practice

This preserves the original entry tool's completed-bar opening-range and
level-check workflow, using Nepal time and supplied candles instead of Yahoo
quotes and the NYSE calendar.

The regular `/trader-entry` command includes a separate offline NEPSE helper.
You can call the same helper through this skill's shared CLI:

```bash
python3 nepse_tools/cli.py entry check DEMO \
  --candles nepse_tools/examples/candles/DEMO.csv \
  --interval 5m --as-of "2026-11-13 11:20"
```

The demo is synthetic. Replace the symbol and path with the learner's own
one-session CSV. Required columns are `timestamp,open,high,low,close`;
`volume` is optional unless the learner requests a volume filter.

## What the rule checks

- `orb` uses the first 15 minutes of the assumed regular session by default.
- A qualifying event is the first completed candle close above the opening
  range high; a wick above the high is not a close above it.
- `level` checks a price the learner supplies with `--level`.
- A candle counts only after its end time. Missing candles are reported, not
  guessed or interpolated.
- `--min-volume-x` is optional and requires volume on every opening-range bar
  and the trigger bar.

For a level practice check:

```bash
python3 nepse_tools/cli.py entry check NABIL \
  --candles /path/to/NABIL-5m.csv --interval 5m \
  --as-of "2026-11-13 11:20" --setup level --level 500
```

## Time and data

Timestamps label candle starts. A timestamp without an offset is interpreted
as Nepal time (UTC+05:45); an explicit offset is converted to NPT. `--as-of`
is also Nepal local time. One CSV must contain one session and either 1m or 5m
bars. The assumed regular session is 11:00-15:00 NPT; override it with
`--session-open` and `--session-close` if needed, and verify the exchange's
current hours and holiday calendar yourself.

The helper never fetches NEPSE quotes. If `--as-of` is omitted, it uses the
last supplied candle's close time and labels that replay assumption. The data
source, time assumption, and safety note are included in the optional JSON.

## Beginner handholding

Ask for the symbol, date, interval, candle CSV, and the time to replay if any
are missing. Explain each OHLC column. Mark the opening-range high and low on
the chart. Have the learner identify the candle's close, not only its high wick.
If the input is incomplete, pause and ask for the missing row rather than
inventing a price.

A result saying `PRACTICE CONDITION MET` means only that the chosen rule
matched the supplied data. It does not mean the user should buy. It does not
calculate position size, fees, tax, settlement, price limits, or broker rules.

## Workflow

After the learner has reviewed a completed trigger, `/nepse-exit` can calculate
a hypothetical plan from the entry JSON. The learner chooses a stop method or
a custom stop. Continue only if the user explicitly asks for each next practice
step. Never send NEPSE output into the U.S.-market exit, budget, risk, or broker
workflow.

## Safety

This is offline education. It does not know whether the candles are real,
complete, current, or from an authorized source. It does not verify holidays or
exchange hours. No order is placed. A stop is not guaranteed to fill. This is
not financial advice.
