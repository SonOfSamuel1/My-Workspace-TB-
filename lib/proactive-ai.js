/**
 * Proactive Communication AI
 * Anticipates needs and suggests proactive communications
 */

const logger = require('./logger');

class ProactiveAI {
  constructor() {
    this.suggestions = [];
    this.patterns = new Map();
    this.triggers = this.initializeTriggers();
  }

  /**
   * Initialize proactive triggers
   */
  initializeTriggers() {
    return {
      'follow_up_needed': {
        check: (email, context) => this.checkFollowUpNeeded(email, context),
        suggestion: 'Send follow-up email'
      },
      'deadline_approaching': {
        check: (email, context) => this.checkDeadlineApproaching(email, context),
        suggestion: 'Remind about upcoming deadline'
      },
      'relationship_maintenance': {
        check: (email, context) => this.checkRelationshipMaintenance(email, context),
        suggestion: 'Check in with contact'
      },
      'opportunity_detected': {
        check: (email, context) => this.checkOpportunity(email, context),
        suggestion: 'Reach out proactively'
      },
      'meeting_prep': {
        check: (email, context) => this.checkMeetingPrep(email, context),
        suggestion: 'Prepare for upcoming meeting'
      }
    };
  }

  /**
   * Analyze and generate proactive suggestions
   */
  async generateSuggestions(emails, context) {
    const suggestions = [];

    for (const email of emails) {
      // Check all triggers
      for (const [triggerName, trigger] of Object.entries(this.triggers)) {
        const result = await trigger.check(email, context);

        if (result.triggered) {
          suggestions.push({
            type: triggerName,
            email,
            suggestion: trigger.suggestion,
            reasoning: result.reasoning,
            priority: result.priority || 'medium',
            confidence: result.confidence || 0.75,
            suggestedAction: result.action,
            draftContent: result.draftContent || null
          });
        }
      }
    }

    // Sort by priority and confidence
    suggestions.sort((a, b) => {
      const priorityOrder = { high: 3, medium: 2, low: 1 };
      const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
      if (priorityDiff !== 0) return priorityDiff;
      return b.confidence - a.confidence;
    });

    this.suggestions = suggestions;

    logger.info('Proactive suggestions generated', {
      count: suggestions.length,
      high: suggestions.filter(s => s.priority === 'high').length
    });

    return suggestions;
  }

  /**
   * Check if follow-up is needed
   */
  async checkFollowUpNeeded(email, context) {
    // Check if we sent an email and haven't heard back
    if (!email.sentByUs) return { triggered: false };

    const daysSinceSent = (Date.now() - new Date(email.date)) / (1000 * 60 * 60 * 24);

    if (daysSinceSent >= 3 && !email.hasResponse) {
      return {
        triggered: true,
        reasoning: `No response received for ${Math.floor(daysSinceSent)} days`,
        priority: 'medium',
        confidence: 0.80,
        action: 'send_follow_up',
        draftContent: await this.generateFollowUpDraft(email)
      };
    }

    return { triggered: false };
  }

  /**
   * Check for approaching deadlines
   */
  async checkDeadlineApproaching(email, context) {
    // Extract deadlines from email
    const deadlines = this.extractDeadlines(email);

    for (const deadline of deadlines) {
      const daysUntil = (new Date(deadline.date) - Date.now()) / (1000 * 60 * 60 * 24);

      if (daysUntil <= 2 && daysUntil > 0) {
        return {
          triggered: true,
          reasoning: `Deadline in ${Math.ceil(daysUntil)} days: ${deadline.description}`,
          priority: 'high',
          confidence: 0.85,
          action: 'send_reminder',
          draftContent: await this.generateDeadlineReminder(email, deadline)
        };
      }
    }

    return { triggered: false };
  }

  /**
   * Check relationship maintenance
   */
  async checkRelationshipMaintenance(email, context) {
    // Check when we last reached out to this person
    const lastContact = context.lastContactWith?.[email.from];

    if (!lastContact) return { triggered: false };

    const daysSinceContact = (Date.now() - new Date(lastContact)) / (1000 * 60 * 60 * 24);

    // If it's been more than 30 days with an important contact
    if (daysSinceContact >= 30 && context.isImportantContact(email.from)) {
      return {
        triggered: true,
        reasoning: `${Math.floor(daysSinceContact)} days since last contact`,
        priority: 'low',
        confidence: 0.70,
        action: 'check_in',
        draftContent: await this.generateCheckInDraft(email)
      };
    }

    return { triggered: false };
  }

  /**
   * Check for opportunities
   */
  async checkOpportunity(email, context) {
    const text = `${email.subject} ${email.body}`.toLowerCase();

    const opportunityKeywords = [
      'looking for', 'interested in', 'need help with',
      'seeking', 'opportunity', 'partnership', 'collaboration'
    ];

    const hasOpportunity = opportunityKeywords.some(kw => text.includes(kw));

    if (hasOpportunity && !email.responded) {
      return {
        triggered: true,
        reasoning: 'Potential opportunity detected in email',
        priority: 'high',
        confidence: 0.75,
        action: 'respond_to_opportunity',
        draftContent: await this.generateOpportunityResponse(email)
      };
    }

    return { triggered: false };
  }

