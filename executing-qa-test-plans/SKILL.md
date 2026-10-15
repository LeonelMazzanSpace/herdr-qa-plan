---
name: executing-qa-test-plans
description: Executes an approved QA test plan with parallel Claude Code workers in Herdr panes, each driving its own iOS simulator, Android emulator (Maestro CLI + MCP), browser (Playwright MCP) or API; also resumes, reports status of, or closes such a run. Manual only — run /executing-qa-test-plans <plan>.
disable-model-invocation: true
---

# Executing QA Test Plans

## Overview

**Manual only.** This skill has `disable-model-invocation: true`: it runs only when the user types `/executing-qa-test-plans` (optionally with the plan path, or "status" / "continuá" for a run in progress). It never starts on its own.

One orchestrator session runs a plan written with `/writing-qa-test-plans`. It boots one device per lane, gives each suite to a fresh Claude worker in its own Herdr pane, and checks each result itself. Every High or Medium bug is then re-reproduced by an independent verify worker before it counts. Finally it consolidates one report for the run.

**Core principles:**
- A worker's report is a claim, not evidence. A suite is `accepted` only after the orchestrator has read the report, opened the evidence and had the bugs verified.
- A FAIL is a claim until it is re-reproduced. Only `confirmed` bugs leave the run (ClickUp, summary "must fix").
- One device, one live worker. The orchestrator owns the devices; workers only drive them.

**REQUIRED BACKGROUND:** the `herdr` and `herdr-agent-orchestration` skills (CLI, agent states), superpowers:verification-before-completion. **How results are judged** lives in `evaluation-standard.md`, which `make-package.sh` appends to every package. It carries what qa-team-spacedev evaluated: evidence rules, severity, the six-dimension quality score, error guessing, AUTH-01…12, accessibility, console/logs, visual, text, tenants and roles, API rules, and the report template. You hold workers to it when accepting.

`<skill-dir>` is this skill's base directory (shown when the skill loads). Call scripts by absolute path: `bash <skill-dir>/scripts/…`. Commands, Maestro MCP tool names and flags are in `devices-and-tools.md`.

**Herdr agent names:** test worker `s0NN`; verify worker `s0NN-v<N>`; full restart `s0NN-a<N>`.

## Roles

- **Orchestrator (you):**
  - boots, installs and shuts down devices;
  - writes the worker MCP configs, packages and findings files;
  - dispatches, accepts and consolidates;
  - is the only writer of `QA-SCRATCHPAD.md`, the vault and ClickUp.

  You do not test suites yourself: a device you are driving is a device a worker cannot own.
- **Test worker:** runs one suite on one lane, writes `qa-report.md` and a run report, never orchestrates.
- **Verify worker:** re-reproduces the listed findings on the same lane from a clean state, and nothing else.
- Decide routine questions yourself and record them as D-numbers. Ask the user only about scope changes, extra devices, production access, destructive actions, and anything written outside the run (ClickUp tickets, vault, `context/` files).

## Asking the User

The person answering may be a QA analyst or a PM, not the person who wrote the plan. Every message and question you show them is **in English** and has this shape:

1. **Status first, as a short list:** what is ready ✅ and what is missing ❌, one line each, each saying what it means for the run ("❌ Maestro is not installed: it is the tool that drives the app on the simulator, so no mobile test can run without it").
2. **Routine decisions you took yourself** go after the status, under "Already decided (no answer needed)", each in plain words. They are never asked.
3. **One question per decision.** The question says what is being decided and why it comes up now, in one or two plain sentences.
4. **Each option is a complete answer:**
   - the label says the action ("Yes, install it", "One iPhone only");
   - the description says what happens if it is chosen: what you will do next, the cost (time, memory, money) and the risk. It also says what is left out, when something is.
5. **Technical words get their meaning inline,** in parentheses, the first time:
   - lane → one test device;
   - permission mode → how freely workers may run commands without asking you;
   - acceptance source → where the acceptance criteria come from;
   - dispatch → launch the workers.
