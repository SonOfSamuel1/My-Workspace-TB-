/**
 * Approval Queue Management with DynamoDB
 * Handles pending approvals, history, and user decisions
 */

const AWS = require('aws-sdk');
const { v4: uuidv4 } = require('uuid');
const logger = require('../logger');

class ApprovalQueueManager {
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

    // Queue settings
    this.maxQueueSize = config.maxQueueSize || 100;
    this.retentionDays = config.retentionDays || 30;
    this.defaultTTL = config.defaultTTL || 86400; // 24 hours
  }

  /**
   * Add item to approval queue
   */
  async addToQueue(item) {
    const approvalId = uuidv4();
    const timestamp = Date.now();
    const ttl = Math.floor(timestamp / 1000) + this.defaultTTL;

    const queueItem = {
      pk: `APPROVAL#${approvalId}`,
      sk: `PENDING#${timestamp}`,
      approvalId,
      timestamp,
      ttl,
      status: 'PENDING',
      type: item.type || 'EMAIL_ACTION',

      // Email details
      emailId: item.emailId,
      subject: item.subject,
      from: item.from,
      to: item.to,
      threadId: item.threadId,

      // Action details
      action: item.action,
      actionType: item.actionType,
      tier: item.tier,

      // Draft or response
      draftContent: item.draftContent,
      suggestedResponse: item.suggestedResponse,

      // Agent request details (if from Email Agent)
      agentRequest: item.agentRequest,
      agentTools: item.agentTools,

      // Metadata
      confidence: item.confidence,
      reasoning: item.reasoning,
      tags: item.tags || [],

      // User context
      userEmail: item.userEmail,
      timezone: item.timezone || 'America/New_York',

      // GSI attributes
      gsi1pk: `USER#${item.userEmail}`,
      gsi1sk: `PENDING#${timestamp}`,
      gsi2pk: `TYPE#${item.type}`,
      gsi2sk: `PENDING#${timestamp}`
    };

    try {
      await this.dynamodb.put({
        TableName: this.tableName,
        Item: queueItem,
        ConditionExpression: 'attribute_not_exists(pk)'
      }).promise();

      logger.info('Added item to approval queue', {
        approvalId,
        type: item.type,
        emailId: item.emailId
      });

      // Check queue size and cleanup if needed
      await this.cleanupIfNeeded();

      return { approvalId, item: queueItem };
    } catch (error) {
      logger.error('Failed to add to approval queue', {
        error: error.message,
        item
      });
      throw error;
    }
  }

  /**
   * Get pending approvals for user
   */
  async getPendingApprovals(userEmail, limit = 20) {
    try {
      const result = await this.dynamodb.query({
        TableName: this.tableName,
        IndexName: 'GSI1',
        KeyConditionExpression: 'gsi1pk = :pk AND begins_with(gsi1sk, :sk)',
        ExpressionAttributeValues: {
          ':pk': `USER#${userEmail}`,
          ':sk': 'PENDING#'
        },
        Limit: limit,
        ScanIndexForward: false // Newest first
      }).promise();

      return result.Items || [];
    } catch (error) {
      logger.error('Failed to get pending approvals', {
        error: error.message,
        userEmail
      });
      throw error;
    }
  }

  /**
   * Get pending approvals by type
   */
  async getPendingByType(type, limit = 20) {
    try {
      const result = await this.dynamodb.query({
        TableName: this.tableName,
        IndexName: 'GSI2',
        KeyConditionExpression: 'gsi2pk = :pk AND begins_with(gsi2sk, :sk)',
        ExpressionAttributeValues: {
          ':pk': `TYPE#${type}`,
          ':sk': 'PENDING#'
        },
        Limit: limit,
        ScanIndexForward: false
      }).promise();

      return result.Items || [];
    } catch (error) {
      logger.error('Failed to get pending by type', {
        error: error.message,
        type
      });
      throw error;
    }
  }

  /**
   * Approve an item
   */
  async approve(approvalId, updates = {}) {
    const timestamp = Date.now();

    try {
      // Get original item
      const original = await this.getApproval(approvalId);
      if (!original) {
        throw new Error('Approval not found');
      }

      // Move to approved history
      const approvedItem = {
        ...original,
        pk: `APPROVAL#${approvalId}`,
        sk: `APPROVED#${timestamp}`,
        status: 'APPROVED',
        approvedAt: timestamp,
        approvedBy: updates.approvedBy,
        modifications: updates.modifications || {},
        finalContent: updates.finalContent || original.draftContent,

        // Update GSI attributes
        gsi1pk: `USER#${original.userEmail}`,
        gsi1sk: `APPROVED#${timestamp}`,
        gsi2pk: `TYPE#${original.type}`,
        gsi2sk: `APPROVED#${timestamp}`
      };

      // Transaction: Delete pending, add approved
      await this.dynamodb.transactWrite({
        TransactItems: [
          {
            Delete: {
              TableName: this.tableName,
              Key: {
                pk: original.pk,
                sk: original.sk
              }
            }
          },
          {
            Put: {
              TableName: this.tableName,
              Item: approvedItem
            }
          }
        ]
      }).promise();

      logger.info('Approval granted', {
        approvalId,
        emailId: original.emailId
      });

      return approvedItem;
    } catch (error) {
      logger.error('Failed to approve item', {
        error: error.message,
        approvalId
      });
      throw error;
    }
  }

  /**
   * Reject an item
   */
  async reject(approvalId, reason = '') {
    const timestamp = Date.now();

    try {
      // Get original item
      const original = await this.getApproval(approvalId);
      if (!original) {
        throw new Error('Approval not found');
      }

      // Move to rejected history
      const rejectedItem = {
        ...original,
        pk: `APPROVAL#${approvalId}`,
        sk: `REJECTED#${timestamp}`,
        status: 'REJECTED',
        rejectedAt: timestamp,
        rejectionReason: reason,

        // Update GSI attributes
        gsi1pk: `USER#${original.userEmail}`,
        gsi1sk: `REJECTED#${timestamp}`,
        gsi2pk: `TYPE#${original.type}`,
        gsi2sk: `REJECTED#${timestamp}`
      };

      // Transaction: Delete pending, add rejected
      await this.dynamodb.transactWrite({
        TransactItems: [
          {
            Delete: {
              TableName: this.tableName,
              Key: {
                pk: original.pk,
                sk: original.sk
              }
            }
          },
          {
            Put: {
              TableName: this.tableName,
              Item: rejectedItem
            }
          }
        ]
      }).promise();

      logger.info('Approval rejected', {
        approvalId,
        emailId: original.emailId,
        reason
      });

      return rejectedItem;
    } catch (error) {
      logger.error('Failed to reject item', {
        error: error.message,
        approvalId
      });
      throw error;
    }
  }

  /**
   * Get specific approval
   */
  async getApproval(approvalId) {
    try {
      // Query with approval ID prefix
      const result = await this.dynamodb.query({
        TableName: this.tableName,
        KeyConditionExpression: 'pk = :pk',
        ExpressionAttributeValues: {
          ':pk': `APPROVAL#${approvalId}`
        },
        Limit: 1
      }).promise();

      return result.Items?.[0];
    } catch (error) {
      logger.error('Failed to get approval', {
        error: error.message,
        approvalId
      });
      throw error;
    }
  }

  /**
   * Get approval history
   */
  async getHistory(userEmail, status = null, limit = 50) {
    try {
      let keyCondition = 'gsi1pk = :pk';
      let expressionValues = {
        ':pk': `USER#${userEmail}`
      };

      if (status) {
        keyCondition += ' AND begins_with(gsi1sk, :sk)';
        expressionValues[':sk'] = `${status}#`;
      }

      const result = await this.dynamodb.query({
        TableName: this.tableName,
        IndexName: 'GSI1',
        KeyConditionExpression: keyCondition,
        ExpressionAttributeValues: expressionValues,
        Limit: limit,
        ScanIndexForward: false
      }).promise();

      return result.Items || [];
    } catch (error) {
      logger.error('Failed to get history', {
        error: error.message,
        userEmail,
        status
      });
      throw error;
    }
  }

  /**
   * Bulk approve multiple items
   */
  async bulkApprove(approvalIds, approvedBy) {
    const results = {
      successful: [],
      failed: []
    };

    for (const approvalId of approvalIds) {
      try {
        const approved = await this.approve(approvalId, { approvedBy });
        results.successful.push(approved);
      } catch (error) {
        results.failed.push({
          approvalId,
          error: error.message
        });
      }
    }

    logger.info('Bulk approval complete', {
      successful: results.successful.length,
      failed: results.failed.length
    });

    return results;
  }

  /**
   * Get statistics
   */
  async getStatistics(userEmail) {
    try {
      const [pending, approved, rejected] = await Promise.all([
        this.getPendingApprovals(userEmail, 100),
        this.getHistory(userEmail, 'APPROVED', 100),
        this.getHistory(userEmail, 'REJECTED', 100)
      ]);

      // Calculate stats
      const stats = {
        pending: pending.length,
        approved: approved.length,
        rejected: rejected.length,
        total: pending.length + approved.length + rejected.length,
        approvalRate: approved.length > 0
          ? (approved.length / (approved.length + rejected.length) * 100).toFixed(1) + '%'
          : '0%',

        // By type breakdown
        byType: {},

        // By tier breakdown
        byTier: {},

        // Time-based stats
        oldestPending: pending.length > 0
          ? new Date(Math.min(...pending.map(p => p.timestamp))).toISOString()
          : null,

        averageResponseTime: this.calculateAverageResponseTime(approved.concat(rejected))
      };

      // Count by type
      [...pending, ...approved, ...rejected].forEach(item => {
        stats.byType[item.type] = (stats.byType[item.type] || 0) + 1;
        if (item.tier) {
          stats.byTier[item.tier] = (stats.byTier[item.tier] || 0) + 1;
        }
      });

      return stats;
    } catch (error) {
      logger.error('Failed to get statistics', {
        error: error.message,
        userEmail
      });
      throw error;
    }
  }

  /**
   * Calculate average response time
   */
  calculateAverageResponseTime(items) {
    const responseTimes = items
      .filter(item => item.approvedAt || item.rejectedAt)
      .map(item => (item.approvedAt || item.rejectedAt) - item.timestamp);

    if (responseTimes.length === 0) return 0;

    const average = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length;
    return Math.round(average / 1000 / 60); // Convert to minutes
  }

  /**
   * Cleanup old items
   */
  async cleanup() {
    const cutoff = Date.now() - (this.retentionDays * 24 * 60 * 60 * 1000);

    try {
      // Query for old items
      const oldItems = await this.dynamodb.scan({
        TableName: this.tableName,
        FilterExpression: 'timestamp < :cutoff AND begins_with(pk, :prefix)',
        ExpressionAttributeValues: {
          ':cutoff': cutoff,
          ':prefix': 'APPROVAL#'
        },
        ProjectionExpression: 'pk, sk'
      }).promise();

      if (oldItems.Items && oldItems.Items.length > 0) {
        // Batch delete old items
        const deleteRequests = oldItems.Items.map(item => ({
          DeleteRequest: {
            Key: {
              pk: item.pk,
              sk: item.sk
            }
          }
        }));

        // Process in batches of 25
        for (let i = 0; i < deleteRequests.length; i += 25) {
          const batch = deleteRequests.slice(i, i + 25);
          await this.dynamodb.batchWrite({
            RequestItems: {
              [this.tableName]: batch
            }
          }).promise();
        }

        logger.info('Cleaned up old approval items', {
          count: oldItems.Items.length
        });
      }
    } catch (error) {
      logger.error('Failed to cleanup old items', {
        error: error.message
      });
    }
  }

  /**
   * Cleanup if queue is too large
   */
  async cleanupIfNeeded() {
    try {
      // Count pending items
      const result = await this.dynamodb.scan({
        TableName: this.tableName,
        FilterExpression: 'begins_with(sk, :sk)',
        ExpressionAttributeValues: {
          ':sk': 'PENDING#'
        },
        Select: 'COUNT'
      }).promise();

      if (result.Count > this.maxQueueSize) {
        await this.cleanup();
      }
    } catch (error) {
      logger.error('Failed to check queue size', {
        error: error.message
      });
    }
  }

  /**
   * Export queue data
   */
  async export(userEmail) {
    try {
      const [pending, approved, rejected] = await Promise.all([
        this.getPendingApprovals(userEmail, 1000),
        this.getHistory(userEmail, 'APPROVED', 1000),
        this.getHistory(userEmail, 'REJECTED', 1000)
      ]);

      return {
        exported: new Date().toISOString(),
        user: userEmail,
        statistics: await this.getStatistics(userEmail),
        pending: pending.map(this.sanitizeItem),
        approved: approved.map(this.sanitizeItem),
        rejected: rejected.map(this.sanitizeItem)
      };
    } catch (error) {
      logger.error('Failed to export data', {
        error: error.message,
        userEmail
      });
      throw error;
    }
  }

  /**
   * Sanitize item for export
   */
  sanitizeItem(item) {
    const sanitized = { ...item };
    delete sanitized.pk;
    delete sanitized.sk;
    delete sanitized.gsi1pk;
    delete sanitized.gsi1sk;
    delete sanitized.gsi2pk;
    delete sanitized.gsi2sk;
    delete sanitized.ttl;
    return sanitized;
  }
}

module.exports = ApprovalQueueManager;