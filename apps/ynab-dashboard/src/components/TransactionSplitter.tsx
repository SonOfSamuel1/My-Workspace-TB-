'use client';

import * as React from 'react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { CategoryPicker } from '@/components/CategoryPicker';
import { formatCurrency, milliunitsToDisplay, displayToMilliunits } from '@/lib/utils';
import type { CategoryGroup, SubTransactionUpdate } from '@/lib/types';
import { Plus, Trash2, Check, X, Loader2, AlertCircle } from 'lucide-react';

interface SplitRow {
  id: string;
  amount: string;
  categoryId: string | null;
  memo: string;
}

interface TransactionSplitterProps {
  totalAmount: number; // In milliunits
  categories: CategoryGroup[];
  onSave: (splits: SubTransactionUpdate[]) => Promise<void>;
  onCancel: () => void;
}

export function TransactionSplitter({
  totalAmount,
  categories,
  onSave,
  onCancel,
}: TransactionSplitterProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isOutflow = totalAmount < 0;
  const absTotal = Math.abs(milliunitsToDisplay(totalAmount));

  const [splits, setSplits] = useState<SplitRow[]>([
    {
      id: crypto.randomUUID(),
      amount: absTotal.toFixed(2),
      categoryId: null,
      memo: '',
    },
  ]);

  const addSplit = () => {
    setSplits([
      ...splits,
      {
        id: crypto.randomUUID(),
        amount: '0.00',
        categoryId: null,
        memo: '',
      },
    ]);
  };

  const removeSplit = (id: string) => {
    if (splits.length > 1) {
      setSplits(splits.filter((s) => s.id !== id));
    }
  };

  const updateSplit = (id: string, field: keyof SplitRow, value: string) => {
    setSplits(
      splits.map((s) => (s.id === id ? { ...s, [field]: value } : s))
    );
  };

  const updateSplitCategory = (id: string, categoryId: string) => {
    setSplits(
      splits.map((s) => (s.id === id ? { ...s, categoryId } : s))
    );
  };

  // Calculate totals
  const splitTotal = splits.reduce(
    (sum, s) => sum + (parseFloat(s.amount) || 0),
    0
  );
  const remaining = absTotal - splitTotal;
  const isBalanced = Math.abs(remaining) < 0.01;

  const handleSave = async () => {
    if (!isBalanced) {
      setError('Split amounts must equal the transaction total');
      return;
    }

    // Check all splits have categories
    const uncategorized = splits.filter((s) => !s.categoryId);
    if (uncategorized.length > 0) {
      setError('All splits must have a category');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const subTransactions: SubTransactionUpdate[] = splits.map((s) => ({
        amount: isOutflow
          ? -displayToMilliunits(parseFloat(s.amount))
          : displayToMilliunits(parseFloat(s.amount)),
        category_id: s.categoryId,
        memo: s.memo || null,
      }));

      await onSave(subTransactions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save split');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="text-xl">Split Transaction</CardTitle>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            Total: {formatCurrency(totalAmount)}
          </span>
          <span
            className={
              isBalanced
                ? 'text-green-600'
                : remaining > 0
                ? 'text-amber-600'
                : 'text-red-600'
            }
          >
            {isBalanced
              ? 'Balanced'
              : remaining > 0
              ? `$${remaining.toFixed(2)} remaining`
              : `$${Math.abs(remaining).toFixed(2)} over`}
          </span>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {splits.map((split, index) => (
          <div key={split.id} className="flex gap-3 items-start p-3 rounded-lg bg-muted/50">
            <div className="flex-1 space-y-3">
              {/* Amount */}
              <div className="flex gap-3">
                <div className="w-32">
                  <Label className="text-xs">Amount</Label>
                  <div className="relative">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground text-sm">
                      $
                    </span>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={split.amount}
                      onChange={(e) =>
                        updateSplit(split.id, 'amount', e.target.value)
                      }
                      className="pl-6 h-9"
                    />
                  </div>
                </div>

                {/* Category */}
                <div className="flex-1">
                  <Label className="text-xs">Category</Label>
                  <CategoryPicker
                    categories={categories}
                    value={split.categoryId}
                    onChange={(id) => updateSplitCategory(split.id, id)}
                  />
                </div>
              </div>

              {/* Memo */}
              <div>
                <Label className="text-xs">Memo (optional)</Label>
                <Input
                  value={split.memo}
                  onChange={(e) => updateSplit(split.id, 'memo', e.target.value)}
                  placeholder="Add a memo"
                  className="h-9"
                />
              </div>
            </div>

            {/* Remove button */}
            {splits.length > 1 && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => removeSplit(split.id)}
                className="mt-5"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        ))}

        {/* Add split button */}
        <Button variant="outline" onClick={addSplit} className="w-full">
          <Plus className="mr-2 h-4 w-4" />
          Add Split
        </Button>

        {/* Error message */}
        {error && (
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            {error}
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-end gap-2">
        <Button variant="outline" onClick={onCancel} disabled={isLoading}>
          <X className="mr-2 h-4 w-4" />
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={isLoading || !isBalanced}>
          {isLoading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Check className="mr-2 h-4 w-4" />
          )}
          Save Split
        </Button>
      </CardFooter>
    </Card>
  );
}
