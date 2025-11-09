'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { trpc } from '@/lib/trpc/client'
import { formatRelativeTime, getTierName } from '@/lib/utils'
import { CheckCircle, XCircle, Edit, Send, AlertCircle } from 'lucide-react'

export default function ApprovalsPage() {
  const [selectedEmail, setSelectedEmail] = useState<string | null>(null)
  const [editedDraft, setEditedDraft] = useState<string>('')
  const [selectedForBulk, setSelectedForBulk] = useState<Set<string>>(new Set())

  const { data: pendingApprovals, isLoading } = trpc.email.pendingApprovals.useQuery({})
  const utils = trpc.useUtils()

  const approveAction = trpc.action.approve.useMutation({
    onSuccess: () => {
      utils.email.pendingApprovals.invalidate()
      setSelectedEmail(null)
      setEditedDraft('')
    },
  })

  const rejectAction = trpc.action.reject.useMutation({
    onSuccess: () => {
      utils.email.pendingApprovals.invalidate()
      setSelectedEmail(null)
    },
  })

  const bulkApprove = trpc.action.bulkApprove.useMutation({
    onSuccess: () => {
      utils.email.pendingApprovals.invalidate()
      setSelectedForBulk(new Set())
    },
  })

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <p className="mt-4 text-muted-foreground">Loading approvals...</p>
        </div>
      </div>
    )
  }

  const selected = pendingApprovals?.find((email) => email.id === selectedEmail)
  const draftAction = selected?.actions[0]

  const handleApprove = (actionId: string) => {
    if (editedDraft && editedDraft !== (draftAction?.data as any)?.responseText) {
      approveAction.mutate({
        id: actionId,
        modifications: {
          ...(draftAction?.data as any),
          responseText: editedDraft,
        },
      })
    } else {
      approveAction.mutate({ id: actionId })
    }
  }

  const handleReject = (actionId: string) => {
    rejectAction.mutate({
      id: actionId,
      reason: 'Rejected by user',
    })
  }

  const toggleBulkSelection = (actionId: string) => {
    const newSelection = new Set(selectedForBulk)
    if (newSelection.has(actionId)) {
      newSelection.delete(actionId)
    } else {
      newSelection.add(actionId)
    }
    setSelectedForBulk(newSelection)
  }

  const handleBulkApprove = () => {
    if (selectedForBulk.size > 0) {
      bulkApprove.mutate({ ids: Array.from(selectedForBulk) })
    }
  }

  return (
    <div className="container mx-auto p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold tracking-tight">Approval Queue</h1>
        <p className="text-muted-foreground mt-2">
          Review and approve draft responses from your email agents
        </p>
      </div>

      {/* Bulk Actions */}
      {selectedForBulk.size > 0 && (
        <Card className="mb-6 border-amber-500">
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="font-semibold">{selectedForBulk.size} items selected</span>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setSelectedForBulk(new Set())}
                >
                  Clear Selection
                </Button>
                <Button
                  onClick={handleBulkApprove}
                  disabled={bulkApprove.isPending}
                >
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Approve All Selected
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {!pendingApprovals || pendingApprovals.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
              <h2 className="text-2xl font-bold mb-2">All caught up!</h2>
              <p className="text-muted-foreground">
                No pending approvals at the moment.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* List of Pending Approvals */}
          <div className="space-y-4">
            <h2 className="text-xl font-semibold">
              Pending ({pendingApprovals.length})
            </h2>
            {pendingApprovals.map((email) => {
              const action = email.actions[0]
              const isSelected = selectedEmail === email.id
              const isBulkSelected = selectedForBulk.has(action?.id || '')

              return (
                <Card
                  key={email.id}
                  className={`cursor-pointer transition-colors ${
                    isSelected ? 'border-primary ring-2 ring-primary' : ''
                  } ${isBulkSelected ? 'border-amber-500' : ''}`}
                  onClick={() => {
                    setSelectedEmail(email.id)
                    setEditedDraft((action?.data as any)?.responseText || '')
                  }}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant={`tier${email.tier}` as any}>
                            {getTierName(email.tier)}
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {email.agent.name}
                          </Badge>
                        </div>
                        <CardTitle className="text-base truncate">
                          {email.subject}
                        </CardTitle>
                        <CardDescription className="truncate">
                          From: {email.from}
                        </CardDescription>
                      </div>
                      <input
                        type="checkbox"
                        checked={isBulkSelected}
                        onChange={(e) => {
                          e.stopPropagation()
                          if (action?.id) toggleBulkSelection(action.id)
                        }}
                        className="mt-1 h-4 w-4 rounded border-gray-300"
                      />
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <p className="text-xs text-muted-foreground">
                      {formatRelativeTime(email.receivedAt)}
                    </p>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          {/* Detail View */}
          <div className="lg:sticky lg:top-8 lg:self-start">
            {!selected ? (
              <Card>
                <CardContent className="py-12 text-center text-muted-foreground">
                  <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Select an email to review the draft</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-4">
                {/* Original Email */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Original Email</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <span className="text-sm font-semibold">Subject:</span>
                      <p className="text-sm">{selected.subject}</p>
                    </div>
                    <div>
                      <span className="text-sm font-semibold">From:</span>
                      <p className="text-sm">{selected.from}</p>
                    </div>
                    {selected.body && (
                      <div>
                        <span className="text-sm font-semibold">Body:</span>
                        <p className="text-sm whitespace-pre-wrap mt-1 p-3 bg-muted rounded">
                          {selected.body.slice(0, 500)}
                          {selected.body.length > 500 && '...'}
                        </p>
                      </div>
                    )}
                    <div>
                      <span className="text-sm font-semibold">Reasoning:</span>
                      <p className="text-sm text-muted-foreground mt-1">
                        {selected.reasoning}
                      </p>
                    </div>
                  </CardContent>
                </Card>

                {/* Draft Response */}
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">Draft Response</CardTitle>
                      <Badge variant="tier3">
                        <Edit className="h-3 w-3 mr-1" />
                        Editable
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Textarea
                      value={editedDraft}
                      onChange={(e) => setEditedDraft(e.target.value)}
                      rows={12}
                      className="font-mono text-sm"
                      placeholder="Draft response will appear here..."
                    />
                  </CardContent>
                </Card>

                {/* Actions */}
                {draftAction && (
                  <div className="flex gap-3">
                    <Button
                      className="flex-1"
                      onClick={() => handleApprove(draftAction.id)}
                      disabled={approveAction.isPending}
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      {approveAction.isPending ? 'Approving...' : 'Approve & Send'}
                    </Button>
                    <Button
                      variant="destructive"
                      onClick={() => handleReject(draftAction.id)}
                      disabled={rejectAction.isPending}
                    >
                      <XCircle className="h-4 w-4 mr-2" />
                      Reject
                    </Button>
                  </div>
                )}

                {(approveAction.error || rejectAction.error) && (
                  <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md">
                    {approveAction.error?.message || rejectAction.error?.message}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
