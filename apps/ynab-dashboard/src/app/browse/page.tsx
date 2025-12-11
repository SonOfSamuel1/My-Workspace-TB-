"use client";

import { useState, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Transaction, Category } from "@/lib/types";
import { formatCurrency, formatDateRelative } from "@/lib/utils";
import { useAllTransactions, useCategories } from "@/hooks/useTransaction";
import {
  AlertCircle,
  Calendar,
  ChevronRight,
  Loader2,
  RefreshCw,
  FolderOpen,
  Search,
} from "lucide-react";

// Filter types
type ApprovalFilter = "all" | "approved" | "unapproved";
type MemoFilter = "all" | "with-memo" | "without-memo";
type FlagFilter = "all" | "blue" | "purple" | "red" | "green" | "yellow" | "orange";

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
              {transaction.category_name || "Uncategorized"} &middot; {transaction.account_name}{" "}
              &middot; {formatDateRelative(transaction.date)}
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

export default function BrowsePage() {
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [approvalFilter, setApprovalFilter] = useState<ApprovalFilter>("all");
  const [memoFilter, setMemoFilter] = useState<MemoFilter>("all");
  const [flagFilter, setFlagFilter] = useState<FlagFilter>("all");
  const [monthFilter, setMonthFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const queryClient = useQueryClient();

  const {
    data: transactions = [],
    isLoading: txLoading,
    error: txError,
    refetch,
    isRefetching,
  } = useAllTransactions();
  const { data: categoryGroups = [], isLoading: catLoading } = useCategories();

  // Flatten categories for dropdown
  const allCategories = useMemo(() => {
    const cats: Category[] = [];
    categoryGroups.forEach((group) => {
      group.categories.forEach((cat) => {
        if (!cat.hidden && !cat.deleted) {
          cats.push({ ...cat, category_group_name: group.name });
        }
      });
    });
    return cats.sort((a, b) => a.name.localeCompare(b.name));
  }, [categoryGroups]);

  // Get available months
  const availableMonths = useMemo(() => {
    const months = new Set(transactions.map((t) => t.date.substring(0, 7)));
    return Array.from(months).sort().reverse();
  }, [transactions]);

  const formatMonthLabel = (month: string): string => {
    const [year, monthNum] = month.split("-");
    const date = new Date(parseInt(year), parseInt(monthNum) - 1);
    return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  };

  // Get last refresh timestamp
  const lastRefresh =
    typeof window !== "undefined" ? localStorage.getItem("ynab-all-transactions-timestamp") : null;
  const lastRefreshDate = lastRefresh ? new Date(parseInt(lastRefresh)) : null;

  const handleRefresh = () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("ynab-all-transactions-timestamp");
    }
    queryClient.invalidateQueries({ queryKey: ["transactions", "all"] });
    refetch();
  };

  // Filter transactions
  const filteredTransactions = useMemo(() => {
    let result = [...transactions].sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
    );

    // Category filter
    if (categoryFilter !== "all") {
      result = result.filter((t) => t.category_id === categoryFilter);
    }

    // Approval filter
    if (approvalFilter === "approved") {
      result = result.filter((t) => t.approved);
    } else if (approvalFilter === "unapproved") {
      result = result.filter((t) => !t.approved);
    }

    // Memo filter
    if (memoFilter === "with-memo") {
      result = result.filter((t) => t.memo && t.memo.trim() !== "");
    } else if (memoFilter === "without-memo") {
      result = result.filter((t) => !t.memo || t.memo.trim() === "");
    }

    // Flag filter
    if (flagFilter !== "all") {
      result = result.filter((t) => t.flag_color === flagFilter);
    }

    // Month filter
    if (monthFilter !== "all") {
      result = result.filter((t) => t.date.startsWith(monthFilter));
    }

    // Search query (payee name, memo)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (t) =>
          t.payee_name?.toLowerCase().includes(query) ||
          t.memo?.toLowerCase().includes(query) ||
          t.category_name?.toLowerCase().includes(query)
      );
    }

    return result;
  }, [
    transactions,
    categoryFilter,
    approvalFilter,
    memoFilter,
    flagFilter,
    monthFilter,
    searchQuery,
  ]);

  const isLoading = txLoading || catLoading;

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

  if (txError) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-4 pt-6">
            <AlertCircle className="h-12 w-12 text-destructive" />
            <h2 className="text-xl font-semibold">Error Loading Transactions</h2>
            <p className="text-center text-muted-foreground">
              {txError instanceof Error ? txError.message : "An error occurred"}
            </p>
            <Button onClick={handleRefresh}>Try Again</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/30 py-8 px-4">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Browse Transactions</h1>
            <p className="text-muted-foreground">Filter by category, status, and more</p>
          </div>
          <Button variant="outline" size="icon" onClick={handleRefresh} disabled={isRefetching}>
            <RefreshCw className={`h-4 w-4 ${isRefetching ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Summary card */}
        <Card className="mb-6">
          <CardContent className="flex items-center gap-4 p-4">
            <div className="rounded-full bg-purple-100 p-3 dark:bg-purple-900">
              <FolderOpen className="h-6 w-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="flex-1">
              <p className="text-2xl font-bold">{transactions.length}</p>
              <p className="text-sm text-muted-foreground">Total Transactions</p>
            </div>
            {lastRefreshDate && (
              <div className="text-right text-sm text-muted-foreground">
                <p>Last synced:</p>
                <p>{lastRefreshDate.toLocaleString()}</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Search bar */}
        <div className="mb-4 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search payee, memo, or category..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 text-sm border rounded-md bg-background"
          />
        </div>

        {/* Filters */}
        <div className="mb-6 space-y-3">
          {/* Category filter */}
          <div className="flex items-center gap-2">
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="flex-1 text-sm border rounded-md px-2 py-1 bg-background"
            >
              <option value="all">All Categories</option>
              {allCategories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.category_group_name}: {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Approval and Memo filters */}
          <div className="flex flex-wrap gap-2">
            <select
              value={approvalFilter}
              onChange={(e) => setApprovalFilter(e.target.value as ApprovalFilter)}
              className="text-sm border rounded-md px-2 py-1 bg-background"
            >
              <option value="all">All Status</option>
              <option value="approved">Approved</option>
              <option value="unapproved">Unapproved</option>
            </select>

            <select
              value={memoFilter}
              onChange={(e) => setMemoFilter(e.target.value as MemoFilter)}
              className="text-sm border rounded-md px-2 py-1 bg-background"
            >
              <option value="all">All Memos</option>
              <option value="with-memo">With Memo</option>
              <option value="without-memo">Without Memo</option>
            </select>

            <select
              value={flagFilter}
              onChange={(e) => setFlagFilter(e.target.value as FlagFilter)}
              className="text-sm border rounded-md px-2 py-1 bg-background"
            >
              <option value="all">All Flags</option>
              <option value="blue">Blue Flag</option>
              <option value="purple">Purple Flag</option>
              <option value="red">Red Flag</option>
              <option value="green">Green Flag</option>
              <option value="yellow">Yellow Flag</option>
              <option value="orange">Orange Flag</option>
            </select>
          </div>

          {/* Month filter */}
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <select
              value={monthFilter}
              onChange={(e) => setMonthFilter(e.target.value)}
              className="text-sm border rounded-md px-2 py-1 bg-background"
            >
              <option value="all">All Months</option>
              {availableMonths.map((month) => (
                <option key={month} value={month}>
                  {formatMonthLabel(month)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Results */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold">Results</h2>
              <Badge variant="secondary">
                {filteredTransactions.length === transactions.length
                  ? transactions.length
                  : `${filteredTransactions.length} of ${transactions.length}`}
              </Badge>
            </div>
            {(categoryFilter !== "all" ||
              approvalFilter !== "all" ||
              memoFilter !== "all" ||
              flagFilter !== "all" ||
              monthFilter !== "all" ||
              searchQuery) && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setCategoryFilter("all");
                  setApprovalFilter("all");
                  setMemoFilter("all");
                  setFlagFilter("all");
                  setMonthFilter("all");
                  setSearchQuery("");
                }}
              >
                Clear Filters
              </Button>
            )}
          </div>

          {filteredTransactions.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-4 py-8">
                <p className="text-muted-foreground">No transactions match the selected filters.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {filteredTransactions.slice(0, 100).map((txn) => (
                <TransactionCard key={txn.id} transaction={txn} />
              ))}
              {filteredTransactions.length > 100 && (
                <p className="text-center text-sm text-muted-foreground py-4">
                  Showing first 100 of {filteredTransactions.length} transactions. Use filters to
                  narrow down.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