6. **Decision IDs go last,** in parentheses, after the plain text ("Test on one iPhone only (D9)"). An option label is never only an ID.
7. **Multi-select only for independent yes/no items,** and each item is a full sentence that makes sense on its own.

Example: the same preflight, asked this way.

> **Status before starting**
> - ✅ iPhone 16 Pro simulator is booted and ready
> - ❌ Maestro is not installed: it is the tool that drives the app on the simulator, so no mobile test can run without it
> - ❌ No app builds (the .app for the iOS simulator, the .apk for Android): there is nothing to install on the devices
> - ❌ No Android emulator is running (I can boot Pixel_8_API_34 myself)
>
> **Already decided (no answer needed):** regression flows not run in over 30 days are listed in the summary as an observation, not as a bug (D10).
>
> **Install Maestro?**
> - *Yes, install it with brew (Recommended)* — Takes about 2 minutes and stays installed on your Mac for every project. Needs Java 17+.
> - *No, web only for now* — iOS and Android tests do not run in this run.
>
> **Who builds the app?**
> - *You build it now (Recommended)* — I compile the simulator .app and the .apk from the Expo project. Takes 10–20 minutes and changes no app code.
> - *I'll provide the files* — I wait for the paths to both files before launching the workers.
>
> **How freely may workers run commands?** Each worker launches the app, taps the screen and takes screenshots through simulator commands.
> - *Let them run on their own (Recommended)* — No approval needed for each command; a safety check blocks risky ones. You can watch any pane. (`auto` mode, D5)
> - *Ask me at every step* — More control, but you approve every command in every pane, and the run is much slower and stops while you are away. (`acceptEdits` mode)
>
> **Where do the acceptance criteria come from?** (the rules that say what the app must do for a test to pass) ClickUp is off, so the plan proposes the vault notes "requisitos/reservas".
> - *From the vault notes (Recommended)* — I re-read them at start and give each suite the lines it needs. If the vault is unreachable, those suites wait and the rest run. (D8)
> - *Only what the plan says* — Faster, but business rules that exist only in the vault are not checked.
>
> **How many phones do I test on?**
> - *One iPhone only (Recommended)* — iOS suites run one after another. Uses less memory, takes longer overall. (D9)
> - *Add a second iPhone* — Faster, but adds 1–2 GB of RAM and a few minutes of boot time.

## Preflight (once per run)

1. `test "$HERDR_ENV" = 1`. If it fails, ask the user to start the orchestrator inside a Herdr pane.
2. Read `QA-SCRATCHPAD.md` (create it from `scratchpad-template.md` if missing), the plan and its summary. Every `to confirm` decision that a lane needs must be answered before that lane is dispatched: permission mode, extra devices, Maestro install, production access. Ask them all in one message, shaped as in "Asking the User".
3. **Tooling.** Check each and record the result in the scratchpad:
   - `herdr --version`; `claude --help` for `--model`, `--permission-mode`, `--strict-mcp-config`, `--mcp-config`, `--add-dir`, `-n`; `jq --version`;
   - mobile lanes only: `maestro --version`, `java -version` (17+); `xcrun simctl help` if iOS is in scope; `emulator -list-avds` and `adb version` if Android is;
   - web lanes only: `npx -y @playwright/mcp@latest --help` for `--isolated`, `--viewport-size` and `--output-dir`;
   - API lanes only: `curl --version`.

   Check only the tooling for the platforms the plan covers. A web-only run never asks for Maestro; a mobile-only run never starts Playwright.

   If Maestro is missing, the mobile lanes are BLOCKED: give the install command and wait for the user's yes before installing anything. Web lanes continue meanwhile.
