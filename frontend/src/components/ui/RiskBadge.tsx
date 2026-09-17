import { cn } from "@/lib/utils";

const styles: Record<string, string> = {
  高: "border-danger/55 bg-danger/16 text-red-100 shadow-[0_0_22px_rgba(255,107,107,.16)]",
  中: "border-warning/55 bg-warning/16 text-amber-100 shadow-[0_0_22px_rgba(255,202,85,.14)]",
  低: "border-agriGreen/45 bg-agriGreen/12 text-emerald-100 shadow-[0_0_22px_rgba(32,213,135,.12)]",
  待处理: "border-warning/50 bg-warning/12 text-amber-100",
  处理中: "border-signalBlue/45 bg-signalBlue/12 text-blue-100",
  已完成: "border-agriGreen/45 bg-agriGreen/12 text-emerald-100",
  高优先级: "border-danger/55 bg-danger/16 text-red-100",
  中优先级: "border-warning/55 bg-warning/16 text-amber-100",
  低优先级: "border-agriGreen/45 bg-agriGreen/12 text-emerald-100"
};

export function RiskBadge({ value, className }: { value: string; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-semibold", styles[value] || "border-white/15 bg-white/8 text-slate-100", className)}>
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-80" />
      {value}
    </span>
  );
}
