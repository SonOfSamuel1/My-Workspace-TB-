#!/usr/bin/env python3
"""
get_next_event.py

Gets the next upcoming calendar event and optionally:
  - Prints info / JSON output
  - Shows a macOS notification
  - Opens the Timer+ app via URL scheme

Usage:
  python3 get_next_event.py                  # print next event info
  python3 get_next_event.py --notify         # + macOS notification
  python3 get_next_event.py --open           # + open Timer+ URL on device
  python3 get_next_event.py --json           # JSON output
  python3 get_next_event.py --threshold 7200 # only trigger if event within 2h
"""

import subprocess
import sys
import json
import argparse


# ── Configuration ─────────────────────────────────────────────────────────────
# URL scheme for your Timer+ app.
# To find the right scheme: open Safari on iPhone, type "timerplus://" in the
# address bar. If Timer+ opens, this is correct. Otherwise try alternatives in
# README.md.
TIMER_SCHEME = "timerplus"

# URL template — {seconds} is replaced with the countdown duration.
# Common patterns:
#   timerplus://timer?duration={seconds}
#   timer-app://start?seconds={seconds}
#   x-callback-url://timerplus/start?duration={seconds}
TIMER_URL_TEMPLATE = f"{TIMER_SCHEME}://timer?duration={{seconds}}"
# ──────────────────────────────────────────────────────────────────────────────


def get_next_event():
    """Query Calendar.app via AppleScript. Returns (title, seconds_until, error)."""
    script = """
    set theDate to current date
    set windowEnd to theDate + (30 * 24 * 3600)
    set nearestTitle to ""
    set nearestSeconds to -1

    tell application "Calendar"
        -- Launch Calendar silently if not already running
        launch
        delay 4
        repeat with cal in every calendar
            try
                set windowEvts to (every event of cal whose start date > theDate and start date < windowEnd)
                repeat with evt in windowEvts
                    set secsUntil to ((start date of evt) - theDate) as integer
                    if nearestSeconds = -1 or secsUntil < nearestSeconds then
                        set nearestSeconds to secsUntil
                        set nearestTitle to summary of evt
                    end if
                end repeat
            end try
        end repeat
    end tell

    if nearestSeconds = -1 then
        return "NONE"
    else
        return nearestTitle & "|||" & nearestSeconds
    end if
    """
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True, text=True, timeout=60
    )

    if result.returncode != 0:
        return None, None, result.stderr.strip()

    output = result.stdout.strip()
    if output == "NONE":
        return None, None, "No upcoming events found"

    parts = output.split("|||", 1)
    if len(parts) != 2:
        return None, None, f"Unexpected AppleScript output: {output}"

    title = parts[0].strip()
    try:
        seconds = int(parts[1].strip())
    except ValueError:
        return None, None, f"Could not parse seconds from: {parts[1]}"

    return title, seconds, None


def format_duration(seconds):
    """Format seconds as human-readable string."""
    if seconds <= 0:
        return "starting now"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m"
    elif m > 0:
        return f"{m}m {s}s"
    else:
        return f"{s}s"


def build_timer_url(seconds):
    return TIMER_URL_TEMPLATE.format(seconds=max(0, seconds))


def show_notification(title, subtitle, message=""):
    script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="Start Timer+ with next calendar event")
    parser.add_argument("--notify", action="store_true", help="Show macOS notification")
    parser.add_argument("--open", action="store_true", help="Open Timer+ URL scheme")
    parser.add_argument("--json", dest="as_json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--threshold", type=int, default=0,
        help="Only trigger if event starts within N seconds (0 = always trigger)"
    )
    args = parser.parse_args()

    title, seconds, error = get_next_event()

    if error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    if args.threshold > 0 and seconds > args.threshold:
        msg = f"Next event '{title}' starts in {format_duration(seconds)} — beyond threshold, skipping."
        if args.as_json:
            print(json.dumps({"skipped": True, "title": title, "seconds": seconds, "reason": msg}))
        else:
            print(msg)
        sys.exit(0)

    duration_str = format_duration(seconds)
    timer_url = build_timer_url(seconds)

    if args.as_json:
        print(json.dumps({
            "title": title,
            "seconds": seconds,
            "duration": duration_str,
            "url": timer_url,
        }))
    else:
        print(f"Next event : {title}")
        print(f"Starts in  : {duration_str} ({seconds}s)")
        print(f"Timer+ URL : {timer_url}")

    if args.notify:
        show_notification(
            "Calendar -> Timer+",
            f"{title} starts in {duration_str}",
            "Tap to open Timer+ on your iPhone"
        )

    if args.open:
        result = subprocess.run(["open", timer_url], capture_output=True)
        if result.returncode != 0:
            print(f"Could not open URL '{timer_url}'", file=sys.stderr)
            print("   Check TIMER_SCHEME in this script -- see README for help.", file=sys.stderr)


if __name__ == "__main__":
    main()
