"""
PDF 리포트 생성 서비스 - McKinsey 컨설팅 보고서 스타일
Playwright 기반 HTML→PDF 변환 / SVG 인포그래픽 / 전문 데이터 시각화
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None  # type: ignore[assignment]

# ─── Color Palette (McKinsey-inspired) ────────────────────────────────────────
NAVY = "#1B2A4A"
BLUE = "#2563EB"
LIGHT_BLUE = "#3B82F6"
TEAL = "#0D9488"
CORAL = "#F97316"
GREEN = "#059669"
RED = "#DC2626"
GOLD = "#D97706"
GRAY_900 = "#111827"
GRAY_700 = "#374151"
GRAY_500 = "#6B7280"
GRAY_300 = "#D1D5DB"
GRAY_100 = "#F3F4F6"
WHITE = "#FFFFFF"

CHART_COLORS = ["#2563EB", "#7C3AED", "#0D9488", "#F97316", "#DC2626", "#D97706"]


class PDFService:
    """PDF 리포트 생성 서비스 - McKinsey 컨설팅 보고서 품질"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def generate_report_pdf(
        self,
        conversation_data: dict[str, Any],
        industry_name: str = "카페",
    ) -> bytes:
        if async_playwright is None:
            raise RuntimeError("playwright 미설치")

        html = self._build_html(conversation_data, industry_name)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.set_content(html, wait_until="networkidle")
                pdf_bytes = await page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
                )
                return pdf_bytes
            finally:
                await browser.close()

    # ═══════════════════════════════════════════════════════════════════════════
    # SVG Chart Helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _svg_donut(self, segments: list[dict], size: int = 180, hole: float = 0.6) -> str:
        """SVG 도넛 차트. segments: [{value, label, color}]"""
        total = sum(s["value"] for s in segments) or 1
        r = size / 2 - 5
        cx = cy = size / 2
        inner_r = r * hole
        paths = []
        start_angle = -90

        for seg in segments:
            pct = seg["value"] / total
            end_angle = start_angle + pct * 360
            large = 1 if pct > 0.5 else 0

            sr = math.radians(start_angle)
            er = math.radians(end_angle)

            x1 = cx + r * math.cos(sr)
            y1 = cy + r * math.sin(sr)
            x2 = cx + r * math.cos(er)
            y2 = cy + r * math.sin(er)
            x3 = cx + inner_r * math.cos(er)
            y3 = cy + inner_r * math.sin(er)
            x4 = cx + inner_r * math.cos(sr)
            y4 = cy + inner_r * math.sin(sr)

            d = (
                f"M {x1:.1f} {y1:.1f} "
                f"A {r:.1f} {r:.1f} 0 {large} 1 {x2:.1f} {y2:.1f} "
                f"L {x3:.1f} {y3:.1f} "
                f"A {inner_r:.1f} {inner_r:.1f} 0 {large} 0 {x4:.1f} {y4:.1f} Z"
            )
            paths.append(f'<path d="{d}" fill="{seg.get("color", BLUE)}" />')
            start_angle = end_angle

        return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">{"".join(paths)}</svg>'

    def _svg_radar(self, categories: list[dict], size: int = 220) -> str:
        """SVG 레이더(스파이더) 차트. categories: [{name, score, max_score}]"""
        n = len(categories)
        if n < 3:
            return ""
        cx = cy = size / 2
        r = size / 2 - 30
        angle_step = 360 / n

        # Grid lines
        grid_lines = ""
        for level in [0.25, 0.5, 0.75, 1.0]:
            pts = []
            for i in range(n):
                a = math.radians(-90 + i * angle_step)
                pts.append(f"{cx + r * level * math.cos(a):.1f},{cy + r * level * math.sin(a):.1f}")
            grid_lines += f'<polygon points="{" ".join(pts)}" fill="none" stroke="{GRAY_300}" stroke-width="0.5" />'

        # Axis lines
        axes = ""
        for i in range(n):
            a = math.radians(-90 + i * angle_step)
            axes += f'<line x1="{cx}" y1="{cy}" x2="{cx + r * math.cos(a):.1f}" y2="{cy + r * math.sin(a):.1f}" stroke="{GRAY_300}" stroke-width="0.5" />'

        # Data polygon
        data_pts = []
        for i, cat in enumerate(categories):
            score = cat.get("score", 0)
            max_s = cat.get("max_score", 100)
            ratio = min(score / max_s, 1.0) if max_s > 0 else 0
            a = math.radians(-90 + i * angle_step)
            data_pts.append(f"{cx + r * ratio * math.cos(a):.1f},{cy + r * ratio * math.sin(a):.1f}")

        data_poly = f'<polygon points="{" ".join(data_pts)}" fill="{BLUE}30" stroke="{BLUE}" stroke-width="2" />'

        # Data points + labels
        dots_labels = ""
        for i, cat in enumerate(categories):
            score = cat.get("score", 0)
            max_s = cat.get("max_score", 100)
            ratio = min(score / max_s, 1.0) if max_s > 0 else 0
            a = math.radians(-90 + i * angle_step)

            dx = cx + r * ratio * math.cos(a)
            dy = cy + r * ratio * math.sin(a)
            dots_labels += f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="3" fill="{BLUE}" />'

            # Label position (outside)
            lx = cx + (r + 18) * math.cos(a)
            ly = cy + (r + 18) * math.sin(a)
            anchor = "middle"
            if math.cos(a) > 0.3:
                anchor = "start"
            elif math.cos(a) < -0.3:
                anchor = "end"
            dots_labels += f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="10" fill="{GRAY_700}" text-anchor="{anchor}" dominant-baseline="central">{cat.get("name", "")} {score:.0f}</text>'

        return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">{grid_lines}{axes}{data_poly}{dots_labels}</svg>'

    def _svg_horizontal_bars(self, items: list[dict], width: int = 480, bar_h: int = 24, gap: int = 8, colors: list[str] = None) -> str:
        """SVG 수평 바 차트. items: [{name, value, extra?}]"""
        if not items:
            return ""
        colors = colors or CHART_COLORS
        max_val = max((it["value"] for it in items), default=1) or 1
        label_w = 100
        value_w = 60
        chart_w = width - label_w - value_w - 10
        h = len(items) * (bar_h + gap) + 10

        bars = ""
        for i, it in enumerate(items):
            y = i * (bar_h + gap) + 5
            w = (it["value"] / max_val) * chart_w
            c = colors[i % len(colors)]
            name = it.get("name", "")
            val = it["value"]
            extra = it.get("extra", "")

            bars += f'<text x="{label_w - 8}" y="{y + bar_h / 2 + 1}" font-size="11" fill="{GRAY_700}" text-anchor="end" dominant-baseline="central">{name}</text>'
            bars += f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="3" fill="{c}" />'
            bars += f'<text x="{label_w + w + 6}" y="{y + bar_h / 2 + 1}" font-size="11" fill="{GRAY_700}" dominant-baseline="central" font-weight="600">{val:,.1f}{extra}</text>'

        return f'<svg width="{width}" height="{h}" viewBox="0 0 {width} {h}" xmlns="http://www.w3.org/2000/svg">{bars}</svg>'

    def _svg_waterfall(self, items: list[dict], width: int = 500, height: int = 220) -> str:
        """SVG 워터폴 차트. items: [{label, value, type: 'add'|'subtract'|'total'}]"""
        if not items:
            return ""
        n = len(items)
        pad_x, pad_y = 60, 30
        chart_w = width - pad_x - 20
        chart_h = height - pad_y - 30
        bar_w = chart_w / n * 0.6
        gap = chart_w / n * 0.4

        max_val = max(abs(it["value"]) for it in items) * 1.2 or 1

        svg = ""
        # Baseline
        baseline_y = pad_y + chart_h * 0.1
        svg += f'<line x1="{pad_x}" y1="{baseline_y + chart_h * 0.45}" x2="{width - 20}" y2="{baseline_y + chart_h * 0.45}" stroke="{GRAY_300}" stroke-width="0.5" stroke-dasharray="3,3" />'

        running = 0
        for i, it in enumerate(items):
            x = pad_x + i * (bar_w + gap) + gap / 2
            val = it["value"]
            t = it.get("type", "add")
            label = it.get("label", "")

            if t == "total":
                bar_top = baseline_y + chart_h * 0.45 - (val / max_val * chart_h * 0.4)
                bar_height = val / max_val * chart_h * 0.4
                color = NAVY
                running = val
            elif t == "subtract":
                prev_top = baseline_y + chart_h * 0.45 - (running / max_val * chart_h * 0.4)
                bar_height = val / max_val * chart_h * 0.4
                bar_top = prev_top
                color = RED
                running -= val
            else:  # add
                bar_height = val / max_val * chart_h * 0.4
                prev_top = baseline_y + chart_h * 0.45 - (running / max_val * chart_h * 0.4)
                bar_top = prev_top - bar_height
                color = BLUE
                running += val

            svg += f'<rect x="{x:.1f}" y="{bar_top:.1f}" width="{bar_w:.1f}" height="{max(bar_height, 2):.1f}" rx="2" fill="{color}" />'
            # Value label
            svg += f'<text x="{x + bar_w / 2:.1f}" y="{bar_top - 5:.1f}" font-size="9" fill="{GRAY_700}" text-anchor="middle" font-weight="600">{self._format_currency(val)}</text>'
            # Bottom label
            svg += f'<text x="{x + bar_w / 2:.1f}" y="{baseline_y + chart_h * 0.45 + 15:.1f}" font-size="9" fill="{GRAY_500}" text-anchor="middle">{label}</text>'

        return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{svg}</svg>'

    def _svg_gauge(self, value: float, max_val: float = 100, size: int = 120, label: str = "") -> str:
        """SVG 반원 게이지 차트"""
        pct = min(value / max_val, 1.0) if max_val > 0 else 0
        r = size / 2 - 10
        cx = cy = size / 2
        # Arc from 180 to 0 degrees (bottom half)
        sa = math.pi  # 180 deg
        ea = math.pi - pct * math.pi  # going to 0
        x1 = cx + r * math.cos(sa)
        y1 = cy - r * math.sin(sa)
        x2 = cx + r * math.cos(ea)
        y2 = cy - r * math.sin(ea)
        large = 1 if pct > 0.5 else 0

        color = GREEN if pct >= 0.7 else (GOLD if pct >= 0.4 else RED)

        return f'''<svg width="{size}" height="{size * 0.65}" viewBox="0 0 {size} {size * 0.65}" xmlns="http://www.w3.org/2000/svg">
            <path d="M {x1:.1f} {y1:.1f} A {r:.1f} {r:.1f} 0 0 1 {cx + r:.1f} {cy:.1f}" fill="none" stroke="{GRAY_300}" stroke-width="10" stroke-linecap="round" />
            <path d="M {x1:.1f} {y1:.1f} A {r:.1f} {r:.1f} 0 {large} 1 {x2:.1f} {y2:.1f}" fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round" />
            <text x="{cx}" y="{cy - 8}" font-size="20" font-weight="700" fill="{NAVY}" text-anchor="middle">{value:.1f}%</text>
            <text x="{cx}" y="{cy + 8}" font-size="9" fill="{GRAY_500}" text-anchor="middle">{label}</text>
        </svg>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Formatting Helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _fmt(self, value: float) -> str:
        """통화 포맷 (만원)"""
        if abs(value) >= 100000000:
            return f"{value / 100000000:.1f}억원"
        if abs(value) >= 10000:
            return f"{int(value / 10000):,}만원"
        return f"{int(value):,}원"

    def _format_currency(self, value: float) -> str:
        return self._fmt(value)

    def _kpi_card(self, label: str, value: str, sub: str = "", color: str = BLUE) -> str:
        return f'''<div style="flex:1; background:{WHITE}; border-radius:8px; padding:18px 16px; text-align:center; border-top:3px solid {color};">
            <div style="font-size:11px; color:{GRAY_500}; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px;">{label}</div>
            <div style="font-size:26px; font-weight:800; color:{NAVY}; line-height:1.2;">{value}</div>
            <div style="font-size:10px; color:{GRAY_500}; margin-top:4px;">{sub}</div>
        </div>'''

    def _insight_box(self, text: str) -> str:
        return f'''<div style="margin:16px 0; padding:14px 18px; background:linear-gradient(135deg, #EFF6FF, #DBEAFE); border-left:4px solid {BLUE}; border-radius:0 6px 6px 0;">
            <div style="font-size:10px; font-weight:700; color:{BLUE}; text-transform:uppercase; letter-spacing:1px; margin-bottom:4px;">KEY INSIGHT</div>
            <div style="font-size:12px; color:{NAVY}; line-height:1.6;">{text}</div>
        </div>'''

    def _section_header(self, num: int, title: str) -> str:
        return f'''<div style="margin-bottom:24px;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:8px;">
                <div style="width:36px; height:36px; background:{NAVY}; color:{WHITE}; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:700;">{num}</div>
                <h2 style="font-size:26px; font-weight:700; color:{NAVY}; margin:0;">{title}</h2>
            </div>
            <div style="height:3px; background:linear-gradient(90deg, {BLUE}, {NAVY}00); border-radius:2px;"></div>
        </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Main HTML Builder
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_html(self, data: dict[str, Any], industry_name: str) -> str:
        now = datetime.now().strftime("%Y년 %m월 %d일")
        recs = data.get("recommendations", [])
        charts = data.get("charts", [])
        comp = data.get("competitive")
        sim = data.get("simulation")
        ctx = data.get("context", {})
        timeline = data.get("timeline")
        trend = data.get("trend")
        programs = data.get("support_programs", [])

        sections = []
        sections.append(self._page_cover(industry_name, now, ctx, recs, sim))
        sections.append(self._page_exec_summary(recs, sim, comp, ctx))

        sec_num = 1
        if charts or comp:
            sections.append(self._page_market(charts, comp, sec_num))
            sec_num += 1
        if recs:
            sections.append(self._page_location(recs, sec_num))
            sec_num += 1
        if sim:
            sections.append(self._page_simulation(sim, sec_num))
            sec_num += 1
        if comp:
            sections.append(self._page_competitive(comp, sec_num))
            sec_num += 1
        if timeline:
            sections.append(self._page_timeline(timeline, sec_num))
            sec_num += 1
        if trend:
            sections.append(self._page_trend(trend, sec_num))
            sec_num += 1
        if programs:
            sections.append(self._page_support(programs, sec_num))
            sec_num += 1

        sections.append(self._page_disclaimer(now))

        body = "\n".join(sections)

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>SpotPick 창업 분석 리포트</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
@page {{ size: A4; margin: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; color:{GRAY_900}; line-height:1.5; font-size:12px; }}
.page {{ width:210mm; min-height:297mm; padding:28mm 22mm 20mm 22mm; page-break-after:always; position:relative; }}
.page-footer {{ position:absolute; bottom:12mm; left:22mm; right:22mm; font-size:8px; color:{GRAY_500}; display:flex; justify-content:space-between; border-top:1px solid {GRAY_300}; padding-top:6px; }}
table {{ width:100%; border-collapse:collapse; font-size:11px; }}
th {{ background:{NAVY}; color:{WHITE}; padding:8px 10px; text-align:left; font-weight:600; font-size:10px; text-transform:uppercase; letter-spacing:0.3px; }}
td {{ padding:8px 10px; border-bottom:1px solid {GRAY_300}; }}
tr:nth-child(even) {{ background:#F8FAFC; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:10px; font-size:10px; font-weight:600; }}
.badge-blue {{ background:#DBEAFE; color:#1E40AF; }}
.badge-green {{ background:#D1FAE5; color:#065F46; }}
.badge-red {{ background:#FEE2E2; color:#991B1B; }}
.badge-yellow {{ background:#FEF3C7; color:#92400E; }}
svg {{ display:block; }}
</style>
</head>
<body>
{body}
</body>
</html>"""

    def _footer(self, page_label: str = "") -> str:
        now = datetime.now().strftime("%Y.%m.%d")
        return f'<div class="page-footer"><span>SpotPick AI 창업 분석 리포트</span><span>Confidential | {now}{" | " + page_label if page_label else ""}</span></div>'

    # ═══════════════════════════════════════════════════════════════════════════
    # Pages
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_cover(self, industry: str, date: str, ctx: dict, recs: list, sim: dict) -> str:
        district = ctx.get("district", recs[0].get("district_name", "서울") if recs else "서울")
        budget = ctx.get("budget", "")
        target = ctx.get("target", "")

        meta_items = [f'<div style="font-size:14px; color:#CBD5E1;">{date} 생성</div>']
        if budget:
            meta_items.append(f'<div style="font-size:14px; color:#CBD5E1;">예산: {budget}</div>')
        if target:
            meta_items.append(f'<div style="font-size:14px; color:#CBD5E1;">타겟: {target}</div>')
        meta = '<div style="margin-top:8px;">'.join(meta_items) + '</div>' * (len(meta_items) - 1) if meta_items else ""

        return f'''<div style="width:210mm; min-height:297mm; background:linear-gradient(160deg, {NAVY} 0%, #0F172A 50%, #1E293B 100%); padding:0; page-break-after:always; position:relative; -webkit-print-color-adjust:exact; print-color-adjust:exact;">
        <div style="position:absolute; top:0; right:0; width:50%; height:100%; background:linear-gradient(135deg, {BLUE}15, {BLUE}05); clip-path:polygon(30% 0, 100% 0, 100% 100%, 0% 100%);"></div>
        <div style="position:relative; z-index:1; padding:60mm 30mm 30mm 30mm;">
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:50px;">
                <div style="width:48px; height:48px; background:{BLUE}; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:20px; font-weight:800; color:{WHITE};">SP</div>
                <span style="font-size:16px; font-weight:600; color:{WHITE}; letter-spacing:2px;">SPOTPICK</span>
            </div>
            <div style="font-size:13px; color:{BLUE}; font-weight:600; letter-spacing:3px; text-transform:uppercase; margin-bottom:16px;">AI-Powered Market Analysis</div>
            <h1 style="font-size:42px; font-weight:800; color:{WHITE}; line-height:1.2; margin-bottom:12px;">{industry} 창업<br/>분석 리포트</h1>
            <div style="font-size:20px; color:#94A3B8; font-weight:300; margin-bottom:40px;">{district} 상권 심층 분석</div>
            <div style="width:60px; height:3px; background:{BLUE}; border-radius:2px; margin-bottom:30px;"></div>
            {meta}
        </div>
        <div style="position:absolute; bottom:25mm; left:30mm; right:30mm; z-index:1;">
            <div style="border-top:1px solid #334155; padding-top:12px; display:flex; justify-content:space-between;">
                <span style="font-size:10px; color:#64748B;">AI가 골라주는 나만의 창업 자리</span>
                <span style="font-size:10px; color:#64748B;">Confidential</span>
            </div>
        </div>
    </div>'''

    def _page_exec_summary(self, recs: list, sim: dict, comp: dict, ctx: dict) -> str:
        # Extract key metrics
        top_district = recs[0].get("district_name", "-") if recs else "-"
        success_prob = recs[0].get("success_probability", 0) if recs else 0
        monthly_sales = 0
        monthly_profit = 0
        break_even = 0
        total_invest_min = 0
        store_count = 0
        survival_rate = 0

        if sim:
            rev = sim.get("revenue", {})
            monthly_sales = rev.get("monthly_sales_per_store", 0)
            be = sim.get("break_even", {})
            monthly_profit = be.get("monthly_net_profit", 0)
            break_even = be.get("break_even_months_min", 0)
            sc = sim.get("startup_cost", {})
            total_invest_min = sc.get("total_min", 0)
            competition = sim.get("competition", {})
            store_count = competition.get("store_count", 0)
            survival_rate = competition.get("survival_rate", 0)

        total_comp = comp.get("total_nearby_cafes", 0) if comp else store_count

        # KPI cards
        kpi1 = self._kpi_card("추천 1위 상권", top_district, f"성공확률 {success_prob:.0f}%", BLUE)
        kpi2 = self._kpi_card("예상 월매출", self._fmt(monthly_sales), f"순이익 {self._fmt(monthly_profit)}", GREEN)
        kpi3 = self._kpi_card("손익분기점", f"{break_even:.0f}개월", f"초기투자 {self._fmt(total_invest_min)}", CORAL)
        kpi4 = self._kpi_card("경쟁 매장", f"{total_comp}개", f"생존율 {survival_rate:.0f}%", RED if total_comp > 50 else GOLD)

        # Success gauge
        gauge = self._svg_gauge(success_prob, 100, 140, "성공 확률")

        # Summary bullets
        bullets = []
        if recs:
            names = [r.get("district_name", "") for r in recs[:3]]
            bullets.append(f'추천 상권 TOP 3: <strong>{", ".join(names)}</strong>')
        if monthly_sales:
            bullets.append(f'월 예상 매출 <strong>{self._fmt(monthly_sales)}</strong>, 순이익률 <strong>{sim.get("break_even", {}).get("net_profit_margin", 0):.1f}%</strong>')
        if break_even:
            bullets.append(f'초기 투자금 회수까지 약 <strong>{break_even:.0f}개월</strong> 소요 예상')
        if total_comp:
            bullets.append(f'주변 경쟁 매장 <strong>{total_comp}개</strong> — 차별화 전략 필수')

        bullet_html = "".join(f'<div style="padding:6px 0; border-bottom:1px solid {GRAY_300}; font-size:12px; color:{GRAY_700};">• {b}</div>' for b in bullets)

        return f'''<div class="page">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:20px;">
            <div style="width:32px; height:32px; background:{BLUE}; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:800; color:{WHITE};">SP</div>
            <span style="font-size:12px; font-weight:600; color:{GRAY_500}; letter-spacing:2px;">EXECUTIVE SUMMARY</span>
        </div>
        <h2 style="font-size:28px; font-weight:800; color:{NAVY}; margin-bottom:6px;">핵심 요약</h2>
        <div style="height:3px; width:60px; background:{BLUE}; border-radius:2px; margin-bottom:24px;"></div>

        <div style="display:flex; gap:12px; margin-bottom:24px;">
            {kpi1}{kpi2}{kpi3}{kpi4}
        </div>

        <div style="display:flex; gap:24px; margin-bottom:20px;">
            <div style="flex:1;">
                <h3 style="font-size:14px; font-weight:700; color:{NAVY}; margin-bottom:12px;">주요 분석 결과</h3>
                {bullet_html}
            </div>
            <div style="width:160px; text-align:center; padding-top:10px;">
                {gauge}
            </div>
        </div>

        {self._insight_box(f"{top_district} 상권은 {success_prob:.0f}%의 성공 확률로 가장 유망하며, 월 {self._fmt(monthly_profit)} 순이익이 예상됩니다. 초기 투자 대비 {break_even:.0f}개월 내 회수가 가능한 안정적 투자처입니다.")}

        <div style="margin-top:20px; padding:16px; background:{GRAY_100}; border-radius:8px;">
            <div style="font-size:10px; font-weight:700; color:{GRAY_500}; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px;">분석 범위</div>
            <div style="display:flex; gap:20px; font-size:11px; color:{GRAY_700};">
                <span>📍 {ctx.get("district", "서울 전역")}</span>
                <span>💰 {ctx.get("budget", "미지정")}</span>
                <span>👥 {ctx.get("target", "전 연령")}</span>
                <span>📅 {datetime.now().strftime("%Y.%m.%d")} 기준</span>
            </div>
        </div>
        {self._footer()}
    </div>'''

    def _page_market(self, charts: list, comp: dict, num: int) -> str:
        header = self._section_header(num, "시장 분석")

        # Build charts
        charts_html = ""
        for chart in charts[:3]:
            title = chart.get("title", "")
            chart_data = chart.get("data", [])
            chart_type = chart.get("type", "")

            if not chart_data:
                continue

            if chart_type == "age":
                # Donut chart for age
                segments = []
                for i, d in enumerate(chart_data):
                    segments.append({"value": d.get("value", 0), "label": d.get("name", ""), "color": CHART_COLORS[i % len(CHART_COLORS)]})
                donut = self._svg_donut(segments, 160)
                legend = "".join(f'<div style="display:flex; align-items:center; gap:6px; margin-bottom:4px;"><div style="width:10px; height:10px; border-radius:2px; background:{CHART_COLORS[i % len(CHART_COLORS)]};"></div><span style="font-size:10px; color:{GRAY_700};">{d.get("name", "")} {d.get("value", 0)}%</span></div>' for i, d in enumerate(chart_data))
                charts_html += f'''<div style="margin-bottom:20px;">
                    <h3 style="font-size:15px; font-weight:700; color:{NAVY}; margin-bottom:12px;">{title}</h3>
                    <div style="display:flex; align-items:center; gap:24px;">
                        <div>{donut}</div>
                        <div>{legend}</div>
                    </div>
                </div>'''
            else:
                # Horizontal bar chart
                items = [{"name": d.get("name", ""), "value": d.get("value", 0), "extra": f' (매출: {self._fmt(d["sales"])})' if d.get("sales") else ""} for d in chart_data]
                bar_svg = self._svg_horizontal_bars(items, width=480, bar_h=22)
                charts_html += f'''<div style="margin-bottom:20px;">
                    <h3 style="font-size:15px; font-weight:700; color:{NAVY}; margin-bottom:12px;">{title}</h3>
                    {bar_svg}
                </div>'''

        # Competitive summary
        comp_summary = ""
        if comp:
            total = comp.get("total_nearby_cafes", 0)
            comp_summary = f'''<div style="padding:12px 16px; background:{GRAY_100}; border-radius:6px; margin-top:12px;">
                <span style="font-size:11px; color:{GRAY_500};">주변 경쟁 매장</span>
                <span style="font-size:22px; font-weight:800; color:{NAVY}; margin-left:8px;">{total}개</span>
            </div>'''

        # Insight
        time_chart = next((c for c in charts if c.get("type") == "time"), None)
        peak_info = ""
        if time_chart and time_chart.get("highlight"):
            peak_info = time_chart["highlight"]
        elif time_chart and time_chart.get("data"):
            peak = max(time_chart["data"], key=lambda x: x.get("value", 0))
            peak_info = f'피크 시간대: {peak.get("name", "")} ({peak.get("value", 0)}%)'

        age_chart = next((c for c in charts if c.get("type") == "age"), None)
        age_info = ""
        if age_chart and age_chart.get("data"):
            top_age = max(age_chart["data"], key=lambda x: x.get("value", 0))
            age_info = f'주 고객층은 {top_age.get("name", "")} ({top_age.get("value", 0)}%)'

        insight_text = " / ".join(filter(None, [peak_info, age_info]))
        insight = self._insight_box(insight_text) if insight_text else ""

        return f'''<div class="page">
        {header}
        {charts_html}
        {comp_summary}
        {insight}
        {self._footer()}
    </div>'''

    def _page_location(self, recs: list, num: int) -> str:
        header = self._section_header(num, "입지 분석")
        cards = ""

        for rec in recs[:3]:
            rank = rec.get("rank", 0)
            name = rec.get("district_name", "")
            prob = rec.get("success_probability", 0)
            sales = rec.get("monthly_sales", 0)
            stores = rec.get("store_count", 0)
            survival = rec.get("survival_rate", 1.0)
            closed = rec.get("closed_ratio", 1 - survival)
            traffic = rec.get("foot_traffic_total", 0)
            scorecard = rec.get("scorecard")

            prob_color = GREEN if prob >= 70 else (GOLD if prob >= 50 else RED)

            # Radar chart for scorecard
            radar_html = ""
            if scorecard:
                cats = scorecard.get("categories", [])
                if isinstance(cats, list) and len(cats) >= 3:
                    radar_data = [{"name": c.get("name", ""), "score": c.get("score", 0), "max_score": 100} for c in cats]
                    radar_html = f'<div style="text-align:center;">{self._svg_radar(radar_data, 190)}<div style="font-size:10px; color:{GRAY_500};">종합 {scorecard.get("total_score", 0):.1f}점 | 상위 {scorecard.get("percentile", 0):.1f}%</div></div>'

            metrics = f'''<div style="display:flex; gap:8px; margin:10px 0;">
                <div style="flex:1; background:{GRAY_100}; padding:8px; border-radius:4px; text-align:center;">
                    <div style="font-size:9px; color:{GRAY_500};">월매출</div>
                    <div style="font-size:14px; font-weight:700; color:{NAVY};">{self._fmt(sales)}</div>
                </div>
                <div style="flex:1; background:{GRAY_100}; padding:8px; border-radius:4px; text-align:center;">
                    <div style="font-size:9px; color:{GRAY_500};">매장수</div>
                    <div style="font-size:14px; font-weight:700; color:{NAVY};">{stores}개</div>
                </div>
                <div style="flex:1; background:{GRAY_100}; padding:8px; border-radius:4px; text-align:center;">
                    <div style="font-size:9px; color:{GRAY_500};">폐업률</div>
                    <div style="font-size:14px; font-weight:700; color:{RED if closed > 0.2 else NAVY};">{closed*100:.1f}%</div>
                </div>
                <div style="flex:1; background:{GRAY_100}; padding:8px; border-radius:4px; text-align:center;">
                    <div style="font-size:9px; color:{GRAY_500};">유동인구</div>
                    <div style="font-size:14px; font-weight:700; color:{NAVY};">{traffic:,}명</div>
                </div>
            </div>'''

            card_content = f'''<div style="display:flex; gap:16px; align-items:flex-start;">
                <div style="flex:1;">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
                        <div style="width:28px; height:28px; background:{prob_color}; color:{WHITE}; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700;">#{rank}</div>
                        <span style="font-size:18px; font-weight:700; color:{NAVY};">{name}</span>
                        <span class="badge badge-{"green" if prob >= 70 else "yellow" if prob >= 50 else "red"}" style="font-size:11px;">{prob:.1f}%</span>
                    </div>
                    {metrics}
                </div>
                {f'<div style="width:200px; flex-shrink:0;">{radar_html}</div>' if radar_html else ''}
            </div>'''

            cards += f'<div style="border:1px solid {GRAY_300}; border-radius:8px; padding:16px; margin-bottom:12px;">{card_content}</div>'

        # Insight
        if recs:
            top = recs[0]
            insight = self._insight_box(f'{top.get("district_name", "")}이(가) 종합 점수 기준 최우수 입지로 분석됩니다. 월 {self._fmt(top.get("monthly_sales", 0))} 매출에 유동인구 {top.get("foot_traffic_total", 0):,}명 규모입니다.')
        else:
            insight = ""

        return f'''<div class="page">
        {header}
        {cards}
        {insight}
        {self._footer()}
    </div>'''

    def _page_simulation(self, sim: dict, num: int) -> str:
        header = self._section_header(num, "창업 시뮬레이션")
        district = sim.get("district_name", "")

        rev = sim.get("revenue", {})
        monthly_sales = rev.get("monthly_sales_per_store", 0)
        daily_sales = rev.get("daily_sales", 0)
        avg_ticket = rev.get("avg_ticket", 0)
        pessimistic = rev.get("pessimistic", 0)
        optimistic = rev.get("optimistic", 0)
        peak_time = rev.get("peak_time", "")

        sc = sim.get("startup_cost", {})
        total_min = sc.get("total_min", 0)
        total_max = sc.get("total_max", 0)
        deposit = sc.get("deposit", 0)
        interior = sc.get("interior", 0)
        equipment_min = sc.get("equipment_min", 0)
        area = sc.get("area_pyeong", 0)

        op = sim.get("operating_cost", {})
        rent = op.get("rent", 0)
        labor = op.get("labor", 0)
        cogs = op.get("cogs", op.get("materials", 0))
        utilities = op.get("utilities", 0)
        other = op.get("other", 0)
        total_op = op.get("total", rent + labor + cogs + utilities + other)

        be = sim.get("break_even", {})
        be_min = be.get("break_even_months_min", 0)
        be_max = be.get("break_even_months_max", 0)
        net_profit = be.get("monthly_net_profit", monthly_sales - total_op)
        margin = be.get("net_profit_margin", (net_profit / monthly_sales * 100) if monthly_sales else 0)

        # Waterfall P&L chart (compact)
        waterfall_items = [
            {"label": "매출", "value": monthly_sales, "type": "total"},
            {"label": "임대료", "value": rent, "type": "subtract"},
            {"label": "인건비", "value": labor, "type": "subtract"},
            {"label": "원재료", "value": cogs, "type": "subtract"},
            {"label": "기타", "value": utilities + other, "type": "subtract"},
            {"label": "순이익", "value": net_profit, "type": "total"},
        ]
        waterfall = self._svg_waterfall(waterfall_items, 480, 155)

        # Startup cost donut (smaller)
        startup_segs = [
            {"value": deposit, "label": "보증금", "color": CHART_COLORS[0]},
            {"value": interior, "label": "인테리어", "color": CHART_COLORS[1]},
            {"value": equipment_min, "label": "설비", "color": CHART_COLORS[2]},
            {"value": max(total_min - deposit - interior - equipment_min, 0), "label": "기타", "color": CHART_COLORS[3]},
        ]
        startup_donut = self._svg_donut([s for s in startup_segs if s["value"] > 0], 110)
        startup_legend = "".join(f'<div style="display:flex; align-items:center; gap:4px; margin-bottom:2px;"><div style="width:8px; height:8px; border-radius:2px; background:{s["color"]};"></div><span style="font-size:9px;">{s["label"]} {self._fmt(s["value"])}</span></div>' for s in startup_segs if s["value"] > 0)

        # Scenario comparison (compact)
        scenario = f'''<div style="display:flex; gap:6px; margin:8px 0;">
            <div style="flex:1; padding:8px; background:#FEF2F2; border-radius:6px; text-align:center; border:1px solid #FECACA;">
                <div style="font-size:8px; color:{RED}; font-weight:600;">비관적</div>
                <div style="font-size:15px; font-weight:800; color:{RED};">{self._fmt(pessimistic)}</div>
            </div>
            <div style="flex:1; padding:8px; background:#EFF6FF; border-radius:6px; text-align:center; border:1px solid #BFDBFE;">
                <div style="font-size:8px; color:{BLUE}; font-weight:600;">기본</div>
                <div style="font-size:15px; font-weight:800; color:{BLUE};">{self._fmt(monthly_sales)}</div>
            </div>
            <div style="flex:1; padding:8px; background:#F0FDF4; border-radius:6px; text-align:center; border:1px solid #BBF7D0;">
                <div style="font-size:8px; color:{GREEN}; font-weight:600;">낙관적</div>
                <div style="font-size:15px; font-weight:800; color:{GREEN};">{self._fmt(optimistic)}</div>
            </div>
        </div>'''

        # Break-even gauge (smaller)
        be_gauge = self._svg_gauge(margin, 100, 100, "순이익률")

        # Menu costs (compact table)
        menu_html = ""
        mc = sim.get("menu_costs", {})
        menu_items = mc.get("menu_costs", mc.get("items", []))
        if menu_items:
            rows = ""
            for it in menu_items:
                n = it.get("menu", it.get("name", ""))
                sp = it.get("selling_price", 0)
                cost = it.get("cost", 0)
                mr = it.get("margin_rate", it.get("margin", 0))
                mr_color = GREEN if mr >= 70 else (GOLD if mr >= 50 else RED)
                rows += f'<tr><td style="padding:4px 6px;">{n}</td><td style="text-align:right; padding:4px 6px;">{int(sp):,}원</td><td style="text-align:right; padding:4px 6px;">{int(cost):,}원</td><td style="text-align:right; font-weight:700; color:{mr_color}; padding:4px 6px;">{mr:.1f}%</td></tr>'
            avg_m = mc.get("avg_margin_rate", 0)
            menu_html = f'''<h3 style="font-size:12px; font-weight:700; color:{NAVY}; margin:10px 0 4px;">메뉴별 원가 분석</h3>
            <table style="font-size:10px;"><tr><th style="padding:4px 6px;">메뉴</th><th style="text-align:right; padding:4px 6px;">판매가</th><th style="text-align:right; padding:4px 6px;">원가</th><th style="text-align:right; padding:4px 6px;">마진율</th></tr>{rows}
            <tr style="background:{NAVY}08;"><td colspan="3" style="font-weight:700; padding:4px 6px;">평균 마진율</td><td style="text-align:right; font-weight:800; color:{BLUE}; padding:4px 6px;">{avg_m:.1f}%</td></tr></table>'''

        # Risk summary (inline compact)
        risks = sim.get("risk_summary", [])
        risk_html = ""
        if risks:
            items = " · ".join(f'⚠ {r}' for r in risks[:3])
            risk_html = f'<div style="padding:6px 10px; background:#FFFBEB; border:1px solid #FDE68A; border-radius:4px; margin-top:8px; font-size:9px; color:{GRAY_700};"><span style="font-weight:700; color:{GOLD};">RISK</span> {items}</div>'

        return f'''<div class="page">
        {header}
        <div style="font-size:11px; color:{GRAY_500}; margin-bottom:10px;">{district} 기준 예상 수치</div>

        <div style="display:flex; gap:14px; margin-bottom:10px;">
            <div style="flex:1;">
                <h3 style="font-size:12px; font-weight:700; color:{NAVY}; margin-bottom:6px;">월간 손익 구조 (Waterfall)</h3>
                {waterfall}
            </div>
            <div style="width:130px; text-align:center;">
                {be_gauge}
                <div style="margin-top:4px; font-size:10px; color:{NAVY}; font-weight:600;">BEP: {be_min:.0f}~{be_max:.0f}개월</div>
            </div>
        </div>

        <h3 style="font-size:12px; font-weight:700; color:{NAVY}; margin-bottom:4px;">시나리오별 매출 전망</h3>
        {scenario}

        <div style="display:flex; gap:14px; margin:8px 0;">
            <div style="flex:1;">
                <h3 style="font-size:12px; font-weight:700; color:{NAVY}; margin-bottom:6px;">초기 투자 비용</h3>
                <div style="display:flex; align-items:center; gap:10px;">
                    {startup_donut}
                    <div>{startup_legend}<div style="margin-top:4px; font-size:10px; font-weight:700; color:{NAVY};">총 {self._fmt(total_min)}~{self._fmt(total_max)}</div></div>
                </div>
            </div>
            <div style="flex:1;">
                <h3 style="font-size:12px; font-weight:700; color:{NAVY}; margin-bottom:6px;">월 운영 비용</h3>
                <table style="font-size:10px;">
                    <tr><td style="padding:3px 6px;">임대료</td><td style="text-align:right; font-weight:600; padding:3px 6px;">{self._fmt(rent)}</td></tr>
                    <tr><td style="padding:3px 6px;">인건비</td><td style="text-align:right; font-weight:600; padding:3px 6px;">{self._fmt(labor)}</td></tr>
                    <tr><td style="padding:3px 6px;">원재료비</td><td style="text-align:right; font-weight:600; padding:3px 6px;">{self._fmt(cogs)}</td></tr>
                    <tr><td style="padding:3px 6px;">공과금/기타</td><td style="text-align:right; font-weight:600; padding:3px 6px;">{self._fmt(utilities + other)}</td></tr>
                    <tr style="background:{NAVY}08;"><td style="font-weight:700; padding:3px 6px;">합계</td><td style="text-align:right; font-weight:800; color:{BLUE}; padding:3px 6px;">{self._fmt(total_op)}</td></tr>
                </table>
            </div>
        </div>

        {menu_html}
        {risk_html}
        {self._insight_box(f"월 순이익 {self._fmt(net_profit)} (마진율 {margin:.1f}%)으로, 초기 투자금 {self._fmt(total_min)} 기준 약 {be_min:.0f}개월 내 회수 가능합니다.")}
        {self._footer()}
    </div>'''

    def _page_competitive(self, comp: dict, num: int) -> str:
        header = self._section_header(num, "경쟁 분석")
        total = comp.get("total_nearby_cafes", comp.get("total_competitors", 0))
        cafe_types = comp.get("cafe_types", [])
        gaps = comp.get("market_gaps", [])
        strategies = comp.get("strategies", [])

        # Donut for cafe type distribution
        segments = [{"value": ct.get("count", 0), "label": self._translate_cafe_type(ct.get("type", "")), "color": CHART_COLORS[i % len(CHART_COLORS)]} for i, ct in enumerate(cafe_types)]
        donut = self._svg_donut(segments, 150)
        legend = "".join(f'<div style="display:flex; align-items:center; gap:5px; margin-bottom:3px;"><div style="width:8px; height:8px; border-radius:2px; background:{CHART_COLORS[i % len(CHART_COLORS)]};"></div><span style="font-size:10px;">{self._translate_cafe_type(ct.get("type", ""))} {ct.get("count", 0)}개 ({ct.get("ratio", 0):.0f}%)</span></div>' for i, ct in enumerate(cafe_types))

        # Table
        rows = ""
        for i, ct in enumerate(cafe_types):
            tn = self._translate_cafe_type(ct.get("type", ""))
            ex = ", ".join(ct.get("examples", [])[:3])
            rows += f'<tr><td>{tn}</td><td style="text-align:right;">{ct.get("count", 0)}개</td><td style="text-align:right; font-weight:600; color:{BLUE};">{ct.get("ratio", 0):.1f}%</td><td style="font-size:10px; color:{GRAY_500};">{ex}</td></tr>'

        # SWOT-style grid (opportunities & strategies)
        gap_items = ""
        for g in gaps:
            if isinstance(g, dict):
                score = g.get("opportunity_score", 0)
                color = GREEN if score >= 70 else GOLD
                gap_items += f'<div style="padding:8px; margin-bottom:6px; background:{WHITE}; border-radius:4px; border-left:3px solid {color};"><div style="font-size:11px; font-weight:600; color:{NAVY};">{g.get("gap_type", "")}</div><div style="font-size:10px; color:{GRAY_500};">{g.get("description", "")}</div><div style="font-size:9px; color:{color}; font-weight:600; margin-top:2px;">기회점수: {score}</div></div>'

        strat_items = ""
        for s in strategies:
            if isinstance(s, dict):
                p = s.get("priority", "")
                p_kr = {"high": "높음", "medium": "중간", "low": "낮음"}.get(p, p)
                p_color = RED if p == "high" else (GOLD if p == "medium" else BLUE)
                strat_items += f'<div style="padding:8px; margin-bottom:6px; background:{WHITE}; border-radius:4px; border-left:3px solid {p_color};"><div style="font-size:11px; font-weight:600; color:{NAVY};">{s.get("strategy", "")} <span style="font-size:9px; padding:1px 6px; background:{p_color}15; color:{p_color}; border-radius:8px;">{p_kr}</span></div><div style="font-size:10px; color:{GRAY_500};">{s.get("reason", "")}</div></div>'

        return f'''<div class="page">
        {header}
        <div style="display:flex; gap:20px; margin-bottom:16px;">
            <div style="flex:1;">
                <div style="font-size:12px; color:{GRAY_500}; margin-bottom:8px;">총 경쟁 매장</div>
                <div style="font-size:32px; font-weight:800; color:{NAVY}; margin-bottom:12px;">{total}<span style="font-size:14px; font-weight:400; color:{GRAY_500};">개</span></div>
                <table>{rows}</table>
            </div>
            <div style="width:180px; text-align:center; padding-top:20px;">
                {donut}
                <div style="margin-top:8px;">{legend}</div>
            </div>
        </div>

        <div style="display:flex; gap:12px; margin-top:16px;">
            <div style="flex:1; padding:14px; background:#EFF6FF; border-radius:8px;">
                <div style="font-size:11px; font-weight:700; color:{BLUE}; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">💡 시장 기회</div>
                {gap_items}
            </div>
            <div style="flex:1; padding:14px; background:#F0FDF4; border-radius:8px;">
                <div style="font-size:11px; font-weight:700; color:{GREEN}; margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">🎯 차별화 전략</div>
                {strat_items}
            </div>
        </div>

        {self._insight_box(f"프랜차이즈 비율 {cafe_types[0].get('ratio', 0):.0f}%로 경쟁이 치열하나, 시장 기회 영역에서 차별화 포인트가 존재합니다." if cafe_types else "경쟁 시장 분석 결과를 바탕으로 차별화 전략을 수립하세요.")}
        {self._footer()}
    </div>'''

    def _page_timeline(self, timeline: dict, num: int) -> str:
        header = self._section_header(num, "창업 타임라인")
        stages = timeline.get("stages", [])
        total_weeks = timeline.get("total_weeks", 0)

        if not stages:
            return ""

        # Gantt chart as SVG
        chart_w = 460
        row_h = 32
        label_w = 130
        chart_area_w = chart_w - label_w
        h = len(stages) * row_h + 30

        gantt = ""
        # Grid lines
        for week in range(0, total_weeks + 1, max(1, total_weeks // 5)):
            x = label_w + (week / total_weeks * chart_area_w) if total_weeks > 0 else label_w
            gantt += f'<line x1="{x:.1f}" y1="20" x2="{x:.1f}" y2="{h - 10}" stroke="{GRAY_300}" stroke-width="0.5" />'
            gantt += f'<text x="{x:.1f}" y="14" font-size="8" fill="{GRAY_500}" text-anchor="middle">{week}주</text>'

        colors_gantt = ["#2563EB", "#7C3AED", "#0D9488", "#F97316", "#EC4899", "#8B5CF6", "#06B6D4", "#10B981"]

        for i, stage in enumerate(stages):
            y = i * row_h + 24
            name = stage.get("name", "")
            sw = stage.get("start_week", 0)
            ew = stage.get("end_week", 0)
            dur = stage.get("duration_weeks", 0)

            bar_x = label_w + (sw / total_weeks * chart_area_w) if total_weeks > 0 else label_w
            bar_w = (dur / total_weeks * chart_area_w) if total_weeks > 0 else 0
            c = colors_gantt[i % len(colors_gantt)]

            gantt += f'<text x="{label_w - 6}" y="{y + row_h / 2 - 2}" font-size="10" fill="{GRAY_700}" text-anchor="end" dominant-baseline="central">{name} ({dur}주)</text>'
            gantt += f'<rect x="{bar_x:.1f}" y="{y + 2}" width="{max(bar_w, 4):.1f}" height="{row_h - 8}" rx="4" fill="{c}" />'
            # Label inside bar
            if bar_w > 40:
                gantt += f'<text x="{bar_x + bar_w / 2:.1f}" y="{y + row_h / 2}" font-size="8" fill="{WHITE}" text-anchor="middle" dominant-baseline="central" font-weight="600">{sw}~{ew}주</text>'

        gantt_svg = f'<svg width="{chart_w}" height="{h}" viewBox="0 0 {chart_w} {h}" xmlns="http://www.w3.org/2000/svg">{gantt}</svg>'

        # Stage details
        details = ""
        for i, stage in enumerate(stages):
            c = colors_gantt[i % len(colors_gantt)]
            details += f'<div style="display:flex; align-items:center; gap:8px; padding:4px 0; border-bottom:1px solid {GRAY_300};"><div style="width:6px; height:6px; border-radius:50%; background:{c};"></div><span style="font-size:10px; color:{NAVY}; font-weight:600; width:100px;">{stage.get("name", "")}</span><span style="font-size:10px; color:{GRAY_500};">{stage.get("description", "")}</span></div>'

        fast = timeline.get("fast_estimate_months", "")
        slow = timeline.get("slow_estimate_months", "")
        estimate = f"빠르면 {fast}개월, 느리면 {slow}개월" if fast and slow else f"약 {total_weeks}주 ({total_weeks / 4:.1f}개월)"

        return f'''<div class="page">
        {header}
        <div style="display:flex; gap:16px; margin-bottom:16px;">
            <div style="padding:12px 16px; background:{BLUE}10; border-radius:8px; flex:1; text-align:center;">
                <div style="font-size:10px; color:{BLUE}; font-weight:600;">총 예상 기간</div>
                <div style="font-size:28px; font-weight:800; color:{NAVY};">{total_weeks}주</div>
                <div style="font-size:10px; color:{GRAY_500};">{estimate}</div>
            </div>
        </div>

        {gantt_svg}

        <div style="margin-top:16px;">
            <h3 style="font-size:12px; font-weight:700; color:{NAVY}; margin-bottom:6px;">단계별 세부 내용</h3>
            {details}
        </div>

        {self._insight_box(f"총 {total_weeks}주 소요 예상이며, 인테리어(가장 긴 단계)와 인허가를 병행 진행하여 일정을 단축할 수 있습니다.")}
        {self._footer()}
    </div>'''

    def _page_trend(self, trend: dict, num: int) -> str:
        header = self._section_header(num, "트렌드 분석")
        trends = trend.get("trends", [])
        if not trends:
            return ""

        # Bar chart for average ratios
        items = [{"name": t.get("keyword", ""), "value": t.get("average_ratio", 0)} for t in trends]
        bar_svg = self._svg_horizontal_bars(items, 460, 28)

        # Period table
        rows = ""
        first = trends[0]
        data_pts = first.get("data", [])
        for idx, pt in enumerate(data_pts[:6]):
            period = pt.get("period", "")
            cells = ""
            for t in trends:
                dl = t.get("data", [])
                val = dl[idx].get("ratio", 0) if idx < len(dl) else 0
                cells += f'<td style="text-align:right;">{val:.0f}</td>'
            rows += f'<tr><td>{period}</td>{cells}</tr>'

        h_cols = "".join(f'<th style="text-align:right;">{t.get("keyword", "")}</th>' for t in trends)

        # Line chart SVG
        chart_w, chart_h = 460, 160
        pad_x, pad_y = 50, 20
        cw = chart_w - pad_x - 20
        ch = chart_h - pad_y - 30
        max_ratio = max(max((p.get("ratio", 0) for p in t.get("data", [])), default=1) for t in trends) or 1

        lines_svg = ""
        # Grid
        for i in range(5):
            y_g = pad_y + ch - (i / 4 * ch)
            lines_svg += f'<line x1="{pad_x}" y1="{y_g:.1f}" x2="{chart_w - 20}" y2="{y_g:.1f}" stroke="{GRAY_300}" stroke-width="0.3" />'
            lines_svg += f'<text x="{pad_x - 5}" y="{y_g:.1f}" font-size="8" fill="{GRAY_500}" text-anchor="end" dominant-baseline="central">{int(max_ratio * i / 4)}</text>'

        for ti, t in enumerate(trends):
            points = []
            dl = t.get("data", [])
            for di, d in enumerate(dl):
                x = pad_x + (di / max(len(dl) - 1, 1)) * cw
                y = pad_y + ch - (d.get("ratio", 0) / max_ratio * ch)
                points.append(f"{x:.1f},{y:.1f}")
            c = CHART_COLORS[ti % len(CHART_COLORS)]
            lines_svg += f'<polyline points="{" ".join(points)}" fill="none" stroke="{c}" stroke-width="2" />'
            for pi, pt in enumerate(points):
                lines_svg += f'<circle cx="{pt.split(",")[0]}" cy="{pt.split(",")[1]}" r="3" fill="{c}" />'

        # X-axis labels
        if data_pts:
            for di, d in enumerate(data_pts):
                x = pad_x + (di / max(len(data_pts) - 1, 1)) * cw
                lines_svg += f'<text x="{x:.1f}" y="{pad_y + ch + 15}" font-size="8" fill="{GRAY_500}" text-anchor="middle">{d.get("period", "")[-5:]}</text>'

        line_chart = f'<svg width="{chart_w}" height="{chart_h}" viewBox="0 0 {chart_w} {chart_h}" xmlns="http://www.w3.org/2000/svg">{lines_svg}</svg>'

        # Legend
        legend = " ".join(f'<span style="display:inline-flex; align-items:center; gap:4px; margin-right:12px;"><span style="width:12px; height:3px; background:{CHART_COLORS[i % len(CHART_COLORS)]}; border-radius:1px;"></span><span style="font-size:10px; color:{GRAY_700};">{t.get("keyword", "")}</span></span>' for i, t in enumerate(trends))

        summary = trend.get("summary", {})
        top_kw = summary.get("top_keyword", "")
        insight_text = f"'{top_kw}'이(가) 가장 높은 검색 관심도를 보이며, 해당 상권의 브랜드 인지도가 높습니다." if top_kw else ""

        return f'''<div class="page">
        {header}
        <h3 style="font-size:13px; font-weight:700; color:{NAVY}; margin-bottom:8px;">키워드 검색 트렌드 비교</h3>
        {bar_svg}

        <h3 style="font-size:13px; font-weight:700; color:{NAVY}; margin:16px 0 8px;">기간별 트렌드 추이</h3>
        <div style="margin-bottom:6px;">{legend}</div>
        {line_chart}

        <h3 style="font-size:13px; font-weight:700; color:{NAVY}; margin:16px 0 8px;">상세 데이터</h3>
        <table><tr><th>기간</th>{h_cols}</tr>{rows}</table>

        {self._insight_box(insight_text) if insight_text else ""}
        {self._footer()}
    </div>'''

    def _page_support(self, programs: list, num: int) -> str:
        header = self._section_header(num, "정부지원사업")

        rows = ""
        for p in programs[:10]:
            name = p.get("program_name", "")
            cat = p.get("category", "")
            amount = p.get("support_amount", "")
            end_date = p.get("application_end_date", "")
            days = p.get("days_until_deadline")
            org = p.get("managing_org", "")

            badge = ""
            if days is not None:
                bc = "badge-red" if days <= 7 else ("badge-yellow" if days <= 30 else "badge-blue")
                badge = f'<span class="badge {bc}">D-{days}</span>'

            rows += f'''<tr>
                <td><strong style="color:{NAVY};">{name}</strong><br/><span style="font-size:9px; color:{GRAY_500};">{cat}</span></td>
                <td style="text-align:right; font-weight:600; color:{BLUE};">{amount}</td>
                <td style="text-align:center;">{end_date}<br/>{badge}</td>
                <td style="font-size:10px; color:{GRAY_500};">{org}</td>
            </tr>'''

        # Urgency summary
        urgent = sum(1 for p in programs if (p.get("days_until_deadline") or 999) <= 30)
        urgent_note = f'<div style="padding:10px 14px; background:#FEF2F2; border:1px solid #FECACA; border-radius:6px; margin-bottom:12px; font-size:11px;"><strong style="color:{RED};">⚡ 마감 임박:</strong> {urgent}건의 지원사업이 30일 이내 마감됩니다.</div>' if urgent else ""

        return f'''<div class="page">
        {header}
        <div style="font-size:12px; color:{GRAY_500}; margin-bottom:12px;">신청 가능한 지원사업 <strong style="color:{NAVY}; font-size:18px;">{len(programs)}건</strong></div>
        {urgent_note}
        <table>
            <tr><th>사업명</th><th style="text-align:right;">지원금액</th><th style="text-align:center;">마감일</th><th>주관기관</th></tr>
            {rows}
        </table>

        <div style="margin-top:16px; padding:12px 16px; background:{GRAY_100}; border-radius:6px;">
            <div style="font-size:10px; font-weight:700; color:{GRAY_500}; margin-bottom:4px;">📢 신청 안내</div>
            <div style="font-size:10px; color:{GRAY_700}; line-height:1.6;">각 지원사업은 신청 자격 및 조건이 상이합니다. 반드시 주관기관 홈페이지를 확인하시고, 필요 서류를 미리 준비하여 마감일 전에 신청하시기 바랍니다.</div>
        </div>
        {self._footer()}
    </div>'''

    def _page_disclaimer(self, date: str) -> str:
        return f'''<div class="page" style="display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
        <div style="max-width:360px;">
            <div style="width:48px; height:48px; background:{BLUE}; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:20px; font-weight:800; color:{WHITE}; margin:0 auto 20px;">SP</div>
            <h2 style="font-size:20px; font-weight:700; color:{NAVY}; margin-bottom:16px;">SpotPick</h2>
            <p style="font-size:11px; color:{GRAY_500}; line-height:1.8; margin-bottom:20px;">
                본 리포트는 SpotPick AI가 공공 데이터 및 통계를 기반으로 생성한 분석 자료입니다.<br/>
                실제 창업 의사결정 시에는 현장 조사 및 전문가 상담을 병행하시기 바랍니다.<br/>
                데이터 기준일: {date}
            </p>
            <div style="width:60px; height:2px; background:{BLUE}; margin:0 auto 16px;"></div>
            <p style="font-size:9px; color:{GRAY_500};">AI가 골라주는 나만의 창업 자리</p>
            <p style="font-size:9px; color:{GRAY_500}; margin-top:4px;">© 2026 SpotPick. All rights reserved.</p>
        </div>
    </div>'''

    def _translate_cafe_type(self, t: str) -> str:
        return {"specialty": "스페셜티", "franchise": "프랜차이즈", "dessert": "디저트", "takeout": "테이크아웃", "bakery": "베이커리", "general": "일반"}.get(t.lower(), t)


# Singleton
_pdf_service: Optional[PDFService] = None


def get_pdf_service() -> PDFService:
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service
