#!/usr/bin/env python3
"""Offline, practice-only entry checks for NEPSE intraday candles.

This deliberately does not fetch market data. It reads user-provided OHLCV
CSV, interprets naive timestamps as Nepal time (UTC+05:45), and counts only
completed 1-minute or 5-minute bars.

    python3 nepse_practice.py check DEMO \
        --candles tests/fixtures/trader-entry/NEPSE-DEMO-5m.csv \
        --interval 5m --as-of "2026-11-13 11:20"

CSV columns: timestamp,open,high,low,close; volume is optional unless the
volume filter is used. Timestamps label the START of each candle. A timestamp
without an offset is interpreted as NPT.
"""

import argparse
import csv
import datetime
import json
import math
import os
import sys

NPT = datetime.timezone(datetime.timedelta(hours=5, minutes=45))
DEFAULT_OPEN = datetime.time(11, 0)
DEFAULT_CLOSE = datetime.time(15, 0)
INTERVAL_MINUTES = {"1m": 1, "5m": 5}


class PracticeError(Exception):
    pass


def parse_timestamp(value, label):
    value = str(value or "").strip()
    if value.endswith(" NPT"):
        value = value[:-4].strip()
    if not value:
        raise PracticeError("%s is blank" % label)
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise PracticeError("%s must look like 2026-11-13 11:15 (Nepal time)" % label)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(NPT).replace(tzinfo=None)
    return parsed


def parse_hhmm(value, label):
    try:
        parsed = datetime.datetime.strptime(value, "%H:%M")
    except (TypeError, ValueError):
        raise PracticeError("%s must use HH:MM, for example 11:00" % label)
    return parsed.time()


def number(row, field, line, optional=False):
    raw = row.get(field)
    if raw is None or str(raw).strip() == "":
        if optional:
            return None
        raise PracticeError("CSV line %d is missing %s" % (line, field))
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise PracticeError("CSV line %d has an invalid %s: %r" % (line, field, raw))
    if not math.isfinite(value):
        raise PracticeError("CSV line %d has a non-finite %s" % (line, field))
    return value


def read_candles(path, interval, session_open, session_close):
    if not os.path.isfile(path):
        raise PracticeError("no candle CSV at %s" % path)
    step = datetime.timedelta(minutes=INTERVAL_MINUTES[interval])
    try:
        fh = open(path, "r", newline="", encoding="utf-8-sig")
    except OSError as exc:
        raise PracticeError("cannot open %s: %s" % (path, exc))
    with fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise PracticeError("CSV needs a header row: timestamp,open,high,low,close,volume")
        columns = {name.strip().lower(): name for name in reader.fieldnames if name}
        time_column = columns.get("timestamp") or columns.get("datetime")
        if not time_column:
            raise PracticeError("CSV needs a timestamp or datetime column")
        for required in ("open", "high", "low", "close"):
            if required not in columns:
                raise PracticeError("CSV needs an %s column" % required)

        candles = []
        for line, row in enumerate(reader, 2):
            stamp = parse_timestamp(row.get(time_column), "CSV line %d timestamp" % line)
            if not (session_open <= stamp.time() < session_close):
                continue  # Exclude pre-open and after-session candles.
            start = datetime.datetime.combine(stamp.date(), stamp.time())
            open_dt = datetime.datetime.combine(stamp.date(), session_open)
            close_dt = datetime.datetime.combine(stamp.date(), session_close)
            elapsed = (start - open_dt).total_seconds()
            step_seconds = step.total_seconds()
            if elapsed % step_seconds != 0:
                raise PracticeError("CSV line %d timestamp is not aligned to the %s bar grid from %s" % (
                    line, interval, session_open.strftime("%H:%M")))
            if start + step > close_dt:
                continue

            o = number(row, columns["open"], line)
            h = number(row, columns["high"], line)
            low = number(row, columns["low"], line)
            c = number(row, columns["close"], line)
            volume = number(row, columns["volume"], line, optional=True) if "volume" in columns else None
            if min(o, h, low, c) <= 0 or h < max(o, c, low) or low > min(o, c, h):
                raise PracticeError("CSV line %d has inconsistent OHLC values" % line)
            if volume is not None and volume < 0:
                raise PracticeError("CSV line %d has negative volume" % line)
            candles.append({"start": start, "open": o, "high": h, "low": low,
                            "close": c, "volume": volume})

    if not candles:
        raise PracticeError("no candles fall inside the assumed regular session %s-%s NPT" % (
            session_open.strftime("%H:%M"), session_close.strftime("%H:%M")))
    dates = sorted(set(bar["start"].date() for bar in candles))
    if len(dates) != 1:
        raise PracticeError("use one trading session per CSV; this file has %d dates" % len(dates))
    candles.sort(key=lambda bar: bar["start"])
    starts = [bar["start"] for bar in candles]
    if len(starts) != len(set(starts)):
        raise PracticeError("CSV has duplicate candle timestamps")
    return candles, dates[0]


