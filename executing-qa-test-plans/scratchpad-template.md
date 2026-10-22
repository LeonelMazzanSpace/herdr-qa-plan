# QA-SCRATCHPAD.md template

`<QA project root>/QA-SCRATCHPAD.md` has one writer: the orchestrator. It is the compact, factual view of the run. Timestamp every update with date, time and time zone. Write the state first, then report to the user.

Update it after each of these: creating or revising the plan, booting a device, dispatching, receiving a report, a verification verdict, a decision, a blocker. Also update it before the session ends or before an expected context compaction.

Suite states: `planned`, `skipped (user)` (platform left out of this run), `dispatched`, `blocked` (say on what), `executed` (run report read), `accepted (pending verification)` (stage A passed; the lane has moved on), `verifying` (its lane's verify batch is live), `accepted`, `accepted (verification waived)`. Bug states: `reported` (by the test worker, pending in `<run-dir>/<lane>.findings.md`), `confirmed`, `confirmed (screenshot)` (Low, by the orchestrator), `flaky k/n`, `not reproduced`, `reported (unverified: <reason>)`, `ticket created <link>`.

The Suites table also records, per suite, the evaluation-standard sections its package carried (the line `make-package.sh` prints), so coverage per platform can be stated at closing.

Track vault sync and ClickUp separately. Never write that a ClickUp ticket exists without reading it back.

```markdown
# QA Scratchpad — <app>
Updated: <YYYY-MM-DD HH:MM TZ> | Run: <run-id> | Status: <planning | executing — wave N | closing | completed>

## Objective and scope
<Goal from the plan; platforms; environment; what "done" means>

## References and environment
<Plan, summary, run dir (~/.cache/qa-runs/<run-id>), evidence root>
<Verified versions: herdr, Claude Code (launch flags, `--chrome`), per lane driver: adb / Maestro CLI + MCP tools listed / AXe / Chrome extension connected / Playwright MCP (approved only), Java, Xcode runtimes, Android emulator. Install decisions and their status>
<Vault: name / none (reason) · ClickUp: source tickets, destination list / none (reason)>

## Lanes
| Lane | Device | Device id | Booted by this run | Build installed | Current suite | Pane / agent |
| --- | --- | --- | --- | --- | --- | --- |

## Scope of this run
<Platforms confirmed by the user (D-number); lanes skipped; user types / roles covered and their account variable names>

## Suites
| ID | Strategy | Lane | Status | Model (effective) | Standard sections (+ fallback) | PASS/FAIL/BLOCKED/not run | Report | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Verification batches
| Lane | Batch | Suites | Findings | Agent | Status | Report |
| --- | --- | --- | --- | --- | --- | --- |

## Bugs
| Bug ID | Suite | Severity | Status | Evidence | Ticket |
| --- | --- | --- | --- | --- | --- |

## Decisions and discrepancies
<D-number, decision, rationale, source, date>

## Blockers and remaining work
<Item, impact, owner, action required>

## Obsidian synchronization
<Notes read; updates queued or done>

## ClickUp
<Tickets fetched (ids, time); destination decision; tickets created and read back; queued if the MCP failed>

## Next steps and recovery
<Immediate sequence; live agents and panes; booted devices; how to resume: read this file + the plan, `herdr agent list`, `xcrun simctl list devices booted`, `adb devices`, reports in the run dir>

## Recent activity
<YYYY-MM-DD HH:MM TZ — suite/event — result — evidence>
```
