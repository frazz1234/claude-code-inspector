# Contributing

Thanks for helping! Bug reports, ideas, docs fixes and code are all welcome. You don't need to be an expert.

## Reporting a bug or suggesting an idea

Open an [issue](https://github.com/frazz1234/claude-code-inspector/issues/new/choose) and pick **Bug report** or **Feature idea**. The form asks for what we need.

Claude Code's config format changes often, so "this shows up wrong for me" reports are really useful. **Please trim personal details** (paths, project names, tokens) from anything you paste.

Found a security problem? Please report it privately. See [SECURITY.md](SECURITY.md).

## Changing the code

1. **Fork** the repo (the Fork button on GitHub) and clone your fork.
2. Make a branch: `git checkout -b fix-something`.
3. Make your change. Run the tests and try the app:
   ```bash
   python3 -m unittest discover -s tests -v
   python3 cc_inspector.py --serve
   ```
4. Commit, push to your fork, and open a **pull request**. The checklist in the pull request form covers the rest.

Every pull request runs the tests on macOS, Linux and Windows automatically. You'll see the result on the pull request page.

## How the code is laid out

| File | What's in it |
| --- | --- |
| `cc_inspector.py` | Everything on the Python side: scanning (`collect_*` functions and `build()`), health checks (`issue(...)`), actions (`do_action()`), the assistant (`assistant_*` functions and `translate_event()`), the local web server (`serve()`) and the command line (`main()`) |
| `cc_inspector_ui.html` | The page. Plain HTML, CSS and JavaScript, no build step. The scan result is inserted where `__DATA__` is. `VIEWS` draws each page, `DETAIL` draws the side panel, `ACT` describes the action buttons, and the "Ask Claude" section holds the chat (`sendChat`, `md`, `special`) |
| `tests/test_cc_inspector.py` | Tests. Each one builds a fake home folder, so your real `~/.claude` is never touched |
| `scripts/demo_home.py` | Builds a made-up Claude Code setup for demos and screenshots: `python3 scripts/demo_home.py /tmp/cci-demo`, then `HOME=/tmp/cci-demo PATH="/tmp/cci-demo/.local/bin:$PATH" python3 cc_inspector.py --serve` |

## Ground rules

- **Standard library only.** People should be able to run one file with no installs.
- **Never leak secrets.** Values of env vars, headers and tokens must not appear in the page, the JSON or the logs. There's a test for this. Add to it if you add a new data source.
- **Changes must be safe.** A new action must:
  - be confirmed in the UI and show what it will do,
  - act only on items the scanner found (looked up again by `ref`),
  - refuse items that changed since the scan,
  - prefer the official `claude` CLI over editing files,
  - prefer moving files to the Trash over deleting them,
  - work with `--read-only` (hidden and refused).
- **Plain words in the UI.** Short sentences. Say what will happen, not how it's implemented.
- **Times in 24-hour format.**

## Good first contributions

- A new health check (add an `issue(...)` call in the matching `collect_*` function, plus a test)
- Support for a config location the inspector doesn't read yet
- Fixes for Windows or Linux paths
- Better wording in the UI or README

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE). Please also follow the [Code of Conduct](CODE_OF_CONDUCT.md).
