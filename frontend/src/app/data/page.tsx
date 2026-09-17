"use client";

import { useState } from "react";
import { Database, Download, FileUp, ServerCog } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHero } from "@/components/ui/PageHero";
import { ErrorState, LoadingState } from "@/components/ui/State";
import { API_BASE, apiFetch, getToken } from "@/lib/api";
import { useApi } from "@/hooks/useApi";

interface ExportSummary {
  summary: Record<string, number>;
  formats: string[];
  datasets: string[];
  note: string;
}

export default function DataPage() {
  const data = useApi<ExportSummary>("/api/data/export", []);
  const exportData = data.data;
  const [file, setFile] = useState<File | null>(null);
  const [importResult, setImportResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [dataset, setDataset] = useState("custom");
  const [error, setError] = useState("");

  async function upload() {
    if (!file) return;
    setLoading(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const result = await apiFetch(`/api/data/import?dataset=${encodeURIComponent(dataset)}`, { method: "POST", body: form });
      setImportResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入失败");
    } finally {
      setLoading(false);
    }
  }

  async function download(datasetName: string) {
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/data/export?dataset=${encodeURIComponent(datasetName)}&format=csv`, {
        headers: { Authorization: `Bearer ${getToken()}` }
      });
      if (!response.ok) throw new Error(await response.text() || "导出失败");
      const blob = await response.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `${datasetName}.csv`;
      link.click();
      URL.revokeObjectURL(link.href);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导出失败");
    }
  }

  return (
    <>
      {data.loading && <LoadingState label="正在读取数据资产目录" />}
      {data.error && <ErrorState message={data.error} />}
      {exportData && (
        <div className="space-y-5">
          <PageHero
            eyebrow="数据资产管理"
            title="农情数据导入、资产盘点与报告出口"
            description="统一管理农田、天气、传感器、病虫害和产量记录，支持 CSV 导入预览与报告导出，服务模型训练和业务复盘。"
            icon={ServerCog}
            stats={[
              { label: "数据表", value: "5 类核心", tone: "blue" },
              { label: "传感器", value: `${exportData.summary.sensor_records.toLocaleString("zh-CN")} 条`, tone: "green" },
              { label: "业务记录", value: `${(exportData.summary.pest_disease_reports + exportData.summary.yield_records).toLocaleString("zh-CN")} 条`, tone: "amber" }
            ]}
          />
          <div className="grid gap-4 md:grid-cols-5">
            {[
              ["农田数据", "farms"],
              ["天气数据", "weather_records"],
              ["传感器数据", "sensor_records"],
              ["病虫害记录", "pest_disease_reports"],
              ["产量记录", "yield_records"]
            ].map(([label, key]) => (
              <div key={key} className="glass-card rounded-lg p-5 transition hover:-translate-y-0.5">
                <Database className="mb-4 h-5 w-5 text-cyanGlow" />
                <div className="text-sm text-cyan-100/58">{label}</div>
                <div className="mt-2 text-3xl font-semibold text-white">{exportData.summary[key].toLocaleString("zh-CN")}</div>
              </div>
            ))}
          </div>

          <div className="grid gap-5 xl:grid-cols-[.85fr_1.15fr]">
            <GlassCard title="CSV导入" subtitle="先选择业务数据集，再校验字段、预览并写入对应业务表；自定义数据仅落盘预览" accent="cyan">
              <label className="mb-3 block text-sm text-cyan-100/62">
                导入目标
                <select value={dataset} onChange={(event) => setDataset(event.target.value)} className="field-control mt-2">
                  <option value="custom">自定义数据（仅预览）</option>
                  {(exportData.datasets || []).map((item) => <option key={item} value={item}>{item}</option>)}
                </select>
              </label>
              <label className="flex min-h-48 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-cyan-200/18 bg-white/5 text-center transition hover:border-cyanGlow/40 hover:bg-cyanGlow/8">
                <FileUp className="h-9 w-9 text-cyanGlow" />
                <div className="mt-3 text-sm text-cyan-50">{file ? file.name : "选择 CSV 文件"}</div>
                <input className="hidden" type="file" accept=".csv" onChange={(e) => setFile(e.target.files?.[0] || null)} />
              </label>
              <button onClick={upload} disabled={!file || loading} className="primary-action mt-4 w-full px-4 py-3 text-sm">
                <FileUp className="h-4 w-4" />
                {loading ? "导入中" : "导入并预览"}
              </button>
              {error && <div className="mt-4 rounded-lg border border-danger/25 bg-danger/10 p-3 text-sm text-red-100">{error}</div>}
              {importResult && <pre className="mt-4 max-h-72 overflow-auto rounded-lg border border-white/10 bg-midnight/70 p-3 text-xs text-cyan-50/78">{JSON.stringify(importResult, null, 2)}</pre>}
            </GlassCard>

            <GlassCard title="导出与数据说明" subtitle="面向竞赛演示的标准数据资产视图" accent="green">
              <div className="space-y-4">
                <div className="rounded-lg border border-white/8 bg-white/5 p-4">
                  <div className="flex items-center gap-2 text-white">
                    <Download className="h-4 w-4 text-cyanGlow" />
                    可导出格式
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {exportData.formats.map((format) => (
                      <span key={format} className="rounded border border-cyan-200/12 bg-cyan-300/8 px-3 py-1 text-sm text-cyan-50">
                        {format}
                      </span>
                    ))}
                  </div>
                </div>
                <p className="rounded-lg border border-emerald-200/12 bg-emerald-400/8 p-4 text-sm leading-7 text-cyan-50/76">{exportData.note}</p>
                <div className="grid gap-3 md:grid-cols-2">
                  {(exportData.datasets || []).slice(0, 4).map((item) => (
                    <button key={item} onClick={() => download(item)} className="rounded-lg border border-white/8 bg-white/5 p-4 text-left text-sm text-cyan-50/76 transition hover:border-cyanGlow/35 hover:bg-cyanGlow/8">导出 {item} CSV</button>
                  ))}
                </div>
              </div>
            </GlassCard>
          </div>
        </div>
      )}
    </>
  );
}
