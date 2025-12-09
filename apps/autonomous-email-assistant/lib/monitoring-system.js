/**
 * Comprehensive Monitoring and Cost Tracking System
 * Tracks metrics, costs, performance, and generates insights
 */

const fs = require('fs').promises;
const path = require('path');
const logger = require('./logger');

class MonitoringSystem {
  constructor(config = {}) {
    this.metricsPath = config.metricsPath || '/tmp/email-metrics.json';
    this.costPath = config.costPath || '/tmp/email-costs.json';
    this.alertsPath = config.alertsPath || '/tmp/email-alerts.json';

    // Metric stores
    this.metrics = {
      executions: [],
      emails: {
        processed: 0,
        tier1: 0,
        tier2: 0,
        tier3: 0,
        tier4: 0,
        agent: 0,
        failed: 0
      },
      performance: {
        avgProcessingTime: 0,
        maxProcessingTime: 0,
        minProcessingTime: Infinity,
        totalDuration: 0
      },
      errors: [],
      hourlyStats: {}
    };

    // Cost tracking
    this.costs = {
      total: 0,
      byService: {
        claude: 0,
        openrouter: 0,
        twilio: 0,
        aws: 0
      },
      byModel: {},
      byMode: {},
      daily: {},
      hourly: {}
    };

    // Alert system
    this.alerts = {
      active: [],
      history: [],
      thresholds: {
        errorRate: config.errorRateThreshold || 0.1,
        costPerHour: config.costThreshold || 5.0,
        processingTime: config.timeThreshold || 300000, // 5 minutes
        failureCount: config.failureThreshold || 3
      }
    };

    // Real-time metrics
    this.realtime = {
      currentHour: new Date().getHours(),
      emailsThisHour: 0,
      costsThisHour: 0,
      errorsThisHour: 0,
      startTime: Date.now()
    };

    this.initialized = false;
  }

  /**
   * Initialize monitoring system
   */
  async initialize() {
    if (this.initialized) return;

    try {
      await this.loadMetrics();
      await this.loadCosts();
      await this.loadAlerts();

      this.initialized = true;
      logger.info('Monitoring system initialized', {
        totalExecutions: this.metrics.executions.length,
        totalCost: this.costs.total.toFixed(4)
      });
    } catch (error) {
      logger.error('Failed to initialize monitoring', {
        error: error.message
      });
      this.initialized = true;
    }
  }

  /**
   * Track execution
   */
  async trackExecution(data) {
    const execution = {
      timestamp: Date.now(),
      mode: data.mode,
      duration: data.duration,
      emailsProcessed: data.emailsProcessed || 0,
      agentProcessed: data.agentProcessed || 0,
      escalations: data.escalations || 0,
      errors: data.errors || 0,
      costs: data.costs || {},
      metadata: data.metadata || {}
    };

    // Add to executions
    this.metrics.executions.push(execution);

    // Update email counts
    this.metrics.emails.processed += execution.emailsProcessed;
    this.metrics.emails.agent += execution.agentProcessed;

    // Update tier counts if provided
    if (data.tierCounts) {
      this.metrics.emails.tier1 += data.tierCounts.tier1 || 0;
      this.metrics.emails.tier2 += data.tierCounts.tier2 || 0;
      this.metrics.emails.tier3 += data.tierCounts.tier3 || 0;
      this.metrics.emails.tier4 += data.tierCounts.tier4 || 0;
    }

    // Update performance metrics
    this.updatePerformanceMetrics(execution.duration);

    // Track costs
    if (data.costs) {
      await this.trackCosts(data.costs, data.mode);
    }

    // Update hourly stats
    this.updateHourlyStats(execution);

    // Check for alerts
    await this.checkAlerts(execution);

    // Save metrics
    await this.saveMetrics();

    logger.info('Execution tracked', {
      mode: data.mode,
      duration: data.duration,
      emails: execution.emailsProcessed,
      cost: execution.costs
    });

    return execution;
  }

