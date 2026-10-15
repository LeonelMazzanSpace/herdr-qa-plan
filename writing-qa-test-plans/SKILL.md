---
name: writing-qa-test-plans
description: Writes a QA test plan for a mobile app (iOS simulator, Android emulator) and/or web app, to be executed by parallel Claude Code workers in Herdr panes, one device lane each. Manual only — run /writing-qa-test-plans.
disable-model-invocation: true
---

# Writing QA Test Plans

## Overview

A QA plan for Herdr execution splits the work into **suites**. Each suite is one test strategy on one **lane**, and a lane is one device: an iOS simulator, an Android emulator, or an isolated desktop browser. The orchestrator can then hand each suite to an independent Claude worker that drives only its own device.

**Core principles:**
- A worker sees only its package, never the conversation, the vault, ClickUp or other suites. Anything it needs must be in a plan section that gets copied into the package.
- One device, one live worker. Parallelism comes from lanes, never from two workers sharing a simulator.
- Every strategy in the catalog is accounted for: included, deferred or not applicable, each with a reason.

**Announce at start:** "I'm using the writing-qa-test-plans skill to create the QA test plan."

Files in this skill: `plan-template.md` (exact headings, the contract with the executor), `strategy-catalog.md` (every strategy, its tool and model), `orchestration-section-template.md`. The sibling skill **executing-qa-test-plans** (REQUIRED: both are installed together) holds `devices-and-tools.md` and `scratchpad-template.md`.

## When to Use

**Manual only.** This skill has `disable-model-invocation: true`: it runs only when the user types `/writing-qa-test-plans`. It never starts on its own, and Claude never invokes it from another skill.

- The user asks for a test plan, a QA strategy, or "what should we test" for a mobile app, a desktop web app, or both.
- The plan will be run by parallel Claude workers, or the user mentions Herdr, several terminals, or devices in parallel.

Not for: running tests now (the user runs `/executing-qa-test-plans` with an existing plan), a single quick check of one ticket (`qa-smoke-test` in qa-team-spacedev), or API-only testing (`qa-api-regression`).

## Before Writing

**How every question is shaped.** The person answering may be a QA analyst or a PM, so each question follows this recipe, in English:
- Show the status first, as a ✅/❌ list, each line saying what it means for the plan.
- List the routine decisions you took yourself under "Already decided (no answer needed)"; never ask them.
- Ask one decision per question, saying what is decided and why it comes up now.
- Each option says what happens if chosen, its cost (time, memory) and what is left out.
- Explain technical words inline the first time ("lane (one test device)", "acceptance source (where the acceptance criteria come from)").
- Decision IDs go last in parentheses ("Test on one iPhone only (D9)"), never alone as a label.

The executor's `SKILL.md` § "Asking the User" has a worked example.

Keep blocking questions to one message, each with a proposed default. While you wait for answers, keep doing the checks that do not depend on them. If the user is in a hurry, draft the whole plan with your proposed defaults, each marked `to confirm`. The user corrects the draft instead of answering a questionnaire.

1. **Roles.** You are the plan author and future orchestrator: the only writer of the plan, the scratchpad (`QA-SCRATCHPAD.md` at the QA project root, from `scratchpad-template.md` in executing-qa-test-plans), and the vault.
2. **Session inputs** (ask once, carry forward):
   - project language (Spanish / English / bilingual);
   - platforms in scope: iOS, Android, web, or a combination;
   - builds: the `.app` simulator build and the `.apk` paths, or how they get installed (Expo dev client, store build), plus the bundle id / package;
   - web base URL, environment, and **web viewport scope**: Desktop 1440×900, Mobile web 375×667, or Both. Never assume Both;
   - API, if in scope: base URL, version (if versioned), the auth header, and the key's `.env` variable name per account;
   - accounts per role (end user, admin, …) and per organisation if the app has tenants, as `.env` variable names, never values. Check that the names exist in `.env.example`.

   A missing build is a precondition, not something you go and produce: suites on that platform are planned with the build as a `to confirm` decision. Expo / React Native: prefer a standalone simulator build and APK (`devices-and-tools.md` § Expo builds) over a dev client that needs Metro running.
