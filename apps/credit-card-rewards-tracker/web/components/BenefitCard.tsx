'use client';

import { useState } from 'react';
import {
  Benefit,
  formatCurrency,
  getBenefitStatus,
  getDaysUntilReset,
  getProgressPercentage,
  isUrgent,
} from '@/lib/benefits-data';
import { Calendar, Clock, CreditCard, ChevronDown, ChevronUp, Check, AlertTriangle } from 'lucide-react';

interface BenefitCardProps {
  benefit: Benefit;
  onLogUsage?: (benefitId: string, amount: number) => void;
}

export default function BenefitCard({ benefit, onLogUsage }: BenefitCardProps) {
  const [expanded, setExpanded] = useState(false);
  const status = getBenefitStatus(benefit);
  const daysLeft = getDaysUntilReset(benefit);
  const progress = getProgressPercentage(benefit);
  const urgent = isUrgent(benefit);
  const remainingCents = benefit.totalAmountCents - benefit.usedAmountCents;

  // Status styling
  const getStatusStyles = () => {
    switch (status) {
      case 'captured':
        return {
          bg: 'bg-green-50',
          border: 'border-green-200',
          progressBg: 'bg-green-500',
          badge: 'bg-green-100 text-green-700',
          icon: <Check className="w-4 h-4" />,
        };
      case 'partial':
        return urgent
          ? {
              bg: 'bg-orange-50',
              border: 'border-orange-300',
              progressBg: 'bg-orange-500',
              badge: 'bg-orange-100 text-orange-700',
              icon: <AlertTriangle className="w-4 h-4" />,
            }
          : {
              bg: 'bg-yellow-50',
              border: 'border-yellow-200',
              progressBg: 'bg-yellow-500',
              badge: 'bg-yellow-100 text-yellow-700',
              icon: null,
            };
      case 'available':
        return urgent
          ? {
              bg: 'bg-red-50',
              border: 'border-red-300',
              progressBg: 'bg-red-500',
              badge: 'bg-red-100 text-red-700',
              icon: <AlertTriangle className="w-4 h-4" />,
            }
          : {
              bg: 'bg-white',
              border: 'border-gray-200',
              progressBg: 'bg-blue-500',
              badge: 'bg-blue-100 text-blue-700',
              icon: null,
            };
      default:
        return {
          bg: 'bg-gray-50',
          border: 'border-gray-200',
          progressBg: 'bg-gray-400',
          badge: 'bg-gray-100 text-gray-700',
          icon: null,
        };
    }
  };

  const styles = getStatusStyles();

  const getTypeLabel = () => {
    switch (benefit.type) {
      case 'monthly':
        return 'Monthly';
      case 'annual':
        return 'Annual';
      case 'semi-annual':
        return 'Semi-Annual';
      default:
        return benefit.type;
    }
  };

  const getResetLabel = () => {
    if (benefit.type === 'monthly') {
      if (daysLeft === 0) return 'Resets today';
      if (daysLeft === 1) return 'Resets tomorrow';
      return `Resets in ${daysLeft} days`;
    } else {
      if (daysLeft <= 0) return 'Reset date passed';
      if (daysLeft === 1) return 'Expires tomorrow';
      return `${daysLeft} days remaining`;
    }
  };

  return (
    <div
      className={`rounded-xl border-2 ${styles.bg} ${styles.border} ${urgent ? 'ring-2 ring-orange-400 ring-offset-2' : ''} transition-all duration-200`}
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gray-100 rounded-lg">
              <CreditCard className="w-5 h-5 text-gray-600" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">{benefit.benefitName}</h3>
              <p className="text-sm text-gray-500">{benefit.cardName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 rounded-full text-xs font-medium ${styles.badge} flex items-center gap-1`}>
              {styles.icon}
              {status === 'captured' ? 'Captured' : status === 'partial' ? 'Partial' : 'Available'}
            </span>
          </div>
        </div>

        {/* Progress Section */}
        <div className="mb-4">
          <div className="flex justify-between items-end mb-2">
            <div>
              <span className="text-2xl font-bold text-gray-900">
                {formatCurrency(benefit.usedAmountCents)}
              </span>
              <span className="text-gray-400"> / </span>
              <span className="text-lg text-gray-600">{formatCurrency(benefit.totalAmountCents)}</span>
            </div>
            {status !== 'captured' && remainingCents > 0 && (
              <div className="text-right">
                <span className="text-sm font-medium text-orange-600">
                  {formatCurrency(remainingCents)} left
                </span>
              </div>
            )}
          </div>

          {/* Progress Bar */}
          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full ${styles.progressBg} rounded-full transition-all duration-500`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Reset Info */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-1 text-gray-500">
              <Calendar className="w-4 h-4" />
              <span>{getTypeLabel()}</span>
            </div>
            <div className={`flex items-center gap-1 ${urgent ? 'text-orange-600 font-medium' : 'text-gray-500'}`}>
              <Clock className="w-4 h-4" />
              <span>{getResetLabel()}</span>
            </div>
          </div>

          <button
            onClick={() => setExpanded(!expanded)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-5 pb-5 pt-0 border-t border-gray-100 mt-2">
          <div className="pt-4 space-y-3">
            {/* Description */}
            <p className="text-sm text-gray-600">{benefit.description}</p>

            {/* Merchants */}
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                Eligible Merchants
              </p>
              <div className="flex flex-wrap gap-2">
                {benefit.merchants.map((merchant) => (
                  <span
                    key={merchant}
                    className="px-2 py-1 bg-gray-100 rounded text-xs text-gray-600"
                  >
                    {merchant}
                  </span>
                ))}
              </div>
            </div>

            {/* Last Used */}
            {benefit.lastUsedDate && (
              <p className="text-xs text-gray-500">
                Last used: {new Date(benefit.lastUsedDate).toLocaleDateString()}
              </p>
            )}

            {/* Log Usage Button */}
            {status !== 'captured' && onLogUsage && (
              <button
                onClick={() => onLogUsage(benefit.id, remainingCents)}
                className="w-full mt-3 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white font-medium rounded-lg transition-colors"
              >
                Log Usage
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
