#!/usr/bin/python3
"""Checks one suite's qa-report.md and run report against the plan, mechanically.

It does the structural part of "Accepting a Suite" (executing-qa-test-plans SKILL.md)
in milliseconds, so the orchestrator only opens the FAIL screenshots: headings and
header fields of the report template (evaluation-standard.md § 13), the quality score
arithmetic and its status, the Bug Register columns and severities, every scenario ID
of the suite present in Scenario Results with a valid outcome, evidence files that
exist, Recommended Actions bullets, strategy-specific sections, and the run report's
STATUS line. It never judges whether a screenshot shows the claimed bug.

Usage:
  /usr/bin/python3 check-report.py --plan <plan.md> --suite S-0NN --report <evidence-dir>/qa-report.md \
    [--run-report <run-dir>/S-0NN.md] [--findings-out <run-dir>/<lane>.findings.md] [--run-id <run-id>]

Prints one line per check (PASS / FAIL / WARN) and a summary; exit 1 when any check FAILs.
--findings-out appends every High and Medium bug as a block for make-package.sh --role verify
(skipping IDs already in the file), so a lane's pending findings accumulate in one file.

Python 3.9+, standard library only. Reuses the parser of render-results.py (same directory).
"""
import argparse
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("render_results", os.path.join(HERE, "render-results.py"))
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)

WEIGHTS = [("Functional", 30), ("Validation", 20), ("Navigation", 15), ("Visual", 15), ("Accessibility", 10), ("Console", 10)]
OUTCOME = re.compile(r"^\s*\**(PASS|FAIL|BLOCKED|not run|N/A)\b", re.I)
SEVERITY = re.compile(r"🔴|🟡|🟢|\b(high|medium|low|alta|media|baja)\b", re.I)
EVIDENCE_FILE = re.compile(r"[\w./-]+\.(png|jpe?g|gif|webp|mp4|mov|txt|log|xml|json|junit\.xml)\b", re.I)
STRATEGY_SECTIONS = {
    "platform-discovery": ["Scope", "Navigation drift"],
    "api-blackbox": ["API coverage"],
    "multi-tenant-access": ["Results by organisation"],
}
NA = re.compile(r"(?i)^\s*n/?a\b")


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, ok, label, detail=""):
        self.rows.append(("PASS" if ok else "FAIL", label, detail))

    def warn(self, label, detail=""):
        self.rows.append(("WARN", label, detail))

    @property
    def failed(self):
        return sum(1 for s, _, _ in self.rows if s == "FAIL")


