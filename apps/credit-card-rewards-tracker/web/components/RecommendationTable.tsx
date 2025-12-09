'use client';

import { CategoryRecommendation } from '@/lib/data';

interface RecommendationTableProps {
  recommendations: CategoryRecommendation[];
}

export default function RecommendationTable({ recommendations }: RecommendationTableProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-100">
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Category</th>
            <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Best Card</th>
            <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Multiplier</th>
            <th className="text-center py-3 px-4 text-xs font-semibold text-gray-500 uppercase tracking-wider">Effective Return</th>
          </tr>
        </thead>
        <tbody>
          {recommendations.map((rec, index) => (
            <tr
              key={rec.category}
              className={`border-b border-gray-50 hover:bg-gray-50 transition-colors ${
                index % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'
              }`}
            >
              <td className="py-3 px-4">
                <span className="font-medium text-gray-900">{rec.category}</span>
              </td>
              <td className="py-3 px-4">
                <div>
                  <span className="text-gray-700">{rec.cardName}</span>
                  <span className="ml-2 text-xs text-gray-400">({rec.program})</span>
                </div>
              </td>
              <td className="py-3 px-4 text-center">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-orange-100 text-orange-800">
                  {rec.multiplier}x
                </span>
              </td>
              <td className="py-3 px-4 text-center">
                <span className={`font-semibold ${
                  rec.effectiveReturn >= 5 ? 'text-green-600' :
                  rec.effectiveReturn >= 3 ? 'text-orange-600' :
                  'text-gray-600'
                }`}>
                  {rec.effectiveReturn.toFixed(1)}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
