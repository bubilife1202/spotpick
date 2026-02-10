import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SpotPick - AI 창업 코치",
  description: "창업, 물어볼 데가 없으셨죠? AI가 당신의 상황을 듣고, 해도 되는지 솔직하게 말해드립니다.",
  keywords: ["창업", "상권분석", "입지추천", "AI", "카페창업", "소상공인", "서울상권"],
  openGraph: {
    title: "SpotPick - AI 창업 코치",
    description: "창업, 물어볼 데가 없으셨죠? AI가 당신의 상황을 듣고, 해도 되는지 솔직하게 말해드립니다.",
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
