"use client";

import { useMemo, useState } from "react";
import { ClipboardPlus, Filter, RotateCcw, Search } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHero } from "@/components/ui/PageHero";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { ErrorState, LoadingState } from "@/components/ui/State";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import type { AlertItem } from "@/types/api";

export default function AlertsPage() {
  const [refresh, setRefresh] = useState(0);
  const alerts = useApi<{ items: AlertItem[] }>("/api/alerts", [refresh]);
  const [busy, setBusy] = useState<number | null>(null);
  const [actionError, setActionError] = useState("");
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [levelFilter, setLevelFilter] = useState("");

  const filteredAlerts = useMemo(() => {
    const items = alerts.data?.items || [];
    return items.filter((alert) => {
      const keyword = `${alert.title} ${alert.town} ${alert.farm_name} ${alert.owner} ${alert.trigger_reason}`.toLowerCase();
      return (!query || keyword.includes(query.toLowerCase())) && (!statusFilter || alert.status === statusFilter) && (!levelFilter || alert.risk_level === levelFilter);
    });
  }, [alerts.data, levelFilter, query, statusFilter]);

  async function patch(id: number, status: string) {
    setBusy(id);
    setActionError("");
    try {
      await apiFetch(`/api/alerts/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setRefresh((v) => v + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "预警状态更新失败");
    } finally {
      setBusy(null);
    }
  }

  async function createTask(id: number) {
    setBusy(id);
    setActionError("");
    try {
      await apiFetch(`/api/alerts/${id}/inspection-task`, { method: "POST" });
      setRefresh((v) => v + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "巡检任务生成失败");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      {alerts.loading && <LoadingState label="正在读取预警中心" />}
      {alerts.error && <ErrorState message={alerts.error} />}
      {alerts.data && (
        <div className="space-y-5">
          <PageHero
            eyebrow="风险预警调度"
            title="预警、负责人、处置状态统一闭环"
            description="对高风险地块触发原因、处置建议和负责人进行统一管理，支持状态切换与一键生成巡检任务。"
            icon={Filter}
            stats={[
              { label: "预警总数", value: `${alerts.data.items.length} 条`, tone: "amber" },
              { label: "高风险", value: `${alerts.data.items.filter((a) => a.risk_level === "高").length} 条`, tone: "red" },
              { label: "已完成", value: `${alerts.data.items.filter((a) => a.status === "已完成").length} 条`, tone: "green" }
            ]}
          />
        <GlassCard
          title="预警中心"
          subtitle="支持搜索、风险等级筛选、状态筛选、状态标签和任务生成"
          accent="red"
          action={<button onClick={() => setRefresh((v) => v + 1)} className="ghost-action p-2 text-cyan-50"><RotateCcw className="h-4 w-4" /></button>}
        >
          <div className="mb-4 grid gap-3 md:grid-cols-[1fr_180px_180px_auto]">
            <label className="relative">
              <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-cyan-100/45" />
              <input value={query} onChange={(e) => setQuery(e.target.value)} className="field-control pl-9" placeholder="搜索预警、地块、负责人或触发原因" />
            </label>
            <select value={levelFilter} onChange={(e) => setLevelFilter(e.target.value)} className="field-control">
              <option value="">全部等级</option>
              <option value="高">高风险</option>
              <option value="中">中风险</option>
              <option value="低">低风险</option>
            </select>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="field-control">
              <option value="">全部状态</option>
              <option value="待处理">待处理</option>
              <option value="处理中">处理中</option>
              <option value="已完成">已完成</option>
            </select>
            <button onClick={() => { setQuery(""); setLevelFilter(""); setStatusFilter(""); }} className="ghost-action px-4 text-sm">重置</button>
          </div>
          {actionError && <div className="mb-4 rounded-lg border border-danger/25 bg-danger/10 p-3 text-sm text-red-100">{actionError}</div>}
          <div className="overflow-x-auto">
            <table className="data-table min-w-[1080px]">
              <thead>
                <tr>
                  <th className="px-3 py-2">预警</th>
                  <th className="px-3 py-2">地块</th>
                  <th className="px-3 py-2">等级</th>
                  <th className="px-3 py-2">状态</th>
                  <th className="px-3 py-2">负责人</th>
                  <th className="px-3 py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredAlerts.map((alert) => (
                  <tr key={alert.id}>
                    <td>
                      <div className="font-medium text-white">{alert.title}</div>
                      <div className="mt-1 max-w-xl text-xs leading-5 text-cyan-100/52">{alert.trigger_reason}</div>
                    </td>
                    <td className="text-cyan-50/78">{alert.town}<br /><span className="text-xs text-cyan-100/48">{alert.farm_name}</span></td>
                    <td><RiskBadge value={alert.risk_level} /></td>
                    <td><RiskBadge value={alert.status} /></td>
                    <td className="text-cyan-50/78">{alert.owner}</td>
                    <td>
                      <div className="flex flex-wrap gap-2">
                        {["待处理", "处理中", "已完成"].map((status) => (
                          <button key={status} disabled={busy === alert.id || alert.status === status} onClick={() => patch(alert.id, status)} className="ghost-action px-2 py-1 text-xs disabled:cursor-default disabled:border-white/5 disabled:bg-white/[0.02] disabled:text-slate-600">
                            {status}
                          </button>
                        ))}
                        <button disabled={busy === alert.id} onClick={() => createTask(alert.id)} className="inline-flex items-center gap-1 rounded-lg border border-agriGreen/30 bg-agriGreen/12 px-2 py-1 text-xs text-emerald-50 hover:bg-agriGreen/18 disabled:opacity-60">
                          <ClipboardPlus className="h-3.5 w-3.5" />
                          生成巡检
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filteredAlerts.length === 0 && <div className="rounded-lg border border-dashed border-cyan-200/18 bg-white/5 p-8 text-center text-sm text-cyan-100/55">暂无匹配预警</div>}
          </div>
        </GlassCard>
        </div>
      )}
    </>
  );
}
