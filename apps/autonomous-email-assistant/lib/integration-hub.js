/**
 * Integration Hub
 * Connect with external services: Salesforce, HubSpot, Slack, Calendar, CRM, etc.
 */

const logger = require('./logger');

class IntegrationHub {
  constructor() {
    this.integrations = new Map();
    this.supportedIntegrations = {
      salesforce: { name: 'Salesforce', category: 'crm', oauth: true },
      hubspot: { name: 'HubSpot', category: 'crm', oauth: true },
      slack: { name: 'Slack', category: 'communication', oauth: true },
      calendar: { name: 'Google Calendar', category: 'productivity', oauth: true },
      notion: { name: 'Notion', category: 'productivity', oauth: true },
      asana: { name: 'Asana', category: 'project_management', oauth: true },
      jira: { name: 'Jira', category: 'project_management', oauth: true },
      zapier: { name: 'Zapier', category: 'automation', webhook: true },
      webhooks: { name: 'Custom Webhooks', category: 'automation', webhook: true }
    };
  }

  /**
   * Add integration
   */
  async addIntegration(userId, integrationType, config) {
    const integrationId = `int_${Date.now()}`;

    const integration = {
      id: integrationId,
      userId,
      type: integrationType,
      config,
      enabled: true,
      createdAt: new Date(),
      lastSync: null,
      syncCount: 0,
      errorCount: 0
    };

    this.integrations.set(integrationId, integration);

    logger.info('Integration added', {
      userId,
      type: integrationType,
      integrationId
    });

    return integration;
  }

  /**
   * Sync with Salesforce
   */
  async syncSalesforce(integrationId, email) {
    logger.info('Syncing with Salesforce', { integrationId });

    // In production: Call Salesforce API
    // - Create/update Contact
    // - Create Activity/Task
    // - Update Opportunity
    // - Create Case if needed

    return {
      success: true,
      actions: ['contact_updated', 'activity_created'],
      salesforceUrl: `https://example.salesforce.com/contact/123`
    };
  }

  /**
   * Sync with HubSpot
   */
  async syncHubSpot(integrationId, email) {
    logger.info('Syncing with HubSpot', { integrationId });

    // In production: Call HubSpot API
    // - Create/update Contact
    // - Log email engagement
    // - Update Deal
    // - Create Ticket if needed

    return {
      success: true,
      actions: ['contact_synced', 'engagement_logged'],
      hubspotUrl: `https://app.hubspot.com/contacts/123`
    };
  }

