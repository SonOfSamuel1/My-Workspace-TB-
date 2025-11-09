'use client'

import { useState } from 'react'
import { Button } from './ui/button'
import { Pause, Play } from 'lucide-react'
import { trpc } from '@/lib/trpc/client'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from './ui/dialog'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import { useToast } from './ui/use-toast'
import { Badge } from './ui/badge'

interface AgentPauseControlsProps {
  agentId: string
  isPaused: boolean
  pauseReason?: string
  onStatusChange?: () => void
}

export function AgentPauseControls({
  agentId,
  isPaused,
  pauseReason,
  onStatusChange,
}: AgentPauseControlsProps) {
  const { toast } = useToast()
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')

  const utils = trpc.useContext()

  const pauseAgent = trpc.agent.pause.useMutation({
    onSuccess: () => {
      toast({ title: 'Agent paused successfully' })
      setOpen(false)
      setReason('')
      utils.agent.getById.invalidate({ id: agentId })
      onStatusChange?.()
    },
    onError: (error) => {
      toast({
        title: 'Failed to pause agent',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const resumeAgent = trpc.agent.resume.useMutation({
    onSuccess: () => {
      toast({ title: 'Agent resumed successfully' })
      utils.agent.getById.invalidate({ id: agentId })
      onStatusChange?.()
    },
    onError: (error) => {
      toast({
        title: 'Failed to resume agent',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const handlePause = () => {
    pauseAgent.mutate({ id: agentId, reason: reason || undefined })
  }

  const handleResume = () => {
    resumeAgent.mutate({ id: agentId })
  }

  if (isPaused) {
    return (
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
          Paused
        </Badge>
        {pauseReason && (
          <span className="text-sm text-muted-foreground" title={pauseReason}>
            ({pauseReason.length > 30 ? pauseReason.slice(0, 30) + '...' : pauseReason})
          </span>
        )}
        <Button
          size="sm"
          variant="outline"
          onClick={handleResume}
          disabled={resumeAgent.isLoading}
        >
          <Play className="mr-2 h-4 w-4" />
          {resumeAgent.isLoading ? 'Resuming...' : 'Resume'}
        </Button>
      </div>
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Pause className="mr-2 h-4 w-4" />
          Pause Agent
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Pause Agent</DialogTitle>
          <DialogDescription>
            The agent will stop processing emails until you resume it.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="reason">Reason (optional)</Label>
            <Textarea
              id="reason"
              placeholder="e.g., On vacation, testing new configuration, etc."
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              This helps you remember why the agent was paused.
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handlePause} disabled={pauseAgent.isLoading}>
            {pauseAgent.isLoading ? 'Pausing...' : 'Pause Agent'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// tRPC Mutations (add to src/server/routers/agent.ts)
/*
pause: protectedProcedure
  .input(z.object({
    id: z.string(),
    reason: z.string().optional(),
  }))
  .mutation(async ({ ctx, input }) => {
    const agent = await ctx.prisma.agent.update({
      where: {
        id: input.id,
        userId: ctx.session.user.id,
      },
      data: {
        enabled: false,
        config: {
          ...(agent.config as any),
          pausedAt: new Date().toISOString(),
          pauseReason: input.reason,
        },
      },
    })

    // Create audit log
    await ctx.prisma.auditLog.create({
      data: {
        userId: ctx.session.user.id,
        action: 'pause_agent',
        resource: 'agent',
        resourceId: input.id,
        newValue: { reason: input.reason },
      },
    })

    return agent
  }),

resume: protectedProcedure
  .input(z.object({ id: z.string() }))
  .mutation(async ({ ctx, input }) => {
    const agent = await ctx.prisma.agent.findUnique({
      where: { id: input.id },
    })

    const config = agent.config as any
    delete config.pausedAt
    delete config.pauseReason

    const updatedAgent = await ctx.prisma.agent.update({
      where: {
        id: input.id,
        userId: ctx.session.user.id,
      },
      data: {
        enabled: true,
        config,
      },
    })

    // Create audit log
    await ctx.prisma.auditLog.create({
      data: {
        userId: ctx.session.user.id,
        action: 'resume_agent',
        resource: 'agent',
        resourceId: input.id,
      },
    })

    return updatedAgent
  }),
*/
