/**
 * AWS Lambda Handler for Daily Todoist Reviewer
 *
 * This Lambda function runs daily to:
 * 1. Fetch high-priority tasks from Todoist
 * 2. Analyze tasks for AI assistance opportunities
 * 3. Generate a beautiful HTML report
 * 4. Send the report via Gmail
 */

import { TodoistDailyReviewer, handler as mainHandler } from './src/index.js';

/**
 * Lambda handler
 */
export const handler = async (event, context) => {
  console.log('='.repeat(60));
  console.log('Daily Todoist Reviewer - Lambda Execution');
  console.log('='.repeat(60));
  console.log(`Request ID: ${context.awsRequestId}`);
  console.log(`Function: ${context.functionName}`);
  console.log(`Remaining Time: ${context.getRemainingTimeInMillis()}ms`);
  console.log(`Event: ${JSON.stringify(event)}`);

  // Get current time in EST
  const estTime = new Date().toLocaleString('en-US', {
    timeZone: 'America/New_York',
    dateStyle: 'full',
    timeStyle: 'long'
  });
  console.log(`Execution Time (EST): ${estTime}`);

  try {
    // Run the main handler
    const result = await mainHandler(event, context);

    console.log('\n' + '='.repeat(60));
    console.log('Execution Summary');
    console.log('='.repeat(60));
    console.log(`Status: ${result.statusCode === 200 ? 'SUCCESS' : 'FAILED'}`);

    if (result.statusCode === 200) {
      const body = JSON.parse(result.body);
      console.log(`Tasks Reviewed: ${body.stats?.totalTasks || 0}`);
      console.log(`AI Assistable: ${body.stats?.aiAssistable || 0}`);
      console.log(`High Priority: ${body.stats?.highPriority || 0}`);
      console.log(`Overdue: ${body.stats?.overdue || 0}`);
      console.log(`Duration: ${body.duration}ms`);
    }

    return result;

  } catch (error) {
    console.error('\n' + '='.repeat(60));
    console.error('EXECUTION FAILED');
    console.error('='.repeat(60));
    console.error(`Error: ${error.message}`);
    console.error(`Stack: ${error.stack}`);

    return {
      statusCode: 500,
      body: JSON.stringify({
        success: false,
        error: error.message,
        requestId: context.awsRequestId
      })
    };
  }
};
