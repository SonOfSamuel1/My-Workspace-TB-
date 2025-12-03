/**
 * Comet Analyzer - Identifies tasks delegable to Perplexity Comet browser
 *
 * Perplexity Comet is an AI-powered browser that can:
 * - Navigate websites and fill forms
 * - Book travel (flights, hotels, rentals)
 * - Compare prices across shopping sites
 * - Extract data from websites
 * - Summarize web content
 * - Manage online accounts
 * - Research across multiple sources
 */

import config from '../config/reviewer-config.js';

/**
 * Comet-delegable task patterns with keywords, capabilities, and prompt templates
 */
const COMET_DELEGABLE_PATTERNS = {
  travelBooking: {
    keywords: [
      'book flight', 'book hotel', 'reserve hotel', 'flight booking', 'hotel reservation',
      'car rental', 'rent a car', 'airbnb', 'travel booking', 'vacation booking',
      'find flights', 'search hotels', 'travel itinerary', 'book accommodation',
      'book trip', 'reserve flight', 'book vacation', 'flight to', 'hotel in'
    ],
    name: 'Travel Booking',
    description: 'Travel booking and reservations',
    cometCapability: 'Flight/hotel/travel booking across multiple sites',
    promptTemplate: (task) => {
      const desc = task.description ? ` Additional details: ${task.description}` : '';
      return `Help me with this travel task: "${task.content}".${desc} Search across multiple booking sites (Google Flights, Kayak, Expedia, Booking.com) to find the best options. Compare prices and present the top 3 choices before I book.`;
    },
    examplePrompts: [
      'Search for round-trip flights from JFK to LAX for Dec 15-22, compare prices across Google Flights, Kayak, and Skyscanner',
      'Find hotels near downtown Seattle for 3 nights starting Jan 5, budget under $200/night',
      'Book a rental car at SFO airport for next weekend, economy class preferred'
    ],
    estimatedTime: 45
  },

  priceComparison: {
    keywords: [
      'compare prices', 'find best price', 'price check', 'cheapest', 'best deal',
      'shop for', 'find lowest', 'price comparison', 'best value', 'compare options',
      'find discounts', 'coupon', 'deals on', 'best price for', 'where to buy'
    ],
    name: 'Price Compare',
    description: 'Price comparison shopping',
    cometCapability: 'Cross-site price comparison and deal finding',
    promptTemplate: (task) => {
      const desc = task.description ? ` Requirements: ${task.description}` : '';
      return `Compare prices for: "${task.content}".${desc} Search across multiple retailers (Amazon, Best Buy, Walmart, Target, and specialty stores). Present a comparison table with prices, availability, ratings, and direct links to buy.`;
    },
    examplePrompts: [
      'Compare prices for Sony WH-1000XM5 headphones across Amazon, Best Buy, and Walmart',
      'Find the best deal on a 65-inch OLED TV, compare at least 5 retailers',
      'Search for laptop deals under $1000 with at least 16GB RAM'
    ],
    estimatedTime: 20
  },

  webResearch: {
    keywords: [
      'research online', 'find information about', 'look up online', 'search for',
      'investigate online', 'gather information', 'find reviews', 'compare reviews',
      'read about', 'find articles', 'search web', 'online research', 'google',
      'find out about', 'learn about online', 'check reviews', 'research best',
      'research top', 'look up', 'find best', 'find top'
    ],
    name: 'Web Research',
    description: 'Multi-source web research',
    cometCapability: 'Research across multiple web sources with summarization',
    promptTemplate: (task) => {
      const desc = task.description ? ` Focus on: ${task.description}` : '';
      return `Research this topic: "${task.content}".${desc} Browse multiple authoritative sources, compare different perspectives, and compile your findings. Provide a comprehensive summary with key insights and source links.`;
    },
    examplePrompts: [
      'Research the top 5 project management tools for small teams, compare features and pricing',
      'Find and summarize recent reviews of the new iPhone model from tech publications',
      'Research best practices for remote team management from multiple business sites'
    ],
    estimatedTime: 30
  },

  dataExtraction: {
    keywords: [
      'extract data', 'scrape', 'pull data from', 'get data from', 'download list',
      'export to spreadsheet', 'collect from website', 'gather data', 'extract list',
      'compile list from', 'get prices from', 'extract information from website',
      'extract from', 'pull from website', 'get from website', 'scrape data',
      'extract pricing', 'extract competitor'
    ],
    name: 'Data Extract',
    description: 'Website data extraction to spreadsheet',
    cometCapability: 'Extract data from websites into structured formats',
    promptTemplate: (task) => {
      const desc = task.description ? ` Data format: ${task.description}` : '';
      return `Extract data: "${task.content}".${desc} Navigate to the relevant websites and extract the requested information. Organize the data into a clean, structured table format that can be copied into a spreadsheet.`;
    },
    examplePrompts: [
      'Extract the list of Fortune 500 companies with their revenue and CEO names',
      'Pull all product names and prices from the first 3 pages of this category',
      'Compile a list of conference speakers from the event website with their companies'
    ],
    estimatedTime: 25
  },

  onlineAccountMgmt: {
    keywords: [
      'update account', 'change password', 'update profile', 'subscription',
      'cancel subscription', 'update settings', 'account settings', 'manage account',
      'update payment', 'renew subscription', 'upgrade plan', 'update billing',
      'unsubscribe', 'cancel service', 'manage subscription'
    ],
    name: 'Account Mgmt',
    description: 'Online account and subscription management',
    cometCapability: 'Navigate account settings and manage subscriptions',
    promptTemplate: (task) => {
      const desc = task.description ? ` Details: ${task.description}` : '';
      return `Manage account: "${task.content}".${desc} Navigate to the account settings page and help me complete this account management task. Walk me through the steps and confirm when the changes are applied.`;
    },
    examplePrompts: [
      'Update my Netflix subscription to the premium plan',
      'Navigate to my Amazon account and update the default shipping address',
      'Cancel my Spotify subscription and confirm the cancellation date'
    ],
    estimatedTime: 15
  },

  formFilling: {
    keywords: [
      'fill out form', 'submit application', 'complete registration', 'sign up for',
      'register for', 'apply online', 'fill application', 'online form',
      'submit request', 'complete form', 'fill in', 'application form', 'signup',
      'registration form', 'fill out', 'submit form', 'application online'
    ],
    name: 'Form Fill',
    description: 'Web form completion and submission',
    cometCapability: 'Navigate and complete web forms',
    promptTemplate: (task) => {
      const desc = task.description ? ` Form details: ${task.description}` : '';
      return `Fill out form: "${task.content}".${desc} Navigate to the website and help me complete the form. Guide me through each section and let me review before submitting.`;
    },
    examplePrompts: [
      'Complete the warranty registration form for my new appliance',
      'Fill out the conference registration form with my details',
      'Submit a support ticket on the vendor website describing the issue'
    ],
    estimatedTime: 20
  },

  contentSummarization: {
    keywords: [
      'summarize article', 'summarize page', 'read and summarize', 'get summary of',
      'summarize website', 'extract key points', 'summarize document', 'tldr',
      'summary of', 'key takeaways from', 'summarize this', 'read this article',
      'summarize the', 'summarize', 'read the', 'review the page'
    ],
    name: 'Summarize',
    description: 'Web content summarization',
    cometCapability: 'Read and summarize web page content',
    promptTemplate: (task) => {
      const desc = task.description ? ` Focus on: ${task.description}` : '';
      // Check if task contains URL
      const urlMatch = (task.content + ' ' + (task.description || '')).match(/https?:\/\/[^\s]+/);
      if (urlMatch) {
        return `Visit ${urlMatch[0]} and summarize the key points.${desc} Extract the main ideas, important details, and any action items. Present a concise summary I can quickly review.`;
      }
      return `Find and summarize content about: "${task.content}".${desc} Locate the relevant page(s), read the content, and create a concise summary with key points and any actionable items.`;
    },
    examplePrompts: [
      'Summarize the main points from this 10-page terms of service document',
      'Read this research paper and extract the key findings',
      'Summarize the product features from the landing page into bullet points'
    ],
    estimatedTime: 15
  },

  comparativeAnalysis: {
    keywords: [
      'compare', 'versus', 'vs', 'vs.', 'comparison between', 'which is better',
      'pros and cons', 'compare features', 'evaluate options', 'side by side',
      'compare alternatives', 'benchmark', 'difference between', 'which should i'
    ],
    name: 'Compare',
    description: 'Cross-website comparative analysis',
    cometCapability: 'Comparative analysis across multiple websites',
    promptTemplate: (task) => {
      const desc = task.description ? ` Criteria: ${task.description}` : '';
      return `Compare: "${task.content}".${desc} Research all options across multiple sources. Create a detailed comparison including features, pricing, pros, cons, and your recommendation based on the analysis.`;
    },
    examplePrompts: [
      'Compare Notion vs Obsidian vs Roam Research for personal knowledge management',
      'Analyze AWS vs Google Cloud vs Azure for a small startup use case',
      'Compare the top 3 email marketing platforms for a 10k subscriber list'
    ],
    estimatedTime: 35
  }
};

