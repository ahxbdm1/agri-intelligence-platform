"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Bell,
  Bot,
  ChevronRight,
  ClipboardList,
  Database,
  FileText,
  LayoutDashboard,
  Leaf,
  LineChart,
  LogOut,
  Map,
  Menu,
  RadioTower,
  Search,
  ShieldCheck,
  Sprout,
  X
} from "lucide-react";
import { clearAuth, getToken } from "@/lib/api";
import { cn } from "@/lib/utils";

const navItems = [
  { group: "指挥中心", href: "/dashboard", label: "农情驾驶舱", icon: LayoutDashboard },
  { group: "指挥中心", href: "/map", label: "地图风险监测", icon: Map },
  { group: "指挥中心", href: "/alerts", label: "预警中心", icon: Bell },
  { group: "AI 研判", href: "/disease", label: "病虫害识别", icon: Leaf },
  { group: "AI 研判", href: "/predictions", label: "产量与风险预测", icon: LineChart },
  { group: "AI 研判", href: "/assistant", label: "AI 农技助手", icon: Bot },
  { group: "业务协同", href: "/inspections", label: "巡检任务", icon: ClipboardList },
  { group: "业务协同", href: "/data", label: "数据管理", icon: Database },
  { group: "业务协同", href: "/reports", label: "报告生成", icon: FileText }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [user, setUser] = useState<{ display_name?: string; role?: string } | null>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    const raw = localStorage.getItem("agri_user");
    if (raw) {
      try {
        setUser(JSON.parse(raw));
      } catch {
        localStorage.removeItem("agri_user");
      }
    }
  }, [router]);

  useEffect(() => setMobileOpen(false), [pathname]);

  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMobileOpen(false);
      }
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  const activeItem = useMemo(() => navItems.find((item) => pathname.startsWith(item.href)), [pathname]);

  function logout() {
    clearAuth();
    router.replace("/login");
  }

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center gap-3 border-b border-white/[0.06] px-5">
        <div className="relative flex h-9 w-9 items-center justify-center rounded-md border border-emerald-200/20 bg-emerald-400/10 text-agriGreen">
          <Sprout className="h-5 w-5" />
          <span className="absolute -right-1 -top-1 h-2 w-2 rounded-full border-2 border-[#081416] bg-agriGreen" />
        </div>
        <div className="min-w-0">
          <div className="font-semibold text-white">农智云瞰</div>
          <div className="truncate text-[10px] text-emerald-100/45">县域智慧农业指挥中心</div>
        </div>
      </div>

      <div className="mx-4 mt-4 grid grid-cols-2 gap-2 rounded-md border border-white/[0.06] bg-white/[0.025] p-2 text-[11px]">
        <div className="flex items-center gap-1.5 text-emerald-100/65"><ShieldCheck className="h-3.5 w-3.5 text-agriGreen" />风控在线</div>
        <div className="flex items-center gap-1.5 text-cyan-100/65"><RadioTower className="h-3.5 w-3.5 text-cyanGlow" />数据接入</div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {navItems.map((item, index) => {
          const Icon = item.icon;
          const active = pathname.startsWith(item.href);
          return (
            <div key={item.href}>
              {item.group !== navItems[index - 1]?.group && <div className="px-3 pb-1 pt-4 text-[10px] font-semibold tracking-[0.14em] text-slate-600 first:pt-2">{item.group}</div>}
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "group relative flex h-10 items-center justify-between rounded-md px-3 text-sm text-slate-400 transition-colors hover:bg-white/[0.045] hover:text-slate-100",
                  active && "bg-emerald-400/[0.09] text-white"
                )}
              >
                {active && <span className="absolute inset-y-2 left-0 w-0.5 rounded-r bg-agriGreen shadow-[0_0_12px_rgba(66,217,154,.8)]" />}
                <span className="flex items-center gap-3">
                  <Icon className={cn("h-4 w-4", active ? "text-agriGreen" : "text-slate-500 group-hover:text-cyanGlow")} />
                  {item.label}
                </span>
                <ChevronRight className={cn("h-3.5 w-3.5 opacity-0 transition-opacity group-hover:opacity-50", active && "opacity-50")} />
              </Link>
            </div>
          );
        })}
      </nav>

      <div className="border-t border-white/[0.06] p-4">
        <div className="flex items-center gap-3 rounded-md bg-white/[0.025] p-2.5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-cyan-400/10 text-xs font-semibold text-cyanGlow">
            {(user?.display_name || "演示").slice(0, 1)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-medium text-slate-200">{user?.display_name || "演示用户"}</div>
            <div className="truncate text-[10px] text-slate-500">{user?.role || "县域管理员"}</div>
          </div>
          <button onClick={logout} title="退出登录" className="rounded p-1.5 text-slate-500 transition hover:bg-white/5 hover:text-white">
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="app-background min-h-screen text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-white/[0.065] bg-[#071113]/95 backdrop-blur-xl lg:block">
        {sidebar}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button aria-label="关闭导航" className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-[min(19rem,86vw)] border-r border-white/10 bg-[#071113] shadow-2xl">
            <button onClick={() => setMobileOpen(false)} aria-label="关闭导航" className="absolute right-3 top-4 z-10 rounded-md p-2 text-slate-400 hover:bg-white/5 hover:text-white">
              <X className="h-4 w-4" />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <div className="min-h-screen min-w-0 lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center border-b border-white/[0.065] bg-[#060e10]/88 px-4 backdrop-blur-xl sm:px-6 lg:px-7">
          <button onClick={() => setMobileOpen(true)} aria-label="打开导航" className="mr-3 rounded-md border border-white/10 p-2 text-slate-300 lg:hidden">
            <Menu className="h-4 w-4" />
          </button>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-[10px] text-slate-500">
              <span>云澜县农业农村局</span><span>/</span><span>智慧农业平台</span>
            </div>
            <h1 className="truncate text-sm font-semibold text-white sm:text-base">{activeItem?.label || "农智云瞰"}</h1>
          </div>
          <QuickNav />
          <div className="ml-3 flex items-center gap-2">
            <div className="hidden items-center gap-2 rounded-md border border-emerald-300/10 bg-emerald-400/[0.055] px-2.5 py-1.5 text-[11px] text-emerald-100/65 sm:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-agriGreen shadow-[0_0_8px_rgba(66,217,154,.8)]" />
              系统运行正常
            </div>
            <Link href="/alerts" aria-label="查看预警" className="relative rounded-md border border-white/[0.07] p-2 text-slate-400 transition hover:bg-white/5 hover:text-white">
              <Bell className="h-4 w-4" />
              <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-danger" />
            </Link>
          </div>
        </header>
        <main className="w-full min-w-0 px-4 py-4 sm:px-6 sm:py-5 lg:px-7">
          <div className="mx-auto w-full max-w-[1720px]">{children}</div>
        </main>
      </div>
    </div>
  );
}

