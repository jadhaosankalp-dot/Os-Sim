"""
Scheduler Bench — CPU Scheduling Simulator (Python / Flask)
-------------------------------------------------------------
Computes FCFS, SJF (non-preemptive) and Round Robin scheduling —
Completion Time, Turnaround Time, Waiting Time and their averages —
and renders everything as a styled, colourful webpage with Gantt charts.

HOW TO RUN
    pip install flask
    python app.py
    Then open http://localhost:8080
"""

from flask import Flask, request, render_template_string
from dataclasses import dataclass, field
from typing import List
import re

app = Flask(__name__)

PALETTE = [
    "#F5A623", "#34D3C9", "#8C7CFF", "#F45B69", "#4CB963",
    "#FFD23F", "#5BC0EB", "#E4572E", "#C084FC", "#2EC4B6",
]


# =========================================================================
# Data model
# =========================================================================

@dataclass
class Proc:
    id: str
    at: int
    bt: int


@dataclass
class Result:
    id: str
    at: int
    bt: int
    ct: int
    tat: int
    wt: int


@dataclass
class Seg:
    id: str
    start: int
    end: int


@dataclass
class SimResult:
    gantt: List[Seg] = field(default_factory=list)
    results: List[Result] = field(default_factory=list)


def id_num(pid: str) -> int:
    digits = re.sub(r"[^0-9]", "", pid)
    return int(digits) if digits else 0


# =========================================================================
# Scheduling algorithms
# =========================================================================

def compute_fcfs(procs_in: List[Proc]) -> SimResult:
    procs = sorted(procs_in, key=lambda p: (p.at, id_num(p.id)))
    time = 0
    gantt: List[Seg] = []
    results: List[Result] = []

    for p in procs:
        if p.at > time:
            gantt.append(Seg("IDLE", time, p.at))
            time = p.at
        start = time
        time += p.bt
        gantt.append(Seg(p.id, start, time))
        ct = time
        tat = ct - p.at
        wt = tat - p.bt
        results.append(Result(p.id, p.at, p.bt, ct, tat, wt))

    results.sort(key=lambda r: id_num(r.id))
    return SimResult(gantt, results)


def compute_sjf(procs_in: List[Proc]) -> SimResult:
    procs = list(procs_in)
    n = len(procs)
    done = [False] * n
    time = 0
    completed = 0
    gantt: List[Seg] = []
    results: List[Result] = []

    while completed < n:
        chosen = -1
        for i in range(n):
            if done[i] or procs[i].at > time:
                continue
            if chosen == -1:
                chosen = i
                continue
            cur, best = procs[i], procs[chosen]
            better = (
                cur.bt < best.bt
                or (cur.bt == best.bt and cur.at < best.at)
                or (cur.bt == best.bt and cur.at == best.at and id_num(cur.id) < id_num(best.id))
            )
            if better:
                chosen = i

        if chosen == -1:
            next_at = min(procs[i].at for i in range(n) if not done[i])
            gantt.append(Seg("IDLE", time, next_at))
            time = next_at
            continue

        p = procs[chosen]
        start = time
        time += p.bt
        gantt.append(Seg(p.id, start, time))
        done[chosen] = True
        completed += 1
        ct = time
        tat = ct - p.at
        wt = tat - p.bt
        results.append(Result(p.id, p.at, p.bt, ct, tat, wt))

    results.sort(key=lambda r: id_num(r.id))
    return SimResult(gantt, results)


