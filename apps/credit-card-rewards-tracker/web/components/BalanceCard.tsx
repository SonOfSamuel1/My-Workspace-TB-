'use client';

import { formatCurrency, formatNumber } from '@/lib/data';

interface BalanceCardProps {
  programName: string;
  points: number;
  valueCents: number;
  lastUpdated: string;
  type?: 'points' | 'cash';
}

export default function BalanceCard({ programName, points, valueCents, lastUpdated, type = 'points' }: BalanceCardProps) {
  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
      <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
        {programName}
      </div>
      <div className="text-3xl font-bold text-gray-900 mb-1">
        {type === 'points' ? (
          <>{formatNumber(points)} <span className="text-lg font-normal text-gray-500">pts</span></>
        ) : (
          formatCurrency(valueCents)
        )}
      </div>
      <div className="text-lg font-semibold text-orange-600">
        {formatCurrency(valueCents)}
      </div>
      <div className="text-xs text-gray-400 mt-2">
        Updated {lastUpdated}
      </div>
    </div>
  );
}
