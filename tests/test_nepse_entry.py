import csv
import datetime
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from _load import FIX, load

nepse = load("trader-entry", "nepse_practice")
DEMO = os.path.join(FIX, "trader-entry", "NEPSE-DEMO-5m.csv")
DAY = datetime.date(2026, 11, 13)


def candles(path=DEMO, interval="5m"):
    return nepse.read_candles(path, interval, datetime.time(11, 0), datetime.time(15, 0))


def as_of(text):
    return nepse.parse_timestamp(text, "--as-of")


def write_rows(rows):
    tmp = tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8", delete=False)
    try:
        writer = csv.writer(tmp)
        writer.writerow(("timestamp", "open", "high", "low", "close", "volume"))
        writer.writerows(rows)
        return tmp.name
    finally:
        tmp.close()


class NepsePractice(unittest.TestCase):
    def test_demo_triggers_only_after_the_1115_candle_closes(self):
        bars, day = candles()
        result = nepse.evaluate("DEMO", bars, day, as_of("2026-11-13 11:20"))
        self.assertEqual(result["status"], "triggered")
        self.assertEqual(result["opening_range"]["high"], 104.0)
        self.assertEqual(result["opening_range"]["low"], 99.0)
        self.assertEqual(result["trigger"]["bar_start_npt"], "11:15")
        self.assertEqual(result["trigger"]["time_npt"], "11:20")
        self.assertEqual(result["trigger"]["close"], 105.0)
        report = "\n".join(nepse.describe(result))
        self.assertIn("PRACTICE CONDITION MET", report)
        self.assertIn("not an instruction to buy", report)
        self.assertIn("offline practice only", report)

    def test_forming_bar_does_not_trigger_early(self):
        bars, day = candles()
        result = nepse.evaluate("DEMO", bars, day, as_of("2026-11-13 11:19"))
        self.assertEqual(result["status"], "waiting")
        self.assertIsNone(result["trigger"])
        self.assertEqual(result["last"]["close_time_npt"], "11:15")

    def test_a_wick_above_the_level_is_not_a_trigger(self):
        path = write_rows([
            ("2026-11-13 11:00", 100, 102, 99, 101, 1200),
            ("2026-11-13 11:05", 101, 103, 100, 102, 900),
            ("2026-11-13 11:10", 102, 104, 101, 103, 800),
            ("2026-11-13 11:15", 103, 106, 102, 103.5, 1400),
        ])
        try:
            bars, day = candles(path)
            result = nepse.evaluate("DEMO", bars, day, as_of("2026-11-13 11:20"))
            self.assertEqual(result["status"], "waiting")
            self.assertIsNone(result["trigger"])
        finally:
            os.unlink(path)

    def test_missing_opening_range_candle_is_incomplete_not_guessed(self):
        path = write_rows([
            ("2026-11-13 11:00", 100, 102, 99, 101, 1200),
            ("2026-11-13 11:10", 102, 104, 101, 103, 800),
            ("2026-11-13 11:15", 103, 106, 102, 105, 1400),
        ])
        try:
            bars, day = candles(path)
            result = nepse.evaluate("DEMO", bars, day, as_of("2026-11-13 11:20"))
            self.assertEqual(result["status"], "incomplete")
            self.assertIn("11:05", result["reason"])
            self.assertIsNone(result["trigger"])
        finally:
            os.unlink(path)

    def test_missing_post_range_candle_prevents_first_trigger_claim(self):
        path = write_rows([
            ("2026-11-13 11:00", 100, 102, 99, 101, 1200),
            ("2026-11-13 11:05", 101, 103, 100, 102, 900),
            ("2026-11-13 11:10", 102, 104, 101, 103, 800),
            ("2026-11-13 11:20", 103, 106, 102, 105, 1400),
        ])
        try:
            bars, day = candles(path)
            result = nepse.evaluate("DEMO", bars, day, as_of("2026-11-13 11:25"))
            self.assertEqual(result["status"], "incomplete")
            self.assertIn("11:15", result["reason"])
            self.assertIsNone(result["trigger"])
        finally:
            os.unlink(path)

    def test_level_setup_uses_the_supplied_level(self):
        bars, day = candles()
        result = nepse.evaluate("DEMO", bars, day, as_of("2026-11-13 11:20"),
                                setup="level", level=104.5)
        self.assertEqual(result["status"], "triggered")
        self.assertEqual(result["trigger"]["level"], 104.5)

    def test_volume_filter_is_optional_and_needs_volume(self):
        bars, day = candles()
        result = nepse.evaluate("DEMO", bars, day, as_of("2026-11-13 11:20"), min_volume_x=1.4)
        self.assertEqual(result["status"], "triggered")
        result = nepse.evaluate("DEMO", bars, day, as_of("2026-11-13 11:20"), min_volume_x=2.0)
        self.assertEqual(result["status"], "waiting")
        self.assertIn("volume was 1.45x", result["reason"])

    def test_npt_naive_and_utc_timestamps_are_normalized(self):
        local = as_of("2026-11-13 11:15")
        utc = as_of("2026-11-13T05:30:00Z")
        self.assertEqual(local, utc)
        self.assertEqual(local.strftime("%H:%M"), "11:15")

    def test_wrong_as_of_date_is_rejected(self):
        bars, day = candles()
        with self.assertRaises(nepse.PracticeError):
            nepse.evaluate("DEMO", bars, day, as_of("2026-11-14 11:20"))

    def test_command_outputs_plain_language_practice_result(self):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = nepse.main(["check", "DEMO", "--candles", DEMO, "--interval", "5m",
                               "--as-of", "2026-11-13 11:20"])
        self.assertEqual(code, 0)
        self.assertIn("NEPSE ENTRY PRACTICE | DEMO", out.getvalue())
        self.assertIn("PRACTICE CONDITION MET", out.getvalue())
        self.assertEqual(err.getvalue(), "")

    def test_omitted_as_of_uses_and_labels_the_last_candle_close(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = nepse.main(["check", "DEMO", "--candles", DEMO, "--interval", "5m"])
        self.assertEqual(code, 0)
        self.assertIn("2026-11-13 11:25:00 NPT", out.getvalue())
        self.assertIn("Replay time assumed from the final CSV candle close", out.getvalue())

    def test_invalid_ohlc_is_refused(self):
        path = write_rows([
            ("2026-11-13 11:00", 100, 98, 99, 101, 1200),
        ])
        try:
            with self.assertRaises(nepse.PracticeError):
                candles(path)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
