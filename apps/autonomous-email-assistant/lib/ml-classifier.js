/**
 * ML-Based Email Classification System
 * Learns from feedback to improve tier classification over time
 */

const logger = require('./logger');
const fs = require('fs');
const path = require('path');

class MLClassifier {
  constructor(modelPath = null) {
    this.modelPath = modelPath || path.join(__dirname, '../data/classification-model.json');
    this.trainingData = [];
    this.model = this.loadModel();
    this.features = {};
  }

  /**
   * Extract features from email
   */
  extractFeatures(email) {
    const features = {
      // Sender features
      senderDomain: this.extractDomain(email.from),
      senderInVIP: this.isVIPSender(email.from),
      senderFrequency: this.getSenderFrequency(email.from),

      // Subject features
      subjectLength: (email.subject || '').length,
      hasUrgentKeywords: /urgent|asap|immediate/i.test(email.subject || ''),
      hasQuestionMark: /\?/.test(email.subject || ''),
      hasRe: /^re:/i.test(email.subject || ''),

      // Body features
      bodyLength: (email.body || '').length,
      hasAttachments: (email.attachments || []).length > 0,
      attachmentCount: (email.attachments || []).length,

      // Time features
      hourOfDay: new Date(email.date).getHours(),
      dayOfWeek: new Date(email.date).getDay(),
      isWeekend: [0, 6].includes(new Date(email.date).getDay()),

      // Content features
      hasNumbers: /\d+/.test(email.body || ''),
      hasLinks: /(http|www\.)/.test(email.body || ''),
      hasMoney: /\$|USD|price|cost|payment/i.test(email.body || ''),

      // Sentiment features
      hasPositive: /thanks|thank you|appreciate|great/i.test(email.body || ''),
      hasNegative: /problem|issue|concern|unfortunately/i.test(email.body || ''),

      // Thread features
      isReply: email.inReplyTo || /^re:/i.test(email.subject || ''),
      threadLength: email.threadLength || 1
    };

    return features;
  }

  /**
   * Classify email using ML model
   */
  classify(email) {
    const features = this.extractFeatures(email);

    // Calculate scores for each tier using weighted features
    const scores = {
      tier1: this.calculateTierScore(features, 1),
      tier2: this.calculateTierScore(features, 2),
      tier3: this.calculateTierScore(features, 3),
      tier4: this.calculateTierScore(features, 4)
    };

    // Find tier with highest score
    let predictedTier = 2; // Default
    let maxScore = scores.tier2;

    for (const [tier, score] of Object.entries(scores)) {
      if (score > maxScore) {
        maxScore = score;
        predictedTier = parseInt(tier.replace('tier', ''));
      }
    }

    const confidence = maxScore / Object.values(scores).reduce((a, b) => a + b, 0);

    logger.debug('ML classification', {
      emailId: email.id,
      predictedTier,
      confidence: confidence.toFixed(2),
      scores
    });

    return {
      tier: predictedTier,
      confidence,
      scores,
      features,
      reasoning: this.explainClassification(features, predictedTier)
    };
  }

  /**
   * Calculate score for specific tier
   */
  calculateTierScore(features, tier) {
    const weights = this.model.weights[`tier${tier}`] || {};
    let score = this.model.baselines[`tier${tier}`] || 0.25;

    // Apply feature weights
    for (const [feature, value] of Object.entries(features)) {
      const weight = weights[feature] || 0;

      if (typeof value === 'boolean') {
        score += value ? weight : 0;
      } else if (typeof value === 'number') {
        score += value * weight * 0.01; // Scale numeric features
      }
    }

    return Math.max(0, Math.min(1, score)); // Clamp to 0-1
  }

  /**
   * Explain classification
   */
  explainClassification(features, tier) {
    const reasons = [];

    if (tier === 1) {
      if (features.senderInVIP) reasons.push('From VIP sender');
      if (features.hasUrgentKeywords) reasons.push('Contains urgent keywords');
      if (features.hasMoney) reasons.push('Financial matter');
    } else if (tier === 2) {
      if (features.senderFrequency > 5) reasons.push('Regular correspondent');
      if (features.hasAttachments && features.bodyLength < 500) {
        reasons.push('Simple request with attachment');
      }
    } else if (tier === 3) {
      if (features.bodyLength > 1000) reasons.push('Complex communication');
      if (!features.isReply) reasons.push('New conversation');
    } else if (tier === 4) {
      if (features.hasNegative) reasons.push('Sensitive content');
      reasons.push('Requires personal attention');
    }

    return reasons;
  }

