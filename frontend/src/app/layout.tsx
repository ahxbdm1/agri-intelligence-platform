import type { Metadata } from "next";
import "@/styles/globals.css";
import { ShellGate } from "@/components/layout/ShellGate";

export const metadata: Metadata = {
  title: "农智云瞰 | 县域农业 AI 决策平台",
  description: "病虫害识别、产量风险预测与农情决策大数据平台"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className="dark">
      <body><ShellGate>{children}</ShellGate></body>
    </html>
  );
}
