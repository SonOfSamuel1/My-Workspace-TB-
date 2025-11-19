# Security & Monitoring Guide

Complete guide for securing and monitoring your Mail Agents application in production.

## ✅ **IMPLEMENTED SECURITY FEATURES**

Your application already includes:

- ✅ **Password Hashing**: bcrypt with 12 rounds
- ✅ **Route Protection**: Middleware enforces authentication
- ✅ **CSRF Protection**: Headers and token validation
- ✅ **Rate Limiting**: In-memory (upgrade to Redis for production)
- ✅ **Soft Deletes**: Data recovery capability
- ✅ **Security Headers**: X-Frame-Options, CSP, X-Content-Type-Options
- ✅ **SQL Injection Protection**: Prisma ORM with parameterized queries
- ✅ **XSS Protection**: React auto-escaping + CSP headers

---

## 🔒 **ADDITIONAL SECURITY HARDENING**

### 1. Environment Variables Security

```bash
# .env.production
# NEVER commit this file!

# Secure secrets with strong random values
NEXTAUTH_SECRET=$(openssl rand -base64 32)
INTEGRATION_API_KEY=$(openssl rand -base64 32)

# Use environment-specific URLs
NEXTAUTH_URL=https://yourdomain.com
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require

# Enable secure cookies in production
NEXTAUTH_URL_INTERNAL=https://yourdomain.com
```

### 2. Update NextAuth for Production

```typescript
// src/lib/auth.ts
export const authOptions: NextAuthOptions = {
  // ... existing config
  cookies: {
    sessionToken: {
      name: `${process.env.NODE_ENV === 'production' ? '__Secure-' : ''}next-auth.session-token`,
      options: {
        httpOnly: true,
        sameSite: 'lax',
        path: '/',
        secure: process.env.NODE_ENV === 'production',
      },
    },
  },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error',
    verifyRequest: '/auth/verify',
  },
}
```

### 3. Content Security Policy (CSP)

Update `middleware.ts` with stricter CSP:

```typescript
// src/middleware.ts (add to existing response headers)
const cspHeader = `
  default-src 'self';
  script-src 'self' 'unsafe-inline' 'unsafe-eval' https://vercel.live;
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  font-src 'self';
  connect-src 'self' https://vercel.live;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
`

response.headers.set(
  'Content-Security-Policy',
  cspHeader.replace(/\s{2,}/g, ' ').trim()
)
```

### 4. API Key Rotation

```typescript
// src/lib/api-keys.ts
import crypto from 'crypto'
import { prisma } from './prisma'

export async function generateAPIKey(userId: string, name: string) {
  const key = `sk_${crypto.randomBytes(32).toString('hex')}`
  const hash = crypto.createHash('sha256').update(key).digest('hex')

  await prisma.apiKey.create({
    data: {
      userId,
      name,
      keyHash: hash,
      expiresAt: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000), // 90 days
    },
  })

  return key // Return only once, never stored in plain text
}

export async function validateAPIKey(key: string): Promise<string | null> {
  const hash = crypto.createHash('sha256').update(key).digest('hex')

  const apiKey = await prisma.apiKey.findUnique({
    where: { keyHash: hash },
  })

  if (!apiKey || apiKey.expiresAt < new Date()) {
    return null
  }

  return apiKey.userId
}
```

### 5. Input Validation with Zod

All tRPC endpoints should validate input:

```typescript
// src/lib/validation.ts
import { z } from 'zod'

export const emailValidator = z.string().email().max(255)
export const urlValidator = z.string().url().max(2048)

export const createAgentSchema = z.object({
  name: z.string().min(1).max(100),
  agentEmail: emailValidator,
  description: z.string().max(500).optional(),
  config: z.object({
    tier1: z.object({ keywords: z.array(z.string()) }).optional(),
    tier2: z.object({ keywords: z.array(z.string()) }).optional(),
    offLimitsContacts: z.array(emailValidator).max(100),
  }),
})

// Use in tRPC:
.input(createAgentSchema)
```

### 6. Prevent Enumeration Attacks

```typescript
// src/app/api/auth/signin/route.ts
// Always return same message for invalid email or password
const GENERIC_ERROR = 'Invalid email or password'

if (!user) {
  return { error: GENERIC_ERROR }
}

if (!isPasswordValid) {
  return { error: GENERIC_ERROR }
}
```

### 7. Session Management

```typescript
// Add session timeout and refresh
export const authOptions: NextAuthOptions = {
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days
    updateAge: 24 * 60 * 60, // Refresh every 24 hours
  },
  callbacks: {
    async session({ session, token }) {
      // Add custom session data
      if (token && session.user) {
        session.user.id = token.sub!
        session.user.role = token.role as string
        session.lastActivity = new Date()
      }
      return session
    },
  },
}
```

---

## 📊 **MONITORING & OBSERVABILITY**

### 1. Sentry Setup (Error Tracking)

```bash
npm install @sentry/nextjs
npx @sentry/wizard@latest -i nextjs
```