def compute_rr(procs_in: List[Proc], quantum: int) -> SimResult:
    procs = sorted(procs_in, key=lambda p: (p.at, id_num(p.id)))
    n = len(procs)
    remaining = [p.bt for p in procs]
    time = 0
    completed = 0
    i = 0
    queue: List[int] = []
    gantt: List[Seg] = []
    done_map = {}

    while completed < n:
        while i < n and procs[i].at <= time:
            queue.append(i)
            i += 1

        if not queue:
            gantt.append(Seg("IDLE", time, procs[i].at))
            time = procs[i].at
            continue

        idx = queue.pop(0)
        p = procs[idx]
        exec_time = min(quantum, remaining[idx])
        start = time
        time += exec_time
        remaining[idx] -= exec_time
        gantt.append(Seg(p.id, start, time))

        while i < n and procs[i].at <= time:
            queue.append(i)
            i += 1

        if remaining[idx] > 0:
            queue.append(idx)
        else:
            ct = time
            tat = ct - p.at
            wt = tat - p.bt
            done_map[p.id] = Result(p.id, p.at, p.bt, ct, tat, wt)
            completed += 1

    results = sorted(done_map.values(), key=lambda r: id_num(r.id))
    return SimResult(gantt, results)


def avg(results: List[Result], field_name: str) -> float:
    return sum(getattr(r, field_name) for r in results) / len(results)


def color_index(pid: str, original: List[Proc]) -> int:
    for i, p in enumerate(original):
        if p.id == pid:
            return i
    return 0


# =========================================================================
# HTML rendering helpers
# =========================================================================

def build_gantt_html(gantt: List[Seg], original: List[Proc]) -> str:
    total = gantt[-1].end

    bar = ['<div class="gantt-bar">']
    for seg in gantt:
        dur = seg.end - seg.start
        idle = seg.id == "IDLE"
        cls = "seg idle" if idle else "seg"
        style = "" if idle else f"background:{PALETTE[color_index(seg.id, original) % len(PALETTE)]};"
        label = "&middot;&middot;&middot;" if idle else seg.id
        bar.append(
            f'<div class="{cls}" style="flex:{dur} 0 0;{style}" '
            f'title="{seg.id} {seg.start}-{seg.end}">{label if dur >= 1 else ""}</div>'
        )
    bar.append("</div>")

    bounds = sorted({0, *(seg.end for seg in gantt)})
    ticks = ['<div class="gantt-ticks">']
    for t in bounds:
        pct = t / total * 100
        if t == 0:
            style = "left:0;transform:none;"
        elif t == total:
            style = f"left:{pct}%;transform:translateX(-100%);"
        else:
            style = f"left:{pct}%;"
        ticks.append(f'<span style="{style}">{t}</span>')
    ticks.append("</div>")

    return f'<div class="gantt-wrap">{"".join(bar)}{"".join(ticks)}</div>'


def build_results_table(results: List[Result], original: List[Proc], head_class: str) -> str:
    rows = []
    for r in results:
        color = PALETTE[color_index(r.id, original) % len(PALETTE)]
        rows.append(
            f'<tr><td><span class="chip"><span class="dot" style="background:{color}"></span>{r.id}</span></td>'
            f"<td>{r.at}</td><td>{r.bt}</td><td>{r.ct}</td><td>{r.tat}</td><td>{r.wt}</td></tr>"
        )
    avg_tat = avg(results, "tat")
    avg_wt = avg(results, "wt")

    return (
        f'<table class="results"><thead><tr class="{head_class}">'
        f'<th class="{head_class}">Process</th><th class="{head_class}">AT</th>'
        f'<th class="{head_class}">BT</th><th class="{head_class}">CT</th>'
        f'<th class="{head_class}">TAT</th><th class="{head_class}">WT</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'<tfoot><tr><td colspan="4">Average</td><td>{avg_tat:.2f}</td><td>{avg_wt:.2f}</td></tr></tfoot>'
        f"</table>"
    )


def algo_card(title: str, tag: str, accent_class: str, head_class: str, sim: SimResult, original: List[Proc]) -> str:
    return (
        f'<div class="card {accent_class}"><div class="card-head"><div class="card-title">'
        f'{title} <span class="tag">{tag}</span></div></div>'
        f"{build_gantt_html(sim.gantt, original)}"
        f"{build_results_table(sim.results, original, head_class)}"
        f"</div>"
    )


