"use client";

import { useState } from "react";
import {
  useTransaction,
  useCategories,
  useUpdateTransaction,
  useApproveTransaction,
  useSplitTransaction,
} from "@/hooks/useTransaction";
import { TransactionEditor } from "@/components/TransactionEditor";
import { TransactionSplitter } from "@/components/TransactionSplitter";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { TransactionUpdate, SubTransactionUpdate } from "@/lib/types";
import { ArrowLeft, Loader2, AlertCircle, ExternalLink } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

export default function TransactionPage() {
  const params = useParams();
  const id = params.id as string;
  const [isSplitMode, setIsSplitMode] = useState(false);
  const { data: transaction, isLoading: txnLoading, error: txnError } = useTransaction(id);
  const { data: categories, isLoading: catLoading } = useCategories();
  const updateMutation = useUpdateTransaction();
  const approveMutation = useApproveTransaction();
  const splitMutation = useSplitTransaction();

  const isLoading = txnLoading || catLoading;

  const handleSave = async (update: TransactionUpdate) => {
    await updateMutation.mutateAsync({
      transactionId: id,
      update,
    });
  };

  const handleApprove = async () => {
    await approveMutation.mutateAsync(id);
  };

  const handleSplit = async (subtransactions: SubTransactionUpdate[]) => {
    await splitMutation.mutateAsync({
      transactionId: id,
      subtransactions,
    });
    setIsSplitMode(false);
  };

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-muted-foreground">Loading transaction...</p>
        </div>
      </div>
    );
  }

  if (txnError || !transaction) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-4 pt-6">
            <AlertCircle className="h-12 w-12 text-destructive" />
            <h2 className="text-xl font-semibold">Transaction Not Found</h2>
            <p className="text-center text-muted-foreground">
              {txnError instanceof Error
                ? txnError.message
                : "The transaction you are looking for could not be found."}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" asChild>
                <Link href="/">
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  Go Home
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/30 py-8 px-4">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <Button variant="ghost" asChild>
            <Link href="/">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Link>
          </Button>

          <Button variant="outline" asChild>
            <a
              href={`https://app.ynab.com/2a373a3b-bc29-46f0-92ab-008f3b0221a9/accounts/${transaction.account_id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              Open in YNAB
            </a>
          </Button>
        </div>

        {/* Transaction Editor or Splitter */}
        {isSplitMode ? (
          <TransactionSplitter
            totalAmount={transaction.amount}
            categories={categories || []}
            onSave={handleSplit}
            onCancel={() => setIsSplitMode(false)}
          />
        ) : (
          <TransactionEditor
            transaction={transaction}
            categories={categories || []}
            onSave={handleSave}
            onApprove={handleApprove}
            onSplit={() => setIsSplitMode(true)}
          />
        )}
      </div>
    </div>
  );
}
