# Production Enhancements Guide

This guide provides implementation roadmaps for advanced features to take your Mail Agents application to the next level.

## ✅ **COMPLETED ENHANCEMENTS**

The following critical improvements have been implemented:

### Security & Authentication
- ✅ Password authentication with bcrypt hashing
- ✅ Route protection middleware with NextAuth
- ✅ CSRF protection via middleware
- ✅ Rate limiting on API routes
- ✅ Soft deletes for data recovery
- ✅ Security headers (X-Frame-Options, CSP, etc.)

### Database & Performance
- ✅ Comprehensive database indexes
- ✅ Composite indexes for common queries
- ✅ Database migration system with Prisma
- ✅ Migration guide (MIGRATION_GUIDE.md)

### User Experience
- ✅ React Error Boundaries with fallback UI
- ✅ Global error handler
- ✅ Skeleton loading states
- ✅ Dark mode theme switching
- ✅ Improved error logging system

### Data Models
- ✅ AuditLog model for compliance
- ✅ Webhook & WebhookDelivery models
- ✅ AgentTemplate model for presets
- ✅ RateLimit model for tracking

---

## 🚀 **REMAINING ENHANCEMENTS**

### 1. Unit & Integration Testing

**Priority**: High
**Effort**: Medium
**Impact**: High (prevents regressions, improves code quality)

#### Setup

```bash
# Install dependencies
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom

@testing-library/user-event happy-dom
```

#### Test Structure

```
web/
├── src/
│   ├── lib/
│   │   └── __tests__/
│   │       ├── logger.test.ts
│   │       └── utils.test.ts
│   ├── components/
│   │   └── __tests__/
│   │       ├── error-boundary.test.tsx
│   │       └── theme-toggle.test.tsx
│   └── server/
│       └── routers/
│           └── __tests__/
│               ├── agent.test.ts
│               ├── email.test.ts
│               └── analytics.test.ts
└── vitest.config.ts
```

#### Example Unit Test

```typescript
// src/lib/__tests__/logger.test.ts
import { describe, it, expect, vi } from 'vitest'
import { logger } from '../logger'

describe('Logger', () => {
  it('should log info messages', () => {
    const consoleSpy = vi.spyOn(console, 'info')
    logger.info('Test message', { foo: 'bar' })
    expect(consoleSpy).toHaveBeenCalled()
  })

  it('should measure execution time', async () => {
    const result = await logger.measure('test', async () => {
      await new Promise(resolve => setTimeout(resolve, 100))
      return 'done'
    })
    expect(result).toBe('done')
  })
})
```

#### Example Integration Test for tRPC

```typescript
// src/server/routers/__tests__/agent.test.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { appRouter } from '../_app'
import { prisma } from '@/lib/prisma'

describe('AgentRouter', () => {
  beforeEach(async () => {
    // Clean up database
    await prisma.agent.deleteMany()
    await prisma.user.deleteMany()
  })

  it('should create a new agent', async () => {
    const caller = appRouter.createCaller({
      session: { user: { id: 'test-user-id' } },
      prisma,
    })

    const agent = await caller.agent.create({
      name: 'Test Agent',
      agentEmail: 'test@example.com',
      timezone: 'America/New_York',
      config: {},
    })

    expect(agent.name).toBe('Test Agent')
    expect(agent.enabled).toBe(true)
  })
})
```

#### Add Scripts to package.json

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage"
  }
}
```

---

### 2. Audit Log System

**Priority**: High (compliance)
**Effort**: Medium
**Impact**: High (security, debugging, compliance)

#### Implementation

The AuditLog model is already in the schema. Now implement the logging middleware:

```typescript
// src/lib/audit.ts
import { prisma } from './prisma'
import { logger } from './logger'

export async function createAuditLog({
  userId,
  action,
  resource,
  resourceId,
  previousValue,
  newValue,
  ipAddress,
  userAgent,
}: {
  userId: string
  action: string
  resource: string
  resourceId?: string
  previousValue?: any
  newValue?: any
  ipAddress?: string
  userAgent?: string
}) {
  try {
    await prisma.auditLog.create({
      data: {
        userId,
        action,
        resource,
        resourceId,
        previousValue,
        newValue,
        ipAddress,
        userAgent,
      },
    })
    logger.info('Audit log created', { userId, action, resource })
  } catch (error) {
    logger.error('Failed to create audit log', error as Error)
  }
}

