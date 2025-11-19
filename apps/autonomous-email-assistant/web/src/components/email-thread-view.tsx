'use client'

import { useState } from 'react'
import { trpc } from '@/lib/trpc-client'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import {
  Mail,
  ChevronDown,
  ChevronUp,
  User,
  Calendar,
  MessageSquare,
  ExternalLink,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface EmailThreadViewProps {
  emailId: string
}

export function EmailThreadView({ emailId }: EmailThreadViewProps) {
  const [expandedEmails, setExpandedEmails] = useState<Set<string>>(new Set([emailId]))

  const { data: threadEmails, isLoading } = trpc.email.getThread.useQuery({
    emailId,
  })

  const toggleEmail = (id: string) => {
    setExpandedEmails((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const expandAll = () => {
    if (threadEmails) {
      setExpandedEmails(new Set(threadEmails.map((e) => e.id)))
    }
  }

  const collapseAll = () => {
    setExpandedEmails(new Set())
  }

  const getTierColor = (tier: number) => {
    switch (tier) {
      case 1:
        return 'bg-red-500'
      case 2:
        return 'bg-green-500'
      case 3:
        return 'bg-amber-500'
      case 4:
        return 'bg-gray-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getGmailLink = (gmailId: string) => {
    return `https://mail.google.com/mail/u/0/#all/${gmailId}`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!threadEmails || threadEmails.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <Mail className="mx-auto h-12 w-12 mb-4 opacity-50" />
        <p>No emails found in this thread</p>
      </div>
    )
  }

  // Extract all unique participants
  const participants = new Set<string>()
  threadEmails.forEach((email) => {
    if (email.from) participants.add(email.from)
    if (email.to) email.to.split(',').forEach((p) => participants.add(p.trim()))
    if (email.cc) email.cc?.split(',').forEach((p) => participants.add(p.trim()))
  })

  const isSingleEmail = threadEmails.length === 1

  return (
    <div className="space-y-4">
      {/* Thread Header */}
      {!isSingleEmail && (
        <div className="rounded-lg border bg-card p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <MessageSquare className="h-5 w-5 text-primary" />
                <h3 className="font-semibold">Conversation Thread</h3>
                <Badge variant="secondary">{threadEmails.length} messages</Badge>
              </div>
              <div className="text-sm text-muted-foreground space-y-1">
                <div className="flex items-center gap-2">
                  <User className="h-4 w-4" />
                  <span>{participants.size} participants</span>
                </div>
                <div className="flex flex-wrap gap-1 mt-2">
                  {Array.from(participants).slice(0, 5).map((participant, index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {participant}
                    </Badge>
                  ))}
                  {participants.size > 5 && (
                    <Badge variant="outline" className="text-xs">
                      +{participants.size - 5} more
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={expandAll}>
                <ChevronDown className="h-4 w-4 mr-1" />
                Expand All
              </Button>
              <Button size="sm" variant="outline" onClick={collapseAll}>
                <ChevronUp className="h-4 w-4 mr-1" />
                Collapse All
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="relative space-y-4">
        {/* Timeline connector line */}
        {!isSingleEmail && (
          <div
            className="absolute left-6 top-8 bottom-8 w-0.5 bg-border"
            aria-hidden="true"
          />
        )}

        {/* Emails in thread */}
        {threadEmails.map((email, index) => {
          const isExpanded = expandedEmails.has(email.id)
          const isFirst = index === 0
          const isLast = index === threadEmails.length - 1

          return (
            <div key={email.id} className="relative">
              {/* Timeline dot */}
              {!isSingleEmail && (
                <div
                  className={`absolute left-4 top-6 h-5 w-5 rounded-full border-4 border-background ${getTierColor(
                    email.tier
                  )} z-10`}
                  aria-hidden="true"
                />
              )}

              {/* Email card */}
              <Card
                className={`${
                  isSingleEmail ? '' : 'ml-16'
                } transition-all hover:shadow-md`}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <button
                      onClick={() => toggleEmail(email.id)}
                      className="flex-1 text-left"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={getTierColor(email.tier)}>
                          Tier {email.tier}
                        </Badge>
                        <Badge variant="outline">{email.status}</Badge>
                        {isFirst && (
                          <Badge variant="secondary" className="text-xs">
                            First
                          </Badge>
                        )}
                        {isLast && !isSingleEmail && (
                          <Badge variant="secondary" className="text-xs">
                            Latest
                          </Badge>
                        )}
                      </div>
                      <h4 className="font-semibold text-base mb-1">
                        {email.subject}
                      </h4>
                      <div className="text-sm text-muted-foreground space-y-0.5">
                        <div className="flex items-center gap-2">
                          <User className="h-3 w-3" />
                          <span className="font-medium">From:</span>
                          <span>{email.from}</span>
                        </div>
                        {email.to && (
                          <div className="flex items-center gap-2">
                            <Mail className="h-3 w-3" />
                            <span className="font-medium">To:</span>
                            <span className="truncate">{email.to}</span>
                          </div>
                        )}
                        <div className="flex items-center gap-2">
                          <Calendar className="h-3 w-3" />
                          <span>
                            {new Date(email.receivedAt).toLocaleString()} (
                            {formatDistanceToNow(new Date(email.receivedAt), {
                              addSuffix: true,
                            })}
                            )
                          </span>
                        </div>
                      </div>
                    </button>

                    <div className="flex gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          window.open(getGmailLink(email.gmailId), '_blank')
                        }
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleEmail(email.id)}
                      >
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                {isExpanded && (
                  <CardContent className="pt-0 space-y-4">
                    {/* Email snippet/body */}
                    {email.snippet && (
                      <div>
                        <div className="text-sm font-medium mb-1">Preview:</div>
                        <div className="text-sm text-muted-foreground">
                          {email.snippet}
                        </div>
                      </div>
                    )}

                    {/* Classification reasoning */}
                    {email.reasoning && (
                      <div>
                        <div className="text-sm font-medium mb-1">
                          Classification Reasoning:
                        </div>
                        <div className="text-sm text-muted-foreground bg-muted p-3 rounded-lg">
                          {email.reasoning}
                        </div>
                      </div>
                    )}

                    {/* Confidence */}
                    {email.confidence !== null && email.confidence !== undefined && (
                      <div>
                        <div className="text-sm font-medium mb-1">
                          Confidence:
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="flex-1 bg-muted rounded-full h-2">
                            <div
                              className="bg-primary rounded-full h-2 transition-all"
                              style={{ width: `${email.confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-sm text-muted-foreground">
                            {Math.round(email.confidence * 100)}%
                          </span>
                        </div>
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>
            </div>
          )
        })}
      </div>
    </div>
  )
}
