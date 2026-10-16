# Driver protocol (how a worker drives its device fast)

`make-package.sh` appends `## Common` and the section of each tool named in the suite's `**Tool:**` field to every package. Latencies below were measured on a 16 GB M2 Pro Mac, Pixel_8_API_34 emulator and iPhone 16 Pro simulator (iOS 18.2), Maestro 2.11.0, Claude Code 2.1.3xx, 2026-10-15. Re-measure when something looks off; do not trust them blindly.

## Common

The slow part of a test is not the device: it is the number of model turns and the bytes that come back from each one. One action per turn with a screenshot after it costs 10–20 s and 150–250 KB of context per step. Work by screens, not by taps.

1. **Look once per screen, then act from the tree.** Read the hierarchy with your driver's inspect command (`adb` dump, Maestro `inspect_screen`, AXe `describe-ui`, Chrome `find` / `read_page`). Tap by the text, id or label it shows, or by the centre of the bounds it gives. Never estimate coordinates from a screenshot.
2. **Batch a whole scenario step into one call** when no decision is needed between actions: a Maestro `run` with several commands, an AXe `batch`, one Bash command with several `adb` lines, Chrome `browser_batch`. The ceiling is one tool call per scenario row of the plan; the norm is fewer.
3. **Verify by text, not by eye.** An expected text is checked with an assertion or a `grep` on the tree (Maestro `assertVisible` ≈ 150 ms, `grep` on an `adb` dump ≈ 0 ms, AXe `describe-ui`, Chrome `find`). The hierarchy is the proof for the report when the check is textual; it costs 7–10 KB, a screenshot costs 150–250 KB.
4. **Evidence is a file, not an inline image.** Write screenshots straight to the evidence directory (`takeScreenshot:` inside the flow, `screencap -p > file`, `axe screenshot --output`, `simctl io screenshot`, the Chrome screenshot tool's save-to-disk option). Look at an image (Read, or a tool that returns it inline) only when the check is visual: `ui-visual`, `text-quality` per screen, dark mode, an anomaly the tree does not explain. In every other strategy: at most one inline image per scenario, and never after every tap.
5. **Never pay a process start per step.** `maestro test` costs 9–22 s per invocation (JVM + driver install) and `maestro hierarchy` 5–16 s: use the CLI only to run whole existing flow files, never for one tap. The Maestro MCP, `adb`, AXe and Chrome keep their driver alive between calls.
6. **Settle time is yours to bound.** The orchestrator turns off animations at preflight (`adb shell settings put global *_animation_scale 0`); check it is still off if taps feel slow. In Maestro, a tap followed by an assertion can take `waitToSettleTimeoutMs: 200`, because the assertion already waits for the text.
7. **Reset state without a reinstall:** `adb shell pm clear <package>`, `xcrun simctl terminate <udid> <bundle>` then `launch`, `launchApp: { clearState: true }` in Maestro, a new tab in Chrome.
8. **Three calls on one step without progress means stop and inspect.** Re-read the tree, check the device id, check the app is in the foreground (`adb shell dumpsys window | grep mCurrentFocus`, Maestro `inspect_screen`). Do not retry blindly and do not script around the driver.
9. **Do not install anything.** A missing tool, port or permission is `STATUS: BLOCKED` with its name. Installs are the user's decision, made at planning or preflight.

Measured, per action (warm driver): `adb input tap` 41 ms · `adb exec-out screencap` 190 ms · `adb uiautomator dump` 540 ms with animations off, 2.1 s with them on · Maestro MCP `inspect_screen` 180 ms (iOS) / 600 ms (Android) · Maestro MCP `run` with one `tapOn` 0.9–3.6 s (iOS) / 3–7 s (Android) · Maestro MCP 7-step flow 2.3 s (iOS) / 16 s (Android) · Maestro MCP `take_screenshot` 1 s and 160–200 KB inline · `simctl io screenshot` 270 ms · `maestro test <file>` 9–22 s per invocation.

## adb

Android lane with no Maestro. Everything goes through Bash, always `adb -s <serial>`. Serial, package and evidence dir come from your package header.

**Shell state does not persist between Bash calls.** Paste these two lines at the top of every call; do not save them as a script file (driver scripts are not allowed):

```bash
S=<serial>; D=<evidence-dir>; mkdir -p "$D"
look(){ adb -s $S shell uiautomator dump --compressed /sdcard/ui.xml >/dev/null && adb -s $S pull /sdcard/ui.xml "$D/$1.xml" >/dev/null 2>&1 && grep -o '<node [^>]*>' "$D/$1.xml" | sed -E 's/.*text="([^"]*)".*content-desc="([^"]*)".*bounds="([^"]*)".*/\1|\2|\3/' | grep -v '^||'; }
```

`look 02-home` saves the tree as `$D/02-home.xml` (evidence) and prints one `text|content-desc|bounds` line per visible node, 1–3 KB instead of the 10–25 KB XML. Tap the centre of a node's `bounds="[x1,y1][x2,y2]"`: `((x1+x2)/2, (y1+y2)/2)`.

| Need | Command |
|---|---|
| Launch (main activity) | `A=$(adb -s $S shell cmd package resolve-activity --brief -c android.intent.category.LAUNCHER <package> \| tail -1); adb -s $S shell am start -W -n "$A"` — `monkey -p <package> 1` may open a different exported activity |
| Stop / clear / deep link | `adb -s $S shell am force-stop <package>` · `adb -s $S shell pm clear <package>` · `adb -s $S shell am start -W -a android.intent.action.VIEW -d "<url>"` |
| Tap / long press | `adb -s $S shell input tap X Y` · `adb -s $S shell input swipe X Y X Y 800` (long press = swipe in place) |
| Type | `adb -s $S shell input text 'hello%sworld'` (`%s` is a space; ASCII only: accents and emoji are a gap of this driver, plan them on a `maestro-mcp` lane or report N/A with the reason) |
| Keys | `adb -s $S shell input keyevent 4` (BACK) · `3` (HOME) · `66` (ENTER) · `67` (DEL) · `82` (MENU/unlock) |
| Swipe / scroll | `adb -s $S shell input swipe 540 1500 540 600 300` (down the list) |
| Foreground app | `adb -s $S shell dumpsys window \| grep mCurrentFocus` (140 ms) |
| Screenshot to file | `adb -s $S exec-out screencap -p > "$D/NN-<what>.png"` |
| Crashes / logs | `adb -s $S logcat -b crash -d` · `adb -s $S logcat -d -t 300 \| grep -i -E 'fatal\|exception\|anr'` |
| Text appeared? | `look 03-after \| grep -c 'Welcome'`; wait at most 5 × 1 s |

One Bash call holds a whole scenario step, and its output is the proof for the report:

```bash
S=emulator-5554; D=evidence/app/S-001-smoke/run-1; mkdir -p "$D"
look(){ …as above…; }
adb -s $S shell input tap 407 863; sleep 1
look 02-network | grep -i 'internet' || echo "MISSING: Internet"
adb -s $S exec-out screencap -p > "$D/02-network.png"
```

**`uiautomator dump` prints `Killed` (exit 137):** a Maestro driver is still running on the device and holds its only UiAutomation connection (process `dev.mobile.maestro`). Run `adb -s $S shell am force-stop dev.mobile.maestro` once and retry; this is the one exception to "do not fix the driver yourself", because the process belongs to your own lane's device. If the dump is still killed, BLOCKED.

## maestro-mcp

Tools `list_devices`, `inspect_screen`, `take_screenshot`, `run` (`device_id` + `yaml` / `files` / `dir`), `cheat_sheet`. Always pass `device_id`.

- One `run` per scenario step, with every command of the step inside, and the evidence saved by the flow itself:

  ```yaml
  appId: com.company.app
  ---
  - tapOn:
      text: "Reservar"
      waitToSettleTimeoutMs: 200
  - assertVisible: "Elegí una fecha"
  - takeScreenshot: evidence/<app>/S-002-reservas/<run-id>/03-fecha
  - back
  ```

  The result text says whether every command passed; a failed `assertVisible` names the missing text. That line is the proof for a PASS.
- `inspect_screen` once per new screen (180–600 ms, 7–10 KB). Not after every command.
- `take_screenshot` returns 160–200 KB inline and writes nothing: use it only for a visual judgement. For files, `takeScreenshot:` inside the flow (path relative to the working dir, `.png` added).
- Existing flow files run whole: `run` with `files: [...]` or `dir` + tags.
- `back` is Android-only. On iOS, go back by tapping the navigation bar's back label (the previous screen's title, from `inspect_screen`) or with `- swipe: { start: "1%,50%", end: "60%,50%" }`.
- `Device became unreachable during viewHierarchy` on iOS is the XCTest runner restarting: wait 5 s and retry the same `run` once. If it fails again, screenshot with `xcrun simctl io <udid> screenshot` and report BLOCKED; the orchestrator restarts the driver.
- A port or driver error while another Maestro MCP lane of the same platform is live is the port limit: report BLOCKED with the message; the orchestrator sequences the lanes.

