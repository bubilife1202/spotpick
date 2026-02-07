"""
PDF 리포트 생성 서비스 - 프로페셔널 창업 사업계획서 품질
Playwright 기반 HTML→PDF 변환 / 시스템 폰트 사용 / 실제 차트 렌더링
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
    """PDF 리포트 생성 서비스 - 프로페셔널 사업계획서"""

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
                - timeline: 창업 타임라인
                - trend: 네이버 트렌드 데이터
                - support_programs: 정부지원사업 목록
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
        timeline = data.get("timeline")
        trend = data.get("trend")
        support_programs = data.get("support_programs", [])

        # 표지
        cover_html = self._render_cover(industry_name, now, context)

        # 동적 목차 (데이터 있는 섹션만)
        toc_html = self._render_toc(data)

        # 시장 분석
        market_html = self._render_market_analysis(charts, competitive)

        # 입지 분석 (스코어카드 포함)
        location_html = self._render_location_analysis(recommendations)

        # 시뮬레이션 (중첩 구조 처리)
        simulation_html = self._render_simulation(simulation) if simulation else ""

        # 경쟁 분석 (리스트 구조 처리 + 번역)
        competitive_html = self._render_competitive_analysis(competitive) if competitive else ""

        # 창업 타임라인 (간트 차트)
        timeline_html = self._render_timeline(timeline) if timeline else ""

        # 트렌드 분석 (네이버 트렌드)
        trend_html = self._render_trend_analysis(trend) if trend else ""

        # 정부지원사업
        support_html = self._render_support_programs(support_programs) if support_programs else ""

        return f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpotPick 창업 분석 리포트 - {industry_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
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
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}

        .cover .subtitle {{
            font-size: 24px;
            font-weight: 400;
            margin-bottom: 40px;
            opacity: 0.95;
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
            padding: 12px 10px;
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

        .chart-bar {{
            background: #f3f4f6;
            border-radius: 8px;
            margin: 20px 0;
            padding: 15px;
        }}

        .chart-bar .bar-item {{
            margin-bottom: 12px;
        }}

        .chart-bar .bar-label {{
            font-size: 13px;
            color: #374151;
            margin-bottom: 5px;
            display: flex;
            justify-content: space-between;
        }}

        .chart-bar .bar-bg {{
            background: #e5e7eb;
            height: 30px;
            border-radius: 5px;
            overflow: hidden;
            position: relative;
        }}

        .chart-bar .bar-fill {{
            background: linear-gradient(90deg, #667eea, #764ba2);
            height: 100%;
            display: flex;
            align-items: center;
            padding-left: 10px;
            color: white;
            font-weight: 600;
            font-size: 13px;
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

        .badge.info {{
            background: #dbeafe;
            color: #1e40af;
        }}

        .timeline-bar {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
        }}

        .timeline-bar .timeline-header {{
            font-size: 14px;
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
        }}

        .timeline-bar .timeline-track {{
            background: #f3f4f6;
            height: 40px;
            border-radius: 5px;
            position: relative;
            margin-bottom: 5px;
        }}

        .timeline-bar .timeline-fill {{
            background: linear-gradient(90deg, #10b981, #059669);
            height: 100%;
            border-radius: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
            font-size: 12px;
        }}

        .timeline-bar .timeline-desc {{
            font-size: 12px;
            color: #6b7280;
            margin-top: 5px;
        }}

        .footer {{
            text-align: center;
            font-size: 12px;
            color: #666;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }}

        .scorecard-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 15px 0;
        }}

        .scorecard-item {{
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 10px;
            text-align: center;
        }}

        .scorecard-item .score-label {{
            font-size: 11px;
            color: #6b7280;
            margin-bottom: 5px;
        }}

        .scorecard-item .score-value {{
            font-size: 16px;
            font-weight: 700;
            color: #667eea;
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
    {timeline_html}
    {trend_html}
    {support_html}
</body>
</html>
"""

    def _render_cover(self, industry_name: str, date: str, context: dict[str, Any]) -> str:
        """표지 렌더링 - SpotPick 브랜딩"""
        district = context.get("district", "서울 전역")
        budget = context.get("budget", "")
        target = context.get("target", "")

        return f"""
    <div class="cover">
        <div style="margin-bottom: 60px; padding: 30px; background: rgba(255,255,255,0.1); border-radius: 20px; backdrop-filter: blur(10px);">
            <div style="width: 80px; height: 80px; margin: 0 auto 20px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 36px; font-weight: 700; color: #667eea;">SP</div>
            <h1 style="font-size: 56px; margin-bottom: 15px;">{industry_name} 창업 분석 리포트</h1>
            <div class="subtitle" style="font-size: 28px;">{district} 상권 분석</div>
        </div>
        <div class="metadata" style="font-size: 18px; line-height: 2;">
            <p style="margin-bottom: 10px;">📅 {date} 생성</p>
            {f'<p style="margin-bottom: 10px;">💰 예산: {budget}</p>' if budget else ''}
            {f'<p style="margin-bottom: 10px;">🎯 타겟: {target}</p>' if target else ''}
        </div>
    </div>
"""

    def _render_toc(self, data: dict[str, Any]) -> str:
        """동적 목차 렌더링 - 데이터 있는 섹션만 표시"""
        toc_items = []
        section_num = 1

        if data.get("charts") or data.get("competitive"):
            toc_items.append(f"<li>{section_num}. 시장 분석</li>")
            section_num += 1

        if data.get("recommendations"):
            toc_items.append(f"<li>{section_num}. 입지 분석</li>")
            section_num += 1

        if data.get("simulation"):
            toc_items.append(f"<li>{section_num}. 창업 시뮬레이션</li>")
            section_num += 1

        if data.get("competitive"):
            toc_items.append(f"<li>{section_num}. 경쟁 분석</li>")
            section_num += 1

        if data.get("timeline"):
            toc_items.append(f"<li>{section_num}. 창업 타임라인</li>")
            section_num += 1

        if data.get("trend"):
            toc_items.append(f"<li>{section_num}. 트렌드 분석</li>")
            section_num += 1

        if data.get("support_programs"):
            toc_items.append(f"<li>{section_num}. 정부지원사업</li>")
            section_num += 1

        toc_html = "\n            ".join(toc_items)

        return f"""
    <div class="toc">
        <h2>목차</h2>
        <ul>
            {toc_html}
        </ul>
        <div class="footer">
            <p>SpotPick AI 창업 분석 리포트 | {datetime.now().strftime("%Y년 %m월 %d일")}</p>
        </div>
    </div>
"""

    def _format_currency(self, value: float) -> str:
        """통화 포맷팅 - 만원 단위 사용"""
        if value >= 10000:
            man_won = int(value / 10000)
            return f"{man_won:,}만원"
        else:
            return f"{int(value):,}원"

    def _render_bar_chart(self, items: list[dict[str, Any]], max_value: float = None) -> str:
        """HTML div 기반 가로 막대 차트 렌더링"""
        if not items:
            return ""

        if max_value is None:
            max_value = max((item.get("value", 0) for item in items), default=1)

        bars_html = ""
        for item in items:
            name = item.get("name", "")
            value = item.get("value", 0)
            sales = item.get("sales")
            transactions = item.get("transactions")

            percentage = (value / max_value * 100) if max_value > 0 else 0

            # 추가 정보 표시
            extra_info = ""
            if sales is not None:
                extra_info += f" (매출: {self._format_currency(sales)})"
            if transactions is not None:
                extra_info += f" (건수: {transactions:,}건)"

            bars_html += f"""
        <div class="bar-item">
            <div class="bar-label">
                <span>{name}{extra_info}</span>
                <span style="font-weight: 600;">{value:,}</span>
            </div>
            <div class="bar-bg">
                <div class="bar-fill" style="width: {percentage:.1f}%;">
                    {percentage:.1f}%
                </div>
            </div>
        </div>
"""

        return f"""
    <div class="chart-bar">
        {bars_html}
    </div>
"""

    def _render_market_analysis(self, charts: list[dict[str, Any]], competitive: Optional[dict[str, Any]]) -> str:
        """시장 분석 섹션 - 실제 차트 렌더링"""
        charts_html = ""
        for chart in charts[:3]:
            title = chart.get("title", "")
            chart_data = chart.get("data", [])

            if chart_data:
                charts_html += f"""
        <h3>{title}</h3>
        {self._render_bar_chart(chart_data)}
"""

        competitive_summary = ""
        if competitive:
            total_cafes = competitive.get("total_competitors", 0)
            competitive_summary = f"""
        <div class="card">
            <h4>경쟁 현황</h4>
            <p>주변 경쟁 매장: <strong style="color: #667eea; font-size: 20px;">{total_cafes}개</strong></p>
        </div>
"""

        return f"""
    <div class="section">
        <h2>1. 시장 분석</h2>
        {charts_html}
        {competitive_summary}
        <div class="footer">
            <p>SpotPick AI 창업 분석 리포트 | {datetime.now().strftime("%Y년 %m월 %d일")}</p>
        </div>
    </div>
"""

    def _render_location_analysis(self, recommendations: list[dict[str, Any]]) -> str:
        """입지 분석 섹션 - 스코어카드 포함"""
        if not recommendations:
            return """
    <div class="section">
        <h2>2. 입지 분석</h2>
        <p>추천 상권이 없습니다.</p>
    </div>
"""

        cards_html = ""
        for rec in recommendations[:5]:
            rank = rec.get("rank", 0)
            district_name = rec.get("district_name", "")
            success_prob = rec.get("success_probability", 0)
            monthly_sales = rec.get("monthly_sales", 0)
            store_count = rec.get("store_count", 0)
            closed_ratio = rec.get("closed_ratio", 0)
            foot_traffic = rec.get("foot_traffic_total", 0)
            scorecard = rec.get("scorecard")

            # 성공 확률에 따른 뱃지 색상
            if success_prob >= 70:
                badge_class = "success"
            elif success_prob >= 50:
                badge_class = "warning"
            else:
                badge_class = "danger"

            # 스코어카드 렌더링
            scorecard_html = ""
            if scorecard:
                total_score = scorecard.get("total_score", 0)
                percentile = scorecard.get("percentile", 0)
                categories = scorecard.get("categories", {})

                scorecard_items = ""
                for cat_name, cat_score in categories.items():
                    scorecard_items += f"""
                    <div class="scorecard-item">
                        <div class="score-label">{cat_name}</div>
                        <div class="score-value">{cat_score:.1f}</div>
                    </div>
"""

                scorecard_html = f"""
            <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #e5e7eb;">
                <div style="margin-bottom: 10px;">
                    <span style="font-weight: 600; color: #667eea; font-size: 16px;">종합 점수: {total_score:.1f}점</span>
                    <span class="badge info" style="margin-left: 10px;">상위 {percentile:.1f}%</span>
                </div>
                <div class="scorecard-grid">
                    {scorecard_items}
                </div>
            </div>
"""

            cards_html += f"""
        <div class="card">
            <h4>#{rank} {district_name} <span class="badge {badge_class}">{success_prob:.1f}%</span></h4>
            <div class="metric">
                <div class="label">월 평균 매출</div>
                <div class="value">{self._format_currency(monthly_sales)}</div>
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
            {scorecard_html}
        </div>
"""

        return f"""
    <div class="section">
        <h2>2. 입지 분석</h2>
        <h3>추천 상권</h3>
        {cards_html}
        <div class="footer">
            <p>SpotPick AI 창업 분석 리포트 | {datetime.now().strftime("%Y년 %m월 %d일")}</p>
        </div>
    </div>
"""

    def _render_simulation(self, simulation: dict[str, Any]) -> str:
        """시뮬레이션 섹션 - 중첩 구조 처리"""
        district_name = simulation.get("district_name", "")

        # 중첩 구조 데이터 추출
        revenue = simulation.get("revenue", {})
        monthly_sales = revenue.get("monthly_sales_per_store", 0)
        daily_sales = revenue.get("daily_sales", 0)
        daily_customers = revenue.get("daily_customers", 0)
        avg_spending = revenue.get("average_spending_per_customer", 0)

        startup = simulation.get("startup_cost", {})
        total_min = startup.get("total_min", 0)
        total_max = startup.get("total_max", 0)
        interior = startup.get("interior", 0)
        equipment = startup.get("equipment", 0)
        initial_inventory = startup.get("initial_inventory", 0)

        operating = simulation.get("operating_cost", {})
        rent = operating.get("rent", 0)
        labor = operating.get("labor", 0)
        materials = operating.get("materials", 0)
        utilities = operating.get("utilities", 0)
        other = operating.get("other", 0)
        total_operating = rent + labor + materials + utilities + other

        break_even_data = simulation.get("break_even", {})
        break_even_months = break_even_data.get("months", 0)

        competition = simulation.get("competition", {})
        competition_level = competition.get("level", "보통")
        nearby_stores = competition.get("nearby_stores", 0)

        menu_costs_data = simulation.get("menu_costs", {})

        # 월 순이익 계산
        monthly_profit = monthly_sales - total_operating

        # 수익률
        profit_ratio = (monthly_profit / monthly_sales * 100) if monthly_sales > 0 else 0

        # 매출 구성 테이블
        revenue_table = f"""
        <table style="background: white;">
            <tr style="background: #667eea; color: white;">
                <th>항목</th>
                <th style="text-align: right;">금액</th>
            </tr>
            <tr>
                <td>월 평균 매출</td>
                <td style="text-align: right; font-weight: 600; color: #667eea;">{self._format_currency(monthly_sales)}</td>
            </tr>
            <tr style="background: #f9fafb;">
                <td>일 평균 매출</td>
                <td style="text-align: right;">{self._format_currency(daily_sales)}</td>
            </tr>
            <tr>
                <td>일 평균 고객 수</td>
                <td style="text-align: right;">{daily_customers:,}명</td>
            </tr>
            <tr style="background: #f9fafb;">
                <td>객단가</td>
                <td style="text-align: right;">{self._format_currency(avg_spending)}</td>
            </tr>
        </table>
"""

        # 초기 투자 비용 테이블
        startup_table = f"""
        <table style="background: white;">
            <tr style="background: #667eea; color: white;">
                <th>항목</th>
                <th style="text-align: right;">금액</th>
            </tr>
            <tr>
                <td>총 초기 투자 (최소)</td>
                <td style="text-align: right; font-weight: 700; color: #667eea;">{self._format_currency(total_min)}</td>
            </tr>
            <tr style="background: #f9fafb;">
                <td>총 초기 투자 (최대)</td>
                <td style="text-align: right; font-weight: 700; color: #ef4444;">{self._format_currency(total_max)}</td>
            </tr>
            <tr>
                <td>인테리어</td>
                <td style="text-align: right;">{self._format_currency(interior)}</td>
            </tr>
            <tr style="background: #f9fafb;">
                <td>설비/장비</td>
                <td style="text-align: right;">{self._format_currency(equipment)}</td>
            </tr>
            <tr>
                <td>초기 재고</td>
                <td style="text-align: right;">{self._format_currency(initial_inventory)}</td>
            </tr>
        </table>
"""

        # 운영 비용 테이블
        operating_table = f"""
        <table style="background: white;">
            <tr style="background: #667eea; color: white;">
                <th>항목</th>
                <th style="text-align: right;">금액</th>
            </tr>
            <tr>
                <td>월 임대료</td>
                <td style="text-align: right;">{self._format_currency(rent)}</td>
            </tr>
            <tr style="background: #f9fafb;">
                <td>인건비</td>
                <td style="text-align: right;">{self._format_currency(labor)}</td>
            </tr>
            <tr>
                <td>재료비</td>
                <td style="text-align: right;">{self._format_currency(materials)}</td>
            </tr>
            <tr style="background: #f9fafb;">
                <td>공과금</td>
                <td style="text-align: right;">{self._format_currency(utilities)}</td>
            </tr>
            <tr>
                <td>기타</td>
                <td style="text-align: right;">{self._format_currency(other)}</td>
            </tr>
            <tr style="background: #f3f4f6;">
                <td><strong>합계</strong></td>
                <td style="text-align: right; font-weight: 700; color: #667eea;">{self._format_currency(total_operating)}</td>
            </tr>
        </table>
"""

        # 메뉴 원가 테이블
        menu_table = ""
        if menu_costs_data:
            menu_items = menu_costs_data.get("items", [])
            if menu_items:
                menu_rows = ""
                for item in menu_items:
                    item_name = item.get("name", "")
                    selling_price = item.get("selling_price", 0)
                    cost = item.get("cost", 0)
                    margin = item.get("margin", 0)

                    menu_rows += f"""
                <tr>
                    <td>{item_name}</td>
                    <td style="text-align: right;">{selling_price:,}원</td>
                    <td style="text-align: right;">{cost:,}원</td>
                    <td style="text-align: right; font-weight: 600; color: #10b981;">{margin:.1f}%</td>
                </tr>
"""

                menu_table = f"""
        <h3 style="margin-top: 30px;">📋 메뉴별 원가 분석</h3>
        <table style="background: white;">
            <tr style="background: #667eea; color: white;">
                <th>메뉴명</th>
                <th style="text-align: right;">판매가</th>
                <th style="text-align: right;">원가</th>
                <th style="text-align: right;">마진율</th>
            </tr>
            {menu_rows}
        </table>
"""

        # 리스크 요약
        risk_bullets = f"""
        <ul style="list-style: disc; padding-left: 20px; margin: 15px 0;">
            <li style="margin-bottom: 8px;">주변 경쟁 매장: <strong>{nearby_stores}개</strong> (경쟁 수준: <strong>{competition_level}</strong>)</li>
            <li style="margin-bottom: 8px;">손익분기점: <strong>{break_even_months:.1f}개월</strong> 예상</li>
            <li style="margin-bottom: 8px;">월 순이익률: <strong>{profit_ratio:.1f}%</strong></li>
        </ul>
"""

        return f"""
    <div class="section">
        <h2>3. 창업 시뮬레이션</h2>
        <h3>{district_name} 예상 수치</h3>

        <div class="card">
            <h4>💰 매출 예상</h4>
            {revenue_table}
        </div>

        <div class="card">
            <h4>🏁 초기 투자 비용</h4>
            {startup_table}
        </div>

        <div class="card">
            <h4>📊 월 운영 비용</h4>
            {operating_table}
        </div>

        <div class="card">
            <h4>💵 손익 분석</h4>
            <div style="margin-bottom: 15px;">
                <span class="metric">
                    <div class="label">월 매출</div>
                    <div class="value" style="color: #667eea;">{self._format_currency(monthly_sales)}</div>
                </span>
                <span class="metric">
                    <div class="label">월 운영비</div>
                    <div class="value" style="color: #ef4444;">{self._format_currency(total_operating)}</div>
                </span>
                <span class="metric">
                    <div class="label">월 순이익</div>
                    <div class="value" style="color: {'#10b981' if monthly_profit > 0 else '#ef4444'};">{self._format_currency(monthly_profit)}</div>
                </span>
            </div>
            <p style="margin-bottom: 10px; font-size: 13px; color: #666;">월 순이익률</p>
            <div style="width: 100%; height: 35px; background: #e5e7eb; border-radius: 8px; overflow: hidden; position: relative;">
                <div style="width: {max(0, min(100, profit_ratio)):.1f}%; height: 100%; background: linear-gradient(90deg, #10b981, #059669);"></div>
                <span style="position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); font-weight: 700; color: #1f2937; font-size: 15px;">{profit_ratio:.1f}%</span>
            </div>
        </div>

        {menu_table}

        <div class="card" style="background: linear-gradient(135deg, #fef3c710, #fde68a10); border-left: 4px solid #f59e0b;">
            <h4 style="color: #f59e0b;">⚠️ 리스크 요약</h4>
            {risk_bullets}
        </div>

        <div class="footer">
            <p>SpotPick AI 창업 분석 리포트 | {datetime.now().strftime("%Y년 %m월 %d일")}</p>
        </div>
    </div>
"""

    def _translate_cafe_type(self, type_name: str) -> str:
        """카페 유형 영문→한글 번역"""
        translations = {
            "specialty": "스페셜티",
            "franchise": "프랜차이즈",
            "dessert": "디저트",
            "takeout": "테이크아웃",
            "bakery": "베이커리",
            "general": "일반",
        }
        return translations.get(type_name.lower(), type_name)

    def _render_competitive_analysis(self, competitive: dict[str, Any]) -> str:
        """경쟁 분석 섹션 - 리스트 구조 처리 + 번역"""
        total = competitive.get("total_competitors", 0)
        cafe_types = competitive.get("cafe_types", [])  # LIST of dicts
        market_gaps = competitive.get("market_gaps", [])
        strategies = competitive.get("strategies", [])

        # 카페 유형 테이블
        types_html = ""
        for idx, cafe_type in enumerate(cafe_types):
            type_name = cafe_type.get("type", "")
            count = cafe_type.get("count", 0)
            ratio = cafe_type.get("ratio", 0)
            examples = cafe_type.get("examples", [])

            translated_name = self._translate_cafe_type(type_name)
            examples_str = ", ".join(examples[:3]) if examples else ""

            types_html += f"""
                <tr style="background: {'#f9fafb' if idx % 2 == 0 else 'white'};">
                    <td>{translated_name}</td>
                    <td style="text-align: right;">{count}개</td>
                    <td style="text-align: right; font-weight: 600; color: #667eea;">{ratio:.1f}%</td>
                    <td style="font-size: 12px; color: #6b7280;">{examples_str}</td>
                </tr>
"""

        # 시장 격차 분석
        gaps_html = ""
        if market_gaps:
            for gap in market_gaps:
                gaps_html += f"<li style='margin-bottom: 8px;'>{gap}</li>"
        else:
            gap_text = competitive.get("market_gap", "")
            if gap_text:
                gaps_html = f"<li>{gap_text}</li>"

        gaps_section = f"""
        <div class="card" style="background: linear-gradient(135deg, #667eea10, #764ba210); border-left: 4px solid #667eea;">
            <h4 style="color: #667eea; margin-bottom: 15px;">💡 시장 격차 분석</h4>
            <ul style="list-style: disc; padding-left: 20px; font-size: 14px; line-height: 1.8;">
                {gaps_html}
            </ul>
        </div>
""" if gaps_html else ""

        # 차별화 전략
        strategy_html = ""
        if strategies:
            for strategy in strategies:
                strategy_html += f"<li style='margin-bottom: 8px;'>{strategy}</li>"
        else:
            strategy_text = competitive.get("strategy", "")
            if strategy_text:
                strategy_html = f"<li>{strategy_text}</li>"

        strategy_section = f"""
        <div class="card" style="background: linear-gradient(135deg, #10b98110, #059f4610); border-left: 4px solid #10b981;">
            <h4 style="color: #10b981; margin-bottom: 15px;">🎯 추천 차별화 전략</h4>
            <ul style="list-style: disc; padding-left: 20px; font-size: 14px; line-height: 1.8;">
                {strategy_html}
            </ul>
        </div>
""" if strategy_html else ""

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
                <th>예시</th>
            </tr>
            {types_html}
        </table>

        <h3 style="margin-top: 40px;">💡 시장 기회 및 전략</h3>
        {gaps_section}
        {strategy_section}

        <div class="footer">
            <p>SpotPick AI 창업 분석 리포트 | {datetime.now().strftime("%Y년 %m월 %d일")}</p>
        </div>
    </div>
