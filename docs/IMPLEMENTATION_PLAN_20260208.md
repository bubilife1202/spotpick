# SpotPick 긴급 개선 기획안
> 작성일: 2026-02-08 | 마감: 2026-02-19 | 버전: v0.7.0 목표

---

## 현황 진단

| 항목 | 상태 | 문제 |
|------|------|------|
| 차별화 전달 | ❌ | 랜딩페이지에서 "왜 SpotPick인가" 3초 안에 안 보임 |
| 트랙션 수집 | ❌ | 애널리틱스 코드 0줄. 사용 데이터 전무 |
| 수익모델 | ❌ | 전체 무료. 프리미엄 개념 없음. 심사위원 질문 대비 불가 |

---

## 1. 차별화 전달 — 랜딩 페이지 리디자인

### 1-1. 문제 정의

현재 랜딩: "어떤 창업을 생각하고 계세요?" + 3개 입구 버튼
→ **기능 나열일 뿐, 왜 써야 하는지 모름**

### 1-2. 개선 설계

#### A. 히어로 섹션 (Above the fold)

```
[Before]
"어떤 창업을 생각하고 계세요?"
[지도] [조건] [AI]

[After]
"창업, 감으로 하지 마세요"
서울 1,077개 상권 데이터 + AI가 분석하는
업종 선택부터 사업계획서까지 5분 완성

[핵심 수치 3개]
┌──────────┐ ┌──────────┐ ┌──────────┐
│ 1,077개  │ │   10개   │ │  5분     │
│ 분석 상권 │ │ 지원 업종 │ │ 플랜 완성 │
└──────────┘ └──────────┘ └──────────┘

[CTA] "무료로 분석 시작하기"
```

#### B. Before/After 비교 섹션 (스크롤 다운)

```
┌─────────────────────────────────────────────┐
│  기존 상권분석                SpotPick       │
│  ──────────                ──────────       │
│  ❌ 데이터만 나열           ✅ AI가 해석     │
│  ❌ 분석에서 끝             ✅ 사업계획서까지 │
│  ❌ 전문가 수준 필요        ✅ 대화형 질문   │
│  ❌ 시뮬레이션 없음         ✅ 수익 시뮬     │
│  ❌ 1주일 소요              ✅ 5분 완성      │
└─────────────────────────────────────────────┘
```

#### C. 5단계 여정 미리보기 섹션

```
① 업종 선택 → ② AI 입지 추천 → ③ 상세 분석 → ④ 수익 시뮬 → ⑤ 사업계획서
   (10개 업종)   (1,077개 상권)   (6개 리포트)   (비관~낙관)    (PDF 다운로드)
```

각 단계 클릭 시 해당 화면 스크린샷/목업 표시

#### D. 기존 3개 입구 버튼 유지 (하단 이동)

현재 "지도에서 찾기 / 조건으로 찾기 / AI에게 물어보기" 카드는 히어로 아래로 이동

### 1-3. 구현 범위

| 파일 | 작업 |
|------|------|
| `/web/src/app/page.tsx` (LandingPage) | 히어로 텍스트 변경, 수치 배지 3개 추가, Before/After 섹션 추가, 5단계 프리뷰 추가 |
| `/web/src/app/globals.css` | 카운트업 애니메이션, 스크롤 reveal 애니메이션 |

### 1-4. 구현 상세

**히어로 컴포넌트 구조:**
```tsx
function HeroSection() {
  return (
    <section className="text-center pt-12 pb-8">
      {/* 메인 카피 */}
      <h2 className="text-3xl font-bold">
        창업, 감으로 하지 마세요
      </h2>
      <p className="text-slate-500 mt-3">
        서울 1,077개 상권 데이터 + AI가 분석하는<br/>
        업종 선택부터 사업계획서까지 5분 완성
      </p>

      {/* 핵심 수치 */}
      <div className="grid grid-cols-3 gap-4 mt-8 max-w-sm mx-auto">
        <StatBadge number="1,077" label="분석 상권" />
        <StatBadge number="10" label="지원 업종" />
        <StatBadge number="5분" label="플랜 완성" />
      </div>

      {/* 메인 CTA */}
      <button className="mt-8 px-8 py-4 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-2xl text-lg font-bold shadow-xl">
        무료로 분석 시작하기
      </button>
    </section>
  );
}
```

**Before/After 섹션:**
```tsx
function ComparisonSection() {
  const rows = [
    { before: "데이터만 나열", after: "AI가 해석해서 전략 제시" },
    { before: "분석에서 끝", after: "사업계획서까지 원스톱" },
    { before: "전문가 수준 필요", after: "대화형으로 누구나" },
    { before: "시뮬레이션 없음", after: "수익 시뮬레이션 내장" },
    { before: "보고서 작성 1주일", after: "AI가 5분 만에 완성" },
  ];
  // 좌: ❌ 기존 / 우: ✅ SpotPick 비교 테이블
}
```

