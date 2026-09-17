import { cn } from "@/lib/utils";

export function GlassCard({
  title,
  subtitle,
  action,
  className,
  accent = "cyan",
  children
}: {
  title?: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
  accent?: "green" | "cyan" | "blue" | "amber" | "red";
  children: React.ReactNode;
}) {
  const accentMap = {
    green: "bg-agriGreen",
    cyan: "bg-cyanGlow",
    blue: "bg-signalBlue",
    amber: "bg-warning",
    red: "bg-danger"
  };

  return (
    <section className={cn("glass-card rounded-lg p-4 sm:p-5", className)}>
      {(title || action) && (
        <div className="mb-4 flex min-h-10 items-start justify-between gap-4 border-b border-white/[0.06] pb-3">
          <div className="min-w-0">
            {title && (
              <div className="flex items-center gap-2.5">
                <span className={cn("h-3.5 w-0.5 rounded-full shadow-[0_0_10px_currentColor]", accentMap[accent])} />
                <h2 className="truncate text-sm font-semibold text-slate-100 sm:text-[15px]">{title}</h2>
              </div>
            )}
            {subtitle && <p className="mt-1.5 line-clamp-2 text-xs leading-5 text-slate-500">{subtitle}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
