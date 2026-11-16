import json
import os
import re
import unittest

from _load import ROOT

# The original U.S. pack remains intact alongside the NEPSE practice set.
SKILLS = ["trader-scanner", "trader-news", "trader-entry", "trader-exit", "trader-timemachine",
          "trader-risk", "trader-budget", "trader-broker", "trader-alerts", "trader-analyst",
          "trader-pelosi"]
NEPSE_SKILLS = ["nepse-scanner", "nepse-news", "nepse-entry", "nepse-exit", "nepse-timemachine",
                "nepse-risk", "nepse-budget", "nepse-broker", "nepse-alerts", "nepse-analyst",
                "nepse-disclosures"]
ALL_SKILLS = SKILLS + NEPSE_SKILLS
NEPSE_COUNTERPARTS = {
    "nepse-scanner": "trader-scanner",
    "nepse-news": "trader-news",
    "nepse-entry": "trader-entry",
    "nepse-exit": "trader-exit",
    "nepse-timemachine": "trader-timemachine",
    "nepse-risk": "trader-risk",
    "nepse-budget": "trader-budget",
    "nepse-broker": "trader-broker",
    "nepse-alerts": "trader-alerts",
    "nepse-analyst": "trader-analyst",
    "nepse-disclosures": "trader-pelosi",
}
ABOUT = ("22 Claude skills: the original 11 U.S. day-trading skills plus 11 offline NEPSE practice skills "
         "for user-supplied Nepal-market data.")
# skills on the way to an order carry the safety block
ORDER_PATH = ["trader-scanner", "trader-entry", "trader-exit", "trader-timemachine", "trader-budget",
              "trader-pelosi", "trader-risk", "trader-broker", "trader-alerts"]
V1_ONLY = ["trader-copycat", "trader-screener", "trader-tax", "trader-rebalance"]


