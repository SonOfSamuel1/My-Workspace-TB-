/**
 * AI Analyzer - Analyzes tasks and generates intelligent suggestions
 *
 * This module categorizes tasks and identifies which ones Claude can help complete.
 * Supports two modes:
 * 1. Claude CLI mode (default): Uses local Claude Code for real AI analysis
 * 2. Pattern matching mode (fallback): Uses keyword-based analysis
 */

import config from '../config/reviewer-config.js';
import { analyzeWithClaude, analyzeTaskDetailed } from '../scripts/analyze-tasks.js';

/**
 * Task categories that Claude can assist with
 */
const AI_ASSISTABLE_PATTERNS = {
  research: {
    keywords: ['research', 'find', 'search', 'look up', 'investigate', 'explore', 'discover', 'learn about', 'analyze'],
    description: 'Research and information gathering',
    canAutomate: true,
    suggestionTemplate: 'I can help research this topic and provide a summary with key findings.'
  },
  communication: {
    keywords: ['email', 'message', 'respond', 'reply', 'write to', 'contact', 'reach out', 'follow up', 'send'],
    description: 'Email and communication drafting',
    canAutomate: true,
    suggestionTemplate: 'I can draft this communication for your review before sending.'
  },
  coding: {
    keywords: ['code', 'implement', 'build', 'create', 'develop', 'fix bug', 'debug', 'refactor', 'test', 'script', 'automate'],
    description: 'Code development and technical tasks',
    canAutomate: true,
    suggestionTemplate: 'I can help write, review, or debug this code.'
  },
  writing: {
    keywords: ['write', 'draft', 'document', 'blog', 'article', 'post', 'content', 'copy', 'proposal', 'report'],
    description: 'Writing and content creation',
    canAutomate: true,
    suggestionTemplate: 'I can draft this content or help outline the structure.'
  },
  admin: {
    keywords: ['organize', 'schedule', 'plan', 'book', 'arrange', 'set up', 'prepare', 'update', 'review', 'check'],
    description: 'Administrative and organizational tasks',
    canAutomate: true,
    suggestionTemplate: 'I can help organize, plan, or prepare materials for this task.'
  },
  planning: {
    keywords: ['plan', 'strategy', 'roadmap', 'outline', 'brainstorm', 'ideate', 'design', 'architect'],
    description: 'Planning and strategy',
    canAutomate: true,
    suggestionTemplate: 'I can help create a plan, outline, or strategy for this.'
  },
  analysis: {
    keywords: ['analyze', 'review', 'evaluate', 'assess', 'compare', 'audit', 'examine', 'study'],
    description: 'Analysis and review tasks',
    canAutomate: true,
    suggestionTemplate: 'I can analyze this and provide insights or recommendations.'
  },
  dataWork: {
    keywords: ['data', 'spreadsheet', 'excel', 'csv', 'report', 'metrics', 'dashboard', 'numbers', 'calculate'],
    description: 'Data processing and analysis',
    canAutomate: true,
    suggestionTemplate: 'I can help process, analyze, or visualize this data.'
  }
};

/**
 * Patterns that indicate Claude cannot help
 */
const NON_AI_PATTERNS = {
  physical: {
    keywords: ['go to', 'visit', 'pick up', 'drop off', 'meet', 'attend', 'call', 'phone', 'exercise', 'gym', 'clean', 'buy', 'shop', 'grocery'],
    reason: 'Requires physical presence or action'
  },
  personal: {
    keywords: ['family', 'doctor', 'appointment', 'personal', 'private', 'confidential'],
    reason: 'Personal matter requiring human judgment'
  },
  realtime: {
    keywords: ['call', 'phone call', 'meeting', 'zoom', 'teams', 'interview', 'presentation'],
    reason: 'Requires real-time human interaction'
  }
};

/**
 * Time estimation patterns (in minutes)
 */
const TIME_ESTIMATES = {
  quick: { range: [5, 15], keywords: ['quick', 'brief', 'simple', 'easy', 'small'] },
  short: { range: [15, 30], keywords: ['short', 'review', 'check', 'update'] },
  medium: { range: [30, 60], keywords: ['draft', 'create', 'write', 'research'] },
  long: { range: [60, 120], keywords: ['analyze', 'develop', 'implement', 'build'] },
  extended: { range: [120, 240], keywords: ['comprehensive', 'full', 'complete', 'major'] }
};