4. **Run dir:** `mkdir -p -m 700 ~/.cache/qa-runs/<run-id>`. Packages, run reports, findings files, MCP configs, excerpts and `ledger.md` live there. Evidence goes to the project's `evidence/`.
5. **Optional sources, fresh:**
   - **Vault:** only for suites whose header names notes. Confirm the vault MCP is connected, reread the notes and quote the needed lines into `<run-dir>/<suite>.vault.md`.
   - **ClickUp mode, decided once, here.** ClickUp is `on` only if the plan names ClickUp tickets or a destination list, or the user gives one in this run.
     - The plan says `ClickUp: none (user)`: the answer is already given, so `off` without asking.
     - The plan names nothing and the user did not mention ClickUp: ask once, in the preflight questions: "¿Usamos ClickUp en esta corrida? Pasame la lista o los tickets."
     - No list or tickets given: `off`. Record it as a D-number and write `ClickUp: off (user)` in the scratchpad.

     With `off`, no ClickUp tool is called for the rest of the run, even if the MCP is connected: no ticket reads, no record searches, no ticket creation, no further questions. **The deliverable is the HTML results page** (Closing step 4).
   - **ClickUp tickets as source** (mode `on`): only for suites whose header names tickets. Resolve the connector (`ToolSearch` for `clickup`), fetch each ticket now with `clickup_get_task`, and quote title, description and acceptance criteria into `<run-dir>/<suite>.clickup.md`.
   - If an MCP is down: tell the user, keep only the suites that need it waiting, and run the rest. Never read the vault from disk, never invent ticket content, never reuse ticket text from an old run.
6. **Devices, lane by lane:** `bash <skill-dir>/scripts/boot-device.sh …` with the plan's Device matrix values. Record the printed id, the `booted-by-this-run` line, and the installed build.
   - Create extra simulators or AVDs only when the plan's decision for them is `approved`.
   - **Health check per lane.** Write `<run-dir>/health-<lane>.yaml` yourself: the lane's `appId` (bundle id / package from the plan header), `---`, `- launchApp`, and `- assertVisible: "<a text on the first screen>"` taken from the plan or `context/navigation-map.md`; if neither has one, use `- takeScreenshot: <run-dir>/health-<lane>` and look at it. Run `maestro --device <id> test <run-dir>/health-<lane>.yaml`. Without Maestro: `xcrun simctl launch <udid> <bundle id>` / `adb -s <serial> shell monkey -p <package> 1`, then a screenshot you open. For web, the base URL answers.
   - A lane that fails its health check is `blocked`. Fix what you own (reboot, reinstall), otherwise tell the user.
7. **Worker MCP configs:** `<run-dir>/mcp-<lane>.json` per lane, from `devices-and-tools.md` § Worker MCP config. Workers start with `--strict-mcp-config`, so they get only their own driver and cannot reach ClickUp or the vault. A lane running a `maestro-cli` suite, and every API lane, gets `{"mcpServers": {}}`: they work through the CLI or `curl` and hold no MCP driver port.
8. **Maestro MCP port limit:** at most one live `maestro-mcp` worker per platform. If the plan has two MCP lanes on the same platform in a wave, run them one after the other. Exception: you test two sessions for real on two devices and both work; record that as a D-number.
9. **Permission mode.** Workers need a mode that runs Maestro, simctl and adb without asking each time. `--permission-mode auto` may be refused: either the `herdr agent start` call is denied, or the worker's pane shows the refusal (`herdr agent read <name> --source visible` right after start). If so, ask the user once which write-capable mode they approve, and record the answer. Never switch to bypass flags, and never answer a worker's permission prompt yourself.
10. **Keep the Mac awake.** Ask; with an OK, run `caffeinate -i` in a pane you create.

## Lane Loop

