import { AlertTriangle, Loader2, RotateCcw } from "lucide-react";

export function LoadingState({ label = "数据加载中" }: { label?: string }) {
  return (
    <div className="glass-card flex min-h-40 items-center justify-center rounded-lg p-6 text-sm text-cyan-100/70" role="status" aria-live="polite">
      <div className="text-center">
        <Loader2 className="mx-auto h-6 w-6 animate-spin text-cyanGlow" />
        <div className="mt-3">{label}</div>
        <div className="mx-auto mt-4 h-1 w-52 overflow-hidden rounded-full bg-white/8">
          <div className="h-full w-1/2 animate-pulse rounded-full bg-gradient-to-r from-agriGreen to-signalBlue" />
        </div>
      </div>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex min-h-40 items-center justify-center rounded-lg border border-danger/25 bg-danger/8 p-4 text-sm text-red-100 shadow-[0_0_30px_rgba(255,107,107,.12)]">
      <div className="flex max-w-xl flex-col items-center gap-3 text-center">
        <div className="flex h-9 w-9 items-center justify-center rounded-md border border-danger/30 bg-danger/12">
          <AlertTriangle className="h-4 w-4" />
        </div>
        <p role="alert">{message}</p>
        {onRetry && (
          <button type="button" onClick={onRetry} className="ghost-action px-3 py-2 text-xs">
            <RotateCcw className="h-3.5 w-3.5" />
            重新加载
          </button>
        )}
      </div>
    </div>
  );
}
