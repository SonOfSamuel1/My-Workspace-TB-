/**
 * Email Autopilot System
 * Fully autonomous email management with AI-powered decision making
 */

const logger = require('./logger');

class EmailAutopilot {
  constructor() {
    this.mode = 'assisted'; // assisted, autopilot, full_autonomous
    this.confidenceThreshold = 0.85;
    this.learningEnabled = true;
    this.safetyChecks = true;
    this.autoResponseTemplates = new Map();
    this.decisionHistory = [];
  }

  /**
   * Enable autopilot mode
   */
  enableAutopilot(options = {}) {
    this.mode = options.mode || 'autopilot';
    this.confidenceThreshold = options.confidenceThreshold || 0.85;
    this.safetyChecks = options.safetyChecks !== false;

    logger.info('Autopilot enabled', {
      mode: this.mode,
      confidenceThreshold: this.confidenceThreshold
    });

    return {
      enabled: true,
      mode: this.mode,
      settings: {
        confidenceThreshold: this.confidenceThreshold,
        safetyChecks: this.safetyChecks,
        learningEnabled: this.learningEnabled
      }
    };
  }

  /**
   * Process email in autopilot mode
   */
  async processEmailAutonomously(email, context) {
    logger.info('Processing email in autopilot mode', { emailId: email.id });

    // Step 1: Analyze email comprehensively
    const analysis = await this.analyzeEmail(email, context);

    // Step 2: Make autonomous decision
    const decision = await this.makeDecision(email, analysis, context);

    // Step 3: Safety checks
    if (this.safetyChecks) {
      const safetyCheck = await this.performSafetyChecks(decision, email);
      if (!safetyCheck.passed) {
        logger.warn('Safety check failed, escalating', {
          emailId: email.id,
          reason: safetyCheck.reason
        });
        return this.escalateForReview(email, decision, safetyCheck);
      }
    }

    // Step 4: Execute decision if confidence is high enough
    if (decision.confidence >= this.confidenceThreshold) {
      const execution = await this.executeDecision(decision, email);

      // Record for learning
      this.recordDecision(email, decision, execution);

      return {
        processed: true,
        autonomous: true,
        decision,
        execution,
        requiresReview: false
      };
    } else {
      // Confidence too low, queue for review
      return {
        processed: false,
        autonomous: false,
        decision,
        requiresReview: true,
        reason: `Confidence ${decision.confidence} below threshold ${this.confidenceThreshold}`
      };
    }
  }

  /**
   * Analyze email comprehensively
   */
  async analyzeEmail(email, context) {
    return {
      intent: this.detectIntent(email),
      requiresResponse: this.requiresResponse(email),
      actionItems: this.extractActionItems(email),
      sentiment: context.sentiment || { emotion: 'neutral', urgency: 'medium' },
      threadContext: context.thread || null,
      businessImpact: this.assessBusinessImpact(email),
      timeMatters: this.assessTimeSensitivity(email),
      relationships: this.analyzeRelationships(email)
    };
  }

  /**
   * Make autonomous decision
   */
  async makeDecision(email, analysis, context) {
    const decision = {
      action: null,
      reasoning: [],
      confidence: 0,
      alternatives: [],
      estimatedImpact: 'medium',
      responseRequired: analysis.requiresResponse
    };

    // Decision tree based on analysis
    if (analysis.businessImpact === 'high') {
      decision.action = 'escalate';
      decision.reasoning.push('High business impact detected');
      decision.confidence = 0.95;
    } else if (analysis.intent === 'meeting_request') {
      decision.action = 'schedule_meeting';
      decision.reasoning.push('Meeting request detected');
      decision.confidence = 0.90;
      decision.details = {
        duration: analysis.actionItems.duration || 30,
        attendees: analysis.actionItems.attendees || []
      };
    } else if (analysis.intent === 'information_request') {
      decision.action = 'provide_information';
      decision.reasoning.push('Information request - can be handled autonomously');
      decision.confidence = 0.85;
    } else if (analysis.intent === 'confirmation') {
      decision.action = 'confirm';
      decision.reasoning.push('Confirmation request');
      decision.confidence = 0.92;
    } else if (analysis.requiresResponse && analysis.sentiment.emotion === 'angry') {
      decision.action = 'draft_response';
      decision.reasoning.push('Requires careful response due to negative sentiment');
      decision.confidence = 0.75; // Lower confidence for sensitive situations
    } else if (!analysis.requiresResponse) {
      decision.action = 'file';
      decision.reasoning.push('No response needed - filing for reference');
      decision.confidence = 0.88;
    } else {
      decision.action = 'draft_response';
      decision.reasoning.push('Standard response required');
      decision.confidence = 0.80;
    }

    return decision;
  }

