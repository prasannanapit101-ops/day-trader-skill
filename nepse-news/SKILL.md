---
name: nepse-news
description: >-
  NEPSE News Monitor. Organizes Nepal company headlines, links and exchange
  notices supplied by the user into simple keyword categories while keeping
  the original date and source visible. It does not fetch current news, verify
  a publisher, or infer price impact. Use when a learner shares a news CSV or
  JSON and wants help understanding what a NEPSE-company headline says.
argument-hint: "[news CSV or JSON] [optional symbol]"
---

# NEPSE News Monitor

This command tags headlines the learner already has. It does not download
news, check a paywall, verify a notice, or predict how a ticker will move.
Keyword tags are filing-navigation hints, not sentiment analysis.

It keeps the original news monitor's company-by-company headline review, but
categorizes only supplied records and makes no live-feed or price-impact claim.

```bash
python3 nepse_tools/cli.py news \
  --file nepse_tools/examples/news.example.csv

python3 nepse_tools/cli.py news --file /path/to/headlines.csv --symbol NABIL
```

The input may be CSV or JSON. Useful fields are `timestamp` or `date`,
`symbol`, `headline`, `source`, and `url`. The example in the repository is
fictional. Its `example.invalid` link is deliberately not a real source.

## Steps

1. Ask which company and date range the learner cares about.
2. Request the original link or the headline file if it was not provided.
3. Keep the exact headline, date, publisher, and URL beside any explanation.
4. Explain a matching keyword tag only as a way to organize the headline:
   results, dividend/bonus, rights issue, AGM/book closure, merger, or notice.
5. Separate what the source states from what it could mean. Do not guess
   whether the event is positive or negative for a share price.
6. Encourage the learner to open the original NEPSE or company notice for
   dates, amounts, eligibility rules, and conditions.

## Beginner handholding

Explain unfamiliar terms one at a time. EPS means earnings per share. A book
closure date can affect who is eligible for a declared corporate benefit, but
exact rules depend on the official notice. A rights issue is an offer of
additional shares to eligible holders, not a guaranteed gain. An AGM is a
company meeting, not an automatic signal to trade.

If no file is available, say the command cannot check today's news. Ask the
user to share a link or headline. Never invent a story, a date, an exchange
announcement, or a source.

## Output and limitations

`--symbol` filters records with a symbol field, or headlines that mention the
ticker when the field is absent. `--limit` caps how many matching records are
shown. Rows without a headline are skipped. No previous-run state is stored,
so the same supplied headlines can appear again on a later run.

The output does not assess source credibility or read the linked article. A
headline can be inaccurate, stale, incomplete, or written to attract clicks.
A company announcement and a news summary are not interchangeable.

## Safety

A headline alone is not a reason to buy, sell, or hold. Do not pass keyword
tags to the NEPSE risk or ticket tools as if they were verified facts. No live
news was fetched and no notification or order was sent. This is education,
not financial advice.
