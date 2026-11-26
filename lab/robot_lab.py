"""Local robot lab - runs ONLY on 127.0.0.1 (answer to the job's "coding bots in your free time").
A tiny site (search page, product pages, images, a fake login with fictional accounts) + 3 scripted robots + 1 simulated
human visitor. The access log is turned into the same session features as the public web robot dataset, then
src/signals_eval.py scores each session with a model trained on that public data.
Purpose: see which BEHAVIOURAL signals separate scripts from people. No evasion technique is written or tested here.
Run from the repository root:  python lab/robot_lab.py      (about 1 minute; writes data/output/lab_sessions.csv)
"""
from __future__ import annotations

import random
import statistics
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
HOST, PORT = "127.0.0.1", 8765
LOG: list[tuple[str, float, str, str, int]] = []          # (visitor, time, method, path, status)
ACCOUNTS = {"A0000001": "demo-pass-1", "A0000002": "demo-pass-2"}   # fictional accounts of the local site


def guard(url: str) -> str:
    """Safety rule: the robots may only talk to this machine."""
    if urlparse(url).hostname not in ("127.0.0.1", "localhost"):
        raise ValueError(f"refused: {url} is not local")
    return url


class Site(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str = "text/html") -> None:
        LOG.append((self.headers.get("X-Visitor", "?"), time.time(), self.command, self.path, code))
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        p = self.path
        if p == "/" or p.startswith("/search") or p.startswith("/product/"):
            n = int(p.rsplit("/", 1)[-1]) if p.startswith("/product/") and p.rsplit("/", 1)[-1].isdigit() else 0
            code = 404 if n > 40 else 200
            self._send(code, b"<html><img src='/img/a.png'><img src='/img/b.png'><link href='/s.css'></html>")
        elif p.startswith("/img/") or p == "/s.css":
            self._send(200, b"x", "image/png" if p.startswith("/img/") else "text/css")
        else:
            self._send(404, b"not found")

    do_HEAD = do_GET

    def do_POST(self):  # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        user, _, pwd = body.partition(":")
        self._send(200 if ACCOUNTS.get(user) == pwd else 401, b"ok")

    def log_message(self, *a):  # keep the console quiet
        pass


def call(visitor: str, path: str, method: str = "GET", data: bytes | None = None) -> None:
    req = Request(guard(f"http://{HOST}:{PORT}{path}"), data=data, method=method, headers={"X-Visitor": visitor})
    try:
        urlopen(req, timeout=5).read()
    except Exception:  # noqa: BLE001  (4xx answers are part of the experiment)
        pass


def human(v: str) -> None:
    """Reads a few pages, loads their images and stylesheet, irregular pauses."""
    for _ in range(random.randint(5, 8)):
        page = random.choice(["/", "/search?q=lamp", f"/product/{random.randint(1, 30)}"])
        for path in (page, "/s.css", "/img/a.png", "/img/b.png"):
            call(v, path)
        time.sleep(random.uniform(0.8, 6.0))


def fast_reader(v: str) -> None:
    """Fetches product pages back to back, no images, walks past the end of the catalogue (404)."""
    for n in range(1, 61):
        call(v, f"/product/{n}")


def slow_reader(v: str) -> None:
    """One page every 1.5 s, like a metronome: few requests, very regular."""
    for n in range(1, 25):
        call(v, f"/product/{n}", "HEAD" if n % 4 == 0 else "GET")
        time.sleep(1.5)


def login_burst(v: str) -> None:
    """Tries fictional username:password pairs against the local fake login (the credential stuffing shape)."""
    for i in range(80):
        call(v, "/login", "POST", f"A{i:07d}:guess{i}".encode())


def features(rows: list[tuple]) -> dict:
    """Same definitions as the public dataset, for the subset the lab can compute (times in seconds, others are shares)."""
    t = sorted(r[1] for r in rows)
    gaps = [b - a for a, b in zip(t, t[1:])] or [0.0]
    n = len(rows)
    paths = [r[3] for r in rows]
    html = sum(1 for p in paths if not p.startswith(("/img/", "/s.css")))
    return {"NUMBER_OF_REQUESTS": n, "TOTAL_DURATION": round(t[-1] - t[0], 2), "AVERAGE_TIME": round(statistics.mean(gaps), 3),
            "STANDARD_DEVIATION": round(statistics.pstdev(gaps), 3), "REPEATED_REQUESTS": round(1 - len(set(paths)) / n, 3),
            "HTTP_RESPONSE_4XX": round(sum(400 <= r[4] < 500 for r in rows) / n, 3),
            "IMAGES": round(sum(p.startswith("/img/") for p in paths) / n, 3), "TOTAL_HTML": round(html / n, 3),
            "NIGHT": 0.0, "HEAD_METHOD": round(sum(r[2] == "HEAD" for r in rows) / n, 3),
            "POST_METHOD": round(sum(r[2] == "POST" for r in rows) / n, 3)}


def main() -> None:
    random.seed(42)
    srv = ThreadingHTTPServer((HOST, PORT), Site)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    plan = [("human-1", "human", human), ("human-2", "human", human), ("human-3", "human", human),
            ("bot-fast-reader", "robot", fast_reader), ("bot-slow-reader", "robot", slow_reader),
            ("bot-login-burst", "robot", login_burst)]
    threads = [threading.Thread(target=f, args=(v,)) for v, _, f in plan]
    [t.start() for t in threads]
    [t.join() for t in threads]
    srv.shutdown()
    import csv  # noqa: PLC0415
    out = ROOT / "data" / "output" / "lab_sessions.csv"
    rows = [{"visitor": v, "kind": k, **features([r for r in LOG if r[0] == v])} for v, k, _ in plan]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(LOG)} requests logged on {HOST}; sessions written to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
