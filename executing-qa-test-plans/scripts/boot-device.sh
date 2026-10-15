#!/usr/bin/env bash
# Boots one lane's device, waits until it is ready, and optionally installs the build.
# Prints `booted-by-this-run: yes|no` on stderr and the device id to pass to Maestro
# (`device_id` / `--device`) as the last stdout line.
#
# Usage:
#   bash boot-device.sh --platform ios --udid <udid> [--app <path/App.app>]
#   bash boot-device.sh --platform android --avd <AVD name> [--port 5554] [--app <path/app.apk>] [--read-only]
#
# iOS: boots the simulator if it is shut down (or waits if it is already booting),
#   waits for bootstatus, opens Simulator.app. --app must be a simulator build
#   (a .app directory), not an .ipa.
# Android: starts the emulator on the given even console port (serial emulator-<port>)
#   unless that serial is already online with the same AVD, waits up to 6 minutes for
#   sys.boot_completed, and unlocks the screen. Emulator log: $TMPDIR/qa-emulator-<port>.log.
# Never erases, wipes or shuts down anything.
set -euo pipefail

die() { printf 'boot-device: %s\n' "$1" >&2; exit 1; }

PLATFORM= UDID= AVD= PORT=5554 APP= READ_ONLY=
while [ $# -gt 0 ]; do
  case $1 in
    --read-only) READ_ONLY=1; shift; continue ;;
  esac
  [ $# -ge 2 ] || die "missing value for $1"
  case $1 in
    --platform) PLATFORM=$2 ;; --udid) UDID=$2 ;; --avd) AVD=$2 ;;
    --port) PORT=$2 ;; --app) APP=$2 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift 2
done
[ -z "$APP" ] || [ -e "$APP" ] || die "build not found: $APP"

boot_ios() {
  [ -n "$UDID" ] || die "--udid is required for ios"
  command -v xcrun >/dev/null || die "xcrun not found (install Xcode Command Line Tools)"
  command -v jq >/dev/null || die "jq not found (brew install jq)"
  if [ -n "$APP" ]; then
    case $APP in *.app|*.app/) [ -d "$APP" ] || die "--app must be a simulator .app directory: $APP" ;;
      *) die "--app for ios must be a simulator build (.app), not $APP" ;; esac
  fi
  state=$(xcrun simctl list devices -j | jq -r --arg u "$UDID" '.devices[][] | select(.udid == $u) | .state')
  [ -n "$state" ] || die "no simulator with udid $UDID (xcrun simctl list devices available)"
  case $state in
    Shutdown) xcrun simctl boot "$UDID"; printf 'booted-by-this-run: yes\n' >&2 ;;
    Booting) printf 'booted-by-this-run: no (was already booting)\n' >&2 ;;
    Booted) printf 'booted-by-this-run: no\n' >&2 ;;
    *) die "simulator $UDID is in state '$state'; resolve it by hand" ;;
  esac
  xcrun simctl bootstatus "$UDID" -b >/dev/null
  open -a Simulator --args -CurrentDeviceUDID "$UDID"
  if [ -n "$APP" ]; then
    xcrun simctl install "$UDID" "$APP"
    printf 'installed %s\n' "$APP" >&2
  fi
  printf '%s\n' "$UDID"
}

adb_state() { adb devices | awk -v s="$1" '$1 == s { print $2 }'; }

boot_android() {
  [ -n "$AVD" ] || die "--avd is required for android"
  case $PORT in *[!0-9]*|'') die "--port must be a number" ;; esac
  [ $((PORT % 2)) -eq 0 ] && [ "$PORT" -ge 5554 ] && [ "$PORT" -le 5682 ] || die "--port must be even, 5554–5682"
  case $APP in ''|*.apk) ;; *) die "--app for android must be an .apk: $APP" ;; esac
  SDK=${ANDROID_HOME:-${ANDROID_SDK_ROOT:-$HOME/Library/Android/sdk}}
  EMULATOR=$(command -v emulator || printf '%s' "$SDK/emulator/emulator")
  [ -x "$EMULATOR" ] || die "emulator not found (set ANDROID_HOME)"
  command -v adb >/dev/null || die "adb not found"
  "$EMULATOR" -list-avds | grep -qx "$AVD" || die "no AVD named $AVD (emulator -list-avds)"
  SERIAL="emulator-$PORT"
  state=$(adb_state "$SERIAL")
  case $state in
    device)
      running=$(adb -s "$SERIAL" emu avd name 2>/dev/null | head -1 | tr -d '\r')
      [ "$running" = "$AVD" ] || die "$SERIAL is already running AVD '$running', not $AVD: pick another --port"
      printf 'booted-by-this-run: no\n' >&2 ;;
    '')
      LOG="${TMPDIR:-/tmp}/qa-emulator-$PORT.log"
      set -- -avd "$AVD" -port "$PORT" -no-snapshot-load -no-audio -no-boot-anim
      [ -z "$READ_ONLY" ] || set -- "$@" -read-only
      nohup "$EMULATOR" "$@" >"$LOG" 2>&1 &
      EMU_PID=$!
      printf 'booted-by-this-run: yes (emulator pid %s, log %s)\n' "$EMU_PID" "$LOG" >&2 ;;
    *) die "$SERIAL is '$state' (offline or unauthorized): port busy; pick another --port or fix that emulator by hand" ;;
  esac
  i=0
  until [ "$(adb -s "$SERIAL" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" = 1 ]; do
    i=$((i + 1)); [ $i -le 180 ] || die "$SERIAL did not finish booting in 6 minutes"
    if [ -n "${EMU_PID:-}" ] && ! kill -0 "$EMU_PID" 2>/dev/null; then
      die "emulator exited during boot; see ${LOG:-the emulator log}"
    fi
    sleep 2
  done
  adb -s "$SERIAL" shell input keyevent 82 >/dev/null 2>&1 || true
  if [ -n "$APP" ]; then
    adb -s "$SERIAL" install -r "$APP" >&2
  fi
  printf '%s\n' "$SERIAL"
}

case $PLATFORM in
  ios) boot_ios ;;
  android) boot_android ;;
  *) die "--platform must be ios or android" ;;
esac
