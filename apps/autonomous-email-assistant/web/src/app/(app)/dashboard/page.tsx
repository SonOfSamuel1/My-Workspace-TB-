'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { trpc } from '@/lib/trpc/client'
import { formatRelativeTime, getTierName } from '@/lib/utils'
import Link from 'next/link'
import { Mail, Activity, CheckCircle, AlertCircle } from 'lucide-react'

export default function DashboardPage() {
  const { data: agents, isLoading: agentsLoading } = trpc.agent.list.useQuery()
  const { data: pendingApprovals, isLoading: approvalsLoading } =
    trpc.email.pendingApprovals.useQuery({})

  if (agentsLoading || approvalsLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <p className="mt-4 text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  const totalAgents = agents?.length || 0
  const activeAgents = agents?.filter((a) => a.enabled).length || 0
  const totalPendingApprovals = pendingApprovals?.length || 0

  return (
    <div className="container mx-auto p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-2">
          Overview of your email agent activity
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Agents</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalAgents}</div>
            <p className="text-xs text-muted-foreground">
              {activeAgents} active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Pending Approvals
            </CardTitle>
            <AlertCircle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalPendingApprovals}</div>
            <p className="text-xs text-muted-foreground">
              Require your review
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Emails Processed (7d)
            </CardTitle>
            <Mail className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-</div>
            <p className="text-xs text-muted-foreground">
              Connect agents to see data
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Auto-handled (7d)
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">-</div>
            <p className="text-xs text-muted-foreground">
              Tier 2 autonomous responses
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Agents List */}
        <Card className="col-span-4">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Your Agents</CardTitle>
                <CardDescription>
                  Manage and monitor your email agents
                </CardDescription>
              </div>
              <Link href="/agents/new">
                <Button size="sm">Create Agent</Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent>
            {!agents || agents.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground mb-4">
                  No agents yet. Create your first agent to get started!
                </p>
                <Link href="/agents/new">
                  <Button>Create Your First Agent</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-4">
                {agents.map((agent) => (
                  <div
                    key={agent.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent transition-colors"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{agent.name}</h3>
                        {agent.enabled ? (
                          <Badge variant="tier2" className="text-xs">
                            Active
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs">
                            Disabled
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {agent.agentEmail}
                      </p>
                      <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                        <span>{agent._count.emails} emails</span>
                        <span>{agent._count.actions} actions</span>
                        {agent.lastRunAt && (
                          <span>
                            Last run: {formatRelativeTime(agent.lastRunAt)}
                          </span>
                        )}
                      </div>
                    </div>
                    <Link href={`/agents/${agent.id}`}>
                      <Button variant="outline" size="sm">
                        View
                      </Button>
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pending Approvals Sidebar */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle>Pending Approvals</CardTitle>
            <CardDescription>
              Draft responses awaiting your review
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!pendingApprovals || pendingApprovals.length === 0 ? (
              <div className="text-center py-8">
                <CheckCircle className="h-12 w-12 text-green-500 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">
                  All caught up! No pending approvals.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {pendingApprovals.slice(0, 5).map((email) => (
                  <div
                    key={email.id}
                    className="p-3 border rounded-lg hover:bg-accent transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge variant={`tier${email.tier}` as any}>
                            {getTierName(email.tier)}
                          </Badge>
                        </div>
                        <p className="text-sm font-medium mt-1 truncate">
                          {email.subject}
                        </p>
                        <p className="text-xs text-muted-foreground truncate">
                          From: {email.from}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatRelativeTime(email.receivedAt)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
                {pendingApprovals.length > 5 && (
                  <Link href="/approvals">
                    <Button variant="outline" className="w-full" size="sm">
                      View All ({pendingApprovals.length})
                    </Button>
                  </Link>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
