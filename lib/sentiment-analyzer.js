/**
 * Sentiment Analysis System
 * Detects emotion, urgency, and tone in emails
 */

const logger = require('./logger');

class SentimentAnalyzer {
  constructor() {
    // Keyword patterns for sentiment detection
    this.patterns = {
      urgent: /\b(urgent|asap|immediately|emergency|critical|time[- ]sensitive|deadline|now|today)\b/i,
      angry: /\b(angry|frustrated|disappointed|unacceptable|terrible|horrible|worst|furious|upset)\b/i,
      positive: /\b(thanks|thank you|appreciate|grateful|excellent|great|perfect|wonderful|amazing|love)\b/i,
      negative: /\b(unfortunately|problem|issue|concern|worry|trouble|difficult|failed|error|wrong)\b/i,
      polite: /\b(please|kindly|would appreciate|if possible|at your convenience)\b/i,
      demanding: /\b(need|must|require|expect|should|have to|necessary)\b/i
    };
  }

  /**
   * Analyze email sentiment
   */
  analyze(email) {
    const text = `${email.subject || ''} ${email.body || ''}`.toLowerCase();

    const sentiment = {
      urgency: this.detectUrgency(text),
      emotion: this.detectEmotion(text),
      tone: this.detectTone(text),
      overallScore: 0,
      recommendations: []
    };

    // Calculate overall sentiment score
    sentiment.overallScore = this.calculateScore(sentiment);

    // Generate recommendations
    sentiment.recommendations = this.generateRecommendations(sentiment);

    logger.debug('Sentiment analyzed', {
      emailId: email.id,
      urgency: sentiment.urgency.level,
      emotion: sentiment.emotion.primary
    });

    return sentiment;
  }

  /**
   * Detect urgency level
   */
  detectUrgency(text) {
    const matches = text.match(this.patterns.urgent) || [];
    const score = Math.min(matches.length * 0.3, 1.0);

    // Check for deadline mentions
    const hasDeadline = /\b(deadline|due|by|before|until)\b/i.test(text);
    const hasTodayTomorrow = /\b(today|tomorrow|asap)\b/i.test(text);

    let level = 'low';
    if (score > 0.6 || hasTodayTomorrow) level = 'high';
    else if (score > 0.3 || hasDeadline) level = 'medium';

    return {
      level,
      score,
      indicators: matches,
      hasDeadline,
      hasTodayTomorrow
    };
  }

  /**
   * Detect emotion
   */
  detectEmotion(text) {
    const scores = {
      angry: (text.match(this.patterns.angry) || []).length * 0.3,
      positive: (text.match(this.patterns.positive) || []).length * 0.2,
      negative: (text.match(this.patterns.negative) || []).length * 0.25
    };

    // Determine primary emotion
    let primary = 'neutral';
    let maxScore = 0;

    for (const [emotion, score] of Object.entries(scores)) {
      if (score > maxScore) {
        maxScore = score;
        primary = emotion;
      }
    }

    if (maxScore < 0.3) primary = 'neutral';

    return {
      primary,
      scores,
      confidence: Math.min(maxScore, 1.0)
    };
  }

  /**
   * Detect tone
   */
  detectTone(text) {
    const politeScore = (text.match(this.patterns.polite) || []).length * 0.3;
    const demandingScore = (text.match(this.patterns.demanding) || []).length * 0.3;

    let tone = 'neutral';
    if (politeScore > demandingScore && politeScore > 0.3) {
      tone = 'polite';
    } else if (demandingScore > politeScore && demandingScore > 0.3) {
      tone = 'demanding';
    }

    return {
      type: tone,
      politeScore,
      demandingScore
    };
  }

  /**
   * Calculate overall sentiment score
   */
  calculateScore(sentiment) {
    let score = 0.5; // Neutral baseline

    // Urgency impact
    if (sentiment.urgency.level === 'high') score += 0.3;
    else if (sentiment.urgency.level === 'medium') score += 0.15;

    // Emotion impact
    if (sentiment.emotion.primary === 'angry') score += 0.4;
    else if (sentiment.emotion.primary === 'negative') score += 0.2;
    else if (sentiment.emotion.primary === 'positive') score -= 0.1;

    // Tone impact
    if (sentiment.tone.type === 'demanding') score += 0.1;
    else if (sentiment.tone.type === 'polite') score -= 0.05;

    return Math.min(Math.max(score, 0), 1); // Clamp to 0-1
  }

  /**
   * Generate recommendations
   */
  generateRecommendations(sentiment) {
    const recommendations = [];

    // Urgency recommendations
    if (sentiment.urgency.level === 'high') {
      recommendations.push({
        type: 'priority',
        message: 'High urgency detected - escalate or respond quickly',
        action: 'escalate'
      });
    }

    // Emotion recommendations
    if (sentiment.emotion.primary === 'angry') {
      recommendations.push({
        type: 'tone',
        message: 'Sender appears frustrated - use empathetic response',
        action: 'empathetic_response'
      });
      recommendations.push({
        type: 'escalation',
        message: 'Consider personal response from executive',
        action: 'suggest_personal_response'
      });
    }

    // Tone recommendations
    if (sentiment.tone.type === 'demanding') {
      recommendations.push({
        type: 'response_style',
        message: 'Demanding tone detected - be firm but professional',
        action: 'professional_boundary'
      });
    }

    // Combined high-risk
    if (sentiment.overallScore > 0.7) {
      recommendations.push({
        type: 'risk',
        message: 'High-risk email - review before taking action',
        action: 'manual_review'
      });
    }

    return recommendations;
  }

  /**
   * Suggest response tone based on sentiment
   */
  suggestResponseTone(sentiment) {
    if (sentiment.emotion.primary === 'angry') {
      return {
        tone: 'empathetic',
        guidelines: [
          'Acknowledge their frustration',
          'Apologize if appropriate',
          'Provide clear action steps',
          'Set expectations for resolution'
        ]
      };
    }

    if (sentiment.urgency.level === 'high') {
      return {
        tone: 'responsive',
        guidelines: [
          'Acknowledge urgency immediately',
          'Provide timeline for resolution',
          'Be direct and actionable',
          'Skip pleasantries, get to the point'
        ]
      };
    }

    if (sentiment.emotion.primary === 'positive') {
      return {
        tone: 'warm',
        guidelines: [
          'Match their positive energy',
          'Express appreciation',
          'Be friendly and personal',
          'Build on the positive relationship'
        ]
      };
    }

    return {
      tone: 'professional',
      guidelines: [
        'Be clear and concise',
        'Maintain professional courtesy',
        'Provide complete information',
        'End with clear next steps'
      ]
    };
  }
}

module.exports = new SentimentAnalyzer();
module.exports.SentimentAnalyzer = SentimentAnalyzer;
