"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useMemo, useState } from "react";
import { AlertTriangle, ArrowUpRight, BarChart3, CheckCircle2, CloudSun, Crosshair, Droplets, FileText, Gauge, Leaf, LocateFixed, MapPinned, RadioTower, ScanLine, ShieldAlert } from "lucide-react";
import { Workflow } from "lucide-react";
import { CropPieChart, RiskTrendChart, TownRankingChart } from "@/components/charts/DashboardCharts";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHero } from "@/components/ui/PageHero";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { ErrorState, LoadingState } from "@/components/ui/State";
import { StatCard } from "@/components/ui/StatCard";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import type { Farm } from "@/types/api";

const RiskMap = dynamic(() => import("@/components/map/RiskMap").then((m) => m.RiskMap), { ssr: false });

interface Summary {
  total_area_mu: number;
  farm_count: number;
  high_risk_farms: number;
  today_new_reports: number;
  report_data_date: string | null;
  predicted_loss_rate: number;
  ai_accuracy: number;
  alert_process_rate: number;
}

interface Trends {
  risk_trend: { date: string; risk: number }[];
  crop_structure: { name: string; value: number }[];
  data_as_of: string;
}

interface Ranking {
  ranking: { town: string; risk_score: number; farm_count: number }[];
  latest_alerts: { id: number; title: string; town: string; farm_name: string; risk_level: string; status: string }[];
  risk_level_counts: Record<string, number>;
}

interface DispatchResult {
  queue_count: number;
  generated_task_count: number;
  existing_task_count: number;
  material_plan: { material: string; quantity: number; unit: string; reason: string }[];
  priority_queue: { farm_name: string; town: string; crop: string; risk_score: number; priority: string; weather_hint: string }[];
  next_actions: string[];
}

