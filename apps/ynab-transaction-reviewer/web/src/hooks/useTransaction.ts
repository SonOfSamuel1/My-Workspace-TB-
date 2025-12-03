'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Transaction, CategoryGroup, TransactionUpdate } from '@/lib/types';

// Budget ID hardcoded for personal use - this is a single-user app
const BUDGET_ID = '2a373a3b-bc29-46f0-92ab-008f3b0221a9';

async function fetchTransaction(transactionId: string): Promise<Transaction> {
  const response = await fetch(`/api/ynab/budgets/${BUDGET_ID}/transactions/${transactionId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch transaction');
  }
  const data = await response.json();
  return data.data.transaction;
}

async function fetchCategories(): Promise<CategoryGroup[]> {
  const response = await fetch(`/api/ynab/budgets/${BUDGET_ID}/categories`);
  if (!response.ok) {
    throw new Error('Failed to fetch categories');
  }
  const data = await response.json();
  return data.data.category_groups;
}

async function updateTransaction(
  transactionId: string,
  update: Partial<TransactionUpdate>
): Promise<Transaction> {
  const response = await fetch(`/api/ynab/budgets/${BUDGET_ID}/transactions/${transactionId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ transaction: update }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error?.detail || 'Failed to update transaction');
  }
  const data = await response.json();
  return data.data.transaction;
}

export function useTransaction(transactionId: string) {
  return useQuery({
    queryKey: ['transaction', transactionId],
    queryFn: () => fetchTransaction(transactionId),
    enabled: !!transactionId,
  });
}

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: fetchCategories,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useUpdateTransaction() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      transactionId,
      update,
    }: {
      transactionId: string;
      update: Partial<TransactionUpdate>;
    }) => updateTransaction(transactionId, update),
    onSuccess: (data, variables) => {
      // Update the transaction in the cache
      queryClient.setQueryData(['transaction', variables.transactionId], data);
      // Invalidate transactions list
      queryClient.invalidateQueries({ queryKey: ['transactions'] });
    },
  });
}

export function useApproveTransaction() {
  const updateMutation = useUpdateTransaction();

  return {
    ...updateMutation,
    mutateAsync: (transactionId: string) =>
      updateMutation.mutateAsync({
        transactionId,
        update: { approved: true },
      }),
  };
}
