#!/usr/bin/env python3
"""Drive the real kugiri desktop app through tauri-plugin-webdriver.

Stdlib only. Every subcommand except `launch` acts on one run directory:
--run DIR, else $KUGIRI_RUN, else the newest live run under .verify/kugiri/.
"""

import argparse
import base64
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
RUNS = REPO / ".verify" / "kugiri"
TARGET_DIR = REPO / "src-tauri" / "target" / "verify"
BINARY = TARGET_DIR / "debug" / "kugiri"
ELEMENT_KEY = "element-6066-11e4-a52e-4f735466cecf"
READY_SELECTOR = "#root > *"  # React has mounted into index.html's root


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def http(method, port, path, body=None, timeout=30):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read() or b"{}").get("value")
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        die(f"{method} {path} -> HTTP {e.code}: {detail}")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def load_run(arg):
    if arg:
        run = Path(arg)
    elif os.environ.get("KUGIRI_RUN"):
        run = Path(os.environ["KUGIRI_RUN"])
    else:
        live = sorted(RUNS.glob("*/run.json"), key=lambda p: p.stat().st_mtime)
        if not live:
            die("no live run under .verify/kugiri/; run `launch` first")
        run = live[-1].parent
    state_file = run / "run.json"
    if not state_file.exists():
        die(f"{run} has no run.json (never launched, or already stopped)")
    return run, json.loads(state_file.read_text())


def save_run(run, state):
    (run / "run.json").write_text(json.dumps(state, indent=2))


def sess(state, path):
    return f"/session/{state['session']}{path}"


def find(state, css):
    value = http("POST", state["port"], sess(state, "/element"),
                 {"using": "css selector", "value": css})
    return value[ELEMENT_KEY]


def cmd_launch(a):
    if not a.no_build:
        env = dict(os.environ, CARGO_TARGET_DIR=str(TARGET_DIR))
        print("building: pnpm tauri build --debug --no-bundle --features webdriver", flush=True)
        r = subprocess.run(["pnpm", "tauri", "build", "--debug", "--no-bundle", "--features", "webdriver"],
                           cwd=REPO, env=env)
        if r.returncode:
            die("build failed; fix it before driving the app")
    if not BINARY.exists():
        die(f"{BINARY} missing; drop --no-build")

    port = a.port or free_port()
    run = RUNS / f"{time.strftime('%Y%m%d-%H%M%S')}-{os.urandom(2).hex()}"
    (run / "evidence").mkdir(parents=True)
    log = open(run / "app.log", "w")
    env = dict(os.environ, TAURI_WEBDRIVER_PORT=str(port))
    proc = subprocess.Popen([str(BINARY)], cwd=REPO, env=env, stdout=log,
                            stderr=subprocess.STDOUT, start_new_session=True)
    state = {"pid": proc.pid, "port": port, "binary": str(BINARY),
             "session": None, "started": time.time()}
    save_run(run, state)

    deadline = time.time() + a.timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            die(f"app exited with {proc.returncode}; see {run / 'app.log'}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/status", timeout=2) as r:
                if json.loads(r.read())["value"]["ready"]:
                    break
        except OSError:
            pass
        time.sleep(0.5)
    else:
        die(f"WebDriver on :{port} never became ready; see {run / 'app.log'}")

    state["session"] = http("POST", port, "/session", {"capabilities": {}})["sessionId"]
    save_run(run, state)

    while time.time() < deadline:
        found = http("POST", port, sess(state, "/execute/sync"), {
            "script": "return !!document.querySelector(arguments[0]);",
            "args": [READY_SELECTOR]})
        if found:
            print(f"READY run={run} pid={proc.pid} port={port}")
            print(f"export KUGIRI_RUN={run}")
            return
        time.sleep(0.5)
    die(f"UI never rendered {READY_SELECTOR}; see {run / 'app.log'}")


