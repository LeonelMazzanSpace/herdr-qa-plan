# Devices and tools reference

Checked against Maestro CLI 2.11.0 (2026-09-29), herdr 0.9.1, Claude Code 2.1.301 (`--chrome`, Claude in Chrome extension ≥ 1.0.36) and AXe docs (2026-10-15). Tool names drift between versions. Re-check against the installed `--help` and the tools a session actually lists before trusting this file. How a worker uses each driver, with measured latencies, is in `driver-protocol.md`.

## Driver choice per lane

**Nothing is installed without the user's yes.** The plan records every install (Maestro, AXe, Playwright MCP, Java) as a `to confirm` decision; the preflight asks once; a lane whose driver is missing and not approved is `blocked (driver not approved)`, never worked around with a script.

| Platform | Default driver (`Tool:`) | Needs | When to pick another |
|---|---|---|---|
| android | `adb` — Bash only, `adb -s <serial>` for taps, text, keys, screenshots, `uiautomator dump` for the tree. 41 ms per tap, 190 ms per screenshot, 0.5 s per tree with animations off. No Java, no Maestro, no port limit: as many Android lanes as the RAM allows | Android SDK platform-tools | `maestro-mcp` when the suite needs unicode/emoji input, or runs existing Maestro flows (`maestro-cli` for the latter). `maestro-mcp` on Android is 3–7 s per tap |
| ios | `maestro-mcp` when Maestro is installed — the simulator has no native tap command. 0.9–3.6 s per tap, 180 ms per `inspect_screen`, 2.3 s for a 7-step flow. **One live `maestro-mcp` lane per platform** (fixed driver port) | Maestro CLI ≥ 2.11, Java 17+ | `axe` (brew, single binary, no Java, no daemon, no port limit) when the user approves it: the way to run a second iOS lane, or to run iOS without Maestro at all. If neither Maestro nor AXe is installed, iOS lanes are blocked until the user picks one |
| web | `chrome` — Claude in Chrome, the native integration of Claude Code: worker started with `--chrome`, no MCP server, no install. Drives the user's real Chrome and profile (logged-in state included). **One Chrome lane at a time** (every session shares one tab group). Desktop viewport only (`resize_window`; no device emulation) | Chrome running, extension installed and signed in to the same claude.ai org, direct Anthropic plan (not Bedrock/Vertex), `/login` session | `playwright-mcp` when the user approves `npx -y @playwright/mcp@latest`: isolated profile per lane (parallel web lanes), `--device`/`--viewport-size` for the 375×667 mobile-web pass, headless. Never the default |
| api | `http` (Bash `curl`) | curl | – |

Second lane of the same platform: Android → another `adb` lane (another AVD). iOS → an `axe` lane (approved install) or, without AXe, suites that only run existing flow files with `maestro-cli` (one CLI invocation per flow set, never per step: each costs 9–22 s). Web → a `playwright-mcp` lane (approved install); without it, web suites run one after the other on the Chrome lane.

Device-level helpers (`xcrun simctl`, `adb` setup commands below) are always available and never count as a driver.

## Maestro CLI