/**
 * Comet Analyzer class
 */
export class CometAnalyzer {
  constructor(customConfig = {}) {
    this.config = { ...config.ai?.cometBrowser, ...customConfig };
    this.patterns = COMET_DELEGABLE_PATTERNS;
    this.enabled = this.config?.enabled !== false;
  }

  /**
   * Analyze all tasks for Comet delegation opportunities
   * @param {Object} taskData - Task data from task-fetcher
   * @returns {Object} - Analysis results with Comet opportunities
   */
  analyzeTasks(taskData) {
    const analysis = {
      analyzedAt: new Date().toISOString(),
      enabled: this.enabled,
      summary: {
        totalTasks: taskData.all.length,
        cometDelegable: 0,
        byCategory: {},
        totalTimeSavings: 0
      },
      cometOpportunities: [],
      tasks: []
    };

    if (!this.enabled) {
      return analysis;
    }

    for (const task of taskData.all) {
      const taskAnalysis = this.analyzeTask(task);
      analysis.tasks.push(taskAnalysis);

      if (taskAnalysis.cometCanHelp) {
        analysis.summary.cometDelegable++;
        analysis.summary.totalTimeSavings += taskAnalysis.estimatedTime || 0;
        analysis.cometOpportunities.push(taskAnalysis);

        const category = taskAnalysis.cometCategory;
        if (!analysis.summary.byCategory[category]) {
          analysis.summary.byCategory[category] = 0;
        }
        analysis.summary.byCategory[category]++;
      }
    }

    // Sort by priority first, then by time savings
    analysis.cometOpportunities.sort((a, b) => {
      const priorityA = a.task?.priority || 1;
      const priorityB = b.task?.priority || 1;
      if (priorityB !== priorityA) {
        return priorityB - priorityA;
      }
      return (b.estimatedTime || 0) - (a.estimatedTime || 0);
    });

    return analysis;
  }

