"""
Tests for cc_inspector. Standard library only — run with:

    python3 -m unittest discover -s tests -v

Every test builds a throwaway fake home folder, so your real ~/.claude is never read or changed.
Actions that need the `claude` CLI (plugins, MCP) aren't covered here; everything else is.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cc_inspector as ci  # noqa: E402

SETTINGS = {
    "permissions": {"allow": ["Bash(npm test:*)", "Bash(ls:*)"], "deny": ["Bash(rm -rf:*)"]},
    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo one"},
                                  {"type": "command", "command": "echo two"}]}]},
    "statusLine": {"type": "command", "command": "echo status"},
    "env": {"MY_TOKEN": "sk-should-never-appear-in-output-1234567890"},
}
CLAUDE_JSON = {
    "mcpServers": {
        "remote": {"type": "http", "url": "https://example.com/mcp", "headers": {"Authorization": "Bearer secret-value-123"}},
        "local-tool": {"command": "definitely-not-a-real-program-xyz", "env": {"API_KEY": "sk-abcdefghijklmnop"}},
    },
    "skillUsage": {"hello": {"usageCount": 3, "lastUsedAt": 1790000000000}},
}


def write(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class FakeHome(unittest.TestCase):
    """Points the module at a fresh fake home for each test."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="cci-test-"))
        self.home = self.tmp / "home"
        cd = self.home / ".claude"
        write(cd / "settings.json", json.dumps(SETTINGS, indent=2))
        write(self.home / ".claude.json", json.dumps(CLAUDE_JSON))
        write(cd / "skills/hello/SKILL.md", "---\nname: hello\ndescription: Says hello.\n---\nHi\n")
        write(cd / "skills/no-desc/SKILL.md", "---\nname: no-desc\n---\nHi\n")
        write(cd / "agents/helper.md", "---\nname: helper\ndescription: Helps.\n---\nHi\n")
        write(cd / "CLAUDE.md", "Be nice.\n")
        write(cd / ".credentials.json", '{"secret": "nope"}')
        self._saved = (ci.HOME, ci.CLAUDE_DIR, ci.CLAUDE_JSON)
        ci.HOME, ci.CLAUDE_DIR, ci.CLAUDE_JSON = self.home, cd, self.home / ".claude.json"
        self.cd = cd

    def tearDown(self):
        ci.HOME, ci.CLAUDE_DIR, ci.CLAUDE_JSON = self._saved
        shutil.rmtree(self.tmp, ignore_errors=True)

    def scan(self):
        return ci.build(None, False)


class TestScan(FakeHome):
    def test_empty_home_does_not_crash(self):
        shutil.rmtree(self.home)
        self.home.mkdir()
        rep = self.scan()
        self.assertEqual(rep["stats"]["skills"], 0)
        self.assertEqual(rep["stats"]["mcp"], 0)

    def test_finds_everything(self):
        rep = self.scan()
        self.assertEqual({s["name"] for s in rep["skills"]}, {"hello", "no-desc"})
        self.assertEqual([i["name"] for i in rep["items"]], ["helper"])
        self.assertEqual({m["name"] for m in rep["mcp"]}, {"remote", "local-tool"})
        self.assertEqual(len([h for h in rep["hooks"] if h["event"] == "Stop"]), 2)
        self.assertTrue(any(h["event"] == "statusLine" for h in rep["hooks"]))
        self.assertEqual(rep["stats"]["allowRules"], 2)
        self.assertEqual(rep["stats"]["denyRules"], 1)
        self.assertEqual(len(rep["memory"]), 1)

    def test_usage_counts(self):
        hello = next(s for s in self.scan()["skills"] if s["name"] == "hello")
        self.assertEqual(hello["uses"], 3)

    def test_health_checks(self):
        msgs = " ".join(i["msg"] for i in self.scan()["issues"])
        self.assertIn("definitely-not-a-real-program-xyz", msgs)      # missing MCP command
        self.assertIn("no-desc: missing description", msgs)            # skill without description

    def test_secrets_never_in_output(self):
        dumped = json.dumps(self.scan(), default=str)
        for secret in ("sk-should-never-appear", "secret-value-123", "sk-abcdefghijklmnop"):
            self.assertNotIn(secret, dumped)

    def test_actions_offered(self):
        rep = self.scan()
        self.assertEqual(next(s for s in rep["skills"] if s["name"] == "hello")["act"], ["disable", "delete"])
        self.assertEqual(next(m for m in rep["mcp"] if m["name"] == "remote")["act"], ["remove", "login", "logout"])
        self.assertEqual(next(m for m in rep["mcp"] if m["name"] == "local-tool")["act"], ["remove"])
        self.assertTrue(all(h["act"] == ["remove"] for h in rep["hooks"]))

    def test_html_report_renders(self):
        html = ci.render_html(self.scan(), False)
        self.assertNotIn("__DATA__", html)
        self.assertNotIn("__LIVE__", html)
        self.assertNotIn("__TOKEN__", html)
        self.assertNotIn("sk-should-never-appear", html)


