import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { z } from 'zod'

// Schema for email sync data
const emailSyncSchema = z.object({
  agentEmail: z.string().email(),
  emails: z.array(
    z.object({
      gmailId: z.string(),
      gmailThreadId: z.string().optional(),
      subject: z.string(),
      from: z.string(),
      to: z.string().optional(),
      snippet: z.string().optional(),
      body: z.string().optional(),
      tier: z.number().min(1).max(4),
      reasoning: z.string(),
      confidence: z.number().min(0).max(1).optional(),
      status: z.enum(['processed', 'pending_approval', 'escalated', 'flagged']),
      receivedAt: z.string(),
      processedAt: z.string().optional(),
      actions: z.array(
        z.object({
          type: z.string(),
          data: z.any(),
          requiresApproval: z.boolean().optional(),
          toolName: z.string().optional(),
          toolInput: z.any().optional(),
          toolOutput: z.any().optional(),
          status: z.string().optional(),
        })
      ).optional(),
    })
  ),
})

/**
 * Sync endpoint for CLI to push email processing results
 * POST /api/integration/sync
 *
 * Authentication: API key in header (X-API-Key)
 */
export async function POST(req: NextRequest) {
  try {
    // Check API key (simple auth for MVP - use proper auth in production)
    const apiKey = req.headers.get('X-API-Key')
    if (!apiKey || apiKey !== process.env.INTEGRATION_API_KEY) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    const body = await req.json()
    const { agentEmail, emails } = emailSyncSchema.parse(body)

    // Find agent by email
    const agent = await prisma.agent.findUnique({
      where: { agentEmail },
    })

    if (!agent) {
      return NextResponse.json(
        { error: 'Agent not found' },
        { status: 404 }
      )
    }

    // Sync emails
    const results = await Promise.all(
      emails.map(async (emailData) => {
        // Check if email already exists (by gmailId)
        const existing = await prisma.email.findFirst({
          where: {
            agentId: agent.id,
            gmailId: emailData.gmailId,
          },
        })

        if (existing) {
          // Update existing email
          return prisma.email.update({
            where: { id: existing.id },
            data: {
              subject: emailData.subject,
              from: emailData.from,
              to: emailData.to,
              snippet: emailData.snippet,
              body: emailData.body,
              tier: emailData.tier,
              reasoning: emailData.reasoning,
              confidence: emailData.confidence,
              status: emailData.status,
              processedAt: emailData.processedAt
                ? new Date(emailData.processedAt)
                : null,
              processed: emailData.status === 'processed',
            },
          })
        }

        // Create new email
        const email = await prisma.email.create({
          data: {
            agentId: agent.id,
            gmailId: emailData.gmailId,
            gmailThreadId: emailData.gmailThreadId,
            subject: emailData.subject,
            from: emailData.from,
            to: emailData.to,
            snippet: emailData.snippet,
            body: emailData.body,
            tier: emailData.tier,
            reasoning: emailData.reasoning,
            confidence: emailData.confidence,
            status: emailData.status,
            receivedAt: new Date(emailData.receivedAt),
            processedAt: emailData.processedAt
              ? new Date(emailData.processedAt)
              : null,
            processed: emailData.status === 'processed',
          },
        })

        // Create actions if provided
        if (emailData.actions && emailData.actions.length > 0) {
          await Promise.all(
            emailData.actions.map((actionData) =>
              prisma.agentAction.create({
                data: {
                  agentId: agent.id,
                  emailId: email.id,
                  type: actionData.type,
                  data: actionData.data,
                  requiresApproval: actionData.requiresApproval || false,
                  toolName: actionData.toolName,
                  toolInput: actionData.toolInput,
                  toolOutput: actionData.toolOutput,
                  status: actionData.status || 'completed',
                },
              })
            )
          )
        }

        return email
      })
    )

    // Update agent lastRunAt
    await prisma.agent.update({
      where: { id: agent.id },
      data: { lastRunAt: new Date() },
    })

    return NextResponse.json({
      success: true,
      synced: results.length,
      agentId: agent.id,
    })
  } catch (error) {
    console.error('Sync error:', error)

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.errors },
        { status: 400 }
      )
    }

    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * Get agent configuration by email
 * GET /api/integration/sync?agentEmail=...
 */
export async function GET(req: NextRequest) {
  try {
    const apiKey = req.headers.get('X-API-Key')
    if (!apiKey || apiKey !== process.env.INTEGRATION_API_KEY) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    const { searchParams } = new URL(req.url)
    const agentEmail = searchParams.get('agentEmail')

    if (!agentEmail) {
      return NextResponse.json(
        { error: 'agentEmail parameter required' },
        { status: 400 }
      )
    }

    const agent = await prisma.agent.findUnique({
      where: { agentEmail },
      include: {
        _count: {
          select: {
            emails: true,
            actions: true,
          },
        },
      },
    })

    if (!agent) {
      return NextResponse.json(
        { error: 'Agent not found' },
        { status: 404 }
      )
    }

    return NextResponse.json({
      id: agent.id,
      name: agent.name,
      agentEmail: agent.agentEmail,
      enabled: agent.enabled,
      config: agent.config,
      lastRunAt: agent.lastRunAt,
      stats: {
        totalEmails: agent._count.emails,
        totalActions: agent._count.actions,
      },
    })
  } catch (error) {
    console.error('Get agent error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
