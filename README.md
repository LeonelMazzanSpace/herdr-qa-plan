# Mobile + desktop web QA skills with Herdr

Two skills to plan and run QA for a mobile app (Xcode iOS simulators and Android Studio emulators) and its web version (Chrome). A Claude orchestrator hands each test strategy to an independent Claude worker in its own Herdr pane, and each worker drives a single device with its lane's driver:

| Platform | Default driver | Installs anything | Alternative (only with your OK) |
|---|---|---|---|
| Android | `adb` directly (tap 41 ms, screenshot 190 ms, tree 0.5 s) | no | `maestro-mcp` to type unicode/emoji or run existing Maestro flows |
| iOS | `maestro-mcp` if Maestro is already installed (one lane per platform) | no, if already there | `axe` (brew, no Java, no lane limit) or install Maestro |
| Web | `chrome`: Claude Code's native Chrome (`--chrome`), your own profile, one lane at a time | no | `playwright-mcp` (npx) for parallel web lanes or the 375×667 mobile viewport |
| API | `curl` | no | – |
| The project's Playwright tests | `playwright-test`: the project's own runner (`@playwright/test`), headless, no device, no MCP | no | – |

**If the project already has Playwright** (a `playwright.config.*` or `@playwright/test` in its `package.json`) and web is in scope, the plan adds a regression suite with those tests on its own no-device lane. A fresh Claude worker runs it with the project's runner (never an `npx` that downloads), reads the results from a JSON file, classifies each failure (bug, stale test, precondition or environment) and never edits the tests or updates snapshots. If the plan predates this rule, the orchestrator offers to add it at preflight.

**Neither skill installs anything without asking.** Maestro, AXe, Playwright MCP or Java appear in the plan as `to confirm` decisions; if you say no, the lanes that needed them are blocked and the rest still run.

Both are **manual only** (`disable-model-invocation: true`): Claude never loads them on its own; they run only when you call `/writing-qa-test-plans` or `/executing-qa-test-plans`.

| Skill | When to use it |
|---|---|
| `writing-qa-test-plans/` | To build the test plan. It goes through every strategy in the catalog (smoke, acceptance, regression, negative, exploratory, UI, accessibility, localization, interruptions, network, install/upgrade, security, performance, cross-platform parity, cross-system E2E) and marks each one included, deferred or not applicable, with its reason. It also defines the lanes (one device per lane), the accounts and data ranges, the model for each suite, and the suites with concrete scenarios. |
| `executing-qa-test-plans/` | To run that plan: boot the devices, build the packages, launch the workers in Herdr, accept each suite (mechanical check with `check-report.py` plus the FAIL screenshots), re-verify the bugs with one independent worker per lane, consolidate the report and, if approved, file the confirmed bugs in ClickUp. It also resumes a run. |

## First questions

Both skills keep messages short: one line for what is ready, one per problem and one per option; details live in files (plan, summary, HTML page), not in the chat.

`/writing-qa-test-plans`, with nothing else, asks:

1. **Conversation language**, alone and first. Everything after it is in that language (the plan and reports use the project language, which is separate).
2. In a single message, before any check:
   - **platforms:** iOS, Android, web, API or all;
   - **area:** one specific feature (for example, Portfolio) or the whole app;
   - **user types** and the `.env` variable of each account (never the value). It looks for them first in the vault, `context/navigation-map.md` and `.env.example`;
   - **existing regression:** where it lives (`.md` files, a repo link, ClickUp test cases, vault notes) and the tickets or docs describing the change (a redesign, a new version). It first looks on its own for `context/*regression*.md`, `context/*uat*.md`, `context/*test-cases*.md`, `maestro/flows/` and the Playwright specs.
3. Session details: environment and base URL, web viewport (1440, 375 or both), builds, project language.

