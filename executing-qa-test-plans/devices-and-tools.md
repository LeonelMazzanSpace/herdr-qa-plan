# Devices and tools reference

Checked against Maestro CLI 2.11.0 (2026-09-29), herdr 0.9.1 and Claude Code 2.1.x. Tool names drift between versions. Re-check against the installed `--help` and the tools a session actually lists before trusting this file.

## Maestro CLI

- Install (only with the user's approval): `curl -fsSL "https://get.maestro.mobile.dev" | bash`, or `brew tap mobile-dev-inc/tap && brew install mobile-dev-inc/tap/maestro`. Requires Java 17+ (`java -version`, `JAVA_HOME` set) and Xcode with the Command Line Tools.
- Verify: `maestro --version`.
- Physical iOS devices are **not supported**. Use iOS simulators, or physical Android devices.
- Run flows on one device: `maestro --device <udid|serial> test <flow-or-dir> --format junit --output <run-dir>/<suite>.junit.xml --test-output-dir <evidence-dir>/maestro --debug-output <evidence-dir>/maestro-debug`.
  - Tags: `--include-tags smoke,login` / `--exclude-tags wip` (comma-separated, OR logic).
  - Variables: `-e KEY=VALUE`. Shell variables named `MAESTRO_*` are passed automatically. Pass credentials as `-e EMAIL="$TEST_USER_EMAIL"` inside the same Bash command that sourced `.env`.
- Separate `maestro test --device X` processes pick free driver ports. **One CLI process per lane** is the parallel model. Sharding (`--shard-split` / `--shard-all`) spreads one flow set over several devices from one process; use it only when a single suite owns several lanes.
- `maestro start-device --platform ios|android [--device-model …] [--device-os iOS-18-2|android-34] [--device-locale es_AR]` creates and boots a Maestro-managed device. `maestro list-devices` shows the accepted values. Prefer the simctl/emulator commands below for devices that already exist.
- `maestro hierarchy [--compact]` prints the current screen tree.

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
- **Port limit (unverified at runtime, from Maestro source).** The MCP session manager uses fixed driver ports, 22087 for iOS and 7001 for Android. Two MCP sessions driving two devices **of the same platform** at the same time will probably collide. Rule: at most **one live `maestro-mcp` lane per platform**. Further lanes of the same platform run `maestro-cli` suites. The preflight may lift this rule only after a real two-session test, recorded as a D-number.

### Worker MCP config

Workers start with `--strict-mcp-config --mcp-config <run-dir>/mcp-<lane>.json`. They get only their lane's driver: no ClickUp, no vault, no other servers.

Mobile lane (`mcp-L1-ios.json`):

```json
{ "mcpServers": { "maestro": { "command": "maestro", "args": ["mcp", "--no-viewer", "--working-dir", "<QA project root>"] } } }
```

Web lane (`mcp-L3-web.json`). `--isolated` gives each worker its own in-memory browser profile, so two web lanes never share cookies:

```json
{ "mcpServers": { "playwright": { "command": "npx", "args": ["-y", "@playwright/mcp@latest", "--isolated", "--viewport-size", "1440,900", "--output-dir", "<evidence dir of the suite>"] } } }
```

Check the flags with `npx -y @playwright/mcp@latest --help` at preflight.

`--viewport-size` follows the plan's web viewport scope:
- **Desktop:** `1440,900`.
- **Mobile web:** `375,667`.
- **Both:** `1440,900`. For the mobile pass, the worker calls `browser_resize` to 375×667, repeats the in-scope checks, takes screenshots per viewport, and reports responsiveness issues per viewport. The plan's Worker environment says which applies.

Lane running a `maestro-cli` suite (`mcp-L4-ios.json`): `{ "mcpServers": {} }`. The worker reads screens with `maestro --device <id> hierarchy` and acts through `maestro --device <id> test`. It holds no MCP driver port, so it can run beside an MCP lane of the same platform.

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
- Maestro JVM: about 0.5–1 GB per session.
- Playwright browser: about 0.5–1 GB.

On a 16 GB Mac, plan at most 4 devices in total, and no more than 2 of them Android emulators. Before adding a lane, check that memory pressure is green with `memory_pressure` or Activity Monitor. A third simulator next to an emulator is a decision to test on the actual machine, not a default.

## Herdr and Claude

- `herdr pane split --pane <id> --direction right|down --cwd <dir> --no-focus` → read `.result.pane.pane_id`.
- `herdr agent start <name> --kind claude --pane <pane> --timeout 120000 -- <claude flags>`.
- `herdr agent prompt <name> "<text>" --wait --timeout 3600000`; `herdr agent read <name> --source visible`; `herdr agent list`; `herdr agent wait <name> --timeout …`.
- Claude flags used: `--model`, `--permission-mode`, `--add-dir`, `--strict-mcp-config`, `--mcp-config`, `-n`.