def build_comparison(fcfs: SimResult, sjf: SimResult, rr: SimResult) -> str:
    tats = [avg(fcfs.results, "tat"), avg(sjf.results, "tat"), avg(rr.results, "tat")]
    wts = [avg(fcfs.results, "wt"), avg(sjf.results, "wt"), avg(rr.results, "wt")]
    names = ["FCFS", "SJF (Non-Preemptive)", "Round Robin"]
    pills = ["pill-amber", "pill-teal", "pill-violet"]
    colors = ["var(--amber)", "var(--teal)", "var(--violet)"]

    max_val = max(*tats, *wts)
    best_tat = min(tats)
    best_wt = min(wts)

    best_badge = '<span class="best-badge">BEST</span>'
    body = []
    for i in range(3):
        tat_w = tats[i] / max_val * 100
        wt_w = wts[i] / max_val * 100
        tat_badge = best_badge if tats[i] == best_tat else ""
        wt_badge = best_badge if wts[i] == best_wt else ""
        body.append(
            f'<tr><td><span class="algo-pill {pills[i]}">{names[i]}</span></td>'
            f'<td><div class="metric-cell"><span class="metric-num">{tats[i]:.2f}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{tat_w:.1f}%;background:{colors[i]}"></div></div>'
            f'{tat_badge}</div></td>'
            f'<td><div class="metric-cell"><span class="metric-num">{wts[i]:.2f}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{wt_w:.1f}%;background:{colors[i]}"></div></div>'
            f'{wt_badge}</div></td></tr>'
        )

    return (
        '<div class="card"><div class="card-head"><div class="card-title">04 &middot; Comparison '
        '<span class="tag">Avg TAT &amp; Avg WT</span></div></div>'
        '<table class="compare"><thead><tr><th>Algorithm</th><th>Avg Turnaround Time</th>'
        f'<th>Avg Waiting Time</th></tr></thead><tbody>{"".join(body)}</tbody></table></div>'
    )


def default_rows() -> str:
    sample = [(0, 5), (1, 3), (2, 8), (3, 6), (4, 2)]
    rows = []
    for i, (at, bt) in enumerate(sample):
        color = PALETTE[i % len(PALETTE)]
        rows.append(
            f'<tr><td><span class="chip"><span class="dot" style="background:{color}"></span>'
            f'<input class="numin" style="width:56px" type="text" name="pid" value="P{i + 1}"></span></td>'
            f'<td><input class="numin" type="number" name="at" min="0" value="{at}"></td>'
            f'<td><input class="numin" type="number" name="bt" min="1" value="{bt}"></td>'
            f'<td><button type="button" class="icon-btn" onclick="removeRow(this)">&#10005;</button></td></tr>'
        )
    return "".join(rows)


# =========================================================================
# Page shell (CSS + template)
# =========================================================================

