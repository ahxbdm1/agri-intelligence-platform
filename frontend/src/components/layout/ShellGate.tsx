"use client";

import { usePathname } from "next/navigation";
import { AppShell } from "@/components/layout/AppShell";

const shelllessRoutes = new Set(["/", "/login"]);

export function ShellGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  if (shelllessRoutes.has(pathname)) {
    return <>{children}</>;
  }

  return <AppShell>{children}</AppShell>;
}
