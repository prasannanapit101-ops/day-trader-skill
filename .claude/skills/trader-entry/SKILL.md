---
name: trader-entry
description: >-
  Entry Timer. Watches a setup bar by bar and tells you the moment to get in.
  Reads free Yahoo 1-minute or 5-minute bars, builds the opening range (the
  first 15 minutes by default) and calls the entry on the first completed bar
  that CLOSES above the range high, or above a level you give it (like a
  20-day high from the scanner), with an optional volume check. Says waiting
  and how far, triggered with the time and the price, expired, or not open
  yet, and writes trader/entry.json for /trader-exit. Long side only. It never
  places an order. Use when the user says "tell me when to get in", "watch
  TSLA", "has it broken out", "did it break the opening range", "entry
  signal", "time my entry", "check my watchlist", or after /trader-scanner
  and /trader-news, before /trader-exit. For NEPSE practice, reads user-supplied
  1-minute or 5-minute OHLCV CSV in Nepal time, explains the setup in plain
  language, and never fetches live data or recommends a buy. Use when the user
  mentions NEPSE, Nepal stocks, or asks for beginner-friendly entry practice.
argument-hint: "[TICKER] [US or NEPSE] [setup] [chart or candle CSV]"
---

# trader-entry

The Entry Timer turns a setup into one moment: the bar that confirms it. For
U.S. tickers, it reads Yahoo 1-minute or 5-minute bars. For NEPSE practice, it
uses the separate offline CSV helper below; do not run the U.S. Yahoo/NYSE
entry logic on a NEPSE symbol. A price that pokes above a level in the middle
of a bar is not a trigger. A bar that CLOSES above it is. It never buys
anything. Day trading loses most people money, and a clean signal does not
change that.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/entry.py" check TSLA                  # 15-minute opening range, 5-minute bars
python3 "${CLAUDE_SKILL_DIR}/entry.py" check TSLA --write          # also save trader/entry.json
python3 "${CLAUDE_SKILL_DIR}/entry.py" check TSLA --setup level --level 371.20
python3 "${CLAUDE_SKILL_DIR}/entry.py" check TSLA --interval 1m --min-volume-x 1.5
python3 "${CLAUDE_SKILL_DIR}/entry.py" watch TSLA --until 15:30    # one line per closed bar, stops on the trigger
python3 "${CLAUDE_SKILL_DIR}/entry.py" watchlist                   # every hit in trader/watchlist.json
```

Other flags for U.S. symbols: `--or-minutes N` (default 15), `--json`,
`--offline FILE` (a saved Yahoo chart JSON, `.json` or `.json.gz`, or a folder
of `<TICKER>.json`), `--now "2026-10-19 10:15"` (New York time) to replay a
day. `watch` with `--now` or `--offline` runs on a simulated clock and
replays the day bar by bar without waiting.

## NEPSE practice mode (offline only)

Do not run `entry.py` for NEPSE: that path assumes U.S. Yahoo data and NYSE
time. `nepse_practice.py` is a separate learning helper. It uses only a
one-session OHLCV CSV you provide; it does not fetch live NEPSE prices or
orders. It does not model fees, settlement, price limits, or broker rules.
Its default session is 11:00-15:00 NPT and its opening range is the first 15
minutes of regular trading (11:00-11:15). Check NEPSE's current
[market page](https://www.nepalstock.com/todaysprice) and holiday calendar
before using real-session data; the helper does not maintain that calendar.
Session hours can be overridden with
`--session-open` and `--session-close`.

```bash
# Synthetic demo only; this is not a real NEPSE quote.
python3 "${CLAUDE_SKILL_DIR}/nepse_practice.py" check DEMO \
    --candles tests/fixtures/trader-entry/NEPSE-DEMO-5m.csv \
    --interval 5m --as-of "2026-11-13 11:20"

# Replace the path and symbol with your own chart export.
python3 "${CLAUDE_SKILL_DIR}/nepse_practice.py" check NABIL \
    --candles /path/to/NABIL-5m.csv --interval 5m \
    --as-of "2026-11-13 11:20" --setup orb