**5단계 프리뷰:**
```tsx
function JourneyPreview() {
  const steps = [
    { num: 1, title: "업종 선택", desc: "10개 업종 중 선택", icon: Search },
    { num: 2, title: "AI 입지 추천", desc: "1,077개 상권 분석", icon: MapPin },
    { num: 3, title: "상세 분석", desc: "6개 분석 리포트", icon: BarChart3 },
    { num: 4, title: "수익 시뮬", desc: "비관~낙관 시나리오", icon: SlidersHorizontal },
    { num: 5, title: "사업계획서", desc: "PDF 다운로드", icon: FileText },
  ];
  // 가로 스크롤 카드 or 세로 타임라인
}
```

---

## 2. 트랙션 수집 — 이벤트 트래킹 시스템

### 2-1. 문제 정의

- 애널리틱스 코드 0줄
- 사용자 행동 데이터 전무
- 엑셀러레이터에 보여줄 트랙션 지표 없음

### 2-2. 설계 원칙

- **외부 의존성 최소화**: GA 대신 자체 경량 트래킹
- **백엔드 1개 엔드포인트**: `POST /api/v1/analytics/event`
- **프론트 1개 유틸**: `trackEvent(name, props)` 함수
- **대시보드 불필요**: 백엔드 로그 + 간단한 조회 API면 충분

### 2-3. 추적할 이벤트

| 이벤트명 | 발생 시점 | 속성 |
|----------|----------|------|
| `page_view` | 페이지 로드 | `{ page, referrer }` |
| `journey_start` | 랜딩 CTA 클릭 | `{ entry_type: "map" \| "condition" \| "ai" \| "smart_search" }` |
| `industry_select` | 업종 선택 | `{ industry_code }` |
| `district_select` | 상권 선택 | `{ district_code, source: "results" \| "explore" \| "chat" }` |
| `report_view` | 보고서 조회 | `{ district_code, industry_code }` |
| `simulation_run` | 시뮬레이터 실행 | `{ district_code, industry_code }` |
| `plan_generate` | 사업계획서 생성 | `{ district_code, industry_code }` |
| `plan_download` | PDF 다운로드 | `{ district_code, industry_code }` |
| `journey_complete` | 5단계 완료 | `{ total_time_sec, industry_code }` |
| `chat_message` | 채팅 메시지 전송 | `{ message_count }` |
| `compare_open` | 비교 모달 오픈 | `{ item_count }` |

### 2-4. 구현 설계

#### A. 프론트엔드 유틸 (`/web/src/lib/analytics.ts`)

```typescript
// 경량 이벤트 트래킹 — 외부 의존성 없음
const ANALYTICS_ENDPOINT = "/api/v1/analytics/event";

interface EventProps {
  [key: string]: string | number | boolean | undefined;
}

// 세션 ID (탭 단위)
let sessionId: string | null = null;
function getSessionId(): string {
  if (!sessionId) {
    sessionId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }
  return sessionId;
}

export function trackEvent(name: string, props?: EventProps) {
  if (typeof window === "undefined") return;

  const payload = {
    event: name,
    session_id: getSessionId(),
    timestamp: new Date().toISOString(),
    page: window.location.pathname,
    props: props || {},
  };

  // Fire-and-forget — 실패해도 UX에 영향 없음
  navigator.sendBeacon?.(
    ANALYTICS_ENDPOINT,
    JSON.stringify(payload)
  ) || fetch(ANALYTICS_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {});
}

// 페이지뷰 자동 추적 훅
export function usePageView(page: string) {
  useEffect(() => {
    trackEvent("page_view", { page });
  }, [page]);
}
```

#### B. 백엔드 엔드포인트 (`/api/routes/analytics.py`)

```python
from fastapi import APIRouter, Request
from pydantic import BaseModel
from datetime import datetime
import json, os

router = APIRouter(prefix="/analytics", tags=["analytics"])

class AnalyticsEvent(BaseModel):
    event: str
    session_id: str
    timestamp: str
    page: str
    props: dict = {}

# 파일 기반 로깅 (DB 불필요, 간단)
LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "analytics_logs")
os.makedirs(LOG_DIR, exist_ok=True)

@router.post("/event")
async def track_event(event: AnalyticsEvent, request: Request):
    log_entry = {
        **event.dict(),
        "ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", ""),
        "received_at": datetime.utcnow().isoformat(),
    }

    # 일별 로그 파일
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"{date_str}.jsonl")

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return {"ok": True}

@router.get("/summary")
async def get_summary():
    """간단한 집계 — 엑셀러레이터 발표용 수치"""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"{today}.jsonl")

    if not os.path.exists(log_file):
        return {"total_events": 0, "unique_sessions": 0, "events": {}}

    events = {}
    sessions = set()
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                name = entry.get("event", "unknown")
                events[name] = events.get(name, 0) + 1
                sessions.add(entry.get("session_id"))
            except:
                pass

    return {
        "date": today,
        "total_events": sum(events.values()),
        "unique_sessions": len(sessions),
        "events": events,
    }
```