// Middleware for tRPC
export function auditMiddleware<T extends { userId: string }>(
  action: string,
  resource: string
) {
  return async (opts: any) => {
    const { ctx, next, input } = opts

    // Get previous state for updates/deletes
    let previousValue
    if (input?.id) {
      // Fetch current state before mutation
      // previousValue = await prisma[resource].findUnique({ where: { id: input.id } })
    }

    const result = await next()

    // Log the action
    await createAuditLog({
      userId: ctx.session.user.id,
      action,
      resource,
      resourceId: input?.id,
      previousValue,
      newValue: result,
      ipAddress: ctx.req?.ip,
      userAgent: ctx.req?.headers?.['user-agent'],
    })

    return result
  }
}
```

#### Usage in tRPC Routers

```typescript
// src/server/routers/agent.ts
import { auditMiddleware } from '@/lib/audit'

export const agentRouter = createTRPCRouter({
  create: protectedProcedure
    .use(auditMiddleware('create_agent', 'agent'))
    .input(createAgentSchema)
    .mutation(async ({ ctx, input }) => {
      // ... create agent
    }),

  update: protectedProcedure
    .use(auditMiddleware('update_agent', 'agent'))
    .input(updateAgentSchema)
    .mutation(async ({ ctx, input }) => {
      // ... update agent
    }),
})
```

#### Audit Log Viewer

Create a page at `/settings/audit-logs`:

```typescript
// src/app/(app)/settings/audit-logs/page.tsx
import { trpc } from '@/lib/trpc/client'

