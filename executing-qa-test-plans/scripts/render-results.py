#!/usr/bin/env python3
"""Renders a QA run's results as one self-contained HTML page.

Reads the run's suite reports, evidence/<app>/<suite>/<run-id>[-aN]/qa-report.md, written
by executing-qa-test-plans workers (evaluation-standard.md § 13), keeping only the highest
attempt per suite. It writes a page that opens with no network: inline CSS, no scripts,
and screenshots linked by relative path, following the team's qa-report-render rules.
The markdown reports stay the source of truth: the page shows only what they contain.

Usage:
  /usr/bin/python3 render-results.py --evidence-root evidence/<app-slug> --run-id <run-id> \
    --out evidence/<app-slug>/QA-RUN-RESULTS-<run-id>.html --title "<App> — QA run" \
    [--lang es|en|bi] [--summary evidence/<app-slug>/QA-RUN-SUMMARY-<run-id>.md] \
    [--clickup-note "<why tickets were not created>"]

Python 3.9+, standard library only. Prints the output path and counts.
"""
import argparse
import glob
import html
import os
import re
import sys

ES = {
    "run": "Corrida", "date": "Fecha", "url": "URL", "accounts": "Cuentas", "lanes": "Carriles",
    "score": "Puntaje de calidad", "suites": "Suites", "pass": "PASS", "fail": "FAIL",
    "blocked": "BLOCKED", "notrun": "No ejecutado", "bugs": "Bugs", "high": "Alta",
    "medium": "Media", "low": "Baja", "dimensions": "Puntaje por dimensión",
    "verdict": "Veredicto", "matrix": "Resultados por suite", "suite": "Suite",
    "lane": "Carril", "device": "Plataforma y dispositivo", "status": "Estado",
    "register": "Lista priorizada de bugs", "none_bugs": "No se registraron bugs en esta corrida.",
    "verification": "Verificación", "unverified": "sin verificar", "record": "Registro",
    "fp": "Falsos positivos corregidos", "gaps": "Brechas de cobertura",
    "testdata": "Datos de prueba a revisar", "actions": "Acciones recomendadas",
    "kind": "Tipo", "item": "Ítem", "details": "Detalle por suite", "scenario": "Escenario",
    "outcome": "Resultado", "evidence": "Evidencia", "note": "Nota", "source": "Fuente",
    "nothing": "Sin datos.", "clickup": "ClickUp", "missing": "falta",
    "clickup_default": "Esta corrida no usó ClickUp: los resultados se entregan en esta página.",
    "blocked_note": "BLOCKED = no se pudo ejecutar (falta una precondición); no es un defecto.",
}
EN = {
    "run": "Run", "date": "Date", "url": "URL", "accounts": "Accounts", "lanes": "Lanes",
    "score": "Quality score", "suites": "Suites", "pass": "PASS", "fail": "FAIL",
    "blocked": "BLOCKED", "notrun": "Not run", "bugs": "Bugs", "high": "High",
    "medium": "Medium", "low": "Low", "dimensions": "Score per dimension",
    "verdict": "Verdict", "matrix": "Results by suite", "suite": "Suite",
    "lane": "Lane", "device": "Platform and device", "status": "Status",
    "register": "Priority fix list", "none_bugs": "No bugs were recorded in this run.",
    "verification": "Verification", "unverified": "unverified", "record": "Record",
    "fp": "Corrected false positives", "gaps": "Coverage gaps",
    "testdata": "Test data to review", "actions": "Recommended actions",
    "kind": "Kind", "item": "Item", "details": "Details per suite", "scenario": "Scenario",
    "outcome": "Outcome", "evidence": "Evidence", "note": "Note", "source": "Source",
    "nothing": "No data.", "clickup": "ClickUp", "missing": "missing",
    "clickup_default": "This run did not use ClickUp: the results are delivered on this page.",
    "blocked_note": "BLOCKED = could not be run (a precondition is missing); it is not a defect.",
}
LABELS = {"es": ES, "en": EN, "bi": {k: ES[k] if ES[k] == EN[k] else "%s / %s" % (ES[k], EN[k]) for k in ES}}
DIMENSIONS = ["Functional", "Validation", "Navigation", "Visual", "Accessibility", "Console"]
# Sections rendered as-is inside each suite's details, when present.
EXTRA_SECTIONS = ["Scope", "Navigation drift", "Results by organisation", "API coverage",
                  "Scripted suite results", "Accessibility Audit", "Console & Logs Health",
                  "Visual & UX Observations"]

