/**
 * Configuration for Daily Todoist Reviewer
 */
export default {
  // System enabled flag
  enabled: true,

  // Schedule configuration
  schedule: {
    timezone: 'America/New_York',
    dailyTime: '05:00',  // 5 AM EST
    skipSaturday: true,  // No report on Saturdays
    skipSunday: false
  },

  // Todoist filtering options
  todoist: {
    filters: {
      // Priority levels to include (Todoist: p1=urgent, p2=high, p3=medium, p4=low)
      // In API: priority 4=urgent, 3=high, 2=medium, 1=low
      priorities: ['p2', 'p3', 'p4'],

      // Timeframes to fetch
      timeframes: ['today', 'overdue', '7 days'],

      // Optional: Only include specific projects (leave empty for all)
      projects: [],

      // Labels to exclude from review
      excludeLabels: ['waiting', 'someday', 'delegated']
    }
  },

  // AI Analysis configuration
  ai: {
    // Analysis depth: 'quick' | 'detailed' | 'comprehensive'
    analysisDepth: 'detailed',

    // Enable specific AI features
    enableTaskSuggestions: true,
    enableTimeEstimation: true,
    enableTaskBreakdown: true,
    enableAutonomousIdentification: true,

    // Task categories for classification
    // Categories marked with cometBrowserTask: true are ideal for Perplexity Comet browser
    categories: [
      { id: 'research', name: 'Research & Information', aiCanHelp: true, cometBrowserTask: true },
      { id: 'webSearch', name: 'Web Search & Lookup', aiCanHelp: true, cometBrowserTask: true },
      { id: 'priceComparison', name: 'Price & Product Comparison', aiCanHelp: true, cometBrowserTask: true },
      { id: 'booking', name: 'Booking & Reservations', aiCanHelp: true, cometBrowserTask: true },
      { id: 'factCheck', name: 'Fact Checking & Verification', aiCanHelp: true, cometBrowserTask: true },
      { id: 'shopping', name: 'Online Shopping & Orders', aiCanHelp: true, cometBrowserTask: true },
      { id: 'formFilling', name: 'Form Filling & Applications', aiCanHelp: true, cometBrowserTask: true },
      { id: 'communication', name: 'Communication & Email', aiCanHelp: true, cometBrowserTask: false },
      { id: 'coding', name: 'Code & Technical', aiCanHelp: true, cometBrowserTask: false },
      { id: 'writing', name: 'Writing & Content', aiCanHelp: true, cometBrowserTask: false },
      { id: 'admin', name: 'Administrative', aiCanHelp: true, cometBrowserTask: true },
      { id: 'planning', name: 'Planning & Strategy', aiCanHelp: true, cometBrowserTask: false },
      { id: 'review', name: 'Review & Analysis', aiCanHelp: true, cometBrowserTask: true },
      { id: 'creative', name: 'Creative & Design', aiCanHelp: false, cometBrowserTask: false },
      { id: 'meeting', name: 'Meetings & Calls', aiCanHelp: false, cometBrowserTask: false },
      { id: 'physical', name: 'Physical Tasks', aiCanHelp: false, cometBrowserTask: false },
      { id: 'personal', name: 'Personal & Private', aiCanHelp: false, cometBrowserTask: false }
    ],

    // Perplexity Comet browser configuration
    cometBrowser: {
      enabled: true,

      // Task types that Comet browser excels at
      capabilities: [
        'real-time web search and research',
        'price and product comparison across websites',
        'booking appointments, reservations, and tickets',
        'fact-checking and verification',
        'form filling and online applications',
        'finding contact information and business details',
        'comparing services and reading reviews',
        'tracking shipments and orders',
        'finding best deals and coupons'
      ],

      // Highlight these tasks specially in reports
      highlightInReport: true,

      // Categories enabled for Comet detection
      enabledCategories: [
        'travelBooking',
        'priceComparison',
        'webResearch',
        'dataExtraction',
        'onlineAccountMgmt',
        'formFilling',
        'contentSummarization',
        'comparativeAnalysis'
      ],

      // Minimum confidence threshold for showing Comet suggestions
      minConfidence: 0.5,

      // Maximum Comet tasks to show in dedicated section
      maxDisplayed: 5,

      // Show Comet badge on tasks in other sections
      showBadges: true,

      // Show dedicated Comet section in report
      showSection: true
    }
  },

  // Email configuration
  email: {
    // Recipient (can be overridden by env var)
    recipient: process.env.TODOIST_REVIEW_EMAIL || process.env.USER_EMAIL,

    // Email subject template
    subjectTemplate: 'Daily Task Review - {date}',

    // Include sections in email
    sections: {
      summary: true,
      highPriority: true,
      aiAssistable: true,
      overdue: true,
      upcomingWeek: true,
      quickActions: true,
      metrics: true
    },

    // Visual theme: 'modern' | 'minimal' | 'colorful'
    theme: 'modern'
  },

  // Autonomous action configuration (Phase 2)
  automation: {
    enabled: false,

    // Actions that can be performed automatically
    autoApprove: [
      'research',
      'data_gathering',
      'draft_generation'
    ],

    // Actions requiring user approval
    requireApproval: [
      'email_sending',
      'task_modification',
      'calendar_changes'
    ],

    // Safety limits
    limits: {
      maxAutoActions: 5,
      maxEmailDrafts: 3,
      requireConfirmationAbove: 'medium' // priority threshold
    }
  },

  // Logging configuration
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    includeTimestamp: true
  },

  // Local execution configuration (Claude Code CLI)
  localExecution: {
    // Use Claude CLI for AI analysis (requires Claude Code subscription)
    useClaudeCLI: process.env.USE_CLAUDE_CLI !== 'false',

    // Fallback to pattern matching if Claude CLI fails
    fallbackToPatterns: true,

    // Claude CLI command (usually just 'claude')
    claudeCommand: process.env.CLAUDE_COMMAND || 'claude',

    // Timeout for Claude CLI calls (ms)
    claudeTimeout: parseInt(process.env.CLAUDE_TIMEOUT || '120000', 10),

    // Enable email reply polling
    enableReplyPolling: process.env.ENABLE_REPLY_POLLING !== 'false',

    // Poll interval for email replies (ms) - default 5 minutes
    pollIntervalMs: parseInt(process.env.POLL_INTERVAL_MS || '300000', 10),

    // Data directory for task mappings and processed messages
    dataDir: process.env.DATA_DIR || './data'
  }
};
