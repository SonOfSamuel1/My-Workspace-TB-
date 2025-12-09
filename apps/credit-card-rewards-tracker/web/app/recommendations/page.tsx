import Navbar from '@/components/Navbar';
import RecommendationTable from '@/components/RecommendationTable';
import { sampleRecommendations, sampleCards } from '@/lib/data';
import { Lightbulb, AlertTriangle, CheckCircle } from 'lucide-react';

export default function RecommendationsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Best Card by Category</h1>
          <p className="text-gray-500 mt-1">Maximize your rewards with these recommendations</p>
        </div>

        {/* Quick Tips */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-green-50 rounded-xl p-5 border border-green-100">
            <div className="flex items-start gap-3">
              <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
              <div>
                <div className="font-semibold text-green-900">Best Return</div>
                <div className="text-sm text-green-700 mt-1">
                  Use Venture X for travel bookings - up to 10% return!
                </div>
              </div>
            </div>
          </div>
          <div className="bg-orange-50 rounded-xl p-5 border border-orange-100">
            <div className="flex items-start gap-3">
              <Lightbulb className="w-6 h-6 text-orange-600 flex-shrink-0" />
              <div>
                <div className="font-semibold text-orange-900">Pro Tip</div>
                <div className="text-sm text-orange-700 mt-1">
                  Stack grocery bonuses with store promotions for extra savings
                </div>
              </div>
            </div>
          </div>
          <div className="bg-yellow-50 rounded-xl p-5 border border-yellow-100">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0" />
              <div>
                <div className="font-semibold text-yellow-900">Reminder</div>
                <div className="text-sm text-yellow-700 mt-1">
                  Quarterly category activations may be required
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Recommendations Table */}
        <div className="mb-12">
          <RecommendationTable recommendations={sampleRecommendations} />
        </div>

        {/* Category Deep Dive */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* High Value Categories */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="font-bold text-gray-900 mb-4">High Value Categories</h3>
            <div className="space-y-4">
              {sampleRecommendations
                .filter((r) => r.effectiveReturn >= 4)
                .map((rec) => (
                  <div key={rec.category} className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900">{rec.category}</div>
                      <div className="text-sm text-gray-500">{rec.cardName}</div>
                    </div>
                    <div className="text-xl font-bold text-green-600">{rec.effectiveReturn}%</div>
                  </div>
                ))}
            </div>
          </div>

          {/* Card Usage Strategy */}
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-100">
            <h3 className="font-bold text-gray-900 mb-4">Quick Card Strategy</h3>
            <div className="space-y-4">
              {sampleCards.slice(0, 4).map((card) => {
                const topCategory = card.categoryMultipliers.sort((a, b) => b.multiplier - a.multiplier)[0];
                return (
                  <div key={card.id} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                    <div className="w-12 h-8 bg-gradient-to-r from-gray-700 to-gray-900 rounded flex items-center justify-center">
                      <span className="text-white text-xs font-bold">{card.issuer.slice(0, 2).toUpperCase()}</span>
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 text-sm">{card.name}</div>
                      <div className="text-xs text-gray-500">
                        Best for: {topCategory?.category || 'General'} ({topCategory?.multiplier || card.baseRewardRate}x)
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Optimization Tips */}
        <div className="mt-8 bg-gradient-to-r from-orange-500 to-red-500 rounded-xl p-6 text-white">
          <h3 className="font-bold text-xl mb-4">Optimization Strategies</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white/10 rounded-lg p-4">
              <div className="font-semibold mb-2">Transfer Partners</div>
              <p className="text-sm text-white/80">
                Chase UR and Amex MR points are most valuable when transferred to airline/hotel partners.
                Target 1.5-2.0+ cpp for best value.
              </p>
            </div>
            <div className="bg-white/10 rounded-lg p-4">
              <div className="font-semibold mb-2">Category Stacking</div>
              <p className="text-sm text-white/80">
                Use shopping portals + category bonuses + store promotions to multiply rewards
                on single purchases.
              </p>
            </div>
            <div className="bg-white/10 rounded-lg p-4">
              <div className="font-semibold mb-2">Annual Fee ROI</div>
              <p className="text-sm text-white/80">
                Track rewards earned vs fees paid. Consider downgrading cards with less than 100% ROI.
              </p>
            </div>
            <div className="bg-white/10 rounded-lg p-4">
              <div className="font-semibold mb-2">Retention Offers</div>
              <p className="text-sm text-white/80">
                Call 60 days before annual fee posts to request retention offers - free points or statement credits!
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