"""

    def _render_timeline(self, timeline: dict[str, Any]) -> str:
        """창업 타임라인 섹션 - 간트 차트 스타일"""
        stages = timeline.get("stages", [])
        total_weeks = timeline.get("total_weeks", 0)

        if not stages:
            return ""

        stages_html = ""
        for stage in stages:
            name = stage.get("name", "")
            duration_weeks = stage.get("duration_weeks", 0)
            start_week = stage.get("start_week", 0)
            end_week = stage.get("end_week", 0)
            description = stage.get("description", "")

            # 간트 차트 바 위치 및 길이 계산
            bar_start_percent = (start_week / total_weeks * 100) if total_weeks > 0 else 0
            bar_width_percent = (duration_weeks / total_weeks * 100) if total_weeks > 0 else 0

            stages_html += f"""
        <div class="timeline-bar">
            <div class="timeline-header">{name} ({duration_weeks}주)</div>
            <div class="timeline-track">
                <div class="timeline-fill" style="width: {bar_width_percent:.1f}%; margin-left: {bar_start_percent:.1f}%;">
                    {start_week}주 ~ {end_week}주
                </div>
            </div>
            <div class="timeline-desc">{description}</div>
        </div>
"""

        return f"""
    <div class="section">
        <h2>5. 창업 타임라인</h2>
        <p style="font-size: 16px; margin-bottom: 20px;">총 예상 기간: <strong style="color: #667eea; font-size: 20px;">{total_weeks}주</strong></p>
        {stages_html}
        <div class="footer">
            <p>SpotPick AI 창업 분석 리포트 | {datetime.now().strftime("%Y년 %m월 %d일")}</p>
        </div>
    </div>
