"use client";

import * as React from "react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CategoryPicker } from "@/components/CategoryPicker";
import { formatCurrency, formatDate, milliunitsToDisplay, displayToMilliunits } from "@/lib/utils";
import type { Transaction, CategoryGroup, TransactionUpdate } from "@/lib/types";
import {
  Calendar,
  DollarSign,
  FileText,
  User,
  Building,
  Check,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock,
  Split,
} from "lucide-react";

interface TransactionEditorProps {
  transaction: Transaction;
  categories: CategoryGroup[];
  onSave: (update: TransactionUpdate) => Promise<void>;
  onApprove?: () => Promise<void>;
  onCancel?: () => void;
  onSplit?: () => void;
}

export function TransactionEditor({
  transaction,
  categories,
  onSave,
  onApprove,
  onCancel,
  onSplit,
}: TransactionEditorProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form state
  const [payeeName, setPayeeName] = useState(transaction.payee_name);
  const [memo, setMemo] = useState(transaction.memo || "");
  const [date, setDate] = useState(transaction.date);
  const [categoryId, setCategoryId] = useState(transaction.category_id);
  const [amount, setAmount] = useState(
    Math.abs(milliunitsToDisplay(transaction.amount)).toFixed(2)
  );

  const isOutflow = transaction.amount < 0;

  const handleSave = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const amountMilliunits = displayToMilliunits(parseFloat(amount));
      const update: TransactionUpdate = {
        id: transaction.id,
        payee_name: payeeName,
        memo: memo || null,
        date,
        category_id: categoryId,
        amount: isOutflow ? -Math.abs(amountMilliunits) : Math.abs(amountMilliunits),
      };

      await onSave(update);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save transaction");
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!onApprove) return;

    setIsLoading(true);
    setError(null);

    try {
      await onApprove();
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve transaction");
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadge = () => {
    if (!transaction.category_id) {
      return (
        <Badge variant="warning" className="flex items-center gap-1">
          <AlertCircle className="h-3 w-3" />
          Uncategorized
        </Badge>
      );
    }
    if (!transaction.approved) {
      return (
        <Badge variant="info" className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          Pending Approval
        </Badge>
      );
    }
    return (
      <Badge variant="success" className="flex items-center gap-1">
        <CheckCircle className="h-3 w-3" />
        Approved
      </Badge>
    );
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl">Edit Transaction</CardTitle>
          {getStatusBadge()}
        </div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Building className="h-4 w-4" />
          {transaction.account_name}
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Amount display */}
        <div className="flex items-center justify-center py-4">
          <span className={`text-4xl font-bold ${isOutflow ? "text-red-600" : "text-green-600"}`}>
            {isOutflow ? "-" : "+"}
            {formatCurrency(Math.abs(transaction.amount))}
          </span>
        </div>

        {/* Payee */}
        <div className="space-y-2">
          <Label htmlFor="payee" className="flex items-center gap-2">
            <User className="h-4 w-4" />
            Payee
          </Label>
          <Input
            id="payee"
            value={payeeName}
            onChange={(e) => setPayeeName(e.target.value)}
            placeholder="Enter payee name"
          />
        </div>

        {/* Category */}
        <div className="space-y-2">
          <Label className="flex items-center gap-2">
            <DollarSign className="h-4 w-4" />
            Category
          </Label>
          <CategoryPicker categories={categories} value={categoryId} onChange={setCategoryId} />
        </div>

        {/* Date */}
        <div className="space-y-2">
          <Label htmlFor="date" className="flex items-center gap-2">
            <Calendar className="h-4 w-4" />
            Date
          </Label>
          <Input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>

        {/* Memo */}
        <div className="space-y-2">
          <Label htmlFor="memo" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Memo
          </Label>
          <Input
            id="memo"
            value={memo}
            onChange={(e) => setMemo(e.target.value)}
            placeholder="Add a memo (optional)"
          />
        </div>

        {/* Amount (editable) */}
        <div className="space-y-2">
          <Label htmlFor="amount" className="flex items-center gap-2">
            <DollarSign className="h-4 w-4" />
            Amount
          </Label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
              $
            </span>
            <Input
              id="amount"
              type="number"
              step="0.01"
              min="0"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="pl-7"
            />
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
        )}

        {/* Success message */}
        {success && (
          <div className="rounded-md bg-green-100 p-3 text-sm text-green-800 flex items-center gap-2">
            <CheckCircle className="h-4 w-4" />
            Transaction saved successfully!
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-between gap-2">
        <div className="flex gap-2">
          {onCancel && (
            <Button variant="outline" onClick={onCancel} disabled={isLoading}>
              <X className="mr-2 h-4 w-4" />
              Cancel
            </Button>
          )}
          {onSplit && transaction.subtransactions.length === 0 && (
            <Button variant="outline" onClick={onSplit} disabled={isLoading}>
              <Split className="mr-2 h-4 w-4" />
              Split
            </Button>
          )}
        </div>

        <div className="flex gap-2">
          {!transaction.approved && onApprove && (
            <Button variant="success" onClick={handleApprove} disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Check className="mr-2 h-4 w-4" />
              )}
              Approve
            </Button>
          )}

          <Button onClick={handleSave} disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Check className="mr-2 h-4 w-4" />
            )}
            Save Changes
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
