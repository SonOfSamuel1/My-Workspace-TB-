/**
 * Action Token Generator
 * Generates secure, time-limited tokens for email action buttons
 *
 * Tokens are HMAC-SHA256 signed with a 24-hour expiry.
 * Used for one-click approve/reject/snooze buttons in email summaries.
 */

const crypto = require('crypto');

class ActionTokenGenerator {
  constructor(secretKey) {
    this.secretKey = secretKey || process.env.ACTION_SECRET_KEY || this._generateDefaultKey();
    this.tokenExpiry = 24 * 60 * 60 * 1000; // 24 hours
  }

  /**
   * Generate a secure default key if none provided
   * Note: In production, always use ACTION_SECRET_KEY env var
   */
  _generateDefaultKey() {
    console.warn('ActionTokenGenerator: Using generated default key. Set ACTION_SECRET_KEY in production.');
    return crypto.randomBytes(32).toString('hex');
  }

  /**
   * Generate a signed token for an email action
   * @param {string} emailId - Gmail message ID
   * @param {string} action - Action type (approve, reject, snooze, archive)
   * @param {string} userId - User email address
   * @param {object} options - Additional options
   * @returns {string} Base64url encoded signed token
   */
  generateToken(emailId, action, userId, options = {}) {
    const payload = {
      eid: emailId,
      act: action,
      uid: userId,
      exp: Date.now() + (options.expiry || this.tokenExpiry),
      nonce: crypto.randomBytes(8).toString('hex'),
      // Optional metadata
      ...(options.metadata && { meta: options.metadata })
    };

    const payloadStr = Buffer.from(JSON.stringify(payload)).toString('base64url');
    const signature = crypto
      .createHmac('sha256', this.secretKey)
      .update(payloadStr)
      .digest('base64url');

    return `${payloadStr}.${signature}`;
  }

  /**
   * Verify and decode a token
   * @param {string} token - The token to verify
   * @returns {object} Verification result with valid flag and decoded payload
   */
  verifyToken(token) {
    try {
      if (!token || typeof token !== 'string') {
        return { valid: false, error: 'Invalid token format' };
      }

      const parts = token.split('.');
      if (parts.length !== 2) {
        return { valid: false, error: 'Malformed token' };
      }

      const [payloadStr, signature] = parts;

      // Verify signature
      const expectedSignature = crypto
        .createHmac('sha256', this.secretKey)
        .update(payloadStr)
        .digest('base64url');

      // Use timing-safe comparison to prevent timing attacks
      if (!crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expectedSignature)
      )) {
        return { valid: false, error: 'Invalid signature' };
      }

      // Decode and check expiry
      const payload = JSON.parse(Buffer.from(payloadStr, 'base64url').toString());

      if (Date.now() > payload.exp) {
        return { valid: false, error: 'Token expired' };
      }

      return {
        valid: true,
        emailId: payload.eid,
        action: payload.act,
        userId: payload.uid,
        expiresAt: new Date(payload.exp),
        metadata: payload.meta || null
      };
    } catch (error) {
      return { valid: false, error: `Token verification failed: ${error.message}` };
    }
  }

  /**
   * Generate action URL with embedded token
   * @param {string} baseUrl - Base URL for action endpoint
   * @param {string} emailId - Gmail message ID
   * @param {string} action - Action type
   * @param {string} userId - User email address
   * @returns {string} Full action URL
   */
  generateActionUrl(baseUrl, emailId, action, userId) {
    const token = this.generateToken(emailId, action, userId);
    return `${baseUrl}/${action}?token=${encodeURIComponent(token)}`;
  }

  /**
   * Generate multiple action URLs for an email
   * @param {string} baseUrl - Base URL for action endpoint
   * @param {string} emailId - Gmail message ID
   * @param {string} userId - User email address
   * @param {string[]} actions - Array of action types
   * @returns {object} Map of action to URL
   */
  generateActionUrls(baseUrl, emailId, userId, actions = ['approve', 'reject', 'snooze', 'view']) {
    const urls = {};
    for (const action of actions) {
      urls[action] = this.generateActionUrl(baseUrl, emailId, action, userId);
    }
    return urls;
  }
}

module.exports = ActionTokenGenerator;