"""

    def _render_trend_analysis(self, trend: dict[str, Any]) -> str:
        """트렌드 분석 섹션 - 네이버 트렌드"""
        trends = trend.get("trends", [])

        if not trends:
            return ""

        # 키워드별 평균 비율로 막대 차트
        trend_items = []
        for trend_item in trends:
            keyword = trend_item.get("keyword", "")
            avg_ratio = trend_item.get("average_ratio", 0)
            trend_items.append({"name": keyword, "value": avg_ratio})

        chart_html = self._render_bar_chart(trend_items)

        # 기간별 상세 테이블
        detail_rows = ""
        if trends:
            # 첫 번째 키워드의 기간별 데이터
            first_trend = trends[0]
            data_points = first_trend.get("data", [])

            for idx, point in enumerate(data_points[:6]):  # 최근 6개월
                period = point.get("period", "")
                row_html = f"<tr><td>{period}</td>"

                for trend_item in trends:
                    data_list = trend_item.get("data", [])
                    if idx < len(data_list):
                        ratio = data_list[idx].get("ratio", 0)
                        row_html += f"<td style='text-align: right;'>{ratio:.1f}</td>"
                    else:
                        row_html += "<td style='text-align: right;'>-</td>"

                row_html += "</tr>"
                detail_rows += row_html

        header_cols = "".join([f"<th style='text-align: right;'>{t.get('keyword', '')}</th>" for t in trends])

        detail_table = f"""
        <h3 style="margin-top: 30px;">📈 기간별 트렌드 변화</h3>
        <table style="background: white;">
            <tr style="background: #667eea; color: white;">
                <th>기간</th>
                {header_cols}
            </tr>
            {detail_rows}
        </table>
