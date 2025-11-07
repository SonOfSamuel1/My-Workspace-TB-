/**
 * Email Deduplication System
 * Detects and handles duplicate emails, forward chains, and CC'd messages
 */

const crypto = require('crypto');
const logger = require('./logger');

class EmailDeduplication {
  constructor() {
    this.seenEmails = new Map(); // emailHash -> email metadata
    this.forwardChains = new Map(); // original -> forwards
    this.ccGroups = new Map(); // groupHash -> emails
    this.duplicateActions = new Map(); // duplicateId -> action taken
  }

  /**
   * Check if email is duplicate and handle accordingly
   */
  async checkAndHandle(email) {
    const analysis = this.analyzeDuplication(email);

    if (analysis.isDuplicate) {
      logger.info('Duplicate email detected', {
        emailId: email.id,
        type: analysis.type,
        originalId: analysis.original?.id
      });

      const action = await this.handleDuplicate(email, analysis);
      this.duplicateActions.set(email.id, action);

      return {
        isDuplicate: true,
        analysis,
        action,
        shouldProcess: action.process
      };
    }

    // Not a duplicate, record it
    this.recordEmail(email);

    return {
      isDuplicate: false,
      analysis,
      shouldProcess: true
    };
  }

  /**
   * Analyze if email is a duplicate
   */
  analyzeDuplication(email) {
    const checks = {
      exactDuplicate: this.checkExactDuplicate(email),
      contentDuplicate: this.checkContentDuplicate(email),
      forwardDuplicate: this.checkForwardDuplicate(email),
      ccDuplicate: this.checkCCDuplicate(email),
      quotedReply: this.checkQuotedReply(email)
    };

    // Determine if duplicate and type
    let isDuplicate = false;
    let type = null;
    let original = null;
    let confidence = 0;

    if (checks.exactDuplicate.match) {
      isDuplicate = true;
      type = 'exact';
      original = checks.exactDuplicate.original;
      confidence = 100;
    } else if (checks.contentDuplicate.match && checks.contentDuplicate.similarity > 0.95) {
      isDuplicate = true;
      type = 'content';
      original = checks.contentDuplicate.original;
      confidence = checks.contentDuplicate.similarity * 100;
    } else if (checks.forwardDuplicate.match) {
      isDuplicate = true;
      type = 'forward';
      original = checks.forwardDuplicate.original;
      confidence = 90;
    } else if (checks.ccDuplicate.match && checks.ccDuplicate.similarity > 0.9) {
      isDuplicate = true;
      type = 'cc_group';
      original = checks.ccDuplicate.original;
      confidence = 85;
    }

    return {
      isDuplicate,
      type,
      original,
      confidence,
      checks,
      reasoning: this.generateReasoning(checks, type)
    };
  }

  /**
   * Check for exact duplicate (same Message-ID)
   */
  checkExactDuplicate(email) {
    if (!email.messageId) {
      return { match: false };
    }

    const hash = this.hashMessageId(email.messageId);
    const existing = this.seenEmails.get(hash);

    if (existing) {
      return {
        match: true,
        original: existing,
        reason: 'Same Message-ID'
      };
    }

    return { match: false };
  }

  /**
   * Check for content duplicate (similar body)
   */
  checkContentDuplicate(email) {
    const contentHash = this.hashContent(email);

    // Check for exact content match
    const existing = this.seenEmails.get(contentHash);
    if (existing) {
      return {
        match: true,
        original: existing,
        similarity: 1.0,
        reason: 'Identical content'
      };
    }

    // Check for similar content
    const similarEmail = this.findSimilarContent(email);
    if (similarEmail) {
      return {
        match: true,
        original: similarEmail.email,
        similarity: similarEmail.similarity,
        reason: 'Similar content detected'
      };
    }

    return { match: false };
  }