CSS = """
:root{
  --bg:#0A0F1C;
  --bg-grid: rgba(255,255,255,0.025);
  --panel:#111A2E;
  --panel-soft:#0E1626;
  --border:#233150;
  --border-soft:#1A2540;
  --text:#EAF0FB;
  --muted:#8494B0;
  --muted-2:#5D6B87;
  --amber:#F5A623;
  --amber-dim:#3A2E14;
  --teal:#34D3C9;
  --teal-dim:#123330;
  --violet:#8C7CFF;
  --violet-dim:#241F44;
  --danger:#F45B69;
  --radius:14px;
}
*{box-sizing:border-box;}
body{
  margin:0;
  background:
    linear-gradient(var(--bg-grid) 1px, transparent 1px) 0 0/100% 32px,
    linear-gradient(90deg, var(--bg-grid) 1px, transparent 1px) 0 0/32px 100%,
    var(--bg);
  color:var(--text);
  font-family:'Inter',sans-serif;
  padding:32px 20px 80px;
  min-height:100vh;
}
.wrap{max-width:1180px;margin:0 auto;}
header{margin-bottom:36px;}
.eyebrow{
  font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:0.14em;
  text-transform:uppercase;color:var(--amber);display:flex;align-items:center;gap:8px;margin-bottom:10px;
}
.eyebrow::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--amber);box-shadow:0 0 8px var(--amber);}
h1{font-family:'IBM Plex Mono',monospace;font-size:clamp(28px,4vw,42px);font-weight:700;margin:0 0 10px;letter-spacing:-0.01em;}
h1 span{color:var(--muted-2);}
.sub{color:var(--muted);font-size:15px;line-height:1.6;max-width:640px;}
.card{
  background:linear-gradient(180deg,var(--panel),var(--panel-soft));
  border:1px solid var(--border);border-radius:var(--radius);padding:22px 24px;margin-bottom:24px;
  box-shadow:0 1px 0 rgba(255,255,255,0.02) inset, 0 12px 30px -18px rgba(0,0,0,0.6);
}
.card-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px;}
.card-title{
  font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:600;letter-spacing:0.08em;
  text-transform:uppercase;color:var(--text);display:flex;align-items:center;gap:10px;
}
.card-title .tag{font-size:10px;padding:2px 8px;border-radius:5px;background:var(--border-soft);color:var(--muted);font-weight:500;letter-spacing:0.06em;}
.accent-amber{border-left:3px solid var(--amber);}
.accent-teal{border-left:3px solid var(--teal);}
.accent-violet{border-left:3px solid var(--violet);}
#procTable{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:13px;}
#procTable th{text-align:left;color:var(--muted);font-weight:500;font-size:11px;letter-spacing:0.06em;text-transform:uppercase;padding:0 10px 10px;}
#procTable td{padding:6px 10px;}
#procTable tr:not(.hdr){border-top:1px solid var(--border-soft);}
.chip{display:inline-flex;align-items:center;gap:7px;font-weight:600;color:var(--text);}
.dot{width:10px;height:10px;border-radius:3px;flex:none;}
input.numin{
  width:70px;background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:7px;
  padding:7px 9px;font-family:'IBM Plex Mono',monospace;font-size:13px;transition:border-color .15s;
}
input.numin:focus{outline:none;border-color:var(--amber);}
.icon-btn{
  background:transparent;border:1px solid var(--border);color:var(--muted);border-radius:7px;width:30px;
  height:30px;cursor:pointer;font-size:15px;display:inline-flex;align-items:center;justify-content:center;transition:.15s;
}
.icon-btn:hover{border-color:var(--danger);color:var(--danger);}
.controls-row{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-top:16px;}
.btn{
  font-family:'IBM Plex Mono',monospace;font-weight:600;font-size:13px;border:none;border-radius:9px;
  padding:11px 18px;cursor:pointer;letter-spacing:0.02em;transition:transform .1s, box-shadow .15s;
}
.btn:active{transform:scale(0.97);}
.btn-primary{background:linear-gradient(135deg,var(--amber),#E08A00);color:#1A1200;box-shadow:0 6px 18px -6px rgba(245,166,35,0.55);}
.btn-primary:hover{box-shadow:0 8px 22px -6px rgba(245,166,35,0.75);}
.btn-ghost{background:var(--border-soft);color:var(--text);border:1px solid var(--border);}
.btn-ghost:hover{border-color:var(--muted-2);}
.quantum-field{
  display:flex;align-items:center;gap:9px;font-family:'IBM Plex Mono',monospace;font-size:12px;color:var(--muted);
  background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:8px 12px;
}
.quantum-field input{width:50px;background:transparent;border:none;color:var(--amber);font-family:'IBM Plex Mono',monospace;font-weight:700;font-size:14px;}
.quantum-field input:focus{outline:none;}
.gantt-bar{display:flex;width:100%;height:46px;border-radius:9px;overflow:hidden;border:1px solid var(--border);}
.seg{
  display:flex;align-items:center;justify-content:center;font-family:'IBM Plex Mono',monospace;font-weight:700;
  font-size:12px;color:#0A0F1C;border-right:1px solid rgba(10,15,28,0.35);position:relative;min-width:2px;
  white-space:nowrap;overflow:hidden;
}
.seg.idle{
  background:repeating-linear-gradient(135deg, #1C2740, #1C2740 6px, #182034 6px, #182034 12px);
  color:var(--muted-2);font-weight:600;
}
.gantt-ticks{position:relative;height:20px;margin-top:6px;font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted-2);}
.gantt-ticks span{position:absolute;transform:translateX(-50%);}
.gantt-wrap{margin-bottom:4px;}
table.results{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:13px;margin-top:16px;}
table.results thead th{text-align:left;padding:10px 12px;font-size:11px;letter-spacing:0.06em;text-transform:uppercase;color:#0A0F1C;font-weight:700;}
table.results tbody td{padding:10px 12px;border-bottom:1px solid var(--border-soft);}
table.results tbody tr:nth-child(odd){background:rgba(255,255,255,0.015);}
table.results tbody tr:hover{background:rgba(255,255,255,0.045);}
table.results tfoot td{padding:12px;font-weight:700;border-top:1px solid var(--border);color:var(--text);}
.head-amber{background:linear-gradient(90deg,var(--amber),#c98718);}
.head-teal{background:linear-gradient(90deg,var(--teal),#1ea89d);}
.head-violet{background:linear-gradient(90deg,var(--violet),#6a5be0);}
table.compare{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:13px;}
table.compare thead th{text-align:left;padding:12px;font-size:11px;letter-spacing:0.06em;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--border);}
table.compare tbody td{padding:14px 12px;border-bottom:1px solid var(--border-soft);}
table.compare tbody tr:hover{background:rgba(255,255,255,0.03);}
.algo-pill{display:inline-flex;align-items:center;gap:8px;font-weight:700;padding:5px 12px;border-radius:20px;font-size:12px;}
.pill-amber{background:var(--amber-dim);color:var(--amber);}
.pill-teal{background:var(--teal-dim);color:var(--teal);}
.pill-violet{background:var(--violet-dim);color:var(--violet);}
.bar-track{background:var(--border-soft);border-radius:6px;height:10px;overflow:hidden;width:100%;min-width:120px;}
.bar-fill{height:100%;border-radius:6px;}
.best-badge{font-size:10px;font-weight:700;letter-spacing:0.05em;color:#0A0F1C;background:var(--amber);padding:2px 8px;border-radius:5px;margin-left:8px;}
.metric-cell{display:flex;align-items:center;gap:10px;}
.metric-num{width:44px;flex:none;text-align:right;font-weight:700;}
.foot-note{color:var(--muted-2);font-size:12px;font-family:'IBM Plex Mono',monospace;margin-top:28px;text-align:center;letter-spacing:0.02em;}
@media(max-width:640px){
  .card{padding:16px;}
  #procTable{font-size:11px;}
  input.numin{width:52px;}
}
"""

