/**
 * Multi-User Management System
 * Support multiple users/accounts with separate configurations
 */

const logger = require('./logger');
const crypto = require('crypto');

class MultiUserManagement {
  constructor() {
    this.users = new Map();
    this.sessions = new Map();
    this.teamAccounts = new Map();
    this.sharedConfigurations = new Map();
  }

  /**
   * Create new user account
   */
  createUser(userData) {
    const userId = this.generateUserId();

    const user = {
      id: userId,
      email: userData.email,
      name: userData.name,
      role: userData.role || 'user',
      preferences: {
        delegationLevel: userData.delegationLevel || 2,
        timezone: userData.timezone || 'America/New_York',
        language: userData.language || 'en',
        communicationStyle: userData.communicationStyle || 'professional',
        escalationPhone: userData.escalationPhone,
        escalationEmail: userData.escalationEmail,
        slackChannel: userData.slackChannel
      },
      emailAccounts: [],
      workflows: [],
      offLimitsContacts: userData.offLimitsContacts || [],
      vipContacts: userData.vipContacts || [],
      labels: userData.labels || this.getDefaultLabels(),
      tier Rules: userData.tierRules || this.getDefaultTierRules(),
      createdAt: new Date(),
      lastActive: new Date(),
      status: 'active',
      quota: {
        emailsPerDay: userData.emailsPerDay || 1000,
        claudeTokensPerDay: userData.claudeTokensPerDay || 1000000
      },
      usage: {
        emailsToday: 0,
        tokensToday: 0,
        totalEmails: 0,
        totalTokens: 0
      },
      teamId: userData.teamId || null
    };

    this.users.set(userId, user);

    logger.info('User created', {
      userId,
      email: user.email,
      role: user.role
    });

    return user;
  }

  /**
   * Link email account to user
   */
  async linkEmailAccount(userId, emailAccountData) {
    const user = this.users.get(userId);
    if (!user) {
      throw new Error(`User ${userId} not found`);
    }

    const accountId = this.generateAccountId();

    const emailAccount = {
      id: accountId,
      email: emailAccountData.email,
      provider: emailAccountData.provider || 'gmail',
      credentials: {
        type: emailAccountData.credentialsType || 'oauth',
        // In production, store encrypted credentials
        encrypted: this.encryptCredentials(emailAccountData.credentials)
      },
      isPrimary: emailAccountData.isPrimary || false,
      enabled: true,
      linkedAt: new Date(),
      lastSync: null,
      stats: {
        totalProcessed: 0,
        lastProcessedAt: null
      }
    };

    user.emailAccounts.push(emailAccount);

    logger.info('Email account linked', {
      userId,
      accountId,
      email: emailAccount.email
    });

    return emailAccount;
  }

  /**
   * Create team account
   */
  createTeam(teamData) {
    const teamId = this.generateTeamId();

    const team = {
      id: teamId,
      name: teamData.name,
      adminUsers: [teamData.createdBy],
      members: [],
      sharedWorkflows: [],
      sharedConfigurations: {},
      billing: {
        plan: teamData.plan || 'team',
        quotaShared: true,
        emailsPerDay: teamData.emailsPerDay || 5000,
        claudeTokensPerDay: teamData.claudeTokensPerDay || 5000000
      },
      createdAt: new Date(),
      createdBy: teamData.createdBy
    };

    this.teamAccounts.set(teamId, team);

    logger.info('Team created', {
      teamId,
      name: team.name,
      createdBy: teamData.createdBy
    });

    return team;
  }

  /**
   * Add user to team
   */
  addTeamMember(teamId, userId, role = 'member') {
    const team = this.teamAccounts.get(teamId);
    if (!team) {
      throw new Error(`Team ${teamId} not found`);
    }

    const user = this.users.get(userId);
    if (!user) {
      throw new Error(`User ${userId} not found`);
    }

    const member = {
      userId,
      role, // admin, member, viewer
      joinedAt: new Date(),
      permissions: this.getTeamPermissions(role)
    };

    team.members.push(member);
    user.teamId = teamId;

    logger.info('User added to team', {
      teamId,
      userId,
      role
    });

    return member;
  }

  /**
   * Get team permissions based on role
   */
  getTeamPermissions(role) {
    const permissions = {
      admin: {
        canManageMembers: true,
        canEditWorkflows: true,
        canViewAnalytics: true,
        canManageBilling: true,
        canEditSharedConfig: true
      },
      member: {
        canManageMembers: false,
        canEditWorkflows: true,
        canViewAnalytics: true,
        canManageBilling: false,
        canEditSharedConfig: false
      },
      viewer: {
        canManageMembers: false,
        canEditWorkflows: false,
        canViewAnalytics: true,
        canManageBilling: false,
        canEditSharedConfig: false
      }
    };

    return permissions[role] || permissions.viewer;
  }

