/**
 * Email State Management with DynamoDB
 * Tracks email processing history, decisions, and metrics
 */

const AWS = require('aws-sdk');
const crypto = require('crypto');
const logger = require('../logger');

class EmailStateManager {
  constructor(config = {}) {
    this.tableName = config.tableName || process.env.STATE_TABLE || 'email-assistant-state';
    this.region = config.region || process.env.AWS_REGION || 'us-east-1';

    // Initialize DynamoDB
    this.dynamodb = new AWS.DynamoDB.DocumentClient({
      region: this.region,
      maxRetries: 3,
      httpOptions: {
        timeout: 5000
      }
    });

    // Cache settings
    this.cacheEnabled = config.cacheEnabled !== false;
    this.cache = new Map();
    this.cacheMaxSize = config.cacheMaxSize || 1000;
    this.cacheTTL = config.cacheTTL || 3600000; // 1 hour
  }

  /**
   * Record email processing
   */
  async recordEmailProcessed(email) {
    const timestamp = Date.now();
    const emailHash = this.generateEmailHash(email);

    const stateItem = {
      pk: `EMAIL#${email.id}`,
      sk: `STATE#${timestamp}`,

      // Email identification
      emailId: email.id,
      messageId: email.messageId,
      threadId: email.threadId,
      emailHash,

      // Email metadata
      subject: email.subject,
      from: email.from,
      to: email.to,
      cc: email.cc,
      date: email.date,
      snippet: email.snippet?.substring(0, 500),

      // Processing results
      tier: email.tier,
      classification: email.classification,
      action: email.action,
      confidence: email.confidence,

      // Labels and tags
      labels: email.labels || [],
      tags: email.tags || [],

      // Response details
      responseGenerated: email.responseGenerated || false,
      responseSent: email.responseSent || false,
      responseContent: email.responseContent,

      // Agent details (if processed by Email Agent)
      agentProcessed: email.agentProcessed || false,
      agentTools: email.agentTools || [],
      agentResult: email.agentResult,

      // Timing
      timestamp,
      processingTime: email.processingTime,

      // User context
      userEmail: email.userEmail,
      timezone: email.timezone || 'America/New_York',

      // GSI attributes for querying
      gsi1pk: `DATE#${new Date(timestamp).toISOString().split('T')[0]}`,
      gsi1sk: `EMAIL#${email.id}`,
      gsi2pk: `TIER#${email.tier}`,
      gsi2sk: `TIME#${timestamp}`,
      gsi3pk: `THREAD#${email.threadId}`,
      gsi3sk: `TIME#${timestamp}`
    };

    try {
      await this.dynamodb.put({
        TableName: this.tableName,
        Item: stateItem
      }).promise();

      // Update cache
      if (this.cacheEnabled) {
        this.updateCache(email.id, stateItem);
      }

      logger.debug('Email state recorded', {
        emailId: email.id,
        tier: email.tier,
        action: email.action
      });

      return stateItem;
    } catch (error) {
      logger.error('Failed to record email state', {
        error: error.message,
        emailId: email.id
      });
      throw error;
    }
  }

  /**
   * Check if email was already processed
   */
  async isProcessed(emailId) {
    // Check cache first
    if (this.cacheEnabled && this.cache.has(emailId)) {
      const cached = this.cache.get(emailId);
      if (Date.now() - cached.timestamp < this.cacheTTL) {
        return true;
      }
    }

    try {
      const result = await this.dynamodb.query({
        TableName: this.tableName,
        KeyConditionExpression: 'pk = :pk',
        ExpressionAttributeValues: {
          ':pk': `EMAIL#${emailId}`
        },
        Limit: 1
      }).promise();

      const processed = result.Items && result.Items.length > 0;

      // Update cache
      if (this.cacheEnabled && processed) {
        this.updateCache(emailId, result.Items[0]);
      }

      return processed;
    } catch (error) {
      logger.error('Failed to check if email processed', {
        error: error.message,
        emailId
      });
      return false;
    }
  }

  /**
   * Get email processing history
   */
  async getEmailHistory(emailId) {
    try {
      const result = await this.dynamodb.query({
        TableName: this.tableName,
        KeyConditionExpression: 'pk = :pk',
        ExpressionAttributeValues: {
          ':pk': `EMAIL#${emailId}`
        },
        ScanIndexForward: false
      }).promise();

      return result.Items || [];
    } catch (error) {
      logger.error('Failed to get email history', {
        error: error.message,
        emailId
      });
      throw error;
    }
  }