CSS = """
:root{--bg:#0f1117;--surface:#1a1d27;--border:#2e3347;--text:#e2e8f0;--text-muted:#8892a4;
--green:#22c55e;--red:#ef4444;--yellow:#f59e0b;--blue:#3b82f6;--purple:#a78bfa}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
.container{max-width:1100px;margin:0 auto;padding:24px 16px 64px}
h1{margin:0 0 8px;font-size:26px}
h2{color:var(--purple);font-size:19px;margin:36px 0 12px;border-bottom:1px solid var(--border);padding-bottom:6px}
h3{font-size:15px;margin:16px 0 8px;color:var(--text-muted)}
a{color:var(--blue)}
code{background:var(--bg);border:1px solid var(--border);border-radius:4px;padding:0 4px;font-size:13px}
.header{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:20px}
.meta{display:flex;flex-wrap:wrap;gap:8px 24px;margin-top:8px}
.label{color:var(--text-muted);margin-right:6px}
.score-card{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-top:20px}
.score-item{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px}
.score-item .value{font-size:26px;font-weight:700;display:block}
.score-item .label{display:block;margin:0}
.score-item.pass .value{color:var(--green)}.score-item.fail .value{color:var(--red)}.score-item.warn .value{color:var(--yellow)}
.score-item.total{border-color:var(--purple)}
.table-wrap{overflow-x:auto;margin:8px 0}
table{width:100%;border-collapse:collapse;background:var(--surface);border:1px solid var(--border);border-radius:8px}
th,td{padding:8px 10px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}
th{color:var(--text-muted);font-weight:600}
.badge{display:inline-block;border-radius:999px;padding:1px 10px;font-size:12px;font-weight:700;white-space:nowrap;border:1px solid}
.badge.pass{color:var(--green);border-color:var(--green)}.badge.fail{color:var(--red);border-color:var(--red)}
.badge.warn{color:var(--yellow);border-color:var(--yellow)}.badge.info{color:var(--blue);border-color:var(--blue)}
.bug-card{background:var(--surface);border:1px solid var(--border);border-left:4px solid var(--blue);border-radius:8px;padding:14px;margin:12px 0}
.bug-card.high{border-left-color:var(--red)}.bug-card.medium{border-left-color:var(--yellow)}.bug-card.low{border-left-color:var(--green)}
.bug-id{font-family:ui-monospace,Menlo,monospace;color:var(--text-muted);font-size:13px}
.detail{margin-top:8px}
.tag-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.shots{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}
.shots img{max-width:220px;max-height:420px;border:1px solid var(--border);border-radius:6px;display:block}
.note{background:var(--surface);border:1px solid var(--border);border-left:4px solid var(--yellow);border-radius:8px;padding:12px 14px;margin:10px 0}
.note.info{border-left-color:var(--blue)}
.note ul{margin:4px 0;padding-left:20px}
details{background:var(--surface);border:1px solid var(--border);border-radius:8px;margin:10px 0;padding:10px 14px}
summary{cursor:pointer;font-weight:600}
details table{background:var(--bg)}
.muted{color:var(--text-muted)}
"""


def esc(text):
    return html.escape(text or "", quote=True)


