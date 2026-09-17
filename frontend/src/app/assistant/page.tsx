"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Bot, Cloud, DatabaseZap, FileSearch, HardDrive, LoaderCircle, Send, Sparkles, Trash2, TriangleAlert } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { PageHero } from "@/components/ui/PageHero";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { apiFetch } from "@/lib/api";
import { useApi } from "@/hooks/useApi";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: { source: string; title: string; score: number }[];
  mode?: "ragflow" | "local";
  provider?: string;
  warning?: string | null;
  latency_ms?: number;
}

interface RAGStatus {
  configured: boolean;
  available: boolean;
  mode: "ragflow" | "local";
  provider: string;
  message: string;
  dataset_count: number;
  chat_configured: boolean;
}

const examples = ["番茄早疫病怎么防治？", "未来三天高湿天气会增加什么风险？", "哪些地块应该优先巡检？"];

export default function AssistantPage() {
  const [question, setQuestion] = useState(examples[0]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const messageListRef = useRef<HTMLDivElement>(null);
  const ragStatus = useApi<RAGStatus>("/api/assistant/status", []);
  const ranking = useApi<{ ranking: { town: string; risk_score: number }[]; latest_alerts: { title: string; town: string; farm_name: string; risk_level: string; status: string }[] }>("/api/dashboard/risk-ranking", []);

  useEffect(() => {
    const list = messageListRef.current;
    if (!list) return;
    list.scrollTo({ top: list.scrollHeight, behavior: "smooth" });
  }, [loading, messages]);

  async function ask(text = question) {
    const prompt = text.trim();
    if (!prompt || loading) return;
    setLoading(true);
    setError("");
    setQuestion("");
    setMessages((items) => [...items, { role: "user", content: prompt }]);
    try {
      const data = await apiFetch<{ answer: string; citations: Message["citations"]; mode: Message["mode"]; provider: string; warning?: string | null; latency_ms: number }>("/api/assistant/chat", {
        method: "POST",
        body: JSON.stringify({ question: prompt })
      });
      setMessages((items) => [...items, {
        role: "assistant",
        content: data.answer,
        citations: data.citations,
        mode: data.mode,
        provider: data.provider,
        warning: data.warning,
        latency_ms: data.latency_ms
      }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "问答请求失败");
      setQuestion(prompt);
    } finally {
      setLoading(false);
    }
  }

  function clearConversation() {
    if (loading) return;
    setMessages([]);
    setError("");
    setQuestion(examples[0]);
  }

  return (
    <>
      <div className="space-y-5">
        <PageHero
          eyebrow="RAG 智能农技问答"
          title="知识库检索 + 当前风险数据引用"
          description="助手优先调用 RAGFlow 农业知识库，并结合系统高风险地块、预警和天气上下文；远程不可用时自动切换本地知识库。"
          icon={Bot}
          stats={[
            { label: "知识来源", value: ragStatus.data?.available ? "RAGFlow" : "本地RAG", tone: "green" },
            { label: "系统上下文", value: "实时风险", tone: "blue" },
            { label: "回答引用", value: "可追溯", tone: "amber" }
          ]}
        />
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <GlassCard
          title="AI农技助手"
          subtitle={ragStatus.data?.message || "正在检查 RAGFlow 远程知识库"}
          accent="cyan"
            action={(
              <div className="flex items-center gap-2">
                <div className={`inline-flex items-center gap-1.5 rounded border px-2 py-1 text-[10px] ${ragStatus.data?.available ? "border-agriGreen/25 bg-agriGreen/10 text-emerald-200" : "border-warning/25 bg-warning/10 text-amber-200"}`}>
                  {ragStatus.data?.available ? <Cloud className="h-3 w-3" /> : <HardDrive className="h-3 w-3" />}
                  {ragStatus.loading ? "检测中" : ragStatus.data?.available ? "远程在线" : "本地降级"}
                </div>
                <button type="button" onClick={clearConversation} disabled={!messages.length || loading} aria-label="清空对话" title="清空对话" className="rounded border border-white/10 p-1.5 text-slate-500 transition hover:border-cyanGlow/25 hover:bg-white/5 hover:text-cyan-50 disabled:cursor-not-allowed disabled:opacity-35">
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          className="min-w-0"
        >
          <div className="flex h-[clamp(32rem,calc(100dvh-16rem),46rem)] min-h-0 flex-col overflow-hidden rounded-lg border border-white/10 bg-midnight/55">
            <div ref={messageListRef} data-message-scroll aria-live="polite" className="min-h-0 flex-1 space-y-4 overflow-y-auto overscroll-contain p-4 [scrollbar-gutter:stable]">
              {messages.length === 0 && (
                <div className="flex h-full flex-col items-center justify-center text-center text-cyan-100/58">
                  <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-lg bg-gradient-to-br from-agriGreen/18 to-signalBlue/18 shadow-glow">
                    <Bot className="h-10 w-10 text-cyanGlow" />
                  </div>
                  <div className="font-medium text-white">专业农技问答工作台</div>
                  <div className="mt-2 max-w-md text-sm leading-7">请选择示例问题或输入农业技术问题，答案会显示知识库引用、风险数据依据和建议操作。</div>
                </div>
              )}
              {messages.map((msg, idx) => (
                <div key={idx} className={`max-w-[92%] rounded-lg border p-4 shadow-card ${msg.role === "user" ? "ml-auto border-signalBlue/25 bg-signalBlue/14" : "border-emerald-200/12 bg-white/6"}`}>
                  <div className="mb-2 flex items-center gap-2 text-xs text-cyan-100/54">
                    {msg.role === "user" ? <Sparkles className="h-3.5 w-3.5 text-signalBlue" /> : <Bot className="h-3.5 w-3.5 text-agriGreen" />}
                    {msg.role === "user" ? "用户提问" : "农智云瞰助手"}
                    {msg.role === "assistant" && msg.provider && (
                      <span className="ml-auto inline-flex items-center gap-1 rounded border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] text-slate-400">
                        {msg.mode === "ragflow" ? <Cloud className="h-3 w-3 text-agriGreen" /> : <HardDrive className="h-3 w-3 text-warning" />}
                        {msg.provider} · {msg.latency_ms ? `${(msg.latency_ms / 1000).toFixed(1)}s` : ""}
                      </span>
                    )}
                  </div>
                  <div className="whitespace-pre-wrap text-sm leading-7 text-cyan-50/88">{msg.content || "知识库暂未返回可展示内容，请稍后重试或换一种问法。"}</div>
                  {msg.warning && (
                    <div className="mt-3 flex items-start gap-2 rounded-md border border-warning/20 bg-warning/[0.07] p-2.5 text-xs leading-5 text-amber-100/75">
                      <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warning" />
                      {msg.warning}
                    </div>
                  )}
                  {msg.citations && (
                    <div className="mt-4 rounded-lg border border-cyan-200/10 bg-cyan-300/6 p-3">
                      <div className="mb-2 flex items-center gap-2 text-xs text-cyan-100/56">
                        <FileSearch className="h-3.5 w-3.5 text-cyanGlow" />
                        引用来源
                      </div>
                      <div className="flex flex-wrap gap-2">
                      {msg.citations.map((cite) => (
                        <span key={`${cite.source}-${cite.title}`} title={cite.title} className="max-w-full rounded border border-cyan-200/12 bg-cyan-300/8 px-2 py-1 text-xs text-cyan-100/70">
                          <span className="block max-w-[16rem] truncate">{cite.title || cite.source}</span>
                          <span className="text-[10px] text-cyan-100/42">{cite.source} · {(cite.score * 100).toFixed(1)}%相关</span>
                        </span>
                      ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="max-w-[92%] rounded-lg border border-emerald-200/12 bg-white/6 p-4 shadow-card" role="status" aria-live="polite">
                  <div className="mb-2 flex items-center gap-2 text-xs text-cyan-100/54">
                    <Bot className="h-3.5 w-3.5 text-agriGreen" />
                    农智云瞰助手
                  </div>
                  <div className="flex items-center gap-3 text-sm text-cyan-50/78">
                    <LoaderCircle className="h-4 w-4 animate-spin text-cyanGlow" />
                    正在检索农业知识库并融合当前风险数据，请稍候...
                  </div>
                </div>
              )}
            </div>
            <div className="shrink-0 border-t border-white/10 bg-[#071317]/96 p-3 backdrop-blur-xl">
              {error && <div className="mb-3 rounded-lg border border-danger/25 bg-danger/10 p-3 text-sm text-red-100">{error}</div>}
              <div className="mb-2 flex items-center justify-between gap-3">
                <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">快速提问</span>
                <span className="hidden text-[10px] text-slate-600 sm:inline">Enter 发送 · 回答自动滚动</span>
              </div>
              <div className="mb-3 flex flex-wrap gap-2">
                {examples.map((item) => (
                  <button key={item} onClick={() => ask(item)} disabled={loading} className="ghost-action px-3 py-1.5 text-xs disabled:cursor-not-allowed disabled:opacity-45">
                    {item}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <input
                  aria-label="输入农技问题"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.nativeEvent.isComposing) ask();
                  }}
                  disabled={loading}
                  className="field-control min-w-0 flex-1 disabled:cursor-wait disabled:opacity-60"
                  placeholder="输入农技问题"
                />
                <button type="button" onClick={() => ask()} disabled={loading || !question.trim()} className="primary-action px-4 text-sm">
                  <Send className="h-4 w-4" />
                  {loading ? "检索中" : "发送"}
                </button>
              </div>
            </div>
          </div>
        </GlassCard>

        <div className="space-y-5 xl:max-h-[calc(100dvh-10rem)] xl:overflow-y-auto xl:pr-1">
        <GlassCard title="系统风险数据引用" subtitle="助手回答会结合这些实时系统上下文" accent="red">
          <div className="space-y-3">
            {(ranking.data?.latest_alerts || []).slice(0, 4).map((alert) => (
              <div key={`${alert.title}-${alert.farm_name}`} className="rounded-lg border border-white/8 bg-white/5 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium text-white">{alert.title}</div>
                    <div className="mt-1 text-xs text-cyan-100/52">{alert.town} · {alert.farm_name}</div>
                  </div>
                  <RiskBadge value={alert.risk_level} />
                </div>
              </div>
            ))}
            {!ranking.data?.latest_alerts?.length && <div className="rounded-lg border border-dashed border-cyan-200/18 bg-white/5 p-6 text-center text-sm text-cyan-100/55">暂无风险引用数据</div>}
          </div>
        </GlassCard>
        <GlassCard title="建议操作" accent="green">
          <div className="space-y-3 text-sm leading-7 text-cyan-100/68">
            {[
              ["生成高风险地块巡检任务", "/inspections"],
              ["打开地图核查风险集中区", "/map"],
              ["导出日报提交农技站", "/reports"],
              ["将人工复核结果回填模型", "/disease"]
            ].map(([item, href]) => (
              <Link key={item} href={href} className="group flex items-center gap-3 rounded-lg border border-white/8 bg-white/5 p-3 text-sm text-cyan-100/78 transition hover:border-cyanGlow/25 hover:bg-cyanGlow/7 hover:text-white">
                <DatabaseZap className="h-4 w-4 text-cyanGlow" />
                {item}
                <ArrowUpRight className="ml-auto h-3.5 w-3.5 text-slate-600 transition group-hover:text-cyanGlow" />
              </Link>
            ))}
          </div>
        </GlassCard>
        <GlassCard title="知识库引用规则" accent="blue">
          <div className="space-y-3 text-sm leading-7 text-cyan-100/68">
            <p>助手优先调用 RAGFlow 远程知识库，回答会展示远程文档引用和相似度。</p>
            <p>系统会注入当前高风险地块、最新天气提示等业务上下文，因此不是普通聊天框。</p>
            <p>远程连接失败时系统自动切换本地 TF-IDF，并在回答中明确显示降级原因。</p>
          </div>
        </GlassCard>
        </div>
      </div>
      </div>
    </>
  );
}
