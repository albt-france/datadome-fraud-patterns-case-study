"""PDF kit (Rovio style): grey-beige background, white cards, title = conclusion, PUBLIC DATA / SIMULATED tags,
Segoe UI, landscape A4, rendered by Edge headless.

render() also:
  * measures every .page / .grid / .card / .kpi in the browser and lists those whose content overflows
    (clipped text or charts); the build FAILS if any overflows (set ALLOW_OVERFLOW=1 to bypass while drafting);
  * empties the PDF metadata;
  * writes data/output/pdf_checks.json (pages, overflow list), read by tools/check_release.py.
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
from pathlib import Path

from common import AI, FOOT, OUT, RAW, SITE, PDF_NAME  # noqa: F401  (AI re-exported for the Methods page)

EDGE_CANDIDATES = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                   r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
BUILD = RAW / "report_build"
BLUE, ORANGE, GREY, RED, GREEN, VIO = "#1f4e79", "#d9822b", "#b0aca3", "#c62828", "#2e7d32", "#7e57c2"

CSS = """
@page { size: 297mm 210mm; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Segoe UI', sans-serif; color: #222; background: #ebe8e1; }
.page { width: 297mm; height: 210mm; padding: 8mm 11mm 6mm; background: #ebe8e1; page-break-after: always;
        display: flex; flex-direction: column; overflow: hidden; }
.page:last-child { page-break-after: auto; }
.kicker { font-size: 8.5pt; color: #6b665c; letter-spacing: .04em; text-transform: uppercase; }
h1 { font-size: 17.5pt; margin: 1mm 0 1mm; font-weight: 600; line-height: 1.15; }
h2 { font-size: 10pt; margin: 0 0 1.5mm; font-weight: 600; padding-right: 27mm; }
.sub { font-size: 9pt; color: #4a463e; margin-bottom: 2.5mm; }
.grid { display: grid; gap: 3.5mm; flex: 1; min-height: 0; overflow: hidden; }
.col { display: flex; flex-direction: column; gap: 3.5mm; min-height: 0; }
.card { background: #fff; border-radius: 3mm; padding: 3mm 3.5mm; box-shadow: 0 .3mm 1mm rgba(0,0,0,.07);
        overflow: hidden; position: relative; min-height: 0; }
.card svg { width: 100%; height: auto; max-height: 100%; }
.tag { position: absolute; top: 2.6mm; right: 3mm; font-size: 6.3pt; font-weight: 700; letter-spacing: .05em;
       padding: .6mm 1.6mm; border-radius: 1mm; }
.pub { background: #dde8f3; color: #1f4e79; } .sim { background: #fbe5c8; color: #8a4b00; } .mix { background: #e9e1f5; color: #5b3a9a; }
.ill { background: #e6e6e6; color: #444; }
.note { font-size: 7.6pt; color: #555; margin-top: 1mm; line-height: 1.33; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 3.5mm; margin-bottom: 3.5mm; }
.kpi { background: #fff; border-radius: 3mm; padding: 3mm 3.5mm; position: relative; overflow: hidden; }
.kpi b { display: block; font-size: 18pt; font-weight: 600; color: #1f4e79; margin-top: 2mm; }
.kpi span.t { font-size: 8pt; color: #444; }
ul, ol { margin: 0; padding-left: 4.5mm; font-size: 8.4pt; line-height: 1.38; }
li { margin-bottom: .7mm; }
table { border-collapse: collapse; width: 100%; font-size: 7.6pt; }
td, th { border-bottom: .2mm solid #e3e0d8; padding: .7mm 1.1mm; text-align: left; vertical-align: top; }
th { color: #6b665c; font-weight: 600; }
.foot { display: flex; justify-content: space-between; font-size: 7pt; color: #7a756b; margin-top: 2mm; }
p { font-size: 8.4pt; line-height: 1.38; margin: 0 0 1.4mm; }
.ex { font-size: 7.9pt; background: #f6f4ef; border-radius: 1.5mm; padding: 1.4mm 2mm; margin: 1mm 0; line-height: 1.35; }
.red { color: #c62828; font-weight: 600; } .green { color: #2e7d32; font-weight: 600; }
"""
TAG = {"pub": '<span class="tag pub">PUBLIC DATA</span>', "sim": '<span class="tag sim">SIMULATED</span>',
       "mix": '<span class="tag mix">PUBLIC + SIMULATED</span>', "ill": '<span class="tag ill">ILLUSTRATIVE</span>', "": ""}

# Runs in the browser before the DOM is dumped: lists every box whose content is taller or wider than the box.
PROBE = """<script>(function(){var bad=[],pages=[].slice.call(document.querySelectorAll('.page'));
[].forEach.call(document.querySelectorAll('.page,.grid,.col,.card,.kpi'),function(el){
 if(el.scrollHeight>el.clientHeight+2||el.scrollWidth>el.clientWidth+2){var pg=el.closest('.page');
  var h=el.querySelector('h1,h2');bad.push({page:pages.indexOf(pg),box:el.className,
  title:(h?h.textContent:'').slice(0,80),over_px:Math.max(el.scrollHeight-el.clientHeight,el.scrollWidth-el.clientWidth)});}});
var pre=document.createElement('pre');pre.id='__overflow';pre.textContent=JSON.stringify(bad);document.body.appendChild(pre);})();</script>"""


def svg(fig) -> str:
    """Matplotlib figure -> inline SVG (text stays text: sharp and searchable)."""
    import matplotlib.pyplot as plt  # noqa: PLC0415
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)
    s = buf.getvalue()
    return s[s.find("<svg"):]


def setup_matplotlib() -> None:
    import matplotlib  # noqa: PLC0415
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415
    plt.rcParams.update({"font.family": "Segoe UI", "font.size": 8.5, "svg.fonttype": "none", "axes.spines.top": False,
                         "axes.spines.right": False, "axes.edgecolor": "#999999", "axes.labelcolor": "#444444",
                         "xtick.color": "#444444", "ytick.color": "#444444"})


def page(n: int, kicker: str, title: str, sub: str, body: str, label: str, last: int = 6) -> str:
    """label: e.g. 'Viseven · Data Analyst case study' (bottom right)."""
    return (f'<section class="page"><div class="kicker">{kicker}</div><h1>{title}</h1><div class="sub">{sub}</div>'
            f'{body}<div class="foot"><span>{FOOT}</span><span>{label} · page {n} / {last}</span></div></section>')


def card(title: str, content: str, tag: str = "", note: str = "", style: str = "") -> str:
    """tag: 'pub' | 'sim' | 'mix' | 'ill' | '' (text-only cards may have no tag; every chart must have one)."""
    n = f'<div class="note">{note}</div>' if note else ""
    return f'<div class="card" style="{style}">{TAG[tag]}<h2>{title}</h2>{content}{n}</div>'


def kpi(value: str, text: str, tag: str) -> str:
    return f'<div class="kpi">{TAG[tag]}<b>{value}</b><span class="t">{text}</span></div>'


def grid(cols: str, *cards: str) -> str:
    """cols: CSS grid-template-columns, e.g. '1fr 1.3fr 1fr'. Wrap stacked cards in col(...)."""
    return f'<div class="grid" style="grid-template-columns:{cols};">{"".join(cards)}</div>'


def col(*cards: str) -> str:
    return f'<div class="col">{"".join(cards)}</div>'


def _edge() -> str:
    for c in EDGE_CANDIDATES:
        if Path(c).exists():
            return c
    raise SystemExit("Microsoft Edge not found: install it or set EDGE_CANDIDATES")


def render(pages: list[str], title: str, expected_pages: int = 7) -> Path:
    from pypdf import PdfReader, PdfWriter  # noqa: PLC0415

    BUILD.mkdir(parents=True, exist_ok=True)
    out = SITE / "report" / PDF_NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    body = "".join(pages)
    html = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title><style>{CSS}</style></head><body>{body}</body></html>'
    src = (BUILD / "report.html").resolve()
    src.write_text(html, encoding="utf-8")
    edge = _edge()

    # 1) overflow probe (same page size as print: 297 x 210 mm = 1123 x 794 px at 96 dpi)
    probe = (BUILD / "probe.html").resolve()
    probe.write_text(html.replace("</body>", PROBE + "</body>"), encoding="utf-8")
    dom = subprocess.run([edge, "--headless=new", "--disable-gpu", "--window-size=1123,794", "--virtual-time-budget=3000",
                          "--dump-dom", "file:///" + str(probe).replace("\\", "/")],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    m = re.search(r'<pre id="__overflow">(.*?)</pre>', dom, re.S)
    overflow = json.loads(m.group(1).replace("&quot;", '"').replace("&amp;", "&")) if m else None

    # 2) print
    tmp = (BUILD / "report_raw.pdf").resolve()
    subprocess.run([edge, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                    f"--print-to-pdf={tmp}", "file:///" + str(src).replace("\\", "/")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    rd, wr = PdfReader(str(tmp)), PdfWriter()
    for pg in rd.pages:
        wr.add_page(pg)
    wr.add_metadata({"/Producer": "", "/Creator": "", "/Title": "", "/Author": "", "/Subject": "", "/Keywords": ""})
    with open(out, "wb") as f:
        wr.write(f)

    checks = {"pages": len(rd.pages), "expected_pages": expected_pages,
              "overflow": overflow if overflow is not None else "probe failed"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pdf_checks.json").write_text(json.dumps(checks, indent=1), encoding="utf-8")
    print(f"saved {out.relative_to(SITE.parent)}: {len(rd.pages)} pages")
    problems = []
    if len(rd.pages) != expected_pages:
        problems.append(f"{len(rd.pages)} pages instead of {expected_pages} (a page spilled over: shorten its content)")
    if overflow is None:
        problems.append("overflow probe failed (Edge --dump-dom returned nothing)")
    elif overflow:
        for o in overflow:
            problems.append(f"overflow page {o['page']} [{o['box']}] '{o['title']}' by {o['over_px']} px")
    if problems:
        print("PDF PROBLEMS:\n  " + "\n  ".join(problems))
        if not os.environ.get("ALLOW_OVERFLOW"):
            raise SystemExit(1)
    return out