- Install (only with the user's approval): `curl -fsSL "https://get.maestro.mobile.dev" | bash`, or `brew tap mobile-dev-inc/tap && brew install mobile-dev-inc/tap/maestro`. Requires Java 17+ (`java -version`, `JAVA_HOME` set) and Xcode with the Command Line Tools.
- Verify: `maestro --version`.
- Physical iOS devices are **not supported**. Use iOS simulators, or physical Android devices.
- Run flows on one device: `maestro --device <udid|serial> test <flow-or-dir> --format junit --output <run-dir>/<suite>.junit.xml --test-output-dir <evidence-dir>/maestro --debug-output <evidence-dir>/maestro-debug`.
  - Tags: `--include-tags smoke,login` / `--exclude-tags wip` (comma-separated, OR logic).
  - Variables: `-e KEY=VALUE`. Shell variables named `MAESTRO_*` are passed automatically. Pass credentials as `-e EMAIL="$TEST_USER_EMAIL"` inside the same Bash command that sourced `.env`.
- Separate `maestro test --device X` processes pick free driver ports. **One CLI process per lane** is the parallel model. Sharding (`--shard-split` / `--shard-all`) spreads one flow set over several devices from one process; use it only when a single suite owns several lanes.
- `maestro start-device --platform ios|android [--device-model …] [--device-os iOS-18-2|android-34] [--device-locale es_AR]` creates and boots a Maestro-managed device. `maestro list-devices` shows the accepted values. Prefer the simctl/emulator commands below for devices that already exist.
- `maestro hierarchy [--compact]` prints the current screen tree. Costs 5–16 s per call (new JVM + driver each time), like every `maestro test`: never use the CLI for one tap or one look. The MCP keeps the driver alive.

### Flow YAML (minimum)

```yaml
appId: com.company.app
tags: [smoke]
---
- launchApp:
    clearState: true
- tapOn: "Iniciar sesión"
- inputText: ${EMAIL}
- assertVisible: "Bienvenido"
- takeScreenshot: 03-home        # saved relative to the working dir or --test-output-dir
```

`runFlow: { file: sub.yaml, env: { ROLE: admin } }` composes flows. `onFlowStart` / `onFlowComplete` are hooks. If `onFlowStart` fails, the body is skipped.

## Maestro MCP

- Server: `maestro mcp` (stdio). Flags: `--working-dir <dir>`, `--no-viewer`, `--viewer-port <n>`.
- Personal registration (for the orchestrator or interactive use): `claude mcp add maestro --scope user -- maestro mcp`.
- Tools (2.11.0):

  | Tool | Parameters | Use |
  |---|---|---|
  | `list_devices` | – | ids, names, platform, connected. Also lists `chromium` (web beta) |
  | `inspect_screen` | `device_id` | Current screen as compact JSON: texts, ids, accessibility labels, bounds |
  | `take_screenshot` | `device_id` | JPEG of the screen (≤ 2000 px). Returns the image to the session; it does not write a file |
  | `run` | `device_id` + one of `yaml` (inline flow string) · `files` (array) · `dir` (+ `include_tags` / `exclude_tags`); optional `env` map | Every interaction. Taps, typing, back and swipes are short inline flows, e.g. `yaml: "appId: com.company.app\n---\n- tapOn: \"Reservar\""` |
  | `cheat_sheet` | – | Maestro command syntax |
  | `open_maestro_viewer` | – | Opens the viewer UI |

  Removed in 2026 (do not plan around them): `start_device`, `launch_app`, `tap_on`, `input_text`, `back`, `stop_app`, `check_flow_syntax`, `query_docs`, `inspect_view_hierarchy`, `run_flow`, `run_flow_files`. **The MCP cannot boot devices.** The orchestrator boots them before dispatch.
- **Saving evidence from the MCP.** `take_screenshot` returns an image, not a file. A worker that needs a file at the moment of discovery runs, in the same step, either `run` with `yaml: "appId: <id>\n---\n- takeScreenshot: <evidence-dir>/07-<what>"`, or Bash `xcrun simctl io <udid> screenshot <evidence-dir>/07-<what>.png` / `adb -s <serial> exec-out screencap -p > <evidence-dir>/07-<what>.png`.
- **Port limit (from Maestro source and issue #3611).** The MCP session manager uses fixed driver ports, 22087 for iOS and 7001 for Android: a second MCP session of the same platform reuses the first session's runner and can read or tap the wrong device. Rule: at most **one live `maestro-mcp` lane per platform**. Further Android lanes use `adb`; further iOS lanes use `axe` (approved install) or `maestro-cli` for existing flow files. The preflight may lift this rule only after a real two-session test, recorded as a D-number.
- **Speed.** Measured 2026-10-15: `inspect_screen` 180 ms (iOS) / 600 ms (Android); `run` with one `tapOn` 0.9–3.6 s (iOS) / 3–7 s (Android); a 7-step flow in one `run` 2.3 s (iOS) / 16 s (Android); `take_screenshot` 1 s and 160–200 KB inline. Batching every step of a scenario into one `run`, and verifying with `assertVisible` instead of screenshots, is what makes a Maestro lane fast (`driver-protocol.md`).

## AXe (iOS simulator, optional)

- Single-binary CLI over Apple's accessibility and HID APIs (built on a pinned IDB revision), MIT, iOS simulators only, macOS 14+, Xcode 26/27. No daemon, no Java, no port: several simulators at once, one `--udid` per call.
- Install (only with the user's approval): `brew install cameroncooke/axe/axe`. Verify: `axe --help`, `axe list-simulators`.
- Commands: `describe-ui` (JSON accessibility tree, `--point x,y`), `tap` (`--id`, `--label`, `--value`, `-x -y`, `--wait-timeout`), `type`, `key`, `key-sequence`, `key-combo`, `swipe`, `gesture scroll-down|scroll-up|edge-swipe`, `touch`, `button home|lock`, `slider`, `screenshot --output`, `record-video`, `batch --step … --step …` (interaction steps in one HID session). Full reference: `axe-cli.com/docs/command-reference`.
- Worker usage and the per-step batching recipe: `driver-protocol.md § axe`.

## Claude in Chrome (web, native)

- Built into Claude Code: `claude --chrome …` (or `CLAUDE_CODE_ENABLE_CFC=1` in the worker's shell; `--no-chrome` to disable). Needs the "Claude in Chrome" extension (≥ 1.0.36, Chrome Web Store id `fcoeoabgfenejglbffodgkkbkcdhcgfn`) in a running Chrome signed in to the same claude.ai organisation, and a `/login` session on a direct Anthropic plan. Not on Bedrock/Vertex/Foundry, not headless, not WSL.
- Verified 2026-10-15 on Claude Code 2.1.301: the tools survive `--strict-mcp-config --mcp-config '{"mcpServers":{}}'`, and are listed in `-p` sessions. Server name `claude-in-chrome`; tools `navigate`, `find`, `read_page`, `get_page_text`, `form_input`, `computer`, `browser_batch`, `tabs_context_mcp`, `tabs_create_mcp`, `tabs_close_mcp`, `resize_window`, `read_console_messages`, `read_network_requests`, `javascript_tool`, `file_upload`, `upload_image`, `gif_creator`, `list_connected_browsers`, `select_browser`, `switch_browser`, `shortcuts_list`, `shortcuts_execute`. Deferred: the worker loads them with ToolSearch.
- Limits that shape the plan: it is the **user's profile** (their cookies and logins; a QA account must be logged in by the worker in its own tab, and the user sees every tab); **one tab group shared by every session**, so one Chrome lane at a time; **no device emulation**, so mobile-web viewports go to `playwright-mcp` or are N/A; per-site permissions of the extension apply (the user pre-allows the QA domains in the extension settings, or an unattended worker stalls); JavaScript dialogs block the tools.
- Evidence: the screenshot action has a save-to-disk option (Claude Code ≥ 2.1.211) that reports the file path; the worker moves or copies it into the evidence dir.

### Worker MCP config

Workers start with `--strict-mcp-config --mcp-config <run-dir>/mcp-<lane>.json`. They get only their lane's driver: no ClickUp, no vault, no other servers.

`maestro-mcp` lane (`mcp-L1-ios.json`):

```json
{ "mcpServers": { "maestro": { "command": "maestro", "args": ["mcp", "--no-viewer", "--working-dir", "<QA project root>"] } } }
```

`adb` lane, `axe` lane, `http` lane, `maestro-cli` lane: `{ "mcpServers": {} }`. They work through Bash and hold no MCP driver.

`chrome` lane: `{ "mcpServers": {} }` **plus the `--chrome` flag** in the `herdr agent start` command. The Chrome tools are built in, not an MCP config entry; `--strict-mcp-config` keeps them.

`playwright-mcp` lane (`mcp-L3-web.json`), only when the user approved the install. `--isolated` gives each worker its own in-memory browser profile, so two web lanes never share cookies:

```json
{ "mcpServers": { "playwright": { "command": "npx", "args": ["-y", "@playwright/mcp@latest", "--isolated", "--viewport-size", "1440,900", "--output-dir", "<evidence dir of the suite>"] } } }
```

Check the flags with `npx -y @playwright/mcp@latest --help` at preflight.

`--viewport-size` follows the plan's web viewport scope:
- **Desktop:** `1440,900`.
- **Mobile web:** `375,667`.
- **Both:** `1440,900`. For the mobile pass, the worker calls `browser_resize` to 375×667, repeats the in-scope checks, takes screenshots per viewport, and reports responsiveness issues per viewport. The plan's Worker environment says which applies.

`--viewport-size` applies to Playwright only. A `chrome` lane resizes the real window with `resize_window` to the desktop size and cannot do the mobile pass.

## Expo / React Native builds

Tests should not depend on a Metro bundler running on the Mac. Prefer standalone builds:
- iOS simulator `.app`: an EAS build profile with `"ios": { "simulator": true }` (`eas build -p ios --profile <profile>`, then unpack the `.tar.gz`), or `npx expo run:ios --configuration Release` (the `.app` lands under `ios/build/…/Release-iphonesimulator/`).
- Android `.apk`: an EAS profile with `"android": { "buildType": "apk" }`, or `npx expo run:android --variant release`.

With a dev client instead, one Metro (port 8081) serves several simulators, but the app is only as stable as Metro. Record that as a decision, and a Metro restart blocks every lane.

## iOS simulators (Xcode)

| Need | Command |
|---|---|
| List | `xcrun simctl list devices available` (`-j` for JSON) |
| Boot and wait | `xcrun simctl boot <udid>; xcrun simctl bootstatus <udid> -b` |
| Show the window | `open -a Simulator` |
| Create another lane's device | `xcrun simctl create "QA L4 iPhone SE" "iPhone SE (3rd generation)" <runtime-id>` (runtime ids: `xcrun simctl list runtimes`), or `xcrun simctl clone <udid> "<new name>"` on a shut-down device |
| Install / launch / uninstall | `xcrun simctl install <udid> <App.app>` · `xcrun simctl launch <udid> <bundle id>` · `xcrun simctl uninstall <udid> <bundle id>` |
| Screenshot | `xcrun simctl io <udid> screenshot <file>.png` |
| Record video | `xcrun simctl io <udid> recordVideo <file>.mp4` (Ctrl-C to stop) |
| Deep link | `xcrun simctl openurl <udid> "<scheme>://path"` |
| Dark mode / font size | `xcrun simctl ui <udid> appearance dark` · `xcrun simctl ui <udid> content_size extra-extra-large` |
| Permissions | `xcrun simctl privacy <udid> grant|revoke|reset <service> <bundle id>` |
| Push | `xcrun simctl push <udid> <bundle id> <payload>.json` |
| Locale | Set at creation, or with `maestro start-device --device-locale`. Otherwise via the Settings app |
| Logs / crashes | `xcrun simctl spawn <udid> log show --last 10m --predicate 'process == "<AppName>"'` |
| Shut down | `xcrun simctl shutdown <udid>` (never `erase` without the user's OK) |

Always pass the UDID, never `booted`, once more than one simulator is running.

## Android emulators (Android Studio)

| Need | Command |
|---|---|
| List AVDs / devices | `emulator -list-avds` · `adb devices` |
| Boot and wait | `emulator -avd <name> -port <even 5554–5682> -no-snapshot-load -no-audio &` then `adb -s emulator-<port> wait-for-device` and poll `adb -s emulator-<port> shell getprop sys.boot_completed` until `1` |
| Same AVD twice | Add `-read-only` to the second instance; better, create a second AVD |
| Create an AVD | `avdmanager create avd -n QA_L5_Pixel -k "system-images;android-34;google_apis;arm64-v8a"` (`avdmanager` lives in `$ANDROID_HOME/cmdline-tools/latest/bin`) |
| Install / launch / clear | `adb -s <serial> install -r <app>.apk` · `adb -s <serial> shell monkey -p <package> 1` · `adb -s <serial> shell pm clear <package>` |
| Screenshot | `adb -s <serial> exec-out screencap -p > <file>.png` |
| Record video | `adb -s <serial> shell screenrecord /sdcard/qa.mp4` then `adb -s <serial> pull /sdcard/qa.mp4` |
| Deep link | `adb -s <serial> shell am start -W -a android.intent.action.VIEW -d "<scheme>://path"` |
| Dark mode / font scale | `adb -s <serial> shell cmd uimode night yes` · `adb -s <serial> shell settings put system font_scale 1.3` |
| Animations off (preflight, every Android lane) | `for k in window_animation_scale transition_animation_scale animator_duration_scale; do adb -s <serial> shell settings put global $k 0; done` — `uiautomator dump` drops from 2.1 s to 0.5 s and Maestro settles faster. Restore with `1` at closing if the device is not shut down |
| Read the screen / tap / type (the `adb` driver) | `driver-protocol.md § adb` |
| Free the device for `uiautomator dump` | `adb -s <serial> shell am force-stop dev.mobile.maestro` — Maestro's on-device driver holds the only UiAutomation connection; while it lives, every dump is `Killed` (exit 137). Run it before an `adb` lane starts on a device Maestro has used |
| Network | `adb -s <serial> shell svc wifi disable` + `svc data disable` (offline) · `adb -s <serial> emu network speed gsm` |
| Permissions | `adb -s <serial> shell pm grant|revoke <package> <permission>` |
| Cold start | `adb -s <serial> shell am start -W -n <package>/<activity>` (TotalTime) |
| Crashes / logs | `adb -s <serial> logcat -b crash -d` · `adb -s <serial> logcat -d -t 500` |
| Shut down | `adb -s <serial> emu kill` |

**Always pass `-s <serial>` to `adb`.** With two emulators running, a bare `adb` command fails or hits the wrong device.

## Resource budget (rule of thumb)

Rough RAM costs:
- Android emulator: about 2–4 GB, plus 2 cores.
- iOS simulator: about 1–2 GB.
- Claude worker: about 0.5 GB.
- Maestro JVM: about 0.5–1 GB per session (none on `adb` / `axe` lanes).
- Playwright browser: about 0.5–1 GB (a `chrome` lane uses the Chrome already open).

On a 16 GB Mac, plan at most 4 devices in total, and no more than 2 of them Android emulators. Before adding a lane, check that memory pressure is green with `memory_pressure` or Activity Monitor. A third simulator next to an emulator is a decision to test on the actual machine, not a default.

## Herdr and Claude

- `herdr pane split --pane <id> --direction right|down --cwd <dir> --no-focus` → read `.result.pane.pane_id`.
- `herdr agent start <name> --kind claude --pane <pane> --timeout 120000 -- <claude flags>`.
- `herdr agent prompt <name> "<text>" --wait --timeout 3600000`; `herdr agent read <name> --source visible`; `herdr agent list`; `herdr agent wait <name> --timeout …`.
- Claude flags used: `--model`, `--permission-mode`, `--add-dir`, `--strict-mcp-config`, `--mcp-config`, `-n`, and `--chrome` on `chrome` lanes only.