INDEX_JS = """
const palette = ['#F5A623','#34D3C9','#8C7CFF','#F45B69','#4CB963','#FFD23F','#5BC0EB','#E4572E','#C084FC','#2EC4B6'];
function refreshCount(){
  document.getElementById('procCount').textContent =
    document.querySelectorAll('#procBody tr').length + ' processes';
}
function addRow(){
  const tbody = document.getElementById('procBody');
  const idx = tbody.querySelectorAll('tr').length + 1;
  const color = palette[(idx - 1) % palette.length];
  const tr = document.createElement('tr');
  tr.innerHTML =
    '<td><span class="chip"><span class="dot" style="background:' + color + '"></span>' +
    '<input class="numin" style="width:56px" type="text" name="pid" value="P' + idx + '"></span></td>' +
    '<td><input class="numin" type="number" name="at" min="0" value="0"></td>' +
    '<td><input class="numin" type="number" name="bt" min="1" value="1"></td>' +
    '<td><button type="button" class="icon-btn" onclick="removeRow(this)">&#10005;</button></td>';
  tbody.appendChild(tr);
  refreshCount();
}
function removeRow(btn){
  const tbody = document.getElementById('procBody');
  if (tbody.querySelectorAll('tr').length <= 1) return;
  btn.closest('tr').remove();
  refreshCount();
}
refreshCount();
"""

