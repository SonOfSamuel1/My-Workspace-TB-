/**
 * Google Calendar Weekly Report Automation
 *
 * This script searches your Google Calendars and emails you a customized report
 * every Saturday at 7pm with upcoming events in four categories:
 * 1. Unique Events (next 90 days)
 * 2. Medical Appointments (next 12 months)
 * 3. Birthdays (next 60 days)
 * 4. Anniversaries (next 60 days)
 *
 * Setup Instructions:
 * 1. Copy this entire script into Google Apps Script (script.google.com)
 * 2. Configure the calendar IDs and email address below
 * 3. Run 'setupWeeklyTrigger()' once to install the automation
 * 4. Run 'testGenerateReport()' to test immediately
 * 5. That's it! You'll receive reports every Saturday at 7pm ET
 */
 

// ============================================================================
// CONFIGURATION - CHANGE THESE VALUES
// ============================================================================

// 1. Unique Events Calendar ID
// This is the calendar ID for section 1 (Unique Events - next 90 days)
const UNIQUE_EVENTS_CALENDAR_ID = 'e8b8ac59c51a37cace65afd1eb320b01080d6eda9a67f8437c9360ad6d575a57@group.calendar.google.com';

// 2. Birthdays & Anniversaries Calendar ID
// This is the calendar ID for sections 3 & 4 (Birthdays and Anniversaries)
const BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID = '33c41f9c4db1bb4a5132d46ed878d0e9ee287b4a7967714be4bb4cb0d6693802@group.calendar.google.com';

// 3. Your email address (where reports will be sent)
const EMAIL_TO = 'your.email@gmail.com';

// 4. Report delivery time (default: Saturday 7pm)
const REPORT_DAY = ScriptApp.WeekDay.SATURDAY;
const REPORT_HOUR = 19; // 7pm in 24-hour format

// 5. Timezone
const TIMEZONE = 'America/New_York';

// ============================================================================
// MEDICAL KEYWORDS - Edit this list to customize medical appointment detection
// ============================================================================

const MEDICAL_KEYWORDS = [
  'dentist', 'dental', 'doctor', 'appointment', 'appt', 'PCP',
  'pediatric', 'pediatrics', 'well visit', 'cleaning', 'ortho', 'orthodontist',
  'PT', 'physical therapy', 'OT', 'occupational therapy',
  'dermatology', 'derm', 'vision', 'eye exam', 'optometry', 'ophthalmology',
  'ENT', 'GI', 'cardiology', 'urology', 'OB', 'OB/GYN',
  'immunization', 'vaccine', 'shot', 'checkup', 'physical'
];

// ============================================================================
// EMAIL TEMPLATE - Customize the HTML email format
// ============================================================================

const EMAIL_TEMPLATE = `
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }
    .container { max-width: 700px; margin: 0 auto; padding: 20px; }
    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; border-radius: 8px 8px 0 0; text-align: center; }
    .header h1 { margin: 0; font-size: 28px; font-weight: 600; }
    .header p { margin: 10px 0 0 0; font-size: 14px; opacity: 0.9; }
    .content { background-color: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; }
    .section { background-color: white; padding: 20px; margin-bottom: 20px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .section-header { color: #667eea; font-size: 20px; font-weight: 600; margin: 0 0 15px 0; padding-bottom: 10px; border-bottom: 2px solid #667eea; }
    .event { padding: 12px 0; border-bottom: 1px solid #e5e7eb; }
    .event:last-child { border-bottom: none; }
    .event-date { font-weight: 600; color: #374151; font-size: 15px; }
    .event-time { color: #6b7280; font-size: 14px; margin-left: 10px; }
    .event-title { color: #111827; font-size: 15px; margin-top: 4px; }
    .event-location { color: #9ca3af; font-size: 13px; margin-top: 2px; font-style: italic; }
    .no-events { color: #9ca3af; font-style: italic; text-align: center; padding: 20px; }
    .footer { background-color: #f3f4f6; padding: 20px; text-align: center; font-size: 12px; color: #6b7280; border-radius: 0 0 8px 8px; }
    .footer a { color: #667eea; text-decoration: none; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>📅 Weekly Calendar Report</h1>
      <p>Generated on {{REPORT_DATE}}</p>
    </div>
    <div class="content">
      {{SECTIONS}}
    </div>
    <div class="footer">
      Generated automatically by Google Apps Script<br>
      Next report: Next Saturday at 7:00pm ET
    </div>
  </div>
</body>
</html>
`;