/**
 * AI Analyzer class
 */
export class AIAnalyzer {
  constructor(customConfig = {}) {
    this.config = { ...config.ai, ...customConfig };
    // Use Claude CLI by default, fall back to pattern matching if disabled or fails
    this.useClaudeCLI = config.localExecution?.useClaudeCLI !== false;
  }

  /**
   * Analyze all tasks and generate suggestions
   * Uses Claude CLI for real AI analysis, with pattern matching as fallback
   */
  async analyzeTasksForReview(taskData) {
    // Try Claude CLI first if enabled
    if (this.useClaudeCLI) {
      try {
        const claudeAnalysis = await this.analyzeWithClaudeCLI(taskData);
        if (claudeAnalysis) {
          return claudeAnalysis;
        }
      } catch (error) {
        console.warn('Claude CLI analysis failed, falling back to pattern matching:', error.message);
      }
    }

    // Fall back to pattern matching
    return this.analyzeWithPatterns(taskData);
  }

  /**
   * Analyze tasks using Claude CLI (real AI)
   */
  async analyzeWithClaudeCLI(taskData) {
    const claudeResult = await analyzeWithClaude(taskData.all);

    if (!claudeResult || !claudeResult.analyses) {
      return null;
    }

    const analysis = {
      analyzedAt: new Date().toISOString(),
      analysisMethod: 'claude-cli',
      summary: {
        totalTasks: taskData.all.length,
        aiAssistable: 0,
        requiresHuman: 0,
        byCategory: {}
      },
      tasks: [],
      aiOpportunities: [],
      recommendations: []
    };

    // Process Claude's analysis results
    for (const taskAnalysis of claudeResult.analyses) {
      // Ensure task data is present
      if (!taskAnalysis.task) {
        const originalTask = taskData.all.find(t => t.id === taskAnalysis.taskId);
        if (originalTask) {
          taskAnalysis.task = {
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
          };
        }
      }

      analysis.tasks.push(taskAnalysis);

      if (taskAnalysis.aiCanHelp) {
        analysis.summary.aiAssistable++;
        analysis.aiOpportunities.push(taskAnalysis);
      } else {
        analysis.summary.requiresHuman++;
      }

      // Track by category
      const category = taskAnalysis.category || 'uncategorized';
      if (!analysis.summary.byCategory[category]) {
        analysis.summary.byCategory[category] = 0;
      }
      analysis.summary.byCategory[category]++;
    }

    // Sort AI opportunities by impact (priority first, then time savings)
    analysis.aiOpportunities.sort((a, b) => {
      const priorityA = a.task?.priority || 1;
      const priorityB = b.task?.priority || 1;
      if (priorityB !== priorityA) {
        return priorityB - priorityA;
      }
      return (b.estimatedTimeSavings || 0) - (a.estimatedTimeSavings || 0);
    });

    // Generate overall recommendations
    analysis.recommendations = this.generateRecommendations(analysis);

    return analysis;
  }

  /**
   * Analyze tasks using pattern matching (fallback method)
   */
  analyzeWithPatterns(taskData) {
    const analysis = {
      analyzedAt: new Date().toISOString(),
      analysisMethod: 'pattern-matching',
      summary: {
        totalTasks: taskData.all.length,
        aiAssistable: 0,
        requiresHuman: 0,
        byCategory: {}
      },
      tasks: [],
      aiOpportunities: [],
      recommendations: []
    };

    // Analyze each task
    for (const task of taskData.all) {
      const taskAnalysis = this.analyzeTask(task);
      analysis.tasks.push(taskAnalysis);

      if (taskAnalysis.aiCanHelp) {
        analysis.summary.aiAssistable++;
        analysis.aiOpportunities.push(taskAnalysis);
      } else {
        analysis.summary.requiresHuman++;
      }

      // Track by category
      const category = taskAnalysis.category || 'uncategorized';
      if (!analysis.summary.byCategory[category]) {
        analysis.summary.byCategory[category] = 0;
      }
      analysis.summary.byCategory[category]++;
    }

    // Sort AI opportunities by impact
    analysis.aiOpportunities.sort((a, b) => {
      // Priority first
      if (b.task.priority !== a.task.priority) {
        return b.task.priority - a.task.priority;
      }
      // Then by estimated time savings
      return (b.estimatedTimeSavings || 0) - (a.estimatedTimeSavings || 0);
    });

    // Generate overall recommendations
    analysis.recommendations = this.generateRecommendations(analysis);

    return analysis;
  }

