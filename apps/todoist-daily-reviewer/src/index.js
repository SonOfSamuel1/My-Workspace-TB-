/**
 * Daily Todoist Reviewer - Main Entry Point
 *
 * This module orchestrates the daily task review process:
 * 1. Fetch tasks from Todoist
 * 2. Analyze tasks with AI
 * 3. Generate HTML report
 * 4. Send email
 */

import 'dotenv/config';
import { TaskFetcher } from './task-fetcher.js';
import { AIAnalyzer } from './ai-analyzer.js';
import { CometAnalyzer } from './comet-analyzer.js';
import { ReportGenerator } from './report-generator.js';
import { SESEmailSender, LambdaSESEmailSender } from './ses-email-sender.js';
import { EmailSender, LambdaEmailSender } from './email-sender.js';
import config from '../config/reviewer-config.js';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Determine which email sender to use (SES preferred)
const USE_SES = process.env.USE_SES !== 'false'; // Default to true

/**
 * Main reviewer class
 */
export class TodoistDailyReviewer {
  constructor(options = {}) {
    this.config = { ...config, ...options };
    this.isLambda = !!process.env.AWS_LAMBDA_FUNCTION_NAME;
  }

  /**
   * Run the complete daily review
   */
  async run() {
    const startTime = Date.now();
    console.log('Starting Daily Todoist Review...');
    console.log(`Environment: ${this.isLambda ? 'AWS Lambda' : 'Local'}`);

    try {
      // Validate configuration
      this.validateConfig();

      // Step 1: Fetch tasks
      console.log('\n[1/4] Fetching tasks from Todoist...');
      const taskData = await this.fetchTasks();
      console.log(`Found ${taskData.all.length} tasks to review`);

      // Step 2: Analyze tasks
      console.log('\n[2/4] Analyzing tasks with AI and Comet...');
      const analysis = await this.analyzeTasks(taskData);
      console.log(`AI (Claude) can help with ${analysis.summary.aiAssistable} tasks`);
      console.log(`Comet browser can help with ${analysis.comet?.delegableCount || 0} tasks`);
      console.log(`Analysis method: ${analysis.analysisMethod || 'pattern-matching'}`);

      // Step 3: Generate report
      console.log('\n[3/4] Generating HTML report...');
      const { htmlReport, taskMappings } = this.generateReport(taskData, analysis);
      console.log(`Report generated (${htmlReport.length} bytes)`);

      // Save task mappings for reply poller
      await this.saveTaskMappings(taskMappings);
      console.log(`Saved task mappings for ${Object.keys(taskMappings).length} tasks`);

      // Step 4: Send email
      console.log('\n[4/4] Sending email...');
      const emailResult = await this.sendEmail(htmlReport);
      console.log(`Email sent to ${this.config.email.recipient}`);

      const duration = Date.now() - startTime;
      console.log(`\nDaily review completed in ${duration}ms`);

      return {
        success: true,
        stats: {
          totalTasks: taskData.all.length,
          aiAssistable: analysis.summary.aiAssistable,
          highPriority: taskData.highPriority.length,
          overdue: taskData.overdue.length
        },
        emailResult,
        duration
      };

    } catch (error) {
      console.error('\nDaily review failed:', error.message);
      throw error;
    }
  }

  /**
   * Validate configuration
   */
  validateConfig() {
    const required = [
      { key: 'TODOIST_API_TOKEN', env: process.env.TODOIST_API_TOKEN },
      { key: 'TODOIST_REVIEW_EMAIL', env: this.config.email.recipient || process.env.TODOIST_REVIEW_EMAIL }
    ];

    const missing = required.filter(r => !r.env);

    if (missing.length > 0) {
      throw new Error(`Missing required configuration: ${missing.map(m => m.key).join(', ')}`);
    }

    // Email credentials check
    if (USE_SES) {
      // SES uses IAM credentials automatically
      console.log('Using AWS SES for email delivery');
    } else if (!process.env.GMAIL_OAUTH_CREDENTIALS && !process.env.GOOGLE_CREDENTIALS_FILE) {
      console.warn('Warning: Gmail credentials not configured. Email sending may fail.');
    }
  }

  /**
   * Fetch tasks from Todoist
   */
  async fetchTasks() {
    const fetcher = new TaskFetcher(
      process.env.TODOIST_API_TOKEN,
      this.config.todoist
    );

    return fetcher.fetchTasksForReview();
  }