export default function DashboardPage() {
  const summary = useApi<Summary>("/api/dashboard/summary", []);
  const trends = useApi<Trends>("/api/dashboard/trends", []);
  const ranking = useApi<Ranking>("/api/dashboard/risk-ranking", []);
  const farms = useApi<{ items: Farm[] }>("/api/farms", []);
  const loading = summary.loading || trends.loading || ranking.loading || farms.loading;
  const error = summary.error || trends.error || ranking.error || farms.error;
  const [dispatch, setDispatch] = useState<DispatchResult | null>(null);
  const [dispatchLoading, setDispatchLoading] = useState(false);
  const [dispatchError, setDispatchError] = useState("");
  const [selectedFarm, setSelectedFarm] = useState<Farm | null>(null);

  const weatherSnapshot = useMemo(() => {
    const items = farms.data?.items || [];
    if (!items.length) return null;
    const temperature = items.reduce((total, farm) => total + Number(farm.recent_weather.temperature ?? 0), 0) / items.length;
    const humidity = items.reduce((total, farm) => total + Number(farm.recent_weather.humidity ?? 0), 0) / items.length;
    const rainfall = items.reduce((total, farm) => total + Number(farm.recent_weather.rainfall ?? 0), 0) / items.length;
    const weatherType = items[0].recent_weather.weather_type || "多云";
    return { temperature, humidity, rainfall, weatherType };
  }, [farms.data]);

  const priorityFarms = useMemo(() => [...(farms.data?.items || [])].sort((a, b) => b.current_risk_score - a.current_risk_score).slice(0, 3), [farms.data]);

  async function runDispatch() {
    setDispatchLoading(true);
    setDispatchError("");
    try {
      const result = await apiFetch<DispatchResult>("/api/workflows/daily-dispatch", {
        method: "POST",
        body: JSON.stringify({ max_tasks: 12 })
      });
      setDispatch(result);
    } catch (err) {
      setDispatchError(err instanceof Error ? err.message : "调度工作流执行失败");
    } finally {
      setDispatchLoading(false);
    }
  }

  return (
    <>
      {loading && <LoadingState label="正在汇聚农情、气象、模型预测和预警数据" />}
      {error && <ErrorState message={error} />}
      {!loading && !error && summary.data && trends.data && ranking.data && farms.data && (
        <div className="space-y-5">
          <PageHero
            eyebrow="县域智慧农业指挥中心"
            title="农情风险态势一屏统览"
            description="实时汇聚地块、作物、天气、传感器、病虫害上报、模型预测和预警处置数据，辅助县域农业主管部门进行病虫害防控、减产风险管理和农资调度。"
            icon={RadioTower}
            stats={[
              { label: "监测地块", value: `${summary.data.farm_count} 个`, tone: "green" },
              { label: "高风险占比", value: `${((summary.data.high_risk_farms / Math.max(summary.data.farm_count, 1)) * 100).toFixed(1)}%`, tone: "red" },
              { label: "预警处理率", value: `${summary.data.alert_process_rate}%`, tone: "blue" }
            ]}
          />
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <DashboardAction href="/map" icon={MapPinned} title="查看风险地块" description="按乡镇和风险等级筛选" tone="cyan" />
            <DashboardAction href="/disease" icon={Leaf} title="识别叶片病害" description="上传图片进行 AI 研判" tone="green" />
            <DashboardAction href="/inspections" icon={ScanLine} title="安排巡检任务" description="查看优先级和截止时间" tone="amber" />
            <DashboardAction href="/reports" icon={FileText} title="生成农情日报" description="归档今日指标与建议" tone="blue" />
          </div>
          <div className="grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 xl:grid-cols-6">
            <StatCard label="全县种植面积" value={summary.data.total_area_mu} unit="亩" icon={MapPinned} accent="green" />
            <StatCard label="高风险地块" value={summary.data.high_risk_farms} unit="个" icon={AlertTriangle} accent="red" />
            <StatCard label="最新日新增上报" value={summary.data.today_new_reports} unit="条" icon={ScanLine} accent="amber" />
            <StatCard label="预测减产风险" value={summary.data.predicted_loss_rate} unit="%" icon={Gauge} accent="blue" />
            <StatCard label="AI识别准确率" value={summary.data.ai_accuracy} unit="%" icon={Crosshair} accent="green" />
            <StatCard label="预警处理率" value={summary.data.alert_process_rate} unit="%" icon={CheckCircle2} accent="blue" />
          </div>
          <div className="grid items-stretch gap-5 xl:grid-cols-[1.25fr_.75fr]">
            <GlassCard title="县域风险空间概览" subtitle="点击地块查看风险评分，进入地图页执行筛选和巡检安排" accent="cyan" action={<Link href="/map" className="ghost-action px-3 py-1.5 text-xs">进入地图 <ArrowUpRight className="h-3.5 w-3.5" /></Link>}>
              <div className="relative h-[300px] overflow-hidden rounded-lg border border-cyan-200/12 bg-[#081416] shadow-[0_0_44px_rgba(36,214,199,.08)] sm:h-[340px]">
                <div className="pointer-events-none absolute left-3 top-3 z-[500] flex items-center gap-2 rounded-md border border-cyan-200/16 bg-midnight/80 px-2.5 py-1.5 text-[11px] text-cyan-50/76 backdrop-blur-xl">
                  <LocateFixed className="h-3.5 w-3.5 text-cyanGlow" />
                  {selectedFarm ? `${selectedFarm.town} · ${selectedFarm.name}` : "点击地块查看详情"}
                </div>
                <div className="pointer-events-none absolute bottom-3 right-3 z-[500] flex gap-3 rounded-md border border-cyan-200/16 bg-midnight/80 px-2.5 py-1.5 text-[10px] text-cyan-50/72 backdrop-blur-xl">
                  <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-danger" />高风险</span>
                  <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-warning" />中风险</span>
                  <span><i className="mr-1 inline-block h-2 w-2 rounded-full bg-agriGreen" />低风险</span>
                </div>
                <RiskMap farms={farms.data.items} onSelect={setSelectedFarm} />
              </div>
            </GlassCard>
            <SituationPanel weather={weatherSnapshot} selectedFarm={selectedFarm} priorityFarms={priorityFarms} onSelect={setSelectedFarm} />
          </div>
          <GlassCard
            title="今日农情调度工作流"
            subtitle="将风险评分、天气因子、高风险地块、巡检任务和农资建议串联为一次可执行操作"
            accent="blue"
            action={(
              <button onClick={runDispatch} disabled={dispatchLoading} className="primary-action px-3 py-2 text-xs">
                <Workflow className="h-3.5 w-3.5" />
                {dispatchLoading ? "正在编排" : "执行今日调度"}
              </button>
            )}
          >
            {dispatchError && <div className="mb-3 rounded-lg border border-danger/25 bg-danger/10 p-3 text-xs text-red-100">{dispatchError}</div>}
            {!dispatch ? (
              <div className="flex min-h-20 items-center gap-3 rounded-lg border border-dashed border-cyan-200/16 bg-white/5 px-4 text-sm text-cyan-100/58">
                <Workflow className="h-5 w-5 text-cyanGlow" />
                点击执行后，系统将为高风险地块生成去重后的巡检任务，并给出农资调度建议。
              </div>
            ) : (
              <div className="grid gap-3 lg:grid-cols-[.75fr_1.25fr]">
                <div className="grid grid-cols-3 gap-2">
                  <WorkflowMetric label="进入队列" value={`${dispatch.queue_count} 个`} />
                  <WorkflowMetric label="新建任务" value={`${dispatch.generated_task_count} 个`} />
                  <WorkflowMetric label="已存在任务" value={`${dispatch.existing_task_count} 个`} />
                  <div className="col-span-3 rounded-lg border border-amber-200/12 bg-amber-400/6 p-3">
                    <div className="text-xs text-amber-100/58">农资调度建议</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {dispatch.material_plan.length ? dispatch.material_plan.map((item) => (
                        <span key={item.material} className="rounded border border-amber-200/15 bg-amber-400/8 px-2 py-1 text-xs text-amber-50/82">{item.material} · {item.quantity}{item.unit}</span>
                      )) : <span className="text-xs text-cyan-100/55">暂无额外农资需求</span>}
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  {dispatch.priority_queue.slice(0, 3).map((item) => (
                    <div key={item.farm_name} className="flex items-center justify-between gap-3 rounded-lg border border-white/8 bg-white/5 px-3 py-2.5">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-white">{item.farm_name}</div>
                        <div className="mt-1 truncate text-xs text-cyan-100/52">{item.town} · {item.crop} · {item.weather_hint}</div>
                      </div>
                      <div className="shrink-0 text-right"><div className="text-sm font-semibold text-amber-100">{item.risk_score}</div><div className="text-[10px] text-cyan-100/45">风险评分</div></div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </GlassCard>
          <div className="-mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-cyan-100/48">
            <span>病虫害上报数据截至：{summary.data.report_data_date || "暂无"}</span>
            <span>风险趋势数据截至：{trends.data.data_as_of || "暂无"}</span>
            <span>指标由业务数据库实时聚合</span>
          </div>

          <div className="grid items-start gap-5 xl:grid-cols-[1.35fr_.65fr]">
            <GlassCard title="未来风险趋势" subtitle="基于地块风险预测按日聚合，单位：评分 0-100" accent="cyan">
              <RiskTrendChart data={trends.data.risk_trend} />
            </GlassCard>
            <GlassCard title="作物结构" subtitle="按监测面积统计，单位：亩" accent="green">
              <CropPieChart data={trends.data.crop_structure} />
              <div className="grid grid-cols-3 gap-2">
                {trends.data.crop_structure.map((item) => (
                  <div key={item.name} className="rounded-md border border-white/8 bg-white/5 px-2 py-1.5 text-xs text-cyan-50/76 transition hover:bg-white/8">
                    <div className="truncate font-medium text-white">{item.name}</div>
                    <div className="mt-0.5 truncate text-[10px] text-cyan-100/52">{item.value.toFixed(0)} 亩</div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>

          <div className="grid items-start gap-5 xl:grid-cols-[.9fr_1.1fr]">
            <GlassCard title="乡镇风险排名" subtitle="按当前地块风险评分平均值排序" accent="amber">
              <TownRankingChart data={ranking.data.ranking} />
            </GlassCard>
            <GlassCard title="最新预警列表" subtitle="按预警生成时间倒序展示" accent="red">
              <div className="space-y-3">
                {ranking.data.latest_alerts.length === 0 ? (
                  <div className="rounded-lg border border-dashed border-cyan-200/18 bg-white/5 p-8 text-center text-sm text-cyan-100/55">暂无最新预警</div>
                ) : ranking.data.latest_alerts.map((alert) => (
                  <div key={alert.id} className="grid gap-3 rounded-lg border border-white/8 bg-white/5 p-3 transition hover:-translate-y-0.5 hover:border-cyan-200/18 hover:bg-white/8 md:grid-cols-[1fr_auto_auto] md:items-center">
                    <div className="flex gap-3">
                      <div className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-danger/12 text-danger">
                        <ShieldAlert className="h-4 w-4" />
                      </div>
                      <div>
                        <div className="font-medium text-white">{alert.title}</div>
                        <div className="mt-1 text-xs text-cyan-100/55">{alert.town} · {alert.farm_name}</div>
                      </div>
                    </div>
                    <RiskBadge value={alert.risk_level} />
                    <RiskBadge value={alert.status} />
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>

          <GlassCard title="县域治理闭环" subtitle="数据采集、模型研判、预警处置、巡检回访、报告归档" accent="blue">
            <div className="grid gap-3 md:grid-cols-5">
              {[
                ["多源采集", "天气、传感器、上报、产量"],
                ["AI识别", "叶片图像病害判别"],
                ["风险预测", "地块评分与产量趋势"],
                ["调度处置", "预警生成巡检任务"],
                ["报告归档", "日报输出与模型回填"]
              ].map(([title, text]) => (
                <div key={title} className="rounded-lg border border-cyan-200/10 bg-gradient-to-br from-white/8 to-white/3 p-4 transition hover:-translate-y-0.5 hover:border-cyanGlow/24">
                  <BarChart3 className="mb-3 h-5 w-5 text-cyanGlow" />
                  <div className="font-medium text-white">{title}</div>
                  <div className="mt-1 text-sm text-cyan-100/58">{text}</div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}
    </>
  );
}

function WorkflowMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-white/8 bg-white/5 p-3"><div className="text-[11px] text-cyan-100/48">{label}</div><div className="mt-1 text-lg font-semibold text-white">{value}</div></div>;
}

function SituationPanel({ weather, selectedFarm, priorityFarms, onSelect }: { weather: { temperature: number; humidity: number; rainfall: number; weatherType: string } | null; selectedFarm: Farm | null; priorityFarms: Farm[]; onSelect: (farm: Farm) => void }) {
  const focus = selectedFarm || priorityFarms[0];
  return (
    <GlassCard title="当前农情摘要" subtitle="天气环境与优先关注对象" accent="green">
      {!weather ? <div className="flex min-h-[300px] items-center justify-center text-sm text-cyan-100/55">暂无天气数据</div> : (
        <div className="space-y-4">
          <div className="rounded-lg border border-cyanGlow/12 bg-cyanGlow/[0.045] p-4">
            <div className="flex items-center justify-between gap-3">
              <div><div className="text-xs text-cyan-100/52">监测区域平均天气</div><div className="mt-1 text-lg font-semibold text-white">{weather.weatherType}</div></div>
              <CloudSun className="h-7 w-7 text-cyanGlow" />
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2">
              <WeatherMetric label="温度" value={`${weather.temperature.toFixed(1)}℃`} />
              <WeatherMetric label="湿度" value={`${weather.humidity.toFixed(0)}%`} icon={<Droplets className="h-3 w-3" />} />
              <WeatherMetric label="降雨" value={`${weather.rainfall.toFixed(1)}mm`} />
            </div>
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between text-xs text-cyan-100/55"><span>优先关注地块</span><Link href="/inspections" className="text-cyanGlow hover:text-white">查看任务</Link></div>
            <div className="space-y-2">
              {priorityFarms.map((farm) => (
                <button key={farm.id} type="button" onClick={() => onSelect(farm)} className="flex w-full items-center justify-between gap-3 rounded-lg border border-white/8 bg-white/5 p-3 text-left transition hover:border-cyanGlow/25 hover:bg-white/8">
                  <span className="min-w-0"><span className="block truncate text-sm font-medium text-white">{farm.name}</span><span className="mt-1 block truncate text-[11px] text-cyan-100/50">{farm.town} · {farm.crop}</span></span>
                  <span className="shrink-0 text-right"><RiskBadge value={farm.risk_level} /><span className="mt-1 block text-[10px] text-cyan-100/45">{farm.current_risk_score.toFixed(1)}分</span></span>
                </button>
              ))}
              {!priorityFarms.length && <div className="rounded-lg border border-dashed border-cyan-200/18 p-5 text-center text-sm text-cyan-100/55">暂无优先关注地块</div>}
            </div>
          </div>
          {focus && <div className="border-t border-white/8 pt-3 text-xs text-cyan-100/52">当前建议：优先核查 <span className="font-medium text-white">{focus.town} · {focus.name}</span> 的叶片病斑和田间湿度。</div>}
        </div>
      )}
    </GlassCard>
  );
}

function WeatherMetric({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return <div className="rounded-md border border-white/8 bg-black/15 p-2"><div className="flex items-center gap-1 text-[10px] text-cyan-100/45">{icon}{label}</div><div className="mt-1 text-sm font-semibold tabular-nums text-white">{value}</div></div>;
}

function DashboardAction({ href, icon: Icon, title, description, tone }: { href: string; icon: typeof MapPinned; title: string; description: string; tone: "green" | "cyan" | "amber" | "blue" }) {
  const styles = {
    green: "border-agriGreen/15 bg-agriGreen/[0.045] hover:border-agriGreen/35",
    cyan: "border-cyanGlow/15 bg-cyanGlow/[0.045] hover:border-cyanGlow/35",
    amber: "border-warning/15 bg-warning/[0.045] hover:border-warning/35",
    blue: "border-signalBlue/15 bg-signalBlue/[0.045] hover:border-signalBlue/35"
  }[tone];
  return (
    <Link href={href} className={`group flex min-w-0 items-center gap-3 rounded-lg border px-3 py-3 transition hover:-translate-y-0.5 hover:bg-white/[0.06] ${styles}`}>
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-white/10 bg-black/15 text-cyanGlow"><Icon className="h-4 w-4" /></span>
      <span className="min-w-0">
        <span className="flex items-center gap-1 text-sm font-medium text-white">{title}<ArrowUpRight className="h-3 w-3 text-slate-600 transition group-hover:text-cyanGlow" /></span>
        <span className="mt-0.5 block truncate text-[11px] text-cyan-100/50">{description}</span>
      </span>
    </Link>
  );
}
