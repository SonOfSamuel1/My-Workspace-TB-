import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a number as currency (YNAB uses milliunits - 1000 = $1.00)
 */
export function formatCurrency(milliunits: number): string {
  const amount = milliunits / 1000;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

/**
 * Format a date string for display
 */
export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format a date string relative to today
 */
export function formatDateRelative(dateString: string): string {
  const date = new Date(dateString);
  const today = new Date();
  const diffTime = today.getTime() - date.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;

  return formatDate(dateString);
}

/**
 * Convert milliunits to display value (divide by 1000)
 */
export function milliunitsToDisplay(milliunits: number): number {
  return milliunits / 1000;
}

/**
 * Convert display value to milliunits (multiply by 1000)
 */
export function displayToMilliunits(display: number): number {
  return Math.round(display * 1000);
}
