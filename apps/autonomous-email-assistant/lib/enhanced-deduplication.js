/**
 * Enhanced Email Deduplication with Persistence
 * Provides persistent storage, time-based expiry, and statistics
 */

const crypto = require('crypto');
const fs = require('fs').promises;
const path = require('path');
const logger = require('./logger');

class EnhancedEmailDeduplication {
  constructor(config = {}) {
    this.storePath = config.storePath || '/tmp/email-deduplication.json';
    this.maxAge = config.maxAge || 86400000; // 24 hours default
    this.maxEntries = config.maxEntries || 10000;

    // In-memory stores
    this.seenEmails = new Map();
    this.messageIdMap = new Map();
    this.threadMap = new Map();
    this.hashIndex = new Map();

    // Statistics
    this.stats = {
      totalChecked: 0,
      duplicatesFound: 0,
      uniqueEmails: 0,
      lastCleanup: Date.now(),
      savedBytes: 0
    };

    this.initialized = false;
  }

  /**
   * Initialize deduplication system
   */
  async initialize() {
    if (this.initialized) return;

    try {
      await this.load();
      this.initialized = true;
      logger.info('Email deduplication initialized', {
        entries: this.seenEmails.size,
        storePath: this.storePath
      });
    } catch (error) {
      logger.error('Failed to initialize deduplication', {
        error: error.message
      });
      this.initialized = true; // Continue with empty state
    }
  }

  /**
   * Check if email is duplicate
   */
  async isDuplicate(emailId, emailContent = null) {
    this.stats.totalChecked++;

    // Check by message ID
    if (this.messageIdMap.has(emailId)) {
      this.stats.duplicatesFound++;
      logger.debug('Duplicate found by message ID', { emailId });
      return true;
    }

    // Check by content hash if provided
    if (emailContent) {
      const contentHash = this.generateContentHash(emailContent);
      if (this.hashIndex.has(contentHash)) {
        this.stats.duplicatesFound++;
        logger.debug('Duplicate found by content hash', { emailId, hash: contentHash });
        return true;
      }
    }

    // Check if seen before (backwards compatibility)
    if (this.seenEmails.has(emailId)) {
      const entry = this.seenEmails.get(emailId);

      // Check if expired
      if (Date.now() - entry.timestamp > this.maxAge) {
        this.seenEmails.delete(emailId);
        return false;
      }

      this.stats.duplicatesFound++;
      logger.debug('Duplicate found in seen emails', { emailId });
      return true;
    }

    return false;
  }

  /**
   * Mark email as processed
   */
  async markProcessed(emailId, metadata = {}) {
    const timestamp = Date.now();

    // Create entry
    const entry = {
      id: emailId,
      timestamp,
      ...metadata
    };

    // Store in multiple indexes
    this.seenEmails.set(emailId, entry);
    this.messageIdMap.set(emailId, timestamp);

    // Add to thread map if thread ID provided
    if (metadata.threadId) {
      if (!this.threadMap.has(metadata.threadId)) {
        this.threadMap.set(metadata.threadId, new Set());
      }
      this.threadMap.get(metadata.threadId).add(emailId);
    }

    // Add content hash if provided
    if (metadata.contentHash) {
      this.hashIndex.set(metadata.contentHash, emailId);
    }

    this.stats.uniqueEmails++;

    // Cleanup if needed
    if (this.seenEmails.size > this.maxEntries) {
      await this.cleanup();
    }

    logger.debug('Email marked as processed', {
      emailId,
      threadId: metadata.threadId
    });
  }

  /**
   * Check if emails are in same thread
   */
  isInSameThread(emailId1, emailId2) {
    for (const [threadId, emails] of this.threadMap.entries()) {
      if (emails.has(emailId1) && emails.has(emailId2)) {
        return true;
      }
    }
    return false;
  }