  /**
   * Analyze tasks with AI and Comet
   */
  async analyzeTasks(taskData) {
    // AI analysis (Claude)
    const aiAnalyzer = new AIAnalyzer(this.config.ai);
    const aiAnalysis = await aiAnalyzer.analyzeTasksForReview(taskData);

    // Comet browser analysis
    const cometAnalyzer = new CometAnalyzer(this.config.ai?.cometBrowser);
    const cometAnalysis = cometAnalyzer.analyzeTasks(taskData);

    // Merge analyses - add Comet data to each task and to overall analysis
    return this.mergeAnalyses(aiAnalysis, cometAnalysis);
  }

  /**
   * Merge AI and Comet analyses
   */
  mergeAnalyses(aiAnalysis, cometAnalysis) {
    // Create a map of Comet analysis by task ID
    const cometMap = new Map(
      cometAnalysis.tasks.map(t => [t.task.id, t])
    );

    // Add Comet data to each task in AI analysis
    for (const task of aiAnalysis.tasks) {
      const cometData = cometMap.get(task.task.id);
      if (cometData && cometData.cometCanHelp) {
        task.cometCanHelp = true;
        task.cometCategory = cometData.cometCategory;
        task.cometCategoryName = cometData.cometCategoryName;
        task.cometCapability = cometData.cometCapability;
        task.cometPrompt = cometData.cometPrompt;
        task.cometConfidence = cometData.confidence;
        task.cometEstimatedTime = cometData.estimatedTime;
      }
    }

    // Also add Comet data to AI opportunities
    for (const opp of aiAnalysis.aiOpportunities) {
      const cometData = cometMap.get(opp.task.id);
      if (cometData && cometData.cometCanHelp) {
        opp.cometCanHelp = true;
        opp.cometCategory = cometData.cometCategory;
        opp.cometCategoryName = cometData.cometCategoryName;
        opp.cometCapability = cometData.cometCapability;
        opp.cometPrompt = cometData.cometPrompt;
      }
    }

    // Add Comet summary to analysis
    aiAnalysis.comet = {
      enabled: cometAnalysis.enabled,
      delegableCount: cometAnalysis.summary.cometDelegable,
      byCategory: cometAnalysis.summary.byCategory,
      totalTimeSavings: cometAnalysis.summary.totalTimeSavings,
      opportunities: cometAnalysis.cometOpportunities
    };

    return aiAnalysis;
  }

  /**
   * Generate HTML report
   */
  generateReport(taskData, analysis) {
    const generator = new ReportGenerator(this.config.email);
    const htmlReport = generator.generateReport(taskData, analysis);
    const taskMappings = generator.getTaskMappings();
    return { htmlReport, taskMappings };
  }

  /**
   * Save task mappings to file for reply poller
   */
  async saveTaskMappings(taskMappings) {
    const dataDir = path.join(__dirname, '..', 'data');
    const mappingsFile = path.join(dataDir, 'task-mappings.json');

    await fs.mkdir(dataDir, { recursive: true });
    await fs.writeFile(mappingsFile, JSON.stringify(taskMappings, null, 2), 'utf8');
  }

