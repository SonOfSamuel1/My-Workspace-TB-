import { z } from 'zod'
import { createTRPCRouter, protectedProcedure } from '../trpc'
import { subDays, startOfDay, endOfDay } from 'date-fns'

export const analyticsRouter = createTRPCRouter({
  // Get overview stats for dashboard
  overview: protectedProcedure
    .input(
      z.object({
        agentId: z.string().optional(),
        days: z.number().min(1).max(90).default(7),
      })
    )
    .query(async ({ ctx, input }) => {
      const where: any = {
        agent: {
          userId: ctx.session.user.id,
        },
        receivedAt: {
          gte: subDays(new Date(), input.days),
        },
      }

      if (input.agentId) {
        where.agentId = input.agentId
      }

      const [totalEmails, tierDistribution, statusDistribution, actionTypes] =
        await Promise.all([
          ctx.prisma.email.count({ where }),
          ctx.prisma.email.groupBy({
            by: ['tier'],
            where,
            _count: true,
          }),
          ctx.prisma.email.groupBy({
            by: ['status'],
            where,
            _count: true,
          }),
          ctx.prisma.agentAction.groupBy({
            by: ['type'],
            where: {
              agent: {
                userId: ctx.session.user.id,
              },
              ...(input.agentId && { agentId: input.agentId }),
              createdAt: {
                gte: subDays(new Date(), input.days),
              },
            },
            _count: true,
          }),
        ])

      return {
        totalEmails,
        tierDistribution: {
          tier1: tierDistribution.find((t) => t.tier === 1)?._count ?? 0,
          tier2: tierDistribution.find((t) => t.tier === 2)?._count ?? 0,
          tier3: tierDistribution.find((t) => t.tier === 3)?._count ?? 0,
          tier4: tierDistribution.find((t) => t.tier === 4)?._count ?? 0,
        },
        statusDistribution: statusDistribution.map((s) => ({
          status: s.status,
          count: s._count,
        })),
        actionTypes: actionTypes.map((a) => ({
          type: a.type,
          count: a._count,
        })),
      }
    }),

  // Get time series data for charts
  timeSeries: protectedProcedure
    .input(
      z.object({
        agentId: z.string().optional(),
        days: z.number().min(1).max(90).default(30),
      })
    )
    .query(async ({ ctx, input }) => {
      const startDate = startOfDay(subDays(new Date(), input.days))
      const endDate = endOfDay(new Date())

      const where: any = {
        agent: {
          userId: ctx.session.user.id,
        },
        receivedAt: {
          gte: startDate,
          lte: endDate,
        },
      }

      if (input.agentId) {
        where.agentId = input.agentId
      }

      // Get emails grouped by date and tier
      const emails = await ctx.prisma.email.findMany({
        where,
        select: {
          receivedAt: true,
          tier: true,
        },
      })

      // Group by date
      const dataByDate = new Map<string, any>()

      emails.forEach((email) => {
        const dateKey = startOfDay(email.receivedAt).toISOString()

        if (!dataByDate.has(dateKey)) {
          dataByDate.set(dateKey, {
            date: dateKey,
            total: 0,
            tier1: 0,
            tier2: 0,
            tier3: 0,
            tier4: 0,
          })
        }

        const data = dataByDate.get(dateKey)!
        data.total++
        data[`tier${email.tier}` as keyof typeof data]++
      })

      return Array.from(dataByDate.values()).sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
      )
    }),

  // Get top senders
  topSenders: protectedProcedure
    .input(
      z.object({
        agentId: z.string().optional(),
        days: z.number().min(1).max(90).default(30),
        limit: z.number().min(1).max(50).default(10),
      })
    )
    .query(async ({ ctx, input }) => {
      const where: any = {
        agent: {
          userId: ctx.session.user.id,
        },
        receivedAt: {
          gte: subDays(new Date(), input.days),
        },
      }

      if (input.agentId) {
        where.agentId = input.agentId
      }

      const senders = await ctx.prisma.email.groupBy({
        by: ['from'],
        where,
        _count: true,
        orderBy: {
          _count: {
            from: 'desc',
          },
        },
        take: input.limit,
      })

      return senders.map((s) => ({
        email: s.from,
        count: s._count,
      }))
    }),

  // Get response time metrics
  responseMetrics: protectedProcedure
    .input(
      z.object({
        agentId: z.string().optional(),
        days: z.number().min(1).max(90).default(7),
      })
    )
    .query(async ({ ctx, input }) => {
      const where: any = {
        agent: {
          userId: ctx.session.user.id,
        },
        receivedAt: {
          gte: subDays(new Date(), input.days),
        },
        processedAt: {
          not: null,
        },
      }

      if (input.agentId) {
        where.agentId = input.agentId
      }

      const emails = await ctx.prisma.email.findMany({
        where,
        select: {
          receivedAt: true,
          processedAt: true,
          tier: true,
        },
      })

      const responseTimes = emails.map((email) => {
        const responseTime =
          (email.processedAt!.getTime() - email.receivedAt.getTime()) /
          1000 /
          60 // minutes
        return {
          tier: email.tier,
          responseTime,
        }
      })

      const avgByTier = [1, 2, 3, 4].map((tier) => {
        const tierTimes = responseTimes.filter((rt) => rt.tier === tier)
        const avg =
          tierTimes.length > 0
            ? tierTimes.reduce((sum, rt) => sum + rt.responseTime, 0) /
              tierTimes.length
            : 0

        return {
          tier,
          avgResponseTime: avg,
          count: tierTimes.length,
        }
      })

      const overallAvg =
        responseTimes.length > 0
          ? responseTimes.reduce((sum, rt) => sum + rt.responseTime, 0) /
            responseTimes.length
          : 0

      return {
        overall: overallAvg,
        byTier: avgByTier,
      }
    }),

  // Get cost estimates (for Claude Code + OpenRouter)
  costEstimate: protectedProcedure
    .input(
      z.object({
        agentId: z.string().optional(),
        days: z.number().min(1).max(90).default(30),
      })
    )
    .query(async ({ ctx, input }) => {
      // Get analytics data for the period
      const where: any = {
        agentId: input.agentId,
        date: {
          gte: startOfDay(subDays(new Date(), input.days)),
        },
      }

      if (input.agentId) {
        const analytics = await ctx.prisma.analytics.findMany({
          where,
          select: {
            claudeTokens: true,
            openrouterTokens: true,
            estimatedCost: true,
          },
        })

        const totals = analytics.reduce(
          (acc, curr) => ({
            claudeTokens: acc.claudeTokens + curr.claudeTokens,
            openrouterTokens: acc.openrouterTokens + curr.openrouterTokens,
            estimatedCost: acc.estimatedCost + curr.estimatedCost,
          }),
          { claudeTokens: 0, openrouterTokens: 0, estimatedCost: 0 }
        )

        return totals
      }

      // If no agentId, sum across all user's agents
      const agents = await ctx.prisma.agent.findMany({
        where: {
          userId: ctx.session.user.id,
        },
        select: {
          id: true,
        },
      })

      const analytics = await ctx.prisma.analytics.findMany({
        where: {
          agentId: {
            in: agents.map((a) => a.id),
          },
          date: {
            gte: startOfDay(subDays(new Date(), input.days)),
          },
        },
        select: {
          claudeTokens: true,
          openrouterTokens: true,
          estimatedCost: true,
        },
      })

      const totals = analytics.reduce(
        (acc, curr) => ({
          claudeTokens: acc.claudeTokens + curr.claudeTokens,
          openrouterTokens: acc.openrouterTokens + curr.openrouterTokens,
          estimatedCost: acc.estimatedCost + curr.estimatedCost,
        }),
        { claudeTokens: 0, openrouterTokens: 0, estimatedCost: 0 }
      )

      return totals
    }),
})
