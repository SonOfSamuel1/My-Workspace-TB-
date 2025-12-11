"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Transaction } from "@/lib/types";
import { formatCurrency, formatDateRelative } from "@/lib/utils";
import { useAllTransactions } from "@/hooks/useTransaction";
import {
  AlertCircle,
  Calendar,
  Clock,
  ChevronRight,
  Loader2,
  RefreshCw,
  Database,
} from "lucide-react";

// Filter types
type FilterType =
  | "all"
  | "with-memo"
  | "without-memo"
  | "blue-flag"
  | "purple-flag"
  | "amazon"
  | "approved"
  | "unapproved";

// Custom SVG flag icons
function BlueFlagIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M3 2v12M3 2l9 4-9 4"
        fill="#3B82F6"
        stroke="#3B82F6"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PurpleFlagIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M3 2v12M3 2l9 4-9 4"
        fill="#8B5CF6"
        stroke="#8B5CF6"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

// Filter functions
function filterTransactions(transactions: Transaction[], filter: FilterType): Transaction[] {
  switch (filter) {
    case "with-memo":
      return transactions.filter((t) => t.memo && t.memo.trim() !== "");
    case "without-memo":
      return transactions.filter((t) => !t.memo || t.memo.trim() === "");
    case "blue-flag":
      return transactions.filter((t) => t.flag_color === "blue");
    case "purple-flag":
      return transactions.filter((t) => t.flag_color === "purple");
    case "amazon":
      return transactions.filter((t) => t.payee_name?.toLowerCase().includes("amazon"));
    case "approved":
      return transactions.filter((t) => t.approved);
    case "unapproved":
      return transactions.filter((t) => !t.approved);
    default:
      return transactions;
  }
}

function filterByMonth(transactions: Transaction[], month: string): Transaction[] {
  if (month === "all") return transactions;
  return transactions.filter((t) => t.date.startsWith(month));
}

function getAvailableMonths(transactions: Transaction[]): string[] {
  const months = new Set(transactions.map((t) => t.date.substring(0, 7)));
  return Array.from(months).sort().reverse();
}

