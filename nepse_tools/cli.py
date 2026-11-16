#!/usr/bin/env python3
"""Offline-first companion tools for the NEPSE learning skill pack.

All market observations and company records are supplied by the user as CSV or
JSON. This module has no live-data client, no calendar feed, and no broker or
TMS connection. It is practice software, not a source of trading advice.
"""

import argparse
import csv
import datetime
import glob
import importlib.util
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile

NPT = datetime.timezone(datetime.timedelta(hours=5, minutes=45))
SESSION_OPEN = datetime.time(11, 0)   # Assumption only; not an exchange calendar.
SESSION_CLOSE = datetime.time(15, 0)  # Verify current NEPSE hours before use.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERVALS = {"1m": 1, "5m": 5}


class NepseError(Exception):
    """Expected input or practice-rule error shown without a traceback."""


def parse_npt(value, field="timestamp"):
    """Parse a timestamp, interpreting naive times as Nepal time (UTC+05:45)."""
    value = str(value or "").strip()
    if value.upper().endswith(" NPT"):
        value = value[:-4].strip()
    if not value:
        raise NepseError("%s is blank" % field)
    try:
        dt = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise NepseError("%s must look like 2026-11-13 11:15 in Nepal time" % field)
    if dt.tzinfo is not None:
        dt = dt.astimezone(NPT).replace(tzinfo=None)
    return dt


def _clock(value, field):
    value = str(value or "").strip()
    if not re.match(r"^(?:[01]?\d|2[0-3]):[0-5]\d$", value):
        raise NepseError("%s must be HH:MM, for example 11:00" % field)
    try:
        return datetime.datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise NepseError("%s must be HH:MM, for example 11:00" % field)


def _session(open_value, close_value, interval_minutes=None):
    session_open = _clock(open_value, "--session-open") if isinstance(open_value, str) else open_value
    session_close = _clock(close_value, "--session-close") if isinstance(close_value, str) else close_value
    if not isinstance(session_open, datetime.time) or not isinstance(session_close, datetime.time):
        raise NepseError("session boundaries must be clock times")
    if session_close <= session_open:
        raise NepseError("--session-close must be after --session-open")
    duration = (session_close.hour * 60 + session_close.minute) - (session_open.hour * 60 + session_open.minute)
    if interval_minutes is not None:
        if not isinstance(interval_minutes, int) or interval_minutes <= 0:
            raise NepseError("candle interval must be a positive number of minutes")
        if duration % interval_minutes:
            raise NepseError("session length must be a multiple of the candle interval")
    return session_open, session_close, duration


def _number(value, field, row_number=None, optional=False):
    location = "row %s " % row_number if row_number is not None else ""
    if isinstance(value, bool):
        raise NepseError("%sis an invalid %s: booleans are not numbers" % (location, field))
    if value is None or str(value).strip() == "":
        if optional:
            return None
        raise NepseError("%sis missing %s" % (location, field))
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise NepseError("%shas an invalid %s: %r" % (location, field, value))
    if not math.isfinite(number):
        raise NepseError("%shas a non-finite %s" % (location, field))
    return number


def _positive(value, field):
    number = _number(value, field)
    if number <= 0:
        raise NepseError("%s must be above zero" % field)
    return number


def _nonnegative(value, field):
    number = _number(value, field)
    if number < 0:
        raise NepseError("%s cannot be negative" % field)
    return number


def _whole_number(value, field, minimum=0):
    number = _number(value, field)
    if number != int(number) or number < minimum:
        qualifier = "at least %d" % minimum
        raise NepseError("%s must be a whole number %s" % (field, qualifier))
    return int(number)


def _symbol(value, field="symbol"):
    symbol = str(value or "").strip().upper()
    if not symbol or any(ord(char) < 33 or ord(char) == 127 for char in symbol):
        raise NepseError("%s must be a non-blank ticker without whitespace" % field)
    return symbol


def read_ohlcv(path, interval_minutes=5, session_open=SESSION_OPEN, session_close=SESSION_CLOSE):
    """Read bar-start OHLCV data; naive timestamps are NPT, outside bars drop."""
    if not os.path.isfile(path):
        raise NepseError("no candle CSV at %s" % path)
    session_open, session_close, _ = _session(session_open, session_close, interval_minutes)
    try:
        fh = open(path, "r", newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise NepseError("cannot open %s: %s" % (path, exc))
    with fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise NepseError("CSV needs a header row: timestamp,open,high,low,close[,volume]")
        columns = {name.strip().lower(): name for name in reader.fieldnames if name and name.strip()}
        time_col = columns.get("timestamp") or columns.get("datetime")
        if not time_col:
            raise NepseError("CSV needs a timestamp or datetime column")
        for field in ("open", "high", "low", "close"):
            if field not in columns:
                raise NepseError("CSV needs an %s column" % field)
        bars = []
        step = datetime.timedelta(minutes=interval_minutes)
        step_seconds = step.total_seconds()
        for row_number, row in enumerate(reader, 2):
            stamp = parse_npt(row.get(time_col), "row %d timestamp" % row_number)
            if not (session_open <= stamp.time() < session_close):
                continue
            start = datetime.datetime.combine(stamp.date(), stamp.time())
            open_dt = datetime.datetime.combine(stamp.date(), session_open)
            close_dt = datetime.datetime.combine(stamp.date(), session_close)
            elapsed = (start - open_dt).total_seconds()
            if elapsed % step_seconds != 0:
                raise NepseError("row %d timestamp is not aligned to the %d-minute grid from %s" % (
                    row_number, interval_minutes, session_open.strftime("%H:%M")))
            if start + step > close_dt:
                continue
            o = _number(row.get(columns["open"]), "open", row_number)
            h = _number(row.get(columns["high"]), "high", row_number)
            low = _number(row.get(columns["low"]), "low", row_number)
            c = _number(row.get(columns["close"]), "close", row_number)
            volume = _number(row.get(columns["volume"]), "volume", row_number, optional=True) \
                if "volume" in columns else None
            if min(o, h, low, c) <= 0 or h < max(o, c, low) or low > min(o, c, h):
                raise NepseError("row %d has inconsistent OHLC values" % row_number)
            if volume is not None and volume < 0:
                raise NepseError("row %d has negative volume" % row_number)
            bars.append({"start": start, "open": o, "high": h, "low": low,
                         "close": c, "volume": volume})
    bars.sort(key=lambda bar: bar["start"])
    if not bars:
        raise NepseError("no candles inside the assumed %s-%s NPT session" % (
            session_open.strftime("%H:%M"), session_close.strftime("%H:%M")))
    starts = [bar["start"] for bar in bars]
    if len(starts) != len(set(starts)):
        raise NepseError("CSV has duplicate candle timestamps")
    return bars


def _normalise_record(record):
    return {str(key).strip().lower(): value for key, value in record.items() if key is not None}


def read_records(path):
    """Read a CSV/JSON list of object-like records and normalise key casing."""
    if not os.path.isfile(path):
        raise NepseError("no input file at %s" % path)
    if path.lower().endswith(".json"):
        data = read_json(path)
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            data = _normalise_record(data)
            records = None
            for key in ("items", "records", "orders", "alerts", "data"):
                if isinstance(data.get(key), list):
                    records = data[key]
                    break
            if records is None:
                records = [data]
        else:
            raise NepseError("JSON input must be an object or a list of objects")
        if not all(isinstance(record, dict) for record in records):
            raise NepseError("JSON input list must contain objects only")
        return [_normalise_record(record) for record in records]
    try:
        with open(path, "r", newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                raise NepseError("CSV input needs a header row")
            return [_normalise_record(record) for record in reader]
    except (OSError, UnicodeError) as exc:
        raise NepseError("cannot read CSV %s: %s" % (path, exc))


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError, UnicodeError) as exc:
        raise NepseError("cannot read JSON %s: %s" % (path, exc))


def write_json(path, value):
    parent = os.path.dirname(os.path.abspath(path))
    try:
        os.makedirs(parent, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix=".nepse-", suffix=".tmp", dir=parent)
    except OSError as exc:
        raise NepseError("cannot prepare JSON output %s: %s" % (path, exc))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh, indent=2, sort_keys=True, allow_nan=False)
            fh.write("\n")
        os.replace(temp_path, path)
    except (OSError, TypeError, ValueError) as exc:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise NepseError("cannot write JSON %s: %s" % (path, exc))


