/**
 * Report Generator - Creates beautiful HTML email reports
 *
 * Generates professional, mobile-responsive HTML emails for the daily task review.
 */

/**
 * Report Generator class
 */
export class ReportGenerator {
  constructor(config = {}) {
    this.config = config;
    this.theme = config.theme || "modern";
    // Task index for reference numbers (#1, #2, etc.)
    this.taskIndex = new Map();
    this.taskCounter = 0;
    // Store Comet-delegable task IDs for badge display
    this.cometTaskIds = new Set();
  }

  /**
   * Reset task counter for new report
   */
  resetTaskIndex() {
    this.taskIndex.clear();
    this.taskCounter = 0;
    this.cometTaskIds.clear();
  }

  /**
   * Check if a task is Comet-delegable
   */
  isCometDelegable(taskId) {
    return this.cometTaskIds.has(taskId);
  }

  /**
   * Get or assign reference number for a task
   */
  getTaskRef(taskId) {
    if (!this.taskIndex.has(taskId)) {
      this.taskCounter++;
      this.taskIndex.set(taskId, this.taskCounter);
    }
    return this.taskIndex.get(taskId);
  }

  /**
   * Get all task mappings for the email poller
   */
  getTaskMappings() {
    const mappings = {};
    for (const [taskId, refNum] of this.taskIndex) {
      mappings[refNum] = taskId;
    }
    return mappings;
  }

  /**
   * Generate complete HTML email report
   */
  generateReport(taskData, analysis) {
    // Reset task index for new report
    this.resetTaskIndex();

    // Populate Comet-delegable task IDs for badge display in all sections
    if (analysis.comet?.opportunities) {
      for (const opp of analysis.comet.opportunities) {
        this.cometTaskIds.add(opp.task.id);
      }
    }

    const date = new Date().toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });

    return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Task Review - ${date}</title>
  ${this.getStyles()}
</head>
<body>
  <div class="container">
    ${this.generateHeader(date, analysis)}
    ${this.generateQuickActionsGuide()}
    ${this.generateSummarySection(analysis)}
    ${this.generateCometSection(analysis)}
    ${this.generateAIOpportunitiesSection(analysis)}
    ${this.generateHighPrioritySection(taskData)}
    ${this.generateOverdueSection(taskData)}
    ${this.generateUpcomingSection(taskData)}
    ${this.generateRecommendationsSection(analysis)}
    ${this.generateFooter()}
  </div>
</body>
</html>`;
  }

  /**
   * Generate quick actions guide section
   */
  generateQuickActionsGuide() {
    return `
<div class="section" style="background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%); border-bottom: 2px solid #667eea;">
  <h2 class="section-title" style="margin-bottom: 15px;">
    <span class="section-icon">&#9889;</span>
    Quick Actions - Reply to This Email
  </h2>
  <p style="color: #444; font-size: 14px; margin-bottom: 15px;">
    Reply to this email with any of these commands to take action on tasks:
  </p>
  <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
    <div style="background: white; padding: 12px; border-radius: 8px; border-left: 3px solid #48bb78;">
      <strong style="color: #48bb78;">complete #3</strong>
      <div style="font-size: 12px; color: #666;">Mark task #3 as done</div>
    </div>
    <div style="background: white; padding: 12px; border-radius: 8px; border-left: 3px solid #ed8936;">
      <strong style="color: #ed8936;">defer #2 tomorrow</strong>
      <div style="font-size: 12px; color: #666;">Reschedule to tomorrow</div>
    </div>
    <div style="background: white; padding: 12px; border-radius: 8px; border-left: 3px solid #667eea;">
      <strong style="color: #667eea;">break down #1</strong>
      <div style="font-size: 12px; color: #666;">Claude creates subtasks</div>
    </div>
    <div style="background: white; padding: 12px; border-radius: 8px; border-left: 3px solid #9f7aea;">
      <strong style="color: #9f7aea;">help #4</strong>
      <div style="font-size: 12px; color: #666;">Get Claude's guidance</div>
    </div>
  </div>
  <p style="color: #666; font-size: 12px; margin-top: 12px; font-style: italic;">
    Tasks are numbered #1, #2, etc. in order below. Use the number in your reply.
  </p>
