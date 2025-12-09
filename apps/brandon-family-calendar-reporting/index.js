/**
 * Brandon Family Calendar Report - AWS Lambda Handler
 *
 * Fetches upcoming events from Google Calendars and sends a weekly report
 * with four sections:
 * 1. Unique Events (next 90 days)
 * 2. Medical Appointments (next 12 months, keyword-based)
 * 3. Birthdays (next 60 days)
 * 4. Anniversaries (next 60 days)
 */

const { google } = require("googleapis");
const { SESClient, SendEmailCommand } = require("@aws-sdk/client-ses");
const { SSMClient, GetParameterCommand } = require("@aws-sdk/client-ssm");
const moment = require("moment-timezone");
const fs = require("fs");
const path = require("path");

// Configuration
const TIMEZONE = process.env.TIMEZONE || "America/New_York";

// Medical keywords for filtering
const MEDICAL_KEYWORDS = [
  "dentist",
  "dental",
  "doctor",
  "appointment",
  "appt",
  "PCP",
  "pediatric",
  "pediatrics",
  "well visit",
  "cleaning",
  "ortho",
  "orthodontist",
  "PT",
  "physical therapy",
  "OT",
  "occupational therapy",
  "dermatology",
  "derm",
  "vision",
  "eye exam",
  "optometry",
  "ophthalmology",
  "ENT",
  "GI",
  "cardiology",
  "urology",
  "OB",
  "OB/GYN",
  "immunization",
  "vaccine",
  "shot",
  "checkup",
  "physical",
];

/**
 * Create authenticated Google Calendar client
 */
async function getCalendarClient() {
  const SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"];

  // Method 1: Service Account credentials from environment
  if (process.env.GOOGLE_CLIENT_EMAIL && process.env.GOOGLE_PRIVATE_KEY) {
    console.log("Using service account credentials from environment");
    const auth = new google.auth.GoogleAuth({
      credentials: {
        type: "service_account",
        client_email: process.env.GOOGLE_CLIENT_EMAIL,
        private_key: process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, "\n"),
      },
      scopes: SCOPES,
    });
    return google.calendar({ version: "v3", auth });
  }

  // Method 2: OAuth credentials from local files
  if (process.env.GOOGLE_CREDENTIALS_PATH && process.env.GOOGLE_TOKEN_PATH) {
    console.log("Using OAuth credentials from files");
    const credentialsPath = path.resolve(process.env.GOOGLE_CREDENTIALS_PATH);
    const tokenPath = path.resolve(process.env.GOOGLE_TOKEN_PATH);

    if (fs.existsSync(credentialsPath) && fs.existsSync(tokenPath)) {
      const credentials = JSON.parse(fs.readFileSync(credentialsPath, "utf8"));
      const token = JSON.parse(fs.readFileSync(tokenPath, "utf8"));

      const { client_id, client_secret, redirect_uris } =
        credentials.installed || credentials.web;

      const oAuth2Client = new google.auth.OAuth2(
        client_id,
        client_secret,
        redirect_uris ? redirect_uris[0] : "http://localhost"
      );
      oAuth2Client.setCredentials(token);

      return google.calendar({ version: "v3", auth: oAuth2Client });
    }
  }

  // Method 3: SSM Parameter Store (for Lambda)
  console.log("Fetching credentials from SSM Parameter Store");
  const ssmClient = new SSMClient({ region: process.env.AWS_REGION });

  try {
    const credentialsCommand = new GetParameterCommand({
      Name: process.env.SSM_OAUTH_CREDENTIALS_PATH,
      WithDecryption: true,
    });
    const credentialsResponse = await ssmClient.send(credentialsCommand);
    const credentials = JSON.parse(credentialsResponse.Parameter.Value);

    if (credentials.type === "service_account") {
      const auth = new google.auth.GoogleAuth({
        credentials,
        scopes: SCOPES,
      });
      return google.calendar({ version: "v3", auth });
    }

    const tokenCommand = new GetParameterCommand({
      Name: process.env.SSM_OAUTH_TOKEN_PATH,
      WithDecryption: true,
    });
    const tokenResponse = await ssmClient.send(tokenCommand);
    const token = JSON.parse(tokenResponse.Parameter.Value);

    const { client_id, client_secret, redirect_uris } =
      credentials.installed || credentials.web;

    const oAuth2Client = new google.auth.OAuth2(
      client_id,
      client_secret,
      redirect_uris ? redirect_uris[0] : "http://localhost"
    );
    oAuth2Client.setCredentials(token);

    return google.calendar({ version: "v3", auth: oAuth2Client });
  } catch (error) {
    console.error("Failed to get credentials from SSM:", error.message);
    throw new Error("Unable to retrieve Google credentials");
  }
}