  /**
   * Check if email is a forward of existing email
   */
  checkForwardDuplicate(email) {
    const subject = email.subject || '';

    // Check if subject indicates forwarding
    const isFwd = /^(fwd?:|fw:|forwarded:)/i.test(subject.trim());
    if (!isFwd) {
      return { match: false };
    }

    // Extract original subject
    const originalSubject = subject.replace(/^(fwd?:|fw:|forwarded:)\s*/i, '').trim();

    // Look for original email with this subject
    for (const [hash, seenEmail] of this.seenEmails.entries()) {
      if (seenEmail.cleanSubject === this.cleanSubject(originalSubject)) {
        // Check if body contains quoted original
        if (this.containsQuotedContent(email.body, seenEmail.body)) {
          return {
            match: true,
            original: seenEmail,
            reason: 'Forward of existing email'
          };
        }
      }
    }

    return { match: false };
  }

  /**
   * Check if email is part of CC'd group
   */
  checkCCDuplicate(email) {
    const ccGroupHash = this.hashCCGroup(email);

    // Check if we've seen this CC group before
    const existingGroup = this.ccGroups.get(ccGroupHash);
    if (existingGroup) {
      // Check if content is very similar
      const similarity = this.calculateSimilarity(
        email.body || '',
        existingGroup[0].body || ''
      );

      if (similarity > 0.9) {
        return {
          match: true,
          original: existingGroup[0],
          similarity,
          reason: 'CC\'d email group'
        };
      }
    }

    return { match: false };
  }

  /**
   * Check if email is a quoted reply with minimal new content
   */
  checkQuotedReply(email) {
    const body = email.body || '';

    // Look for quote markers
    const quoteMarkers = ['>', '|', '-----Original Message-----', 'On .* wrote:'];
    const hasQuotes = quoteMarkers.some(marker =>
      new RegExp(marker).test(body)
    );

    if (!hasQuotes) {
      return { match: false };
    }

    // Extract new content (not quoted)
    const newContent = this.extractNewContent(body);
    const quotedContent = body.length - newContent.length;

    // If email is mostly quoted content (>80%)
    if (quotedContent / body.length > 0.8) {
      return {
        match: true,
        reason: 'Mostly quoted content',
        newContentRatio: newContent.length / body.length
      };
    }

    return { match: false };
  }

  /**
   * Handle duplicate email
   */
  async handleDuplicate(email, analysis) {
    const action = {
      type: null,
      process: false,
      label: null,
      notification: false,
      reason: ''
    };

    switch (analysis.type) {
      case 'exact':
        // Exact duplicate - mark as duplicate, don't process
        action.type = 'mark_duplicate';
        action.process = false;
        action.label = 'Duplicate';
        action.reason = 'Exact duplicate detected';
        break;

      case 'content':
        // Content duplicate - archive, don't process
        action.type = 'archive';
        action.process = false;
        action.label = 'Duplicate';
        action.reason = `Content ${Math.round(analysis.confidence)}% similar`;
        break;

      case 'forward':
        // Forward - might have new recipients, process if new context
        if (this.hasNewRecipients(email, analysis.original)) {
          action.type = 'process_as_forward';
          action.process = true;
          action.label = 'Forward';
          action.reason = 'Forward with new recipients';
        } else {
          action.type = 'archive';
          action.process = false;
          action.label = 'Duplicate-Forward';
          action.reason = 'Forward to same recipients';
        }
        break;

      case 'cc_group':
        // CC'd email - process only first one
        action.type = 'mark_cc_duplicate';
        action.process = false;
        action.label = 'CC-Duplicate';
        action.reason = 'Already received in CC group';
        break;

      default:
        action.type = 'process';
        action.process = true;
    }

    logger.debug('Duplicate action determined', {
      emailId: email.id,
      action: action.type,
      willProcess: action.process
    });

    return action;
  }

