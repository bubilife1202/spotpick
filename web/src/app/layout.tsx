import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SpotPick — AI 창업 의사결정 플랫폼",
  description: "서울 1,077개 상권 데이터 + AI 분석. 업종선택부터 사업계획서까지 5분 완성.",
  keywords: ["창업", "상권분석", "입지추천", "AI", "카페창업", "소상공인", "서울상권"],
  openGraph: {
    title: "SpotPick — 창업, 감으로 하지 마세요",
    description: "AI가 최적 상권을 찾고, 수익을 예측하고, 사업계획서를 만들어드립니다.",
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
