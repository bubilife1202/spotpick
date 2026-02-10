# SpotPick v0.7.0 — 해시드 바이브랩스 합격 기획안
> 작성일: 2026-02-08 | 제출 마감: 2026-02-19 (D-11)
> 제출물: 제품 URL + 데모 + 간단한 설명

---

## 0. 바이브랩스 심사 기준 → SpotPick 대응 전략

**바이브랩스는 피치덱을 안 봅니다. 제품 URL과 운영 데이터를 봅니다.**

| 심사 기준 | 의미 | SpotPick 대응 |
|----------|------|-------------|
| ① AI 네이티브 사고방식 | AI를 보조도구가 아닌 공동창업자로 활용 | 제품: Gemini가 분석·계획서 생성. 개발: Claude Code로 전체 개발. **둘 다 AI 네이티브** |
| ② 배포 빈도·속도 | 얼마나 자주 배포하는가 | D-11 동안 매일 배포. Git log가 증거. v0.6.1 → v0.7.0 |
| ③ 반복 개선 속도·질 | 피드백 → 개선 루프가 빠른가 | 평가 피드백(66.9점) → 즉시 반영 → 사용자 데이터 수집 → 재개선 |
| ④ 작업 분해·AI 위임 | 작업을 AI에게 효과적으로 맡기는가 | 데이터 분석 = Gemini, 계획서 생성 = Gemini, 코드 작성 = Claude Code |
| ⑤ 오류·실패 복구 | 장애 대응 능력 | 에러 바운더리, 폴백 로직, 헬스체크 API 이미 존재 |
| ⑥ 실행 루프 안정성 | 지속 가능한 개발·운영 사이클 | 프로덕션 배포 + 애널리틱스 + 일일 개선 루프 구축 |

---

## 1. 제출 전략

### 1-1. 제출물 구성

바이브랩스 제출: **제품 URL + 데모 + 간단한 설명**

```
┌─ 제출물 ─────────────────────────────────────────────┐
│                                                       │
│  1. 제품 URL                                          │
│     https://spotpick.kr (프로덕션 배포 URL)            │
│                                                       │
│  2. 데모                                              │
│     1분 스크린 레코딩:                                 │
│     업종선택 → 프랜차이즈비교 → 입지추천 → 분석        │
│     → 시뮬레이션 → 지원금매칭 → 사업계획서 PDF         │
│     "7단계를 실제로 5분 만에 완주하는 영상"            │
│                                                       │
│  3. 설명 (200자)                                      │
│     "SpotPick — 창업 의사결정 AI 플랫폼.              │
│     서울 1,077개 상권 × 10개 업종.                     │
│     업종선택부터 사업계획서까지 7단계 원스톱.           │
│     프랜차이즈 vs 독립 비교(공정위 API),               │
│     수익 시뮬레이션, 정부지원 23개 매칭, PDF 생성.     │
│     전체 AI 네이티브 — 제품은 Gemini,                  │
│     개발은 Claude Code. 1인 개발 11일 완성."           │
│                                                       │
└───────────────────────────────────────────────────────┘
```

### 1-2. 심사위원이 URL 클릭했을 때 보여야 하는 것

심사위원은 URL을 클릭하고 **30초 안에** 판단합니다.

**30초 안에 전달해야 하는 3가지:**
1. 이 서비스가 뭔지 (히어로 카피)
2. 뭘 할 수 있는지 (7단계 파이프라인)
3. 지금 바로 써볼 수 있는지 (CTA → 즉시 체험)

---

## 2. D-11 일정표

### 전체 타임라인

```
D-11 (2/08 토) ── 기획 확정 + Phase 0 (배포 인프라)
D-10 (2/09 일) ── Phase 1: 랜딩 페이지 리디자인
D-9  (2/10 월) ── Phase 2: JourneyStepper 7단계 + 프랜차이즈 비교 페이지
D-8  (2/11 화) ── Phase 3: 지원금 매칭 페이지 + 사업계획서 강화
D-7  (2/12 수) ── Phase 4: 스코어카드 투명성 강화 (report 페이지)
D-6  (2/13 목) ── Phase 5: 애널리틱스 시스템
D-5  (2/14 금) ── Phase 6: 프리미엄 넛지 + 전체 UI 폴리시
D-4  (2/15 토) ── 통합 테스트 + 버그 수정
D-3  (2/16 일) ── 실사용자 테스트 + 피드백 반영
D-2  (2/17 월) ── 트랙션 수집 시작 (커뮤니티 배포)
D-1  (2/18 화) ── 데모 영상 촬영 + 제출 설명 작성
D-0  (2/19 수) ── 제출
```

### 매일 배포 원칙