Dispatch while there are fewer than **6 live worker panes** (test and verify workers both count, `caffeinate` does not), or fewer than the plan's lower cap.
- Each lane runs its suites in plan order. A suite starts when the previous suite on its lane is `accepted` and its `Depends on` suites are accepted. Lanes advance independently; "waves" in the plan are only the intended order.
- **Suites that run alone:** `performance-stability`, and `network-conditions` suites that take the Mac offline, start only when no other test worker is live. Hold the other lanes' next suites until they finish.
- At any moment, at most one live `maestro-mcp` worker per platform (preflight step 8).
- When a pane frees up, use it in this order: pending verify workers first, then suites in plan order.

1. **Package:** `bash <skill-dir>/scripts/make-package.sh --plan … --suite S-0NN --model … --why … --run-id … --run-dir … --device <lane device id> --evidence evidence/<app-slug>/S-0NN-<slug>/<run-id>[-a<N>] --root <QA project root> [--vault-excerpts …] [--clickup-excerpts …] [--notes …]`. Patterns learned from earlier suites go in `--notes` (see Learning Across Suites).
2. **Pane:** check the width with `herdr pane layout --pane "$HERDR_PANE_ID"`.
   - At least 180 columns: two worker columns of up to 3 panes each, to the right of yours.
   - Narrower: one column, cap 4, recorded.
   - Reuse a pane freed by `/exit` before splitting a new one.
3. **Launch:**
   ```bash
   herdr agent start s0NN --kind claude --pane <pane> --timeout 120000 -- --model <plan model> --permission-mode <approved mode> --strict-mcp-config --mcp-config <run-dir>/mcp-<lane>.json --add-dir <run-dir> -n "S-0NN <strategy> <lane>"
   ```
4. **Verify the effective model** on the status line (`herdr agent read s0NN --source visible`) and record it.
5. **Prompt once,** as a Bash call with `run_in_background: true`, so you stay free; you are notified when it returns:
   ```bash
   herdr agent prompt s0NN "Read <run-dir>/S-0NN.package.md and execute it exactly. Write your run report to <run-dir>/S-0NN.md and end with STATUS and REPORT lines." --wait --timeout 3600000
   ```
   A verify worker gets: `"Read <run-dir>/S-0NN.verify-package.md and execute it exactly. Write your report to <run-dir>/S-0NN.verify.md and end with STATUS and REPORT lines."`
6. **Scratchpad:** lane, pane, model, `dispatched`.

While workers run, prepare the next packages, accept finished suites, and reconcile `herdr agent list` with the scratchpad. When idle, wait in bounded stretches; do not poll every few seconds.

## Accepting a Suite

Accept a suite only when every check below passes, in order:

1. The worker is `idle` or `done`, and the **run report file** says `STATUS: PASS`. Chat text does not count. Run-report status is about the *execution*, not the app: PASS = the suite was run to the end (or to its timebox), whatever bugs it found; FAIL = the worker could not run it properly; BLOCKED = it could not start. FAIL and BLOCKED go to "When a Worker Stops or Breaks".
2. `qa-report.md` exists in the suite's evidence dir and follows the evaluation standard's report template (§ 13):
   - a `# QA Report — ` title and a `**Quality Score:** NN/100` line;
   - `## Quality Score Breakdown` with the six dimensions. The total matches Σ score × weight, and the Executive Summary status matches the thresholds (≥ 85 PASS, 60–84 CONDITIONAL PASS, < 60 FAIL);
   - a `## Bug Register` with the 4 columns, each severity consistent with the standard's criteria (§ 2);
   - `## Scenario Results` covering every scenario ID of the suite (plus AUTH-01…12 for auth flows), each with PASS / FAIL / BLOCKED / `not run (timebox)` / N/A;
   - `## Accessibility Audit` and `## Console & Logs Health` filled in, or `N/A` with the reason;
   - `### Must Fix`, `### Should Fix` and `### Nice to Have` with at least one bullet each;
   - the strategy-specific sections: `## Scope` and `## Navigation drift` for discovery, `## API coverage` for API.

   A missing scenario is a gap: send the worker a follow-up (step "idle but no report" below).