  /**
   * Analyze a single task for Comet delegation
   */
  analyzeTask(task) {
    const content = `${task.content} ${task.description || ''}`.toLowerCase();

    const result = {
      task: {
        id: task.id,
        content: task.content,
        description: task.description,
        priority: task.priority,
        priorityLabel: task.priorityLabel,
        dueDate: task.due?.date,
        daysUntilDue: task.daysUntilDue,
        isOverdue: task.isOverdue,
        project: task.project?.name,
        labels: task.labels,
        url: task.url
      },
      cometCanHelp: false,
      cometCategory: null,
      cometCategoryName: null,
      cometCapability: null,
      cometPrompt: null,
      matchedKeywords: [],
      confidence: 0,
      estimatedTime: 0,
      examplePrompts: []
    };

    if (!this.enabled) {
      return result;
    }

    // Check each Comet pattern
    for (const [categoryId, pattern] of Object.entries(this.patterns)) {
      const matchedKeywords = pattern.keywords.filter(kw => content.includes(kw));

      if (matchedKeywords.length > 0) {
        result.cometCanHelp = true;
        result.cometCategory = categoryId;
        result.cometCategoryName = pattern.name;
        result.cometCapability = pattern.cometCapability;
        result.cometPrompt = pattern.promptTemplate(task);
        result.matchedKeywords = matchedKeywords;
        result.confidence = Math.min(0.5 + (matchedKeywords.length * 0.15), 1.0);
        result.estimatedTime = pattern.estimatedTime || 20;
        result.examplePrompts = pattern.examplePrompts;
        break; // Use first matching category
      }
    }

    return result;
  }

  /**
   * Get formatted Comet prompt for a specific task
   */
  getCometPrompt(taskId, tasks) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return null;

    const analysis = this.analyzeTask(task);
    if (!analysis.cometCanHelp) return null;

    return {
      prompt: analysis.cometPrompt,
      category: analysis.cometCategory,
      categoryName: analysis.cometCategoryName,
      capability: analysis.cometCapability,
      examples: analysis.examplePrompts
    };
  }

  /**
   * Get all available Comet categories
   */
  getCategories() {
    return Object.entries(this.patterns).map(([id, pattern]) => ({
      id,
      name: pattern.name,
      description: pattern.description,
      capability: pattern.cometCapability,
      keywords: pattern.keywords.slice(0, 5), // Sample keywords
      examplePrompts: pattern.examplePrompts
    }));
  }

  /**
   * Check if Comet analysis is enabled
   */
  isEnabled() {
    return this.enabled;
  }
}

export { COMET_DELEGABLE_PATTERNS };
export default CometAnalyzer;
