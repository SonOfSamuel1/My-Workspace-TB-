import { z } from 'zod'
import { createTRPCRouter, protectedProcedure } from '../trpc'
import {
  createVersionSnapshot,
  getVersionHistory,
  getVersion,
  rollbackToVersion,
  compareVersions,
} from '@/lib/agent-versioning'

export const agentRouter = createTRPCRouter({
  // Get all agents for the current user
  list: protectedProcedure.query(async ({ ctx }) => {
    return ctx.prisma.agent.findMany({
      where: {
        userId: ctx.session.user.id,
      },
      orderBy: {
        createdAt: 'desc',
      },
      include: {
        _count: {
          select: {
            emails: true,
            actions: true,
          },
        },
      },
    })
  }),

  // Get a single agent by ID
  get: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const agent = await ctx.prisma.agent.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id, // Ensure user owns this agent
        },
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
        throw new Error('Agent not found')
      }

      return agent
    }),

  // Create a new agent
  create: protectedProcedure
    .input(
      z.object({
        name: z.string().min(1).max(100),
        agentEmail: z.string().email(),
        description: z.string().optional(),
        config: z.object({
          timezone: z.string().default('America/New_York'),
          businessHours: z.object({
            start: z.number().min(0).max(23).default(9),
            end: z.number().min(0).max(23).default(17),
          }),
          offLimitsContacts: z.array(z.string().email()).default([]),
          communicationStyle: z.string().default('professional'),
          tierRules: z.any().optional(),
        }),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Check if agent email is already in use
      const existing = await ctx.prisma.agent.findUnique({
        where: { agentEmail: input.agentEmail },
      })

      if (existing) {
        throw new Error('This agent email is already in use')
      }

      return ctx.prisma.agent.create({
        data: {
          userId: ctx.session.user.id,
          name: input.name,
          agentEmail: input.agentEmail,
          description: input.description,
          config: input.config,
        },
      })
    }),

  // Update an agent
  update: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        name: z.string().min(1).max(100).optional(),
        description: z.string().optional(),
        enabled: z.boolean().optional(),
        config: z.any().optional(),
        changeReason: z.string().optional(), // Optional reason for the change
      })
    )
    .mutation(async ({ ctx, input }) => {
      const { id, changeReason, ...data } = input

      // Ensure user owns this agent
      const agent = await ctx.prisma.agent.findFirst({
        where: {
          id,
          userId: ctx.session.user.id,
        },
      })

      if (!agent) {
        throw new Error('Agent not found')
      }

      // If config is being updated, create a version snapshot
      if (input.config) {
        await createVersionSnapshot(
          id,
          input.config,
          ctx.session.user.id,
          changeReason
        )
      }

      return ctx.prisma.agent.update({
        where: { id },
        data,
      })
    }),

  // Delete an agent
  delete: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      // Ensure user owns this agent
      const agent = await ctx.prisma.agent.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id,
        },
      })

      if (!agent) {
        throw new Error('Agent not found')
      }

      return ctx.prisma.agent.delete({
        where: { id: input.id },
      })
    }),

  // Get agent statistics
  stats: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const agent = await ctx.prisma.agent.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id,
        },
      })

      if (!agent) {
        throw new Error('Agent not found')
      }

      const [totalEmails, tierCounts, recentActivity] = await Promise.all([
        ctx.prisma.email.count({
          where: { agentId: input.id },
        }),
        ctx.prisma.email.groupBy({
          by: ['tier'],
          where: { agentId: input.id },
          _count: true,
        }),
        ctx.prisma.email.findMany({
          where: { agentId: input.id },
          orderBy: { receivedAt: 'desc' },
          take: 10,
          select: {
            id: true,
            subject: true,
            from: true,
            tier: true,
            status: true,
            receivedAt: true,
          },
        }),
      ])

      const tierDistribution = {
        tier1: tierCounts.find((t) => t.tier === 1)?._count ?? 0,
        tier2: tierCounts.find((t) => t.tier === 2)?._count ?? 0,
        tier3: tierCounts.find((t) => t.tier === 3)?._count ?? 0,
        tier4: tierCounts.find((t) => t.tier === 4)?._count ?? 0,
      }

      return {
        totalEmails,
        tierDistribution,
        recentActivity,
      }
    }),

  // Get version history for an agent
  getVersionHistory: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        limit: z.number().min(1).max(100).default(50),
      })
    )
    .query(async ({ ctx, input }) => {
      // Ensure user owns this agent
      const agent = await ctx.prisma.agent.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id,
        },
      })

      if (!agent) {
        throw new Error('Agent not found')
      }

      return getVersionHistory(input.id, input.limit)
    }),

  // Get a specific version
  getVersion: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        version: z.number().int().positive(),
      })
    )
    .query(async ({ ctx, input }) => {
      // Ensure user owns this agent
      const agent = await ctx.prisma.agent.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id,
        },
      })

      if (!agent) {
        throw new Error('Agent not found')
      }

      const version = await getVersion(input.id, input.version)

      if (!version) {
        throw new Error('Version not found')
      }

      return version
    }),

  // Compare two versions
  compareVersions: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        versionA: z.number().int().positive(),
        versionB: z.number().int().positive(),
      })
    )
    .query(async ({ ctx, input }) => {
      // Ensure user owns this agent
      const agent = await ctx.prisma.agent.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id,
        },
      })

      if (!agent) {
        throw new Error('Agent not found')
      }

      return compareVersions(input.id, input.versionA, input.versionB)
    }),

  // Rollback to a specific version
  rollback: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        version: z.number().int().positive(),
        reason: z.string().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Ensure user owns this agent
      const agent = await ctx.prisma.agent.findFirst({
        where: {
          id: input.id,
          userId: ctx.session.user.id,
        },
      })

      if (!agent) {
        throw new Error('Agent not found')
      }

      return rollbackToVersion(
        input.id,
        input.version,
        ctx.session.user.id,
        input.reason
      )
    }),
})