- **매일 최소 1회 프로덕션 배포** (Git tag + deploy)
- 배포 이력이 심사 자료: v0.6.1 → v0.6.2 → ... → v0.7.0
- 커밋 메시지에 변경 내용 명확히 기록

---

## 3. Phase 0 — 배포 인프라 (D-11)

### 3-1. 프로덕션 배포

현재 상태 확인 후 배포 환경 구축:

| 항목 | 작업 |
|------|------|
| 프론트엔드 | Vercel 배포 (Next.js 기본) |
| 백엔드 | Railway 또는 Fly.io (FastAPI) |
| 도메인 | spotpick.kr 또는 spotpick.vercel.app |
| HTTPS | 자동 (Vercel/Railway) |
| 환경변수 | Gemini API Key, Seoul API Key 등 |

### 3-2. 헬스체크

- 프론트: Vercel 자동
- 백엔드: `/api/v1/health` 이미 존재 (2개 엔드포인트)
- 모니터링: UptimeRobot 무료 (5분 간격 핑)

---

## 4. Phase 1 — 랜딩 페이지 (D-10)

### 4-1. 목표

심사위원이 URL 클릭 → 30초 안에 "이게 뭔지, 뭘 할 수 있는지" 파악 → CTA 클릭

### 4-2. 페이지 구조

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  SECTION 1: 히어로 (Above the Fold)                     │
│                                                         │
│  "창업, 감으로 하지 마세요"                              │
│   서울 1,077개 상권 · 10개 업종 · 7종 공공데이터         │
│   AI가 모든 창업 의사결정을 도와드립니다                  │
│                                                         │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │
│  │ 1,077  │ │  10개  │ │  23개  │ │  5분   │           │
│  │분석상권│ │지원업종│ │정부지원│ │플랜완성│           │
│  └────────┘ └────────┘ └────────┘ └────────┘           │
│                                                         │
│  [ 무료로 시작하기 ]    [ 데모 영상 보기 ▶ ]            │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SECTION 2: 7단계 의사결정 파이프라인                    │
│                                                         │
│  "창업에 필요한 모든 결정, 한 곳에서"                    │
│                                                         │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐                   │
│  │  ①  │─▶│  ②  │─▶│  ③  │─▶│  ④  │                   │
│  │업종 │  │프랜 │  │입지 │  │상세 │                   │
│  │선택 │  │차이즈│  │추천 │  │분석 │                   │
│  └─────┘  └─────┘  └─────┘  └─────┘                   │
│               │                                         │
│               ▼                                         │
│  ┌─────┐  ┌─────┐  ┌─────┐                             │
│  │  ⑤  │─▶│  ⑥  │─▶│  ⑦  │                             │
│  │수익 │  │지원금│  │사업 │                             │
│  │시뮬 │  │매칭 │  │계획서│                             │
│  └─────┘  └─────┘  └─────┘                             │
│                                                         │
│  각 단계 호버 시: 기능 설명 + 스크린샷 미리보기          │
│  각 단계 클릭 시: 해당 단계로 바로 이동                  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SECTION 3: 경쟁 비교                                   │
│                                                         │
│  "다른 서비스와 비교해보세요"                            │
│                                                         │
│  기능           오픈업  ChatGPT  SpotPick               │
│  ─────────────  ─────  ───────  ────────               │
│  상권 데이터      ✅     ❌        ✅                    │
│  AI 해석          ⚠️     ✅        ✅                    │
│  프랜차이즈 비교  ❌     ❌        ✅                    │
│  수익 시뮬레이션  ❌     ❌        ✅                    │
│  정부지원 매칭    ❌     ❌        ✅                    │
│  사업계획서 PDF   ❌     ❌        ✅                    │
│  원스톱 연결      ❌     ❌        ✅                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SECTION 4: 4가지 진입점                                │
│                                                         │
│  ┌───────────────┐  ┌───────────────┐                  │
│  │ "어디가       │  │ "여기는       │                  │
│  │  좋을까?"     │  │  어떨까?"     │                  │
│  │ → AI 입지추천 │  │ → 위치 진단   │                  │
│  └───────────────┘  └───────────────┘                  │
│  ┌───────────────┐  ┌───────────────┐                  │
│  │ "잘되는 곳    │  │ "잘          │                  │
│  │  알려줘"      │  │  모르겠어"   │                  │
│  │ → 성공 랭킹   │  │ → AI 상담    │                  │
│  └───────────────┘  └───────────────┘                  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SECTION 5: 요금제 (간결하게)                           │
│                                                         │
│  무료 ₩0          Pro ₩9,900/월                        │
│  기본 분석         무제한 분석                           │
│  TOP 5 추천        전체 추천                             │
│  계획서 1회/일     무제한 + PDF                          │
│  * 베타 기간 전체 무료                                  │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  SECTION 6: 기술 스택 (바이브랩스 심사용)               │
│                                                         │
│  "AI 네이티브로 만들었습니다"                           │
│                                                         │
│  ┌─ 제품 내 AI ────────────────────────────┐            │
│  │ • Gemini 2.5 Flash — 상권 분석 해석     │            │
│  │ • Gemini 2.5 Flash — 사업계획서 생성    │            │
│  │ • Gemini 2.5 Flash — 대화형 상담        │            │
│  └─────────────────────────────────────────┘            │
│  ┌─ 개발 과정 AI ──────────────────────────┐            │
│  │ • Claude Code — 전체 프론트/백엔드 개발  │            │
│  │ • 58개 API, 21개 라우터, 11,430줄       │            │
│  │ • 1인 개발, 2주 완성                     │            │
│  └─────────────────────────────────────────┘            │
│                                                         │
│  [ GitHub 보기 ] (배포 이력 = 실행력 증거)              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4-3. 구현 상세

