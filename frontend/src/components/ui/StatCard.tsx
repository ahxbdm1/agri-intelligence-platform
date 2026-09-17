"use client";

import { useRef } from "react";
import type { LucideIcon } from "lucide-react";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { formatNumber } from "@/lib/utils";

export function StatCard({
  label,
  value,
  unit,
  icon: Icon,
  accent = "green"
}: {
  label: string;
  value: number | string;
  unit?: string;
  icon: LucideIcon;
  accent?: "green" | "blue" | "amber" | "red";
}) {
  const valueRef = useRef<HTMLSpanElement>(null);
  const accentStyle = {
    green: "border-agriGreen/20 bg-agriGreen/[0.07] text-agriGreen",
    blue: "border-signalBlue/20 bg-signalBlue/[0.07] text-signalBlue",
    amber: "border-warning/20 bg-warning/[0.07] text-warning",
    red: "border-danger/20 bg-danger/[0.07] text-danger"
  }[accent];

  useGSAP(() => {
    if (typeof value !== "number" || !valueRef.current) return;
    const state = { current: 0 };
    const tween = gsap.to(state, {
      current: value,
      duration: 0.8,
      ease: "power2.out",
      onUpdate: () => {
        if (valueRef.current) valueRef.current.textContent = formatNumber(state.current, 1);
      }
    });
    return () => tween.kill();
  }, { dependencies: [value] });

  return (
    <div className="glass-card group rounded-lg p-4 transition-colors hover:border-white/[0.14]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-xs text-slate-500">{label}</p>
          <div className="mt-3 flex items-baseline gap-1.5">
            <span ref={valueRef} className="text-2xl font-semibold tabular-nums text-white">{typeof value === "number" ? "0" : value}</span>
            {unit && <span className="text-[11px] text-slate-500">{unit}</span>}
          </div>
        </div>
        <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md border ${accentStyle}`}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2 text-[10px] text-slate-600">
        <span className={`h-1.5 w-1.5 rounded-full ${accent === "red" ? "bg-danger" : accent === "amber" ? "bg-warning" : accent === "blue" ? "bg-signalBlue" : "bg-agriGreen"}`} />
        实时数据
      </div>
    </div>
  );
}