#### C. 이벤트 삽입 위치

| 파일 | 위치 | 이벤트 |
|------|------|--------|
| `page.tsx` | `LandingPage` mount | `page_view` |
| `page.tsx` | `saveAndNavigate()` | `journey_start` |
| `page.tsx` | `handleSend()` | `chat_message` |
| `results/page.tsx` | mount | `page_view` |
| `explore/page.tsx` | `handleDistrictClick()` | `district_select` |
| `report/page.tsx` | mount | `report_view` |
| `simulator/page.tsx` | 슬라이더 변경 시 | `simulation_run` |
| `business-plan/page.tsx` | 생성 완료 시 | `plan_generate` |
| `PDFExportButton.tsx` | 다운로드 완료 시 | `plan_download` |
| `results/page.tsx` | 비교 모달 오픈 | `compare_open` |

---

## 3. 수익모델 가시화 — 프리미엄 티어 설계

### 3-1. 문제 정의

- 모든 기능 무료 → 심사위원 "돈은 어떻게 벌어?" 질문 대비 불가
- 수익모델이 제품 안에서 안 보임

### 3-2. 설계 원칙

- **실제 결제 구현 불필요** (데모 단계)
- **프리미엄 개념만 UI에 가시화**
- **무료 사용은 유지**하되 "프리미엄이면 이것까지 가능" 표시
- 사용자 flow를 방해하지 않는 soft paywall

### 3-3. 무료 vs 프리미엄 구분

```
┌─────────────────────────────────────────────────────┐
│              무료 (Free)        프리미엄 (Pro)       │
│  ─────────────────────    ─────────────────────     │
│  ✅ 상권 추천 TOP 5       ✅ 상권 추천 전체         │
│  ✅ 기본 분석 보고서       ✅ 심층 분석 + AI 코멘트  │
│  ✅ 기본 시뮬레이션        ✅ 시나리오 비교 저장     │
│  ❌ 사업계획서 1회/일      ✅ 무제한 생성            │
│  ❌ PDF 다운로드 제한      ✅ PDF 무제한 다운로드     │
│  ❌ 비교 분석 2개          ✅ 비교 분석 5개          │
│  ❌ -                     ✅ 상권 변동 알림          │
│  ❌ -                     ✅ 우선 AI 응답            │
└─────────────────────────────────────────────────────┘

가격안: 월 9,900원 / 연 79,000원 (33% 할인)
```

### 3-4. UI 구현 — 프리미엄 넛지 포인트 4개

#### A. 사업계획서 생성 후 — 업그레이드 배너

```
┌──────────────────────────────────────────┐
│  ⭐ 오늘 무료 생성 1/1회 사용           │
│                                          │
│  Pro 업그레이드 시:                      │
│  • 무제한 사업계획서 생성                │
│  • 상세 재무 시뮬레이션                  │
│  • 상권 변동 실시간 알림                 │
│                                          │
│  [월 9,900원으로 시작하기]               │
│                                          │
│  ✕ 다음에 할게요                        │
└──────────────────────────────────────────┘
```

위치: `business-plan/page.tsx` — 사업계획서 생성 완료 후 하단

#### B. 비교 모달 — 3개 초과 시

```
┌──────────────────────────────────────────┐
│  🔒 Pro에서는 최대 5개 상권 비교 가능    │
│  [업그레이드]  [무료로 계속 (2개)]       │
└──────────────────────────────────────────┘
```

위치: `results/page.tsx` — CompareBar에서 MAX_COMPARE 도달 시

#### C. PDF 다운로드 — 프리미엄 배지

```
┌──────────────────────────────────────────┐
│  [📄 PDF 다운로드]  ⭐ Pro              │
│  무료 체험: 오늘 1회 남음               │
└──────────────────────────────────────────┘
```

위치: `report/page.tsx`, `business-plan/page.tsx` — PDF 버튼 옆

#### D. 랜딩 페이지 — 가격 섹션

