# QA test plan template

Copy the block below into `qa-plans/YYYY-MM-DD-<name>.md` and replace every `<…>`. The headings are a contract with **executing-qa-test-plans**: its `scripts/make-package.sh` finds sections by exact heading text, optionally followed by ` (…)`. `## Device matrix (v2)` matches; `## Devices` does not.

Values known only at execution (device UDIDs/serials of devices not yet created, the run id's date, pane ids) are written as `resolved at execution`. That is the only allowed placeholder.

Write the plan in the project's language (`{project_language}`); keep the headings and header-line field names in English, because the script reads them.

````markdown
# <App> — QA test plan: <scope in a few words>

> **For agentic workers:** executed with executing-qa-test-plans; a worker runs only its own suite on its own lane.

**Goal:** <one sentence: what this run must tell the team, e.g. "go / no-go for release 2.4 on iOS, Android and admin web">
**App under test:**
- iOS: <path to .app (simulator build) or "installed via Expo dev client" or "none"> · bundle id `<com.company.app>`
- Android: <path to .apk or "none"> · package `<com.company.app>`
- Web: <base URL or "none"> (environment: <staging | dev | production read-only>)
- Backend environment URL the mobile builds point to: <https://api.staging.example.com>. Mobile reports put it in `**URL:**`, which ClickUp uses to tag the environment.
**First screen text (health check):** iOS "<text>" · Android "<text>" · Web "<text>"
**Sources:** Vault: <vault name + notes read, or `none` (reason)> · ClickUp: <list/tickets read, or `none` (reason)> · Project context: <`context/navigation-map.md`, `context/regression-flows.md`, `maestro/flows/`, or `none`>
**API:** <base URL · version · auth header, or "none">
**Language:** <project language> · **Viewport scope (web):** <Desktop 1440×900 | Mobile web 375×667 | Both>

## Decisions recorded for this plan

| # | Decision | Source | Status |
|---|---|---|---|
| D1 | Platforms in scope: <iOS, Android, web, API, or all> (asked first) | user | approved |
| D2 | User types covered: <admin (`ADMIN_EMAIL`), end user (`TEST_USER_EMAIL`), …; roles without an account named> | <user / vault / `.env.example`> | <approved / to confirm> |
| D3 | <e.g. Two Android `adb` lanes: Pixel_8_API_34 on 5554 and 5556 (`--read-only`), Mac has 32 GB> | plan author | adopted by plan author |
| D4 | <e.g. Workers run with `--permission-mode auto`> | <user / plan author> | <approved / adopted by plan author / to confirm> |
| D5 | <e.g. Verified bugs are created in ClickUp list 9001 "Bugs"> | user | to confirm |

## Strategy coverage (orchestrator-only section)

Every strategy from the catalog, with no omissions.

| Strategy | Decision | Priority | Suites | Reason |
|---|---|---|---|---|
| smoke | include now | P0 | S-001, S-004 | – |
| install-upgrade | not applicable | – | – | no previous build available |
| performance-stability | deferred | P2 | – | time; emulator-only results |
| … | … | … | … | … |

## Global Constraints

- The evaluation standard (`executing-qa-test-plans/evaluation-standard.md`) applies to every suite; each package carries § 0, 1, 2, 3, 7, 11 and 13 plus the sections its strategy owns (error guessing, AUTH scenarios, accessibility, visual, text, tenants, API, scripted suites), listed in the package under "Scope of the evaluation standard". Every worker still reports what it notices in evidence it already has. The lines below add only project-specific rules.
- Known non-bug quirks: <list, or "see context/navigation-map.md § Known Non-Bug Quirks", or "none recorded">.
- Never create, modify or delete production data. Never complete a purchase or payment, press a bulk or external-facing control (emails, notifications to real people), or approve/deny third-party records, unless this plan's decisions explicitly allow it.
- Credentials are referenced by `.env` variable name only. Never print, echo or write their values.
- Workers never create ClickUp tickets, never write to the vault, never install or download tools (no `brew`, no `npx`, no `curl | bash`), and never boot, shut down, erase or reinstall a device that is not their own lane's.
- <Project-specific constraints: test environment only, rate limits, demo data rules.>

## Device matrix

| Lane | Platform | Device | OS | Device id | Driver (`Tool:`) | Build installed | Owner rule |
|---|---|---|---|---|---|---|---|
| L1-ios | ios | iPhone 16 Pro (simulator) | iOS 18.2 | `<udid>` | `maestro-mcp` (installed) · or `axe` (D<n>, to confirm) | <.app path> | one worker at a time; one `maestro-mcp` lane per platform |
| L2-android | android | Pixel_8_API_34 (emulator) | API 34 | `emulator-5554` (console 5554) | `adb` (no install) | <.apk path> | one worker at a time |
| L2b-android | android | Pixel_8_API_34 (emulator, `--read-only`) or <second AVD> | API 34 | `emulator-5556` (console 5556) | `adb` (no install) | <.apk path> | one worker at a time; default from 16 GB (D3) |
| L3-web | web | Chrome (Claude in Chrome, the user's profile) | – | – | `chrome` (`--chrome`, no install) | <base URL> | one worker at a time; the only Chrome lane |
| L4-api | api | none (Bash `curl`) | – | – | `http` | <API base URL · version> | one worker at a time; starts in wave 1 |

Drivers come from `devices-and-tools.md` § Driver choice per lane (executing-qa-test-plans). A lane whose driver is not installed names the decision that installs it.

## Test data and accounts

| Lane | Role | Account (`.env` variable names, as they exist in `.env.example`) | Exclusive data range |
|---|---|---|---|
| L1-ios | <end user> | `<TEST_USER_EMAIL>` / `<TEST_USER_PASSWORD>` | <e.g. records named `QA-L1-*`, dates 2026-11-01…07> |
| L2b-android | <end user, second account> | `<TEST_USER2_EMAIL>` / `<TEST_USER2_PASSWORD>` (or the same account with the risk recorded as a decision) | <`QA-L2B-*`> |
| L3-web | <admin> | `<ADMIN_EMAIL>` / `<ADMIN_PASSWORD>` | <reads L1/L2 records; creates `QA-L3-*`> |

User types the app has, from the user-types question (source: user / vault / `.env.example`): <admin, operator, end user, …>. Roles without an account in `.env.example`: <list, each a `to confirm` decision>.

Each lane creates and edits only data in its own range, so parallel lanes never collide. Never write a variable name that does not exist; a missing account for a role is a `to confirm` decision. Seed data the suites rely on: <list, or "none">.

## Orchestration (orchestrator-only section)

<Filled from `orchestration-section-template.md` in this skill (writing-qa-test-plans): lanes and waves, model table, device preflight, launch recipe, ClickUp reporting, acceptance, closing steps.>

## Worker environment

- You run in your own Herdr pane, from the QA project root `<absolute path>`. You own exactly one lane: the device in your package. No other worker touches it while you run; you touch no other device.
- Your driver is the `Tool:` of your suite; its commands and the Driver protocol (one batched call per step, look once per screen, verify by text, screenshots to files) are at the end of your package. Android `adb`: Bash with `adb -s <serial>`. iOS `maestro-mcp`: the Maestro MCP tools with your `device_id`; `axe`: Bash with `axe … --udid`. Web `chrome`: the Claude in Chrome tools in tabs you create, viewport <Desktop 1440×900 via `resize_window`>; `playwright-mcp` (only when approved): viewport(s) <Desktop 1440×900 | Mobile web 375×667 | Both: start at 1440×900, then `browser_resize` to 375×667 and repeat, screenshots per viewport>. API: Bash `curl` only, following the evaluation standard § 12.
- Read `.env` only through Bash, inside one command: `set -a && source .env && set +a`, then use the variables. Never `Read`, `cat` or print it.
- Evidence goes to `evidence/<app-slug>/<suite-id>-<slug>/<run-id>/` (a full restart uses `<run-id>-a<N>`), so no run ever overwrites another: numbered screenshots `01-<what>.png` and `qa-report.md`.
- New Maestro flows you write go only under `maestro/flows/<suite-id>/`. Do not edit flows owned by other suites.
- Do not create `*.js` or other driver scripts, and do not install or download anything. Maestro YAML flows are test assets and are allowed where the suite says so.

## Suites

### Suite S-001: <title>

**Strategy:** smoke · **Platform:** android · **Lane:** L2-android · **Tool:** adb · **Model:** sonnet · **Priority:** P0 · **Depends on:** none · **Timebox:** 20 min · **Vault:** none · **ClickUp:** none

**Objective / charter:** <for exploratory: "Explore <area> with <resources> to discover <risk>">

**Preconditions:** <build installed on the lane, account, seed data; anything missing makes the dependent scenarios BLOCKED>

**Scenarios:**

| ID | Scenario | Steps | Expected | Technique |
|---|---|---|---|---|
| S-001-01 | App launches to login | launch app | text "Iniciar sesión" in the tree, no crash dialog | smoke |
| S-001-02 | … | … | … | … |

**Out of scope:** <what this suite does not check>

**Exit criteria:** every scenario has PASS / FAIL / BLOCKED with evidence; report written.

**Evidence:** `evidence/<app-slug>/S-001-<slug>/<run-id>/`

### Suite S-002: <title>

…

## Self-review (orchestrator-only section)

<Checklist results from writing-qa-test-plans § Self-Review, one line each.>
````

## Header line fields

| Field | Values |
|---|---|
| Strategy | a name from `strategy-catalog.md` |
| Platform | `ios` · `android` · `web` · `api` · `none` (comparison suites) |
| Lane | a lane id from the Device matrix, or `none` |
| Tool | `adb` (Android default) · `maestro-mcp` (iOS default when installed) · `axe` (iOS, approved install) · `maestro-cli` (existing flow files only) · `chrome` (web default) · `playwright-mcp` (web, approved install) · `http` · `shell` · combinations with `+` |
| Model | `opus` · `sonnet` · `haiku` |
| Priority | `P0` · `P1` · `P2` |
| Depends on | suite ids (`S-001 accepted`), or `none` |
| Timebox | minutes |
| Vault | note paths the worker needs, or `none` |
| ClickUp | ticket ids whose content the worker needs, or `none` |