/**
 * Fetch events from a calendar
 */
async function fetchCalendarEvents(calendar, calendarId, timeMin, timeMax) {
  if (!calendarId) {
    return [];
  }

  try {
    const response = await calendar.events.list({
      calendarId: calendarId,
      timeMin: timeMin.toISOString(),
      timeMax: timeMax.toISOString(),
      singleEvents: true,
      orderBy: "startTime",
    });

    return (response.data.items || []).map((event) => ({
      title: event.summary || "(No title)",
      startTime: event.start.dateTime || event.start.date,
      endTime: event.end.dateTime || event.end.date,
      isAllDay: !event.start.dateTime,
      location: event.location || "",
      description: event.description || "",
      htmlLink: event.htmlLink || "",
      eventId: event.id || "",
    }));
  } catch (error) {
    console.error(`Error fetching calendar ${calendarId}:`, error.message);
    return [];
  }
}

/**
 * Check if event is medical-related
 */
function isMedicalEvent(event) {
  const searchText = `${event.title} ${event.description}`.toLowerCase();
  return MEDICAL_KEYWORDS.some((keyword) =>
    searchText.includes(keyword.toLowerCase())
  );
}

/**
 * Remove duplicates based on title and date
 */
function removeDuplicates(events) {
  const seen = new Map();

  for (const event of events) {
    const dateKey = moment(event.startTime).tz(TIMEZONE).format("YYYY-MM-DD");
    const key = `${event.title.toLowerCase().trim()}_${dateKey}`;

    if (!seen.has(key)) {
      seen.set(key, event);
    }
  }

  return Array.from(seen.values());
}

/**
 * Sort events by date
 */
function sortEventsByDate(events) {
  return events.sort(
    (a, b) => new Date(a.startTime) - new Date(b.startTime)
  );
}

/**
 * Format time in 12-hour format
 */
