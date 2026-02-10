# SpotPick v1.0 수정기획안 — 매물 탐색 + 창업비용 비교 + 워크플로우 재설계

> 작성일: 2026-02-09 | 기준: v0.9.5 (커밋 8ee8617)

---

## 1. 핵심 문제 인식

현재 SpotPick은 **"어디가 좋을까?"에 대한 답**은 주지만, **"그래서 거기 매물은 있어?"와 "프랜차이즈 vs 독립 뭐가 나아?"**에 대한 답이 없다.

사용자 여정이 **분석 → 끝**으로 끊기고, **분석 → 매물 탐색 → 비용 비교 → 실행 결정**이라는 실제 창업 의사결정 루프가 완성되지 않는다.

---

## 2. 목표: 5-Step 완결형 창업 워크플로우

```
[현재] 입력 → AI 리포트 → 액션플랜(끝)

[개선] 입력 → AI 리포트 → 매물탐색 → 비용비교 → 액션플랜
       Step1    Step2       Step3      Step4       Step5
```

### Step 3: 매물 탐색 (신규)
> "추천받은 상권에 실제 임대 가능한 매물이 있나?"

- 추천 상권 근처 상가 임대 매물 목록
- 추정 임대료 vs 실매물 시세 비교
- 매물별 면적, 보증금/월세, 층수, 용도

### Step 4: 비용 비교 (신규)
> "프랜차이즈로 할까 독립으로 할까? 총 얼마 들어?"

- 프랜차이즈: 가맹비 + 교육비 + 인테리어 + 매물 임대료
- 독립창업: 인테리어 + 장비 + 매물 임대료
- 나란히 비교 + AI 추천

---

## 3. 기술 설계

### 3-A. 매물 데이터 소스 전략

**우선순위 1: 네이버 부동산 크롤링/API**
- 상가/사무실 매물 검색 가능
- `https://land.naver.com/` 검색 → 상가임대 매물
- Naver API 키 이미 보유 (`NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`)

**우선순위 2: 카카오맵 부동산 카테고리 검색**
- 이미 `kakao_local_service.py` 구현됨
- 카테고리 코드 `BK9` (은행) 대신 `AG2` (부동산) 검색으로 인근 부동산 중개소 목록 + 연락처 제공
- 실매물 데이터는 아니지만 "이 근처 부동산 중개소" 안내 가능

**우선순위 3: 공공데이터 상가임대료 통계**
- 한국부동산원 상업용부동산 임대동향 (이미 KREI 데이터로 일부 활용 중)
- 소상공인시장진흥공단 상가임대료 정보

**구현 전략: 멀티소스 폴백**
```
네이버 부동산 매물 검색 (실시간 매물)
  ↓ 실패 시
카카오맵 부동산 중개소 + 추정 시세
  ↓ 실패 시
KREI 통계 기반 시세 + "매물은 직접 확인" 안내
```

### 3-B. 백엔드 신규 API

#### `api/services/property_service.py` (신규)
```python
# 네이버 부동산 매물 검색
async def search_properties(
    lat: float, lng: float, radius: int = 1000,
    property_type: str = "상가",
) -> list[PropertyListing]
# 반환: [{name, address, area_m2, deposit, monthly_rent, floor, source_url}]

# 카카오맵 부동산 중개소 검색 (폴백)
async def search_realtors(lat: float, lng: float, radius: int = 500) -> list[Realtor]
# 반환: [{name, address, phone, distance}]
```

#### `api/routes/property.py` (신규)
```
GET /api/v1/property/listings?district_code=XXX&industry_code=XXX
→ 매물 목록 + 추정시세 vs 실매물 시세 비교

GET /api/v1/property/realtors?district_code=XXX
→ 인근 부동산 중개소 목록
```

#### `api/routes/franchise.py` 확장
```
GET /api/v1/franchise/cost-compare?industry_code=XXX&monthly_rent=XXX&area_pyeong=15
→ {
    franchise: {total_cost, breakdown: {가맹비, 교육비, 인테리어, 보증금, 월세}},
    independent: {total_cost, breakdown: {인테리어, 장비, 보증금, 월세}},
    difference: 차액,
    ai_recommendation: "프랜차이즈 추천 이유 / 독립 추천 이유"
  }
```

### 3-C. 프론트엔드 신규 페이지

#### `/property` (매물 탐색 페이지)
- 상권 기반 매물 리스트 카드 (면적, 보증금/월세, 층)
- SpotPick 추정 임대료 vs 실매물 시세 비교 차트
- 인근 부동산 중개소 연락처 카드
- "이 매물로 시뮬레이션" 버튼 → 시뮬레이터 연동

#### `/cost-compare` (비용 비교 페이지)
- 프랜차이즈 vs 독립창업 비용 워터폴 비교
- 선택한 매물 임대료 자동 반영
- 총 투자금 / 월 고정비 / 손익분기점 나란히 비교
- AI 종합 추천 (Gemini)
- "선택 확정 → 사업계획서" 버튼

### 3-D. 리포트 페이지 연동 수정

`/analyze/report` 하단 CTA 버튼 변경:
```
[현재] 사업계획서 생성 & 액션 플랜

[개선] 매물 찾아보기 → /property?district_code=XXX
       비용 비교하기  → /cost-compare?industry_code=XXX
       사업계획서     → /analyze/action (기존)
```

### 3-E. Stepper 업데이트

```
[현재 3-Step]
① 입력 → ② AI 리포트 → ③ 액션 플랜

[개선 5-Step]
① 입력 → ② AI 리포트 → ③ 매물 탐색 → ④ 비용 비교 → ⑤ 액션 플랜
```

---

## 4. 파일별 구현 명세

