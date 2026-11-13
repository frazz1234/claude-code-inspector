#!/usr/bin/env python3
"""
Build a realistic, made-up Claude Code setup in a folder, for screenshots and demos.

    python3 scripts/demo_home.py /tmp/cci-demo
    HOME=/tmp/cci-demo PATH="/tmp/cci-demo/.local/bin:$PATH" python3 cc_inspector.py --serve

Everything in it is fake: plugin names, servers, projects. It includes a few deliberate problems
(a missing MCP program, a skill without a description, a pile of settings backups) so the
health checks have something to show.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path

DAY = 86_400_000
NOW = int(time.time() * 1000)


def w(p: Path, text: str, mode: int | None = None):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    if mode:
        p.chmod(mode)


def skill(base: Path, name: str, desc: str | None):
    fm = f"---\nname: {name}\n" + (f"description: {desc}\n" if desc else "") + "---\n"
    w(base / name / "SKILL.md", fm + f"\n# {name}\n\nInstructions for the {name} skill.\n")


def build(home: Path):
    if home.exists():
        shutil.rmtree(home)
    cd = home / ".claude"
    plug = cd / "plugins"

    # ── plugins (two marketplaces) ──────────────────────────────────────────
    plugins = {
        "code-review-kit@acme-tools": dict(v="2.1.0", desc="Pull request reviews, security scans and changelogs.",
                                           skills={"review-pr": "Review a pull request for bugs, style and missing tests.",
                                                   "security-scan": "Look for leaked secrets and risky code before you commit.",
                                                   "changelog": "Write a changelog entry from recent commits."},
                                           hooks={"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/hooks/guard.sh"}]}]},
                                           on=True, uses=41),
        "docs-helper@acme-tools": dict(v="1.4.2", desc="Write and search documentation.",
                                       skills={"api-docs": "Generate API reference docs from source code.",
                                               "readme-writer": "Draft or refresh a README for the current project."},
                                       mcp={"docs-search": {"type": "http", "url": "https://docs-search.example.com/mcp"}},
                                       on=True, uses=12),
        "db-tools@acme-tools": dict(v="0.9.0", desc="Explain SQL and talk to a local Postgres.",
                                    skills={"sql-explain": "Explain what a SQL query does and how to speed it up."},
                                    mcp={"postgres": {"command": "pg-mcp-server", "args": ["--readonly"], "env": {"DATABASE_URL": "postgres://demo"}}},
                                    on=True, uses=0),
        "test-runner@acme-tools": dict(v="1.0.3", desc="Run tests, find flaky ones and fix failures.",
                                       commands={"run-tests": "Run the test suite and summarise failures.",
                                                 "flaky": "Find tests that fail only sometimes."},
                                       agents={"test-fixer": "Fixes failing tests one at a time."},
                                       on=False, uses=5),
        "git-helpers@community-plugins": dict(v="1.2.0", desc="Commit messages and branch cleanup.",
                                              skills={"commit-message": "Write a clear commit message from the staged diff.",
                                                      "branch-cleanup": "List and delete merged branches."},
                                              on=True, uses=23),
        "theme-pack@community-plugins": dict(v="3.0.0", desc="Status line themes.",
                                             hooks={"SessionStart": [{"hooks": [{"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/bin/theme.sh"}]}]},
                                             on=True, uses=7),
    }
    installed, enabled, usage, markets = {}, {}, {}, {}
    for pid, p in plugins.items():
        name, market = pid.split("@")
        root = plug / "cache" / market / name / p["v"]
        w(root / ".claude-plugin/plugin.json", json.dumps({"name": name, "version": p["v"], "description": p["desc"],
                                                            "author": {"name": "Demo Author"}}, indent=2))
        for s, d in p.get("skills", {}).items():
            skill(root / "skills", s, d)
        for c, d in p.get("commands", {}).items():
            w(root / "commands" / f"{c}.md", f"---\ndescription: {d}\n---\n{d}\n")
        for a, d in p.get("agents", {}).items():
            w(root / "agents" / f"{a}.md", f"---\nname: {a}\ndescription: {d}\n---\n{d}\n")
        if "hooks" in p:
            w(root / "hooks/hooks.json", json.dumps({"hooks": p["hooks"]}, indent=2))
            for g in p["hooks"].values():
                for h in g[0]["hooks"]:
                    w(root / h["command"].replace("${CLAUDE_PLUGIN_ROOT}/", ""), "#!/bin/sh\nexit 0\n", 0o755)
        if "mcp" in p:
            w(root / ".mcp.json", json.dumps({"mcpServers": p["mcp"]}, indent=2))
        installed[pid] = [{"scope": "user", "installPath": str(root), "version": p["v"],
                           "installedAt": "2026-09-02T10:00:00.000Z", "lastUpdated": "2026-11-01T09:30:00.000Z"}]
        enabled[pid] = p["on"]
        if p["uses"]:
            usage[pid] = {"usageCount": p["uses"], "lastUsedAt": NOW - p["uses"] * 3_600_000}
        markets.setdefault(market, {"source": {"source": "github", "repo": f"example/{market}"},
                                    "installLocation": str(plug / "marketplaces" / market), "lastUpdated": "2026-11-10T08:00:00.000Z"})
        (plug / "marketplaces" / market).mkdir(parents=True, exist_ok=True)
    w(plug / "installed_plugins.json", json.dumps({"version": 2, "plugins": installed}, indent=2))
    w(plug / "known_marketplaces.json", json.dumps(markets, indent=2))
    w(cd / "mcp-needs-auth-cache.json", json.dumps({"plugin:docs-helper:docs-search": {"timestamp": NOW}}))

    # ── your own skills, agents, commands, memory ──────────────────────────
    skill(cd / "skills", "weekly-report", "Summarise this week's commits and closed issues into a short report.")
    skill(cd / "skills", "deploy-checklist", "Walk through the release checklist before deploying to production.")
    skill(cd / "skills", "old-experiment", None)                        # no description -> health check
    w(cd / "agents/code-explainer.md", "---\nname: code-explainer\ndescription: Explains unfamiliar code in plain words.\nmodel: sonnet\n---\nExplain.\n")
    w(cd / "commands/standup.md", "---\ndescription: Draft my standup update from yesterday's work.\n---\nDraft it.\n")
    w(cd / "CLAUDE.md", "# My preferences\n\n- Use TypeScript strict mode.\n- Prefer small pull requests.\n- Use 24-hour times.\n")
    w(cd / "rules/testing.md", "Always add a test when fixing a bug.\n")
    w(cd / "statusline.sh", "#!/bin/sh\necho \"$(basename \"$PWD\")\"\n", 0o755)

    # ── settings: permissions, hooks, status line ──────────────────────────
    (home / "notes").mkdir(parents=True, exist_ok=True)
    settings = {
        "model": "opus",
        "permissions": {
            "allow": ["Bash(npm run test:*)", "Bash(git status)", "Bash(git diff:*)",
                      "WebFetch(domain:docs.python.org)", "Read(~/notes/**)"],
            "ask": ["Bash(git push:*)"],
            "deny": ["Bash(rm -rf:*)", "Read(./.env)"],
            "defaultMode": "acceptEdits",
            "additionalDirectories": [str(home / "notes")],
        },
        "hooks": {
            "PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "npx prettier --write \"$CLAUDE_FILE_PATHS\""}]}],
            "Stop": [{"hooks": [{"type": "command", "command": "afplay /System/Library/Sounds/Glass.aiff", "async": True}]}],
        },
        "statusLine": {"type": "command", "command": "~/.claude/statusline.sh"},
        "enabledPlugins": enabled,
        "env": {"GITHUB_TOKEN": "ghp_demo_token_value_is_hidden_123456"},
    }
    w(cd / "settings.json", json.dumps(settings, indent=2))
    for i in range(32):                                                   # backup pile-up -> health check
        w(cd / f"settings.json.backup-202611{1 + i % 12:02d}-{100000 + i:06d}", "{}")

    # ── ~/.claude.json: MCP servers, projects, usage ───────────────────────
    for proj in ("code/webapp", "code/api"):
        (home / proj).mkdir(parents=True, exist_ok=True)
    cj = {
        "installMethod": "native", "autoUpdates": True, "numStartups": 412, "firstStartVersion": "2.0.14",
        "mcpServers": {
            "context-docs": {"type": "http", "url": "https://context-docs.example.com/mcp"},
            "filesystem": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "~/notes"]},
            "local-notes": {"command": "notes-mcp", "args": ["--dir", "~/notes"]},   # not installed -> health check
        },
        "projects": {
            str(home / "code/webapp"): {"allowedTools": ["Bash(npm run dev)", "Bash(npx playwright test:*)"], "hasTrustDialogAccepted": True,
                                        "mcpServers": {"browser": {"command": "npx", "args": ["-y", "@playwright/mcp"]}}, "lastCost": 1.84},
            str(home / "code/api"): {"allowedTools": ["Bash(go test ./...)"], "hasTrustDialogAccepted": True, "lastCost": 0.62},
            str(home / "code/old-prototype"): {"allowedTools": [], "hasTrustDialogAccepted": False},
        },
        "skillUsage": {
            "code-review-kit:review-pr": {"usageCount": 34, "lastUsedAt": NOW - 2 * 3_600_000},
            "git-helpers:commit-message": {"usageCount": 27, "lastUsedAt": NOW - 5 * 3_600_000},
            "weekly-report": {"usageCount": 9, "lastUsedAt": NOW - 3 * DAY},
            "docs-helper:readme-writer": {"usageCount": 8, "lastUsedAt": NOW - 6 * DAY},
            "code-review-kit:security-scan": {"usageCount": 6, "lastUsedAt": NOW - 1 * DAY},
            "deploy-checklist": {"usageCount": 3, "lastUsedAt": NOW - 9 * DAY},
            "git-helpers:branch-cleanup": {"usageCount": 2, "lastUsedAt": NOW - 12 * DAY},
        },
        "pluginUsage": usage,
    }
    w(home / ".claude.json", json.dumps(cj, indent=2))

    # A `claude` shim inside the demo home, so screenshots show "~/.local/bin/claude"
    # instead of your real path. It just forwards to your real claude.
    real = shutil.which("claude")
    if real:
        shim = home / ".local/bin/claude"
        w(shim, f'#!/bin/sh\nexec "{real}" "$@"\n', 0o755)
    print(f"Demo setup written to {home}")
    print(f'Try it:  HOME="{home}" PATH="{home}/.local/bin:$PATH" python3 cc_inspector.py --serve')


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python3 scripts/demo_home.py <empty-or-throwaway-folder>")
    target = Path(sys.argv[1]).expanduser().resolve()
    if target == Path.home().resolve():
        sys.exit("Refusing to overwrite your real home folder.")
    if target.exists() and any(target.iterdir()) and not (target / ".claude").exists():
        sys.exit(f"{target} isn't empty and doesn't look like a demo home. Pick an empty folder.")
    build(target)
