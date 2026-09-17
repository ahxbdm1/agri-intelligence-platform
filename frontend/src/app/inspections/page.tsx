"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, ClipboardList, Clock3, RotateCcw, Search } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHero } from "@/components/ui/PageHero";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { ErrorState, LoadingState } from "@/components/ui/State";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import type { InspectionTask } from "@/types/api";

export default function InspectionsPage() {
  const [refresh, setRefresh] = useState(0);
  const tasks = useApi<{ items: InspectionTask[] }>("/api/inspection-tasks", [refresh]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [actionError, setActionError] = useState("");

  const filteredTasks = useMemo(() => {
    const items = tasks.data?.items || [];
    return items.filter((task) => {
      const keyword = `${task.title} ${task.town} ${task.farm_name} ${task.crop} ${task.assignee} ${task.description}`.toLowerCase();
      return (!query || keyword.includes(query.toLowerCase())) && (!statusFilter || task.status === statusFilter) && (!priorityFilter || task.priority === priorityFilter);
    });
  }, [priorityFilter, query, statusFilter, tasks.data]);

  async function patch(id: number, status: string) {
    setActionError("");
    try {
      await apiFetch(`/api/inspection-tasks/${id}`, { method: "PATCH", body: JSON.stringify({ status }) });
      setRefresh((v) => v + 1);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "任务状态更新失败");
    }
  }

  return (
    <>
      {tasks.loading && <LoadingState label="正在同步巡检任务" />}
      {tasks.error && <ErrorState message={tasks.error} />}
      {tasks.data && (
        <div className="space-y-5">
          <PageHero
            eyebrow="巡检任务协同"
            title="按风险优先级组织现场复核"
            description="由预警和模型结果驱动巡检任务，管理负责人、截止时间、处理状态和现场记录，形成风险治理回访闭环。"
            icon={ClipboardList}
            stats={[
              { label: "任务总数", value: `${tasks.data.items.length} 个`, tone: "blue" },
              { label: "高优先级", value: `${tasks.data.items.filter((t) => t.priority === "高").length} 个`, tone: "red" },
              { label: "已完成", value: `${tasks.data.items.filter((t) => t.status === "已完成").length} 个`, tone: "green" }
            ]}
          />
          <div className="grid gap-4 md:grid-cols-3">
            <SummaryCard label="待处理" value={tasks.data.items.filter((t) => t.status === "待处理").length} icon={Clock3} />
            <SummaryCard label="处理中" value={tasks.data.items.filter((t) => t.status === "处理中").length} icon={RotateCcw} />
            <SummaryCard label="已完成" value={tasks.data.items.filter((t) => t.status === "已完成").length} icon={CheckCircle2} />
          </div>
          <GlassCard title="巡检任务管理" subtitle="支持搜索、优先级筛选、状态筛选和状态标签" accent="green">
          <div className="mb-4 grid gap-3 md:grid-cols-[1fr_180px_180px_auto]">
              <label className="relative">
                <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-cyan-100/45" />
                <input value={query} onChange={(e) => setQuery(e.target.value)} className="field-control pl-9" placeholder="搜索任务、地块、负责人或描述" />
              </label>
              <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} className="field-control">
                <option value="">全部优先级</option>
                <option value="高">高优先级</option>
                <option value="中">中优先级</option>
                <option value="低">低优先级</option>
              </select>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="field-control">
                <option value="">全部状态</option>
                <option value="待处理">待处理</option>
                <option value="处理中">处理中</option>
                <option value="已完成">已完成</option>
              </select>
              <button onClick={() => { setQuery(""); setPriorityFilter(""); setStatusFilter(""); }} className="ghost-action px-4 text-sm">重置</button>
          </div>
          {actionError && <div className="mb-4 rounded-lg border border-danger/25 bg-danger/10 p-3 text-sm text-red-100">{actionError}</div>}
            <div className="grid gap-3 xl:grid-cols-2">
              {filteredTasks.slice(0, 80).map((task) => (
                <div key={task.id} className="rounded-lg border border-white/8 bg-white/5 p-4 transition hover:-translate-y-0.5 hover:border-cyan-200/18 hover:bg-white/8">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-medium text-white">{task.title}</div>
                      <div className="mt-1 text-xs text-cyan-100/52">{task.town} · {task.farm_name} · {task.crop}</div>
                    </div>
                    <div className="flex gap-2">
                      <RiskBadge value={`${task.priority}优先级`} />
                      <RiskBadge value={task.status} />
                    </div>
                  </div>
                  <p className="mt-3 line-clamp-2 text-sm leading-6 text-cyan-50/68">{task.description}</p>
                  <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm text-cyan-100/58">
                    <span>负责人：{task.assignee}</span>
                    <span>截止：{task.due_date}</span>
                  </div>
                  <div className="mt-4 flex gap-2">
                    {["待处理", "处理中", "已完成"].map((status) => (
                      <button key={status} disabled={task.status === status} onClick={() => patch(task.id, status)} className="ghost-action px-3 py-1.5 text-xs disabled:cursor-default disabled:border-white/5 disabled:bg-white/[0.02] disabled:text-slate-600">
                        {status}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            {filteredTasks.length === 0 && <div className="rounded-lg border border-dashed border-cyan-200/18 bg-white/5 p-8 text-center text-sm text-cyan-100/55">暂无匹配巡检任务</div>}
          </GlassCard>
        </div>
      )}
    </>
  );
}

function SummaryCard({ label, value, icon: Icon }: { label: string; value: number; icon: typeof Clock3 }) {
  return (
    <div className="glass-card flex items-center justify-between rounded-lg p-5 transition hover:-translate-y-0.5">
      <div>
        <div className="text-sm text-cyan-100/58">{label}</div>
        <div className="mt-2 text-3xl font-semibold text-white">{value}</div>
      </div>
      <Icon className="h-7 w-7 text-cyanGlow" />
    </div>
  );
}