function QuickNav() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const results = navItems.filter((item) => item.label.toLowerCase().includes(query.trim().toLowerCase()));

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen(true);
      }
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  function go(href: string) {
    router.push(href);
    setQuery("");
    setOpen(false);
  }

  return (
    <div className="relative hidden xl:block">
      <button
        type="button"
        aria-expanded={open}
        aria-label="打开快捷跳转"
        onClick={() => setOpen((value) => !value)}
        className="flex w-56 items-center gap-2 rounded-md border border-white/[0.07] bg-white/[0.025] px-3 py-2 text-left text-xs text-slate-500 transition hover:border-cyanGlow/25 hover:text-slate-300"
      >
        <Search className="h-3.5 w-3.5" />
        快捷跳转
        <span className="ml-auto rounded border border-white/10 px-1.5 py-0.5 text-[9px] text-slate-600">Ctrl K</span>
      </button>
      {open && (
        <div role="dialog" aria-label="快捷跳转面板" className="absolute right-0 top-12 z-50 w-72 rounded-lg border border-cyan-200/15 bg-[#0a171a]/98 p-2 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center gap-2 rounded-md border border-white/10 bg-black/20 px-2.5">
            <Search className="h-3.5 w-3.5 text-cyanGlow" />
            <input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && results[0]) go(results[0].href); }} placeholder="输入页面名称" className="h-9 min-w-0 flex-1 bg-transparent text-xs text-white outline-none placeholder:text-slate-600" />
          </div>
          <div className="mt-2 space-y-1">
            {results.length ? results.map((item) => {
              const Icon = item.icon;
              return <button key={item.href} type="button" onClick={() => go(item.href)} className="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-xs text-slate-300 transition hover:bg-cyan-300/8 hover:text-white"><Icon className="h-3.5 w-3.5 text-cyanGlow" />{item.label}<ChevronRight className="ml-auto h-3 w-3 text-slate-600" /></button>;
            }) : <div className="px-2.5 py-3 text-xs text-slate-500">没有匹配页面</div>}
          </div>
        </div>
      )}
    </div>
  );
}
