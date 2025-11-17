#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

// YNAB API Base URL
const YNAB_API_BASE = "https://api.ynab.com/v1";

// YNAB API Client
class YNABClient {
  private apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  private async makeRequest(endpoint: string, method: string = "GET", body?: any) {
    const url = `${YNAB_API_BASE}${endpoint}`;
    const headers: Record<string, string> = {
      "Authorization": `Bearer ${this.apiKey}`,
      "Content-Type": "application/json",
    };

    const options: RequestInit = {
      method,
      headers,
    };

    if (body && (method === "POST" || method === "PUT" || method === "PATCH")) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`YNAB API error (${response.status}): ${errorText}`);
    }

    return await response.json();
  }

  // Budgets
  async getBudgets() {
    return this.makeRequest("/budgets");
  }

  async getBudget(budgetId: string, lastKnowledgeOfServer?: number) {
    let endpoint = `/budgets/${budgetId}`;
    if (lastKnowledgeOfServer) {
      endpoint += `?last_knowledge_of_server=${lastKnowledgeOfServer}`;
    }
    return this.makeRequest(endpoint);
  }

  // Accounts
  async getAccounts(budgetId: string, lastKnowledgeOfServer?: number) {
    let endpoint = `/budgets/${budgetId}/accounts`;
    if (lastKnowledgeOfServer) {
      endpoint += `?last_knowledge_of_server=${lastKnowledgeOfServer}`;
    }
    return this.makeRequest(endpoint);
  }

  async getAccount(budgetId: string, accountId: string) {
    return this.makeRequest(`/budgets/${budgetId}/accounts/${accountId}`);
  }

  async createAccount(budgetId: string, account: {
    name: string;
    type: string;
    balance: number;
  }) {
    return this.makeRequest(`/budgets/${budgetId}/accounts`, "POST", { account });
  }

  // Categories
  async getCategories(budgetId: string, lastKnowledgeOfServer?: number) {
    let endpoint = `/budgets/${budgetId}/categories`;
    if (lastKnowledgeOfServer) {
      endpoint += `?last_knowledge_of_server=${lastKnowledgeOfServer}`;
    }
    return this.makeRequest(endpoint);
  }

  async getCategory(budgetId: string, categoryId: string) {
    return this.makeRequest(`/budgets/${budgetId}/categories/${categoryId}`);
  }

  async updateCategoryForMonth(
    budgetId: string,
    month: string,
    categoryId: string,
    data: { budgeted?: number; goal_target?: number }
  ) {
    return this.makeRequest(
      `/budgets/${budgetId}/months/${month}/categories/${categoryId}`,
      "PATCH",
      { category: data }
    );
  }

  // Transactions
  async getTransactions(
    budgetId: string,
    options?: {
      sinceDate?: string;
      type?: string;
      lastKnowledgeOfServer?: number;
    }
  ) {
    let endpoint = `/budgets/${budgetId}/transactions`;
    const params = new URLSearchParams();

    if (options?.sinceDate) params.append("since_date", options.sinceDate);
    if (options?.type) params.append("type", options.type);
    if (options?.lastKnowledgeOfServer) {
      params.append("last_knowledge_of_server", options.lastKnowledgeOfServer.toString());
    }

    const queryString = params.toString();
    if (queryString) endpoint += `?${queryString}`;

    return this.makeRequest(endpoint);
  }

  async getTransactionsByAccount(budgetId: string, accountId: string, sinceDate?: string) {
    let endpoint = `/budgets/${budgetId}/accounts/${accountId}/transactions`;
    if (sinceDate) {
      endpoint += `?since_date=${sinceDate}`;
    }
    return this.makeRequest(endpoint);
  }

  async getTransactionsByCategory(budgetId: string, categoryId: string, sinceDate?: string) {
    let endpoint = `/budgets/${budgetId}/categories/${categoryId}/transactions`;
    if (sinceDate) {
      endpoint += `?since_date=${sinceDate}`;
    }
    return this.makeRequest(endpoint);
  }

  async getTransaction(budgetId: string, transactionId: string) {
    return this.makeRequest(`/budgets/${budgetId}/transactions/${transactionId}`);
  }

  async createTransaction(budgetId: string, transaction: {
    account_id: string;
    date: string;
    amount: number;
    payee_id?: string;
    payee_name?: string;
    category_id?: string;
    memo?: string;
    cleared?: string;
    approved?: boolean;
  }) {
    return this.makeRequest(`/budgets/${budgetId}/transactions`, "POST", { transaction });
  }

  async createTransactions(budgetId: string, transactions: any[]) {
    return this.makeRequest(`/budgets/${budgetId}/transactions`, "POST", { transactions });
  }

  async updateTransaction(budgetId: string, transactionId: string, transaction: any) {
    return this.makeRequest(
      `/budgets/${budgetId}/transactions/${transactionId}`,
      "PUT",
      { transaction }
    );
  }

  async updateTransactions(budgetId: string, transactions: any[]) {
    return this.makeRequest(`/budgets/${budgetId}/transactions`, "PATCH", { transactions });
  }

  // Payees
  async getPayees(budgetId: string, lastKnowledgeOfServer?: number) {
    let endpoint = `/budgets/${budgetId}/payees`;
    if (lastKnowledgeOfServer) {
      endpoint += `?last_knowledge_of_server=${lastKnowledgeOfServer}`;
    }
    return this.makeRequest(endpoint);
  }

  async getPayee(budgetId: string, payeeId: string) {
    return this.makeRequest(`/budgets/${budgetId}/payees/${payeeId}`);
  }

  // Scheduled Transactions
  async getScheduledTransactions(budgetId: string, lastKnowledgeOfServer?: number) {
    let endpoint = `/budgets/${budgetId}/scheduled_transactions`;
    if (lastKnowledgeOfServer) {
      endpoint += `?last_knowledge_of_server=${lastKnowledgeOfServer}`;
    }
    return this.makeRequest(endpoint);
  }

  async getScheduledTransaction(budgetId: string, scheduledTransactionId: string) {
    return this.makeRequest(
      `/budgets/${budgetId}/scheduled_transactions/${scheduledTransactionId}`
    );
  }

  async createScheduledTransaction(budgetId: string, scheduledTransaction: any) {
    return this.makeRequest(
      `/budgets/${budgetId}/scheduled_transactions`,
      "POST",
      { scheduled_transaction: scheduledTransaction }
    );
  }

  async updateScheduledTransaction(
    budgetId: string,
    scheduledTransactionId: string,
    scheduledTransaction: any
  ) {
    return this.makeRequest(
      `/budgets/${budgetId}/scheduled_transactions/${scheduledTransactionId}`,
      "PUT",
      { scheduled_transaction: scheduledTransaction }
    );
  }

  async deleteScheduledTransaction(budgetId: string, scheduledTransactionId: string) {
    return this.makeRequest(
      `/budgets/${budgetId}/scheduled_transactions/${scheduledTransactionId}`,
      "DELETE"
    );
  }

  // Months
  async getBudgetMonths(budgetId: string, lastKnowledgeOfServer?: number) {
    let endpoint = `/budgets/${budgetId}/months`;
    if (lastKnowledgeOfServer) {
      endpoint += `?last_knowledge_of_server=${lastKnowledgeOfServer}`;
    }
    return this.makeRequest(endpoint);
  }

  async getBudgetMonth(budgetId: string, month: string) {
    return this.makeRequest(`/budgets/${budgetId}/months/${month}`);
  }

  // User
  async getUser() {
    return this.makeRequest("/user");
  }
}

