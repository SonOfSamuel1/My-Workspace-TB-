import { NextRequest } from 'next/server'

// Store active connections
const connections = new Set<ReadableStreamDefaultController>()

/**
 * Server-Sent Events endpoint for real-time notifications
 * GET /api/notifications/stream
 */
export async function GET(req: NextRequest) {
  // Create a readable stream for SSE
  const stream = new ReadableStream({
    start(controller) {
      // Add this connection to the set
      connections.add(controller)

      // Send initial connection message
      const data = JSON.stringify({ type: 'connected', timestamp: new Date().toISOString() })
      controller.enqueue(`data: ${data}\n\n`)

      // Send keep-alive ping every 30 seconds
      const interval = setInterval(() => {
        try {
          controller.enqueue(`: keepalive\n\n`)
        } catch (error) {
          clearInterval(interval)
          connections.delete(controller)
        }
      }, 30000)

      // Cleanup on close
      req.signal.addEventListener('abort', () => {
        clearInterval(interval)
        connections.delete(controller)
        try {
          controller.close()
        } catch (error) {
          // Controller already closed
        }
      })
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}

/**
 * Helper function to broadcast notifications to all connected clients
 * Call this from other parts of your app to send notifications
 */
export function broadcastNotification(data: any) {
  const message = `data: ${JSON.stringify(data)}\n\n`

  connections.forEach((controller) => {
    try {
      controller.enqueue(message)
    } catch (error) {
      // Connection closed, will be cleaned up
      connections.delete(controller)
    }
  })
}