## axe

iOS lane driven by the AXe CLI (installed only by the user's decision). Everything goes through Bash with `--udid <udid>`.

| Need | Command |
|---|---|
| Read the screen | `axe describe-ui --udid U` (JSON tree with labels, identifiers, frames; `--point x,y` for one element) |
| Tap | `axe tap --label "Iniciar sesión" --udid U` · `--id <accessibilityIdentifier>` · `-x X -y Y` as a last resort · `--wait-timeout 5` polls for the element |
| Type / keys | `axe type 'hello' --udid U` (US keyboard characters) · `axe key 40 --udid U` (return) · `axe key-sequence --keycodes 42,42 --udid U` (backspace ×2) |
| Swipe / scroll | `axe gesture scroll-down --udid U` · `axe swipe --start-x --start-y --end-x --end-y --udid U` |
| Hardware | `axe button home --udid U` |
| Batch a step | `axe batch --udid U --step "tap --label Email" --step "type 'qa@x.com'" --step "key 40"` (interaction steps only; `describe-ui` and `screenshot` stay separate) |
| Screenshot to file | `axe screenshot --output <evidence-dir>/NN-<what>.png --udid U` (or `xcrun simctl io U screenshot <file>`) |
| Launch / stop / deep link | `xcrun simctl launch U <bundle>` · `xcrun simctl terminate U <bundle>` · `xcrun simctl openurl U "<url>"` |
| Logs / crashes | `xcrun simctl spawn U log show --last 5m --predicate 'process == "<AppName>"'` |

Text appeared? `axe describe-ui --udid U | grep -c '"<text>"'`.

## chrome

Web lane driven by Claude in Chrome (the session was started with `--chrome`; the tools are `mcp__claude-in-chrome__*`, loaded with ToolSearch when deferred). It drives the user's real Chrome and profile: the user is already logged in where they are logged in, and your tabs are visible to them.

- **Driver check:** `list_connected_browsers` lists a browser, then `tabs_context_mcp` with `createIfEmpty` gives you your tab group. Work only in tabs you created; never close or use the user's other tabs.
- **Look:** `find` (natural-language element lookup) and `read_page` / `get_page_text` for the DOM text. Act with `navigate`, `form_input`, `computer` (click, type, scroll, screenshot), `browser_batch` for a whole step.
- **Verify** with `find` / `get_page_text`, not screenshots. **Console and network** at the end of each scenario with `read_console_messages` and `read_network_requests` (evaluation standard § 7).
- **Evidence:** the screenshot action with its save-to-disk option, moved or named into the evidence dir; check the tool schema (ToolSearch) for the exact parameter at your first screenshot.
- **Viewport:** `resize_window` to the plan's desktop size. There is no device emulation: a `375×667` mobile-web pass is not possible on this driver (Chrome windows do not shrink below about 500 px). Report such scenarios as `N/A (driver)`; the plan puts them on a `playwright-mcp` lane when the user approved one.
- **One Chrome lane at a time.** Every Claude Code session shares one tab group in the extension; a second web worker would act in your tabs. A JavaScript dialog (alert/confirm) blocks the tools: dismiss it through `computer` and note it.
- Pages that ask for a login the profile does not have, or a CAPTCHA, are BLOCKED with the URL; the user handles them.

## playwright-mcp

Opt-in web lane (the user approved `npx -y @playwright/mcp@latest`). Isolated profile, so nothing is logged in: log in with the lane's account. `browser_navigate`, `browser_snapshot` (accessibility tree, the thing to read), `browser_click` / `browser_type` / `browser_fill_form` by `ref` from the snapshot, `browser_take_screenshot` with `filename` into the output dir, `browser_console_messages`, `browser_network_requests`, `browser_resize` for the viewport scope. One snapshot per page state, not per click; screenshots only as evidence.

## maestro-cli

Only for running flow files that already exist (`maestro --device <id> test <dir-or-file> --format junit --output <run-dir>/<suite>.junit.xml --test-output-dir <evidence-dir>/maestro`), one invocation per flow set, never one per step. Read results from the junit file and the screenshots Maestro saved. Writing new flows on this lane means reading screens with `maestro hierarchy` at 5–16 s each: plan that time, or use the lane's interactive driver (`adb` / `maestro-mcp` / `axe`) to write the flow, then run it once with the CLI.

## http

No device. Bash `curl` per the evaluation standard § 12. Batch related requests in one Bash call; print status and the fields you assert, never credentials.