  /**
   * Share workflow within team
   */
  shareWorkflow(workflowId, userId, teamId) {
    const team = this.teamAccounts.get(teamId);
    if (!team) {
      throw new Error(`Team ${teamId} not found`);
    }

    const user = this.users.get(userId);
    if (!user || user.teamId !== teamId) {
      throw new Error('User not authorized for this team');
    }

    team.sharedWorkflows.push({
      workflowId,
      sharedBy: userId,
      sharedAt: new Date(),
      permissions: 'view_and_copy' // or 'edit'
    });

    logger.info('Workflow shared with team', {
      workflowId,
      teamId,
      sharedBy: userId
    });
  }

  /**
   * Get user configuration for email processing
   */
  getUserConfiguration(userId) {
    const user = this.users.get(userId);
    if (!user) {
      throw new Error(`User ${userId} not found`);
    }

    const config = {
      userId: user.id,
      email: user.email,
      name: user.name,
      preferences: user.preferences,
      offLimitsContacts: user.offLimitsContacts,
      vipContacts: user.vipContacts,
      labels: user.labels,
      tierRules: user.tierRules,
      emailAccounts: user.emailAccounts.filter(a => a.enabled)
    };

    // If user is part of team, include shared configurations
    if (user.teamId) {
      const team = this.teamAccounts.get(user.teamId);
      if (team) {
        config.teamConfiguration = team.sharedConfigurations;
        config.sharedWorkflows = team.sharedWorkflows;
      }
    }

    return config;
  }

  /**
   * Check and enforce quota
   */
  checkQuota(userId, emailCount = 0, tokenCount = 0) {
    const user = this.users.get(userId);
    if (!user) {
      throw new Error(`User ${userId} not found`);
    }

    let quota = user.quota;
    let usage = user.usage;

    // If part of team with shared quota
    if (user.teamId) {
      const team = this.teamAccounts.get(user.teamId);
      if (team && team.billing.quotaShared) {
        quota = team.billing;
        usage = this.getTeamUsage(user.teamId);
      }
    }

    const emailsRemaining = quota.emailsPerDay - (usage.emailsToday + emailCount);
    const tokensRemaining = quota.claudeTokensPerDay - (usage.tokensToday + tokenCount);

    const withinQuota = emailsRemaining >= 0 && tokensRemaining >= 0;

    return {
      withinQuota,
      quotas: {
        emails: {
          limit: quota.emailsPerDay,
          used: usage.emailsToday,
          remaining: emailsRemaining
        },
        tokens: {
          limit: quota.claudeTokensPerDay,
          used: usage.tokensToday,
          remaining: tokensRemaining
        }
      },
      action: withinQuota ? 'allow' : 'deny',
      message: withinQuota ?
        'Within quota limits' :
        `Quota exceeded. Emails: ${emailsRemaining < 0 ? emailsRemaining : 'OK'}, Tokens: ${tokensRemaining < 0 ? tokensRemaining : 'OK'}`
    };
  }

  /**
   * Track usage for user
   */
  trackUsage(userId, emailCount = 0, tokenCount = 0) {
    const user = this.users.get(userId);
    if (!user) return;

    user.usage.emailsToday += emailCount;
    user.usage.tokensToday += tokenCount;
    user.usage.totalEmails += emailCount;
    user.usage.totalTokens += tokenCount;
    user.lastActive = new Date();

    logger.debug('Usage tracked', {
      userId,
      emailCount,
      tokenCount
    });
  }

  /**
   * Reset daily usage (run daily at midnight)
   */
  resetDailyUsage() {
    for (const [userId, user] of this.users.entries()) {
      user.usage.emailsToday = 0;
      user.usage.tokensToday = 0;
    }

    logger.info('Daily usage reset for all users');
  }

  /**
   * Get team usage
   */
  getTeamUsage(teamId) {
    const team = this.teamAccounts.get(teamId);
    if (!team) return { emailsToday: 0, tokensToday: 0 };

    let totalEmails = 0;
    let totalTokens = 0;

    for (const member of team.members) {
      const user = this.users.get(member.userId);
      if (user) {
        totalEmails += user.usage.emailsToday;
        totalTokens += user.usage.tokensToday;
      }
    }

    return {
      emailsToday: totalEmails,
      tokensToday: totalTokens
    };
  }

  /**
   * Create session for user
   */
  createSession(userId) {
    const sessionId = this.generateSessionId();
    const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours

    const session = {
      id: sessionId,
      userId,
      createdAt: new Date(),
      expiresAt,
      lastActivity: new Date()
    };

    this.sessions.set(sessionId, session);

    return session;
  }