export default function AuditLogsPage() {
  const { data: logs } = trpc.audit.list.useQuery({ limit: 100 })

  return (
    <div>
      <h1>Audit Logs</h1>
      <table>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Action</th>
            <th>Resource</th>
            <th>User</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {logs?.map((log) => (
            <tr key={log.id}>
              <td>{new Date(log.createdAt).toLocaleString()}</td>
              <td>{log.action}</td>
              <td>{log.resource}</td>
              <td>{log.userId}</td>
              <td>
                <button onClick={() => showDetails(log)}>View</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

---

### 3. Webhook System

**Priority**: Medium
**Effort**: High
**Impact**: High (integrations, extensibility)

#### Implementation

```typescript
// src/lib/webhooks.ts
import crypto from 'crypto'
import { prisma } from './prisma'
import { logger } from './logger'

export async function triggerWebhooks(
  agentId: string,
  event: string,
  payload: any
) {
  const webhooks = await prisma.webhook.findMany({
    where: {
      agentId,
      enabled: true,
      events: { has: event },
    },
  })

  for (const webhook of webhooks) {
    await deliverWebhook(webhook, event, payload)
  }
}

async function deliverWebhook(
  webhook: any,
  event: string,
  payload: any
) {
  const startTime = Date.now()
  const body = JSON.stringify({ event, data: payload })

  // Generate HMAC signature
  const signature = crypto
    .createHmac('sha256', webhook.secret)
    .update(body)
    .digest('hex')

  try {
    const response = await fetch(webhook.url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Webhook-Signature': signature,
        'X-Webhook-Event': event,
      },
      body,
    })

    const duration = Date.now() - startTime

    await prisma.webhookDelivery.create({
      data: {
        webhookId: webhook.id,
        event,
        payload,
        statusCode: response.status,
        responseBody: await response.text(),
        duration,
        completedAt: new Date(),
      },
    })

    // Reset failure count on success
    if (response.ok) {
      await prisma.webhook.update({
        where: { id: webhook.id },
        data: { failureCount: 0, lastTriggeredAt: new Date() },
      })
    } else {
      await incrementFailureCount(webhook.id)
    }
  } catch (error) {
    logger.error('Webhook delivery failed', error as Error, {
      webhookId: webhook.id,
      event,
    })

    await prisma.webhookDelivery.create({
      data: {
        webhookId: webhook.id,
        event,
        payload,
        error: (error as Error).message,
        attemptedAt: new Date(),
      },
    })

    await incrementFailureCount(webhook.id)
  }
}

async function incrementFailureCount(webhookId: string) {
  const webhook = await prisma.webhook.update({
    where: { id: webhookId },
    data: { failureCount: { increment: 1 } },
  })

  // Disable webhook after 10 failures
  if (webhook.failureCount >= 10) {
    await prisma.webhook.update({
      where: { id: webhookId },
      data: { enabled: false },
    })
    logger.warn('Webhook disabled due to failures', { webhookId })
  }
}
```

#### Trigger Webhooks in Email Processing

```typescript
// In email processing logic
await triggerWebhooks(agentId, 'email_received', {
  emailId: email.id,
  tier: email.tier,
  subject: email.subject,
  from: email.from,
})

await triggerWebhooks(agentId, 'action_completed', {
  actionId: action.id,
  type: action.type,
  success: true,
})
```

---

### 4. Email Notifications for Approvals

**Priority**: Medium
**Effort**: Low-Medium
**Impact**: High (user engagement)

#### Setup with Resend (or SendGrid/Mailgun)

```bash
npm install resend
```

```typescript
// src/lib/email.ts
import { Resend } from 'resend'

const resend = new Resend(process.env.RESEND_API_KEY)

export async function sendApprovalNotification(
  userEmail: string,
  agentName: string,
  emailSubject: string,
  approvalUrl: string
) {
  await resend.emails.send({
    from: 'Mail Agents <notifications@yourdomain.com>',
    to: userEmail,
    subject: `Approval Needed: ${agentName}`,
    html: `
      <h1>Action Requires Approval</h1>
      <p>Your agent <strong>${agentName}</strong> needs your approval for an email:</p>
      <p><strong>Subject:</strong> ${emailSubject}</p>
      <p><a href="${approvalUrl}">Review and Approve</a></p>
    `,
  })
}

// Trigger in action creation
await sendApprovalNotification(
  user.email,
  agent.name,
  email.subject,
  `${process.env.NEXT_PUBLIC_APP_URL}/approvals?id=${action.id}`
)
```

---

### 5. Agent Templates/Presets

**Priority**: Medium
**Effort**: Low
**Impact**: Medium (user convenience)

The AgentTemplate model is ready. Implement the UI:

```typescript
// src/app/(app)/templates/page.tsx
export default function TemplatesPage() {
  const { data: templates } = trpc.template.list.useQuery()

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {templates?.map((template) => (
        <Card key={template.id}>
          <CardHeader>
            <CardTitle>{template.name}</CardTitle>
            <CardDescription>{template.description}</CardDescription>
          </CardHeader>
          <CardFooter>
            <Button onClick={() => applyTemplate(template.id)}>
              Use Template
            </Button>
          </CardFooter>
        </Card>
      ))}
    </div>
  )
}
```

#### Seed Official Templates

```typescript
// prisma/seed-templates.ts
const templates = [
  {
    name: 'Executive Assistant',
    category: 'executive',
    description: 'Handle executive emails with priority classification',
    config: {
      tier1: { keywords: ['urgent', 'ceo', 'board'] },
      tier2: { keywords: ['meeting', 'schedule'] },
      style: 'professional',
    },
    isOfficial: true,
    isPublic: true,
  },
  {
    name: 'Customer Support',
    category: 'support',
    description: 'Auto-respond to common support requests',
    config: {
      tier2: { keywords: ['refund', 'shipping', 'order'] },
      autoResponses: {
        shipping: 'Your order typically ships within 2-3 business days...',
      },
    },
    isOfficial: true,
    isPublic: true,
  },
]

await prisma.agentTemplate.createMany({ data: templates })
```

---

### 6. Cost Tracking Dashboard

**Priority**: Low-Medium
**Effort**: Low
**Impact**: Medium (transparency)

The Analytics model already tracks `estimatedCost`. Enhance the analytics dashboard:

```typescript
// Add to analytics page
function CostTracker() {
  const { data: costs } = trpc.analytics.costs.useQuery({
    timeRange: 30,
  })

  const totalCost = costs?.reduce((sum, day) => sum + day.estimatedCost, 0) || 0
  const avgDailyCost = totalCost / 30

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost Analysis</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <p className="text-sm text-muted-foreground">Total (30 days)</p>
            <p className="text-3xl font-bold">${totalCost.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Average per day</p>
            <p className="text-xl">${avgDailyCost.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Projected monthly</p>
            <p className="text-xl">${(avgDailyCost * 30).toFixed(2)}</p>
          </div>
        </div>

        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={costs}>
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line dataKey="estimatedCost" stroke="#8884d8" />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
```

---

### 7. Bulk Operations UI

**Priority**: Low
**Effort**: Low
**Impact**: Medium (power users)

Add multi-select to agent list:

```typescript
function AgentList() {
  const [selected, setSelected] = useState<string[]>([])
  const bulkDelete = trpc.agent.bulkDelete.useMutation()
  const bulkToggle = trpc.agent.bulkToggle.useMutation()

  return (
    <div>
      {selected.length > 0 && (
        <div className="flex gap-2 mb-4">
          <Button
            onClick={() => bulkToggle.mutate({ ids: selected, enabled: false })}
          >
            Disable Selected ({selected.length})
          </Button>
          <Button
            variant="destructive"
            onClick={() => bulkDelete.mutate({ ids: selected })}
          >
            Delete Selected
          </Button>
        </div>
      )}

      {agents.map((agent) => (
        <div key={agent.id} className="flex items-center gap-2">
          <Checkbox
            checked={selected.includes(agent.id)}
            onCheckedChange={(checked) => {
              setSelected(checked
                ? [...selected, agent.id]
                : selected.filter((id) => id !== agent.id)
              )
            }}
          />
          <AgentCard agent={agent} />
        </div>
      ))}
    </div>
  )
}
```

---

### 8. Advanced Search

**Priority**: Medium
**Effort**: Medium
**Impact**: High (usability at scale)

Implement full-text search with Postgres:

```sql
-- Add to migration
CREATE INDEX email_search_idx ON "Email" USING gin(to_tsvector('english', subject || ' ' || COALESCE(body, '')));
```

```typescript
// Update email router
list: protectedProcedure
  .input(z.object({
    search: z.string().optional(),
    tier: z.number().optional(),
    agentId: z.string().optional(),
  }))
  .query(async ({ ctx, input }) => {
    const where: Prisma.EmailWhereInput = {
      agent: { userId: ctx.session.user.id },
    }

    if (input.search) {
      where.OR = [
        { subject: { contains: input.search, mode: 'insensitive' } },
        { from: { contains: input.search, mode: 'insensitive' } },
        { body: { contains: input.search, mode: 'insensitive' } },
      ]
    }

    if (input.tier) where.tier = input.tier
    if (input.agentId) where.agentId = input.agentId

    return prisma.email.findMany({ where, orderBy: { receivedAt: 'desc' } })
  })
```

---

### 9. Email Thread Visualization

**Priority**: Low
**Effort**: High
**Impact**: Medium (UX improvement)

Group emails by `gmailThreadId`:

```typescript
function EmailThread({ threadId }: { threadId: string }) {
  const { data: emails } = trpc.email.getThread.useQuery({ threadId })

  return (
    <div className="space-y-2">
      {emails?.map((email, index) => (
        <div
          key={email.id}
          className={`ml-${index * 4} border-l-2 pl-4`}
        >
          <p className="font-medium">{email.subject}</p>
          <p className="text-sm text-muted-foreground">{email.from}</p>
          <p className="text-sm">{email.snippet}</p>
        </div>
      ))}
    </div>
  )
}
```

---

### 10. Sentry Integration

**Priority**: High
**Effort**: Low
**Impact**: High (production monitoring)

```bash
npm install @sentry/nextjs
npx @sentry/wizard@latest -i nextjs
```

Update `sentry.client.config.ts`:

```typescript
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  tracesSampleRate: 0.1,
  environment: process.env.NODE_ENV,
  integrations: [
    new Sentry.BrowserTracing(),
    new Sentry.Replay(),
  ],
})
```

The error boundaries already log to Sentry if available!

---

### 11. Storybook

**Priority**: Low
**Effort**: Medium
**Impact**: Medium (developer experience)

```bash
npx storybook@latest init
```

Create stories:

```typescript
// src/components/ui/button.stories.tsx
import type { Meta, StoryObj } from '@storybook/react'
import { Button } from './button'

const meta: Meta<typeof Button> = {
  title: 'UI/Button',
  component: Button,
}

export default meta
type Story = StoryObj<typeof Button>

export const Default: Story = {
  args: {
    children: 'Click me',
  },
}

export const Destructive: Story = {
  args: {
    variant: 'destructive',
    children: 'Delete',
  },
}
```

---

### 12. Husky Git Hooks

**Priority**: Low
**Effort**: Low
**Impact**: Medium (code quality)

```bash
npm install --save-dev husky lint-staged
npx husky init
```

```json
// package.json
{
  "lint-staged": {
    "*.{ts,tsx}": ["eslint --fix", "prettier --write"],
    "*.{json,md}": ["prettier --write"]
  }
}
```

```bash
# .husky/pre-commit
npm run lint-staged
npm run type-check
```

---

### 13. Redis Session Storage

**Priority**: Low (unless high traffic)
**Effort**: Medium
**Impact**: High (scalability)

```bash
npm install @upstash/redis ioredis
```

```typescript
// src/lib/redis.ts
import { Redis } from '@upstash/redis'

export const redis = new Redis({
  url: process.env.UPSTASH_REDIS_REST_URL,
  token: process.env.UPSTASH_REDIS_REST_TOKEN,
})

// Update NextAuth adapter
import { UpstashRedisAdapter } from '@auth/upstash-redis-adapter'

export const authOptions: NextAuthOptions = {
  adapter: UpstashRedisAdapter(redis),
  // ...
}
```

---

### 14. Background Job Queue

**Priority**: Medium (for webhook retries, email processing)
**Effort**: High
**Impact**: High (reliability)

```bash
npm install bullmq ioredis
```

```typescript
// src/lib/queue.ts
import { Queue, Worker } from 'bullmq'
import { redis } from './redis'

export const webhookQueue = new Queue('webhooks', { connection: redis })

// Worker process
const worker = new Worker(
  'webhooks',
  async (job) => {
    const { webhookId, event, payload } = job.data
    await deliverWebhook(webhookId, event, payload)
  },
  { connection: redis }
)

// Add job
await webhookQueue.add('deliver', {
  webhookId: webhook.id,
  event: 'email_received',
  payload: { emailId: email.id },
}, {
  attempts: 3,
  backoff: { type: 'exponential', delay: 2000 },
})
```

---

## 🎯 **RECOMMENDED IMPLEMENTATION ORDER**

1. **Week 1**: Unit tests, Sentry integration, Husky
2. **Week 2**: Audit logs, Webhooks
3. **Week 3**: Email notifications, Templates
4. **Week 4**: Advanced search, Bulk operations
5. **Week 5**: Cost tracking, Thread visualization

---

## 📊 **IMPACT MATRIX**

| Feature | Priority | Effort | Impact | When to Implement |
|---------|----------|--------|--------|-------------------|
| Unit Tests | High | Medium | High | Immediately |
| Sentry | High | Low | High | Immediately |
| Audit Logs | High | Medium | High | Week 1-2 |
| Webhooks | Medium | High | High | Week 2-3 |
| Email Notifications | Medium | Low | High | Week 2 |
| Templates | Medium | Low | Medium | Week 3 |
| Advanced Search | Medium | Medium | High | Week 4 |
| Bulk Operations | Low | Low | Medium | Week 4 |
| Cost Tracking | Low | Low | Medium | Week 5 |
| Thread Viz | Low | High | Medium | Future |
| Storybook | Low | Medium | Medium | Future |
| Redis Sessions | Low | Medium | High | When scaling |
| Background Jobs | Medium | High | High | When scaling |

---

## 🛠️ **QUICK WIN FEATURES** (< 1 hour each)

1. Add theme toggle to navigation bar
2. Show total cost on analytics page
3. Add "Export as CSV" to analytics
4. Add keyboard shortcuts (Cmd+K for search)
5. Add "Recently Deleted" view (soft deletes)
6. Add agent status badges to dashboard
7. Add "Quick Actions" dropdown on email list
8. Add loading states to all buttons

---

All models and infrastructure for these features are ready in the database schema!
