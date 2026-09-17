"use client";

import { useEffect, useState } from "react";
import { Activity, BrainCircuit, Gauge, Play, TrendingUp } from "lucide-react";
import { ForecastChart } from "@/components/charts/DashboardCharts";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHero } from "@/components/ui/PageHero";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { ErrorState, LoadingState } from "@/components/ui/State";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/hooks/useApi";
import type { Farm } from "@/types/api";

interface RiskResult {
  risk_score: number;
  risk_level: string;
  top_factors: { factor: string; contribution: number }[];
  model_version: string;
}

interface YieldResult {
  points: { date: string; predicted_yield: number; risk_score: number }[];
  metrics: Record<string, number>;
  top_factors: { factor: string; impact: string; contribution: number }[];
  suggestions: string[];
  model_version: string;
}

export default function PredictionsPage() {
  const farms = useApi<{ items: Farm[] }>("/api/farms", []);
  const metrics = useApi<{ items: Record<string, { metric_name: string; metric_value: number }[]> }>("/api/model/metrics", []);
  const [farmId, setFarmId] = useState<number | "">("");
  const [risk, setRisk] = useState<RiskResult | null>(null);
  const [yieldResult, setYieldResult] = useState<YieldResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!farmId && farms.data?.items?.length) setFarmId(farms.data.items[0].id);
  }, [farms.data, farmId]);

  useEffect(() => {
    if (farmId) run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [farmId]);

  async function run() {
    if (!farmId) return;
    setLoading(true);
    setError("");
    try {
      const body = JSON.stringify({ farm_id: farmId, days: 7 });
      const [riskRes, yieldRes] = await Promise.all([
        apiFetch<RiskResult>("/api/predictions/risk", { method: "POST", body }),
        apiFetch<YieldResult>("/api/predictions/yield", { method: "POST", body })
      ]);
      setRisk(riskRes);
      setYieldResult(yieldRes);
    } catch (err) {
      setError(err instanceof Error ? err.message : "预测失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {(farms.loading || metrics.loading) && <LoadingState label="正在加载地块、模型指标和预测服务" />}
      {(farms.error || metrics.error || error) && <ErrorState message={farms.error || metrics.error || error} />}
      {farms.data && metrics.data && (
        <div className="space-y-5">
          <PageHero
            eyebrow="AI 风险与产量预测"
            title="未来7天风险趋势与产量研判"
            description="模型融合天气、传感器、历史病虫害、地块特征和作物类型，输出风险等级、因子贡献、产量曲线和处置建议。"
            icon={TrendingUp}
            stats={[
              { label: "可选地块", value: `${farms.data.items.length} 个`, tone: "green" },
              { label: "风险模型", value: risk?.model_version || "待预测", tone: "amber" },
              { label: "产量模型", value: yieldResult?.model_version || "待预测", tone: "blue" }
            ]}
          />
          <GlassCard title="预测参数" subtitle="选择作物地块后，模型自动融合天气、传感器、历史病害和地块特征" accent="cyan">
            <div className="grid gap-3 md:grid-cols-[1fr_auto]">
              <select value={farmId} onChange={(e) => setFarmId(Number(e.target.value))} className="field-control">
                {farms.data.items.map((farm) => (
                  <option key={farm.id} value={farm.id}>
                    {farm.town} · {farm.name} · {farm.crop}
                  </option>
                ))}
              </select>
              <button onClick={run} disabled={loading} className="primary-action px-5 py-3 text-sm">
                <Play className="h-4 w-4" />
                {loading ? "预测中" : "重新预测"}
              </button>
            </div>
          </GlassCard>

          <div className="grid gap-5 xl:grid-cols-[.78fr_1.22fr]">
            <GlassCard title="风险评分模型" subtitle="RandomForest/XGBoost 可替换结构，输出风险等级和因子贡献" accent="red">
              {risk ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between rounded-lg border border-white/10 bg-gradient-to-br from-danger/12 to-white/5 p-5">
                    <div>
                      <div className="text-sm text-cyan-100/55">当前风险评分</div>
                      <div className="mt-2 text-4xl font-semibold text-white">{risk.risk_score}</div>
                    </div>
                    <RiskBadge value={risk.risk_level} className="text-sm" />
                  </div>
                  <div className="space-y-2">
                    {risk.top_factors.map((factor) => (
                      <div key={factor.factor} className="rounded-lg border border-white/8 bg-white/5 p-3">
                        <div className="flex justify-between text-sm">
                          <span className="text-cyan-50">{factor.factor}</span>
                          <span className="text-warning">{factor.contribution}</span>
                        </div>
                        <div className="mt-2 h-1.5 rounded-full bg-white/8">
                          <div className="h-1.5 rounded-full bg-gradient-to-r from-warning to-danger" style={{ width: `${Math.min(100, Number(factor.contribution) * 2)}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : <LoadingState label="等待预测结果" />}
            </GlassCard>

            <GlassCard title="未来7天产量与风险趋势" subtitle="单位：kg/亩；右轴为风险评分" accent="green">
              {yieldResult ? <ForecastChart data={yieldResult.points} /> : <LoadingState label="等待产量预测" />}
            </GlassCard>
          </div>

          <div className="grid gap-5 xl:grid-cols-3">
            <GlassCard title="模型误差指标" accent="blue">
              <div className="grid gap-3">
                {Object.entries(yieldResult?.metrics || {}).map(([name, value]) => (
                  <Metric key={name} icon={Gauge} label={name.toUpperCase()} value={value.toFixed(3)} />
                ))}
                {Object.entries(metrics.data.items.risk_model || {}).slice(0, 3).map(([idx, item]) => (
                  <Metric key={idx} icon={BrainCircuit} label={`Risk ${item.metric_name}`} value={item.metric_value.toFixed(3)} />
                ))}
              </div>
            </GlassCard>
            <GlassCard title="主要影响因素" accent="amber">
              <div className="space-y-3">
                {(yieldResult?.top_factors || []).map((factor) => (
                  <div key={factor.factor} className="rounded-lg border border-white/8 bg-white/5 p-3">
                    <div className="flex justify-between text-sm text-cyan-50">
                      <span>{factor.factor}</span>
                      <span>{factor.impact}</span>
                    </div>
                    <div className="mt-2 h-2 rounded bg-white/8">
                      <div className="h-2 rounded bg-gradient-to-r from-agriGreen to-signalBlue" style={{ width: `${factor.contribution}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>
            <GlassCard title="决策建议" accent="green">
              <div className="space-y-3">
                {(yieldResult?.suggestions || []).map((text) => (
                  <div key={text} className="flex gap-3 rounded-lg border border-emerald-200/10 bg-emerald-400/8 p-3 text-sm leading-6 text-cyan-50/82">
                    <Activity className="mt-1 h-4 w-4 shrink-0 text-agriGreen" />
                    {text}
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>
        </div>
      )}
    </>
  );
}

function Metric({ icon: Icon, label, value }: { icon: typeof Gauge; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-white/8 bg-white/5 p-3">
      <div className="flex items-center gap-2 text-sm text-cyan-100/66">
        <Icon className="h-4 w-4 text-cyanGlow" />
        {label}
      </div>
      <div className="font-semibold text-white">{value}</div>
    </div>
  );
}
