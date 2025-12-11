import { NextRequest, NextResponse } from "next/server";
import { validateApiKey, unauthorizedResponse } from "@/lib/api-auth";
import { getTransactionsCache } from "@/lib/cache";
import type { Transaction } from "@/lib/types";

/**
 * GET /api/data/transactions
 *
 * Returns cached transaction data for external apps.
 * Requires x-api-key header for authentication.
 *
 * Query Parameters:
 *   category_id: string - Filter by category ID
 *   approved: "true" | "false" - Filter by approval status
 *   limit: number (default 100)
 *   offset: number (default 0)
 */
export async function GET(request: NextRequest) {
  // Validate API key
  if (!validateApiKey(request)) {
    return unauthorizedResponse();
  }

  // Get cached data
  const cache = getTransactionsCache();

  if (!cache) {
    return NextResponse.json(
      {
        error: "No cached data",
        message: "Transaction cache is empty. Call POST /api/data/sync to populate.",
      },
      { status: 404 }
    );
  }

  // Parse query parameters
  const searchParams = request.nextUrl.searchParams;
  const categoryId = searchParams.get("category_id");
  const approved = searchParams.get("approved");
  const limit = parseInt(searchParams.get("limit") || "100", 10);
  const offset = parseInt(searchParams.get("offset") || "0", 10);

  // Filter transactions
  let transactions: Transaction[] = cache.transactions;

  if (categoryId) {
    transactions = transactions.filter((t) => t.category_id === categoryId);
  }

  if (approved !== null) {
    const isApproved = approved === "true";
    transactions = transactions.filter((t) => t.approved === isApproved);
  }

  // Get total before pagination
  const total = transactions.length;

  // Apply pagination
  transactions = transactions.slice(offset, offset + limit);

  return NextResponse.json({
    transactions,
    total,
    limit,
    offset,
    cached_at: cache.cached_at,
  });
}