</div>`;
  }

  /**
   * Get CSS styles
   */
  getStyles() {
    return `
<style>
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f7fa;
  }

  .container {
    max-width: 680px;
    margin: 0 auto;
    background-color: #ffffff;
  }

  /* Header */
  .header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 40px 30px;
    text-align: center;
  }

  .header h1 {
    font-size: 28px;
    font-weight: 600;
    margin-bottom: 8px;
  }

  .header .date {
    font-size: 16px;
    opacity: 0.9;
  }

  .header .headline {
    margin-top: 20px;
    font-size: 18px;
    background: rgba(255,255,255,0.15);
    padding: 12px 20px;
    border-radius: 8px;
    display: inline-block;
  }

  /* Section styling */
  .section {
    padding: 30px;
    border-bottom: 1px solid #eee;
  }

  .section:last-child {
    border-bottom: none;
  }

  .section-title {
    font-size: 20px;
    font-weight: 600;
    color: #333;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .section-icon {
    font-size: 24px;
  }

  /* Summary cards */
  .summary-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
  }

  .summary-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 20px;
    text-align: center;
  }

  .summary-card.highlight {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }

  .summary-card .number {
    font-size: 36px;
    font-weight: 700;
    line-height: 1;
  }

  .summary-card .label {
    font-size: 14px;
    margin-top: 8px;
    opacity: 0.8;
  }

  /* Task cards */
  .task-card {
    background: #f8f9fa;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    border-left: 4px solid #667eea;
  }

  .task-card.urgent {
    border-left-color: #e53e3e;
    background: #fff5f5;
  }

  .task-card.high {
    border-left-color: #ed8936;
    background: #fffaf0;
  }

  .task-card.overdue {
    border-left-color: #e53e3e;
    background: #fff5f5;
  }

  .task-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 10px;
  }

  .task-title {
    font-size: 16px;
    font-weight: 600;
    color: #333;
    flex: 1;
  }

  .task-priority {
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 20px;
    margin-left: 10px;
  }

  .priority-urgent {
    background: #e53e3e;
    color: white;
  }

  .priority-high {
    background: #ed8936;
    color: white;
  }

  .priority-medium {
    background: #ecc94b;
    color: #744210;
  }

  .task-meta {
    font-size: 13px;
    color: #666;
    margin-bottom: 10px;
  }

  .task-suggestion {
    background: white;
    border-radius: 8px;
    padding: 15px;
    margin-top: 15px;
    border: 1px solid #e2e8f0;
  }

  .task-suggestion-header {
    font-size: 13px;
    font-weight: 600;
    color: #667eea;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .task-suggestion p {
    font-size: 14px;
    color: #555;
    margin-bottom: 10px;
  }

  .action-items {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .action-item {
    font-size: 12px;
    background: #edf2f7;
    color: #4a5568;
    padding: 4px 10px;
    border-radius: 15px;
  }

  /* Recommendations */
  .recommendation {
    display: flex;
    gap: 15px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 10px;
    margin-bottom: 12px;
  }

  .recommendation-icon {
    font-size: 24px;
    flex-shrink: 0;
  }

  .recommendation-content h4 {
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .recommendation-content p {
    font-size: 14px;
    color: #666;
  }

  /* Time savings banner */
  .time-banner {
    background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
    color: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 20px;
  }

  .time-banner .time {
    font-size: 32px;
    font-weight: 700;
  }

  .time-banner .label {
    font-size: 14px;
    opacity: 0.9;
    margin-top: 5px;
  }

  /* Footer */
  .footer {
    background: #f8f9fa;
    padding: 30px;
    text-align: center;
  }

  .footer p {
    font-size: 14px;
    color: #666;
    margin-bottom: 8px;
  }

  .footer .cta-button {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 30px;
    border-radius: 25px;
    text-decoration: none;
    font-weight: 600;
    margin-top: 15px;
  }

  .footer .disclaimer {
    font-size: 12px;
    color: #999;
    margin-top: 20px;
  }

  /* Progress bar */
  .progress-container {
    background: #e2e8f0;
    border-radius: 10px;
    height: 12px;
    overflow: hidden;
    margin-top: 10px;
  }

  .progress-bar {
    height: 100%;
    border-radius: 10px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  /* Empty state */
  .empty-state {
    text-align: center;
    padding: 30px;
    color: #666;
  }

  .empty-state-icon {
    font-size: 48px;
    margin-bottom: 15px;
  }

  /* Comet Section Styling */
  .comet-section {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    padding: 30px;
    border-bottom: 3px solid #00d4ff;
  }

  .comet-section .section-title {
    color: #ffffff;
  }

  .comet-intro {
    color: #b8c5d6;
    font-size: 14px;
    margin-bottom: 20px;
    line-height: 1.6;
  }

  .comet-intro a {
    color: #00d4ff;
  }

  .comet-stats {
    display: flex;
    gap: 15px;
    margin-bottom: 25px;
  }

  .comet-stat {
    background: rgba(0, 212, 255, 0.1);
    border: 1px solid rgba(0, 212, 255, 0.2);
    border-radius: 10px;
    padding: 15px 20px;
    text-align: center;
    flex: 1;
  }

  .comet-stat-number {
    color: #00d4ff;
    font-size: 28px;
    font-weight: 700;
  }

  .comet-stat-label {
    color: #8892a0;
    font-size: 12px;
    margin-top: 4px;
  }

  .comet-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(0, 212, 255, 0.3);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 15px;
    border-left: 4px solid #00d4ff;
  }

  .comet-card .task-header {
    margin-bottom: 10px;
  }

  .comet-card .task-title {
    color: #ffffff;
  }

  .comet-card .task-meta {
    color: #8892a0;
  }

  .comet-category-badge {
    background: rgba(0, 212, 255, 0.15);
    color: #00d4ff;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-left: 8px;
  }

  .comet-prompt-container {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 15px;
    margin-top: 15px;
  }

  .comet-prompt-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }

  .comet-prompt-label {
    color: #00d4ff;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .comet-copy-hint {
    color: #6e7681;
    font-size: 11px;
    font-style: italic;
  }

  .comet-prompt-text {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 12px;
    font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
    font-size: 13px;
    color: #c9d1d9;
    line-height: 1.5;
    word-break: break-word;
    cursor: text;
    user-select: all;
    -webkit-user-select: all;
    -moz-user-select: all;
  }

  .comet-prompt-text:focus,
  .comet-prompt-text::selection {
    background-color: rgba(0, 212, 255, 0.3);
    outline: 2px solid #00d4ff;
  }

  /* Comet Badge - appears on tasks throughout report */
  .comet-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #00d4ff;
    color: #00d4ff;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 12px;
    margin-left: 8px;
  }

  .comet-empty-state {
    text-align: center;
    padding: 30px;
    color: #8892a0;
  }

  .comet-empty-icon {
    font-size: 40px;
    margin-bottom: 12px;
    opacity: 0.6;
  }

  /* Mobile responsive */
  @media (max-width: 600px) {
    .header {
      padding: 30px 20px;
    }

    .header h1 {
      font-size: 24px;
    }

    .section {
      padding: 20px;
    }

    .summary-grid {
      grid-template-columns: 1fr;
    }

    .task-header {
      flex-direction: column;
      gap: 10px;
    }

    .task-priority {
      margin-left: 0;
    }

    .comet-stats {
      flex-direction: column;
      gap: 10px;
    }

    .comet-prompt-text {
      font-size: 12px;
    }

    .comet-badge {
      margin-left: 0;
      margin-top: 8px;
    }
  }
