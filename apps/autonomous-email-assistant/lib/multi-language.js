/**
 * Multi-Language Support System
 * Automatic language detection, translation, and response generation
 */

const logger = require('./logger');

class MultiLanguageSupport {
  constructor() {
    this.supportedLanguages = [
      'en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi'
    ];

    this.languageNames = {
      'en': 'English',
      'es': 'Spanish',
      'fr': 'French',
      'de': 'German',
      'it': 'Italian',
      'pt': 'Portuguese',
      'ru': 'Russian',
      'zh': 'Chinese',
      'ja': 'Japanese',
      'ko': 'Korean',
      'ar': 'Arabic',
      'hi': 'Hindi'
    };

    // Common words for language detection
    this.languagePatterns = {
      'es': ['el', 'la', 'de', 'que', 'y', 'a', 'en', 'un', 'ser', 'se', 'no', 'haber', 'por', 'con', 'su', 'para', 'como', 'estar', 'tener', 'le', 'lo', 'todo'],
      'fr': ['le', 'de', 'un', 'être', 'et', 'à', 'il', 'avoir', 'ne', 'je', 'son', 'que', 'se', 'qui', 'ce', 'dans', 'en', 'du', 'elle', 'au', 'pour'],
      'de': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich', 'des', 'auf', 'für', 'ist', 'im', 'dem', 'nicht', 'ein', 'eine', 'als'],
      'it': ['il', 'di', 'e', 'la', 'a', 'in', 'un', 'che', 'è', 'per', 'da', 'non', 'con', 'una', 'sono', 'si', 'le', 'dei', 'come', 'delle'],
      'pt': ['o', 'a', 'de', 'e', 'que', 'do', 'da', 'em', 'um', 'para', 'é', 'com', 'não', 'uma', 'os', 'no', 'se', 'na', 'por', 'mais'],
      'ru': ['и', 'в', 'не', 'на', 'я', 'что', 'с', 'он', 'а', 'это', 'как', 'по', 'но', 'они', 'мы', 'вы', 'так', 'же', 'к', 'у'],
      'zh': ['的', '一', '是', '不', '了', '在', '人', '有', '我', '他', '这', '个', '们', '中', '来', '上', '大', '为', '和', '国'],
      'ja': ['の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ', 'ある', 'いる', 'も', 'する', 'から', 'な', 'こと', 'として'],
      'ko': ['의', '가', '이', '은', '들', '는', '좀', '잘', '걍', '과', '도', '를', '으로', '자', '에', '와', '한', '하다', '있다', '되다'],
      'ar': ['في', 'من', 'على', 'إلى', 'هذا', 'أن', 'كان', 'قد', 'ما', 'لم', 'إذا', 'كل', 'عن', 'أو', 'هو', 'بعد', 'عند', 'ذلك', 'هي', 'كما'],
      'hi': ['के', 'में', 'की', 'और', 'को', 'है', 'से', 'इस', 'ने', 'का', 'पर', 'हैं', 'यह', 'था', 'लिए', 'एक', 'कि', 'तो', 'हो', 'साथ']
    };

    this.translationCache = new Map();
    this.detectionHistory = [];
  }

  /**
   * Detect language of email
   */
  detectLanguage(email) {
    const text = `${email.subject || ''} ${email.body || ''}`;
    const cleaned = this.cleanText(text);

    // Try multiple detection methods
    const methods = {
      patternBased: this.detectByPatterns(cleaned),
      characterSet: this.detectByCharacterSet(cleaned),
      commonWords: this.detectByCommonWords(cleaned)
    };

    // Combine results with confidence weighting
    const scores = {};

    // Weight pattern-based detection highest
    if (methods.patternBased.language) {
      scores[methods.patternBased.language] =
        (scores[methods.patternBased.language] || 0) + methods.patternBased.confidence * 0.5;
    }

    // Weight character set detection
    if (methods.characterSet.language) {
      scores[methods.characterSet.language] =
        (scores[methods.characterSet.language] || 0) + methods.characterSet.confidence * 0.3;
    }

    // Weight common words detection
    if (methods.commonWords.language) {
      scores[methods.commonWords.language] =
        (scores[methods.commonWords.language] || 0) + methods.commonWords.confidence * 0.2;
    }

    // Find highest scoring language
    let detectedLanguage = 'en'; // Default to English
    let highestScore = 0;

    for (const [lang, score] of Object.entries(scores)) {
      if (score > highestScore) {
        highestScore = score;
        detectedLanguage = lang;
      }
    }

    const result = {
      language: detectedLanguage,
      languageName: this.languageNames[detectedLanguage],
      confidence: Math.round(Math.min(highestScore, 1) * 100),
      methods,
      isSupported: this.supportedLanguages.includes(detectedLanguage)
    };

    // Record detection
    this.detectionHistory.push({
      emailId: email.id,
      result,
      timestamp: new Date()
    });

    logger.debug('Language detected', {
      emailId: email.id,
      language: detectedLanguage,
      confidence: result.confidence
    });

    return result;
  }

