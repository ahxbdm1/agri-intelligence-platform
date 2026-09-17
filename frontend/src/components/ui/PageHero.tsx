import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function PageHero({
  eyebrow,
  title,
  description,
  icon: Icon,
  stats,
  className
}: {
  eyebrow: string;
  title: string;
  description: string;
  icon?: LucideIcon;
  stats?: { label: string; value: string; tone?: "green" | "blue" | "amber" | "red" }[];
  className?: string;
}) {
  const tones = {
    green: "border-agriGreen/20 bg-agriGreen/[0.055]",
    blue: "border-signalBlue/20 bg-signalBlue/[0.055]",
    amber: "border-warning/20 bg-warning/[0.055]",
    red: "border-danger/20 bg-danger/[0.055]"
  };

  return (
    <section className={cn("relative border-b border-white/[0.07] pb-5", className)}>
      <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-agriGreen/35 via-cyanGlow/20 to-transparent" />
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="max-w-3xl">
          <div className="flex items-center gap-2 text-[11px] font-semibold text-agriGreen">
            {Icon && <Icon className="h-3.5 w-3.5" />}
            {eyebrow}
            <span className="ml-1 inline-flex items-center gap-1 rounded border border-cyanGlow/15 bg-cyanGlow/[0.045] px-1.5 py-0.5 text-[9px] font-medium text-cyan-100/65">
              <span className="h-1.5 w-1.5 rounded-full bg-cyanGlow shadow-[0_0_8px_rgba(71,215,221,.65)]" />
              县域业务
            </span>
          </div>
          <h2 className="mt-2 text-xl font-semibold leading-tight text-white sm:text-2xl">{title}</h2>
          <p className="mt-2 max-w-3xl text-xs leading-6 text-slate-400 sm:text-sm">{description}</p>
        </div>
        {stats && (
          <div className="grid min-w-0 grid-cols-3 gap-2 xl:min-w-[430px]">
            {stats.map((stat) => (
              <div key={stat.label} className={cn("min-w-0 rounded-md border px-3 py-2.5", tones[stat.tone || "green"])}>
                <div className="truncate text-[9px] text-slate-500 sm:text-[10px]">{stat.label}</div>
                <div className="mt-1 truncate text-sm font-semibold tabular-nums text-slate-100 sm:text-base">{stat.value}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
