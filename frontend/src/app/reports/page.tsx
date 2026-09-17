"use client";

import { useState } from "react";
import { Code2, FileText, Globe2, NotebookText, WandSparkles } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHero } from "@/components/ui/PageHero";
import { apiFetch } from "@/lib/api";

interface ReportResult {
  report_id: string;
  title: string;
  markdown: string;
  html: string;
  paths: { markdown: string; html: string };
}

export default function ReportsPage() {
  const [town, setTown] = useState("");
  const [report, setReport] = useState<ReportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [previewMode, setPreviewMode] = useState<"markdown" | "html">("markdown");
  const towns = ["", "东湖镇", "青禾镇", "云溪镇", "稻香镇", "南川镇", "北岭镇"];

  async function generate() {
    setLoading(true);
    setError("");
    try {
      const data = await apiFetch<ReportResult>("/api/reports/daily", { method: "POST", body: JSON.stringify({ town: town || null }) });
      setReport(data);
      setPreviewMode("markdown");
    } catch (err) {
      setError(err instanceof Error ? err.message : "报告生成失败");
    } finally {
      setLoading(false);
    }
  }

  function download(content: string, filename: string, type: string) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <div className="space-y-5">
        <PageHero
          eyebrow="自动报告生成"
          title="县域农情风险日报一键归档"
          description="将 KPI、风险地块、预警、模型预测和处置建议自动生成 Markdown/HTML 报告，适合日报归档、竞赛答辩和视频演示。"
          icon={NotebookText}
          stats={[
            { label: "输出格式", value: "MD / HTML", tone: "green" },
            { label: "报告范围", value: town || "全县", tone: "blue" },
            { label: "生成状态", value: loading ? "生成中" : report ? "已生成" : "待生成", tone: "amber" }
          ]}
        />
      <div className="grid gap-5 xl:grid-cols-[380px_1fr]">
        <GlassCard title="县域农情风险日报" subtitle="一键生成包含 KPI、风险地块、模型预测和处置建议的 Markdown/HTML 报告" accent="green">
          <label className="text-sm text-cyan-100/62">
            报告范围
            <select value={town} onChange={(e) => setTown(e.target.value)} className="field-control mt-2">
              {towns.map((item) => (
                <option key={item || "county"} value={item}>
                  {item || "全县"}
                </option>
              ))}
            </select>
          </label>
          <button onClick={generate} disabled={loading} className="primary-action mt-5 w-full px-4 py-3 text-sm">
            <WandSparkles className="h-4 w-4" />
            {loading ? "生成中" : "生成日报"}
          </button>
          {error && <div className="mt-4 rounded-lg border border-danger/25 bg-danger/10 p-3 text-sm text-red-100">{error}</div>}
          {report && (
            <div className="mt-5 space-y-3 rounded-lg border border-white/10 bg-white/5 p-4 text-sm text-cyan-100/68">
              <div className="flex items-center gap-2 font-medium text-white">
                <FileText className="h-4 w-4 text-cyanGlow" />
                {report.title}
              </div>
              <div>报告ID：{report.report_id}</div>
              <div className="break-all">Markdown：{report.paths.markdown}</div>
              <div className="break-all">HTML：{report.paths.html}</div>
              <div className="flex flex-wrap gap-2 pt-2">
                <button onClick={() => download(report.markdown, `${report.report_id}.md`, "text/markdown;charset=utf-8")} className="ghost-action px-3 py-1.5 text-xs">下载 Markdown</button>
                <button onClick={() => download(report.html, `${report.report_id}.html`, "text/html;charset=utf-8")} className="ghost-action px-3 py-1.5 text-xs">下载 HTML</button>
              </div>
            </div>
          )}
          <div className="mt-5 grid gap-3 text-sm">
            {["KPI 指标摘要", "风险地块清单", "模型预测研判", "处置建议归档"].map((item) => (
              <div key={item} className="rounded-lg border border-white/8 bg-white/5 p-3 text-cyan-50/72">{item}</div>
            ))}
          </div>
        </GlassCard>

        <GlassCard title="报告预览" subtitle="可作为日报、答辩材料和演示视频素材" accent="blue">
          {!report ? (
            <div className="flex min-h-[500px] flex-col items-center justify-center rounded-lg border border-dashed border-cyan-200/18 bg-white/5 text-cyan-100/58">
              <FileText className="mb-3 h-10 w-10 text-cyanGlow" />
              点击左侧按钮生成报告
            </div>
          ) : (
            <div>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <div className="text-xs text-cyan-100/52">{previewMode === "markdown" ? "Markdown 原文预览" : "HTML 页面预览"}</div>
                <div className="flex rounded-md border border-white/10 bg-white/5 p-1">
                  <button type="button" onClick={() => setPreviewMode("markdown")} className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs transition ${previewMode === "markdown" ? "bg-cyanGlow/12 text-cyan-50" : "text-slate-500 hover:text-slate-200"}`}><Code2 className="h-3.5 w-3.5" />Markdown</button>
                  <button type="button" onClick={() => setPreviewMode("html")} className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1.5 text-xs transition ${previewMode === "html" ? "bg-agriGreen/12 text-emerald-50" : "text-slate-500 hover:text-slate-200"}`}><Globe2 className="h-3.5 w-3.5" />HTML</button>
                </div>
              </div>
              {previewMode === "markdown" ? (
                <div className="max-h-[720px] overflow-auto rounded-lg border border-white/10 bg-[#f8fffb] p-6 text-[#13382f] shadow-card">
                  <pre className="whitespace-pre-wrap font-sans text-sm leading-7">{report.markdown}</pre>
                </div>
              ) : (
                <iframe title="农情日报 HTML 预览" sandbox="" srcDoc={report.html} className="h-[720px] w-full rounded-lg border border-white/10 bg-white" />
              )}
            </div>
          )}
        </GlassCard>
      </div>
      </div>
    </>
  );
}
