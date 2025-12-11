"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export function Navigation() {
  const pathname = usePathname();

  const tabs = [
    { href: "/", label: "Needs Approval" },
    { href: "/all-transactions", label: "All Transactions" },
  ];

  return (
    <nav className="border-b bg-background">
      <div className="mx-auto max-w-2xl px-4">
        <div className="flex gap-4">
          {tabs.map((tab) => (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "py-3 text-sm font-medium border-b-2 -mb-px transition-colors",
                pathname === tab.href
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground"
              )}
            >
              {tab.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
