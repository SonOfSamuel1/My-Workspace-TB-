'use client'

import { use } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { trpc } from '@/lib/trpc/client'
import { ArrowLeft, History } from 'lucide-react'
import { AgentVersionHistory } from '@/components/agent-version-history'

export default function AgentVersionsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  const { data: agent, isLoading } = trpc.agent.get.useQuery({ id })

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <p className="mt-4 text-muted-foreground">Loading agent...</p>
        </div>
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="container mx-auto p-8 max-w-4xl">
        <div className="text-center">
          <h2 className="text-2xl font-bold">Agent not found</h2>
          <Link href="/dashboard">
            <Button className="mt-4">Back to Dashboard</Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4 sm:p-8 max-w-6xl">
      <div className="mb-6 flex items-center justify-between">
        <Link href={`/agents/${id}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Agent
          </Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <History className="h-6 w-6 text-primary" />
            <div>
              <CardTitle>Version History</CardTitle>
              <CardDescription>
                Track all configuration changes for {agent.name} ({agent.agentEmail})
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <AgentVersionHistory agentId={id} />
        </CardContent>
      </Card>

      {/* Help Section */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-lg">How Version Control Works</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div>
            <strong className="text-foreground">Automatic Snapshots:</strong> Every time you
            update the agent configuration, a new version is automatically created with a
            snapshot of all settings.
          </div>
          <div>
            <strong className="text-foreground">Compare Versions:</strong> Select any two
            versions (mark them as A and B) to see a detailed diff of what changed between
            them.
          </div>
          <div>
            <strong className="text-foreground">Rollback:</strong> If you need to undo changes,
            you can rollback to any previous version. This creates a new version with the old
            settings, so you can always go forward again if needed.
          </div>
          <div>
            <strong className="text-foreground">Change Tracking:</strong> Each version includes
            a summary of what changed, who made the change, and when it happened.
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