  /**
   * Validate session
   */
  validateSession(sessionId) {
    const session = this.sessions.get(sessionId);

    if (!session) {
      return { valid: false, reason: 'Session not found' };
    }

    if (new Date() > new Date(session.expiresAt)) {
      this.sessions.delete(sessionId);
      return { valid: false, reason: 'Session expired' };
    }

    // Update last activity
    session.lastActivity = new Date();

    return { valid: true, session };
  }

  /**
   * Get default labels
   */
  getDefaultLabels() {
    return [
      'Action Required',
      'To Read',
      'Waiting For',
      'Completed',
      'VIP',
      'Meetings',
      'Travel',
      'Expenses',
      'Newsletters'
    ];
  }

  /**
   * Get default tier rules
   */
  getDefaultTierRules() {
    return {
      tier1: {
        escalateImmediately: true,
        notificationMethod: ['sms', 'push', 'email'],
        keywords: ['urgent', 'critical', 'revenue', 'legal', 'board']
      },
      tier2: {
        handleAutonomously: true,
        requiresApproval: false,
        actions: ['schedule', 'respond', 'label', 'archive']
      },
      tier3: {
        draftForApproval: true,
        notifyDraftReady: true
      },
      tier4: {
        flagOnly: true,
        neverSend: true
      }
    };
  }

  /**
   * Generate user ID
   */
  generateUserId() {
    return `user_${Date.now()}_${crypto.randomBytes(8).toString('hex')}`;
  }

  /**
   * Generate account ID
   */
  generateAccountId() {
    return `account_${Date.now()}_${crypto.randomBytes(6).toString('hex')}`;
  }

  /**
   * Generate team ID
   */
  generateTeamId() {
    return `team_${Date.now()}_${crypto.randomBytes(6).toString('hex')}`;
  }

  /**
   * Generate session ID
   */
  generateSessionId() {
    return crypto.randomBytes(32).toString('hex');
  }

  /**
   * Encrypt credentials (placeholder)
   */
  encryptCredentials(credentials) {
    // In production, use proper encryption
    // AWS KMS, Vault, or similar
    return Buffer.from(JSON.stringify(credentials)).toString('base64');
  }

  /**
   * Decrypt credentials (placeholder)
   */
  decryptCredentials(encrypted) {
    // In production, use proper decryption
    return JSON.parse(Buffer.from(encrypted, 'base64').toString());
  }

  /**
   * Get user statistics
   */
  getUserStatistics(userId) {
    const user = this.users.get(userId);
    if (!user) return null;

    return {
      userId: user.id,
      email: user.email,
      accountAge: Math.floor((new Date() - new Date(user.createdAt)) / (1000 * 60 * 60 * 24)),
      emailAccounts: user.emailAccounts.length,
      usage: user.usage,
      quota: user.quota,
      quotaUsagePercent: {
        emails: (user.usage.emailsToday / user.quota.emailsPerDay * 100).toFixed(1),
        tokens: (user.usage.tokensToday / user.quota.claudeTokensPerDay * 100).toFixed(1)
      },
      teamMember: !!user.teamId
    };
  }

  /**
   * Get team statistics
   */
  getTeamStatistics(teamId) {
    const team = this.teamAccounts.get(teamId);
    if (!team) return null;

    const usage = this.getTeamUsage(teamId);

    return {
      teamId: team.id,
      name: team.name,
      members: team.members.length,
      usage,
      quota: team.billing,
      quotaUsagePercent: {
        emails: (usage.emailsToday / team.billing.emailsPerDay * 100).toFixed(1),
        tokens: (usage.tokensToday / team.billing.claudeTokensPerDay * 100).toFixed(1)
      },
      sharedWorkflows: team.sharedWorkflows.length
    };
  }

  /**
   * Get all users
   */
  getAllUsers() {
    return Array.from(this.users.values());
  }

  /**
   * Get all teams
   */
  getAllTeams() {
    return Array.from(this.teamAccounts.values());
  }

  /**
   * Export data
   */
  exportData() {
    return {
      users: Array.from(this.users.entries()),
      teams: Array.from(this.teamAccounts.entries()),
      exportedAt: new Date().toISOString()
    };
  }

  /**
   * Import data
   */
  importData(data) {
    this.users = new Map(data.users);
    this.teamAccounts = new Map(data.teams);

    logger.info('Multi-user data imported', {
      users: this.users.size,
      teams: this.teamAccounts.size
    });
  }
}

module.exports = new MultiUserManagement();
module.exports.MultiUserManagement = MultiUserManagement;
