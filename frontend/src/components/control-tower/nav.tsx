"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/intake", label: "Intake" },
  { href: "/mandate", label: "Mandate" },
  { href: "/sessions", label: "Sessions" },
  { href: "/comparison", label: "Comparison" },
  { href: "/evidence", label: "Evidence" },
  { href: "/recovery", label: "Recovery" },
  { href: "/escalation", label: "Escalation" },
  { href: "/audit", label: "Audit" },
] as const;

export function ControlTowerNav() {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary navigation" className="min-w-0">
      <ul className="flex flex-nowrap items-center gap-1 overflow-x-auto py-1 font-mono text-xs font-medium sm:gap-2 sm:text-sm">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/"
              ? pathname === "/"
              : pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <li key={item.href} className="shrink-0">
              <Link
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "inline-flex items-center rounded-md px-3 py-2 whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
                  isActive
                    ? "bg-secondary text-secondary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
