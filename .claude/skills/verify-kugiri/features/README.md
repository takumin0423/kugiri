# kugiri verification map

This directory is the maintained source for verifying kugiri's user-facing behavior. Read this index before driving the app, then use the matching feature file as the recipe. `V` is `.claude/skills/verify-kugiri/scripts/verify.py`, run outside the sandbox.

## Baseline preconditions

- A run launched by `V launch` in this session, with `KUGIRI_RUN` exported.
- `V doctor` prints `OK`.
- The window shows the start screen: heading `Welcome to Tauri + React`, an empty `#greet-input`, and an empty result line.

## Driving conventions

- Start every recipe from the baseline. Relaunch rather than undo a previous recipe's state.
- Act through `V type` and `V click`. Read state through `V text` and `V exec`.
- Treat every command as literal. Keep quoted strings and selectors unchanged.
- Drive only the run you launched. Leave the user's `pnpm tauri dev` window alone.

## Proof and skip reporting

- Screenshot before the action and after it, into `$KUGIRI_RUN/evidence/`, named `<feature-id>-<step>.png`.
- Pair each screenshot with the `V text --expect` output that names the observed string.
- Report each entry point separately. One the harness cannot drive is reported as unverified, with the reason. A different entry point does not stand in for it.

## Feature entry contract

Each feature file starts with an H1 title and one paragraph describing the user-visible behavior. It then uses exactly four H2 sections in this order: `Sub-features`, `How to get to it (user POV)`, `Driving it with verify.py`, `Gotchas`. Name only user paths, stable handles, required state, commands, and observable proof.

## Features

- [Greet](./greet.md) covers submitting a name and getting the greeting back from Rust, by button and by Enter, including an empty name.
- [External links](./external-links.md) covers the Vite, Tauri, and React logos that open their sites in the system browser.
