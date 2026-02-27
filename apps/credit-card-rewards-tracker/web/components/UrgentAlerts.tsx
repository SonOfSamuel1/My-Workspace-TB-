'use client';

import {
  Benefit,
  formatCurrency,
  getDaysUntilReset,
  isUrgent,
} from '@/lib/benefits-data';
import { AlertTriangle, Clock, ArrowRight } from 'lucide-react';

interface UrgentAlertsProps {
  benefits: Benefit[];
  onBenefitClick?: (benefitId: string) => void;
}

export default function UrgentAlerts({ benefits, onBenefitClick }: UrgentAlertsProps) {
  const urgentBenefits = benefits
    .filter((b) => b.isActive && isUrgent(b))
    .sort((a, b) => getDaysUntilReset(a) - getDaysUntilReset(b));

  if (urgentBenefits.length === 0) {
    return null;
  }

  return (
    <div className="bg-gradient-to-r from-orange-500 to-red-500 rounded-xl p-6 text-white shadow-lg">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-white/20 rounded-lg">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <div>
          <h2 className="text-xl font-bold">Action Required</h2>
          <p className="text-white/80 text-sm">
            {urgentBenefits.length} credit{urgentBenefits.length !== 1 ? 's' : ''} expiring soon
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {urgentBenefits.map((benefit) => {
          const daysLeft = getDaysUntilReset(benefit);
          const remaining = benefit.totalAmountCents - benefit.usedAmountCents;

          return (
            <div
              key={benefit.id}
              onClick={() => onBenefitClick?.(benefit.id)}
              className="bg-white/10 hover:bg-white/20 rounded-lg p-4 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold">{benefit.benefitName}</h3>
                    <span className="text-white/70 text-sm">• {benefit.cardName}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-2xl font-bold">{formatCurrency(remaining)}</span>
                    <span className="text-white/70">remaining</span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="flex items-center gap-1 text-white/90">
                      <Clock className="w-4 h-4" />
                      <span className="font-medium">
                        {daysLeft === 0
                          ? 'Today!'
                          : daysLeft === 1
                            ? 'Tomorrow'
                            : `${daysLeft} days`}
                      </span>
                    </div>
                    <div className="text-xs text-white/60">until reset</div>
                  </div>
                  <ArrowRight className="w-5 h-5 text-white/60" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 pt-4 border-t border-white/20">
        <div className="flex items-center justify-between text-sm">
          <span className="text-white/80">Total at risk:</span>
          <span className="text-xl font-bold">
            {formatCurrency(
              urgentBenefits.reduce(
                (sum, b) => sum + (b.totalAmountCents - b.usedAmountCents),
                0
              )
            )}
          </span>
        </div>
      </div>
    </div>
  );
}
