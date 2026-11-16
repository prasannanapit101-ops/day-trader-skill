import csv
import datetime
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from _load import FIX, ROOT, load
from nepse_tools import cli

DEMO = os.path.join(ROOT, "nepse_tools", "examples", "candles", "DEMO.csv")
ENTRY = load("trader-entry", "nepse_practice")


def invoke(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


def write_csv(path, headers, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
    return path


def entry_result():
    bars, day = ENTRY.read_candles(DEMO, "5m", datetime.time(11, 0), datetime.time(15, 0))
    return ENTRY.evaluate("DEMO", bars, day, ENTRY.parse_timestamp("2026-11-13 11:20", "--as-of"))


def plan_from_entry():
    result = entry_result()
    stop = (result["opening_range"]["high"] + result["opening_range"]["low"]) / 2
    entry = result["trigger"]["close"]
    risk = entry - stop
    return {"market": "NEPSE", "currency": "NPR", "symbol": "DEMO", "side": "BUY",
            "date": result["date"], "setup": "orb", "interval": "5m",
            "entry": entry, "entry_time_npt": result["trigger"]["time_npt"],
            "entry_bar_start_npt": result["trigger"]["bar_start_npt"],
            "stop": stop, "target": entry + risk, "risk_per_share": risk,
            "target_r": 1.0, "stop_method": "or-mid", "or_minutes": 15,
            "opening_range": result["opening_range"], "practice_only": True, "order_placed": False}


def previous_weekdays(day, count):
    found = []
    current = day - datetime.timedelta(days=1)
    while len(found) < count:
        if current.weekday() < 5:
            found.append(current)
        current -= datetime.timedelta(days=1)
    return sorted(found)


def synthetic_session(day):
    rows = []
    for index in range(48):
        stamp = datetime.datetime.combine(day, datetime.time(11, 0)) + datetime.timedelta(minutes=5 * index)
        if index < 3:
            o, h, low, close = 100, 101, 99, 100
        elif index == 3:
            o, h, low, close = 100, 103, 100, 102
        elif index == 4:
            o, h, low, close = 102, 104, 101, 103
        else:
            o, h, low, close = 103, 103.5, 102.5, 103
        rows.append((stamp.strftime("%Y-%m-%d %H:%M"), o, h, low, close, 1000 + index))
    return rows


class NepseParsing(unittest.TestCase):
    def test_naive_timestamps_mean_npt_and_offsets_are_converted(self):
        local = cli.parse_npt("2026-11-13 11:15")
        utc = cli.parse_npt("2026-11-13T05:30:00Z")
        offset = cli.parse_npt("2026-11-13T11:15:00+05:45")
        self.assertEqual(local, utc)
        self.assertEqual(local, offset)

    def test_ohlcv_reader_sorts_and_filters_out_of_session_bars(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "one.csv")
            write_csv(path, ["timestamp", "open", "high", "low", "close"], [
                ("2026-11-13 10:55", 100, 101, 99, 100),
                ("2026-11-13 11:05", 101, 103, 100, 102),
                ("2026-11-13 11:00", 100, 102, 99, 101),
            ])
            bars = cli.read_ohlcv(path, 5)
            self.assertEqual([bar["start"].strftime("%H:%M") for bar in bars], ["11:00", "11:05"])

    def test_duplicate_off_grid_and_inconsistent_bars_are_rejected(self):
        cases = [
            [("2026-11-13 11:00", 100, 102, 99, 101), ("2026-11-13 11:00", 101, 103, 100, 102)],
            [("2026-11-13 11:01", 100, 102, 99, 101)],
            [("2026-11-13 11:00", 100, 98, 99, 101)],
        ]
        for rows in cases:
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as folder:
                path = os.path.join(folder, "bad.csv")
                write_csv(path, ["timestamp", "open", "high", "low", "close"], rows)
                with self.assertRaises(cli.NepseError):
                    cli.read_ohlcv(path, 5)

    def test_json_record_lists_must_contain_objects(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "bad.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(["not an object"], fh)
            with self.assertRaises(cli.NepseError):
                cli.read_records(path)


class NepseSkills(unittest.TestCase):
    def test_scan_reads_the_synthetic_symbol_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            import shutil
            shutil.copyfile(DEMO, os.path.join(folder, "DEMO.csv"))
            code, out, err = invoke(["scan", "--candles-dir", folder, "--as-of", "2026-11-13 11:20"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("DEMO       triggered", out)
        self.assertIn("NPR 104.00", out)
        self.assertIn("did not fetch prices", out)

    def test_scan_rejects_invalid_session_and_time(self):
        code, out, err = invoke(["scan", "--candles-dir", os.path.dirname(DEMO),
                                 "--as-of", "not-a-time"])
        self.assertEqual(code, 2)
        self.assertIn("--as-of", err)
        code, out, err = invoke(["scan", "--candles-dir", os.path.dirname(DEMO),
                                 "--as-of", "2026-11-13 11:20", "--session-open", "15:00",
                                 "--session-close", "11:00"])
        self.assertEqual(code, 2)
        self.assertIn("session-close", err)

    def test_entry_subcommand_delegates_to_offline_helper(self):
        result = subprocess.run([sys.executable, os.path.join(ROOT, "nepse_tools", "cli.py"),
                                 "entry", "check", "DEMO", "--candles", DEMO,
                                 "--as-of", "2026-11-13 11:20", "--json"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        doc = json.loads(result.stdout)
        self.assertEqual(doc["market"], "NEPSE")
        self.assertEqual(doc["status"], "triggered")

    def test_news_review_preserves_source_and_tags_headline(self):
        path = os.path.join(ROOT, "nepse_tools", "examples", "news.example.csv")
        code, out, err = invoke(["news", "--file", path, "--symbol", "DEMO"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("financial-results", out)
        self.assertIn("Sample source", out)
        self.assertIn("example.invalid", out)
        self.assertIn("not sentiment", out)

    def test_exit_reads_entry_json_and_writes_reusable_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            entry_path = os.path.join(folder, "entry.json")
            plan_path = os.path.join(folder, "plan.json")
            with open(entry_path, "w", encoding="utf-8") as fh:
                json.dump(entry_result(), fh)
            code, out, err = invoke(["exit", "--from-entry", entry_path, "--write", plan_path])
            self.assertEqual(code, 0, err)
            self.assertIn("or-mid", out)
            self.assertIn("Nothing was placed", out)
            with open(plan_path, encoding="utf-8") as fh:
                plan = json.load(fh)
            self.assertEqual(plan["market"], "NEPSE")
            self.assertEqual(plan["symbol"], "DEMO")
            self.assertEqual(plan["entry"], 105.0)
            self.assertEqual(plan["stop"], 101.5)
            self.assertEqual(plan["target"], 108.5)
            self.assertIs(plan["order_placed"], False)

    def test_exit_rejects_nonpositive_and_ill_formed_inputs(self):
        code, out, err = invoke(["exit", "DEMO", "--entry", "10", "--stop", "10", "--target-r", "1"])
        self.assertEqual(code, 2)
        self.assertIn("entry above", err)
        code, out, err = invoke(["exit", "DEMO", "--entry", "nan", "--stop", "1"])
        self.assertEqual(code, 2)
        self.assertIn("non-finite", err)

    def test_time_machine_replay_is_repeatable_and_uses_history(self):
        with tempfile.TemporaryDirectory() as folder:
            candles_path = os.path.join(folder, "history.csv")
            plan_path = os.path.join(folder, "plan.json")
            output_path = os.path.join(folder, "replay.json")
            plan = plan_from_entry()
            history_rows = []
            for day in previous_weekdays(datetime.date(2026, 11, 13), 20):
                history_rows.extend(synthetic_session(day))
            with open(DEMO, newline="", encoding="utf-8") as demo_fh:
                history_rows.extend(list(csv.reader(demo_fh))[1:])
            write_csv(candles_path, ["timestamp", "open", "high", "low", "close", "volume"], history_rows)
            with open(plan_path, "w", encoding="utf-8") as fh:
                json.dump(plan, fh)
            args = ["timemachine", "--plan", plan_path, "--candles", candles_path,
                    "--replays", "50", "--seed", "19", "--window", "0",
                    "--write", output_path, "--json"]
            code, out, err = invoke(args)
            self.assertEqual(code, 0, err)
            self.assertIn("Prior full sessions: 20", out)
            self.assertIn("target 20", out)
            with open(output_path, encoding="utf-8") as fh:
                saved = json.load(fh)
            self.assertEqual(saved["history"]["setups"], 20)
            self.assertEqual(saved["history"]["targets"], 20)
            self.assertEqual(saved["bootstrap"]["seed"], 19)
            json_start = out.index("{\n", out.index("Wrote"))
            parsed1 = json.loads(out[json_start:])
            code2, out2, err2 = invoke(args[:-3] + ["--json"])
            self.assertEqual(code2, 0, err2)
            parsed2 = json.loads(out2[out2.index("{\n"):])
            self.assertEqual(parsed1["bootstrap"], parsed2["bootstrap"])

    def test_time_machine_requires_a_minimum_of_complete_prior_sessions(self):
        with tempfile.TemporaryDirectory() as folder:
            candles_path = os.path.join(folder, "history.csv")
            plan_path = os.path.join(folder, "plan.json")
            rows = synthetic_session(datetime.date(2026, 11, 12))
            with open(DEMO, newline="", encoding="utf-8") as demo_fh:
                rows.extend(list(csv.reader(demo_fh))[1:])
            write_csv(candles_path, ["timestamp", "open", "high", "low", "close", "volume"], rows)
            with open(plan_path, "w", encoding="utf-8") as fh:
                json.dump(plan_from_entry(), fh)
            code, out, err = invoke(["timemachine", "--plan", plan_path, "--candles", candles_path])
        self.assertEqual(code, 2)
        self.assertIn("complete prior session", err)

    def test_budget_reads_plan_and_writes_a_risk_checker_order(self):
        with tempfile.TemporaryDirectory() as folder:
            plan_path = os.path.join(folder, "plan.json")
            orders_path = os.path.join(folder, "orders.json")
            with open(plan_path, "w", encoding="utf-8") as fh:
                json.dump(plan_from_entry(), fh)
            code, out, err = invoke(["budget", "--plan", plan_path, "--capital", "100000",
                                     "--max-loss", "1200", "--write", orders_path])
            self.assertEqual(code, 0, err)
            self.assertIn("practice size: 342", out)
            with open(orders_path, encoding="utf-8") as fh:
                doc = json.load(fh)
            order = doc["orders"][0]
            self.assertEqual(order["quantity"], 342)
            self.assertEqual(order["entry"], 105)
            self.assertEqual(order["side"], "BUY")
            self.assertIs(order["paper_only"], True)

    def test_budget_returns_zero_size_without_creating_an_order(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "orders.json")
            code, out, err = invoke(["budget", "DEMO", "--capital", "100", "--max-loss", "1",
                                     "--entry", "105", "--stop", "99", "--write", path])
            self.assertEqual(code, 1)
            self.assertIn("No whole-share size fits", out)
            self.assertFalse(os.path.exists(path))

    def test_risk_checker_passes_only_with_positive_paper_limits(self):
        with tempfile.TemporaryDirectory() as folder:
            orders_path = os.path.join(folder, "orders.json")
            config_path = os.path.join(folder, "config.json")
            with open(orders_path, "w", encoding="utf-8") as fh:
                json.dump({"orders": [{"symbol": "DEMO", "side": "BUY", "quantity": 10,
                                       "entry": 105, "stop": 99, "target": 117}]}, fh)
            config = {"cash_npr": 10000, "max_loss_per_trade_npr": 100,
                      "max_daily_loss_npr": 300, "max_trades_per_day": 3,
                      "min_reward_risk": 1, "round_trip_fee_per_share_npr": 0,
                      "paper_only": True, "allow_short": False}
            with open(config_path, "w", encoding="utf-8") as fh:
                json.dump(config, fh)
            code, out, err = invoke(["risk", "--orders", orders_path, "--config", config_path])
            self.assertEqual(code, 0, err)
            self.assertIn("PASS DEMO", out)
            config["paper_only"] = False
            with open(config_path, "w", encoding="utf-8") as fh:
                json.dump(config, fh)
            code, out, err = invoke(["risk", "--orders", orders_path, "--config", config_path])
            self.assertEqual(code, 2)
            self.assertIn("paper_only must be true", err)

    def test_risk_checker_blocks_daily_limits_and_fractional_quantity(self):
        with tempfile.TemporaryDirectory() as folder:
            orders_path = os.path.join(folder, "orders.json")
            config_path = os.path.join(folder, "config.json")
            with open(orders_path, "w", encoding="utf-8") as fh:
                json.dump({"orders": [{"symbol": "DEMO", "side": "BUY", "quantity": 10.5,
                                       "entry": 105, "stop": 99, "target": 117}]}, fh)
            config = {"cash_npr": 10000, "max_loss_per_trade_npr": 100,
                      "max_daily_loss_npr": 5, "max_trades_per_day": 1,
                      "min_reward_risk": 1, "paper_only": True, "allow_short": False}
            with open(config_path, "w", encoding="utf-8") as fh:
                json.dump(config, fh)
            code, out, err = invoke(["risk", "--orders", orders_path, "--config", config_path])
            self.assertEqual(code, 1)
            self.assertIn("BLOCK DEMO", out)
            self.assertIn("whole number", out)
            self.assertIn("daily limit", out)

    def test_broker_builds_nonsent_paper_ticket_and_refuses_unowned_sale(self):
        with tempfile.TemporaryDirectory() as folder:
            order_path = os.path.join(folder, "order.json")
            with open(order_path, "w", encoding="utf-8") as fh:
                json.dump({"symbol": "DEMO", "side": "BUY", "quantity": 2,
                           "entry": 105}, fh)
            code, out, err = invoke(["broker", "--order", order_path])
            self.assertEqual(code, 0, err)
            self.assertIn("NOT PLACED", out)
            with open(order_path, "w", encoding="utf-8") as fh:
                json.dump({"symbol": "DEMO", "side": "SELL", "quantity": 3,
                           "limit_price": 105, "owned_shares": 2}, fh)
            code, out, err = invoke(["broker", "--order", order_path])
            self.assertEqual(code, 2)
            self.assertIn("owned_shares", err)

    def test_alerts_use_latest_supplied_timestamp_and_no_feed(self):
        with tempfile.TemporaryDirectory() as folder:
            prices = os.path.join(folder, "prices.csv")
            write_csv(prices, ["timestamp", "symbol", "price"], [
                ("2026-11-13 11:00", "DEMO", 90),
                ("2026-11-13 11:20", "DEMO", 105),
            ])
            rules = os.path.join(ROOT, "nepse_tools", "examples", "alerts.example.json")
            code, out, err = invoke(["alerts", "--rules", rules, "--prices", prices])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("2026-11-13 11:20", out)
        self.assertIn("no polling", out)

    def test_analyst_compares_supplied_periods_and_disclosures_filter(self):
        financials = os.path.join(ROOT, "nepse_tools", "examples", "financials.example.csv")
        code, out, err = invoke(["analyst", "--file", financials])
        self.assertEqual(code, 0, err)
        self.assertIn("+15.00%", out)
        self.assertIn("supplied figures only", out)
        notices = os.path.join(ROOT, "nepse_tools", "examples", "disclosures.example.csv")
        code, out, err = invoke(["disclosures", "--file", notices, "--symbol", "DEMO"])
        self.assertEqual(code, 0, err)
        self.assertIn("book-closure-or-agm", out)
        self.assertIn("public company/exchange notices", out)


if __name__ == "__main__":
    unittest.main()
