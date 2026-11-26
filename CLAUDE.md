# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

kugiri is a Tauri 2 desktop app: a React 19 + TypeScript frontend built by Vite (`src/`) inside a Rust shell (`src-tauri/`). The repo is still the `create-tauri-app` template; the `greet` command is placeholder code.

## Commands

Package manager is pnpm (Tauri's `beforeDevCommand` / `beforeBuildCommand` call `pnpm`).

- `pnpm tauri dev` — run the desktop app with HMR; starts Vite itself.
- `pnpm tauri build` — production bundle; runs `pnpm build` first.
- `pnpm build` — typecheck (`tsc`) + Vite build to `dist/`. This is the only frontend check; there is no linter or test runner yet.
- `cargo check` / `cargo clippy` / `cargo test` — run inside `src-tauri/`.

Vite is pinned to port 1420 with `strictPort`; if dev fails to start, something else holds that port.

## Frontend ↔ Rust bridge

Adding a backend feature touches several files that must agree:

1. Define a `#[tauri::command]` in `src-tauri/src/lib.rs` and register it in `tauri::generate_handler![...]`. Unregistered commands fail only at runtime.
2. Call it from React with `invoke("name", { args })` from `@tauri-apps/api/core`. Argument keys are camelCase on the JS side and map to snake_case Rust parameters.
3. For a Tauri plugin, add the crate in `Cargo.toml`, the `@tauri-apps/plugin-*` package, `.plugin(...)` in `lib.rs`, and its permission in `src-tauri/capabilities/default.json`. A missing capability permission surfaces as a runtime "not allowed" error.

`main.rs` only calls `kugiri_lib::run()`; app setup lives in `lib.rs` (the `_lib` crate name is needed so the lib and bin don't collide on Windows).
