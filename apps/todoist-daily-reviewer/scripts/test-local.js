#!/usr/bin/env node
/**
 * Local testing script for Daily Todoist Reviewer
 *
 * Usage:
 *   node scripts/test-local.js [command]
 *
 * Commands:
 *   preview   - Preview tasks without sending email (default)
 *   generate  - Generate HTML report and open in browser
 *   send      - Run full review and send email
 *   validate  - Validate configuration
 */

import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { config } from 'dotenv';
import { exec } from 'child_process';

// Load .env file
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
config({ path: join(__dirname, '..', '.env') });

// Import the reviewer
const { TodoistDailyReviewer } = await import('../src/index.js');

async function main() {
  const command = process.argv[2] || 'preview';

  console.log('='.repeat(60));
  console.log('Daily Todoist Reviewer - Local Test');
  console.log('='.repeat(60));
  console.log(`Command: ${command}`);
  console.log(`Time: ${new Date().toLocaleString()}`);
  console.log('');

  const reviewer = new TodoistDailyReviewer();

  try {
    switch (command) {
      case 'preview':
        await reviewer.previewTasks();
        break;

      case 'generate':
        console.log('Generating report...');
        const { htmlReport, analysis, taskData } = await reviewer.generateOnly();

        // Save to file
        const fs = await import('fs');
        const outputDir = join(__dirname, '..', 'output');
        fs.mkdirSync(outputDir, { recursive: true });

        const outputPath = join(outputDir, `daily-review-${Date.now()}.html`);
        fs.writeFileSync(outputPath, htmlReport);

        console.log(`\nReport saved to: ${outputPath}`);
        console.log(`Total tasks: ${taskData.all.length}`);
        console.log(`AI assistable: ${analysis.summary.aiAssistable}`);

        // Open in default browser (macOS)
        exec(`open "${outputPath}"`);
        break;

      case 'send':
        console.log('Running full review with email...');
        const result = await reviewer.run();
        console.log('\nResult:', JSON.stringify(result, null, 2));
        break;

      case 'validate':
        console.log('Validating configuration...');
        reviewer.validateConfig();
        console.log('Configuration valid!');

        console.log('\nTesting Todoist connection...');
        const tasks = await reviewer.fetchTasks();
        console.log(`Connected! Found ${tasks.all.length} tasks.`);

        console.log('\nConfiguration:');
        console.log(`  Recipient: ${process.env.TODOIST_REVIEW_EMAIL || 'Not set'}`);
        console.log(`  Todoist Token: ${process.env.TODOIST_API_TOKEN ? 'Set' : 'Not set'}`);
        console.log(`  Gmail OAuth: ${process.env.GMAIL_OAUTH_CREDENTIALS || process.env.GOOGLE_CREDENTIALS_FILE ? 'Set' : 'Not set'}`);
        break;

      default:
        console.log(`Unknown command: ${command}`);
        console.log('\nAvailable commands:');
        console.log('  preview   - Preview tasks without sending email');
        console.log('  generate  - Generate HTML report and open in browser');
        console.log('  send      - Run full review and send email');
        console.log('  validate  - Validate configuration');
    }

  } catch (error) {
    console.error('\nError:', error.message);
    if (process.env.DEBUG) {
      console.error(error.stack);
    }
    process.exit(1);
  }
}

main();
