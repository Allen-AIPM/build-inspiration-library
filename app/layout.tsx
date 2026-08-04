import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Build Inspiration | 建筑灵感库",
  description: "为建筑、室内与空间创作收集值得停留的视觉瞬间。",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