  /**
   * Record training example
   */
  recordFeedback(email, predictedTier, actualTier, userFeedback = null) {
    const features = this.extractFeatures(email);

    this.trainingData.push({
      emailId: email.id,
      features,
      predicted: predictedTier,
      actual: actualTier,
      timestamp: new Date().toISOString(),
      feedback: userFeedback
    });

    logger.info('Feedback recorded', {
      emailId: email.id,
      predicted: predictedTier,
      actual: actualTier,
      correct: predictedTier === actualTier
    });

    // Retrain if we have enough new examples
    if (this.trainingData.length >= 10) {
      this.retrain();
    }
  }

  /**
   * Retrain model with new data
   */
  retrain() {
    logger.info('Retraining ML model', {
      trainingExamples: this.trainingData.length
    });

    // Simple weight adjustment based on feedback
    // In production, would use proper ML library
    for (const example of this.trainingData) {
      const { features, predicted, actual } = example;

      if (predicted !== actual) {
        // Adjust weights for incorrect prediction
        this.adjustWeights(features, predicted, actual);
      }
    }

    // Save updated model
    this.saveModel();

    // Clear training data after retraining
    this.trainingData = [];
  }

  /**
   * Adjust weights based on error
   */
  adjustWeights(features, predicted, actual) {
    const learningRate = 0.01;

    // Decrease weights for predicted tier
    for (const [feature, value] of Object.entries(features)) {
      if (typeof value === 'boolean' && value) {
        this.model.weights[`tier${predicted}`][feature] =
          (this.model.weights[`tier${predicted}`][feature] || 0) - learningRate;
      }
    }

    // Increase weights for actual tier
    for (const [feature, value] of Object.entries(features)) {
      if (typeof value === 'boolean' && value) {
        this.model.weights[`tier${actual}`][feature] =
          (this.model.weights[`tier${actual}`][feature] || 0) + learningRate;
      }
    }
  }

  /**
   * Load model from disk
   */
  loadModel() {
    try {
      if (fs.existsSync(this.modelPath)) {
        const data = fs.readFileSync(this.modelPath, 'utf8');
        logger.info('ML model loaded', { path: this.modelPath });
        return JSON.parse(data);
      }
    } catch (error) {
      logger.warn('Could not load ML model, using default', { error: error.message });
    }

    // Return default model
    return this.createDefaultModel();
  }

  /**
   * Create default model
   */
  createDefaultModel() {
    return {
      version: '1.0',
      baselines: {
        tier1: 0.15,
        tier2: 0.40,
        tier3: 0.25,
        tier4: 0.10
      },
      weights: {
        tier1: {
          senderInVIP: 0.5,
          hasUrgentKeywords: 0.3,
          hasMoney: 0.2,
          hasNegative: 0.15
        },
        tier2: {
          senderFrequency: 0.1,
          hasAttachments: 0.1,
          isReply: 0.15
        },
        tier3: {
          bodyLength: 0.001,
          hasQuestionMark: 0.1
        },
        tier4: {
          hasNegative: 0.2,
          hasMoney: 0.15
        }
      },
      trainingCount: 0,
      accuracy: 0,
      lastTrained: null
    };
  }

  /**
   * Save model to disk
   */
  saveModel() {
    try {
      const dir = path.dirname(this.modelPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      this.model.lastTrained = new Date().toISOString();
      this.model.trainingCount++;

      fs.writeFileSync(this.modelPath, JSON.stringify(this.model, null, 2));
      logger.info('ML model saved', { path: this.modelPath });
    } catch (error) {
      logger.error('Failed to save ML model', { error: error.message });
    }
  }

  /**
   * Get model statistics
   */
  getStatistics() {
    return {
      version: this.model.version,
      trainingCount: this.model.trainingCount,
      lastTrained: this.model.lastTrained,
      accuracy: this.model.accuracy,
      pendingFeedback: this.trainingData.length
    };
  }

  /**
   * Helper: Extract domain from email
   */
  extractDomain(email) {
    const match = email.match(/@([^>]+)/);
    return match ? match[1].toLowerCase() : '';
  }

  /**
   * Helper: Check if VIP sender
   */
  isVIPSender(email) {
    // In production, check against VIP list
    return false;
  }

  /**
   * Helper: Get sender frequency
   */
  getSenderFrequency(email) {
    // In production, query database for sender history
    return 0;
  }
}

module.exports = new MLClassifier();
module.exports.MLClassifier = MLClassifier;
