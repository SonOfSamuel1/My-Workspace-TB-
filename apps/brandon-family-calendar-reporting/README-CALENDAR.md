# Google Calendar Weekly Report Automation

**Automatically generate and email a comprehensive calendar report every Saturday at 7pm.**

---

## 🎯 What This Does

Searches your Google Calendars and emails you a beautifully formatted report with **four sections**:

1. **Unique Events** — Next 90 days from a specific calendar
2. **Medical Appointments** — Next 12 months across ALL calendars (auto-detected by keywords)
3. **Birthdays** — Next 60 days from your birthday calendar
4. **Anniversaries** — Next 60 days from the same calendar

**Features:**
- ✅ **100% Free** - Uses Google Apps Script (no servers, no subscriptions)
- ✅ **Zero Maintenance** - Set it and forget it
- ✅ **Fully Customizable** - Edit time windows, keywords, and email design
- ✅ **Smart Deduplication** - Removes duplicates and collapses recurring events
- ✅ **Professional Emails** - Beautiful HTML formatting
- ✅ **Timezone Aware** - Handles America/New_York timezone correctly

---

## ⚡ Quick Start

**Setup Time:** 5 minutes

1. Read **`CALENDAR-SETUP.md`** for step-by-step instructions
2. Copy the script from `calendar-report-automation.gs`
3. Configure 2 values (your email + calendar IDs are pre-filled)
4. Run `setupWeeklyTrigger()` once
5. Done! Get reports every Saturday at 7pm

---

## 📁 Files Included

| File | Description |
|------|-------------|
| `calendar-report-automation.gs` | **Main script** - Copy this to Google Apps Script |
| `CALENDAR-SETUP.md` | ⚡ Complete setup guide with troubleshooting |
| `README-CALENDAR.md` | 📄 This file - overview and documentation |

---

## 📧 Report Format

Each section is sorted chronologically and includes:

- **Date**: "Mon, Oct 27, 2025"
- **Time**: 12-hour format without leading zeros ("9:30am - 10:30am" or "All day")
- **Title**: Event name
- **Location**: If present (shows with 📍 icon)

**Sample Email:**

```
📅 Weekly Calendar Report
Generated on Saturday, October 24, 2025 at 7:00pm EDT

┌─────────────────────────────────────────┐
│ 1. Unique Events — Next 90 Days         │
├─────────────────────────────────────────┤
│ Mon, Oct 27, 2025    9:30am - 10:30am   │
│ Team Planning Session                    │
│ 📍 Conference Room B                     │
│                                          │
│ Wed, Oct 29, 2025    All day            │
│ Company Offsite                          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 2. Medical — Next 12 Months             │
├─────────────────────────────────────────┤
│ Fri, Nov 7, 2025     2:00pm - 3:00pm    │
│ Annual Physical - Dr. Smith             │
│ 📍 123 Medical Plaza                     │
│                                          │
│ Mon, Nov 17, 2025    10:00am - 11:00am  │
│ Dental Cleaning                          │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 3. Birthdays — Next 60 Days             │
├─────────────────────────────────────────┤
│ Sat, Nov 15, 2025    All day            │
│ Mom's Birthday                           │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ 4. Anniversaries — Next 60 Days         │
├─────────────────────────────────────────┤
│ None                                     │
└─────────────────────────────────────────┘
```

---

## 🔧 Configuration

### Required Settings (2 items)

```javascript
// 1. Your email address
const EMAIL_TO = 'your.email@gmail.com';

// 2. Calendar IDs (pre-filled based on your requirements)
const UNIQUE_EVENTS_CALENDAR_ID = 'e8b8ac59...@group.calendar.google.com';
const BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID = '33c41f9c...@group.calendar.google.com';
```

### Optional Settings

