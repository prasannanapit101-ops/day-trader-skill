# The Day Trader skill

22 Claude skills: the original 11 U.S. day-trading skills plus 11 offline
NEPSE practice skills for user-supplied Nepal-market data.

Free, MIT, no signup, no API key. U.S. tools read public sources such as Yahoo
Finance charts, Nasdaq Trader's symbol lists, SEC EDGAR and the House Clerk.
NEPSE tools are offline-first: they do not fetch quotes, exchange notices, or
company filings, and they have no TMS or broker connection.

One scans thousands of charts for setups. Another tracks breaking news on
every stock you watch. One watches a setup bar by bar and tells you the moment
to get in, and another sets your stop and your target before you do. And the
craziest one is the Time Machine: before you risk a dollar, it replays the
rest of the session 10,000 times from the stock's own recent bars, plus every
past day the same setup fired, and tells you the honest odds.

The U.S. broker workflow requires risk approval and your explicit yes before
an order is sent; it defaults to paper trading. NEPSE ticket generation is
paper-only and cannot submit any order.

> **Looking for the original Trader skill?** Copy an investor's 13F, the
> stock screener, tax lots and rebalancing live in
> [github.com/Jakeschincariol/trader-skill](https://github.com/Jakeschincariol/trader-skill).
> This repo is its day-trading sequel: the Trader skill v2.

## Install

Paste this into Claude:

```
https://github.com/Jakeschincariol/day-trader-skill

install skill
```

Or as a plugin, in Claude Code:

```
/plugin marketplace add Jakeschincariol/day-trader-skill
/plugin install day-trader-skill@day-trader-skill
```

Claude Code namespaces plugin skills, so installed as a plugin they show up as
`/day-trader-skill:trader-scanner` and so on. Copy the folders instead if you want
plain `/trader-scanner`:

```bash
git clone https://github.com/Jakeschincariol/day-trader-skill.git
cp -r day-trader-skill/trader-* day-trader-skill/nepse-* ~/.claude/skills/
```

### Use the skills from this fork in Claude Code

This fork includes all 22 skills under `.claude/skills/`. To access them, open
this repository's root directory in Claude Code. From a terminal:

```bash
cd /path/to/day-trader-skill
claude
```

The original commands are `/trader-scanner`, `/trader-news`, `/trader-entry`,
`/trader-exit`, `/trader-timemachine`, `/trader-risk`, `/trader-budget`,
`/trader-broker`, `/trader-alerts`, `/trader-analyst` and `/trader-pelosi`.
The NEPSE commands are `/nepse-scanner`, `/nepse-news`, `/nepse-entry`,
`/nepse-exit`, `/nepse-timemachine`, `/nepse-risk`, `/nepse-budget`,
`/nepse-broker`, `/nepse-alerts`, `/nepse-analyst` and `/nepse-disclosures`.
No extra plugin installation or copying is needed in this repository. These
commands are scoped to this checkout; to use the NEPSE commands in another
project, copy the matching `nepse-*` skill folders into its `.claude/skills/`,
then copy `nepse_tools/` and `trader-entry/nepse_practice.py` into matching
paths at that project's root. Run the CLI from that root. If Claude Code was
already open, reopen the project or restart the session. No
Claude Code at all? Read a `SKILL.md` in a chat, but Python commands still need
the repository and its local files.

The tools need Python 3.8 or newer. Nothing to pip install. The SEC tools
(news filings, the analyst) ask you to identify yourself: put your name and
email in `trader/config.json` (`"sec_user_agent": "Your Name you@example.com"`)
or in the `SEC_USER_AGENT` environment variable.

## The original U.S. eleven

| command | job | what it does |
| --- | --- | --- |
| `/trader-scanner` | Chart Scanner | Scans thousands of charts for setups: opening-range breakouts, flags, oversold bounces. |
| `/trader-news` | News Monitor | Tracks breaking news on every stock you watch and flags what moves it. |
| `/trader-entry` | Entry Timer | Watches U.S. setups and checks NEPSE practice setups from user-supplied candles. |
| `/trader-exit` | Exit Planner | Sets your stop and your target before you enter, so you know when to get out. |
| `/trader-timemachine` | Time Machine | Replays every possible outcome of a trade before you risk a dollar: 10,000 simulated sessions plus every past time the setup fired. |
| `/trader-risk` | Risk Manager | Checks every trade against your limits and stops anything over them. |
| `/trader-budget` | Budget Manager | Sizes every position to your budget and your max loss per trade. |
| `/trader-broker` | Order Executor | Sends approved orders to your broker, paper trading by default, never without your yes. |
| `/trader-alerts` | Price Alerts | Rings when a price, a stop or the opening bell hits. |
| `/trader-analyst` | Earnings Analyst | Reads earnings reports and sums up what changed. |
| `/trader-pelosi` | Pelosi Tracker | Reads Congress's stock-trade disclosures the minute they are filed. |

## The eleven NEPSE practice skills

| NEPSE command | Closest U.S. counterpart | adapted role |
| --- | --- | --- |
| `/nepse-scanner` | `/trader-scanner` | Screens learner-supplied per-symbol 1m/5m CSVs for opening-range practice; no exchange-wide live scan. |
| `/nepse-news` | `/trader-news` | Organizes supplied headlines and keeps dates, sources, and links visible; no feed. |
| `/nepse-entry` | `/trader-entry` | Checks completed candle closes against an opening range or user-supplied level. |
| `/nepse-exit` | `/trader-exit` | Calculates NPR risk and target from the user's selected stop method. |
| `/nepse-timemachine` | `/trader-timemachine` | Replays supplied history and seeded bootstrap paths from complete sessions. |
| `/nepse-risk` | `/trader-risk` | Checks hypothetical orders against the learner's own NPR limits. |
| `/nepse-budget` | `/trader-budget` | Calculates whole-share practice size and can write a proposed order JSON. |
| `/nepse-broker` | `/trader-broker` | Formats a paper ticket only; no broker or TMS connection. |
| `/nepse-alerts` | `/trader-alerts` | Makes a one-time comparison using quote rows supplied by the learner. |
| `/nepse-analyst` | `/trader-analyst` | Compares user-supplied company financials without fetching filings. |
| `/nepse-disclosures` | `/trader-pelosi` | Replaces political-trade tracking with supplied public company/exchange notices. |

## How to use it

The original U.S. workflow writes its state under `trader/` and hands results
between its skills. Keep that flow separate from NEPSE files:

```
U.S.:    scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker
         alerts while the U.S. trade is open; analyst / pelosi for research
NEPSE:   supplied candles -> nepse-scanner -> nepse-news -> nepse-entry
         -> nepse-exit -> nepse-timemachine -> nepse-budget -> nepse-risk
         -> nepse-broker (paper ticket only); supplied quotes -> nepse-alerts
         supplied records -> nepse-news / nepse-analyst / nepse-disclosures
```

The NEPSE tools are an offline learning set, not a mirror of the U.S. live-data
and broker integrations. They do not fetch NEPSE prices, company reports or
exchange notices, do not check the official trading calendar, and cannot
connect to TMS or submit orders. Each command uses only files the learner
provides. Do not pass NPR prices, plans, or orders to U.S.-market tools.

An example, the trade in the reel: Tesla, Monday October 19 2026, real data.

1. **`/trader-scanner`** at 10:15 AM ET: of the 231 charts in the reel's
   scan, 42 had closed above their 15-minute opening range. TSLA is one: range 354.47 to 362.18,
   the 10:10 candle closed at 364.18, 0.55 % over the top.
2. **`/trader-news`**: the morning's TSLA headlines, in New York time
   ("Tesla-SpaceX Merger Mania Strikes Wall Street Ahead of Earnings", 8:04,
   tagged earnings and deal). Tesla reports this week: a day trade is out
   before the close, so it is not exposed to the report.
3. **`/trader-entry`** watched TSLA bar by bar. At 10:12 it said waiting (the
   10:10 bar was still forming). At 10:15 it said triggered: the first
   5-minute close above the range, 364.18.
4. **`/trader-exit`** set the plan before the entry: stop at the range's
   midpoint, 358.32, so 5.86 a share at risk; target one times that risk,
   370.04; flat by 3:55 PM either way.
5. **`/trader-timemachine`** replayed the rest of the day 10,000 times, each
   5-minute candle drawn from TSLA's own candles at that time of day over the
   previous 59 sessions (seed 19, so anyone can repeat it): target first
   29.4 %, stop first 25.5 %, still open at the close 45.1 %. It also re-ran
   the same rule on those 59 real sessions: it fired 33 times, 13 hit the
   target, 15 the stop, 5 neither. Its verdict: close to a coin flip. That is
   the point of looking before you risk a dollar.
6. **`/trader-budget`** with a $5,000 account and a $50 max loss per trade:
   50 / 5.86 = 8 shares ($2,913.44). If the stop fills at 358.32, the loss is
   $46.88. It writes one bracket order: buy 8 TSLA, stop-loss 358.32,
   take-profit 370.04.
7. **`/trader-risk`** checks it against your limits: the max loss, the daily
   loss limit, trades per day, reward to risk, the entry window, position
   size and cash. PASS or BLOCK, with the reason.
8. **`/trader-broker`** shows you the ticket in plain words. You type yes for
   that exact order. Claude calls your brokerage connector (Alpaca's MCP
   server, paper account by default), and Claude's own "Allow once / Deny"
   card asks you one more time.
9. **`/trader-alerts`** rings on the stop, the target and at 3:55 PM to
   flatten whatever is still open.

## The tools

All tools use standard-library Python. The U.S. data tools read public
endpoints and are polite about it. The NEPSE CLI uses only learner-supplied
CSV/JSON and has no network or broker client.

```bash
python3 trader-scanner/scan.py universe                                # ~5,900 US stocks, Nasdaq Trader
python3 trader-scanner/scan.py daily                                   # pre-market setups, whole universe
python3 trader-scanner/scan.py orb --at 10:15                          # opening-range breakouts so far
python3 trader-news/news.py --tickers TSLA --hours 12                  # headlines, 8-Ks, today's move
python3 trader-entry/entry.py check TSLA --setup orb                   # U.S. entry check
python3 trader-entry/entry.py watch TSLA --every 30                    # U.S. bars, until a trigger
python3 trader-entry/nepse_practice.py check DEMO \
    --candles tests/fixtures/trader-entry/NEPSE-DEMO-5m.csv \
    --interval 5m --as-of "2026-11-13 11:20"                      # synthetic NEPSE demo, NPT
python3 trader-exit/exit.py plan --stop or-mid --target 1R --write     # -> trader/plan.json
python3 trader-timemachine/timemachine.py run --write                  # 10,000 replays + the history
python3 trader-budget/size.py --write                                  # -> trader/orders.json
python3 trader-risk/check.py                                           # PASS / BLOCK per order
python3 trader-broker/ticket.py show                                   # the tickets, READY or not
python3 trader-alerts/alerts.py add --from-plan                        # stop, target, flat by close
python3 trader-alerts/alerts.py check                                  # rings what hit, once
python3 trader-analyst/facts.py TSLA                                   # quarters, growth, EPS
python3 trader-pelosi/ptr.py index --member pelosi                     # her PTRs this year
```

## NEPSE practice workflow

Use the `/nepse-*` skills for a Nepal-market practice workflow. The regular
`trader-entry/entry.py` path uses U.S. Yahoo data and New York time; the separate
NEPSE helper reads only the candles you supply. Run the shared CLI from the
repository root:

```bash
# Optional: screen one-session per-symbol CSV files you provide.
python3 nepse_tools/cli.py scan --candles-dir /path/to/per-symbol-csvs \
  --as-of "2026-11-13 11:20" --interval 5m --or-minutes 15

# Check one symbol and write a reusable entry result.
python3 nepse_tools/cli.py entry check NABIL \
  --candles /path/to/NABIL-5m.csv --interval 5m \
  --as-of "2026-11-13 11:20" --write trader/nepse-entry.json

# Choose a practice stop method and save the plan.
python3 nepse_tools/cli.py exit --from-entry trader/nepse-entry.json \
  --stop-method or-mid --target-r 1 --write trader/nepse-plan.json

# Historical replay needs 20+ full prior sessions plus the plan-date entry bar.
python3 nepse_tools/cli.py timemachine --plan trader/nepse-plan.json \
  --candles /path/to/NABIL-multi-session-5m.csv --replays 10000 --seed 19

# Size a hypothetical order, then check it against your own limits.
python3 nepse_tools/cli.py budget --plan trader/nepse-plan.json \
  --capital 100000 --max-loss 1200 --write trader/nepse-orders.json
cp nepse_tools/config.example.json trader/nepse-config.json
# Edit every zero limit to your own numbers; the risk command rejects missing limits.
python3 nepse_tools/cli.py risk --orders trader/nepse-orders.json \
  --config trader/nepse-config.json --daily-loss 0 --trades-today 0

# This formats a paper ticket only. It does not send an order.
python3 nepse_tools/cli.py broker --order trader/nepse-orders.json
```

Other practice workflows use supplied records only:

```bash
python3 nepse_tools/cli.py news --file /path/to/headlines.csv --symbol NABIL
python3 nepse_tools/cli.py alerts --rules /path/to/alerts.json --prices /path/to/prices.csv
python3 nepse_tools/cli.py analyst --file /path/to/financials.csv
python3 nepse_tools/cli.py disclosures --file /path/to/notices.csv --symbol NABIL
```

CSV candles use `timestamp,open,high,low,close` and optional `volume`. Time
labels are candle starts; naive timestamps mean Nepal time (UTC+05:45). The
assumed session is 11:00-15:00 NPT, but this is only a configurable assumption,
not an official calendar. Use `--session-open` and `--session-close` when
needed and verify the current schedule and holidays against official NEPSE
announcements. These helpers do not model fees, tax, settlement, price limits,
liquidity, TMS rules, or broker requirements.

`nepse_tools/examples/candles/DEMO.csv` and the other `DEMO` records are
synthetic. They are not real companies, prices, quotes, headlines, filings or
notices. Scanner files contain one symbol and one session each. Time Machine
needs full multi-session history and checks that prior sessions are complete;
never make up candles to satisfy that requirement. Its seeded paths resample
user-provided history and are not a forecast.

For step-by-step help in Claude Code, start with `/nepse-entry` and say:

```text
I'm practicing NEPSE, not placing an order. Please explain one step at a time.
My symbol is [symbol], interval is 5m, and these are my candles:
[paste timestamp, open, high, low, close, and optional volume rows]
```

```bash
python3 -m unittest discover -s tests -v
```

The tests run offline. Most fixtures are cut from real data: TSLA's 5-minute
bars for the 60 days to October 19 2026, the 10:15 AM opening-range scan,
Yahoo's TSLA headlines that morning, the House Clerk's 2026 index, real PTR
text and real XBRL facts. The NEPSE entry fixture is explicitly synthetic and
exists only to test the practice calculation. The U.S. fixtures reproduce the
numbers in the example above.

## Fine print

**Not financial advice.** This is software that reads public data and does
arithmetic. It does not know your situation and it cannot see the future.
Most people who day trade lose money. You can lose money. Decide for
yourself, and talk to a licensed professional if you need advice.

**No trade goes through until you say yes.** Only `/trader-broker` can lead to
an order, and only after `/trader-risk` passes that exact order and you type
yes for it in the chat. Set your brokerage tool to "Needs approval" in Claude
(Customize, Connectors, tool permissions), never "Always allow", so Claude's
own "Allow once / Deny" card is a second check. No options, margin, short
selling or leverage unless you turn them on.

**Paper first.** `"paper": true` is the default in `config.example.json`, and
Alpaca's MCP server defaults to its paper account. Keys live in environment
variables, never in the chat.

**The U.S. Time Machine is a simulation, not a prediction.** It uses that
stock's recent 5-minute bars. The NEPSE Time Machine uses the history the user
supplies and seeded resampling; neither sees future events such as reports,
halts, gaps or headlines. Treat any replay as a reality check, never as a
promise.

**NEPSE is offline and paper-only.** The NEPSE tools do not fetch prices,
news, financial reports or notices, and they do not check the official market
calendar or connect to TMS. `/nepse-broker` only writes a ticket marked NOT
PLACED. Verify every input against authoritative sources yourself.

**A stop is a plan, not a guarantee.** In a fast market or across a gap, a
stop order can fill well past its price. The max loss shown is the loss at
the stop price.

**The data is free and unofficial.** Yahoo Finance's chart endpoint is not an
official API: it can lag, change or rate-limit you. The scanner and the entry
timer read 1-minute or 5-minute bars, not every tick. Check anything that
matters against your broker before you act on it.

**Day-trading rules.** FINRA removed the $25,000 pattern-day-trader minimum
on June 4, 2026 (Regulatory Notice 26-10), and brokers may phase the change
in until October 20, 2027, so yours may still apply the old rule. If it does,
set `"pdt_guard": true` and `/trader-risk` counts your day trades.

**Congress's trades are public, not inside information.** Members must disclose
trades over $1,000 within 45 days (the STOCK Act). The Pelosi skill reads those
public filings the minute they post.

**Taxes.** Day-trading gains are short-term gains, and frequent trading makes
wash sales likely. Nothing here is tax advice.

## Files

```
.claude/skills/    project-local copies of all 22 skills for Claude Code
trader-*/          original U.S. skills and tools (including the separate NEPSE entry helper)
nepse-*/           11 NEPSE workflow skill guides
nepse_tools/       offline CSV/JSON CLI, configs and synthetic examples
trader-entry/      U.S. entry.py plus offline nepse_practice.py
trader-exit/       U.S. exit planner
trader-timemachine/ U.S. simulation
trader-budget/     U.S. sizing tool and config examples
tests/             unittest suite + offline fixtures
```

MIT. Made by [Jake Schincariol](https://opusjake.ai).