  /**
   * Track costs
   */
  async trackCosts(costs, mode = 'unknown') {
    const timestamp = Date.now();
    const date = new Date().toISOString().split('T')[0];
    const hour = new Date().getHours();

    // Calculate total cost for this execution
    let executionCost = 0;

    if (costs.claude) {
      const claudeCost = parseFloat(costs.claude.cost || 0);
      this.costs.byService.claude += claudeCost;
      executionCost += claudeCost;

      // Track by model
      const model = 'claude-sonnet';
      this.costs.byModel[model] = (this.costs.byModel[model] || 0) + claudeCost;
    }

    if (costs.agent) {
      const agentCost = parseFloat(costs.agent.cost || 0);
      this.costs.byService.openrouter += agentCost;
      executionCost += agentCost;

      // Track by model
      const model = costs.agent.model || 'deepseek-r1';
      this.costs.byModel[model] = (this.costs.byModel[model] || 0) + agentCost;
    }

    if (costs.twilio) {
      const twilioCost = parseFloat(costs.twilio || 0);
      this.costs.byService.twilio += twilioCost;
      executionCost += twilioCost;
    }

    // AWS Lambda costs (estimated)
    const awsCost = this.estimateAWSCost(costs.duration || 0);
    this.costs.byService.aws += awsCost;
    executionCost += awsCost;

    // Update totals
    this.costs.total += executionCost;

    // Track by mode
    this.costs.byMode[mode] = (this.costs.byMode[mode] || 0) + executionCost;

    // Track daily
    if (!this.costs.daily[date]) {
      this.costs.daily[date] = 0;
    }
    this.costs.daily[date] += executionCost;

    // Track hourly
    const hourKey = `${date}_${hour}`;
    if (!this.costs.hourly[hourKey]) {
      this.costs.hourly[hourKey] = 0;
    }
    this.costs.hourly[hourKey] += executionCost;

    // Update realtime
    this.realtime.costsThisHour += executionCost;

    // Check cost alerts
    if (this.realtime.costsThisHour > this.alerts.thresholds.costPerHour) {
      await this.createAlert('COST_THRESHOLD', {
        hourlyCosl: this.realtime.costsThisHour,
        threshold: this.alerts.thresholds.costPerHour
      });
    }

    await this.saveCosts();

    return {
      execution: executionCost,
      total: this.costs.total,
      hourly: this.realtime.costsThisHour
    };
  }

  /**
   * Estimate AWS Lambda cost
   */
  estimateAWSCost(durationMs) {
    // AWS Lambda pricing (approximate)
    const memoryGB = 0.5; // 512MB
    const gbSeconds = (memoryGB * durationMs) / 1000;
    const costPerGBSecond = 0.0000166667;
    const invocationCost = 0.0000002;

    return (gbSeconds * costPerGBSecond) + invocationCost;
  }

  /**
   * Update performance metrics
   */
  updatePerformanceMetrics(duration) {
    if (duration < this.metrics.performance.minProcessingTime) {
      this.metrics.performance.minProcessingTime = duration;
    }
    if (duration > this.metrics.performance.maxProcessingTime) {
      this.metrics.performance.maxProcessingTime = duration;
    }

    this.metrics.performance.totalDuration += duration;

    const execCount = this.metrics.executions.length;
    this.metrics.performance.avgProcessingTime =
      this.metrics.performance.totalDuration / execCount;
  }

  /**
   * Update hourly statistics
   */
  updateHourlyStats(execution) {
    const hour = new Date().getHours();
    const key = `hour_${hour}`;

    if (!this.metrics.hourlyStats[key]) {
      this.metrics.hourlyStats[key] = {
        executions: 0,
        emails: 0,
        errors: 0,
        avgDuration: 0,
        totalDuration: 0
      };
    }

    const stats = this.metrics.hourlyStats[key];
    stats.executions++;
    stats.emails += execution.emailsProcessed;
    stats.errors += execution.errors;
    stats.totalDuration += execution.duration;
    stats.avgDuration = stats.totalDuration / stats.executions;

    // Update realtime
    const currentHour = new Date().getHours();
    if (currentHour !== this.realtime.currentHour) {
      // Reset for new hour
      this.realtime.currentHour = currentHour;
      this.realtime.emailsThisHour = 0;
      this.realtime.costsThisHour = 0;
      this.realtime.errorsThisHour = 0;
    }

    this.realtime.emailsThisHour += execution.emailsProcessed;
    this.realtime.errorsThisHour += execution.errors;
  }

  /**
   * Track error
   */
  async trackError(error, context = {}) {
    const errorEntry = {
      timestamp: Date.now(),
      message: error.message,
      code: error.code,
      stack: error.stack,
      context,
      retryable: error.retryable || false
    };

    this.metrics.errors.push(errorEntry);
    this.metrics.emails.failed++;
    this.realtime.errorsThisHour++;

    // Check error rate
    const errorRate = this.calculateErrorRate();
    if (errorRate > this.alerts.thresholds.errorRate) {
      await this.createAlert('ERROR_RATE', {
        rate: errorRate,
        threshold: this.alerts.thresholds.errorRate,
        recentErrors: this.metrics.errors.slice(-5)
      });
    }

    logger.error('Error tracked in monitoring', {
      error: error.message,
      context
    });

    await this.saveMetrics();
  }