  /**
   * Get emails by date
   */
  async getEmailsByDate(date, limit = 100) {
    const dateStr = typeof date === 'string' ? date : date.toISOString().split('T')[0];

    try {
      const result = await this.dynamodb.query({
        TableName: this.tableName,
        IndexName: 'GSI1',
        KeyConditionExpression: 'gsi1pk = :pk',
        ExpressionAttributeValues: {
          ':pk': `DATE#${dateStr}`
        },
        Limit: limit,
        ScanIndexForward: false
      }).promise();

      return result.Items || [];
    } catch (error) {
      logger.error('Failed to get emails by date', {
        error: error.message,
        date: dateStr
      });
      throw error;
    }
  }

  /**
   * Get emails by tier
   */
  async getEmailsByTier(tier, limit = 50) {
    try {
      const result = await this.dynamodb.query({
        TableName: this.tableName,
        IndexName: 'GSI2',
        KeyConditionExpression: 'gsi2pk = :pk',
        ExpressionAttributeValues: {
          ':pk': `TIER#${tier}`
        },
        Limit: limit,
        ScanIndexForward: false
      }).promise();

      return result.Items || [];
    } catch (error) {
      logger.error('Failed to get emails by tier', {
        error: error.message,
        tier
      });
      throw error;
    }
  }

  /**
   * Get thread history
   */
  async getThreadHistory(threadId) {
    try {
      const result = await this.dynamodb.query({
        TableName: this.tableName,
        IndexName: 'GSI3',
        KeyConditionExpression: 'gsi3pk = :pk',
        ExpressionAttributeValues: {
          ':pk': `THREAD#${threadId}`
        },
        ScanIndexForward: true // Chronological order
      }).promise();

      return result.Items || [];
    } catch (error) {
      logger.error('Failed to get thread history', {
        error: error.message,
        threadId
      });
      throw error;
    }
  }

  /**
   * Get processing metrics
   */
  async getMetrics(startDate, endDate) {
    const emails = [];
    let currentDate = new Date(startDate);
    const end = new Date(endDate);

    // Query each day
    while (currentDate <= end) {
      const dateStr = currentDate.toISOString().split('T')[0];
      const dayEmails = await this.getEmailsByDate(dateStr, 1000);
      emails.push(...dayEmails);
      currentDate.setDate(currentDate.getDate() + 1);
    }

    // Calculate metrics
    const metrics = {
      total: emails.length,
      byTier: {},
      byAction: {},
      byHour: {},
      avgProcessingTime: 0,
      responseRate: 0,
      agentProcessedRate: 0,

      // Time-based metrics
      peakHour: null,
      busiestDay: null,

      // Sender metrics
      topSenders: {},

      // Thread metrics
      uniqueThreads: new Set(),
      avgThreadLength: 0
    };

    let totalProcessingTime = 0;
    let responseCount = 0;
    let agentProcessedCount = 0;

    emails.forEach(email => {
      // Tier breakdown
      metrics.byTier[email.tier] = (metrics.byTier[email.tier] || 0) + 1;

      // Action breakdown
      metrics.byAction[email.action] = (metrics.byAction[email.action] || 0) + 1;

      // Hour breakdown
      const hour = new Date(email.timestamp).getHours();
      metrics.byHour[hour] = (metrics.byHour[hour] || 0) + 1;

      // Processing time
      if (email.processingTime) {
        totalProcessingTime += email.processingTime;
      }

      // Response tracking
      if (email.responseSent) {
        responseCount++;
      }

      // Agent processing
      if (email.agentProcessed) {
        agentProcessedCount++;
      }

      // Sender tracking
      const sender = email.from?.toLowerCase();
      if (sender) {
        metrics.topSenders[sender] = (metrics.topSenders[sender] || 0) + 1;
      }

      // Thread tracking
      if (email.threadId) {
        metrics.uniqueThreads.add(email.threadId);
      }
    });

    // Calculate averages
    metrics.avgProcessingTime = emails.length > 0
      ? Math.round(totalProcessingTime / emails.length)
      : 0;

    metrics.responseRate = emails.length > 0
      ? (responseCount / emails.length * 100).toFixed(1) + '%'
      : '0%';

    metrics.agentProcessedRate = emails.length > 0
      ? (agentProcessedCount / emails.length * 100).toFixed(1) + '%'
      : '0%';

    // Find peak hour
    const peakHour = Object.entries(metrics.byHour)
      .sort((a, b) => b[1] - a[1])[0];
    metrics.peakHour = peakHour ? `${peakHour[0]}:00` : null;

    // Top senders (limit to top 10)
    metrics.topSenders = Object.entries(metrics.topSenders)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .reduce((acc, [sender, count]) => {
        acc[sender] = count;
        return acc;
      }, {});

    // Thread metrics
    metrics.uniqueThreads = metrics.uniqueThreads.size;
    metrics.avgThreadLength = metrics.uniqueThreads > 0
      ? Math.round(emails.length / metrics.uniqueThreads)
      : 0;

    return metrics;
  }