```javascript
// Delivery schedule
const REPORT_DAY = ScriptApp.WeekDay.SATURDAY;
const REPORT_HOUR = 19;  // 7pm

// Timezone
const TIMEZONE = 'America/New_York';

// Medical keywords (fully customizable)
const MEDICAL_KEYWORDS = [
  'dentist', 'doctor', 'appointment', 'vaccine', ...
];
```

---

## 🎨 Customization Examples

### Change Delivery Time

Want Sunday morning at 9am?

```javascript
const REPORT_DAY = ScriptApp.WeekDay.SUNDAY;
const REPORT_HOUR = 9;
```

Then re-run `setupWeeklyTrigger()` to update.

### Extend Time Windows

```javascript
// In generateUniqueEventsSection()
endDate.setDate(endDate.getDate() + 120);  // 120 days instead of 90

// In generateMedicalSection()
endDate.setFullYear(endDate.getFullYear() + 2);  // 2 years instead of 1

// In generateBirthdaysSection()
endDate.setDate(endDate.getDate() + 90);  // 90 days instead of 60
```

### Add Custom Medical Keywords

```javascript
const MEDICAL_KEYWORDS = [
  // Default keywords
  'dentist', 'doctor', 'appointment',

  // Add your custom ones
  'veterinarian', 'vet',           // Pet care
  'massage', 'chiropractor',        // Alternative care
  'lab work', 'blood test',         // Testing
  'dr. smith', 'dr. jones'          // Specific doctors
];
```

### Send to Multiple Recipients

```javascript
const EMAIL_TO = 'you@gmail.com,spouse@gmail.com,assistant@company.com';
```

### Filter Out Work Calendar from Medical Search

```javascript
// In generateMedicalSection(), add after line 155:
for (const calendar of allCalendars) {
  // Skip work calendar
  if (calendar.getName().includes('Work')) {
    continue;
  }

  try {
    const calendarId = calendar.getId();
    // ... rest of code
```

### Change Email Colors

Edit the `EMAIL_TEMPLATE` around line 48. Look for these color codes:

```css
/* Header gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* Change to green */
background: linear-gradient(135deg, #10b981 0%, #059669 100%);

/* Or orange */
background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
```

---

## 🧪 Testing & Debugging

### Test Functions

| Function | Purpose | When to Use |
|----------|---------|-------------|
| `testGenerateReport` | Send a report now | Initial testing, verify setup |
| `testSections` | Test each section individually | Debug empty sections |
| `listAllCalendars` | Show all accessible calendars | Find calendar IDs |

