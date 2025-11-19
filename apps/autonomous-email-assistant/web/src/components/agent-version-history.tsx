'use client'

import { useState } from 'react'
import { trpc } from '@/lib/trpc-client'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Clock, RotateCcw, GitCompare, CheckCircle2, User } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { VersionDiffViewer } from './version-diff-viewer'

interface AgentVersionHistoryProps {
  agentId: string
}

export function AgentVersionHistory({ agentId }: AgentVersionHistoryProps) {
  const [selectedVersionA, setSelectedVersionA] = useState<number | null>(null)
  const [selectedVersionB, setSelectedVersionB] = useState<number | null>(null)
  const [showDiff, setShowDiff] = useState(false)
  const [showRollbackDialog, setShowRollbackDialog] = useState(false)
  const [rollbackVersion, setRollbackVersion] = useState<number | null>(null)
  const [rollbackReason, setRollbackReason] = useState('')
  const [isRollingBack, setIsRollingBack] = useState(false)

  // Fetch version history
  const { data: versions, isLoading, refetch } = trpc.agent.getVersionHistory.useQuery({
    id: agentId,
    limit: 50,
  })

  // Rollback mutation
  const rollbackMutation = trpc.agent.rollback.useMutation({
    onSuccess: () => {
      setShowRollbackDialog(false)
      setRollbackVersion(null)
      setRollbackReason('')
      setIsRollingBack(false)
      refetch()
    },
    onError: (error) => {
      alert(`Rollback failed: ${error.message}`)
      setIsRollingBack(false)
    },
  })

  const handleRollback = async () => {
    if (!rollbackVersion) return

    setIsRollingBack(true)
    rollbackMutation.mutate({
      id: agentId,
      version: rollbackVersion,
      reason: rollbackReason || undefined,
    })
  }

  const handleCompare = () => {
    if (selectedVersionA && selectedVersionB) {
      setShowDiff(true)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  if (!versions || versions.length === 0) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        <Clock className="mx-auto mb-2 h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          No version history yet. Updates to this agent will appear here.
        </p>
      </div>
    )
  }

  const latestVersion = versions[0]?.version ?? 0

  return (
    <div className="space-y-4">
      {/* Compare Controls */}
      {selectedVersionA && selectedVersionB && (
        <div className="rounded-lg border bg-muted/50 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <GitCompare className="h-5 w-5" />
              <span className="text-sm font-medium">
                Comparing v{selectedVersionA} → v{selectedVersionB}
              </span>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setSelectedVersionA(null)
                  setSelectedVersionB(null)
                }}
              >
                Clear
              </Button>
              <Button size="sm" onClick={handleCompare}>
                View Diff
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Version List */}
      <div className="space-y-2">
        {versions.map((version) => {
          const isLatest = version.version === latestVersion
          const isSelectedA = selectedVersionA === version.version
          const isSelectedB = selectedVersionB === version.version

          return (
            <div
              key={version.id}
              className={`rounded-lg border p-4 transition-colors ${
                isSelectedA || isSelectedB
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:bg-muted/50'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm font-medium">
                      Version {version.version}
                    </span>
                    {isLatest && (
                      <Badge variant="default" className="text-xs">
                        <CheckCircle2 className="mr-1 h-3 w-3" />
                        Current
                      </Badge>
                    )}
                    {version.changeReason?.includes('Rollback') && (
                      <Badge variant="secondary" className="text-xs">
                        <RotateCcw className="mr-1 h-3 w-3" />
                        Rollback
                      </Badge>
                    )}
                  </div>

                  {version.changesSummary && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {version.changesSummary}
                    </p>
                  )}

                  {version.changeReason && (
                    <p className="mt-1 text-sm italic text-muted-foreground">
                      "{version.changeReason}"
                    </p>
                  )}

                  <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDistanceToNow(new Date(version.createdAt), {
                        addSuffix: true,
                      })}
                    </span>
                    {version.changedBy && (
                      <span className="flex items-center gap-1">
                        <User className="h-3 w-3" />
                        User ID: {version.changedBy.slice(0, 8)}...
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex flex-col gap-2">
                  {/* Compare Selection */}
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant={isSelectedA ? 'default' : 'outline'}
                      onClick={() =>
                        setSelectedVersionA(
                          isSelectedA ? null : version.version
                        )
                      }
                    >
                      A
                    </Button>
                    <Button
                      size="sm"
                      variant={isSelectedB ? 'default' : 'outline'}
                      onClick={() =>
                        setSelectedVersionB(
                          isSelectedB ? null : version.version
                        )
                      }
                    >
                      B
                    </Button>
                  </div>

                  {/* Rollback Button */}
                  {!isLatest && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setRollbackVersion(version.version)
                        setShowRollbackDialog(true)
                      }}
                    >
                      <RotateCcw className="mr-1 h-3 w-3" />
                      Rollback
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Diff Viewer Dialog */}
      {selectedVersionA && selectedVersionB && (
        <Dialog open={showDiff} onOpenChange={setShowDiff}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                Version Comparison: v{selectedVersionA} → v{selectedVersionB}
              </DialogTitle>
            </DialogHeader>
            <VersionDiffViewer
              agentId={agentId}
              versionA={selectedVersionA}
              versionB={selectedVersionB}
            />
          </DialogContent>
        </Dialog>
      )}

      {/* Rollback Confirmation Dialog */}
      <AlertDialog open={showRollbackDialog} onOpenChange={setShowRollbackDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Rollback to Version {rollbackVersion}?</AlertDialogTitle>
            <AlertDialogDescription>
              This will restore the agent configuration to version {rollbackVersion}.
              A new version will be created to track this rollback, so you can always
              revert if needed.
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="py-4">
            <label className="text-sm font-medium">
              Reason for rollback (optional)
            </label>
            <Textarea
              placeholder="e.g., Reverting problematic changes to tier rules"
              value={rollbackReason}
              onChange={(e) => setRollbackReason(e.target.value)}
              className="mt-2"
              rows={3}
            />
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={isRollingBack}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRollback}
              disabled={isRollingBack}
            >
              {isRollingBack ? 'Rolling back...' : 'Rollback'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