  /**
   * Check meeting prep
   */
  async checkMeetingPrep(email, context) {
    // Check if there's an upcoming meeting with this person
    const upcomingMeeting = context.upcomingMeetings?.find(m =>
      m.attendees.includes(email.from)
    );

    if (!upcomingMeeting) return { triggered: false };

    const hoursUntil = (new Date(upcomingMeeting.start) - Date.now()) / (1000 * 60 * 60);

    // If meeting is in 2-24 hours
    if (hoursUntil >= 2 && hoursUntil <= 24) {
      return {
        triggered: true,
        reasoning: `Meeting with ${email.from} in ${Math.ceil(hoursUntil)} hours`,
        priority: 'medium',
        confidence: 0.90,
        action: 'prepare_meeting_context',
        draftContent: await this.generateMeetingPrepSummary(email, upcomingMeeting)
      };
    }

    return { triggered: false };
  }

  /**
   * Generate follow-up draft
   */
  async generateFollowUpDraft(email) {
    return {
      to: email.to,
      subject: `Following up: ${email.subject}`,
      body: `Hi,\n\nI wanted to follow up on my previous email regarding ${email.subject}. \n\nDo you have any thoughts on this?\n\nBest regards`
    };
  }

  /**
   * Generate deadline reminder
   */
  async generateDeadlineReminder(email, deadline) {
    return {
      to: email.from,
      subject: `Reminder: ${deadline.description}`,
      body: `Hi,\n\nJust a friendly reminder that ${deadline.description} is coming up on ${deadline.date}.\n\nLet me know if you need anything.\n\nBest regards`
    };
  }

  /**
   * Generate check-in draft
   */
  async generateCheckInDraft(email) {
    return {
      to: email.from,
      subject: 'Checking in',
      body: `Hi,\n\nIt's been a while since we last connected. I wanted to check in and see how things are going.\n\nLet me know if there's anything I can help with.\n\nBest regards`
    };
  }

  /**
   * Generate opportunity response
   */
  async generateOpportunityResponse(email) {
    return {
      to: email.from,
      subject: `Re: ${email.subject}`,
      body: `Hi,\n\nThank you for reaching out. I'm interested in exploring this opportunity further.\n\nWould you be available for a call to discuss?\n\nBest regards`
    };
  }

  /**
   * Generate meeting prep summary
   */
  async generateMeetingPrepSummary(email, meeting) {
    return {
      type: 'internal_note',
      subject: `Meeting Prep: ${meeting.title}`,
      body: `Upcoming meeting with ${email.from}\n\nTime: ${meeting.start}\nTopic: ${meeting.title}\n\nRecent context:\n- Last email: ${email.subject}\n- Relationship status: Active\n\nKey points to discuss:\n[To be filled based on email history]`
    };
  }

  /**
   * Extract deadlines from email
   */
  extractDeadlines(email) {
    const text = `${email.subject} ${email.body}`;
    const deadlines = [];

    // Simple date extraction (in production, use more sophisticated NLP)
    const datePatterns = [
      /by (\w+ \d{1,2})/gi,
      /deadline: (\w+ \d{1,2})/gi,
      /due (\w+ \d{1,2})/gi
    ];

    for (const pattern of datePatterns) {
      const matches = text.matchAll(pattern);
      for (const match of matches) {
        deadlines.push({
          description: match[0],
          date: match[1], // Would parse this properly in production
          source: email.id
        });
      }
    }

    return deadlines;
  }

  /**
   * Get pending suggestions
   */
  getPendingSuggestions() {
    return this.suggestions.filter(s => !s.actedUpon);
  }

  /**
   * Act on suggestion
   */
  async actOnSuggestion(suggestionId, action) {
    const suggestion = this.suggestions.find(s => s.id === suggestionId);

    if (!suggestion) {
      throw new Error('Suggestion not found');
    }

    logger.info('Acting on proactive suggestion', {
      suggestionId,
      type: suggestion.type,
      action
    });

    suggestion.actedUpon = true;
    suggestion.actionTaken = action;
    suggestion.actionedAt = new Date();

    // In production: Execute the actual action
    return {
      success: true,
      action,
      suggestion
    };
  }

  /**
   * Dismiss suggestion
   */
  dismissSuggestion(suggestionId, reason) {
    const suggestion = this.suggestions.find(s => s.id === suggestionId);

    if (suggestion) {
      suggestion.dismissed = true;
      suggestion.dismissReason = reason;

      logger.debug('Proactive suggestion dismissed', {
        suggestionId,
        reason
      });
    }
  }

  /**
   * Get statistics
   */
  getStatistics() {
    return {
      totalSuggestions: this.suggestions.length,
      pending: this.suggestions.filter(s => !s.actedUpon && !s.dismissed).length,
      actedUpon: this.suggestions.filter(s => s.actedUpon).length,
      dismissed: this.suggestions.filter(s => s.dismissed).length,
      byType: this.getSuggestionsByType(),
      byPriority: {
        high: this.suggestions.filter(s => s.priority === 'high').length,
        medium: this.suggestions.filter(s => s.priority === 'medium').length,
        low: this.suggestions.filter(s => s.priority === 'low').length
      }
    };
  }

  /**
   * Get suggestions by type
   */
  getSuggestionsByType() {
    const byType = {};

    for (const suggestion of this.suggestions) {
      byType[suggestion.type] = (byType[suggestion.type] || 0) + 1;
    }

    return byType;
  }
}

module.exports = new ProactiveAI();
module.exports.ProactiveAI = ProactiveAI;