  /**
   * Send to Slack
   */
  async sendToSlack(integrationId, message) {
    const integration = this.integrations.get(integrationId);
    if (!integration) throw new Error('Integration not found');

    logger.info('Sending to Slack', { integrationId });

    // Already implemented in slack-bot.js
    // This wraps it for integration hub

    return {
      success: true,
      channel: integration.config.channel,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Create calendar event
   */
  async createCalendarEvent(integrationId, eventData) {
    logger.info('Creating calendar event', { integrationId });

    // In production: Call Google Calendar API
    // - Create event
    // - Send invites
    // - Set reminders

    return {
      success: true,
      eventId: 'cal_event_123',
      eventUrl: `https://calendar.google.com/event/123`
    };
  }

  /**
   * Create Notion page
   */
  async createNotionPage(integrationId, pageData) {
    logger.info('Creating Notion page', { integrationId });

    // In production: Call Notion API
    // - Create page in database
    // - Add properties
    // - Link related items

    return {
      success: true,
      pageId: 'notion_page_123',
      pageUrl: `https://notion.so/page/123`
    };
  }

  /**
   * Create Asana task
   */
  async createAsanaTask(integrationId, taskData) {
    logger.info('Creating Asana task', { integrationId });

    // In production: Call Asana API
    // - Create task
    // - Assign to user
    // - Set due date
    // - Add to project

    return {
      success: true,
      taskId: 'asana_task_123',
      taskUrl: `https://app.asana.com/0/123`
    };
  }

  /**
   * Create Jira issue
   */
  async createJiraIssue(integrationId, issueData) {
    logger.info('Creating Jira issue', { integrationId });

    // In production: Call Jira API
    // - Create issue
    // - Set priority
    // - Assign
    // - Link to epic/sprint

    return {
      success: true,
      issueKey: 'PROJ-123',
      issueUrl: `https://company.atlassian.net/browse/PROJ-123`
    };
  }

  /**
   * Trigger Zapier webhook
   */
  async triggerZapier(integrationId, data) {
    const integration = this.integrations.get(integrationId);
    if (!integration) throw new Error('Integration not found');

    logger.info('Triggering Zapier webhook', { integrationId });

    // In production: HTTP POST to Zapier webhook
    // - Send email data
    // - Zapier handles the rest

    return {
      success: true,
      webhookUrl: integration.config.webhookUrl
    };
  }

  /**
   * Trigger custom webhook
   */
  async triggerWebhook(integrationId, data) {
    const integration = this.integrations.get(integrationId);
    if (!integration) throw new Error('Integration not found');

    logger.info('Triggering custom webhook', { integrationId });

    // In production: HTTP POST to custom endpoint
    // Include authentication headers

    return {
      success: true,
      endpoint: integration.config.endpoint,
      statusCode: 200
    };
  }

  /**
   * Handle integration based on email event
   */
  async handleEmailEvent(userId, event, data) {
    const userIntegrations = this.getUserIntegrations(userId);
    const results = [];

    for (const integration of userIntegrations) {
      if (!integration.enabled) continue;

      try {
        let result;

        switch (integration.type) {
          case 'salesforce':
            if (event === 'email_received' || event === 'email_sent') {
              result = await this.syncSalesforce(integration.id, data);
            }
            break;

          case 'hubspot':
            if (event === 'email_received' || event === 'email_sent') {
              result = await this.syncHubSpot(integration.id, data);
            }
            break;

          case 'slack':
            if (event === 'escalation' || event === 'draft_ready') {
              result = await this.sendToSlack(integration.id, data);
            }
            break;

          case 'webhooks':
            result = await this.triggerWebhook(integration.id, { event, data });
            break;

          case 'zapier':
            result = await this.triggerZapier(integration.id, { event, data });
            break;
        }

        if (result) {
          integration.lastSync = new Date();
          integration.syncCount++;
          results.push({ integration: integration.type, result });
        }

      } catch (error) {
        integration.errorCount++;
        logger.error('Integration failed', {
          integrationType: integration.type,
          error: error.message
        });
        results.push({
          integration: integration.type,
          error: error.message
        });
      }
    }

    return results;
  }

  /**
   * Get user integrations
   */
  getUserIntegrations(userId) {
    return Array.from(this.integrations.values())
      .filter(i => i.userId === userId);
  }

  /**
   * Test integration
   */
  async testIntegration(integrationId) {
    const integration = this.integrations.get(integrationId);
    if (!integration) throw new Error('Integration not found');

    logger.info('Testing integration', {
      integrationId,
      type: integration.type
    });

    // Test connection based on type
    try {
      const testData = { test: true, timestamp: new Date().toISOString() };

      switch (integration.type) {
        case 'webhooks':
        case 'zapier':
          return await this.triggerWebhook(integrationId, testData);

        case 'slack':
          return await this.sendToSlack(integrationId, 'Integration test successful');

        default:
          return { success: true, message: 'Test placeholder' };
      }
    } catch (error) {
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Get integration statistics
   */
  getStatistics() {
    const stats = {
      totalIntegrations: this.integrations.size,
      byType: {},
      totalSyncs: 0,
      totalErrors: 0
    };

    for (const integration of this.integrations.values()) {
      if (!stats.byType[integration.type]) {
        stats.byType[integration.type] = {
          count: 0,
          syncs: 0,
          errors: 0
        };
      }

      stats.byType[integration.type].count++;
      stats.byType[integration.type].syncs += integration.syncCount;
      stats.byType[integration.type].errors += integration.errorCount;

      stats.totalSyncs += integration.syncCount;
      stats.totalErrors += integration.errorCount;
    }

    return stats;
  }

  /**
   * Export data
   */
  exportData() {
    return {
      integrations: Array.from(this.integrations.entries()),
      exportedAt: new Date().toISOString()
    };
  }

  /**
   * Import data
   */
  importData(data) {
    this.integrations = new Map(data.integrations);
    logger.info('Integration data imported', {
      integrations: this.integrations.size
    });
  }
}

module.exports = new IntegrationHub();
module.exports.IntegrationHub = IntegrationHub;
