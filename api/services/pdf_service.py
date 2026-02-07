"""
PDF 리포트 생성 서비스 — McKinsey 컨설팅 보고서 품질
Playwright 기반 HTML→PDF 변환 / SVG 인포그래픽 / AI 분석 코멘터리
"""

from __future__ import annotations

import base64
import io
import json
import logging
import math
import os
from typing import Any, Optional
from datetime import datetime
from html import escape as html_escape
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import httpx  # type: ignore[import-not-found]
except ImportError:
    httpx = None  # type: ignore[assignment]

try:
    from PIL import Image, ImageDraw, ImageFont  # type: ignore[import-not-found]
except ImportError:
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None  # type: ignore[assignment]

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except Exception:
    pass

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

try:
    from google import genai  # type: ignore[import-not-found]
except Exception:
    genai = None  # type: ignore[assignment]

# ─── Monochromatic Blue Scale ────────────────────────────────────────────────
B1 = "#1B2A4A"   # darkest navy
B2 = "#2D4A7A"   # dark blue
B3 = "#3B6FB5"   # medium blue
B4 = "#6B9FDB"   # light blue
B5 = "#A3C4ED"   # lightest blue

NAVY = B1
BLUE = B3
RED = "#C0392B"
GREEN = "#1E7D4E"
GOLD = "#B7791F"
GRAY_900 = "#111827"
GRAY_700 = "#374151"
GRAY_500 = "#6B7280"
GRAY_400 = "#9CA3AF"
GRAY_300 = "#D1D5DB"
GRAY_200 = "#E5E7EB"
GRAY_100 = "#F3F4F6"
GRAY_50 = "#F9FAFB"
WHITE = "#FFFFFF"

CHART_COLORS = [B1, B2, B3, B4, B5]
CHART_6 = [B1, B2, B3, B4, B5, "#7C8DB5"]

SEOUL_AVG_SURVIVAL_3Y = 38.0  # percent


class PDFService:
    """PDF 리포트 생성 서비스"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def _generate_ai_analysis(self, data: dict[str, Any], industry_name: str) -> dict[str, str]:
        """Gemini를 호출하여 각 섹션별 컨설팅 분석 코멘터리 생성"""
        if not GEMINI_API_KEY or genai is None:
            logger.warning("Gemini API 미설정 — AI 분석 생략")
            return {}

        recs = data.get("recommendations", [])
        charts = data.get("charts", [])
        comp = data.get("competitive")
        sim = data.get("simulation")
        timeline = data.get("timeline")
        trend = data.get("trend")
        programs = data.get("support_programs", [])

        # 섹션별 데이터 요약
        summary_parts = []
        if recs:
            top3 = [{"name": r.get("district_name"), "success_prob": r.get("success_probability"),
                      "monthly_sales": r.get("monthly_sales"), "store_count": r.get("store_count"),
                      "survival_rate": r.get("survival_rate"), "foot_traffic": r.get("foot_traffic_total"),
                      "worker": r.get("worker_total"), "rent": r.get("estimated_rent")} for r in recs[:3]]
            summary_parts.append(f"[추천상권] {json.dumps(top3, ensure_ascii=False)}")
        if charts:
            chart_summary = [{"type": c.get("type"), "data": c.get("data", [])[:6]} for c in charts[:3]]
            summary_parts.append(f"[시장데이터] {json.dumps(chart_summary, ensure_ascii=False)}")
        if sim:
            sim_brief = {
                "monthly_sales": sim.get("revenue", {}).get("monthly_sales_per_store"),
                "net_profit": sim.get("break_even", {}).get("monthly_net_profit"),
                "margin": sim.get("break_even", {}).get("net_profit_margin"),
                "break_even_months": sim.get("break_even", {}).get("break_even_months_min"),
                "total_investment": sim.get("startup_cost", {}).get("total_min"),
                "rent": sim.get("operating_cost", {}).get("rent"),
                "store_count": sim.get("competition", {}).get("store_count"),
                "franchise_ratio": sim.get("competition", {}).get("franchise_ratio"),
                "survival_rate": sim.get("competition", {}).get("survival_rate"),
            }
            summary_parts.append(f"[시뮬레이션] {json.dumps(sim_brief, ensure_ascii=False)}")
        if comp:
            comp_brief = {
                "total": comp.get("total_nearby_cafes"),
                "types": [{"type": t.get("type"), "ratio": t.get("ratio")} for t in comp.get("cafe_types", [])[:5]],
                "gaps": [g.get("gap_type") for g in comp.get("market_gaps", [])[:3]],
            }
            summary_parts.append(f"[경쟁분석] {json.dumps(comp_brief, ensure_ascii=False)}")
        if trend and trend.get("trends"):
            trend_brief = [{"keyword": t.get("keyword"), "avg": t.get("average_ratio")} for t in trend.get("trends", [])[:3]]
            summary_parts.append(f"[트렌드] {json.dumps(trend_brief, ensure_ascii=False)}")

        data_text = "\n".join(summary_parts)

        prompt = f"""당신은 맥킨지 수석 컨설턴트입니다. 아래 {industry_name} 창업 분석 데이터를 보고, 각 섹션별로 전문적인 컨설팅 분석을 작성하세요.

데이터:
{data_text}