  /**
   * Record email to detect future duplicates
   */
  recordEmail(email) {
    const messageIdHash = this.hashMessageId(email.messageId);
    const contentHash = this.hashContent(email);
    const ccGroupHash = this.hashCCGroup(email);

    const record = {
      id: email.id,
      messageId: email.messageId,
      from: email.from,
      to: email.to,
      subject: email.subject,
      cleanSubject: this.cleanSubject(email.subject),
      body: email.body,
      date: email.date,
      recordedAt: new Date()
    };

    // Store by different hashes
    if (email.messageId) {
      this.seenEmails.set(messageIdHash, record);
    }

    this.seenEmails.set(contentHash, record);

    // Track CC groups
    if (!this.ccGroups.has(ccGroupHash)) {
      this.ccGroups.set(ccGroupHash, []);
    }
    this.ccGroups.get(ccGroupHash).push(record);

    // Track forward chains
    if (this.isForward(email)) {
      const originalSubject = this.extractOriginalSubject(email.subject);
      if (!this.forwardChains.has(originalSubject)) {
        this.forwardChains.set(originalSubject, []);
      }
      this.forwardChains.get(originalSubject).push(record);
    }

    // Clean up old records (older than 30 days)
    this.cleanupOldRecords();
  }

  /**
   * Find similar content
   */
  findSimilarContent(email) {
    const emailBody = (email.body || '').toLowerCase();
    let bestMatch = null;
    let bestSimilarity = 0;

    for (const [hash, seenEmail] of this.seenEmails.entries()) {
      // Skip if different sender (less likely to be duplicate)
      if (seenEmail.from !== email.from) continue;

      const similarity = this.calculateSimilarity(
        emailBody,
        (seenEmail.body || '').toLowerCase()
      );

      if (similarity > bestSimilarity && similarity > 0.8) {
        bestSimilarity = similarity;
        bestMatch = seenEmail;
      }
    }

    if (bestMatch) {
      return { email: bestMatch, similarity: bestSimilarity };
    }

    return null;
  }

  /**
   * Calculate text similarity (Jaccard similarity)
   */
  calculateSimilarity(text1, text2) {
    const words1 = new Set(text1.split(/\s+/).filter(w => w.length > 3));
    const words2 = new Set(text2.split(/\s+/).filter(w => w.length > 3));

    const intersection = new Set([...words1].filter(w => words2.has(w)));
    const union = new Set([...words1, ...words2]);

    if (union.size === 0) return 0;

    return intersection.size / union.size;
  }

  /**
   * Check if email contains quoted content from original
   */
  containsQuotedContent(body1, body2) {
    if (!body1 || !body2) return false;

    const normalized1 = body1.toLowerCase().replace(/\s+/g, ' ');
    const normalized2 = body2.toLowerCase().replace(/\s+/g, ' ');

    // Check if body1 contains significant portion of body2
    const words2 = normalized2.split(' ').filter(w => w.length > 3);
    const matchCount = words2.filter(w => normalized1.includes(w)).length;

    return matchCount / words2.length > 0.7;
  }

  /**
   * Extract new content (not quoted)
   */
  extractNewContent(body) {
    if (!body) return '';

    const lines = body.split('\n');
    const newLines = lines.filter(line => {
      const trimmed = line.trim();
      // Skip quoted lines
      if (trimmed.startsWith('>')) return false;
      if (trimmed.startsWith('|')) return false;
      if (/^On .* wrote:/.test(trimmed)) return false;
      if (trimmed.includes('-----Original Message-----')) return false;
      return true;
    });

    return newLines.join('\n');
  }

  /**
   * Check if email has new recipients compared to original
   */
  hasNewRecipients(email, original) {
    const emailRecipients = new Set([
      email.to,
      ...(email.cc || [])
    ].filter(Boolean));

    const originalRecipients = new Set([
      original.to,
      ...(original.cc || [])
    ].filter(Boolean));

    // Check if there are any recipients not in original
    for (const recipient of emailRecipients) {
      if (!originalRecipients.has(recipient)) {
        return true;
      }
    }

    return false;
  }

