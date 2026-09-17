"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { Filter, MapPinned } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHero } from "@/components/ui/PageHero";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { ErrorState, LoadingState } from "@/components/ui/State";
import { useApi } from "@/hooks/useApi";
import type { Farm } from "@/types/api";

const RiskMap = dynamic(() => import("@/components/map/RiskMap").then((m) => m.RiskMap), { ssr: false });

export default function MapPage() {
  const { data, loading, error } = useApi<{ items: Farm[]; filters: { towns: string[]; risk_levels: string[] } }>("/api/farms", []);
  const [town, setTown] = useState("");
  const [crop, setCrop] = useState("");
  const [risk, setRisk] = useState("");
  const [selected, setSelected] = useState<Farm | null>(null);

  const farms = useMemo(() => {
    const items = data?.items || [];
    return items.filter((farm) => (!town || farm.town === town) && (!crop || farm.crop === crop) && (!risk || farm.risk_level === risk));
  }, [data, town, crop, risk]);

  const crops = useMemo(() => Array.from(new Set((data?.items || []).map((f) => f.crop))), [data]);

  useEffect(() => {
    if (selected && !farms.some((farm) => farm.id === selected.id)) setSelected(null);
  }, [farms, selected]);

  return (
    <>
      {loading && <LoadingState label="正在加载县域地块和风险热力信息" />}
      {error && <ErrorState message={error} />}
      {!loading && !error && data && (
        <div className="space-y-5">
          <PageHero
            eyebrow="地块级风险空间监测"
            title="县域农田风险热力图"
            description="以地块 polygon 展示风险等级，叠加作物、乡镇、天气和模型因子，辅助农技人员确定巡检路线与资源投放优先级。"
            icon={MapPinned}
            stats={[
              { label: "当前地块", value: `${farms.length} 个`, tone: "green" },
              { label: "高风险", value: `${farms.filter((f) => f.risk_level === "高").length} 个`, tone: "red" },
              { label: "覆盖乡镇", value: `${new Set(farms.map((f) => f.town)).size} 个`, tone: "blue" }
            ]}
          />
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_390px]">
          <GlassCard
            title="风险热力地图"
            subtitle="多地块 polygon 风险上色，点击地块查看风险因子与巡检建议"
            action={<MapPinned className="h-5 w-5 text-cyanGlow" />}
            className="min-h-[600px]"
            accent="cyan"
          >
            <div className="mb-4 grid gap-3 md:grid-cols-4">
              <Select label="乡镇" value={town} onChange={setTown} options={data.filters.towns} />
              <Select label="作物" value={crop} onChange={setCrop} options={crops} />
              <Select label="风险等级" value={risk} onChange={setRisk} options={["高", "中", "低"]} />
              <div className="flex items-end">
                <button onClick={() => { setTown(""); setCrop(""); setRisk(""); }} className="ghost-action h-11 w-full text-sm">
                  <Filter className="h-4 w-4" />
                  重置筛选
                </button>
              </div>
              </div>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs text-cyan-100/52">
              <span>当前显示 {farms.length} / {data.items.length} 个地块</span>
              <span>{[town && `乡镇：${town}`, crop && `作物：${crop}`, risk && `等级：${risk}`].filter(Boolean).join(" · ") || "未设置筛选条件"}</span>
            </div>
            <div className="relative h-[500px] overflow-hidden rounded-lg border border-cyan-200/12 shadow-[0_0_44px_rgba(36,214,199,.08)] sm:h-[560px] xl:h-[620px]">
              <div className="pointer-events-none absolute left-4 top-4 z-[500] rounded-lg border border-cyan-200/16 bg-midnight/80 px-3 py-2 text-xs text-cyan-50/76 backdrop-blur-xl">
                风险颜色：<span className="text-red-200">高</span> / <span className="text-amber-200">中</span> / <span className="text-emerald-200">低</span>
              </div>
              <div className="pointer-events-none absolute bottom-4 left-4 z-[500] grid gap-2 rounded-lg border border-cyan-200/16 bg-midnight/80 p-3 text-xs text-cyan-50/72 backdrop-blur-xl sm:grid-cols-3">
                {["高", "中", "低"].map((level) => (
                  <div key={level} className="flex items-center gap-2">
                    <span className={`h-2.5 w-2.5 rounded-full ${level === "高" ? "bg-danger" : level === "中" ? "bg-warning" : "bg-agriGreen"}`} />
                    {level}风险 {farms.filter((f) => f.risk_level === level).length}
                  </div>
                ))}
              </div>
              <RiskMap farms={farms} onSelect={setSelected} />
            </div>
          </GlassCard>

          <div className="space-y-5">
            <GlassCard title="地块详情" subtitle="当前筛选结果与选中地块画像" accent="green">
              {!selected ? (
                <div className="rounded-lg border border-dashed border-cyan-200/18 bg-white/5 p-8 text-center text-sm text-cyan-100/62">请在地图中选择一个地块，系统会展示作物、天气、风险因子和建议巡检时间。</div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-lg font-semibold text-white">{selected.name}</h3>
                      <RiskBadge value={selected.risk_level} />
                    </div>
                    <p className="mt-1 text-sm text-cyan-100/58">{selected.town} · {selected.crop} · {selected.area_mu}亩</p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <Info label="风险等级" value={<RiskBadge value={selected.risk_level} />} />
                    <Info label="风险评分" value={selected.current_risk_score.toFixed(1)} />
                    <Info label="土壤类型" value={selected.soil_type} />
                    <Info label="灌溉条件" value={selected.irrigation_level} />
                    <Info label="近期天气" value={`${selected.recent_weather.weather_type} ${selected.recent_weather.temperature}℃`} />
                    <Info label="空气湿度" value={`${selected.recent_weather.humidity}%`} />
                  </div>
                  <div>
                    <div className="mb-2 text-sm text-cyan-100/62">主要风险因子</div>
                    <div className="space-y-2">
                      {selected.top_factors.map((factor) => (
                        <div key={factor.factor} className="rounded-lg border border-white/8 bg-white/5 p-3 text-sm">
                          <div className="flex justify-between text-cyan-50">
                            <span>{factor.factor}</span>
                            <span>{factor.contribution}</span>
                          </div>
                          <div className="mt-2 h-1.5 rounded-full bg-white/8">
                            <div className="h-1.5 rounded-full bg-gradient-to-r from-warning to-danger" style={{ width: `${Math.min(100, Number(factor.contribution) * 2)}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </GlassCard>
            <GlassCard title="风险分布" accent="red">
              <div className="grid grid-cols-3 gap-3">
                {["高", "中", "低"].map((level) => (
                  <div key={level} className="rounded-lg border border-white/8 bg-white/5 p-4 text-center">
                    <RiskBadge value={level} />
                    <div className="mt-3 text-2xl font-semibold text-white">{farms.filter((f) => f.risk_level === level).length}</div>
                    <div className="mt-1 text-xs text-cyan-100/50">个地块</div>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>
          </div>
        </div>
      )}
    </>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (value: string) => void; options: string[] }) {
  return (
    <label className="text-sm text-cyan-100/62">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} className="field-control mt-2">
        <option value="">全部</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-white/8 bg-white/5 p-3">
      <div className="text-xs text-cyan-100/45">{label}</div>
      <div className="mt-2 text-cyan-50">{value}</div>
    </div>
  );
}
