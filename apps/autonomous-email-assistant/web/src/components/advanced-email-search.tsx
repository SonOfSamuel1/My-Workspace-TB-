'use client'

import { useState } from 'react'
import { trpc } from '@/lib/trpc-client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Search,
  Save,
  Trash2,
  Star,
  Calendar,
  Paperclip,
  X,
} from 'lucide-react'

interface SearchFilters {
  query?: string
  agentIds?: string[]
  tiers?: number[]
  statuses?: string[]
  dateFrom?: Date
  dateTo?: Date
  hasAttachments?: boolean
}

interface AdvancedEmailSearchProps {
  onSearch: (filters: SearchFilters) => void
  initialFilters?: SearchFilters
}

export function AdvancedEmailSearch({
  onSearch,
  initialFilters = {},
}: AdvancedEmailSearchProps) {
  const [filters, setFilters] = useState<SearchFilters>(initialFilters)
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const [searchName, setSearchName] = useState('')
  const [searchDescription, setSearchDescription] = useState('')

  const { data: agents } = trpc.agent.list.useQuery()
  const { data: savedSearches, refetch: refetchSavedSearches } =
    trpc.email.getSavedSearches.useQuery()

  const createSavedSearch = trpc.email.createSavedSearch.useMutation({
    onSuccess: () => {
      setShowSaveDialog(false)
      setSearchName('')
      setSearchDescription('')
      refetchSavedSearches()
    },
  })

  const deleteSavedSearch = trpc.email.deleteSavedSearch.useMutation({
    onSuccess: () => {
      refetchSavedSearches()
    },
  })

  const useSavedSearch = trpc.email.useSavedSearch.useMutation()

  const handleSearch = () => {
    onSearch(filters)
  }

  const handleSaveSearch = () => {
    createSavedSearch.mutate({
      name: searchName,
      description: searchDescription || undefined,
      filters: filters as any,
    })
  }

  const handleLoadSavedSearch = (search: any) => {
    const savedFilters = search.filters as SearchFilters
    setFilters(savedFilters)
    onSearch(savedFilters)
    useSavedSearch.mutate({ id: search.id })
  }

  const handleReset = () => {
    setFilters({})
    onSearch({})
  }

  const toggleAgent = (agentId: string) => {
    const current = filters.agentIds || []
    const updated = current.includes(agentId)
      ? current.filter((id) => id !== agentId)
      : [...current, agentId]
    setFilters({ ...filters, agentIds: updated })
  }

  const toggleTier = (tier: number) => {
    const current = filters.tiers || []
    const updated = current.includes(tier)
      ? current.filter((t) => t !== tier)
      : [...current, tier]
    setFilters({ ...filters, tiers: updated })
  }

  const toggleStatus = (status: string) => {
    const current = filters.statuses || []
    const updated = current.includes(status)
      ? current.filter((s) => s !== status)
      : [...current, status]
    setFilters({ ...filters, statuses: updated })
  }

  const activeFiltersCount =
    (filters.query ? 1 : 0) +
    (filters.agentIds?.length || 0) +
    (filters.tiers?.length || 0) +
    (filters.statuses?.length || 0) +
    (filters.dateFrom || filters.dateTo ? 1 : 0) +
    (filters.hasAttachments !== undefined ? 1 : 0)

  return (
    <div className="space-y-6">
      {/* Search Bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search emails..."
            value={filters.query || ''}
            onChange={(e) => setFilters({ ...filters, query: e.target.value })}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="pl-10"
          />
        </div>
        <Button onClick={handleSearch}>
          <Search className="mr-2 h-4 w-4" />
          Search
        </Button>
        {activeFiltersCount > 0 && (
          <Button variant="outline" onClick={handleReset}>
            <X className="mr-2 h-4 w-4" />
            Clear ({activeFiltersCount})
          </Button>
        )}
        <Button variant="outline" onClick={() => setShowSaveDialog(true)}>
          <Save className="mr-2 h-4 w-4" />
          Save
        </Button>
      </div>

      {/* Saved Searches */}
      {savedSearches && savedSearches.length > 0 && (
        <div>
          <Label className="mb-2 block text-sm font-medium">Saved Searches</Label>
          <div className="flex flex-wrap gap-2">
            {savedSearches.map((search) => (
              <div
                key={search.id}
                className="group flex items-center gap-2 rounded-lg border bg-card p-2 text-sm hover:bg-muted"
              >
                <button
                  onClick={() => handleLoadSavedSearch(search)}
                  className="flex items-center gap-2"
                >
                  <Star className="h-4 w-4 text-primary" />
                  <span>{search.name}</span>
                  {search.usageCount > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {search.usageCount}
                    </Badge>
                  )}
                </button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100"
                  onClick={() => deleteSavedSearch.mutate({ id: search.id })}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {/* Agents Filter */}
        <div className="space-y-2">
          <Label>Agents</Label>
          <div className="space-y-1.5 rounded-lg border p-3">
            {agents?.map((agent) => (
              <label
                key={agent.id}
                className="flex cursor-pointer items-center gap-2"
              >
                <Checkbox
                  checked={filters.agentIds?.includes(agent.id)}
                  onCheckedChange={() => toggleAgent(agent.id)}
                />
                <span className="text-sm">{agent.name}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Tiers Filter */}
        <div className="space-y-2">
          <Label>Tiers</Label>
          <div className="space-y-1.5 rounded-lg border p-3">
            {[1, 2, 3, 4].map((tier) => (
              <label
                key={tier}
                className="flex cursor-pointer items-center gap-2"
              >
                <Checkbox
                  checked={filters.tiers?.includes(tier)}
                  onCheckedChange={() => toggleTier(tier)}
                />
                <span className="text-sm">
                  Tier {tier}
                  {tier === 1 && ' (Escalate)'}
                  {tier === 2 && ' (Handle)'}
                  {tier === 3 && ' (Draft)'}
                  {tier === 4 && ' (Flag)'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Status Filter */}
        <div className="space-y-2">
          <Label>Status</Label>
          <div className="space-y-1.5 rounded-lg border p-3">
            {[
              'processed',
              'pending_approval',
              'escalated',
              'flagged',
            ].map((status) => (
              <label
                key={status}
                className="flex cursor-pointer items-center gap-2"
              >
                <Checkbox
                  checked={filters.statuses?.includes(status)}
                  onCheckedChange={() => toggleStatus(status)}
                />
                <span className="text-sm capitalize">
                  {status.replace('_', ' ')}
                </span>
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Date Range & Attachments */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Date Range
          </Label>
          <div className="grid grid-cols-2 gap-2">
            <Input
              type="date"
              value={
                filters.dateFrom
                  ? filters.dateFrom.toISOString().split('T')[0]
                  : ''
              }
              onChange={(e) =>
                setFilters({
                  ...filters,
                  dateFrom: e.target.value ? new Date(e.target.value) : undefined,
                })
              }
              placeholder="From"
            />
            <Input
              type="date"
              value={
                filters.dateTo
                  ? filters.dateTo.toISOString().split('T')[0]
                  : ''
              }
              onChange={(e) =>
                setFilters({
                  ...filters,
                  dateTo: e.target.value ? new Date(e.target.value) : undefined,
                })
              }
              placeholder="To"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label className="flex items-center gap-2">
            <Paperclip className="h-4 w-4" />
            Attachments
          </Label>
          <Select
            value={
              filters.hasAttachments === undefined
                ? 'all'
                : filters.hasAttachments
                ? 'with'
                : 'without'
            }
            onValueChange={(value) =>
              setFilters({
                ...filters,
                hasAttachments:
                  value === 'all' ? undefined : value === 'with',
              })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Emails</SelectItem>
              <SelectItem value="with">With Attachments</SelectItem>
              <SelectItem value="without">Without Attachments</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Save Search Dialog */}
      <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Search</DialogTitle>
            <DialogDescription>
              Save these filters for quick access later
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="searchName">Name *</Label>
              <Input
                id="searchName"
                value={searchName}
                onChange={(e) => setSearchName(e.target.value)}
                placeholder="e.g., Urgent emails from this week"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="searchDescription">Description (optional)</Label>
              <Input
                id="searchDescription"
                value={searchDescription}
                onChange={(e) => setSearchDescription(e.target.value)}
                placeholder="e.g., All tier 1 emails from the past 7 days"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowSaveDialog(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveSearch}
              disabled={!searchName || createSavedSearch.isPending}
            >
              {createSavedSearch.isPending ? 'Saving...' : 'Save Search'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