  /**
   * Perform safety checks
   */
  async performSafetyChecks(decision, email) {
    const checks = {
      financialImpact: this.checkFinancialImpact(email),
      legalRisk: this.checkLegalRisk(email),
      reputationRisk: this.checkReputationRisk(email),
      sensitiveContent: this.checkSensitiveContent(email),
      recipientValidation: this.validateRecipients(email)
    };

    const failed = [];

    for (const [check, result] of Object.entries(checks)) {
      if (!result.passed) {
        failed.push({ check, reason: result.reason });
      }
    }

    if (failed.length > 0) {
      return {
        passed: false,
        failedChecks: failed,
        reason: `Safety checks failed: ${failed.map(f => f.check).join(', ')}`
      };
    }

    return { passed: true };
  }

  /**
   * Execute decision
   */
  async executeDecision(decision, email) {
    logger.info('Executing autonomous decision', {
      emailId: email.id,
      action: decision.action
    });

    const execution = {
      action: decision.action,
      executedAt: new Date(),
      success: false,
      details: {}
    };

    switch (decision.action) {
      case 'escalate':
        // Send escalation notification
        execution.success = true;
        execution.details.escalatedTo = 'user';
        execution.details.method = ['email', 'sms'];
        break;

      case 'schedule_meeting':
        // Use smart scheduler
        execution.success = true;
        execution.details.meetingScheduled = true;
        execution.details.proposedTime = new Date(Date.now() + 24 * 60 * 60 * 1000);
        break;

      case 'provide_information':
        // Generate information response
        const response = await this.generateInformationResponse(email);
        execution.success = true;
        execution.details.responseSent = true;
        execution.details.responseText = response;
        break;

      case 'confirm':
        // Send confirmation
        execution.success = true;
        execution.details.confirmationSent = true;
        break;

      case 'draft_response':
        // Create draft for review
        const draft = await this.generateDraft(email);
        execution.success = true;
        execution.details.draftCreated = true;
        execution.details.requiresApproval = true;
        break;

      case 'file':
        // File email with appropriate label
        execution.success = true;
        execution.details.filed = true;
        execution.details.label = this.determineLabel(email);
        break;
    }

    return execution;
  }

  /**
   * Detect intent
   */
  detectIntent(email) {
    const text = `${email.subject} ${email.body}`.toLowerCase();

    if (/schedule|meeting|call|zoom|teams/.test(text)) {
      return 'meeting_request';
    }
    if (/question|wondering|could you|can you tell/.test(text)) {
      return 'information_request';
    }
    if (/confirm|confirmation|please verify/.test(text)) {
      return 'confirmation';
    }
    if (/thank you|thanks|appreciate/.test(text)) {
      return 'acknowledgment';
    }
    if (/urgent|asap|critical|emergency/.test(text)) {
      return 'urgent_matter';
    }

    return 'general';
  }

  /**
   * Check if requires response
   */
  requiresResponse(email) {
    const text = `${email.subject} ${email.body}`.toLowerCase();

    const responseIndicators = [
      /\?/, // Contains question
      /please (respond|reply|let me know)/,
      /could you/,
      /can you/,
      /would you/,
      /need to know/,
      /waiting for/
    ];

    const noResponseIndicators = [
      /fyi/,
      /for your information/,
      /no response needed/,
      /just letting you know/,
      /unsubscribe/
    ];

    // Check for no-response indicators first
    if (noResponseIndicators.some(pattern => pattern.test(text))) {
      return false;
    }

    // Check for response indicators
    return responseIndicators.some(pattern => pattern.test(text));
  }

  /**
   * Extract action items
   */
  extractActionItems(email) {
    // In production: Use NLP to extract action items
    return {
      tasks: [],
      deadlines: [],
      attendees: [],
      duration: null
    };
  }

  /**
   * Assess business impact
   */
  assessBusinessImpact(email) {
    const highImpactKeywords = [
      'contract', 'revenue', 'partnership', 'investment',
      'legal', 'board', 'acquisition', 'merger'
    ];

    const text = `${email.subject} ${email.body}`.toLowerCase();

    if (highImpactKeywords.some(kw => text.includes(kw))) {
      return 'high';
    }

    return 'medium';
  }

  /**
   * Assess time sensitivity
   */
  assessTimeSensitivity(email) {
    const text = `${email.subject} ${email.body}`.toLowerCase();

    if (/urgent|asap|immediate|today|now/.test(text)) {
      return 'urgent';
    }
    if (/tomorrow|this week|soon/.test(text)) {
      return 'soon';
    }

    return 'normal';
  }

