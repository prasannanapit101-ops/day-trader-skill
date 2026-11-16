---
name: nepse-alerts
description: >-
  NEPSE Price Alert Checker. Performs a one-time above/below comparison between
  alert levels and the latest timestamped quote rows a learner supplies in CSV.
  It does not poll, send reminders, watch a stop in the background, fetch live
  prices, or place orders. Use when a user shares quote data and wants a simple
  practice check of a price level.
argument-hint: "[alert rules JSON] [timestamped prices CSV]"
---

# NEPSE Price Alert Checker

This tool compares supplied price rows with supplied `above` or `below` levels
once. It is not a background watcher, notification service, or live quote feed.

It preserves the original alerts skill's threshold-check role, but replaces
continuous quote/calendar polling with a single comparison of supplied rows.

```bash
python3 nepse_tools/cli.py alerts \
  --rules nepse_tools/examples/alerts.example.json \
  --prices nepse_tools/examples/prices.example.csv
```

Rules JSON contains an `alerts` list. Each item has a `symbol` and exactly one
of `above` or `below`, with the threshold in NPR. Price CSV needs
`timestamp,symbol,price`. Naive timestamps are read as Nepal local time.

## How to use it

1. Ask where the quote came from and when it was recorded.
2. Read the quote date/time aloud before reporting whether the threshold was
   crossed.
3. Explain that a threshold comparison says nothing about the next price move.
4. If no supplied quote matches a rule's symbol, report `NO DATA`, not a guess.
5. If the quote is old, stale, delayed, or synthetic, say so clearly.

The latest supplied timestamp for each symbol is used. If multiple rules share
a symbol, the same latest quote is compared against each threshold. The example
CSV contains a synthetic `DEMO` price, not a live share quote.

## Limitations

The command does not keep state, ring once, send push notifications, run on a
schedule, monitor stop orders, or call a broker. A user must rerun it with new
CSV data for another comparison. It does not know quote freshness or source
quality and does not fetch any missing values.

For a beginner, show the simple comparison (`price >= above` or `price <=
below`) and let them decide what a practice alert means. Never state that a
crossed level is a recommendation or that a price will continue in that
direction.

## When the quote is missing

A `NO DATA` row means there was no matching symbol in the supplied price file.
It does not mean the share did not trade. Ask the learner for a quote row with
a timestamp and source; do not fill a blank with a remembered or guessed price.
The tool also does not check whether a quote is from today's session.

## Safety

An alert is information, never an order. The command will not sell shares or
close a position. Do not imply that it is monitoring a stop in the background.
No network access, notification, or order execution is supported. This is
practice, not financial advice.
