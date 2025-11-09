import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { getToken } from 'next-auth/jwt'

// Rate limiting storage (in-memory for now, use Redis in production)
const rateLimitStore = new Map<string, { count: number; resetAt: number }>()

// Clean up old entries every 5 minutes
setInterval(() => {
  const now = Date.now()
  for (const [key, value] of rateLimitStore.entries()) {
    if (value.resetAt < now) {
      rateLimitStore.delete(key)
    }
  }
}, 5 * 60 * 1000)

// Rate limit configuration
const RATE_LIMITS = {
  '/api/auth/signup': { requests: 5, window: 60 * 60 * 1000 }, // 5 per hour
  '/api/integration/sync': { requests: 100, window: 60 * 1000 }, // 100 per minute
  '/api/trpc': { requests: 1000, window: 60 * 1000 }, // 1000 per minute
}

function checkRateLimit(identifier: string, path: string): boolean {
  const config = Object.entries(RATE_LIMITS).find(([key]) => path.startsWith(key))?.[1]
  if (!config) return true // No rate limit configured

  const key = `${identifier}:${path}`
  const now = Date.now()
  const record = rateLimitStore.get(key)

  if (!record || record.resetAt < now) {
    rateLimitStore.set(key, { count: 1, resetAt: now + config.window })
    return true
  }

  if (record.count >= config.requests) {
    return false
  }

  record.count++
  return true
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Rate limiting for API routes
  if (pathname.startsWith('/api/')) {
    const identifier = request.ip || request.headers.get('x-forwarded-for') || 'unknown'

    if (!checkRateLimit(identifier, pathname)) {
      return NextResponse.json(
        { error: 'Too many requests. Please try again later.' },
        { status: 429 }
      )
    }
  }

  // Protected routes that require authentication
  const protectedPaths = [
    '/dashboard',
    '/agents',
    '/emails',
    '/approvals',
    '/analytics',
    '/settings',
  ]

  const isProtectedPath = protectedPaths.some(path => pathname.startsWith(path))

  if (isProtectedPath) {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    })

    if (!token) {
      const url = new URL('/auth/signin', request.url)
      url.searchParams.set('callbackUrl', pathname)
      return NextResponse.redirect(url)
    }
  }

  // Redirect authenticated users away from auth pages
  if (pathname.startsWith('/auth/signin') || pathname.startsWith('/auth/signup')) {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    })

    if (token) {
      return NextResponse.redirect(new URL('/dashboard', request.url))
    }
  }

  // Add security headers
  const response = NextResponse.next()

  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  response.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=()'
  )

  // Add CSRF token header for API routes
  if (pathname.startsWith('/api/trpc')) {
    const token = await getToken({
      req: request,
      secret: process.env.NEXTAUTH_SECRET,
    })

    if (token) {
      response.headers.set('X-User-Id', token.sub || '')
    }
  }

  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
}