  /**
   * Detect language by pattern matching
   */
  detectByPatterns(text) {
    const words = text.toLowerCase().split(/\s+/);
    const scores = {};

    for (const [lang, patterns] of Object.entries(this.languagePatterns)) {
      let matchCount = 0;
      for (const word of words) {
        if (patterns.includes(word)) {
          matchCount++;
        }
      }

      if (words.length > 0) {
        scores[lang] = matchCount / Math.min(words.length, 100);
      }
    }

    const sorted = Object.entries(scores).sort((a, b) => b[1] - a[1]);

    if (sorted.length > 0 && sorted[0][1] > 0.05) {
      return {
        language: sorted[0][0],
        confidence: Math.min(sorted[0][1] * 2, 1),
        method: 'pattern'
      };
    }

    return { language: null, confidence: 0, method: 'pattern' };
  }

  /**
   * Detect language by character set
   */
  detectByCharacterSet(text) {
    // Check for specific character ranges
    const checks = {
      'zh': /[\u4e00-\u9fa5]/, // Chinese
      'ja': /[\u3040-\u309f\u30a0-\u30ff]/, // Japanese (Hiragana/Katakana)
      'ko': /[\uac00-\ud7af]/, // Korean
      'ar': /[\u0600-\u06ff]/, // Arabic
      'ru': /[\u0400-\u04ff]/, // Cyrillic
      'hi': /[\u0900-\u097f]/ // Devanagari (Hindi)
    };

    for (const [lang, pattern] of Object.entries(checks)) {
      const matches = text.match(pattern);
      if (matches && matches.length > 5) {
        return {
          language: lang,
          confidence: 0.9,
          method: 'charset'
        };
      }
    }

    return { language: null, confidence: 0, method: 'charset' };
  }

  /**
   * Detect by common word frequency
   */
  detectByCommonWords(text) {
    // Similar to pattern-based but with different weighting
    return this.detectByPatterns(text);
  }

  /**
   * Translate email to target language
   */
  async translateEmail(email, targetLanguage) {
    const sourceLanguage = this.detectLanguage(email).language;

    if (sourceLanguage === targetLanguage) {
      return {
        translated: false,
        reason: 'Same source and target language',
        original: email
      };
    }

    // Check cache
    const cacheKey = this.getCacheKey(email.id, targetLanguage);
    const cached = this.translationCache.get(cacheKey);
    if (cached) {
      logger.debug('Translation cache hit', { emailId: email.id, targetLanguage });
      return cached;
    }

    // In production, use actual translation API (Google Translate, DeepL, etc.)
    const translation = await this.performTranslation(email, sourceLanguage, targetLanguage);

    // Cache result
    this.translationCache.set(cacheKey, translation);

    return translation;
  }

  /**
   * Perform actual translation (placeholder for API integration)
   */
  async performTranslation(email, sourceLanguage, targetLanguage) {
    logger.info('Translating email', {
      emailId: email.id,
      from: sourceLanguage,
      to: targetLanguage
    });

    // In production, integrate with:
    // - Google Cloud Translation API
    // - DeepL API
    // - AWS Translate
    // - Azure Translator

    // For now, return structure with placeholder
    const translation = {
      translated: true,
      sourceLanguage,
      targetLanguage,
      original: {
        subject: email.subject,
        body: email.body
      },
      translated: {
        subject: `[Translated to ${this.languageNames[targetLanguage]}] ${email.subject}`,
        body: `[Translation not available in demo mode]\n\nOriginal:\n${email.body}`
      },
      confidence: 85,
      translationService: 'placeholder'
    };

    return translation;
  }

  /**
   * Generate response in detected language
   */
  async generateResponse(email, responseContent, matchLanguage = true) {
    if (!matchLanguage) {
      return responseContent;
    }

    const emailLanguage = this.detectLanguage(email).language;

    if (emailLanguage === 'en') {
      // Already in English
      return responseContent;
    }

    // Translate response to email's language
    logger.info('Generating response in detected language', {
      emailId: email.id,
      language: emailLanguage
    });

    // In production, translate responseContent to emailLanguage
    const translatedResponse = await this.translateText(
      responseContent,
      'en',
      emailLanguage
    );

    return {
      original: responseContent,
      translated: translatedResponse,
      language: emailLanguage,
      note: `Response automatically generated in ${this.languageNames[emailLanguage]}`
    };
  }

  /**
   * Translate text
   */
  async translateText(text, sourceLanguage, targetLanguage) {
    // Check cache
    const cacheKey = this.hashText(text) + `_${targetLanguage}`;
    const cached = this.translationCache.get(cacheKey);
    if (cached) {
      return cached.translated.body || cached;
    }

    // In production, call translation API
    // For now, return placeholder
    const translated = `[Translated to ${this.languageNames[targetLanguage]}]\n${text}`;

    this.translationCache.set(cacheKey, translated);

    return translated;
  }

