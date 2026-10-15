#!/usr/bin/env bash
# Builds a worker package from a QA plan written with writing-qa-test-plans.
# Sections are found by heading text, so the plan must use the skill's headings.
#
# Usage:
#   bash make-package.sh --plan <plan.md> --suite S-001 --model sonnet --why "<rationale>" \
#     --run-id <run-id> --run-dir <run-dir> --device "<udid | emulator-5554 | chromium>" \
#     --evidence <evidence-dir> --root <QA project root> \
#     [--vault-excerpts <file>] [--clickup-excerpts <file>] [--notes <file>] \
#     [--role test|verify] [--findings <file>] [--attempt N]
#
# --role test (default) runs the suite and writes qa-report.md plus a run report.
# --role verify re-reproduces the findings listed in --findings (required) and
#   appends a verification section; it tests nothing else.
# Attempt 1 writes <run-dir>/<suite>.package.md (or .verify-package.md) and asks
# for <suite>.md (or <suite>.verify.md); attempt N > 1 adds -aN to both, so no
# earlier file is overwritten. Output mode is 600; the script prints the path.
# Fails if a required section is missing, or if the suite lists vault notes or
# ClickUp tickets and the matching excerpts file is not passed.
set -euo pipefail
# The header line uses "·" as separator; byte-based matching would cut fields at
# any other multi-byte character, so force a UTF-8 locale.
export LC_ALL=en_US.UTF-8

die() { printf 'make-package: %s\n' "$1" >&2; exit 1; }

PLAN= SUITE= MODEL= WHY= RUN_ID= RUN_DIR= DEVICE= EVIDENCE= ROOT=
VAULT= CLICKUP= NOTES= ROLE=test FINDINGS= ATTEMPT=1
while [ $# -gt 0 ]; do
  [ $# -ge 2 ] || die "missing value for $1"
  case $1 in
    --plan) PLAN=$2 ;; --suite) SUITE=$2 ;; --model) MODEL=$2 ;; --why) WHY=$2 ;;
    --run-id) RUN_ID=$2 ;; --run-dir) RUN_DIR=$2 ;; --device) DEVICE=$2 ;;
    --evidence) EVIDENCE=$2 ;; --root) ROOT=$2 ;;
    --vault-excerpts) VAULT=$2 ;; --clickup-excerpts) CLICKUP=$2 ;;
    --notes) NOTES=$2 ;; --role) ROLE=$2 ;; --findings) FINDINGS=$2 ;;
    --attempt) ATTEMPT=$2 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift 2
done
for v in PLAN SUITE MODEL WHY RUN_ID RUN_DIR DEVICE EVIDENCE ROOT; do
  eval "[ -n \"\${$v}\" ]" || die "missing --$(printf '%s' "$v" | tr 'A-Z_' 'a-z-')"
done
case $ROLE in test|verify) ;; *) die "--role must be test or verify" ;; esac
[ -f "$PLAN" ] || die "plan not found: $PLAN"
[ -d "$RUN_DIR" ] || die "run dir not found: $RUN_DIR"
for f in NOTES VAULT CLICKUP FINDINGS; do
  eval "val=\${$f}"
  [ -z "$val" ] || [ -f "$val" ] || die "$(printf '%s' "$f" | tr 'A-Z' 'a-z') file not found: $val"
done
[ "$ROLE" != verify ] || [ -n "$FINDINGS" ] || die "--role verify needs --findings <file>"
STANDARD="$(cd "$(dirname "$0")/.." && pwd)/evaluation-standard.md"
[ -f "$STANDARD" ] || die "evaluation standard not found: $STANDARD"

