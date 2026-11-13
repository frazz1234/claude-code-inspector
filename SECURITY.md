# Security

This tool reads your Claude Code config and, in app mode, can change it. Security reports are very welcome.

## Reporting a problem

**Please don't open a public issue.** Report it privately instead: [open a private security report](https://github.com/frazz1234/claude-code-inspector/security/advisories/new).

Useful things to include:
- what an attacker could do (for example, read a file outside `~/.claude`, see a secret value, trigger an action from another website, or get the assistant to read a credential file),
- the steps to reproduce it,
- your OS, Python version and inspector version (`python3 cc_inspector.py --version`).

You'll get a reply as soon as possible. Once a fix is released, you'll be credited if you want to be.

## What the tool is meant to guarantee

- The app only listens on `127.0.0.1` and rejects requests with another host name.
- Only the app's own page can make changes. That takes a fresh secret token each time the app starts, plus a matching `Origin`.
- Actions only run on items found by a fresh scan, and are refused if the item changed in the meantime.
- The file viewer only opens files inside `~/.claude` (and the selected project), and never files that look like credentials or keys.
- Values of env vars, headers and tokens never appear in the page, the JSON or the terminal output.
- The assistant (`claude -p`) runs in safe mode with only Read, Glob and Grep, confined to the Claude config folder, with credential files denied. It can't change anything itself; its suggestions only become buttons the user confirms.

If you find a way around any of these, that's a security bug.
