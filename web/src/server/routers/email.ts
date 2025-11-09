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

  // Advanced search with multiple filters
  advancedSearch: protectedProcedure
    .input(
      z.object({
        query: z.string().optional(),
        agentIds: z.array(z.string()).optional(),
        tiers: z.array(z.number().min(1).max(4)).optional(),
        statuses: z.array(z.string()).optional(),
        dateFrom: z.date().optional(),
        dateTo: z.date().optional(),
        hasAttachments: z.boolean().optional(),
        limit: z.number().min(1).max(100).default(50),
        cursor: z.string().optional(),
      })
    )
    .query(async ({ ctx, input }) => {
      const where: any = {
        agent: {
          userId: ctx.session.user.id,
        },
      }

      // Text search
      if (input.query && input.query.length > 0) {
        where.OR = [
          { subject: { contains: input.query, mode: 'insensitive' } },
          { from: { contains: input.query, mode: 'insensitive' } },
          { to: { contains: input.query, mode: 'insensitive' } },
          { body: { contains: input.query, mode: 'insensitive' } },
        ]
      }

      // Agent filter
      if (input.agentIds && input.agentIds.length > 0) {
        where.agentId = { in: input.agentIds }
      }

      // Tier filter
      if (input.tiers && input.tiers.length > 0) {
        where.tier = { in: input.tiers }
      }

      // Status filter
      if (input.statuses && input.statuses.length > 0) {
        where.status = { in: input.statuses }
      }

      // Date range filter
      if (input.dateFrom || input.dateTo) {
        where.receivedAt = {}
        if (input.dateFrom) {
          where.receivedAt.gte = input.dateFrom
        }
        if (input.dateTo) {
          where.receivedAt.lte = input.dateTo
        }
      }

      // Attachments filter
      if (input.hasAttachments !== undefined) {
        if (input.hasAttachments) {
          where.attachments = { not: null }
        } else {
          where.attachments = null
        }
      }

      const emails = await ctx.prisma.email.findMany({
        where,
        take: input.limit + 1,
        cursor: input.cursor ? { id: input.cursor } : undefined,
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
        },
      })

      let nextCursor: typeof input.cursor | undefined = undefined
      if (emails.length > input.limit) {
        const nextItem = emails.pop()
        nextCursor = nextItem!.id
      }

      // Get total count for this search
      const totalCount = await ctx.prisma.email.count({ where })

      return {
        emails,
        nextCursor,
        totalCount,
      }
    }),

  // Saved Searches Management
  getSavedSearches: protectedProcedure.query(async ({ ctx }) => {
    return ctx.prisma.savedEmailSearch.findMany({
      where: {
        userId: ctx.session.user.id,
      },
      orderBy: [{ usageCount: 'desc' }, { createdAt: 'desc' }],
    })
  }),

  createSavedSearch: protectedProcedure
    .input(
      z.object({
        name: z.string().min(1).max(100),
        description: z.string().optional(),
        filters: z.object({
          query: z.string().optional(),
          agentIds: z.array(z.string()).optional(),
          tiers: z.array(z.number().min(1).max(4)).optional(),
          statuses: z.array(z.string()).optional(),
          dateFrom: z.date().optional(),
          dateTo: z.date().optional(),
          hasAttachments: z.boolean().optional(),
        }),
      })
    )
    .mutation(async ({ ctx, input }) => {
      return ctx.prisma.savedEmailSearch.create({
        data: {
          userId: ctx.session.user.id,
          name: input.name,
          description: input.description,
          filters: input.filters as any,
        },
      })
    }),

  updateSavedSearch: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        name: z.string().min(1).max(100).optional(),
        description: z.string().optional(),
        filters: z
          .object({
            query: z.string().optional(),
            agentIds: z.array(z.string()).optional(),
            tiers: z.array(z.number().min(1).max(4)).optional(),
            statuses: z.array(z.string()).optional(),
            dateFrom: z.date().optional(),
            dateTo: z.date().optional(),
            hasAttachments: z.boolean().optional(),
          })
          .optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const { id, ...data } = input

      // Ensure user owns this saved search
      const search = await ctx.prisma.savedEmailSearch.findFirst({
        where: {
          id,
          userId: ctx.session.user.id,
        },
      })

      if (!search) {
        throw new Error('Saved search not found')
      }

      return ctx.prisma.savedEmailSearch.update({
        where: { id },
        data: data.filters ? { ...data, filters: data.filters as any } : data,
      })
    }),

  deleteSavedSearch: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      // Ensure user owns this saved search
      const search = await ctx.prisma.savedEmailSearch.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id,
        },
      })

      if (!search) {
        throw new Error('Saved search not found')
      }

      return ctx.prisma.savedEmailSearch.delete({
        where: { id: input.id },
      })
    }),

  useSavedSearch: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      // Ensure user owns this saved search
      const search = await ctx.prisma.savedEmailSearch.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id,
        },
      })

      if (!search) {
        throw new Error('Saved search not found')
      }

      // Increment usage count and update last used timestamp
      return ctx.prisma.savedEmailSearch.update({
        where: { id: input.id },
        data: {
          usageCount: { increment: 1 },
          lastUsedAt: new Date(),
        },
      })
    }),
})
