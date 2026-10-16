# Orchestration section template

Copy these two sections into the plan as separate `##` sections. Workers receive "Worker environment" in their packages; they never see "Orchestration". Replace every `<…>`. Keep `resolved at execution` only for values that cannot be known yet: device ids of devices still to be created, pane ids, the run id's date. The permission mode stays `<mode approved by the user>`, a `to confirm` decision. Remove lines that do not apply. Commands and tool names come from `devices-and-tools.md` in executing-qa-test-plans; re-check them against the installed `--help` before writing the plan.

````markdown
## Orchestration (orchestrator-only section)

Workers ignore this section.

**Roles.** The orchestrator (this Claude session, pane `<$HERDR_PANE_ID, re-read at execution>`) owns:
- booting, installing and shutting down devices;
- the worker MCP configs and packages;
- dispatch of test and verify workers;
- acceptance and the consolidated report;
- `QA-SCRATCHPAD.md`, the vault and ClickUp.

Each worker owns exactly one suite on one lane.

**Lanes and waves** (at most 6 live worker panes, verify workers included; at most one `maestro-mcp` lane per platform and one `chrome` lane at a time; <lower cap and reason, if any>):

| Wave | L1-ios | L2-android | L3-web | Depends on |
|---|---|---|---|---|
| 0 | preflight: boot, install, health check (orchestrator) | ← | ← | – |
| 1 | S-001 smoke | S-004 smoke | S-007 smoke | wave 0 |
| 2 | S-002 acceptance | S-005 regression (`adb`, or `maestro-cli` on existing flows) | S-008 regression | own lane's smoke accepted |
| 3 | S-003 a11y | S-006 performance (alone, last) | S-009 cross-system (ledger) | … |
| close | verify workers for remaining FAILs · cross-platform parity (orchestrator) · consolidated report | | | all suites accepted |

A lane moves to its next suite as soon as the previous one on that lane is accepted. It does not wait for the other lanes.

**Model policy** (verify the effective model on the worker's status line):

| Suite | Model | Rationale |
|---|---|---|
| S-001 | sonnet | smoke against a fixed list of critical paths |
| S-003 | opus | accessibility: judging labels, contrast, target sizes |
| … | … | … |
| Verify workers | ≥ the suite's model; opus for security findings | independent re-reproduction |

**Device preflight** (orchestrator, wave 0; `bash <executing-qa-test-plans dir>/scripts/boot-device.sh` does boot + wait + install):

```bash
bash <skill-dir>/scripts/boot-device.sh --platform ios --udid <udid> --app <path/App.app>
bash <skill-dir>/scripts/boot-device.sh --platform android --avd Pixel_8_API_34 --port 5554 --app <path/app.apk>
```

Animations off on every Android lane (`devices-and-tools.md` § Android emulators). Health check per lane with its own driver (executing-qa-test-plans § Preflight 6): `adb` launch + `uiautomator dump` + grep of the "First screen text"; Maestro lanes a `health-<lane>.yaml` run once; `axe` launch + `describe-ui` + grep; web: the base URL answers.

**Worker launch** (verified flags: Claude Code <version>, herdr <version>):

```bash
run_id=<app>-qa-<yyyymmdd>-<hhmm>               # resolved at execution; unique even for two runs the same day
run_dir="$HOME/.cache/qa-runs/$run_id"; mkdir -p -m 700 "$run_dir"
# per lane: MCP config with only that lane's driver (devices-and-tools.md § Worker MCP config)
#   maestro-mcp lane: $run_dir/mcp-L1-ios.json with the maestro server
#   adb, axe, chrome, maestro-cli and http lanes: {"mcpServers": {}}
#   chrome lane: add --chrome to the claude flags below (no server; the tools are built in)
#   playwright-mcp lane (approved install only): $run_dir/mcp-L3-web.json with the playwright server
split=$(herdr pane split --pane <worker-column-pane> --direction down --cwd <QA project root> --no-focus)
pane=$(printf '%s' "$split" | jq -r '.result.pane.pane_id')
herdr agent start s001 --kind claude --pane "$pane" --timeout 120000 -- \
  --model sonnet --permission-mode <mode approved by the user> \
  --strict-mcp-config --mcp-config "$run_dir/mcp-L1-ios.json" \
  --add-dir "$run_dir" -n "S-001 smoke L1-ios"
herdr agent prompt s001 "Read $run_dir/S-001.package.md and execute it exactly. Write your run report to $run_dir/S-001.md and end with STATUS and REPORT lines." --wait --timeout 3600000
```

**Verify worker.** Agent `s0NN-v<N>`, on the same lane after the test worker has exited, with the same MCP config and flags (`--chrome` on a Chrome lane), `-n "S-0NN verify"`, prompt "Read $run_dir/S-0NN.verify-package.md and execute it exactly. Write your report to $run_dir/S-0NN.verify.md and end with STATUS and REPORT lines."

**Suites that run alone:** <performance-stability and Mac-offline network suites, by id>. They start only when no other test worker is live.

**Acceptance per suite.** All of these must hold:
- the worker is idle or done and its run report says `STATUS: PASS`. That status is about the execution: the suite ran to the end or to its timebox. Bugs found do not make it FAIL;
- every scenario of the suite has PASS / FAIL / BLOCKED in `qa-report.md`;
- every FAIL has an evidence file that exists and that the orchestrator opened;
- every High or Medium FAIL was re-reproduced by a verify worker (CONFIRMED / NOT REPRODUCED / FLAKY);
- the happy path has a success screenshot.

**ClickUp** (or `**ClickUp:** none` plus the reason):
- Source tickets: <ids>. The orchestrator fetches them fresh at execution and quotes them into `<suite>.clickup.md` for the packages.
- Bug destination: list `<id>` (`<name>`), decision D<n> `<to confirm | approved>`. Only CONFIRMED bugs, after a duplicate search, filed as soon as they are confirmed. Through `/report-bugs-to-clickup <qa-report.md>` when qa-team-spacedev's skill is available; otherwise the orchestrator creates them with the same template after showing the preview table.

**Closing steps:** cross-platform parity comparison · consolidated report `evidence/<app-slug>/QA-RUN-SUMMARY-<run-id>.md` · HTML results page `evidence/<app-slug>/QA-RUN-RESULTS-<run-id>.html` (`scripts/render-results.py`; required when ClickUp is not connected) · `context/regression-flows.md` "last successful run" updates, only with the user's OK · ClickUp (if approved) · vault sync (if any) · shut down only the devices this run booted, after asking.

## Worker environment

<Copy from plan-template.md § Worker environment and fill in the paths.>
````
