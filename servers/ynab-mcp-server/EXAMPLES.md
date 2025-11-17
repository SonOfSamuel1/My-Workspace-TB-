# YNAB MCP Server Usage Examples

This document provides example queries you can use with Claude once the YNAB MCP server is configured.

## Getting Started

First, you'll need to get your budget ID. Ask Claude:

```
What are my YNAB budgets?
```

Claude will use the `ynab_get_budgets` tool and return your budgets with their IDs.

## Budget Information

### View Budget Summary
```
Show me a summary of my "My Budget" including all accounts and their balances
```

### View Categories
```
What are all my budget categories?
```

### View Specific Category
```
How much did I budget for groceries this month?
```

## Accounts

### List All Accounts
```
Show me all my accounts in my primary budget
```

### View Account Details
```
What's the current balance of my checking account?
```

### Create New Account
```
Create a new savings account called "Emergency Fund" with a starting balance of $1,000
```

## Transactions

### View Recent Transactions
```
Show me all transactions from the last 30 days
```

### View Transactions by Account
```
Show me all transactions in my checking account from January 2025
```

### View Transactions by Category
```
What did I spend on restaurants last month?
```

### Create a Transaction
```
Add a transaction for $45.23 at Whole Foods in the Groceries category from my checking account today
```

### Create Multiple Transactions
```
Add the following transactions to my budget:
- $25 at Starbucks yesterday (Coffee category)
- $120 at Shell for gas (Auto category)
- $15.99 for Netflix (Subscriptions category)
```

### Update a Transaction
```
Change the amount of transaction [ID] to $50 and update the category to Dining Out
```

## Payees

### List All Payees
```
Show me all my payees
```

### Find Specific Payee
```
Do I have a payee called "Amazon"?
```

## Scheduled Transactions

### View Scheduled Transactions
```
What are my upcoming recurring transactions?
```

### Create Scheduled Transaction
```
Create a monthly scheduled transaction for my rent of $1,500 on the 1st of each month
```

### Update Scheduled Transaction
```
Update my Netflix scheduled transaction to $17.99
```

### Delete Scheduled Transaction
```
Delete the scheduled transaction for [name]
```

## Monthly Budget Data

### View Month Overview
```
Show me my budget for January 2025
```

### Update Category Budget
```
Set my groceries budget to $600 for this month
```

### Set Category Goal
```
Set a savings goal of $5,000 for my vacation category
```

## Analysis Queries

Claude can also help you analyze your YNAB data:

### Spending Analysis
```
Analyze my spending patterns for the last 3 months and tell me where I'm spending the most
```

### Budget vs Actual
```
Compare my budgeted amounts to actual spending for each category this month
```

### Category Trends
```
Show me how my grocery spending has changed over the last 6 months
```

### Account Reconciliation
```
Help me reconcile my checking account - show me all uncleared transactions
```

## Tips for Working with the MCP Server

1. **Always use full amounts in dollars**: Claude will automatically convert to milliunits (multiply by 1000)

2. **Be specific about dates**: Use clear date references like "today", "yesterday", "last month", or specific dates like "January 15, 2025"

3. **Use category and account names**: You don't need to remember IDs - Claude can look them up

4. **Combine operations**: You can ask Claude to perform multiple operations in one request

5. **Ask for summaries**: Claude can aggregate and analyze YNAB data to provide insights

## Advanced Examples

### Budget Review
```
Give me a complete budget review for this month:
- Show me which categories are over budget
- List any uncategorized transactions
- Show my account balances
- Summarize my top 5 spending categories
```

### Monthly Setup
```
Set up my budget for next month:
- Copy all budgeted amounts from this month
- Add $100 to my savings category
- Create a new "Holiday Gifts" category with $500
```

### Transaction Import
```
I have these cash transactions to add:
- Coffee: $4.50
- Lunch: $12.75
- Groceries: $45.20
- Gas: $38.00

Add them all to my cash account for today
```

### Spending Report
```
Create a spending report for last month showing:
- Total spending by category
- Comparison to budgeted amounts
- Percentage of budget used in each category
- Top 10 largest transactions
```

## Error Handling

If you encounter errors, Claude can help diagnose:

```
I'm getting an error when trying to create a transaction. Can you check my budget setup?
```

The MCP server will return detailed error messages that Claude can interpret and help you fix.

## Rate Limiting

Remember that YNAB has a rate limit of 200 requests per hour. If you're doing bulk operations, Claude can:

1. Batch operations where possible
2. Use delta requests to only fetch changed data
3. Warn you if you're approaching the limit

## Additional Resources

- [YNAB API Documentation](https://api.ynab.com/)
- [YNAB Help Center](https://support.ynab.com/)
- YNAB uses "The Four Rules" methodology - Claude can help you apply these rules to your budget

Happy budgeting!