3. **Open the evidence** of every FAIL (Read the image) and of the happy path. A FAIL whose screenshot does not show the claimed problem goes back to the worker, or straight to verification with that note.
4. Check scope: the worker wrote only to its evidence dir, its run report, `maestro/flows/<suite>/` and the ledger, and touched no other lane's device.
5. **Verification:**
   - Exit the test worker (`/exit`, then confirm the shell prompt with `herdr pane read <pane> --source visible`).
   - Write `<run-dir>/S-0NN.findings.md` listing every High and Medium bug: ID, steps, expected result, actual result, evidence path.
   - Build the verify package with `make-package.sh --role verify --findings …` and launch `s0NN-v1` on the **same lane**, using a model ≥ the suite's (`opus` for security findings).
   - You check Low bugs yourself from their screenshots. If the screenshot plainly shows the issue (a typo, a misaligned label), mark it `confirmed (screenshot)`. Otherwise add it to the verify worker's findings. Every severity can reach ClickUp once confirmed, as in the old `report-bugs-to-clickup` rule.
6. **Apply the verdicts** in `qa-report.md` and in the scratchpad:
   - `CONFIRMED` → `confirmed`;
   - `FLAKY k/n` → stays in the Bug Register, with "(intermittent k/n)" added to the description;
   - `NOT REPRODUCED` → move the row out of the Bug Register into `## Corrected false positives`, with the verify evidence. Never delete it.

   If a verdict moves bugs, recompute the quality score and the status.
6b. **Known or new: decided by the record.** For each confirmed bug, search the record:
   - ClickUp bug tickets, open or closed, only with ClickUp mode `on`;
   - earlier `qa-report.md` files under `evidence/`.

   Then classify it:
   - an **open** entry → `known <link>`. Cite it, do not file it again;
   - **closed as designed / as intended** → expected behaviour. Move it to Corrected false positives, citing the entry;
   - **closed for any other reason** → `possible regression`. Report it with the old entry;
   - **no entry** → `new`.

   No hazard list overrides a recorded entry.
6c. **API caller-dependent failures are held.** A 401 or 403, or a 404 across an organisation boundary, that depends on which key was used is not filed until the user confirms who owns the key. Ask once, naming the variable.
   Write the classification into the suite's `qa-report.md` under `## Record check` (`| Bug ID | Record | Link |`), so the HTML page shows it.
6d. **Discovery drift** (a section missing, added or moved compared with `context/navigation-map.md`) is reported, never fixed in the map. At closing, suggest the user run `/qa-project-setup`.
6e. **After a discovery suite is accepted,** show the user the sections, organisations and roles it found, and which ones the plan does not cover yet. With their OK, append one suite per uncovered section to the plan, on the same lane, with the next free IDs. Record it as a D-number. Packages always come from the plan. This is the old "Full Site Audit": discover, then test each path.
7. Write `accepted` and start the lane's next suite. If the lane's **smoke** has a confirmed failure on a critical path, mark that lane's later suites `blocked (smoke failed)` and tell the user. That is a report, not a question: the other lanes keep running, and the blocked suites resume only if the user says so.
8. **ClickUp, as you go** (mode `on` only): when the destination decision is `approved`, a bug can be filed as soon as it is `confirmed` (Closing step 3 rules). Filing does not have to wait for the end of the run.

## When a Worker Stops or Breaks