```

CSV headers are `timestamp,open,high,low,close`; `volume` is optional unless
you set `--min-volume-x`. `timestamp` is the start of each candle. Timestamps
without an offset are read as Nepal time (UTC+05:45). `--as-of` is also Nepal
local time. Use one trading session per
file and 1-minute or 5-minute candles. Only completed candles count; missing
bars inside the opening range or before the check time are reported as
incomplete instead of guessed. If you omit `--as-of`, the tool replays through
the last CSV candle's close and says the data is offline.

For a beginner, ask one question at a time. If they do not have a CSV, first
explain the needed columns and ask them to paste a few candles or export a
chart; never invent prices. Explain the range high/low, the difference between
a wick and a closed candle, and what data is missing. The output is a practice
condition, not a buy instruction. Do not pass a NEPSE result to the U.S.-only
`trader-exit`, `trader-budget`, `trader-risk`, or `trader-broker` tools.

## What it reads and writes

| file/source | what |
| --- | --- |
| `trader/watchlist.json` | the U.S. scanner's hits (`hits[].symbol`), for `watchlist` |
| `trader/config.json` | U.S. entry cutoffs in New York time. Optional |
| Yahoo chart API | U.S. bars, `range=1d&interval=5m` (or `1m`): free, unofficial, can lag |
| `trader/entry.json` | U.S. result with `check --write`, or when `watch` triggers |
| User-supplied NEPSE CSV | one session of 1m/5m OHLCV candles; no live fetch |
| `trader/nepse-entry.json` | NEPSE practice result with `nepse_practice.py --write` |

## The rule

- **Opening range (orb).** The high and low of the first 15 minutes: the
  9:30, 9:35 and 9:40 five-minute bars, or fifteen 1-minute bars. The level
  to beat is the range high.
- **Level.** A price you give, like a 20-day high from `/trader-scanner`.
- **The trigger** is the first completed bar after the range that CLOSES
  above the level. A wick above is not a trigger. A close exactly at the
  level is not above it.
- **The time** is that bar's close time (the 10:10 bar closes at 10:15 AM).
  The price is its close, to the cent.
- **Only closed bars count.** A bar is closed when the clock passes its start
  plus 5 (or 1) minutes and Yahoo has caught up to that moment (it waits a
  minute at most). Yahoo's live tick, like 10:49:45, is never a bar.
- **Volume, if you want it.** `--min-volume-x 1.5` also needs the trigger
  bar's volume at 1.5 times the range bars' average. The 9:30 bar holds the
  opening auction, so 1.0 is already strict.
- **Time limits.** No entries before 9:45 or after 15:30 (config). On a 1:00
  p.m. early close the cutoff moves up with the close, to 12:30.
- **What it says.** Waiting (and how far the last close is from the level),
  triggered, expired, or no data. Before 9:30: not open yet. Before 9:45: the
  range is still forming. Weekends and NYSE holidays: the market is closed.

## Steps

1. Identify the market first. For U.S. symbols, get the ticker, use the U.S.
   scanner/news path when useful, and run `entry.py check SYMBOL`. For NEPSE,
   do not use Yahoo, the U.S. scanner, or the NYSE clock.
2. For NEPSE practice, ask for the symbol and one session of 1m/5m OHLCV CSV
   (or a chart export the user can turn into that CSV). Explain the expected
   columns and Nepal-time timestamps if they need help. Never fill in missing
   prices from guesses.
3. Run `nepse_practice.py check SYMBOL --candles FILE --interval 5m --as-of
   "YYYY-MM-DD HH:MM"`. Explain whether the range is still forming, the data
   is incomplete, or a completed close met the practice rule. Point out the
   exact candle and show how its close compares with the level. For U.S.
   symbols only, `entry.py watch` can run in the background or `entry.py check`
   can run on a `/loop`; do not use either live-watching path for NEPSE.
4. For a beginner, explain one idea at a time: opening-range high/low, why a
   wick is not a close, and what the result cannot tell them. Ask them to mark
   the level on their own chart and describe what would invalidate the setup.
5. For U.S. results only, hand off to `/trader-exit` for a stop and target.
   Do not hand a NEPSE result to the U.S.-only exit, budget, risk, or broker
   tools. Nothing was bought or placed by either entry path.

## Example: the reel

TSLA, Monday 2026-10-19, 5-minute bars. The opening range is 354.47 to
362.18. At 10:12 the 10:10 bar is still open, so it waits:

```
WAITING  last close $361.68 (10:05 bar), $0.50 under the range high $362.18 (-0.14%).
The 10:10 bar is still forming ($364.18 so far, closes 10:15 AM); it does not count until it closes.
```

At 10:15 the bar has closed:

```
TSLA  Mon 2026-10-19 10:15 ET  opening-range breakout (15-minute range) on 5-minute bars (Yahoo, free, can lag)
Opening range 9:30-9:45: high $362.18, low $354.47 (3 of 3 bars).
TRIGGERED 10:15 AM at $364.18: the 10:10 bar (bar 8) closed above the range high $362.18 (+0.55%).
This is the moment to get in, if you take the trade. Nothing was placed.
Next: set the stop and target BEFORE you buy: /trader-exit (exit.py plan --from trader/entry.json).
```

With `--min-volume-x 1` the 10:10 bar is too thin (0.60x the range's volume)
and the trigger moves to 10:35 AM at 365.75 (the 10:30 bar, 7.98x).

## Rules

- For U.S. symbols, use Yahoo 1-minute or 5-minute bars; they are unofficial
  and can lag. For NEPSE, use only the candles the user supplies, and label
  the result offline practice rather than live data.
- A signal is information, not an order, and not a promise. Nothing here
  promises winning trades or money.
- Long side only. v2 plans longs only. If the user wants a short, say that.
- One trigger per setup per day: the first close above. Later closes do not
  reset it.
- Never call an entry early because a bar looks like it will close above.

## What it never does

It never places an order, never sizes a position, never sets the stop (that
is `/trader-exit`), never moves the level after the fact, and never counts a
bar that has not closed. It never runs `/trader-broker` from a background
watch: nobody is there to say yes.

## Safety

- Education and tooling, not financial advice. A PASS is a rules check, not a recommendation.
- Paper trading by default (`"paper": true`). Going live is the user's own decision, in their own config.
- Nothing in this pack places an order except trader-broker, and only when all three hold: trader-risk
  passed that exact order today, the user typed an explicit yes for that one order in the chat, and the
  user clicked Allow once on Claude's own card because the order tool is set to "Needs approval"
  (Customize > Connectors > tool permissions). Never set an order tool to "Always allow".
- No options, margin, short selling or leverage unless the config allows it and the user confirms.
- Broker keys live in environment variables or the Claude Desktop config, never in the chat.