def inline_md(text):
    """Escapes, then renders `code` and **bold**: the only inline markup reports use."""
    out = esc(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return out


def split_sections(text):
    """Returns (preamble lines, {heading: lines}) for level-2 headings, ignoring fences."""
    pre, sections, current, fence = [], {}, None, False
    for line in text.splitlines():
        if line.strip().startswith(("```", "~~~")):
            fence = not fence
        if not fence and line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
            continue
        (sections[current] if current else pre).append(line)
    return pre, sections


def find_section(sections, *prefixes):
    for name, lines in sections.items():
        if any(name.lower().startswith(p.lower()) for p in prefixes):
            return lines
    return []


def table_rows(lines):
    rows = []
    for line in lines:
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def parse_table(lines):
    block = []
    for line in lines:
        if line.strip().startswith("|"):
            block.append(line)
        elif block:
            break
    rows = table_rows(block)
    return (rows[0], rows[1:]) if rows else ([], [])


def md_block(lines):
    """Renders a section body: tables, bullet lists and paragraphs. Escapes everything."""
    out, i = [], 0
    lines = [l for l in lines if l.strip() not in ("---", "***")]
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i]); i += 1
            rows = table_rows(block)
            if rows:
                out.append('<div class="table-wrap"><table><tr>%s</tr>' % "".join("<th>%s</th>" % inline_md(c) for c in rows[0]))
                for r in rows[1:]:
                    out.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline_md(c) for c in r))
                out.append("</table></div>")
            continue
        if re.match(r"\s*[-*]\s+", line):
            items = []
            while i < len(lines) and re.match(r"\s*[-*]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*]\s+", "", lines[i])); i += 1
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline_md(t) for t in items))
            continue
        if line.startswith("### "):
            out.append("<h3>%s</h3>" % inline_md(line[4:]))
        elif line.strip():
            out.append("<p>%s</p>" % inline_md(line.strip()))
        i += 1
    return "".join(out)


def column(header, *names):
    for i, h in enumerate(header):
        if any(n.lower() in h.lower() for n in names):
            return i
    return None


def cell(row, i):
    return row[i] if i is not None and i < len(row) else ""


def outcome_class(text):
    t = (text or "").upper()
    if "BLOCKED" in t:
        return "warn", "blocked"
    if "NOT RUN" in t or "NO EJECUTADO" in t:
        return "info", "notrun"
    if "N/A" in t:
        return "info", None
    if "CONDITIONAL" in t:
        return "warn", None
    if "FAIL" in t:
        return "fail", "fail"
    if "PASS" in t:
        return "pass", "pass"
    return "info", None


def severity(text):
    t = (text or "").lower()
    if "🔴" in t or "high" in t or "alta" in t or "critical" in t:
        return "high"
    if "🟡" in t or "medium" in t or "media" in t:
        return "medium"
    if "🟢" in t or "low" in t or "baja" in t:
        return "low"
    return "medium"


def score_status(score):
    return "PASS" if score >= 85 else ("CONDITIONAL PASS" if score >= 60 else "FAIL")


def score_class(score):
    return "pass" if score >= 85 else ("warn" if score >= 60 else "fail")


def is_empty(lines):
    body = " ".join(l.strip() for l in lines).strip(" -*")
    return not body or re.fullmatch(r"(?i)(none|ninguno|ninguna|n/a)[ .]*(for this run\.?)?", body) is not None


def parse_meta(pre):
    meta, title = {}, ""
    for line in pre:
        if line.startswith("# ") and not title:
            title = re.sub(r"^#\s*QA Report\s*[—-]\s*", "", line[2:].strip()) or line[2:].strip()
        for key, value in re.findall(r"\*\*([^*:]+):\*\*\s*([^·\n]+)", line):
            meta.setdefault(key.strip(), value.strip())
    return title, meta