// Define available tools
const tools: Tool[] = [
  {
    name: "ynab_get_budgets",
    description: "Get all budgets for the authenticated user",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
  {
    name: "ynab_get_budget",
    description: "Get details for a specific budget including accounts, categories, and payees",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget to retrieve",
        },
        last_knowledge_of_server: {
          type: "number",
          description: "Optional: Only return data that has changed since the last knowledge of server",
        },
      },
      required: ["budget_id"],
    },
  },
  {
    name: "ynab_get_accounts",
    description: "Get all accounts for a budget",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        last_knowledge_of_server: {
          type: "number",
          description: "Optional: Only return data that has changed since the last knowledge of server",
        },
      },
      required: ["budget_id"],
    },
  },
  {
    name: "ynab_get_account",
    description: "Get a specific account",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        account_id: {
          type: "string",
          description: "The ID of the account",
        },
      },
      required: ["budget_id", "account_id"],
    },
  },
  {
    name: "ynab_create_account",
    description: "Create a new account in a budget",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        name: {
          type: "string",
          description: "The name of the account",
        },
        type: {
          type: "string",
          description: "Account type: checking, savings, creditCard, cash, lineOfCredit, otherAsset, otherLiability",
        },
        balance: {
          type: "number",
          description: "The current balance in milliunits (1000 = $1.00)",
        },
      },
      required: ["budget_id", "name", "type", "balance"],
    },
  },
  {
    name: "ynab_get_categories",
    description: "Get all categories for a budget, organized by category groups",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        last_knowledge_of_server: {
          type: "number",
          description: "Optional: Only return data that has changed since the last knowledge of server",
        },
      },
      required: ["budget_id"],
    },
  },
  {
    name: "ynab_get_category",
    description: "Get a specific category",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        category_id: {
          type: "string",
          description: "The ID of the category",
        },
      },
      required: ["budget_id", "category_id"],
    },
  },
  {
    name: "ynab_update_category",
    description: "Update a category for a specific month (set budgeted amount or goal target)",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        month: {
          type: "string",
          description: "The month in ISO format (YYYY-MM-DD)",
        },
        category_id: {
          type: "string",
          description: "The ID of the category",
        },
        budgeted: {
          type: "number",
          description: "Optional: The budgeted amount in milliunits",
        },
        goal_target: {
          type: "number",
          description: "Optional: The goal target amount in milliunits",
        },
      },
      required: ["budget_id", "month", "category_id"],
    },
  },
  {
    name: "ynab_get_transactions",
    description: "Get all transactions for a budget",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        since_date: {
          type: "string",
          description: "Optional: Only return transactions on or after this date (ISO format YYYY-MM-DD)",
        },
        type: {
          type: "string",
          description: "Optional: Filter by type (uncategorized or unapproved)",
        },
        last_knowledge_of_server: {
          type: "number",
          description: "Optional: Only return data that has changed since the last knowledge of server",
        },
      },
      required: ["budget_id"],
    },
  },
  {
    name: "ynab_get_transactions_by_account",
    description: "Get all transactions for a specific account",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        account_id: {
          type: "string",
          description: "The ID of the account",
        },
        since_date: {
          type: "string",
          description: "Optional: Only return transactions on or after this date (ISO format YYYY-MM-DD)",
        },
      },
      required: ["budget_id", "account_id"],
    },
  },
  {
    name: "ynab_get_transactions_by_category",
    description: "Get all transactions for a specific category",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        category_id: {
          type: "string",
          description: "The ID of the category",
        },
        since_date: {
          type: "string",
          description: "Optional: Only return transactions on or after this date (ISO format YYYY-MM-DD)",
        },
      },
      required: ["budget_id", "category_id"],
    },
  },
  {
    name: "ynab_get_transaction",
    description: "Get a specific transaction",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        transaction_id: {
          type: "string",
          description: "The ID of the transaction",
        },
      },
      required: ["budget_id", "transaction_id"],
    },
  },
  {
    name: "ynab_create_transaction",
    description: "Create a new transaction",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        account_id: {
          type: "string",
          description: "The ID of the account",
        },
        date: {
          type: "string",
          description: "The transaction date in ISO format (YYYY-MM-DD)",
        },
        amount: {
          type: "number",
          description: "The transaction amount in milliunits (positive for inflow, negative for outflow)",
        },
        payee_id: {
          type: "string",
          description: "Optional: The ID of the payee",
        },
        payee_name: {
          type: "string",
          description: "Optional: The name of the payee (if payee_id not provided)",
        },
        category_id: {
          type: "string",
          description: "Optional: The ID of the category",
        },
        memo: {
          type: "string",
          description: "Optional: A memo for the transaction",
        },
        cleared: {
          type: "string",
          description: "Optional: The cleared status (cleared, uncleared, reconciled)",
        },
        approved: {
          type: "boolean",
          description: "Optional: Whether the transaction is approved",
        },
      },
      required: ["budget_id", "account_id", "date", "amount"],
    },
  },
  {
    name: "ynab_update_transaction",
    description: "Update an existing transaction",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        transaction_id: {
          type: "string",
          description: "The ID of the transaction to update",
        },
        account_id: {
          type: "string",
          description: "Optional: The ID of the account",
        },
        date: {
          type: "string",
          description: "Optional: The transaction date in ISO format (YYYY-MM-DD)",
        },
        amount: {
          type: "number",
          description: "Optional: The transaction amount in milliunits",
        },
        payee_id: {
          type: "string",
          description: "Optional: The ID of the payee",
        },
        category_id: {
          type: "string",
          description: "Optional: The ID of the category",
        },
        memo: {
          type: "string",
          description: "Optional: A memo for the transaction",
        },
        cleared: {
          type: "string",
          description: "Optional: The cleared status (cleared, uncleared, reconciled)",
        },
        approved: {
          type: "boolean",
          description: "Optional: Whether the transaction is approved",
        },
      },
      required: ["budget_id", "transaction_id"],
    },
  },
  {
    name: "ynab_get_payees",
    description: "Get all payees for a budget",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        last_knowledge_of_server: {
          type: "number",
          description: "Optional: Only return data that has changed since the last knowledge of server",
        },
      },
      required: ["budget_id"],
    },
  },
  {
    name: "ynab_get_payee",
    description: "Get a specific payee",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        payee_id: {
          type: "string",
          description: "The ID of the payee",
        },
      },
      required: ["budget_id", "payee_id"],
    },
  },
  {
    name: "ynab_get_scheduled_transactions",
    description: "Get all scheduled transactions for a budget",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        last_knowledge_of_server: {
          type: "number",
          description: "Optional: Only return data that has changed since the last knowledge of server",
        },
      },
      required: ["budget_id"],
    },
  },
  {
    name: "ynab_get_scheduled_transaction",
    description: "Get a specific scheduled transaction",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        scheduled_transaction_id: {
          type: "string",
          description: "The ID of the scheduled transaction",
        },
      },
      required: ["budget_id", "scheduled_transaction_id"],
    },
  },
  {
    name: "ynab_create_scheduled_transaction",
    description: "Create a new scheduled transaction",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        account_id: {
          type: "string",
          description: "The ID of the account",
        },
        date_first: {
          type: "string",
          description: "The first date for the scheduled transaction (ISO format YYYY-MM-DD)",
        },
        frequency: {
          type: "string",
          description: "Frequency: never, daily, weekly, everyOtherWeek, twiceAMonth, every4Weeks, monthly, everyOtherMonth, every3Months, every4Months, twiceAYear, yearly",
        },
        amount: {
          type: "number",
          description: "The transaction amount in milliunits",
        },
        payee_id: {
          type: "string",
          description: "Optional: The ID of the payee",
        },
        category_id: {
          type: "string",
          description: "Optional: The ID of the category",
        },
        memo: {
          type: "string",
          description: "Optional: A memo for the scheduled transaction",
        },
      },
      required: ["budget_id", "account_id", "date_first", "frequency", "amount"],
    },
  },
  {
    name: "ynab_update_scheduled_transaction",
    description: "Update an existing scheduled transaction",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        scheduled_transaction_id: {
          type: "string",
          description: "The ID of the scheduled transaction",
        },
        account_id: {
          type: "string",
          description: "Optional: The ID of the account",
        },
        date_first: {
          type: "string",
          description: "Optional: The first date for the scheduled transaction (ISO format)",
        },
        frequency: {
          type: "string",
          description: "Optional: Frequency value",
        },
        amount: {
          type: "number",
          description: "Optional: The transaction amount in milliunits",
        },
        payee_id: {
          type: "string",
          description: "Optional: The ID of the payee",
        },
        category_id: {
          type: "string",
          description: "Optional: The ID of the category",
        },
        memo: {
          type: "string",
          description: "Optional: A memo",
        },
      },
      required: ["budget_id", "scheduled_transaction_id"],
    },
  },
  {
    name: "ynab_delete_scheduled_transaction",
    description: "Delete a scheduled transaction",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        scheduled_transaction_id: {
          type: "string",
          description: "The ID of the scheduled transaction to delete",
        },
      },
      required: ["budget_id", "scheduled_transaction_id"],
    },
  },
  {
    name: "ynab_get_months",
    description: "Get all budget months",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        last_knowledge_of_server: {
          type: "number",
          description: "Optional: Only return data that has changed since the last knowledge of server",
        },
      },
      required: ["budget_id"],
    },
  },
  {
    name: "ynab_get_month",
    description: "Get a specific budget month with category data",
    inputSchema: {
      type: "object",
      properties: {
        budget_id: {
          type: "string",
          description: "The ID of the budget",
        },
        month: {
          type: "string",
          description: "The month in ISO format (YYYY-MM-DD, typically first of month)",
        },
      },
      required: ["budget_id", "month"],
    },
  },
  {
    name: "ynab_get_user",
    description: "Get the authenticated user's information",
    inputSchema: {
      type: "object",
      properties: {},
    },
  },
];