</style>`;
  }

  /**
   * Generate header section
   */
  generateHeader(date, analysis) {
    const headline =
      analysis.recommendations.find((r) => r.type === "efficiency")?.description ||
      `${analysis.summary.totalTasks} tasks to review - ${analysis.summary.aiAssistable} can be assisted`;

    return `
<div class="header">
  <h1>Daily Task Review</h1>
  <div class="date">${date}</div>
  <div class="headline">${headline}</div>
</div>`;
  }

  /**
   * Generate summary section
   */
  generateSummarySection(analysis) {
    const { totalTasks, aiAssistable, requiresHuman } = analysis.summary;
    const cometDelegable = analysis.comet?.delegableCount || 0;
    const percentage = totalTasks > 0 ? Math.round((aiAssistable / totalTasks) * 100) : 0;

    // Calculate time savings (AI + Comet)
    const aiTimeSavings = analysis.aiOpportunities.reduce(
      (sum, opp) => sum + (opp.estimatedTimeSavings || 0),
      0
    );
    const cometTimeSavings = analysis.comet?.totalTimeSavings || 0;
    const totalTimeSavings = aiTimeSavings + cometTimeSavings;
    const hoursText =
      totalTimeSavings >= 60
        ? `${Math.round(totalTimeSavings / 60)}h ${totalTimeSavings % 60}m`
        : `${totalTimeSavings}m`;

    return `
