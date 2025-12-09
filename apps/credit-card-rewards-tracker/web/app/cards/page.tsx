import Navbar from '@/components/Navbar';
import CardItem from '@/components/CardItem';
import { sampleCards, formatCurrency } from '@/lib/data';

export default function CardsPage() {
  const totalAnnualFees = sampleCards.reduce((sum, card) => sum + card.annualFee, 0);
  const activeCards = sampleCards.filter((c) => c.isActive);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">My Cards</h1>
          <p className="text-gray-500 mt-1">Manage your credit card portfolio</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="text-sm text-gray-500 uppercase tracking-wider">Active Cards</div>
            <div className="text-3xl font-bold text-gray-900 mt-1">{activeCards.length}</div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="text-sm text-gray-500 uppercase tracking-wider">Total Annual Fees</div>
            <div className="text-3xl font-bold text-orange-600 mt-1">{formatCurrency(totalAnnualFees)}</div>
          </div>
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100">
            <div className="text-sm text-gray-500 uppercase tracking-wider">Reward Programs</div>
            <div className="text-3xl font-bold text-gray-900 mt-1">
              {new Set(sampleCards.map((c) => c.rewardProgram)).size}
            </div>
          </div>
        </div>

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sampleCards.map((card) => (
            <CardItem key={card.id} card={card} />
          ))}
        </div>

        {/* Annual Fee Summary */}
        <div className="mt-12">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Annual Fee Summary</h2>
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-100">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Card</th>
                  <th className="text-right py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Annual Fee</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Due Date</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody>
                {sampleCards.map((card) => (
                  <tr key={card.id} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="font-medium text-gray-900">{card.name}</div>
                      <div className="text-sm text-gray-500">{card.issuer.charAt(0).toUpperCase() + card.issuer.slice(1)}</div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      {card.annualFee > 0 ? (
                        <span className="font-semibold text-gray-900">{formatCurrency(card.annualFee)}</span>
                      ) : (
                        <span className="text-green-600 font-medium">No Fee</span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-600">
                      {card.annualFeeDueDate || '-'}
                    </td>
                    <td className="py-3 px-4">
                      {card.isActive ? (
                        <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-medium">Active</span>
                      ) : (
                        <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded-full text-xs font-medium">Inactive</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="bg-gray-50">
                  <td className="py-3 px-4 font-bold text-gray-900">Total</td>
                  <td className="py-3 px-4 text-right font-bold text-orange-600">{formatCurrency(totalAnnualFees)}</td>
                  <td colSpan={2}></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
