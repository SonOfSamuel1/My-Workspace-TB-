/**
 * AWS Lambda Calendar Report Automation
 *
 * This Lambda function generates weekly calendar reports and sends them via email.
 * Uses OAuth2 credentials for Google Calendar API access.
 */

const { google } = require('googleapis');
const { SESClient, SendEmailCommand } = require('@aws-sdk/client-ses');
const { SSMClient, GetParameterCommand, PutParameterCommand } = require('@aws-sdk/client-ssm');
const moment = require('moment-timezone');

// ============================================================================
// CONFIGURATION - Set via Lambda Environment Variables
// ============================================================================

const CONFIG = {
  // Google Calendar Configuration
  UNIQUE_EVENTS_CALENDAR_ID: process.env.UNIQUE_EVENTS_CALENDAR_ID || 'primary',
  BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID: process.env.BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID || 'primary',
  MEDICAL_CALENDAR_ID: process.env.MEDICAL_CALENDAR_ID || 'primary',

  // Email Configuration
  EMAIL_TO: process.env.EMAIL_TO || '',
  EMAIL_FROM: process.env.EMAIL_FROM || '',

  // Timezone
  TIMEZONE: process.env.TIMEZONE || 'America/New_York',

  // Google OAuth2 Credentials (stored in SSM Parameter Store)
  SSM_OAUTH_CREDENTIALS_PATH: process.env.SSM_OAUTH_CREDENTIALS_PATH || '/calendar-report/oauth-credentials',
  SSM_OAUTH_TOKEN_PATH: process.env.SSM_OAUTH_TOKEN_PATH || '/calendar-report/oauth-token',

  // AWS Configuration
  AWS_REGION: process.env.AWS_REGION || 'us-east-1'
};

// Medical keywords for detection
const MEDICAL_KEYWORDS = [
  'dentist', 'dental', 'doctor', 'appointment', 'appt', 'PCP',
  'pediatric', 'pediatrics', 'well visit', 'cleaning', 'ortho', 'orthodontist',
  'PT', 'physical therapy', 'OT', 'occupational therapy',
  'dermatology', 'derm', 'vision', 'eye exam', 'optometry', 'ophthalmology',
  'ENT', 'GI', 'cardiology', 'urology', 'OB', 'OB/GYN',
  'immunization', 'vaccine', 'shot', 'checkup', 'physical'
];

// ============================================================================
// EMAIL TEMPLATE
// ============================================================================

const EMAIL_TEMPLATE = `
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #374151; margin: 0; padding: 0; background-color: #f9fafb; }
    .container { max-width: 640px; margin: 0 auto; padding: 24px; }
    .header { background: #1e3a8a; color: white; padding: 32px 24px; border-radius: 8px 8px 0 0; text-align: center; }
    .header h1 { margin: 0; font-size: 22px; font-weight: 500; letter-spacing: -0.025em; }
    .header p { margin: 8px 0 0 0; font-size: 13px; color: #93c5fd; }
    .content { background-color: #ffffff; padding: 24px; border-left: 1px solid #e5e7eb; border-right: 1px solid #e5e7eb; }
    .section { background-color: #ffffff; padding: 0 0 0 16px; margin-bottom: 32px; border-left: 3px solid #1e3a8a; }
    .section:last-child { margin-bottom: 0; }
    .section-header { color: #111827; font-size: 15px; font-weight: 600; margin: 0 0 16px 0; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb; letter-spacing: 0.02em; }
    .section-dot { display: inline-block; width: 8px; height: 8px; background-color: #1e3a8a; border-radius: 50%; margin-right: 10px; vertical-align: middle; }
    .section-title { vertical-align: middle; }
    .event { padding: 14px 0; border-bottom: 1px solid #f3f4f6; }
    .event:last-child { border-bottom: none; padding-bottom: 0; }
    .event-date { font-weight: 600; color: #111827; font-size: 13px; text-transform: uppercase; letter-spacing: 0.03em; }
    .event-time { color: #6b7280; font-size: 12px; margin-left: 8px; font-weight: 400; }
    .event-title { color: #374151; font-size: 15px; margin-top: 4px; }
    .event-title-link { color: #1e3a8a; font-size: 15px; margin-top: 4px; text-decoration: none; }
    .event-location { color: #9ca3af; font-size: 13px; margin-top: 4px; font-style: italic; }
    .no-events { color: #9ca3af; text-align: center; padding: 24px 0; font-size: 14px; }
    .footer { background-color: #f9fafb; padding: 20px 24px; text-align: center; font-size: 12px; color: #6b7280; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px; }
    .btn-regenerate { display: inline-block; background-color: #1e3a8a; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: 500; margin-top: 16px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Brandon Family Calendar Report</h1>
      <p>Generated on {{REPORT_DATE}}</p>
    </div>
    <div class="content">
      {{SECTIONS}}
    </div>
    <div class="footer">
      Generated automatically<br>
      Reports sent: Wednesdays at 5am ET & Saturdays at 7pm ET<br>
      <a href="https://08m0wxuzoh.execute-api.us-east-1.amazonaws.com/regenerate" class="btn-regenerate">Regenerate Report</a>
    </div>
  </div>
</body>
</html>
`;