def cmd_doctor(a):
    run, st = load_run(a.run)
    problems = []
    if not pid_alive(st["pid"]):
        problems.append(f"pid {st['pid']} is not running")
    else:
        comm = subprocess.run(["ps", "-p", str(st["pid"]), "-o", "comm="],
                              capture_output=True, text=True).stdout.strip()
        if comm != st["binary"]:
            problems.append(f"pid {st['pid']} is {comm!r}, not {st['binary']}")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{st['port']}/status", timeout=3) as r:
            if not json.loads(r.read())["value"]["ready"]:
                problems.append("WebDriver /status says not ready")
    except OSError as e:
        problems.append(f"WebDriver :{st['port']} unreachable: {e}")
    if not problems:
        try:
            url = http("GET", st["port"], sess(st, "/url"), timeout=5)
            print(f"page url: {url}")
        except SystemExit:
            problems.append("session is gone; stop and relaunch")
    sources = [p for d in ("src", "src-tauri/src") for p in (REPO / d).rglob("*") if p.is_file()]
    newest = max(p.stat().st_mtime for p in sources)
    if Path(st["binary"]).stat().st_mtime < newest:
        problems.append("binary is older than src/ or src-tauri/src/; relaunch without --no-build")
    print(f"run={run} pid={st['pid']} port={st['port']}")
    if problems:
        for p in problems:
            print(f"PROBLEM: {p}")
        sys.exit(1)
    print("OK")


def cmd_type(a):
    _, st = load_run(a.run)
    el = find(st, a.css)
    if a.clear:
        http("POST", st["port"], sess(st, f"/element/{el}/clear"), {})
    http("POST", st["port"], sess(st, f"/element/{el}/value"), {"text": a.text})


def cmd_click(a):
    _, st = load_run(a.run)
    http("POST", st["port"], sess(st, f"/element/{find(st, a.css)}/click"), {})


def cmd_text(a):
    _, st = load_run(a.run)
    deadline = time.time() + a.wait
    while True:
        text = http("GET", st["port"], sess(st, f"/element/{find(st, a.css)}/text"))
        if a.expect is None or text == a.expect or time.time() >= deadline:
            break
        time.sleep(0.25)
    print(text)
    if a.expect is not None and text != a.expect:
        die(f"expected {a.expect!r}, got {text!r}")


def cmd_exec(a):
    _, st = load_run(a.run)
    print(json.dumps(http("POST", st["port"], sess(st, "/execute/sync"),
                          {"script": a.script, "args": []})))


def cmd_screenshot(a):
    run, st = load_run(a.run)
    png = base64.b64decode(http("GET", st["port"], sess(st, "/screenshot")))
    out = run / "evidence" / a.name
    out.write_bytes(png)
    print(out)


def cmd_stop(a):
    run, st = load_run(a.run)
    if st.get("session"):
        try:
            urllib.request.urlopen(urllib.request.Request(
                f"http://127.0.0.1:{st['port']}{sess(st, '')}", method="DELETE"), timeout=3)
        except OSError:
            pass
    pid = st["pid"]
    if pid_alive(pid):
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            if not pid_alive(pid):
                break
            time.sleep(0.25)
        else:
            os.kill(pid, signal.SIGKILL)
    (run / "run.json").rename(run / "run.stopped.json")
    print(f"stopped pid={pid}; evidence kept in {run / 'evidence'}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("launch", help="build, start the app, open a WebDriver session")
    s.add_argument("--no-build", action="store_true")
    s.add_argument("--port", type=int, help="WebDriver port (default: a free one)")
    s.add_argument("--timeout", type=float, default=60)
    s.set_defaults(fn=cmd_launch)

    def with_run(name, fn, help):
        s = sub.add_parser(name, help=help)
        s.add_argument("--run")
        s.set_defaults(fn=fn)
        return s

    with_run("doctor", cmd_doctor, "read-only health check of a run")
    s = with_run("type", cmd_type, "type text into the element matching CSS")
    s.add_argument("css")
    s.add_argument("text")
    s.add_argument("--clear", action="store_true")
    s = with_run("click", cmd_click, "click the element matching CSS")
    s.add_argument("css")
    s = with_run("text", cmd_text, "print an element's text; --expect fails on mismatch")
    s.add_argument("css")
    s.add_argument("--expect")
    s.add_argument("--wait", type=float, default=5)
    s = with_run("exec", cmd_exec, "run sync JS in the page and print the JSON result")
    s.add_argument("script")
    s = with_run("screenshot", cmd_screenshot, "save a PNG under <run>/evidence/")
    s.add_argument("name")
    with_run("stop", cmd_stop, "end the session and kill the app this run started")

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
