# Test strategy catalog

Every strategy a plan can include. For each candidate, decide **include now**, **deferred** (with the reason) or **not applicable** (with the reason), and record the result in the plan's `## Strategy coverage` table. A strategy that is never mentioned reads as covered, so none is left out silently.

Platforms: `ios` · `android` · `web` (viewport scope Desktop 1440×900 / Mobile web 375×667 / Both, asked once) · `api` (HTTP, no device).

**Every suite, whatever its strategy, is judged by the executor's `evaluation-standard.md`.** That file is appended to each worker package. It covers evidence rules, severity, the six-dimension quality score (0–100, PASS ≥ 85, CONDITIONAL PASS 60–84, FAIL < 60), error guessing, the 12 standard auth scenarios, the accessibility, console/log, visual and text checks, tenants and roles, API rules and the report template. Suites list their own scenarios; the standard adds the judging. Any suite that covers login, register or password reset gets the AUTH-01…12 set automatically.
Tools:
- `maestro-mcp`: interactive driving through the Maestro MCP tools; at most one live per platform.
- `maestro-cli`: scripted YAML flows run with `maestro --device <id> test`. When `maestro/flows/` has no flows for the suite, the worker writes them under `maestro/flows/<suite-id>/`, reading screens with `maestro --device <id> hierarchy`, then runs them. Plan extra time for that, or use the lane for flows that already exist.
- `playwright-mcp`: desktop web.
- `shell`: `xcrun simctl`, `adb`, `emulator`.
- `http`: Bash `curl` with the credential rules of the evaluation standard § 12 (API lanes).

## Mobile and web

