"use client";

import { QueryClient } from "@tanstack/react-query";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { useState, useEffect } from "react";

// Create persister for localStorage
const persister =
  typeof window !== "undefined"
    ? createSyncStoragePersister({
        storage: window.localStorage,
        key: "ynab-dashboard-cache",
      })
    : undefined;

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes default
            gcTime: 7 * 24 * 60 * 60 * 1000, // 7 days for persistence
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  // Check for 12-hour auto-refresh on mount
  useEffect(() => {
    const TWELVE_HOURS = 12 * 60 * 60 * 1000;
    const lastFetch = localStorage.getItem("ynab-all-transactions-timestamp");
    const isStale = !lastFetch || Date.now() - parseInt(lastFetch) > TWELVE_HOURS;

    if (isStale) {
      // Invalidate all-transactions cache to trigger refetch
      queryClient.invalidateQueries({ queryKey: ["transactions", "all"] });
    }
  }, [queryClient]);

  if (!persister) {
    // Fallback for SSR - use regular QueryClientProvider
    return (
      <PersistQueryClientProvider
        client={queryClient}
        persistOptions={{ persister: undefined as never }}
      >
        {children}
      </PersistQueryClientProvider>
    );
  }

  return (
    <PersistQueryClientProvider
      client={queryClient}
      persistOptions={{
        persister,
        maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
      }}
    >
      {children}
    </PersistQueryClientProvider>
  );
}