function formatMonthLabel(month: string): string {
  const [year, monthNum] = month.split("-");
  const date = new Date(parseInt(year), parseInt(monthNum) - 1);
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function TransactionCard({ transaction }: { transaction: Transaction }) {
  const isOutflow = transaction.amount < 0;

  return (
    <Link href={`/transactions/${transaction.id}`}>
      <Card className="hover:bg-accent/50 transition-colors cursor-pointer">
        <CardContent className="flex items-center justify-between p-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-medium truncate">{transaction.payee_name}</p>
              {!transaction.approved && (
                <Badge variant="warning" className="text-xs">
                  Pending
                </Badge>
              )}
            </div>
            {transaction.memo && (
              <p className="text-sm text-muted-foreground truncate">{transaction.memo}</p>
            )}
            <p className="text-sm text-muted-foreground">
              {transaction.account_name} &middot; {formatDateRelative(transaction.date)}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`font-semibold ${isOutflow ? "text-red-600" : "text-green-600"}`}>
              {formatCurrency(transaction.amount)}
            </span>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function AllTransactionsPage() {
  const [activeFilter, setActiveFilter] = useState<FilterType>("all");
  const [monthFilter, setMonthFilter] = useState<string>("all");
  const queryClient = useQueryClient();

  const { data: transactions = [], isLoading, error, refetch, isRefetching } = useAllTransactions();

  // Get last refresh timestamp
  const lastRefresh =
    typeof window !== "undefined" ? localStorage.getItem("ynab-all-transactions-timestamp") : null;
  const lastRefreshDate = lastRefresh ? new Date(parseInt(lastRefresh)) : null;

  const handleRefresh = () => {
    // Clear the timestamp to force refresh
    if (typeof window !== "undefined") {
      localStorage.removeItem("ynab-all-transactions-timestamp");
    }
    queryClient.invalidateQueries({ queryKey: ["transactions", "all"] });
    refetch();
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading all transactions...</p>
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
              {error instanceof Error ? error.message : "An error occurred"}
            </p>
            <Button onClick={handleRefresh}>Try Again</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Sort by date descending
  const sortedTransactions = [...transactions].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );

  return (
    <div className="min-h-screen bg-muted/30 py-8 px-4">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">All Transactions</h1>
            <p className="text-muted-foreground">Browse your complete transaction history</p>
          </div>
          <Button variant="outline" size="icon" onClick={handleRefresh} disabled={isRefetching}>
            <RefreshCw className={`h-4 w-4 ${isRefetching ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Summary card */}
        <Card className="mb-6">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="rounded-full bg-green-100 p-3 dark:bg-green-900">
              <Database className="h-6 w-6 text-green-600 dark:text-green-400" />
            </div>
            <div className="flex-1">
              <p className="text-2xl font-bold">{transactions.length}</p>
              <p className="text-sm text-muted-foreground">Total Transactions (Cached)</p>
            </div>
            {lastRefreshDate && (
              <div className="text-right text-sm text-muted-foreground">
                <p>Last synced:</p>
                <p>{lastRefreshDate.toLocaleString()}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Filter buttons */}
        <div className="mb-6">
          {/* Type filters */}
          <div className="flex flex-wrap gap-2 mb-3">
            <Button
              variant={activeFilter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("all")}
            >
              All
            </Button>
            <Button
              variant={activeFilter === "unapproved" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("unapproved")}
            >
              Unapproved
            </Button>
            <Button
              variant={activeFilter === "approved" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("approved")}
            >
              Approved
            </Button>
            <Button
              variant={activeFilter === "with-memo" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("with-memo")}
            >
              With Memo
            </Button>
            <Button
              variant={activeFilter === "without-memo" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("without-memo")}
            >
              Without Memo
            </Button>
            <Button
              variant={activeFilter === "blue-flag" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("blue-flag")}
            >
              <BlueFlagIcon className="h-4 w-4 mr-1" />
              Blue Flag
            </Button>
            <Button
              variant={activeFilter === "purple-flag" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("purple-flag")}
            >
              <PurpleFlagIcon className="h-4 w-4 mr-1" />
              Purple Flag
            </Button>
            <Button
              variant={activeFilter === "amazon" ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter("amazon")}
            >
              Amazon
            </Button>
          </div>

          {/* Month filter dropdown */}
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <select
              value={monthFilter}
              onChange={(e) => setMonthFilter(e.target.value)}
              className="text-sm border rounded-md px-2 py-1 bg-background"
            >
              <option value="all">All Months</option>
              {getAvailableMonths(sortedTransactions).map((month) => (
                <option key={month} value={month}>
                  {formatMonthLabel(month)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Transactions list */}
        {(() => {
          const typeFiltered = filterTransactions(sortedTransactions, activeFilter);
          const filteredTransactions = filterByMonth(typeFiltered, monthFilter);

          if (transactions.length === 0) {
            return (
              <Card>
                <CardContent className="flex flex-col items-center gap-4 py-12">
                  <Clock className="h-16 w-16 text-muted-foreground" />
                  <div className="text-center">
                    <h2 className="text-xl font-semibold">No Transactions Yet</h2>
                    <p className="text-muted-foreground">
                      Click refresh to load your transactions.
                    </p>
                  </div>
                </CardContent>
              </Card>
            );
          }

          return (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <h2 className="text-lg font-semibold">Transactions</h2>
                <Badge variant="secondary">
                  {filteredTransactions.length === transactions.length
                    ? transactions.length
                    : `${filteredTransactions.length} of ${transactions.length}`}
                </Badge>
              </div>
              {filteredTransactions.length === 0 ? (
                <Card>
                  <CardContent className="flex flex-col items-center gap-4 py-8">
                    <p className="text-muted-foreground">
                      No transactions match the selected filters.
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setActiveFilter("all");
                        setMonthFilter("all");
                      }}
                    >
                      Clear Filters
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-2">
                  {filteredTransactions.map((txn) => (
                    <TransactionCard key={txn.id} transaction={txn} />
                  ))}
                </div>
              )}
            </div>
          );
        })()}
      </div>
    </div>
  );
}
