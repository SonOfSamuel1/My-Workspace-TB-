/**
 * Enhanced Email Summary Generator v2.0
 * Creates beautiful, responsive HTML email summaries with:
 * - Modern design system (Cyan/Emerald palette)
 * - Table-based layouts for email client compatibility
 * - Quick action buttons with secure tokens
 * - Data visualization (progress bars, stats with trends)
 * - Priority highlighting
 * - Mobile-first responsive design
 */

const logger = require('./logger');
const ActionTokenGenerator = require('./action-token-generator');

class EmailSummaryGenerator {
  constructor(config = {}) {
    this.dashboardUrl = config.dashboardUrl || 'https://email-assistant.yourdomain.com/dashboard';
    this.actionBaseUrl = config.actionBaseUrl || `${this.dashboardUrl}/api/actions`;
    this.userEmail = config.userEmail || 'terrance@goodportion.org';

    // Action token generator for quick action buttons
    this.tokenGenerator = new ActionTokenGenerator(config.actionSecretKey);

    // Modern design system - Cyan/Emerald palette
    this.brandColors = {
      // Primary
      primary: '#0891b2',
      primaryDark: '#0e7490',
      primaryLight: '#22d3ee',
      primaryBg: '#ecfeff',

      // Semantic colors
      urgent: '#dc2626',
      urgentBg: '#fef2f2',
      warning: '#d97706',
      warningBg: '#fffbeb',
      success: '#059669',
      successBg: '#ecfdf5',
      info: '#2563eb',
      infoBg: '#eff6ff',

      // Neutrals
      dark: '#0f172a',
      medium: '#475569',
      light: '#f1f5f9',
      border: '#e2e8f0',
      white: '#ffffff'
    };

    // Font stack for email clients
    this.fontStack = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
  }

  /**
   * Generate morning brief email
   */
  async generateMorningBrief(data) {
    const {
      overnight = {},
      tier1Escalations = [],
      tier3Pending = [],
      tier2Handled = [],
      stats = {},
      agentActivity = {}
    } = data;

    const hasUrgent = tier1Escalations.length > 0;

    const html = this.buildEmailTemplate({
      title: 'Morning Email Brief',
      subtitle: this.getGreeting() + ', here\'s your morning summary',
      emailType: hasUrgent ? 'urgent' : 'default',
      sections: [
        hasUrgent && this.buildAlertBanner(tier1Escalations.length),
        this.buildQuickStatsGrid({
          processed: overnight.totalEmails || 0,
          escalations: tier1Escalations.length,
          handled: tier2Handled.length,
          pending: tier3Pending.length
        }),
        this.buildUrgentSection(tier1Escalations),
        this.buildPendingApprovalsSection(tier3Pending),
        this.buildOvernightSummary(overnight),
        this.buildHandledSection(tier2Handled),
        this.buildAgentActivitySection(agentActivity)
      ],
      ctaButton: {
        text: 'View Full Dashboard',
        url: this.dashboardUrl
      }
    });

    const plainText = this.generatePlainText(data, 'morning');

    return {
      html,
      plainText,
      subject: hasUrgent
        ? `[ACTION REQUIRED] ${tier1Escalations.length} urgent email${tier1Escalations.length > 1 ? 's' : ''} need attention`
        : `Morning Brief: ${tier3Pending.length} pending approval`
    };
  }

  /**
   * Generate end-of-day report
   */
  async generateEODReport(data) {
    const {
      todayStats = {},
      actionsTaken = [],
      pendingForTomorrow = [],
      costs = {},
      insights = [],
      topSenders = []
    } = data;

    const html = this.buildEmailTemplate({
      title: 'End of Day Report',
      subtitle: 'Your daily email management summary',
      emailType: 'default',
      sections: [
        this.buildQuickStatsGrid({
          processed: todayStats.totalProcessed || 0,
          escalations: todayStats.escalations || 0,
          handled: todayStats.handled || 0,
          drafts: todayStats.drafts || 0
        }, {
          processedTrend: todayStats.processedTrend,
          showTrends: true
        }),
        this.buildEmailFlowVisualization(todayStats),
        this.buildActionsTable(actionsTaken),
        this.buildCostSummaryRow(costs),
        this.buildTomorrowSection(pendingForTomorrow),
        this.buildInsightsSection(insights),
        this.buildTopSendersSection(topSenders)
      ],
      ctaButton: {
        text: 'View Analytics Dashboard',
        url: `${this.dashboardUrl}/analytics`
      }
    });

    const plainText = this.generatePlainText(data, 'eod');

    return {
      html,
      plainText,
      subject: `EOD Report: ${todayStats.totalProcessed || 0} emails processed, ${todayStats.handled || 0} auto-handled`
    };
  }