"""

        return f"""
    <div class="section">
        <h2>6. 트렌드 분석</h2>
        <h3>📊 키워드 검색 트렌드 비교</h3>
        {chart_html}
        {detail_table}
        <div class="footer">
            <p>SpotPick AI 창업 분석 리포트 | {datetime.now().strftime("%Y년 %m월 %d일")}</p>
        </div>
    </div>
"""

    def _render_support_programs(self, support_programs: list[dict[str, Any]]) -> str:
        """정부지원사업 섹션"""
        if not support_programs:
            return ""

        programs_rows = ""
        for idx, program in enumerate(support_programs[:10]):  # 상위 10개
            program_name = program.get("program_name", "")
            category = program.get("category", "")
            support_amount = program.get("support_amount", "")
            application_end_date = program.get("application_end_date", "")
            days_until_deadline = program.get("days_until_deadline")
            managing_org = program.get("managing_org", "")

            # D-day 뱃지
            dday_badge = ""
            if days_until_deadline is not None:
                if days_until_deadline <= 7:
                    badge_class = "danger"
                elif days_until_deadline <= 30:
                    badge_class = "warning"
                else:
                    badge_class = "info"

                dday_badge = f'<span class="badge {badge_class}">D-{days_until_deadline}</span>'

            programs_rows += f"""
                <tr style="background: {'#f9fafb' if idx % 2 == 0 else 'white'};">
                    <td><strong>{program_name}</strong><br/><small style="color: #6b7280;">{category}</small></td>
                    <td style="text-align: right; font-weight: 600; color: #667eea;">{support_amount}</td>
                    <td style="text-align: center;">{application_end_date}<br/>{dday_badge}</td>
                    <td style="font-size: 12px; color: #6b7280;">{managing_org}</td>
                </tr>