<div class="section">
  <h2 class="section-title">
    <span class="section-icon">&#128202;</span>
    Quick Summary
  </h2>

  ${
    totalTimeSavings > 0
      ? `
  <div class="time-banner">
    <div class="time">${hoursText}</div>
    <div class="label">Potential time savings with AI + Comet assistance</div>
  </div>
  `
      : ""
  }

  <div class="summary-grid">
    <div class="summary-card">
      <div class="number">${totalTasks}</div>
      <div class="label">Total Tasks</div>
    </div>
    <div class="summary-card highlight">
      <div class="number">${aiAssistable}</div>
      <div class="label">Claude Can Help</div>
    </div>
    ${
      cometDelegable > 0
        ? `
    <div class="summary-card" style="background: linear-gradient(135deg, #00d4ff 0%, #0099cc 100%); color: white;">
      <div class="number">${cometDelegable}</div>
      <div class="label">Comet Delegable</div>
    </div>
    `
        : `
    <div class="summary-card">
      <div class="number">${requiresHuman}</div>
      <div class="label">Requires You</div>
    </div>
    `
    }
    <div class="summary-card">
      <div class="number">${percentage}%</div>
      <div class="label">Automatable</div>
    </div>
  </div>

  <div class="progress-container" style="margin-top: 20px;">
    <div class="progress-bar" style="width: ${percentage}%;"></div>
  </div>
  <p style="text-align: center; font-size: 13px; color: #666; margin-top: 8px;">
    ${aiAssistable} tasks by Claude${cometDelegable > 0 ? `, ${cometDelegable} by Comet browser` : ""}
  </p>
</div>`;
  }

  /**
   * Generate AI opportunities section
   */
  generateAIOpportunitiesSection(analysis) {
    const opportunities = analysis.aiOpportunities.slice(0, 5);

    if (opportunities.length === 0) {
      return `
<div class="section">
  <h2 class="section-title">
    <span class="section-icon">&#129302;</span>
    AI Assistance Opportunities
  </h2>
  <div class="empty-state">
    <div class="empty-state-icon">&#128161;</div>
    <p>No tasks identified for AI assistance today.</p>
    <p style="font-size: 13px; margin-top: 5px;">All your tasks require personal attention.</p>
  </div>
</div>`;
    }

    return `
<div class="section">
  <h2 class="section-title">
    <span class="section-icon">&#129302;</span>
    AI Can Help With These
  </h2>
  <p style="color: #666; margin-bottom: 20px; font-size: 14px;">
    These tasks are great candidates for AI assistance. Click any task to open in Todoist.
  </p>
  ${opportunities.map((opp) => this.generateOpportunityCard(opp)).join("")}
</div>`;
  }

  /**
   * Generate opportunity card
   */
  generateOpportunityCard(opp) {
    const taskRef = this.getTaskRef(opp.task.id);
    const priorityClass =
      opp.task.priority === 4 ? "urgent" : opp.task.priority === 3 ? "high" : "";
    const priorityBadge = this.getPriorityBadge(opp.task.priority);
    const confidenceBadge = opp.confidenceScore ? this.getConfidenceBadge(opp.confidenceScore) : "";
    const cometBadge = opp.cometCanHelp ? this.generateCometBadge() : "";

    return `
