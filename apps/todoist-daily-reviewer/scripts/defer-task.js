#!/usr/bin/env node

/**
 * Defer Task Script
 *
 * Reschedules a Todoist task to a new date.
 * Usage: node defer-task.js <taskId> <dateString>
 *
 * Date examples: tomorrow, monday, next week, 2024-12-01
 */

import 'dotenv/config';

const TODOIST_API_TOKEN = process.env.TODOIST_API_TOKEN;
const TODOIST_API_URL = 'https://api.todoist.com/rest/v2';

/**
 * Parse a natural language date string into Todoist due_string format
 */
function parseDateString(input) {
  const normalized = input.toLowerCase().trim();

  // Common natural language dates that Todoist understands
  const naturalDates = [
    'today', 'tomorrow', 'monday', 'tuesday', 'wednesday',
    'thursday', 'friday', 'saturday', 'sunday',
    'next week', 'next monday', 'next tuesday', 'next wednesday',
    'next thursday', 'next friday', 'next saturday', 'next sunday',
    'in 2 days', 'in 3 days', 'in a week', 'end of week', 'end of month'
  ];

  // Check if it's a natural language date
  if (naturalDates.some(d => normalized.includes(d) || normalized === d)) {
    return normalized;
  }

  // Check if it's a date format (YYYY-MM-DD)
  if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
    return normalized;
  }

  // Check for common abbreviations
  const dayAbbreviations = {
    'mon': 'monday',
    'tue': 'tuesday',
    'wed': 'wednesday',
    'thu': 'thursday',
    'fri': 'friday',
    'sat': 'saturday',
    'sun': 'sunday'
  };

  for (const [abbr, full] of Object.entries(dayAbbreviations)) {
    if (normalized === abbr) {
      return full;
    }
  }

  // Default: pass through to Todoist (it has good natural language parsing)
  return normalized;
}

async function deferTask(taskId, dateString) {
  if (!taskId) {
    throw new Error('Task ID is required');
  }

  if (!dateString) {
    throw new Error('Date string is required (e.g., "tomorrow", "monday", "next week")');
  }

  if (!TODOIST_API_TOKEN) {
    throw new Error('TODOIST_API_TOKEN environment variable is not set');
  }

  const dueString = parseDateString(dateString);
  console.log(`Deferring task ${taskId} to "${dueString}"...`);

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
  const oldDue = task.due?.date || 'no due date';

  // Update the task with new due date
  const updateResponse = await fetch(`${TODOIST_API_URL}/tasks/${taskId}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${TODOIST_API_TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      due_string: dueString
    })
  });

  if (!updateResponse.ok) {
    const errorText = await updateResponse.text();
    throw new Error(`Failed to defer task: ${updateResponse.status} ${errorText}`);
  }

  const updatedTask = await updateResponse.json();

  return {
    success: true,
    taskId,
    taskContent: task.content,
    oldDue,
    newDue: updatedTask.due?.date || dueString,
    message: `Task "${task.content}" has been rescheduled from ${oldDue} to ${updatedTask.due?.date || dueString}.`
  };
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const taskId = process.argv[2];
  const dateString = process.argv.slice(3).join(' ');

  if (!taskId || !dateString) {
    console.error('Usage: node defer-task.js <taskId> <dateString>');
    console.error('Examples:');
    console.error('  node defer-task.js abc123 tomorrow');
    console.error('  node defer-task.js abc123 next monday');
    console.error('  node defer-task.js abc123 2024-12-15');
    process.exit(1);
  }

  deferTask(taskId, dateString)
    .then(result => {
      console.log('Success:', result.message);
      console.log(JSON.stringify(result, null, 2));
    })
    .catch(error => {
      console.error('Error:', error.message);
      process.exit(1);
    });
}

export { deferTask };
