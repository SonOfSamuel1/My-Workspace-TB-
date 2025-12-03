#!/usr/bin/env node

/**
 * Complete Task Script
 *
 * Marks a Todoist task as complete using the Todoist API.
 * Usage: node complete-task.js <taskId>
 */

import 'dotenv/config';

const TODOIST_API_TOKEN = process.env.TODOIST_API_TOKEN;
const TODOIST_API_URL = 'https://api.todoist.com/rest/v2';

async function completeTask(taskId) {
  if (!taskId) {
    throw new Error('Task ID is required');
  }

  if (!TODOIST_API_TOKEN) {
    throw new Error('TODOIST_API_TOKEN environment variable is not set');
  }

  console.log(`Completing task ${taskId}...`);

  // First, get the task details for confirmation
  const taskResponse = await fetch(`${TODOIST_API_URL}/tasks/${taskId}`, {
    headers: {
      'Authorization': `Bearer ${TODOIST_API_TOKEN}`
    }
  });

  if (!taskResponse.ok) {
    throw new Error(`Failed to fetch task: ${taskResponse.status} ${taskResponse.statusText}`);
  }

  const task = await taskResponse.json();

  // Close (complete) the task
  const closeResponse = await fetch(`${TODOIST_API_URL}/tasks/${taskId}/close`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${TODOIST_API_TOKEN}`
    }
  });

  if (!closeResponse.ok) {
    throw new Error(`Failed to complete task: ${closeResponse.status} ${closeResponse.statusText}`);
  }

  return {
    success: true,
    taskId,
    taskContent: task.content,
    message: `Task "${task.content}" has been marked as complete.`
  };
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const taskId = process.argv[2];

  if (!taskId) {
    console.error('Usage: node complete-task.js <taskId>');
    process.exit(1);
  }

  completeTask(taskId)
    .then(result => {
      console.log('Success:', result.message);
      console.log(JSON.stringify(result, null, 2));
    })
    .catch(error => {
      console.error('Error:', error.message);
      process.exit(1);
    });
}

export { completeTask };
