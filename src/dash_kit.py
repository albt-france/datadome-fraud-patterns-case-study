"""Dashboard kit: one self-contained HTML file (Plotly embedded, works offline, light and dark themes), 5 tabs.

build(tabs, data, js) writes site/dashboard/index.html.
  tabs: [(label, inner_html), ...] (5 tabs). In the HTML use:
        <div class="card"><h2>Title <span class="tag pub">PUBLIC DATA</span></h2><div id="p_x" class="plot"></div><p>note</p></div>
        tags: pub (PUBLIC DATA), sim (SIMULATED), mix (PUBLIC + SIMULATED), ill (ILLUSTRATIVE).
  data: dict, available in JS as D.
  js:   charts, e.g.  P('p_x', [{type:'bar', x:D.a.map(r=>r.k), y:D.a.map(r=>r.v), marker:{color:C.a}}], {yaxis:{title:'n'}});
        Charts are drawn the first time their tab is shown (correct width). Helpers: C (colours), css(), fmt(v, d).
"""
from __future__ import annotations

import json

from plotly.offline import get_plotlyjs

from common import FOOT, SITE

CSS = """
:root { color-scheme: light; --bg:#F4F4F2; --card:#FCFCFB; --line:#E1E0D9; --ink:#0B0B0B; --muted:#52514E; --accent:#2A78D6; --pub:#E3EEFB; --pubt:#1C5CAB; --sim:#FBE9E0; --simt:#9A3B12; --mix:#ECE6F7; --mixt:#5B3A9A; --ill:#ECECEC; --illt:#444; --ok:#1BAF7A; --bad:#D64545; --grey:#A9A79F; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { color-scheme: dark; --bg:#141413; --card:#1A1A19; --line:#33322F; --ink:#F0EFEC; --muted:#C3C2B7; --accent:#3987E5; --pub:#1C2E45; --pubt:#9CC3F2; --sim:#40261A; --simt:#F2B89C; --mix:#2C2440; --mixt:#C9B6F0; --ill:#2A2A28; --illt:#CCC; --grey:#6E6C66; } }
* { box-sizing: border-box; }
body { margin:0; font-family:'Segoe UI', Arial, sans-serif; background:var(--bg); color:var(--ink); }
.wrap { max-width:1280px; margin:0 auto; padding:20px 16px 40px; }
h1 { font-size:24px; margin:0 0 4px; } .sub { color:var(--muted); margin:0 0 14px; font-size:14px; }
nav { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; }
nav button { border:1px solid var(--line); background:var(--card); color:var(--ink); padding:7px 12px; border-radius:6px; cursor:pointer; font:inherit; font-size:14px; }
nav button.on { border-color:var(--accent); color:var(--accent); font-weight:600; }
.tab { display:none; } .tab.on { display:block; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(340px, 1fr)); gap:12px; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; margin-bottom:12px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px; min-width:0; }
.card h2 { font-size:15px; margin:0 0 6px; } .card p, .card li { font-size:13px; color:var(--muted); margin:4px 0; }
.tag { font-size:11px; font-weight:700; letter-spacing:.06em; padding:3px 7px; border-radius:4px; margin-left:6px; vertical-align:middle; white-space:nowrap; }
.pub { background:var(--pub); color:var(--pubt); } .sim { background:var(--sim); color:var(--simt); } .mix { background:var(--mix); color:var(--mixt); } .ill { background:var(--ill); color:var(--illt); }
.big { font-size:30px; font-weight:700; margin:4px 0; }
table { border-collapse:collapse; width:100%; font-size:13px; } th, td { text-align:left; padding:4px 6px; border-bottom:1px solid var(--line); }
th { color:var(--muted); font-weight:600; } .scroll { max-height:340px; overflow:auto; }
footer { margin-top:18px; font-size:12px; color:var(--muted); }
.plot { width:100%; height:320px; overflow:hidden; }
"""

JS_HELPERS = """
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const C = {a: css('--accent'), ok: css('--ok'), bad: css('--bad'), grey: css('--grey'), org:'#EB6834', vio:'#8A63D2', yel:'#EDA100'};
const layout = (extra) => Object.assign({margin:{l:50,r:15,t:10,b:45}, paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  font:{family:'Segoe UI, Arial', size:12, color:css('--muted')}, xaxis:{gridcolor:css('--line'), zeroline:false},
  yaxis:{gridcolor:css('--line'), zeroline:false}, legend:{orientation:'h', y:1.15}, barmode:'group'}, extra||{});
const cfg = {displayModeBar:false, responsive:true};
const fmt = (v, d=0) => v==null ? '–' : Number(v).toLocaleString('en', {maximumFractionDigits:d, minimumFractionDigits:d});
const Q = {};
const P = (id, tr, lay) => { const t = document.getElementById(id).closest('section').id; (Q[t] = Q[t] || []).push(() => Plotly.newPlot(id, tr, layout(lay), cfg)); };
const show = t => { (Q[t] || []).forEach(f => f()); Q[t] = []; };
document.querySelectorAll('#nav button').forEach(b => b.onclick = () => {
  document.querySelectorAll('#nav button').forEach(x=>x.classList.toggle('on', x===b));
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('on', t.id===b.dataset.t));
  show(b.dataset.t);
});
"""


def build(title: str, subtitle: str, tabs: list[tuple[str, str]], data: dict, js: str, footer_extra: str = "") -> None:
    if len(tabs) != 5:
        raise SystemExit(f"the dashboard needs 5 tabs, got {len(tabs)}")
    nav = "".join(f'<button data-t="t{i}"{" class=on" if i == 1 else ""}>{lab}</button>' for i, (lab, _) in enumerate(tabs, 1))
    secs = "".join(f'<section id="t{i}" class="tab{" on" if i == 1 else ""}">{body}</section>' for i, (_, body) in enumerate(tabs, 1))
    foot = FOOT + (f" · {footer_extra}" if footer_extra else "")
    html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title}</title><style>{CSS}</style></head><body><div class="wrap"><h1>{title}</h1><p class="sub">{subtitle}</p>'
            f'<nav id="nav">{nav}</nav>{secs}<footer>{foot}</footer></div>'
            f'<script>{get_plotlyjs()}</script><script>const D = {json.dumps(data)};{JS_HELPERS}{js}\nshow("t1");</script></body></html>')
    out = SITE / "dashboard" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"written site/dashboard/index.html {out.stat().st_size / 1e6:.1f} MB")