def _entry_module():
    path = os.path.join(ROOT, "trader-entry", "nepse_practice.py")
    spec = importlib.util.spec_from_file_location("nepse_entry_practice", path)
    if spec is None or spec.loader is None:
        raise NepseError("cannot load the NEPSE entry practice helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command_entry(args):
    script = os.path.join(ROOT, "trader-entry", "nepse_practice.py")
    try:
        return subprocess.run([sys.executable, script] + args.args, check=False).returncode
    except OSError as exc:
        raise NepseError("cannot start the NEPSE entry helper: %s" % exc)


def command_scan(args):
    entry = _entry_module()
    try:
        as_of = entry.parse_timestamp(args.as_of, "--as-of")
    except entry.PracticeError as exc:
        raise NepseError(str(exc))
    interval_minutes = INTERVALS[args.interval]
    session_open, session_close, _ = _session(args.session_open, args.session_close, interval_minutes)
    if args.or_minutes <= 0 or args.or_minutes % interval_minutes:
        raise NepseError("--or-minutes must be a positive multiple of --interval")
    if args.min_volume_x is not None and _positive(args.min_volume_x, "--min-volume-x") <= 0:
        raise NepseError("--min-volume-x must be above zero")
    files = sorted(glob.glob(os.path.join(args.candles_dir, "*.csv")))
    if not files:
        raise NepseError("no per-symbol CSV files found in %s" % args.candles_dir)
    print("NEPSE CSV SCAN | offline practice | as of %s NPT | %s bars | assumed %s-%s session" % (
        args.as_of, args.interval, session_open.strftime("%H:%M"), session_close.strftime("%H:%M")))
    print("SYMBOL     STATUS       OR HIGH      OR LOW       LAST CLOSE   NOTE")
    errors = 0
    for path in files:
        symbol = os.path.splitext(os.path.basename(path))[0].upper()
        try:
            bars, day = entry.read_candles(path, args.interval, session_open=session_open,
                                           session_close=session_close)
            result = entry.evaluate(symbol, bars, day, as_of, setup="orb", or_minutes=args.or_minutes,
                                    interval=args.interval, min_volume_x=args.min_volume_x,
                                    session_open=session_open, session_close=session_close)
            opening = result.get("opening_range") or {}
            last = result.get("last") or {}
            note = result.get("reason", "")
            print("%-10s %-12s %-12s %-12s %-12s %s" % (
                symbol, result["status"], _money(opening.get("high")), _money(opening.get("low")),
                _money(last.get("close")), note))
        except (entry.PracticeError, KeyError, TypeError, ValueError) as exc:
            errors += 1
            print("%-10s ERROR        -            -            -            %s" % (symbol, exc))
    print("Supplied-candle screen only. It did not fetch prices, verify the session calendar, or recommend a trade.")
    return 2 if errors == len(files) else 0


def _money(value):
    if value is None:
        return "-"
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "-"
    return "NPR %.2f" % value if math.isfinite(value) else "-"


NEWS_TAGS = (
    ("financial-results", ("financial result", "quarterly result", "net profit", "eps", "revenue")),
    ("dividend-or-bonus", ("dividend", "bonus share", "cash dividend")),
    ("rights-issue", ("right share", "rights issue", "right issue")),
    ("book-closure-or-agm", ("book closure", "agm", "annual general meeting")),
    ("merger-or-acquisition", ("merger", "acquisition", "acquire")),
    ("regulatory-or-trading-notice", ("sebon", "nepse notice", "suspension", "halt", "delist")),
)


def classify_text(text):
    lower = str(text or "").lower()
    tags = [tag for tag, words in NEWS_TAGS if any(word in lower for word in words)]
    return tags or ["unclassified"]


def command_news(args):
    if args.limit <= 0:
        raise NepseError("--limit must be a positive number")
    records = read_records(args.file)
    symbol = _symbol(args.symbol, "--symbol") if args.symbol else None
    matches = []
    for item in records:
        headline = str(item.get("headline") or item.get("title") or "").strip()
        if not headline:
            continue
        item_symbol = str(item.get("symbol") or item.get("ticker") or "").strip().upper()
        if symbol and item_symbol and item_symbol != symbol:
            continue
        if symbol and not item_symbol and symbol not in headline.upper():
            continue
        matches.append((item, headline))
    if not matches:
        print("No matching headlines in the supplied file. No live news was fetched.")
        return 1
    print("NEPSE NEWS REVIEW | supplied headlines only | keyword tags are not sentiment")
    for item, headline in matches[:args.limit]:
        stamp = item.get("timestamp") or item.get("date") or "date not supplied"
        item_symbol = item.get("symbol") or item.get("ticker") or (symbol or "market")
        source = item.get("source") or "source not supplied"
        url = item.get("url") or ""
        print("%s | %s | %s | %s" % (stamp, item_symbol, ", ".join(classify_text(headline)), headline))
        print("  Source: %s%s" % (source, (" | " + str(url)) if url else ""))
    if len(matches) > args.limit:
        print("Showing %d of %d matching supplied headlines." % (args.limit, len(matches)))
    print("Verify the original notice/article and its date before drawing conclusions.")
    return 0


def command_exit(args):
    entry_doc = None
    opening = None
    setup = "manual"
    date = args.date
    entry_time = args.entry_time
    entry_bar_start = None
    interval = args.interval
    or_minutes = args.or_minutes
    if args.from_entry:
        if args.entry is not None:
            raise NepseError("do not combine --from-entry with --entry; use the completed entry result as supplied")
        entry_doc = read_json(args.from_entry)
        if not isinstance(entry_doc, dict) or str(entry_doc.get("market", "")).upper() != "NEPSE":
            raise NepseError("--from-entry must be a NEPSE entry-result JSON file")
        if entry_doc.get("status") != "triggered" or not isinstance(entry_doc.get("trigger"), dict):
            raise NepseError("the supplied entry file has no completed practice trigger")
        doc_symbol = _symbol(entry_doc.get("symbol"))
        if args.symbol and _symbol(args.symbol) != doc_symbol:
            raise NepseError("the positional symbol does not match --from-entry")
        symbol = doc_symbol
        entry = _positive(entry_doc["trigger"].get("close"), "entry trigger close")
        opening = entry_doc.get("opening_range")
        setup = str(entry_doc.get("setup") or "orb").lower()
        date = entry_doc.get("date")
        entry_time = entry_doc["trigger"].get("time_npt")
        entry_bar_start = entry_doc["trigger"].get("bar_start_npt")
        interval = entry_doc.get("interval", interval)
        or_minutes = entry_doc.get("or_minutes", or_minutes)
    else:
        if not args.symbol:
            raise NepseError("give a symbol or use --from-entry PATH")
        symbol = _symbol(args.symbol)
        if args.entry is None:
            raise NepseError("--entry is required unless --from-entry is used")
        entry = _positive(args.entry, "--entry")
        setup = args.setup
    target_r = _positive(args.target_r, "--target-r")

    method = args.stop_method
    if args.stop is not None:
        if method not in (None, "custom"):
            raise NepseError("use either --stop with a price or --stop-method, not both")
        method = "custom"
    if method is None:
        method = "or-mid" if entry_doc and setup == "orb" else "custom"
    if method == "custom":
        if args.stop is None:
            raise NepseError("--stop PRICE is required for a custom stop")
        stop = _positive(args.stop, "--stop")
    else:
        if not isinstance(opening, dict) or opening.get("high") is None or opening.get("low") is None:
            raise NepseError("--stop-method %s needs the entry result's opening range" % method)
        range_high = _positive(opening.get("high"), "opening-range high")
        range_low = _positive(opening.get("low"), "opening-range low")
        if range_high <= range_low:
            raise NepseError("opening-range high must be above its low")
        stop = (range_high + range_low) / 2.0 if method == "or-mid" else range_low
    if stop >= entry:
        raise NepseError("long practice plans require entry above the user's stop")
    risk = entry - stop
    target = entry + risk * target_r
    if not math.isfinite(target):
        raise NepseError("calculated target is outside the supported numeric range")
    if date:
        try:
            date = datetime.date.fromisoformat(str(date)).isoformat()
        except ValueError:
            raise NepseError("--date must be YYYY-MM-DD")
    if entry_time:
        entry_clock = _clock(entry_time, "entry time")
        entry_time = entry_clock.strftime("%H:%M")
    plan = {"market": "NEPSE", "currency": "NPR", "symbol": symbol, "side": "BUY",
            "date": date, "setup": setup, "interval": interval,
            "entry": entry, "entry_time_npt": entry_time, "entry_bar_start_npt": entry_bar_start,
            "stop": stop, "target": round(target, 4), "risk_per_share": round(risk, 4),
            "target_r": target_r, "stop_method": method, "or_minutes": or_minutes,
            "opening_range": opening, "practice_only": True, "order_placed": False}
    print("NEPSE EXIT PLAN | %s | NPR | learning calculation only" % symbol)
    print("Entry assumption: %s | Stop: %s (%s)" % (
        _money(entry), _money(stop), "your supplied level" if method == "custom" else method))
    print("Risk per share: %s | Stop distance: %.2f%%" % (_money(risk), risk / entry * 100.0))
    print("At %.2fR, target level: %s | Gross reward per share: %s" % (
        target_r, _money(target), _money(target - entry)))
    print("This plan contains only the levels and rule you supplied or selected. Fees, settlement, slippage, price limits and broker rules are not included.")
    print("Nothing was placed. A stop is not a guaranteed fill price.")
    if args.write:
        write_json(args.write, plan)
        print("Wrote %s." % args.write)
    return 0


def _histories(path, interval_minutes, session_open=SESSION_OPEN, session_close=SESSION_CLOSE):
    bars = read_ohlcv(path, interval_minutes, session_open, session_close)
    sessions = {}
    for bar in bars:
        sessions.setdefault(bar["start"].date(), []).append(bar)
    return sessions


def _replay_plan(path, interval_arg=None):
    plan = read_json(path)
    if not isinstance(plan, dict) or str(plan.get("market", "")).upper() != "NEPSE":
        raise NepseError("--plan must be a NEPSE exit-plan JSON file")
    symbol = _symbol(plan.get("symbol"))
    if str(plan.get("side", "BUY")).upper() != "BUY":
        raise NepseError("the NEPSE replay currently supports long BUY practice plans only")
    setup = str(plan.get("setup") or "").lower()
    if setup != "orb":
        raise NepseError("historical replay currently supports an opening-range breakout plan only")
    try:
        day = datetime.date.fromisoformat(str(plan.get("date") or ""))
    except ValueError:
        raise NepseError("plan needs a date in YYYY-MM-DD form; create it from a dated entry result")
    entry = _positive(plan.get("entry"), "plan entry")
    stop = _positive(plan.get("stop"), "plan stop")
    target = _positive(plan.get("target"), "plan target")
    if not stop < entry < target:
        raise NepseError("plan needs stop < entry < target for a long practice replay")
    interval_text = str(plan.get("interval") or "5m")
    plan_interval = INTERVALS.get(interval_text)
    if plan_interval is None:
        raise NepseError("plan interval must be 1m or 5m")
    if interval_arg is not None and interval_arg != plan_interval:
        raise NepseError("--interval-minutes does not match the plan interval (%s)" % interval_text)
    interval = interval_arg or plan_interval
    entry_time_value = plan.get("entry_time_npt")
    if not entry_time_value:
        raise NepseError("plan needs entry_time_npt; create it from a completed NEPSE entry result")
    entry_time = _clock(entry_time_value, "plan entry_time_npt")
    or_minutes = _whole_number(plan.get("or_minutes", 15), "plan or_minutes", minimum=1)
    stop_method = str(plan.get("stop_method") or "custom").lower()
    if stop_method not in ("or-mid", "or-low", "custom"):
        raise NepseError("plan stop_method must be or-mid, or-low, or custom")
    target_r = _positive((target - entry) / (entry - stop), "plan reward/risk")
    stop_fraction = (entry - stop) / entry
    if not math.isfinite(stop_fraction) or stop_fraction <= 0:
        raise NepseError("plan stop distance is outside the supported numeric range")
    return {"symbol": symbol, "date": day, "entry": entry, "stop": stop, "target": target,
            "target_r": target_r, "setup": setup,
            "interval_minutes": interval, "entry_time": entry_time,
            "entry_bar_start": plan.get("entry_bar_start_npt"), "or_minutes": or_minutes,
            "stop_method": stop_method, "stop_fraction": stop_fraction}


def _percentile(values, fraction):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def _simulated_paths(sessions, plan, session_open, last_index, replays, seed, window):
    """Bootstrap intraday candle returns from prior complete sessions; repeatable by seed."""
    count = len(sessions[0][1])
    pool = [[] for _ in range(count)]
    for _, bars in sessions:
        for index in range(1, count):
            previous_close = bars[index - 1]["close"]
            bar = bars[index]
            pool[index].append((bar["open"] / previous_close, bar["high"] / previous_close,
                                bar["low"] / previous_close, bar["close"] / previous_close))
    start_index = (plan["entry_time"].hour * 60 + plan["entry_time"].minute
                   - (session_open.hour * 60 + session_open.minute)) // plan["interval_minutes"] - 1
    risk = plan["entry"] - plan["stop"]
    target_r = plan["target_r"]
    rng = random.Random(seed)
    outcomes = []
    closing_prices = []
    r_values = []
    green_count = 0
    for _ in range(replays):
        price = plan["entry"]
        outcome = None
        for index in range(start_index + 1, last_index + 1):
            source_index = index if window == 0 else max(1, min(count - 1, index + rng.randint(-window, window)))
            open_ratio, high_ratio, low_ratio, close_ratio = rng.choice(pool[source_index])
            high = price * high_ratio
            low = price * low_ratio
            close = price * close_ratio
            if not all(math.isfinite(value) for value in (high, low, close)):
                raise NepseError("resampled path exceeded the supported numeric range")
            if outcome is None:
                if low <= plan["stop"]:
                    outcome = "stop"  # if both levels fall in a bar, count the stop first
                elif high >= plan["target"]:
                    outcome = "target"
            price = close
        outcome = outcome or "close"
        outcomes.append(outcome)
        closing_prices.append(price)
        if outcome == "target":
            r_values.append(target_r)
            green_count += 1
        elif outcome == "stop":
            r_values.append(-1.0)
        else:
            r_values.append((price - plan["entry"]) / risk)
            if price > plan["entry"]:
                green_count += 1
    target_count = outcomes.count("target")
    stop_count = outcomes.count("stop")
    close_count = outcomes.count("close")
    return {"replays": replays, "seed": seed, "window_bars": window,
            "bars_after_entry": last_index - start_index,
            "target_first_pct": target_count * 100.0 / replays,
            "stop_first_pct": stop_count * 100.0 / replays,
            "neither_by_close_pct": close_count * 100.0 / replays,
            "green_at_target_or_close_pct": green_count * 100.0 / replays,
            "median_close_npr": _percentile(closing_prices, 0.50),
            "p05_close_npr": _percentile(closing_prices, 0.05),
            "p95_close_npr": _percentile(closing_prices, 0.95),
            "average_gross_r": sum(r_values) / len(r_values)}


def _historical_replay(sessions, plan, range_count, last_index):
    results = []
    for day, bars in sessions:
        opening = bars[:range_count]
        range_high = max(bar["high"] for bar in opening)
        range_low = min(bar["low"] for bar in opening)
        entry_index = next((i for i in range(range_count, last_index + 1)
                            if bars[i]["close"] > range_high), None)
        if entry_index is None:
            continue
        entry = bars[entry_index]["close"]
        if plan["stop_method"] == "or-mid":
            stop = (range_high + range_low) / 2.0
        elif plan["stop_method"] == "or-low":
            stop = range_low
        else:
            stop = entry * (1.0 - plan["stop_fraction"])
        if stop <= 0 or stop >= entry:
            continue
        risk = entry - stop
        target = entry + risk * plan["target_r"]
        if not math.isfinite(target):
            continue
        outcome = "close"
        exit_price = bars[last_index]["close"]
        for bar in bars[entry_index + 1:last_index + 1]:
            stop_hit = bar["low"] <= stop
            target_hit = bar["high"] >= target
            if stop_hit and target_hit:
                outcome, exit_price = "stop (both touched; counted stop-first)", stop
                break
            if stop_hit:
                outcome, exit_price = "stop", stop
                break
            if target_hit:
                outcome, exit_price = "target", target
                break
        results.append({"date": day.isoformat(), "entry_npr": entry, "stop_npr": stop,
                        "target_npr": target, "outcome": outcome,
                        "gross_r": (exit_price - entry) / risk})
    return results


def command_time_machine(args):
    interval_arg = args.interval_minutes
    plan = _replay_plan(args.plan, interval_arg)
    session_open, session_close, session_minutes = _session(
        args.session_open, args.session_close, plan["interval_minutes"])
    step = plan["interval_minutes"]
    if session_open != SESSION_OPEN:
        # The plan's NPT time is read against the session supplied to this replay.
        open_minutes = session_open.hour * 60 + session_open.minute
    else:
        open_minutes = SESSION_OPEN.hour * 60 + SESSION_OPEN.minute
    close_minutes = session_close.hour * 60 + session_close.minute
    if plan["or_minutes"] >= session_minutes or plan["or_minutes"] % step:
        raise NepseError("plan opening range must align to the interval and leave at least one later candle")
    entry_minutes = plan["entry_time"].hour * 60 + plan["entry_time"].minute
    entry_offset = entry_minutes - open_minutes
    if entry_offset <= 0 or entry_offset % step:
        raise NepseError("plan entry_time_npt must be an interval-aligned candle close after session open")
    entry_index = entry_offset // step - 1
    range_count = plan["or_minutes"] // step
    if entry_index < range_count:
        raise NepseError("plan entry time must be after the opening range is complete")
    if args.until:
        until_time = _clock(args.until, "--until")
        until_minutes = until_time.hour * 60 + until_time.minute
    else:
        until_minutes = close_minutes
    if until_minutes > close_minutes or until_minutes <= entry_minutes or (until_minutes - open_minutes) % step:
        raise NepseError("--until must be an interval-aligned time after entry and no later than session close")
    last_index = (until_minutes - open_minutes) // step - 1
    if last_index <= entry_index:
        raise NepseError("--until leaves no completed candles after the entry")
    sessions_by_day = _histories(args.candles, step, session_open, session_close)
    plan_bars = sessions_by_day.get(plan["date"], [])
    plan_starts = {bar["start"]: bar for bar in plan_bars}
    open_dt = datetime.datetime.combine(plan["date"], session_open)
    step_delta = datetime.timedelta(minutes=step)
    plan_entry_start = open_dt + entry_index * step_delta
    if plan_entry_start not in plan_starts:
        raise NepseError("candle data has no completed entry bar at %s NPT on %s" % (
            plan_entry_start.strftime("%H:%M"), plan["date"].isoformat()))
    actual_entry_bar = plan_starts[plan_entry_start]
    if abs(actual_entry_bar["close"] - plan["entry"]) > 0.01:
        raise NepseError("plan entry NPR %.4f does not match the supplied candle close NPR %.4f" % (
            plan["entry"], actual_entry_bar["close"]))
    if plan["entry_bar_start"]:
        expected_start = _clock(plan["entry_bar_start"], "plan entry_bar_start_npt")
        if expected_start != plan_entry_start.time():
            raise NepseError("plan entry_bar_start_npt does not match entry_time_npt")
    bar_count = session_minutes // step
    complete_sessions = []
    skipped = 0
    for day, bars in sorted(sessions_by_day.items()):
        if day >= plan["date"]:
            continue
        by_start = {bar["start"]: bar for bar in bars}
        day_open = datetime.datetime.combine(day, session_open)
        expected = [day_open + i * step_delta for i in range(bar_count)]
        if any(start not in by_start for start in expected):
            skipped += 1
            continue
        complete_sessions.append((day, [by_start[start] for start in expected]))
    if len(complete_sessions) < args.min_sessions:
        raise NepseError("only %d complete prior session(s) in the CSV; at least %d are required for a replay pool" % (
            len(complete_sessions), args.min_sessions))
    if not 1 <= args.min_sessions <= 10000:
        raise NepseError("--min-sessions must be between 1 and 10,000")
    if not 1 <= args.replays <= 1000000:
        raise NepseError("--replays must be between 1 and 1,000,000")
    if not 0 <= args.window <= 10:
        raise NepseError("--window must be between 0 and 10 bars")
    mc = _simulated_paths(complete_sessions, plan, session_open, last_index,
                          args.replays, args.seed, args.window)
    history = _historical_replay(complete_sessions, plan, range_count, last_index)
    if history:
        targets = sum(1 for item in history if item["outcome"] == "target")
        stops = sum(1 for item in history if item["outcome"].startswith("stop"))
        average_history_r = sum(item["gross_r"] for item in history) / len(history)
    else:
        targets, stops, average_history_r = 0, 0, None
    result = {"market": "NEPSE", "currency": "NPR", "symbol": plan["symbol"],
              "plan_date": plan["date"].isoformat(), "setup": plan["setup"],
              "session_open_npt": session_open.strftime("%H:%M"),
              "session_close_npt": session_close.strftime("%H:%M"),
              "interval_minutes": step, "opening_range_minutes": plan["or_minutes"],
              "target_r": plan["target_r"], "stop_method": plan["stop_method"],
              "history": {"prior_complete_sessions": len(complete_sessions), "skipped_incomplete_sessions": skipped,
                          "setups": len(history), "targets": targets, "stops": stops,
                          "neither_by_close": len(history) - targets - stops,
                          "average_gross_r": average_history_r, "trades": history},
              "bootstrap": mc, "seed": args.seed, "practice_only": True, "prediction": False}
    print("NEPSE TIME MACHINE | historical replay + seeded bootstrap | user-supplied OHLCV only")
    print("Plan: %s on %s | entry %s | stop %s | target %s (%.2fR)" % (
        plan["symbol"], plan["date"].isoformat(), _money(plan["entry"]), _money(plan["stop"]),
        _money(plan["target"]), plan["target_r"]))
    print("Prior full sessions: %d | incomplete prior sessions skipped: %d | rule setups: %d" % (
        len(complete_sessions), skipped, len(history)))
    print("History: target %d | stop %d | neither by close %d | average gross R %s" % (
        targets, stops, len(history) - targets - stops,
        "%+.3f" % average_history_r if average_history_r is not None else "n/a"))
    print("%d seeded paths (seed %d): target first %.1f%% | stop first %.1f%% | neither %.1f%% | green %.1f%%" % (
        args.replays, args.seed, mc["target_first_pct"], mc["stop_first_pct"],
        mc["neither_by_close_pct"], mc["green_at_target_or_close_pct"]))
    print("Closing price: median %s, 5th-95th percentile %s to %s | average gross R %+.3f" % (
        _money(mc["median_close_npr"]), _money(mc["p05_close_npr"]),
        _money(mc["p95_close_npr"]), mc["average_gross_r"]))
    print("Simulation resamples bars from the supplied prior sessions; the stop is counted first if both levels fall in one bar. This is not a prediction.")
    print("Fees, taxes, settlement, gaps through stops, slippage, announcements and halts are not modeled.")
    if args.write:
        write_json(args.write, result)
        print("Wrote %s." % args.write)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


def _load_order_file(path):
    data = read_json(path)
    if isinstance(data, dict):
        normalised = _normalise_record(data)
        orders = normalised.get("orders")
        if orders is None:
            orders = [normalised]
    else:
        orders = data
    if not isinstance(orders, list) or not all(isinstance(order, dict) for order in orders):
        raise NepseError("order file must be an order object or contain an orders list of objects")
    return [_normalise_record(order) for order in orders]


def command_budget(args):
    plan_path = args.plan
    plan = None
    if plan_path:
        if args.symbol or args.entry is not None or args.stop is not None or args.target is not None or args.target_r is not None:
            raise NepseError("use either --plan or manual symbol/price flags, not both")
        plan = read_json(plan_path)
        if not isinstance(plan, dict) or str(plan.get("market", "")).upper() != "NEPSE":
            raise NepseError("--plan must be a NEPSE exit-plan JSON file")
        symbol = _symbol(plan.get("symbol"))
        entry = _positive(plan.get("entry"), "plan entry")
        stop = _positive(plan.get("stop"), "plan stop")
        target = _positive(plan.get("target"), "plan target")
    else:
        if not args.symbol:
            raise NepseError("give a symbol or use --plan PATH")
        symbol = _symbol(args.symbol)
        if args.entry is None or args.stop is None:
            raise NepseError("--entry and --stop are required unless --plan is used")
        entry = _positive(args.entry, "--entry")
        stop = _positive(args.stop, "--stop")
        if args.target is not None:
            if args.target_r is not None:
                raise NepseError("use either --target or --target-r, not both")
            target = _positive(args.target, "--target")
        else:
            target_r = _positive(args.target_r if args.target_r is not None else 1.0, "--target-r")
            target = entry + (entry - stop) * target_r
    capital = _positive(args.capital, "--capital")
    max_loss = _positive(args.max_loss, "--max-loss")
    fee = _nonnegative(args.fee_per_share, "--round-trip-fee-per-share")
    if entry <= stop:
        raise NepseError("for this long practice calculation, entry must be above stop")
    if target <= entry or not math.isfinite(target):
        raise NepseError("target must be a finite price above entry")
    target_r = _positive((target - entry) / (entry - stop), "reward/risk")
    risk_per_share = entry - stop + fee
    if not math.isfinite(risk_per_share) or risk_per_share <= 0:
        raise NepseError("risk per share is outside the supported numeric range")
    risk_ratio = max_loss / risk_per_share
    cash_ratio = capital / entry
    if not math.isfinite(risk_ratio) or not math.isfinite(cash_ratio):
        raise NepseError("the supplied values are outside the supported share-count range")
    by_risk = int(math.floor(risk_ratio))
    by_cash = int(math.floor(cash_ratio))
    shares = min(by_risk, by_cash)
    planned_loss = shares * risk_per_share
    gross_cost = shares * entry
    reward_risk = (target - entry) / (entry - stop)
    print("NEPSE POSITION PRACTICE | %s | NPR | whole shares" % symbol)
    print("Max-loss budget: %s | Risk/share incl. supplied fee estimate: %s" % (
        _money(max_loss), _money(risk_per_share)))
    print("Shares by risk: %d | shares by cash before buy fees: %d | practice size: %d" % (
        by_risk, by_cash, shares))
    print("Gross buy value: %s | planned stop loss incl. supplied fee estimate: %s | reward/risk %.2f" % (
        _money(gross_cost), _money(planned_loss), reward_risk))
    if fee == 0:
        print("Fee estimate is zero because none was supplied; actual fees, taxes and slippage are excluded.")
    if shares == 0:
        print("No whole-share size fits both inputs. Nothing was placed.")
        return 1
    print("Sizing arithmetic only, not a recommendation. No order was placed.")
    if args.write:
        order = {"symbol": symbol, "side": "BUY", "quantity": shares, "entry": entry,
                 "limit_price": entry, "stop": stop, "target": target,
                 "planned_loss_npr": round(planned_loss, 4), "gross_value_npr": round(gross_cost, 4),
                 "reward_risk": round(reward_risk, 4), "paper_only": True}
        write_json(args.write, {"market": "NEPSE", "currency": "NPR", "status": "PROPOSED - NOT PLACED",
                                "paper_only": True, "source_plan": plan_path, "orders": [order]})
        print("Wrote proposed order JSON to %s." % args.write)
    return 0


def _risk_config(path):
    config = read_json(path)
    if not isinstance(config, dict):
        raise NepseError("risk config must be a JSON object")
    max_loss = _positive(config.get("max_loss_per_trade_npr"), "max_loss_per_trade_npr")
    cash_value = config.get("cash_npr")
    if cash_value in (None, "", 0, "0"):
        cash_value = config.get("account_npr")
    cash = _positive(cash_value, "cash_npr or account_npr")
    daily_cap = _positive(config.get("max_daily_loss_npr"), "max_daily_loss_npr")
    max_trades = _whole_number(config.get("max_trades_per_day"), "max_trades_per_day", minimum=1)
    min_rr = _positive(config.get("min_reward_risk"), "min_reward_risk")
    fee = _nonnegative(config.get("round_trip_fee_per_share_npr", 0), "round_trip_fee_per_share_npr")
    if config.get("paper_only") is not True:
        raise NepseError("paper_only must be true; NEPSE ticket generation is paper-only")
    if config.get("allow_short", False) is not False:
        raise NepseError("allow_short must remain false in this long-only NEPSE practice tool")
    return {"max_loss": max_loss, "cash": cash, "daily_cap": daily_cap,
            "max_trades": max_trades, "min_rr": min_rr, "fee": fee}


def _order_value(order, primary, alternate=None):
    value = order.get(primary)
    if value in (None, "") and alternate:
        value = order.get(alternate)
    return value


def command_risk(args):
    limits = _risk_config(args.config)
    orders = _load_order_file(args.orders)
    if not orders:
        raise NepseError("order file contains no orders to check")
    daily_loss = _nonnegative(args.daily_loss, "--daily-loss")
    trades_today = _whole_number(args.trades_today, "--trades-today", minimum=0)
    print("NEPSE RISK CHECK | your configured practice limits | not legal or broker approval")
    blocked = 0
    accepted_risk = 0.0
    accepted_cost = 0.0
    accepted_count = 0
    for index, order in enumerate(orders, 1):
        symbol = str(order.get("symbol") or "UNKNOWN").strip().upper()
        reasons = []
        raw_qty = _order_value(order, "quantity", "qty")
        raw_entry = _order_value(order, "entry", "limit_price")
        raw_stop = order.get("stop")
        raw_target = order.get("target")
        try:
            qty_value = _positive(raw_qty, "quantity")
            qty = int(qty_value)
            if qty != qty_value:
                reasons.append("quantity must be a whole number of shares")
        except NepseError as exc:
            qty, qty_value = 0, None
            reasons.append(str(exc))
        values = []
        for raw, label in ((raw_entry, "entry"), (raw_stop, "stop"), (raw_target, "target")):
            try:
                values.append(_positive(raw, label))
            except NepseError as exc:
                values.append(None)
                reasons.append(str(exc))
        entry, stop, target = values
        side = str(order.get("side", "BUY")).strip().upper()
        if side != "BUY":
            reasons.append("this practice risk check only accepts long BUY entries")
        if not symbol or symbol == "UNKNOWN":
            reasons.append("symbol is required")
        if entry is not None and stop is not None and stop >= entry:
            reasons.append("buy entry must be above stop")
        if entry is not None and target is not None and target <= entry:
            reasons.append("target must be above entry for a long practice plan")
        valid_levels = entry is not None and stop is not None and target is not None and entry > stop
        valid_qty = qty_value is not None and qty > 0 and qty == qty_value
        if valid_levels and valid_qty:
            risk = qty * (entry - stop + limits["fee"])
            cost = qty * entry
            rr = (target - entry) / (entry - stop) if target > entry else 0.0
        else:
            risk, cost, rr = float("inf"), float("inf"), 0.0
        if risk > limits["max_loss"]:
            reasons.append("planned loss NPR %s exceeds configured max NPR %s" % (
                _money(risk), _money(limits["max_loss"])))
        if accepted_cost + cost > limits["cash"]:
            reasons.append("proposed gross cost including earlier PASS orders exceeds configured available cash")
        if rr < limits["min_rr"]:
            reasons.append("reward/risk %.2f is below configured minimum %.2f" % (rr, limits["min_rr"]))
        if daily_loss + accepted_risk + risk > limits["daily_cap"]:
            reasons.append("realized loss plus this and earlier PASS orders exceeds the daily limit")
        if trades_today + accepted_count + 1 > limits["max_trades"]:
            reasons.append("configured trades-per-day limit would be exceeded")
        if reasons:
            blocked += 1
            print("BLOCK %s | qty %d | planned loss %s | %s" % (
                symbol, qty, _money(risk), "; ".join(reasons)))
        else:
            accepted_risk += risk
            accepted_cost += cost
            accepted_count += 1
            print("PASS %s | qty %d | planned loss %s | reward/risk %.2f | paper only" % (
                symbol, qty, _money(risk), rr))
    print("%d of %d proposed order(s) blocked. This is arithmetic, not a recommendation or rule-compliance check." % (
        blocked, len(orders)))
    print("Open positions, pending orders, fees not entered here, and the accuracy of your inputs are not verified.")
    return 1 if blocked else 0


def command_broker(args):
    orders = _load_order_file(args.order)
    if len(orders) != 1:
        raise NepseError("paper ticket takes exactly one order")
    order = orders[0]
    symbol = _symbol(order.get("symbol"))
    side = str(order.get("side", "BUY")).strip().upper()
    if side not in ("BUY", "SELL"):
        raise NepseError("side must be BUY or SELL")
    qty_value = _positive(_order_value(order, "quantity", "qty"), "quantity")
    qty = int(qty_value)
    if qty != qty_value:
        raise NepseError("quantity must be a whole number of shares")
    price = _positive(_order_value(order, "limit_price", "entry"), "limit price")
    if side == "SELL":
        owned = _whole_number(order.get("owned_shares"), "owned_shares", minimum=0)
        if owned < qty:
            raise NepseError("SELL quantity exceeds stated owned_shares; shorting is not enabled")
    ticket = {"market": "NEPSE", "currency": "NPR", "symbol": symbol, "side": side,
              "quantity": qty, "limit_price_npr": price, "paper_only": True,
              "order_sent": False, "status": "PAPER TICKET ONLY - NOT PLACED"}
    print("NEPSE PAPER TICKET | NOT PLACED")
    print("%s %d %s at limit %s" % (side, qty, symbol, _money(price)))
    print("This tool has no TMS/broker connection and cannot send an order.")
    if args.write:
        write_json(args.write, ticket)
        print("Wrote %s." % args.write)
    return 0


def command_alerts(args):
    rules_data = read_json(args.rules)
    rules = rules_data.get("alerts", rules_data) if isinstance(rules_data, dict) else rules_data
    if not isinstance(rules, list) or not all(isinstance(rule, dict) for rule in rules):
        raise NepseError("rules JSON must be a list of objects or contain an alerts list of objects")
    price_rows = read_records(args.prices)
    latest = {}
    for row_number, row in enumerate(price_rows, 1):
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            raise NepseError("price row %d is missing symbol" % row_number)
        stamp = parse_npt(row.get("timestamp") or row.get("datetime"), "price row %d timestamp" % row_number)
        price = _positive(row.get("price"), "price row %d price" % row_number)
        if symbol not in latest or stamp > latest[symbol][0]:
            latest[symbol] = (stamp, price)
    checked = []
    for rule_number, rule in enumerate(rules, 1):
        symbol = _symbol(rule.get("symbol"), "alert rule %d symbol" % rule_number)
        has_above = rule.get("above") not in (None, "")
        has_below = rule.get("below") not in (None, "")
        if has_above == has_below:
            raise NepseError("alert rule %d must set exactly one of above or below" % rule_number)
        key = "above" if has_above else "below"
        level = _positive(rule.get(key), "alert rule %d %s level" % (rule_number, key))
        checked.append((symbol, key, level))
    print("NEPSE ALERT CHECK | one offline comparison of supplied quotes; no polling or notifications")
    hits = 0
    for symbol, key, level in checked:
        if symbol not in latest:
            print("NO DATA %s | no supplied quote" % symbol)
            continue
        stamp, price = latest[symbol]
        hit = price >= level if key == "above" else price <= level
        if hit:
            hits += 1
        condition = "%s %s" % (key, _money(level))
        print("%s %s | latest supplied price %s at %s NPT; condition %s" % (
            "ALERT" if hit else "WAIT", symbol, _money(price), stamp.strftime("%Y-%m-%d %H:%M"), condition))
    print("%d alert condition(s) hit. Verify quote source, timestamp and freshness yourself." % hits)
    return 0 if hits else 1


def _pct_change(current, previous):
    if previous in (None, 0) or not math.isfinite(current) or not math.isfinite(previous):
        return None
    change = (current - previous) / abs(previous) * 100.0
    return change if math.isfinite(change) else None


def command_analyst(args):
    rows = [row for row in read_records(args.file) if row.get("period")]
    if not rows:
        raise NepseError("financial data needs rows with a period column")
    latest = rows[-1]
    previous = rows[-2] if len(rows) > 1 else None
    print("NEPSE COMPANY REPORT REVIEW | supplied figures only | no forecast")
    print("Latest supplied period: %s" % latest.get("period"))
    if previous:
        print("Comparison period: %s. Rows are used in the order supplied; confirm periods and units." % previous.get("period"))
    any_metric = False
    for key, label in (("revenue_npr", "Revenue NPR"), ("operating_profit_npr", "Operating profit NPR"),
                       ("net_income_npr", "Net income NPR"), ("eps_npr", "EPS NPR/share")):
        raw = latest.get(key)
        if raw in (None, ""):
            continue
        try:
            value = _number(raw, label)
        except NepseError:
            print("%s: skipped, supplied latest value is not numeric" % label)
            continue
        any_metric = True
        old = None
        if previous and previous.get(key) not in (None, ""):
            try:
                old = _number(previous[key], label + " comparison")
            except NepseError:
                old = None
        pct = _pct_change(value, old) if old is not None else None
        comparison = "; change n/a" if pct is None else "; arithmetic change %+.2f%% vs %s" % (pct, previous.get("period"))
        rendered = "NPR %.4f" % value if key == "eps_npr" else _money(value)
        print("%s: %s%s" % (label, rendered, comparison))
    if not any_metric:
        print("No numeric metrics were found in the latest supplied row.")
    print("Check the original filing, reporting period, units and one-off items; percentage changes can mislead around zero or negative values.")
    print("This is a summary of supplied figures, not a valuation, prediction or buy/sell view.")
    return 0


def command_disclosures(args):
    rows = read_records(args.file)
    symbol = _symbol(args.symbol, "--symbol") if args.symbol else None
    found = []
    for row in rows:
        row_symbol = str(row.get("symbol") or "").strip().upper()
        if symbol and row_symbol != symbol:
            continue
        headline = str(row.get("headline") or row.get("title") or "").strip()
        if headline:
            found.append((row, headline))
    if not found:
        print("No matching disclosures in the supplied file. No filing source was searched.")
        return 1
    print("NEPSE CORPORATE DISCLOSURES | supplied public notices only")
    for row, headline in found:
        category = classify_text("%s %s" % (row.get("type", ""), headline))
        print("%s | %s | %s | %s" % (
            row.get("date") or row.get("timestamp") or "date not supplied",
            row.get("symbol") or "market", ", ".join(category), headline))
        source = row.get("source") or "source not supplied"
        url = row.get("url") or ""
        print("  Source: %s%s" % (source, (" | " + str(url)) if url else ""))
    print("This tracks supplied public company/exchange notices, not politicians' or insiders' private trades.")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Offline-first NEPSE learning tools. No live data, TMS connection, or order execution.")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("scan", help="screen one session of per-symbol 1m/5m CSV candles")
    p.add_argument("--candles-dir", required=True, help="one CSV per symbol for the same session")
    p.add_argument("--as-of", required=True, help="Nepal time, e.g. '2026-11-13 11:20'")
    p.add_argument("--interval", choices=tuple(INTERVALS), default="5m")
    p.add_argument("--or-minutes", type=int, default=15)
    p.add_argument("--min-volume-x", type=float)
    p.add_argument("--session-open", default="11:00", help="assumed session start in NPT; verify current hours")
    p.add_argument("--session-close", default="15:00", help="assumed session end in NPT; verify current hours")
    p.set_defaults(func=command_scan)

    p = sub.add_parser("news", help="organise user-supplied NEPSE headlines")
    p.add_argument("--file", required=True, help="CSV or JSON with headline/source/date fields")
    p.add_argument("--symbol")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=command_news)

    p = sub.add_parser("entry", help="run the separate offline NEPSE entry practice helper", add_help=False)
    p.add_argument("args", nargs=argparse.REMAINDER)
    p.set_defaults(func=command_entry)

    p = sub.add_parser("exit", help="make a practice plan from an entry result or user-chosen price levels")
    p.add_argument("symbol", nargs="?")
    p.add_argument("--from-entry", help="NEPSE entry-result JSON written by the entry helper")
    p.add_argument("--entry", type=float, help="entry price in NPR; not needed with --from-entry")
    p.add_argument("--stop", type=float, help="your chosen stop in NPR, for a custom stop")
    p.add_argument("--stop-method", choices=("or-mid", "or-low", "custom"),
                    help="opening-range stop rule, or custom with --stop")
    p.add_argument("--setup", choices=("orb", "level", "manual"), default="manual")
    p.add_argument("--date", help="optional plan date, YYYY-MM-DD")
    p.add_argument("--entry-time", help="optional completed candle close time, HH:MM NPT")
    p.add_argument("--interval", choices=tuple(INTERVALS), default="5m")
    p.add_argument("--or-minutes", type=int, default=15)
    p.add_argument("--target-r", type=float, default=1.0)
    p.add_argument("--write", nargs="?", const="trader/nepse-plan.json", metavar="PATH",
                    help="save the plan JSON (default trader/nepse-plan.json)")
    p.set_defaults(func=command_exit)

    p = sub.add_parser("timemachine", help="replay a NEPSE plan over supplied history and seeded paths")
    p.add_argument("--plan", required=True, help="NEPSE plan JSON written by the exit skill")
    p.add_argument("--candles", required=True, help="multi-session CSV including the plan date and prior sessions")
    p.add_argument("--interval-minutes", type=int, choices=(1, 5),
                    help="optional check against the plan's interval")
    p.add_argument("--until", help="optional replay cutoff in NPT, e.g. 14:55")
    p.add_argument("--session-open", default="11:00", help="assumed session start in NPT; verify current hours")
    p.add_argument("--session-close", default="15:00", help="assumed session end in NPT; verify current hours")
    p.add_argument("--replays", type=int, default=10000)
    p.add_argument("--seed", type=int, default=19)
    p.add_argument("--window", type=int, default=2, help="bar-slot resampling window")
    p.add_argument("--min-sessions", type=int, default=20, help="minimum complete prior sessions")
    p.add_argument("--json", action="store_true")
    p.add_argument("--write", metavar="PATH", help="save replay summary as JSON")
    p.set_defaults(func=command_time_machine)

    p = sub.add_parser("budget", help="size whole-share practice positions in NPR")
    p.add_argument("symbol", nargs="?")
    p.add_argument("--plan", help="NEPSE plan JSON written by the exit skill")
    p.add_argument("--capital", type=float, required=True, help="available cash in NPR")
    p.add_argument("--max-loss", type=float, required=True, help="user's max planned loss in NPR")
    p.add_argument("--entry", type=float, help="manual entry price; not needed with --plan")
    p.add_argument("--stop", type=float, help="manual stop price; not needed with --plan")
    p.add_argument("--target", type=float, help="manual target price; defaults to --target-r")
    p.add_argument("--target-r", type=float, help="practice target multiple; defaults to 1R")
    p.add_argument("--round-trip-fee-per-share", dest="fee_per_share", type=float, default=0.0,
                    help="your own estimated round-trip fee per share; zero means fees excluded")
    p.add_argument("--write", nargs="?", const="trader/nepse-orders.json", metavar="PATH",
                    help="save a proposed order JSON, never submit it")
    p.set_defaults(func=command_budget)

    p = sub.add_parser("risk", help="check hypothetical orders against the learner's NPR risk limits")
    p.add_argument("--orders", required=True, help="JSON order or object with an orders list")
    p.add_argument("--config", required=True, help="your own NEPSE risk configuration JSON")
    p.add_argument("--daily-loss", type=float, default=0.0, help="realized loss so far today, NPR")
    p.add_argument("--trades-today", type=int, default=0)
    p.set_defaults(func=command_risk)

    p = sub.add_parser("broker", help="format a paper ticket only; never sends orders")
    p.add_argument("--order", required=True, help="one JSON order")
    p.add_argument("--write", nargs="?", const="trader/nepse-paper-ticket.json")
    p.set_defaults(func=command_broker)

    p = sub.add_parser("alerts", help="check rules once against a supplied quote CSV")
    p.add_argument("--rules", required=True, help="JSON list or object with alerts list")
    p.add_argument("--prices", required=True, help="CSV: timestamp,symbol,price")
    p.set_defaults(func=command_alerts)

    p = sub.add_parser("analyst", help="compare user-supplied company financial periods")
    p.add_argument("--file", required=True, help="CSV with period and NPR metrics")
    p.set_defaults(func=command_analyst)

    p = sub.add_parser("disclosures", help="review user-supplied NEPSE/company public notices")
    p.add_argument("--file", required=True, help="CSV or JSON of public notices")
    p.add_argument("--symbol")
    p.set_defaults(func=command_disclosures)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except NepseError as exc:
        print("nepse_tools: %s" % exc, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("nepse_tools: stopped", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