  /**
   * Generate midday check email (only if urgent items)
   */
  async generateMiddayCheck(urgentItems) {
    if (!urgentItems || urgentItems.length === 0) {
      return null;
    }

    const html = this.buildEmailTemplate({
      title: 'Urgent Items Alert',
      subtitle: 'Immediate attention required',
      emailType: 'urgent',
      sections: [
        this.buildAlertBanner(urgentItems.length, 'These items require your immediate attention'),
        this.buildUrgentAlertSection(urgentItems)
      ],
      ctaButton: {
        text: 'Handle All Urgent Items',
        url: `${this.dashboardUrl}/urgent`,
        color: this.brandColors.urgent
      }
    });

    const plainText = urgentItems.map(item =>
      `URGENT: ${item.subject} from ${item.from}`
    ).join('\n');

    return {
      html,
      plainText,
      subject: `[URGENT] ${urgentItems.length} item${urgentItems.length > 1 ? 's' : ''} require immediate attention`,
      priority: 'high'
    };
  }

  // ==========================================
  // TEMPLATE BUILDING METHODS
  // ==========================================

  /**
   * Build the main email template with table-based layout
   */
  buildEmailTemplate({ title, subtitle, sections, ctaButton, emailType = 'default' }) {
    const sectionsHtml = sections.filter(s => s).join('');
    const headerGradient = emailType === 'urgent'
      ? `background: linear-gradient(135deg, ${this.brandColors.urgent} 0%, #b91c1c 100%);`
      : `background: linear-gradient(135deg, ${this.brandColors.primary} 0%, ${this.brandColors.primaryDark} 100%);`;

    return `<!DOCTYPE html>
<html lang="en" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="x-apple-disable-message-reformatting">
  <title>${title}</title>
  <!--[if mso]>
  <noscript>
    <xml>
      <o:OfficeDocumentSettings>
        <o:PixelsPerInch>96</o:PixelsPerInch>
      </o:OfficeDocumentSettings>
    </xml>
  </noscript>
  <style>
    table { border-collapse: collapse; }
    td { font-family: Arial, sans-serif; }
    .button-td { padding: 0 !important; }
  </style>
  <![endif]-->
  <style>
    /* Reset */
    body, table, td, p, a, li { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
    table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
    img { -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }

    /* Base */
    body { margin: 0 !important; padding: 0 !important; width: 100% !important; background-color: ${this.brandColors.light}; }

    /* Mobile Responsive */
    @media only screen and (max-width: 600px) {
      .container { width: 100% !important; padding: 12px !important; }
      .stat-cell { display: block !important; width: 100% !important; padding: 8px 0 !important; }
      .stat-table { margin-bottom: 8px !important; }
      .action-cell { display: block !important; width: 100% !important; margin-bottom: 8px !important; padding: 0 !important; }
      .action-button { width: 100% !important; text-align: center !important; }
      .hide-mobile { display: none !important; }
      .stack-mobile { display: block !important; width: 100% !important; }
      .mobile-padding { padding: 16px !important; }
      .mobile-text-center { text-align: center !important; }
      .email-item-table { margin-bottom: 16px !important; }
    }
  </style>
</head>
<body style="margin: 0; padding: 0; background-color: ${this.brandColors.light};">
  <!-- Wrapper -->
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: ${this.brandColors.light};">
    <tr>
      <td align="center" style="padding: 24px 16px;">
        <!-- Container -->
        <table role="presentation" class="container" width="600" cellspacing="0" cellpadding="0" border="0" style="background-color: ${this.brandColors.white}; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);">
          <!-- Header -->
          <tr>
            <td style="${headerGradient} padding: 32px 24px; text-align: center;">
              <h1 style="margin: 0 0 8px 0; font-family: ${this.fontStack}; font-size: 24px; font-weight: 700; color: ${this.brandColors.white}; letter-spacing: -0.5px;">
                ${title}
              </h1>
              <p style="margin: 0; font-family: ${this.fontStack}; font-size: 14px; color: rgba(255,255,255,0.9);">
                ${subtitle}
              </p>
            </td>
          </tr>

          <!-- Content -->
          <tr>
            <td class="mobile-padding" style="padding: 24px;">
              ${sectionsHtml}

              ${ctaButton ? this.buildCTAButton(ctaButton) : ''}
            </td>
          </tr>

          <!-- Footer -->
          ${this.buildFooter()}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
  }

  /**
   * Build alert banner for urgent items
   */
  buildAlertBanner(count, message = null) {
    const defaultMessage = count === 1
      ? '1 urgent email needs your immediate attention'
      : `${count} urgent emails need your immediate attention`;

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td style="background: ${this.brandColors.urgentBg}; border: 1px solid ${this.brandColors.urgent}; border-radius: 8px; padding: 16px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
              <tr>
                <td width="40" style="vertical-align: top;">
                  <div style="width: 32px; height: 32px; background: ${this.brandColors.urgent}; border-radius: 50%; text-align: center; line-height: 32px; font-size: 16px;">
                    &#9888;
                  </div>
                </td>
                <td style="vertical-align: middle; padding-left: 12px;">
                  <span style="font-family: ${this.fontStack}; font-size: 15px; font-weight: 600; color: ${this.brandColors.urgent};">
                    ${message || defaultMessage}
                  </span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build quick stats grid with visual indicators
   */
  buildQuickStatsGrid(stats, options = {}) {
    const items = [
      { label: 'Processed', value: stats.processed || 0, color: this.brandColors.primary, trend: options.processedTrend },
      { label: 'Escalated', value: stats.escalations || 0, color: this.brandColors.urgent },
      { label: 'Handled', value: stats.handled || 0, color: this.brandColors.success },
      { label: options.showTrends ? 'Drafts' : 'Pending', value: stats.drafts || stats.pending || 0, color: this.brandColors.warning }
    ];

    const statCells = items.map(item => `
      <td class="stat-cell" width="25%" style="padding: 8px; vertical-align: top;">
        <table role="presentation" class="stat-table" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: ${this.brandColors.light}; border-radius: 8px;">
          <tr>
            <td style="padding: 16px; text-align: center;">
              <div style="font-family: ${this.fontStack}; font-size: 32px; font-weight: 700; color: ${item.color}; line-height: 1;">
                ${item.value}
              </div>
              <div style="font-family: ${this.fontStack}; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: ${this.brandColors.medium}; margin-top: 4px;">
                ${item.label}
              </div>
              ${options.showTrends && item.trend !== undefined ? `
                <div style="font-family: ${this.fontStack}; font-size: 10px; color: ${item.trend >= 0 ? this.brandColors.success : this.brandColors.urgent}; margin-top: 4px;">
                  ${item.trend >= 0 ? '&#9650;' : '&#9660;'} ${Math.abs(item.trend)}%
                </div>
              ` : ''}
            </td>
          </tr>
        </table>
      </td>
    `).join('');

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          ${statCells}
        </tr>
      </table>
    `;
  }

