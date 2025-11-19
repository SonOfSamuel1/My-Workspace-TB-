'use client'

import { trpc } from '@/lib/trpc-client'
import { Plus, Minus, ArrowRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface VersionDiffViewerProps {
  agentId: string
  versionA: number
  versionB: number
}

export function VersionDiffViewer({
  agentId,
  versionA,
  versionB,
}: VersionDiffViewerProps) {
  const { data: diff, isLoading } = trpc.agent.compareVersions.useQuery({
    id: agentId,
    versionA,
    versionB,
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!diff || diff.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        <p className="text-sm text-muted-foreground">
          No differences found between these versions.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {diff.map((change, index) => {
        const isAdded = change.type === 'added'
        const isRemoved = change.type === 'removed'
        const isModified = change.type === 'modified'

        return (
          <div
            key={index}
            className={`rounded-lg border p-4 ${
              isAdded
                ? 'border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950'
                : isRemoved
                ? 'border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950'
                : 'border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950'
            }`}
          >
            {/* Change Type Badge */}
            <div className="mb-2 flex items-center gap-2">
              <Badge
                variant={
                  isAdded ? 'default' : isRemoved ? 'destructive' : 'secondary'
                }
                className="text-xs"
              >
                {isAdded && <Plus className="mr-1 h-3 w-3" />}
                {isRemoved && <Minus className="mr-1 h-3 w-3" />}
                {isModified && <ArrowRight className="mr-1 h-3 w-3" />}
                {change.type.toUpperCase()}
              </Badge>
              <code className="text-sm font-mono text-muted-foreground">
                {change.field}
              </code>
            </div>

            {/* Value Display */}
            <div className="space-y-2">
              {isAdded && (
                <div className="rounded bg-white dark:bg-gray-900 p-3">
                  <div className="text-xs text-muted-foreground mb-1">
                    New Value:
                  </div>
                  <pre className="text-sm overflow-x-auto">
                    {formatValue(change.newValue)}
                  </pre>
                </div>
              )}

              {isRemoved && (
                <div className="rounded bg-white dark:bg-gray-900 p-3">
                  <div className="text-xs text-muted-foreground mb-1">
                    Removed Value:
                  </div>
                  <pre className="text-sm overflow-x-auto">
                    {formatValue(change.oldValue)}
                  </pre>
                </div>
              )}

              {isModified && (
                <>
                  <div className="rounded bg-white dark:bg-gray-900 p-3">
                    <div className="text-xs text-muted-foreground mb-1">
                      Old Value:
                    </div>
                    <pre className="text-sm overflow-x-auto text-red-700 dark:text-red-400">
                      {formatValue(change.oldValue)}
                    </pre>
                  </div>
                  <div className="flex items-center justify-center">
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="rounded bg-white dark:bg-gray-900 p-3">
                    <div className="text-xs text-muted-foreground mb-1">
                      New Value:
                    </div>
                    <pre className="text-sm overflow-x-auto text-green-700 dark:text-green-400">
                      {formatValue(change.newValue)}
                    </pre>
                  </div>
                </>
              )}
            </div>
          </div>
        )
      })}

      {/* Summary */}
      <div className="rounded-lg border bg-muted p-4">
        <h4 className="text-sm font-medium mb-2">Change Summary</h4>
        <div className="grid grid-cols-3 gap-4 text-center text-sm">
          <div>
            <div className="text-2xl font-bold text-green-600">
              {diff.filter((d) => d.type === 'added').length}
            </div>
            <div className="text-muted-foreground">Added</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-yellow-600">
              {diff.filter((d) => d.type === 'modified').length}
            </div>
            <div className="text-muted-foreground">Modified</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-600">
              {diff.filter((d) => d.type === 'removed').length}
            </div>
            <div className="text-muted-foreground">Removed</div>
          </div>
        </div>
      </div>
    </div>
  )
}

function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return 'null'
  }

  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }

  if (typeof value === 'string') {
    return `"${value}"`
  }

  return String(value)
}
