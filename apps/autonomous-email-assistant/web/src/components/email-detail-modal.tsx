'use client'

import { useState } from 'react'
import { trpc } from '@/lib/trpc-client'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Mail,
  Calendar,
  User,
  Users,
  Paperclip,
  ExternalLink,
  Code,
  FileText,
  AlertTriangle,
  Shield,
  Download,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import DOMPurify from 'isomorphic-dompurify'

interface EmailDetailModalProps {
  emailId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface Attachment {
  filename: string
  mimeType: string
  size: number
  attachmentId?: string
}

export function EmailDetailModal({
  emailId,
  open,
  onOpenChange,
}: EmailDetailModalProps) {
  const [showHtml, setShowHtml] = useState(true)

  const { data: email, isLoading } = trpc.email.get.useQuery(
    { id: emailId! },
    { enabled: !!emailId && open }
  )

  if (!emailId) return null

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

  const getTierLabel = (tier: number) => {
    switch (tier) {
      case 1:
        return 'Urgent - Escalate'
      case 2:
        return 'Handle Autonomously'
      case 3:
        return 'Draft for Approval'
      case 4:
        return 'Flag Only'
      default:
        return 'Unknown'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'processed':
        return 'default'
      case 'pending_approval':
        return 'secondary'
      case 'escalated':
        return 'destructive'
      case 'flagged':
        return 'outline'
      default:
        return 'outline'
    }
  }

  const getSanitizedHtml = (html: string) => {
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'p',
        'br',
        'strong',
        'em',
        'u',
        'a',
        'ul',
        'ol',
        'li',
        'blockquote',
        'h1',
        'h2',
        'h3',
        'h4',
        'h5',
        'h6',
        'div',
        'span',
        'table',
        'thead',
        'tbody',
        'tr',
        'td',
        'th',
      ],
      ALLOWED_ATTR: ['href', 'target', 'style', 'class'],
    })
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getGmailLink = (gmailId: string) => {
    return `https://mail.google.com/mail/u/0/#all/${gmailId}`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        ) : !email ? (
          <div className="text-center py-12">
            <AlertTriangle className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground">Email not found</p>
          </div>
        ) : (
          <>
            <DialogHeader>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <DialogTitle className="text-2xl">{email.subject}</DialogTitle>
                  <DialogDescription className="mt-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge className={getTierColor(email.tier)}>
                        Tier {email.tier}: {getTierLabel(email.tier)}
                      </Badge>
                      <Badge variant={getStatusColor(email.status)}>
                        {email.status.replace('_', ' ')}
                      </Badge>
                      {email.confidence && (
                        <Badge variant="outline">
                          {Math.round(email.confidence * 100)}% confidence
                        </Badge>
                      )}
                    </div>
                  </DialogDescription>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(getGmailLink(email.gmailId), '_blank')}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View in Gmail
                </Button>
              </div>
            </DialogHeader>

            <div className="space-y-4 mt-4">
              {/* Email Headers */}
              <div className="rounded-lg border p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <User className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-muted-foreground">
                      From
                    </div>
                    <div className="text-sm">{email.from}</div>
                  </div>
                </div>

                {email.to && (
                  <div className="flex items-start gap-3">
                    <Mail className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-muted-foreground">
                        To
                      </div>
                      <div className="text-sm">{email.to}</div>
                    </div>
                  </div>
                )}

                {email.cc && (
                  <div className="flex items-start gap-3">
                    <Users className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-muted-foreground">
                        CC
                      </div>
                      <div className="text-sm">{email.cc}</div>
                    </div>
                  </div>
                )}

                {email.bcc && (
                  <div className="flex items-start gap-3">
                    <Users className="h-5 w-5 text-muted-foreground mt-0.5" />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-muted-foreground">
                        BCC
                      </div>
                      <div className="text-sm">{email.bcc}</div>
                    </div>
                  </div>
                )}

                <div className="flex items-start gap-3">
                  <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-muted-foreground">
                      Received
                    </div>
                    <div className="text-sm">
                      {new Date(email.receivedAt).toLocaleString()} (
                      {formatDistanceToNow(new Date(email.receivedAt), {
                        addSuffix: true,
                      })}
                      )
                    </div>
                  </div>
                </div>
              </div>

              {/* Attachments */}
              {email.attachments && Array.isArray(email.attachments) && email.attachments.length > 0 && (
                <div className="rounded-lg border p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Paperclip className="h-5 w-5" />
                    <h3 className="font-medium">
                      Attachments ({email.attachments.length})
                    </h3>
                  </div>
                  <div className="space-y-2">
                    {(email.attachments as Attachment[]).map((attachment, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 bg-muted rounded-md"
                      >
                        <div className="flex items-center gap-3">
                          <FileText className="h-5 w-5 text-muted-foreground" />
                          <div>
                            <div className="text-sm font-medium">
                              {attachment.filename}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {attachment.mimeType} •{' '}
                              {formatFileSize(attachment.size)}
                            </div>
                          </div>
                        </div>
                        <Button variant="ghost" size="sm">
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Email Body */}
              <Tabs value={showHtml ? 'html' : 'text'} onValueChange={(v) => setShowHtml(v === 'html')}>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-medium">Message</h3>
                  <TabsList>
                    <TabsTrigger value="html">
                      <FileText className="h-4 w-4 mr-2" />
                      Rich Text
                    </TabsTrigger>
                    <TabsTrigger value="text">
                      <Code className="h-4 w-4 mr-2" />
                      Plain Text
                    </TabsTrigger>
                  </TabsList>
                </div>

                <TabsContent value="html" className="rounded-lg border p-4">
                  {email.bodyHtml ? (
                    <div
                      className="prose prose-sm max-w-none dark:prose-invert"
                      dangerouslySetInnerHTML={{
                        __html: getSanitizedHtml(email.bodyHtml),
                      }}
                    />
                  ) : email.body ? (
                    <div className="whitespace-pre-wrap text-sm">{email.body}</div>
                  ) : (
                    <div className="text-sm text-muted-foreground italic">
                      No email body available
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="text" className="rounded-lg border p-4">
                  {email.body ? (
                    <pre className="whitespace-pre-wrap text-sm font-mono">
                      {email.body}
                    </pre>
                  ) : (
                    <div className="text-sm text-muted-foreground italic">
                      No plain text version available
                    </div>
                  )}
                </TabsContent>
              </Tabs>

              {/* Classification Reasoning */}
              <div className="rounded-lg border p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Shield className="h-5 w-5 text-primary" />
                  <h3 className="font-medium">Classification Reasoning</h3>
                </div>
                <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                  {email.reasoning}
                </div>
              </div>

              {/* Actions History */}
              {email.actions && email.actions.length > 0 && (
                <div className="rounded-lg border p-4">
                  <h3 className="font-medium mb-3">Actions History</h3>
                  <div className="space-y-2">
                    {email.actions.map((action) => (
                      <div
                        key={action.id}
                        className="flex items-start justify-between p-3 bg-muted rounded-md"
                      >
                        <div>
                          <div className="text-sm font-medium">
                            {action.type.replace(/_/g, ' ')}
                          </div>
                          <div className="text-xs text-muted-foreground">
                            {formatDistanceToNow(new Date(action.createdAt), {
                              addSuffix: true,
                            })}
                          </div>
                        </div>
                        <Badge variant={action.status === 'completed' ? 'default' : 'secondary'}>
                          {action.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
