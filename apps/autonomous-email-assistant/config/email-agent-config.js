/**
 * Email Agent Configuration
 * Configure the autonomous email agent with reasoning and tools
 */

module.exports = {
  // Agent email address (must be set up and monitored)
  agentEmail: process.env.AGENT_EMAIL || 'assistant@yourdomain.com',

  // OpenRouter API configuration
  openRouter: {
    apiKey: process.env.OPENROUTER_API_KEY,

    // Reasoning models available on OpenRouter
    reasoningModel: process.env.REASONING_MODEL || 'deepseek/deepseek-r1',

    // Alternative reasoning models:
    // - 'openai/o1' - OpenAI o1 (most advanced)
    // - 'openai/o1-mini' - OpenAI o1 mini (faster, cheaper)
    // - 'deepseek/deepseek-r1' - DeepSeek R1 (excellent reasoning, open)
    // - 'google/gemini-2.0-flash-thinking-exp' - Gemini 2.0 with thinking

    fallbackModel: 'anthropic/claude-3.5-sonnet', // If reasoning model fails

    // Smart model selection (cost optimization)
    smartModels: {
      enabled: process.env.SMART_MODELS !== 'false', // Enable by default
      simple: 'google/gemini-2.0-flash-thinking-exp:free', // $0.0005/call
      standard: 'deepseek/deepseek-chat', // $0.001/call
      complex: 'deepseek/deepseek-r1', // $0.002/call
    },
  },

  // Safety settings
  safety: {
    enabled: true,

    // Require approval for these action types
    requireApproval: [
      'financial_transaction',
      'delete_data',
      'send_bulk_email',
      'external_api_call'
    ],

    // Auto-approve these patterns (case-insensitive)
    autoApprove: [
      'check status',
      'get information',
      'search for',
      'find emails about'
    ],

    // Blocked domains for web automation
    blockedDomains: [
      'bank.com',
      'paypal.com',
      'credit-card-processor.com'
    ],

    // Maximum actions per email
    maxActionsPerEmail: 10,

    // Maximum web automation steps
    maxPlaywrightSteps: 20
  },

  // Tool configuration
  tools: {
    playwright: {
      enabled: true,
      headless: true,
      timeout: 30000,
      // Allowed domains for automation (empty = all allowed unless blocked)
      allowedDomains: [],
      // Screenshot on error
      screenshotOnError: true
    },

    calendar: {
      enabled: true,
      provider: 'google', // or 'microsoft', 'apple'
      timezone: 'America/New_York'
    },

    data: {
      enabled: true,
      // Maximum data size to process (in bytes)
      maxDataSize: 10 * 1024 * 1024 // 10MB
    }
  },

  // Email monitoring settings
  monitoring: {
    // How often to check for new emails (milliseconds)
    pollInterval: 60000, // 1 minute

    // Process emails older than this (milliseconds)
    processOlderThan: 0, // Process immediately

    // Maximum emails to process per cycle
    maxEmailsPerCycle: 10
  },

  // Response settings
  response: {
    // Include reasoning in response
    includeReasoning: true,

    // Include action details
    includeActionDetails: true,

    // Response signature
    signature: '\n\nBest regards,\nYour Email Assistant',

    // Send confirmation for auto-approved actions
    confirmAutoApproved: true
  },

  // Logging
  logging: {
    level: process.env.LOG_LEVEL || 'info',
    logActions: true,
    logReasoning: true
  },

  // Advanced settings
  advanced: {
    // Use conversation context from thread
    useThreadContext: true,

    // Maximum thread context length
    maxContextLength: 10000,

    // Retry failed actions
    retryFailedActions: true,
    maxRetries: 3,

    // Cache reasoning results
    cacheReasoning: true,
    cacheDuration: 3600000 // 1 hour
  }
};
