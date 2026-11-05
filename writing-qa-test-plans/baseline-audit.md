# Baseline audit: planning from an existing regression

When the area under test already has regression coverage, the plan starts from it, not from zero. The audit reads every regression source of the area, decides what each flow is worth after the change being tested (a redesign, a new version of a feature), finds the regression that is missing, and only then are the suites written. Its results are the plan's `## Baseline audit (orchestrator-only section)`.

**Core rule: every scenario of the area states its origin.** Either a **source** (a baseline flow, a change ticket's acceptance criterion, a vault note, a file the user named), or **`proposed`**: a scenario the planner adds from the coverage review below, with the dimension and the risk that justify it. Both go into the plan; the label lets the user see at a glance what was already agreed and what is the planner's suggestion, and drop suggestions at review.

## Inputs (from the first message: the area, and the existing-regression question)

**Baseline sources** — where the existing regression lives. Any mix of:

| Kind | How to read it (read-only, always) |
|---|---|
| Local `.md` / `.csv` / `.feature` files | `Read` in full. Before asking, look for them yourself: `context/*regression*.md`, `context/*uat*.md`, `context/*test-cases*.md`, `maestro/flows/`, the project's Playwright specs (Before Writing step 3), and show what you found as ✅ status lines for the user to confirm |
| A file in another local repo | its absolute path, read in full |
| A repo URL (GitHub, Bitbucket, GitLab) | the user's local clone if they have one; otherwise the raw file through `gh api` / WebFetch. Never clone without asking |
| ClickUp test cases (a list, a folder, a test-suite task with subtasks, a Doc) | the ClickUp connector, read-only: `clickup_get_list` / `clickup_filter_tasks` / `clickup_get_task` (with subtasks) / `clickup_get_document_pages`. Same outcomes as Before Writing step 5 when the MCP is down |
| Vault notes | the vault MCP only (Before Writing step 4), never from disk |

A source the user names by a part only ("R-25 to R-28 and R-39", "TS-02") limits the audit to those items of that source; record the filter in the Sources table.

**Change sources** — what changed and why the baseline may be stale: redesign or feature tickets, epics, PRDs, vault notes, release notes. Read their description and acceptance criteria. A design link (Figma) the planner cannot open is listed as a change source `not read`.

**Area map** — the screens, states and entry points of the area, for the coverage review: `context/navigation-map.md`, the change tickets, the screens the baseline flows touch, the vault, and the app's routes or screens in the code when the repo is at hand (read-only).

**Area filter** — the area is the one answered in D1. A whole-app plan has the whole app as its area. Otherwise a baseline flow belongs to the area when its name, screen, route or source grouping (list, section, test suite) names the area. A flow that touches the area only partly (a checkout that starts from the redesigned screen) belongs to it. When membership is doubtful, include the flow and classify it `unclear`.

## Procedure

1. **Inventory.** Read every baseline source in full and list each flow of the area with its own id as the source writes it (`R-25`, `RF-12`, a ClickUp task id), steps, expected result, test data and last successful run if recorded. One flow found in several sources is one row naming every source; when the sources disagree on steps or expected result, say which one the plan follows and why, or mark it `unclear`.
2. **Read the change sources.** Note, per change ticket, which screens, flows, components and texts it alters, adds or removes.
3. **Classify each baseline flow** with exactly one value. Classifying an existing flow is a judgement about evidence, so the reason names the change source (ticket id + the sentence that decides it) or says that none touches the flow:

   | Classification | When | In the plan |
   |---|---|---|
   | `valid` | No change source touches the flow, or one touches it without altering its steps or expected result | `functional-regression` scenario, steps and expected copied from the baseline as written |
   | `changed` | A change source alters its steps, screens, texts or expected result | `functional-regression` scenario rewritten where the change source says; the rest stays as the baseline wrote it. The suite's `**ClickUp:**` (or `**Vault:**`) lists that change source, so the worker gets its text. If the source does not give the new expected text, the scenario says "as <ticket> describes" and the ticket is in the header |
   | `deprecated` | A change source removes the flow or the screen it runs on, explicitly | No scenario. Listed in the audit with the source sentence, and proposed for retirement from the regression set |
   | `unclear` | Membership doubtful, sources disagree, the change source is ambiguous or `not read` | Scenario kept in `functional-regression` with its baseline steps, plus a `to confirm` decision naming what the user must say. Never silently dropped and never guessed into `changed` or `deprecated` |

   No change sources at all: every flow of the area is `valid (no change source given)`.
4. **Missing regression: what the regression set does not cover.** Two passes, both written to the `Missing regression` table:
   - **From the sources:** a change ticket's acceptance criterion, a new screen, component or state the change adds, a vault requirement, with no baseline flow covering it. Origin: the source.
   - **From the coverage review** (origin `proposed`): walk the area map against the dimensions below and add a row for each gap that carries a real risk for this area. Name the dimension and the risk in one line ("empty state: a new user lands on Portfolio with no holdings; the redesign replaced that screen").

   | Dimension | What to look for, per screen or flow of the area |
   |---|---|
   | Entry points | Every way in: menu, tab, deep link, notification, back from another screen, an old URL or route the change renamed |
   | States | Empty, one item, many (scroll, pagination, sort, filter, search), loading, backend error, offline or slow |
   | Data | Boundaries, zero and negative values, decimals, currency, dates and time zones, long texts, special characters |
   | Roles and tenants | Each role and organisation in scope (D2) sees and does what it should; a limited role cannot |
   | Persistence | Reload or refresh, logout and login, kill and relaunch, back navigation, the state kept or reset as expected |
   | Cross-flow | Actions in another area that should show here (and the reverse): create, edit, delete, a payment, a sync |
   | Platforms and viewports | Each platform and viewport in scope, orientation; a flow the baseline wrote for one only |
   | The change itself | Every component the change adds or modifies: its interactive states (hover, focus, disabled, selected), its new copy, elements the change removed that must really be gone, old behaviours a redesign usually drops (sorting, totals, links) |

   Priority per row: `P0` when it guards money, data loss, auth or the area's main path; `P1` for the rest worth running this cycle; `P2` listed only. `P0` and `P1` rows become scenarios in this plan; `P2` rows stay in the table as `deferred` with the reason. Each row also says whether it should **join the regression set** after the run (`add`) or is a one-off check of this change (`one-off`).
5. **Where the scenarios go.** `valid`, `changed` and `unclear` flows → `functional-regression`. Missing rows → `acceptance` when the origin is a ticket with criteria (one scenario per criterion, quoted); otherwise the strategy the behaviour belongs to (`functional-regression` for a new end-to-end flow, `negative-validation`, `responsive-web`, `ui-visual`, `multi-tenant-access`, `network-conditions`, …). A `proposed` scenario's Scenario cell starts with `proposed ·`, so it stays visible in the suite and in the results.
6. **Platforms and viewports.** A flow the baseline wrote for one platform or viewport, and the plan covers more than one, gets a scenario per platform / viewport in scope, on that platform's lane. A baseline flow for a platform outside D1 is listed with `not applicable (platform out of scope)`.
7. **Stale data and age.** A flow whose test data no longer exists, or whose last successful run is older than 30 days, is flagged in the audit's Notes column; the `functional-regression` rules in `strategy-catalog.md` apply at execution.
8. **Show the audit to the user before writing suites**: counts per classification, every `deprecated` and `unclear` row, and the `Missing regression` table split into "from sources" and "proposed". Ask about the `unclear` rows and whether to keep the proposed ones, in one message, each with a proposed default (keep the `P0` and `P1` proposals). In a hurry: write the plan with the defaults marked `to confirm`.

The baseline sources and the change tickets are never edited during planning. What the regression set should gain or lose (deprecated flows to retire, changed flows to rewrite, missing rows marked `add`) is listed in `Proposed updates to the regression set`, for the user to apply; the executor offers to update `context/regression-flows.md` at closing, as it already does.

## Plan section

Write it right after `## Strategy coverage (orchestrator-only section)`. It is orchestrator-only: workers get the flows through their suite's scenario rows. Body in the project language; headings, table headers and classification values in English.

````markdown
## Baseline audit (orchestrator-only section)

**Area:** <area or feature> · **Change:** <redesign / feature, one line>

### Sources read

| Source | Kind | Filter | Flows of the area | Read |
|---|---|---|---|---|
| `context/regression-flows.md` | baseline (file) | area only | 9 | full |
| `context/uat-regression-set.md` | baseline (file) | R-25…R-28, R-39 | 5 | full |
| [TS-02 Portfolio](https://app.clickup.com/t/abc123) | baseline (ClickUp cases) | subtasks | 14 | full |
| [Portfolio redesign header](https://app.clickup.com/t/def456) | change (ticket) | – | – | description + AC |
| Figma "Portfolio v2" | change (design) | – | – | not read (no access) |
| `context/navigation-map.md` | area map | Portfolio section | – | full |

### Flow classification

| Flow | Title | Sources | Classification | Reason (change source + sentence, or "no change source touches it") | Plan scenarios | Notes |
|---|---|---|---|---|---|---|
| R-25 | … | uat-regression-set.md · TS-02/<task> | valid | … | S-003-01 (desktop), S-007-01 (mobile web) | – |
| RF-12 | … | regression-flows.md | changed | DEF-456: "…" | S-003-04 | step 3 rewritten |
| RF-14 | … | regression-flows.md | deprecated | DEF-456: "…" | – | propose retiring |
| TS-02-09 | … | ClickUp | unclear | sources disagree on the expected total | S-003-09 | D7 to confirm |

Totals: <n> valid · <n> changed · <n> deprecated · <n> unclear.

### Missing regression

| # | Behaviour not covered by the regression set | Origin | Dimension | Priority | Plan scenario | Regression set |
|---|---|---|---|---|---|---|
| M-1 | … | DEF-456 AC 3: "…" | the change itself | P0 | S-005-03 | add |
| M-2 | … | proposed: new user with no holdings, the redesign replaced the empty screen | states | P1 | S-003-12 | add |
| M-3 | … | proposed: … | data | P2 | deferred (time) | add |

Totals: <n> from sources · <n> proposed (<n> planned, <n> deferred).

### Open questions

<What the user must provide or decide that blocks a row above (an account for a role, a design the planner could not open), or "none".>

### Proposed updates to the regression set

<Flows to retire (deprecated), rewrite (changed) or add (missing rows marked `add`), for the user to apply after the run; or "none".>
````

Every `S-0NN-NN` in the `Plan scenarios` and `Plan scenario` columns exists in a suite. Every baseline scenario names its flow id in its Scenario cell (`R-25 · Ver portfolio vacío`) and every proposed one starts with `proposed ·` (`proposed · Portfolio sin posiciones`), so the audit and the suites can be checked against each other.
