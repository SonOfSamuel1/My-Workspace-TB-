import { NextResponse } from "next/server";

/**
 * Validates the API key from request headers
 * Requires x-api-key header to match YNAB_DASHBOARD_API_KEY env variable
 */
export function validateApiKey(request: Request): boolean {
  const apiKey = request.headers.get("x-api-key");
  const expectedKey = process.env.YNAB_DASHBOARD_API_KEY;

  if (!expectedKey) {
    console.error("YNAB_DASHBOARD_API_KEY environment variable not set");
    return false;
  }

  return apiKey === expectedKey;
}

/**
 * Returns a 401 Unauthorized response for invalid API keys
 */
export function unauthorizedResponse(): NextResponse {
  return NextResponse.json(
    {
      error: "Unauthorized",
      message: "Invalid or missing API key. Include x-api-key header.",
    },
    { status: 401 }
  );
}
