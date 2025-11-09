import { z } from 'zod'
import { createTRPCRouter, protectedProcedure } from '../trpc'

export const actionRouter = createTRPCRouter({
  // List actions for an agent or email
  list: protectedProcedure
    .input(
      z.object({
        agentId: z.string().optional(),
        emailId: z.string().optional(),
        type: z.string().optional(),
        requiresApproval: z.boolean().optional(),
        limit: z.number().min(1).max(100).default(50),
      })
    )
    .query(async ({ ctx, input }) => {
      const where: any = {
        agent: {
          userId: ctx.session.user.id,
        },
      }

      if (input.agentId) where.agentId = input.agentId
      if (input.emailId) where.emailId = input.emailId
      if (input.type) where.type = input.type
      if (input.requiresApproval !== undefined)
        where.requiresApproval = input.requiresApproval

      return ctx.prisma.agentAction.findMany({
        where,
        take: input.limit,
        orderBy: {
          createdAt: 'desc',
        },
        include: {
          email: {
            select: {
              id: true,
              subject: true,
              from: true,
            },
          },
          agent: {
            select: {
              id: true,
              name: true,
            },
          },
        },
      })
    }),

  // Approve an action
  approve: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        modifications: z.any().optional(), // Allow editing the draft before approving
      })
    )
    .mutation(async ({ ctx, input }) => {
      const action = await ctx.prisma.agentAction.findFirst({
        where: {
          id: input.id,
        },
        include: {
          agent: {
            select: {
              userId: true,
            },
          },
          email: true,
        },
      })

      if (!action || action.agent.userId !== ctx.session.user.id) {
        throw new Error('Action not found')
      }

      if (!action.requiresApproval) {
        throw new Error('This action does not require approval')
      }

      // Update action to approved
      const updatedAction = await ctx.prisma.agentAction.update({
        where: { id: input.id },
        data: {
          approved: true,
          approvedAt: new Date(),
          approvedBy: ctx.session.user.id,
          ...(input.modifications && { data: input.modifications }),
        },
      })

      // Update email status
      if (action.email) {
        await ctx.prisma.email.update({
          where: { id: action.emailId! },
          data: { status: 'processed' },
        })
      }

      // TODO: Trigger actual email sending or action execution here
      // This would integrate with the existing email-agent system

      return updatedAction
    }),

  // Reject an action
  reject: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        reason: z.string().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const action = await ctx.prisma.agentAction.findFirst({
        where: {
          id: input.id,
        },
        include: {
          agent: {
            select: {
              userId: true,
            },
          },
        },
      })

      if (!action || action.agent.userId !== ctx.session.user.id) {
        throw new Error('Action not found')
      }

      return ctx.prisma.agentAction.update({
        where: { id: input.id },
        data: {
          approved: false,
          approvedAt: new Date(),
          approvedBy: ctx.session.user.id,
          status: 'failed',
          error: input.reason || 'Rejected by user',
        },
      })
    }),

  // Bulk approve actions
  bulkApprove: protectedProcedure
    .input(
      z.object({
        ids: z.array(z.string()),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Verify all actions belong to the user
      const actions = await ctx.prisma.agentAction.findMany({
        where: {
          id: { in: input.ids },
          agent: {
            userId: ctx.session.user.id,
          },
          requiresApproval: true,
          approved: null,
        },
      })

      if (actions.length !== input.ids.length) {
        throw new Error('Some actions were not found or cannot be approved')
      }

      // Update all actions
      const result = await ctx.prisma.agentAction.updateMany({
        where: {
          id: { in: input.ids },
        },
        data: {
          approved: true,
          approvedAt: new Date(),
          approvedBy: ctx.session.user.id,
        },
      })

      // Update associated emails
      const emailIds = actions
        .map((a) => a.emailId)
        .filter((id): id is string => id !== null)

      if (emailIds.length > 0) {
        await ctx.prisma.email.updateMany({
          where: {
            id: { in: emailIds },
          },
          data: {
            status: 'processed',
          },
        })
      }

      return result
    }),
})
