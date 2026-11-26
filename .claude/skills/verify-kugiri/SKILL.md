---
name: verify-kugiri
description: Drive the real kugiri desktop app (Tauri 2, macOS window) through its debug-only WebDriver server to prove a UI or Rust-command change works, capturing screenshots and element text as evidence. Use when a change touches src/ or src-tauri/ and the claim is "it works in the app", or to reproduce a UI bug.
---

# Verify kugiri

kugiri is a Tauri 2 app: React in a WKWebView, Rust commands behind `invoke`. `tauri-plugin-webdriver` is an optional dependency behind the cargo feature `webdriver`. `src-tauri/src/lib.rs` registers it only under `#[cfg(all(debug_assertions, feature = "webdriver"))]`, and it serves W3C WebDriver on `127.0.0.1:$TAURI_WEBDRIVER_PORT`. Plain `pnpm tauri dev` and release builds leave it out. Only this skill's build turns it on. Every proof goes through that server against the real window, so `invoke` reaches real Rust.

All steps use one helper, `.claude/skills/verify-kugiri/scripts/verify.py` (stdlib Python). Below, `V` stands for that path. `V --help` and `V <cmd> --help` list every subcommand.

## Sandbox

The app is a GUI process. Inside Claude Code's Bash sandbox it cannot open a window, the build cannot write `~/.cargo`, and `ps` is denied. Run every `V` command with the sandbox disabled. `$TMPDIR` differs inside and outside the sandbox, so keep all state under the repo, as the helper does.

## Launch

```sh
V launch            # build + start + open a WebDriver session
V launch --no-build # reuse the last verify build
```

`launch` runs `pnpm tauri build --debug --no-bundle --features webdriver` with `CARGO_TARGET_DIR=src-tauri/target/verify`. That builds the frontend into `dist/` and embeds it, so the app needs no Vite and port 1420 stays free for the user's `pnpm tauri dev`. The separate target dir keeps this build from invalidating the dev build's cache. The first build takes about a minute.

It then starts `src-tauri/target/verify/debug/kugiri` on a free WebDriver port and waits until `/status` is ready and React has mounted into `#root`. Ready is the line:

```
READY run=<repo>/.verify/kugiri/<timestamp>-<hex> pid=<pid> port=<port>
export KUGIRI_RUN=<repo>/.verify/kugiri/<timestamp>-<hex>
```

Shell state does not carry between Claude Code Bash calls. Capture the path with `R=$(V launch | sed -n 's/^export KUGIRI_RUN=//p')`. Then, within the same call, run `export KUGIRI_RUN=$R`, or pass `--run <path>` on every later call. Without either, commands fall back to the newest live run, which may belong to another agent.

The app keeps no data yet, so there is no seed or migration step. Two launches side by side were driven to different greetings without crosstalk, because each run gets its own port and run dir. Once the app stores data, runs will share it under the bundle identifier `dev.takumin0423.kugiri`. Add a per-run data dir before trusting parallel runs then.

## Doctor

```sh
V doctor
```

Read-only. It checks that the recorded pid is alive and is the verify binary, that WebDriver answers on the recorded port, that the session still works, and that the binary is newer than every file in `src/` and `src-tauri/src/`. It prints `OK` or one `PROBLEM:` line per failure and exits 1. Run it before driving, and again whenever a step fails oddly. A stale binary means relaunch without `--no-build`.

## Drive

| Command | Effect |
| --- | --- |
| `V type <css> <text> [--clear]` | Set the element's text through WebDriver Element Send Keys. Special keys arrive as literal characters: `` lands in the value as U+E007, not as Enter. The W3C Actions keyDown/keyUp for Enter, sent with the field focused (`document.activeElement` confirmed), returns success but submits nothing. So the harness has no Enter key, and an Enter-only path is reported unverified. |
| `V click <css>` | Click the element. |
| `V text <css> [--expect S] [--wait SEC]` | Print the element's visible text. With `--expect`, poll up to `--wait` (5 s) and exit 1 on mismatch. |
| `V exec '<js>'` | Run sync JS in the page and print the JSON result. Use it to read state. User actions go through `type` and `click`. |
| `V screenshot <name>.png` | Save a PNG of the window into `$KUGIRI_RUN/evidence/`. |

Every failure exits non-zero. Chain steps with `&&`, so a failed step stops the run. `set -e` did not stop a run in Claude Code's Bash tool.

The plugin synthesizes input inside the webview. It proves DOM behavior and the `invoke` round trip, not native keyboard, focus, IME, or menu behavior. Report those as unverified.

Selectors are CSS. The current UI has no ARIA labels or `data-testid` attributes, so the feature map uses the stable ids and structure that exist. When you add UI, give it an `id` or `data-testid` and record it in the feature file.

The feature map in [`features/README.md`](features/README.md) has the recipe for every user-facing feature. Read the feature's file before driving it, and cover every entry point it lists.

## Evidence

Evidence lives in `.verify/kugiri/<timestamp>/evidence/`, which is gitignored, and survives `stop`. A proof contains:

- A screenshot before the action and one after, showing the resulting state.
- The `V text --expect` output naming the exact observed string.
- For Rust commands, a result only Rust can produce, such as the `greet` suffix `You've been greeted from Rust!`. That shows the call crossed `invoke`.
- For a side effect (a file written, a setting saved), a second read through a different view, such as the file on disk or a relaunch.

Drive the user path: keystrokes and clicks. Calling `invoke` from `V exec` or setting React state skips the code under test. `app.log` in the run dir holds the app's stdout and stderr. Attach it when Rust logs or panics.

## Cleanup

```sh
V stop
```

It ends the WebDriver session, sends SIGTERM to the pid this run recorded (SIGKILL after 5 s), and renames `run.json` to `run.stopped.json`. It kills only that pid. Leave other kugiri windows alone, including the user's `pnpm tauri dev`. `evidence/` and `app.log` stay. Run `stop` after every attempt, failed ones too. To prune old runs, delete `.verify/kugiri/<timestamp>/` dirs by hand once their evidence is no longer needed.
