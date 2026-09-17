"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

const chartText = "#829f99";
const colors = ["#42d99a", "#47d7dd", "#5a9cf5", "#f7bd57", "#f16d73", "#9d8cf3"];
const tooltipStyle = {
  background: "rgba(7,18,20,.97)",
  border: "1px solid rgba(151,206,194,.18)",
  borderRadius: 6,
  color: "#effcf7",
  boxShadow: "0 18px 40px rgba(0,0,0,.36)"
};

function ChartEmpty() {
  return (
    <div className="flex h-[260px] items-center justify-center rounded-lg border border-dashed border-cyan-200/18 bg-white/5 text-sm text-cyan-100/55">
      暂无可展示的图表数据
    </div>
  );
}

export function RiskTrendChart({ data }: { data: { date: string; risk: number }[] }) {
  if (!data?.length) return <ChartEmpty />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#47d7dd" stopOpacity={0.34} />
            <stop offset="95%" stopColor="#47d7dd" stopOpacity={0.015} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(151,206,194,.08)" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: chartText, fontSize: 11 }} minTickGap={24} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: chartText, fontSize: 11 }} domain={[0, 100]} tickLine={false} axisLine={false} width={34} />
        <Tooltip contentStyle={tooltipStyle} labelFormatter={(label) => `日期：${label}`} formatter={(value) => [`${value} 分`, "风险评分"]} />
        <Legend wrapperStyle={{ color: chartText, fontSize: 12 }} />
        <Area type="monotone" dataKey="risk" name="风险评分" stroke="#47d7dd" strokeWidth={2.2} fill="url(#riskGradient)" activeDot={{ r: 4, fill: "#47d7dd", stroke: "#071214" }} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function CropPieChart({ data }: { data: { name: string; value: number }[] }) {
  if (!data?.length) return <ChartEmpty />;
  return (
    <ResponsiveContainer width="100%" height={190}>
      <PieChart>
        <Pie data={data} innerRadius={45} outerRadius={68} paddingAngle={2} dataKey="value" nameKey="name" stroke="rgba(5,11,13,.8)" strokeWidth={2}>
          {data.map((_, index) => (
            <Cell key={index} fill={colors[index % colors.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${value} 亩`, "面积"]} />
        <Legend wrapperStyle={{ color: chartText, fontSize: 12 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function TownRankingChart({ data }: { data: { town: string; risk_score: number }[] }) {
  if (!data?.length) return <ChartEmpty />;
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid stroke="rgba(151,206,194,.08)" vertical={false} />
        <XAxis dataKey="town" tick={{ fill: chartText, fontSize: 11 }} tickLine={false} axisLine={false} />
        <YAxis tick={{ fill: chartText, fontSize: 11 }} domain={[0, 100]} tickLine={false} axisLine={false} width={34} />
        <Tooltip contentStyle={tooltipStyle} formatter={(value) => [`${value} 分`, "风险评分"]} />
        <Legend wrapperStyle={{ color: chartText, fontSize: 12 }} />
        <Bar dataKey="risk_score" name="风险评分" radius={[4, 4, 0, 0]} fill="#42d99a" maxBarSize={34} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ForecastChart({ data }: { data: { date: string; predicted_yield: number; risk_score: number }[] }) {
  if (!data?.length) return <ChartEmpty />;
  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="yieldGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#20d587" stopOpacity={0.34} />
            <stop offset="95%" stopColor="#20d587" stopOpacity={0.04} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(255,255,255,.08)" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: chartText, fontSize: 11 }} />
        <YAxis yAxisId="left" tick={{ fill: chartText, fontSize: 11 }} />
        <YAxis yAxisId="right" orientation="right" tick={{ fill: chartText, fontSize: 11 }} domain={[0, 100]} />
        <Tooltip contentStyle={tooltipStyle} formatter={(value, name) => [name === "预测亩产" ? `${value} kg/亩` : `${value} 分`, name]} />
        <Legend wrapperStyle={{ color: chartText, fontSize: 12 }} />
        <Area yAxisId="left" type="monotone" dataKey="predicted_yield" name="预测亩产" stroke="#20d587" fill="url(#yieldGradient)" strokeWidth={2.5} />
        <Area yAxisId="right" type="monotone" dataKey="risk_score" name="风险评分" stroke="#ffca55" fill="rgba(255,202,85,.08)" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
