# Greet

The user types a name and submits the form. The Rust `greet` command answers, and the line under the form shows `Hello, <name>! You've been greeted from Rust!`.

## Sub-features

- `greet-button` submits with the `Greet` button.
- `greet-enter` submits with Enter in the name field.
- `greet-empty` submits with no name and still gets a greeting.

## How to get to it (user POV)

- Type in the `Enter a name...` field, then click `Greet`.
- Type in the `Enter a name...` field, then press Enter.

## Driving it with verify.py

Preconditions:

- Baseline from the [index](./README.md).

- **Before.** Run `V screenshot greet-before.png`. It shows the empty field and no result line.
- **Enter a name.** Run `V type '#greet-input' 'kugiri' --clear`. The field reads `kugiri`.
- **Submit by button.** Run `V click 'button[type=submit]'`. The form submits.
- **Read the answer.** Run `V text 'form + p' --expect "Hello, kugiri! You've been greeted from Rust!"`. It prints that string and exits 0. The `from Rust!` suffix exists only in `src-tauri/src/lib.rs`, so it shows the call crossed `invoke`.
- **After.** Run `V screenshot greet-button-after.png`. It shows the name in the field and the greeting under it.
- **Empty name.** Run `V type '#greet-input' '' --clear`, `V click 'button[type=submit]'`, and `V text 'form + p' --expect "Hello, ! You've been greeted from Rust!"`. It prints that string.
- **Submit by Enter.** The harness cannot press Enter. Report `greet-enter` as unverified: "Element Send Keys types U+E007 literally, and W3C Actions does not submit".

## Gotchas

- The result `<p>` has no id. `form + p` is the only stable handle. Add an id when the UI changes, and update this file.
- The greeting is set asynchronously after `invoke`. Use `--expect`, which polls, rather than reading `V text` once right after the click.
- `V type` without `--clear` appends to the current value.
- `greet-enter` cannot be driven. Element Send Keys inserts U+E007 into the value. W3C Actions Enter, sent with the field focused, submits nothing.
