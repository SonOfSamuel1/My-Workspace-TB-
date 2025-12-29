import { NextRequest, NextResponse } from "next/server";
import { validateApiKey, unauthorizedResponse } from "@/lib/api-auth";
import { getCategoriesCache } from "@/lib/cache";

/**
 * GET /api/data/categories
 *
 * Returns cached category data for external apps.
 * Requires x-api-key header for authentication.
 */
export async function GET(request: NextRequest) {
  // Validate API key
  if (!validateApiKey(request)) {
    return unauthorizedResponse();
  }

  // Get cached data
  const cache = getCategoriesCache();

  if (!cache) {
    return NextResponse.json(
      {
        error: "No cached data",
        message: "Categories cache is empty. Call POST /api/data/sync to populate.",
      },
      { status: 404 }
    );
  }

  return NextResponse.json({
    categories: cache.categories,
    cached_at: cache.cached_at,
  });
}