# Prints the first section at heading level $2 whose text is exactly $1, or $1
# followed by " (…)"; a $1 ending in ":" matches as a prefix ("Suite S-004:").
# Stops at the next heading of the same or higher level. Headings inside code
# fences are ignored; CRLF line endings are tolerated.
section() {
  awk -v want="$1" -v lvl="$2" '
    function heading_level(line) { return match(line, /^#+ /) ? RLENGTH - 1 : 0 }
    function matches(text) {
      sub(/[[:space:]]+$/, "", text)
      if (text == want || index(text, want " (") == 1) return 1
      return substr(want, length(want)) == ":" && index(text, want) == 1
    }
    {
      sub(/\r$/, "")
      fence = match($0, /^(`{3,}|~{3,})/) ? RLENGTH : 0
      h = (!infence && !fence) ? heading_level($0) : 0
      if (on && h > 0 && h <= lvl) on = 0
      if (!on && !done && h == lvl && matches(substr($0, lvl + 2))) { on = 1; done = 1 }
      if (on) buf[++n] = $0
      if (fence && !infence) { infence = fence }
      else if (fence && infence && fence >= infence && $0 ~ /^(`+|~+)[[:space:]]*$/) { infence = 0 }
    }
    END {
      while (n > 0 && (buf[n] ~ /^[[:space:]]*$/ || buf[n] == "---")) n--
      for (i = 1; i <= n; i++) print buf[i]
    }' "$PLAN"
}

required() {
  out=$(section "$1" "$2")
  [ -n "$out" ] || die "section not found in plan: '$1'"
  printf '%s\n\n' "$out"
}

is_none() {
  case $(printf '%s' "$1" | tr 'A-Z' 'a-z') in ''|none|-|–|—|n/a) return 0 ;; esac
  return 1
}

SUITE_TEXT=$(section "Suite $SUITE:" 3)
[ -n "$SUITE_TEXT" ] || die "suite heading not found: '### Suite $SUITE:' (append the suite to the plan first)"

header_field() {
  printf '%s\n' "$SUITE_TEXT" | grep -m1 -o "\*\*$1:\*\* [^·]*" | sed -e "s/^\*\*$1:\*\* //" -e 's/[[:space:]]*$//' || true
}
LANE=$(header_field Lane)
STRATEGY=$(header_field Strategy)
TOOL=$(header_field Tool)
TIMEBOX=$(header_field Timebox)
DEPS=$(header_field 'Depends on')
VAULT_NOTES=$(header_field Vault)
TICKETS=$(header_field ClickUp)
[ -n "$LANE" ] || die "suite $SUITE has no **Lane:** in its header line"
if ! is_none "$VAULT_NOTES" && [ -z "$VAULT" ]; then
  die "suite lists vault notes ($VAULT_NOTES): pass --vault-excerpts"
fi
if ! is_none "$TICKETS" && [ -z "$CLICKUP" ]; then
  die "suite lists ClickUp tickets ($TICKETS): pass --clickup-excerpts"
fi

SUFFIX=; [ "$ATTEMPT" = 1 ] || SUFFIX="-a$ATTEMPT"
if [ "$ROLE" = verify ]; then
  OUT="$RUN_DIR/$SUITE.verify-package$SUFFIX.md"
  REPORT="$RUN_DIR/$SUITE.verify$SUFFIX.md"
else
  OUT="$RUN_DIR/$SUITE.package$SUFFIX.md"
  REPORT="$RUN_DIR/$SUITE$SUFFIX.md"
fi
trap 'rm -f "$OUT.tmp"' EXIT

if [ "$ROLE" = verify ]; then
  ROLE_LINE="verify_worker (independent re-reproduction, single suite, no orchestration)"
  OBJECTIVE="re-reproduce **only** the findings listed under \"Findings to verify\", from a clean app state, on your lane's device. Do not run the suite's other scenarios and do not look for new bugs."
  METHOD="For each finding: reset to a clean state (relaunch the app with clearState, or a new browser context), follow its steps exactly, up to 3 attempts. Verdict: CONFIRMED (reproduced every time; fresh screenshot at the moment it happens), FLAKY (reproduced k of n; say k/n), NOT REPRODUCED (never reproduced in 3 attempts; screenshot of the correct behaviour). If a precondition is missing, BLOCKED with its name."
  OUTPUT="Output: append a section \`## Verification (independent)\` to \`$EVIDENCE/qa-report.md\` with a table \`| Bug ID | Verdict | Attempts | Evidence | Note |\`. Save new screenshots in \`$EVIDENCE\` with the prefix \`v-\`. Do not edit any other part of qa-report.md. Write \`$REPORT\` with: Suite, Role verify, Attempt, Status (PASS = verification done, whatever the verdicts | BLOCKED), the model you ran as, and the verdict table."
else
  ROLE_LINE="test_worker (single suite, no orchestration)"
  OBJECTIVE="execute **only** the suite \"$SUITE\" quoted at the end, every scenario, on your lane's device, within its timebox, and write the reports."
  METHOD="Follow the scenarios in order. Evidence rules are in Global Constraints. Screenshot every anomaly at the moment you see it, before retrying. Diagnose before reporting: inspect the screen (Maestro \`inspect_screen\` / Playwright snapshot) to rule out a wrong selector or a wrong interaction. If the suite's smoke dependency fails or a precondition is missing, the affected scenarios are BLOCKED, never FAIL. If the timebox runs out, stop and report the remaining scenarios as \`not run (timebox)\`."
  OUTPUT="Output, two files: (1) \`$EVIDENCE/qa-report.md\` exactly as \"Report template\" (§ 13) of the Evaluation standard at the end of this package, with the quality score (§ 3), severities (§ 2), the accessibility (§ 6) and console/logs (§ 7) tables, and the strategy-specific sections that apply. (2) \`$REPORT\` with: Suite, Attempt, Status (PASS = suite executed to the end or timebox | FAIL = could not execute it properly | BLOCKED = could not start), the model you ran as (from your status line, else \"not verified\"), the quality score and status, counts of PASS / FAIL / BLOCKED / not run, the list of FAIL scenario IDs with bug IDs and evidence paths, blockers, test data flags, records created in your data range (for cleanup), and the ledger lines you wrote, if any."
fi

case $TOOL in
  *maestro-mcp*) DRIVER_CHECK="your session must list the Maestro MCP tools \`list_devices\`, \`inspect_screen\`, \`take_screenshot\` and \`run\` (load them with ToolSearch if deferred), and \`list_devices\` must show \`$DEVICE\` as connected." ;;
  *playwright-mcp*) DRIVER_CHECK="your session must list the Playwright MCP tools \`browser_navigate\`, \`browser_snapshot\` and \`browser_take_screenshot\` (load them with ToolSearch if deferred)." ;;
  *http*) DRIVER_CHECK="\`curl --version\` must work. This suite has no MCP driver and no device: requests go through Bash \`curl\` following § 12 of the Evaluation standard." ;;
  *maestro-cli*) DRIVER_CHECK="\`maestro --version\` must work and \`maestro --device $DEVICE hierarchy --compact\` must print the current screen. This suite has no MCP driver: read screens with \`maestro --device $DEVICE hierarchy\`, act through flows run with \`maestro --device $DEVICE test\`." ;;
  *) DRIVER_CHECK="the commands your suite's Tool field names (${TOOL:-none}) must work against \`$DEVICE\`." ;;