아래 7개 섹션에 대해 각각 정확히 2-3문장으로 작성하세요.
각 분석은 반드시 (1) 데이터에서 도출한 핵심 인사이트 (So What?) + (2) 구체적 행동 제안 (Implication)을 포함해야 합니다.
숫자를 적극 인용하고, "~할 수 있습니다", "~이 필요합니다" 등 행동 지향적으로 작성하세요.

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
  "executive_summary": "...",
  "market": "...",
  "location": "...",
  "simulation": "...",
  "competitive": "...",
  "risk": "...",
  "trend": "..."
}}"""

        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text or ""
            # JSON 추출
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            result = json.loads(text)
            logger.info("AI 분석 코멘터리 생성 완료")
            return result
        except Exception as e:
            logger.error(f"AI 분석 생성 실패: {e}", exc_info=True)
            return {}

    async def generate_report_pdf(
        self,
        conversation_data: dict[str, Any],
        industry_name: str = "카페",
    ) -> bytes:
        if async_playwright is None:
            raise RuntimeError("playwright 미설치")

        # AI 분석 코멘터리 생성
        ai_analysis = await self._generate_ai_analysis(conversation_data, industry_name)

        # 지도 이미지 생성 (추천 상권 마커)
        map_image_b64 = await self._generate_map_image(conversation_data.get("recommendations", []))

        html = self._build_html(conversation_data, industry_name, ai_analysis, map_image_b64=map_image_b64)

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
    # Static Map Image Generation (OSM tiles + Pillow)
    # ═══════════════════════════════════════════════════════════════════════════

    async def _geocode_district(self, district_name: str) -> Optional[dict[str, float]]:
        """Kakao 키워드 검색으로 상권명 → 좌표 변환 (fallback)"""
        if not KAKAO_REST_API_KEY or httpx is None:
            return None
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    "https://dapi.kakao.com/v2/local/search/keyword.json",
                    params={"query": f"서울 {district_name}", "size": 1},
                    headers={"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"},
                )
                resp.raise_for_status()
                docs = resp.json().get("documents", [])
                if docs:
                    x = docs[0].get("x")
                    y = docs[0].get("y")
                    if x and y:
                        return {"lat": float(y), "lng": float(x)}
        except Exception as e:
            logger.debug(f"지오코딩 실패 ({district_name}): {e}")
        return None

    def _lat_lng_to_tile(self, lat: float, lng: float, zoom: int) -> tuple[int, int]:
        """위경도를 OSM 타일 좌표(x, y)로 변환"""
        n = 2 ** zoom
        x = int((lng + 180.0) / 360.0 * n)
        y = int((1.0 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n)
        return x, y

    def _lat_lng_to_pixel(self, lat: float, lng: float, zoom: int) -> tuple[float, float]:
        """위경도를 OSM 전체 픽셀 좌표로 변환 (zoom 레벨 기준)"""
        n = 2 ** zoom
        px = (lng + 180.0) / 360.0 * n * 256
        py = (1.0 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n * 256
        return px, py

    def _calculate_zoom(self, coords: list[dict[str, float]], img_w: int, img_h: int) -> int:
        """모든 마커가 이미지 안에 보이도록 줌 레벨 계산"""
        if len(coords) <= 1:
            return 15  # 단일 포인트는 높은 줌

        lats = [c["lat"] for c in coords]
        lngs = [c["lng"] for c in coords]
        lat_min, lat_max = min(lats), max(lats)
        lng_min, lng_max = min(lngs), max(lngs)

        # 마진 추가 (20%)
        lat_margin = max((lat_max - lat_min) * 0.25, 0.005)
        lng_margin = max((lng_max - lng_min) * 0.25, 0.005)
        lat_min -= lat_margin
        lat_max += lat_margin
        lng_min -= lng_margin
        lng_max += lng_margin

        for z in range(17, 7, -1):
            px_min_x, px_min_y = self._lat_lng_to_pixel(lat_max, lng_min, z)
            px_max_x, px_max_y = self._lat_lng_to_pixel(lat_min, lng_max, z)
            if (px_max_x - px_min_x) <= img_w and (px_max_y - px_min_y) <= img_h:
                return z
        return 8

    async def _fetch_osm_tile(self, client: Any, z: int, x: int, y: int) -> Optional[bytes]:
        """OSM 타일 다운로드"""
        url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
        except Exception as e:
            logger.debug(f"OSM 타일 다운로드 실패 ({z}/{x}/{y}): {e}")
            return None

    async def _generate_map_image(self, recommendations: list[dict]) -> Optional[str]:
        """
        추천 상권 좌표로 지도 이미지 생성 → base64 PNG 반환.
        실패 시 None 반환 (graceful fallback).
        """
        if Image is None or httpx is None:
            logger.info("Pillow 또는 httpx 미설치 — 지도 생성 생략")
            return None

        if not recommendations:
            return None

        # 1. 좌표 수집 (최대 3개)
        coords: list[dict[str, Any]] = []  # {lat, lng, rank, name}
        for rec in recommendations[:3]:
            lat: Optional[float] = None
            lng: Optional[float] = None

            # coordinates 필드 확인
            c = rec.get("coordinates")
            if isinstance(c, dict):
                lat = c.get("lat")
                lng = c.get("lng")

            # 직접 필드 확인
            if lat is None or lng is None:
                lat = rec.get("latitude") or rec.get("district_lat")
                lng = rec.get("longitude") or rec.get("district_lng")

            # 좌표 없으면 지오코딩
            if (lat is None or lng is None) and rec.get("district_name"):
                geo = await self._geocode_district(rec["district_name"])
                if geo:
                    lat, lng = geo["lat"], geo["lng"]

            if lat is not None and lng is not None:
                try:
                    coords.append({
                        "lat": float(lat),
                        "lng": float(lng),
                        "rank": rec.get("rank", len(coords) + 1),
                        "name": rec.get("district_name", ""),
                    })
                except (ValueError, TypeError):
                    continue

        if not coords:
            logger.info("유효한 좌표 없음 — 지도 생성 생략")
            return None

        try:
            return await self._render_osm_map(coords)
        except Exception as e:
            logger.warning(f"지도 이미지 생성 실패 (graceful skip): {e}", exc_info=True)
            return None

    async def _render_osm_map(self, coords: list[dict[str, Any]]) -> Optional[str]:
        """OSM 타일을 다운로드하고 마커를 그려서 base64 PNG로 반환"""
        IMG_W, IMG_H = 600, 360

        # 줌 레벨 & 중심 계산
        zoom = self._calculate_zoom(coords, IMG_W - 60, IMG_H - 60)

        center_lat = sum(c["lat"] for c in coords) / len(coords)
        center_lng = sum(c["lng"] for c in coords) / len(coords)

        center_px, center_py = self._lat_lng_to_pixel(center_lat, center_lng, zoom)

        # 필요한 타일 범위 계산
        left_px = center_px - IMG_W / 2
        top_py = center_py - IMG_H / 2

        tile_x_min = int(left_px // 256)
        tile_y_min = int(top_py // 256)
        tile_x_max = int((left_px + IMG_W) // 256)
        tile_y_max = int((top_py + IMG_H) // 256)

        # 타일 다운로드
        async with httpx.AsyncClient(
            timeout=10,
            headers={"User-Agent": "SpotPick-PDFReport/1.0 (contact: support@spotpick.kr)"},
        ) as client:
            canvas = Image.new("RGB", (IMG_W, IMG_H), (240, 240, 240))

            for tx in range(tile_x_min, tile_x_max + 1):
                for ty in range(tile_y_min, tile_y_max + 1):
                    tile_bytes = await self._fetch_osm_tile(client, zoom, tx, ty)
                    if tile_bytes:
                        try:
                            tile_img = Image.open(io.BytesIO(tile_bytes))
                            # 타일 위치 → 캔버스 위치
                            paste_x = int(tx * 256 - left_px)
                            paste_y = int(ty * 256 - top_py)
                            canvas.paste(tile_img, (paste_x, paste_y))
                        except Exception:
                            continue

        # 마커 그리기
        draw = ImageDraw.Draw(canvas)
        marker_colors = [(192, 32, 32), (32, 80, 160), (30, 125, 78)]  # 빨강, 파랑, 초록

        # 폰트 로드 (한글 지원 폰트 우선)
        font_marker = ImageFont.load_default()
        font_label = ImageFont.load_default()
        font_candidates = [
            # macOS Korean fonts
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/System/Library/Fonts/Supplemental/AppleGothic.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
            # Linux Korean fonts
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for fp in font_candidates:
            try:
                font_marker = ImageFont.truetype(fp, 14)
                font_label = ImageFont.truetype(fp, 11)
                break
            except Exception:
                continue

        for i, c in enumerate(coords):
            px, py = self._lat_lng_to_pixel(c["lat"], c["lng"], zoom)
            x = int(px - left_px)
            y = int(py - top_py)

            color = marker_colors[i % len(marker_colors)]
            rank = c.get("rank", i + 1)

            # 마커 핀 그리기 (드롭 핀 모양)
            # 핀 헤드 (원)
            r = 14
            draw.ellipse([x - r, y - r * 2 - 6, x + r, y - 6], fill=color, outline=(255, 255, 255), width=2)
            # 핀 포인트 (삼각형)
            draw.polygon([(x - 6, y - 10), (x + 6, y - 10), (x, y)], fill=color)

            # 순위 번호
            text = str(rank)
            bbox = draw.textbbox((0, 0), text, font=font_marker)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((x - tw // 2, y - r - 6 - th // 2 - 2), text, fill=(255, 255, 255), font=font_marker)

            # 상권명 라벨 (마커 위)
            name = c.get("name", "")
            if name:
                # 너무 긴 이름은 줄임
                if len(name) > 12:
                    name = name[:11] + "…"
                nbbox = draw.textbbox((0, 0), name, font=font_label)
                nw = nbbox[2] - nbbox[0]
                nh = nbbox[3] - nbbox[1]
                label_x = x - nw // 2
                label_y = y - r * 2 - 12 - nh
                # 라벨 배경
                pad = 3
                draw.rounded_rectangle(
                    [label_x - pad, label_y - pad, label_x + nw + pad, label_y + nh + pad],
                    radius=3, fill=(255, 255, 255, 220), outline=color, width=1,
                )
                draw.text((label_x, label_y), name, fill=color, font=font_label)

        # OSM 저작권 표시
        attr_text = "\u00a9 OpenStreetMap"
        abbox = draw.textbbox((0, 0), attr_text, font=font_label)
        aw = abbox[2] - abbox[0]
        ah = abbox[3] - abbox[1]
        draw.rectangle([IMG_W - aw - 8, IMG_H - ah - 6, IMG_W, IMG_H], fill=(255, 255, 255, 200))
        draw.text((IMG_W - aw - 4, IMG_H - ah - 3), attr_text, fill=(100, 100, 100), font=font_label)

        # PNG → base64
        buf = io.BytesIO()
        canvas.save(buf, format="PNG", optimize=True)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        logger.info(f"지도 이미지 생성 완료 ({len(coords)}개 마커, zoom={zoom})")
        return b64

    # ═══════════════════════════════════════════════════════════════════════════
    # SVG Chart Helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _svg_donut(self, segments: list[dict], size: int = 180, hole: float = 0.6) -> str:
        total = sum(s["value"] for s in segments) or 1
        r = size / 2 - 5
        cx = cy = size / 2
        inner_r = r * hole
        paths = []
        start_angle = -90

        for seg in segments:
            pct = seg["value"] / total
            if pct <= 0:
                continue
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
            paths.append(f'<path d="{d}" fill="{seg.get("color", B3)}" />')
            start_angle = end_angle

        return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">{"".join(paths)}</svg>'

    def _svg_radar(self, categories: list[dict], size: int = 200) -> str:
        n = len(categories)
        if n < 3:
            return ""
        cx = cy = size / 2
        r = size / 2 - 28
        angle_step = 360 / n

        grid_lines = ""
        for level in [0.25, 0.5, 0.75, 1.0]:
            pts = []
            for i in range(n):
                a = math.radians(-90 + i * angle_step)
                pts.append(f"{cx + r * level * math.cos(a):.1f},{cy + r * level * math.sin(a):.1f}")
            grid_lines += f'<polygon points="{" ".join(pts)}" fill="none" stroke="{GRAY_300}" stroke-width="0.5" />'

        axes = ""
        for i in range(n):
            a = math.radians(-90 + i * angle_step)
            axes += f'<line x1="{cx}" y1="{cy}" x2="{cx + r * math.cos(a):.1f}" y2="{cy + r * math.sin(a):.1f}" stroke="{GRAY_300}" stroke-width="0.5" />'

        data_pts = []
        for i, cat in enumerate(categories):
            score = cat.get("score", 0)
            max_s = cat.get("max_score", 100)
            ratio = min(score / max_s, 1.0) if max_s > 0 else 0
            a = math.radians(-90 + i * angle_step)
            data_pts.append(f"{cx + r * ratio * math.cos(a):.1f},{cy + r * ratio * math.sin(a):.1f}")

        data_poly = f'<polygon points="{" ".join(data_pts)}" fill="{B3}30" stroke="{B3}" stroke-width="1.5" />'

        dots_labels = ""
        for i, cat in enumerate(categories):
            score = cat.get("score", 0)
            max_s = cat.get("max_score", 100)
            ratio = min(score / max_s, 1.0) if max_s > 0 else 0
            a = math.radians(-90 + i * angle_step)

            dx = cx + r * ratio * math.cos(a)
            dy = cy + r * ratio * math.sin(a)
            dots_labels += f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="2.5" fill="{B2}" />'

            lx = cx + (r + 16) * math.cos(a)
            ly = cy + (r + 16) * math.sin(a)
            anchor = "middle"
            if math.cos(a) > 0.3:
                anchor = "start"
            elif math.cos(a) < -0.3:
                anchor = "end"
            name = cat.get("name", "")
            dots_labels += f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="9" font-family="sans-serif" fill="{GRAY_700}" text-anchor="{anchor}" dominant-baseline="central">{name} {score:.0f}</text>'

        return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">{grid_lines}{axes}{data_poly}{dots_labels}</svg>'

    def _svg_horizontal_bars(self, items: list[dict], width: int = 460, bar_h: int = 22, gap: int = 6) -> str:
        if not items:
            return ""
        max_val = max((it["value"] for it in items), default=1) or 1
        label_w = 90
        value_w = 65
        chart_w = width - label_w - value_w - 10
        h = len(items) * (bar_h + gap) + 4

        bars = ""
        for i, it in enumerate(items):
            y = i * (bar_h + gap) + 2
            w = (it["value"] / max_val) * chart_w
            c = CHART_COLORS[i % len(CHART_COLORS)]
            name = it.get("name", "")
            val = it["value"]
            extra = it.get("extra", "")
            bars += f'<text x="{label_w - 6}" y="{y + bar_h / 2 + 1}" font-size="9" font-family="sans-serif" fill="{GRAY_700}" text-anchor="end" dominant-baseline="central">{name}</text>'
            bars += f'<rect x="{label_w}" y="{y + 1}" width="{max(w, 2):.1f}" height="{bar_h - 2}" rx="2" fill="{c}" />'
            bars += f'<text x="{label_w + max(w, 2) + 5}" y="{y + bar_h / 2 + 1}" font-size="9" font-family="sans-serif" fill="{GRAY_700}" dominant-baseline="central" font-weight="600">{val:,.1f}{extra}</text>'

        return f'<svg width="{width}" height="{h}" viewBox="0 0 {width} {h}" xmlns="http://www.w3.org/2000/svg">{bars}</svg>'

    def _svg_waterfall(self, items: list[dict], width: int = 480, height: int = 200) -> str:
        if not items:
            return ""
        n = len(items)
        pad_x, pad_y = 50, 25
        chart_w = width - pad_x - 20
        chart_h = height - pad_y - 30
        bar_w = chart_w / n * 0.55
        step = chart_w / n

        all_vals = [abs(it["value"]) for it in items]
        max_val = max(all_vals) * 1.15 or 1

        svg = ""
        baseline_y = pad_y + chart_h * 0.5

        svg += f'<line x1="{pad_x}" y1="{baseline_y}" x2="{width - 20}" y2="{baseline_y}" stroke="{GRAY_300}" stroke-width="0.5" stroke-dasharray="3,3" />'

        running = 0
        for i, it in enumerate(items):
            x = pad_x + i * step + (step - bar_w) / 2
            val = it["value"]
            t = it.get("type", "add")
            label = it.get("label", "")

            if t == "total":
                bar_height = abs(val) / max_val * chart_h * 0.42
                if val >= 0:
                    bar_top = baseline_y - bar_height
                else:
                    bar_top = baseline_y
                color = B1
                running = val
            elif t == "subtract":
                bar_height = abs(val) / max_val * chart_h * 0.42
                prev_top = baseline_y - (running / max_val * chart_h * 0.42)
                bar_top = prev_top
                color = RED
                running -= val
            else:
                bar_height = abs(val) / max_val * chart_h * 0.42
                prev_top = baseline_y - (running / max_val * chart_h * 0.42)
                bar_top = prev_top - bar_height
                color = B3
                running += val

            svg += f'<rect x="{x:.1f}" y="{bar_top:.1f}" width="{bar_w:.1f}" height="{max(bar_height, 2):.1f}" rx="2" fill="{color}" />'
            svg += f'<text x="{x + bar_w / 2:.1f}" y="{bar_top - 4:.1f}" font-size="8" font-family="sans-serif" fill="{GRAY_700}" text-anchor="middle" font-weight="600">{self._fmt(val)}</text>'
            svg += f'<text x="{x + bar_w / 2:.1f}" y="{baseline_y + chart_h * 0.5 + 12:.1f}" font-size="8" font-family="sans-serif" fill="{GRAY_500}" text-anchor="middle">{label}</text>'

        return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{svg}</svg>'

    def _svg_gauge(self, value: float, max_val: float = 100, size: int = 110, label: str = "") -> str:
        pct = min(value / max_val, 1.0) if max_val > 0 else 0
        r = size / 2 - 10
        cx = cy = size / 2
        sa = math.pi
        ea = math.pi - pct * math.pi
        x1 = cx + r * math.cos(sa)
        y1 = cy - r * math.sin(sa)
        x2 = cx + r * math.cos(ea)
        y2 = cy - r * math.sin(ea)
        large = 1 if pct > 0.5 else 0

        color = GREEN if pct >= 0.7 else (GOLD if pct >= 0.4 else RED)

        return f'''<svg width="{size}" height="{int(size * 0.6)}" viewBox="0 0 {size} {int(size * 0.6)}" xmlns="http://www.w3.org/2000/svg">
            <path d="M {x1:.1f} {y1:.1f} A {r:.1f} {r:.1f} 0 0 1 {cx + r:.1f} {cy:.1f}" fill="none" stroke="{GRAY_200}" stroke-width="8" stroke-linecap="round" />
            <path d="M {x1:.1f} {y1:.1f} A {r:.1f} {r:.1f} 0 {large} 1 {x2:.1f} {y2:.1f}" fill="none" stroke="{color}" stroke-width="8" stroke-linecap="round" />
            <text x="{cx}" y="{cy - 6}" font-size="17" font-weight="700" font-family="sans-serif" fill="{NAVY}" text-anchor="middle">{value:.1f}%</text>
            <text x="{cx}" y="{cy + 8}" font-size="8" font-family="sans-serif" fill="{GRAY_500}" text-anchor="middle">{label}</text>
        </svg>'''

    def _svg_line_chart(self, trends: list[dict], width: int = 460, height: int = 150) -> str:
        if not trends:
            return ""
        pad_x, pad_y = 40, 15
        cw = width - pad_x - 15
        ch = height - pad_y - 25
        max_ratio = 1
        for t in trends:
            for p in t.get("data", []):
                max_ratio = max(max_ratio, p.get("ratio", 0))
        max_ratio = max_ratio * 1.1

        svg = ""
        for i in range(5):
            y_g = pad_y + ch - (i / 4 * ch)
            svg += f'<line x1="{pad_x}" y1="{y_g:.1f}" x2="{width - 15}" y2="{y_g:.1f}" stroke="{GRAY_200}" stroke-width="0.4" />'
            svg += f'<text x="{pad_x - 4}" y="{y_g:.1f}" font-size="7" font-family="sans-serif" fill="{GRAY_400}" text-anchor="end" dominant-baseline="central">{int(max_ratio * i / 4)}</text>'

        for ti, t in enumerate(trends):
            points = []
            dl = t.get("data", [])
            for di, d in enumerate(dl):
                x = pad_x + (di / max(len(dl) - 1, 1)) * cw
                y = pad_y + ch - (d.get("ratio", 0) / max_ratio * ch)
                points.append(f"{x:.1f},{y:.1f}")
            c = CHART_COLORS[ti % len(CHART_COLORS)]
            svg += f'<polyline points="{" ".join(points)}" fill="none" stroke="{c}" stroke-width="1.5" />'
            for pt in points:
                px, py = pt.split(",")
                svg += f'<circle cx="{px}" cy="{py}" r="2.5" fill="{c}" />'

        data_pts = trends[0].get("data", []) if trends else []
        for di, d in enumerate(data_pts):
            x = pad_x + (di / max(len(data_pts) - 1, 1)) * cw
            lbl = d.get("period", "")[-5:]
            svg += f'<text x="{x:.1f}" y="{pad_y + ch + 12}" font-size="7" font-family="sans-serif" fill="{GRAY_400}" text-anchor="middle">{lbl}</text>'

        return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">{svg}</svg>'

    def _svg_gantt(self, stages: list[dict], total_weeks: int, width: int = 460) -> str:
        if not stages or total_weeks <= 0:
            return ""
        row_h = 28
        label_w = 120
        chart_area_w = width - label_w - 10
        h = len(stages) * row_h + 25

        svg = ""
        for week in range(0, total_weeks + 1, max(1, total_weeks // 6)):
            x = label_w + (week / total_weeks * chart_area_w)
            svg += f'<line x1="{x:.1f}" y1="18" x2="{x:.1f}" y2="{h - 5}" stroke="{GRAY_200}" stroke-width="0.5" />'
            svg += f'<text x="{x:.1f}" y="12" font-size="7" font-family="sans-serif" fill="{GRAY_400}" text-anchor="middle">{week}w</text>'

        for i, stage in enumerate(stages):
            y = i * row_h + 20
            name = stage.get("name", "")
            sw = stage.get("start_week", 0)
            dur = stage.get("duration_weeks", 0)

            bar_x = label_w + (sw / total_weeks * chart_area_w)
            bar_w = (dur / total_weeks * chart_area_w)
            c = CHART_COLORS[i % len(CHART_COLORS)]

            svg += f'<text x="{label_w - 5}" y="{y + row_h / 2 - 2}" font-size="9" font-family="sans-serif" fill="{GRAY_700}" text-anchor="end" dominant-baseline="central">{name}</text>'
            svg += f'<rect x="{bar_x:.1f}" y="{y + 2}" width="{max(bar_w, 3):.1f}" height="{row_h - 8}" rx="3" fill="{c}" />'
            if bar_w > 30:
                svg += f'<text x="{bar_x + bar_w / 2:.1f}" y="{y + row_h / 2}" font-size="7" font-family="sans-serif" fill="{WHITE}" text-anchor="middle" dominant-baseline="central" font-weight="600">{dur}w</text>'

        return f'<svg width="{width}" height="{h}" viewBox="0 0 {width} {h}" xmlns="http://www.w3.org/2000/svg">{svg}</svg>'

    # ═══════════════════════════════════════════════════════════════════════════
    # Formatting Helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _fmt(self, value: float) -> str:
        if value is None or value == 0:
            return "-"
        if abs(value) >= 100000000:
            return f"{value / 100000000:.1f}억"
        if abs(value) >= 10000:
            return f"{int(value / 10000):,}만"
        return f"{int(value):,}원"

    def _fmt_won(self, value: float) -> str:
        if value is None or value == 0:
            return "-"
        if abs(value) >= 100000000:
            return f"{value / 100000000:.1f}억원"
        if abs(value) >= 10000:
            return f"{int(value / 10000):,}만원"
        return f"{int(value):,}원"

    def _fmt_num(self, value: float) -> str:
        if value is None:
            return "-"
        if abs(value) >= 10000:
            return f"{value / 10000:.1f}만"
        return f"{int(value):,}"

    def _pct_of(self, part: float, whole: float) -> str:
        if not whole:
            return "-"
        return f"{part / whole * 100:.1f}%"

    # ═══════════════════════════════════════════════════════════════════════════
    # Component Helpers
    # ═══════════════════════════════════════════════════════════════════════════

    def _footer(self, date_str: str, page_num: int) -> str:
        return f'''<div style="position:absolute; bottom:14mm; left:24mm; right:24mm; display:flex; justify-content:space-between; align-items:center; border-top:1px solid {GRAY_200}; padding-top:5px;">
            <span style="font-size:7px; color:{GRAY_400}; font-family:sans-serif;">SpotPick AI 창업 분석 리포트</span>
            <span style="font-size:7px; color:{GRAY_400}; font-family:sans-serif;">Confidential  |  {date_str}</span>
            <span style="font-size:7px; color:{GRAY_400}; font-family:sans-serif;">Page {page_num}</span>
        </div>'''

    def _source_footnote(self, text: str) -> str:
        return f'<div style="margin-top:auto; padding-top:6px; border-top:1px solid {GRAY_200};"><span style="font-size:7px; color:{GRAY_400}; font-family:sans-serif;">Source: {text}</span></div>'

    def _section_number(self, num: int, title: str, subtitle: str = "") -> str:
        sub_html = f'<div style="font-size:9px; color:{GRAY_500}; font-family:sans-serif; margin-top:2px;">{subtitle}</div>' if subtitle else ""
        return f'''<div style="margin-bottom:16px;">
            <div style="display:flex; align-items:baseline; gap:10px; margin-bottom:4px;">
                <span style="font-size:11px; font-weight:700; color:{B3}; font-family:sans-serif; letter-spacing:1px;">SECTION {num:02d}</span>
            </div>
            <h2 style="font-size:16px; font-weight:700; color:{NAVY}; margin:0; font-family:Georgia,'Noto Serif KR',serif; line-height:1.35;">{title}</h2>
            {sub_html}
            <div style="height:2px; width:40px; background:{B3}; margin-top:6px; border-radius:1px;"></div>
        </div>'''

    def _kpi_card(self, label: str, value: str, sub: str = "", accent: str = B3) -> str:
        return f'''<div style="flex:1; background:{WHITE}; border-radius:6px; padding:12px 10px; text-align:center; border-top:2.5px solid {accent}; box-shadow:0 1px 3px rgba(0,0,0,0.06);">
            <div style="font-size:8px; color:{GRAY_500}; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.4px; font-family:sans-serif;">{label}</div>
            <div style="font-size:20px; font-weight:800; color:{NAVY}; line-height:1.2; font-family:sans-serif;">{value}</div>
            <div style="font-size:7.5px; color:{GRAY_500}; margin-top:3px; font-family:sans-serif;">{sub}</div>
        </div>'''

    def _insight_box(self, title: str, text: str) -> str:
        return f'''<div style="margin:12px 0; padding:10px 14px; background:#EEF2F7; border-left:3px solid {B2}; border-radius:0 4px 4px 0;">
            <div style="font-size:8px; font-weight:700; color:{B2}; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:3px; font-family:sans-serif;">{title}</div>
            <div style="font-size:9.5px; color:{NAVY}; line-height:1.55; font-family:sans-serif;">{text}</div>
        </div>'''

    def _ai_analysis_box(self, text: str) -> str:
        """AI 컨설턴트 분석 코멘터리 박스 — So What? + Implication"""
        if not text:
            return ""
        escaped = html_escape(text)
        return f'''<div style="margin:14px 0; padding:12px 16px; background:linear-gradient(135deg, #F0F4FA 0%, #E8EEF6 100%); border-left:4px solid {NAVY}; border-radius:0 6px 6px 0; box-shadow:0 1px 3px rgba(27,42,74,0.08);">
            <div style="display:flex; align-items:center; gap:6px; margin-bottom:5px;">
                <div style="width:18px; height:18px; background:{NAVY}; border-radius:4px; display:flex; align-items:center; justify-content:center;">
                    <span style="font-size:9px; font-weight:800; color:{WHITE}; font-family:sans-serif;">AI</span>
                </div>
                <span style="font-size:8px; font-weight:700; color:{NAVY}; text-transform:uppercase; letter-spacing:1px; font-family:sans-serif;">Consultant Analysis</span>
            </div>
            <div style="font-size:9.5px; color:{GRAY_900}; line-height:1.65; font-family:sans-serif;">{escaped}</div>
        </div>'''

    def _severity_badge(self, level: str) -> str:
        level_lower = level.lower() if level else "medium"
        if level_lower in ("high", "높음"):
            return f'<span style="display:inline-block; padding:1px 8px; border-radius:8px; font-size:8px; font-weight:600; background:#FEE2E2; color:{RED};">HIGH</span>'
        elif level_lower in ("low", "낮음"):
            return f'<span style="display:inline-block; padding:1px 8px; border-radius:8px; font-size:8px; font-weight:600; background:#D1FAE5; color:{GREEN};">LOW</span>'
        return f'<span style="display:inline-block; padding:1px 8px; border-radius:8px; font-size:8px; font-weight:600; background:#FEF3C7; color:{GOLD};">MED</span>'

    # ═══════════════════════════════════════════════════════════════════════════
    # Main HTML Builder
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_html(self, data: dict[str, Any], industry_name: str, ai_analysis: dict[str, str] | None = None, map_image_b64: Optional[str] = None) -> str:
        now = datetime.now()
        date_full = now.strftime("%Y년 %m월 %d일")
        date_short = now.strftime("%Y.%m.%d")

        recs = data.get("recommendations", [])
        charts = data.get("charts", [])
        comp = data.get("competitive")
        sim = data.get("simulation")
        ctx = data.get("context", {})
        timeline = data.get("timeline")
        trend = data.get("trend")
        programs = data.get("support_programs", [])

        ai = ai_analysis or {}

        pages = []
        page_num = 0

        # Page 1: Cover (no page number)
        pages.append(self._page_cover(industry_name, date_full, ctx, recs))

        # Page 2: Table of Contents
        page_num = 2
        toc_sections = self._build_toc_list(recs, charts, comp, sim, timeline, trend, programs)
        pages.append(self._page_toc(toc_sections, date_short, page_num))

        # Page 3: Executive Summary
        page_num = 3
        pages.append(self._page_exec_summary(recs, sim, comp, ctx, industry_name, date_short, page_num, ai_text=ai.get("executive_summary", "")))

        sec_num = 1
        page_num = 4

        # Page 4: Market Analysis
        if charts:
            pages.append(self._page_market(charts, recs, sec_num, date_short, page_num, ai_text=ai.get("market", "")))
            sec_num += 1
            page_num += 1

        # Page 5: Location Analysis
        if recs:
            pages.append(self._page_location(recs, sec_num, date_short, page_num, ai_text=ai.get("location", ""), map_image_b64=map_image_b64))
            sec_num += 1
            page_num += 1

        # Page 6: Financial Simulation — Revenue & P&L
        if sim:
            pages.append(self._page_sim_revenue(sim, sec_num, date_short, page_num, ai_text=ai.get("simulation", "")))
            page_num += 1
            # Page 7: Financial Simulation — Investment & Costs
            pages.append(self._page_sim_costs(sim, sec_num, date_short, page_num))
            sec_num += 1
            page_num += 1

        # Page 8: Competitive Analysis
        if comp:
            pages.append(self._page_competitive(comp, sec_num, date_short, page_num, ai_text=ai.get("competitive", "")))
            sec_num += 1
            page_num += 1

        # Page 9: Risk Assessment
        if sim or recs:
            pages.append(self._page_risk(sim, recs, sec_num, date_short, page_num, ai_text=ai.get("risk", "")))
            sec_num += 1
            page_num += 1

        # Page 10: Timeline
        if timeline:
            pages.append(self._page_timeline(timeline, sec_num, date_short, page_num))
            sec_num += 1
            page_num += 1

        # Page 11: Trend Analysis
        if trend and trend.get("trends"):
            pages.append(self._page_trend(trend, sec_num, date_short, page_num, ai_text=ai.get("trend", "")))
            sec_num += 1
            page_num += 1

        # Page 12: Support Programs
        if programs:
            pages.append(self._page_support(programs, sec_num, date_short, page_num))
            sec_num += 1
            page_num += 1

        # Page 13: Methodology & Sources
        pages.append(self._page_methodology(industry_name, date_full, date_short, page_num))
        page_num += 1

        # Page 14: Disclaimer
        pages.append(self._page_disclaimer(date_full))

        body = "\n".join(pages)

        return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>SpotPick 창업 분석 리포트</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
@page {{ size: A4; margin: 0; }}
body {{
    font-family: 'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif;
    color:{GRAY_900};
    line-height:1.45;
    font-size:11px;
    -webkit-print-color-adjust:exact;
    print-color-adjust:exact;
}}
.page {{
    width:210mm;
    height:297mm;
    padding:28mm 24mm 22mm 24mm;
    page-break-after:always;
    position:relative;
    overflow:hidden;
    display:flex;
    flex-direction:column;
}}
.page-content {{
    flex:1;
    display:flex;
    flex-direction:column;
}}
table {{ width:100%; border-collapse:collapse; font-size:9px; font-family:sans-serif; }}
th {{
    background:{NAVY};
    color:{WHITE};
    padding:6px 8px;
    text-align:left;
    font-weight:600;
    font-size:8px;
    text-transform:uppercase;
    letter-spacing:0.3px;
}}
td {{ padding:5px 8px; border-bottom:1px solid {GRAY_200}; font-size:9px; }}
tr:nth-child(even) td {{ background:{GRAY_50}; }}
svg {{ display:block; }}
</style>
</head>
<body>
{body}
</body>
</html>"""

    def _build_toc_list(self, recs, charts, comp, sim, timeline, trend, programs) -> list[dict]:
        items = []
        p = 3
        items.append({"title": "Executive Summary", "page": p})
        p += 1
        sec = 1
        if charts:
            items.append({"title": f"{sec}. 시장 분석 (Market Analysis)", "page": p})
            sec += 1; p += 1
        if recs:
            items.append({"title": f"{sec}. 입지 분석 (Location Analysis)", "page": p})
            sec += 1; p += 1
        if sim:
            items.append({"title": f"{sec}. 재무 시뮬레이션 - 매출/손익", "page": p})
            p += 1
            items.append({"title": f"   재무 시뮬레이션 - 투자/비용", "page": p})
            sec += 1; p += 1
        if comp:
            items.append({"title": f"{sec}. 경쟁 분석 (Competitive Analysis)", "page": p})
            sec += 1; p += 1
        if sim or recs:
            items.append({"title": f"{sec}. 리스크 평가 (Risk Assessment)", "page": p})
            sec += 1; p += 1
        if timeline:
            items.append({"title": f"{sec}. 창업 타임라인 (Timeline)", "page": p})
            sec += 1; p += 1
        if trend and trend.get("trends"):
            items.append({"title": f"{sec}. 트렌드 분석 (Trend Analysis)", "page": p})
            sec += 1; p += 1
        if programs:
            items.append({"title": f"{sec}. 정부지원사업 (Support Programs)", "page": p})
            sec += 1; p += 1
        items.append({"title": "분석 방법론 및 데이터 출처", "page": p})
        p += 1
        items.append({"title": "Disclaimer", "page": p})
        return items

    def _location_overview(self, recs: list) -> str:
        """추천 상권 위치 개요 — 시각적 카드"""
        if not recs:
            return ""
        cards = ""
        for i, rec in enumerate(recs[:3]):
            name = html_escape(rec.get("district_name", ""))
            dtype = html_escape(rec.get("district_type", ""))
            prob = rec.get("success_probability", 0)
            color = [B1, B2, B3][i]
            cards += f'''<div style="flex:1; padding:10px; background:{WHITE}; border-radius:6px; border:1px solid {GRAY_200}; text-align:center;">
            <div style="width:32px; height:32px; background:{color}; color:{WHITE}; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; font-family:sans-serif; margin:0 auto 6px;">{i+1}</div>
            <div style="font-size:11px; font-weight:700; color:{NAVY}; font-family:sans-serif;">{name}</div>
            <div style="font-size:8px; color:{GRAY_500}; font-family:sans-serif; margin-top:2px;">{dtype}</div>
            <div style="font-size:13px; font-weight:800; color:{color}; font-family:sans-serif; margin-top:4px;">{prob:.1f}%</div>
        </div>'''
        return f'<div style="display:flex; gap:10px; margin-bottom:14px;">{cards}</div>'

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Cover
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_cover(self, industry: str, date: str, ctx: dict, recs: list) -> str:
        district = ctx.get("district", recs[0].get("district_name", "서울") if recs else "서울")
        budget = ctx.get("budget", "")
        target = ctx.get("target", "")

        meta_lines = [f'<div style="font-size:11px; color:#94A3B8; font-family:sans-serif; margin-bottom:4px;">{date} 작성</div>']
        if budget:
            meta_lines.append(f'<div style="font-size:11px; color:#94A3B8; font-family:sans-serif; margin-bottom:4px;">투자 예산: {budget}</div>')
        if target:
            meta_lines.append(f'<div style="font-size:11px; color:#94A3B8; font-family:sans-serif; margin-bottom:4px;">타겟 고객: {target}</div>')
        meta_html = "".join(meta_lines)

        return f'''<div style="width:210mm; height:297mm; background:linear-gradient(160deg, {NAVY} 0%, #0F172A 50%, #1E293B 100%); page-break-after:always; position:relative; -webkit-print-color-adjust:exact; print-color-adjust:exact; overflow:hidden;">
        <div style="position:absolute; top:0; right:0; width:45%; height:100%; background:linear-gradient(135deg, {B3}12, {B3}04); clip-path:polygon(35% 0, 100% 0, 100% 100%, 0% 100%);"></div>
        <div style="position:absolute; bottom:0; left:0; width:100%; height:180px; background:linear-gradient(0deg, {B1}40, transparent);"></div>
        <div style="position:relative; z-index:1; padding:55mm 32mm 30mm 32mm;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:48px;">
                <div style="width:40px; height:40px; background:{B3}; border-radius:8px; display:flex; align-items:center; justify-content:center;">
                    <span style="font-size:16px; font-weight:800; color:{WHITE}; font-family:sans-serif;">SP</span>
                </div>
                <span style="font-size:13px; font-weight:600; color:{WHITE}; letter-spacing:3px; font-family:sans-serif;">SPOTPICK</span>
            </div>
            <div style="font-size:11px; color:{B4}; font-weight:600; letter-spacing:3px; text-transform:uppercase; margin-bottom:14px; font-family:sans-serif;">AI-Powered Market Analysis Report</div>
            <h1 style="font-size:36px; font-weight:800; color:{WHITE}; line-height:1.25; margin-bottom:10px; font-family:Georgia,'Noto Serif KR',serif;">{district} {industry} 창업<br/>시장 분석 리포트</h1>
            <div style="font-size:14px; color:#94A3B8; font-weight:300; margin-bottom:36px; font-family:sans-serif;">{district} 상권 데이터 기반 심층 분석</div>
            <div style="width:50px; height:2px; background:{B3}; border-radius:1px; margin-bottom:24px;"></div>
            {meta_html}
        </div>
        <div style="position:absolute; bottom:22mm; left:32mm; right:32mm; z-index:1;">
            <div style="border-top:1px solid #334155; padding-top:10px; display:flex; justify-content:space-between;">
                <span style="font-size:8px; color:#64748B; font-family:sans-serif;">Prepared by SpotPick AI Analysis Engine</span>
                <span style="font-size:8px; color:#64748B; font-family:sans-serif;">Confidential</span>
            </div>
        </div>
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Table of Contents
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_toc(self, items: list[dict], date_short: str, page_num: int) -> str:
        rows = ""
        for item in items:
            indent = "padding-left:12px;" if item["title"].startswith("   ") else ""
            title = item["title"].strip()
            rows += f'''<div style="display:flex; justify-content:space-between; align-items:baseline; padding:7px 0; border-bottom:1px dotted {GRAY_300}; {indent}">
                <span style="font-size:10px; color:{NAVY}; font-family:sans-serif;">{title}</span>
                <span style="font-size:10px; color:{GRAY_500}; font-family:sans-serif; flex-shrink:0; margin-left:12px;">{item["page"]}</span>
            </div>'''

        return f'''<div class="page">
        <div class="page-content">
            <div style="margin-bottom:24px;">
                <div style="font-size:10px; color:{B3}; font-weight:600; letter-spacing:2px; text-transform:uppercase; margin-bottom:6px; font-family:sans-serif;">CONTENTS</div>
                <h2 style="font-size:22px; font-weight:700; color:{NAVY}; font-family:Georgia,'Noto Serif KR',serif;">목차</h2>
                <div style="height:2px; width:40px; background:{B3}; margin-top:8px; border-radius:1px;"></div>
            </div>
            <div style="max-width:420px;">
                {rows}
            </div>
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Executive Summary
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_exec_summary(self, recs: list, sim: dict, comp: dict, ctx: dict, industry_name: str, date_short: str, page_num: int, ai_text: str = "") -> str:
        top = recs[0] if recs else {}
        top_district = top.get("district_name", "-")
        success_prob = top.get("success_probability", 0)
        scorecard = top.get("scorecard", {})
        percentile = scorecard.get("percentile", 0)

        monthly_sales = 0
        monthly_profit = 0
        margin = 0
        be_min = 0
        total_invest = 0
        survival = 0
        store_count = 0
        rent = 0

        if sim:
            rev = sim.get("revenue", {})
            monthly_sales = rev.get("monthly_sales_per_store", 0)
            be = sim.get("break_even", {})
            monthly_profit = be.get("monthly_net_profit", 0)
            margin = be.get("net_profit_margin", 0)
            be_min = be.get("break_even_months_min", 0)
            sc = sim.get("startup_cost", {})
            total_invest = sc.get("total_min", 0)
            competition = sim.get("competition", {})
            store_count = competition.get("store_count", 0)
            survival = competition.get("survival_rate", 0)
            op = sim.get("operating_cost", {})
            rent = op.get("rent", 0)

        total_comp = comp.get("total_nearby_cafes", store_count) if comp else store_count
        rent_ratio = f"{rent / monthly_sales * 100:.1f}" if monthly_sales and rent else "0"
        survival_vs_avg = f"+{survival - SEOUL_AVG_SURVIVAL_3Y:.0f}%p" if survival > SEOUL_AVG_SURVIVAL_3Y else f"{survival - SEOUL_AVG_SURVIVAL_3Y:.0f}%p"

        # KPI cards with benchmarks
        kpi1 = self._kpi_card("추천 1위", top_district, f"성공확률 {success_prob:.0f}% | 상위 {percentile:.0f}%", B2)
        kpi2 = self._kpi_card("월 예상 매출", self._fmt_won(monthly_sales), f"순이익 {self._fmt_won(monthly_profit)} (마진 {margin:.1f}%)", GREEN)
        kpi3 = self._kpi_card("투자 회수", f"{be_min:.0f}개월", f"투자금 {self._fmt_won(total_invest)}", B3)
        kpi4 = self._kpi_card("생존율", f"{survival:.0f}%", f"서울 평균 {SEOUL_AVG_SURVIVAL_3Y:.0f}% 대비 {survival_vs_avg}", GREEN if survival > SEOUL_AVG_SURVIVAL_3Y else RED)

        # Narrative
        findings = []
        if recs:
            names = ", ".join(r.get("district_name", "") for r in recs[:3])
            findings.append(f'분석 대상 {len(recs)}개 상권 중 <strong>{top_district}</strong>이 종합 {scorecard.get("total_score", 0):.1f}점(상위 {percentile:.0f}%)으로 최적 입지로 선정되었습니다. 후보 상권: {names}.')
        if monthly_sales:
            findings.append(f'월 예상 매출 <strong>{self._fmt_won(monthly_sales)}</strong>에서 운영비를 차감한 순이익은 <strong>{self._fmt_won(monthly_profit)}</strong>(마진율 {margin:.1f}%)이며, 초기 투자금 {self._fmt_won(total_invest)} 기준 <strong>{be_min:.0f}개월</strong> 내 회수가 가능합니다.')
        if total_comp:
            findings.append(f'반경 내 경쟁 매장 <strong>{total_comp}개</strong>가 분포하며, 임대료는 매출 대비 {rent_ratio}%입니다. 생존율 {survival:.0f}%는 서울 {industry_name} 평균({SEOUL_AVG_SURVIVAL_3Y:.0f}%) 대비 {survival_vs_avg} 수준입니다.')

        findings_html = ""
        for i, f in enumerate(findings):
            findings_html += f'<div style="padding:6px 0; font-size:9.5px; color:{GRAY_700}; line-height:1.55; font-family:sans-serif;"><span style="color:{B2}; font-weight:700;">{i+1}.</span> {f}</div>'

        # Scope box
        district_label = ctx.get("district", "서울 전역")
        budget_label = ctx.get("budget", "미지정")
        target_label = ctx.get("target", "전 연령")

        return f'''<div class="page">
        <div class="page-content">
            <div style="margin-bottom:14px;">
                <div style="font-size:10px; color:{B3}; font-weight:600; letter-spacing:2px; text-transform:uppercase; margin-bottom:4px; font-family:sans-serif;">EXECUTIVE SUMMARY</div>
                <h2 style="font-size:18px; font-weight:700; color:{NAVY}; font-family:Georgia,'Noto Serif KR',serif;">핵심 분석 요약</h2>
                <div style="height:2px; width:40px; background:{B3}; margin-top:6px; border-radius:1px;"></div>
            </div>

            <div style="display:flex; gap:8px; margin-bottom:14px;">
                {kpi1}{kpi2}{kpi3}{kpi4}
            </div>

            <div style="margin-bottom:12px;">
                <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px; font-family:sans-serif;">Key Findings</div>
                {findings_html}
            </div>

            {self._insight_box("RECOMMENDATION", f"{top_district} 상권은 매출 잠재력, 유동인구, 경쟁 강도를 종합적으로 고려할 때 가장 유망한 입지입니다. {industry_name} 창업 시 스페셜티/브런치 등 차별화 전략과 함께 피크타임 외 매출 확대 방안을 병행할 것을 권고합니다.")}

            {self._ai_analysis_box(ai_text)}

            <div style="margin-top:auto; padding:10px 14px; background:{GRAY_50}; border-radius:6px; border:1px solid {GRAY_200};">
                <div style="font-size:8px; font-weight:700; color:{GRAY_500}; text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px; font-family:sans-serif;">분석 범위 (Scope)</div>
                <div style="display:flex; gap:24px; font-size:9px; color:{GRAY_700}; font-family:sans-serif;">
                    <span><strong>지역:</strong> {district_label}</span>
                    <span><strong>예산:</strong> {budget_label}</span>
                    <span><strong>타겟:</strong> {target_label}</span>
                    <span><strong>기준일:</strong> {date_short}</span>
                </div>
            </div>
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Market Analysis
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_market(self, charts: list, recs: list, sec_num: int, date_short: str, page_num: int, ai_text: str = "") -> str:
        # Derive action title
        age_chart = next((c for c in charts if c.get("type") == "age"), None)
        time_chart = next((c for c in charts if c.get("type") == "time"), None)

        main_age = ""
        peak_time = ""
        peak_pct = 0
        if age_chart and age_chart.get("data"):
            top_age = max(age_chart["data"], key=lambda x: x.get("value", 0))
            main_age = top_age.get("name", "")
        if time_chart and time_chart.get("data"):
            top_time = max(time_chart["data"], key=lambda x: x.get("value", 0))
            peak_time = top_time.get("name", "")
            peak_pct = top_time.get("value", 0)

        action_title = f"{main_age}가 주 고객층이며 {peak_time} 매출 집중도가 {peak_pct}%"
        if not main_age:
            action_title = "고객 연령대 및 시간대별 매출 집중도 분석"

        charts_html = ""

        # Age donut
        if age_chart and age_chart.get("data"):
            segments = [{"value": d.get("value", 0), "label": d.get("name", ""), "color": CHART_6[i % len(CHART_6)]} for i, d in enumerate(age_chart["data"])]
            donut = self._svg_donut(segments, 140)
            legend = "".join(
                f'<div style="display:flex; align-items:center; gap:4px; margin-bottom:3px;">'
                f'<div style="width:8px; height:8px; border-radius:2px; background:{CHART_6[i % len(CHART_6)]};"></div>'
                f'<span style="font-size:8.5px; color:{GRAY_700}; font-family:sans-serif;">{d.get("name", "")} <strong>{d.get("value", 0)}%</strong></span></div>'
                for i, d in enumerate(age_chart["data"])
            )
            charts_html += f'''<div style="margin-bottom:14px;">
                <div style="font-size:11px; font-weight:700; color:{NAVY}; margin-bottom:8px; font-family:sans-serif;">연령대별 고객 분포</div>
                <div style="display:flex; align-items:center; gap:20px;">
                    <div>{donut}</div>
                    <div>{legend}</div>
                </div>
            </div>'''

        # Time bars
        if time_chart and time_chart.get("data"):
            items = [{"name": d.get("name", ""), "value": d.get("value", 0), "extra": f" ({self._fmt_won(d['sales'])})" if d.get("sales") else "%"} for d in time_chart["data"]]
            bar_svg = self._svg_horizontal_bars(items, width=440, bar_h=20, gap=5)
            charts_html += f'''<div style="margin-bottom:14px;">
                <div style="font-size:11px; font-weight:700; color:{NAVY}; margin-bottom:8px; font-family:sans-serif;">시간대별 매출 비중</div>
                {bar_svg}
            </div>'''

        # Day bars
        day_chart = next((c for c in charts if c.get("type") == "day"), None)
        if day_chart and day_chart.get("data"):
            items = [{"name": d.get("name", ""), "value": d.get("value", 0), "extra": "%"} for d in day_chart["data"]]
            bar_svg = self._svg_horizontal_bars(items, width=440, bar_h=18, gap=4)
            charts_html += f'''<div style="margin-bottom:10px;">
                <div style="font-size:11px; font-weight:700; color:{NAVY}; margin-bottom:8px; font-family:sans-serif;">요일별 매출 비중</div>
                {bar_svg}
            </div>'''

        return f'''<div class="page">
        <div class="page-content">
            {self._section_number(sec_num, action_title, "Market Analysis")}
            {charts_html}
            {self._ai_analysis_box(ai_text)}
            {self._source_footnote("서울 상권분석 서비스 / 소상공인시장진흥공단 (2025년 데이터)")}
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Location Analysis
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_location(self, recs: list, sec_num: int, date_short: str, page_num: int, ai_text: str = "", map_image_b64: Optional[str] = None) -> str:
        top = recs[0] if recs else {}
        sc = top.get("scorecard", {})
        action_title = f"{top.get('district_name', '')}이 종합 {sc.get('total_score', 0):.1f}점으로 최적 입지, 상위 {sc.get('percentile', 0):.0f}%"

        # 지도 이미지 HTML
        map_html = ""
        if map_image_b64:
            # 범례 (마커 색상 매핑)
            marker_colors_hex = ["#C02020", "#2050A0", "#1E7D4E"]
            legend_items = ""
            for i, rec in enumerate(recs[:3]):
                c = marker_colors_hex[i % len(marker_colors_hex)]
                name = html_escape(rec.get("district_name", ""))
                rank = rec.get("rank", i + 1)
                legend_items += f'''<span style="display:inline-flex; align-items:center; gap:3px; margin-right:10px;">
                    <span style="width:10px; height:10px; background:{c}; border-radius:50%; display:inline-block;"></span>
                    <span style="font-size:8px; color:{GRAY_700}; font-family:sans-serif;">#{rank} {name}</span>
                </span>'''

            map_html = f'''<div style="margin-bottom:12px;">
                <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:6px; font-family:sans-serif;">추천 상권 위치 지도</div>
                <div style="border:1px solid {GRAY_200}; border-radius:6px; overflow:hidden;">
                    <img src="data:image/png;base64,{map_image_b64}" style="width:100%; height:auto; display:block;" />
                    <div style="padding:6px 10px; background:{GRAY_50}; border-top:1px solid {GRAY_200};">
                        {legend_items}
                    </div>
                </div>
            </div>'''

        cards_html = ""
        for rec in recs[:3]:
            rank = rec.get("rank", 0)
            name = rec.get("district_name", "")
            dtype = rec.get("district_type", "")
            prob = rec.get("success_probability", 0)
            sales = rec.get("monthly_sales", 0)
            stores = rec.get("store_count", 0)
            survival = rec.get("survival_rate", 1.0)
            if isinstance(survival, float) and survival <= 1.0:
                survival_pct = survival * 100
            else:
                survival_pct = float(survival)
            traffic = rec.get("foot_traffic_total", 0)
            workers = rec.get("worker_total", 0)
            rent_est = rec.get("estimated_rent", 0)
            scorecard = rec.get("scorecard")

            badge_color = GREEN if prob >= 70 else (GOLD if prob >= 50 else RED)

            radar_html = ""
            if scorecard:
                cats = scorecard.get("categories", [])
                if isinstance(cats, list) and len(cats) >= 3:
                    radar_data = [{"name": c.get("name", ""), "score": c.get("score", 0), "max_score": 100} for c in cats]
                    radar_html = self._svg_radar(radar_data, 170)

            survival_vs = f"서울 평균 대비 +{survival_pct - SEOUL_AVG_SURVIVAL_3Y:.0f}%p" if survival_pct > SEOUL_AVG_SURVIVAL_3Y else f"서울 평균 대비 {survival_pct - SEOUL_AVG_SURVIVAL_3Y:.0f}%p"

            metrics_html = f'''<div style="display:flex; gap:6px; margin-top:6px; flex-wrap:wrap;">
                <div style="flex:1; min-width:65px; background:{GRAY_50}; padding:5px 6px; border-radius:3px; text-align:center; border:1px solid {GRAY_200};">
                    <div style="font-size:7px; color:{GRAY_500}; font-family:sans-serif;">월매출</div>
                    <div style="font-size:11px; font-weight:700; color:{NAVY}; font-family:sans-serif;">{self._fmt(sales)}</div>
                </div>
                <div style="flex:1; min-width:65px; background:{GRAY_50}; padding:5px 6px; border-radius:3px; text-align:center; border:1px solid {GRAY_200};">
                    <div style="font-size:7px; color:{GRAY_500}; font-family:sans-serif;">매장수</div>
                    <div style="font-size:11px; font-weight:700; color:{NAVY}; font-family:sans-serif;">{stores}개</div>
                </div>
                <div style="flex:1; min-width:65px; background:{GRAY_50}; padding:5px 6px; border-radius:3px; text-align:center; border:1px solid {GRAY_200};">
                    <div style="font-size:7px; color:{GRAY_500}; font-family:sans-serif;">유동인구</div>
                    <div style="font-size:11px; font-weight:700; color:{NAVY}; font-family:sans-serif;">{self._fmt_num(traffic)}명</div>
                </div>
                <div style="flex:1; min-width:65px; background:{GRAY_50}; padding:5px 6px; border-radius:3px; text-align:center; border:1px solid {GRAY_200};">
                    <div style="font-size:7px; color:{GRAY_500}; font-family:sans-serif;">직장인구</div>
                    <div style="font-size:11px; font-weight:700; color:{NAVY}; font-family:sans-serif;">{self._fmt_num(workers)}명</div>
                </div>
                <div style="flex:1; min-width:65px; background:{GRAY_50}; padding:5px 6px; border-radius:3px; text-align:center; border:1px solid {GRAY_200};">
                    <div style="font-size:7px; color:{GRAY_500}; font-family:sans-serif;">생존율</div>
                    <div style="font-size:11px; font-weight:700; color:{GREEN if survival_pct > 60 else RED}; font-family:sans-serif;">{survival_pct:.0f}%</div>
                </div>
            </div>
            <div style="font-size:7px; color:{GRAY_400}; margin-top:3px; font-family:sans-serif;">예상 임대료 {self._fmt_won(rent_est)}/월 | {survival_vs}</div>'''

            card_left = f'''<div style="flex:1;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <div style="width:22px; height:22px; background:{NAVY}; color:{WHITE}; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:10px; font-weight:700; font-family:sans-serif;">#{rank}</div>
                    <span style="font-size:13px; font-weight:700; color:{NAVY}; font-family:sans-serif;">{name}</span>
                    <span style="font-size:8px; color:{GRAY_500}; font-family:sans-serif;">{dtype}</span>
                    <span style="display:inline-block; padding:1px 8px; border-radius:8px; font-size:8px; font-weight:600; background:{"#D1FAE5" if prob >= 70 else "#FEF3C7" if prob >= 50 else "#FEE2E2"}; color:{badge_color};">{prob:.1f}%</span>
                </div>
                {metrics_html}
            </div>'''

            radar_section = ""
            if radar_html:
                sc_total = scorecard.get("total_score", 0)
                sc_pctile = scorecard.get("percentile", 0)
                radar_section = f'''<div style="width:180px; flex-shrink:0; text-align:center;">
                    {radar_html}
                    <div style="font-size:8px; color:{GRAY_500}; font-family:sans-serif;">종합 {sc_total:.1f}점 | 상위 {sc_pctile:.0f}%</div>
                </div>'''

            cards_html += f'''<div style="border:1px solid {GRAY_200}; border-radius:6px; padding:10px 12px; margin-bottom:8px;">
                <div style="display:flex; gap:12px; align-items:flex-start;">
                    {card_left}
                    {radar_section}
                </div>
            </div>'''

        return f'''<div class="page">
        <div class="page-content">
            {self._section_number(sec_num, action_title, "Location Analysis")}
            {map_html}
            {self._location_overview(recs)}
            {cards_html}
            {self._ai_analysis_box(ai_text)}
            {self._source_footnote("서울 상권분석 서비스 / 소상공인시장진흥공단 (2025년 데이터)")}
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Simulation — Revenue & P&L
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_sim_revenue(self, sim: dict, sec_num: int, date_short: str, page_num: int, ai_text: str = "") -> str:
        district = sim.get("district_name", "")
        rev = sim.get("revenue", {})
        monthly_sales = rev.get("monthly_sales_per_store", 0)
        daily_sales = rev.get("daily_sales", 0)
        avg_ticket = rev.get("avg_ticket", 0)
        pessimistic = rev.get("pessimistic", 0)
        optimistic = rev.get("optimistic", 0)
        peak_sales = rev.get("peak_time_sales", 0)
        peak_time = rev.get("peak_time", "")
        txns = rev.get("monthly_transactions_per_store", 0)

        op = sim.get("operating_cost", {})
        rent = op.get("rent", 0)
        labor = op.get("labor", 0)
        cogs = op.get("cogs", op.get("materials", 0))
        utilities = op.get("utilities", 0)
        other = op.get("other", 0)
        total_op = op.get("total", rent + labor + cogs + utilities + other)

        be = sim.get("break_even", {})
        net_profit = be.get("monthly_net_profit", monthly_sales - total_op)
        margin = be.get("net_profit_margin", (net_profit / monthly_sales * 100) if monthly_sales else 0)
        be_min = be.get("break_even_months_min", 0)
        be_max = be.get("break_even_months_max", 0)

        action_title = f"월 순이익 {self._fmt(net_profit)}원, 투자금 {be_min:.0f}개월 내 회수 가능"

        # Waterfall
        waterfall_items = [
            {"label": "매출", "value": monthly_sales, "type": "total"},
            {"label": "임대료", "value": rent, "type": "subtract"},
            {"label": "인건비", "value": labor, "type": "subtract"},
            {"label": "원재료", "value": cogs, "type": "subtract"},
            {"label": "기타", "value": utilities + other, "type": "subtract"},
            {"label": "순이익", "value": net_profit, "type": "total"},
        ]
        waterfall = self._svg_waterfall(waterfall_items, 460, 175)

        # Revenue metrics table
        rent_ratio = f"{rent / monthly_sales * 100:.1f}" if monthly_sales else "0"
        rev_table = f'''<table style="margin-top:10px;">
            <tr><th style="width:40%;">지표</th><th style="text-align:right;">금액</th><th style="text-align:right;">비고</th></tr>
            <tr><td>월 매출</td><td style="text-align:right; font-weight:600;">{self._fmt_won(monthly_sales)}</td><td style="text-align:right; color:{GRAY_500};">일 {self._fmt_won(daily_sales)}</td></tr>
            <tr><td>월 거래 건수</td><td style="text-align:right; font-weight:600;">{txns:,}건</td><td style="text-align:right; color:{GRAY_500};">객단가 {int(avg_ticket):,}원</td></tr>
            <tr><td>피크타임 매출</td><td style="text-align:right; font-weight:600;">{self._fmt_won(peak_sales)}</td><td style="text-align:right; color:{GRAY_500};">{peak_time}</td></tr>
            <tr><td>임대료 비율</td><td style="text-align:right; font-weight:600;">{rent_ratio}%</td><td style="text-align:right; color:{GRAY_500};">매출 대비</td></tr>
            <tr><td>순이익률</td><td style="text-align:right; font-weight:700; color:{GREEN if margin > 20 else GOLD};">{margin:.1f}%</td><td style="text-align:right; color:{GRAY_500};">{self._fmt_won(net_profit)}/월</td></tr>
        </table>'''

        # Scenario comparison
        pess_delta = ((pessimistic - monthly_sales) / monthly_sales * 100) if monthly_sales else 0
        opt_delta = ((optimistic - monthly_sales) / monthly_sales * 100) if monthly_sales else 0
        scenario = f'''<div style="display:flex; gap:6px; margin:10px 0;">
            <div style="flex:1; padding:8px; background:#F5F0F0; border-radius:4px; text-align:center; border:1px solid #E8D8D8;">
                <div style="font-size:7px; color:{RED}; font-weight:700; text-transform:uppercase; font-family:sans-serif;">Pessimistic</div>
                <div style="font-size:14px; font-weight:800; color:{RED}; font-family:sans-serif;">{self._fmt_won(pessimistic)}</div>
                <div style="font-size:7px; color:{GRAY_500}; font-family:sans-serif;">기본 대비 {pess_delta:.0f}%</div>
            </div>
            <div style="flex:1; padding:8px; background:#EEF2F7; border-radius:4px; text-align:center; border:1px solid #C5D5EA;">
                <div style="font-size:7px; color:{B2}; font-weight:700; text-transform:uppercase; font-family:sans-serif;">Base Case</div>
                <div style="font-size:14px; font-weight:800; color:{B1}; font-family:sans-serif;">{self._fmt_won(monthly_sales)}</div>
                <div style="font-size:7px; color:{GRAY_500}; font-family:sans-serif;">예상 시나리오</div>
            </div>
            <div style="flex:1; padding:8px; background:#EDF5ED; border-radius:4px; text-align:center; border:1px solid #C5DFC5;">
                <div style="font-size:7px; color:{GREEN}; font-weight:700; text-transform:uppercase; font-family:sans-serif;">Optimistic</div>
                <div style="font-size:14px; font-weight:800; color:{GREEN}; font-family:sans-serif;">{self._fmt_won(optimistic)}</div>
                <div style="font-size:7px; color:{GRAY_500}; font-family:sans-serif;">기본 대비 +{opt_delta:.0f}%</div>
            </div>
        </div>'''

        return f'''<div class="page">
        <div class="page-content">
            {self._section_number(sec_num, action_title, f"Financial Simulation -- Revenue & P&L | {district}")}

            <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:6px; font-family:sans-serif;">월간 손익 구조 (P&L Waterfall)</div>
            {waterfall}

            <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:4px; margin-top:8px; font-family:sans-serif;">시나리오별 매출 전망</div>
            {scenario}

            <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:4px; margin-top:6px; font-family:sans-serif;">주요 매출 지표</div>
            {rev_table}

            {self._ai_analysis_box(ai_text)}
            {self._source_footnote("SpotPick AI 분석 모델 기반 추정치 / 서울 상권분석 서비스")}
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Simulation — Investment & Costs
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_sim_costs(self, sim: dict, sec_num: int, date_short: str, page_num: int) -> str:
        sc = sim.get("startup_cost", {})
        deposit = sc.get("deposit", 0)
        interior = sc.get("interior", 0)
        equip_min = sc.get("equipment_min", 0)
        equip_max = sc.get("equipment_max", 0)
        inv_min = sc.get("initial_inventory_min", 0)
        inv_max = sc.get("initial_inventory_max", 0)
        permits_min = sc.get("permits_misc_min", 0)
        permits_max = sc.get("permits_misc_max", 0)
        total_min = sc.get("total_min", 0)
        total_max = sc.get("total_max", 0)
        area = sc.get("area_pyeong", 0)
        grade = sc.get("interior_grade", "")

        op = sim.get("operating_cost", {})
        rent = op.get("rent", 0)
        labor = op.get("labor", 0)
        cogs = op.get("cogs", op.get("materials", 0))
        utilities = op.get("utilities", 0)
        other_op = op.get("other", 0)
        total_op = op.get("total", rent + labor + cogs + utilities + other_op)

        rev = sim.get("revenue", {})
        monthly_sales = rev.get("monthly_sales_per_store", 0)

        be = sim.get("break_even", {})
        margin = be.get("net_profit_margin", 0)
        be_min = be.get("break_even_months_min", 0)
        be_max = be.get("break_even_months_max", 0)

        # Startup cost donut
        segs = [
            {"value": deposit, "label": "보증금", "color": CHART_COLORS[0]},
            {"value": interior, "label": "인테리어", "color": CHART_COLORS[1]},
            {"value": equip_min, "label": "장비/설비", "color": CHART_COLORS[2]},
            {"value": inv_min, "label": "초기 재고", "color": CHART_COLORS[3]},
            {"value": permits_min, "label": "인허가/기타", "color": CHART_COLORS[4]},
        ]
        segs = [s for s in segs if s["value"] > 0]
        donut = self._svg_donut(segs, 120)
        legend = "".join(
            f'<div style="display:flex; align-items:center; gap:4px; margin-bottom:2px;">'
            f'<div style="width:7px; height:7px; border-radius:1px; background:{s["color"]};"></div>'
            f'<span style="font-size:8px; color:{GRAY_700}; font-family:sans-serif;">{s["label"]} {self._fmt_won(s["value"])}</span></div>'
            for s in segs
        )

        # Startup cost table
        startup_table = f'''<table style="margin-top:6px;">
            <tr><th>항목</th><th style="text-align:right;">최소</th><th style="text-align:right;">최대</th></tr>
            <tr><td>보증금</td><td style="text-align:right;">{self._fmt_won(deposit)}</td><td style="text-align:right;">{self._fmt_won(deposit)}</td></tr>
            <tr><td>인테리어 ({grade}, {area}평)</td><td style="text-align:right;">{self._fmt_won(interior)}</td><td style="text-align:right;">{self._fmt_won(interior)}</td></tr>
            <tr><td>장비/설비</td><td style="text-align:right;">{self._fmt_won(equip_min)}</td><td style="text-align:right;">{self._fmt_won(equip_max)}</td></tr>
            <tr><td>초기 재고</td><td style="text-align:right;">{self._fmt_won(inv_min)}</td><td style="text-align:right;">{self._fmt_won(inv_max)}</td></tr>
            <tr><td>인허가/기타</td><td style="text-align:right;">{self._fmt_won(permits_min)}</td><td style="text-align:right;">{self._fmt_won(permits_max)}</td></tr>
            <tr style="background:{NAVY}08;"><td style="font-weight:700;">합계</td><td style="text-align:right; font-weight:800; color:{NAVY};">{self._fmt_won(total_min)}</td><td style="text-align:right; font-weight:800; color:{NAVY};">{self._fmt_won(total_max)}</td></tr>
        </table>'''

        # Operating cost table with % of revenue
        def _op_row(name, val):
            pct = f"{val / monthly_sales * 100:.1f}%" if monthly_sales else "-"
            return f'<tr><td>{name}</td><td style="text-align:right; font-weight:600;">{self._fmt_won(val)}</td><td style="text-align:right; color:{GRAY_500};">{pct}</td></tr>'

        op_table = f'''<table style="margin-top:6px;">
            <tr><th>항목</th><th style="text-align:right;">월 비용</th><th style="text-align:right;">매출 대비</th></tr>
            {_op_row("임대료", rent)}
            {_op_row("인건비", labor)}
            {_op_row("원재료비(COGS)", cogs)}
            {_op_row("공과금", utilities)}
            {_op_row("기타 비용", other_op)}
            <tr style="background:{NAVY}08;"><td style="font-weight:700;">합계</td><td style="text-align:right; font-weight:800; color:{NAVY};">{self._fmt_won(total_op)}</td><td style="text-align:right; font-weight:700; color:{NAVY};">{self._pct_of(total_op, monthly_sales)}</td></tr>
        </table>'''

        # Menu cost table
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
                cat = it.get("category", "")
                mr_color = GREEN if mr >= 70 else (GOLD if mr >= 50 else RED)
                rows += f'<tr><td>{n}</td><td style="color:{GRAY_500};">{cat}</td><td style="text-align:right;">{int(sp):,}원</td><td style="text-align:right;">{int(cost):,}원</td><td style="text-align:right; font-weight:700; color:{mr_color};">{mr:.1f}%</td></tr>'
            avg_m = mc.get("avg_margin_rate", 0)
            menu_html = f'''<div style="margin-top:10px;">
                <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:4px; font-family:sans-serif;">메뉴별 원가 분석</div>
                <table><tr><th>메뉴</th><th>분류</th><th style="text-align:right;">판매가</th><th style="text-align:right;">원가</th><th style="text-align:right;">마진율</th></tr>{rows}
                <tr style="background:{NAVY}08;"><td colspan="4" style="font-weight:700;">평균 마진율</td><td style="text-align:right; font-weight:800; color:{B2};">{avg_m:.1f}%</td></tr></table>
            </div>'''

        # Break-even gauge
        gauge = self._svg_gauge(margin, 100, 100, "순이익률")

        return f'''<div class="page">
        <div class="page-content">
            <div style="margin-bottom:14px;">
                <div style="font-size:9px; color:{B3}; font-weight:600; letter-spacing:1px; text-transform:uppercase; margin-bottom:2px; font-family:sans-serif;">SECTION {sec_num:02d} (cont.)</div>
                <h2 style="font-size:14px; font-weight:700; color:{NAVY}; margin:0; font-family:Georgia,'Noto Serif KR',serif;">초기 투자 및 운영 비용 분석</h2>
                <div style="height:2px; width:40px; background:{B3}; margin-top:5px; border-radius:1px;"></div>
            </div>

            <div style="display:flex; gap:14px; margin-bottom:8px;">
                <div style="flex:1;">
                    <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:4px; font-family:sans-serif;">초기 투자 비용</div>
                    <div style="display:flex; align-items:center; gap:10px;">
                        {donut}
                        <div>{legend}<div style="margin-top:4px; font-size:9px; font-weight:700; color:{NAVY}; font-family:sans-serif;">총 {self._fmt_won(total_min)} ~ {self._fmt_won(total_max)}</div></div>
                    </div>
                </div>
                <div style="width:110px; text-align:center; padding-top:6px;">
                    {gauge}
                    <div style="margin-top:2px; font-size:8px; color:{NAVY}; font-weight:600; font-family:sans-serif;">BEP {be_min:.0f}~{be_max:.0f}개월</div>
                </div>
            </div>

            {startup_table}

            <div style="margin-top:10px;">
                <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:4px; font-family:sans-serif;">월 운영 비용</div>
                {op_table}
            </div>

            {menu_html}

            {self._source_footnote("SpotPick AI 분석 모델 기반 추정치")}
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Competitive Analysis
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_competitive(self, comp: dict, sec_num: int, date_short: str, page_num: int, ai_text: str = "") -> str:
        total = comp.get("total_nearby_cafes", comp.get("total_competitors", 0))
        cafe_types = comp.get("cafe_types", [])
        gaps = comp.get("market_gaps", [])
        strategies = comp.get("strategies", [])
        competitors = comp.get("top_competitors", [])

        franchise_ratio = 0
        for ct in cafe_types:
            if ct.get("type", "").lower() == "franchise":
                franchise_ratio = ct.get("ratio", 0)

        gap_label = gaps[0].get("gap_type", "틈새") if gaps else "차별화"
        action_title = f"경쟁 매장 {total}개 중 프랜차이즈 {franchise_ratio:.0f}%, {gap_label} 틈새 존재"

        # Donut
        segments = [{"value": ct.get("count", 0), "label": self._translate_cafe_type(ct.get("type", "")), "color": CHART_COLORS[i % len(CHART_COLORS)]} for i, ct in enumerate(cafe_types)]
        donut = self._svg_donut(segments, 130)
        legend = "".join(
            f'<div style="display:flex; align-items:center; gap:4px; margin-bottom:2px;">'
            f'<div style="width:7px; height:7px; border-radius:1px; background:{CHART_COLORS[i % len(CHART_COLORS)]};"></div>'
            f'<span style="font-size:8px; color:{GRAY_700}; font-family:sans-serif;">{self._translate_cafe_type(ct.get("type", ""))} {ct.get("count", 0)}개 ({ct.get("ratio", 0):.0f}%)</span></div>'
            for i, ct in enumerate(cafe_types)
        )

        # Type table
        type_rows = ""
        for ct in cafe_types:
            tn = self._translate_cafe_type(ct.get("type", ""))
            ex = ", ".join(ct.get("examples", [])[:3])
            type_rows += f'<tr><td>{tn}</td><td style="text-align:right;">{ct.get("count", 0)}개</td><td style="text-align:right; font-weight:600; color:{B2};">{ct.get("ratio", 0):.1f}%</td><td style="color:{GRAY_500};">{ex}</td></tr>'

        # Market gaps
        gap_cards = ""
        for g in gaps:
            if isinstance(g, dict):
                score = g.get("opportunity_score", 0)
                color = GREEN if score >= 70 else GOLD
                gap_cards += f'''<div style="padding:6px 8px; margin-bottom:4px; background:{WHITE}; border-radius:3px; border-left:3px solid {color};">
                    <div style="font-size:9px; font-weight:600; color:{NAVY}; font-family:sans-serif;">{g.get("gap_type", "")}</div>
                    <div style="font-size:8px; color:{GRAY_500}; font-family:sans-serif;">{g.get("description", "")}</div>
                    <div style="font-size:7px; color:{color}; font-weight:600; margin-top:1px; font-family:sans-serif;">기회점수 {score}/100</div>
                </div>'''

        # Strategies
        strat_cards = ""
        for s in strategies:
            if isinstance(s, dict):
                p = s.get("priority", "medium")
                p_kr = {"high": "높음", "medium": "중간", "low": "낮음"}.get(p, p)
                strat_cards += f'''<div style="padding:6px 8px; margin-bottom:4px; background:{WHITE}; border-radius:3px; border-left:3px solid {B3};">
                    <div style="font-size:9px; font-weight:600; color:{NAVY}; font-family:sans-serif;">{s.get("strategy", "")} <span style="font-size:7px; padding:1px 5px; background:{GRAY_100}; border-radius:6px; color:{GRAY_700};">우선순위: {p_kr}</span></div>
                    <div style="font-size:8px; color:{GRAY_500}; font-family:sans-serif;">{s.get("reason", "")}</div>
                </div>'''

        return f'''<div class="page">
        <div class="page-content">
            {self._section_number(sec_num, action_title, "Competitive Analysis")}

            <div style="display:flex; gap:16px; margin-bottom:12px;">
                <div style="flex:1;">
                    <div style="font-size:9px; color:{GRAY_500}; margin-bottom:4px; font-family:sans-serif;">총 경쟁 매장 수</div>
                    <div style="font-size:26px; font-weight:800; color:{NAVY}; margin-bottom:8px; font-family:sans-serif;">{total}<span style="font-size:11px; font-weight:400; color:{GRAY_500};">개</span></div>
                    <table><tr><th>업태</th><th style="text-align:right;">수</th><th style="text-align:right;">비율</th><th>대표 브랜드</th></tr>{type_rows}</table>
                </div>
                <div style="width:160px; text-align:center; padding-top:14px;">
                    {donut}
                    <div style="margin-top:6px;">{legend}</div>
                </div>
            </div>

            <div style="display:flex; gap:10px; margin-top:8px;">
                <div style="flex:1; padding:10px; background:#EEF2F7; border-radius:6px;">
                    <div style="font-size:9px; font-weight:700; color:{B2}; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px; font-family:sans-serif;">Market Gaps (시장 기회)</div>
                    {gap_cards}
                </div>
                <div style="flex:1; padding:10px; background:{GRAY_50}; border-radius:6px;">
                    <div style="font-size:9px; font-weight:700; color:{B2}; margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px; font-family:sans-serif;">Strategies (차별화 전략)</div>
                    {strat_cards}
                </div>
            </div>

            {self._ai_analysis_box(ai_text)}
            {self._source_footnote("서울 상권분석 서비스 / SpotPick AI 경쟁 분석 모델")}
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Risk Assessment
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_risk(self, sim: dict, recs: list, sec_num: int, date_short: str, page_num: int, ai_text: str = "") -> str:
        risks = []

        # From simulation risk_summary
        if sim:
            for r in sim.get("risk_summary", []):
                if isinstance(r, str):
                    severity = "HIGH" if any(w in r for w in ["심화", "상승", "높"]) else "MED"
                    risks.append({"factor": "시장/운영", "description": r, "severity": severity})
                elif isinstance(r, dict):
                    risks.append(r)

            # Competition risks
            comp_data = sim.get("competition", {})
            if comp_data.get("franchise_ratio", 0) > 30:
                risks.append({"factor": "경쟁 강도", "description": f"프랜차이즈 비율 {comp_data.get('franchise_ratio', 0):.0f}%로 브랜드 경쟁이 치열합니다.", "severity": "HIGH"})
            new_stores = comp_data.get("new_stores", 0)
            if new_stores > 5:
                risks.append({"factor": "신규 진입", "description": f"최근 1년 신규 매장 {new_stores}개 개업으로 시장 포화 우려가 있습니다.", "severity": "MED"})

        # From recommendation risk_factors
        for rec in recs[:3]:
            for rf in rec.get("risk_factors", []):
                if rf not in [r.get("description", "") for r in risks]:
                    risks.append({"factor": rec.get("district_name", ""), "description": rf, "severity": "MED"})

        # Build table
        risk_rows = ""
        for r in risks:
            if isinstance(r, dict):
                factor = r.get("factor", "일반")
                desc = r.get("description", str(r))
                sev = r.get("severity", "MED")
            else:
                factor = "일반"
                desc = str(r)
                sev = "MED"
            risk_rows += f'<tr><td style="font-weight:600; color:{NAVY}; width:18%;">{factor}</td><td>{self._severity_badge(sev)}</td><td>{desc}</td></tr>'

        high_count = sum(1 for r in risks if (r.get("severity", "") if isinstance(r, dict) else "").upper() in ("HIGH", "높음"))
        med_count = sum(1 for r in risks if (r.get("severity", "") if isinstance(r, dict) else "").upper() in ("MED", "MEDIUM", "중간"))
        low_count = len(risks) - high_count - med_count

        return f'''<div class="page">
        <div class="page-content">
            {self._section_number(sec_num, f"총 {len(risks)}건의 리스크 식별, 주요 {high_count}건 고위험", "Risk Assessment")}

            <div style="display:flex; gap:8px; margin-bottom:14px;">
                <div style="flex:1; padding:10px; background:#FEF2F2; border-radius:6px; text-align:center; border:1px solid #FECACA;">
                    <div style="font-size:20px; font-weight:800; color:{RED}; font-family:sans-serif;">{high_count}</div>
                    <div style="font-size:8px; color:{RED}; font-weight:600; font-family:sans-serif;">HIGH RISK</div>
                </div>
                <div style="flex:1; padding:10px; background:#FFFBEB; border-radius:6px; text-align:center; border:1px solid #FDE68A;">
                    <div style="font-size:20px; font-weight:800; color:{GOLD}; font-family:sans-serif;">{med_count}</div>
                    <div style="font-size:8px; color:{GOLD}; font-weight:600; font-family:sans-serif;">MEDIUM</div>
                </div>
                <div style="flex:1; padding:10px; background:#F0FDF4; border-radius:6px; text-align:center; border:1px solid #BBF7D0;">
                    <div style="font-size:20px; font-weight:800; color:{GREEN}; font-family:sans-serif;">{low_count}</div>
                    <div style="font-size:8px; color:{GREEN}; font-weight:600; font-family:sans-serif;">LOW RISK</div>
                </div>
            </div>

            <table>
                <tr><th style="width:18%;">영역</th><th style="width:12%;">심각도</th><th>설명</th></tr>
                {risk_rows}
            </table>

            {self._insight_box("RISK MITIGATION", "고위험 항목에 대해서는 사전 대비 전략을 반드시 수립해야 합니다. 임대료 상승 리스크는 장기 계약 및 권리금 협상으로, 경쟁 심화 리스크는 명확한 차별화 포지셔닝으로 대응할 것을 권고합니다.")}

            {self._ai_analysis_box(ai_text)}
            {self._source_footnote("SpotPick AI 리스크 분석 모델 / 서울 상권분석 서비스")}
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Timeline
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_timeline(self, timeline: dict, sec_num: int, date_short: str, page_num: int) -> str:
        stages = timeline.get("stages", [])
        total_weeks = timeline.get("total_weeks", 0)
        fast = timeline.get("fast_estimate_months", "")
        slow = timeline.get("slow_estimate_months", "")

        if not stages:
            return ""

        longest = max(stages, key=lambda s: s.get("duration_weeks", 0))
        action_title = f"총 {total_weeks}주 소요, {longest.get('name', '')}이 {longest.get('duration_weeks', 0)}주로 최장 단계"

        gantt = self._svg_gantt(stages, total_weeks, 460)

        # Stage details table
        detail_rows = ""
        for i, stage in enumerate(stages):
            overlap = "가능" if stage.get("can_overlap") else "-"
            detail_rows += f'''<tr>
                <td style="font-weight:600; color:{NAVY};">{stage.get("name", "")}</td>
                <td style="text-align:center;">{stage.get("duration_weeks", 0)}주</td>
                <td style="text-align:center;">{stage.get("start_week", 0)}~{stage.get("end_week", 0)}주차</td>
                <td style="text-align:center;">{overlap}</td>
                <td style="color:{GRAY_500};">{stage.get("description", "")}</td>
            </tr>'''

        estimate = f"빠른 진행 시 {fast}개월, 일반적으로 {slow}개월" if fast and slow else f"약 {total_weeks}주"

        return f'''<div class="page">
        <div class="page-content">
            {self._section_number(sec_num, action_title, "Startup Timeline")}

            <div style="display:flex; gap:10px; margin-bottom:12px;">
                <div style="flex:1; padding:10px 14px; background:{GRAY_50}; border-radius:6px; text-align:center; border:1px solid {GRAY_200};">
                    <div style="font-size:8px; color:{B2}; font-weight:600; text-transform:uppercase; font-family:sans-serif;">총 예상 기간</div>
                    <div style="font-size:22px; font-weight:800; color:{NAVY}; font-family:sans-serif;">{total_weeks}주</div>
                    <div style="font-size:8px; color:{GRAY_500}; font-family:sans-serif;">{estimate}</div>
                </div>
                <div style="flex:1; padding:10px 14px; background:{GRAY_50}; border-radius:6px; text-align:center; border:1px solid {GRAY_200};">
                    <div style="font-size:8px; color:{B2}; font-weight:600; text-transform:uppercase; font-family:sans-serif;">핵심 단계</div>
                    <div style="font-size:14px; font-weight:700; color:{NAVY}; font-family:sans-serif;">{longest.get("name", "")}</div>
                    <div style="font-size:8px; color:{GRAY_500}; font-family:sans-serif;">{longest.get("duration_weeks", 0)}주 소요</div>
                </div>
            </div>

            <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:6px; font-family:sans-serif;">Gantt Chart</div>
            {gantt}

            <div style="margin-top:12px;">
                <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:4px; font-family:sans-serif;">단계별 세부 내용</div>
                <table>
                    <tr><th>단계</th><th style="text-align:center;">기간</th><th style="text-align:center;">일정</th><th style="text-align:center;">병행</th><th>내용</th></tr>
                    {detail_rows}
                </table>
            </div>

            {self._source_footnote("SpotPick AI 타임라인 추정 모델")}
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Trend Analysis
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_trend(self, trend: dict, sec_num: int, date_short: str, page_num: int, ai_text: str = "") -> str:
        trends = trend.get("trends", [])
        if not trends:
            return ""

        summary = trend.get("summary", {})
        top_kw = summary.get("top_keyword", "")
        top_avg = summary.get("top_average", 0)
        action_title = f"'{top_kw}'이 평균 {top_avg:.0f}으로 최고 검색 관심도" if top_kw else "키워드 검색 트렌드 분석"

        # Bar chart
        items = [{"name": t.get("keyword", ""), "value": t.get("average_ratio", 0)} for t in trends]
        bar_svg = self._svg_horizontal_bars(items, 440, 22, 5)

        # Line chart
        line_chart = self._svg_line_chart(trends, 440, 140)

        # Legend
        legend = " ".join(
            f'<span style="display:inline-flex; align-items:center; gap:3px; margin-right:10px;">'
            f'<span style="width:10px; height:2px; background:{CHART_COLORS[i % len(CHART_COLORS)]}; border-radius:1px;"></span>'
            f'<span style="font-size:8px; color:{GRAY_700}; font-family:sans-serif;">{t.get("keyword", "")}</span></span>'
            for i, t in enumerate(trends)
        )

        # Data table
        first = trends[0]
        data_pts = first.get("data", [])
        h_cols = "".join(f'<th style="text-align:right;">{t.get("keyword", "")}</th>' for t in trends)
        rows = ""
        for idx, pt in enumerate(data_pts[:8]):
            period = pt.get("period", "")
            cells = ""
            for t in trends:
                dl = t.get("data", [])
                val = dl[idx].get("ratio", 0) if idx < len(dl) else 0
                cells += f'<td style="text-align:right;">{val:.0f}</td>'
            rows += f'<tr><td>{period}</td>{cells}</tr>'

        period_info = trend.get("period", {})
        period_str = f'{period_info.get("start", "")} ~ {period_info.get("end", "")}' if period_info else ""

        return f'''<div class="page">
        <div class="page-content">
            {self._section_number(sec_num, action_title, f"Trend Analysis | {period_str}")}

            <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:6px; font-family:sans-serif;">키워드별 평균 검색 관심도</div>
            {bar_svg}

            <div style="font-size:10px; font-weight:700; color:{NAVY}; margin:12px 0 4px; font-family:sans-serif;">기간별 트렌드 추이</div>
            <div style="margin-bottom:4px;">{legend}</div>
            {line_chart}

            <div style="font-size:10px; font-weight:700; color:{NAVY}; margin:10px 0 4px; font-family:sans-serif;">상세 데이터</div>
            <table><tr><th>기간</th>{h_cols}</tr>{rows}</table>

            {self._ai_analysis_box(ai_text)}
            {self._source_footnote("네이버 데이터랩 / Google Trends (검색 관심도 지수, 100 = 최고치)")}
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Support Programs
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_support(self, programs: list, sec_num: int, date_short: str, page_num: int) -> str:
        urgent = sum(1 for p in programs if (p.get("days_until_deadline") or 999) <= 30)
        action_title = f"신청 가능 {len(programs)}건, 마감 임박 {urgent}건 우선 대응 필요" if urgent else f"신청 가능한 정부지원사업 {len(programs)}건"

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
                if days <= 7:
                    badge = f'<span style="display:inline-block; padding:1px 6px; border-radius:6px; font-size:7px; font-weight:600; background:#FEE2E2; color:{RED};">D-{days}</span>'
                elif days <= 30:
                    badge = f'<span style="display:inline-block; padding:1px 6px; border-radius:6px; font-size:7px; font-weight:600; background:#FEF3C7; color:{GOLD};">D-{days}</span>'
                else:
                    badge = f'<span style="display:inline-block; padding:1px 6px; border-radius:6px; font-size:7px; font-weight:600; background:#DBEAFE; color:{B2};">D-{days}</span>'

            rows += f'''<tr>
                <td><strong style="color:{NAVY};">{name}</strong><br/><span style="font-size:7px; color:{GRAY_500};">{cat}</span></td>
                <td style="text-align:right; font-weight:600; color:{B2};">{amount}</td>
                <td style="text-align:center;">{end_date} {badge}</td>
                <td style="color:{GRAY_500};">{org}</td>
            </tr>'''

        urgent_note = ""
        if urgent:
            urgent_note = f'''<div style="padding:8px 12px; background:#FEF2F2; border:1px solid #FECACA; border-radius:4px; margin-bottom:10px; font-size:9px; font-family:sans-serif;">
                <strong style="color:{RED};">마감 임박 {urgent}건</strong> -- 30일 이내 마감되는 지원사업이 있습니다. 조기 신청을 권고합니다.
            </div>'''

        return f'''<div class="page">
        <div class="page-content">
            {self._section_number(sec_num, action_title, "Government Support Programs")}
            {urgent_note}
            <table>
                <tr><th>사업명 / 분류</th><th style="text-align:right;">지원금액</th><th style="text-align:center;">마감일</th><th>주관기관</th></tr>
                {rows}
            </table>

            <div style="margin-top:14px; padding:10px 14px; background:{GRAY_50}; border-radius:6px; border:1px solid {GRAY_200};">
                <div style="font-size:8px; font-weight:700; color:{GRAY_500}; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px; font-family:sans-serif;">신청 안내</div>
                <div style="font-size:8px; color:{GRAY_700}; line-height:1.6; font-family:sans-serif;">
                    1. 각 지원사업의 신청 자격 및 조건은 주관기관 홈페이지에서 확인하시기 바랍니다.<br/>
                    2. 사업자등록증, 사업계획서 등 필요 서류를 미리 준비하세요.<br/>
                    3. 마감일 최소 1주일 전에 신청을 완료하는 것을 권장합니다.
                </div>
            </div>

            {self._source_footnote("중소벤처기업부 / 소상공인시장진흥공단 / 서울시 (" + date_short + " 기준)")}
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Methodology & Sources
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_methodology(self, industry: str, date_full: str, date_short: str, page_num: int) -> str:
        return f'''<div class="page">
        <div class="page-content">
            <div style="margin-bottom:16px;">
                <div style="font-size:10px; color:{B3}; font-weight:600; letter-spacing:2px; text-transform:uppercase; margin-bottom:4px; font-family:sans-serif;">APPENDIX</div>
                <h2 style="font-size:16px; font-weight:700; color:{NAVY}; font-family:Georgia,'Noto Serif KR',serif;">분석 방법론 및 데이터 출처</h2>
                <div style="height:2px; width:40px; background:{B3}; margin-top:6px; border-radius:1px;"></div>
            </div>

            <div style="margin-bottom:16px;">
                <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:6px; font-family:sans-serif;">1. 데이터 출처 (Data Sources)</div>
                <table>
                    <tr><th style="width:35%;">데이터</th><th>출처</th><th style="width:20%;">기준</th></tr>
                    <tr><td>상권 매출/업종 통계</td><td>서울시 우리마을가게 상권분석 서비스 (서울 열린데이터광장)</td><td>2024~2025</td></tr>
                    <tr><td>유동인구 데이터</td><td>서울시 생활인구 데이터 / SK Telecom 유동인구</td><td>2024~2025</td></tr>
                    <tr><td>점포 개폐업 현황</td><td>소상공인시장진흥공단 상권정보시스템</td><td>2024~2025</td></tr>
                    <tr><td>임대료 시세</td><td>한국부동산원 상업용부동산 임대동향 / 상권정보시스템</td><td>2024~2025</td></tr>
                    <tr><td>업종별 원가 구조</td><td>소상공인시장진흥공단 업종별 경영 실태조사</td><td>2024</td></tr>
                    <tr><td>검색 트렌드</td><td>네이버 데이터랩 / Google Trends</td><td>최근 12개월</td></tr>
                    <tr><td>정부지원사업</td><td>중소벤처기업부 / 소상공인시장진흥공단 / 서울시</td><td>{date_full} 기준</td></tr>
                </table>
            </div>

            <div style="margin-bottom:16px;">
                <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:6px; font-family:sans-serif;">2. 분석 방법론 (Methodology)</div>
                <div style="font-size:9px; color:{GRAY_700}; line-height:1.6; font-family:sans-serif;">
                    <p style="margin-bottom:6px;"><strong>입지 평가 모델:</strong> 매출 잠재력(30%), 유동인구(20%), 경쟁강도(20%), 생존율(15%), 성장성(15%) 가중 합산 스코어카드 방식으로 상권을 평가합니다. 각 항목은 서울시 전체 상권 대비 백분위(percentile)로 정규화됩니다.</p>
                    <p style="margin-bottom:6px;"><strong>매출 추정:</strong> 해당 상권 동일 업종 점포의 평균 매출 데이터를 기반으로 하며, 면적, 좌석수, 객단가를 반영한 보정 계수를 적용합니다. 시나리오 분석은 표준편차 기반 상/하한을 산출합니다.</p>
                    <p style="margin-bottom:6px;"><strong>비용 추정:</strong> 업종별 표준 원가율, 지역별 임대료 시세, 인건비 기준(최저시급 기반) 등 공식 통계를 적용합니다.</p>
                    <p style="margin-bottom:6px;"><strong>경쟁 분석:</strong> 반경 500m 내 동일 업종 점포를 분류하고, 프랜차이즈 비율, 업태별 분포, 개폐업 추이를 종합하여 시장 기회를 도출합니다.</p>
                    <p><strong>리스크 평가:</strong> 임대료 변동성, 경쟁 강도, 시장 포화도, 계절성 등 다변수를 분석하여 HIGH/MEDIUM/LOW 등급으로 분류합니다.</p>
                </div>
            </div>

            <div style="margin-bottom:16px;">
                <div style="font-size:10px; font-weight:700; color:{NAVY}; margin-bottom:6px; font-family:sans-serif;">3. 주요 가정 (Key Assumptions)</div>
                <div style="font-size:9px; color:{GRAY_700}; line-height:1.6; font-family:sans-serif;">
                    <p style="margin-bottom:4px;">- 서울 {industry} 평균 3년 생존율: {SEOUL_AVG_SURVIVAL_3Y:.0f}% (소상공인시장진흥공단 기준)</p>
                    <p style="margin-bottom:4px;">- 영업일수: 월 30일 기준 (무휴 운영 가정)</p>
                    <p style="margin-bottom:4px;">- 인건비: 사업주 1인 + 아르바이트 기준</p>
                    <p style="margin-bottom:4px;">- 모든 금액은 부가세 별도 기준</p>
                    <p>- 본 분석은 통계 데이터 기반 추정치이며, 개별 상황에 따라 실제 결과는 상이할 수 있습니다.</p>
                </div>
            </div>

            <div style="margin-top:auto; padding:8px 12px; background:{GRAY_50}; border-radius:4px; border:1px solid {GRAY_200};">
                <div style="font-size:7px; color:{GRAY_400}; line-height:1.6; font-family:sans-serif;">
                    분석 엔진: SpotPick AI v2.0 | 분석 기준일: {date_full} | 리포트 생성: {datetime.now().strftime("%Y-%m-%d %H:%M")}
                </div>
            </div>
        </div>
        {self._footer(date_short, page_num)}
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Page: Disclaimer
    # ═══════════════════════════════════════════════════════════════════════════

    def _page_disclaimer(self, date: str) -> str:
        return f'''<div class="page" style="display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center;">
        <div style="max-width:380px;">
            <div style="width:40px; height:40px; background:{B3}; border-radius:8px; display:flex; align-items:center; justify-content:center; margin:0 auto 18px;">
                <span style="font-size:16px; font-weight:800; color:{WHITE}; font-family:sans-serif;">SP</span>
            </div>
            <h2 style="font-size:18px; font-weight:700; color:{NAVY}; margin-bottom:14px; font-family:Georgia,'Noto Serif KR',serif;">SpotPick</h2>
            <div style="width:40px; height:2px; background:{B3}; margin:0 auto 18px; border-radius:1px;"></div>
            <p style="font-size:9px; color:{GRAY_500}; line-height:1.8; margin-bottom:18px; font-family:sans-serif;">
                본 리포트는 SpotPick AI 분석 엔진이 공공 데이터 및 통계를 기반으로<br/>
                생성한 참고용 분석 자료입니다.<br/><br/>
                실제 창업 의사결정 시에는 반드시 현장 조사 및<br/>
                전문가 상담을 병행하시기 바랍니다.<br/><br/>
                본 자료에 포함된 수치, 예측, 분석 결과는 통계적 추정치이며,<br/>
                실제 결과와 차이가 발생할 수 있습니다.<br/><br/>
                본 리포트의 무단 복제, 배포를 금합니다.
            </p>
            <div style="border-top:1px solid {GRAY_200}; padding-top:14px; margin-top:10px;">
                <p style="font-size:8px; color:{GRAY_400}; font-family:sans-serif;">데이터 기준일: {date}</p>
                <p style="font-size:8px; color:{GRAY_400}; margin-top:4px; font-family:sans-serif;">AI가 골라주는 나만의 창업 자리</p>
                <p style="font-size:7px; color:{GRAY_400}; margin-top:8px; font-family:sans-serif;">&copy; 2026 SpotPick. All rights reserved. Confidential.</p>
            </div>
        </div>
    </div>'''

    # ═══════════════════════════════════════════════════════════════════════════
    # Utility
    # ═══════════════════════════════════════════════════════════════════════════

    def _translate_cafe_type(self, t: str) -> str:
        return {
            "specialty": "스페셜티",
            "franchise": "프랜차이즈",
            "dessert": "디저트",
            "takeout": "테이크아웃",
            "bakery": "베이커리",
            "general": "일반",
        }.get(t.lower(), t)


# Singleton
_pdf_service: Optional[PDFService] = None


def get_pdf_service() -> PDFService:
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service
