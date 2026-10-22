---
name: writing-qa-test-plans
description: Writes a QA test plan for a mobile app (iOS simulator, Android emulator) and/or web app (Chrome), to be executed by parallel Claude Code workers in Herdr panes, one device lane each, with the driver of each lane chosen and every install recorded as a decision. Manual only — run /writing-qa-test-plans.
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

**Two questions are always asked, in the first message, before any check:**

- **Platforms.** "What do we test: iOS, Android, web, API, or all of them?" Multi-select, one item per platform, even when the user already named some: the answer is the scope of the plan and is recorded as D1. Nothing outside it is planned, checked, booted or installed (§ Single-Platform Scope).
- **User types.** First look for them yourself: the vault (if its MCP is connected: notes on roles, permissions, organisations, test accounts), `context/navigation-map.md` (role-dependent sections, tenants), `.env.example` (account variable names such as `ADMIN_EMAIL`, `TEST_USER_EMAIL`). Show what you found as status lines ("✅ Found in the vault: roles admin, operator, end user; accounts `ADMIN_EMAIL`, `TEST_USER_EMAIL`"). Then ask only what is missing: "Which user types does the app have, and which of them should this plan cover?" with the roles you found as items to confirm plus the option to add others, and, per role, the `.env` variable name of its account (never the value). If nothing was found anywhere, ask the open question. A role with no account is still planned: its suites carry the account as a `to confirm` decision, and `multi-tenant-access` / role scenarios are `deferred` with that reason until it exists.

1. **Roles.** You are the plan author and future orchestrator: the only writer of the plan, the scratchpad (`QA-SCRATCHPAD.md` at the QA project root, from `scratchpad-template.md` in executing-qa-test-plans), and the vault.
2. **Session inputs** (ask once, carry forward):
   - project language (Spanish / English / bilingual);
   - platforms in scope: the answer to the first question above;
   - builds: the `.app` simulator build and the `.apk` paths, or how they get installed (Expo dev client, store build), plus the bundle id / package;
   - web base URL, environment, and **web viewport scope**: Desktop 1440×900, Mobile web 375×667, or Both. Never assume Both;
   - API, if in scope: base URL, version (if versioned), the auth header, and the key's `.env` variable name per account;
   - accounts per role (from the user-types question) and per organisation if the app has tenants, as `.env` variable names, never values. Check that the names exist in `.env.example`.

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
   - Android in scope: `adb version`, `emulator -list-avds`. That is all an `adb` lane needs;
   - iOS in scope: `xcrun simctl list devices available`, then which iOS driver exists: `maestro --version` (≥ 2.11) with `java -version` (17+), or `axe --help`;
   - web in scope: Chrome installed (`ls /Applications | grep Chrome`) and `claude --help` lists `--chrome`. Ask the user whether the Claude in Chrome extension is installed and signed in (you cannot check it from here). Playwright is **not** checked unless the user asks for it. When it is: the only check is `npx -y @playwright/mcp@0.0.83 --help` (the pinned version in `devices-and-tools.md`), and the plan writes that exact string in the decision, the Device matrix and the Worker MCP config. A Playwright MCP the user already registered in their own Claude (`claude mcp list`, often `@latest`) is **not** "installed" for the plan: workers never see the user's MCP registrations, only the run's pinned config. Never write `@latest` or an unpinned name anywhere in the plan;
   - `herdr --version`, `test "$HERDR_ENV" = 1`, `claude --help` for the launch flags;
   - RAM, for the lane defaults below: `sysctl -n hw.memsize` (bytes), and `emulator -list-avds` for a second Android lane.

   **Driver per lane and installs.** Pick each lane's `Tool:` with `devices-and-tools.md` § Driver choice per lane: Android `adb` (no install), iOS `maestro-mcp` if Maestro is installed, else `axe` or Maestro as a `to confirm` install decision, web `chrome`. Every install (Maestro, AXe, Playwright MCP, Java) is a `to confirm` decision with its cost and what it unlocks, never a default and never done by you. Suites on a lane whose driver is not installed are still planned; they cannot start until the user approves. Lanes whose driver exists start first.

   **Playwright MCP is opt-in.** Offer it only when the plan needs what Chrome cannot do: parallel web lanes, the 375×667 mobile-web pass, headless, or an isolated profile without the user's logins. The option says it downloads and runs a third-party server with `npx`. If the user says web is Chrome only, the mobile-web viewport scope becomes `N/A (driver)` in the plan.
