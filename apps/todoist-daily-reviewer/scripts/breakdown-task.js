#!/usr/bin/env node

/**
 * Breakdown Task Script
 *
 * Uses Claude Code CLI to break down a task into subtasks, then creates them in Todoist.
 * Usage: node breakdown-task.js <taskId>
 */

import 'dotenv/config';
import { spawn } from 'child_process';

const TODOIST_API_TOKEN = process.env.TODOIST_API_TOKEN;
const TODOIST_API_URL = 'https://api.todoist.com/rest/v2';

/**
 * Fetch task details from Todoist
 */
async function getTask(taskId) {
  const response = await fetch(`${TODOIST_API_URL}/tasks/${taskId}`, {
    headers: {
      'Authorization': `Bearer ${TODOIST_API_TOKEN}`
    }
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch task: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

/**
 * Create a subtask in Todoist
 */
async function createSubtask(parentId, content, projectId) {
  const response = await fetch(`${TODOIST_API_URL}/tasks`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${TODOIST_API_TOKEN}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      content,
      parent_id: parentId,
      project_id: projectId
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to create subtask: ${response.status} ${errorText}`);
  }

  return response.json();
}

/**
 * Run Claude Code CLI to get subtask suggestions
 */
function getClaudeBreakdown(task) {
  return new Promise((resolve, reject) => {
    const prompt = `Break down this task into 3-7 clear, actionable subtasks.

Task: "${task.content}"
${task.description ? `Description: ${task.description}` : ''}
${task.project_id ? `Project ID: ${task.project_id}` : ''}

Create subtasks that are:
- Specific and actionable
- Small enough to complete in one session
- Ordered logically (what to do first)

Respond with ONLY valid JSON, no explanation:
{
  "subtasks": [
    {"content": "First step: specific action", "estimatedMinutes": 15},
    {"content": "Second step: specific action", "estimatedMinutes": 30}
  ],
  "reasoning": "Brief explanation of the breakdown"
}`;

    const claude = spawn('claude', ['--print', '-p', prompt], {
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env }
    });

    let stdout = '';
    let stderr = '';

    claude.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    claude.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    claude.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Claude CLI exited with code ${code}: ${stderr}`));
      } else {
        // Try to parse JSON from response
        try {
          const jsonMatch = stdout.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            resolve(JSON.parse(jsonMatch[0]));
          } else {
            reject(new Error('No JSON found in Claude response'));
          }
        } catch (parseError) {
          reject(new Error(`Failed to parse Claude response: ${parseError.message}`));
        }
      }
    });

    claude.on('error', (err) => {
      reject(new Error(`Failed to spawn Claude CLI: ${err.message}`));
    });

    // 2 minute timeout
    setTimeout(() => {
      claude.kill();
      reject(new Error('Claude CLI timed out after 2 minutes'));
    }, 120000);
  });
}

/**
 * Main function to break down a task
 */
async function breakdownTask(taskId) {
  if (!taskId) {
    throw new Error('Task ID is required');
  }

  if (!TODOIST_API_TOKEN) {
    throw new Error('TODOIST_API_TOKEN environment variable is not set');
  }

  console.log(`Breaking down task ${taskId}...`);

  // Get the task details
  const task = await getTask(taskId);
  console.log(`Task: "${task.content}"`);

  // Get Claude's breakdown
  console.log('Asking Claude for breakdown suggestions...');
  const breakdown = await getClaudeBreakdown(task);
  console.log(`Claude suggested ${breakdown.subtasks.length} subtasks`);

  // Create subtasks in Todoist
  const createdSubtasks = [];
  for (const subtask of breakdown.subtasks) {
    console.log(`  Creating: ${subtask.content}`);
    const created = await createSubtask(taskId, subtask.content, task.project_id);
    createdSubtasks.push({
      id: created.id,
      content: created.content
    });
  }

  return {
    success: true,
    taskId,
    taskContent: task.content,
    subtasksCreated: createdSubtasks.length,
    subtasks: createdSubtasks,
    reasoning: breakdown.reasoning,
    message: `Task "${task.content}" has been broken down into ${createdSubtasks.length} subtasks.`
  };
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const taskId = process.argv[2];

  if (!taskId) {
    console.error('Usage: node breakdown-task.js <taskId>');
    process.exit(1);
  }

  breakdownTask(taskId)
    .then(result => {
      console.log('\nSuccess:', result.message);
      console.log('\nCreated subtasks:');
      result.subtasks.forEach((st, i) => {
        console.log(`  ${i + 1}. ${st.content}`);
      });
      if (result.reasoning) {
        console.log('\nReasoning:', result.reasoning);
      }
    })
    .catch(error => {
      console.error('Error:', error.message);
      process.exit(1);
    });
}

export { breakdownTask };