| Strategy | Platforms | Tool | Default model | Include when | Technique / what it covers |
|---|---|---|---|---|---|
| `platform-discovery` | all UI platforms | maestro-mcp · playwright-mcp | sonnet | Whole-app audits, a new project, or `context/navigation-map.md` may be stale. First suite on its lane, before smoke | Reads the live navigation, tenants and role-dependent sections, reports drift against the navigation map without editing it (standard § 10). Its report scopes the later suites |
| `smoke` | all | maestro-mcp · playwright-mcp | sonnet | Always, first on every lane. Every other suite on the lane depends on it | App launches, login, the 3–5 critical paths reach their end screen. A smoke FAIL stops the lane's later suites (they become BLOCKED) |
| `acceptance` | all | maestro-mcp · playwright-mcp | sonnet | ClickUp tickets or vault requirements give acceptance criteria | One scenario per acceptance criterion, quoted verbatim from the source; each criterion ends PASS / FAIL / BLOCKED; never invent a criterion. A light pass on validations tied to the feature. At closing the orchestrator offers to add or update the flow in `context/regression-flows.md`. No source → not applicable |
| `functional-regression` | all | maestro-cli (existing flows) · maestro-mcp · playwright-mcp · shell (`npx playwright test` for an `e2e-tests/` suite) | sonnet | The project has `context/regression-flows.md` or `maestro/flows/`, or the release touches existing features | Re-run documented flows end-to-end, exactly as written, with their test data; one flow's failure does not stop the others; stale test data flagged apart from defects; flows whose last successful run is older than 30 days called out; "last successful run" updated only on PASS, by the orchestrator with the user's OK |
| `negative-validation` | all | maestro-mcp · playwright-mcp | sonnet | Any form or input | Equivalence partitioning, boundary values (min, max, min−1, max+1), error guessing (empty, special characters, `<script>`, `' OR 1=1 --`, letters in numeric fields, rapid double tap) |
| `exploratory` | all | maestro-mcp · playwright-mcp | opus | New feature, unclear requirements, or no documented flows | Session-based: one charter per suite ("Explore <area> with <resources> to discover <risk>"), timeboxed (30–60 min), notes as it goes |
| `ui-visual` | all UI platforms | maestro-mcp + shell · playwright-mcp | sonnet | Layout-heavy screens or a design system | Visual & UX review (standard § 8): typography, hierarchy, spacing, consistency, contrast, loading/empty states, feedback. Mobile: small screen (iPhone SE / small AVD) and large screen (Pro Max / tablet), landscape, dark mode (`xcrun simctl ui <udid> appearance dark`, `adb -s <serial> shell cmd uimode night yes`), clipped or overlapping text |
| `responsive-web` | web | playwright-mcp | sonnet | Any web suite | The viewport scope asked at planning: Desktop 1440×900, Mobile web 375×667, or both, plus any viewport the plan names. No horizontal overflow, broken alignment or hidden controls; screenshots per viewport; issues reported per viewport |
| `accessibility` | all | maestro-mcp (`inspect_screen`) · playwright-mcp (snapshot) | opus | Public-facing app, or the client asks | Missing accessibility labels on controls, touch targets < 44 pt (iOS) / 48 dp (Android), contrast, font scaling (`xcrun simctl ui <udid> content_size extra-extra-large`, `adb -s <serial> shell settings put system font_scale 1.3`), focus order on web, headings and roles |
| `text-quality` | all UI platforms | maestro-mcp · playwright-mcp | sonnet | The app has user-facing copy (almost always). Can share a lane run with `ui-visual` | Typos, grammar, mixed language, raw i18n keys, placeholder copy, punctuation and capitalisation, high-confidence only, one screenshot per screen (standard § 9) |
| `localization` | all | maestro-mcp · playwright-mcp | sonnet | The app ships more than one language | Device locale switch, untranslated keys in each language, truncated strings, date/number/currency formats. Per language, the text checks of `text-quality` |
| `multi-tenant-access` | all | maestro-mcp · playwright-mcp · http | opus | The app has organisations, tenants, workspaces or roles that change what a user sees | Per organisation: branding and data scope update, no other organisation's data, sections reachable, forms submit. Per role: sections and actions match the role; a limited role cannot reach admin screens. Needs one account per role/organisation; with one account, it is `deferred` with that reason (standard § 10) |
| `interruptions-lifecycle` | ios · android | maestro-mcp + shell | sonnet | Mobile, always worth considering | Background/foreground mid-flow, kill and relaunch (state restored?), rotation, OS permission prompts (allow, deny, deny forever), push or local notification while in a flow, Android back button on every screen, deep links (`xcrun simctl openurl`, `adb shell am start -d`) |
| `network-conditions` | ios · android · web | shell · playwright-mcp | sonnet | The app fetches data or syncs | Offline mid-flow, recovery when the connection comes back, slow network. Android: `adb -s <serial> emu network speed gsm` / `adb shell svc wifi disable` + `svc data disable`. iOS simulator has no CLI network throttle: test offline by turning off the Mac's network only when the lane runs alone, or mark it deferred |
| `install-upgrade` | ios · android | shell | sonnet | A previous build is available | Fresh install, upgrade over the previous build (data kept, session kept or cleanly expired), uninstall/reinstall. Needs both build paths in the plan; otherwise not applicable |
| `security-blackbox` | all | maestro-mcp · playwright-mcp | opus | There is auth, payments or user data | Session expiry mid-flow, logout really invalidates, deep link to an authenticated screen while logged out, sensitive data visible in the app switcher snapshot, one account reaching another account's data (two accounts required), no secrets in visible logs |
| `cross-platform-parity` | ios + android (+ web) | orchestrator compares reports | sonnet | The same features ship on more than one platform | Same flow, same data, compare outcomes and copy across platform reports. Runs after the platform suites; it is a read-only comparison of their evidence, no device |
| `cross-system-e2e` | mobile + web | ledger file | sonnet | Mobile creates data that web (admin) shows, or the reverse | One lane writes records to the run's ledger (`<run-dir>/ledger.md`); a later web suite verifies them. Dependency recorded in the suite header |
| `performance-stability` | android (ios limited) | shell + maestro-cli | sonnet | Release candidate, or the client reports slowness or crashes | Cold start time (`adb shell am start -W`), a Maestro flow looped N times without crash, monkey run (`adb -s <serial> shell monkey -p <package> --throttle 300 -v 2000`), crash logs (`adb logcat -b crash -d`, `xcrun simctl spawn <udid> log show --last 10m --predicate 'eventType == logEvent AND messageType == fault'`). Always labelled "emulator/simulator-indicative, not device-grade". Runs alone on its lane, last |
| `api-blackbox` | api | http (Bash `curl`) | sonnet (opus for authorization-heavy APIs) | The user names the API, or mobile/web failures need to be separated from backend failures | Its own lane `Lx-api`, no device. Version and account are inputs; keyless host check first; partitioning, boundaries, error guessing on payloads; authorization across organisations and roles; data asserted, not only status; caller-dependent failures held; no production writes; cleanup after writes; API coverage table (standard § 12). A sweep only when the user asks for the whole API; otherwise the endpoints the plan names |

## Choosing what goes in "now"

- **Urgency** never removes `smoke` and never hides a strategy. The plan author proposes `deferred` with the reason "time" in the coverage table. Deferring changes scope, so the user confirms it when reviewing the plan.
- **Priority** in the coverage table is `P0` (blocks release), `P1` (should run this cycle), `P2` (deferred is acceptable).
- A strategy the environment cannot support (no previous build, no second account, iOS network throttling) is `not applicable` or `deferred` with that missing precondition named. It never becomes a suite that will only report BLOCKED.
- `performance-stability` and `network-conditions` (iOS offline) disturb other lanes. Schedule them last, or alone.

## Model per suite

| Work | Model |
|---|---|
| Running existing Maestro flows, checking a fixed list of acceptance criteria, smoke | `sonnet` (`haiku` only for re-running flows with no judgment involved: exit codes and screenshots) |
| Exploratory, accessibility, security, anything that has to judge what "wrong" looks like | `opus` |
| Verification of FAIL findings (independent re-reproduction) | at least the suite's model; `opus` for security findings |

Driving a device through MCP requires reading screens and hierarchies. Do not plan `haiku` for `maestro-mcp` or `playwright-mcp` suites.