  /**
   * Generate dashboard data
   */
  async getDashboardData(days = 7) {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(startDate.getDate() - days);

    const metrics = await this.getMetrics(startDate, endDate);

    // Get recent escalations
    const escalations = await this.getEmailsByTier('TIER_1', 20);

    // Get recent auto-handled
    const autoHandled = await this.getEmailsByTier('TIER_2', 20);

    return {
      period: {
        start: startDate.toISOString(),
        end: endDate.toISOString(),
        days
      },
      metrics,
      recentEscalations: escalations.map(e => ({
        id: e.emailId,
        subject: e.subject,
        from: e.from,
        date: e.date,
        action: e.action
      })),
      recentAutoHandled: autoHandled.map(e => ({
        id: e.emailId,
        subject: e.subject,
        from: e.from,
        date: e.date,
        action: e.action,
        responseSent: e.responseSent
      })),
      lastUpdated: new Date().toISOString()
    };
  }

  /**
   * Update learning data
   */
  async updateLearning(emailId, feedback) {
    const timestamp = Date.now();

    const learningItem = {
      pk: `LEARNING#${emailId}`,
      sk: `FEEDBACK#${timestamp}`,

      emailId,
      timestamp,
      feedback: feedback.feedback, // 'correct', 'incorrect', 'adjusted'
      originalTier: feedback.originalTier,
      correctTier: feedback.correctTier,
      notes: feedback.notes,

      // For pattern learning
      pattern: {
        subject: feedback.subjectPattern,
        sender: feedback.senderPattern,
        keywords: feedback.keywords
      }
    };

    try {
      await this.dynamodb.put({
        TableName: this.tableName,
        Item: learningItem
      }).promise();

      logger.info('Learning feedback recorded', {
        emailId,
        feedback: feedback.feedback
      });

      return learningItem;
    } catch (error) {
      logger.error('Failed to record learning feedback', {
        error: error.message,
        emailId
      });
      throw error;
    }
  }

  /**
   * Get learning patterns
   */
  async getLearningPatterns(limit = 100) {
    try {
      const result = await this.dynamodb.scan({
        TableName: this.tableName,
        FilterExpression: 'begins_with(pk, :pk)',
        ExpressionAttributeValues: {
          ':pk': 'LEARNING#'
        },
        Limit: limit
      }).promise();

      // Analyze patterns
      const patterns = {
        corrections: [],
        commonMistakes: {},
        senderPatterns: {},
        subjectPatterns: {}
      };

      result.Items?.forEach(item => {
        if (item.feedback === 'incorrect' || item.feedback === 'adjusted') {
          patterns.corrections.push({
            original: item.originalTier,
            correct: item.correctTier,
            pattern: item.pattern
          });

          const mistake = `${item.originalTier}->${item.correctTier}`;
          patterns.commonMistakes[mistake] = (patterns.commonMistakes[mistake] || 0) + 1;
        }

        if (item.pattern?.sender) {
          patterns.senderPatterns[item.pattern.sender] = item.correctTier;
        }

        if (item.pattern?.subject) {
          patterns.subjectPatterns[item.pattern.subject] = item.correctTier;
        }
      });

      return patterns;
    } catch (error) {
      logger.error('Failed to get learning patterns', {
        error: error.message
      });
      throw error;
    }
  }

  /**
   * Generate email hash for deduplication
   */
  generateEmailHash(email) {
    const normalized = {
      subject: email.subject?.toLowerCase().trim(),
      from: email.from?.toLowerCase().trim(),
      date: email.date,
      snippet: email.snippet?.substring(0, 200)
    };

    return crypto
      .createHash('sha256')
      .update(JSON.stringify(normalized))
      .digest('hex')
      .substring(0, 16);
  }

  /**
   * Update cache
   */
  updateCache(emailId, data) {
    if (this.cache.size >= this.cacheMaxSize) {
      // Evict oldest entry
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }

    this.cache.set(emailId, {
      ...data,
      cachedAt: Date.now()
    });
  }

  /**
   * Clear cache
   */
  clearCache() {
    this.cache.clear();
    logger.debug('Email state cache cleared');
  }
}

module.exports = EmailStateManager;