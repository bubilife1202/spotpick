import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SpotPick - AI 창업 입지 분석",
  description: "1,077개 상권 데이터와 AI가 분석하는 최적의 창업 입지 추천. 업종 선택부터 사업계획서까지 원스톱.",
  keywords: ["창업", "상권분석", "입지추천", "AI", "카페창업", "소상공인", "서울상권"],
  openGraph: {
    title: "SpotPick - AI 창업 입지 분석",
    description: "1,077개 상권 데이터와 AI가 분석하는 최적의 창업 입지 추천",
    type: "website",
    locale: "ko_KR",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