  /**
   * Calculate error rate
   */
  calculateErrorRate() {
    const recentExecs = this.metrics.executions.slice(-10);
    if (recentExecs.length === 0) return 0;

    const totalErrors = recentExecs.reduce((sum, exec) => sum + (exec.errors || 0), 0);
    const totalEmails = recentExecs.reduce((sum, exec) => sum + exec.emailsProcessed, 0);

    return totalEmails > 0 ? totalErrors / totalEmails : 0;
  }

  /**
   * Check for alerts
   */
  async checkAlerts(execution) {
    // Check processing time
    if (execution.duration > this.alerts.thresholds.processingTime) {
      await this.createAlert('SLOW_PROCESSING', {
        duration: execution.duration,
        threshold: this.alerts.thresholds.processingTime,
        mode: execution.mode
      });
    }

    // Check consecutive failures
    const recentFailures = this.metrics.executions
      .slice(-5)
      .filter(exec => exec.errors > 0).length;

    if (recentFailures >= this.alerts.thresholds.failureCount) {
      await this.createAlert('CONSECUTIVE_FAILURES', {
        failures: recentFailures,
        threshold: this.alerts.thresholds.failureCount
      });
    }
  }

  /**
   * Create alert
   */
  async createAlert(type, data) {
    const alert = {
      id: `alert_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      type,
      timestamp: Date.now(),
      data,
      resolved: false
    };

    this.alerts.active.push(alert);
    this.alerts.history.push(alert);

    logger.warn('Alert created', {
      type,
      data
    });

    // Send notification if configured
    await this.sendAlertNotification(alert);

    await this.saveAlerts();

    return alert;
  }

  /**
   * Send alert notification
   */
  async sendAlertNotification(alert) {
    // This would integrate with SNS, email, or other notification service
    // For now, just log it prominently
    logger.error('🚨 MONITORING ALERT', {
      type: alert.type,
      data: alert.data,
      timestamp: new Date(alert.timestamp).toISOString()
    });
  }

  /**
   * Resolve alert
   */
  async resolveAlert(alertId) {
    const alert = this.alerts.active.find(a => a.id === alertId);
    if (alert) {
      alert.resolved = true;
      alert.resolvedAt = Date.now();

      // Remove from active
      this.alerts.active = this.alerts.active.filter(a => a.id !== alertId);

      await this.saveAlerts();

      logger.info('Alert resolved', { alertId });
    }
  }

  /**
   * Get dashboard data
   */
  getDashboard() {
    const now = Date.now();
    const last24h = now - 86400000;
    const lastHour = now - 3600000;

    // Calculate metrics for different time periods
    const recent24h = this.metrics.executions.filter(e => e.timestamp > last24h);
    const recentHour = this.metrics.executions.filter(e => e.timestamp > lastHour);

    return {
      summary: {
        totalEmails: this.metrics.emails.processed,
        totalCost: this.costs.total.toFixed(4),
        totalExecutions: this.metrics.executions.length,
        avgProcessingTime: Math.round(this.metrics.performance.avgProcessingTime),
        uptime: now - this.realtime.startTime
      },
      current: {
        emailsThisHour: this.realtime.emailsThisHour,
        costsThisHour: this.realtime.costsThisHour.toFixed(4),
        errorsThisHour: this.realtime.errorsThisHour,
        activeAlerts: this.alerts.active.length
      },
      last24Hours: {
        executions: recent24h.length,
        emails: recent24h.reduce((sum, e) => sum + e.emailsProcessed, 0),
        errors: recent24h.reduce((sum, e) => sum + e.errors, 0)
      },
      lastHour: {
        executions: recentHour.length,
        emails: recentHour.reduce((sum, e) => sum + e.emailsProcessed, 0),
        errors: recentHour.reduce((sum, e) => sum + e.errors, 0)
      },
      tierDistribution: {
        tier1: this.metrics.emails.tier1,
        tier2: this.metrics.emails.tier2,
        tier3: this.metrics.emails.tier3,
        tier4: this.metrics.emails.tier4
      },
      costBreakdown: this.costs.byService,
      modelUsage: this.costs.byModel,
      alerts: this.alerts.active
    };
  }

  /**
   * Get insights
   */
  getInsights() {
    const insights = [];

    // Cost insights
    const avgCostPerEmail = this.metrics.emails.processed > 0
      ? this.costs.total / this.metrics.emails.processed
      : 0;

    if (avgCostPerEmail > 0.01) {
      insights.push({
        type: 'cost',
        severity: 'warning',
        message: `Average cost per email is $${avgCostPerEmail.toFixed(4)}, consider optimizing model usage`
      });
    }

    // Performance insights
    if (this.metrics.performance.avgProcessingTime > 60000) {
      insights.push({
        type: 'performance',
        severity: 'warning',
        message: `Average processing time is ${Math.round(this.metrics.performance.avgProcessingTime / 1000)}s, consider optimization`
      });
    }

    // Error insights
    const errorRate = this.calculateErrorRate();
    if (errorRate > 0.05) {
      insights.push({
        type: 'reliability',
        severity: 'error',
        message: `Error rate is ${(errorRate * 100).toFixed(1)}%, investigate recent failures`
      });
    }

    // Usage patterns
    const peakHour = this.findPeakHour();
    if (peakHour) {
      insights.push({
        type: 'usage',
        severity: 'info',
        message: `Peak email volume at ${peakHour.hour}:00 with ${peakHour.emails} emails`
      });
    }

    return insights;
  }

  /**
   * Find peak hour
   */
  findPeakHour() {
    let peakHour = null;
    let maxEmails = 0;

    for (const [key, stats] of Object.entries(this.metrics.hourlyStats)) {
      if (stats.emails > maxEmails) {
        maxEmails = stats.emails;
        peakHour = {
          hour: parseInt(key.replace('hour_', '')),
          emails: stats.emails,
          executions: stats.executions
        };
      }
    }

    return peakHour;
  }

  /**
   * Export metrics
   */
  async exportMetrics(exportPath) {
    const exportData = {
      exported: new Date().toISOString(),
      metrics: this.metrics,
      costs: this.costs,
      alerts: this.alerts,
      dashboard: this.getDashboard(),
      insights: this.getInsights()
    };

    await fs.writeFile(exportPath, JSON.stringify(exportData, null, 2));
    logger.info('Metrics exported', { path: exportPath });

    return exportPath;
  }

  /**
   * Save metrics
   */
  async saveMetrics() {
    try {
      await fs.mkdir(path.dirname(this.metricsPath), { recursive: true });
      await fs.writeFile(this.metricsPath, JSON.stringify(this.metrics, null, 2));
    } catch (error) {
      logger.error('Failed to save metrics', { error: error.message });
    }
  }

  /**
   * Load metrics
   */
  async loadMetrics() {
    try {
      const data = await fs.readFile(this.metricsPath, 'utf-8');
      this.metrics = { ...this.metrics, ...JSON.parse(data) };
    } catch (error) {
      if (error.code !== 'ENOENT') {
        logger.error('Failed to load metrics', { error: error.message });
      }
    }
  }

  /**
   * Save costs
   */
  async saveCosts() {
    try {
      await fs.mkdir(path.dirname(this.costPath), { recursive: true });
      await fs.writeFile(this.costPath, JSON.stringify(this.costs, null, 2));
    } catch (error) {
      logger.error('Failed to save costs', { error: error.message });
    }
  }

  /**
   * Load costs
   */
  async loadCosts() {
    try {
      const data = await fs.readFile(this.costPath, 'utf-8');
      this.costs = { ...this.costs, ...JSON.parse(data) };
    } catch (error) {
      if (error.code !== 'ENOENT') {
        logger.error('Failed to load costs', { error: error.message });
      }
    }
  }

  /**
   * Save alerts
   */
  async saveAlerts() {
    try {
      await fs.mkdir(path.dirname(this.alertsPath), { recursive: true });
      await fs.writeFile(this.alertsPath, JSON.stringify(this.alerts, null, 2));
    } catch (error) {
      logger.error('Failed to save alerts', { error: error.message });
    }
  }

  /**
   * Load alerts
   */
  async loadAlerts() {
    try {
      const data = await fs.readFile(this.alertsPath, 'utf-8');
      const loaded = JSON.parse(data);

      // Only load active alerts, not history
      this.alerts.active = loaded.active || [];
      this.alerts.history = loaded.history || [];
      this.alerts.thresholds = { ...this.alerts.thresholds, ...loaded.thresholds };
    } catch (error) {
      if (error.code !== 'ENOENT') {
        logger.error('Failed to load alerts', { error: error.message });
      }
    }
  }

  /**
   * Reset metrics
   */
  async reset() {
    this.metrics = {
      executions: [],
      emails: {
        processed: 0,
        tier1: 0,
        tier2: 0,
        tier3: 0,
        tier4: 0,
        agent: 0,
        failed: 0
      },
      performance: {
        avgProcessingTime: 0,
        maxProcessingTime: 0,
        minProcessingTime: Infinity,
        totalDuration: 0
      },
      errors: [],
      hourlyStats: {}
    };

    this.costs = {
      total: 0,
      byService: {
        claude: 0,
        openrouter: 0,
        twilio: 0,
        aws: 0
      },
      byModel: {},
      byMode: {},
      daily: {},
      hourly: {}
    };

    this.alerts.history = [];
    this.alerts.active = [];

    await this.saveMetrics();
    await this.saveCosts();
    await this.saveAlerts();

    logger.info('Monitoring system reset');
  }
}

module.exports = MonitoringSystem;