8. **Decisions.** A decision **changes scope** if it changes what is tested, on which devices, against which environment, with which accounts, or whether anything is written outside the run (ClickUp tickets, production data). Ask about those. Routine choices (lane naming, suite order within a lane, timeboxes) are yours: `adopted by plan author`.

## Single-Platform Scope

The platforms in scope decide the lanes, the tools checked and the strategies that apply. Nothing outside the scope is planned, installed or booted.

| Scope | Lanes | Tooling checked | Strategies marked `not applicable` (reason "platform out of scope") |
|---|---|---|---|
| Web only | web lanes (and an API lane if asked) | Chrome + `--chrome`; Playwright MCP only by decision. **Not** Maestro, Java, Xcode or Android | `interruptions-lifecycle`, `install-upgrade`, mobile-only rows of `ui-visual`, `network-conditions` on devices, `cross-platform-parity` unless desktop vs mobile web is compared |
| Mobile only (iOS, Android or both) | one lane per device (and an API lane if asked) | Android: `adb`. iOS: Maestro + Java, or AXe. **Not** a browser | `responsive-web`, web rows of `ui-visual`, `cross-system-e2e` unless a web admin exists and is in scope |
| iOS only or Android only | lanes of that platform only | only that platform's tooling | the above, plus parity between iOS and Android |

Extra parallelism in a single-platform scope comes from more devices of that platform. Android: a second `adb` lane is the default (§ Lanes), no driver limit. iOS: a second lane is the default when AXe is already installed; otherwise it needs AXe (approved install) or runs only existing flow files with `maestro-cli`. Web: a second lane needs an approved Playwright MCP; with Chrome alone, web suites run one after the other on one lane.

## Lanes: the Rules That Make Parallel Workers Safe

- **One lane = one device = one live worker.** Suites on the same lane run in sequence. Two suites can run in parallel only on different lanes.
- **Waves are only the intended order.** Each lane moves to its next suite as soon as its previous one is accepted, without waiting for other lanes. Every limit below applies "at any moment", not "per wave".
- **Number of lanes = degree of parallelism.** More parallelism means more devices. **Defaults, recorded as `adopted by plan author`** (the user can trim them when reviewing the plan):
  - **Android: two `adb` lanes** when the Mac has 16 GB or more and the scope has at least two Android suites after the smoke. The second lane is a second AVD if `emulator -list-avds` shows one, else the same AVD booted again with `--read-only` on the next even port (`boot-device.sh --read-only`; no creation, no install). Split the Android suites between the lanes by plan order; each lane has its own smoke. Below 16 GB, or with another emulator already planned, one Android lane.
  - **iOS: a second lane when `axe --help` already works** (an `axe` lane next to the `maestro-mcp` one, on another simulator that exists). Without AXe, a second iOS lane is a `to confirm` install decision.
  - **API: always its own lane** (`Lx-api`, tool `http`), dispatched in the first wave: it needs no device and no smoke.
  - **Web: one `chrome` lane.** A second one is a Playwright decision.

  Creating a new AVD or simulator, and any install, stays a `to confirm` decision with its cost (`devices-and-tools.md` § Resource budget). The executor checks memory pressure before booting the second Android device and falls back to one lane if it is not green.