```typescript
// sentry.client.config.ts
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

  // Performance Monitoring
  tracesSampleRate: 0.1, // 10% of transactions

  // Session Replay
  replaysSessionSampleRate: 0.1, // 10% of sessions
  replaysOnErrorSampleRate: 1.0, // 100% of errors

  // Environment
  environment: process.env.NODE_ENV,

  // Ignore errors
  ignoreErrors: [
    'ResizeObserver loop limit exceeded',
    'Non-Error promise rejection',
  ],

  // Before sending
  beforeSend(event, hint) {
    // Don't send errors from localhost
    if (event.request?.url?.includes('localhost')) {
      return null
    }
    return event
  },
})
```

```typescript
// sentry.server.config.ts
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 0.1,
  environment: process.env.NODE_ENV,

  // Tag all errors with server context
  initialScope: {
    tags: {
      runtime: 'node',
    },
  },
})
```

### 2. Vercel Analytics (Performance)

```bash
npm install @vercel/analytics
```

```typescript
// src/app/layout.tsx
import { Analytics } from '@vercel/analytics/react'

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        {children}
        <Analytics />
      </body>
    </html>
  )
}
```

### 3. Custom Performance Monitoring

```typescript
// src/lib/performance.ts
export function measurePerformance(name: string) {
  const start = performance.now()

  return {
    end: () => {
      const duration = performance.now() - start

      // Log slow operations
      if (duration > 1000) {
        logger.warn('Slow operation detected', { name, duration })
      }

      // Send to analytics
      if (typeof window !== 'undefined' && (window as any).gtag) {
        (window as any).gtag('event', 'timing_complete', {
          name,
          value: Math.round(duration),
          event_category: 'Performance',
        })
      }

      return duration
    },
  }
}

// Usage:
const measure = measurePerformance('fetch_emails')
const emails = await prisma.email.findMany()
measure.end()
```

### 4. Health Check Endpoint

```typescript
// src/app/api/health/route.ts
import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'

export async function GET() {
  try {
    // Check database connection
    await prisma.$queryRaw`SELECT 1`

    // Check external services (optional)
    const checks = {
      database: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
    }

    return NextResponse.json(checks, { status: 200 })
  } catch (error) {
    return NextResponse.json(
      {
        database: 'unhealthy',
        error: (error as Error).message,
      },
      { status: 503 }
    )
  }
}
```

### 5. Request Logging Middleware

```typescript
// src/middleware.ts (add to existing middleware)
import { logger } from '@/lib/logger'

export async function middleware(request: NextRequest) {
  const start = Date.now()
  const response = await NextResponse.next()
  const duration = Date.now() - start

  // Log all API requests
  if (request.nextUrl.pathname.startsWith('/api/')) {
    logger.info('API Request', {
      method: request.method,
      path: request.nextUrl.pathname,
      status: response.status,
      duration: `${duration}ms`,
      userAgent: request.headers.get('user-agent'),
      ip: request.ip || request.headers.get('x-forwarded-for'),
    })
  }

  return response
}
```

### 6. Uptime Monitoring

Use a service like:
- **Better Uptime**: https://betteruptime.com
- **UptimeRobot**: https://uptimerobot.com
- **Pingdom**: https://www.pingdom.com

Configure to hit `/api/health` every 5 minutes.

---

## 🚨 **ALERTS & NOTIFICATIONS**

### 1. Critical Error Alerts

