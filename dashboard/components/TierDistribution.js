/**
 * Tier Distribution Component
 * Displays tier distribution as a bar chart
 */

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';

const COLORS = {
  tier1: '#ef4444', // red
  tier2: '#10b981', // green
  tier3: '#3b82f6', // blue
  tier4: '#6b7280'  // gray
};

export default function TierDistribution({ data }) {
  if (!data || !data.counts) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        No data available
      </div>
    );
  }

  const chartData = [
    { name: 'Tier 1\nEscalated', count: data.counts.tier1, fill: COLORS.tier1 },
    { name: 'Tier 2\nHandled', count: data.counts.tier2, fill: COLORS.tier2 },
    { name: 'Tier 3\nDraft', count: data.counts.tier3, fill: COLORS.tier3 },
    { name: 'Tier 4\nFlagged', count: data.counts.tier4, fill: COLORS.tier4 }
  ];

  return (
    <div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" fontSize={12} />
          <YAxis />
          <Tooltip />
          <Bar dataKey="count" radius={[8, 8, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      <div className="mt-4 grid grid-cols-4 gap-2 text-center text-sm">
        {Object.entries(data.percentages).map(([tier, pct]) => (
          <div key={tier} className="text-gray-600">
            <div className="font-semibold">{pct}%</div>
            <div className="text-xs text-gray-500">{tier.replace('tier', 'T')}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
