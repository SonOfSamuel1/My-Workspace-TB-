import { NextRequest, NextResponse } from "next/server";
import { validateApiKey, unauthorizedResponse } from "@/lib/api-auth";
import { setTransactionsCache, setCategoriesCache } from "@/lib/cache";
import type { Transaction, CategoryGroup } from "@/lib/types";

const BUDGET_ID = "2a373a3b-bc29-46f0-92ab-008f3b0221a9";
const YNAB_API_BASE = "https://api.ynab.com/v1";

/**
 * POST /api/data/sync
 *
 * Fetches fresh data from YNAB API and updates the server cache.
 * Requires x-api-key header for authentication.
 *
 * Returns:
 *   success: boolean
 *   transactions_count: number
 *   categories_count: number
 *   synced_at: string (ISO timestamp)
 */
export async function POST(request: NextRequest) {
  // Validate API key
  if (!validateApiKey(request)) {
    return unauthorizedResponse();
  }

  const ynabApiKey = process.env.YNAB_API_KEY;
  if (!ynabApiKey) {
    return NextResponse.json(
      { error: "Server configuration error", message: "YNAB API key not configured" },
      { status: 500 }
    );
  }

  const headers = {
    Authorization: `Bearer ${ynabApiKey}`,
    "Content-Type": "application/json",
  };

  try {
    // Fetch transactions and categories in parallel
    const [transactionsRes, categoriesRes] = await Promise.all([
      fetch(`${YNAB_API_BASE}/budgets/${BUDGET_ID}/transactions`, { headers }),
      fetch(`${YNAB_API_BASE}/budgets/${BUDGET_ID}/categories`, { headers }),
    ]);

    if (!transactionsRes.ok) {
      const error = await transactionsRes.json();
      return NextResponse.json(
        { error: "YNAB API error", message: error.error?.detail || "Failed to fetch transactions" },
        { status: transactionsRes.status }
      );
    }

    if (!categoriesRes.ok) {
      const error = await categoriesRes.json();
      return NextResponse.json(
        { error: "YNAB API error", message: error.error?.detail || "Failed to fetch categories" },
        { status: categoriesRes.status }
      );
    }

    const transactionsData = await transactionsRes.json();
    const categoriesData = await categoriesRes.json();

    const transactions: Transaction[] = transactionsData.data.transactions;
    const categories: CategoryGroup[] = categoriesData.data.category_groups;

    // Update caches
    const transactionsCache = setTransactionsCache(transactions);
    const categoriesCache = setCategoriesCache(categories);

    return NextResponse.json({
      success: true,
      transactions_count: transactions.length,
      categories_count: categories.reduce((acc, g) => acc + g.categories.length, 0),
      synced_at: transactionsCache.cached_at,
    });
  } catch (error) {
    console.error("Sync error:", error);
    return NextResponse.json(
      { error: "Sync failed", message: error instanceof Error ? error.message : "Unknown error" },
      { status: 500 }
    );
  }
}
