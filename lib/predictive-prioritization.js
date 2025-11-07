/**
 * Predictive Email Prioritization System
 * Uses ML and historical patterns to predict email importance before reading
 */

const logger = require('./logger');

class PredictivePrioritization {
  constructor() {
    this.historicalData = [];
    this.patterns = new Map();
    this.userBehavior = {
      readingPatterns: new Map(),
      responsePatterns: new Map(),
      escalationPatterns: new Map()
    };
    this.timeBasedPatterns = new Map();
  }

  /**
   * Predict email priority before opening
   */
  predictPriority(email) {
    const features = this.extractPredictiveFeatures(email);
    const scores = {
      senderScore: this.scoreSender(email.from),
      subjectScore: this.scoreSubject(email.subject),
      timeScore: this.scoreTimingPattern(email.date),
      threadScore: this.scoreThreadImportance(email.threadId),
      behaviorScore: this.scoreUserBehavior(email),
      contextScore: this.scoreContext(email)
    };

    const weights = {
      sender: 0.25,
      subject: 0.20,
      time: 0.15,
      thread: 0.15,
      behavior: 0.15,
      context: 0.10
    };

    const totalScore =
      scores.senderScore * weights.sender +
      scores.subjectScore * weights.subject +
      scores.timeScore * weights.time +
      scores.threadScore * weights.thread +
      scores.behaviorScore * weights.behavior +
      scores.contextScore * weights.context;

    const priority = this.scoreToPriority(totalScore);

    return {
      priority, // critical, high, medium, low
      score: totalScore,
      confidence: this.calculateConfidence(scores),
      breakdown: scores,
      reasoning: this.generateReasoning(scores, priority),
      predictedTier: this.priorityToTier(priority),
      urgencyLevel: this.scoreToUrgency(totalScore),
      suggestedAction: this.suggestAction(priority, scores)
    };
  }

  /**
   * Score sender importance based on history
   */
  scoreSender(from) {
    const senderHistory = this.patterns.get(from) || {
      totalEmails: 0,
      escalatedCount: 0,
      avgResponseTime: 0,
      userEngagement: 0
    };

    if (senderHistory.totalEmails === 0) {
      // New sender - use domain and heuristics
      return this.scoreNewSender(from);
    }

    // Calculate sender score based on history
    const escalationRate = senderHistory.escalatedCount / senderHistory.totalEmails;
    const engagementScore = senderHistory.userEngagement / senderHistory.totalEmails;
    const frequencyBonus = Math.min(senderHistory.totalEmails / 100, 1) * 0.2;

    return Math.min((escalationRate * 0.5 + engagementScore * 0.3 + frequencyBonus) * 100, 100);
  }

  /**
   * Score new sender
   */
  scoreNewSender(from) {
    const domain = this.extractDomain(from);

    // VIP domains
    const vipDomains = ['ceo@', 'cto@', 'cfo@', 'founder@', 'board@'];
    if (vipDomains.some(vip => from.toLowerCase().includes(vip))) {
      return 90;
    }

    // Company domains vs personal
    if (this.isCompanyDomain(domain)) {
      return 60;
    }

    // Default for new personal senders
    return 40;
  }

  /**
   * Score subject line urgency and importance
   */
  scoreSubject(subject) {
    if (!subject) return 30;

    let score = 50; // Base score

    // Urgency keywords
    const urgentKeywords = ['urgent', 'asap', 'critical', 'emergency', 'immediate', 'important'];
    const urgentMatch = urgentKeywords.some(kw => subject.toLowerCase().includes(kw));
    if (urgentMatch) score += 25;

    // Action keywords
    const actionKeywords = ['review', 'approve', 'sign', 'decision', 'respond', 'confirm'];
    const actionMatch = actionKeywords.some(kw => subject.toLowerCase().includes(kw));
    if (actionMatch) score += 15;

    // Business keywords
    const businessKeywords = ['contract', 'proposal', 'revenue', 'budget', 'partnership', 'investment'];
    const businessMatch = businessKeywords.some(kw => subject.toLowerCase().includes(kw));
    if (businessMatch) score += 20;

    // Negative indicators
    const lowPriorityKeywords = ['newsletter', 'unsubscribe', 'fyi', 'update', 'notification'];
    const lowPriorityMatch = lowPriorityKeywords.some(kw => subject.toLowerCase().includes(kw));
    if (lowPriorityMatch) score -= 20;

    // Multiple exclamation marks or all caps (might be spam or overly urgent)
    if ((subject.match(/!/g) || []).length > 2) score -= 10;
    if (subject === subject.toUpperCase() && subject.length > 5) score -= 15;

    return Math.max(0, Math.min(score, 100));
  }

