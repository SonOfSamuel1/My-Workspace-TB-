/**
 * Thread Detection System
 *
 * Detects email threads, maintains conversation context,
 * and provides intelligent thread analysis.
 */

const crypto = require('crypto');
const logger = require('./logger');

class ThreadDetector {
  constructor() {
    this.threads = new Map(); // threadId -> thread data
    this.emailToThread = new Map(); // emailId -> threadId
  }

  /**
   * Clean subject line for thread matching
   */
  cleanSubject(subject) {
    if (!subject) return '';

    return subject
      .replace(/^(Re|Fwd|Fw):\s*/gi, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  /**
   * Generate thread ID from subject and participants
   */
  generateThreadId(subject, participants) {
    const cleanedSubject = this.cleanSubject(subject);
    const sortedParticipants = [...participants].sort().join(',');
    const combined = `${cleanedSubject}:${sortedParticipants}`;

    return crypto.createHash('md5').update(combined).digest('hex');
  }

  /**
   * Extract participants from email
   */
  extractParticipants(email) {
    const participants = new Set();

    if (email.from) participants.add(this.normalizeEmail(email.from));
    if (email.to) {
      email.to.split(',').forEach(addr =>
        participants.add(this.normalizeEmail(addr))
      );
    }
    if (email.cc) {
      email.cc.split(',').forEach(addr =>
        participants.add(this.normalizeEmail(addr))
      );
    }

    return Array.from(participants);
  }

  /**
   * Normalize email address
   */
  normalizeEmail(email) {
    if (!email) return '';

    // Extract email from "Name <email@domain.com>" format
    const match = email.match(/<(.+?)>/);
    const addr = match ? match[1] : email;

    return addr.trim().toLowerCase();
  }

  /**
   * Detect if email is part of existing thread
   */
  detectThread(email) {
    // Method 1: Check Message-ID headers
    if (email.inReplyTo && this.emailToThread.has(email.inReplyTo)) {
      return this.emailToThread.get(email.inReplyTo);
    }

    if (email.references) {
      const refs = email.references.split(/\s+/);
      for (const ref of refs) {
        if (this.emailToThread.has(ref)) {
          return this.emailToThread.get(ref);
        }
      }
    }

    // Method 2: Subject + participants matching
    const participants = this.extractParticipants(email);
    const threadId = this.generateThreadId(email.subject, participants);

    if (this.threads.has(threadId)) {
      return threadId;
    }

    // Method 3: Fuzzy subject matching with same participants
    const cleanedSubject = this.cleanSubject(email.subject);
    for (const [existingThreadId, thread] of this.threads.entries()) {
      if (this.isSimilarSubject(cleanedSubject, thread.subject)) {
        const overlap = this.participantOverlap(participants, thread.participants);
        if (overlap > 0.7) { // 70% participant overlap
          return existingThreadId;
        }
      }
    }

    return null;
  }

  /**
   * Check if subjects are similar
   */
  isSimilarSubject(subject1, subject2) {
    const s1 = this.cleanSubject(subject1);
    const s2 = this.cleanSubject(subject2);

    // Exact match
    if (s1 === s2) return true;

    // One contains the other
    if (s1.includes(s2) || s2.includes(s1)) return true;

    // Levenshtein distance check
    const distance = this.levenshteinDistance(s1, s2);
    const maxLen = Math.max(s1.length, s2.length);
    const similarity = 1 - (distance / maxLen);

    return similarity > 0.8; // 80% similar
  }

  /**
   * Calculate Levenshtein distance
   */
  levenshteinDistance(str1, str2) {
    const matrix = [];

    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i];
    }

    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }

    return matrix[str2.length][str1.length];
  }

  /**
   * Calculate participant overlap
   */
  participantOverlap(participants1, participants2) {
    const set1 = new Set(participants1);
    const set2 = new Set(participants2);

    let overlap = 0;
    for (const p of set1) {
      if (set2.has(p)) overlap++;
    }

    const total = Math.max(set1.size, set2.size);
    return total > 0 ? overlap / total : 0;
  }

  /**
   * Add email to thread or create new thread
   */
  addEmail(email) {
    const threadId = this.detectThread(email) ||
                     this.generateThreadId(email.subject, this.extractParticipants(email));

    // Store email -> thread mapping
    if (email.messageId) {
      this.emailToThread.set(email.messageId, threadId);
    }

    // Get or create thread
    if (!this.threads.has(threadId)) {
      this.threads.set(threadId, {
        id: threadId,
        subject: this.cleanSubject(email.subject),
        participants: this.extractParticipants(email),
        emails: [],
        startDate: email.date,
        lastDate: email.date,
        messageCount: 0,
        userResponseCount: 0,
        otherResponseCount: 0,
        avgResponseTime: 0,
        status: 'active'
      });
    }

    const thread = this.threads.get(threadId);

    // Add email to thread
    thread.emails.push({
      id: email.id,
      messageId: email.messageId,
      from: this.normalizeEmail(email.from),
      date: email.date,
      subject: email.subject,
      body: email.body?.substring(0, 500), // Store snippet
      tier: email.tier,
      isFromUser: this.isUserEmail(email.from)
    });

    // Update thread metadata
    thread.messageCount++;
    thread.lastDate = email.date;

    if (this.isUserEmail(email.from)) {
      thread.userResponseCount++;
    } else {
      thread.otherResponseCount++;
    }

    // Calculate average response time
    this.updateResponseTime(thread);

    logger.info('Email added to thread', {
      threadId,
      emailId: email.id,
      messageCount: thread.messageCount
    });

    return threadId;
  }

  /**
   * Check if email is from user
   */
  isUserEmail(email) {
    const normalized = this.normalizeEmail(email);
    // Configure user emails
    const userEmails = process.env.USER_EMAIL ?
      [this.normalizeEmail(process.env.USER_EMAIL)] :
      [];

    return userEmails.includes(normalized);
  }

  /**
   * Update average response time for thread
   */
  updateResponseTime(thread) {
    const emails = thread.emails;
    if (emails.length < 2) return;

    let totalResponseTime = 0;
    let responseCount = 0;

    for (let i = 1; i < emails.length; i++) {
      const prev = emails[i - 1];
      const curr = emails[i];

      // Different senders = response
      if (prev.from !== curr.from) {
        const responseTime = new Date(curr.date) - new Date(prev.date);
        totalResponseTime += responseTime;
        responseCount++;
      }
    }

    if (responseCount > 0) {
      thread.avgResponseTime = totalResponseTime / responseCount;
    }
  }

  /**
   * Get thread by ID
   */
  getThread(threadId) {
    return this.threads.get(threadId);
  }

  /**
   * Get thread for email
   */
  getThreadForEmail(emailId) {
    const threadId = this.emailToThread.get(emailId);
    return threadId ? this.threads.get(threadId) : null;
  }

  /**
   * Analyze thread and provide insights
   */
  analyzeThread(threadId) {
    const thread = this.threads.get(threadId);
    if (!thread) return null;

    const analysis = {
      threadId: thread.id,
      subject: thread.subject,
      duration: this.calculateDuration(thread),
      messageCount: thread.messageCount,
      participants: thread.participants.length,
      userMessages: thread.userResponseCount,
      otherMessages: thread.otherResponseCount,
      avgResponseTime: this.formatResponseTime(thread.avgResponseTime),
      status: this.determineThreadStatus(thread),
      needsFollowUp: this.needsFollowUp(thread),
      sentiment: this.analyzeThreadSentiment(thread),
      summary: this.generateThreadSummary(thread)
    };

    return analysis;
  }

  /**
   * Calculate thread duration
   */
  calculateDuration(thread) {
    if (!thread.startDate || !thread.lastDate) return '0 days';

    const duration = new Date(thread.lastDate) - new Date(thread.startDate);
    const days = Math.floor(duration / (1000 * 60 * 60 * 24));
    const hours = Math.floor((duration % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));

    if (days > 0) return `${days} day${days > 1 ? 's' : ''}`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
    return 'Less than 1 hour';
  }

  /**
   * Format response time
   */
  formatResponseTime(ms) {
    if (!ms) return 'N/A';

    const hours = Math.floor(ms / (1000 * 60 * 60));
    const minutes = Math.floor((ms % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 24) return `${Math.floor(hours / 24)} day${hours / 24 > 1 ? 's' : ''}`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ${minutes} min`;
    return `${minutes} minutes`;
  }

  /**
   * Determine thread status
   */
  determineThreadStatus(thread) {
    const lastEmail = thread.emails[thread.emails.length - 1];
    const hoursSinceLastEmail = (Date.now() - new Date(lastEmail.date)) / (1000 * 60 * 60);

    if (lastEmail.isFromUser) {
      return 'waiting_for_response';
    } else if (hoursSinceLastEmail > 48) {
      return 'stale';
    } else if (hoursSinceLastEmail > 24) {
      return 'aging';
    } else {
      return 'active';
    }
  }

  /**
   * Check if thread needs follow-up
   */
  needsFollowUp(thread) {
    const lastEmail = thread.emails[thread.emails.length - 1];

    // User sent last message
    if (lastEmail.isFromUser) {
      const hoursSince = (Date.now() - new Date(lastEmail.date)) / (1000 * 60 * 60);

      // No response in 3 days
      if (hoursSince > 72) {
        return {
          needed: true,
          reason: 'No response in 3 days',
          urgency: 'high',
          daysSince: Math.floor(hoursSince / 24)
        };
      }
    } else {
      // Other party sent last message
      const hoursSince = (Date.now() - new Date(lastEmail.date)) / (1000 * 60 * 60);

      // Haven't responded in 24 hours
      if (hoursSince > 24) {
        return {
          needed: true,
          reason: 'Pending response to their message',
          urgency: 'medium',
          hoursSince: Math.floor(hoursSince)
        };
      }
    }

    return { needed: false };
  }

  /**
   * Analyze thread sentiment
   */
  analyzeThreadSentiment(thread) {
    // Simplified sentiment analysis
    // In production, would use ML model
    const recentEmails = thread.emails.slice(-3);
    let urgentCount = 0;
    let positiveCount = 0;
    let negativeCount = 0;

    for (const email of recentEmails) {
      const body = (email.body || '').toLowerCase();

      // Urgent indicators
      if (body.match(/urgent|asap|immediate|critical|emergency/)) {
        urgentCount++;
      }

      // Positive indicators
      if (body.match(/thanks|thank you|appreciate|great|excellent|perfect/)) {
        positiveCount++;
      }

      // Negative indicators
      if (body.match(/unfortunately|problem|issue|concern|frustrated|disappointed/)) {
        negativeCount++;
      }
    }

    if (urgentCount > 0) return 'urgent';
    if (negativeCount > positiveCount) return 'negative';
    if (positiveCount > negativeCount) return 'positive';
    return 'neutral';
  }

  /**
   * Generate thread summary
   */
  generateThreadSummary(thread) {
    const participants = thread.participants.length;
    const duration = this.calculateDuration(thread);

    let summary = `${thread.messageCount} email${thread.messageCount > 1 ? 's' : ''} over ${duration}`;

    if (participants > 2) {
      summary += ` with ${participants} participants`;
    }

    const status = this.determineThreadStatus(thread);
    if (status === 'waiting_for_response') {
      summary += ' (awaiting response)';
    } else if (status === 'stale') {
      summary += ' (stale - no activity)';
    }

    return summary;
  }

  /**
   * Get all active threads
   */
  getActiveThreads() {
    const activeThreads = [];

    for (const thread of this.threads.values()) {
      if (this.determineThreadStatus(thread) !== 'stale') {
        activeThreads.push(this.analyzeThread(thread.id));
      }
    }

    // Sort by last activity
    return activeThreads.sort((a, b) =>
      new Date(b.lastDate) - new Date(a.lastDate)
    );
  }

  /**
   * Get threads needing follow-up
   */
  getThreadsNeedingFollowUp() {
    const needsFollowUp = [];

    for (const thread of this.threads.values()) {
      const followUp = this.needsFollowUp(thread);
      if (followUp.needed) {
        needsFollowUp.push({
          ...this.analyzeThread(thread.id),
          followUp
        });
      }
    }

    // Sort by urgency
    return needsFollowUp.sort((a, b) => {
      const urgencyOrder = { high: 0, medium: 1, low: 2 };
      return urgencyOrder[a.followUp.urgency] - urgencyOrder[b.followUp.urgency];
    });
  }

  /**
   * Get thread statistics
   */
  getStatistics() {
    let totalThreads = 0;
    let activeThreads = 0;
    let staleThreads = 0;
    let totalMessages = 0;
    let avgMessagesPerThread = 0;
    let avgResponseTime = 0;

    for (const thread of this.threads.values()) {
      totalThreads++;
      totalMessages += thread.messageCount;

      const status = this.determineThreadStatus(thread);
      if (status === 'stale') {
        staleThreads++;
      } else {
        activeThreads++;
        avgResponseTime += thread.avgResponseTime || 0;
      }
    }

    avgMessagesPerThread = totalThreads > 0 ? totalMessages / totalThreads : 0;
    avgResponseTime = activeThreads > 0 ? avgResponseTime / activeThreads : 0;

    return {
      totalThreads,
      activeThreads,
      staleThreads,
      totalMessages,
      avgMessagesPerThread: Math.round(avgMessagesPerThread * 10) / 10,
      avgResponseTime: this.formatResponseTime(avgResponseTime)
    };
  }

  /**
   * Export threads to JSON
   */
  exportThreads() {
    const exported = [];

    for (const thread of this.threads.values()) {
      exported.push({
        ...thread,
        analysis: this.analyzeThread(thread.id)
      });
    }

    return exported;
  }

  /**
   * Import threads from JSON
   */
  importThreads(data) {
    for (const thread of data) {
      this.threads.set(thread.id, thread);

      // Rebuild email -> thread mapping
      for (const email of thread.emails) {
        if (email.messageId) {
          this.emailToThread.set(email.messageId, thread.id);
        }
      }
    }

    logger.info('Imported threads', { count: data.length });
  }

  /**
   * Clear old threads (older than N days)
   */
  clearOldThreads(daysOld = 90) {
    const cutoff = Date.now() - (daysOld * 24 * 60 * 60 * 1000);
    let removed = 0;

    for (const [threadId, thread] of this.threads.entries()) {
      if (new Date(thread.lastDate) < cutoff) {
        // Remove thread
        this.threads.delete(threadId);

        // Remove email mappings
        for (const email of thread.emails) {
          if (email.messageId) {
            this.emailToThread.delete(email.messageId);
          }
        }

        removed++;
      }
    }

    logger.info('Cleared old threads', { removed, daysOld });
    return removed;
  }
}

// Singleton instance
const threadDetector = new ThreadDetector();

module.exports = threadDetector;
module.exports.ThreadDetector = ThreadDetector;