**파일**: `/web/src/app/page.tsx` (전체 재구성)

```tsx
export default function LandingPage() {
  return (
    <main className="min-h-screen bg-white">
      <HeroSection />
      <PipelineSection />
      <ComparisonSection />
      <EntryPointSection />
      <PricingSection />
      <TechStackSection />
    </main>
  );
}
```

**HeroSection:**
```tsx
function HeroSection() {
  return (
    <section className="relative pt-16 pb-12 px-4 text-center">
      <h1 className="text-4xl font-bold tracking-tight">
        창업, 감으로 하지 마세요
      </h1>
      <p className="mt-4 text-lg text-slate-500 max-w-xl mx-auto">
        서울 1,077개 상권 · 10개 업종 · 7종 공공데이터<br />
        AI가 모든 창업 의사결정을 도와드립니다
      </p>
      <div className="grid grid-cols-4 gap-3 mt-8 max-w-md mx-auto">
        <StatBadge value="1,077" label="분석 상권" unit="개" />
        <StatBadge value="10" label="지원 업종" unit="개" />
        <StatBadge value="23" label="정부 지원" unit="개" />
        <StatBadge value="5" label="플랜 완성" unit="분" />
      </div>
      <div className="flex gap-3 justify-center mt-8">
        <Link href="/onboarding"
          className="px-8 py-4 bg-gradient-to-r from-blue-500 to-indigo-600
                     text-white rounded-2xl text-lg font-bold shadow-lg">
          무료로 시작하기
        </Link>
      </div>
    </section>
  );
}
```

**PipelineSection** (7단계):
```tsx
const STEPS = [
  { num: 1, title: "업종 선택", desc: "10개 요식업종", icon: UtensilsCrossed, color: "blue" },
  { num: 2, title: "프랜차이즈 비교", desc: "공정위 데이터", icon: GitCompare, color: "violet" },
  { num: 3, title: "AI 입지 추천", desc: "1,077개 상권", icon: MapPin, color: "emerald" },
  { num: 4, title: "상세 분석", desc: "투명 스코어카드", icon: BarChart3, color: "amber" },
  { num: 5, title: "수익 시뮬", desc: "손익분기 계산", icon: Calculator, color: "rose" },
  { num: 6, title: "지원금 매칭", desc: "23개 프로그램", icon: BadgePercent, color: "teal" },
  { num: 7, title: "사업계획서", desc: "AI 5분 생성", icon: FileText, color: "indigo" },
];
```

**ComparisonSection** (경쟁 비교):
```tsx
const FEATURES = [
  { name: "상권 데이터 분석", openup: true,  chatgpt: false, spotpick: true },
  { name: "AI 해석·전략",     openup: "partial", chatgpt: true, spotpick: true },
  { name: "프랜차이즈 비교",  openup: false, chatgpt: false, spotpick: true },
  { name: "수익 시뮬레이션",  openup: false, chatgpt: false, spotpick: true },
  { name: "정부지원 매칭",    openup: false, chatgpt: false, spotpick: true },
  { name: "상표 검색",        openup: false, chatgpt: false, spotpick: true },
  { name: "사업계획서 PDF",   openup: false, chatgpt: false, spotpick: true },
  { name: "7단계 원스톱",     openup: false, chatgpt: false, spotpick: true },
];
```

