import Navbar from '@/components/Navbar';
import BenefitCard from '@/components/BenefitCard';
import UrgentAlerts from '@/components/UrgentAlerts';
import {
  sampleBenefits,
  getBenefitsSummary,
  formatCurrency,
  getBenefitStatus,
} from '@/lib/benefits-data';
import { Wallet, Target, CheckCircle, AlertTriangle } from 'lucide-react';

export default function Home() {
  const summary = getBenefitsSummary(sampleBenefits);

  // Group benefits by card
  const benefitsByCard = sampleBenefits
    .filter((b) => b.isActive)
    .reduce(
      (acc, benefit) => {
        if (!acc[benefit.cardName]) {
          acc[benefit.cardName] = [];
        }
        acc[benefit.cardName].push(benefit);
        return acc;
      },
      {} as Record<string, typeof sampleBenefits>
    );

  // Separate monthly and annual benefits
  const monthlyBenefits = sampleBenefits.filter((b) => b.isActive && b.type === 'monthly');
  const annualBenefits = sampleBenefits.filter(
    (b) => b.isActive && (b.type === 'annual' || b.type === 'semi-annual')
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Credit Card Benefits</h1>
          <p className="text-gray-500 mt-1">Track and capture your card credits before they expire</p>
        </div>

        {/* Summary Hero */}
        <div className="gradient-primary rounded-2xl p-8 text-white mb-8 shadow-lg">
          <div className="flex items-center gap-2 text-white/80 mb-2">
            <Wallet className="w-5 h-5" />
            <span className="text-sm font-medium uppercase tracking-wider">This Month&apos;s Credits</span>
          </div>
          <div className="flex items-baseline gap-4 mb-4">
            <div className="text-5xl font-bold">{formatCurrency(summary.monthlyUsedCents)}</div>
            <div className="text-2xl text-white/70">/ {formatCurrency(summary.monthlyAvailableCents)}</div>
          </div>
          <div className="h-3 bg-white/20 rounded-full overflow-hidden mb-4">
            <div
              className="h-full bg-white rounded-full transition-all duration-500"
              style={{
                width: `${summary.monthlyAvailableCents > 0 ? (summary.monthlyUsedCents / summary.monthlyAvailableCents) * 100 : 0}%`,
              }}
            />
          </div>
          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <span className="text-white/70">Captured:</span>
              <span className="ml-2 font-semibold">{formatCurrency(summary.monthlyUsedCents)}</span>
            </div>
            <div>
              <span className="text-white/70">Remaining:</span>
              <span className="ml-2 font-semibold">{formatCurrency(summary.monthlyRemainingCents)}</span>
            </div>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-100 rounded-lg">
                <Target className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{summary.totalBenefits}</div>
                <div className="text-sm text-gray-500">Active Benefits</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-green-100 rounded-lg">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{summary.capturedCount}</div>
                <div className="text-sm text-gray-500">Fully Captured</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-orange-100 rounded-lg">
                <AlertTriangle className="w-6 h-6 text-orange-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">{summary.urgentCount}</div>
                <div className="text-sm text-gray-500">Expiring Soon</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-purple-100 rounded-lg">
                <Wallet className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">
                  {formatCurrency(summary.totalRemainingCents)}
                </div>
                <div className="text-sm text-gray-500">Total Available</div>
              </div>
            </div>
          </div>
        </div>

        {/* Urgent Alerts */}
        <div className="mb-8">
          <UrgentAlerts benefits={sampleBenefits} />
        </div>

        {/* Monthly Credits Section */}
        <div className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Monthly Credits</h2>
            <span className="text-sm text-gray-500">
              {monthlyBenefits.filter((b) => getBenefitStatus(b) === 'captured').length} of{' '}
              {monthlyBenefits.length} captured
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {monthlyBenefits.map((benefit) => (
              <BenefitCard key={benefit.id} benefit={benefit} />
            ))}
          </div>
        </div>

        {/* Annual/Semi-Annual Credits Section */}
        <div className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Annual &amp; Semi-Annual Credits</h2>
            <span className="text-sm text-gray-500">
              {annualBenefits.filter((b) => getBenefitStatus(b) === 'captured').length} of{' '}
              {annualBenefits.length} captured
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {annualBenefits.map((benefit) => (
              <BenefitCard key={benefit.id} benefit={benefit} />
            ))}
          </div>
        </div>

        {/* Tips Section */}
        <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl p-6 text-white">
          <h3 className="font-bold text-xl mb-4">Tips to Maximize Your Credits</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white/10 rounded-lg p-4">
              <div className="font-semibold mb-2">Set Calendar Reminders</div>
              <p className="text-sm text-white/80">
                Add reminders on the 20th of each month to use expiring monthly credits.
              </p>
            </div>
            <div className="bg-white/10 rounded-lg p-4">
              <div className="font-semibold mb-2">Stack with Promotions</div>
              <p className="text-sm text-white/80">
                Combine card credits with merchant promotions for extra value.
              </p>
            </div>
            <div className="bg-white/10 rounded-lg p-4">
              <div className="font-semibold mb-2">Use Full Amount</div>
              <p className="text-sm text-white/80">
                Credits don&apos;t roll over - use the full amount each period.
              </p>
            </div>
            <div className="bg-white/10 rounded-lg p-4">
              <div className="font-semibold mb-2">Check Eligible Merchants</div>
              <p className="text-sm text-white/80">
                Verify purchases qualify before buying to ensure credit applies.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500">
            Credit Card Benefits Tracker &bull; Updated December 2025
          </p>
        </div>
      </footer>
    </div>
  );
}
