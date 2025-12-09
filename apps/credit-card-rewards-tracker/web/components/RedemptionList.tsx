'use client';

import { Redemption, formatCurrency } from '@/lib/data';
import { ArrowRightLeft, Plane, Gift, CreditCard } from 'lucide-react';

interface RedemptionListProps {
  redemptions: Redemption[];
}

const typeIcons: Record<string, React.ReactNode> = {
  transfer_partner: <ArrowRightLeft className="w-5 h-5" />,
  travel_portal: <Plane className="w-5 h-5" />,
  statement_credit: <CreditCard className="w-5 h-5" />,
  gift_card: <Gift className="w-5 h-5" />,
};

const programColors: Record<string, string> = {
  chase_ultimate_rewards: 'bg-blue-100 text-blue-800',
  amex_membership_rewards: 'bg-indigo-100 text-indigo-800',
  capital_one_miles: 'bg-red-100 text-red-800',
  cash_back: 'bg-green-100 text-green-800',
};

export default function RedemptionList({ redemptions }: RedemptionListProps) {
  return (
    <div className="space-y-3">
      {redemptions.map((red) => (
        <div
          key={red.id}
          className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 hover:shadow-md transition-shadow"
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className="p-2 bg-gray-100 rounded-lg text-gray-600">
                {typeIcons[red.redemptionType] || <Gift className="w-5 h-5" />}
              </div>
              <div>
                <div className="font-medium text-gray-900">
                  {red.partner || red.redemptionType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </div>
                <div className="text-sm text-gray-500">
                  {red.notes}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${programColors[red.program] || 'bg-gray-100 text-gray-600'}`}>
                    {red.program.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </span>
                  <span className="text-xs text-gray-400">{red.date}</span>
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="font-bold text-green-600 text-lg">
                {formatCurrency(red.valueReceivedCents)}
              </div>
              {red.pointsRedeemed > 0 && (
                <div className="text-sm text-gray-500">
                  {red.pointsRedeemed.toLocaleString()} pts
                </div>
              )}
              <div className={`text-xs font-medium mt-1 ${
                red.centsPerPoint >= 2 ? 'text-green-600' :
                red.centsPerPoint >= 1.5 ? 'text-orange-600' :
                'text-gray-500'
              }`}>
                {red.centsPerPoint.toFixed(2)} cpp
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