  /**
   * Build email flow visualization (horizontal stacked bar)
   */
  buildEmailFlowVisualization(stats) {
    const total = (stats.totalProcessed || 0);
    if (total === 0) return '';

    const escalated = stats.escalations || 0;
    const handled = stats.handled || 0;
    const drafts = stats.drafts || 0;
    const flagged = Math.max(0, total - escalated - handled - drafts);

    const escPct = Math.round((escalated / total) * 100);
    const handledPct = Math.round((handled / total) * 100);
    const draftsPct = Math.round((drafts / total) * 100);
    const flaggedPct = 100 - escPct - handledPct - draftsPct;

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td>
            <div style="font-family: ${this.fontStack}; font-size: 12px; font-weight: 600; color: ${this.brandColors.dark}; margin-bottom: 8px;">
              Email Processing Breakdown
            </div>
            <!-- Stacked bar -->
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border-radius: 4px; overflow: hidden;">
              <tr>
                ${escPct > 0 ? `<td width="${escPct}%" style="background: ${this.brandColors.urgent}; height: 24px;"></td>` : ''}
                ${handledPct > 0 ? `<td width="${handledPct}%" style="background: ${this.brandColors.success}; height: 24px;"></td>` : ''}
                ${draftsPct > 0 ? `<td width="${draftsPct}%" style="background: ${this.brandColors.warning}; height: 24px;"></td>` : ''}
                ${flaggedPct > 0 ? `<td width="${flaggedPct}%" style="background: ${this.brandColors.medium}; height: 24px;"></td>` : ''}
              </tr>
            </table>
            <!-- Legend -->
            <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin-top: 8px;">
              <tr>
                <td style="padding-right: 16px;">
                  <span style="display: inline-block; width: 10px; height: 10px; background: ${this.brandColors.urgent}; border-radius: 2px; margin-right: 4px; vertical-align: middle;"></span>
                  <span style="font-family: ${this.fontStack}; font-size: 11px; color: ${this.brandColors.medium}; vertical-align: middle;">Escalated (${escalated})</span>
                </td>
                <td style="padding-right: 16px;">
                  <span style="display: inline-block; width: 10px; height: 10px; background: ${this.brandColors.success}; border-radius: 2px; margin-right: 4px; vertical-align: middle;"></span>
                  <span style="font-family: ${this.fontStack}; font-size: 11px; color: ${this.brandColors.medium}; vertical-align: middle;">Handled (${handled})</span>
                </td>
                <td style="padding-right: 16px;">
                  <span style="display: inline-block; width: 10px; height: 10px; background: ${this.brandColors.warning}; border-radius: 2px; margin-right: 4px; vertical-align: middle;"></span>
                  <span style="font-family: ${this.fontStack}; font-size: 11px; color: ${this.brandColors.medium}; vertical-align: middle;">Drafts (${drafts})</span>
                </td>
                <td>
                  <span style="display: inline-block; width: 10px; height: 10px; background: ${this.brandColors.medium}; border-radius: 2px; margin-right: 4px; vertical-align: middle;"></span>
                  <span style="font-family: ${this.fontStack}; font-size: 11px; color: ${this.brandColors.medium}; vertical-align: middle;">Flagged (${flagged})</span>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build progress bar
   */
  buildProgressBar(label, current, max, color) {
    const percentage = max > 0 ? Math.min(100, Math.round((current / max) * 100)) : 0;

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 8px 0;">
        <tr>
          <td width="80" style="font-family: ${this.fontStack}; font-size: 12px; color: ${this.brandColors.medium};">
            ${label}
          </td>
          <td style="padding: 0 12px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: ${this.brandColors.border}; border-radius: 4px;">
              <tr>
                <td width="${percentage}%" style="background: ${color}; height: 8px; border-radius: 4px;"></td>
                <td width="${100 - percentage}%"></td>
              </tr>
            </table>
          </td>
          <td width="50" style="text-align: right; font-family: ${this.fontStack}; font-size: 12px; font-weight: 600; color: ${this.brandColors.dark};">
            ${current}/${max}
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build action button (table-based for email compatibility)
   */
  buildActionButton(action, url, options = {}) {
    const buttonConfigs = {
      approve: { label: 'Approve', bg: this.brandColors.success, text: this.brandColors.white, icon: '&#10003;' },
      reject: { label: 'Reject', bg: this.brandColors.urgent, text: this.brandColors.white, icon: '&#10005;' },
      snooze: { label: 'Snooze', bg: this.brandColors.warning, text: this.brandColors.white, icon: '&#9716;' },
      view: { label: 'View', bg: 'transparent', text: this.brandColors.primary, border: this.brandColors.primary, icon: '&#8594;' },
      archive: { label: 'Archive', bg: this.brandColors.medium, text: this.brandColors.white, icon: '&#128193;' },
      gmail: { label: 'Open in Gmail', bg: 'transparent', text: this.brandColors.primary, border: this.brandColors.primary, icon: '&#9993;' }
    };

    const config = buttonConfigs[action] || buttonConfigs.view;
    const borderStyle = config.border ? `border: 1px solid ${config.border};` : '';
    const bgStyle = config.bg === 'transparent' ? '' : `background-color: ${config.bg};`;

    return `
      <td class="action-cell" style="padding-right: 8px;">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
          <tr>
            <td class="button-td" style="border-radius: 6px; ${bgStyle} ${borderStyle}">
              <a href="${url}" target="_blank" class="action-button" style="display: inline-block; padding: 10px 16px; font-family: ${this.fontStack}; font-size: 13px; font-weight: 600; color: ${config.text}; text-decoration: none; border-radius: 6px;">
                ${options.showIcon !== false ? config.icon + ' ' : ''}${options.label || config.label}
              </a>
            </td>
          </tr>
        </table>
      </td>
    `;
  }

  /**
   * Build email item card with action buttons
   */
  buildEmailItemWithActions(email, tier, actions = ['approve', 'reject', 'gmail']) {
    const tierConfigs = {
      1: { color: this.brandColors.urgent, bg: this.brandColors.urgentBg, label: 'URGENT' },
      2: { color: this.brandColors.success, bg: this.brandColors.successBg, label: 'HANDLED' },
      3: { color: this.brandColors.warning, bg: this.brandColors.warningBg, label: 'PENDING' },
      4: { color: this.brandColors.info, bg: this.brandColors.infoBg, label: 'FLAGGED' }
    };

    const config = tierConfigs[tier] || tierConfigs[3];

    // Generate action URLs with tokens
    const actionButtons = actions.map(action => {
      let url;
      if (action === 'gmail' || action === 'view') {
        url = this.getGmailLink(email.id);
      } else {
        url = this.tokenGenerator.generateActionUrl(this.actionBaseUrl, email.id, action, this.userEmail);
      }
      return this.buildActionButton(action, url);
    }).join('');

    return `
      <table role="presentation" class="email-item-table" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: ${this.brandColors.white}; border: 1px solid ${this.brandColors.border}; border-left: 4px solid ${config.color}; border-radius: 8px; margin-bottom: 12px;">
        <tr>
          <td style="padding: 16px;">
            <!-- Header -->
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
              <tr>
                <td style="vertical-align: top;">
                  <span style="display: inline-block; background: ${config.bg}; color: ${config.color}; padding: 3px 8px; border-radius: 4px; font-family: ${this.fontStack}; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                    ${config.label}
                  </span>
                  <div style="font-family: ${this.fontStack}; font-size: 14px; font-weight: 600; color: ${this.brandColors.dark}; margin-top: 8px;">
                    ${this.escapeHtml(email.from)}
                  </div>
                </td>
                <td style="text-align: right; vertical-align: top;">
                  <span style="font-family: ${this.fontStack}; font-size: 11px; color: ${this.brandColors.medium};">
                    ${this.formatTime(email.timestamp)}
                  </span>
                </td>
              </tr>
            </table>

            <!-- Subject -->
            <div style="font-family: ${this.fontStack}; font-size: 15px; font-weight: 500; color: ${this.brandColors.dark}; margin: 8px 0;">
              ${this.escapeHtml(email.subject)}
            </div>

            <!-- Preview -->
            <div style="font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.medium}; line-height: 1.5; margin-bottom: 16px;">
              ${this.escapeHtml((email.preview || email.snippet || '').substring(0, 140))}${(email.preview || email.snippet || '').length > 140 ? '...' : ''}
            </div>

            <!-- Action buttons -->
            <table role="presentation" cellspacing="0" cellpadding="0" border="0">
              <tr>
                ${actionButtons}
              </tr>
            </table>
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build CTA button
   */
  buildCTAButton(button) {
    const bgColor = button.color || this.brandColors.primary;

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-top: 24px;">
        <tr>
          <td align="center">
            <table role="presentation" cellspacing="0" cellpadding="0" border="0">
              <tr>
                <td style="border-radius: 8px; background: ${bgColor};">
                  <a href="${button.url}" target="_blank" style="display: inline-block; padding: 14px 28px; font-family: ${this.fontStack}; font-size: 16px; font-weight: 600; color: ${this.brandColors.white}; text-decoration: none; border-radius: 8px;">
                    ${button.text}
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build footer
   */
  buildFooter() {
    return `
      <tr>
        <td style="background: ${this.brandColors.light}; padding: 24px; border-top: 1px solid ${this.brandColors.border};">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
            <tr>
              <td align="center">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                  <tr>
                    <td style="padding: 0 12px;">
                      <a href="${this.dashboardUrl}" style="font-family: ${this.fontStack}; font-size: 13px; font-weight: 500; color: ${this.brandColors.primary}; text-decoration: none;">Dashboard</a>
                    </td>
                    <td style="padding: 0 12px;">
                      <a href="${this.dashboardUrl}/settings" style="font-family: ${this.fontStack}; font-size: 13px; font-weight: 500; color: ${this.brandColors.primary}; text-decoration: none;">Settings</a>
                    </td>
                    <td style="padding: 0 12px;">
                      <a href="${this.dashboardUrl}/analytics" style="font-family: ${this.fontStack}; font-size: 13px; font-weight: 500; color: ${this.brandColors.primary}; text-decoration: none;">Analytics</a>
                    </td>
                    <td style="padding: 0 12px;">
                      <a href="${this.dashboardUrl}/help" style="font-family: ${this.fontStack}; font-size: 13px; font-weight: 500; color: ${this.brandColors.primary}; text-decoration: none;">Help</a>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td align="center" style="padding-top: 16px;">
                <p style="font-family: ${this.fontStack}; font-size: 12px; color: ${this.brandColors.medium}; margin: 0;">
                  Powered by Email Assistant AI &bull; ${new Date().toLocaleDateString()}
                </p>
                <p style="font-family: ${this.fontStack}; font-size: 11px; margin: 8px 0 0 0;">
                  <a href="${this.dashboardUrl}/unsubscribe" style="color: ${this.brandColors.medium}; text-decoration: underline;">Manage Notifications</a>
                </p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    `;
  }

  // ==========================================
  // SECTION BUILDERS
  // ==========================================

  /**
   * Build urgent section
   */
  buildUrgentSection(escalations) {
    if (!escalations || escalations.length === 0) return '';

    const items = escalations.slice(0, 5).map(email =>
      this.buildEmailItemWithActions(email, 1, ['gmail'])
    ).join('');

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td>
            <h2 style="font-family: ${this.fontStack}; font-size: 16px; font-weight: 600; color: ${this.brandColors.dark}; margin: 0 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid ${this.brandColors.light};">
              &#128680; Urgent Items (${escalations.length})
            </h2>
            ${items}
            ${escalations.length > 5 ? `
              <p style="text-align: center; margin: 16px 0 0 0;">
                <a href="${this.dashboardUrl}/urgent" style="font-family: ${this.fontStack}; font-size: 14px; color: ${this.brandColors.primary}; text-decoration: none;">
                  View all ${escalations.length} urgent items &rarr;
                </a>
              </p>
            ` : ''}
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build pending approvals section
   */
  buildPendingApprovalsSection(pending) {
    if (!pending || pending.length === 0) return '';

    const items = pending.slice(0, 5).map(email =>
      this.buildEmailItemWithActions(email, 3, ['approve', 'reject', 'gmail'])
    ).join('');

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td>
            <h2 style="font-family: ${this.fontStack}; font-size: 16px; font-weight: 600; color: ${this.brandColors.dark}; margin: 0 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid ${this.brandColors.light};">
              &#9993; Pending Your Approval (${pending.length})
            </h2>
            ${items}
            ${pending.length > 5 ? `
              <p style="text-align: center; margin: 16px 0 0 0;">
                <a href="${this.dashboardUrl}/pending" style="font-family: ${this.fontStack}; font-size: 14px; color: ${this.brandColors.primary}; text-decoration: none;">
                  Review all ${pending.length} pending items &rarr;
                </a>
              </p>
            ` : ''}
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build overnight summary
   */
  buildOvernightSummary(overnight) {
    if (!overnight || Object.keys(overnight).length === 0) return '';

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td style="background: ${this.brandColors.light}; border-radius: 8px; padding: 16px;">
            <h2 style="font-family: ${this.fontStack}; font-size: 14px; font-weight: 600; color: ${this.brandColors.dark}; margin: 0 0 12px 0;">
              &#127769; Overnight Activity
            </h2>
            ${this.buildProgressBar('Received', overnight.totalEmails || 0, overnight.totalEmails || 1, this.brandColors.primary)}
            ${this.buildProgressBar('Handled', overnight.handled || 0, overnight.totalEmails || 1, this.brandColors.success)}
            ${this.buildProgressBar('Escalated', overnight.escalations || 0, overnight.totalEmails || 1, this.brandColors.urgent)}
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build handled section (collapsed)
   */
  buildHandledSection(handled) {
    if (!handled || handled.length === 0) return '';

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td style="background: ${this.brandColors.successBg}; border: 1px solid ${this.brandColors.success}; border-radius: 8px; padding: 16px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
              <tr>
                <td>
                  <span style="font-family: ${this.fontStack}; font-size: 14px; font-weight: 600; color: ${this.brandColors.success};">
                    &#10003; ${handled.length} emails auto-handled
                  </span>
                </td>
                <td style="text-align: right;">
                  <a href="${this.dashboardUrl}/handled" style="font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.success}; text-decoration: none;">
                    View details &rarr;
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build agent activity section
   */
  buildAgentActivitySection(agentActivity) {
    if (!agentActivity || agentActivity.processed === 0) return '';

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td style="background: linear-gradient(135deg, ${this.brandColors.primaryBg} 0%, #cffafe 100%); border-radius: 8px; padding: 16px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
              <tr>
                <td width="40" style="vertical-align: top;">
                  <div style="width: 32px; height: 32px; background: ${this.brandColors.primary}; border-radius: 8px; text-align: center; line-height: 32px; font-size: 18px;">
                    &#129302;
                  </div>
                </td>
                <td style="padding-left: 12px; vertical-align: top;">
                  <div style="font-family: ${this.fontStack}; font-size: 14px; font-weight: 600; color: ${this.brandColors.dark};">
                    Email Agent Activity
                  </div>
                  <div style="font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.medium}; margin-top: 4px;">
                    Processed ${agentActivity.processed || 0} emails autonomously
                    ${agentActivity.tasksCompleted ? ` &bull; ${agentActivity.tasksCompleted} tasks completed` : ''}
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build actions table
   */
  buildActionsTable(actions) {
    if (!actions || actions.length === 0) return '';

    const rows = actions.slice(0, 8).map(action => {
      const badgeColors = {
        escalated: { bg: this.brandColors.urgentBg, text: this.brandColors.urgent },
        handled: { bg: this.brandColors.successBg, text: this.brandColors.success },
        drafted: { bg: this.brandColors.warningBg, text: this.brandColors.warning },
        archived: { bg: this.brandColors.infoBg, text: this.brandColors.info }
      };
      const badge = badgeColors[action.type] || badgeColors.archived;

      return `
        <tr>
          <td style="padding: 10px 8px; border-bottom: 1px solid ${this.brandColors.border}; font-family: ${this.fontStack}; font-size: 12px; color: ${this.brandColors.medium};">
            ${this.formatTime(action.timestamp)}
          </td>
          <td style="padding: 10px 8px; border-bottom: 1px solid ${this.brandColors.border}; font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.dark};">
            ${this.escapeHtml(action.subject || 'No subject').substring(0, 40)}${(action.subject || '').length > 40 ? '...' : ''}
          </td>
          <td style="padding: 10px 8px; border-bottom: 1px solid ${this.brandColors.border};">
            <span style="display: inline-block; background: ${badge.bg}; color: ${badge.text}; padding: 2px 8px; border-radius: 4px; font-family: ${this.fontStack}; font-size: 10px; font-weight: 600; text-transform: uppercase;">
              ${action.type}
            </span>
          </td>
          <td style="padding: 10px 8px; border-bottom: 1px solid ${this.brandColors.border}; text-align: center;">
            <a href="${this.getGmailLink(action.emailId)}" style="font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.primary}; text-decoration: none;">View</a>
          </td>
        </tr>
      `;
    }).join('');

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td>
            <h2 style="font-family: ${this.fontStack}; font-size: 16px; font-weight: 600; color: ${this.brandColors.dark}; margin: 0 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid ${this.brandColors.light};">
              &#128221; Today's Actions
            </h2>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
              <tr style="background: ${this.brandColors.light};">
                <th style="padding: 10px 8px; text-align: left; font-family: ${this.fontStack}; font-size: 11px; font-weight: 600; text-transform: uppercase; color: ${this.brandColors.medium};">Time</th>
                <th style="padding: 10px 8px; text-align: left; font-family: ${this.fontStack}; font-size: 11px; font-weight: 600; text-transform: uppercase; color: ${this.brandColors.medium};">Email</th>
                <th style="padding: 10px 8px; text-align: left; font-family: ${this.fontStack}; font-size: 11px; font-weight: 600; text-transform: uppercase; color: ${this.brandColors.medium};">Action</th>
                <th style="padding: 10px 8px; text-align: center; font-family: ${this.fontStack}; font-size: 11px; font-weight: 600; text-transform: uppercase; color: ${this.brandColors.medium};">Link</th>
              </tr>
              ${rows}
            </table>
            ${actions.length > 8 ? `
              <p style="text-align: center; margin: 16px 0 0 0;">
                <a href="${this.dashboardUrl}/actions" style="font-family: ${this.fontStack}; font-size: 14px; color: ${this.brandColors.primary}; text-decoration: none;">
                  View all ${actions.length} actions &rarr;
                </a>
              </p>
            ` : ''}
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build cost summary row (compact)
   */
  buildCostSummaryRow(costs) {
    if (!costs || costs.total === undefined) return '';

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td style="background: ${this.brandColors.light}; border-radius: 8px; padding: 16px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
              <tr>
                <td>
                  <span style="font-family: ${this.fontStack}; font-size: 14px; font-weight: 600; color: ${this.brandColors.dark};">
                    &#128176; Daily Cost: $${costs.total.toFixed(2)}
                  </span>
                  <span style="font-family: ${this.fontStack}; font-size: 12px; color: ${this.brandColors.medium}; margin-left: 12px;">
                    Monthly projection: $${(costs.total * 30).toFixed(2)}
                  </span>
                </td>
                <td style="text-align: right;">
                  <a href="${this.dashboardUrl}/analytics/costs" style="font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.primary}; text-decoration: none;">
                    Details &rarr;
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build tomorrow section
   */
  buildTomorrowSection(pendingForTomorrow) {
    if (!pendingForTomorrow || pendingForTomorrow.length === 0) return '';

    const items = pendingForTomorrow.slice(0, 4).map(item => `
      <tr>
        <td style="padding: 8px 0; border-bottom: 1px solid ${this.brandColors.border};">
          <div style="font-family: ${this.fontStack}; font-size: 13px; font-weight: 500; color: ${this.brandColors.dark};">
            ${this.escapeHtml(item.subject)}
          </div>
          <div style="font-family: ${this.fontStack}; font-size: 12px; color: ${this.brandColors.medium}; margin-top: 2px;">
            from ${this.escapeHtml(item.from)}
            ${item.followUpDate ? ` &bull; Follow up: ${this.formatDate(item.followUpDate)}` : ''}
          </div>
        </td>
      </tr>
    `).join('');

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td>
            <h2 style="font-family: ${this.fontStack}; font-size: 16px; font-weight: 600; color: ${this.brandColors.dark}; margin: 0 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid ${this.brandColors.light};">
              &#128197; Pending for Tomorrow (${pendingForTomorrow.length})
            </h2>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
              ${items}
            </table>
            ${pendingForTomorrow.length > 4 ? `
              <p style="margin: 12px 0 0 0;">
                <a href="${this.dashboardUrl}/tomorrow" style="font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.primary}; text-decoration: none;">
                  View all ${pendingForTomorrow.length} items &rarr;
                </a>
              </p>
            ` : ''}
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build insights section
   */
  buildInsightsSection(insights) {
    if (!insights || insights.length === 0) return '';

    const insightIcons = {
      performance: '&#9889;',
      cost: '&#128176;',
      pattern: '&#128200;',
      recommendation: '&#128161;',
      warning: '&#9888;',
      success: '&#10003;',
      info: '&#8505;'
    };

    const items = insights.slice(0, 4).map(insight => `
      <tr>
        <td width="24" style="vertical-align: top; padding: 8px 0;">
          <span style="font-size: 14px;">${insightIcons[insight.type] || insightIcons.info}</span>
        </td>
        <td style="vertical-align: top; padding: 8px 0 8px 8px;">
          <div style="font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.dark};">
            ${this.escapeHtml(insight.message)}
          </div>
          ${insight.action ? `
            <a href="${insight.actionUrl || this.dashboardUrl}" style="font-family: ${this.fontStack}; font-size: 12px; color: ${this.brandColors.primary}; text-decoration: none;">
              ${insight.action} &rarr;
            </a>
          ` : ''}
        </td>
      </tr>
    `).join('');

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td>
            <h2 style="font-family: ${this.fontStack}; font-size: 16px; font-weight: 600; color: ${this.brandColors.dark}; margin: 0 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid ${this.brandColors.light};">
              &#128161; Insights & Recommendations
            </h2>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background: linear-gradient(135deg, ${this.brandColors.infoBg} 0%, #dbeafe 100%); border-radius: 8px; padding: 12px;">
              ${items}
            </table>
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build top senders section
   */
  buildTopSendersSection(topSenders) {
    if (!topSenders || topSenders.length === 0) return '';

    const rows = topSenders.slice(0, 5).map((sender, index) => `
      <tr>
        <td style="padding: 10px 8px; border-bottom: 1px solid ${this.brandColors.border}; font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.medium};">
          ${index + 1}
        </td>
        <td style="padding: 10px 8px; border-bottom: 1px solid ${this.brandColors.border}; font-family: ${this.fontStack}; font-size: 13px; color: ${this.brandColors.dark};">
          ${this.escapeHtml(sender.email)}
        </td>
        <td style="padding: 10px 8px; border-bottom: 1px solid ${this.brandColors.border}; text-align: center; font-family: ${this.fontStack}; font-size: 13px; font-weight: 600; color: ${this.brandColors.dark};">
          ${sender.count}
        </td>
        <td style="padding: 10px 8px; border-bottom: 1px solid ${this.brandColors.border}; text-align: center;">
          <span style="display: inline-block; background: ${this.brandColors.infoBg}; color: ${this.brandColors.info}; padding: 2px 8px; border-radius: 4px; font-family: ${this.fontStack}; font-size: 10px; font-weight: 600;">
            ${sender.averageTier || 'N/A'}
          </span>
        </td>
      </tr>
    `).join('');

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
          <td>
            <h2 style="font-family: ${this.fontStack}; font-size: 16px; font-weight: 600; color: ${this.brandColors.dark}; margin: 0 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid ${this.brandColors.light};">
              &#128101; Top Senders Today
            </h2>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
              <tr style="background: ${this.brandColors.light};">
                <th style="padding: 10px 8px; text-align: left; font-family: ${this.fontStack}; font-size: 11px; font-weight: 600; text-transform: uppercase; color: ${this.brandColors.medium};">#</th>
                <th style="padding: 10px 8px; text-align: left; font-family: ${this.fontStack}; font-size: 11px; font-weight: 600; text-transform: uppercase; color: ${this.brandColors.medium};">Sender</th>
                <th style="padding: 10px 8px; text-align: center; font-family: ${this.fontStack}; font-size: 11px; font-weight: 600; text-transform: uppercase; color: ${this.brandColors.medium};">Emails</th>
                <th style="padding: 10px 8px; text-align: center; font-family: ${this.fontStack}; font-size: 11px; font-weight: 600; text-transform: uppercase; color: ${this.brandColors.medium};">Avg Tier</th>
              </tr>
              ${rows}
            </table>
          </td>
        </tr>
      </table>
    `;
  }

  /**
   * Build urgent alert section (for midday alerts)
   */
  buildUrgentAlertSection(urgentItems) {
    const items = urgentItems.slice(0, 3).map(email =>
      this.buildEmailItemWithActions(email, 1, ['gmail'])
    ).join('');

    return `
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
          <td>
            ${items}
          </td>
        </tr>
      </table>
    `;
  }

  // ==========================================
  // UTILITY METHODS
  // ==========================================

  /**
   * Generate Gmail deep link
   */
  getGmailLink(emailId) {
    return `https://mail.google.com/mail/u/0/#inbox/${emailId}`;
  }

  /**
   * Get greeting based on time of day
   */
  getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  /**
   * Format time (relative)
   */
  formatTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return date.toLocaleDateString();
  }

  /**
   * Format date
   */
  formatDate(date) {
    if (!date) return '';
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: new Date(date).getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
    });
  }

  /**
   * Escape HTML
   */
  escapeHtml(text) {
    if (!text) return '';
    const map = {
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
  }

  /**
   * Generate plain text version
   */
  generatePlainText(data, type) {
    let text = '';

    if (type === 'morning') {
      text = `MORNING EMAIL BRIEF\n`;
      text += `==================\n\n`;

      if (data.tier1Escalations && data.tier1Escalations.length > 0) {
        text += `URGENT ITEMS (${data.tier1Escalations.length}):\n`;
        data.tier1Escalations.forEach(item => {
          text += `  - ${item.subject} from ${item.from}\n`;
        });
        text += `\n`;
      }

      if (data.tier3Pending && data.tier3Pending.length > 0) {
        text += `PENDING APPROVAL (${data.tier3Pending.length}):\n`;
        data.tier3Pending.forEach(item => {
          text += `  - ${item.subject} from ${item.from}\n`;
        });
        text += `\n`;
      }

      if (data.tier2Handled && data.tier2Handled.length > 0) {
        text += `AUTO-HANDLED: ${data.tier2Handled.length} emails\n\n`;
      }
    } else if (type === 'eod') {
      text = `END OF DAY REPORT\n`;
      text += `=================\n\n`;

      if (data.todayStats) {
        text += `TODAY'S STATS:\n`;
        text += `  - Emails Processed: ${data.todayStats.totalProcessed || 0}\n`;
        text += `  - Escalations: ${data.todayStats.escalations || 0}\n`;
        text += `  - Auto-Handled: ${data.todayStats.handled || 0}\n`;
        text += `  - Drafts Created: ${data.todayStats.drafts || 0}\n`;
        text += `\n`;
      }

      if (data.costs) {
        text += `COSTS:\n`;
        text += `  - Daily Total: $${data.costs.total?.toFixed(2) || '0.00'}\n`;
        text += `  - Monthly Projection: $${((data.costs.total || 0) * 30).toFixed(2)}\n`;
        text += `\n`;
      }

      if (data.pendingForTomorrow && data.pendingForTomorrow.length > 0) {
        text += `PENDING FOR TOMORROW (${data.pendingForTomorrow.length}):\n`;
        data.pendingForTomorrow.slice(0, 5).forEach(item => {
          text += `  - ${item.subject} from ${item.from}\n`;
        });
        text += `\n`;
      }
    }

    text += `\nView full dashboard: ${this.dashboardUrl}\n`;

    return text;
  }
}

module.exports = EmailSummaryGenerator;
