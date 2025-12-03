#!/usr/bin/env node

/**
 * Claude Code CLI Task Analyzer
 *
 * Spawns Claude Code CLI to analyze tasks using real AI intelligence.
 * Uses the `claude` command with --print flag for non-interactive output.
 * No API key needed - uses your Cursor/Claude Code subscription.
 */

import { spawn } from 'child_process';
import { promisify } from 'util';

const ANALYSIS_PROMPT = `You are analyzing Todoist tasks to determine which ones you (Claude) can help complete.

For each task, analyze:
1. Whether AI can meaningfully assist (consider if it requires physical presence, real-time interaction, or is too personal)
2. The category of the task (research, communication, coding, writing, admin, planning, analysis, dataWork, physical, personal, or general)
3. A specific, personalized suggestion for how you can help (not generic templates)
4. Estimated time in minutes the task would take
5. Confidence score (0.0-1.0) for your assessment
6. 2-4 specific action items you could perform

Respond with ONLY valid JSON in this exact format (no markdown, no explanation):
{
  "analyses": [
    {
      "taskId": "string",
      "aiCanHelp": boolean,
      "category": "string",
      "suggestion": "string (personalized, specific to this task)",
      "estimatedTime": number,
      "estimatedTimeSavings": number,
      "confidenceScore": number,
      "reasoning": "string (brief explanation)",
      "actionItems": ["string", "string", ...]
    }
  ]
}

IMPORTANT:
- Be conservative - if unsure, set aiCanHelp to false
- Tasks involving calls, meetings, gym, doctor, shopping, family = aiCanHelp: false
- Research, writing, coding, email drafting, planning, analysis = aiCanHelp: true
- Make suggestions SPECIFIC to each task, not generic templates`;

/**
 * Spawn Claude Code CLI and get analysis
 * @param {Array} tasks - Array of task objects to analyze
 * @returns {Promise<Object>} - Analysis results
 */
export async function analyzeWithClaude(tasks) {
  if (!tasks || tasks.length === 0) {
    return { analyses: [] };
  }

  // Format tasks for the prompt
  const taskList = tasks.map((task, index) => {
    const parts = [
      `${index + 1}. [ID: ${task.id}]`,
      `"${task.content}"`,
      `(Priority: ${task.priorityLabel || 'Normal'}`,
    ];

    if (task.due?.date) {
      parts.push(`Due: ${task.due.date}`);
    }
    if (task.project?.name) {
      parts.push(`Project: ${task.project.name}`);
    }
    parts[parts.length - 1] += ')';

    if (task.description) {
      parts.push(`\n   Description: ${task.description}`);
    }

    return parts.join(' ');
  }).join('\n');

  const fullPrompt = `${ANALYSIS_PROMPT}

Here are the tasks to analyze:

${taskList}

Remember: Respond with ONLY valid JSON, no other text.`;

  try {
    const result = await runClaudeCLI(fullPrompt);
    return parseAnalysisResult(result, tasks);
  } catch (error) {
    console.error('Claude CLI analysis failed:', error.message);
    // Fall back to pattern matching if Claude fails
    return null;
  }
}

/**
 * Run Claude Code CLI with a prompt
 * @param {string} prompt - The prompt to send to Claude
 * @returns {Promise<string>} - Claude's response
 */
function runClaudeCLI(prompt) {
  return new Promise((resolve, reject) => {
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
        resolve(stdout.trim());
      }
    });

    claude.on('error', (err) => {
      reject(new Error(`Failed to spawn Claude CLI: ${err.message}`));
    });

    // Set a timeout of 2 minutes
    setTimeout(() => {
      claude.kill();
      reject(new Error('Claude CLI timed out after 2 minutes'));
    }, 120000);
  });
}

/**
 * Parse Claude's analysis result
 * @param {string} result - Raw result from Claude
 * @param {Array} originalTasks - Original task array for fallback data
 * @returns {Object} - Parsed analysis
 */
