/**
 * Cost Tracking System
 * Tracks API usage and costs across Claude, AWS, and other services
 */

const logger = require('./logger');

class CostTracker {
  constructor() {
    this.costs = {
      claude: { input: 0, output: 0, total: 0 },
      lambda: { invocations: 0, duration: 0, total: 0 },
      other: { total: 0 }
    };

    this.metrics = {
      emailsProcessed: 0,
      responsesGenerated: 0,
      classificationsPerformed: 0
    };

    // Pricing (per million tokens/units)
    this.pricing = {
      claude: {
        haiku: { input: 0.25, output: 1.25 },
        sonnet: { input: 3.00, output: 15.00 },
        opus: { input: 15.00, output: 75.00 }
      },
      lambda: {
        perRequest: 0.20 / 1000000, // $0.20 per 1M requests
        perGbSecond: 0.0000166667 // $0.0000166667 per GB-second
      }
    };
  }

  /**
   * Track Claude API usage
   */
  trackClaudeUsage(model, inputTokens, outputTokens) {
    const modelPricing = this.pricing.claude[model] || this.pricing.claude.sonnet;

    const inputCost = (inputTokens / 1000000) * modelPricing.input;
    const outputCost = (outputTokens / 1000000) * modelPricing.output;
    const total = inputCost + outputCost;

    this.costs.claude.input += inputCost;
    this.costs.claude.output += outputCost;
    this.costs.claude.total += total;

    logger.debug('Claude API usage tracked', {
      model,
      inputTokens,
      outputTokens,
      cost: total.toFixed(4)
    });

    return total;
  }

  /**
   * Track Lambda invocation
   */
  trackLambdaInvocation(durationMs, memoryMb = 512) {
    this.costs.lambda.invocations++;
    this.costs.lambda.duration += durationMs;

    const requestCost = this.pricing.lambda.perRequest;
    const computeCost = ((durationMs / 1000) * (memoryMb / 1024)) * this.pricing.lambda.perGbSecond;
    const total = requestCost + computeCost;

    this.costs.lambda.total += total;

    return total;
  }

  /**
   * Track email processed
   */
  trackEmailProcessed() {
    this.metrics.emailsProcessed++;
  }

  /**
   * Track response generated
   */
  trackResponseGenerated() {
    this.metrics.responsesGenerated++;
  }

  /**
   * Track classification
   */
  trackClassification() {
    this.metrics.classificationsPerformed++;
  }

  /**
   * Get current costs
   */
  getCosts() {
    return {
      breakdown: {
        claude: this.costs.claude.total,
        lambda: this.costs.lambda.total,
        other: this.costs.other.total
      },
      total: this.costs.claude.total + this.costs.lambda.total + this.costs.other.total,
      metrics: this.metrics,
      efficiency: {
        costPerEmail: this.metrics.emailsProcessed > 0 ?
          (this.costs.claude.total + this.costs.lambda.total) / this.metrics.emailsProcessed : 0,
        costPerResponse: this.metrics.responsesGenerated > 0 ?
          this.costs.claude.total / this.metrics.responsesGenerated : 0
      }
    };
  }

  /**
   * Get cost report
   */
  generateReport() {
    const costs = this.getCosts();

    return {
      period: 'current_session',
      costs: {
        claude: `$${costs.breakdown.claude.toFixed(2)}`,
        lambda: `$${costs.breakdown.lambda.toFixed(2)}`,
        total: `$${costs.total.toFixed(2)}`
      },
      metrics: costs.metrics,
      efficiency: {
        costPerEmail: `$${costs.efficiency.costPerEmail.toFixed(4)}`,
        costPerResponse: `$${costs.efficiency.costPerResponse.toFixed(4)}`
      },
      projections: this.projectMonthlyCosts(costs)
    };
  }

  /**
   * Project monthly costs
   */
  projectMonthlyCosts(currentCosts) {
    // Assume current metrics are for 1 day
    const dailyCost = currentCosts.total;
    const monthlyCost = dailyCost * 30;

    return {
      daily: `$${dailyCost.toFixed(2)}`,
      monthly: `$${monthlyCost.toFixed(2)}`,
      yearly: `$${(monthlyCost * 12).toFixed(2)}`
    };
  }

  /**
   * Reset costs
   */
  reset() {
    this.costs = {
      claude: { input: 0, output: 0, total: 0 },
      lambda: { invocations: 0, duration: 0, total: 0 },
      other: { total: 0 }
    };
    this.metrics = {
      emailsProcessed: 0,
      responsesGenerated: 0,
      classificationsPerformed: 0
    };
  }
}

module.exports = new CostTracker();