```typescript
// src/lib/alerts.ts
import { logger } from './logger'

export async function sendCriticalAlert(
  title: string,
  message: string,
  error?: Error
) {
  logger.error(title, error, { critical: true })

  // Send to Slack
  if (process.env.SLACK_WEBHOOK_URL) {
    await fetch(process.env.SLACK_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: `🚨 CRITICAL: ${title}`,
        blocks: [
          {
            type: 'section',
            text: { type: 'mrkdwn', text: `*${title}*\n${message}` },
          },
          error && {
            type: 'section',
            text: { type: 'mrkdwn', text: `\`\`\`${error.stack}\`\`\`` },
          },
        ].filter(Boolean),
      }),
    })
  }

  // Send to PagerDuty (for production)
  if (process.env.PAGERDUTY_API_KEY) {
    await fetch('https://api.pagerduty.com/incidents', {
      method: 'POST',
      headers: {
        'Authorization': `Token token=${process.env.PAGERDUTY_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        incident: {
          type: 'incident',
          title,
          body: { type: 'incident_body', details: message },
        },
      }),
    })
  }
}

// Usage:
try {
  await processEmails()
} catch (error) {
  await sendCriticalAlert(
    'Email Processing Failed',
    'Unable to process emails for agent XYZ',
    error as Error
  )
}
```

### 2. Daily Summary Emails

```typescript
// Create a cron job or scheduled function
export async function sendDailySummary() {
  const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000)

  const stats = await prisma.analytics.aggregate({
    where: { date: { gte: yesterday } },
    _sum: {
      emailsProcessed: true,
      escalations: true,
      estimatedCost: true,
    },
  })

  await sendEmail({
    to: 'admin@yourdomain.com',
    subject: 'Daily Mail Agents Summary',
    html: `
      <h1>Yesterday's Activity</h1>
      <ul>
        <li>Emails Processed: ${stats._sum.emailsProcessed}</li>
        <li>Escalations: ${stats._sum.escalations}</li>
        <li>Estimated Cost: $${stats._sum.estimatedCost?.toFixed(2)}</li>
      </ul>
    `,
  })
}
```

---

## 🔐 **COMPLIANCE & AUDITING**

### 1. GDPR Compliance

```typescript
// src/app/api/user/export-data/route.ts
// Implement data export for GDPR
export async function GET(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session) return new Response('Unauthorized', { status: 401 })

  const userData = await prisma.user.findUnique({
    where: { id: session.user.id },
    include: {
      agents: true,
      auditLogs: true,
    },
  })

  return new Response(JSON.stringify(userData, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Content-Disposition': 'attachment; filename="user-data.json"',
    },
  })
}

// src/app/api/user/delete-account/route.ts
// Implement right to be forgotten
export async function DELETE(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session) return new Response('Unauthorized', { status: 401 })

  // Soft delete user and all related data
  await prisma.user.update({
    where: { id: session.user.id },
    data: { deletedAt: new Date() },
  })

  // Schedule hard deletion after 30 days
  await prisma.deletion Schedule.create({
    data: {
      userId: session.user.id,
      scheduledFor: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
    },
  })

  return new Response('Account deletion scheduled', { status: 200 })
}
```

### 2. Audit Log Retention

```typescript
// Create a cron job to clean old logs
export async function cleanOldAuditLogs() {
  const retentionDays = parseInt(process.env.AUDIT_LOG_RETENTION_DAYS || '90')
  const cutoffDate = new Date(Date.now() - retentionDays * 24 * 60 * 60 * 1000)

  const deleted = await prisma.auditLog.deleteMany({
    where: { createdAt: { lt: cutoffDate } },
  })

  logger.info(`Deleted ${deleted.count} old audit logs`)
}
```

---

## 🐛 **DEBUGGING IN PRODUCTION**

### 1. Enable Debug Mode for Specific Users

```typescript
// src/lib/debug.ts
const DEBUG_USERS = process.env.DEBUG_USER_IDS?.split(',') || []

export function isDebugEnabled(userId: string): boolean {
  return DEBUG_USERS.includes(userId)
}

// Usage in API:
if (isDebugEnabled(ctx.session.user.id)) {
  logger.debug('Detailed debug info', { /* ... */ })
}
```

### 2. Feature Flags

```typescript
// src/lib/features.ts
const FEATURES = {
  webhooks: process.env.FEATURE_WEBHOOKS === 'true',
  advancedSearch: process.env.FEATURE_ADVANCED_SEARCH === 'true',
  bulkOperations: process.env.FEATURE_BULK_OPS === 'true',
}

export function isFeatureEnabled(feature: keyof typeof FEATURES): boolean {
  return FEATURES[feature]
}

// Usage in UI:
{isFeatureEnabled('webhooks') && <WebhookSettings />}
```

---

## 📋 **SECURITY CHECKLIST**

Before deploying to production:

- [ ] All secrets in environment variables (not in code)
- [ ] HTTPS enabled on all endpoints
- [ ] Database connections use SSL
- [ ] Rate limiting enabled on all public endpoints
- [ ] CSRF protection enabled
- [ ] Security headers configured (CSP, X-Frame-Options, etc.)
- [ ] Password hashing with bcrypt (12+ rounds)
- [ ] Input validation on all user inputs
- [ ] SQL injection protection (using ORM)
- [ ] XSS protection (React + CSP)
- [ ] Session security (httpOnly, secure, sameSite cookies)
- [ ] API key rotation policy in place
- [ ] Audit logging enabled for sensitive actions
- [ ] Error messages don't leak sensitive info
- [ ] File upload size limits enforced
- [ ] Dependency vulnerabilities scanned (`npm audit`)
- [ ] Sentry or error tracking configured
- [ ] Uptime monitoring configured
- [ ] Backup strategy in place
- [ ] Incident response plan documented

---

## 🚀 **DEPLOYMENT CHECKLIST**

- [ ] Run security scan: `npm audit`
- [ ] Run type checking: `npm run type-check`
- [ ] Run linting: `npm run lint`
- [ ] Run tests: `npm run test`
- [ ] Review environment variables
- [ ] Enable database SSL
- [ ] Configure CDN for static assets
- [ ] Set up database backups (daily)
- [ ] Configure monitoring and alerts
- [ ] Document rollback procedure
- [ ] Test health check endpoint
- [ ] Verify error tracking is working
- [ ] Set up log aggregation
- [ ] Configure auto-scaling (if needed)
- [ ] Review and update CSP headers

---

## 📚 **ADDITIONAL RESOURCES**

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Next.js Security Best Practices](https://nextjs.org/docs/app/building-your-application/deploying/production-checklist)
- [Prisma Security Guide](https://www.prisma.io/docs/guides/deployment/deployment-guides/security)
- [NextAuth.js Security](https://next-auth.js.org/configuration/options#security)

Your application is already production-ready with most critical security features implemented!