  /**
   * Analyze a single task
   */
  analyzeTask(task) {
    const content = `${task.content} ${task.description || ''}`.toLowerCase();

    const result = {
      task: {
        id: task.id,
        content: task.content,
        description: task.description,
        priority: task.priority,
        priorityLabel: task.priorityLabel,
        dueDate: task.due?.date,
        daysUntilDue: task.daysUntilDue,
        isOverdue: task.isOverdue,
        project: task.project?.name,
        labels: task.labels,
        url: task.url
      },
      category: null,
      aiCanHelp: false,
      aiAssistanceType: null,
      suggestion: null,
      estimatedTime: null,
      estimatedTimeSavings: null,
      reasoning: null,
      actionItems: []
    };

    // Check if task matches non-AI patterns first
    for (const [type, pattern] of Object.entries(NON_AI_PATTERNS)) {
      if (pattern.keywords.some(kw => content.includes(kw))) {
        result.category = type;
        result.aiCanHelp = false;
        result.reasoning = pattern.reason;
        return result;
      }
    }

    // Check AI-assistable patterns
    for (const [type, pattern] of Object.entries(AI_ASSISTABLE_PATTERNS)) {
      if (pattern.keywords.some(kw => content.includes(kw))) {
        result.category = type;
        result.aiCanHelp = true;
        result.aiAssistanceType = pattern.description;
        result.suggestion = this.generateSuggestion(task, type, pattern);
        result.actionItems = this.generateActionItems(task, type);
        break;
      }
    }

    // If no pattern matched, analyze content for general assistance
    if (!result.category) {
      result.category = 'general';
      result.aiCanHelp = this.canAssistWithGeneral(content);
      if (result.aiCanHelp) {
        result.suggestion = 'I can help break down this task or provide guidance on approach.';
        result.actionItems = ['Break down into subtasks', 'Research best practices', 'Create action plan'];
      }
    }

    // Estimate time
    result.estimatedTime = this.estimateTime(content);
    if (result.aiCanHelp) {
      result.estimatedTimeSavings = Math.round(result.estimatedTime * 0.6); // Assume 60% time savings
    }

    return result;
  }

  /**
   * Generate specific suggestion for a task
   */
  generateSuggestion(task, type, pattern) {
    const baseSuggestion = pattern.suggestionTemplate;

    // Add context-specific details
    let additionalContext = '';

    if (task.isOverdue) {
      additionalContext = ' This task is overdue - I can prioritize getting this done quickly.';
    } else if (task.daysUntilDue === 0) {
      additionalContext = ' This is due today - I can help complete it right away.';
    } else if (task.priority === 4) {
      additionalContext = ' As an urgent task, I can focus on this first.';
    }

    return baseSuggestion + additionalContext;
  }

  /**
   * Generate action items for a task type
   */
  generateActionItems(task, type) {
    const actions = {
      research: [
        'Search for relevant information',
        'Compile key findings',
        'Create summary document',
        'Identify next steps'
      ],
      communication: [
        'Draft email/message',
        'Review and suggest edits',
        'Prepare follow-up points',
        'Schedule send time'
      ],
      coding: [
        'Analyze requirements',
        'Write initial code',
        'Add error handling',
        'Create tests'
      ],
      writing: [
        'Create outline',
        'Draft content',
        'Edit and refine',
        'Format for publication'
      ],
      admin: [
        'Gather requirements',
        'Create checklist',
        'Prepare materials',
        'Document process'
      ],
      planning: [
        'Define objectives',
        'Identify constraints',
        'Create timeline',
        'Outline milestones'
      ],
      analysis: [
        'Collect data points',
        'Perform analysis',
        'Identify patterns',
        'Generate insights'
      ],
      dataWork: [
        'Clean and organize data',
        'Run calculations',
        'Create visualizations',
        'Generate report'
      ]
    };

    return actions[type] || ['Break into subtasks', 'Identify blockers', 'Create action plan'];
  }