"""

        return f"""
    <div class="section">
        <h2>7. 정부지원사업</h2>
        <p style="font-size: 16px; margin-bottom: 20px;">신청 가능한 지원사업 <strong style="color: #667eea; font-size: 20px;">{len(support_programs)}건</strong></p>

        <table style="border: 1px solid #e5e7eb;">
            <tr style="background: #667eea; color: white;">
                <th>사업명</th>
                <th style="text-align: right;">지원금액</th>
                <th style="text-align: center;">신청 마감</th>
                <th>주관기관</th>
            </tr>
            {programs_rows}
        </table>

        <div class="card" style="margin-top: 20px; background: linear-gradient(135deg, #3b82f610, #2563eb10); border-left: 4px solid #3b82f6;">
            <h4 style="color: #3b82f6;">📢 안내</h4>
            <p style="font-size: 13px; line-height: 1.8;">
                각 지원사업은 신청 자격 및 조건이 상이합니다. 반드시 주관기관 홈페이지를 확인하시고,<br/>
                필요 서류를 미리 준비하여 마감일 전에 신청하시기 바랍니다.
            </p>
        </div>

        <div class="footer">
            <p>SpotPick AI 창업 분석 리포트 | {datetime.now().strftime("%Y년 %m월 %d일")}</p>
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
