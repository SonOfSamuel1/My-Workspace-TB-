/**
 * Server-side cache for YNAB data
 * This cache persists across requests within the same serverless instance
 * For production with high availability, consider upgrading to Redis or Vercel KV
 */

import type { Transaction, CategoryGroup } from "./types";

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

interface TransactionsCache {
  transactions: Transaction[];
  cached_at: string;
}

interface CategoriesCache {
  categories: CategoryGroup[];
  cached_at: string;
}

// Global cache storage (persists across requests in serverless)
const transactionsCache: CacheEntry<TransactionsCache> | null = null;
const categoriesCache: CacheEntry<CategoriesCache> | null = null;

// Use module-level variables that persist across requests
let _transactionsCache: CacheEntry<TransactionsCache> | null = null;
let _categoriesCache: CacheEntry<CategoriesCache> | null = null;

export function getTransactionsCache(): TransactionsCache | null {
  return _transactionsCache?.data ?? null;
}

export function setTransactionsCache(transactions: Transaction[]): TransactionsCache {
  const cached_at = new Date().toISOString();
  const data: TransactionsCache = { transactions, cached_at };
  _transactionsCache = {
    data,
    timestamp: Date.now(),
  };
  return data;
}

export function getCategoriesCache(): CategoriesCache | null {
  return _categoriesCache?.data ?? null;
}

export function setCategoriesCache(categories: CategoryGroup[]): CategoriesCache {
  const cached_at = new Date().toISOString();
  const data: CategoriesCache = { categories, cached_at };
  _categoriesCache = {
    data,
    timestamp: Date.now(),
  };
  return data;
}

export function invalidateTransactionsCache(): void {
  _transactionsCache = null;
}

export function invalidateCategoriesCache(): void {
  _categoriesCache = null;
}

export function invalidateAllCache(): void {
  _transactionsCache = null;
  _categoriesCache = null;
}

export function getCacheTimestamp(type: "transactions" | "categories"): number | null {
  if (type === "transactions") {
    return _transactionsCache?.timestamp ?? null;
  }
  return _categoriesCache?.timestamp ?? null;
}