  /**
   * Get thread emails
   */
  getThreadEmails(threadId) {
    const emails = this.threadMap.get(threadId);
    if (!emails) return [];

    return Array.from(emails).map(id => ({
      id,
      ...this.seenEmails.get(id)
    }));
  }

  /**
   * Generate content hash
   */
  generateContentHash(content) {
    if (typeof content === 'object') {
      // Extract key fields for hashing
      const normalized = {
        subject: content.subject?.toLowerCase().trim(),
        from: content.from?.toLowerCase().trim(),
        body: content.body?.substring(0, 1000).toLowerCase().trim()
      };
      content = JSON.stringify(normalized);
    }

    return crypto
      .createHash('sha256')
      .update(content)
      .digest('hex')
      .substring(0, 16);
  }

  /**
   * Check for near duplicates
   */
  findNearDuplicates(email, threshold = 0.85) {
    const candidates = [];
    const emailHash = this.generateContentHash(email);

    for (const [id, entry] of this.seenEmails.entries()) {
      if (entry.contentHash) {
        const similarity = this.calculateSimilarity(emailHash, entry.contentHash);
        if (similarity > threshold) {
          candidates.push({
            id,
            similarity,
            entry
          });
        }
      }
    }

    return candidates.sort((a, b) => b.similarity - a.similarity);
  }

  /**
   * Calculate hash similarity (simple approach)
   */
  calculateSimilarity(hash1, hash2) {
    if (hash1 === hash2) return 1;

    let matches = 0;
    const len = Math.min(hash1.length, hash2.length);

    for (let i = 0; i < len; i++) {
      if (hash1[i] === hash2[i]) matches++;
    }

    return matches / len;
  }

  /**
   * Cleanup expired entries
   */
  async cleanup() {
    const startSize = this.seenEmails.size;
    const cutoff = Date.now() - this.maxAge;
    const toDelete = [];

    // Find expired entries
    for (const [id, entry] of this.seenEmails.entries()) {
      if (entry.timestamp < cutoff) {
        toDelete.push(id);
      }
    }

    // Delete expired entries
    for (const id of toDelete) {
      const entry = this.seenEmails.get(id);

      // Remove from all indexes
      this.seenEmails.delete(id);
      this.messageIdMap.delete(id);

      if (entry.contentHash) {
        this.hashIndex.delete(entry.contentHash);
      }

      if (entry.threadId) {
        const threadEmails = this.threadMap.get(entry.threadId);
        if (threadEmails) {
          threadEmails.delete(id);
          if (threadEmails.size === 0) {
            this.threadMap.delete(entry.threadId);
          }
        }
      }
    }

    this.stats.lastCleanup = Date.now();

    logger.info('Deduplication cleanup completed', {
      removed: toDelete.length,
      remaining: this.seenEmails.size,
      previousSize: startSize
    });

    // Save after cleanup
    await this.save();
  }

  /**
   * Save state to disk
   */
  async save() {
    try {
      const data = {
        version: '1.0',
        timestamp: Date.now(),
        stats: this.stats,
        entries: Array.from(this.seenEmails.entries()).map(([id, entry]) => ({
          id,
          ...entry
        })),
        threads: Array.from(this.threadMap.entries()).map(([threadId, emails]) => ({
          threadId,
          emails: Array.from(emails)
        }))
      };

      // Ensure directory exists
      await fs.mkdir(path.dirname(this.storePath), { recursive: true });

      // Write atomically
      const tempPath = `${this.storePath}.tmp`;
      await fs.writeFile(tempPath, JSON.stringify(data, null, 2));
      await fs.rename(tempPath, this.storePath);

      this.stats.savedBytes = JSON.stringify(data).length;

      logger.debug('Deduplication state saved', {
        entries: this.seenEmails.size,
        size: this.stats.savedBytes
      });
    } catch (error) {
      logger.error('Failed to save deduplication state', {
        error: error.message
      });
    }
  }