class TestFileViewerSafety(FakeHome):
    def test_allows_files_inside_claude_dir(self):
        self.assertIsNotNone(ci.safe_path(str(self.cd / "skills/hello/SKILL.md"), None))

    def test_blocks_outside_and_traversal(self):
        self.assertIsNone(ci.safe_path("/etc/passwd", None))
        self.assertIsNone(ci.safe_path(str(self.cd / ".." / ".ssh" / "id_rsa"), None))
        self.assertIsNone(ci.safe_path(str(self.cd / "skills/hello/../../../x"), None))

    def test_blocks_credential_files(self):
        self.assertIsNone(ci.safe_path(str(self.cd / ".credentials.json"), None))

    @unittest.skipIf(sys.platform == "win32", "symlinks need admin rights on Windows")
    def test_follows_symlinked_skill(self):
        outside = self.tmp / "elsewhere/linked"
        write(outside / "SKILL.md", "---\nname: linked\ndescription: x\n---\n")
        os.symlink(outside, self.cd / "skills/linked")
        self.assertIsNotNone(ci.safe_path(str(self.cd / "skills/linked/SKILL.md"), None))

    def test_redact_json(self):
        out = ci.redact_json({"env": {"A": "1"}, "headers": {"B": "2"}, "apiKey": "x", "author": "Ann", "n": 1})
        self.assertEqual(out["env"], {"A": "[redacted]"})
        self.assertEqual(out["headers"], {"B": "[redacted]"})
        self.assertEqual(out["apiKey"], "[redacted]")
        self.assertEqual(out["author"], "Ann")


class TestActions(FakeHome):
    def act(self, kind, match, action):
        rep = self.scan()
        pool = {"skill": rep["skills"], "item": rep["items"], "hook": rep["hooks"], "rule": rep["permissions"]["rules"]}[kind]
        rec = next(r for r in pool if match(r))
        return ci.do_action(kind, rec["ref"], action, None), rec

    def settings(self):
        return json.loads((self.cd / "settings.json").read_text())

    def test_skill_disable_enable(self):
        (ok, msg, _), _ = self.act("skill", lambda s: s["name"] == "hello", "disable")
        self.assertTrue(ok, msg)
        self.assertTrue((self.cd / "skills-disabled/hello/SKILL.md").exists())
        self.assertFalse(next(s for s in self.scan()["skills"] if s["name"] == "hello")["enabled"])
        (ok, msg, _), _ = self.act("skill", lambda s: s["name"] == "hello", "enable")
        self.assertTrue(ok, msg)
        self.assertTrue((self.cd / "skills/hello/SKILL.md").exists())

    def test_delete_goes_to_trash(self):
        (ok, msg, _), _ = self.act("item", lambda i: i["name"] == "helper", "delete")
        self.assertTrue(ok, msg)
        self.assertFalse((self.cd / "agents/helper.md").exists())
        self.assertIn("Trash", msg) if sys.platform != "win32" else None

    def test_remove_hook_keeps_rest_and_one_backup(self):
        (ok, msg, _), _ = self.act("hook", lambda h: h["command"] == "echo one", "remove")
        self.assertTrue(ok, msg)
        s = self.settings()
        self.assertEqual([h["command"] for h in s["hooks"]["Stop"][0]["hooks"]], ["echo two"])
        self.assertEqual(s["permissions"], SETTINGS["permissions"])      # other keys untouched
        self.assertEqual(s["env"], SETTINGS["env"])
        self.act("hook", lambda h: h["command"] == "echo two", "remove")
        self.assertNotIn("hooks", self.settings())                        # empty containers cleaned up
        self.assertEqual(len(list(self.cd.glob("settings.json.cci-*"))), 1)

    def test_remove_status_line(self):
        (ok, msg, _), _ = self.act("hook", lambda h: h["event"] == "statusLine", "remove")
        self.assertTrue(ok, msg)
        self.assertNotIn("statusLine", self.settings())

    def test_remove_rule(self):
        (ok, msg, _), _ = self.act("rule", lambda r: r["rule"] == "Bash(ls:*)", "remove")
        self.assertTrue(ok, msg)
        self.assertEqual(self.settings()["permissions"]["allow"], ["Bash(npm test:*)"])

    def test_stale_item_is_refused(self):
        rep = self.scan()
        two = next(h for h in rep["hooks"] if h["command"] == "echo two")
        self.act("hook", lambda h: h["command"] == "echo one", "remove")   # shifts "two" to index 0
        ok, msg, _ = ci.do_action("hook", two["ref"], "remove", None)
        self.assertFalse(ok)
        self.assertEqual(self.settings()["hooks"]["Stop"][0]["hooks"][0]["command"], "echo two")

    def test_unknown_ref_and_disallowed_action_refused(self):
        self.assertFalse(ci.do_action("skill", str(self.home / ".ssh"), "delete", None)[0])
        rep = self.scan()
        mcp = next(m for m in rep["mcp"] if m["name"] == "local-tool")
        self.assertFalse(ci.do_action("mcp", mcp["ref"], "login", None)[0])   # stdio servers can't log in


class TestParsing(unittest.TestCase):
    def test_parse_mcp_list(self):
        out = ci.parse_mcp_list(
            "Checking MCP server health…\n\n"
            "plugin:savvy:Savant V1: https://x.io/mcp (HTTP) - ! Needs authentication\n"
            "ctx: https://c.com/mcp (HTTP) - ✔ Connected\n"
            "plugin:data:snowflake:  (HTTP) - - Not configured\n"
            "broken: bun run x - ✘ Failed to connect\n")
        self.assertEqual(out["plugin:savvy:Savant V1"]["status"], "auth")
        self.assertEqual(out["ctx"]["status"], "connected")
        self.assertEqual(out["plugin:data:snowflake"]["status"], "off")
        self.assertEqual(out["broken"]["status"], "failed")

    def test_frontmatter(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "SKILL.md"
            p.write_text("---\nname: x\ndescription: >\n  folded\n  text\n---\nbody")
            fm = ci.parse_frontmatter(p)
            self.assertEqual(fm["name"], "x")
            self.assertEqual(fm["description"], "folded text")


if __name__ == "__main__":
    unittest.main()
