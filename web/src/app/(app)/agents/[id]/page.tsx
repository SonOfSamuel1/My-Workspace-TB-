'use client'

import { use } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { trpc } from '@/lib/trpc/client'
import { ArrowLeft, Mail, Settings, Activity, Power, PowerOff } from 'lucide-react'
import { formatRelativeTime, getTierName } from '@/lib/utils'

export default function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)

  const { data: agent, isLoading } = trpc.agent.get.useQuery({ id })
  const { data: stats } = trpc.agent.stats.useQuery({ id })
  const { data: emails } = trpc.email.list.useQuery({ agentId: id, limit: 20 })

  const utils = trpc.useUtils()
  const updateAgent = trpc.agent.update.useMutation({
    onSuccess: () => {
      utils.agent.get.invalidate({ id })
      utils.agent.list.invalidate()
    },
  })

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

  const config = agent.config as any

  const toggleEnabled = () => {
    updateAgent.mutate({
      id: agent.id,
      enabled: !agent.enabled,
    })
  }

  return (
    <div className="container mx-auto p-8 max-w-6xl">
      {/* Header */}
      <div className="mb-6">
        <Link href="/dashboard">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Dashboard
          </Button>
        </Link>
      </div>

      {/* Agent Header */}
      <div className="mb-8">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-4xl font-bold">{agent.name}</h1>
              {agent.enabled ? (
                <Badge variant="tier2" className="flex items-center gap-1">
                  <Power className="h-3 w-3" />
                  Active
                </Badge>
              ) : (
                <Badge variant="outline" className="flex items-center gap-1">
                  <PowerOff className="h-3 w-3" />
                  Disabled
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground">{agent.agentEmail}</p>
            {agent.description && (
              <p className="text-sm text-muted-foreground mt-2">{agent.description}</p>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant={agent.enabled ? 'outline' : 'default'}
              onClick={toggleEnabled}
              disabled={updateAgent.isPending}
            >
              {agent.enabled ? 'Disable' : 'Enable'}
            </Button>
            <Link href={`/agents/${agent.id}/edit`}>
              <Button variant="outline">
                <Settings className="h-4 w-4 mr-2" />
                Configure
              </Button>
            </Link>
          </div>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-4 gap-4 mt-6">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Emails</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.totalEmails}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Tier 1</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-500">
                  {stats.tierDistribution.tier1}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Tier 2</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">
                  {stats.tierDistribution.tier2}
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Tier 3</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-amber-500">
                  {stats.tierDistribution.tier3}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="emails" className="space-y-4">
        <TabsList>
          <TabsTrigger value="emails">
            <Mail className="h-4 w-4 mr-2" />
            Emails
          </TabsTrigger>
          <TabsTrigger value="activity">
            <Activity className="h-4 w-4 mr-2" />
            Activity
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="h-4 w-4 mr-2" />
            Settings
          </TabsTrigger>
        </TabsList>

        {/* Emails Tab */}
        <TabsContent value="emails">
          <Card>
            <CardHeader>
              <CardTitle>Recent Emails</CardTitle>
              <CardDescription>
                Latest emails processed by this agent
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!emails || emails.emails.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No emails processed yet
                </div>
              ) : (
                <div className="space-y-3">
                  {emails.emails.map((email) => (
                    <div
                      key={email.id}
                      className="flex items-start justify-between p-4 border rounded-lg hover:bg-accent transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Badge variant={`tier${email.tier}` as any}>
                            {getTierName(email.tier)}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {email.status}
                          </Badge>
                        </div>
                        <h4 className="font-semibold truncate">{email.subject}</h4>
                        <p className="text-sm text-muted-foreground truncate">
                          From: {email.from}
                        </p>
                        {email.snippet && (
                          <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                            {email.snippet}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground mt-2">
                          {formatRelativeTime(email.receivedAt)}
                        </p>
                      </div>
                    </div>
                  ))}
                  {emails.nextCursor && (
                    <Button variant="outline" className="w-full">
                      Load More
                    </Button>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Activity Tab */}
        <TabsContent value="activity">
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>
                Actions taken by this agent
              </CardDescription>
            </CardHeader>
            <CardContent>
              {stats && stats.recentActivity.length > 0 ? (
                <div className="space-y-3">
                  {stats.recentActivity.map((email) => (
                    <div
                      key={email.id}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <Badge variant={`tier${email.tier}` as any}>
                            {getTierName(email.tier)}
                          </Badge>
                          <span className="text-sm font-medium truncate">
                            {email.subject}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {email.from} • {formatRelativeTime(email.receivedAt)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  No recent activity
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings">
          <Card>
            <CardHeader>
              <CardTitle>Agent Configuration</CardTitle>
              <CardDescription>
                Current settings for this agent
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div>
                <h3 className="font-semibold mb-3">Schedule</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Timezone:</span>
                    <span className="font-medium">{config?.timezone || 'Not set'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Business Hours:</span>
                    <span className="font-medium">
                      {config?.businessHours?.start?.toString().padStart(2, '0')}:00 -{' '}
                      {config?.businessHours?.end?.toString().padStart(2, '0')}:00
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3">Communication</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Style:</span>
                    <span className="font-medium capitalize">
                      {config?.communicationStyle || 'Professional'}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-3">Off-Limits Contacts</h3>
                {config?.offLimitsContacts && config.offLimitsContacts.length > 0 ? (
                  <div className="space-y-2">
                    {config.offLimitsContacts.map((contact: string) => (
                      <div key={contact} className="p-2 bg-muted rounded text-sm">
                        {contact}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No off-limits contacts</p>
                )}
              </div>

              <Link href={`/agents/${agent.id}/edit`}>
                <Button className="w-full">
                  <Settings className="h-4 w-4 mr-2" />
                  Edit Configuration
                </Button>
              </Link>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
