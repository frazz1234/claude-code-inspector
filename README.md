# Claude Code Inspector

[![Tests](https://github.com/frazz1234/claude-code-inspector/actions/workflows/ci.yml/badge.svg)](https://github.com/frazz1234/claude-code-inspector/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

See and manage everything that's installed in your [Claude Code](https://claude.com/claude-code) setup on one page: plugins, skills, MCP servers, hooks, permissions, agents, slash commands and memory files. It also runs health checks that find broken or messy config.

- **One Python file.** No dependencies, nothing to install.
- **Safe changes.** Turn things on or off, update, sign in, remove, delete. Every change asks you first, uses the official `claude` CLI where one exists, and can be undone where possible. Use `--read-only` to just look.
- **Private.** It runs only on your computer and sends nothing anywhere. Secret values (env vars, headers, tokens) are hidden in everything it shows.

## Quick start

```bash
git clone https://github.com/frazz1234/claude-code-inspector.git
cd claude-code-inspector
python3 cc_inspector.py --serve
```

Your browser opens at <http://127.0.0.1:8765>. Press `Ctrl+C` in the terminal to stop it.

Needs Python 3.9 or newer. Works on macOS, Linux and Windows. On Windows, use `py` or `python` instead of `python3`.

## What you get

| Page | What it shows |
| --- | --- |
| **Overview** | Summary cards, what needs attention, your most-used skills, your biggest plugins, version and install info |
| **Health checks** | Problems found in your setup, each with a suggested fix |
| **Plugins** | Every plugin (local, from a marketplace, built-in or synced from claude.ai): whether it's on or off, its version, what it contains, how often you've used it, plus your marketplaces |
| **Skills** | Every skill and where it comes from, how often you've used it, and problems with its frontmatter |
| **MCP servers** | Where each server is defined, its type, what it runs, whether that program is installed, and the names (not values) of its env vars and headers |
| **Permissions** | Allow, ask and deny rules from every settings file, the default mode, and extra folders Claude may access |
| **Projects** | The approvals Claude Code remembers for each project, whether you trusted it, its MCP servers and its last session cost |
| **Hooks** | Every hook and the status line, and whether the program it calls exists |
| **Agents & commands** | Your own and your plugins' subagents and slash commands |
| **Memory & settings** | `CLAUDE.md` and rule files, and every settings file (user, local, project, managed) |

Click any row to open its details. A plugin's details list all its skills, MCP servers and hooks, and each one opens in turn. A skill shows its `SKILL.md`, and a hook shows its script. You can browse a plugin's folder and copy the command to turn it on or off.

The **Rescan** button reads your config again. **Check MCP connections** runs `claude mcp list` to show which servers actually connect. The **project picker** in the sidebar adds one of your projects to the scan.

## Managing your setup

Open any item and use the buttons at the top of its details. Each one shows what will happen and the exact command it runs, and waits for you to confirm.

| Item | Actions | How it's done |
| --- | --- | --- |
| **Plugin** | Turn on / Turn off, Update, Uninstall | `claude plugin enable` / `disable` / `update` / `uninstall` |
| **MCP server** | Sign in, Sign out, Remove | `claude mcp login` / `logout` / `remove`. Sign in opens your browser. Servers from plugins are removed by turning off their plugin. |
| **Skill** (yours or your project's) | Turn off / Turn on, Delete | Turn off moves the folder to `skills-disabled/` next to `skills/`, so Claude Code stops loading it, and Turn on moves it back. Delete moves it to the Trash. |
| **Agent / slash command** (yours or your project's) | Delete | Moves the file to the Trash |
| **Hook / status line** (in a settings file) | Remove | Edits that settings file |
| **Permission rule** | Remove | Edits that settings file |

- **Plugin parts** (a plugin's skills, MCP servers, hooks and commands) are managed by turning the whole plugin on or off.
- **Synced from claude.ai:** plugins and skills synced from your claude.ai account are managed in claude.ai. The app shows them but doesn't change them.
- **Managed settings** set by your organization are never changed.
- **Settings edits** are written all at once, so a half-written file can't happen, and the previous version is kept as `settings.json.cci-backup`. That's one backup per file, overwritten each time, so backups don't pile up.
- **Trash:** files go to the system Trash on macOS and Linux. On Windows they go to `~/.claude/.cci-trash`.
- **Restart:** start a new Claude Code session to pick up changes.

### Health checks

- An MCP server or hook calls a program that isn't installed
- A plugin is turned on but not installed, or installed but missing from disk
- Very broad permission rules (`Bash(*)`), `bypassPermissions` mode, or long one-off rules that will never match again
- Extra folders in your permissions that no longer exist
- Two skills with the same name, a skill without a description, or a description over the 1,024-character limit
- Piles of `settings.json` backups, which usually mean some tool keeps rewriting your settings
- Very large `CLAUDE.md` files (they're added to every session)
- MCP servers waiting for you to sign in, and project entries whose folders were deleted

## Other ways to run it

```bash
python3 cc_inspector.py                       # write claude-code-report.html + .json and open the page
python3 cc_inspector.py --project ~/code/app  # also scan a project's .claude/, .mcp.json and CLAUDE.md
python3 cc_inspector.py --live                # also run `claude mcp list` (slower)
python3 cc_inspector.py --json-only --no-open # just the JSON, e.g. for scripts or CI
python3 cc_inspector.py --serve --port 9000   # the app on another port
python3 cc_inspector.py --serve --read-only    # the app without any buttons that change things
```

The one-file report works without a server, but it can't open files or rescan.

> **Before you share a report:** `claude-code-report.html` and `.json` list your plugins, file paths and project folders. Secret values are hidden, but check the report before you post it anywhere.

## What it reads

| Location | Used for |
| --- | --- |
| `~/.claude/settings.json`, `settings.local.json` | Permissions, enabled plugins, hooks, status line |
| `~/.claude.json` | MCP servers, per-project approvals, plugin and skill usage counts |
| `~/.claude/plugins/` | Installed and claude.ai-synced plugins, marketplaces |
| `~/.claude/skills/`, `agents/`, `commands/`, `rules/`, `CLAUDE.md` | Your own skills, agents, commands and memory |
| Managed settings (`/Library/Application Support/ClaudeCode/`, `/etc/claude-code/`, `C:\ProgramData\ClaudeCode\`) | Policies set by your organization |
| `<project>/.claude/`, `.mcp.json`, `CLAUDE.md` | Only with `--project` or the project picker |

If you set `CLAUDE_CONFIG_DIR`, it reads that folder instead of `~/.claude`.

## Safety

- The app only accepts connections from your own computer (`127.0.0.1`). It also rejects requests sent with another host name, which blocks DNS-rebinding attacks.
- Changes are only accepted from the app's own page. Each request needs a secret token that's created fresh every time the app starts, and must come from the app's own address. Other websites open in your browser can't make changes.
- The app never acts on a file path sent by the browser. It scans your config again, looks the item up, and only runs actions the scanner allows for that item. If the item changed since your last scan (say, another tool edited your settings), the action is refused, so you never delete the wrong thing.
- The file viewer only opens files inside `~/.claude` (and the project you picked). It refuses `../` escapes and files whose names look like credentials, keys or `.env` files.
- In JSON files, the values of env vars and headers, and of any key that looks secret, are hidden. Values that look like tokens are hidden in every file.

## Contributing

This is an open-source project, and help is welcome: bug reports, ideas, docs and code.

- **Found a bug or have an idea?** [Open an issue](https://github.com/frazz1234/claude-code-inspector/issues/new/choose). Claude Code's config format changes often, so "this shows up wrong for me" reports are very useful.
- **Want to change the code?** Read [CONTRIBUTING.md](CONTRIBUTING.md). It's a fork, a branch and a pull request, and the tests run automatically.
- **Found a security problem?** Report it privately. See [SECURITY.md](SECURITY.md).

To run the tests yourself:

```bash
python3 -m unittest discover -s tests -v
```

## License

[MIT](LICENSE)

Not affiliated with or endorsed by Anthropic. "Claude" and "Claude Code" are trademarks of Anthropic.
