'use client';

import { useState } from 'react';
import Navbar from '@/components/Navbar';
import BenefitCard from '@/components/BenefitCard';
import {
  sampleBenefits,
  formatCurrency,
  getBenefitStatus,
  BenefitType,
  BenefitStatus,
} from '@/lib/benefits-data';
import { Filter, SortDesc } from 'lucide-react';

type SortOption = 'card' | 'expiring' | 'amount' | 'status';
type FilterType = 'all' | BenefitType;
type FilterStatus = 'all' | BenefitStatus;

export default function BenefitsPage() {
  const [sortBy, setSortBy] = useState<SortOption>('card');
  const [filterType, setFilterType] = useState<FilterType>('all');
  const [filterStatus, setFilterStatus] = useState<FilterStatus>('all');
  const [filterCard, setFilterCard] = useState<string>('all');

  // Get unique card names
  const cardNames = Array.from(new Set(sampleBenefits.map((b) => b.cardName)));

  // Filter benefits
  let filteredBenefits = sampleBenefits.filter((b) => b.isActive);

  if (filterType !== 'all') {
    filteredBenefits = filteredBenefits.filter((b) => b.type === filterType);
  }

  if (filterStatus !== 'all') {
    filteredBenefits = filteredBenefits.filter((b) => getBenefitStatus(b) === filterStatus);
  }

  if (filterCard !== 'all') {
    filteredBenefits = filteredBenefits.filter((b) => b.cardName === filterCard);
  }

  // Sort benefits
  filteredBenefits = [...filteredBenefits].sort((a, b) => {
    switch (sortBy) {
      case 'card':
        return a.cardName.localeCompare(b.cardName);
      case 'expiring':
        // Sort by days until reset
        const getDays = (benefit: typeof a) => {
          if (benefit.type === 'monthly' && benefit.resetDay) {
            const now = new Date();
            const currentMonth = now.getMonth();
            const currentYear = now.getFullYear();
            let resetDate = new Date(currentYear, currentMonth, benefit.resetDay);
            if (now.getDate() >= benefit.resetDay) {
              resetDate = new Date(currentYear, currentMonth + 1, benefit.resetDay);
            }
            return Math.ceil((resetDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
          } else if (benefit.resetDate) {
            const resetDate = new Date(benefit.resetDate);
            const now = new Date();
            if (resetDate < now) {
              resetDate.setFullYear(resetDate.getFullYear() + 1);
            }
            return Math.ceil((resetDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
          }
          return 999;
        };
        return getDays(a) - getDays(b);
      case 'amount':
        return b.totalAmountCents - a.totalAmountCents;
      case 'status':
        const statusOrder = { available: 0, partial: 1, captured: 2, expired: 3 };
        return statusOrder[getBenefitStatus(a)] - statusOrder[getBenefitStatus(b)];
      default:
        return 0;
    }
  });

  // Calculate totals for filtered benefits
  const totalAvailable = filteredBenefits.reduce((sum, b) => sum + b.totalAmountCents, 0);
  const totalUsed = filteredBenefits.reduce((sum, b) => sum + b.usedAmountCents, 0);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">All Benefits</h1>
          <p className="text-gray-500 mt-1">View and filter all your credit card benefits</p>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2 text-gray-600">
              <Filter className="w-5 h-5" />
              <span className="font-medium">Filters:</span>
            </div>

            {/* Type Filter */}
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as FilterType)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="all">All Types</option>
              <option value="monthly">Monthly</option>
              <option value="annual">Annual</option>
              <option value="semi-annual">Semi-Annual</option>
            </select>

            {/* Status Filter */}
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as FilterStatus)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="all">All Statuses</option>
              <option value="available">Available</option>
              <option value="partial">Partial</option>
              <option value="captured">Captured</option>
            </select>

            {/* Card Filter */}
            <select
              value={filterCard}
              onChange={(e) => setFilterCard(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="all">All Cards</option>
              {cardNames.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>

            <div className="flex-1" />

            {/* Sort */}
            <div className="flex items-center gap-2">
              <SortDesc className="w-5 h-5 text-gray-400" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
              >
                <option value="card">Sort by Card</option>
                <option value="expiring">Sort by Expiring Soon</option>
                <option value="amount">Sort by Amount</option>
                <option value="status">Sort by Status</option>
              </select>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="flex items-center justify-between mb-6 p-4 bg-white rounded-lg border border-gray-100">
          <div className="text-sm text-gray-600">
            Showing <span className="font-semibold text-gray-900">{filteredBenefits.length}</span> benefits
          </div>
          <div className="flex items-center gap-6 text-sm">
            <div>
              <span className="text-gray-500">Total Value:</span>
              <span className="ml-2 font-semibold text-gray-900">{formatCurrency(totalAvailable)}</span>
            </div>
            <div>
              <span className="text-gray-500">Used:</span>
              <span className="ml-2 font-semibold text-green-600">{formatCurrency(totalUsed)}</span>
            </div>
            <div>
              <span className="text-gray-500">Remaining:</span>
              <span className="ml-2 font-semibold text-orange-600">
                {formatCurrency(totalAvailable - totalUsed)}
              </span>
            </div>
          </div>
        </div>

        {/* Benefits Grid */}
        {filteredBenefits.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredBenefits.map((benefit) => (
              <BenefitCard key={benefit.id} benefit={benefit} />
            ))}
          </div>
        ) : (
          <div className="text-center py-12 bg-white rounded-xl border border-gray-100">
            <p className="text-gray-500">No benefits match your filters</p>
            <button
              onClick={() => {
                setFilterType('all');
                setFilterStatus('all');
                setFilterCard('all');
              }}
              className="mt-4 px-4 py-2 text-orange-600 hover:bg-orange-50 rounded-lg transition-colors"
            >
              Clear Filters
            </button>
          </div>
        )}
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