<div class="task-card ${priorityClass}">
  <div class="task-header">
    <span style="background: #667eea; color: white; font-weight: bold; padding: 4px 10px; border-radius: 20px; font-size: 13px; margin-right: 10px;">#${taskRef}</span>
    <span class="task-title" style="flex: 1;">
      ${this.linkifyContent(opp.task.content)}
    </span>
    ${priorityBadge}
    ${cometBadge}
  </div>
  <div class="task-meta">
    ${opp.task.project ? `<strong>${opp.task.project}</strong> &bull; ` : ""}
    ${opp.category} &bull;
    ${opp.estimatedTimeSavings ? `Save ~${opp.estimatedTimeSavings} min` : ""}
    ${opp.task.dueDate ? ` &bull; Due: ${this.formatDate(opp.task.dueDate)}` : ""}
    ${confidenceBadge}
  </div>
  <div class="task-suggestion">
    <div class="task-suggestion-header">
      &#10024; How I Can Help
    </div>
    <p>${this.escapeHtml(opp.suggestion)}</p>
    <div class="action-items">
      ${(opp.actionItems || [])
        .slice(0, 4)
        .map((item) => `<span class="action-item">${this.escapeHtml(item)}</span>`)
        .join("")}
    </div>
  </div>
  <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #667eea;">
    Reply: <code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">help #${taskRef}</code> or
    <code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">break down #${taskRef}</code>
  </div>
</div>`;
  }

  /**
   * Get confidence badge HTML
   */
  getConfidenceBadge(score) {
    if (!score || score < 0) return "";
    const percentage = Math.round(score * 100);
    let color = "#48bb78"; // green for high
    if (score < 0.7) color = "#ecc94b"; // yellow for medium
    if (score < 0.5) color = "#a0aec0"; // gray for low

    return ` &bull; <span style="color: ${color}; font-size: 11px;">${percentage}% confident</span>`;
  }

  /**
   * Generate high priority section
   */
  generateHighPrioritySection(taskData) {
    const tasks = taskData.highPriority.slice(0, 5);

    if (tasks.length === 0) {
      return "";
    }

    return `
<div class="section">
  <h2 class="section-title">
    <span class="section-icon">&#128293;</span>
    High Priority Tasks
  </h2>
  ${tasks.map((task) => this.generateSimpleTaskCard(task)).join("")}
</div>`;
  }

  /**
   * Generate overdue section
   */
  generateOverdueSection(taskData) {
    const tasks = taskData.overdue;

    if (tasks.length === 0) {
      return "";
    }

    return `
<div class="section">
  <h2 class="section-title">
    <span class="section-icon">&#9888;&#65039;</span>
    Overdue Tasks
  </h2>
  <p style="color: #e53e3e; margin-bottom: 20px; font-size: 14px;">
    These ${tasks.length} task(s) are past their due date and need attention.
  </p>
  ${tasks.map((task) => this.generateSimpleTaskCard(task, "overdue")).join("")}
</div>`;
  }

  /**
   * Generate upcoming section
   */
  generateUpcomingSection(taskData) {
    const tasks = taskData.upcoming.slice(0, 5);

    if (tasks.length === 0) {
      return "";
    }

    return `
<div class="section">
  <h2 class="section-title">
    <span class="section-icon">&#128197;</span>
    Coming Up This Week
  </h2>
  ${tasks.map((task) => this.generateSimpleTaskCard(task)).join("")}
  ${
    taskData.upcoming.length > 5
      ? `
  <p style="text-align: center; color: #666; font-size: 14px; margin-top: 15px;">
    + ${taskData.upcoming.length - 5} more tasks this week
  </p>`
      : ""
  }
</div>`;
  }

  /**
   * Generate simple task card
   */
  generateSimpleTaskCard(task, variant = "") {
    const taskRef = this.getTaskRef(task.id);
    const priorityBadge = this.getPriorityBadge(task.priority);
    const cometBadge = this.isCometDelegable(task.id) ? this.generateCometBadge() : "";

    return `
