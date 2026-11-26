# External links

The Vite, Tauri, and React logos are links with `target="_blank"`. Clicking one is expected to open that project's site in the system browser, through `tauri-plugin-opener`, while the app window stays on the start screen. That expectation comes from the code. No run has observed it yet.

## Sub-features

- `link-vite` targets `https://vite.dev/`.
- `link-tauri` targets `https://tauri.app/`.
- `link-react` targets `https://react.dev/`.

## How to get to it (user POV)

- Click a logo in the row under the heading.

## Driving it with verify.py

Preconditions:

- Baseline from the [index](./README.md).
- The user agreed to a browser tab opening on their desktop. Ask first.

- **Targets.** Run `V exec 'return [...document.querySelectorAll("main a")].map(a=>[a.querySelector("img").alt,a.href,a.target])'`. It prints the three `[alt, href, "_blank"]` triples listed under Sub-features. This step has been observed.
- **Click.** Run `V click 'a[href="https://tauri.app"]'`, and repeat for each link. Then run `V doctor`. The expected `page url` is still `tauri://localhost`. Not yet observed.
- **Opened tab.** The harness cannot see the system browser. Ask the user whether the tab opened, or report it as unverified.

## Gotchas

- Clicking opens a real tab in the user's default browser. Click only when the change under test touches links or the opener plugin.
- `a.href` reads back with a trailing slash. The `href` attribute in `src/App.tsx` has none, so CSS selectors use the attribute form without the slash.