  /**
   * Generate reasoning for duplication
   */
  generateReasoning(checks, type) {
    const reasons = [];

    if (checks.exactDuplicate.match) {
      reasons.push('Exact Message-ID match');
    }

    if (checks.contentDuplicate.match) {
      reasons.push(`Content ${Math.round(checks.contentDuplicate.similarity * 100)}% similar`);
    }

    if (checks.forwardDuplicate.match) {
      reasons.push('Detected as forward of existing email');
    }

    if (checks.ccDuplicate.match) {
      reasons.push('Part of CC\'d email group');
    }

    if (checks.quotedReply.match) {
      reasons.push(`${Math.round((1 - checks.quotedReply.newContentRatio) * 100)}% quoted content`);
    }

    return reasons;
  }

  /**
   * Clean subject line
   */
  cleanSubject(subject) {
    if (!subject) return '';

    return subject
      .replace(/^(re:|fwd?:|fw:)\s*/gi, '')
      .trim()
      .toLowerCase();
  }

  /**
   * Check if email is a forward
   */
  isForward(email) {
    const subject = email.subject || '';
    return /^(fwd?:|fw:|forwarded:)/i.test(subject.trim());
  }

  /**
   * Extract original subject from forward
   */
  extractOriginalSubject(subject) {
    return subject.replace(/^(fwd?:|fw:|forwarded:)\s*/i, '').trim();
  }

  /**
   * Hash Message-ID
   */
  hashMessageId(messageId) {
    if (!messageId) return null;
    return crypto.createHash('md5').update(messageId).digest('hex');
  }

  /**
   * Hash content
   */
  hashContent(email) {
    const content = [
      email.from || '',
      this.cleanSubject(email.subject || ''),
      (email.body || '').substring(0, 500) // First 500 chars
    ].join('|');

    return crypto.createHash('md5').update(content).digest('hex');
  }

  /**
   * Hash CC group
   */
  hashCCGroup(email) {
    const recipients = [
      email.to,
      ...(email.cc || [])
    ].filter(Boolean).sort().join(',');

    const content = [
      recipients,
      this.cleanSubject(email.subject || '')
    ].join('|');

    return crypto.createHash('md5').update(content).digest('hex');
  }

  /**
   * Clean up old records
   */
  cleanupOldRecords() {
    const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
    let removed = 0;

    for (const [hash, email] of this.seenEmails.entries()) {
      if (new Date(email.recordedAt) < thirtyDaysAgo) {
        this.seenEmails.delete(hash);
        removed++;
      }
    }

    if (removed > 0) {
      logger.debug('Cleaned up old deduplication records', { removed });
    }
  }

  /**
   * Get statistics
   */
  getStatistics() {
    return {
      trackedEmails: this.seenEmails.size,
      forwardChains: this.forwardChains.size,
      ccGroups: this.ccGroups.size,
      duplicatesDetected: this.duplicateActions.size,
      duplicateTypes: this.getDuplicateTypeBreakdown()
    };
  }

  /**
   * Get duplicate type breakdown
   */
  getDuplicateTypeBreakdown() {
    const breakdown = {
      exact: 0,
      content: 0,
      forward: 0,
      cc_group: 0
    };

    for (const action of this.duplicateActions.values()) {
      if (action.type && breakdown.hasOwnProperty(action.type)) {
        breakdown[action.type]++;
      }
    }

    return breakdown;
  }

  /**
   * Export data for backup
   */
  exportData() {
    return {
      seenEmails: Array.from(this.seenEmails.entries()),
      forwardChains: Array.from(this.forwardChains.entries()),
      ccGroups: Array.from(this.ccGroups.entries()),
      exportedAt: new Date().toISOString()
    };
  }

  /**
   * Import data from backup
   */
  importData(data) {
    this.seenEmails = new Map(data.seenEmails);
    this.forwardChains = new Map(data.forwardChains);
    this.ccGroups = new Map(data.ccGroups);

    logger.info('Deduplication data imported', {
      seenEmails: this.seenEmails.size,
      forwardChains: this.forwardChains.size,
      ccGroups: this.ccGroups.size
    });
  }
}

module.exports = new EmailDeduplication();
module.exports.EmailDeduplication = EmailDeduplication;