<div class="task-card ${variant}">
  <div class="task-header">
    <span style="background: #667eea; color: white; font-weight: bold; padding: 4px 10px; border-radius: 20px; font-size: 13px; margin-right: 10px;">#${taskRef}</span>
    <span class="task-title" style="flex: 1;">
      ${this.linkifyContent(task.content)}
    </span>
    ${priorityBadge}
    ${cometBadge}
  </div>
  <div class="task-meta">
    ${task.project?.name ? `${task.project.name} &bull; ` : ""}
    ${task.due?.date ? `Due: ${this.formatDate(task.due.date)}` : "No due date"}
    ${task.isOverdue ? ' &bull; <strong style="color: #e53e3e;">OVERDUE</strong>' : ""}
  </div>
  <div style="margin-top: 10px; font-size: 12px; color: #666;">
    Reply: <code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">complete #${taskRef}</code> or
    <code style="background: #f1f5f9; padding: 2px 6px; border-radius: 4px;">defer #${taskRef} tomorrow</code>
  </div>
</div>`;
  }

  /**
   * Generate recommendations section
   */
  generateRecommendationsSection(analysis) {
    const recommendations = analysis.recommendations.filter((r) => r.type !== "efficiency");

    if (recommendations.length === 0) {
      return "";
    }

    const icons = {
      priority: "&#127919;",
      batch: "&#128230;",
      urgent: "&#128680;",
      default: "&#128161;",
    };

    return `
<div class="section">
  <h2 class="section-title">
    <span class="section-icon">&#128161;</span>
    Recommendations
  </h2>
  ${recommendations
    .map(
      (rec) => `
  <div class="recommendation">
    <div class="recommendation-icon">${icons[rec.type] || icons.default}</div>
    <div class="recommendation-content">
      <h4>${this.escapeHtml(rec.title)}</h4>
      <p>${this.escapeHtml(rec.description)}</p>
    </div>
  </div>
  `
    )
    .join("")}
</div>`;
  }

  /**
   * Generate Comet browser delegation section
   */
  generateCometSection(analysis) {
    const cometData = analysis.comet;

    // Don't show section if Comet is disabled or no opportunities
    if (!cometData?.enabled || !cometData?.opportunities?.length) {
      return "";
    }

    const opportunities = cometData.opportunities.slice(0, 5);
    const timeSavings = cometData.totalTimeSavings || 0;
    const hoursText = timeSavings >= 60 ? `~${Math.round(timeSavings / 60)}h` : `~${timeSavings}m`;

    return `
<div class="section comet-section">
  <h2 class="section-title">
    <span class="section-icon">&#127760;</span>
    Delegate to Comet Browser
  </h2>

  <p class="comet-intro">
    These tasks involve <strong style="color: #00d4ff;">web browsing, research, or online actions</strong> that
    <a href="https://www.perplexity.ai/comet" target="_blank">Perplexity Comet</a>
    can handle. Copy the prompts below and paste directly into Comet.
  </p>

  <div class="comet-stats">
    <div class="comet-stat">
      <div class="comet-stat-number">${cometData.delegableCount}</div>
      <div class="comet-stat-label">Browser Tasks</div>
    </div>
    <div class="comet-stat">
      <div class="comet-stat-number">${hoursText}</div>
      <div class="comet-stat-label">Time Saved</div>
    </div>
  </div>

  ${opportunities.map((opp) => this.generateCometCard(opp)).join("")}

  ${
    cometData.delegableCount > 5
      ? `
  <p style="text-align: center; color: #8892a0; font-size: 14px; margin-top: 15px;">
    + ${cometData.delegableCount - 5} more Comet-delegable tasks
  </p>`
      : ""
  }
</div>`;
  }

  /**
   * Generate individual Comet task card
   */
  generateCometCard(opp) {
    const taskRef = this.getTaskRef(opp.task.id);
    const priorityBadge = this.getPriorityBadge(opp.task.priority);

    return `