// ============================================================================
// MAIN SCRIPT - DO NOT EDIT BELOW UNLESS YOU KNOW WHAT YOU'RE DOING
// ============================================================================

/**
 * Main function that generates and sends the weekly calendar report
 */
function generateWeeklyReport() {
  try {
    Logger.log('Starting calendar report generation...');

    const now = new Date();
    const reportDate = Utilities.formatDate(now, TIMEZONE, 'EEEE, MMMM d, yyyy \'at\' h:mm a z');

    // Generate all four sections
    const sections = [];

    // Section 1: Unique Events (next 90 days)
    sections.push(generateUniqueEventsSection());

    // Section 2: Medical Appointments (next 12 months)
    sections.push(generateMedicalSection());

    // Section 3: Birthdays (next 60 days)
    sections.push(generateBirthdaysSection());

    // Section 4: Anniversaries (next 60 days)
    sections.push(generateAnniversariesSection());

    // Build and send email
    const emailHtml = EMAIL_TEMPLATE
      .replace('{{REPORT_DATE}}', reportDate)
      .replace('{{SECTIONS}}', sections.join('\n'));

    const subject = `📅 Weekly Calendar Report - ${Utilities.formatDate(now, TIMEZONE, 'MMM d, yyyy')}`;

    GmailApp.sendEmail(EMAIL_TO, subject, '', {
      htmlBody: emailHtml
    });

    Logger.log(`Report sent successfully to ${EMAIL_TO}`);

  } catch (error) {
    Logger.log(`Error generating report: ${error.message}`);
    // Send error notification email
    GmailApp.sendEmail(EMAIL_TO, '⚠️ Calendar Report Error',
      `There was an error generating your calendar report:\n\n${error.message}\n\nPlease check your Google Apps Script logs.`);
    throw error;
  }
}

/**
 * Section 1: Unique Events (next 90 days)
 */
function generateUniqueEventsSection() {
  Logger.log('Generating Unique Events section...');

  const startDate = new Date();
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 90);

  const events = getEventsFromCalendar(UNIQUE_EVENTS_CALENDAR_ID, startDate, endDate);
  const uniqueEvents = removeDuplicatesAndCollapseRecurring(events);
  const sortedEvents = sortEventsByDate(uniqueEvents);

  return buildSectionHtml('1. Unique Events — Next 90 Days', sortedEvents);
}

/**
 * Section 2: Medical Appointments (next 12 months, all calendars)
 */
function generateMedicalSection() {
  Logger.log('Generating Medical section...');

  const startDate = new Date();
  const endDate = new Date();
  endDate.setFullYear(endDate.getFullYear() + 1); // 12 months

  const allCalendars = CalendarApp.getAllCalendars();
  let allEvents = [];

  // Search all calendars
  for (const calendar of allCalendars) {
    try {
      const calendarId = calendar.getId();
      const events = getEventsFromCalendar(calendarId, startDate, endDate);
      allEvents = allEvents.concat(events);
    } catch (error) {
      Logger.log(`Warning: Could not access calendar ${calendar.getName()}: ${error.message}`);
    }
  }

  // Filter for medical keywords
  const medicalEvents = allEvents.filter(event => isMedicalEvent(event));
  const uniqueEvents = removeDuplicatesAndCollapseRecurring(medicalEvents);
  const sortedEvents = sortEventsByDate(uniqueEvents);

  return buildSectionHtml('2. Medical — Next 12 Months', sortedEvents);
}

/**
 * Section 3: Birthdays (next 60 days)
 */