  /**
   * Score based on timing patterns
   */
  scoreTimingPattern(date) {
    const emailDate = new Date(date);
    const hour = emailDate.getHours();
    const day = emailDate.getDay();

    let score = 50;

    // Business hours emails are generally more important
    if (hour >= 9 && hour <= 17) {
      score += 15;
    }

    // After-hours emails from business contacts might be urgent
    if (hour < 7 || hour > 19) {
      score += 10; // Could be urgent
    }

    // Weekday vs weekend
    if (day >= 1 && day <= 5) {
      score += 10; // Weekday
    } else {
      score += 15; // Weekend emails are often urgent
    }

    // Check historical patterns for this time
    const timeKey = `${day}-${hour}`;
    const timePattern = this.timeBasedPatterns.get(timeKey);
    if (timePattern) {
      score += timePattern.avgImportance * 0.2;
    }

    return Math.min(score, 100);
  }

  /**
   * Score thread importance
   */
  scoreThreadImportance(threadId) {
    if (!threadId) return 50;

    const threadPattern = this.patterns.get(`thread_${threadId}`);
    if (!threadPattern) return 50;

    let score = 50;

    // Active threads are more important
    const hoursSinceLastActivity = (Date.now() - new Date(threadPattern.lastActivity)) / (1000 * 60 * 60);
    if (hoursSinceLastActivity < 24) score += 20;
    else if (hoursSinceLastActivity < 72) score += 10;

    // Long threads might be important ongoing discussions
    if (threadPattern.emailCount > 5) score += 15;

    // User engagement in thread
    if (threadPattern.userReplied) score += 20;

    return Math.min(score, 100);
  }

  /**
   * Score based on user behavior patterns
   */
  scoreUserBehavior(email) {
    const from = email.from;
    const readingPattern = this.userBehavior.readingPatterns.get(from);
    const responsePattern = this.userBehavior.responsePatterns.get(from);

    if (!readingPattern && !responsePattern) return 50;

    let score = 50;

    // How quickly does user typically read emails from this sender?
    if (readingPattern && readingPattern.avgReadTime < 3600) { // < 1 hour
      score += 20;
    }

    // How often does user respond?
    if (responsePattern && responsePattern.responseRate > 0.7) {
      score += 20;
    }

    // Does user typically escalate these emails?
    if (responsePattern && responsePattern.escalationRate > 0.3) {
      score += 15;
    }

    return Math.min(score, 100);
  }

  /**
   * Score based on current context
   */
  scoreContext(email) {
    let score = 50;

    // Time of day context
    const now = new Date();
    const hour = now.getHours();

    // Start of day - prioritize emails received overnight
    if (hour >= 7 && hour <= 9) {
      const emailHour = new Date(email.date).getHours();
      if (emailHour < 7 || emailHour > 19) {
        score += 15;
      }
    }

    // End of day - prioritize time-sensitive items
    if (hour >= 16 && hour <= 18) {
      score += 10;
    }

    // Check if email relates to upcoming events
    if (this.hasUpcomingDeadline(email)) {
      score += 25;
    }

    return Math.min(score, 100);
  }

  /**
   * Convert score to priority level
   */
  scoreToPriority(score) {
    if (score >= 80) return 'critical';
    if (score >= 65) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
  }