def evaluate(symbol, candles, day, as_of, setup="orb", or_minutes=15, interval="5m",
             level=None, min_volume_x=None, session_open=DEFAULT_OPEN, session_close=DEFAULT_CLOSE):
    step_minutes = INTERVAL_MINUTES[interval]
    if or_minutes <= 0 or or_minutes % step_minutes:
        raise PracticeError("--or-minutes must be a positive multiple of the %s interval" % interval)
    if as_of.date() != day:
        raise PracticeError("--as-of date must match the candle CSV date (%s)" % day.isoformat())
    if setup == "level" and (level is None or level <= 0):
        raise PracticeError("--setup level needs --level PRICE")
    if setup == "orb" and level is not None:
        raise PracticeError("--level is only used with --setup level")
    if min_volume_x is not None and min_volume_x <= 0:
        raise PracticeError("--min-volume-x must be above zero")

    step = datetime.timedelta(minutes=step_minutes)
    open_dt = datetime.datetime.combine(day, session_open)
    close_dt = datetime.datetime.combine(day, session_close)
    range_end = open_dt + datetime.timedelta(minutes=or_minutes)
    expected_range = [open_dt + i * step for i in range(or_minutes // step_minutes)]
    by_start = {bar["start"]: bar for bar in candles}
    completed = {bar["start"]: bar for bar in candles if bar["start"] + step <= as_of}
    result = {
        "market": "NEPSE",
        "symbol": symbol.upper(),
        "date": day.isoformat(),
        "as_of_npt": as_of.strftime("%Y-%m-%d %H:%M:%S"),
        "interval": interval,
        "setup": setup,
        "or_minutes": or_minutes,
        "session_open_npt": session_open.strftime("%H:%M"),
        "session_close_npt": session_close.strftime("%H:%M"),
        "data_source": "user-supplied CSV; offline practice only",
        "as_of_source": "user-provided Nepal local time",
        "status": "waiting",
        "reason": "",
        "opening_range": None,
        "level": level,
        "last": None,
        "trigger": None,
        "calendar_note": "Trading days and holidays are not checked. Verify the current NEPSE calendar and session hours.",
        "safety_note": "Practice signal only, not a buy recommendation. No order was placed.",
    }

    if as_of < open_dt:
        result.update(status="not-open", reason="the assumed regular session starts at %s NPT" %
                      session_open.strftime("%H:%M"))
        return result

    range_bars = [completed[t] for t in expected_range if t in completed]
    if as_of < range_end:
        result.update(status="forming", reason="opening range is still forming: %d of %d required bars have closed" %
                      (len(range_bars), len(expected_range)))
        return result

    missing_range = [t.strftime("%H:%M") for t in expected_range if t not in completed]
    if missing_range:
        result.update(status="incomplete", reason="missing completed opening-range candle(s): %s" %
                      ", ".join(missing_range))
        return result

    range_high = max(bar["high"] for bar in range_bars)
    range_low = min(bar["low"] for bar in range_bars)
    volume_values = [bar["volume"] for bar in range_bars]
    average_volume = (sum(volume_values) / len(volume_values)
                      if all(value is not None for value in volume_values) else None)
    if min_volume_x is not None and average_volume is None:
        raise PracticeError("--min-volume-x needs a volume value on every opening-range candle")
    if min_volume_x is not None and average_volume <= 0:
        raise PracticeError("opening-range average volume must be above zero for --min-volume-x")
    trigger_level = range_high if setup == "orb" else level
    result["level"] = trigger_level
    result["opening_range"] = {
        "start_npt": open_dt.strftime("%H:%M"),
        "end_npt": range_end.strftime("%H:%M"),
        "high": round(range_high, 4),
        "low": round(range_low, 4),
        "bars": len(range_bars),
        "expected_bars": len(expected_range),
        "average_volume": round(average_volume, 2) if average_volume is not None else None,
    }

    cutoff = min(as_of, close_dt)
    candidate_count = max(0, int((cutoff - range_end).total_seconds() // step.total_seconds()))
    candidate_starts = [range_end + i * step for i in range(candidate_count)]
    last = range_bars[-1]
    volume_rejection = None
    for start in candidate_starts:
        bar = completed.get(start)
        if bar is None:
            result.update(status="incomplete", reason="missing completed %s candle at %s NPT; cannot confirm the first trigger" % (
                interval, start.strftime("%H:%M")))
            if last:
                result["last"] = _public_bar(last, trigger_level, interval)
            return result
        last = bar
        close_above = bar["close"] > trigger_level
        volume_ok = (min_volume_x is None or
                     (bar["volume"] is not None and bar["volume"] >= average_volume * min_volume_x))
        if close_above and min_volume_x is not None and not volume_ok:
            if bar["volume"] is None:
                volume_rejection = "the %s candle closed above the level, but its volume is missing" % start.strftime("%H:%M")
            else:
                volume_ratio = bar["volume"] / average_volume
                volume_rejection = ("the %s candle closed above the level, but volume was %.2fx the opening-range average; "
                                    "your filter requires %.2fx" %
                                    (start.strftime("%H:%M"), volume_ratio, min_volume_x))
        if close_above and volume_ok:
            end = start + step
            pct = (bar["close"] - trigger_level) / trigger_level * 100.0
            result.update(status="triggered", reason="the completed candle closed above the practice level",
                          trigger={"bar_start_npt": start.strftime("%H:%M"),
                                   "time_npt": end.strftime("%H:%M"),
                                   "close": round(bar["close"], 4),
                                   "level": round(trigger_level, 4),
                                   "amount_above": round(bar["close"] - trigger_level, 4),
                                   "pct_above": round(pct, 3),
                                   "volume": bar["volume"]})
            result["last"] = _public_bar(bar, trigger_level, interval)
            return result

    if last:
        result["last"] = _public_bar(last, trigger_level, interval)
    if as_of >= close_dt:
        reason = "no qualifying completed candle was found by the assumed session close"
        if volume_rejection:
            reason += "; " + volume_rejection
        result.update(status="expired", reason=reason)
    elif volume_rejection:
        result.update(status="waiting", reason=volume_rejection)
    elif last:
        result.update(status="waiting", reason="no completed candle has closed above the practice level yet")
    else:
        result.update(status="waiting", reason="the opening range is complete; waiting for the first post-range candle to close")
    return result


def _public_bar(bar, level, interval):
    return {
        "start_npt": bar["start"].strftime("%H:%M"),
        "close_time_npt": (bar["start"] + datetime.timedelta(minutes=INTERVAL_MINUTES[interval])).strftime("%H:%M"),
        "close": round(bar["close"], 4),
        "distance_to_level": round(bar["close"] - level, 4),
        "volume": bar["volume"],
    }


def describe(result):
    lines = ["NEPSE ENTRY PRACTICE | %s | %s NPT" % (
        result["symbol"], result["as_of_npt"]),
        "Data: user-supplied CSV; offline practice only, not a live quote.",
    ]
    if result.get("as_of_source") == "last CSV candle close (inferred)":
        lines.append("Replay time assumed from the final CSV candle close; pass --as-of to inspect an earlier point.")
    lines.append("Assumed regular session: %s-%s NPT. %s" % (
        result["session_open_npt"], result["session_close_npt"], result["calendar_note"]))
    opening = result.get("opening_range")
    if opening:
        lines.append("Opening range %s-%s NPT: high NPR %.4f, low NPR %.4f (%d/%d bars)." % (
            opening["start_npt"], opening["end_npt"], opening["high"], opening["low"],
            opening["bars"], opening["expected_bars"]))
        lines.append("Practice level: NPR %.4f (%s)." % (
            result["level"], "opening-range high" if result["setup"] == "orb" else "your supplied level"))
    if result["status"] == "triggered":
        trigger = result["trigger"]
        lines.append("PRACTICE CONDITION MET at %s NPT: the %s candle closed at NPR %.4f, %.4f (%.3f%%) above the level." % (
            trigger["time_npt"], trigger["bar_start_npt"], trigger["close"],
            trigger["amount_above"], trigger["pct_above"]))
        lines.append("This is a rule check, not an instruction to buy. The candle close matters; a wick above the level alone would not count.")
    else:
        lines.append("%s: %s." % (result["status"].upper(), result["reason"]))
        last = result.get("last")
        if last:
            relative = "above" if last["distance_to_level"] > 0 else "below"
            if last["distance_to_level"] == 0:
                relative = "at"
            lines.append("Last completed candle: %s NPT close NPR %.4f, NPR %.4f %s the level." % (
                last["close_time_npt"], last["close"], abs(last["distance_to_level"]), relative))
    lines.extend([
        "Learning: only a fully closed candle can confirm this setup; the high/low wick is not the close.",
        "Next practice step: mark the range high and low on your chart, then explain what would invalidate the idea before considering any risk.",
        result["safety_note"],
    ])
    return lines


def write_json(path, result):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="NEPSE Entry Practice: evaluate user-supplied candles, offline only.")
    sub = parser.add_subparsers(dest="command")
    check = sub.add_parser("check", help="check a practice setup from one session of CSV candles")
    check.add_argument("symbol", help="NEPSE symbol or DEMO label")
    check.add_argument("--candles", required=True, help="CSV with timestamp,open,high,low,close[,volume]")
    check.add_argument("--interval", choices=sorted(INTERVAL_MINUTES), default="5m")
    check.add_argument("--as-of", help="replay time in Nepal local time, e.g. '2026-11-13 11:20'")
    check.add_argument("--setup", choices=("orb", "level"), default="orb")
    check.add_argument("--or-minutes", type=int, default=15)
    check.add_argument("--level", type=float, help="price to close above when --setup level")
    check.add_argument("--min-volume-x", type=float, help="trigger candle volume vs opening-range average")
    check.add_argument("--session-open", default="11:00", help="assumed regular session open in NPT")
    check.add_argument("--session-close", default="15:00", help="assumed regular session close in NPT")
    check.add_argument("--write", nargs="?", const="trader/nepse-entry.json", metavar="PATH",
                       help="write result JSON (default trader/nepse-entry.json)")
    check.add_argument("--json", action="store_true", help="print JSON rather than the learning report")
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1
    try:
        session_open = parse_hhmm(args.session_open, "--session-open")
        session_close = parse_hhmm(args.session_close, "--session-close")
        if session_close <= session_open:
            raise PracticeError("--session-close must be after --session-open")
        candles, day = read_candles(args.candles, args.interval, session_open, session_close)
        inferred_as_of = not args.as_of
        if args.as_of:
            as_of = parse_timestamp(args.as_of, "--as-of")
        else:
            as_of = max(bar["start"] for bar in candles) + datetime.timedelta(
                minutes=INTERVAL_MINUTES[args.interval])
        result = evaluate(args.symbol, candles, day, as_of, setup=args.setup, or_minutes=args.or_minutes,
                          interval=args.interval, level=args.level, min_volume_x=args.min_volume_x,
                          session_open=session_open, session_close=session_close)
        if inferred_as_of:
            result["as_of_source"] = "last CSV candle close (inferred)"
        if args.write:
            write_json(args.write, result)
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            for line in describe(result):
                print(line)
            if args.write:
                print("Wrote %s." % args.write)
        return 0 if result["status"] == "triggered" else 1
    except PracticeError as exc:
        print("nepse_practice.py: %s" % exc, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("nepse_practice.py: stopped." , file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