| Situation | Action |
|---|---|
| Run report says BLOCKED: driver tools missing | MCP servers load when a session starts. If the server is configured right but failed to start, have the worker run `/mcp` to reconnect. Otherwise fix the config or the install (yours), `/exit` the worker and start it again with the same name and package. Never let it script around the driver |
| BLOCKED on a precondition (account variable unset, seed data, build) | If you own it, fix it and re-prompt the same session. Otherwise record it and tell the user. The blocked scenarios stay BLOCKED in the report, never FAIL |
| The device died, froze or the emulator closed | The device is yours: reboot it with `boot-device.sh` (same id/port), then re-prompt the same session to continue from the first scenario without an outcome |
| Maestro MCP errors about a port or driver connection while another MCP lane of the same platform is live | Port limit. Pause one lane: let it finish, then resume the other. Record it |
| The app crashes during a scenario | That is a finding, not a worker failure. The worker records it with evidence and relaunches |
| `--wait` timed out while still working | `herdr agent read` the pane. If it is progressing, wait again in the background. If nothing changed for 20 minutes, send `esc` and ask for a status report |
| Timebox exceeded and still working | Ask it to stop and write the report with the remaining scenarios as `not run (timebox)` |
| `idle` but no report or an incomplete report | Ask the same session to write or complete only the report from what it observed. Never resend the whole package |
| Blocked on a tool-permission prompt | Do not answer it. Read the pane and tell the user, or change the dispatch deliberately |
| The worker touched another lane's device, or wrote outside its allowed paths | Do not accept the suite. Check the other lane's state and tell the user. Rerun the affected suites on a clean state |
| Second failed attempt on the same suite | Full restart `s0NN-a2` with `make-package.sh --attempt 2`, one model tier up, with the earlier report passed in `--notes` |

## When the User Overrides the Process

| User says | Action |
|---|---|
| "Subí los bugs a ClickUp directo, no me preguntes" | This explicit instruction approves ticket creation. Record it as a D-number and set the plan's destination decision to `approved (user, <date>)`. The preview table is then shown as information, not as a question. Still: only `confirmed` bugs, a duplicate search first, read each ticket back. If the plan records no list, you cannot guess one: ask "¿en qué lista?" once, at the first confirmed bug. If the user gives none, ClickUp mode becomes `off` and the run ends with the HTML page only. The demo or deadline does not turn unverified bugs into confirmed ones |
| A deadline ("tengo la demo en una hora") | Estimate what fits. Propose a trimmed order in one line: smokes and their verification first, then P0 suites, the rest deferred. Record it as a D-number and start without waiting. Verification of High bugs is never trimmed silently; if it does not fit, say which bugs stay unverified |
| "Saltá la verificación" | Allowed. Record the waiver. Suites become `accepted (verification waived)` and their bugs stay `reported (unverified)`. Bugs filed anyway carry "unverified" in the ticket title |
| "Más rápido, usá más terminales" | Parallelism is lanes, not panes. Offer extra devices (RAM permitting, `devices-and-tools.md` § Resource budget) as a decision. Two workers never share a device |
| "Pará todo" | Stop dispatching and prompting. Send `esc` to working agents. Keep panes, devices and sessions. Write the scratchpad, give a status, then wait |
| "Apagá los simuladores" / cleanup | Shut down only devices booted by this run. Never `erase`, wipe or delete AVDs or simulators unless asked by name |

## Learning Across Suites

When a verified bug reveals a pattern (an unlabeled icon button, keyboard covering the submit button, a stale list after background/foreground), add it to the `--notes` of every later package on every platform. Also add parity checks to the closing comparison.

## Closing the Run

1. **Cross-platform parity:** compare the same flows across the iOS, Android and web reports, covering outcomes, copy and behaviour. Differences become findings in the summary.
2. **Consolidated report:** `evidence/<app-slug>/QA-RUN-SUMMARY-<run-id>.md` in the project language, containing:
   - `**Overall Score:** NN/100`: the mean of the suite scores, with its status;
   - a per-suite table: lane, strategy, score, status, PASS/FAIL/BLOCKED/not run, confirmed bugs;
   - `## Cross-Cutting Issues`: problems that show up in more than one suite or platform;
   - `## Priority Fix List`: confirmed bugs ranked by severity across all suites, each marked new, known or possible regression, with evidence;
   - flaky and corrected findings;
   - test data flags, and regression flows whose last successful run is older than 30 days (including the ones this run did not cover);
   - the strategies deferred in the plan, and the coverage gaps;
   - a plain-language go / no-go note under the exact heading `## Go / no-go` (the HTML page reads it).
