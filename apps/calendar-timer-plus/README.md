# Calendar → Timer+

Reads your next calendar event and starts a countdown timer in Timer+ with the
time remaining until it begins.

**Two independent paths — use one or both:**

| Path | Trigger | Runs on |
|------|---------|---------|
| Mac script + LaunchAgent | Scheduled (every 15min) + manual | Mac |
| iOS Shortcut + Personal Automation | Scheduled + manual | iPhone |

---

## Quick Start (Mac)

```bash
# 1. Find your Timer+ URL scheme (see section below)
# 2. Edit TIMER_URL_TEMPLATE in get_next_event.py
# 3. Test it
python3 get_next_event.py

# 4. Install the LaunchAgent (runs every 15 min automatically)
./install.sh

# 5. Manual trigger any time
./start_timer.sh
```

---

## Step 1 — Find Your Timer+ URL Scheme

Every app has a unique URL scheme. To find yours:

1. Open **Safari** on your iPhone
2. In the address bar, type `timerplus://` and press Go
3. If Timer+ opens → your scheme is `timerplus`
4. If it doesn't work, try: `timer-app://`, `timerplus2://`, `countdowntimer://`
5. Check the Timer+ app settings or website for a "URL Scheme" or "x-callback-url" section

Once you know the scheme, check the app's documentation or App Store page for
the full URL format. Common patterns:

```
timerplus://timer?duration=300          # 300 seconds
timerplus://timer?start=true&duration=300
timer-app://start?seconds=300
x-callback-url://timerplus/start?duration=300
```

**Update the script:**
Open `get_next_event.py` and edit these two lines at the top:

```python
TIMER_SCHEME = "timerplus"              # ← your scheme
TIMER_URL_TEMPLATE = "timerplus://timer?duration={seconds}"  # ← full URL
```

---

## Mac Script

### Usage

```bash
python3 get_next_event.py               # show next event info
python3 get_next_event.py --notify      # + macOS notification
python3 get_next_event.py --open        # + open Timer+ URL
python3 get_next_event.py --json        # JSON output
python3 get_next_event.py --threshold 3600  # only if event within 1 hour
```

### Scheduled (LaunchAgent)

The `install.sh` script installs a LaunchAgent that runs every 15 minutes:

```bash
./install.sh
```

To change the interval, edit the `StartInterval` value in the `.plist` file
(seconds). Examples: `900` = 15 min, `1800` = 30 min, `3600` = 1 hour.

After editing the plist, reload it:
```bash
launchctl unload ~/Library/LaunchAgents/com.terrancebrandon.calendar-timer-plus.plist
launchctl load  ~/Library/LaunchAgents/com.terrancebrandon.calendar-timer-plus.plist
```

### Logs

```bash
tail -f /tmp/calendar-timer-plus.log
tail -f /tmp/calendar-timer-plus-error.log
```

### Uninstall

```bash
launchctl unload ~/Library/LaunchAgents/com.terrancebrandon.calendar-timer-plus.plist
rm ~/Library/LaunchAgents/com.terrancebrandon.calendar-timer-plus.plist
```

---

## iOS Shortcut (Recommended for iPhone)

This runs entirely on your iPhone — no Mac needed. Use this for reliable
on-device scheduling and a manual Home Screen button.

### Create the Shortcut

1. Open **Shortcuts** on iPhone
2. Tap **+** to create a new shortcut, name it **"Start Timer+ for Next Event"**
3. Add these actions in order:

**Action 1 — Find Calendar Events**
- Action: `Find Calendar Events`
- Calendars: All (or select specific ones)
- Filter: Start Date → is after → Current Date
- Sort by: Start Date (ascending)
- Limit: 1

**Action 2 — Get the event's start date**
- Action: `Get Details of Calendar Events`
- Detail: `Start Date`

**Action 3 — Calculate time until event**
- Action: `Calculate Between Dates`
- From: `Current Date`
- To: (the Start Date from Action 2)
- In: `Seconds`

**Action 4 — Open Timer+ URL**
- Action: `Open URLs`
- URL: `timerplus://timer?duration=[result from Action 3]`
  - Tap the URL field → insert the variable from Action 3 (the seconds count)

### Add to Home Screen (Manual Trigger)

1. In the shortcut editor, tap the **Share** icon
2. Tap **Add to Home Screen**
3. Name it "Timer+ for Next Event" and tap **Add**

### Schedule with Personal Automation

1. Open **Shortcuts** → **Automation** tab → **+** → **New Automation**
2. Choose a trigger:
   - **Time of Day** — runs at specific times (e.g., every morning at 8am)
   - **App** — runs when you open a specific app
   - **Calendar** — runs when a calendar event starts (most useful!)
3. Add Action: `Run Shortcut` → select **"Start Timer+ for Next Event"**
4. Turn off **"Ask Before Running"** so it runs automatically

**Recommended automation:** Trigger = "Calendar Event" starts → Run the shortcut.
This auto-starts the timer exactly when each event begins.

---

## How It Works

```
Mac LaunchAgent (every 15 min)
  └── get_next_event.py
        ├── AppleScript → Calendar.app → next event + start time
        ├── Calculate: seconds until event starts
        └── open timerplus://timer?duration=<seconds>

iOS Shortcut (Personal Automation / Home Screen)
  └── Find Calendar Events (next 1, sorted by start date)
        ├── Get Start Date
        ├── Calculate seconds from Now to Start Date
        └── Open URL: timerplus://timer?duration=<seconds>
```