// ============================================================================
// SSM & OAUTH HELPERS
// ============================================================================

const ssmClient = new SSMClient({ region: CONFIG.AWS_REGION });

/**
 * Get parameter from SSM Parameter Store
 */
async function getSSMParameter(name) {
  try {
    const command = new GetParameterCommand({
      Name: name,
      WithDecryption: true
    });
    const response = await ssmClient.send(command);
    return response.Parameter.Value;
  } catch (error) {
    console.error(`Error getting SSM parameter ${name}:`, error.message);
    throw error;
  }
}

/**
 * Update parameter in SSM Parameter Store
 */
async function updateSSMParameter(name, value) {
  try {
    const command = new PutParameterCommand({
      Name: name,
      Value: value,
      Type: 'SecureString',
      Overwrite: true
    });
    await ssmClient.send(command);
    console.log(`Updated SSM parameter: ${name}`);
  } catch (error) {
    console.error(`Error updating SSM parameter ${name}:`, error.message);
    throw error;
  }
}

/**
 * Create authenticated Google Calendar client using OAuth2
 */
async function getCalendarClient() {
  // Get OAuth credentials from SSM
  const credentialsJson = await getSSMParameter(CONFIG.SSM_OAUTH_CREDENTIALS_PATH);
  const credentials = JSON.parse(credentialsJson);

  // Get OAuth token from SSM
  const tokenJson = await getSSMParameter(CONFIG.SSM_OAUTH_TOKEN_PATH);
  const token = JSON.parse(tokenJson);

  const { client_id, client_secret } = credentials.installed || credentials.web || credentials;

  // Create OAuth2 client
  const oauth2Client = new google.auth.OAuth2(
    client_id,
    client_secret,
    'http://localhost'
  );

  // Set credentials
  oauth2Client.setCredentials({
    access_token: token.access_token,
    refresh_token: token.refresh_token,
    expiry_date: token.expiry_date
  });

  // Handle token refresh
  oauth2Client.on('tokens', async (tokens) => {
    console.log('Token refreshed');
    const updatedToken = {
      ...token,
      access_token: tokens.access_token,
      expiry_date: tokens.expiry_date
    };
    if (tokens.refresh_token) {
      updatedToken.refresh_token = tokens.refresh_token;
    }
    // Save updated token to SSM
    await updateSSMParameter(CONFIG.SSM_OAUTH_TOKEN_PATH, JSON.stringify(updatedToken));
  });

  return google.calendar({ version: 'v3', auth: oauth2Client });
}

// ============================================================================
// CALENDAR EVENT FUNCTIONS
// ============================================================================

/**
 * Get events from a specific calendar
 */
async function getEventsFromCalendar(calendar, calendarId, startDate, endDate) {
  try {
    const response = await calendar.events.list({
      calendarId: calendarId,
      timeMin: startDate.toISOString(),
      timeMax: endDate.toISOString(),
      singleEvents: true,
      orderBy: 'startTime',
      maxResults: 2500
    });

    const events = response.data.items || [];

    return events.map(event => {
      const isAllDay = !event.start.dateTime;
      let startTime, endTime;

      if (isAllDay) {
        // For all-day events, parse date as local to avoid timezone shift
        // event.start.date is like "2025-12-01"
        const [year, month, day] = event.start.date.split('-').map(Number);
        startTime = new Date(year, month - 1, day);
        const [endYear, endMonth, endDay] = event.end.date.split('-').map(Number);
        endTime = new Date(endYear, endMonth - 1, endDay);
      } else {
        // For timed events, dateTime includes timezone info
        startTime = new Date(event.start.dateTime);
        endTime = new Date(event.end.dateTime);
      }

      return {
        title: event.summary || 'Untitled',
        startTime,
        endTime,
        isAllDay,
        location: event.location || '',
        description: event.description || '',
        id: event.id,
        htmlLink: event.htmlLink || ''
      };
    });

  } catch (error) {
    console.error(`Error accessing calendar ${calendarId}:`, error.message);
    return [];
  }
}

/**
 * Get all calendars accessible to the user
 */
