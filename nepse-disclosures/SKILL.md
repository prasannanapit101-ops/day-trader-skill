---
name: nepse-disclosures
description: >-
  NEPSE Corporate Disclosures. Organizes public NEPSE or company notices
  supplied by the learner, including results, dividends, rights issues, AGMs,
  book closures, mergers and trading notices, while preserving dates and
  sources. It does not scrape filings, track legislators, or infer price
  impact. Use when a learner shares a notice CSV/JSON and asks what it says.
argument-hint: "[public notice CSV or JSON] [optional symbol]"
---

# NEPSE Corporate Disclosures

This is the Nepal-market counterpart to a U.S.-specific political-trade
tracker. It organizes only public company or exchange notices the learner
provides. It does not assume a Nepal equivalent of a U.S. congressional PTR
feed and does not track private or insider trades.

```bash
python3 nepse_tools/cli.py disclosures \
  --file nepse_tools/examples/disclosures.example.csv --symbol DEMO
```

Input may be CSV or JSON. Useful fields are `date`, `symbol`, `type`,
`headline`, `source`, and `url`. The bundled example is fictional; its
`example.invalid` address is not a real disclosure source.

## Review steps

1. Identify the company and notice date.
2. Keep the exact title, source, URL and notice type visible.
3. Explain the keyword category as an index, not a conclusion about whether
   the notice is good or bad for shareholders.
4. Ask the learner to verify the full official NEPSE or company notice.
5. For a corporate action, confirm the actual amount, dates, eligibility,
   conditions and any changes in the original notice.

## Plain-language terms

A dividend is a distribution declared by a company; its amount and eligibility
come from the official notice. A bonus share is an additional share allotment
under stated terms. A rights issue offers eligible holders an opportunity to
subscribe for shares. Book closure is a date-related process used to identify
eligible holders. An AGM is a shareholder meeting. A trading halt is not a
recommendation or an invitation to trade elsewhere.

These explanations are general. They do not replace the official filing or
Nepal-specific professional advice. Ask for the notice when the exact terms
matter. Do not infer that an announcement guarantees a price move.

## Limitations

The tool does not scrape NEPSE, validate URLs, monitor updates, read scanned
PDFs, determine legal eligibility, or detect unreported insider transactions.
It performs no identity or political-trade tracking. If no supplied records
match the requested symbol, say that the command did not search for more data.

## Safety

Use public sources and verify the original notice. Do not claim that a person
traded a share without reliable public evidence. Never treat a disclosure or
keyword tag as a buy/sell signal. No live feed or order function is included.
This is education, not financial advice.