  /**
   * Load state from disk
   */
  async load() {
    try {
      const data = await fs.readFile(this.storePath, 'utf-8');
      const parsed = JSON.parse(data);

      // Restore stats
      if (parsed.stats) {
        this.stats = { ...this.stats, ...parsed.stats };
      }

      // Restore entries
      if (parsed.entries) {
        for (const entry of parsed.entries) {
          // Skip expired entries
          if (Date.now() - entry.timestamp > this.maxAge) continue;

          this.seenEmails.set(entry.id, entry);
          this.messageIdMap.set(entry.id, entry.timestamp);

          if (entry.contentHash) {
            this.hashIndex.set(entry.contentHash, entry.id);
          }
        }
      }

      // Restore threads
      if (parsed.threads) {
        for (const thread of parsed.threads) {
          this.threadMap.set(thread.threadId, new Set(thread.emails));
        }
      }

      logger.info('Deduplication state loaded', {
        entries: this.seenEmails.size,
        threads: this.threadMap.size
      });
    } catch (error) {
      if (error.code !== 'ENOENT') {
        logger.error('Failed to load deduplication state', {
          error: error.message
        });
      }
      // Start with empty state
    }
  }

  /**
   * Get statistics
   */
  getStats() {
    return {
      ...this.stats,
      currentEntries: this.seenEmails.size,
      threads: this.threadMap.size,
      duplicateRate: this.stats.totalChecked > 0
        ? (this.stats.duplicatesFound / this.stats.totalChecked * 100).toFixed(2) + '%'
        : '0%',
      memoryUsage: process.memoryUsage().heapUsed
    };
  }

  /**
   * Reset deduplication state
   */
  async reset() {
    this.seenEmails.clear();
    this.messageIdMap.clear();
    this.threadMap.clear();
    this.hashIndex.clear();

    this.stats = {
      totalChecked: 0,
      duplicatesFound: 0,
      uniqueEmails: 0,
      lastCleanup: Date.now(),
      savedBytes: 0
    };

    try {
      await fs.unlink(this.storePath);
      logger.info('Deduplication state reset');
    } catch (error) {
      // Ignore if file doesn't exist
    }
  }

  /**
   * Export data for analysis
   */
  async exportData(exportPath) {
    const data = {
      exported: new Date().toISOString(),
      stats: this.getStats(),
      emails: Array.from(this.seenEmails.values()),
      threads: Array.from(this.threadMap.entries()).map(([id, emails]) => ({
        threadId: id,
        emailCount: emails.size,
        emails: Array.from(emails)
      })),
      duplicatePatterns: this.analyzeDuplicatePatterns()
    };

    await fs.writeFile(exportPath, JSON.stringify(data, null, 2));
    logger.info('Deduplication data exported', { path: exportPath });
  }

  /**
   * Analyze duplicate patterns
   */
  analyzeDuplicatePatterns() {
    const patterns = {
      byHour: {},
      bySender: {},
      bySubject: {},
      byThread: {}
    };

    for (const [id, entry] of this.seenEmails.entries()) {
      // By hour
      const hour = new Date(entry.timestamp).getHours();
      patterns.byHour[hour] = (patterns.byHour[hour] || 0) + 1;

      // By sender
      if (entry.from) {
        patterns.bySender[entry.from] = (patterns.bySender[entry.from] || 0) + 1;
      }

      // By subject pattern
      if (entry.subject) {
        const subjectPattern = entry.subject.replace(/\d+/g, 'N').substring(0, 20);
        patterns.bySubject[subjectPattern] = (patterns.bySubject[subjectPattern] || 0) + 1;
      }
    }

    // Thread sizes
    for (const [threadId, emails] of this.threadMap.entries()) {
      const size = emails.size;
      patterns.byThread[size] = (patterns.byThread[size] || 0) + 1;
    }

    return patterns;
  }
}

module.exports = EnhancedEmailDeduplication;