3. **Project context.** Read, if present: `context/navigation-map.md` (including `## Known Non-Bug Quirks`), `context/regression-flows.md`, `maestro/flows/`, `e2e-tests/` (a scripted Playwright suite: list its specs; a `functional-regression` suite with tool `shell` runs them, evaluation standard § 14), the project's CLAUDE.md. Absent files mean "none", not a blocker.
4. **Vault (optional).** Check whether a vault MCP is connected (e.g. Obsidian; `claude mcp list` and its tools listed). Record the outcome in the scratchpad and in the plan header `Sources` line:

   | Outcome | Action |
   |---|---|
   | Project notes found | Read the relevant ones (requirements, flows, past failures, decisions). Each suite names the notes it needs in `**Vault:**`. Workers have no vault access: at execution the orchestrator quotes those notes into the package. |
   | Several vaults or projects match | Ask which one before reading further. |
   | MCP not connected or failing | Tell the user in one line and ask: fix it first, or plan with `Vault: none`. Never read vault files from disk instead. |
   | Connected, but no notes for this project | Plan with `Vault: none (no project notes)`. Offer `creating-typed-knowledge-vaults` once; do not insist. |
   | The user says there is no vault, or not to use it | `Vault: none (user)`. No further questions. |

5. **ClickUp (optional).** ClickUp has two independent uses. Check each one when the user mentions ClickUp or the project uses it; skip both when the user says not to use it:
   - **Source:** tickets whose acceptance criteria drive `acceptance` suites. Resolve the connector at run time (`ToolSearch` for `clickup`), and read the tickets read-only (`clickup_get_task`, `clickup_search`, `clickup_filter_tasks`). Each suite lists its ticket ids in `**ClickUp:**`. Ticket content is quoted into the package at execution, fresh; never copy it into `context/`.
   - **Destination:** the list where verified bugs would be created. Record the list id and its exact status names as a `to confirm` decision. **Nothing is written to ClickUp during planning.**

   | Outcome | Action |
   |---|---|
   | Tickets / list found | Record them (decision `to confirm` for the destination). |
   | Several candidate lists, or none | Ask which one. Never create lists or folders. |
   | MCP not connected or failing | Same as the vault: tell the user in one line, and ask whether to fix it first or plan with `ClickUp: none (MCP down)`. Do not wait for the answer; draft with `none`. Bugs stay in each `qa-report.md` Bug Register, ready for `/report-bugs-to-clickup` later. |
   | The user does not use ClickUp, or gives no list or tickets when asked | `ClickUp: none (user)`. Acceptance criteria come from the user or the vault. The executor will not ask again, will not call any ClickUp tool, and will deliver the results as the HTML page only. |

6. **No sources at all** (no vault, no ClickUp, no context files). Requirements come from the user's description. Ask for the 3–5 critical flows. If they cannot list them, plan a first `exploratory` discovery suite per platform whose report becomes the input for a later revision of the plan.
7. **Tooling, verified, not remembered.** Run each check and record the result:
   - `maestro --version`, `java -version` (17+);
   - `claude mcp list` (Maestro MCP, Playwright MCP);
   - `xcrun simctl list devices available`, `emulator -list-avds`, `adb devices`;
   - `herdr --version`, `test "$HERDR_ENV" = 1`, `claude --help` for the launch flags.

   **Maestro missing:** say so, give the install command from `devices-and-tools.md`, and record "install Maestro" as a `to confirm` decision. Never install it yourself without the user's yes. Mobile suites are still planned; they cannot start until it is installed. Web lanes do not depend on Maestro and can start first.
