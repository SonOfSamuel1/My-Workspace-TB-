'use client';

import { Card, formatCurrency } from '@/lib/data';
import { CreditCard } from 'lucide-react';

interface CardItemProps {
  card: Card;
}

const issuerColors: Record<string, string> = {
  chase: 'from-blue-600 to-blue-800',
  amex: 'from-blue-400 to-blue-600',
  discover: 'from-orange-500 to-orange-700',
  capital_one: 'from-red-600 to-red-800',
};

const issuerLogos: Record<string, string> = {
  chase: 'Chase',
  amex: 'AMEX',
  discover: 'DISCOVER',
  capital_one: 'Capital One',
};

export default function CardItem({ card }: CardItemProps) {
  const gradientClass = issuerColors[card.issuer] || 'from-gray-600 to-gray-800';

  return (
    <div className="relative">
      <div className={`bg-gradient-to-br ${gradientClass} rounded-xl p-5 text-white shadow-lg hover:shadow-xl transition-shadow`}>
        <div className="flex justify-between items-start mb-8">
          <div className="text-xs font-bold tracking-wider opacity-80">
            {issuerLogos[card.issuer] || card.issuer.toUpperCase()}
          </div>
          <CreditCard className="w-8 h-8 opacity-60" />
        </div>

        <div className="text-lg tracking-widest font-mono mb-4 opacity-90">
          •••• •••• •••• {card.lastFour}
        </div>

        <div className="flex justify-between items-end">
          <div>
            <div className="text-xs opacity-70 uppercase">Card Name</div>
            <div className="font-medium">{card.name}</div>
          </div>
          <div className="text-right">
            <div className="text-xs opacity-70 uppercase">Annual Fee</div>
            <div className="font-medium">
              {card.annualFee > 0 ? formatCurrency(card.annualFee) : 'No Fee'}
            </div>
          </div>
        </div>
      </div>

      {/* Category multipliers */}
      <div className="mt-3 flex flex-wrap gap-2">
        {card.categoryMultipliers.map((mult) => (
          <span
            key={mult.category}
            className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs font-medium"
          >
            {mult.category}: {mult.multiplier}x
          </span>
        ))}
        <span className="px-2 py-1 bg-gray-50 text-gray-500 rounded-full text-xs">
          Base: {card.baseRewardRate}x
        </span>
      </div>
    </div>
  );
}
