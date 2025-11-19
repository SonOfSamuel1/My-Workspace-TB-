/**
 * Volume Chart Component
 * Displays email volume over time
 */

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { format } from 'date-fns';

export default function VolumeChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        No data available
      </div>
    );
  }

  // Format data for recharts
  const chartData = data.map(item => ({
    ...item,
    date: format(new Date(item.date), 'MMM dd')
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="processed"
          stroke="#3b82f6"
          strokeWidth={2}
          name="Processed"
        />
        <Line
          type="monotone"
          dataKey="handled"
          stroke="#10b981"
          strokeWidth={2}
          name="Handled"
        />
        <Line
          type="monotone"
          dataKey="escalated"
          stroke="#ef4444"
          strokeWidth={2}
          name="Escalated"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