8. **Decisions.** A decision **changes scope** if it changes what is tested, on which devices, against which environment, with which accounts, or whether anything is written outside the run (ClickUp tickets, production data). Ask about those. Routine choices (lane naming, suite order within a lane, timeboxes) are yours: `adopted by plan author`.

## Single-Platform Scope

The platforms in scope decide the lanes, the tools checked and the strategies that apply. Nothing outside the scope is planned, installed or booted.

| Scope | Lanes | Tooling checked | Strategies marked `not applicable` (reason "platform out of scope") |
|---|---|---|---|
| Web only | web lanes (and an API lane if asked) | Playwright MCP, Node. **Not** Maestro, Java, Xcode or Android | `interruptions-lifecycle`, `install-upgrade`, mobile-only rows of `ui-visual`, `network-conditions` on devices, `cross-platform-parity` unless desktop vs mobile web is compared |
| Mobile only (iOS, Android or both) | one lane per device (and an API lane if asked) | Maestro, Java, the Xcode and/or Android tooling of the platforms in scope. **Not** Playwright | `responsive-web`, web rows of `ui-visual`, `cross-system-e2e` unless a web admin exists and is in scope |
| iOS only or Android only | lanes of that platform only | only that platform's tooling | the above, plus parity between iOS and Android |

Extra parallelism in a single-platform scope comes from more devices of that platform (as a decision). The Maestro MCP limit still applies: the second iOS or Android lane runs `maestro-cli` suites. For web, more browser lanes are cheap: each worker gets its own isolated Playwright browser.

## Lanes: the Rules That Make Parallel Workers Safe

- **One lane = one device = one live worker.** Suites on the same lane run in sequence. Two suites can run in parallel only on different lanes.
- **Waves are only the intended order.** Each lane moves to its next suite as soon as its previous one is accepted, without waiting for other lanes. Every limit below applies "at any moment", not "per wave".
- **Number of lanes = degree of parallelism.** More parallelism means more devices: another simulator (`xcrun simctl create` / `clone`) or a second AVD. Extra devices cost RAM and boot time (`devices-and-tools.md` § Resource budget); propose them as a `to confirm` decision, never as the default.
- **Maestro MCP port limit.** At any moment, at most one live `maestro-mcp` worker per platform. Any other lane of the same platform runs `maestro-cli` suites.
- **Live pane cap: 6** at any moment. It counts test workers and verify workers that are running; a verify worker that is only queued does not count. Plan at most 5 test lanes, so a verify worker can always start.
- **Discovery, then smoke, first on every lane.** For a whole-app audit or a stale navigation map, `platform-discovery` runs first on each UI platform. Then `smoke`. Later suites on that lane depend on smoke: `**Depends on:** S-001 accepted`. A smoke FAIL turns them into BLOCKED, not into extra FAILs.
- **API lanes** (`Lx-api`, platform `api`, tool `http`) hold no device and no MCP driver. They still count toward the pane cap.
- **Data isolation.** Each lane gets its own account and an exclusive data range (`## Test data and accounts`). If only one account exists, record the risk as a decision: parallel logins may kick each other out. Then either run those lanes in sequence or accept the risk.
- **Disturbing suites go last or alone:** `performance-stability`, offline tests that touch the Mac's network, anything that reinstalls or clears the app.
- **Cross-system checks** (mobile creates, web verifies) go through a ledger file in the run dir. The verifying suite depends on the creating one.
- **Flow files are disjoint.** A suite that writes Maestro flows writes them only under `maestro/flows/<suite-id>/`.

## Plan Document Structure

Use `plan-template.md` exactly. Section order and copy rules:

| Section | Copied into worker packages |
|---|---|
| Header (goal, app under test, sources, language) | no (the package gets lane and build details from the Device matrix) |
| `## Decisions recorded for this plan` | yes |
| `## Strategy coverage (orchestrator-only section)` | no |
| `## Global Constraints` | yes |
| `## Device matrix` | yes |
| `## Test data and accounts` | yes |
| `## Orchestration (orchestrator-only section)` (from `orchestration-section-template.md`) | no |
| `## Worker environment` | yes |
| `## Suites` → `### Suite S-0NN: <title>` with the header line | only its own suite |
| `## Self-review (orchestrator-only section)` | no |