  /**
   * Get language statistics
   */
  getLanguageStatistics() {
    const stats = {
      totalDetections: this.detectionHistory.length,
      languages: {},
      recentDetections: this.detectionHistory.slice(-10)
    };

    // Count language occurrences
    for (const detection of this.detectionHistory) {
      const lang = detection.result.language;
      if (!stats.languages[lang]) {
        stats.languages[lang] = {
          code: lang,
          name: this.languageNames[lang],
          count: 0,
          avgConfidence: 0
        };
      }

      stats.languages[lang].count++;
      stats.languages[lang].avgConfidence += detection.result.confidence;
    }

    // Calculate averages
    for (const lang of Object.keys(stats.languages)) {
      stats.languages[lang].avgConfidence =
        Math.round(stats.languages[lang].avgConfidence / stats.languages[lang].count);
    }

    return stats;
  }

  /**
   * Get multilingual insights
   */
  getMultilingualInsights() {
    const stats = this.getLanguageStatistics();
    const insights = [];

    // Most common non-English language
    const nonEnglish = Object.values(stats.languages)
      .filter(l => l.code !== 'en')
      .sort((a, b) => b.count - a.count);

    if (nonEnglish.length > 0 && nonEnglish[0].count > 5) {
      insights.push({
        type: 'frequent_language',
        message: `You frequently receive emails in ${nonEnglish[0].name}`,
        suggestion: 'Consider adding automated translation for this language',
        language: nonEnglish[0].code,
        count: nonEnglish[0].count
      });
    }

    // Low confidence detections
    const lowConfidence = this.detectionHistory.filter(d =>
      d.result.confidence < 50
    ).length;

    if (lowConfidence > 0) {
      insights.push({
        type: 'low_confidence',
        message: `${lowConfidence} emails had uncertain language detection`,
        suggestion: 'Review these emails manually or improve detection'
      });
    }

    // Multilingual senders
    const senderLanguages = new Map();
    for (const detection of this.detectionHistory) {
      // Would need email.from here in actual implementation
      const sender = 'unknown';
      if (!senderLanguages.has(sender)) {
        senderLanguages.set(sender, new Set());
      }
      senderLanguages.get(sender).add(detection.result.language);
    }

    return {
      insights,
      statistics: stats,
      recommendations: this.generateRecommendations(stats)
    };
  }

  /**
   * Generate recommendations
   */
  generateRecommendations(stats) {
    const recommendations = [];

    const totalEmails = stats.totalDetections;
    const nonEnglishCount = Object.values(stats.languages)
      .filter(l => l.code !== 'en')
      .reduce((sum, l) => sum + l.count, 0);

    const nonEnglishPercentage = (nonEnglishCount / totalEmails) * 100;

    if (nonEnglishPercentage > 20) {
      recommendations.push({
        priority: 'high',
        message: `${Math.round(nonEnglishPercentage)}% of emails are non-English`,
        action: 'Enable automatic translation for all incoming emails'
      });
    }

    if (nonEnglishPercentage > 10 && nonEnglishPercentage <= 20) {
      recommendations.push({
        priority: 'medium',
        message: `${Math.round(nonEnglishPercentage)}% of emails are non-English`,
        action: 'Consider selective translation for important senders'
      });
    }

    // Check if many languages
    const uniqueLanguages = Object.keys(stats.languages).length;
    if (uniqueLanguages > 5) {
      recommendations.push({
        priority: 'medium',
        message: `You communicate in ${uniqueLanguages} different languages`,
        action: 'Consider multilingual template responses'
      });
    }

    return recommendations;
  }

  /**
   * Clean text for processing
   */
  cleanText(text) {
    if (!text) return '';

    return text
      .replace(/[^\w\s\u0080-\uFFFF]/g, ' ') // Keep unicode characters
      .replace(/\s+/g, ' ')
      .trim();
  }

  /**
   * Get cache key
   */
  getCacheKey(emailId, language) {
    return `${emailId}_${language}`;
  }

  /**
   * Hash text for caching
   */
  hashText(text) {
    const crypto = require('crypto');
    return crypto.createHash('md5').update(text).digest('hex');
  }

  /**
   * Clear old cache entries
   */
  clearOldCache() {
    // In production, implement TTL-based cache clearing
    if (this.translationCache.size > 1000) {
      // Keep most recent 500
      const entries = Array.from(this.translationCache.entries());
      this.translationCache = new Map(entries.slice(-500));
    }
  }

  /**
   * Export language data
   */
  exportData() {
    return {
      detectionHistory: this.detectionHistory,
      statistics: this.getLanguageStatistics(),
      exportedAt: new Date().toISOString()
    };
  }

  /**
   * Import language data
   */
  importData(data) {
    this.detectionHistory = data.detectionHistory || [];
    logger.info('Language data imported', {
      detections: this.detectionHistory.length
    });
  }
}

module.exports = new MultiLanguageSupport();
module.exports.MultiLanguageSupport = MultiLanguageSupport;
