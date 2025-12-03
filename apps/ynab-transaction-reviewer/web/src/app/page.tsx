'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Transaction } from '@/lib/types';
import { formatCurrency, formatDateRelative } from '@/lib/utils';
import {
  AlertCircle,
  Clock,
  CheckCircle,
  ChevronRight,
  Loader2,
  RefreshCw,
} from 'lucide-react';

// Budget ID hardcoded for personal use - this is a single-user app
const BUDGET_ID = '2a373a3b-bc29-46f0-92ab-008f3b0221a9';

async function fetchTransactions(): Promise<{
  uncategorized: Transaction[];
  unapproved: Transaction[];
}> {
  // Get transactions from the last 30 days
  const sinceDate = new Date();
  sinceDate.setDate(sinceDate.getDate() - 30);
  const dateStr = sinceDate.toISOString().split('T')[0];

  const response = await fetch(
    `/api/ynab/budgets/${BUDGET_ID}/transactions?since_date=${dateStr}`
  );
  if (!response.ok) {
    throw new Error('Failed to fetch transactions');
  }
  const data = await response.json();
  const transactions: Transaction[] = data.data.transactions;

  return {
    uncategorized: transactions.filter((t) => !t.category_id),
    unapproved: transactions.filter((t) => !t.approved && t.category_id),
  };
}

function TransactionCard({ transaction }: { transaction: Transaction }) {
  const isOutflow = transaction.amount < 0;

  return (
    <Link href={`/transactions/${transaction.id}`}>
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
        <CardContent className="flex items-center justify-between p-4">
          <div className="flex-1 min-w-0">
            <p className="font-medium truncate">{transaction.payee_name}</p>
            <p className="text-sm text-muted-foreground">
              {transaction.account_name} &middot; {formatDateRelative(transaction.date)}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={`font-semibold ${
                isOutflow ? 'text-red-600' : 'text-green-600'
              }`}
            >
              {formatCurrency(transaction.amount)}
            </span>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function HomePage() {
  const { data, isLoading, error, refetch, isRefetching } = useQuery({
    queryKey: ['transactions', 'overview'],
    queryFn: fetchTransactions,
  });

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading transactions...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-4 pt-6">
            <AlertCircle className="h-12 w-12 text-destructive" />
            <h2 className="text-xl font-semibold">Error Loading Transactions</h2>
            <p className="text-center text-muted-foreground">
              {error instanceof Error ? error.message : 'An error occurred'}
            </p>
            <Button onClick={() => refetch()}>Try Again</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { uncategorized = [], unapproved = [] } = data || {};

  return (
    <div className="min-h-screen bg-muted/30 py-8 px-4">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">YNAB Transaction Manager</h1>
            <p className="text-muted-foreground">
              Review and categorize your transactions
            </p>
          </div>
          <Button
            variant="outline"
            size="icon"
            onClick={() => refetch()}
            disabled={isRefetching}
          >
            <RefreshCw
              className={`h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`}
            />
          </Button>
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 gap-4 mb-8">
          <Card>
            <CardContent className="flex items-center gap-4 p-4">
              <div className="rounded-full bg-amber-100 p-3 dark:bg-amber-900">
                <AlertCircle className="h-6 w-6 text-amber-600 dark:text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{uncategorized.length}</p>
                <p className="text-sm text-muted-foreground">Uncategorized</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-4 p-4">
              <div className="rounded-full bg-blue-100 p-3 dark:bg-blue-900">
                <Clock className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{unapproved.length}</p>
                <p className="text-sm text-muted-foreground">Need Approval</p>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* All caught up state */}
        {uncategorized.length === 0 && unapproved.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-12">
              <CheckCircle className="h-16 w-16 text-green-500" />
              <div className="text-center">
                <h2 className="text-xl font-semibold">All Caught Up!</h2>
                <p className="text-muted-foreground">
                  No transactions need your attention right now.
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Uncategorized transactions */}
        {uncategorized.length > 0 && (
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-lg font-semibold">Uncategorized</h2>
              <Badge variant="warning">{uncategorized.length}</Badge>
            </div>
            <div className="space-y-2">
              {uncategorized.slice(0, 10).map((txn) => (
                <TransactionCard key={txn.id} transaction={txn} />
              ))}
              {uncategorized.length > 10 && (
                <p className="text-center text-sm text-muted-foreground py-2">
                  And {uncategorized.length - 10} more...
                </p>
              )}
            </div>
          </div>
        )}

        {/* Unapproved transactions */}
        {unapproved.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-lg font-semibold">Needs Approval</h2>
              <Badge variant="info">{unapproved.length}</Badge>
            </div>
            <div className="space-y-2">
              {unapproved.slice(0, 10).map((txn) => (
                <TransactionCard key={txn.id} transaction={txn} />
              ))}
              {unapproved.length > 10 && (
                <p className="text-center text-sm text-muted-foreground py-2">
                  And {unapproved.length - 10} more...
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
