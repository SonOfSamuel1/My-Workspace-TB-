/**
 * Analytics Engine
 * Comprehensive email analytics and insights
 */

const logger = require('./logger');

class AnalyticsEngine {
  constructor() {
    this.emails = [];
    this.startDate = new Date();
  }

  /**
   * Track email processing
   */
  trackEmail(email, classification, action) {
    this.emails.push({
      id: email.id,
      from: email.from,
      subject: email.subject,
      date: new Date(email.date),
      tier: classification.tier,
      confidence: classification.confidence,
      action: action,
      responseTime: email.responseTime || 0,
      threadId: email.threadId,
      sentiment: email.sentiment,
      timestamp: new Date()
    });
  }

  /**
   * Get volume metrics
   */
  getVolumeMetrics() {
    const now = new Date();
    const today = this.emails.filter(e =>
      e.timestamp.toDateString() === now.toDateString()
    );

    const thisWeek = this.emails.filter(e => {
      const weekAgo = new Date(now - 7 * 24 * 60 * 60 * 1000);
      return e.timestamp >= weekAgo;
    });

    return {
      total: this.emails.length,
      today: today.length,
      thisWeek: thisWeek.length,
      avgPerDay: thisWeek.length / 7,
      peakHour: this.getPeakHour(),
      peakDay: this.getPeakDay()
    };
  }

  /**
   * Get tier distribution
   */
  getTierDistribution() {
    const tiers = { tier1: 0, tier2: 0, tier3: 0, tier4: 0 };

    for (const email of this.emails) {
      tiers[`tier${email.tier}`]++;
    }

    const total = this.emails.length;

    return {
      counts: tiers,
      percentages: {
        tier1: ((tiers.tier1 / total) * 100).toFixed(1),
        tier2: ((tiers.tier2 / total) * 100).toFixed(1),
        tier3: ((tiers.tier3 / total) * 100).toFixed(1),
        tier4: ((tiers.tier4 / total) * 100).toFixed(1)
      }
    };
  }

  /**
   * Get response time metrics
   */
  getResponseMetrics() {
    const withResponseTime = this.emails.filter(e => e.responseTime > 0);

    if (withResponseTime.length === 0) {
      return { avg: 0, median: 0, fastest: 0, slowest: 0 };
    }

    const times = withResponseTime.map(e => e.responseTime).sort((a, b) => a - b);

    return {
      avg: this.formatTime(times.reduce((a, b) => a + b, 0) / times.length),
      median: this.formatTime(times[Math.floor(times.length / 2)]),
      fastest: this.formatTime(times[0]),
      slowest: this.formatTime(times[times.length - 1])
    };
  }

  /**
   * Get top senders
   */
  getTopSenders(limit = 10) {
    const senderCounts = {};

    for (const email of this.emails) {
      senderCounts[email.from] = (senderCounts[email.from] || 0) + 1;
    }

    return Object.entries(senderCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, limit)
      .map(([sender, count]) => ({ sender, count }));
  }

  /**
   * Get productivity insights
   */
  getProductivityInsights() {
    const tier2 = this.emails.filter(e => e.tier === 2).length;
    const total = this.emails.length;
    const autonomousRate = ((tier2 / total) * 100).toFixed(1);

    // Estimate time saved
    const timeSaved = tier2 * 3 + this.emails.filter(e => e.tier === 3).length * 2;

    return {
      autonomousHandling: `${autonomousRate}%`,
      emailsHandled: tier2,
      timeSavedMinutes: timeSaved,
      timeSavedHours: (timeSaved / 60).toFixed(1),
      escalationRate: `${((this.emails.filter(e => e.tier === 1).length / total) * 100).toFixed(1)}%`
    };
  }

  /**
   * Get peak hour
   */
  getPeakHour() {
    const hourCounts = Array(24).fill(0);

    for (const email of this.emails) {
      hourCounts[email.date.getHours()]++;
    }

    const peakHour = hourCounts.indexOf(Math.max(...hourCounts));
    return `${peakHour}:00-${peakHour + 1}:00`;
  }

  /**
   * Get peak day
   */
  getPeakDay() {
    const dayCounts = Array(7).fill(0);
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

    for (const email of this.emails) {
      dayCounts[email.date.getDay()]++;
    }

    const peakDay = dayCounts.indexOf(Math.max(...dayCounts));
    return dayNames[peakDay];
  }

  /**
   * Generate comprehensive report
   */
  generateReport() {
    return {
      period: {
        start: this.startDate.toISOString(),
        end: new Date().toISOString(),
        days: Math.floor((new Date() - this.startDate) / (24 * 60 * 60 * 1000))
      },
      volume: this.getVolumeMetrics(),
      tierDistribution: this.getTierDistribution(),
      responseMetrics: this.getResponseMetrics(),
      topSenders: this.getTopSenders(5),
      productivity: this.getProductivityInsights(),
      trends: this.getTrends()
    };
  }

  /**
   * Get trends
   */
  getTrends() {
    const lastWeek = this.emails.filter(e => {
      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
      return e.timestamp >= weekAgo;
    });

    const previousWeek = this.emails.filter(e => {
      const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);
      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
      return e.timestamp >= twoWeeksAgo && e.timestamp < weekAgo;
    });

    const volumeChange = previousWeek.length > 0 ?
      (((lastWeek.length - previousWeek.length) / previousWeek.length) * 100).toFixed(1) : 0;

    return {
      volumeChange: `${volumeChange > 0 ? '+' : ''}${volumeChange}%`,
      trending: volumeChange > 10 ? 'up' : volumeChange < -10 ? 'down' : 'stable'
    };
  }

  /**
   * Format time in ms to readable format
   */
  formatTime(ms) {
    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }

  /**
   * Export analytics data
   */
  exportData() {
    return {
      emails: this.emails,
      report: this.generateReport()
    };
  }
}

module.exports = new AnalyticsEngine();
module.exports.AnalyticsEngine = AnalyticsEngine;