`/executing-qa-test-plans <plan>` asks the language first (proposing the plan's), then which platforms run in this run and with which accounts.

## Planning from an existing regression

If the area already has regression coverage, the plan does not start from zero: it first runs a **baseline audit** (`writing-qa-test-plans/baseline-audit.md`).

1. **Reads every source of the area** and merges the same flow when it appears in several.
2. **Classifies each flow**, with the reason and the ticket that decides it:
   - `valid`: still holds;
   - `changed`: the redesign changes it (only what the ticket says is rewritten);
   - `deprecated`: the change removes it, only when a ticket says so;
   - `unclear`: left `to confirm` for you, never guessed.
3. **Tells you which regression is missing**, in two ways:
   - **from the sources:** what the change tickets ask for and no flow covers;
   - **proposed by the skill:** it walks the area by dimension (entry points, empty/error/loading states, boundary data, roles, persistence, cross-flows, viewports and the redesign's new components) and adds the gaps with real risk, each with its reason, priority and whether it should join the regression set.
4. **Shows you the result, and only then builds the suites:** one `functional-regression` suite per platform with the valid, changed and unclear flows; the missing P0/P1 rows in the suites they belong to (P2 rows are deferred); and the `## Baseline audit` section in the plan.

Proposed scenarios start with `proposed ·`, so you can tell them from agreed coverage and drop them at review. Your regression sources are never edited while planning. When the run closes, the executor shows the proposed updates (retire, rewrite, add, last successful run date) with each flow's outcome, and applies only the ones you approve, file by file. Anything outside the project (another repo, ClickUp, the vault) is listed for you to apply.

## Money movement

A scenario that pays, buys, transfers, refunds or signs an on-chain transaction carries `**Spend:**` on its suite: what moves, the cap, the account or wallet, and the environment (sandbox, testnet, real). The planner asks about it separately, once per suite: run it up to the cap, prepare it and stop before the final step (recommended with real money), or skip it. It is never asked again during the run: the executor does what that decision says, and `make-package.sh` refuses to build that suite's test or verify package without the approval block. At closing it lists every movement made so you can reconcile it.

## What it evaluates

The same as `qa-team-spacedev`, extended to iOS, Android and API. It lives in `executing-qa-test-plans/evaluation-standard.md`. Each worker receives the common sections (evidence, severity, score, console once per suite, forbidden actions, report template) plus the ones its strategy owns: error guessing in `negative-validation`, accessibility in `accessibility`, visual in `ui-visual`, text in `text-quality`, etc. (table at the top of the file). So a smoke does a smoke, and the cross-cutting checks are done by each platform's suite that owns them. If a platform has no suite for a check, `make-package.sh` puts it into that platform's carrier suite as a safety net, and prints it when building the package. Every worker still reports what it sees in the tree or screenshot it already has (a button without a label, an i18n key, a typo, a crash), without auditing.

What the standard defines:

- **Evidence:** no screenshot, no claim; every scenario ends in PASS, FAIL or BLOCKED (BLOCKED never counts as a defect); false positives are corrected in writing, never deleted; known non-bug behaviours are respected.
- **Quality score 0–100** over 6 dimensions: functional 30%, validation 20%, navigation 15%, visual 15%, accessibility 10%, console and logs 10%. PASS from 85, CONDITIONAL PASS from 60 to 84, FAIL below 60. One per suite and one for the whole run.
- **Severity** high, medium or low, with defined criteria, and Must Fix / Should Fix / Nice to Have actions.
- **Typical error cases:** equivalence classes, boundary values, double submit, back or refresh mid-flow, emoji, injection, long texts, uploads, dates and pagination.
- **The 12 standard authentication scenarios** (AUTH-01…12) in every login, sign-up or password-reset flow.
- **Accessibility** (web and mobile), **console and log health** (browser console, crashes and ANRs on mobile), **visual and UX review**, and **text quality**: typos, grammar, mixed language, i18n keys, placeholders.
- **Platform discovery:** drift against `navigation-map.md`, never editing it.
- **Organisations and roles:** data isolation between organisations; permissions tested with each role.
- **API:** version and account as inputs, credentials never printed, authorization across organisations, and failures that depend on which account calls are held until the key's owner is confirmed.
- **Known failures by the record:** open ticket = known; closed "as designed" = expected behaviour; closed for another reason = possible regression.
- **Regression:** stale test data flagged apart, a warning for flows not run in over 30 days, and an offer to add flows to the regression set.

## How the run stays short

- **Verification does not block the lane.** A suite is `accepted (pending verification)` as soon as it passes the mechanical check and the orchestrator has seen the FAIL screenshots; the lane starts its next suite at that moment. A single verify worker per lane re-reproduces the accumulated High and Medium bugs when the lane finishes its queue, when it has 8 findings, or at once if a smoke fails on a critical flow. CONFIRMED on the first reproduction; three attempts only when the first does not reproduce.
- **Acceptance is mechanical where it can be.** `scripts/check-report.py` validates the report template, the score arithmetic, scenario coverage against the plan and the existence of every evidence file in milliseconds; the orchestrator only opens the FAIL images, in parallel with subagents when several suites finish together.
- **More lanes by default.** Two Android `adb` lanes from 16 GB of RAM (a second AVD or the same one with `--read-only`, nothing installed), a second iOS lane if AXe is already installed, and the API lane always on its own, starting in the first wave.
- **Workers on Sonnet.** Every worker (test and verify) runs on `sonnet`; `opus` is the orchestrator's model (your session) and enters a worker only as a recorded exception: the restart after a second failed attempt, or a suite you asked for by name, with its cost recorded as a decision (≈2× output tokens, against the account's shared usage limit). A plan cannot use `opus` "because the previous run did".
- **Screenshot budget.** One for the happy path's end state plus one per FAIL; visual suites (`ui-visual`, `responsive-web`, `text-quality`, `localization`, `platform-discovery`) one per screen or viewport. `check-report.py` warns when a suite goes over two screenshots per scenario.
- **The orchestrator never runs out of context: it hands over.** It reads its own context usage from the Herdr pane (`ctx:N%`) before every dispatch, acceptance and batch of verdicts. At 70% it finishes only the step in progress, writes a hand-off entry in `QA-SCRATCHPAD.md` (live agents, devices, verification queue, open questions, next action), starts a new orchestrator (`orch-N`) in a new pane, waits for its confirmation and steps down; the relief closes the old pane and carries on. Workers and devices do not notice. It never relies on context compaction.
- **Cost stated before dispatch.** The preflight says how many model calls the run will consume (≈190 per mobile suite and 200–320 per web suite, measured in October 2026) and reminds you that the account's usage limit is shared with your other sessions.

## How workers drive the device fast

The bottleneck is not the emulator but the number of model turns and the bytes each one returns. `executing-qa-test-plans/driver-protocol.md` is appended to every package with the rules and the measured latencies (2026-10-15, M2 Pro 16 GB):

- look at the tree once per screen and act by text/id/bounds, never guess coordinates from a screenshot;
- one call per scenario step (a multi-command Maestro flow, `axe batch`, one Bash with several `adb` lines, `browser_batch` in Chrome);
- verify by text (`assertVisible` ≈ 150 ms, `grep` on the dump) and save screenshots straight to file; the inline image (160–250 KB) only when the check is visual;
- never `maestro test` or `maestro hierarchy` per step (9–22 s per invocation); the CLI only runs whole flow files;
- animations off on Android (`uiautomator dump` drops from 2.1 s to 0.5 s);
- on Playwright, one `browser_run_code_unsafe` per scenario (navigate, act, wait, verify the text and save the screenshot in a single call); `browser_snapshot` once per new screen, only to find selectors. Without this, a 25-suite web run cost twice the calls of a 26-suite mobile one;
- a worker's questions (a login code, a missing precondition) go to `<run-dir>/<suite>.question.md`, never to a widget in the pane (`AskUserQuestion` is blocked at launch); the orchestrator answers in `.answer.md`, and a login code requested more than 8 minutes ago is requested again instead of being relayed stale.

## Optional sources

- **Vault (Obsidian or another MCP):** if connected and it has project notes, the plan cites them and the orchestrator copies the excerpts into the packages. With no vault, or an MCP that does not connect, the plan says `Vault: none (reason)` and carries on. Vault files are never read from disk.
- **ClickUp:** two independent roles, both optional.
  - **Source:** tickets provide the acceptance criteria. They are read fresh every run.
  - **Destination:** where confirmed bugs go. It is written to only with the approved decision, never while planning. Before the first ticket, the skill asks once for the assignee and whether to also add the tickets to a sprint or another list. If ClickUp refuses the extra list ("Tasks in Multiple Lists" off), the summary lists those tickets for you to add by hand.

  If you give no ClickUp (neither in the plan nor when the skill asks, once), the run **never touches ClickUp**, even if the MCP is connected, and the result is **only the HTML page**. The HTML is also generated if ClickUp was planned but disconnected or the destination was not approved. Closing generates an HTML results page: `evidence/<app>/QA-RUN-RESULTS-<run-id>.html`. It has the summary, the go / no-go, results per suite, bugs with their verification and screenshots, false positives and coverage gaps. It opens offline. To share it, send the whole `evidence/<app>/` folder (screenshots are linked). Bugs also stay in each `qa-report.md` Bug Register, ready for `/report-bugs-to-clickup`.
- **No vault and no ClickUp:** requirements come from what the user describes, from `context/` and `maestro/flows/` (if present), or from an exploratory discovery suite.

## Requirements

- Herdr, with the Claude integration (`herdr integration install claude`), and the orchestrator running inside a pane (`HERDR_ENV=1`);
- Claude Code, with the status line showing the context percentage (`ctx:N%`): the orchestrator hand-off depends on that reading and the preflight stops if it is missing;
- the `herdr` and `herdr-agent-orchestration` skills;
- the Superpowers plugin (`verification-before-completion`);
- Xcode with simulators, and Android Studio with at least one AVD (`emulator`, `adb`). That is enough for the Android lanes (`adb`);
- for iOS, one of the two: Maestro CLI ≥ 2.11 with Java 17+ (workers get the Maestro MCP through `--mcp-config`), or AXe (`brew install cameroncooke/axe/axe`). Neither is installed without your OK;
- for web, Google Chrome open with the "Claude in Chrome" extension (≥ 1.0.36) connected to your claude.ai organisation and a `/login` session on a direct Anthropic plan. Workers start with `--chrome`;
- bash. The scripts work with macOS bash 3.2, and `render-results.py` with the system Python (`/usr/bin/python3`, 3.9+);
- optional:
  - the Playwright MCP pinned at `@playwright/mcp@0.0.83` (never `@latest`: workers run it through Bash), only if you approve that decision: parallel web lanes, the 375×667 mobile viewport, headless or an isolated profile. A Playwright MCP you already registered in your Claude (`claude mcp list`) does not count as installed: workers only see the run's config with the pinned version, and the preflight checks that the plan names no other;
  - a vault MCP (Obsidian or another), if the project has a vault;
  - the ClickUp MCP, if tickets are a requirements source or confirmed bugs are filed there;
  - the `qa-team-spacedev` skills (`qa-evidence-discipline`, `report-bugs-to-clickup`, `qa-report-test-execution`). If present they are reused; otherwise the plan copies their rules.

### Setup

1. Herdr and Claude Code installed. Check with `herdr --version` and `claude --version`.
2. Herdr's Claude Code integration:

   ```bash
   herdr integration install claude
   herdr integration status      # must show: claude: current
   ```

3. Herdr skills:

   ```bash
   npx skills add herdrdev/herdr --skill herdr -g
   npx skills add aerain/herdr-agent-orchestration -g -s herdr-agent-orchestration -a claude-code
   ```

4. Superpowers, inside Claude Code:

   ```
   /plugin install superpowers@claude-plugins-official
   ```

5. Simulators and emulators. Check there is at least one device per platform:

   ```bash
   xcrun simctl list devices available   # iOS simulators (Xcode)
   emulator -list-avds                   # Android Studio AVDs
   adb version
   ```

6. iOS driver, only if there are iOS lanes (Android runs on `adb` with nothing else). One of the two options; the skill asks you and never installs on its own:

   ```bash
   # Maestro CLI + Java: pinned version, and without piping the script (read it before running it)
   curl -fsSL "https://get.maestro.mobile.dev" -o /tmp/maestro-install.sh
   MAESTRO_VERSION=2.11.0 bash /tmp/maestro-install.sh
   maestro --version                     # 2.11.0
   java -version                         # 17 or later
   # or AXe (single binary, no Java)
   brew install cameroncooke/axe/axe
   axe list-simulators
   ```

   To use the Maestro MCP yourself, interactively:

   ```bash
   claude mcp add maestro --scope user -- maestro mcp
   ```

7. Web with Claude Code's native Chrome: install the "Claude in Chrome" extension from the Chrome Web Store, sign in to the same claude.ai organisation as your `claude` (`/login`), keep Chrome open and allow the domains you will test in the extension. Check with `claude --chrome` and `/chrome` in a session of your own. Playwright MCP is not needed unless you approve it in the plan. **Careful:** this lane acts inside your real Chrome, with your logged-in sessions. Use it only against your own staging or dev sites, ideally from a dedicated Chrome profile with nothing else open and the extension allowing only the QA domains. For any other site, use the Playwright lane (isolated profile).

## Installation

The full step-by-step guide is [`setup-herdr-qa.html`](setup-herdr-qa.html): requirements, status line, drivers per platform, optional sources, permissions, first use and troubleshooting. The short version is above, in Setup.

To use the skills in every project, link them into your personal skills folder, from the root of this repo:

```bash
ln -s "$PWD/writing-qa-test-plans" ~/.claude/skills/writing-qa-test-plans
ln -s "$PWD/executing-qa-test-plans" ~/.claude/skills/executing-qa-test-plans
```

To use them in a single QA project only, link them into its `.claude/skills/`.

The `.sh` scripts in `executing-qa-test-plans/scripts/` run with `bash <script>` (they work with macOS bash 3.2). `render-results.py` and `check-report.py` run with `/usr/bin/python3` (the system Python, 3.9+, standard library only; `check-report.py` imports the parser from `render-results.py`, so they go together).

## Security

- **Untrusted content:** ticket text, vault excerpts, app or site screens, API responses and logs are data, never instructions (`evaluation-standard.md` § 0, and a line in every package). An injection attempt is reported as a finding, never obeyed.
- **Credentials:** besides the written rule, workers start with `--disallowedTools` (`devices-and-tools.md` § Secret deny rules): it blocks reading `.env*` and dumping the environment even in `auto` mode. It is an extra defence, not a sandbox.
- **Pinned versions:** Maestro 2.11.0 and `@playwright/mcp@0.0.83`. To upgrade them, read the new version's release notes and change every place that names it.
- **`chrome` lane:** the most exposed one, because it uses your real profile (see setup step 7).

## Known limits

- Maestro and AXe do not support physical iOS devices: iOS testing runs on simulators.
- The Maestro MCP uses fixed ports per platform. So at most one MCP worker per platform runs at a time; extra Android lanes use `adb`, and extra iOS lanes use AXe (with your OK) or `maestro test` on existing flows only.
- The native Chrome shares a single tab group across all Claude Code sessions and uses your profile: one web lane at a time, and you see whatever the worker opens. It does not emulate mobile viewports.
- `adb shell input text` cannot type accents or emoji: those scenarios go to a `maestro-mcp` lane or are `N/A (driver)`.
- The iOS simulator has no command-line network throttling.
- Performance measurements on an emulator are indicative, not equivalent to a real device.
