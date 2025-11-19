'use client'

import { useEffect, useRef } from 'react'
import { useToast } from '@/hooks/use-toast'
import { Bell, AlertCircle, CheckCircle, Mail } from 'lucide-react'

export function NotificationsProvider({ children }: { children: React.ReactNode }) {
  const { toast } = useToast()
  const eventSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    // Only connect SSE in browser
    if (typeof window === 'undefined') return

    // Connect to SSE endpoint
    const eventSource = new EventSource('/api/notifications/stream')
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // Handle different notification types
        switch (data.type) {
          case 'tier1_escalation':
            toast({
              title: (
                <div className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-red-500" />
                  <span>Urgent Email</span>
                </div>
              ),
              description: `From: ${data.from} - ${data.subject}`,
              variant: 'destructive',
            })
            break

          case 'approval_needed':
            toast({
              title: (
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4 text-amber-500" />
                  <span>Approval Needed</span>
                </div>
              ),
              description: `Draft ready for review: ${data.subject}`,
            })
            break

          case 'email_processed':
            toast({
              title: (
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  <span>Email Processed</span>
                </div>
              ),
              description: `${data.count} emails processed`,
            })
            break

          case 'agent_updated':
            toast({
              title: (
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span>Agent Updated</span>
                </div>
              ),
              description: `${data.agentName} configuration saved`,
            })
            break

          default:
            console.log('Unknown notification type:', data.type)
        }
      } catch (error) {
        console.error('Failed to parse notification:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      // Reconnect logic happens automatically with EventSource
    }

    // Cleanup on unmount
    return () => {
      eventSource.close()
    }
  }, [toast])

  return <>{children}</>
}