  /**
   * Convert priority to tier
   */
  priorityToTier(priority) {
    const mapping = {
      'critical': 1,
      'high': 2,
      'medium': 3,
      'low': 4
    };
    return mapping[priority] || 3;
  }

  /**
   * Convert score to urgency
   */
  scoreToUrgency(score) {
    if (score >= 75) return 'immediate';
    if (score >= 60) return 'today';
    if (score >= 40) return 'this_week';
    return 'when_possible';
  }

  /**
   * Calculate confidence in prediction
   */
  calculateConfidence(scores) {
    // Calculate variance in scores
    const values = Object.values(scores);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const variance = values.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / values.length;

    // Low variance = high confidence
    const confidence = Math.max(0, 100 - variance);

    return Math.round(confidence);
  }

  /**
   * Generate reasoning for prediction
   */
  generateReasoning(scores, priority) {
    const reasons = [];

    if (scores.senderScore > 70) {
      reasons.push('High-priority sender based on history');
    } else if (scores.senderScore < 30) {
      reasons.push('Low-engagement sender');
    }

    if (scores.subjectScore > 70) {
      reasons.push('Urgent or action-required subject line');
    }

    if (scores.threadScore > 70) {
      reasons.push('Active conversation thread');
    }

    if (scores.behaviorScore > 70) {
      reasons.push('User typically engages quickly with this sender');
    }

    if (scores.contextScore > 70) {
      reasons.push('Time-sensitive based on current context');
    }

    if (reasons.length === 0) {
      reasons.push('Standard priority based on typical patterns');
    }

    return reasons;
  }

  /**
   * Suggest action based on priority
   */
  suggestAction(priority, scores) {
    const actions = {
      critical: {
        action: 'immediate_review',
        description: 'Review immediately and respond within 1 hour',
        notification: 'Push notification + SMS'
      },
      high: {
        action: 'priority_review',
        description: 'Review within 2 hours during business hours',
        notification: 'Push notification'
      },
      medium: {
        action: 'standard_review',
        description: 'Review within 24 hours',
        notification: 'None - normal queue'
      },
      low: {
        action: 'batch_review',
        description: 'Review in next batch or when time permits',
        notification: 'None'
      }
    };

    return actions[priority] || actions.medium;
  }

  /**
   * Learn from user actions
   */
  learnFromAction(email, userAction, timeTaken) {
    const from = email.from;

    // Update sender patterns
    const senderPattern = this.patterns.get(from) || {
      totalEmails: 0,
      escalatedCount: 0,
      avgResponseTime: 0,
      userEngagement: 0
    };

    senderPattern.totalEmails++;

    if (userAction === 'escalated' || userAction === 'immediate_response') {
      senderPattern.escalatedCount++;
      senderPattern.userEngagement++;
    } else if (userAction === 'responded') {
      senderPattern.userEngagement++;
    }

    if (timeTaken) {
      senderPattern.avgResponseTime =
        (senderPattern.avgResponseTime * (senderPattern.totalEmails - 1) + timeTaken) /
        senderPattern.totalEmails;
    }

    this.patterns.set(from, senderPattern);

    // Update user behavior patterns
    if (!this.userBehavior.readingPatterns.has(from)) {
      this.userBehavior.readingPatterns.set(from, {
        totalRead: 0,
        avgReadTime: 0
      });
    }

    const readingPattern = this.userBehavior.readingPatterns.get(from);
    readingPattern.totalRead++;
    if (timeTaken) {
      readingPattern.avgReadTime =
        (readingPattern.avgReadTime * (readingPattern.totalRead - 1) + timeTaken) /
        readingPattern.totalRead;
    }

    // Update time-based patterns
    const emailDate = new Date(email.date);
    const timeKey = `${emailDate.getDay()}-${emailDate.getHours()}`;
    const timePattern = this.timeBasedPatterns.get(timeKey) || {
      count: 0,
      totalImportance: 0,
      avgImportance: 0
    };

    const importance = userAction === 'escalated' ? 100 :
                      userAction === 'immediate_response' ? 80 :
                      userAction === 'responded' ? 60 : 30;

    timePattern.count++;
    timePattern.totalImportance += importance;
    timePattern.avgImportance = timePattern.totalImportance / timePattern.count;

    this.timeBasedPatterns.set(timeKey, timePattern);

    logger.debug('Learned from user action', {
      from: email.from,
      action: userAction,
      timeTaken
    });
  }

