# SpotPick 데이터 소스 총정리

> 최종 업데이트: 2026-02-10
> API 전수조사 완료. 작동 확인된 것만 포함.

---

## A. 실시간 API (작동 확인 완료)

### A1. data.go.kr (공공데이터포털)

| # | API 이름 | 엔드포인트 | 키 | 제공 데이터 | 용도 |
|---|---------|-----------|-----|-----------|------|
| 1 | **건축물대장** | `apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo` | DATA_GO_KR_API_KEY | 용도, 면적, 구조, 준공일 | compliance_advisor (건물 적합성) |
| 2 | **상업업무용 매매 실거래가** | `apis.data.go.kr/1613000/RTMSDataSvcNrgTrade/getRTMSDataSvcNrgTrade` | DATA_GO_KR_API_KEY | 거래금액, 면적, 용도, 건축년도 | lease_advisor (매매가 참고) |
| 3 | **SEMAS 상가업소** | `apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong` | DATA_GO_KR_API_KEY | 업종, 위치, 밀도 | 경쟁 분석 |
| 4 | **SEMAS 상권영역** | `apis.data.go.kr/B553077/api/open/sdsc2/baroApi` | DATA_GO_KR_API_KEY | 상권 범위 폴리곤 | 지도 시각화 |

### A2. 서울 열린데이터광장

| # | API 이름 | 서비스명 | 키 | 레코드 수 | 제공 데이터 |
|---|---------|---------|-----|----------|-----------|
| 5 | **매출** | `VwsmTrdarSelngQq` | SEOUL_API_KEY | 21,718 | 월매출, 시간대별, 요일별, 연령별, 성별 |
| 6 | **유동인구** | `VwsmTrdarFlpopQq` | SEOUL_API_KEY | 1,648 | 성별/연령/시간대별 유동인구 |
| 7 | **점포수** | `VwsmTrdarStorQq` | SEOUL_API_KEY | 76,595 | 개업수, 폐업수, 프랜차이즈수, 생존율 |
| 8 | **상권변화지표** | `VwsmTrdarIxQq` | SEOUL_API_KEY | 1,650 | 변화지표(HH/HL/LH/LL), 평균영업개월 |

### A3. 외부 API

| # | API 이름 | 엔드포인트 | 키 | 제공 데이터 | 용도 |
|---|---------|-----------|-----|-----------|------|
| 9 | **카카오 로컬** | `dapi.kakao.com/v2/local` | KAKAO_REST_API_KEY | 주변 업소 검색 (카페 2,026건/성수동) | 실시간 경쟁점 파악 |
| 10 | **네이버 검색** | `openapi.naver.com/v1/search` | NAVER_CLIENT_ID/SECRET | 매물 검색, 뉴스 | 매물/트렌드 |
| 11 | **VWorld** | `api.vworld.kr` | VWORLD_API_KEY | 용도지역 (상업/주거/공업) | 입지 적합성 |
| 12 | **KOSIS 통계청** | `kosis.kr/openapi` | KOSIS_API_KEY | 원가비율, 인건비율, 산업통계 | simulation (비용 구조) |
| 13 | **KAMIS 농산물가격** | `kamis.or.kr/service/price/xml.do` | **키 불필요** (p_cert_key=111) | 과일/채소/축산 도소매가 일별 시세 | 식재료 원가 추정 |
| 14 | **한국은행 ECOS** | `ecos.bok.or.kr/api/StatisticSearch` | ECOS_API_KEY | 기준금리, CPI, 대출금리 | funding_planner (금리/물가) |

### A4. ECOS 확인된 통계표 코드

```
722Y001  기준금리 (M)     → /722Y001/M/202401/202501/0101000
901Y009  소비자물가 (M)   → /901Y009/M/202401/202501/0       (총지수)
121Y006  대출금리 (M)     → /121Y006/M/202401/202501/BECBLA01 (예금은행 가중평균)
```

---

