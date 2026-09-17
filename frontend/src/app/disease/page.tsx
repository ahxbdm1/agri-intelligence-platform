"use client";

import { useEffect, useMemo, useState } from "react";
import { Camera, CheckCircle2, ImageUp, Microscope, RotateCcw, ScanSearch, ShieldAlert, X } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHero } from "@/components/ui/PageHero";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { apiFetch } from "@/lib/api";

interface DiseaseResult {
  disease_name: string;
  confidence: number;
  severity: string;
  suggestion: string;
  need_review: boolean;
  model_version: string;
  model_note: string;
  explainability: {
    method: string;
    lesion_region: { x: number; y: number; width: number; height: number };
    explanation: string;
    image_features: Record<string, number>;
  };
}

export default function DiseasePage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<DiseaseResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState(0);
  const preview = useMemo(() => (file ? URL.createObjectURL(file) : ""), [file]);

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  function chooseFile(nextFile: File | null | undefined) {
    if (!nextFile) return;
    if (!nextFile.type.startsWith("image/")) {
      setError("请选择 JPG、PNG 或 WEBP 图片文件");
      return;
    }
    if (nextFile.size > 8 * 1024 * 1024) {
      setError("图片大小不能超过 8MB，请压缩后再上传");
      return;
    }
    setFile(nextFile);
    setResult(null);
    setError("");
  }

  function clearFile() {
    setFile(null);
    setResult(null);
    setProgress(0);
    setError("");
  }

  async function submit() {
    setLoading(true);
    setProgress(8);
    setError("");
    const timer = window.setInterval(() => {
      setProgress((value) => Math.min(88, value + 12));
    }, 180);
    try {
      const form = new FormData();
      if (file) form.append("file", file);
      const data = await apiFetch<DiseaseResult>("/api/disease/predict", { method: "POST", body: form });
      setResult(data);
      setProgress(100);
    } catch (err) {
      setError(err instanceof Error ? err.message : "识别失败");
    } finally {
      window.clearInterval(timer);
      setLoading(false);
    }
  }

  return (
    <>
      <div className="space-y-5">
        <PageHero
          eyebrow="CV 病虫害识别"
          title="叶片图像智能识别与可解释诊断"
          description="上传作物叶片图片后，系统返回疑似病虫害、置信度、严重度、防治建议、人工复核建议和疑似病斑区域说明。"
          icon={Microscope}
          stats={[
            { label: "模型接口", value: "CNN兼容", tone: "blue" },
            { label: "复核机制", value: "人工闭环", tone: "amber" },
            { label: "解释输出", value: "区域定位", tone: "green" }
          ]}
        />
      <div className="grid gap-5 xl:grid-cols-[.9fr_1.1fr]">
        <GlassCard title="作物叶片图像识别" subtitle="支持点击或拖拽上传，返回病虫害名称、置信度、防治建议与可解释区域" accent="cyan">
          <div className="rounded-lg border border-dashed border-cyan-200/22 bg-white/5 p-5">
            <label
              onDragOver={(event) => {
                event.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragging(false);
                chooseFile(event.dataTransfer.files?.[0]);
              }}
              className={`flex min-h-80 cursor-pointer flex-col items-center justify-center rounded-lg border p-6 text-center transition ${dragging ? "border-cyanGlow/70 bg-cyanGlow/12 shadow-glow" : "border-white/10 bg-midnight/55 hover:bg-white/8"}`}
            >
              {preview ? (
                <div className="w-full">
                    <div className="relative mx-auto w-fit">
                      <img src={preview} alt={`${file?.name || "叶片图片"}预览`} className="mx-auto max-h-64 rounded-lg border border-white/10 object-contain shadow-card" />
                      <button type="button" onClick={(event) => { event.preventDefault(); event.stopPropagation(); clearFile(); }} aria-label="清除图片" title="清除图片" className="absolute -right-2 -top-2 rounded-full border border-white/15 bg-[#071317] p-1.5 text-slate-300 shadow-lg transition hover:border-danger/40 hover:bg-danger/15 hover:text-red-100">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </div>
                    <div className="mt-4 max-w-full truncate text-sm text-cyan-100/62">{file?.name}</div>
                </div>
              ) : (
                <>
                  <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-gradient-to-br from-agriGreen/18 to-signalBlue/18 shadow-glow">
                    <ImageUp className="h-9 w-9 text-cyanGlow" />
                  </div>
                  <div className="mt-4 font-medium text-white">选择叶片图片</div>
                  <div className="mt-2 text-sm text-cyan-100/55">支持 JPG、PNG、WEBP，单张不超过 8MB；也可不上传体验演示模式</div>
                </>
              )}
              <input type="file" accept="image/*" className="hidden" onChange={(e) => chooseFile(e.target.files?.[0])} />
            </label>
            {error && <div className="mt-4 rounded-lg border border-danger/25 bg-danger/10 p-3 text-sm text-red-100">{error}</div>}
            {loading && (
              <div className="mt-4 rounded-lg border border-cyan-200/12 bg-cyan-300/8 p-3">
                <div className="flex justify-between text-xs text-cyan-100/62">
                  <span>图像特征提取与模型推理</span>
                  <span>{progress}%</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/8">
                  <div className="h-full rounded-full bg-gradient-to-r from-agriGreen via-cyanGlow to-signalBlue transition-all" style={{ width: `${progress}%` }} />
                </div>
              </div>
            )}
            <div className="mt-5 flex gap-2">
            <button onClick={submit} disabled={loading} className="primary-action flex-1 px-4 py-3 text-sm">
              <ScanSearch className="h-4 w-4" />
              {loading ? "识别中" : "开始识别"}
            </button>
            {file && <button type="button" onClick={clearFile} disabled={loading} className="ghost-action px-3 text-xs" title="清除当前图片"><RotateCcw className="h-4 w-4" />清除</button>}
            </div>
          </div>
          <div className="mt-5 rounded-lg border border-cyan-200/10 bg-white/5 p-4 text-sm leading-7 text-cyan-100/66">
            当前接口为可替换模型结构，演示版使用轻量图像统计与 mock-CNN 兼容返回；接入真实 PyTorch 模型时保持 predict(image_bytes) 契约即可。
          </div>
        </GlassCard>

        <GlassCard title="识别结果与模型解释" subtitle="包含人工复核建议和疑似病斑区域说明" accent="green">
          {!result ? (
            <div className="flex min-h-96 flex-col items-center justify-center rounded-lg border border-dashed border-cyan-200/18 bg-white/5 text-cyan-100/58">
              <Camera className="mb-3 h-8 w-8 text-cyanGlow" />
              等待图像识别结果
            </div>
          ) : (
            <div className="space-y-5">
              <div className="grid gap-3 md:grid-cols-4">
                <Info label="疑似病虫害" value={result.disease_name} />
                <Info label="置信度" value={`${(result.confidence * 100).toFixed(1)}%`} />
                <Info label="严重度" value={<RiskBadge value={result.severity === "重" ? "高" : result.severity === "中" ? "中" : "低"} />} />
                <Info label="人工复核" value={result.need_review ? "需要" : "可抽查"} />
              </div>
              <div className="grid gap-4 lg:grid-cols-2">
                <div className="rounded-lg border border-emerald-200/12 bg-emerald-400/8 p-4">
                  <div className="flex items-center gap-2 text-sm text-emerald-100/72">
                    <CheckCircle2 className="h-4 w-4 text-agriGreen" />
                    防治建议
                  </div>
                  <p className="mt-2 leading-7 text-white">{result.suggestion}</p>
                </div>
                <div className="rounded-lg border border-warning/20 bg-warning/8 p-4">
                  <div className="flex items-center gap-2 text-sm text-amber-100/76">
                    <ShieldAlert className="h-4 w-4 text-warning" />
                    复核策略
                  </div>
                  <p className="mt-2 leading-7 text-cyan-50/82">
                    {result.need_review ? "建议农技员现场复核病斑扩展、虫口密度和田间湿度，并将复核结论回填系统。" : "置信度较高，可按抽样复核方式确认并记录处置效果。"}
                  </p>
                </div>
              </div>
              <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
                <div className="relative h-72 overflow-hidden rounded-lg border border-white/10 bg-gradient-to-br from-emerald-950 to-slate-900">
                  {preview ? <img src={preview} alt="explain" className="h-full w-full object-cover opacity-80" /> : <div className="h-full w-full bg-[radial-gradient(circle_at_40%_40%,rgba(32,213,135,.42),transparent_18%),radial-gradient(circle_at_60%_55%,rgba(255,202,85,.28),transparent_12%)]" />}
                  <div
                    className="absolute border-2 border-warning bg-warning/18 shadow-[0_0_32px_rgba(255,202,85,.38)]"
                    style={{
                      left: `${result.explainability.lesion_region.x * 100}%`,
                      top: `${result.explainability.lesion_region.y * 100}%`,
                      width: `${result.explainability.lesion_region.width * 100}%`,
                      height: `${result.explainability.lesion_region.height * 100}%`
                    }}
                  />
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 p-4">
                  <div className="text-sm text-cyan-100/58">{result.explainability.method}</div>
                  <p className="mt-3 leading-7 text-cyan-50/82">{result.explainability.explanation}</p>
                  <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    {Object.entries(result.explainability.image_features).map(([key, value]) => (
                      <div key={key} className="rounded-lg border border-white/8 bg-midnight/60 p-3">
                        <div className="text-cyan-100/45">{key}</div>
                        <div className="mt-1 text-white">{value}</div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 rounded-lg border border-white/8 bg-midnight/60 p-3 text-sm text-cyan-100/66">{result.model_note}</div>
                </div>
              </div>
            </div>
          )}
        </GlassCard>
      </div>
      </div>
    </>
  );
}

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-white/8 bg-white/5 p-4">
      <div className="text-xs text-cyan-100/45">{label}</div>
      <div className="mt-2 font-medium text-white">{value}</div>
    </div>
  );
}
