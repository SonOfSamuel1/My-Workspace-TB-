/**
 * Tests for Sentiment Analyzer
 */

const { SentimentAnalyzer } = require('../lib/sentiment-analyzer');

describe('SentimentAnalyzer', () => {
  let analyzer;

  beforeEach(() => {
    analyzer = new SentimentAnalyzer();
  });

  describe('detectUrgency', () => {
    test('detects high urgency keywords', () => {
      const urgentTexts = [
        'URGENT: Please respond immediately',
        'This is an ASAP request',
        'CRITICAL issue with the system',
        'EMERGENCY meeting needed now'
      ];

      urgentTexts.forEach(text => {
        const urgency = analyzer.detectUrgency(text);
        expect(urgency).toBe('high');
      });
    });

    test('detects medium urgency', () => {
      const mediumTexts = [
        'Please respond when you get a chance',
        'Would appreciate a quick response',
        'Important: Please review this'
      ];

      mediumTexts.forEach(text => {
        const urgency = analyzer.detectUrgency(text);
        expect(urgency).toBe('medium');
      });
    });

    test('detects low urgency', () => {
      const lowTexts = [
        'Just wanted to share this with you',
        'FYI - no action needed',
        'When you have time, take a look'
      ];

      lowTexts.forEach(text => {
        const urgency = analyzer.detectUrgency(text);
        expect(urgency).toBe('low');
      });
    });
  });

  describe('detectEmotion', () => {
    test('detects angry emotion', () => {
      const angryTexts = [
        'I am very frustrated with this service',
        'This is completely unacceptable',
        'I demand a refund immediately'
      ];

      angryTexts.forEach(text => {
        const emotion = analyzer.detectEmotion(text);
        expect(emotion).toBe('angry');
      });
    });

    test('detects positive emotion', () => {
      const positiveTexts = [
        'Thank you so much for your help!',
        'Excellent work on the project',
        'I really appreciate your assistance'
      ];

      positiveTexts.forEach(text => {
        const emotion = analyzer.detectEmotion(text);
        expect(emotion).toBe('positive');
      });
    });

    test('detects negative emotion', () => {
      const negativeTexts = [
        'Unfortunately we cannot proceed',
        'I\'m disappointed with the results',
        'This is not what we expected'
      ];

      negativeTexts.forEach(text => {
        const emotion = analyzer.detectEmotion(text);
        expect(emotion).toBe('negative');
      });
    });

    test('defaults to neutral for unclear emotions', () => {
      const neutralText = 'The meeting is scheduled for Tuesday at 2 PM.';
      const emotion = analyzer.detectEmotion(neutralText);
      expect(emotion).toBe('neutral');
    });
  });

  describe('detectTone', () => {
    test('detects polite tone', () => {
      const politeTexts = [
        'Would you mind helping me with this?',
        'If it\'s not too much trouble, could you...',
        'I would greatly appreciate your assistance'
      ];

      politeTexts.forEach(text => {
        const tone = analyzer.detectTone(text);
        expect(tone).toBe('polite');
      });
    });

    test('detects demanding tone', () => {
      const demandingTexts = [
        'I need this done immediately',
        'You must complete this by EOD',
        'I expect a response within the hour'
      ];

      demandingTexts.forEach(text => {
        const tone = analyzer.detectTone(text);
        expect(tone).toBe('demanding');
      });
    });
  });

  describe('analyze', () => {
    test('provides comprehensive sentiment analysis', () => {
      const email = {
        subject: 'URGENT: System Down',
        body: 'This is unacceptable. The system has been down for hours and we need this fixed immediately!'
      };

      const analysis = analyzer.analyze(email);

      expect(analysis).toHaveProperty('urgency');
      expect(analysis).toHaveProperty('emotion');
      expect(analysis).toHaveProperty('tone');
      expect(analysis).toHaveProperty('score');
      expect(analysis).toHaveProperty('recommendations');

      expect(analysis.urgency).toBe('high');
      expect(analysis.emotion).toBe('angry');
      expect(analysis.recommendations).toBeInstanceOf(Array);
      expect(analysis.recommendations.length).toBeGreaterThan(0);
    });

    test('handles emails with only subject', () => {
      const email = {
        subject: 'Quick question'
      };

      const analysis = analyzer.analyze(email);

      expect(analysis).toBeDefined();
      expect(analysis.urgency).toBeDefined();
      expect(analysis.emotion).toBeDefined();
    });

    test('handles empty emails gracefully', () => {
      const email = {};

      const analysis = analyzer.analyze(email);

      expect(analysis).toBeDefined();
      expect(analysis.urgency).toBe('low');
      expect(analysis.emotion).toBe('neutral');
    });
  });

  describe('generateRecommendations', () => {
    test('recommends immediate response for high urgency + angry', () => {
      const sentiment = {
        urgency: 'high',
        emotion: 'angry',
        tone: 'demanding'
      };

      const recommendations = analyzer.generateRecommendations(sentiment);

      expect(recommendations).toContain(expect.stringContaining('Respond immediately'));
      expect(recommendations).toContain(expect.stringContaining('apologetic'));
    });

    test('recommends prompt response for high urgency', () => {
      const sentiment = {
        urgency: 'high',
        emotion: 'neutral',
        tone: 'neutral'
      };

      const recommendations = analyzer.generateRecommendations(sentiment);

      expect(recommendations).toContain(expect.stringContaining('within 1 hour'));
    });

    test('allows delayed response for low urgency', () => {
      const sentiment = {
        urgency: 'low',
        emotion: 'positive',
        tone: 'polite'
      };

      const recommendations = analyzer.generateRecommendations(sentiment);

      expect(recommendations).toContain(expect.stringContaining('within 24 hours'));
    });
  });

  describe('calculateSentimentScore', () => {
    test('calculates high score for positive emotions', () => {
      const sentiment = {
        urgency: 'low',
        emotion: 'positive',
        tone: 'polite'
      };

      const score = analyzer.calculateSentimentScore(sentiment);

      expect(score).toBeGreaterThan(50);
    });

    test('calculates low score for negative emotions', () => {
      const sentiment = {
        urgency: 'high',
        emotion: 'angry',
        tone: 'demanding'
      };

      const score = analyzer.calculateSentimentScore(sentiment);

      expect(score).toBeLessThan(50);
    });

    test('returns neutral score for neutral sentiment', () => {
      const sentiment = {
        urgency: 'medium',
        emotion: 'neutral',
        tone: 'neutral'
      };

      const score = analyzer.calculateSentimentScore(sentiment);

      expect(score).toBeGreaterThanOrEqual(40);
      expect(score).toBeLessThanOrEqual(60);
    });
  });
});
