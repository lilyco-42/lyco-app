"""Offline self-check of the device gate: does scripts/device_ui_check.py
actually refuse the wrong things? No adb, no emulator, no APK - it feeds the
gate recorded device output and checks what it answers.

Usage: python3 scripts/gate_selfcheck.py
"""

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import device_ui_check as gate  # noqa: E402

HERE = Path(__file__).resolve().parent
ANR = HERE / "fixtures" / "anr-dialog-ui.xml"
ANR_FOCUS = "mCurrentFocus=Window{1aa137a u0 Application Not Responding: system}\n"
results = []


def check(cond, msg):
    results.append(bool(cond))
    print(f"  [{'ok  ' if cond else 'FAIL'}] {msg}")
    return bool(cond)


def stub_adb(reply=""):
    """The gate shells out to adb; here it answers with a recorded string, and
    the dump/pull calls are no-ops because the fixture file is already local."""
    gate.adb = lambda *a, **k: reply
    gate.adb_rc = lambda *a, **k: 0
    gate.SLOWDOWN = 0.001


def refuses_a_system_dialog():
    """The fixture is a real dump from a CI device: system_server ANR'd under TCG,
    so the window held an "isn't responding" dialog carrying two Buttons. A gate
    that settles on *any* Button graded that dialog as the app's layout and then
    reported "found 0 tab buttons" as if the app were broken.
    """
    stub_adb(ANR_FOCUS)
    nodes = gate.ui_dump("stubbed", ANR)
    buttons = [n for n in nodes if n["cls"] == "Button"]
    check(len(buttons) == 2,
          f"the dialog really does carry {len(buttons)} Buttons, which the old "
          "any-Button rule settled on")
    check(not [n for n in nodes if n["pkg"] == gate.APP_ID],
          "and none of them belong to the app")
    try:
        gate.wait_stable("stubbed", ANR, timeout=2, gap=0)
    except SystemExit as exc:
        check("isn't responding" in str(exc), f"wait_stable refused it: {exc}")
    else:
        check(False, "wait_stable accepted a system dialog as the app's tree")


def reads_insets_from_recorded_shapes():
    """The frame line format is not stable across releases, so each shape the
    parser claims to accept is pinned here - a band it stops finding would
    otherwise silently relax or kill a check on the next image update."""
    for label, line, want in (
        ("API 34/36 InsetsSource",
         "        InsetsSource id=cf4e0000 type=statusBars frame=[0,0][1080,136] visible=true",
         (0, 136, 1080)),
        ("mFrame=Rect with ITYPE name",
         "      mType=ITYPE_STATUS_BAR mFrame=Rect(0, 0 - 1080, 75)",
         (0, 75, 1080)),
    ):
        stub_adb(line)
        got = gate.try_inset("stubbed", "statusBars")
        check(got == want, f"{label} -> {got} (want {want})")
        stub_adb("  nothing inset-shaped at all")
        check(gate.try_inset("stubbed", "statusBars") is None,
              f"{label}: an inset-less dump reads as absent, not as 0")


def counts_only_checks_that_ran():
    for label, checks, want_line, want_rc in (
        ("all green", [("ok", "a"), ("ok", "b"), ("ok", "c")], "3/3 checks passed (0 not applicable", 0),
        ("band absent", [("ok", "a"), ("ok", "b"), ("n/a", "no nav bar")], "2/2 checks passed (1 not applicable", 0),
        ("one red", [("ok", "a"), ("FAIL", "b"), ("n/a", "c")], "1/2 checks passed (1 not applicable", 1),
    ):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = gate.report(checks)
        last = buf.getvalue().strip().splitlines()[-1]
        check(rc == want_rc and want_line in last, f"{label}: rc={rc} {last}")


def names_the_focused_window():
    """wait_gone() decides "the app is off screen" by substring, so both real
    label shapes have to keep parsing - a quiet None there would make every
    force-stop pass without waiting."""
    for label, line, want, is_app in (
        ("app window", "  mCurrentFocus=Window{8fa0f90 u0 com.lycoapp/.MainActivity}\n", "com.lycoapp/.MainActivity", True),
        ("ANR dialog", ANR_FOCUS, "Application Not Responding: system", False),
    ):
        stub_adb(line)
        got = gate.focused("stubbed")
        check(got == want and (gate.APP_ID in got) == is_app, f"{label} -> {got!r}")


def main():
    refuses_a_system_dialog()
    names_the_focused_window()
    reads_insets_from_recorded_shapes()
    counts_only_checks_that_ran()
    ok = sum(results)
    print(f"{ok}/{len(results)} gate self-checks passed")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