  /**
   * Check if Claude can help with general tasks
   */
  canAssistWithGeneral(content) {
    // List of action verbs that typically indicate AI can help
    const assistableVerbs = ['create', 'make', 'prepare', 'finish', 'complete', 'do', 'work on'];
    return assistableVerbs.some(verb => content.includes(verb));
  }

  /**
   * Estimate time for a task
   */
  estimateTime(content) {
    for (const [, estimate] of Object.entries(TIME_ESTIMATES)) {
      if (estimate.keywords.some(kw => content.includes(kw))) {
        const [min, max] = estimate.range;
        return Math.round((min + max) / 2);
      }
    }
    // Default medium estimate
    return 45;
  }

  /**
   * Generate overall recommendations
   */
  generateRecommendations(analysis) {
    const recommendations = [];

    // Prioritization recommendation
    if (analysis.aiOpportunities.length > 0) {
      const topTask = analysis.aiOpportunities[0];
      recommendations.push({
        type: 'priority',
        title: 'Start with Highest Impact',
        description: `Begin with "${topTask.task.content}" - ${topTask.aiAssistanceType}`,
        taskId: topTask.task.id
      });
    }

    // Batch similar tasks
    const categories = {};
    for (const opp of analysis.aiOpportunities) {
      if (!categories[opp.category]) {
        categories[opp.category] = [];
      }
      categories[opp.category].push(opp);
    }

    for (const [category, tasks] of Object.entries(categories)) {
      if (tasks.length >= 2) {
        recommendations.push({
          type: 'batch',
          title: `Batch ${category} Tasks`,
          description: `${tasks.length} ${category} tasks can be done together for efficiency`,
          taskIds: tasks.map(t => t.task.id)
        });
      }
    }

    // Time savings summary
    const totalTimeSavings = analysis.aiOpportunities.reduce(
      (sum, opp) => sum + (opp.estimatedTimeSavings || 0), 0
    );

    if (totalTimeSavings > 0) {
      recommendations.push({
        type: 'efficiency',
        title: 'Potential Time Savings',
        description: `AI assistance could save approximately ${Math.round(totalTimeSavings / 60)} hours on these tasks`
      });
    }

    // Overdue tasks warning
    const overdueTasks = analysis.tasks.filter(t => t.task.isOverdue);
    if (overdueTasks.length > 0) {
      recommendations.push({
        type: 'urgent',
        title: 'Address Overdue Tasks',
        description: `${overdueTasks.length} task(s) are overdue and need immediate attention`,
        taskIds: overdueTasks.map(t => t.task.id)
      });
    }

    return recommendations;
  }

  /**
   * Get a formatted analysis report
   */
  getAnalysisReport(analysis) {
    const report = {
      headline: this.generateHeadline(analysis),
      stats: {
        total: analysis.summary.totalTasks,
        aiCanHelp: analysis.summary.aiAssistable,
        requiresHuman: analysis.summary.requiresHuman,
        percentageAiAssistable: Math.round((analysis.summary.aiAssistable / analysis.summary.totalTasks) * 100) || 0
      },
      topOpportunities: analysis.aiOpportunities.slice(0, 5).map(opp => ({
        task: opp.task.content,
        category: opp.category,
        suggestion: opp.suggestion,
        timeSavings: opp.estimatedTimeSavings
      })),
      recommendations: analysis.recommendations
    };

    return report;
  }

  /**
   * Generate a headline summary
   */
  generateHeadline(analysis) {
    const { totalTasks, aiAssistable } = analysis.summary;

    if (totalTasks === 0) {
      return 'No tasks to review today!';
    }

    if (aiAssistable === 0) {
      return `${totalTasks} tasks today - all require your personal attention.`;
    }

    const percentage = Math.round((aiAssistable / totalTasks) * 100);
    return `${totalTasks} tasks today - I can help with ${aiAssistable} (${percentage}%)`;
  }
}

/**
 * Get detailed analysis for a single task (for actions like "help with #3")
 */
export async function getDetailedTaskAnalysis(task, actionType = 'help') {
  return analyzeTaskDetailed(task, actionType);
}

export default AIAnalyzer;