def parse_report(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    pre, sections = split_sections(text)
    title, meta = parse_meta(pre)
    status = ""
    for line in find_section(sections, "Executive Summary", "Resumen"):
        m = re.search(r"\*\*(?:Status|Estado):\*\*\s*(.+)", line)
        if m:
            status = m.group(1).strip()
            break
    score = None
    m = re.match(r"\s*(\d{1,3})", meta.get("Quality Score", ""))
    if m:
        score = min(int(m.group(1)), 100)
    dims = {}
    bh, brows = parse_table(find_section(sections, "Quality Score Breakdown"))
    for row in brows:
        name = cell(row, 0)
        val = re.match(r"\s*\**(\d{1,3})", cell(row, column(bh, "score")))
        for d in DIMENSIONS:
            if d.lower() in name.lower() and val:
                dims[d] = int(val.group(1))
    suite_dir = os.path.dirname(path)
    verdicts = {}
    vh, vrows = parse_table(find_section(sections, "Verification"))
    for row in vrows:
        verdicts[cell(row, column(vh, "bug"))] = cell(row, column(vh, "verdict", "veredicto"))
    records = {}
    rh, rrows = parse_table(find_section(sections, "Record check"))
    for row in rrows:
        records[cell(row, column(rh, "bug"))] = (cell(row, column(rh, "record")), cell(row, column(rh, "link")))
    bugs = []
    bh, brows = parse_table(find_section(sections, "Bug Register"))
    for row in brows:
        bid = cell(row, column(bh, "id"))
        if not bid:
            continue
        bugs.append({
            "id": bid, "severity": severity(cell(row, column(bh, "severity"))),
            "description": cell(row, column(bh, "description")),
            "evidence": cell(row, column(bh, "evidence")),
            "verdict": verdicts.get(bid, ""), "record": records.get(bid, ("", "")),
            "suite_dir": suite_dir, "suite": meta.get("Suite", ""), "lane": meta.get("Lane", ""),
        })
    sh, srows = parse_table(find_section(sections, "Scenario Results"))
    scenarios = [{
        "id": cell(r, column(sh, "id")), "name": cell(r, column(sh, "scenario")),
        "outcome": cell(r, column(sh, "outcome", "result", "status")),
        "evidence": cell(r, column(sh, "evidence")), "note": cell(r, column(sh, "note")),
    } for r in srows]
    actions = []
    current = None
    for line in find_section(sections, "Recommended Actions"):
        h3 = re.match(r"###\s+(.+)", line)
        if h3:
            current = h3.group(1).strip()
            continue
        b = re.match(r"\s*-\s+(.+)", line)
        if b and current and not re.match(r"(?i)must fix", current) and not is_empty([b.group(1)]):
            actions.append((current, b.group(1).strip()))
    return {
        "path": path, "dir": suite_dir, "title": title, "meta": meta, "status": status,
        "suite": meta.get("Suite") or os.path.basename(os.path.dirname(suite_dir)),
        "lane": meta.get("Lane", ""), "score": score, "dims": dims, "bugs": bugs,
        "scenarios": scenarios, "actions": actions,
        "fp": find_section(sections, "Corrected false positives"),
        "gaps": find_section(sections, "Coverage gaps"),
        "testdata": find_section(sections, "Test data flags"),
        "extra": [(name, find_section(sections, name)) for name in EXTRA_SECTIONS
                  if find_section(sections, name) and not is_empty(find_section(sections, name))],
    }


def evidence_links(evidence, suite_dir, out_dir, images, missing_label):
    files = [f.strip(" `") for f in re.split(r"<br\s*/?>|[,;\s]+", evidence or "") if f.strip(" `")]
    files = [f for f in files if re.search(r"\.(png|jpe?g|gif|webp|mp4|mov|txt|log|xml|zip)$", f, re.I)]
    parts = []
    for name in files:
        target = os.path.join(suite_dir, name)
        href = os.path.relpath(target, out_dir).replace(os.sep, "/")
        exists = os.path.exists(target)
        if images and exists and re.search(r"\.(png|jpe?g|gif|webp)$", name, re.I):
            parts.append('<a href="%s"><img loading="lazy" src="%s" alt="%s"></a>' % (esc(href), esc(href), esc(name)))
        else:
            parts.append('<a href="%s">%s</a>%s' % (esc(href), esc(name), "" if exists else ' <span class="muted">(%s)</span>' % missing_label))
    return parts


def find_reports(root, run_id):
    """Highest attempt per suite: <root>/<suite>/<run-id>[-aN]/qa-report.md."""
    best = {}
    for path in glob.glob(os.path.join(root, "*", run_id + "*", "qa-report.md")):
        folder = os.path.basename(os.path.dirname(path))
        m = re.fullmatch(re.escape(run_id) + r"(?:-a(\d+))?", folder)
        if not m:
            continue
        attempt = int(m.group(1) or 1)
        suite = os.path.basename(os.path.dirname(os.path.dirname(path)))
        if suite not in best or attempt > best[suite][0]:
            best[suite] = (attempt, path)
    return [best[s][1] for s in sorted(best)]


def summary_verdict(path):
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        _, sections = split_sections(f.read())
    return find_section(sections, "Go / no-go", "Go/no-go")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--evidence-root", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--lang", choices=["es", "en", "bi"], default="es")
    ap.add_argument("--summary", default="")
    ap.add_argument("--clickup-note", default="")
    a = ap.parse_args()
    L = LABELS[a.lang]

    paths = find_reports(a.evidence_root, a.run_id)
    if not paths:
        sys.exit("render-results: no qa-report.md under %s/*/%s[-aN]/" % (a.evidence_root, a.run_id))
    reports = [parse_report(p) for p in paths]
    out_dir = os.path.dirname(os.path.abspath(a.out))

    counts = {"pass": 0, "fail": 0, "blocked": 0, "notrun": 0}
    for r in reports:
        r["counts"] = {"pass": 0, "fail": 0, "blocked": 0, "notrun": 0}
        for s in r["scenarios"]:
            key = outcome_class(s["outcome"])[1]
            if key:
                counts[key] += 1
                r["counts"][key] += 1
    bugs = [b for r in reports for b in r["bugs"]]
    order = {"high": 0, "medium": 1, "low": 2}
    bugs.sort(key=lambda b: (order[b["severity"]], b["suite"], b["id"]))
    sev = {k: sum(1 for b in bugs if b["severity"] == k) for k in order}

    def uniq(key):
        return sorted({r["meta"].get(key, "") for r in reports} - {""})

    h = ['<!doctype html><html lang="%s"><head><meta charset="utf-8">'
         '<meta name="viewport" content="width=device-width,initial-scale=1">'
         '<title>%s</title><style>%s</style></head><body><div class="container">'
         % ("es" if a.lang != "en" else "en", esc(a.title), CSS)]
    h.append('<div class="header"><h1>%s</h1><div class="meta">' % esc(a.title))
    for label, values in ((L["run"], [a.run_id]), (L["date"], uniq("Date")), (L["url"], uniq("URL")),
                          (L["lanes"], uniq("Lane")), (L["accounts"], uniq("Account"))):
        if values:
            h.append('<span><span class="label">%s</span><span class="value">%s</span></span>' % (esc(label), inline_md(", ".join(values))))
    h.append("</div></div>")

    scores = [r["score"] for r in reports if r["score"] is not None]
    h.append('<div class="score-card">')
    if scores:
        overall = round(sum(scores) / len(scores))
        h.append('<div class="score-item total %s"><span class="label">%s</span><span class="value">%d/100</span><span class="label">%s</span></div>'
                 % (score_class(overall), L["score"], overall, score_status(overall)))
    h.append('<div class="score-item"><span class="label">%s</span><span class="value">%d</span></div>' % (L["suites"], len(reports)))
    for key, cls in (("pass", "pass"), ("fail", "fail"), ("blocked", "warn"), ("notrun", "")):
        h.append('<div class="score-item %s"><span class="label">%s</span><span class="value">%d</span></div>' % (cls, L[key], counts[key]))
    h.append('<div class="score-item %s"><span class="label">%s (%s · %s · %s)</span><span class="value">%d · %d · %d</span></div>'
             % ("fail" if sev["high"] else ("warn" if bugs else "pass"), L["bugs"], L["high"], L["medium"], L["low"], sev["high"], sev["medium"], sev["low"]))
    h.append("</div>")
    dim_avgs = []
    for d in DIMENSIONS:
        vals = [r["dims"][d] for r in reports if d in r["dims"]]
        if vals:
            dim_avgs.append((d, round(sum(vals) / len(vals))))
    if dim_avgs:
        h.append('<h2>%s</h2><div class="score-card">' % L["dimensions"])
        for d, v in dim_avgs:
            h.append('<div class="score-item %s"><span class="label">%s</span><span class="value">%d</span></div>' % (score_class(v), esc(d), v))
        h.append("</div>")

    verdict = summary_verdict(a.summary)
    if verdict:
        h.append('<h2>%s</h2><div class="note info">%s</div>' % (L["verdict"], md_block(verdict)))
    h.append('<div class="note info"><strong>%s:</strong> %s</div>' % (L["clickup"], inline_md(a.clickup_note or L["clickup_default"])))

    h.append('<h2>%s</h2><div class="table-wrap"><table><tr>%s</tr>' % (L["matrix"], "".join(
        "<th>%s</th>" % L[k] for k in ("suite", "lane", "device", "score", "status", "pass", "fail", "blocked", "notrun"))))
    for r in reports:
        c = r["counts"]
        h.append('<tr><td><strong>%s</strong><br><span class="muted">%s</span></td><td>%s</td><td>%s</td><td>%s</td>'
                 '<td><span class="badge %s">%s</span></td><td>%d</td><td>%d</td><td>%d</td><td>%d</td></tr>'
                 % (esc(r["suite"]), esc(r["title"]), esc(r["lane"]), inline_md(r["meta"].get("Platform and device", "")),
                    "%d/100" % r["score"] if r["score"] is not None else "—",
                    outcome_class(r["status"])[0], esc(r["status"] or "—"), c["pass"], c["fail"], c["blocked"], c["notrun"]))
    h.append("</table></div>")
    if counts["blocked"]:
        h.append('<div class="note">%s</div>' % L["blocked_note"])

    h.append("<h2>%s</h2>" % L["register"])
    if not bugs:
        h.append('<div class="note info">%s</div>' % L["none_bugs"])
    for b in bugs:
        v = b["verdict"].upper()
        vcls = "fail" if ("CONFIRMED" in v or "CONFIRMADO" in v) else ("warn" if "FLAKY" in v else "info")
        record, link = b["record"]
        h.append('<div class="bug-card %s"><div class="bug-id">%s</div><div class="detail">%s</div><div class="tag-row">'
                 '<span class="badge %s">%s</span><span class="badge info">%s</span><span class="badge info">%s</span>'
                 '<span class="badge %s">%s: %s</span>'
                 % (b["severity"], esc(b["id"]), inline_md(b["description"]),
                    {"high": "fail", "medium": "warn", "low": "pass"}[b["severity"]], L[b["severity"]],
                    esc(b["suite"]), esc(b["lane"]), vcls, L["verification"], esc(b["verdict"] or L["unverified"])))
        if record:
            h.append('<span class="badge %s">%s: %s</span>' % ("fail" if "regression" in record.lower() else "info", L["record"], inline_md(record)))
        h.append("</div>")
        if link:
            h.append('<p class="muted">%s</p>' % inline_md(link))
        shots = evidence_links(b["evidence"], b["suite_dir"], out_dir, True, L["missing"])
        if shots:
            h.append('<div class="shots">%s</div>' % "".join(shots))
        h.append("</div>")

    for key, field in (("fp", "fp"), ("gaps", "gaps"), ("testdata", "testdata")):
        blocks = [(r, r[field]) for r in reports if r[field] and not is_empty(r[field])]
        if blocks or key == "gaps":
            h.append("<h2>%s</h2>" % L[key])
        if not blocks and key == "gaps":
            h.append('<div class="note">%s</div>' % L["nothing"])
        for r, lines in blocks:
            h.append('<div class="note"><strong>%s</strong>%s</div>' % (esc(r["suite"]), md_block(lines)))

    actions = [(r, kind, text) for r in reports for kind, text in r["actions"]]
    if actions:
        h.append('<h2>%s</h2><div class="table-wrap"><table><tr><th>%s</th><th>%s</th><th>%s</th></tr>'
                 % (L["actions"], L["suite"], L["kind"], L["item"]))
        for r, kind, text in actions:
            h.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (esc(r["suite"]), esc(kind), inline_md(text)))
        h.append("</table></div>")

    h.append("<h2>%s</h2>" % L["details"])
    for r in reports:
        h.append('<details><summary>%s — %s</summary><div class="table-wrap"><table><tr><th>ID</th><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr>'
                 % (esc(r["suite"]), esc(r["title"]), L["scenario"], L["outcome"], L["evidence"], L["note"]))
        for s in r["scenarios"]:
            links = evidence_links(s["evidence"], r["dir"], out_dir, False, L["missing"])
            h.append('<tr><td>%s</td><td>%s</td><td><span class="badge %s">%s</span></td><td>%s</td><td>%s</td></tr>'
                     % (esc(s["id"]), inline_md(s["name"]), outcome_class(s["outcome"])[0], esc(s["outcome"]),
                        "<br>".join(links) or inline_md(s["evidence"]), inline_md(s["note"])))
        h.append("</table></div>")
        for name, lines in r["extra"]:
            h.append("<h3>%s</h3>%s" % (esc(name), md_block(lines)))
        rel = os.path.relpath(r["path"], out_dir).replace(os.sep, "/")
        h.append('<p class="muted">%s: <a href="%s">%s</a></p></details>' % (L["source"], esc(rel), esc(rel)))

    h.append("</div></body></html>\n")
    os.makedirs(out_dir, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("".join(h))
    print("%s (%d suites, %d scenarios, %d bugs: %d high)" % (a.out, len(reports), sum(counts.values()), len(bugs), sev["high"]))



if __name__ == "__main__":
    main()
