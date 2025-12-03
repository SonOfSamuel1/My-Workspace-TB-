# Google Calendar Weekly Report - Quick Setup Guide

**⏱️ Setup Time:** 5 minutes
**💰 Cost:** $0 (100% free)
**🔧 Maintenance:** Zero

Get a beautifully formatted email every Saturday at 7pm with:
- Unique events (next 90 days)
- Medical appointments (next 12 months)
- Birthdays (next 60 days)
- Anniversaries (next 60 days)

---

## 🚀 Quick Start (5 Steps)

### Step 1: Open Google Apps Script

1. Go to **[script.google.com](https://script.google.com)**
2. Click **+ New project** (top left)
3. You'll see an empty code editor

### Step 2: Copy the Script

1. Open the file `calendar-report-automation.gs` (in this folder)
2. **Select all** the code (Cmd/Ctrl + A)
3. **Copy** it (Cmd/Ctrl + C)
4. Go back to your Google Apps Script tab
5. **Delete** the default `function myFunction() {}` code
6. **Paste** the calendar report script (Cmd/Ctrl + V)
7. Click **💾 Save** (or Cmd/Ctrl + S)
8. Name your project: `Calendar Weekly Report`

### Step 3: Configure Your Settings

Find the configuration section at the top of the script (around lines 24-38). You only need to change **2 things**:

```javascript
// Change this to YOUR email address
const EMAIL_TO = 'your.email@gmail.com';  // ← CHANGE THIS

// These calendar IDs are already filled in from your prompt
const UNIQUE_EVENTS_CALENDAR_ID = 'e8b8ac59c51a37cace65afd1eb320b01080d6eda9a67f8437c9360ad6d575a57@group.calendar.google.com';
const BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID = '33c41f9c4db1bb4a5132d46ed878d0e9ee287b4a7967714be4bb4cb0d6693802@group.calendar.google.com';
```

**That's it!** The calendar IDs are already configured based on your requirements.

💡 **Pro Tip:** If you need to find other calendar IDs, see the "Finding Calendar IDs" section below.

### Step 4: Test It

1. At the top of the script editor, find the dropdown menu (says "Select function")
2. Select **`testGenerateReport`** from the dropdown
3. Click the **▶️ Run** button
4. **First time only:** Google will ask for permissions:
   - Click **Review Permissions**
   - Choose your Google account
   - Click **Advanced** → **Go to Calendar Weekly Report (unsafe)**
   - Click **Allow**
5. Wait 10-20 seconds
6. **Check your email!** You should see "📅 Weekly Calendar Report"

✅ **If you got the email, you're done with testing!**

### Step 5: Activate Weekly Schedule

1. In the script editor, change the dropdown to **`setupWeeklyTrigger`**
2. Click **▶️ Run**
3. You'll see a popup: "Setup Complete!"
4. Click **OK**

🎉 **You're all set!** You'll now receive a calendar report every **Saturday at 7:00pm ET**.

---

## 📧 What the Email Looks Like

Your email will have **four sections**:

```
📅 Weekly Calendar Report
Generated on Saturday, October 24, 2025 at 7:00pm EDT

┌─────────────────────────────────────┐
│ 1. Unique Events — Next 90 Days     │
├─────────────────────────────────────┤
│ Mon, Oct 27, 2025  9:30am - 10:30am │
│ Team Standup                         │
│ 📍 Conference Room A                 │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 2. Medical — Next 12 Months         │
├─────────────────────────────────────┤
│ Wed, Nov 5, 2025  2:00pm - 3:00pm   │
│ Dentist Appointment                  │
│ 📍 123 Main St                       │
└─────────────────────────────────────┘

... and sections for Birthdays and Anniversaries
```

---

## 🔍 Finding Calendar IDs (Optional)

If you need to change which calendars to search:

### Method 1: Google Calendar Settings (Easiest)

1. Go to **[calendar.google.com](https://calendar.google.com)**
2. On the left sidebar, find the calendar you want
3. Click the **⋮** (three dots) next to the calendar name
4. Click **Settings and sharing**
5. Scroll down to **"Integrate calendar"**
6. Copy the **Calendar ID** (looks like: `abc123@group.calendar.google.com`)

### Method 2: Using the Script

1. In your Google Apps Script, change the dropdown to **`listAllCalendars`**
2. Click **▶️ Run**
3. Click **Execution log** (bottom of screen)
4. You'll see all your calendars with their IDs

---

## 🎨 Customization Options

### Change Email Delivery Time

Want it on Sunday at 9am instead? Edit these lines (around line 38):

```javascript
const REPORT_DAY = ScriptApp.WeekDay.SUNDAY;  // or MONDAY, TUESDAY, etc.
const REPORT_HOUR = 9;  // 0-23 (9 = 9am, 14 = 2pm, 21 = 9pm)
```

**Then re-run `setupWeeklyTrigger`** to update the schedule.

### Add More Medical Keywords

Edit the `MEDICAL_KEYWORDS` array (around line 43):

```javascript
const MEDICAL_KEYWORDS = [
  'dentist', 'dental', 'doctor',
  'veterinarian', 'vet',  // ← Add pet care
  'therapy', 'counseling'  // ← Add mental health
  // ... add more keywords
];
```

### Change Time Windows

Want to see 120 days of unique events instead of 90? Edit the functions:

```javascript
// In generateUniqueEventsSection() around line 125
endDate.setDate(endDate.getDate() + 120);  // Changed from 90
```

### Change Birthday/Anniversary Detection

The script looks for these words in event titles:

- **Birthdays:** "birthday", "bday", "born"
- **Anniversaries:** "anniversary", "anniv"

To customize, edit the filter logic in `generateBirthdaysSection()` and `generateAnniversariesSection()` (around lines 180-210).

---

## 🐛 Troubleshooting

### ❌ Not Receiving Emails

**Check spam folder first!** Then:

1. Verify `EMAIL_TO` is correct (line 34)
2. Run `testGenerateReport` and check execution logs
3. Look for error messages in **View** → **Logs**

### ❌ "Calendar not found" Error

**Problem:** Calendar ID is wrong or you don't have access.

**Solution:**
1. Run `listAllCalendars` to see available calendars
2. Copy the correct Calendar ID
3. Update the configuration section
4. Save and re-test

### ❌ Empty Sections (Shows "None")

**Possible reasons:**
- No events in that calendar for the time period
- Calendar ID is wrong
- Events don't match the filters (for Medical/Birthdays/Anniversaries)

**How to debug:**
1. Run `testSections` to see what each section finds
2. Check **View** → **Logs** for details
3. Run `listAllCalendars` to verify calendar access

### ❌ Medical Section Empty But You Have Appointments

**Problem:** Event titles don't match the keywords.

**Solution:**
1. Look at your actual medical appointment titles
2. Add custom keywords to `MEDICAL_KEYWORDS` array
3. Example: If your dentist is "Dr. Smith", add `'dr. smith'`

### ❌ Authorization Issues

**Problem:** "Authorization required" or "Permission denied"

**Solution:**
1. Go to [script.google.com](https://script.google.com)
2. Open your project
3. Run `testGenerateReport` again
4. Grant all permissions when prompted
5. Make sure you're using the same Google account that owns the calendars

### ❌ Trigger Not Running

**Problem:** Saturday came and went, no email.

**Solution:**
1. Go to **Triggers** (⏰ clock icon on left)
2. Verify there's a trigger for `generateWeeklyReport`
3. Check "Last run" column for errors
4. Delete the trigger and run `setupWeeklyTrigger` again

---

## 📊 Monitoring Your Automation

### View Execution History

1. Open [script.google.com](https://script.google.com)
2. Open your **Calendar Weekly Report** project
3. Click **Executions** (▶️ icon on left)
4. See every time the script ran and whether it succeeded

### View Detailed Logs

1. Go to **Executions**
2. Click on any execution
3. Click **View logs**
4. See detailed output of what the script found

### Check Triggers

1. Click **Triggers** (⏰ clock icon)
2. See when the next report will run
3. See history of past runs

---

## 🔒 Privacy & Security

- ✅ Script runs in **your** Google account (nobody else can see it)
- ✅ Calendar data stays in **your** Google Drive
- ✅ Emails go directly from **your** Gmail
- ✅ No third-party services involved
- ✅ No data is stored or shared externally

**Best Practices:**
- Don't share your script with sensitive calendar data
- Use Google's "Make a copy" feature to share a blank template
- Review the code if you're curious what it does

---

## 🛠️ Advanced Usage

### Send to Multiple Email Addresses

```javascript
const EMAIL_TO = 'you@gmail.com,partner@gmail.com,family@gmail.com';
```

### Customize Email Design

The email template is HTML! Edit the `EMAIL_TEMPLATE` constant (around line 48) to change:
- Colors (search for `#667eea` and `#764ba2`)
- Font sizes
- Layout
- Add your own CSS styles

### Filter Specific Calendars Out of Medical Search

In `generateMedicalSection()`, add a filter:

```javascript
// Skip calendars you don't want searched for medical
if (calendar.getName().includes('Work') || calendar.getName().includes('Holidays')) {
  continue;  // Skip this calendar
}
```

### Create Multiple Reports with Different Settings

1. Make a copy of the entire script
2. Rename it (e.g., "Calendar Report - Work")
3. Change the configuration
4. Run `setupWeeklyTrigger` for each script

---

## 📝 Management Functions Reference

| Function | What It Does | When to Use |
|----------|-------------|-------------|
| `testGenerateReport` | Send a report immediately | Testing, debugging |
| `setupWeeklyTrigger` | Enable Saturday 7pm automation | Initial setup, after config changes |
| `removeWeeklyTrigger` | Disable automation | Temporarily stop reports |
| `testSections` | Debug individual sections | Troubleshooting empty sections |
| `listAllCalendars` | Show all accessible calendars | Finding calendar IDs |

To run any function:
1. Select it from the dropdown menu at the top
2. Click **▶️ Run**

---

## 🎯 Common Modifications

### "I want daily reports at 8am"

```javascript
// Change around line 38
const REPORT_HOUR = 8;

// Then edit setupWeeklyTrigger() around line 400
ScriptApp.newTrigger('generateWeeklyReport')
  .timeBased()
  .everyDays(1)  // Changed from .onWeekDay(REPORT_DAY)
  .atHour(REPORT_HOUR)
  .create();
```

### "I only want Medical and Birthdays sections"

Comment out sections you don't want (around line 114):

```javascript
// sections.push(generateUniqueEventsSection());  // Commented out
sections.push(generateMedicalSection());
sections.push(generateBirthdaysSection());
// sections.push(generateAnniversariesSection());  // Commented out
```

### "I want different time windows for each section"

Edit the date calculations in each section function:

```javascript
// In generateUniqueEventsSection()
endDate.setDate(endDate.getDate() + 120);  // 120 days instead of 90

// In generateBirthdaysSection()
endDate.setDate(endDate.getDate() + 90);  // 90 days instead of 60
```

---

## 🆘 Still Having Issues?

1. **Read the error message carefully** - It usually tells you what's wrong
2. **Check View → Logs** - Detailed information about what the script is doing
3. **Run `listAllCalendars`** - Verify you have access to the calendars
4. **Test each section individually** - Run `testSections` to see which part is failing
5. **Verify calendar IDs** - Make sure they're correct and you have permission to access them

---

## ✅ You're All Set!

Your calendar automation is now running! You'll receive a comprehensive report every Saturday at 7pm ET.

**Next Steps:**
- Add medical appointments to test the Medical section
- Wait for your first Saturday report at 7pm
- Customize the email design if desired
- Share this script with friends/family (use "Make a copy" to share blank template)

**Enjoy your automated calendar reports!** 📅✨