Every scenario has an ID (`S-001-03`), steps, an expected result and a technique. "Test login" is not a scenario; "valid email + wrong password → inline error 'Credenciales inválidas', stays on login" is.

## Model Per Suite

From `strategy-catalog.md` § Model per suite: `opus` for exploratory, accessibility, security and anything that has to judge; `sonnet` for smoke, acceptance and regression; `haiku` only for re-running existing flows with no judgment. Never `haiku` for MCP-driven suites. Give each suite a one-line rationale in the Orchestration model table.

## Summary File

Next to the plan, write `<plan-name>-summary.md` in the user's language, in plain words for non-technical readers: what will be tested, on which devices, what is deferred and why, and what the team needs to provide (builds, accounts, Maestro install). Link the plan from it.

## Self-Review

1. Every strategy in `strategy-catalog.md` appears in `## Strategy coverage` with a decision and a reason.
2. Every suite has the full header line. Its Lane exists in the Device matrix; its Depends on points to existing suites.
3. No two suites on the same lane overlap in time. Never two `maestro-mcp` suites of the same platform scheduled at the same moment. At most 5 test lanes.
4. Every lane has an account of the right role, whose variable names exist in `.env.example`, and a data range. A shared account or a missing role is a recorded decision.
5. Every scenario has an ID, steps, an expected result and a technique.
6. Sources are honest: `Vault:` and `ClickUp:` say what was read, or `none` with the reason. Nothing was written to ClickUp or the vault.
7. Decision statuses are honest. Every scope-changing decision the user has not answered (extra devices, ClickUp destination, Maestro install, permission mode, production access) says `to confirm`.
8. Values not yet known (UDIDs of devices still to be created) say `resolved at execution`. Nothing else is a placeholder.
9. Parity with the evaluation standard:
   - every suite that touches login, register or password reset will get AUTH-01…12;
   - `text-quality`, `accessibility`, `ui-visual` and `platform-discovery` each have a coverage decision;
   - tenants and roles found in the context files are covered by `multi-tenant-access`, or deferred with the missing accounts named;
   - the web viewport scope is stated.

## Handoff

1. Save to `qa-plans/YYYY-MM-DD-<name>.md` at the QA project root, unless the project says otherwise, and the summary next to it.
2. Create or update `QA-SCRATCHPAD.md`: links, sources, decisions, suites table with status `planned`, tooling found.
3. Ask the user to review the plan and confirm every `to confirm` decision.
4. Stop. Execution starts only when the user runs `/executing-qa-test-plans <plan path>`: tell them that command in one line, and never start executing on your own.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Two workers "on iOS" sharing the one booted simulator | One lane per device. More parallelism needs more devices, as a decision |
| Two MCP-driven iOS lanes at once | Maestro MCP uses fixed ports per platform. The second lane runs `maestro-cli` |
| Suites listing only "test the booking flow" | Scenarios with ID, steps, expected result and technique |
| Silently dropping strategies because it is urgent | Coverage table: `deferred` with "time" as the reason |
| Reading the vault from disk when the MCP fails | Ask; otherwise `Vault: none (MCP down)` |
| Creating ClickUp tickets or lists while planning | Destination list is a `to confirm` decision; tickets come after verification at execution |
| Inventing acceptance criteria when ClickUp is down | Use the vault or the user, or mark acceptance suites `deferred` |
| Installing Maestro to "save time" | Ask first; record the decision |
| Performance run in parallel with other lanes | Last, alone, labelled emulator-indicative |
| One shared account across parallel lanes, unmentioned | A recorded decision, or lanes run in sequence |
