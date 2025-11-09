import { z } from 'zod'
import { createTRPCRouter, protectedProcedure } from '../trpc'

export const emailRouter = createTRPCRouter({
  // List emails with pagination and filters
  list: protectedProcedure
    .input(
      z.object({
        agentId: z.string(),
        tier: z.number().min(1).max(4).optional(),
        status: z.string().optional(),
        limit: z.number().min(1).max(100).default(50),
        cursor: z.string().optional(),
      })
    )
    .query(async ({ ctx, input }) => {
      // Verify user owns this agent
      const agent = await ctx.prisma.agent.findFirst({
        where: {
          id: input.agentId,
          userId: ctx.session.user.id,
        },
      })

      if (!agent) {
        throw new Error('Agent not found')
      }

      const where = {
        agentId: input.agentId,
        ...(input.tier && { tier: input.tier }),
        ...(input.status && { status: input.status }),
      }

      const emails = await ctx.prisma.email.findMany({
        where,
        take: input.limit + 1,
        cursor: input.cursor ? { id: input.cursor } : undefined,
        orderBy: {
          receivedAt: 'desc',
        },
        include: {
          actions: {
            orderBy: {
              createdAt: 'desc',
            },
            take: 5,
          },
        },
      })

      let nextCursor: typeof input.cursor | undefined = undefined
      if (emails.length > input.limit) {
        const nextItem = emails.pop()
        nextCursor = nextItem!.id
      }

      return {
        emails,
        nextCursor,
      }
    }),

  // Get a single email by ID
  get: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const email = await ctx.prisma.email.findFirst({
        where: {
          id: input.id,
        },
        include: {
          agent: {
            select: {
              id: true,
              userId: true,
              name: true,
            },
          },
          actions: {
            orderBy: {
              createdAt: 'desc',
            },
          },
        },
      })

      if (!email || email.agent.userId !== ctx.session.user.id) {
        throw new Error('Email not found')
      }

      return email
    }),

  // Get pending approvals
  pendingApprovals: protectedProcedure
    .input(
      z.object({
        agentId: z.string().optional(),
      })
    )
    .query(async ({ ctx, input }) => {
      const where: any = {
        agent: {
          userId: ctx.session.user.id,
        },
        status: 'pending_approval',
      }

      if (input.agentId) {
        where.agentId = input.agentId
      }

      return ctx.prisma.email.findMany({
        where,
        orderBy: {
          receivedAt: 'desc',
        },
        include: {
          agent: {
            select: {
              id: true,
              name: true,
            },
          },
          actions: {
            where: {
              type: 'draft_created',
              requiresApproval: true,
            },
            orderBy: {
              createdAt: 'desc',
            },
            take: 1,
          },
        },
      })
    }),

  // Search emails
  search: protectedProcedure
    .input(
      z.object({
        agentId: z.string().optional(),
        query: z.string().min(1),
        limit: z.number().min(1).max(100).default(20),
      })
    )
    .query(async ({ ctx, input }) => {
      const where: any = {
        agent: {
          userId: ctx.session.user.id,
        },
        OR: [
          { subject: { contains: input.query, mode: 'insensitive' } },
          { from: { contains: input.query, mode: 'insensitive' } },
          { body: { contains: input.query, mode: 'insensitive' } },
        ],
      }

      if (input.agentId) {
        where.agentId = input.agentId
      }

      return ctx.prisma.email.findMany({
        where,
        take: input.limit,
        orderBy: {
          receivedAt: 'desc',
        },
        select: {
          id: true,
          subject: true,
          from: true,
          tier: true,
          status: true,
          receivedAt: true,
          snippet: true,
          agent: {
            select: {
              id: true,
              name: true,
            },
          },
        },
      })
    }),
})
