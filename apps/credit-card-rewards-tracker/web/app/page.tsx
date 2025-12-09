import Navbar from '@/components/Navbar';
import BalanceCard from '@/components/BalanceCard';
import RecommendationTable from '@/components/RecommendationTable';
import RedemptionList from '@/components/RedemptionList';
import {
  sampleBalances,
  sampleCashBack,
  sampleRecommendations,
  sampleRedemptions,
  calculateTotalValue,
  formatCurrency,
} from '@/lib/data';
import { TrendingUp, Wallet, CreditCard, ArrowRightLeft } from 'lucide-react';

export default function Home() {
  const totals = calculateTotalValue();

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Track and optimize your credit card rewards</p>
        </div>

        {/* Total Value Hero */}
        <div className="gradient-primary rounded-2xl p-8 text-white mb-8 shadow-lg">
          <div className="flex items-center gap-2 text-white/80 mb-2">
            <Wallet className="w-5 h-5" />
            <span className="text-sm font-medium uppercase tracking-wider">Total Rewards Value</span>
          </div>
          <div className="text-5xl font-bold mb-4">{formatCurrency(totals.totalValue)}</div>
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <span className="text-white/70">Points Value:</span>
              <span className="ml-2 font-semibold">{formatCurrency(totals.pointsValue)}</span>
            </div>
            <div>
              <span className="text-white/70">Cash Back:</span>
              <span className="ml-2 font-semibold">{formatCurrency(totals.cashBackValue)}</span>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-100 rounded-lg">
                <CreditCard className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">4</div>
                <div className="text-sm text-gray-500">Active Cards</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-green-100 rounded-lg">
                <ArrowRightLeft className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{sampleRedemptions.length}</div>
                <div className="text-sm text-gray-500">Redemptions YTD</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-orange-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">1.63 cpp</div>
                <div className="text-sm text-gray-500">Avg Redemption Value</div>
              </div>
            </div>
          </div>
        </div>

        {/* Balances Grid */}
        <div className="mb-8">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Current Balances</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {sampleBalances.map((balance) => (
              <BalanceCard
                key={balance.program}
                programName={balance.programName}
                points={balance.points}
                valueCents={balance.valueCents}
                lastUpdated={balance.lastUpdated}
                type="points"
              />
            ))}
            {sampleCashBack.map((cb) => (
              <BalanceCard
                key={cb.cardId}
                programName={cb.cardName}
                points={0}
                valueCents={cb.amountCents}
                lastUpdated={cb.lastUpdated}
                type="cash"
              />
            ))}
          </div>
        </div>

        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Best Cards */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Best Card by Category</h2>
            <RecommendationTable recommendations={sampleRecommendations.slice(0, 5)} />
          </div>

          {/* Recent Redemptions */}
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Redemptions</h2>
            <RedemptionList redemptions={sampleRedemptions.slice(0, 3)} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500">
            Credit Card Rewards Tracker &bull; Updated December 2025
          </p>
        </div>
      </footer>
    </div>
  );
}