```
┌──────────────────────────────────────────┐
│           요금제                          │
│                                          │
│  ┌─────────┐    ┌─────────────┐         │
│  │  무료    │    │  ⭐ Pro     │         │
│  │         │    │             │         │
│  │  ₩0     │    │ ₩9,900/월  │         │
│  │         │    │             │         │
│  │ 기본분석 │    │ 무제한 분석 │         │
│  │ 1일1회  │    │ PDF 무제한  │         │
│  │ 비교 2개│    │ 비교 5개   │         │
│  │         │    │ 변동 알림  │         │
│  │ [시작]  │    │ [시작하기] │         │
│  └─────────┘    └─────────────┘         │
│                                          │
│  * 현재 베타 기간 전체 무료              │
└──────────────────────────────────────────┘
```

위치: `page.tsx` LandingPage — 5단계 프리뷰 섹션 아래

### 3-5. 구현 범위

| 파일 | 작업 |
|------|------|
| `/web/src/lib/premium.ts` | `isPremium()`, `getRemainingUsage()`, `PremiumBanner` 컴포넌트 (localStorage 기반 카운터) |
| `/web/src/app/page.tsx` | 가격 섹션 추가 |
| `/web/src/app/business-plan/page.tsx` | 생성 후 업그레이드 배너 |
| `/web/src/app/results/page.tsx` | 비교 제한 넛지 |
| `/web/src/components/PDFExportButton.tsx` | Pro 배지 표시 |

### 3-6. 프리미엄 상태 관리 (데모용)

```typescript
// /web/src/lib/premium.ts

// 베타 기간: 실제 결제 없이 모든 기능 열림
// UI에만 프리미엄 개념을 보여주되, 기능은 차단하지 않음
const BETA_MODE = true;

export function isPremium(): boolean {
  if (BETA_MODE) return true; // 베타 기간 전체 무료
  return localStorage.getItem("spotpick_premium") === "true";
}

export function getDailyUsage(feature: string): number {
  const key = `spotpick_usage_${feature}_${new Date().toISOString().slice(0, 10)}`;
  return parseInt(localStorage.getItem(key) || "0");
}

export function incrementUsage(feature: string) {
  const key = `spotpick_usage_${feature}_${new Date().toISOString().slice(0, 10)}`;
  const current = getDailyUsage(feature);
  localStorage.setItem(key, String(current + 1));
}

// 무료 한도
export const FREE_LIMITS = {
  plan_generate: 1,    // 사업계획서 1일 1회
  pdf_download: 1,     // PDF 1일 1회
  compare_items: 3,    // 비교 3개 (기존 MAX_COMPARE)
};
```

핵심: `BETA_MODE = true`로 실제 기능 차단 없음. **UI에서만 프리미엄 개념 표시.**

---

## 4. 구현 순서 및 예상 시간

```
Phase 1: 랜딩 페이지 리디자인 (2~3시간)
├─ 히어로 섹션 (메인 카피 + 수치 배지 + CTA)
├─ Before/After 비교 섹션
├─ 5단계 여정 프리뷰
└─ 가격 섹션

Phase 2: 애널리틱스 시스템 (1~2시간)
├─ /web/src/lib/analytics.ts 생성
├─ /api/routes/analytics.py 생성
├─ 주요 페이지에 trackEvent 삽입 (11개 이벤트)
└─ /api/v1/analytics/summary 엔드포인트

Phase 3: 프리미엄 넛지 UI (1~2시간)
├─ /web/src/lib/premium.ts 생성
├─ 사업계획서 업그레이드 배너
├─ 비교 제한 넛지
└─ PDF Pro 배지
```

총 예상: **4~7시간**

---

## 5. 성공 기준

| 지표 | 목표 |
|------|------|
| 랜딩 → 분석 시작 전환율 | 측정 가능 상태 (현재 0%) |
| 여정 완료율 (5단계) | 측정 가능 상태 |
| PDF 다운로드 수 | 측정 가능 상태 |
| 수익모델 질문 대응 | "월 9,900원 구독 모델, 베타 기간 무료" 답변 가능 |
| 차별점 질문 대응 | "원스톱 AI 창업 분석 — 분석에서 끝나지 않고 계획서까지" |

---

## 6. 엑셀러레이터 심사 대비 핵심 메시지

**문제**: 예비 창업자의 67%가 입지 선정에 실패하고, 상권분석에 평균 2주+50만원 소요

**솔루션**: SpotPick — 서울 1,077개 상권을 AI가 분석, 5분 만에 업종 선택부터 사업계획서까지 원스톱

**차별점**:
1. 데이터 → 액션: 분석에서 끝나지 않고 시뮬레이션 + 사업계획서까지
2. AI 대화형: "강남에서 카페 8천만원"이면 즉시 맞춤 분석
3. 5단계 여정: 업종→입지→분석→시뮬→플랜, 한 번에 해결

**비즈모델**: 프리미엄 구독 월 9,900원 (무제한 분석 + PDF + 알림)

**트랙션**: [배포 후 수치 삽입] 일 사용자 수, 여정 완료율, PDF 다운로드 수
