#!/usr/bin/env node

/**
 * Script to create Gmail labels for Executive Email Assistant
 * Uses the authenticated Gmail credentials from ~/.gmail-mcp/
 */

const fs = require('fs');
const path = require('path');
const { google } = require('googleapis');

// Labels to create
const LABELS = [
  'Action Required',
  'To Read',  // Changed from "Read" - Gmail reserves that term
  'Waiting For',
  'Completed',  // Changed from "Archive/Archived" - Gmail reserves those terms
  'VIP',
  'Meetings',
  'Travel',
  'Expenses',
  'Newsletters'
];

async function createLabels() {
  try {
    // Load credentials
    const credentialsPath = path.join(process.env.HOME, '.gmail-mcp', 'credentials.json');
    const keysPath = path.join(process.env.HOME, '.gmail-mcp', 'gcp-oauth.keys.json');

    if (!fs.existsSync(credentialsPath)) {
      console.error('Error: credentials.json not found at', credentialsPath);
      process.exit(1);
    }

    if (!fs.existsSync(keysPath)) {
      console.error('Error: gcp-oauth.keys.json not found at', keysPath);
      process.exit(1);
    }

    const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
    const keys = JSON.parse(fs.readFileSync(keysPath, 'utf8'));

    // Set up OAuth2 client
    const oauth2Client = new google.auth.OAuth2(
      keys.installed.client_id,
      keys.installed.client_secret,
      keys.installed.redirect_uris[0]
    );

    oauth2Client.setCredentials(credentials);

    // Create Gmail API client
    const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

    console.log('Connected to Gmail API');
    console.log('Creating labels for terrance@goodportion.org...\n');

    // Get existing labels first
    const existingLabelsResponse = await gmail.users.labels.list({
      userId: 'me'
    });

    const existingLabels = existingLabelsResponse.data.labels || [];
    const existingLabelNames = existingLabels.map(l => l.name);

    console.log('Existing labels:', existingLabelNames.length);

    // Create each label
    let created = 0;
    let skipped = 0;

    for (const labelName of LABELS) {
      if (existingLabelNames.includes(labelName)) {
        console.log(`⏭️  Skipped: "${labelName}" (already exists)`);
        skipped++;
      } else {
        try {
          await gmail.users.labels.create({
            userId: 'me',
            requestBody: {
              name: labelName,
              labelListVisibility: 'labelShow',
              messageListVisibility: 'show'
            }
          });
          console.log(`✅ Created: "${labelName}"`);
          created++;
        } catch (error) {
          console.error(`❌ Failed to create "${labelName}":`, error.message);
        }
      }
    }

    console.log('\n---');
    console.log(`✅ Labels created: ${created}`);
    console.log(`⏭️  Labels skipped: ${skipped}`);
    console.log(`📊 Total labels: ${created + skipped}/${LABELS.length}`);
    console.log('\nAll set! Your Gmail labels are ready for the Executive Email Assistant.');

  } catch (error) {
    console.error('Error:', error.message);
    process.exit(1);
  }
}

// Run the script
createLabels();
