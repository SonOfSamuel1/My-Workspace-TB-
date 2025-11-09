import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format date to relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: Date): string {
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) return 'just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`

  return date.toLocaleDateString()
}

/**
 * Get tier color classes
 */
export function getTierColor(tier: number): string {
  switch (tier) {
    case 1: return 'bg-red-500 text-white'
    case 2: return 'bg-green-500 text-white'
    case 3: return 'bg-amber-500 text-white'
    case 4: return 'bg-blue-500 text-white'
    default: return 'bg-gray-500 text-white'
  }
}

/**
 * Get tier name
 */
export function getTierName(tier: number): string {
  switch (tier) {
    case 1: return 'Escalate'
    case 2: return 'Handle'
    case 3: return 'Draft'
    case 4: return 'Flag'
    default: return 'Unknown'
  }
}

/**
 * Format bytes to human readable size
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

/**
 * Format currency
 */
export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount)
}
