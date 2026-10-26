# Hand-off template

Two blocks. The outgoing orchestrator writes the first one into `QA-SCRATCHPAD.md` under "Next steps and recovery" after the relief is started (so its pane id and effective model are known), then saves the second one as `<run-dir>/handoff-orch-<N>.md` and prompts the relief with "Read <run-dir>/handoff-orch-<N>.md and execute it exactly." Replace every `<…>` except `<the current time>` in block 2, which the relief fills; `a | b` means pick one; the table rows are examples. `<N>` is the relief's number (the first relief is `orch-2`). Write absolute paths everywhere (expand `~`): the relief reads them with its file tools. Fill the agents table from a fresh `herdr agent list`, the device ids from `adb devices` / `xcrun simctl list devices booted`, and the layout from `herdr pane layout --pane "$HERDR_PANE_ID"`.

## 1. Scratchpad entry

```markdown
### Hand-off to orch-<N> — <YYYY-MM-DD HH:MM TZ>
Outgoing: orch-<N-1> (pane <your $HERDR_PANE_ID>), context <NN>% · Relief: orch-<N> (pane <relief pane id>, effective model <as read from its status line | not verified>)
Launch: model <alias> (D<n>), worker permission mode <mode> (D<n>), scope <platforms> (D<n>), ClickUp <on | off> (D<n>), cap <N> panes (D<n>)
Paths: QA project root <path>, plan <plan path>, run dir <run-dir>, evidence root <path>, skill dir <skill-dir>
Safe point: <what just finished, e.g. "S-004 accepted (pending verification), its findings appended to L2-android.findings.md"; nothing is half done>
Layout: column A <pane ids>, column B <pane ids | none>; caffeinate pane <id | none>

Live agents (the relief re-arms one background `herdr agent wait NAME --timeout <ms until its timebox ends>` per `working` row):
| Agent | Pane | State | Lane · device id | Dispatched → timebox ends | Will write |
| --- | --- | --- | --- | --- | --- |
| s005 | <pane> | working | L1 ios · <udid> | 14:02 → 15:14 | <run-dir>/S-005.md |
| vl2-1 | <pane> | working | L2 android · emulator-5556 | 14:20 → 14:50 | <run-dir>/L2-android-v1.verify.md |

Idle lanes: <lane → its next suite and why it is not dispatched (the 70% reading, a driver limit, "suites that run alone") | none>
Verify queue: <lane: N pending High/Medium findings in <run-dir>/<lane>.findings.md, next batch due when … | none>
Open worker questions: <none | <run-dir>/s003.question.md, asked 14:20, answer is the user's (a login code: over 8 minutes old means ask for a fresh one)>
ClickUp (mode on only): <confirmed bugs not yet filed: BUG-01 … | none>; created tickets are already in the scratchpad's ClickUp section
Next action: <the exact next step, e.g. "when S-005.md appears, run Accepting a Suite (stage A); S-006 is packaged at <run-dir>/S-006.package.md, not dispatched only because of the 70% reading: dispatch it on lane L1">
Open questions for the user: <none | the question, in the "Asking the User" shape, for the relief to ask>
```

Everything the relief needs must be in this entry, the plan, the D-numbers and the run dir. Nothing in your chat survives.

## 2. Relief prompt (`<run-dir>/handoff-orch-<N>.md`)

```markdown
You are orch-<N>, the relief orchestrator of QA run <run-id>, in pane <relief pane id>. The previous orchestrator, orch-<N-1> (pane <pane id>), is handing you the run because its context reached 70%. It is waiting for your confirmation and does nothing else; you close its pane once it is idle.

Do, in this order:
1. Read <skill-dir>/SKILL.md in full and follow "As the relief" in its Handing Off section, starting with its preflight. Read the other files of that directory only when SKILL.md points you to them.
2. Read <QA project root>/QA-SCRATCHPAD.md in full; your starting point is the last "Hand-off to orch-<N>" entry. Then read the plan <plan path> and its summary. Do not ask the preflight questions again, boot or reinstall devices, or repeat the cost estimate: scope, accounts, installs, permission mode and ClickUp mode are D-numbers in the scratchpad.
3. Append a `Resumed by orch-<N> at <the current time>` line to the scratchpad's "Recent activity". From that line, you are the only writer.
4. Reconcile with `herdr agent list`, `adb devices`, `xcrun simctl list devices booted` and `ls <run-dir>/*.question.md`; re-arm one background wait per `working` agent in the entry; file the pending ClickUp bugs, if any.
5. Wait until orch-<N-1> is idle (never close it while working), then close its pane: `herdr pane close <pane id>`. Focus yourself and tell the user, in English, in one line that you own the run.
6. Continue the Lane Loop from "Next action". Keep checking your own context; at 70%, hand off to orch-<N+1> the same way.
```
