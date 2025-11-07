/**
 * Dashboard Home Page
 * Real-time metrics and email management overview
 */

import { useState, useEffect } from 'react';
import useSWR from 'swr';
import Head from 'next/head';
import {
  ChartBarIcon,
  EnvelopeIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  CurrencyDollarIcon
} from '@heroicons/react/24/outline';

import MetricCard from '../components/MetricCard';
import EmailList from '../components/EmailList';
import VolumeChart from '../components/VolumeChart';
import TierDistribution from '../components/TierDistribution';
import PendingApprovals from '../components/PendingApprovals';

const fetcher = (url) => fetch(url).then((res) => res.json());

export default function Dashboard() {
  const { data: metrics, error: metricsError } = useSWR('/api/metrics', fetcher, {
    refreshInterval: 30000 // Refresh every 30 seconds
  });

  const { data: emails, error: emailsError } = useSWR('/api/emails/recent', fetcher, {
    refreshInterval: 60000
  });

  const { data: approvals, error: approvalsError } = useSWR('/api/approvals/pending', fetcher, {
    refreshInterval: 15000
  });

  const loading = !metrics && !metricsError;

  return (
    <div className="min-h-screen bg-gray-50">
      <Head>
        <title>Email Assistant Dashboard</title>
        <meta name="description" content="Autonomous Email Assistant Dashboard" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Email Assistant Dashboard
              </h1>
              <p className="mt-1 text-sm text-gray-500">
                Autonomous email processing and management
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <div className="flex items-center">
                <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse mr-2"></div>
                <span className="text-sm text-gray-600">System Active</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <>
            {/* Metrics Grid */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
              <MetricCard
                title="Emails Today"
                value={metrics?.today?.processed || 0}
                icon={EnvelopeIcon}
                color="blue"
                trend={metrics?.trends?.volumeChange}
              />
              <MetricCard
                title="Handled Autonomously"
                value={`${metrics?.today?.handledPct || 0}%`}
                icon={CheckCircleIcon}
                color="green"
                subtitle={`${metrics?.today?.handled || 0} emails`}
              />
              <MetricCard
                title="Pending Approval"
                value={approvals?.count || 0}
                icon={ClockIcon}
                color="yellow"
                urgent={approvals?.count > 5}
              />
              <MetricCard
                title="Escalated"
                value={metrics?.today?.escalated || 0}
                icon={ExclamationTriangleIcon}
                color="red"
              />
            </div>

            {/* Secondary Metrics */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 mb-8">
              <MetricCard
                title="Avg Response Time"
                value={metrics?.responseMetrics?.avg || '0m'}
                icon={ClockIcon}
                color="purple"
              />
              <MetricCard
                title="Cost Today"
                value={`$${metrics?.costs?.today || '0.00'}`}
                icon={CurrencyDollarIcon}
                color="indigo"
                subtitle={`Projected: $${metrics?.costs?.monthly || '0.00'}/mo`}
              />
              <MetricCard
                title="Success Rate"
                value={`${metrics?.productivity?.autonomousHandling || '0%'}`}
                icon={ChartBarIcon}
                color="teal"
              />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Email Volume (7 Days)
                </h2>
                <VolumeChart data={metrics?.volumeHistory || []} />
              </div>

              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Tier Distribution
                </h2>
                <TierDistribution data={metrics?.tierDistribution || {}} />
              </div>
            </div>

            {/* Pending Approvals */}
            {approvals && approvals.count > 0 && (
              <div className="mb-8">
                <PendingApprovals approvals={approvals.items || []} />
              </div>
            )}

            {/* Recent Emails */}
            <div className="bg-white rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">
                  Recent Emails
                </h2>
              </div>
              <EmailList emails={emails?.items || []} />
            </div>
          </>
        )}
      </main>
    </div>
  );
}
