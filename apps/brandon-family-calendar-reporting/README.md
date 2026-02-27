# Brandon Family Calendar Reporting System

**Automated weekly calendar report system that generates and emails comprehensive calendar summaries with unique events, medical appointments, birthdays, and anniversaries.**

[![Status](https://img.shields.io/badge/status-active-success.svg)]()
[![Platform](https://img.shields.io/badge/platform-Google%20Apps%20Script-blue.svg)]()
[![Cost](https://img.shields.io/badge/cost-free-brightgreen.svg)]()
[![Setup Time](https://img.shields.io/badge/setup-5%20minutes-orange.svg)]()

---

## 📧 What You Get

Every **Saturday at 7:00 PM ET**, you'll receive a beautifully formatted email with:

### 📅 Section 1: Unique Events (Next 90 Days)
All upcoming unique events from your main calendar - trips, reservations, special activities

### 🏥 Section 2: Medical Appointments (Next 12 Months)
Auto-detected medical appointments across ALL calendars - dentist, doctor visits, health checkups

### 🎂 Section 3: Birthdays (Next 60 Days)
Upcoming birthdays so you never miss a celebration

### 💍 Section 4: Anniversaries (Next 60 Days)
Important anniversaries and milestones

---

## ✨ Key Features

- ✅ **100% Free** - Uses Google Apps Script (no servers, no subscriptions)
- ✅ **Zero Maintenance** - Set it and forget it
- ✅ **Smart Deduplication** - Automatically removes duplicate and recurring events
- ✅ **Auto-Detection** - Medical appointments identified by keywords
- ✅ **Beautiful HTML Emails** - Professional, mobile-friendly design
- ✅ **Fully Customizable** - Edit time windows, keywords, styling, and schedule

---

## 🚀 Quick Start

### Setup Time: 5 Minutes

1. **Read the Setup Guide**
   - Open [`CALENDAR-SETUP.md`](CALENDAR-SETUP.md) for step-by-step instructions

2. **Copy the Script**
   - Go to [script.google.com](https://script.google.com)
   - Create a new project
   - Copy the code from `calendar-report-automation.gs`

3. **Configure 2 Values**
   ```javascript
   const EMAIL_TO = 'your.email@gmail.com';  // Your email
   const UNIQUE_EVENTS_CALENDAR_ID = 'your-calendar-id@group.calendar.google.com';
   ```

4. **Test & Activate**
   - Run `testGenerateReport` to test
   - Run `setupWeeklyTrigger` to activate
   - Done! You'll get reports every Saturday at 7pm

📖 **For detailed instructions, see [`CALENDAR-SETUP.md`](CALENDAR-SETUP.md)**

---

## 📁 Files in This Repository

| File | Description |
|------|-------------|
| [`calendar-report-automation.gs`](calendar-report-automation.gs) | Main Google Apps Script - copy this to script.google.com |
| [`CALENDAR-SETUP.md`](CALENDAR-SETUP.md) | Complete setup guide with troubleshooting |
| [`README-CALENDAR.md`](README-CALENDAR.md) | Detailed documentation and customization options |
| `README.md` | This file - quick overview |

---

## 📧 Sample Email Output

```
📅 Brandon Family Calendar Report
Friday, October 24, 2025 at 6:57 PM EDT

┌────────────────────────────────────────┐
│ 1. UNIQUE EVENTS — NEXT 90 DAYS        │
├────────────────────────────────────────┤
│ Thu, Oct 30         All day            │
│ Family Trip to LA                      │
│                                        │
│ Thu, Oct 30    3:00pm-12:00pm          │
│ Residence Inn Riverside Moreno Valley  │
│ 📍 Residence Inn Riverside Moreno      │
│    Valley                              │
│                                        │
│ Tue, Nov 4     9:45am-4:55pm           │
│ Disneyland Park Visit                  │
└────────────────────────────────────────┘

┌────────────────────────────────────────┐
│ 2. MEDICAL — NEXT 12 MONTHS            │
├────────────────────────────────────────┤
│ Wed, Nov 12    2:00pm-3:00pm           │
│ Annual Physical - Dr. Smith            │
│ 📍 123 Medical Plaza                   │
└────────────────────────────────────────┘

... Birthdays and Anniversaries sections
```

---

## 🎨 Customization Options

### Change Delivery Schedule
```javascript
const REPORT_DAY = ScriptApp.WeekDay.SUNDAY;  // Any day of week
const REPORT_HOUR = 9;  // 0-23 (9am, 2pm, 7pm, etc.)
```

### Adjust Time Windows
```javascript
// Unique Events: 120 days instead of 90
endDate.setDate(endDate.getDate() + 120);

// Medical: 6 months instead of 12
endDate.setMonth(endDate.getMonth() + 6);
```

### Add Custom Medical Keywords
```javascript
const MEDICAL_KEYWORDS = [
  'dentist', 'doctor', 'appointment',
  'veterinarian', 'vet',  // Add pet care
  'therapy', 'counseling'  // Add mental health
];
```

### Customize Email Design
Edit the `EMAIL_TEMPLATE` variable to change colors, fonts, and layout.

📖 **For more customization examples, see [`README-CALENDAR.md`](README-CALENDAR.md)**

---

## 🔧 How It Works

1. **Google Apps Script** runs automatically every Saturday at 7pm ET
2. **Fetches events** from your configured Google Calendars
3. **Filters and organizes** events into 4 categories
4. **Removes duplicates** and collapses recurring events
5. **Generates HTML email** with beautiful formatting
6. **Sends via Gmail** directly to your inbox

All processing happens in your Google account - no external services needed!

---

## 🐛 Troubleshooting

### Not Receiving Emails?
- Check spam folder
- Verify `EMAIL_TO` is correct
- Check execution logs in Google Apps Script

### Empty Sections?
- Medical: Add custom keywords for your appointments
- Birthdays/Anniversaries: Ensure event titles contain "birthday" or "anniversary"
- Unique Events: Verify calendar ID is correct

### "Calendar not found" Error?
- Run `listAllCalendars` to find correct calendar ID
- Ensure you have access to the calendar

📖 **For detailed troubleshooting, see [`CALENDAR-SETUP.md`](CALENDAR-SETUP.md)**

---

## 🔒 Privacy & Security

- ✅ Script runs in **your** Google account
- ✅ Calendar data stays in **your** Google Calendar
- ✅ Emails sent from **your** Gmail
- ✅ No third-party services or APIs
- ✅ No external data storage
- ✅ Only you can access the script

---

## 💡 Use Cases

Perfect for:

✅ **Family Organization** - Keep everyone informed of upcoming events
✅ **Health Management** - Never miss medical appointments
✅ **Special Occasions** - Prepare for birthdays and anniversaries in advance
✅ **Trip Planning** - See all upcoming trips and reservations
✅ **Weekly Planning** - Review what's coming up in the next 90 days

---

## 📊 Management & Monitoring

### View Execution History
1. Open [script.google.com](https://script.google.com)
2. Click **Executions** to see all past runs
3. Check for errors or failures

### Test Functions
| Function | Purpose |
|----------|---------|
| `testGenerateReport` | Send a report immediately (for testing) |
| `testSections` | Test each section individually |
| `listAllCalendars` | Show all accessible calendars and their IDs |
| `setupWeeklyTrigger` | Activate the weekly automation |
| `removeWeeklyTrigger` | Disable the automation |

---

## 🛠️ Technical Details

**Platform:** Google Apps Script (JavaScript)
**Services:** CalendarApp, GmailApp, ScriptApp
**Trigger:** Time-based (weekly)
**Execution Time:** ~5-10 seconds per run
**Cost:** $0.00 (free)

**Google Apps Script Free Tier:**
- 20,000 email recipients per day
- 90 minutes of execution time per day
- 30 time-based triggers per script

This automation uses a tiny fraction of these limits.

---

## 🎓 Learn More

- [Google Apps Script Documentation](https://developers.google.com/apps-script)
- [CalendarApp Reference](https://developers.google.com/apps-script/reference/calendar/calendar-app)
- [GmailApp Reference](https://developers.google.com/apps-script/reference/gmail/gmail-app)
- [Time-based Triggers](https://developers.google.com/apps-script/guides/triggers/installable)

---

## 🤝 Contributing

Found a bug or have an improvement?

1. Fork this repository
2. Make your changes
3. Test thoroughly
4. Submit a pull request

---

## 📝 License

MIT License - Feel free to use and modify for your own family calendar reporting!

---

## 🙏 Acknowledgments

Built with:
- **Google Apps Script** - Free automation platform
- **Google Calendar API** - Event data source
- **Gmail API** - Email delivery

---

## 📞 Support

**For setup help:**
1. Read [`CALENDAR-SETUP.md`](CALENDAR-SETUP.md)
2. Check the troubleshooting section in [`README-CALENDAR.md`](README-CALENDAR.md)
3. Review execution logs in Google Apps Script

---

## 🎉 Get Started Now!

1. Open [`CALENDAR-SETUP.md`](CALENDAR-SETUP.md)
2. Follow the 5-minute quick start guide
3. Receive your first report next Saturday at 7pm!

**Enjoy staying organized and never missing important family events!** 📅✨