// Create server instance
const server = new Server(
  {
    name: "ynab-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Get API key from environment
const apiKey = process.env.YNAB_API_KEY;
if (!apiKey) {
  console.error("Error: YNAB_API_KEY environment variable is required");
  process.exit(1);
}

const client = new YNABClient(apiKey);

// Handle list_tools request
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools,
  };
});

// Handle call_tool request
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    let result;

    // Ensure args is defined
    if (!args) {
      throw new Error("Missing arguments for tool call");
    }

    switch (name) {
      case "ynab_get_budgets":
        result = await client.getBudgets();
        break;

      case "ynab_get_budget":
        result = await client.getBudget(
          args.budget_id as string,
          args.last_knowledge_of_server as number | undefined
        );
        break;

      case "ynab_get_accounts":
        result = await client.getAccounts(
          args.budget_id as string,
          args.last_knowledge_of_server as number | undefined
        );
        break;

      case "ynab_get_account":
        result = await client.getAccount(
          args.budget_id as string,
          args.account_id as string
        );
        break;

      case "ynab_create_account":
        result = await client.createAccount(args.budget_id as string, {
          name: args.name as string,
          type: args.type as string,
          balance: args.balance as number,
        });
        break;

      case "ynab_get_categories":
        result = await client.getCategories(
          args.budget_id as string,
          args.last_knowledge_of_server as number | undefined
        );
        break;

      case "ynab_get_category":
        result = await client.getCategory(
          args.budget_id as string,
          args.category_id as string
        );
        break;

      case "ynab_update_category":
        result = await client.updateCategoryForMonth(
          args.budget_id as string,
          args.month as string,
          args.category_id as string,
          {
            budgeted: args.budgeted as number | undefined,
            goal_target: args.goal_target as number | undefined,
          }
        );
        break;

      case "ynab_get_transactions":
        result = await client.getTransactions(args.budget_id as string, {
          sinceDate: args.since_date as string | undefined,
          type: args.type as string | undefined,
          lastKnowledgeOfServer: args.last_knowledge_of_server as number | undefined,
        });
        break;

      case "ynab_get_transactions_by_account":
        result = await client.getTransactionsByAccount(
          args.budget_id as string,
          args.account_id as string,
          args.since_date as string | undefined
        );
        break;

      case "ynab_get_transactions_by_category":
        result = await client.getTransactionsByCategory(
          args.budget_id as string,
          args.category_id as string,
          args.since_date as string | undefined
        );
        break;

      case "ynab_get_transaction":
        result = await client.getTransaction(
          args.budget_id as string,
          args.transaction_id as string
        );
        break;

      case "ynab_create_transaction":
        result = await client.createTransaction(args.budget_id as string, {
          account_id: args.account_id as string,
          date: args.date as string,
          amount: args.amount as number,
          payee_id: args.payee_id as string | undefined,
          payee_name: args.payee_name as string | undefined,
          category_id: args.category_id as string | undefined,
          memo: args.memo as string | undefined,
          cleared: args.cleared as string | undefined,
          approved: args.approved as boolean | undefined,
        });
        break;

      case "ynab_update_transaction":
        {
          const updateData: any = {};
          if (args.account_id !== undefined) updateData.account_id = args.account_id;
          if (args.date !== undefined) updateData.date = args.date;
          if (args.amount !== undefined) updateData.amount = args.amount;
          if (args.payee_id !== undefined) updateData.payee_id = args.payee_id;
          if (args.category_id !== undefined) updateData.category_id = args.category_id;
          if (args.memo !== undefined) updateData.memo = args.memo;
          if (args.cleared !== undefined) updateData.cleared = args.cleared;
          if (args.approved !== undefined) updateData.approved = args.approved;

          result = await client.updateTransaction(
            args.budget_id as string,
            args.transaction_id as string,
            updateData
          );
        }
        break;

      case "ynab_get_payees":
        result = await client.getPayees(
          args.budget_id as string,
          args.last_knowledge_of_server as number | undefined
        );
        break;

      case "ynab_get_payee":
        result = await client.getPayee(
          args.budget_id as string,
          args.payee_id as string
        );
        break;

      case "ynab_get_scheduled_transactions":
        result = await client.getScheduledTransactions(
          args.budget_id as string,
          args.last_knowledge_of_server as number | undefined
        );
        break;

      case "ynab_get_scheduled_transaction":
        result = await client.getScheduledTransaction(
          args.budget_id as string,
          args.scheduled_transaction_id as string
        );
        break;

      case "ynab_create_scheduled_transaction":
        {
          const scheduledTx: any = {
            account_id: args.account_id,
            date_first: args.date_first,
            frequency: args.frequency,
            amount: args.amount,
          };
          if (args.payee_id !== undefined) scheduledTx.payee_id = args.payee_id;
          if (args.category_id !== undefined) scheduledTx.category_id = args.category_id;
          if (args.memo !== undefined) scheduledTx.memo = args.memo;

          result = await client.createScheduledTransaction(
            args.budget_id as string,
            scheduledTx
          );
        }
        break;

      case "ynab_update_scheduled_transaction":
        {
          const updateData: any = {};
          if (args.account_id !== undefined) updateData.account_id = args.account_id;
          if (args.date_first !== undefined) updateData.date_first = args.date_first;
          if (args.frequency !== undefined) updateData.frequency = args.frequency;
          if (args.amount !== undefined) updateData.amount = args.amount;
          if (args.payee_id !== undefined) updateData.payee_id = args.payee_id;
          if (args.category_id !== undefined) updateData.category_id = args.category_id;
          if (args.memo !== undefined) updateData.memo = args.memo;

          result = await client.updateScheduledTransaction(
            args.budget_id as string,
            args.scheduled_transaction_id as string,
            updateData
          );
        }
        break;

      case "ynab_delete_scheduled_transaction":
        result = await client.deleteScheduledTransaction(
          args.budget_id as string,
          args.scheduled_transaction_id as string
        );
        break;

      case "ynab_get_months":
        result = await client.getBudgetMonths(
          args.budget_id as string,
          args.last_knowledge_of_server as number | undefined
        );
        break;

      case "ynab_get_month":
        result = await client.getBudgetMonth(
          args.budget_id as string,
          args.month as string
        );
        break;

      case "ynab_get_user":
        result = await client.getUser();
        break;

      default:
        throw new Error(`Unknown tool: ${name}`);
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("YNAB MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
