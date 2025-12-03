/**
 * Secure Email Classification System
 * Implements validation layers and security controls for email classification
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// Import security modules
const RateLimiter = require('../../security/rate-limiter');
const AuditLogger = require('../../security/audit-logger');

class SecureEmailClassifier {
    constructor(options = {}) {
        // Configuration
        this.config = this.loadSecurityConfig(options.configPath);

        // Off-limits contacts (never process automatically)
        this.offLimitsContacts = new Set([
            'darrell.coleman@example.com',
            'paul.robertson@example.com',
            'tatyana.brandon@example.com',
            // Add more from config
            ...(this.config.email_classification?.off_limits_contacts || [])
        ]);

        // Critical domains requiring extra validation
        this.criticalDomains = new Set([
            'government.gov',
            'irs.gov',
            'bank.com',
            'legal.com'
        ]);

        // Confidence thresholds
        this.thresholds = {
            tier1: this.config.email_classification?.tier_1_confidence_threshold || 0.95,
            tier2: this.config.email_classification?.tier_2_confidence_threshold || 0.9,
            tier3: this.config.email_classification?.tier_3_auto_draft || true
        };

        // Initialize security components
        this.rateLimiter = options.rateLimiter || null;
        this.auditLogger = options.auditLogger || null;

        // Classification cache (prevents re-processing)
        this.classificationCache = new Map();
        this.cacheTimeout = 3600000; // 1 hour

        // Statistics
        this.stats = {
            totalClassified: 0,
            tier1Count: 0,
            tier2Count: 0,
            tier3Count: 0,
            blockedCount: 0,
            offLimitsBlocked: 0
        };
    }

    /**
     * Load security configuration
     */
    loadSecurityConfig(configPath) {
        const defaultConfig = {
            email_classification: {
                tier_1_confidence_threshold: 0.95,
                tier_2_confidence_threshold: 0.9,
                tier_3_auto_draft: true,
                off_limits_contacts: []
            },
            rate_limits: {
                emails_per_hour: 10,
                sms_per_5_minutes: 1,
                api_calls_per_minute: 30
            },
            audit: {
                log_all_sends: true,
                log_all_classifications: true,
                store_drafts: true
            }
        };

        if (configPath && fs.existsSync(configPath)) {
            try {
                const customConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
                return { ...defaultConfig, ...customConfig };
            } catch (err) {
                console.error('Failed to load custom config, using defaults:', err);
            }
        }

        return defaultConfig;
    }

    /**
     * Classify an email with security validation
     */
    async classifyEmail(email) {
        const startTime = Date.now();

        try {
            // 1. Pre-classification security checks
            const securityCheck = await this.performSecurityChecks(email);
            if (!securityCheck.passed) {
                return this.createBlockedResponse(email, securityCheck.reason);
            }

            // 2. Check cache
            const cacheKey = this.getCacheKey(email);
            if (this.classificationCache.has(cacheKey)) {
                const cached = this.classificationCache.get(cacheKey);
                if (Date.now() - cached.timestamp < this.cacheTimeout) {
                    this.logClassification(email, cached.result, true);
                    return cached.result;
                }
            }

            // 3. Perform classification
            const classification = await this.performClassification(email);

            // 4. Validate classification
            const validation = await this.validateClassification(email, classification);
            if (!validation.valid) {
                return this.createBlockedResponse(email, validation.reason);
            }

            // 5. Apply security overrides
            const finalClassification = this.applySecurityOverrides(email, classification);

            // 6. Cache result
            this.classificationCache.set(cacheKey, {
                result: finalClassification,
                timestamp: Date.now()
            });

            // 7. Log and audit
            this.logClassification(email, finalClassification, false);

            // 8. Update statistics
            this.updateStatistics(finalClassification);

            return finalClassification;

        } catch (error) {
            console.error('Classification error:', error);

            // Log security event
            if (this.auditLogger) {
                this.auditLogger.log_security_violation(
                    'classification_error',
                    error.message
                );
            }

            // Default to most restrictive tier
            return this.createBlockedResponse(email, 'Classification error');
        }
    }

    /**
     * Perform security checks before classification
     */
    async performSecurityChecks(email) {
        // Check off-limits contacts
        if (this.isOffLimitsContact(email.from)) {
            this.stats.offLimitsBlocked++;
            return {
                passed: false,
                reason: 'Off-limits contact'
            };
        }

        // Check rate limits
        if (this.rateLimiter && !await this.rateLimiter.can_classify_email()) {
            return {
                passed: false,
                reason: 'Rate limit exceeded'
            };
        }

        // Check for suspicious patterns
        const suspiciousPatterns = [
            /\$\d{4,}/,  // Large dollar amounts
            /urgent.{0,20}action.{0,20}required/i,
            /verify.{0,20}account.{0,20}immediately/i,
            /suspended.{0,20}account/i
        ];

        for (const pattern of suspiciousPatterns) {
            if (pattern.test(email.subject) || pattern.test(email.body)) {
                return {
                    passed: false,
                    reason: 'Suspicious content pattern detected'
                };
            }
        }

        // Check sender domain
        const senderDomain = email.from.split('@')[1];
        if (this.criticalDomains.has(senderDomain)) {
            // Require manual review for critical domains
            return {
                passed: false,
                reason: 'Critical domain requires manual review'
            };
        }

        return { passed: true };
    }

    /**
     * Check if contact is off-limits
     */
    isOffLimitsContact(emailAddress) {
        // Normalize email address
        const normalized = emailAddress.toLowerCase().trim();

        // Check exact match
        if (this.offLimitsContacts.has(normalized)) {
            return true;
        }

        // Check domain-based rules
        const domain = normalized.split('@')[1];
        if (this.offLimitsContacts.has(`*@${domain}`)) {
            return true;
        }

        // Check name-based rules
        for (const offLimits of this.offLimitsContacts) {
            if (offLimits.includes('*')) {
                const pattern = offLimits.replace('*', '.*');
                const regex = new RegExp(pattern, 'i');
                if (regex.test(normalized)) {
                    return true;
                }
            }
        }

        return false;
    }

    /**
     * Perform the actual email classification
     */
    async performClassification(email) {
        // This is where you'd integrate with your ML model or classification service
        // For now, using rule-based classification

        const classification = {
            tier: 3,  // Default to most restrictive
            confidence: 0.0,
            reasoning: [],
            suggestedAction: 'draft',
            requiresApproval: true
        };

        // Analyze email metadata
        const hoursSinceReceived = (Date.now() - new Date(email.date).getTime()) / (1000 * 60 * 60);

        // Tier 1: Urgent, requires immediate response
        if (this.isTier1Email(email, hoursSinceReceived)) {
            classification.tier = 1;
            classification.confidence = 0.95;
            classification.reasoning.push('Urgent email requiring immediate response');
            classification.suggestedAction = 'auto_reply';
            classification.requiresApproval = false;
        }
        // Tier 2: Important but not urgent
        else if (this.isTier2Email(email, hoursSinceReceived)) {
            classification.tier = 2;
            classification.confidence = 0.85;
            classification.reasoning.push('Important email, can wait up to 24 hours');
            classification.suggestedAction = 'draft_and_schedule';
            classification.requiresApproval = true;
        }
        // Tier 3: Can wait or may not need response
        else {
            classification.tier = 3;
            classification.confidence = 0.75;
            classification.reasoning.push('Non-urgent email');
            classification.suggestedAction = 'draft';
            classification.requiresApproval = true;
        }

        return classification;
    }

    /**
     * Check if email qualifies as Tier 1
     */
    isTier1Email(email, hoursSinceReceived) {
        // Keywords indicating urgency
        const urgentKeywords = [
            'urgent', 'emergency', 'asap', 'immediately',
            'critical', 'time-sensitive', 'deadline today'
        ];

        const subjectLower = email.subject.toLowerCase();
        const bodyLower = (email.body || '').toLowerCase();

        // Check for urgent keywords
        const hasUrgentKeyword = urgentKeywords.some(keyword =>
            subjectLower.includes(keyword) || bodyLower.includes(keyword)
        );

        // Check if from VIP
        const isVIP = this.isVIPSender(email.from);

        // Check if recent (less than 2 hours old)
        const isRecent = hoursSinceReceived < 2;

        return hasUrgentKeyword && (isVIP || isRecent);
    }

    /**
     * Check if email qualifies as Tier 2
     */
    isTier2Email(email, hoursSinceReceived) {
        // Keywords indicating importance
        const importantKeywords = [
            'important', 'meeting', 'appointment', 'follow-up',
            'reminder', 'action required', 'response needed'
        ];

        const subjectLower = email.subject.toLowerCase();
        const bodyLower = (email.body || '').toLowerCase();

        // Check for important keywords
        const hasImportantKeyword = importantKeywords.some(keyword =>
            subjectLower.includes(keyword) || bodyLower.includes(keyword)
        );

        // Check if from known contact
        const isKnownContact = this.isKnownContact(email.from);

        // Check if relatively recent (less than 24 hours)
        const isRecentEnough = hoursSinceReceived < 24;

        return hasImportantKeyword && isKnownContact && isRecentEnough;
    }

    /**
     * Check if sender is VIP
     */
    isVIPSender(emailAddress) {
        const vipDomains = ['goodportion.org', 'important-client.com'];
        const domain = emailAddress.split('@')[1];
        return vipDomains.includes(domain);
    }

    /**
     * Check if sender is known contact
     */
    isKnownContact(emailAddress) {
        // In production, this would check against a contact database
        // For now, checking if it's not a generic/automated sender
        const automatedPatterns = [
            'noreply@', 'no-reply@', 'donotreply@',
            'notifications@', 'alerts@', 'automated@'
        ];

        return !automatedPatterns.some(pattern =>
            emailAddress.toLowerCase().includes(pattern)
        );
    }

    /**
     * Validate classification results
     */
    async validateClassification(email, classification) {
        // Check confidence thresholds
        if (classification.tier === 1 && classification.confidence < this.thresholds.tier1) {
            return {
                valid: false,
                reason: `Tier 1 confidence below threshold (${classification.confidence} < ${this.thresholds.tier1})`
            };
        }

        if (classification.tier === 2 && classification.confidence < this.thresholds.tier2) {
            return {
                valid: false,
                reason: `Tier 2 confidence below threshold (${classification.confidence} < ${this.thresholds.tier2})`
            };
        }

        // Validate suggested action
        const validActions = ['auto_reply', 'draft_and_schedule', 'draft', 'ignore', 'block'];
        if (!validActions.includes(classification.suggestedAction)) {
            return {
                valid: false,
                reason: `Invalid suggested action: ${classification.suggestedAction}`
            };
        }

        // Additional tier-specific validation
        if (classification.tier === 1) {
            // Tier 1 should never be from unknown senders
            if (!this.isKnownContact(email.from) && !this.isVIPSender(email.from)) {
                return {
                    valid: false,
                    reason: 'Tier 1 classification not allowed for unknown senders'
                };
            }
        }

        return { valid: true };
    }

    /**
     * Apply security overrides to classification
     */
    applySecurityOverrides(email, classification) {
        const overridden = { ...classification };

        // Never auto-reply to certain domains
        const noAutoReplyDomains = ['irs.gov', 'court.gov', 'police.gov'];
        const senderDomain = email.from.split('@')[1];

        if (noAutoReplyDomains.includes(senderDomain)) {
            if (overridden.suggestedAction === 'auto_reply') {
                overridden.suggestedAction = 'draft';
                overridden.requiresApproval = true;
                overridden.reasoning.push('Security override: No auto-reply to government domain');
            }
        }

        // Force manual review for emails with attachments
        if (email.hasAttachments) {
            overridden.requiresApproval = true;
            overridden.reasoning.push('Manual review required: Email has attachments');
        }

        // Force manual review for emails mentioning money/payments
        const moneyPatterns = [
            /\$[\d,]+/,
            /payment/i,
            /invoice/i,
            /wire transfer/i,
            /bank account/i
        ];

        const hasMoneyMention = moneyPatterns.some(pattern =>
            pattern.test(email.subject) || pattern.test(email.body)
        );

        if (hasMoneyMention) {
            overridden.requiresApproval = true;
            overridden.reasoning.push('Manual review required: Financial content detected');
        }

        return overridden;
    }

    /**
     * Create blocked response
     */
    createBlockedResponse(email, reason) {
        this.stats.blockedCount++;

        const response = {
            tier: 99,  // Special tier for blocked
            confidence: 1.0,
            reasoning: [reason],
            suggestedAction: 'block',
            requiresApproval: true,
            blocked: true,
            blockReason: reason
        };

        // Log blocking event
        if (this.auditLogger) {
            this.auditLogger.log_email_blocked(email.from, reason);
        }

        return response;
    }

    /**
     * Get cache key for email
     */
    getCacheKey(email) {
        const data = `${email.id}:${email.from}:${email.subject}`;
        return crypto.createHash('sha256').update(data).digest('hex');
    }

    /**
     * Log classification result
     */
    logClassification(email, classification, fromCache) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            emailId: email.id,
            from: email.from,
            subject: email.subject,
            tier: classification.tier,
            confidence: classification.confidence,
            action: classification.suggestedAction,
            fromCache: fromCache,
            blocked: classification.blocked || false
        };

        // Log to audit system
        if (this.auditLogger && this.config.audit?.log_all_classifications) {
            this.auditLogger.log_email_classified(
                email.from,
                email.subject,
                classification.tier,
                classification.confidence
            );
        }

        // Store classification history
        const historyFile = path.join(__dirname, 'classification-history.jsonl');
        fs.appendFileSync(historyFile, JSON.stringify(logEntry) + '\n');
    }

    /**
     * Update statistics
     */
    updateStatistics(classification) {
        this.stats.totalClassified++;

        switch (classification.tier) {
            case 1:
                this.stats.tier1Count++;
                break;
            case 2:
                this.stats.tier2Count++;
                break;
            case 3:
                this.stats.tier3Count++;
                break;
        }
    }

    /**
     * Get classification statistics
     */
    getStatistics() {
        return {
            ...this.stats,
            cacheSize: this.classificationCache.size,
            tier1Percentage: (this.stats.tier1Count / this.stats.totalClassified * 100).toFixed(2),
            tier2Percentage: (this.stats.tier2Count / this.stats.totalClassified * 100).toFixed(2),
            tier3Percentage: (this.stats.tier3Count / this.stats.totalClassified * 100).toFixed(2),
            blockRate: (this.stats.blockedCount / this.stats.totalClassified * 100).toFixed(2)
        };
    }

    /**
     * Clear classification cache
     */
    clearCache() {
        this.classificationCache.clear();
    }

    /**
     * Update off-limits contacts
     */
    updateOffLimitsContacts(contacts) {
        this.offLimitsContacts = new Set(contacts);
    }

    /**
     * Add new off-limits contact
     */
    addOffLimitsContact(contact) {
        this.offLimitsContacts.add(contact.toLowerCase().trim());
    }

    /**
     * Remove off-limits contact
     */
    removeOffLimitsContact(contact) {
        this.offLimitsContacts.delete(contact.toLowerCase().trim());
    }
}

module.exports = SecureEmailClassifier;