function generateBirthdaysSection() {
  Logger.log('Generating Birthdays section...');

  const startDate = new Date();
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 60);

  const events = getEventsFromCalendar(BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID, startDate, endDate);

  // Filter for birthday events (titles containing "birthday" or common birthday indicators)
  const birthdayEvents = events.filter(event => {
    const title = event.title.toLowerCase();
    return title.includes('birthday') || title.includes('bday') || title.includes('born');
  });

  const uniqueEvents = removeDuplicatesAndCollapseRecurring(birthdayEvents);
  const sortedEvents = sortEventsByDate(uniqueEvents);

  return buildSectionHtml('3. Birthdays — Next 60 Days', sortedEvents);
}

/**
 * Section 4: Anniversaries (next 60 days)
 */
function generateAnniversariesSection() {
  Logger.log('Generating Anniversaries section...');

  const startDate = new Date();
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 60);

  const events = getEventsFromCalendar(BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID, startDate, endDate);

  // Filter for anniversary events
  const anniversaryEvents = events.filter(event => {
    const title = event.title.toLowerCase();
    return title.includes('anniversary') || title.includes('anniv');
  });

  const uniqueEvents = removeDuplicatesAndCollapseRecurring(anniversaryEvents);
  const sortedEvents = sortEventsByDate(uniqueEvents);

  return buildSectionHtml('4. Anniversaries — Next 60 Days', sortedEvents);
}

/**
 * Get events from a specific calendar
 */
function getEventsFromCalendar(calendarId, startDate, endDate) {
  try {
    const calendar = CalendarApp.getCalendarById(calendarId);

    if (!calendar) {
      Logger.log(`Warning: Calendar not found: ${calendarId}`);
      return [];
    }

    const calendarEvents = calendar.getEvents(startDate, endDate);

    return calendarEvents.map(event => ({
      title: event.getTitle(),
      startTime: event.getStartTime(),
      endTime: event.getEndTime(),
      isAllDay: event.isAllDayEvent(),
      location: event.getLocation(),
      description: event.getDescription(),
      id: event.getId()
    }));

  } catch (error) {
    Logger.log(`Error accessing calendar ${calendarId}: ${error.message}`);
    return [];
  }
}

/**
 * Check if an event is medical-related
 */
function isMedicalEvent(event) {
  const searchText = `${event.title} ${event.description || ''}`.toLowerCase();

  return MEDICAL_KEYWORDS.some(keyword =>
    searchText.includes(keyword.toLowerCase())
  );
}

/**
 * Remove duplicates and collapse recurring events to next occurrence
 */
function removeDuplicatesAndCollapseRecurring(events) {
  const seen = new Map();

  for (const event of events) {
    // Create a unique key based on title and date (not exact time)
    const dateKey = Utilities.formatDate(event.startTime, TIMEZONE, 'yyyy-MM-dd');
    const key = `${event.title.toLowerCase().trim()}_${dateKey}`;

    if (!seen.has(key)) {
      seen.set(key, event);
    }
  }

  return Array.from(seen.values());
}

/**
 * Sort events chronologically
 */
function sortEventsByDate(events) {
  return events.sort((a, b) => a.startTime - b.startTime);
}

/**
 * Build HTML for a section
 */
function buildSectionHtml(sectionTitle, events) {
  if (events.length === 0) {
    return `
      <div class="section">
        <h2 class="section-header">${sectionTitle}</h2>
        <div class="no-events">None</div>
      </div>
    `;
  }

  const eventHtml = events.map(event => formatEventHtml(event)).join('');

  return `
    <div class="section">
      <h2 class="section-header">${sectionTitle}</h2>
      ${eventHtml}
    </div>
  `;
}

/**
 * Format a single event as HTML
 */
function formatEventHtml(event) {
  const dateStr = Utilities.formatDate(event.startTime, TIMEZONE, 'EEE, MMM d, yyyy');

  let timeStr;
  if (event.isAllDay) {
    timeStr = 'All day';
  } else {
    const startTime = formatTime12Hour(event.startTime);
    const endTime = formatTime12Hour(event.endTime);
    timeStr = `${startTime} - ${endTime}`;
  }

  const locationHtml = event.location
    ? `<div class="event-location">📍 ${escapeHtml(event.location)}</div>`
    : '';

  return `
    <div class="event">
      <div class="event-date">
        ${dateStr}
        <span class="event-time">${timeStr}</span>
      </div>
      <div class="event-title">${escapeHtml(event.title)}</div>
      ${locationHtml}
    </div>
  `;
}

