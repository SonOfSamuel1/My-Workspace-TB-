'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { trpc } from '@/lib/trpc/client'
import { formatCurrency } from '@/lib/utils'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { TrendingUp, Mail, DollarSign, Clock } from 'lucide-react'
import { format } from 'date-fns'

const TIER_COLORS = {
  tier1: '#ef4444', // red
  tier2: '#22c55e', // green
  tier3: '#f59e0b', // amber
  tier4: '#3b82f6', // blue
}

export default function AnalyticsPage() {
  const [selectedAgent, setSelectedAgent] = useState<string>('all')
  const [timeRange, setTimeRange] = useState<number>(30)

  const { data: agents } = trpc.agent.list.useQuery()
  const { data: overview } = trpc.analytics.overview.useQuery({
    agentId: selectedAgent === 'all' ? undefined : selectedAgent,
    days: timeRange,
  })
  const { data: timeSeries } = trpc.analytics.timeSeries.useQuery({
    agentId: selectedAgent === 'all' ? undefined : selectedAgent,
    days: timeRange,
  })
  const { data: topSenders } = trpc.analytics.topSenders.useQuery({
    agentId: selectedAgent === 'all' ? undefined : selectedAgent,
    days: timeRange,
    limit: 10,
  })
  const { data: responseMetrics } = trpc.analytics.responseMetrics.useQuery({
    agentId: selectedAgent === 'all' ? undefined : selectedAgent,
    days: timeRange,
  })
  const { data: costEstimate } = trpc.analytics.costEstimate.useQuery({
    agentId: selectedAgent === 'all' ? undefined : selectedAgent,
    days: timeRange,
  })

  const tierDistributionData = overview
    ? [
        { name: 'Tier 1: Escalate', value: overview.tierDistribution.tier1, fill: TIER_COLORS.tier1 },
        { name: 'Tier 2: Handle', value: overview.tierDistribution.tier2, fill: TIER_COLORS.tier2 },
        { name: 'Tier 3: Draft', value: overview.tierDistribution.tier3, fill: TIER_COLORS.tier3 },
        { name: 'Tier 4: Flag', value: overview.tierDistribution.tier4, fill: TIER_COLORS.tier4 },
      ]
    : []

  return (
    <div className="container mx-auto p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground mt-2">
          Insights and metrics for your email agents
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-8">
        <div className="w-64">
          <Select value={selectedAgent} onValueChange={setSelectedAgent}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Agents</SelectItem>
              {agents?.map((agent) => (
                <SelectItem key={agent.id} value={agent.id}>
                  {agent.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-48">
          <Select value={timeRange.toString()} onValueChange={(v) => setTimeRange(parseInt(v))}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="60">Last 60 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Emails</CardTitle>
            <Mail className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview?.totalEmails || 0}</div>
            <p className="text-xs text-muted-foreground">
              Last {timeRange} days
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {responseMetrics?.overall ? `${Math.round(responseMetrics.overall)}m` : '-'}
            </div>
            <p className="text-xs text-muted-foreground">
              Minutes to process
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Auto-Handled</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {overview?.tierDistribution.tier2 || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Tier 2 autonomous responses
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Estimated Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {costEstimate ? formatCurrency(costEstimate.estimatedCost) : '-'}
            </div>
            <p className="text-xs text-muted-foreground">
              API usage cost
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid gap-6 md:grid-cols-2 mb-6">
        {/* Email Volume Over Time */}
        <Card>
          <CardHeader>
            <CardTitle>Email Volume Over Time</CardTitle>
            <CardDescription>Daily email processing trends</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={timeSeries || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(date) => format(new Date(date), 'MMM d')}
                />
                <YAxis />
                <Tooltip
                  labelFormatter={(date) => format(new Date(date), 'MMM d, yyyy')}
                />
                <Legend />
                <Line type="monotone" dataKey="total" stroke="#8884d8" name="Total" />
                <Line type="monotone" dataKey="tier1" stroke={TIER_COLORS.tier1} name="Tier 1" />
                <Line type="monotone" dataKey="tier2" stroke={TIER_COLORS.tier2} name="Tier 2" />
                <Line type="monotone" dataKey="tier3" stroke={TIER_COLORS.tier3} name="Tier 3" />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Tier Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Tier Distribution</CardTitle>
            <CardDescription>Breakdown by classification tier</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={tierDistributionData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => `${name.split(':')[0]}: ${value}`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {tierDistributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2 */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Top Senders */}
        <Card>
          <CardHeader>
            <CardTitle>Top Senders</CardTitle>
            <CardDescription>Most frequent email senders</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topSenders || []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis
                  dataKey="email"
                  type="category"
                  width={150}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip />
                <Bar dataKey="count" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Response Time by Tier */}
        <Card>
          <CardHeader>
            <CardTitle>Response Time by Tier</CardTitle>
            <CardDescription>Average processing time (minutes)</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={responseMetrics?.byTier || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="tier"
                  tickFormatter={(tier) => `Tier ${tier}`}
                />
                <YAxis />
                <Tooltip
                  labelFormatter={(tier) => `Tier ${tier}`}
                  formatter={(value: number) => [`${Math.round(value)} min`, 'Avg Time']}
                />
                <Bar dataKey="avgResponseTime" fill="#8884d8">
                  {responseMetrics?.byTier?.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={TIER_COLORS[`tier${entry.tier}` as keyof typeof TIER_COLORS]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