def plan_suite(plan_path, suite):
    """Returns (header fields, scenario IDs) of `### Suite <suite>:` in the plan."""
    with open(plan_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    body, on, fence = [], False, False
    for line in lines:
        if line.startswith(("```", "~~~")):
            fence = not fence
            continue
        if fence:
            continue
        if re.match(r"^#{1,3} ", line) and on:
            if re.match(r"^### Suite ", line) or re.match(r"^#{1,2} ", line):
                break
        if re.match(r"^### Suite %s:" % re.escape(suite), line):
            on = True
            continue
        if on:
            body.append(line)
    if not body:
        sys.exit("check-report: suite heading not found in plan: '### Suite %s:'" % suite)
    fields = {}
    for line in body:
        if "**Strategy:**" in line:
            for key, value in re.findall(r"\*\*([^*:]+):\*\*\s*([^·\n]+)", line):
                fields[key.strip()] = value.strip()
            break
    ids = []
    for line in body:
        m = re.match(r"^\|\s*(%s-\d+)\s*\|" % re.escape(suite), line)
        if m:
            ids.append(m.group(1))
    return fields, ids


def section_lines(sections, *names):
    return rr.find_section(sections, *names)


def files_in(text):
    return [m.group(0).strip("`") for m in EVIDENCE_FILE.finditer(text or "")]


def check_files(c, label, text, evidence_dir):
    missing = [f for f in files_in(text) if not os.path.exists(os.path.join(evidence_dir, f)) and not os.path.exists(f)]
    c.add(not missing, label, ", ".join(missing))
    return not missing


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--suite", required=True)
    ap.add_argument("--report", required=True, help="the suite's qa-report.md")
    ap.add_argument("--run-report", default="", help="the worker's run report in the run dir")
    ap.add_argument("--findings-out", default="", help="append High/Medium bugs as findings for the verify worker")
    ap.add_argument("--run-id", default="")
    a = ap.parse_args()
    c = Checks()

    fields, plan_ids = plan_suite(a.plan, a.suite)
    strategy = fields.get("Strategy", "")
    platform = fields.get("Platform", "")
    evidence_dir = os.path.dirname(os.path.abspath(a.report))

    if not os.path.exists(a.report):
        c.add(False, "qa-report.md exists", a.report)
        return finish(c)
    with open(a.report, encoding="utf-8") as f:
        text = f.read()
    pre, sections = rr.split_sections(text)
    r = rr.parse_report(a.report)
    meta = r["meta"]

    # Header
    title_line = next((l for l in pre if l.startswith("# ")), "")
    c.add(title_line.startswith("# QA Report — "), "title is '# QA Report — <suite title>'", title_line)
    if platform in ("ios", "android"):
        c.add("(mobile" in title_line.lower(), "mobile title ends with (Mobile iOS) / (Mobile Android)", title_line)
    for key in ("Date", "URL", "Platform and device", "Lane", "Suite", "Strategy", "Run", "Account", "Quality Score"):
        c.add(bool(meta.get(key)), "header field **%s:**" % key)
    c.add(meta.get("Suite", "").strip() == a.suite, "header Suite matches %s" % a.suite, meta.get("Suite", ""))
    if a.run_id:
        c.add(meta.get("Run", "").strip() == a.run_id, "header Run matches %s" % a.run_id, meta.get("Run", ""))
    c.add(not re.search(r"(?i)(password|token|secret|api[_-]?key)\s*[:=]\s*\S{6,}", text), "no credential-looking values in the report")

    # Score
    c.add(r["score"] is not None, "Quality Score is a number", meta.get("Quality Score", ""))
    bh, brows = rr.parse_table(section_lines(sections, "Quality Score Breakdown"))
    score_col = rr.column(bh, "score")
    total, weight_sum, found = 0.0, 0, []
    for name, weight in WEIGHTS:
        row = next((x for x in brows if name.lower() in rr.cell(x, 0).lower()), None)
        if row is None:
            continue
        found.append(name)
        val = rr.cell(row, score_col)
        if NA.match(val):
            continue
        m = re.match(r"\s*\**(\d{1,3})", val)
        if m:
            total += int(m.group(1)) * weight
            weight_sum += weight
        else:
            c.add(False, "dimension %s has a numeric score or N/A" % name, val)
    c.add(len(found) == 6, "six score dimensions in the breakdown", "found: %s" % ", ".join(found))
    computed = round(total / weight_sum) if weight_sum else None
    if computed is not None and r["score"] is not None:
        c.add(abs(computed - r["score"]) <= 1, "overall = Σ score × weight (renormalised for N/A)",
              "stated %s, computed %s" % (r["score"], computed))
        expected = rr.score_status(r["score"])
        c.add(expected.lower() in r["status"].lower(), "Executive Summary status matches the score thresholds",
              "score %s → %s, report says '%s'" % (r["score"], expected, r["status"]))

    # Bug Register
    bug_lines = section_lines(sections, "Bug Register")
    c.add(bool(bug_lines), "## Bug Register present")
    bh, brows = rr.parse_table(bug_lines)
    c.add(len(bh) >= 4 and rr.column(bh, "id") is not None and rr.column(bh, "severity") is not None
          and rr.column(bh, "description") is not None and rr.column(bh, "evidence") is not None,
          "Bug Register has ID / Severity / Description / Evidence columns", " | ".join(bh))
    if not r["bugs"]:
        c.add("no issues found" in " ".join(bug_lines).lower(), "empty Bug Register says 'No issues found during this run.'")
    for row in brows:
        bid = rr.cell(row, rr.column(bh, "id"))
        if not bid:
            continue
        sev = rr.cell(row, rr.column(bh, "severity"))
        c.add(bool(SEVERITY.search(sev)), "bug %s has a severity" % bid, sev)
        desc = rr.cell(row, rr.column(bh, "description"))
        c.add(bool(desc) and not re.match(r"^[*`\[]", desc), "bug %s description starts with a plain sentence" % bid, desc[:60])
        ev = rr.cell(row, rr.column(bh, "evidence"))
        c.add(bool(files_in(ev)), "bug %s names an evidence file" % bid, ev)
        check_files(c, "bug %s evidence exists" % bid, ev, evidence_dir)

    # Scenario Results
    sh, srows = rr.parse_table(section_lines(sections, "Scenario Results"))
    seen = {}
    for s in r["scenarios"]:
        if s["id"]:
            seen[s["id"]] = s
    missing = [i for i in plan_ids if i not in seen]
    c.add(not missing, "every plan scenario of %s has a row (%d in plan)" % (a.suite, len(plan_ids)), ", ".join(missing))
    c.add(bool(plan_ids), "plan lists scenario IDs for %s" % a.suite)
    for sid, s in seen.items():
        ok = bool(OUTCOME.match(s["outcome"]))
        c.add(ok, "scenario %s outcome is PASS / FAIL / BLOCKED / not run / N/A" % sid, s["outcome"])
        word = (OUTCOME.match(s["outcome"]).group(1).upper() if ok else "")
        if word == "FAIL":
            c.add(bool(files_in(s["evidence"])), "FAIL %s names an evidence file" % sid, s["evidence"])
            check_files(c, "FAIL %s evidence exists" % sid, s["evidence"], evidence_dir)
        elif word == "PASS":
            c.add(bool(s["evidence"].strip()), "PASS %s has evidence (file or snapshot)" % sid, s["evidence"])
            if files_in(s["evidence"]):
                check_files(c, "PASS %s evidence exists" % sid, s["evidence"], evidence_dir)
        elif word == "BLOCKED":
            c.add(bool(s["note"].strip()), "BLOCKED %s names its precondition" % sid)
    auth_ids = [i for i in seen if re.search(r"AUTH-\d\d$", i)]
    if auth_ids and len(auth_ids) < 12:
        c.warn("AUTH scenarios present but fewer than 12", ", ".join(sorted(auth_ids)))

    # Fixed sections
    for name in ("Executive Summary", "Accessibility Audit", "Console & Logs Health", "Visual & UX Observations",
                 "Recommended Actions", "Corrected false positives", "Test data flags", "Coverage gaps", "Evidence Files"):
        lines = section_lines(sections, name)
        c.add(bool(lines) and any(l.strip() for l in lines), "## %s present and not empty" % name)
    for name in ("Must Fix", "Should Fix", "Nice to Have"):
        found_h, bullets = False, 0
        for line in section_lines(sections, "Recommended Actions"):
            if re.match(r"###\s+%s" % re.escape(name), line):
                found_h = True
                continue
            if found_h and re.match(r"###\s+", line):
                break
            if found_h and re.match(r"\s*-\s+\S", line):
                bullets += 1
        c.add(found_h and bullets > 0, "### %s has at least one bullet" % name)
    for name in STRATEGY_SECTIONS.get(strategy, []):
        c.add(bool(section_lines(sections, name)), "strategy %s: ## %s present" % (strategy, name))
    if strategy == "functional-regression" and "shell" in fields.get("Tool", ""):
        c.add(bool(section_lines(sections, "Scripted suite results")), "scripted suite: ## Scripted suite results present")
    eh, erows = rr.parse_table(section_lines(sections, "Evidence Files"))
    for row in erows:
        name = rr.cell(row, 0)
        if files_in(name):
            check_files(c, "Evidence Files: %s exists" % name.strip("`"), name, evidence_dir)
    unref = []
    try:
        for f in sorted(os.listdir(evidence_dir)):
            if re.search(r"\.(png|jpe?g|gif|webp)$", f, re.I) and f not in text:
                unref.append(f)
    except OSError:
        pass
    if unref:
        c.warn("%d screenshot(s) in the evidence dir not referenced by the report" % len(unref), ", ".join(unref[:8]))

    # Run report
    if a.run_report:
        if os.path.exists(a.run_report):
            with open(a.run_report, encoding="utf-8") as f:
                rtext = f.read()
            m = re.search(r"(?im)^\s*\**STATUS\**\s*:\**\s*(PASS|FAIL|BLOCKED)\b", rtext)
            c.add(bool(m), "run report has a STATUS line", a.run_report)
            if m:
                c.add(m.group(1).upper() == "PASS", "run report STATUS is PASS (execution completed)", m.group(1))
        else:
            c.add(False, "run report exists", a.run_report)

    # Findings for the verify worker
    if a.findings_out:
        existing = ""
        if os.path.exists(a.findings_out):
            with open(a.findings_out, encoding="utf-8") as f:
                existing = f.read()
        added = 0
        with open(a.findings_out, "a", encoding="utf-8") as f:
            for b in r["bugs"]:
                if b["severity"] not in ("high", "medium") or ("### %s" % b["id"]) in existing:
                    continue
                f.write("### %s (%s)\n" % (b["id"], b["severity"].capitalize()))
                f.write("Suite: %s · Lane: %s · qa-report: %s · Evidence dir: %s\n" % (a.suite, r["lane"], os.path.abspath(a.report), evidence_dir))
                f.write("Description (from the report): %s\n" % b["description"])
                f.write("Evidence: %s\n" % b["evidence"])
                f.write("Steps: <orchestrator: copy from the description if not explicit>\nExpected: <…>\nActual: <…>\n\n")
                added += 1
        c.rows.append(("INFO", "findings appended to %s" % a.findings_out, "%d new High/Medium" % added))
    return finish(c)


def finish(c):
    for status, label, detail in c.rows:
        print("%-5s %s%s" % (status, label, (" — " + detail) if detail else ""))
    fails = c.failed
    print("check-report: %d checks, %d failed, %d warnings" % (
        sum(1 for s, _, _ in c.rows if s in ("PASS", "FAIL")), fails, sum(1 for s, _, _ in c.rows if s == "WARN")))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