**TechStackSection** (바이브랩스 심사용):
```tsx
function TechStackSection() {
  return (
    <section className="py-16 bg-slate-50">
      <h2>AI 네이티브로 만들었습니다</h2>
      <div className="grid grid-cols-2 gap-8">
        <div>
          <h3>제품 내 AI</h3>
          <ul>
            <li>Gemini 2.5 Flash — 상권 분석 해석</li>
            <li>Gemini 2.5 Flash — 사업계획서 생성</li>
            <li>Gemini 2.5 Flash — 대화형 창업 상담</li>
          </ul>
        </div>
        <div>
          <h3>개발 과정 AI</h3>
          <ul>
            <li>Claude Code — 프론트/백엔드 전체</li>
            <li>58개 API · 21개 라우터 · 11,430줄</li>
            <li>1인 개발 · 2주 완성</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
```

---

## 5. Phase 2 — 7단계 여정 완성 (D-9)

### 5-1. JourneyStepper 확장

**수정 파일**: `/web/src/lib/journey-store.ts`, `/web/src/components/JourneyStepper.tsx`

journey-store 변경:
```typescript
// 기존 step: 1~5 → 1~7 확장
// 추가 상태:
type JourneyStep = 1 | 2 | 3 | 4 | 5 | 6 | 7;

interface JourneyState {
  // ... 기존 상태 유지
  franchiseChoice: "franchise" | "independent" | null;  // STEP 2
  franchiseBenchmark: FranchiseBenchmark | null;         // STEP 2 데이터
  matchedPrograms: SupportProgram[];                      // STEP 6 데이터
}

const STEP_ROUTES: Record<JourneyStep, string> = {
  1: "/onboarding",
  2: "/franchise",       // ★ 신규
  3: "/results",
  4: "/report",
  5: "/simulator",
  6: "/support",         // ★ 신규
  7: "/business-plan",
};

const STEP_LABELS = [
  "업종 선택",
  "프랜차이즈 비교",   // ★ 신규
  "입지 추천",
  "상세 분석",
  "수익 시뮬",
  "지원금 매칭",       // ★ 신규
  "사업계획서",
];
```

JourneyStepper 컴포넌트:
```tsx
// 데스크톱: 가로 스텝 표시
// 모바일: "STEP 3/7 · AI 입지 추천" + 프로그레스 도트
function JourneyStepper({ currentStep }: { currentStep: JourneyStep }) {
  return (
    <>
      {/* 데스크톱 */}
      <nav className="hidden md:flex items-center justify-center gap-2 py-4">
        {STEP_LABELS.map((label, i) => (
          <StepDot
            key={i}
            step={i + 1}
            label={label}
            status={
              i + 1 < currentStep ? "completed" :
              i + 1 === currentStep ? "current" : "pending"
            }
            onClick={() => navigateToStep(i + 1)}
          />
        ))}
      </nav>
      {/* 모바일 */}
      <div className="md:hidden flex items-center justify-between px-4 py-3">
        <button onClick={goPrev}>◀</button>
        <div className="text-center">
          <div className="text-sm font-medium">STEP {currentStep}/7</div>
          <div className="text-xs text-slate-500">{STEP_LABELS[currentStep - 1]}</div>
        </div>
        <button onClick={goNext}>▶</button>
      </div>
    </>
  );
}
```

### 5-2. 프랜차이즈 비교 페이지 (STEP 2)

**신규 파일**: `/web/src/app/franchise/page.tsx`

**백엔드 API**: `/api/v1/franchise/benchmark/{industry_code}` (이미 존재)

반환 데이터 (이미 구현된 것):
- `franchise_fee` (가맹비)
- `education_fee` (교육비)
- `deposit` (보증금)
- `interior_cost` (인테리어)
- `total_startup_cost` (총 창업비용)
- `brand_count` (가맹본부 수)
- `store_count` (가맹점 수)
- `avg_sales` (평균 매출)