/**
 * Format time in 12-hour format without leading zeros (e.g., 9:30am, 12:00pm)
 */
function formatTime12Hour(date) {
  let hours = date.getHours();
  const minutes = date.getMinutes();
  const ampm = hours >= 12 ? 'pm' : 'am';

  hours = hours % 12;
  hours = hours ? hours : 12; // 0 should be 12

  const minutesStr = minutes < 10 ? '0' + minutes : minutes;

  return `${hours}:${minutesStr}${ampm}`;
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ============================================================================
// SETUP AND MANAGEMENT FUNCTIONS
// ============================================================================

/**
 * Setup the weekly trigger for Saturday at 7pm
 * RUN THIS ONCE to install the automation
 */
function setupWeeklyTrigger() {
  // Delete existing triggers to avoid duplicates
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'generateWeeklyReport') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  // Create new trigger - runs every Saturday at 7pm
  ScriptApp.newTrigger('generateWeeklyReport')
    .timeBased()
    .onWeekDay(REPORT_DAY)
    .atHour(REPORT_HOUR)
    .create();

  Logger.log(`Weekly trigger installed! Report will be sent every ${REPORT_DAY} at ${REPORT_HOUR}:00 ${TIMEZONE}`);

  // Show success message if running from UI
  try {
    SpreadsheetApp.getUi().alert(
      'Setup Complete!',
      `The automation is now active!\n\n` +
      `You will receive calendar reports every Saturday at 7:00pm ET.\n\n` +
      `Run 'testGenerateReport' to send a test report immediately.`,
      SpreadsheetApp.getUi().ButtonSet.OK
    );
  } catch (e) {
    // Not running from UI, that's fine
    Logger.log('Trigger setup complete (no UI available for alert)');
  }
}

/**
 * Remove the weekly trigger
 * Run this to disable the automation
 */
function removeWeeklyTrigger() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'generateWeeklyReport') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  Logger.log('Weekly trigger removed. Automation disabled.');
}

/**
 * Test function - generates and sends a report immediately
 * Use this to test your setup before enabling the trigger
 */
function testGenerateReport() {
  Logger.log('Running test report generation...');

  try {
    generateWeeklyReport();
    Logger.log('Test successful! Check your email inbox.');
  } catch (error) {
    Logger.log(`Test failed: ${error.message}`);
    throw error;
  }
}

/**
 * Test individual sections to debug issues
 */
function testSections() {
  Logger.log('Testing individual sections...');

  Logger.log('\n=== Section 1: Unique Events ===');
  const section1 = generateUniqueEventsSection();
  Logger.log(section1.substring(0, 200));

  Logger.log('\n=== Section 2: Medical ===');
  const section2 = generateMedicalSection();
  Logger.log(section2.substring(0, 200));

  Logger.log('\n=== Section 3: Birthdays ===');
  const section3 = generateBirthdaysSection();
  Logger.log(section3.substring(0, 200));

  Logger.log('\n=== Section 4: Anniversaries ===');
  const section4 = generateAnniversariesSection();
  Logger.log(section4.substring(0, 200));

  Logger.log('\nTest complete! Check logs above for results.');
}

/**
 * List all accessible calendars for debugging
 */
function listAllCalendars() {
  Logger.log('Listing all accessible calendars...\n');

  const calendars = CalendarApp.getAllCalendars();

  calendars.forEach(calendar => {
    Logger.log(`Calendar: ${calendar.getName()}`);
    Logger.log(`ID: ${calendar.getId()}`);
    Logger.log(`Color: ${calendar.getColor()}`);
    Logger.log('---');
  });

  Logger.log(`\nTotal calendars found: ${calendars.length}`);
}
