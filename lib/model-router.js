/**
 * Smart Model Router
 *
 * Analyzes email complexity and routes to the most cost-effective AI model:
 * - Tier 1 (Simple): Gemini 2.0 Flash Thinking - $0.0005/call
 * - Tier 2 (Standard): DeepSeek V3.1 - $0.001/call
 * - Tier 3 (Complex): DeepSeek R1 - $0.002/call
 */

const logger = require('./logger');

// Model configuration with OpenRouter pricing
const MODELS = {
  SIMPLE: {
    name: 'google/gemini-2.0-flash-thinking-exp:free',
    displayName: 'Gemini 2.0 Flash Thinking',
    cost: 0.0005,
    tier: 'simple',
    maxTokens: 8192,
    description: 'Fast model for simple classification and straightforward responses'
  },
  STANDARD: {
    name: 'deepseek/deepseek-chat',
    displayName: 'DeepSeek V3.1',
    cost: 0.001,
    tier: 'standard',
    maxTokens: 64000,
    description: 'Balanced model for standard email processing'
  },
  COMPLEX: {
    name: 'deepseek/deepseek-r1',
    displayName: 'DeepSeek R1',
    cost: 0.002,
    tier: 'complex',
    maxTokens: 64000,
    description: 'Advanced reasoning model for complex decisions'
  }
};

// Complexity scoring weights
const WEIGHTS = {
  subjectLength: 0.15,
  bodyLength: 0.25,
  hasAttachments: 0.10,
  hasUrls: 0.05,
  sentimentComplexity: 0.15,
  requiresReasoning: 0.30
};

/**
 * Analyze email complexity and return a score (0-100)
 */
function analyzeEmailComplexity(email) {
  let score = 0;
  const factors = {};

  // Subject length analysis (0-20 points)
  const subjectLen = (email.subject || '').length;
  if (subjectLen > 100) {
    factors.subjectLength = 20;
  } else if (subjectLen > 50) {
    factors.subjectLength = 10;
  } else {
    factors.subjectLength = 5;
  }

  // Body length analysis (0-30 points)
  const bodyLen = (email.body || '').length;
  if (bodyLen > 2000) {
    factors.bodyLength = 30;
  } else if (bodyLen > 1000) {
    factors.bodyLength = 20;
  } else if (bodyLen > 500) {
    factors.bodyLength = 10;
  } else {
    factors.bodyLength = 5;
  }

  // Attachments (0-10 points)
  factors.hasAttachments = (email.attachments && email.attachments.length > 0) ? 10 : 0;

  // URLs in body (0-10 points)
  const urlCount = ((email.body || '').match(/https?:\/\//g) || []).length;
  factors.hasUrls = Math.min(urlCount * 3, 10);

  // Sentiment/complexity keywords (0-20 points)
  const complexityKeywords = [
    'analyze', 'compare', 'evaluate', 'recommend', 'assess',
    'strategy', 'proposal', 'decision', 'negotiate', 'contract',
    'legal', 'financial', 'technical', 'urgent', 'critical'
  ];

  const text = `${email.subject} ${email.body}`.toLowerCase();
  const keywordMatches = complexityKeywords.filter(kw => text.includes(kw)).length;
  factors.sentimentComplexity = Math.min(keywordMatches * 4, 20);

  // Reasoning indicators (0-30 points)
  const reasoningIndicators = [
    'why', 'how', 'should i', 'what if', 'pros and cons',
    'help me decide', 'which one', 'best option', 'recommend',
    'multiple', 'options', 'alternatives'
  ];

  const reasoningMatches = reasoningIndicators.filter(ind => text.includes(ind)).length;
  factors.requiresReasoning = Math.min(reasoningMatches * 5, 30);

  // Calculate weighted score
  score = Object.keys(factors).reduce((sum, key) => {
    return sum + (factors[key] * (WEIGHTS[key] || 0));
  }, 0);

  logger.debug('Email complexity analysis', {
    emailId: email.id,
    score: Math.round(score),
    factors
  });

  return {
    score: Math.round(score),
    factors
  };
}

/**
 * Select the appropriate model based on complexity score
 *
 * Scoring thresholds:
 * - 0-30: Simple (Gemini 2.0 Flash)
 * - 31-60: Standard (DeepSeek V3.1)
 * - 61-100: Complex (DeepSeek R1)
 */
function selectModel(email, options = {}) {
  const { forceModel, complexity } = options;

  // Allow manual override
  if (forceModel) {
    const model = Object.values(MODELS).find(m => m.name === forceModel || m.tier === forceModel);
    if (model) {
      logger.info('Using forced model', { model: model.displayName });
      return model;
    }
  }

  // Use provided complexity or analyze
  const { score, factors } = complexity || analyzeEmailComplexity(email);

  // Select model based on score
  let selectedModel;
  if (score <= 30) {
    selectedModel = MODELS.SIMPLE;
  } else if (score <= 60) {
    selectedModel = MODELS.STANDARD;
  } else {
    selectedModel = MODELS.COMPLEX;
  }

  logger.info('Model selected for email', {
    emailId: email.id,
    complexityScore: score,
    selectedModel: selectedModel.displayName,
    tier: selectedModel.tier,
    estimatedCost: `$${selectedModel.cost.toFixed(4)}`
  });

  return {
    ...selectedModel,
    complexityScore: score,
    complexityFactors: factors
  };
}

/**
 * Get model statistics from a batch of emails
 */
function getModelDistribution(emails) {
  const distribution = {
    simple: 0,
    standard: 0,
    complex: 0
  };

  const totalCost = emails.reduce((sum, email) => {
    const model = selectModel(email);
    distribution[model.tier]++;
    return sum + model.cost;
  }, 0);

  const avgCost = emails.length > 0 ? totalCost / emails.length : 0;

  return {
    distribution,
    totalCost,
    avgCost,
    emailCount: emails.length
  };
}

/**
 * Validate model selection for testing
 */
function validateModel(email, expectedTier) {
  const model = selectModel(email);
  const isCorrect = model.tier === expectedTier;

  if (!isCorrect) {
    logger.warn('Model selection mismatch', {
      emailId: email.id,
      expected: expectedTier,
      actual: model.tier,
      score: model.complexityScore
    });
  }

  return {
    isCorrect,
    selected: model,
    expected: expectedTier
  };
}

/**
 * Get model configuration for OpenRouter
 */
function getModelConfig(modelName) {
  const model = Object.values(MODELS).find(m => m.name === modelName);

  if (!model) {
    logger.warn('Unknown model requested, using default', { modelName });
    return MODELS.COMPLEX; // Fallback to most capable model
  }

  return model;
}

module.exports = {
  MODELS,
  selectModel,
  analyzeEmailComplexity,
  getModelDistribution,
  validateModel,
  getModelConfig
};