```tsx
export default function FranchiseComparisonPage() {
  const { industryCode, industryName } = useJourneyStore();
  const [benchmark, setBenchmark] = useState<FranchiseBenchmark | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/franchise/benchmark/${industryCode}`)
      .then(r => r.json())
      .then(data => { setBenchmark(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [industryCode]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <JourneyStepper currentStep={2} />

      <h1 className="text-2xl font-bold mt-8">
        {industryName} — 프랜차이즈 vs 독립 창업
      </h1>

      {loading ? <Skeleton /> : (
        <>
          {/* 2열 비교 카드 */}
          <div className="grid md:grid-cols-2 gap-6 mt-8">
            <FranchiseCard benchmark={benchmark} />
            <IndependentCard benchmark={benchmark} />
          </div>

          {/* 업종 현황 */}
          <IndustryOverview benchmark={benchmark} />

          {/* 선택 */}
          <div className="flex gap-4 mt-8">
            <button onClick={() => choose("franchise")}
              className="flex-1 py-4 border-2 border-blue-500 rounded-xl
                         font-bold hover:bg-blue-50">
              프랜차이즈로 진행
            </button>
            <button onClick={() => choose("independent")}
              className="flex-1 py-4 border-2 border-emerald-500 rounded-xl
                         font-bold hover:bg-emerald-50">
              독립 창업으로 진행
            </button>
          </div>

          {/* 건너뛰기 */}
          <button onClick={skip}
            className="mt-4 text-slate-400 text-sm underline mx-auto block">
            이 단계 건너뛰기
          </button>

          {/* 데이터 출처 */}
          <DataSource
            sources={["공정거래위원회 정보공개서 (2025)"]}
          />
        </>
      )}
    </div>
  );
}
```

**FranchiseCard 컴포넌트:**
```tsx
function FranchiseCard({ benchmark }) {
  const costs = benchmark?.startup_costs;
  return (
    <div className="border rounded-2xl p-6">
      <h3 className="text-lg font-bold text-blue-600">프랜차이즈 창업</h3>
      <div className="mt-4 space-y-3">
        <CostRow label="가맹비" value={costs?.franchise_fee} />
        <CostRow label="교육비" value={costs?.education_fee} />
        <CostRow label="보증금" value={costs?.deposit} />
        <CostRow label="인테리어" value={costs?.interior_cost} />
        <Divider />
        <CostRow label="총 초기비용" value={costs?.total_startup_cost} bold />
      </div>
      <div className="mt-6">
        <h4 className="font-medium">장점</h4>
        <ul className="mt-2 text-sm text-slate-600 space-y-1">
          <li>• 검증된 브랜드 인지도</li>
          <li>• 본사 마케팅·물류 지원</li>
          <li>• 레시피·운영 매뉴얼 제공</li>
        </ul>
      </div>
      <div className="mt-4">
        <h4 className="font-medium">리스크</h4>
        <ul className="mt-2 text-sm text-slate-600 space-y-1">
          <li>• 월 로열티 3~5%</li>
          <li>• 메뉴·인테리어 자유도 제한</li>
          <li>• 계약 해지 시 위약금</li>
        </ul>
      </div>
    </div>
  );
}
```

### 5-3. 지원금 매칭 페이지 (STEP 6)

**신규 파일**: `/web/src/app/support/page.tsx`

**백엔드 API**: `/api/v1/support/matched` (이미 존재)

반환 데이터 (이미 구현된 것):
- `program_name`, `category`, `support_target`
- `max_amount_man` (최대 지원금액, 만원)
- `application_start_date`, `application_end_date`
- `days_until_deadline` (D-day)
- `detail_url` (신청 링크)
- `program_type` (대출/보조금/컨설팅/기술지원)

```tsx
export default function SupportMatchingPage() {
  const { industryCode, selectedDistrict, budgetMin, budgetMax }
    = useJourneyStore();
  const [programs, setPrograms] = useState([]);

  useEffect(() => {
    const params = new URLSearchParams({
      industry_code: industryCode,
      district: selectedDistrict?.district_name || "",
      budget_min: String(budgetMin),
      budget_max: String(budgetMax),
    });
    fetch(`${API_BASE}/api/v1/support/matched?${params}`)
      .then(r => r.json())
      .then(setPrograms);
  }, [industryCode, selectedDistrict]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <JourneyStepper currentStep={6} />

      <h1 className="text-2xl font-bold mt-8">
        받을 수 있는 정부 지원금
      </h1>

      {/* 매칭 조건 표시 */}
      <MatchBadges
        industry={industryCode}
        district={selectedDistrict}
        budget={{ min: budgetMin, max: budgetMax }}
      />

      {/* 프로그램 리스트 */}
      <div className="mt-6 space-y-4">
        {programs.map((program, i) => (
          <ProgramCard key={program.program_id} rank={i + 1} {...program} />
        ))}
      </div>

      {/* 팁 */}
      <div className="mt-8 p-4 bg-amber-50 rounded-xl text-sm">
        사업계획서가 있으면 지원금 심사에 유리합니다.
        다음 단계에서 AI가 사업계획서를 생성합니다.
      </div>

      <NextButton label="사업계획서 만들기 →" step={7} />
    </div>
  );
}
```

**ProgramCard 컴포넌트:**
```tsx
function ProgramCard({ rank, program_name, max_amount_man,
                        days_until_deadline, program_type,
                        managing_org, detail_url }) {
  return (
    <div className="border rounded-xl p-5 hover:border-blue-300 transition">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-sm text-slate-400">#{rank}</span>
          <h3 className="font-bold mt-1">{program_name}</h3>
          <p className="text-sm text-slate-500 mt-1">{managing_org}</p>
        </div>
        <div className="text-right">
          <span className={`px-2 py-1 rounded text-xs font-medium
            ${days_until_deadline <= 14 ? 'bg-red-100 text-red-600'
                                        : 'bg-slate-100 text-slate-600'}`}>
            D-{days_until_deadline}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-4 mt-3">
        <span className="text-lg font-bold text-blue-600">
          최대 {(max_amount_man / 10000).toFixed(0)}억원
        </span>
        <span className="px-2 py-0.5 bg-slate-100 rounded text-xs">
          {program_type}
        </span>
      </div>
      <a href={detail_url} target="_blank" rel="noopener"
         className="mt-3 inline-block text-sm text-blue-500 underline">
        상세보기 →
      </a>
    </div>
  );
}
```

---

## 6. Phase 3 — 사업계획서 강화 (D-8)

### 6-1. 여정 데이터 자동 반영

사업계획서 생성 시 Gemini 프롬프트에 여정 전체 데이터를 포함:

```python
# business_plan_service.py 수정
def build_context(journey_data: dict) -> str:
    context_parts = []

    # STEP 2: 프랜차이즈 선택 결과
    if journey_data.get("franchise_choice"):
        choice = journey_data["franchise_choice"]
        benchmark = journey_data.get("franchise_benchmark", {})
        context_parts.append(f"""
        창업 형태: {choice}
        {'프랜차이즈 평균 초기비용: ' + str(benchmark.get('total_startup_cost', '')) + '원'
         if choice == 'franchise' else '독립 창업 선택'}
        """)

    # STEP 4: 스코어카드 결과
    if journey_data.get("scorecard"):
        sc = journey_data["scorecard"]
        context_parts.append(f"""
        종합 성공점수: {sc['total_score']}점
        매출 백분위: {sc['sales_percentile']}
        생존율: {sc['survival_rate']}
        """)

    # STEP 5: 시뮬레이션 결과
    if journey_data.get("simulation"):
        sim = journey_data["simulation"]
        context_parts.append(f"""
        월 예상매출: {sim['monthly_revenue']}원
        월 운영비: {sim['operating_cost']}원
        손익분기: {sim['break_even_months']}개월
        """)

    # STEP 6: 지원금 매칭 결과
    if journey_data.get("matched_programs"):
        programs = journey_data["matched_programs"][:3]
        context_parts.append(f"""
        매칭된 정부 지원 프로그램:
        {chr(10).join(f'- {p["program_name"]}: 최대 {p["max_amount_man"]}만원'
                       for p in programs)}
        """)

    return "\n".join(context_parts)
```

### 6-2. 사업계획서 새 섹션

기존 8개 → 10개 섹션:

| # | 섹션 | 데이터 소스 | 기존/신규 |
|---|------|-----------|---------|
| 1 | 사업 개요 | 업종 + 입지 | 기존 |
| 2 | 시장 분석 | STEP 4 스코어카드 | 기존 (강화) |
| 3 | 경쟁 분석 | STEP 4 경쟁분석 | 기존 |
| 4 | **창업 형태** | **STEP 2 프랜차이즈 비교** | **★ 신규** |
| 5 | 메뉴·상품 전략 | 업종별 원가율 | 기존 |
| 6 | 마케팅 전략 | Gemini 생성 | 기존 |
| 7 | 재무 계획 | STEP 5 시뮬레이션 | 기존 (강화) |
| 8 | **자금 조달 계획** | **STEP 6 지원금 매칭** | **★ 신규** |
| 9 | 리스크 관리 | STEP 4 + STEP 5 | 기존 |
| 10 | 실행 로드맵 | Gemini 생성 | 기존 |

---

## 7. Phase 4 — 스코어카드 투명성 (D-7)

### 7-1. report 페이지 스코어카드 시각화

**수정 파일**: `/web/src/app/report/page.tsx`

기존: 종합 점수만 표시
개선: 항목별 프로그레스바 + 기여점수

```tsx
function ScorecardBreakdown({ scorecard }) {
  const items = [
    {
      label: "점포당 월매출",
      value: scorecard.sales_per_store,
      percentile: scorecard.sales_percentile,
      weight: 40,
      contribution: scorecard.sales_contribution,
      color: "blue",
    },
    {
      label: "점포 생존율",
      value: scorecard.survival_rate,
      percentile: scorecard.survival_percentile,
      weight: 25,
      contribution: scorecard.survival_contribution,
      color: "emerald",
    },
    {
      label: "매출 성장률",
      value: scorecard.growth_rate,
      percentile: scorecard.growth_percentile,
      weight: 20,
      contribution: scorecard.growth_contribution,
      color: "amber",
    },
    {
      label: "경쟁 안정성",
      value: scorecard.stability_score,
      percentile: scorecard.stability_percentile,
      weight: 15,
      contribution: scorecard.stability_contribution,
      color: "rose",
    },
  ];

  return (
    <div className="space-y-4">
      <h3 className="font-bold text-lg">
        종합 성공점수 {scorecard.total_score}점
        <span className="text-sm text-slate-400 ml-2">
          (상위 {scorecard.total_percentile}%)
        </span>
      </h3>

      {items.map(item => (
        <div key={item.label}>
          <div className="flex justify-between text-sm">
            <span>{item.label}</span>
            <span className="font-medium">
              {item.contribution.toFixed(1)}점 / {item.weight}점
            </span>
          </div>
          <div className="mt-1 h-3 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full bg-${item.color}-500 rounded-full`}
              style={{ width: `${(item.contribution / item.weight) * 100}%` }}
            />
          </div>
          <div className="text-xs text-slate-400 mt-0.5">
            {item.value} · 상위 {item.percentile}% · 가중치 {item.weight}%
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 8. Phase 5 — 애널리틱스 (D-6)

### 8-1. 프론트엔드

**신규 파일**: `/web/src/lib/analytics.ts`

```typescript
const ANALYTICS_ENDPOINT = "/api/v1/analytics/event";

let sessionId: string | null = null;
function getSessionId(): string {
  if (!sessionId) {
    sessionId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }
  return sessionId;
}

export function trackEvent(name: string, props?: Record<string, string | number>) {
  if (typeof window === "undefined") return;
  const payload = {
    event: name,
    session_id: getSessionId(),
    timestamp: new Date().toISOString(),
    page: window.location.pathname,
    props: props || {},
  };
  navigator.sendBeacon?.(ANALYTICS_ENDPOINT, JSON.stringify(payload))
    || fetch(ANALYTICS_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {});
}
```

### 8-2. 추적 이벤트 (13개)

| 이벤트 | 발생 시점 | 속성 |
|--------|----------|------|
| `page_view` | 모든 페이지 로드 | `{ page }` |
| `journey_start` | CTA 클릭 | `{ entry_type }` |
| `industry_select` | 업종 선택 | `{ industry_code }` |
| `franchise_compare` | STEP 2 진입 | `{ industry_code }` |
| `franchise_choose` | 프랜차이즈/독립 선택 | `{ choice }` |
| `district_select` | 상권 선택 | `{ district_code }` |
| `report_view` | 보고서 조회 | `{ district_code }` |
| `simulation_run` | 시뮬레이터 사용 | `{ district_code }` |
| `support_match` | STEP 6 진입 | `{ matched_count }` |
| `plan_generate` | 사업계획서 생성 | `{ sections }` |
| `plan_download` | PDF 다운로드 | `{ }` |
| `journey_complete` | 7단계 완료 | `{ total_time_sec }` |
| `chat_message` | 채팅 전송 | `{ message_count }` |

### 8-3. 백엔드

**신규 파일**: `/api/routes/analytics.py`

- `POST /api/v1/analytics/event` — JSONL 파일 로깅 (IP 해시 처리)
- `GET /api/v1/analytics/summary` — 일별 집계 (DAU, 이벤트별 수, 퍼널 전환율)

---

## 9. Phase 6 — 프리미엄 넛지 + UI 폴리시 (D-5)

### 9-1. 프리미엄 상태 관리

**신규 파일**: `/web/src/lib/premium.ts`

```typescript
const BETA_MODE = true; // 베타 기간: 모든 기능 열림, UI에만 표시

export function isPremium(): boolean {
  if (BETA_MODE) return true;
  return localStorage.getItem("spotpick_premium") === "true";
}

export const FREE_LIMITS = {
  plan_generate: 1,    // 1일 1회
  pdf_download: 1,     // 1일 1회
  compare_items: 3,    // 비교 3개
  support_view: 3,     // 지원금 3개만 표시
  franchise_detail: false,  // 상세 비교 불가
};
```

### 9-2. UI 폴리시 체크리스트

| 항목 | 작업 |
|------|------|
| 모바일 반응형 | 모든 신규 페이지 md: 브레이크포인트 확인 |
| 로딩 상태 | Skeleton UI 통일 |
| 에러 상태 | "데이터를 불러오지 못했습니다" 통일 |
| 빈 상태 | "매칭된 프로그램이 없습니다" 등 |
| 애니메이션 | 페이지 전환 fade-in, 스크롤 reveal |
| 다크모드 | 미지원 (밝은 테마 통일) |
| 데이터 출처 | 모든 분석 결과 하단에 출처 표시 |

---

## 10. 제출 전 체크리스트 (D-1)

### 10-1. 프로덕션 검증

```
□ 프론트엔드 배포 확인 (Vercel)
□ 백엔드 배포 확인 (Railway/Fly.io)
□ API 헬스체크 응답 확인
□ Gemini API 키 유효 확인
□ 서울시 API 키 유효 확인
□ 7단계 풀 여정 테스트 (업종→프랜차이즈→입지→분석→시뮬→지원금→계획서)
□ PDF 다운로드 동작 확인
□ 모바일 브라우저 테스트
□ 애널리틱스 이벤트 수신 확인
```

### 10-2. 데모 영상 (1분)

```
0:00-0:05  SpotPick 로고 + "창업 의사결정 AI 플랫폼"
0:05-0:10  업종 선택 (치킨전문점)
0:10-0:20  프랜차이즈 vs 독립 비교 (공정위 데이터)
0:20-0:30  AI 입지 추천 → 지도 → TOP 5
0:30-0:40  스코어카드 + 시뮬레이션
0:40-0:50  지원금 매칭 (23개 중 8개 매칭)
0:50-0:60  사업계획서 생성 + PDF 다운로드
```

### 10-3. 제출 설명문 (200자 내)

```
SpotPick — 창업 의사결정 AI 플랫폼

서울 1,077개 상권 × 10개 업종 × 7종 공공데이터.
업종선택 → 프랜차이즈 비교(공정위) → AI 입지추천 → 투명 스코어카드
→ 수익 시뮬레이션 → 정부지원 23개 매칭 → 사업계획서 PDF.
7단계 창업 의사결정을 AI가 5분 만에 완성.

제품 AI: Gemini 2.5 Flash (분석·생성·상담)
개발 AI: Claude Code (58 API, 1인 개발)
```

---

## 11. 바이브랩스 8주 프로그램 대비 (선발 후)

선발되면 3~4월 8주간 **프로덕션 운영 + 개선 속도**로 평가받음.

### 8주 로드맵 (선발 후)

| 주차 | 작업 | 목표 지표 |
|------|------|---------|
| 1~2주 | 결과 피드백 루프 구축 (실제 창업자 추적) | 추적 대상 10명 확보 |
| 3~4주 | 독점 데이터: 네이버 리뷰 감성분석 + 실시간 임대료 | 데이터 소스 3종 추가 |
| 5~6주 | 전국 확장 (경기도, 부산, 대구) | 커버 상권 3,000개+ |
| 7~8주 | B2B 파일럿 (프랜차이즈 본사 대상 의도 데이터 리포트) | 파일럿 고객 1곳 |

### Moat 구축 타임라인

```
[현재]        공공데이터 = 누구나 접근 가능 = Moat 없음
   ↓
[3개월 후]    사용자 의사결정 데이터 축적 = 약한 Moat
   ↓
[6개월 후]    실제 창업 결과 데이터 = 중간 Moat
   ↓
[12개월 후]   "SpotPick 추천 = 성공률 23% 높음" 증명 = 강한 Moat
```

---

## 12. 요약: 11일 실행 계획

| 일자 | Phase | 핵심 산출물 | 배포 |
|------|-------|-----------|------|
| D-11 (2/08) | 기획 확정 + 배포 인프라 | Vercel + Railway 세팅 | v0.6.2 |
| D-10 (2/09) | 랜딩 리디자인 | 히어로+파이프라인+비교+진입점+요금제+기술스택 | v0.6.3 |
| D-9 (2/10) | JourneyStepper 7단계 + 프랜차이즈 비교 | franchise/page.tsx + store 확장 | v0.6.4 |
| D-8 (2/11) | 지원금 매칭 + 사업계획서 강화 | support/page.tsx + 10섹션 | v0.6.5 |
| D-7 (2/12) | 스코어카드 투명성 | report 페이지 기여점수 시각화 | v0.6.6 |
| D-6 (2/13) | 애널리틱스 | analytics.ts + 13개 이벤트 | v0.6.7 |
| D-5 (2/14) | 프리미엄 넛지 + UI 폴리시 | premium.ts + 반응형 + 애니메이션 | v0.6.8 |
| D-4 (2/15) | 통합 테스트 | 7단계 풀 여정 검증 | v0.6.9 |
| D-3 (2/16) | 실사용자 테스트 | 피드백 수집 + 즉시 반영 | v0.6.10 |
| D-2 (2/17) | 트랙션 수집 | 커뮤니티 배포 + DAU 측정 | v0.7.0-rc |
| D-1 (2/18) | 데모 영상 + 제출문 | 1분 영상 + 200자 설명 | v0.7.0 |
| D-0 (2/19) | **제출** | URL + 영상 + 설명 | - |

**매일 1배포. 11일 11배포. Git log가 실행력 증거.**

---

*핵심: 바이브랩스는 문서를 안 봅니다. 제품을 봅니다. 이 기획안의 모든 것은 "제출 URL을 클릭했을 때 심사위원이 뭘 보는가"에 맞춰져 있습니다.*