def frontmatter(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (m.group(1) if m else ""), text


def every_text_file():
    for base, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in files:
            if f.endswith((".md", ".py", ".json", ".csv", ".txt", ".xml")) or f == "LICENSE":
                yield os.path.join(base, f)


class Repo(unittest.TestCase):
    def test_both_eleven_skill_sets_are_present_at_the_root(self):
        found = sorted(d for d in os.listdir(ROOT)
                       if os.path.isfile(os.path.join(ROOT, d, "SKILL.md")))
        self.assertEqual(found, sorted(ALL_SKILLS))

    def test_root_contains_the_original_repo_plus_nepse_tools(self):
        root = sorted(d for d in os.listdir(ROOT) if d != ".git")
        expected = [".claude", ".claude-plugin", ".gitignore", "LICENSE", "README.md",
                    "nepse_tools", "tests"] + ALL_SKILLS
        self.assertEqual(root, sorted(expected))

    def test_project_local_skills_are_installed_and_match_sources(self):
        installed_root = os.path.join(ROOT, ".claude", "skills")
        found = sorted(d for d in os.listdir(installed_root)
                       if os.path.isfile(os.path.join(installed_root, d, "SKILL.md")))
        self.assertEqual(found, sorted(ALL_SKILLS))

        for skill in ALL_SKILLS:
            source = os.path.join(ROOT, skill)
            installed = os.path.join(installed_root, skill)
            source_files = {}
            installed_files = {}
            for base, dirs, files in os.walk(source):
                dirs[:] = sorted(d for d in dirs if d != "__pycache__")
                for filename in files:
                    path = os.path.join(base, filename)
                    relative = os.path.relpath(path, source)
                    with open(path, "rb") as fh:
                        source_files[relative] = fh.read()
            for base, dirs, files in os.walk(installed):
                dirs[:] = sorted(d for d in dirs if d != "__pycache__")
                for filename in files:
                    path = os.path.join(base, filename)
                    relative = os.path.relpath(path, installed)
                    with open(path, "rb") as fh:
                        installed_files[relative] = fh.read()
            self.assertEqual(installed_files, source_files, skill)

    def test_nepse_set_is_a_one_to_one_adaptation_of_the_original_set(self):
        self.assertEqual(set(NEPSE_COUNTERPARTS), set(NEPSE_SKILLS))
        self.assertEqual(set(NEPSE_COUNTERPARTS.values()), set(SKILLS))
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = " ".join(fh.read().split())
        for nepse_skill, original_skill in NEPSE_COUNTERPARTS.items():
            self.assertTrue(os.path.isfile(os.path.join(ROOT, nepse_skill, "SKILL.md")), nepse_skill)
            self.assertTrue(os.path.isfile(os.path.join(ROOT, original_skill, "SKILL.md")), original_skill)
            self.assertIn("| `/%s` | `/%s` |" % (nepse_skill, original_skill), readme)

    def test_frontmatter_name_and_description(self):
        for s in ALL_SKILLS:
            fm, text = frontmatter(os.path.join(ROOT, s, "SKILL.md"))
            self.assertIn("name: %s\n" % s, fm + "\n", s)
            self.assertRegex(fm, r"description: ", s)
            self.assertGreater(len(fm), 200, "%s description is too thin" % s)
            self.assertGreater(len(text.splitlines()), 60, s)

    def test_order_path_skills_carry_the_safety_rule(self):
        for s in ORDER_PATH:
            _, text = frontmatter(os.path.join(ROOT, s, "SKILL.md"))
            low = " ".join(text.lower().split())
            self.assertIn("not financial advice", low, s)
            self.assertIn("yes", low, s)

    def test_plugin_manifest_points_at_the_root_skills(self):
        with open(os.path.join(ROOT, ".claude-plugin", "plugin.json")) as fh:
            plugin = json.load(fh)
        self.assertEqual(plugin["name"], "day-trader-skill")
        self.assertEqual(plugin["skills"], "./")
        self.assertEqual(plugin["description"], ABOUT)
        with open(os.path.join(ROOT, ".claude-plugin", "marketplace.json")) as fh:
            market = json.load(fh)
        self.assertEqual(market["name"], "day-trader-skill")
        self.assertEqual(market["plugins"][0]["name"], "day-trader-skill")

    def test_readme_carries_the_reel_copy(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = " ".join(fh.read().split())
        self.assertTrue(readme.startswith("# The Day Trader skill"))
        for line in (ABOUT,
                     "https://github.com/Jakeschincariol/day-trader-skill install skill",
                     "/plugin marketplace add Jakeschincariol/day-trader-skill",
                     "/plugin install day-trader-skill@day-trader-skill",
                     "## Fine print"):
            self.assertIn(line, readme)
        for s in ALL_SKILLS:
            self.assertIn("/" + s, readme, s)

    def test_readme_explains_access_from_this_fork(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = " ".join(fh.read().split())
        for instruction in (
                "This fork includes all 22 skills under `.claude/skills/`.",
                "open this repository's root directory in Claude Code.",
                "cd /path/to/day-trader-skill claude",
                "No extra plugin installation or copying is needed in this repository.",
                "reopen the project or restart the session.",
                "/nepse-scanner", "/nepse-entry", "/nepse-disclosures"):
            self.assertIn(instruction, readme)

    def test_readme_documents_the_full_offline_nepse_set(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
            readme = " ".join(fh.read().split())
        for instruction in (
                "The eleven NEPSE practice skills",
                "nepse_tools/cli.py",
                "timestamp,open,high,low,close",
                "UTC+05:45",
                "do not fetch NEPSE prices",
                "no TMS or broker connection",
                "20+ full prior sessions",
                "synthetic"):
            self.assertIn(instruction, readme)
        for skill in NEPSE_SKILLS:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, skill, "SKILL.md")), skill)
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "nepse_tools", "cli.py")))
        self.assertTrue(os.path.isfile(os.path.join(ROOT, "trader-entry", "nepse_practice.py")))

    def test_entry_skill_routes_nepse_to_offline_practice(self):
        _, text = frontmatter(os.path.join(ROOT, "trader-entry", "SKILL.md"))
        text = " ".join(text.split())
        self.assertIn("nepse_practice.py", text)
        self.assertIn("do not run the U.S. Yahoo/NYSE entry logic on a NEPSE symbol", text)
        self.assertIn("Do not pass a NEPSE result to the U.S.-only", text)

    def test_no_em_dashes_and_no_personal_email(self):
        for path in every_text_file():
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            rel = os.path.relpath(path, ROOT)
            if not rel.startswith(os.path.join("tests", "fixtures")):  # fixtures are real data, kept as published
                self.assertNotIn("\u2014", text, rel)
            self.assertNotIn("jakeschincariol" + "@" + "gmail.com", text, rel)  # built, so this file passes too

    def test_no_v1_only_skill_is_left_behind(self):
        for path in every_text_file():
            rel = os.path.relpath(path, ROOT)
            if rel.startswith("tests" + os.sep) or rel == "README.md":
                continue  # the README points v1 users to the v1 commit
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            for old in V1_ONLY:
                self.assertNotIn(old, text, rel)

    def test_every_tool_runs_on_python_3_8(self):
        # no 3.9+ only modules or syntax in the tools (the README promises 3.8)
        sources = []
        for skill in ALL_SKILLS:
            folder = os.path.join(ROOT, skill)
            sources.extend(os.path.join(folder, filename) for filename in os.listdir(folder)
                           if filename.endswith(".py"))
        sources.append(os.path.join(ROOT, "nepse_tools", "cli.py"))
        for path in sources:
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            for bad in ("import zoneinfo", "from zoneinfo", ".removeprefix(", ".removesuffix(",
                        "match ", "list[", "dict[", "tuple["):
                if bad == "match ":
                    self.assertNotRegex(src, r"(?m)^\s+match \w+.*:$", path)
                elif bad.endswith("["):
                    self.assertNotRegex(src, r"(?<![\w.])%s" % re.escape(bad), path)
                else:
                    self.assertNotIn(bad, src, path)

    def test_day_trading_limits_ship_in_the_example_config(self):
        with open(os.path.join(ROOT, "trader-budget", "config.example.json")) as fh:
            cfg = json.load(fh)
        for k in ("max_loss_per_trade_usd", "max_daily_loss_usd", "max_trades_per_day",
                  "min_reward_risk", "require_stop", "no_entries_after", "flat_by"):
            self.assertIn(k, cfg, k)
        self.assertIs(cfg["require_stop"], True)
        self.assertIs(cfg.get("allow_short", False), False)
        self.assertIs(cfg.get("allow_margin", False), False)

    def test_paper_trading_is_the_default(self):
        with open(os.path.join(ROOT, "trader-budget", "config.example.json")) as fh:
            cfg = json.load(fh)
        self.assertIs(cfg["paper"], True)
        self.assertIs(cfg.get("allow_options", False), False)


if __name__ == "__main__":
    unittest.main()
