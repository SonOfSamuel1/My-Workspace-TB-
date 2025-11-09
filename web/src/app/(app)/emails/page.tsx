'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { trpc } from '@/lib/trpc/client'
import { formatRelativeTime, getTierName } from '@/lib/utils'
import { Search, Filter, Mail } from 'lucide-react'

export default function EmailsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAgent, setSelectedAgent] = useState<string>('all')
  const [selectedTier, setSelectedTier] = useState<string>('all')
  const [selectedStatus, setSelectedStatus] = useState<string>('all')
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null)

  const { data: agents } = trpc.agent.list.useQuery()

  const { data: emailsData, isLoading } = trpc.email.list.useQuery({
    agentId: selectedAgent === 'all' ? '' : selectedAgent,
    tier: selectedTier === 'all' ? undefined : parseInt(selectedTier),
    status: selectedStatus === 'all' ? undefined : selectedStatus,
    limit: 50,
  }, {
    enabled: selectedAgent !== 'all' || searchQuery.length === 0,
  })

  const { data: searchResults } = trpc.email.search.useQuery({
    agentId: selectedAgent === 'all' ? undefined : selectedAgent,
    query: searchQuery,
    limit: 50,
  }, {
    enabled: searchQuery.length > 0,
  })

  const emails = searchQuery.length > 0 ? searchResults : emailsData?.emails
  const selected = emails?.find((e) => e.id === selectedEmail)

  return (
    <div className="container mx-auto p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold tracking-tight">Email Monitor</h1>
        <p className="text-muted-foreground mt-2">
          Track and search all processed emails
        </p>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Search</label>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search emails..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Agent</label>
              <Select value={selectedAgent} onValueChange={setSelectedAgent}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Agents</SelectItem>
                  {agents?.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Tier</label>
              <Select value={selectedTier} onValueChange={setSelectedTier}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tiers</SelectItem>
                  <SelectItem value="1">Tier 1: Escalate</SelectItem>
                  <SelectItem value="2">Tier 2: Handle</SelectItem>
                  <SelectItem value="3">Tier 3: Draft</SelectItem>
                  <SelectItem value="4">Tier 4: Flag</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="processed">Processed</SelectItem>
                  <SelectItem value="pending_approval">Pending Approval</SelectItem>
                  <SelectItem value="escalated">Escalated</SelectItem>
                  <SelectItem value="flagged">Flagged</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent" />
            <p className="mt-4 text-muted-foreground">Loading emails...</p>
          </div>
        </div>
      ) : !emails || emails.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Mail className="h-16 w-16 mx-auto mb-4 opacity-50" />
            <p>No emails found matching your filters</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Email List */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">
              Emails ({emails.length})
            </h2>
            <div className="space-y-3">
              {emails.map((email) => {
                const isSelected = selectedEmail === email.id

                return (
                  <Card
                    key={email.id}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? 'border-primary ring-2 ring-primary' : ''
                    }`}
                    onClick={() => setSelectedEmail(email.id)}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-2 flex-wrap">
                            <Badge variant={`tier${email.tier}` as any}>
                              {getTierName(email.tier)}
                            </Badge>
                            <Badge variant="outline" className="text-xs">
                              {email.status}
                            </Badge>
                            {(email as any).agent && (
                              <Badge variant="outline" className="text-xs">
                                {(email as any).agent.name}
                              </Badge>
                            )}
                          </div>
                          <CardTitle className="text-base truncate">
                            {email.subject}
                          </CardTitle>
                          <CardDescription className="truncate">
                            From: {email.from}
                          </CardDescription>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0 space-y-2">
                      {email.snippet && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {email.snippet}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        {formatRelativeTime(email.receivedAt)}
                      </p>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>

          {/* Email Detail */}
          <div className="lg:sticky lg:top-8 lg:self-start">
            {!selected ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  <Mail className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Select an email to view details</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {/* Email Details */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <Badge variant={`tier${selected.tier}` as any}>
                        {getTierName(selected.tier)}
                      </Badge>
                      <Badge variant="outline">{selected.status}</Badge>
                    </div>
                    <CardTitle>{selected.subject}</CardTitle>
                    <CardDescription>
                      From: {selected.from}
                      {selected.to && ` • To: ${selected.to}`}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <span className="text-sm font-semibold">Received:</span>
                      <p className="text-sm text-muted-foreground">
                        {new Date(selected.receivedAt).toLocaleString()}
                      </p>
                    </div>

                    {selected.body && (
                      <div>
                        <span className="text-sm font-semibold">Message:</span>
                        <div className="mt-2 p-4 bg-muted rounded-lg">
                          <p className="text-sm whitespace-pre-wrap">
                            {selected.body}
                          </p>
                        </div>
                      </div>
                    )}

                    {selected.reasoning && (
                      <div>
                        <span className="text-sm font-semibold">Agent Reasoning:</span>
                        <p className="text-sm text-muted-foreground mt-1">
                          {selected.reasoning}
                        </p>
                      </div>
                    )}

                    {selected.confidence !== null && selected.confidence !== undefined && (
                      <div>
                        <span className="text-sm font-semibold">Confidence:</span>
                        <div className="flex items-center gap-2 mt-1">
                          <div className="flex-1 bg-muted rounded-full h-2">
                            <div
                              className="bg-primary rounded-full h-2 transition-all"
                              style={{ width: `${selected.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-muted-foreground">
                            {Math.round(selected.confidence * 100)}%
                          </span>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Actions */}
                {(selected as any).actions && (selected as any).actions.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Actions Taken</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {(selected as any).actions.map((action: any) => (
                          <div
                            key={action.id}
                            className="p-3 border rounded-lg space-y-2"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-semibold capitalize">
                                {action.type.replace(/_/g, ' ')}
                              </span>
                              <Badge variant="outline" className="text-xs">
                                {action.status}
                              </Badge>
                            </div>
                            {action.data && (
                              <p className="text-sm text-muted-foreground">
                                {JSON.stringify(action.data).slice(0, 100)}...
                              </p>
                            )}
                            <p className="text-xs text-muted-foreground">
                              {formatRelativeTime(action.createdAt)}
                            </p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