  /**
   * Analyze relationships
   */
  analyzeRelationships(email) {
    // In production: Check against CRM, history, etc.
    return {
      senderType: 'known',
      relationshipStrength: 'medium',
      previousInteractions: 5
    };
  }

  /**
   * Check financial impact
   */
  checkFinancialImpact(email) {
    const text = `${email.subject} ${email.body}`.toLowerCase();
    const hasFinancialTerms = /payment|invoice|budget|price|cost|\$/.test(text);

    return {
      passed: !hasFinancialTerms,
      reason: hasFinancialTerms ? 'Contains financial terms' : null
    };
  }

  /**
   * Check legal risk
   */
  checkLegalRisk(email) {
    const text = `${email.subject} ${email.body}`.toLowerCase();
    const hasLegalTerms = /legal|lawsuit|attorney|contract terms|liability/.test(text);

    return {
      passed: !hasLegalTerms,
      reason: hasLegalTerms ? 'Contains legal terms' : null
    };
  }

  /**
   * Check reputation risk
   */
  checkReputationRisk(email) {
    // Check if email is from media, public figure, etc.
    return { passed: true };
  }

  /**
   * Check sensitive content
   */
  checkSensitiveContent(email) {
    const text = `${email.subject} ${email.body}`.toLowerCase();
    const hasSensitive = /confidential|private|personal|ssn|password/.test(text);

    return {
      passed: !hasSensitive,
      reason: hasSensitive ? 'Contains sensitive content' : null
    };
  }

  /**
   * Validate recipients
   */
  validateRecipients(email) {
    // Check if recipients are valid, not blacklisted, etc.
    return { passed: true };
  }

  /**
   * Generate information response
   */
  async generateInformationResponse(email) {
    // In production: Use AI to generate contextual response
    return 'Thank you for your email. The information you requested is...';
  }

  /**
   * Generate draft
   */
  async generateDraft(email) {
    // In production: Use AI to generate appropriate draft
    return {
      to: email.from,
      subject: `Re: ${email.subject}`,
      body: 'Draft response generated by autopilot...'
    };
  }

  /**
   * Determine label
   */
  determineLabel(email) {
    const intent = this.detectIntent(email);

    const labelMap = {
      meeting_request: 'Meetings',
      information_request: 'To Read',
      confirmation: 'Completed',
      acknowledgment: 'Completed',
      urgent_matter: 'Action Required'
    };

    return labelMap[intent] || 'To Read';
  }

  /**
   * Escalate for review
   */
  escalateForReview(email, decision, safetyCheck) {
    return {
      processed: false,
      autonomous: false,
      escalated: true,
      reason: safetyCheck.reason,
      decision,
      requiresReview: true,
      priorityLevel: 'high'
    };
  }

  /**
   * Record decision for learning
   */
  recordDecision(email, decision, execution) {
    this.decisionHistory.push({
      emailId: email.id,
      decision,
      execution,
      timestamp: new Date()
    });

    // Keep last 1000 decisions
    if (this.decisionHistory.length > 1000) {
      this.decisionHistory = this.decisionHistory.slice(-1000);
    }
  }

  /**
   * Get autopilot statistics
   */
  getStatistics() {
    const successful = this.decisionHistory.filter(d => d.execution.success).length;

    return {
      mode: this.mode,
      totalDecisions: this.decisionHistory.length,
      successfulExecutions: successful,
      successRate: this.decisionHistory.length > 0 ?
        (successful / this.decisionHistory.length * 100).toFixed(1) + '%' : '0%',
      avgConfidence: this.calculateAvgConfidence(),
      decisionBreakdown: this.getDecisionBreakdown()
    };
  }

  /**
   * Calculate average confidence
   */
  calculateAvgConfidence() {
    if (this.decisionHistory.length === 0) return 0;

    const totalConfidence = this.decisionHistory.reduce(
      (sum, d) => sum + d.decision.confidence,
      0
    );

    return (totalConfidence / this.decisionHistory.length * 100).toFixed(1);
  }

  /**
   * Get decision breakdown
   */
  getDecisionBreakdown() {
    const breakdown = {};

    for (const record of this.decisionHistory) {
      const action = record.decision.action;
      breakdown[action] = (breakdown[action] || 0) + 1;
    }

    return breakdown;
  }
}

module.exports = new EmailAutopilot();
module.exports.EmailAutopilot = EmailAutopilot;
