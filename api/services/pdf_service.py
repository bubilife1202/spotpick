"""
PDF 리포트 생성 서비스 - Playwright 기반 HTML→PDF 변환
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None  # type: ignore[assignment]


class PDFService:
    """PDF 리포트 생성 서비스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.template_dir = Path(__file__).parent.parent / "templates"
        self.template_dir.mkdir(exist_ok=True)

    async def generate_report_pdf(
        self,
        conversation_data: dict[str, Any],
        industry_name: str = "카페",
    ) -> bytes:
        """
        대화 기반 창업 리포트 PDF 생성

        Args:
            conversation_data: 대화에서 수집한 데이터
                - recommendations: 추천 상권 목록
                - charts: 차트 데이터
                - competitive: 경쟁 분석
                - simulation: 시뮬레이션 데이터
                - context: 사용자 컨텍스트
            industry_name: 업종명 (e.g., "카페", "한식")

        Returns:
            PDF 바이트 데이터
        """
        if async_playwright is None:
            raise RuntimeError("Playwright가 설치되지 않았습니다. pip install playwright 후 playwright install 실행이 필요합니다.")

        html_content = self._render_html_report(conversation_data, industry_name)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.set_content(html_content, wait_until="networkidle")

                # PDF 생성 옵션
                pdf_bytes = await page.pdf(
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "20mm",
                        "right": "15mm",
                        "bottom": "20mm",
                        "left": "15mm",
                    },
                )
                return pdf_bytes
            finally:
                await browser.close()

    def _render_html_report(self, data: dict[str, Any], industry_name: str) -> str:
        """HTML 리포트 렌더링"""
        now = datetime.now().strftime("%Y년 %m월 %d일")

        recommendations = data.get("recommendations", [])
        charts = data.get("charts", [])
        competitive = data.get("competitive")
        simulation = data.get("simulation")
        context = data.get("context", {})

        # 표지
        cover_html = self._render_cover(industry_name, now, context)

        # 목차
        toc_html = self._render_toc()

        # 시장 분석
        market_html = self._render_market_analysis(charts, competitive)

        # 입지 분석
        location_html = self._render_location_analysis(recommendations)

        # 시뮬레이션
        simulation_html = self._render_simulation(simulation) if simulation else ""

        # 경쟁 분석
        competitive_html = self._render_competitive_analysis(competitive) if competitive else ""

        return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>창업 분석 리포트 - {industry_name}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Noto Sans KR', sans-serif;
            color: #1a1a1a;
            line-height: 1.6;
        }}

        .cover {{
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-align: center;
            page-break-after: always;
        }}

        .cover h1 {{
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 20px;
        }}

        .cover .subtitle {{
            font-size: 24px;
            font-weight: 300;
            margin-bottom: 40px;
        }}

        .cover .metadata {{
            font-size: 16px;
            font-weight: 300;
            opacity: 0.9;
        }}

        .toc {{
            page-break-after: always;
            padding: 40px;
        }}

        .toc h2 {{
            font-size: 32px;
            margin-bottom: 30px;
            color: #667eea;
        }}

        .toc ul {{
            list-style: none;
            font-size: 18px;
        }}

        .toc li {{
            padding: 12px 0;
            border-bottom: 1px solid #e0e0e0;
        }}

        .section {{
            page-break-before: always;
            padding: 40px;
        }}

        .section h2 {{
            font-size: 32px;
            margin-bottom: 30px;
            color: #667eea;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}

        .section h3 {{
            font-size: 24px;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #333;
        }}

        .section p {{
            font-size: 14px;
            margin-bottom: 15px;
        }}

        .card {{
            background: #f9fafb;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }}

        .card h4 {{
            font-size: 18px;
            margin-bottom: 10px;
            color: #667eea;
        }}

        .metric {{
            display: inline-block;
            background: white;
            padding: 10px 15px;
            margin: 5px;
            border-radius: 6px;
            font-size: 14px;
        }}

        .metric .label {{
            color: #666;
            font-size: 12px;
        }}

        .metric .value {{
            color: #1a1a1a;
            font-weight: 700;
            font-size: 16px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
            border-radius: 8px;
            overflow: hidden;
        }}

        th, td {{
            padding: 14px 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}

        th {{
            background: #f3f4f6;
            font-weight: 600;
            color: #374151;
        }}

        tr:nth-child(even) {{
            background: #f9fafb;
        }}

        tr:hover {{
            background: #f0f1f3;
        }}

        .chart-placeholder {{
            background: #f0f0f0;
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            margin: 20px 0;
            color: #666;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }}

        .badge.success {{
            background: #d1fae5;
            color: #065f46;
        }}

        .badge.warning {{
            background: #fed7aa;
            color: #92400e;
        }}

        .badge.danger {{
            background: #fecaca;
            color: #991b1b;
        }}

        .footer {{
            text-align: center;
            font-size: 12px;
            color: #666;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}
    </style>
</head>
<body>
    {cover_html}
    {toc_html}
    {market_html}
    {location_html}
    {simulation_html}
    {competitive_html}
</body>
</html>
"""

    def _render_cover(self, industry_name: str, date: str, context: dict[str, Any]) -> str:
        """표지 렌더링"""
        district = context.get("district", "서울 전역")
        budget = context.get("budget", "")  # 문자열 형태 (e.g., "5000만~1억")
        target = context.get("target", "")

        return f"""
    <div class="cover">
        <div style="margin-bottom: 60px; padding: 30px; background: rgba(255,255,255,0.1); border-radius: 20px; backdrop-filter: blur(10px);">
            <div style="width: 80px; height: 80px; margin: 0 auto 20px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 36px; font-weight: 700; color: #667eea;">BC</div>
            <h1 style="font-size: 56px; margin-bottom: 15px; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);">{industry_name} 창업 분석 리포트</h1>
            <div class="subtitle" style="font-size: 28px; opacity: 0.95;">{district} 상권 분석</div>
        </div>
        <div class="metadata" style="font-size: 18px; line-height: 2;">
            <p style="margin-bottom: 10px;">📅 {date} 생성</p>
            {f'<p style="margin-bottom: 10px;">💰 예산: {budget}</p>' if budget else ''}
            {f'<p style="margin-bottom: 10px;">🎯 타겟: {target}</p>' if target else ''}
        </div>
    </div>
"""

    def _render_toc(self) -> str:
        """목차 렌더링"""
        return """
    <div class="toc">
        <h2>목차</h2>
        <ul>
            <li>1. 시장 분석</li>
            <li>2. 입지 분석</li>
            <li>3. 창업 시뮬레이션</li>
            <li>4. 경쟁 분석</li>
        </ul>
        <div class="footer" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center;">
            <p style="font-size: 12px; color: #666;">페이지 1</p>
        </div>
    </div>
"""

    def _render_market_analysis(self, charts: list[dict[str, Any]], competitive: Optional[dict[str, Any]]) -> str:
        """시장 분석 섹션"""
        charts_html = ""
        for chart in charts[:3]:  # 최대 3개 차트
            title = chart.get("title", "")
            chart_type = chart.get("type", "")
            charts_html += f"""
        <div class="chart-placeholder">
            <div>
                <strong>{title}</strong><br/>
                <small>차트 타입: {chart_type}</small>
            </div>
        </div>
"""

        competitive_summary = ""
        if competitive:
            total_cafes = competitive.get("total_competitors", 0)
            competitive_summary = f"""
        <div class="card">
            <h4>경쟁 현황</h4>
            <p>주변 경쟁 매장: <strong>{total_cafes}개</strong></p>
        </div>
"""

        return f"""
    <div class="section">
        <h2>1. 시장 분석</h2>
        <h3>주요 지표</h3>
        {charts_html}
        {competitive_summary}
        <div class="footer" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center;">
            <p style="font-size: 12px; color: #666;">페이지 1</p>
        </div>
    </div>
"""

    def _render_location_analysis(self, recommendations: list[dict[str, Any]]) -> str:
        """입지 분석 섹션"""
        if not recommendations:
            return """
    <div class="section">
        <h2>2. 입지 분석</h2>
        <p>추천 상권이 없습니다.</p>
    </div>
"""

        cards_html = ""
        for rec in recommendations[:5]:  # 상위 5개 추천
            rank = rec.get("rank", 0)
            district_name = rec.get("district_name", "")
            success_prob = rec.get("success_probability", 0)  # 이미 퍼센트 값 (78.5)
            monthly_sales = rec.get("monthly_sales", 0)
            store_count = rec.get("store_count", 0)
            closed_ratio = rec.get("closed_ratio", 0)
            foot_traffic = rec.get("foot_traffic_total", 0)

            # 성공 확률에 따른 뱃지 색상
            if success_prob >= 70:
                badge_class = "success"
            elif success_prob >= 50:
                badge_class = "warning"
            else:
                badge_class = "danger"

            cards_html += f"""
        <div class="card">
            <h4>#{rank} {district_name} <span class="badge {badge_class}">{success_prob:.1f}%</span></h4>
            <div class="metric">
                <div class="label">월 평균 매출</div>
                <div class="value">{monthly_sales:,}원</div>
            </div>
            <div class="metric">
                <div class="label">매장 수</div>
                <div class="value">{store_count:,}개</div>
            </div>
            <div class="metric">
                <div class="label">폐업률</div>
                <div class="value">{closed_ratio*100:.1f}%</div>
            </div>
            <div class="metric">
                <div class="label">유동인구</div>
                <div class="value">{foot_traffic:,}명</div>
            </div>
        </div>
"""

        return f"""
    <div class="section">
        <h2>2. 입지 분석</h2>
        <h3>추천 상권</h3>
        {cards_html}
        <div class="footer" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center;">
            <p style="font-size: 12px; color: #666;">페이지 2</p>
        </div>
    </div>
"""

    def _render_simulation(self, simulation: dict[str, Any]) -> str:
        """시뮬레이션 섹션"""
        district_name = simulation.get("district_name", "")

        # Flat 구조 데이터
        monthly_revenue = simulation.get("monthly_revenue", 0)
        startup_cost = simulation.get("startup_cost", 0)
        monthly_operating_cost = simulation.get("monthly_operating_cost", 0)
        break_even_months = simulation.get("break_even_months", 0)
        monthly_profit = simulation.get("monthly_profit", 0)

        # 시각적 바 차트 (손익분기 진행도)
        profit_ratio = min(100, (monthly_profit / monthly_revenue * 100)) if monthly_revenue > 0 else 0

        return f"""
    <div class="section">
        <h2>3. 창업 시뮬레이션</h2>
        <h3>{district_name} 예상 수치</h3>

        <div class="card">
            <h4>💰 예상 매출 및 비용</h4>
            <div class="metric">
                <div class="label">월 매출</div>
                <div class="value">{monthly_revenue:,}원</div>
            </div>
            <div class="metric">
                <div class="label">월 운영비</div>
                <div class="value">{monthly_operating_cost:,}원</div>
            </div>
            <div class="metric">
                <div class="label">월 순이익</div>
                <div class="value" style="color: {'#10b981' if monthly_profit > 0 else '#ef4444'};">{monthly_profit:,}원</div>
            </div>
        </div>

        <div class="card">
            <h4>📊 수익성 분석</h4>
            <p style="margin-bottom: 10px; font-size: 13px; color: #666;">월 순이익률</p>
            <div style="width: 100%; height: 30px; background: #e5e7eb; border-radius: 15px; overflow: hidden; position: relative;">
                <div style="width: {profit_ratio:.1f}%; height: 100%; background: linear-gradient(90deg, #10b981, #059669); transition: width 0.3s;"></div>
                <span style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); font-weight: 600; color: #1f2937; font-size: 14px;">{profit_ratio:.1f}%</span>
            </div>
        </div>

        <div class="card">
            <h4>🏁 초기 투자 및 손익분기</h4>
            <table style="background: white;">
                <tr style="background: #f9fafb;">
                    <th>항목</th>
                    <th style="text-align: right;">금액</th>
                </tr>
                <tr>
                    <td>초기 투자금</td>
                    <td style="text-align: right; font-weight: 600;">{startup_cost:,}원</td>
                </tr>
                <tr style="background: #f9fafb;">
                    <td>손익분기점</td>
                    <td style="text-align: right; font-weight: 600; color: #667eea;">{break_even_months:.1f}개월</td>
                </tr>
            </table>
        </div>

        <div class="footer" style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; text-align: center;">
            <p style="font-size: 12px; color: #666;">페이지 3</p>
        </div>
    </div>
"""

    def _render_competitive_analysis(self, competitive: dict[str, Any]) -> str:
        """경쟁 분석 섹션"""
        total = competitive.get("total_competitors", 0)
        cafe_types = competitive.get("cafe_types", {})  # dict 형태
        market_gap = competitive.get("market_gap", "")
        strategy = competitive.get("strategy", "")

        types_html = ""
        for type_name, count in cafe_types.items():
            ratio = (count / total * 100) if total > 0 else 0
            types_html += f"""
                <tr style="background: {'#f9fafb' if len(types_html) % 2 == 0 else 'white'};">
                    <td>{type_name}</td>
                    <td style="text-align: right;">{count}개</td>
                    <td style="text-align: right; font-weight: 600; color: #667eea;">{ratio:.1f}%</td>
                </tr>
"""

        return f"""
    <div class="section">
        <h2>4. 경쟁 분석</h2>
        <h3>🏪 주변 경쟁 현황</h3>
        <p style="font-size: 16px; margin-bottom: 20px;">총 <strong style="color: #667eea; font-size: 20px;">{total}개</strong> 경쟁 매장 확인</p>

        <table style="border: 1px solid #e5e7eb;">
            <tr style="background: #667eea; color: white;">
                <th>카페 유형</th>
                <th style="text-align: right;">매장 수</th>
                <th style="text-align: right;">비율</th>
            </tr>
            {types_html}
        </table>

        <h3 style="margin-top: 40px;">💡 시장 기회 및 전략</h3>
        <div class="card" style="background: linear-gradient(135deg, #667eea10, #764ba210); border-left: 4px solid #667eea;">
            <h4 style="color: #667eea; margin-bottom: 15px;">시장 격차 분석</h4>
            <p style="font-size: 15px; line-height: 1.8;">{market_gap}</p>
        </div>

        <div class="card" style="background: linear-gradient(135deg, #10b98110, #059f4610); border-left: 4px solid #10b981;">
            <h4 style="color: #10b981; margin-bottom: 15px;">추천 차별화 전략</h4>
            <p style="font-size: 15px; line-height: 1.8;">{strategy}</p>
        </div>

        <div class="footer" style="margin-top: 40px; padding: 30px 0; border-top: 2px solid #e0e0e0;">
            <p style="font-size: 13px; color: #666; margin-bottom: 8px;">본 리포트는 Builder Curation AI 시스템에 의해 자동 생성되었습니다.</p>
            <p style="font-size: 12px; color: #999;">실제 창업 결정 시 현장 실사 및 전문가 상담을 권장합니다.</p>
            <p style="font-size: 12px; color: #666; margin-top: 15px;">페이지 4</p>
        </div>
    </div>
"""


# 싱글톤 패턴
_pdf_service: Optional[PDFService] = None


def get_pdf_service() -> PDFService:
    """PDF 서비스 싱글톤 인스턴스 반환"""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service
