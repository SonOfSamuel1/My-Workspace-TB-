import Navbar from '@/components/Navbar';
import RedemptionList from '@/components/RedemptionList';
import { sampleRedemptions, formatCurrency } from '@/lib/data';
import { TrendingUp, Award, Target, DollarSign } from 'lucide-react';

export default function RedemptionsPage() {
  const totalValueReceived = sampleRedemptions.reduce((sum, r) => sum + r.valueReceivedCents, 0);
  const totalPointsRedeemed = sampleRedemptions.reduce((sum, r) => sum + r.pointsRedeemed, 0);
  const avgCpp = totalPointsRedeemed > 0 ? totalValueReceived / totalPointsRedeemed : 0;
  const bestCpp = Math.max(...sampleRedemptions.map((r) => r.centsPerPoint));

  // Group by type
  const byType = sampleRedemptions.reduce((acc, r) => {
    const type = r.redemptionType;
    if (!acc[type]) acc[type] = { count: 0, value: 0 };
    acc[type].count++;
    acc[type].value += r.valueReceivedCents;
    return acc;
  }, {} as Record<string, { count: number; value: number }>);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Redemptions</h1>
          <p className="text-gray-500 mt-1">Track your reward redemption history and value</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-green-100 rounded-lg">
                <DollarSign className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{formatCurrency(totalValueReceived)}</div>
                <div className="text-sm text-gray-500">Total Value Received</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Target className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{totalPointsRedeemed.toLocaleString()}</div>
                <div className="text-sm text-gray-500">Points Redeemed</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-orange-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{avgCpp.toFixed(2)} cpp</div>
                <div className="text-sm text-gray-500">Average Value</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-yellow-100 rounded-lg">
                <Award className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{bestCpp.toFixed(2)} cpp</div>
                <div className="text-sm text-gray-500">Best Redemption</div>
              </div>
            </div>
          </div>
        </div>

        {/* Redemption Value Guide */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 mb-8">
          <h2 className="font-bold text-gray-900 mb-4">Redemption Value Guide</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center p-4 rounded-lg bg-red-50 border border-red-100">
              <div className="text-2xl font-bold text-red-600">&lt; 1.0 cpp</div>
              <div className="text-sm text-red-700 mt-1">Poor Value</div>
              <div className="text-xs text-red-500 mt-2">Avoid if possible</div>
            </div>
            <div className="text-center p-4 rounded-lg bg-yellow-50 border border-yellow-100">
              <div className="text-2xl font-bold text-yellow-600">1.0 - 1.25 cpp</div>
              <div className="text-sm text-yellow-700 mt-1">Baseline Value</div>
              <div className="text-xs text-yellow-500 mt-2">Cash back, statement credit</div>
            </div>
            <div className="text-center p-4 rounded-lg bg-green-50 border border-green-100">
              <div className="text-2xl font-bold text-green-600">1.25 - 2.0 cpp</div>
              <div className="text-sm text-green-700 mt-1">Good Value</div>
              <div className="text-xs text-green-500 mt-2">Travel portal, transfers</div>
            </div>
            <div className="text-center p-4 rounded-lg bg-emerald-50 border border-emerald-100">
              <div className="text-2xl font-bold text-emerald-600">&gt; 2.0 cpp</div>
              <div className="text-sm text-emerald-700 mt-1">Excellent Value</div>
              <div className="text-xs text-emerald-500 mt-2">Sweet spot transfers</div>
            </div>
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Redemption List */}
          <div className="lg:col-span-2">
            <h2 className="font-bold text-gray-900 mb-4">Redemption History</h2>
            <RedemptionList redemptions={sampleRedemptions} />
          </div>

          {/* Summary by Type */}
          <div>
            <h2 className="font-bold text-gray-900 mb-4">By Redemption Type</h2>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
              {Object.entries(byType).map(([type, data]) => (
                <div key={type} className="p-4 border-b border-gray-50 last:border-b-0">
                  <div className="flex justify-between items-center">
                    <div>
                      <div className="font-medium text-gray-900 capitalize">
                        {type.replace(/_/g, ' ')}
                      </div>
                      <div className="text-sm text-gray-500">{data.count} redemptions</div>
                    </div>
                    <div className="text-lg font-bold text-green-600">
                      {formatCurrency(data.value)}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Tips */}
            <div className="mt-6 bg-orange-50 rounded-xl p-5 border border-orange-100">
              <h3 className="font-semibold text-orange-900 mb-3">Maximize Redemption Value</h3>
              <ul className="space-y-2 text-sm text-orange-700">
                <li className="flex items-start gap-2">
                  <span className="text-orange-500">•</span>
                  Transfer to Hyatt for 2+ cpp on hotel stays
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-orange-500">•</span>
                  Use Chase Pay Yourself Back for 1.25 cpp
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-orange-500">•</span>
                  Avoid gift card redemptions (&lt;1 cpp)
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-orange-500">•</span>
                  Check transfer bonuses before redeeming
                </li>
              </ul>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