- **Driver limits.** At any moment, at most one live `maestro-mcp` worker per platform (fixed driver ports) and at most one live `chrome` worker (one tab group in the user's Chrome). Other lanes of the same platform use `adb` (Android), `axe` or `maestro-cli` with existing flows (iOS), or an approved `playwright-mcp` (web).
- **Live pane cap: 6** at any moment. It counts test workers and verify workers that are running; a verify worker that is only queued does not count. Plan at most 5 test lanes, so a verify worker can always start.
- **Verification is per lane, off the critical path.** A lane moves to its next suite as soon as the previous one passes the orchestrator's stage A checks; one verify worker per lane re-reproduces the accumulated High and Medium bugs when the lane's queue is empty, when 8 findings are pending, or at once for a critical-path smoke FAIL. Plan nothing that depends on a bug being confirmed before the next suite starts.
- **Each suite carries only the standard sections its strategy owns** (`evaluation-standard.md`, table at the top). The cross-cutting checks (§ 4 error guessing, § 5 auth scenarios, § 6 accessibility, § 8 visual, § 9 text) are covered per platform by their own suites. If a platform has no suite for one of them, the executor's `make-package.sh` puts that section into the platform's carrier suite (first acceptance / functional-regression / exploratory, else the smoke) as a fallback. Plan so the fallback is rare: every platform in scope gets, at least, `negative-validation`, `accessibility`, `ui-visual` and `text-quality` suites or an explicit `deferred` / `not applicable` in the coverage table, and a carrier whose timebox can absorb what is left.
- **Discovery, then smoke, first on every lane.** For a whole-app audit or a stale navigation map, `platform-discovery` runs first on each UI platform. Then `smoke`. Later suites on that lane depend on smoke: `**Depends on:** S-001 accepted`. A smoke FAIL turns them into BLOCKED, not into extra FAILs.
- **API lanes** (`Lx-api`, platform `api`, tool `http`) hold no device and no MCP driver. They still count toward the pane cap.
- **Scenario steps are written for batching.** A worker drives one batched call per scenario step (`driver-protocol.md` in executing-qa-test-plans): write Steps as the actions of one screen and Expected as a text the tree can prove ("'Reserva confirmada' visible"), not as a look ("the screen looks right"). Visual judgements belong to `ui-visual` and `text-quality` suites, where screenshots are the point.
- **Driver gaps are planned, not discovered.** `adb` cannot type accents or emoji (those scenarios go on a `maestro-mcp` lane or are `N/A (driver)`); `chrome` cannot emulate a mobile viewport; `maestro-cli` only runs flows that exist.
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

From `strategy-catalog.md` § Model per suite: `opus` for exploratory, accessibility, security and anything that has to judge; `sonnet` for smoke, acceptance and regression; `haiku` only for re-running existing flows with no judgment. Never `haiku` for a suite that reads screens (`adb`, `maestro-mcp`, `axe`, `chrome`, `playwright-mcp`). Give each suite a one-line rationale in the Orchestration model table.

## Summary File

Next to the plan, write `<plan-name>-summary.md` in the user's language, in plain words for non-technical readers: what will be tested, on which devices, what is deferred and why, and what the team needs to provide (builds, accounts, Maestro install). Link the plan from it.

## Self-Review

1. Every strategy in `strategy-catalog.md` appears in `## Strategy coverage` with a decision and a reason.
2. Every suite has the full header line. Its Lane exists in the Device matrix; its Depends on points to existing suites.
3. No two suites on the same lane overlap in time. Never two `maestro-mcp` suites of the same platform, nor two `chrome` suites, scheduled at the same moment. At most 5 test lanes.
4. Every lane has an account of the right role, whose variable names exist in `.env.example`, and a data range. A shared account or a missing role is a recorded decision.
5. Every scenario has an ID, steps, an expected result and a technique.
6. Sources are honest: `Vault:` and `ClickUp:` say what was read, or `none` with the reason. Nothing was written to ClickUp or the vault.
7. Decision statuses are honest. Every scope-changing decision the user has not answered (extra devices, ClickUp destination, any install: Maestro, AXe, Playwright MCP, Java; permission mode, production access) says `to confirm`. Every lane's `Tool:` is one the Device matrix can run without an unapproved install, or the lane's suites say they wait for that decision.
8. Values not yet known (UDIDs of devices still to be created) say `resolved at execution`. Nothing else is a placeholder.
9. Parity with the evaluation standard:
   - an `acceptance`, `negative-validation` or `security-blackbox` suite on each platform with login, register or password reset carries AUTH-01…12 (§ 5); smokes do not;
   - **per platform in scope**, `negative-validation`, `text-quality`, `accessibility` and `ui-visual` each have a suite, or a `deferred` / `not applicable` row in the coverage table that names the platform; a platform left without one is listed with the carrier suite that takes the fallback and the extra minutes added to its timebox;
   - tenants and roles found in the context files or named in the user-types answer are covered by `multi-tenant-access` and role scenarios, or deferred with the missing accounts named;
   - the web viewport scope is stated.
10. The first two questions were asked and answered: platforms (D1) and user types with their account variable names, each recorded as a decision with its source (user / vault / `.env.example`).
11. No `@latest` and no unpinned package name anywhere in the plan (`grep -n 'latest\|@playwright/mcp' <plan>` shows only `@playwright/mcp@0.0.83`, if Playwright is in the plan at all).

## Handoff

1. Save to `qa-plans/YYYY-MM-DD-<name>.md` at the QA project root, unless the project says otherwise, and the summary next to it.
2. Create or update `QA-SCRATCHPAD.md`: links, sources, decisions, suites table with status `planned`, tooling found.
3. Ask the user to review the plan and confirm every `to confirm` decision.
4. Stop. Execution starts only when the user runs `/executing-qa-test-plans <plan path>`: tell them that command in one line, and never start executing on your own.

## Common Mistakes

| Mistake | Fix |
|---|---|
| Two workers "on iOS" sharing the one booted simulator | One lane per device. More parallelism needs more devices: Android gets two `adb` lanes by default, iOS a second lane when AXe is installed, anything else as a decision |
| Starting the checks before asking what to test | Platforms and user types are the first message, always. The answer is the scope |
| "The app only has one kind of user" assumed from the login screen | Look in the vault, the navigation map and `.env.example`; then ask. An admin area tested with no admin account is a coverage gap the plan must name |
| Playwright "installed" because `claude mcp list` shows it | Workers get the run's config with `@playwright/mcp@0.0.83`; a user-level `@latest` registration is irrelevant and `@latest` never appears in a plan |
| One Android lane "to keep it simple" on a 32 GB Mac | Two `adb` lanes is the default from 16 GB; the second AVD or `--read-only` boot costs nothing to install |
| Every suite told to audit accessibility, console and visuals | Each suite carries only its strategy's sections; cross-cutting checks are suites of their own per platform, with the carrier fallback as the safety net |
| Two MCP-driven iOS lanes at once | Maestro MCP uses fixed ports per platform. The second lane runs `axe` (approved install) or `maestro-cli` on existing flows |
| Android lanes planned on Maestro by habit | `adb` is the default Android driver: 41 ms per tap, no Java, no port limit |
| Web lane planned on Playwright by habit | `chrome` (Claude in Chrome) is the default; Playwright only as an approved decision for what Chrome cannot do |
| Two web lanes on Chrome | One tab group for every session. A second web lane is an approved Playwright lane |
| Expected results written as "looks correct" | Write the text the tree must show; workers verify by text and screenshot only for evidence |
| Suites listing only "test the booking flow" | Scenarios with ID, steps, expected result and technique |
| Silently dropping strategies because it is urgent | Coverage table: `deferred` with "time" as the reason |
| Reading the vault from disk when the MCP fails | Ask; otherwise `Vault: none (MCP down)` |
| Creating ClickUp tickets or lists while planning | Destination list is a `to confirm` decision; tickets come after verification at execution |
| Inventing acceptance criteria when ClickUp is down | Use the vault or the user, or mark acceptance suites `deferred` |
| Installing Maestro, AXe or Playwright to "save time" | Ask first; record the decision. The planner never installs |
| Performance run in parallel with other lanes | Last, alone, labelled emulator-indicative |
| One shared account across parallel lanes, unmentioned | A recorded decision, or lanes run in sequence |
