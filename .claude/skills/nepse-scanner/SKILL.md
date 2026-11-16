---
name: nepse-scanner
description: >-
  NEPSE Chart Scanner. Screens one-session 1-minute or 5-minute OHLCV CSVs
  supplied by the learner for opening-range breakout practice, reports each
  ticker's opening-range high and low and latest completed close, and explains
  missing or invalid data. It has no live quote feed and scans only the symbols
  represented by the supplied CSV files. Use when a user asks to scan their
  NEPSE watchlist and can provide candle exports.
argument-hint: "[folder of per-symbol candle CSVs] [as-of Nepal time]"
---

# NEPSE Scanner

This is an offline practice scanner. It screens only the per-symbol candle
files that the user provides. It is not a full-exchange live screener, does
not download symbols or prices, and does not decide what is worth buying.

This preserves the original scanner's role of surfacing rule-matching charts
for the learner to review, but replaces a U.S. universe and live chart feed
with NEPSE candles supplied by the learner.

Run from the repository root:

```bash
python3 nepse_tools/cli.py scan \
  --candles-dir /path/to/per-symbol-csvs \
  --as-of "2026-11-13 11:20" --interval 5m --or-minutes 15
```

The folder needs one CSV per symbol for the same trading session. For example,
`NABIL.csv` is labelled `NABIL`, and `GBIME.csv` is labelled `GBIME`. Required
columns are `timestamp,open,high,low,close`; `volume` is optional unless you
request `--min-volume-x 1.5`.

## What the scan does

- Reads each file separately and checks it with the NEPSE entry practice rule.
- Builds the opening range from the first `--or-minutes` of the assumed
  session (15 minutes by default).
- Uses completed candle closes, not a wick, for an opening-range breakout.
- Prints the range high and low, latest completed close, status, and reason.
- Flags files that are malformed, have missing required bars, or are for a
  different date from `--as-of`.

The scanner does not identify a symbol universe, run daily-price setups, rank
stocks by liquidity, or fetch data. Those functions require data sources that
are not implemented here. Do not claim that an unprovided symbol was scanned.

## Session and time handling

The current default is an assumption of 11:00 to 15:00 Nepal time, not a
verified current exchange schedule. Confirm the session and holiday calendar
before using real-session data. Override the assumed hours when necessary:

```bash
python3 nepse_tools/cli.py scan --candles-dir /path/to/csvs \
  --as-of "2026-11-13 11:20" --interval 1m \
  --session-open 11:00 --session-close 15:00
```

Timestamps label candle starts. A timestamp without an offset is interpreted
as Nepal time (UTC+05:45). `--as-of` is also Nepal local time. Use one session
per symbol file; the entry helper reports an error for multiple dates.

## Beginner handholding

If the user has no data yet, do not pretend to run a scan. Ask them to export
or paste one symbol's 1m/5m candles and explain the five CSV columns. Begin
with a single ticker and a single session. Explain the difference between the
high/low wick and the completed close, then show the range on the supplied
chart. Tell the learner when a bar is missing instead of filling it in.

## How to read the result

`triggered` means the supplied data matched the rule; it is a practice
condition, not a buy signal. `waiting` means the rule did not qualify yet.
`forming` means the assumed opening range has not completed. `incomplete`
means a required bar is absent. A scan of synthetic or stale data says nothing
about the current market.

## Safety

The scan does not model fees, tax, liquidity, settlement, price limits, broker
rules, announcements, or halts. It cannot see whether a quote is live or delayed.
Do not pass a NEPSE result to a U.S.-market skill. This is practice, not
financial advice; no order was created or sent.
