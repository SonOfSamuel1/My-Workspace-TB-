import { StatCardSkeleton, TableRowSkeleton } from '@/components/ui/skeleton'

export default function DashboardLoading() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your mail agents</p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
        <StatCardSkeleton />
      </div>

      {/* Agents List */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-xl font-semibold">Your Agents</h2>
          <div className="space-y-3">
            <TableRowSkeleton />
            <TableRowSkeleton />
            <TableRowSkeleton />
          </div>
        </div>

        {/* Pending Approvals */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Pending Approvals</h2>
          <div className="space-y-3">
            <TableRowSkeleton />
            <TableRowSkeleton />
          </div>
        </div>
      </div>
    </div>
  )
}
