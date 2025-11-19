import { createTRPCRouter } from '../trpc'
import { agentRouter } from './agent'
import { emailRouter } from './email'
import { actionRouter } from './action'
import { analyticsRouter } from './analytics'

/**
 * This is the primary router for your server.
 *
 * All routers added in /server/routers should be manually added here.
 */
export const appRouter = createTRPCRouter({
  agent: agentRouter,
  email: emailRouter,
  action: actionRouter,
  analytics: analyticsRouter,
})

// export type definition of API
export type AppRouter = typeof appRouter
