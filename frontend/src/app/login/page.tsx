"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { ArrowRight, Check, Lock, ScanLine, ShieldCheck, Sprout, UserRound } from "lucide-react";
import { API_BASE, setAuth } from "@/lib/api";

const accounts = [
  { role: "县域管理员", username: "admin", password: "admin123", desc: "全县风险治理与资源调度" },
  { role: "农技专家", username: "expert", password: "expert123", desc: "病害复核与模型研判" },
  { role: "合作社用户", username: "coop", password: "coop123", desc: "地块上报与任务反馈" }
];

const capabilities = ["病虫害智能识别", "地块风险预测", "巡检闭环调度", "农情日报生成"];

export default function LoginPage() {
  const pageRef = useRef<HTMLElement>(null);
  const router = useRouter();
  const [selected, setSelected] = useState(accounts[0]);
  const [username, setUsername] = useState(accounts[0].username);
  const [password, setPassword] = useState(accounts[0].password);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useGSAP(() => {
    const mm = gsap.matchMedia();
    mm.add("(prefers-reduced-motion: no-preference)", () => {
      gsap.fromTo("[data-login-reveal]", { autoAlpha: 0, y: 18 }, { autoAlpha: 1, y: 0, duration: 0.62, stagger: 0.08, ease: "power3.out" });
      gsap.fromTo("[data-signal-line]", { scaleX: 0, transformOrigin: "left center" }, { scaleX: 1, duration: 1.1, stagger: 0.08, ease: "power2.out", delay: 0.25 });
    });
    return () => mm.revert();
  }, { scope: pageRef });

  function choose(account: (typeof accounts)[number]) {
    setSelected(account);
    setUsername(account.username);
    setPassword(account.password);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const response = await fetch(`${API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role: selected.role })
      });
      if (!response.ok) throw new Error("登录失败，请确认后端服务和演示数据已就绪");
      const data = await response.json();
      setAuth(data.access_token, data.user);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main ref={pageRef} className="app-background relative min-h-screen overflow-hidden bg-[#04090b] px-4 py-5 text-white sm:px-6 lg:px-10">
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(87,182,156,.035)_1px,transparent_1px),linear-gradient(90deg,rgba(87,182,156,.035)_1px,transparent_1px)] bg-[size:56px_56px]" />
      <div className="relative mx-auto flex min-h-[calc(100vh-40px)] max-w-[1440px] flex-col">
        <header data-login-reveal className="flex h-14 items-center justify-between border-b border-white/[0.07]">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-md border border-emerald-200/20 bg-emerald-400/10 text-agriGreen">
              <Sprout className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-semibold">农智云瞰</div>
              <div className="text-[10px] text-slate-500">AGRI INTELLIGENCE COMMAND</div>
            </div>
          </div>
          <div className="hidden items-center gap-2 text-[11px] text-emerald-100/55 sm:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-agriGreen shadow-[0_0_10px_rgba(66,217,154,.8)]" />
            县域农情数据链路已连接
          </div>
        </header>

        <div className="grid flex-1 items-center gap-8 py-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,.62fr)] lg:gap-16">
          <section className="max-w-3xl">
            <div data-login-reveal className="inline-flex items-center gap-2 border-l-2 border-agriGreen pl-3 text-xs font-semibold text-agriGreen">
              大数据与人工智能行业应用开发
            </div>
            <h1 data-login-reveal className="mt-5 max-w-3xl text-3xl font-semibold leading-[1.25] text-white sm:text-5xl lg:text-[3.35rem]">
              看清每一块农田风险，<br className="hidden sm:block" />
              让决策先于损失发生
            </h1>
            <p data-login-reveal className="mt-5 max-w-2xl text-sm leading-7 text-slate-400 sm:text-base">
              面向县域农业主管部门的病虫害识别、产量风险预测与农情决策平台。汇聚地块、气象、传感器与巡检数据，形成从研判到处置的完整闭环。
            </p>

            <div data-login-reveal className="mt-8 grid max-w-2xl gap-x-8 gap-y-4 sm:grid-cols-2">
              {capabilities.map((item) => (
                <div key={item} className="flex items-center gap-3 text-sm text-slate-300">
                  <span className="flex h-5 w-5 items-center justify-center rounded border border-emerald-300/20 bg-emerald-400/[0.07] text-agriGreen"><Check className="h-3 w-3" /></span>
                  {item}
                </div>
              ))}
            </div>

            <div data-login-reveal className="mt-10 grid max-w-2xl grid-cols-3 border-y border-white/[0.07] py-5">
              {[["80", "监测地块"], ["5,200+", "传感器记录"], ["7天", "前瞻风险预测"]].map(([value, label], index) => (
                <div key={label} className={index ? "border-l border-white/[0.07] pl-5 sm:pl-8" : ""}>
                  <div className="text-xl font-semibold tabular-nums text-white sm:text-2xl">{value}</div>
                  <div className="mt-1 text-[10px] text-slate-500 sm:text-xs">{label}</div>
                  <div data-signal-line className="mt-3 h-px w-10 bg-gradient-to-r from-agriGreen to-transparent" />
                </div>
              ))}
            </div>
          </section>

          <form data-login-reveal onSubmit={submit} className="glass-card rounded-lg p-5 sm:p-6">
            <div className="flex items-start justify-between border-b border-white/[0.07] pb-4">
              <div>
                <h2 className="text-lg font-semibold">进入指挥中心</h2>
                <p className="mt-1 text-xs text-slate-500">选择演示身份，账号将自动填充</p>
              </div>
              <div className="flex h-9 w-9 items-center justify-center rounded-md border border-cyan-200/15 bg-cyan-400/[0.07] text-cyanGlow">
                <ShieldCheck className="h-5 w-5" />
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2">
              {accounts.map((account) => (
                <button
                  type="button"
                  key={account.role}
                  onClick={() => choose(account)}
                  className={`min-h-16 rounded-md border px-2 py-2 text-left transition ${selected.role === account.role ? "border-agriGreen/35 bg-agriGreen/[0.09] text-white" : "border-white/[0.07] bg-white/[0.025] text-slate-400 hover:bg-white/[0.045]"}`}
                >
                  <div className="text-xs font-medium">{account.role}</div>
                  <div className="mt-1 hidden text-[9px] leading-4 text-slate-500 sm:block">{account.desc}</div>
                </button>
              ))}
            </div>

            <label className="mt-5 block text-xs text-slate-400">账号</label>
            <div className="mt-2 flex items-center gap-2 rounded-md border border-white/[0.08] bg-black/20 px-3 focus-within:border-cyanGlow/40">
              <UserRound className="h-4 w-4 text-slate-500" />
              <input value={username} onChange={(e) => setUsername(e.target.value)} className="h-11 w-full bg-transparent text-sm outline-none" autoComplete="username" />
            </div>
            <label className="mt-4 block text-xs text-slate-400">密码</label>
            <div className="mt-2 flex items-center gap-2 rounded-md border border-white/[0.08] bg-black/20 px-3 focus-within:border-cyanGlow/40">
              <Lock className="h-4 w-4 text-slate-500" />
              <input value={password} type="password" onChange={(e) => setPassword(e.target.value)} className="h-11 w-full bg-transparent text-sm outline-none" autoComplete="current-password" />
            </div>
            {error && <div className="mt-4 rounded-md border border-danger/25 bg-danger/[0.08] p-3 text-xs text-red-200">{error}</div>}
            <button disabled={loading} className="primary-action mt-5 w-full px-4 text-sm">
              {loading ? "正在验证身份" : "进入平台"}
              {loading ? <ScanLine className="h-4 w-4 animate-pulse" /> : <ArrowRight className="h-4 w-4" />}
            </button>
            <p className="mt-4 text-center text-[10px] text-slate-600">演示环境 · 固定模拟数据 · 不存储个人敏感信息</p>
          </form>
        </div>
      </div>
    </main>
  );
}