  /**
   * Batch predict priorities for multiple emails
   */
  batchPredict(emails) {
    return emails.map(email => ({
      emailId: email.id,
      prediction: this.predictPriority(email)
    })).sort((a, b) => b.prediction.score - a.prediction.score);
  }

  /**
   * Get prioritized inbox view
   */
  getPrioritizedInbox(emails) {
    const predictions = this.batchPredict(emails);

    return {
      critical: predictions.filter(p => p.prediction.priority === 'critical'),
      high: predictions.filter(p => p.prediction.priority === 'high'),
      medium: predictions.filter(p => p.prediction.priority === 'medium'),
      low: predictions.filter(p => p.prediction.priority === 'low'),
      summary: {
        total: emails.length,
        critical: predictions.filter(p => p.prediction.priority === 'critical').length,
        high: predictions.filter(p => p.prediction.priority === 'high').length,
        requiresAction: predictions.filter(p =>
          p.prediction.priority === 'critical' || p.prediction.priority === 'high'
        ).length
      }
    };
  }

  /**
   * Helper: Extract domain from email
   */
  extractDomain(email) {
    const match = email.match(/@(.+)$/);
    return match ? match[1].toLowerCase() : '';
  }

  /**
   * Helper: Check if company domain
   */
  isCompanyDomain(domain) {
    const personalDomains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com'];
    return !personalDomains.includes(domain);
  }

  /**
   * Helper: Check for upcoming deadline
   */
  hasUpcomingDeadline(email) {
    const text = `${email.subject} ${email.body || ''}`.toLowerCase();
    const deadlineKeywords = ['deadline', 'due date', 'by tomorrow', 'by eod', 'by end of'];
    return deadlineKeywords.some(kw => text.includes(kw));
  }

  /**
   * Extract predictive features
   */
  extractPredictiveFeatures(email) {
    return {
      senderDomain: this.extractDomain(email.from),
      senderHistory: this.patterns.get(email.from),
      subjectLength: (email.subject || '').length,
      hasUrgentKeywords: /urgent|asap|critical/i.test(email.subject || ''),
      timeOfDay: new Date(email.date).getHours(),
      dayOfWeek: new Date(email.date).getDay(),
      threadExists: !!email.threadId
    };
  }

  /**
   * Get statistics
   */
  getStatistics() {
    return {
      totalSendersTracked: this.patterns.size,
      totalTimePatterns: this.timeBasedPatterns.size,
      topSenders: Array.from(this.patterns.entries())
        .sort((a, b) => b[1].userEngagement - a[1].userEngagement)
        .slice(0, 10)
        .map(([sender, data]) => ({ sender, engagement: data.userEngagement }))
    };
  }

  /**
   * Export patterns for backup
   */
  exportPatterns() {
    return {
      patterns: Array.from(this.patterns.entries()),
      userBehavior: {
        reading: Array.from(this.userBehavior.readingPatterns.entries()),
        response: Array.from(this.userBehavior.responsePatterns.entries())
      },
      timePatterns: Array.from(this.timeBasedPatterns.entries()),
      exportedAt: new Date().toISOString()
    };
  }

  /**
   * Import patterns from backup
   */
  importPatterns(data) {
    this.patterns = new Map(data.patterns);
    this.userBehavior.readingPatterns = new Map(data.userBehavior.reading);
    this.userBehavior.responsePatterns = new Map(data.userBehavior.response);
    this.timeBasedPatterns = new Map(data.timePatterns);

    logger.info('Patterns imported', {
      senders: this.patterns.size,
      timePatterns: this.timeBasedPatterns.size
    });
  }
}

module.exports = new PredictivePrioritization();
module.exports.PredictivePrioritization = PredictivePrioritization;