async function getAllCalendars(calendar) {
  try {
    const response = await calendar.calendarList.list();
    return response.data.items || [];
  } catch (error) {
    console.error('Error listing calendars:', error.message);
    return [];
  }
}

/**
 * Check if an event is medical-related
 */
function isMedicalEvent(event) {
  const searchText = `${event.title} ${event.description}`.toLowerCase();
  return MEDICAL_KEYWORDS.some(keyword => searchText.includes(keyword.toLowerCase()));
}

/**
 * Remove duplicates and collapse recurring events
 */
function removeDuplicatesAndCollapseRecurring(events) {
  const seen = new Map();

  for (const event of events) {
    const dateKey = moment(event.startTime).tz(CONFIG.TIMEZONE).format('YYYY-MM-DD');
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

// ============================================================================
// SECTION GENERATORS
// ============================================================================

/**
 * Section 1: Unique Events (next 90 days)
 */
async function generateUniqueEventsSection(calendar) {
  console.log('Generating Unique Events section...');

  const startDate = new Date();
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 90);

  const events = await getEventsFromCalendar(calendar, CONFIG.UNIQUE_EVENTS_CALENDAR_ID, startDate, endDate);
  const uniqueEvents = removeDuplicatesAndCollapseRecurring(events);
  const sortedEvents = sortEventsByDate(uniqueEvents);

  return buildSectionHtml('1. Unique Events — Next 90 Days', sortedEvents);
}

/**
 * Section 2: Medical Appointments (next 12 months)
 */
async function generateMedicalSection(calendar) {
  console.log('Generating Medical section...');

  const startDate = new Date();
  const endDate = new Date();
  endDate.setFullYear(endDate.getFullYear() + 1);

  // Get events from the dedicated Medical Appointments calendar
  const events = await getEventsFromCalendar(calendar, CONFIG.MEDICAL_CALENDAR_ID, startDate, endDate);
  const uniqueEvents = removeDuplicatesAndCollapseRecurring(events);
  const sortedEvents = sortEventsByDate(uniqueEvents);

  return buildSectionHtml('2. Medical — Next 12 Months', sortedEvents);
}

/**
 * Section 3: Birthdays (next 60 days)
 */
async function generateBirthdaysSection(calendar) {
  console.log('Generating Birthdays section...');

  const startDate = new Date();
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 60);

  const events = await getEventsFromCalendar(calendar, CONFIG.BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID, startDate, endDate);

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
async function generateAnniversariesSection(calendar) {
  console.log('Generating Anniversaries section...');

  const startDate = new Date();
  const endDate = new Date();
  endDate.setDate(endDate.getDate() + 60);

  const events = await getEventsFromCalendar(calendar, CONFIG.BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID, startDate, endDate);

  const anniversaryEvents = events.filter(event => {
    const title = event.title.toLowerCase();
    return title.includes('anniversary') || title.includes('anniv');
  });

  const uniqueEvents = removeDuplicatesAndCollapseRecurring(anniversaryEvents);
  const sortedEvents = sortEventsByDate(uniqueEvents);

  return buildSectionHtml('4. Anniversaries — Next 60 Days', sortedEvents);
}

// ============================================================================
// HTML FORMATTING FUNCTIONS
// ============================================================================

/**
 * Build HTML for a section
 */
function buildSectionHtml(sectionTitle, events) {
  // Remove number prefix if present (e.g., "1. Unique Events" -> "Unique Events")
  const titleText = sectionTitle.replace(/^\d+\.\s*/, '');

  const headerHtml = `<span class="section-dot"></span><span class="section-title">${titleText}</span>`;

  if (events.length === 0) {
    return `
      <div class="section">
        <h2 class="section-header">${headerHtml}</h2>
        <div class="no-events">None</div>
      </div>
    `;
  }

  const eventHtml = events.map(event => formatEventHtml(event)).join('');

  return `
    <div class="section">
      <h2 class="section-header">${headerHtml}</h2>
      ${eventHtml}
    </div>
  `;
}

/**
 * Format a single event as HTML
 */
function formatEventHtml(event) {
  let dateStr;
  let timeStr;

  if (event.isAllDay) {
    // For all-day events, use moment without timezone conversion (date is already correct)
    dateStr = moment(event.startTime).format('ddd, MMM D, YYYY');
    timeStr = 'All day';
  } else {
    // For timed events, convert to configured timezone
    dateStr = moment(event.startTime).tz(CONFIG.TIMEZONE).format('ddd, MMM D, YYYY');
    const startTime = formatTime12Hour(event.startTime);
    const endTime = formatTime12Hour(event.endTime);
    timeStr = `${startTime} - ${endTime}`;
  }

  const locationHtml = event.location
    ? `<div class="event-location">${escapeHtml(event.location)}</div>`
    : '';

  // Make title a clickable link to Google Calendar if htmlLink is available
  const titleHtml = event.htmlLink
    ? `<a href="${event.htmlLink}" class="event-title-link">${escapeHtml(event.title)}</a>`
    : `<span class="event-title">${escapeHtml(event.title)}</span>`;

  return `
    <div class="event">
      <div class="event-date">
        ${dateStr}
        <span class="event-time">${timeStr}</span>
      </div>
      <div class="event-title">${titleHtml}</div>
      ${locationHtml}
    </div>
  `;
}

/**
 * Format time in 12-hour format
 */
function formatTime12Hour(date) {
  return moment(date).tz(CONFIG.TIMEZONE).format('h:mma');
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
// EMAIL SENDING
// ============================================================================

/**
 * Send email using AWS SES
 */
async function sendEmail(subject, htmlBody) {
  const sesClient = new SESClient({ region: CONFIG.AWS_REGION });

  // Support multiple recipients (comma-separated)
  const toAddresses = CONFIG.EMAIL_TO.split(',').map(email => email.trim());

  const params = {
    Source: CONFIG.EMAIL_FROM,
    Destination: {
      ToAddresses: toAddresses
    },
    Message: {
      Subject: {
        Data: subject,
        Charset: 'UTF-8'
      },
      Body: {
        Html: {
          Data: htmlBody,
          Charset: 'UTF-8'
        },
        Text: {
          Data: 'Please view this email in an HTML-compatible email client.',
          Charset: 'UTF-8'
        }
      }
    }
  };

  try {
    const command = new SendEmailCommand(params);
    const response = await sesClient.send(command);
    console.log('Email sent successfully:', response.MessageId);
    return response;
  } catch (error) {
    console.error('Error sending email:', error);
    throw error;
  }
}

// ============================================================================
// MAIN REPORT GENERATION
// ============================================================================

/**
 * Main function that generates and sends the weekly calendar report
 */
async function generateWeeklyReport() {
  console.log('Starting calendar report generation...');

  try {
    // Validate configuration
    if (!CONFIG.EMAIL_TO || !CONFIG.EMAIL_FROM) {
      throw new Error('EMAIL_TO and EMAIL_FROM must be configured');
    }

    // Initialize Google Calendar client with OAuth
    console.log('Initializing Google Calendar client...');
    const calendar = await getCalendarClient();

    const reportDate = moment().tz(CONFIG.TIMEZONE).format('dddd, MMMM D, YYYY [at] h:mm A z');

    // Generate all four sections
    const sections = [];
    sections.push(await generateUniqueEventsSection(calendar));
    sections.push(await generateMedicalSection(calendar));
    sections.push(await generateBirthdaysSection(calendar));
    sections.push(await generateAnniversariesSection(calendar));

    // Build email
    const emailHtml = EMAIL_TEMPLATE
      .replace('{{REPORT_DATE}}', reportDate)
      .replace('{{SECTIONS}}', sections.join('\n'));

    const subject = `Brandon Family Calendar Report - ${moment().tz(CONFIG.TIMEZONE).format('MMM D, YYYY')}`;

    // Send email
    await sendEmail(subject, emailHtml);

    console.log(`Report sent successfully to ${CONFIG.EMAIL_TO}`);

    return {
      statusCode: 200,
      body: JSON.stringify({
        message: 'Calendar report generated and sent successfully',
        timestamp: new Date().toISOString()
      })
    };

  } catch (error) {
    console.error('Error generating report:', error);

    // Try to send error notification if email is configured
    if (CONFIG.EMAIL_TO && CONFIG.EMAIL_FROM) {
      try {
        await sendEmail(
          'Calendar Report Error',
          `<p>There was an error generating your calendar report:</p><pre>${error.message}</pre><p>Please check your AWS Lambda logs.</p>`
        );
      } catch (emailError) {
        console.error('Failed to send error notification:', emailError);
      }
    }

    return {
      statusCode: 500,
      body: JSON.stringify({
        message: 'Error generating calendar report',
        error: error.message,
        timestamp: new Date().toISOString()
      })
    };
  }
}

// ============================================================================
// LAMBDA HANDLER
// ============================================================================

/**
 * AWS Lambda handler function
 */
exports.handler = async (event, context) => {
  console.log('Lambda function invoked');
  console.log('Event:', JSON.stringify(event, null, 2));

  return await generateWeeklyReport();
};

// For local testing
if (require.main === module) {
  generateWeeklyReport()
    .then(result => {
      console.log('Result:', result);
      process.exit(0);
    })
    .catch(error => {
      console.error('Error:', error);
      process.exit(1);
    });
}