## B. 로컬 데이터 (이미 보유, 1.2GB, 670 파일)

### B1. 서울 상권 시계열 (data/seoul/)

| 데이터 | 파일 수 | 기간 | 내용 |
|--------|--------|------|------|
| 매출 (sales) | 27 (전체) + 270 (업종별) | 2019Q1~2025Q3 | 월매출, 시간대/요일/연령/성별 매출 |
| 점포 (stores) | 27 (전체) + 270 (업종별) | 2019Q1~2025Q3 | 점포수, 개폐업, 프랜차이즈, 생존율 |
| 유동인구 | foot_traffic.json | 최신분기 | 시간대/성별/연령 유동인구 1,648건 |
| 상권변화지표 | change_indicator.json | 최신분기 | HH/HL/LH/LL, 영업개월 1,650건 |
| 집객시설 | facilities.json | 최신분기 | 관광/공공/금융/학교 등 31,560건 |
| 상주인구 | living_population.json | - | 상주인구 데이터 |
| 직장인구 | worker_population.json | - | 직장인구 데이터 |
| 상가임대료 | commercial_rent.json | - | 서울 상가 임대료 |
| 학교 | schools.json | - | 학교 위치 |
| 버스승객 | bus_passengers.json | - | 버스 승하차 |
| 지하철승객 | subway_passengers.json | - | 지하철 승하차 |
| 거주인구 | resident_population.json | - | 거주인구 |

**10개 업종별 분류:** CS100001(한식)~CS100010(카페), 각 업종별 sales/stores 분기별 파일

### B2. 가공 데이터 (data/processed/)

| 파일 | 내용 |
|------|------|
| `summary.json` | 전체 요약 — 1,077개 상권, 15,625개 점포, 2025Q3 기준 |
| `{업종}_districts.json` | 업종별 상권 데이터 (126개 필드/레코드) × 10개 업종 |
| `{업종}_summary.json` | 업종별 요약 통계 × 10개 업종 |
| `district_coords.json` | 상권 좌표 |

**126개 필드 포함:** 월매출, 거래건수, 요일별매출, 시간대별매출(6구간), 연령별매출(6구간), 성별매출, 점포수, 개업수, 폐업수, 프랜차이즈수, 유동인구(시간대/성별/연령), 상권변화지표, 영업개월, 임대료 등

### B3. KREI 외식업체 실측 데이터 (data/krei/)

| 파일 | 내용 |
|------|------|
| `krei_2023_processed.json` | 2,854개 외식업체 경영실태 (2023) |

**업종×상권유형별 제공:**
- monthly_rent_median (월세 중위값)
- deposit_median (보증금 중위값)  
- cogs_ratio (원가율)
- labor_ratio (인건비율)
- rent_ratio (임대료율)
- monthly_sales_median (월매출 중위값)
- area_sqm_median (면적 중위값)

### B4. 업종 설정 (data/industries/)

10개 JSON 파일 (CS100001~CS100010), 각 파일 33개 키:
- 메뉴 원가, 장비 비용, 초기재고, 인허가
- 원가율, 공과금비율, 기타비율, 영업이익률 범위
- 상권유형별 계수, 임대료 범위
- 카페타입 키워드, 포지셔닝, 운영형태
- 일일 시나리오, 키워드 감지, 리스크 템플릿
- 성공요인, 타임라인, ML 피처 기본값
- 시스템 프롬프트, 상표 목록, 초기 질문

### B5. 기타

| 경로 | 내용 |
|------|------|
| `api/data/industry_permits.json` | 10개 업종 × 필요 인허가 목록 |
| `api/data/independent_startup_costs.json` | 10개 업종 × 장비/인테리어 비용 |
| `data/localdata/seoul_restaurants.json` | 서울 음식점 121,620개 (영업허가, 면적, 주소) |
| `data/localdata/general_restaurants.csv` | 일반음식점 데이터 |
| `data/geo/seoul_gu_centers.json` | 서울 25개 구 중심 좌표 |
| `data/cache/geocode_cache.json` | 지오코딩 캐시 |
| `data/realtime/coffee_shops_*.json` | 카카오 API 수집 카페 데이터 |
| `data/analytics/events_*.jsonl` | 사용자 이벤트 로그 |
| `data/mock/` | 목업 데이터 (commercial_areas, district_summary, stores) |