function parseAnalysisResult(result, originalTasks) {
  try {
    // Try to extract JSON from the response (in case there's extra text)
    let jsonStr = result;

    // Look for JSON object pattern
    const jsonMatch = result.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      jsonStr = jsonMatch[0];
    }

    const parsed = JSON.parse(jsonStr);

    // Validate and enrich with original task data
    if (parsed.analyses && Array.isArray(parsed.analyses)) {
      parsed.analyses = parsed.analyses.map(analysis => {
        const originalTask = originalTasks.find(t => t.id === analysis.taskId);
        return {
          ...analysis,
          task: originalTask ? {
            id: originalTask.id,
            content: originalTask.content,
            description: originalTask.description,
            priority: originalTask.priority,
            priorityLabel: originalTask.priorityLabel,
            dueDate: originalTask.due?.date,
            daysUntilDue: originalTask.daysUntilDue,
            isOverdue: originalTask.isOverdue,
            project: originalTask.project?.name,
            labels: originalTask.labels,
            url: originalTask.url
          } : null,
          analysisMethod: 'claude-cli'
        };
      });
    }

    return parsed;
  } catch (error) {
    console.error('Failed to parse Claude response:', error.message);
    console.error('Raw response:', result.substring(0, 500));
    return null;
  }
}

/**
 * Analyze a single task with Claude (for actions like "help with task X")
 * @param {Object} task - Task to analyze in detail
 * @param {string} actionType - Type of help requested (breakdown, help, etc.)
 * @returns {Promise<Object>} - Detailed analysis/suggestions
 */
export async function analyzeTaskDetailed(task, actionType = 'help') {
  const prompts = {
    breakdown: `Break down this task into 3-7 clear, actionable subtasks:

Task: "${task.content}"
${task.description ? `Description: ${task.description}` : ''}
${task.project?.name ? `Project: ${task.project.name}` : ''}

Respond with ONLY valid JSON:
{
  "subtasks": [
    {"content": "string", "estimatedMinutes": number},
    ...
  ],
  "reasoning": "string"
}`,

    help: `Provide detailed guidance on how to complete this task:

Task: "${task.content}"
${task.description ? `Description: ${task.description}` : ''}
${task.project?.name ? `Project: ${task.project.name}` : ''}

Respond with ONLY valid JSON:
{
  "summary": "string (1-2 sentence overview)",
  "steps": ["string", "string", ...],
  "resources": ["string (optional helpful links or references)", ...],
  "tips": ["string (pro tips)", ...],
  "estimatedTime": number
}`,

    research: `Research this topic and provide key findings:

Task: "${task.content}"
${task.description ? `Description: ${task.description}` : ''}

Respond with ONLY valid JSON:
{
  "summary": "string",
  "keyFindings": ["string", ...],
  "recommendations": ["string", ...],
  "sources": ["string (general sources to check)", ...]
}`
  };

  const prompt = prompts[actionType] || prompts.help;

  try {
    const result = await runClaudeCLI(prompt);
    const jsonMatch = result.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      return JSON.parse(jsonMatch[0]);
    }
    return JSON.parse(result);
  } catch (error) {
    console.error(`Claude CLI ${actionType} analysis failed:`, error.message);
    return null;
  }
}

// CLI entry point for testing
if (import.meta.url === `file://${process.argv[1]}`) {
  const testTasks = [
    {
      id: 'test1',
      content: 'Research competitor pricing strategies',
      description: 'Need to understand how competitors price their SaaS products',
      priority: 3,
      priorityLabel: 'High',
      due: { date: '2024-11-28' },
      project: { name: 'Business Development' }
    },
    {
      id: 'test2',
      content: 'Call dentist to schedule appointment',
      priority: 2,
      priorityLabel: 'Medium',
      due: { date: '2024-11-27' },
      project: { name: 'Personal' }
    },
    {
      id: 'test3',
      content: 'Write blog post about AI productivity',
      description: 'Focus on how AI tools can help with daily task management',
      priority: 3,
      priorityLabel: 'High',
      project: { name: 'Marketing' }
    }
  ];

  console.log('Testing Claude Code CLI integration...\n');

  analyzeWithClaude(testTasks)
    .then(result => {
      console.log('Analysis Result:');
      console.log(JSON.stringify(result, null, 2));
    })
    .catch(error => {
      console.error('Test failed:', error);
      process.exit(1);
    });
}