<div class="comet-card">
  <div class="task-header">
    <span style="background: #00d4ff; color: #0d1117; font-weight: bold; padding: 4px 10px; border-radius: 20px; font-size: 13px; margin-right: 10px;">#${taskRef}</span>
    <span class="task-title" style="flex: 1;">
      ${this.linkifyContent(opp.task.content)}
    </span>
    ${priorityBadge}
    <span class="comet-category-badge">${opp.cometCategoryName || opp.cometCategory}</span>
  </div>
  <div class="task-meta">
    ${opp.task.project ? `${opp.task.project} &bull; ` : ""}
    ${opp.cometCapability}
    ${opp.task.dueDate ? ` &bull; Due: ${this.formatDate(opp.task.dueDate)}` : ""}
    &bull; <span style="color: #00d4ff;">~${opp.estimatedTime || opp.cometEstimatedTime || 20} min</span>
  </div>

  ${this.generateCometPromptBox(opp.cometPrompt)}
</div>`;
  }

  /**
   * Generate Comet prompt box
   */
  generateCometPromptBox(prompt) {
    if (!prompt) return "";

    return `
<div class="comet-prompt-container">
  <div class="comet-prompt-header">
    <span class="comet-prompt-label">&#128203; Comet Prompt</span>
    <span class="comet-copy-hint">Click to select, then Cmd+C to copy</span>
  </div>
  <div class="comet-prompt-text">${this.escapeHtml(prompt)}</div>
</div>`;
  }

  /**
   * Generate Comet badge for inline display
   */
  generateCometBadge() {
    return `<span class="comet-badge" title="Delegate to Perplexity Comet">&#127760; Comet</span>`;
  }

  /**
   * Generate footer
   */
  generateFooter() {
    const now = new Date();
    const timestamp = now.toLocaleString("en-US", {
      timeZone: "America/New_York",
      dateStyle: "medium",
      timeStyle: "short",
    });

    return `
<div class="footer">
  <p>Ready to tackle your tasks?</p>
  <a href="https://todoist.com/app/today" class="cta-button">
    Open Todoist
  </a>
  <p class="disclaimer">
    Generated by Daily Todoist Reviewer at ${timestamp} EST<br>
    Reply to this email to ask Claude for help with any task.
  </p>
</div>`;
  }

  /**
   * Get priority badge HTML
   */
  getPriorityBadge(priority) {
    const badges = {
      4: '<span class="task-priority priority-urgent">Urgent</span>',
      3: '<span class="task-priority priority-high">High</span>',
      2: '<span class="task-priority priority-medium">Medium</span>',
      1: "",
    };
    return badges[priority] || "";
  }

  /**
   * Format date for display
   */
  formatDate(dateString) {
    const date = new Date(dateString);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    date.setHours(0, 0, 0, 0);

    const diffDays = Math.ceil((date - today) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Tomorrow";
    if (diffDays === -1) return "Yesterday";
    if (diffDays < -1) return `${Math.abs(diffDays)} days ago`;
    if (diffDays <= 7) return date.toLocaleDateString("en-US", { weekday: "long" });

    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    if (!text) return "";
    const div = { innerHTML: "" };
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return text.replace(/[&<>"']/g, (char) => entities[char]);
  }

  /**
   * HTML-escape text then convert markdown links and bare URLs into clickable <a> tags.
   *
   * Handles:
   * - Todoist markdown links: [Title](https://...) and [Title](obsidian://...)
   * - Bare URLs: https://example.com, obsidian://open?vault=...
   */
  linkifyContent(text) {
    if (!text) return "";
    let escaped = this.escapeHtml(text);

    const schemes = "(?:https?|obsidian)";

    // Convert markdown links [text](url) → <a>text</a>
    // After escapeHtml, &amp; may appear in URLs — the regex accounts for that.
    escaped = escaped.replace(
      new RegExp(`\\[([^\\]]+)\\]\\((${schemes}://[^)]+)\\)`, "g"),
      '<a href="$2" target="_blank" rel="noopener" style="color:#667eea;text-decoration:underline;">$1</a>'
    );

    // Linkify remaining bare URLs not already inside href="..."
    escaped = escaped.replace(
      new RegExp(`(?<!href=")(?<!">)(${schemes}://[^\\s<)]+)`, "g"),
      '<a href="$1" target="_blank" rel="noopener" style="color:#667eea;text-decoration:underline;">$1</a>'
    );

    return escaped;
  }
}

export default ReportGenerator;