esac
if [ "$ROLE" = verify ]; then
  SUITE_HEADING="Suite context (verbatim from the plan — for preconditions and test data only; do NOT run its scenarios)"
else
  SUITE_HEADING="Your suite (verbatim from the plan)"
fi

if is_none "$VAULT_NOTES"; then VAULT_LINE="none for this suite."
else VAULT_LINE="$VAULT_NOTES. Excerpts are quoted below by the orchestrator; you have no vault access."; fi
if is_none "$TICKETS"; then TICKET_LINE="none for this suite."
else TICKET_LINE="$TICKETS. Ticket content is quoted below by the orchestrator, fetched fresh; you have no ClickUp access."; fi

{
cat <<EOF
# QA package — $SUITE ($ROLE, attempt $ATTEMPT)

RUN_ID / SUITE / ATTEMPT_ID: $RUN_ID / $SUITE / $SUITE-$ROLE-a$ATTEMPT
Role and requested model: $ROLE_LINE · model \`$MODEL\` ($WHY)
Strategy · tool · timebox: ${STRATEGY:-see suite} · ${TOOL:-see suite} · ${TIMEBOX:-see suite}
Your lane and device: lane \`$LANE\` · device id \`$DEVICE\`. Pass this id to every Maestro MCP tool (\`device_id\`) and every \`maestro --device\`, \`xcrun simctl\` or \`adb -s\` command. No other worker uses this device while you run. Never touch any other device; never boot, shut down, erase or reinstall devices.
Driver check, before anything else: $DRIVER_CHECK If the check fails, stop at once with STATUS: BLOCKED and say what failed. Never work around a missing driver with scripts.
Objective: $OBJECTIVE
Method: $METHOD
Dependencies: ${DEPS:-none} (the orchestrator dispatched you only after they were accepted).
Obsidian notes: $VAULT_LINE
ClickUp tickets: $TICKET_LINE
Working directory: \`$ROOT\` (QA project root). Evidence directory (create it if missing, add files, never overwrite another run's files): \`$EVIDENCE\`.
Allowed writes: the evidence directory, your report file(s) in \`$RUN_DIR\`, \`maestro/flows/$SUITE/\` if your suite writes flows, and \`$RUN_DIR/ledger.md\` (append only) if your suite records cross-system data. Nothing else: no app code, no project config, no \`context/\` files, no CLAUDE.md, no git commits.
Global scratchpad: \`$ROOT/QA-SCRATCHPAD.md\` — read-only for you.
$OUTPUT
End your final chat message with \`STATUS: PASS|FAIL|BLOCKED\` and \`REPORT: $REPORT\`. The report file is authoritative.
Never print credentials. Do not create ClickUp tickets, do not write to Obsidian, do not install tools, do not delegate to other Herdr agents. Internal subagents may analyse, but every device interaction and every screenshot happens in this session.

---

EOF
if [ -n "$NOTES" ]; then
  printf '## Orchestrator notes\n\n'; cat "$NOTES"; printf '\n---\n\n'
fi
if [ -n "$FINDINGS" ]; then
  printf '## Findings to verify\n\n'; cat "$FINDINGS"; printf '\n---\n\n'
fi
if [ -n "$VAULT" ]; then
  printf '## Vault excerpts (quoted by the orchestrator)\n\n'; cat "$VAULT"; printf '\n---\n\n'
fi
if [ -n "$CLICKUP" ]; then
  printf '## ClickUp tickets (quoted by the orchestrator, fetched fresh)\n\n'; cat "$CLICKUP"; printf '\n---\n\n'
fi
required 'Decisions recorded for this plan' 2
required 'Global Constraints' 2
required 'Device matrix' 2
required 'Test data and accounts' 2
required 'Worker environment' 2
printf -- '---\n\n## %s\n\n%s\n' "$SUITE_HEADING" "$SUITE_TEXT"
printf -- '\n---\n\n'
# The evaluation standard is shown one heading level down, so its sections
# never collide with the plan sections above.
sed -e '/^```/,/^```/!s/^## /### /' \
    -e 's/^# Evaluation standard/## Evaluation standard (how results are judged and written)/' "$STANDARD"
} > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"
chmod 600 "$OUT"
printf '%s (%s lines)\n' "$OUT" "$(wc -l < "$OUT" | tr -d ' ')"