function formatTime12Hour(dateStr) {
  const date = moment(dateStr).tz(TIMEZONE);
  return date.format("h:mma").toLowerCase();
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/**
 * Format a single event as HTML
 */
function formatEventHtml(event) {
  const dateStr = moment(event.startTime)
    .tz(TIMEZONE)
    .format("ddd, MMM D, YYYY")
    .toUpperCase();

  let timeStr;
  if (event.isAllDay) {
    timeStr = "ALL DAY";
  } else {
    const startTime = formatTime12Hour(event.startTime).toUpperCase();
    const endTime = formatTime12Hour(event.endTime).toUpperCase();
    timeStr = `${startTime} - ${endTime}`;
  }

  const locationHtml = event.location
    ? `<div class="event-location">${escapeHtml(event.location)}</div>`
    : "";

  // Create event title with link if available
  const titleHtml = event.htmlLink
    ? `<a href="${event.htmlLink}" class="event-title">${escapeHtml(event.title)}</a>`
    : `<div class="event-title">${escapeHtml(event.title)}</div>`;

  return `
    <div class="event">
      <div class="event-date">
        ${dateStr}<span class="event-time">${timeStr}</span>
      </div>
      ${titleHtml}
      ${locationHtml}
    </div>
  `;
}

/**
 * Build HTML for a section
 */
function buildSectionHtml(sectionTitle, events) {
  if (events.length === 0) {
    return `
      <div class="section">
        <h2 class="section-header">${sectionTitle}</h2>
        <div class="section-content">
          <div class="no-events">None</div>
        </div>
      </div>
    `;
  }

  const eventHtml = events.map((event) => formatEventHtml(event)).join("");

  return `
    <div class="section">
      <h2 class="section-header">${sectionTitle}</h2>
      <div class="section-content">
        ${eventHtml}
      </div>
    </div>
  `;
}

/**
 * Generate all four sections
 */
async function generateSections(calendar) {
  const now = moment().tz(TIMEZONE);
  const sections = [];

  // Section 1: Unique Events — Next 90 Days
  console.log("Generating Section 1: Unique Events...");
  const uniqueEventsEnd = now.clone().add(90, "days");
  const uniqueEvents = await fetchCalendarEvents(
    calendar,
    process.env.UNIQUE_EVENTS_CALENDAR_ID,
    now,
    uniqueEventsEnd
  );
  const uniqueSorted = sortEventsByDate(removeDuplicates(uniqueEvents));
  console.log(`Found ${uniqueSorted.length} unique events`);
  sections.push(buildSectionHtml("Unique Events — Next 90 Days", uniqueSorted));

  // Section 2: Medical — Next 12 Months (from dedicated Medical calendar only)
  console.log("Generating Section 2: Medical...");
  const medicalEnd = now.clone().add(12, "months");
  const medicalEvents = await fetchCalendarEvents(
    calendar,
    process.env.MEDICAL_CALENDAR_ID,
    now,
    medicalEnd
  );
  const medicalSorted = sortEventsByDate(removeDuplicates(medicalEvents));
  console.log(`Found ${medicalSorted.length} medical appointments`);
  sections.push(buildSectionHtml("Medical — Next 12 Months", medicalSorted));

  // Section 3: Birthdays — Next 60 Days
  console.log("Generating Section 3: Birthdays...");
  const birthdaysEnd = now.clone().add(60, "days");
  const birthdayEvents = await fetchCalendarEvents(
    calendar,
    process.env.BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID,
    now,
    birthdaysEnd
  );
  const birthdays = birthdayEvents.filter((event) => {
    const title = event.title.toLowerCase();
    return title.includes("birthday") || title.includes("bday") || title.includes("born");
  });
  const birthdaysSorted = sortEventsByDate(removeDuplicates(birthdays));
  console.log(`Found ${birthdaysSorted.length} birthdays`);
  sections.push(buildSectionHtml("Birthdays — Next 60 Days", birthdaysSorted));

  // Section 4: Anniversaries — Next 60 Days
  console.log("Generating Section 4: Anniversaries...");
  const anniversariesEnd = now.clone().add(60, "days");
  const anniversaryEvents = await fetchCalendarEvents(
    calendar,
    process.env.BIRTHDAYS_ANNIVERSARIES_CALENDAR_ID,
    now,
    anniversariesEnd
  );
  const anniversaries = anniversaryEvents.filter((event) => {
    const title = event.title.toLowerCase();
    return title.includes("anniversary") || title.includes("anniv");
  });
  const anniversariesSorted = sortEventsByDate(removeDuplicates(anniversaries));
  console.log(`Found ${anniversariesSorted.length} anniversaries`);
  sections.push(buildSectionHtml("Anniversaries — Next 60 Days", anniversariesSorted));

  return {
    sections,
    totalEvents:
      uniqueSorted.length +
      medicalSorted.length +
      birthdaysSorted.length +
      anniversariesSorted.length,
  };
}

/**
 * Generate HTML email content
 */
function generateEmailHTML(sections, reportDate, lambdaFunctionUrl) {
  // Use the Lambda function URL if provided, otherwise use a placeholder
  const regenerateUrl = lambdaFunctionUrl || process.env.LAMBDA_FUNCTION_URL || "#";

  return `
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f5f5f5; }
    .container { max-width: 700px; margin: 0 auto; padding: 20px; }
    .header { background-color: #1a365d; color: white; padding: 30px 20px; border-radius: 8px 8px 0 0; text-align: center; }
    .header h1 { margin: 0; font-size: 26px; font-weight: 500; }
    .header p { margin: 10px 0 0 0; font-size: 14px; color: #a0aec0; }
    .content { background-color: white; padding: 25px 30px; border: 1px solid #e2e8f0; border-top: none; }
    .section { padding: 0; margin-bottom: 30px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); overflow: hidden; }
    .section:last-child { margin-bottom: 0; }
    .section-header { background-color: #f1f5f9; color: #1e293b; font-size: 16px; font-weight: 600; padding: 14px 20px; margin: 0; border-bottom: 1px solid #e2e8f0; text-transform: uppercase; letter-spacing: 0.5px; }
    .section-content { padding: 5px 20px 15px 20px; }
    .event { padding: 15px 0; border-bottom: 1px solid #e2e8f0; }
    .event:last-child { border-bottom: none; }
    .event-date { font-weight: 700; color: #1a202c; font-size: 14px; letter-spacing: 0.5px; }
    .event-time { color: #718096; font-size: 14px; margin-left: 15px; font-weight: 400; }
    .event-title { color: #3182ce; font-size: 16px; margin-top: 6px; text-decoration: none; display: block; }
    .event-title:hover { text-decoration: underline; }
    a.event-title { color: #3182ce; }
    .event-location { color: #a0aec0; font-size: 13px; margin-top: 4px; font-style: italic; }
    .no-events { color: #a0aec0; font-style: italic; padding: 10px 0; }
    .footer { background-color: #f7fafc; padding: 25px 30px; text-align: center; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 8px 8px; }
    .regenerate-btn { display: inline-block; background-color: #3182ce; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; font-size: 14px; margin-bottom: 15px; }
    .regenerate-btn:hover { background-color: #2c5282; }
    .footer-text { font-size: 12px; color: #718096; margin-top: 10px; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Brandon Family Calendar Report</h1>
      <p>Generated on ${reportDate}</p>
    </div>
    <div class="content">
      ${sections.join("\n")}
    </div>
    <div class="footer">
      <a href="${regenerateUrl}" class="regenerate-btn">Regenerate Report</a>
      <div class="footer-text">Generated automatically by Brandon Family Calendar Automation</div>
    </div>
  </div>
</body>
</html>
`;
}

/**
 * Generate plain text email content
 */
function generateEmailText(sections, reportDate) {
  let text = `📅 WEEKLY CALENDAR REPORT\n`;
  text += `Generated on ${reportDate}\n`;
  text += `${"=".repeat(50)}\n\n`;

  // Parse sections to extract text (simplified version)
  text += "See HTML version for full details.\n";

  text += `\n${"=".repeat(50)}\n`;
  text += `Generated automatically by Brandon Family Calendar Automation\n`;
  text += `Next report: Next Saturday at 7:00pm ET\n`;

  return text;
}

/**
 * Send email via AWS SES
 */
async function sendEmail(htmlContent, textContent, eventCount) {
  const sesClient = new SESClient({ region: process.env.AWS_REGION });

  const toAddresses = process.env.EMAIL_TO.split(",").map((email) =>
    email.trim()
  );
  const fromAddress = process.env.EMAIL_FROM;

  const now = moment().tz(TIMEZONE);
  const subject = `Brandon Family Calendar Report - ${now.format("MMM D, YYYY")}`;

  const command = new SendEmailCommand({
    Destination: {
      ToAddresses: toAddresses,
    },
    Message: {
      Body: {
        Html: {
          Charset: "UTF-8",
          Data: htmlContent,
        },
        Text: {
          Charset: "UTF-8",
          Data: textContent,
        },
      },
      Subject: {
        Charset: "UTF-8",
        Data: subject,
      },
    },
    Source: fromAddress,
  });

  const response = await sesClient.send(command);
  console.log("Email sent successfully:", response.MessageId);
  return response;
}

/**
 * Lambda handler
 */
exports.handler = async (event, context) => {
  console.log("Starting Weekly Calendar Report generation");
  console.log("Event:", JSON.stringify(event));

  try {
    const calendar = await getCalendarClient();
    const now = moment().tz(TIMEZONE);
    const reportDate = now.format("dddd, MMMM D, YYYY [at] h:mm A z");

    // Generate all four sections
    const { sections, totalEvents } = await generateSections(calendar);
    console.log(`Total events found: ${totalEvents}`);

    // Generate email content
    const htmlContent = generateEmailHTML(sections, reportDate);
    const textContent = generateEmailText(sections, reportDate);

    // Send email
    await sendEmail(htmlContent, textContent, totalEvents);

    return {
      statusCode: 200,
      body: JSON.stringify({
        message: "Calendar report sent successfully",
        eventCount: totalEvents,
        timestamp: new Date().toISOString(),
      }),
    };
  } catch (error) {
    console.error("Error generating calendar report:", error);

    return {
      statusCode: 500,
      body: JSON.stringify({
        message: "Failed to generate calendar report",
        error: error.message,
      }),
    };
  }
};
