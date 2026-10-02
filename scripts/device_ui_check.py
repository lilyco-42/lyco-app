"""Drive the CI-built APK on a local emulator and assert the layout is usable.

Why this exists: the react-native-web Storybook lane renders the same components
but has no status bar, so it cannot see an inset bug. This script reads the real
widget bounds out of uiautomator and compares them against the window insets the
device actually reports.

Usage: python scripts/device_ui_check.py <path-to-apk> [out-dir]
Requires: adb + a booted emulator, and Metro serving mobile/app for a debug APK.
"""

import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

APP_ID = "com.lycoapp"
ACTIVITY = f"{APP_ID}/.MainActivity"
ADB_MISSING = (
    "adb is not on PATH - install platform-tools; inside "
    "ReactiveCircus/android-emulator-runner it is already there"
)
# A software-rendered (TCG) device is roughly an order of magnitude slower than
# a local accelerated one, so each lane scales the same settle windows instead
# of carrying a second copy of them.
SLOWDOWN = float(os.environ.get("LYCO_DEVICE_SLOWDOWN", "1"))


def adb(*args, serial=None):
    cmd = ["adb"] + (["-s", serial] if serial else []) + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit(ADB_MISSING)
    if r.returncode != 0:
        raise SystemExit(f"adb {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout.replace("\r", "")


def adb_rc(*args, serial=None):
    """Return code only, for calls where non-zero is an expected retry signal."""
    cmd = ["adb"] + (["-s", serial] if serial else []) + list(args)
    try:
        return subprocess.run(cmd, capture_output=True, text=True).returncode
    except FileNotFoundError:
        raise SystemExit(ADB_MISSING)


def pick_device():
    lines = [l.split("\t") for l in adb("devices").splitlines()[1:] if "\t" in l]
    online = [l[0] for l in lines if l[1].strip() == "device"]
    if not online:
        raise SystemExit("no emulator in state 'device' - boot one first")
    return online[0]


def wait_booted(serial, timeout=180):
    for _ in range(timeout):
        if adb("shell", "getprop", "sys.boot_completed", serial=serial).strip() == "1":
            return
        time.sleep(1)
    raise SystemExit(f"{serial} did not boot within {timeout}s")


def ui_dump(serial, local):
    """None means 'not drawable yet', which on a slow device is normal for a
    while: a dump taken before the app has rendered returns no root node and
    exits non-zero. Callers retry; they must not treat it as a layout failure."""
    if adb_rc("shell", "uiautomator", "dump", "/sdcard/lyco-ui.xml", serial=serial) != 0:
        return None
    if adb_rc("pull", "/sdcard/lyco-ui.xml", str(local), serial=serial) != 0:
        return None
    try:
        tree = ET.parse(local)
    except ET.ParseError:
        return None
    return [
        {
            "cls": n.get("class").rsplit(".", 1)[-1],
            "text": (n.get("text") or "").strip(),
            "bounds": tuple(int(v) for v in re.findall(r"-?\d+", n.get("bounds") or "")),
            "enabled": n.get("enabled") == "true",
        }
        for n in tree.iter("node")
    ]


def focused(serial):
    out = adb("shell", "dumpsys", "window", serial=serial)
    m = re.search(r"mCurrentFocus=Window\{[^}]*\s(\S+)/", out)
    return m.group(1) if m else ""


def wait_gone(serial, timeout=20):
    """The dying window still answers uiautomator, so its stale tree would be
    read back as if it were the render we just asked for."""
    deadline = time.time() + timeout * SLOWDOWN
    while time.time() < deadline:
        if APP_ID not in focused(serial):
            return
        time.sleep(1)
    raise SystemExit(f"{APP_ID} kept focus for {timeout}s after force-stop")


def wait_stable(serial, local, timeout=120, gap=3):
    """Cold start re-bundles from Metro, and a half-drawn tree must not be judged."""
    deadline = time.time() + timeout * SLOWDOWN
    previous = None
    while time.time() < deadline:
        nodes = ui_dump(serial, local)
        if nodes is None:
            previous = None
            time.sleep(gap * SLOWDOWN)
            continue
        signature = [(n["cls"], n["text"], n["bounds"]) for n in nodes]
        widgets = [n for n in nodes if n["cls"] in ("Button", "EditText")]
        if widgets and signature == previous:
            return nodes
        previous = signature
        time.sleep(gap * SLOWDOWN)
    raise SystemExit(
        f"the tree never settled with real widgets within {int(timeout * SLOWDOWN)}s - "
        "is the app installed and is Metro running for mobile/app (debug APK)?"
    )


INSET_NAMES = {
    "statusBars": ("statusBars", "ITYPE_STATUS_BAR"),
    "navigationBars": ("navigationBars", "ITYPE_NAVIGATION_BAR"),
    "ime": ("ime", "ITYPE_IME"),
}
FRAME_PATTERNS = (
    r"frame=\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]",
    r"mFrame=Rect\((-?\d+),\s*(-?\d+)\s*-\s*(-?\d+),\s*(-?\d+)\)",
)


def try_inset(serial, kind):
    """The frame the system window occupies, straight from the window manager.
    The line format is not stable across releases - API 36 prints
    `type=statusBars frame=[0,0][1080,136]`, older ones print
    `mType=ITYPE_STATUS_BAR` / `mFrame=Rect(...)` - so accept each shape."""
    out = adb("shell", "dumpsys", "window", serial=serial)
    for line in out.splitlines():
        for name in INSET_NAMES.get(kind, (kind,)):
            if name not in line:
                continue
            for pat in FRAME_PATTERNS:
                m = re.search(pat, line)
                if m:
                    l, t, r, b = (int(g) for g in m.groups())
                    return t, b, r - l
    return None


def inset(serial, kind, timeout=120):
    """Wait for it. On a software-rendered boot, sys.boot_completed flips while
    SystemUI is still coming up, so the status-bar provider can legitimately be
    absent from the dump for minutes."""
    deadline = time.time() + timeout * SLOWDOWN
    while time.time() < deadline:
        got = try_inset(serial, kind)
        if got is not None:
            return got
        time.sleep(max(5, int(5 * SLOWDOWN)))
    out = adb("shell", "dumpsys", "window", serial=serial)
    clues = [
        line.strip()[:160]
        for line in out.splitlines()
        if "InsetsSource" in line or "ITYPE_" in line
    ][:6]
    raise SystemExit(
        f"could not read the {kind} inset from dumpsys window within "
        f"{int(timeout * SLOWDOWN)}s; what it did report:\n  "
        + "\n  ".join(clues or ["<no inset lines at all>"])
    )


def find(nodes, cls, text=None):
    return [n for n in nodes if n["cls"] == cls and (text is None or text in n["text"])]


def screencap(serial, dest):
    dest.write_bytes(
        subprocess.run(
            ["adb", "-s", serial, "exec-out", "screencap", "-p"], capture_output=True
        ).stdout
    )


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    apk = Path(sys.argv[1])
    if not apk.exists():
        raise SystemExit(f"no such apk: {apk}")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else ".")
    out.mkdir(parents=True, exist_ok=True)
    dump = out / "_ui.xml"

    serial = pick_device()
    wait_booted(serial)
    stop, sbottom, _ = inset(serial, "statusBars")
    ntop, nbottom, _ = inset(serial, "navigationBars")
    sw, sh = (int(v) for v in re.findall(r"\d+", adb("shell", "wm", "size", serial=serial))[-2:])
    print(f"device={serial} screen={sw}x{sh} statusBar=[{stop},{sbottom}] navBar=[{ntop},{nbottom}]")

    checks = []

    def check(cond, ok_msg, bad_msg):
        checks.append(("ok" if cond else "FAIL", ok_msg if cond else bad_msg))

    adb("install", "-r", str(apk), serial=serial)
    # A debug APK carries no JS bundle, so Metro must already be serving this app.
    adb("reverse", "tcp:8081", "tcp:8081", serial=serial)
    adb("shell", "am", "force-stop", APP_ID, serial=serial)
    wait_gone(serial)
    adb("shell", "am", "start", "-n", ACTIVITY, serial=serial)
    nodes = wait_stable(serial, dump)

    tabs = [n for n in nodes if n["cls"] == "Button" and n["bounds"][1] < sh // 3]
    check(
        len(tabs) == 2,
        f"found {len(tabs)} tab buttons near the top",
        f"expected 2 tab buttons near the top, found {len(tabs)}",
    )
    if len(tabs) != 2:
        return report(checks)

    (l0, t0, r0, b0), (l1, t1, r1, b1) = tabs[0]["bounds"], tabs[1]["bounds"]
    # styles.tabs is flexDirection:'row' with gap:8 - on the 420dpi device that gap
    # is 21px. Without this, a stack (the bug the hand-written HTML preview had)
    # would still pass every other check.
    check(
        l1 > r0 and abs(t0 - t1) < 5,
        f"tabs sit side by side ({r0} -> {l1}, gap {l1 - r0}px)",
        f"tabs are not in a row: first ends x={r0}, second starts x={l1}, tops {t0}/{t1}",
    )
    check(
        t0 >= sbottom and t1 >= sbottom,
        f"both tabs start at y={t0}, below the status bar band (ends y={sbottom})",
        f"tab bar is under the status bar: tabs top y={t0}/{t1} < status bar bottom y={sbottom}",
    )

    # Whatever the status bar covers belongs to its window, so a tap there is lost.
    adb("shell", "input", "tap", str((l1 + r1) // 2), str((t1 + b1) // 2), serial=serial)
    after = wait_stable(serial, dump, timeout=30)
    check(
        bool(find(after, "TextView", "地图占位")),
        "tapping the second tab switched to the map screen",
        "tapping the second tab did not switch screens",
    )
    check(
        bool(find(after, "TextView", "搜身边")) and not find(after, "EditText"),
        "map screen shows its buttons and no chat input",
        "map screen content is wrong",
    )
    screencap(serial, out / "nearby.png")

    adb("shell", "input", "tap", str((l0 + r0) // 2), str((t0 + b0) // 2), serial=serial)
    back = wait_stable(serial, dump, timeout=30)
    inputs = find(back, "EditText")
    check(
        bool(inputs),
        "tapping the first tab came back to the chat screen",
        "the first tab did not return to chat",
    )
    if inputs:
        check(
            inputs[0]["bounds"][3] <= ntop,
            f"chat input bottom y={inputs[0]['bounds'][3]} clears the nav bar band (starts y={ntop})",
            f"chat input is under the nav bar: bottom y={inputs[0]['bounds'][3]} >= {ntop}",
        )
    screencap(serial, out / "chat.png")

    # adjustResize in the manifest does nothing once the app is edge-to-edge: the
    # IME is an overlay inset, so the composer stays where it was and the
    # keyboard covers it. Only KeyboardAvoidingView moves it out of the way.
    if inputs:
        box = inputs[0]["bounds"]
        adb("shell", "input", "tap", str((box[0] + box[2]) // 2), str((box[1] + box[3]) // 2), serial=serial)
        time.sleep(max(2, int(2 * SLOWDOWN)))
        adb("shell", "input", "text", "hi", serial=serial)
        typed = wait_stable(serial, dump, timeout=30)
        ime = try_inset(serial, "ime")
        composer = find(typed, "EditText")
        if not composer:
            check(False, "", "composer vanished when the keyboard opened")
        elif ime is None:
            check(False, "", "the keyboard never came up, so this check proved nothing")
        else:
            check(
                composer[0]["bounds"][3] <= ime[0] + 2,
                f"with the keyboard up (ime starts y={ime[0]}) the composer is at y={composer[0]['bounds'][3]}",
                f"the keyboard covers the composer: its bottom y={composer[0]['bounds'][3]} is under ime top y={ime[0]}",
            )
        screencap(serial, out / "keyboard.png")
        adb("shell", "input", "keyevent", "4", serial=serial)
    return report(checks)


def report(checks):
    for kind, msg in checks:
        print(f"  [{kind:4}] {msg}")
    bad = [c for c in checks if c[0] == "FAIL"]
    print(f"{len(checks) - len(bad)}/{len(checks)} checks passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