  /**
   * Send email report
   */
  async sendEmail(htmlReport) {
    const date = new Date().toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });

    const subject = this.config.email.subjectTemplate.replace('{date}', date);
    const recipient = this.config.email.recipient || process.env.TODOIST_REVIEW_EMAIL;

    // Use SES (preferred) or Gmail as fallback
    if (USE_SES) {
      if (this.isLambda) {
        const sender = new LambdaSESEmailSender();
        return sender.send(recipient, subject, htmlReport);
      } else {
        const sender = new SESEmailSender({
          region: process.env.AWS_REGION || 'us-east-1',
          senderEmail: process.env.SES_SENDER_EMAIL || 'brandonhome.appdev@gmail.com'
        });
        return sender.sendHtmlEmail({
          to: recipient,
          subject,
          htmlContent: htmlReport
        });
      }
    } else {
      // Fallback to Gmail API
      if (this.isLambda) {
        const sender = new LambdaEmailSender();
        return sender.send(recipient, subject, htmlReport);
      } else {
        const sender = new EmailSender({
          credentialsPath: process.env.GOOGLE_CREDENTIALS_FILE,
          tokenPath: process.env.GOOGLE_TOKEN_FILE
        });
        return sender.sendHtmlEmail({
          to: recipient,
          subject,
          htmlContent: htmlReport
        });
      }
    }
  }

  /**
   * Generate report without sending (for testing)
   */
  async generateOnly() {
    console.log('Generating report (no email)...');

    const taskData = await this.fetchTasks();
    const analysis = await this.analyzeTasks(taskData);
    const { htmlReport, taskMappings } = this.generateReport(taskData, analysis);

    // Save task mappings even in generate-only mode
    await this.saveTaskMappings(taskMappings);

    return {
      taskData,
      analysis,
      htmlReport,
      taskMappings
    };
  }

  /**
   * Preview tasks (for debugging)
   */
  async previewTasks() {
    const taskData = await this.fetchTasks();
    const analysis = await this.analyzeTasks(taskData);

    console.log('\n=== TASK PREVIEW ===\n');
    console.log(`Total Tasks: ${taskData.all.length}`);
    console.log(`High Priority: ${taskData.highPriority.length}`);
    console.log(`Overdue: ${taskData.overdue.length}`);
    console.log(`AI Can Help: ${analysis.summary.aiAssistable}`);

    console.log('\n--- AI Opportunities ---');
    for (const opp of analysis.aiOpportunities.slice(0, 5)) {
      console.log(`\n[${opp.task.priorityLabel}] ${opp.task.content}`);
      console.log(`  Category: ${opp.category}`);
      console.log(`  Suggestion: ${opp.suggestion}`);
    }

    console.log('\n--- Recommendations ---');
    for (const rec of analysis.recommendations) {
      console.log(`\n${rec.title}`);
      console.log(`  ${rec.description}`);
    }

    return { taskData, analysis };
  }
}

/**
 * Lambda handler
 */
export async function handler(event, context) {
  console.log('Lambda invocation started', {
    requestId: context?.awsRequestId,
    event: JSON.stringify(event)
  });

  try {
    const reviewer = new TodoistDailyReviewer();
    const result = await reviewer.run();

    return {
      statusCode: 200,
      body: JSON.stringify({
        success: true,
        ...result
      })
    };
  } catch (error) {
    console.error('Lambda execution failed:', error);

    return {
      statusCode: 500,
      body: JSON.stringify({
        success: false,
        error: error.message
      })
    };
  }
}

/**
 * CLI entry point
 */
async function main() {
  const args = process.argv.slice(2);
  const command = args[0] || 'run';

  const reviewer = new TodoistDailyReviewer();

  switch (command) {
    case 'run':
      await reviewer.run();
      break;

    case 'preview':
      await reviewer.previewTasks();
      break;

    case 'generate':
      const { htmlReport } = await reviewer.generateOnly();
      // Save to file
      const fs = await import('fs');
      const outputPath = `output/daily-review-${Date.now()}.html`;
      fs.mkdirSync('output', { recursive: true });
      fs.writeFileSync(outputPath, htmlReport);
      console.log(`Report saved to: ${outputPath}`);
      break;

    case 'validate':
      try {
        reviewer.validateConfig();
        console.log('Configuration is valid!');

        // Test Todoist connection
        const taskData = await reviewer.fetchTasks();
        console.log(`Todoist connected: ${taskData.all.length} tasks found`);

        // Test email connection
        if (USE_SES) {
          const sender = new SESEmailSender({
            region: process.env.AWS_REGION || 'us-east-1',
            senderEmail: process.env.SES_SENDER_EMAIL || 'brandonhome.appdev@gmail.com'
          });
          const validation = await sender.validateCredentials();
          if (validation.valid) {
            console.log(`AWS SES connected (quota: ${validation.quota.sentLast24Hours}/${validation.quota.max24HourSend})`);
          } else {
            console.warn(`SES validation failed: ${validation.error}`);
          }
        } else if (process.env.GOOGLE_CREDENTIALS_FILE) {
          const sender = new EmailSender({
            credentialsPath: process.env.GOOGLE_CREDENTIALS_FILE,
            tokenPath: process.env.GOOGLE_TOKEN_FILE
          });
          const validation = await sender.validateCredentials();
          if (validation.valid) {
            console.log(`Gmail connected: ${validation.email}`);
          } else {
            console.warn(`Gmail validation failed: ${validation.error}`);
          }
        }
      } catch (error) {
        console.error('Validation failed:', error.message);
        process.exit(1);
      }
      break;

    default:
      console.log(`
Daily Todoist Reviewer

Usage:
  node src/index.js [command]

Commands:
  run       Run the daily review and send email (default)
  preview   Preview tasks without sending email
  generate  Generate HTML report and save to file
  validate  Validate configuration and connections
      `);
  }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

export default TodoistDailyReviewer;