### 신규 파일 (5개)

| 파일 | 유형 | 핵심 기능 |
|------|------|-----------|
| `api/services/property_service.py` | Backend | 네이버 부동산 매물 검색 + 카카오 중개소 폴백 |
| `api/routes/property.py` | Backend | `/property/listings`, `/property/realtors` |
| `web/src/app/property/page.tsx` | Frontend | 매물 탐색 UI (카드, 시세 비교, 중개소) |
| `web/src/app/cost-compare/page.tsx` | Frontend | 프랜차이즈 vs 독립 비용 비교 UI |
| `api/services/startup_cost_service.py` | Backend | 독립창업 비용 산출 로직 (업종별 장비, 인테리어 원가) |

### 수정 파일 (5개)

| 파일 | 변경 내용 |
|------|-----------|
| `api/app.py` | property_router 등록 |
| `api/routes/franchise.py` | `/cost-compare` 엔드포인트 추가 |
| `web/src/components/AnalyzeStepper.tsx` | 5-Step으로 확장 |
| `web/src/app/analyze/report/page.tsx` | 하단 CTA에 매물/비교 버튼 추가 |
| `web/src/app/page.tsx` | 랜딩 EntryPoints에 "매물 탐색" 추가 |

### 데이터 파일 (1개)

| 파일 | 내용 |
|------|------|
| `api/data/independent_startup_costs.json` | 업종별 독립창업 비용 데이터 (인테리어, 장비, 초도물량) |

---

## 5. 독립창업 비용 데이터 설계

```json
{
  "CS100010": {
    "name": "카페",
    "interior_per_pyeong": 2500000,
    "equipment": [
      {"name": "에스프레소 머신", "cost": 8000000},
      {"name": "그라인더", "cost": 2000000},
      {"name": "냉장고/쇼케이스", "cost": 3000000},
      {"name": "POS 시스템", "cost": 1500000},
      {"name": "가구/조명", "cost": 5000000}
    ],
    "initial_inventory": 3000000,
    "signage": 2000000,
    "misc": 2000000
  }
}
```

프랜차이즈는 기존 공정위 API (`/franchise/benchmark/{industry_code}`)에서 가져옴.

---

## 6. 매물 검색 흐름 상세

```
사용자가 리포트에서 "매물 찾아보기" 클릭
  ↓
/property?district_code=XXX&industry_code=XXX
  ↓
Backend: district_code → 좌표 변환 (DataService.get_district → lat/lng)
  ↓
네이버 부동산 API: 좌표 반경 1km 상가 매물 검색
  ↓ (실패 시)
카카오 로컬 API: "부동산" 카테고리 검색 → 중개소 목록
  ↓
SpotPick 추정 임대료 (estimate_rent)와 실매물 시세 비교
  ↓
UI: 매물 카드 목록 + 시세 비교 차트 + "이 매물로 비용 비교" 버튼
```

---

## 7. 사용자 워크플로우 (완결형)

```
1. /analyze         업종 + 예산 입력 (30초)
2. /analyze/report  AI 리포트 + TOP3 + 브리핑 + 리스크 알림
   └→ "매물 찾아보기" 클릭
3. /property        추천 상권 매물 목록 + 시세 비교
   └→ 매물 선택 → "이 매물로 비용 비교" 클릭
4. /cost-compare    프랜차이즈 vs 독립 총비용 비교 + AI 추천
   └→ "결정! 사업계획서 생성" 클릭
5. /analyze/action  사업계획서 + PDF + 타임라인 (기존)
```

---

## 8. 네이버 부동산 연동 기술 상세

### 검색 방식
네이버 부동산은 공식 오픈 API가 없으므로 두 가지 대안:

**방안 A: 네이버 지도 API + 부동산 카테고리 (추천)**
- 네이버 지도 검색 API로 "상가 임대" 키워드 검색
- `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` 이미 보유
- URL: `https://openapi.naver.com/v1/search/local.json?query=상가임대+{지역명}`

**방안 B: 상가정보시스템 공공API**
- 소상공인시장진흥공단 상가정보 API (data.go.kr)
- `DATA_GO_KR_API_KEY` 이미 보유
- 상가 매물은 아니지만 해당 지역 상가 현황(면적, 업종, 임대료 수준) 제공

**구현: 방안 A + B 폴백**

```python
# property_service.py

async def search_naver_properties(query: str, display: int = 10):
    """네이버 지역 검색 API로 상가 임대 매물 검색"""
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": f"상가임대 {query}", "display": display}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        ...
```

---

## 9. 리스크 & 한계

| 리스크 | 대응 |
|--------|------|
| 네이버 부동산 실매물 데이터 접근 제한 | 카카오 중개소 + KREI 시세 폴백 |
| 독립창업 비용 정확도 | 업종별 평균값 + "±20% 범위" 표시 |
| 프랜차이즈 비용 공정위 데이터 최신성 | 연도 표시 + "실제 가맹 상담 권장" 문구 |
| API rate limit | 검색 결과 5분 캐싱 |

---

## 10. 구현 우선순위

| 순서 | 작업 | 소요 |
|------|------|------|
| 1 | `startup_cost_service.py` + `independent_startup_costs.json` | 데이터 정의 |
| 2 | `franchise.py` `/cost-compare` 엔드포인트 | 비용 비교 API |
| 3 | `property_service.py` + `property.py` | 매물 검색 API |
| 4 | `/cost-compare` 프론트엔드 | 비용 비교 UI |
| 5 | `/property` 프론트엔드 | 매물 탐색 UI |
| 6 | Stepper 5단계 + 리포트 CTA 수정 | 워크플로우 연결 |
| 7 | 테스트 + 커밋 + 배포 | 배포 |