---

## C. 신청 대기 중인 API

| # | API | 상태 | 제공 데이터 | 필수도 |
|---|-----|------|-----------|--------|
| 1 | **오피스텔 전월세 실거래가** | data.go.kr 검색 → 신청 필요 | 동네별 보증금/월세 실거래가 | ⭐ 높음 |
| 2 | **건축인허가** | data.go.kr 검색 → 신청 필요 | 허가일, 착공일, 사용승인일 | 중간 |

---

## D. 작동 안 하는 API (확인 완료, 사용 불가)

| API | HTTP | 원인 |
|-----|------|------|
| 공정위 프랜차이즈 (3개) | 404 | API 자체 폐기됨 |
| 토지이용규제정보 | 500 | 서버 에러 |
| 서울 임대료 (VwsmTrdarWrcRentQq) | 500 | 모든 분기 서버에러 |
| 서울 상주인구/소득소비/집객시설 | 500 | 서버 에러 |
| 국가법령정보센터 | 500 | API 다운 |
| **상가 전월세** | N/A | **API 자체가 존재하지 않음** (상가는 거래신고 의무 없음) |

---

## E. API 호출 패턴 (공통)

```python
# IMPORTANT: curl with source .env breaks encoding. MUST use httpx:
import httpx
from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv('DATA_GO_KR_API_KEY')

r = httpx.get(url, params={'serviceKey': key, ...})  # ✅
# NOT: curl with shell-interpolated key  # ❌
```

## F. .env 키 현황

```
SEOUL_API_KEY=746d5264...          ✅ 서울 열린데이터
GEMINI_API_KEY=AIzaSyBL...         ✅ Gemini AI
KAKAO_REST_API_KEY=6a2ceb48...     ✅ 카카오 로컬
NAVER_CLIENT_ID=Yryan3iU...        ✅ 네이버 검색
NAVER_CLIENT_SECRET=YOoZwU...      ✅ 네이버 검색
DATA_GO_KR_API_KEY=74df8c04...     ✅ 공공데이터포털 (건축물대장, 매매실거래, SEMAS)
FTC_FRANCHISE_API_KEY=sq2FPw...    ❌ 공정위 (API 폐기됨, 키만 있음)
KOSIS_API_KEY=NDFlYmM2...          ✅ 통계청
VWORLD_API_KEY=96C762FE...         ✅ VWorld 용도지역
ECOS_API_KEY=IZY3P0N2...           ✅ 한국은행 ECOS (2026.02.10 발급, 2028.02.10 만료)
```

---

## G. 데이터 → 서비스 매핑

| 서비스 (구현 예정) | 필요 데이터 | 소스 |
|-------------------|-----------|------|
| **tax_advisor** | 매출규모, 과세기준 | processed districts (월매출) + 법령 기준값 |
| **labor_advisor** | 인건비율, 최저임금, 4대보험 | KREI (labor_ratio) + KOSIS + 법령 기준값 |
| **lease_advisor** | 임대료, 보증금, 환산보증금 | KREI (rent/deposit) + 오피스텔전월세API(신청중) + 법령 기준값 |
| **compliance_advisor** | 건물정보, 인허가 | 건축물대장API + industry_permits.json + localdata |
| **blueprint_service** | 전체 종합 | processed districts (126필드) + industry configs |
| **funding_planner** | 창업비용, 금리, 대출 | startup_costs.json + ECOS (기준금리/대출금리) + 시뮬레이션 |
| **simulation** (기존) | 매출/비용/BEP | processed districts + KREI + industry configs |
| **verdict** (기존) | GO/NO-GO | processed districts + 전체 점수 |