**How to run:**
1. Open your script at [script.google.com](https://script.google.com)
2. Select function from dropdown menu
3. Click **▶️ Run**
4. Check **View** → **Logs** for output

### Common Issues

**Empty Medical Section?**
- Events don't contain medical keywords
- Solution: Add custom keywords or check event titles

**"Calendar not found" Error?**
- Calendar ID is wrong
- Solution: Run `listAllCalendars` to find correct ID

**No Birthdays/Anniversaries?**
- Event titles don't contain "birthday" or "anniversary"
- Solution: Customize the filter logic (see CALENDAR-SETUP.md)

**Authorization Errors?**
- Need to grant permissions
- Solution: Run `testGenerateReport` and approve all permissions

---

## 📊 How It Works

### Section 1: Unique Events

1. Fetches all events from specified calendar for next 90 days
2. Removes duplicates by title + date
3. Collapses recurring events to next occurrence only
4. Sorts chronologically

### Section 2: Medical Appointments

1. Searches **ALL** accessible Google Calendars
2. Filters events where title OR description contains medical keywords
3. Covers next 12 months
4. Deduplicates and sorts

### Section 3: Birthdays

1. Fetches events from birthday/anniversary calendar
2. Filters for events containing "birthday", "bday", or "born"
3. Covers next 60 days
4. Deduplicates and sorts

### Section 4: Anniversaries

1. Uses same calendar as birthdays
2. Filters for events containing "anniversary" or "anniv"
3. Covers next 60 days
4. Deduplicates and sorts

---

## 🔒 Privacy & Security

**Your data stays private:**
- ✅ Script runs in **your** Google account
- ✅ Calendar data never leaves Google's servers
- ✅ Emails sent from **your** Gmail
- ✅ No third-party services or APIs
- ✅ No external data storage
- ✅ Only you can access the script

**Permissions Required:**
- Read access to your Google Calendars
- Send email via Gmail
- Run time-based triggers

**Best Practices:**
- Don't share your configured script publicly
- Use "Make a copy" to share with others (creates blank template)
- Review the code if you're curious what it does

---

## 💡 Use Cases

This automation is perfect for:

✅ **Personal Life Management** - Track all upcoming events in one place
✅ **Family Coordination** - Share weekly calendars with spouse/family
✅ **Health Tracking** - Never miss medical appointments
✅ **Special Occasions** - Prepare for birthdays and anniversaries in advance
✅ **Planning Ahead** - See what's coming up in the next 90 days
✅ **Time Blocking** - Review your schedule weekly to plan better

---

## 🆚 Why This vs Other Solutions?

### vs. Manual Calendar Checking
- ✅ **Pro:** Automatic weekly summaries
- ✅ **Pro:** Aggregates multiple calendars
- ✅ **Pro:** Medical appointments auto-detected
- ✅ **Pro:** Email format easy to scan

### vs. Google Calendar Reminders
- ✅ **Pro:** See ALL upcoming events at once
- ✅ **Pro:** Customizable time windows
- ✅ **Pro:** Combined view of multiple calendars
- ❌ **Con:** Weekly vs per-event reminders

### vs. Zapier/Make.com
- ✅ **Pro:** 100% free (no monthly fees)
- ✅ **Pro:** Fully customizable code
- ✅ **Pro:** No platform lock-in
- ❌ **Con:** 5-minute setup required

### vs. Third-Party Calendar Apps
- ✅ **Pro:** No app installation needed
- ✅ **Pro:** Email format (accessible anywhere)
- ✅ **Pro:** Complete control over formatting
- ✅ **Pro:** No subscription fees

---

## 🛠️ Advanced Modifications

### Daily Reports Instead of Weekly

```javascript
// In setupWeeklyTrigger(), replace the trigger creation with:
ScriptApp.newTrigger('generateWeeklyReport')
  .timeBased()
  .everyDays(1)
  .atHour(REPORT_HOUR)
  .create();
```

### Different Time Windows Per Section

```javascript
// Unique Events: next 30 days only
function generateUniqueEventsSection() {
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 30);  // Changed from 90
  // ... rest of code
}

// Medical: next 6 months instead of 12
function generateMedicalSection() {
  const endDate = new Date();
  endDate.setMonth(endDate.getMonth() + 6);  // New approach
  // ... rest of code
}
```

### Add a Fifth Section (Holidays)

```javascript
// Add after line 110
sections.push(generateHolidaysSection());

// Then create the function
function generateHolidaysSection() {
  Logger.log('Generating Holidays section...');

  const startDate = new Date();
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 90);

  const events = getEventsFromCalendar('YOUR_HOLIDAY_CALENDAR_ID', startDate, endDate);
  const uniqueEvents = removeDuplicatesAndCollapseRecurring(events);
  const sortedEvents = sortEventsByDate(uniqueEvents);

  return buildSectionHtml('5. Holidays — Next 90 Days', sortedEvents);
}
```

### Search Only Specific Calendars for Medical

```javascript
// In generateMedicalSection(), replace getAllCalendars() with specific IDs:
const calendarsToSearch = [
  'primary',  // Your main calendar
  'abc123@group.calendar.google.com',
  'xyz789@group.calendar.google.com'
];

let allEvents = [];
for (const calendarId of calendarsToSearch) {
  const events = getEventsFromCalendar(calendarId, startDate, endDate);
  allEvents = allEvents.concat(events);
}
```

### Include Event Descriptions in Email

```javascript
// In formatEventHtml() around line 310, add after locationHtml:
const descriptionHtml = event.description
  ? `<div class="event-description">${escapeHtml(event.description.substring(0, 100))}...</div>`
  : '';

// Then update the return to include it:
return `
  <div class="event">
    <div class="event-date">...</div>
    <div class="event-title">...</div>
    ${locationHtml}
    ${descriptionHtml}
  </div>
`;

// Add CSS in EMAIL_TEMPLATE:
.event-description { color: #6b7280; font-size: 12px; margin-top: 4px; }
```

---

## 📈 Monitoring & Management

### View Execution History

1. Go to [script.google.com](https://script.google.com)
2. Open your project
3. Click **Executions** (▶️ icon)
4. See all past runs and their status

### View Detailed Logs

1. Go to **Executions**
2. Click any execution
3. Click **View logs**
4. See what the script found in each section

### Manage Triggers

1. Click **Triggers** (⏰ clock icon)
2. See active triggers and next run time
3. Delete/edit triggers as needed

### Temporarily Disable

Run `removeWeeklyTrigger()` to pause reports. Run `setupWeeklyTrigger()` to resume.

---

## 🤝 Sharing with Others

### Share the Script (Blank Template)

1. Open your script at [script.google.com](https://script.google.com)
2. Click **File** → **Make a copy**
3. In the copy, clear sensitive values:
   ```javascript
   const EMAIL_TO = 'your.email@gmail.com';
   const UNIQUE_EVENTS_CALENDAR_ID = 'YOUR_CALENDAR_ID_HERE';
   ```
4. Share the copy's URL with others

### Share the Files

Send them the three files:
- `calendar-report-automation.gs`
- `CALENDAR-SETUP.md`
- `README-CALENDAR.md`

They can copy/paste the script and follow the setup guide.

---

## 📝 Technical Details

**Platform:** Google Apps Script (JavaScript)
**Services Used:** CalendarApp, GmailApp, ScriptApp
**Trigger Type:** Time-based (weekly)
**Execution Time:** ~5-10 seconds per run
**Rate Limits:** [Google Apps Script quotas apply](https://developers.google.com/apps-script/guides/services/quotas)

**Free Tier Limits:**
- 20,000 email recipients per day (more than enough)
- 90 minutes of execution time per day
- 30 time-based triggers per script

You'll never hit these limits with this use case.

---

## 🎓 Learning Resources

**Want to customize further?**

- [Google Apps Script Documentation](https://developers.google.com/apps-script)
- [CalendarApp Reference](https://developers.google.com/apps-script/reference/calendar/calendar-app)
- [GmailApp Reference](https://developers.google.com/apps-script/reference/gmail/gmail-app)
- [Time-based Triggers](https://developers.google.com/apps-script/guides/triggers/installable)

**Similar Projects in This Repo:**
- `fireflies-auto-summarizer.gs` - Automated meeting summaries
- Uses similar patterns for email formatting and triggers

---

## ✨ Credits

**Created for automated weekly calendar reporting**

Uses:
- Google Apps Script (free automation platform)
- Google Calendar API
- Gmail API
- HTML email templates

Inspired by the need to stay organized and never miss important events!

---

## 📞 Support

**For setup help:**
1. Read `CALENDAR-SETUP.md` for step-by-step instructions
2. Check the Troubleshooting section above
3. Review execution logs in Google Apps Script
4. Run `testSections` to debug individual sections

**Common Resources:**
- [Google Calendar Help](https://support.google.com/calendar)
- [Google Apps Script Community](https://stackoverflow.com/questions/tagged/google-apps-script)

---

## 🎉 Get Started Now!

1. Open **`CALENDAR-SETUP.md`**
2. Follow the 5-step quick start guide
3. Receive your first report next Saturday at 7pm!

**Total setup time:** 5 minutes
**Maintenance required:** Zero ✨

Enjoy never missing an important event again! 📅
