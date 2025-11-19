'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html>
      <body>
        <div className="flex min-h-screen items-center justify-center bg-background p-4">
          <div className="w-full max-w-lg space-y-4 rounded-lg border p-6">
            <h1 className="text-2xl font-bold text-destructive">Application Error</h1>
            <p className="text-muted-foreground">
              A critical error occurred. Please refresh the page or contact support.
            </p>
            {process.env.NODE_ENV === 'development' && (
              <div className="rounded-md bg-destructive/10 p-4">
                <p className="font-mono text-sm text-destructive">{error.message}</p>
                {error.digest && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    Error ID: {error.digest}
                  </p>
                )}
              </div>
            )}
            <div className="flex gap-2">
              <button
                onClick={reset}
                className="rounded-md bg-secondary px-4 py-2 text-sm font-medium hover:bg-secondary/80"
              >
                Try Again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/80"
              >
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      </body>
    </html>
  )
}