3. **ClickUp:** only with ClickUp mode `on`, the destination decision `approved`, and the MCP connected. With mode `off`, skip this step entirely.
   - When the user wants to choose list, sprint and assignee themselves, use `/report-bugs-to-clickup <qa-report.md>` per suite, if the qa-team-spacedev skill is available. It asks for those every run.
   - Otherwise create the tickets yourself with the team template, one `clickup_create_task` per bug:
     - **Title:** `[<Bug ID>] <brief description>`.
     - **Description:** `Precondition:` · `Steps to reproduce:` (Step 01, 02, …) · `Actual result:` · `Expected result:` · `Additional information:`, with the evidence as `![<file>](<file>)` and `Original ID | Severity | Reporter | Date | Related tickets`. Add device, OS and run id to Precondition.
     - **Tags:** the environment (dev / staging / production, from the report's `**URL:**`) plus the platform (`mobile-ios` / `mobile-android` / `web` / `api`).
     - **Attachments:** the evidence screenshot.

     Ask once per run for the bugs list, the sprint list and the assignee. If the user said not to be asked: no assignee, no sprint, and say so in the final summary. Show the preview table before creating; when the user said not to be asked, it is information, not a question. If a create call fails, record it and continue with the next one.
   - Only `confirmed` bugs classified `new` or `possible regression` (step 6b). Read each ticket back and record its link.
   - **Improvements** (the `### Nice to Have` items) go to ClickUp only under their own `approved` decision.
     - Use `/report-improvements-to-clickup <qa-report.md>`, or one task per bullet: title `[Improvement] <platform> | <environment> | <suite> | <bullet text verbatim>`, priority Low, the improvements list, and the current sprint if the user named one, with the suite's main screenshot attached.
     - Without that decision, they stay in the reports and the HTML page.
4. **HTML results page — required whenever no tickets were created.** That covers four cases:
   - ClickUp mode `off`: the user gave no ClickUp. This is the **only** deliverable: the page, and nothing about ClickUp after it;
   - a plan with `ClickUp: none`;
   - a ClickUp MCP that is not connected at closing;
   - a destination decision that was never approved.

   The page is how the results reach people:
   ```bash
   /usr/bin/python3 <skill-dir>/scripts/render-results.py --evidence-root evidence/<app-slug> --run-id <run-id> \
     --out evidence/<app-slug>/QA-RUN-RESULTS-<run-id>.html --title "<App> — QA <date>" \
     --lang <es|en|bi> --summary evidence/<app-slug>/QA-RUN-SUMMARY-<run-id>.md --clickup-note "<only when ClickUp was on but no tickets were created: MCP not connected | not approved>"
   ```
   - The page is built only from the run's `qa-report.md` files. If a fact is missing there, fix the markdown and render again; never hand-edit the HTML.
   - It covers the score card, the go / no-go note, results per suite, bug cards with their verification verdict and screenshots, corrected false positives, coverage gaps, and every scenario.
   - It is self-contained: inline CSS, no scripts, no network. Screenshots are linked relative to `evidence/<app-slug>/`, so share the whole folder, zipped, not the `.html` alone.
   - Open it (`open <file>`) to check that it renders and that no evidence link says "(missing)". Give the user its absolute path.
   - Use `/usr/bin/python3` (macOS system Python), not `python3`: version managers such as asdf can shadow it without a version set.
   - With ClickUp connected and tickets created, the page is optional: offer it in one line.
5. **Regression flows,** each written only with the user's yes:
   - Offer to update `context/regression-flows.md` "Last successful run" for the flows that passed end-to-end. Never change it for a failed flow, and never change a regression run's steps or test data.
   - For each `acceptance` suite, ask: add it as a new flow, update an existing flow, or skip.
     - **Add:** ask for a short flow name. Append `## Flow: <name>` with `**Steps:**` taken from what was actually exercised, `**Test data:**`, and `**Last successful run:**` (today on PASS, otherwise `never run`).
     - **Update:** ask which `## Flow:` entry. Edit only what the user says changed (a step, a test-data value, a URL), never rewrite the entry. Set `**Last successful run:**` to today on PASS. On FAIL, leave the existing date untouched: never overwrite a real date with `never run`.
6. **Vault** (if any): offer the sync (`updating-typed-knowledge-vaults` for typed vaults). Write only with the user's yes.
7. **Data and devices:** list the records each lane created in its data range. Ask before deleting any. Ask before shutting down the devices this run booted.
8. Close only the panes this run created. Update the scratchpad and the daily log (`.claude/daily-update.md`, one line per milestone, if the user's or project's instructions use one). Then give the user, in plain words: the result, the checks run, bugs by severity, coverage gaps, and the live resources still running.

## Status and Resume

For "status", "qué falta" or "continuá":
1. Start from the scratchpad.
2. Verify it against `herdr agent list`, `xcrun simctl list devices booted`, `adb devices` and the run dir. A recorded status does not prove a process is alive.
3. Answer with progress per lane, bugs so far, blockers and the next action.

## Quick Reference

| Need | Command |
|---|---|
| Boot a lane | `bash <skill-dir>/scripts/boot-device.sh --platform ios --udid U [--app A]` · `--platform android --avd N --port 5556 [--app A]` |
| Test package | `bash <skill-dir>/scripts/make-package.sh --plan P --suite S-0NN --model M --why W --run-id R --run-dir D --device ID --evidence E --root ROOT [--vault-excerpts F] [--clickup-excerpts F] [--notes F] [--attempt N]` |
| Verify package | same, plus `--role verify --findings <run-dir>/S-0NN.findings.md` |
| HTML results (required without ClickUp) | `/usr/bin/python3 <skill-dir>/scripts/render-results.py --evidence-root evidence/<app> --run-id R --out evidence/<app>/QA-RUN-RESULTS-R.html --title T [--lang es|en|bi] [--summary S] [--clickup-note N]` |
| Live agents | `herdr agent list` · `herdr agent read <name> --source recent-unwrapped --lines 120` |
| Devices | `xcrun simctl list devices booted` · `adb devices` |

## Red Flags

These thoughts mean stop:

| Thought | Reality |
|---|---|
| "Two workers can share the simulator, they test different screens" | They relaunch the app, steal focus and corrupt each other's evidence. One device, one worker |
| "The worker says FAIL, file it" | Open the screenshot, then verify it independently. Only confirmed bugs leave the run |
| "The user said no questions, so file every bug now" | The instruction approves filing, not unverified bugs |
| "Maestro is missing, I'll install it quickly" | Ask first. Web lanes can run meanwhile |
| "MCP tool not listed, have the worker write a script" | BLOCKED. Fix the driver config |
| "I'll drive this lane myself, it's faster" | Then no worker owns that lane. You orchestrate |
| "Bare `adb install` is fine" | With two emulators it fails or hits the wrong one. Always `-s <serial>` |
| "Vault MCP is down, read the markdown files directly" | Never. The suite waits or runs with `Vault: none` |
| "The ticket text from yesterday is in the old package" | Fetch fresh, every run |
| "Delete the false positive, it's noise" | Move it to Corrected false positives with evidence |
| "No ClickUp, so the chat summary is enough" | Without ClickUp, the HTML results page is required |
| "The user gave no ClickUp, but the MCP is connected: I'll just search for duplicates" | Mode `off` means no ClickUp tool calls at all. Use only earlier reports under `evidence/` |
| "I'll ask again at the end whether to upload the bugs" | They already said none. Deliver the HTML; do not bring ClickUp up again |
| "I'll tweak the HTML by hand" | Fix the markdown and render again |
| "Shut down all simulators to clean up" | Only the ones this run booted, after asking |