PAGE_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{{ title }}</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>{{ css | safe }}</style>
</head>
<body>
<div class="wrap">
{{ body | safe }}
<div class="foot-note">FCFS &middot; Non-Preemptive SJF &middot; Round Robin &mdash; computed in Python (Flask)</div>
</div>
</body>
</html>"""


def render_page(title: str, body_html: str) -> str:
    return render_template_string(PAGE_SHELL, title=title, css=CSS, body=body_html)


# =========================================================================
# Routes
# =========================================================================

@app.route("/", methods=["GET"])
def index():
    body = (
        "<header>"
        '<div class="eyebrow">Scheduling Kernel &middot; Simulator</div>'
        "<h1>Scheduler Bench<span>_</span></h1>"
        '<p class="sub">Enter arrival time and burst time for each process, then compare '
        "FCFS, SJF, and Round Robin side by side &mdash; complete with Completion Time, "
        "Turnaround Time, Waiting Time, and averages for every algorithm.</p>"
        "</header>"
        '<div class="card">'
        '<div class="card-head"><div class="card-title">01 &middot; Process Queue '
        '<span class="tag" id="procCount">5 processes</span></div></div>'
        '<form action="/simulate" method="POST">'
        '<table id="procTable">'
        '<tr class="hdr"><th>Process</th><th>Arrival Time</th><th>Burst Time</th><th></th></tr>'
        f'<tbody id="procBody">{default_rows()}</tbody>'
        "</table>"
        '<div class="controls-row">'
        '<button type="button" class="btn btn-ghost" onclick="addRow()">+ Add Process</button>'
        '<div class="quantum-field">Time Quantum (RR) '
        '<input type="number" name="quantum" id="quantum" min="1" value="2"></div>'
        '<button type="submit" class="btn btn-primary">&#9654; Run Simulation</button>'
        "</div>"
        "</form>"
        "</div>"
        f"<script>{INDEX_JS}</script>"
    )
    return render_page("Scheduler Bench", body)


@app.route("/simulate", methods=["POST"])
def simulate():
    pids = request.form.getlist("pid")
    ats = request.form.getlist("at")
    bts = request.form.getlist("bt")

    try:
        quantum = max(1, int(request.form.get("quantum", "2").strip()))
    except (ValueError, TypeError):
        quantum = 2

    processes: List[Proc] = []
    n = min(len(pids), len(ats), len(bts))
    for i in range(n):
        pid = pids[i].strip() or f"P{i + 1}"
        try:
            at = max(0, int(ats[i].strip()))
        except (ValueError, TypeError):
            at = 0
        try:
            bt = max(1, int(bts[i].strip()))
        except (ValueError, TypeError):
            bt = 1
        processes.append(Proc(pid, at, bt))

    if not processes:
        processes.append(Proc("P1", 0, 5))

    fcfs = compute_fcfs(processes)
    sjf = compute_sjf(processes)
    rr = compute_rr(processes, quantum)

    content = (
        "<header>"
        '<div class="eyebrow">Scheduling Kernel &middot; Results</div>'
        "<h1>Simulation Results<span>_</span></h1>"
        f'<p class="sub">{len(processes)} processes &middot; Round Robin quantum = {quantum}</p>'
        '<a class="btn btn-ghost" href="/" style="text-decoration:none;display:inline-block;margin-top:6px;">&#9664; Edit Processes</a>'
        "</header>"
        + algo_card("02 &middot; First Come First Served", "FCFS &middot; Non-Preemptive",
                    "accent-amber", "head-amber", fcfs, processes)
        + algo_card("03 &middot; Shortest Job First", "SJF &middot; Non-Preemptive",
                    "accent-teal", "head-teal", sjf, processes)
        + algo_card("03 &middot; Round Robin", f"RR &middot; Quantum = {quantum}",
                    "accent-violet", "head-violet", rr, processes)
        + build_comparison(fcfs, sjf, rr)
    )
    return render_page("Scheduler Bench — Results", content)


if __name__ == "__main__":
    print("Scheduler Bench is running -> http://localhost:8080")
    app.run(host="0.0.0.0", port=8080, debug=False)
