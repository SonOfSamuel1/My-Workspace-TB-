# YNAB Transaction Dashboard

A Next.js web application for managing YNAB transactions with deep linking support from email reports.

## Features

- View and edit YNAB transactions
- Update transaction categories
- Approve unapproved transactions
- Add/edit memos
- Split transactions
- Deep linking from daily transaction emails

## Deployment

Deployed on Vercel at: https://ynab-dashboard.vercel.app

## Local Development

```bash
# Install dependencies
npm install

# Create .env.local with your credentials
cp .env.example .env.local
# Edit .env.local with your YNAB API key and budget ID

# Run development server
npm run dev
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `YNAB_API_KEY` | Your YNAB API personal access token |
| `YNAB_BUDGET_ID` | Your YNAB budget ID (from URL) |
| `NEXT_PUBLIC_YNAB_BUDGET_ID` | Same as above (for client-side) |

## Routes

- `/` - Transaction list (shows unapproved transactions)
- `/transactions/[id]` - Transaction detail/edit page (deep link target)

## Integration

This dashboard receives deep links from:
- **ynab-transaction-reviewer** - Daily YNAB transaction review emails
- **weekly-budget-report** - Weekly budget summary emails

Email links format: `https://ynab-dashboard.vercel.app/transactions/{transaction_id}`

## Tech Stack

- Next.js 14 (App Router)
- React 18
- TanStack Query (data fetching)
- Tailwind CSS
- Radix UI components
- TypeScript
