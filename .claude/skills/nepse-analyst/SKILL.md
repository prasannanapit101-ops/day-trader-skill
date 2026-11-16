---
name: nepse-analyst
description: >-
  NEPSE Company Analyst. Compares financial metrics supplied by the learner in
  CSV across reporting periods, including revenue, operating profit, net income
  and EPS when present. Preserves the supplied period order and labels NPR
  units, does not fetch filings or fill missing values, and makes no forecast
  or valuation. Use when a learner provides a Nepal company report or table.
argument-hint: "[financial metrics CSV]"
---

# NEPSE Company Analyst

This tool compares figures already collected by the learner. It does not query
company filings, NEPSE, SEBON, investor-relations pages, or a live financial
database. Keep the original report open to verify figures and context.

It keeps the original earnings analyst's period-over-period review, adapted
to supplied NEPSE figures instead of fetched SEC/XBRL filings.

```bash
python3 nepse_tools/cli.py analyst \
  --file nepse_tools/examples/financials.example.csv
```

The example file is fictional. For the learner's own data, use columns such
as `period,revenue_npr,operating_profit_npr,net_income_npr,eps_npr`. Put the
oldest period first and newest period last. Values are compared in the order
they appear; no automatic period sorting is performed.

## Review steps

1. Confirm the company, period labels, units, and whether statements are
   consolidated or standalone.
2. Ask whether the values are NPR, NPR thousands, or NPR millions. The CLI
   cannot infer scale; it prints the numeric values as supplied.
3. Compare the latest row to the previous supplied row where both values are
   numeric. A zero, missing, or invalid earlier value makes percentage change
   unavailable.
4. Explain one metric at a time. Revenue is not profit. EPS is an amount per
   share. A business can report higher revenue and lower net income.
5. Keep one-off gains, losses, restatements and reporting changes separate
   from recurring operations. These require reading the original report.

## Beginner handholding

- Revenue is income from the business before costs.
- Operating profit is after operating expenses, before some financing and tax
  items.
- Net income includes costs, interest, tax and other items.
- EPS is earnings per share, not the market price of a share.

Explain the terms only as needed. Do not infer a company's quality, cheapness,
future growth, or share-price direction from this small table. Arithmetic
percentage changes can mislead when the previous number is negative or close
to zero.

## Limitations

No XBRL filing parser, OCR, transcript reader, unit detection, earnings
calendar, peer comparison, multiples, cash-flow model, or forecast is included.
The tool does not fetch or validate data. Missing values remain missing.

## Safety

This is a plain-language summary of user-supplied figures, not a valuation or
investment opinion. Never call growth a buy signal. Do not fabricate missing
financials or claim a filing was checked. No trade is created or placed. This
is education, not financial advice.
