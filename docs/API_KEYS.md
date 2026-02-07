# API 키 관리 대장

> 만료 전 갱신 필요. 만료 1개월 전 알림 설정 권장.

## 키 목록

| # | 서비스 | 환경변수 | 발급처 | 신청일 | 만료예정일 | 갱신 링크 |
|---|--------|---------|--------|--------|-----------|----------|
| 1 | 서울 열린데이터 | `SEOUL_API_KEY` | data.seoul.go.kr | - | - | https://data.seoul.go.kr |
| 2 | Google Gemini AI | `GEMINI_API_KEY` | Google AI Studio | - | 무제한 | https://aistudio.google.com/apikey |
| 3 | Kakao 로컬 API | `KAKAO_REST_API_KEY` | Kakao Developers | - | 무제한 | https://developers.kakao.com |
| 4 | Naver 검색 API | `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | Naver Developers | - | 무제한 | https://developers.naver.com |
| 5 | 공정위 가맹정보 (창업비용) | `DATA_GO_KR_API_KEY` | data.go.kr | 2026-02-07 | **2028-02-07** | https://www.data.go.kr/data/15110293/openapi.do |
| 6 | 공정위 가맹정보 (업종개황) | `DATA_GO_KR_API_KEY` | data.go.kr | 2026-02-07 | **2028-02-07** | https://www.data.go.kr/data/15109821/openapi.do |
| 7 | 공정위 브랜드별 창업비용 순위 | `DATA_GO_KR_API_KEY` | data.go.kr | 2026-02-07 | **2028-02-07** | https://www.data.go.kr/data/15110379/openapi.do |
| 8 | 지식재산처 상표검색 | `DATA_GO_KR_API_KEY` | data.go.kr | 2026-02-06 | **2028-02-06** | https://www.data.go.kr/data/15057922/openapi.do |
| 9 | 공정위 정보공개서 원본 | `FTC_FRANCHISE_API_KEY` | franchise.ftc.go.kr | 2026-02-07 | - | https://franchise.ftc.go.kr/openApi/guide.do |
| 10 | KOSIS 외식업체경영실태조사 | `KOSIS_API_KEY` | kosis.kr | 2026-02-07 | 무제한 | https://kosis.kr/openapi/ |

## 사용 중인 KOSIS 통계표

> `api/services/kosis_data_service.py`에서 PublicDataReader로 조회.
> API 엔드포인트: `/api/v1/kosis/*`

| 테이블ID | 통계표명 | 활용 용도 | 서비스 연동 |
|---------|---------|---------|-----------|
| DT_114054_029 | 수익성·생산성 분석 | 업종별 영업이익률, 식재료+인건비 비율 | `get_profitability()` |
| DT_114054_028 | 사업실적 | 업종별 매출액, 식재료비·인건비·임차료 비율 | `get_cost_structure()` → 시뮬레이션 원가율 대체 |
| DT_114054_022 | 객단가 | 업종별 평균 객단가 | `get_avg_ticket()` |
| DT_114054_031 | 식재료비 사용 | 업종별 식재료 구성 비율 (쌀/채소/축산물 등) | 예정 |
| DT_114054_072 | 개업 시 투자 비용 | 업종별 창업 투자금 | 예정 |
| DT_114054_021 | 매출액 | 업종별 연간 매출 | 예정 |

**참고**: DT_114054_028은 대분류(일반음식점업/주점업/비알코올 음료점업 등)만 제공.
한식/중식/일식 등 세부 업종은 부모 카테고리(일반음식점업)로 폴백.

## 사용 중인 공정위 API 엔드포인트

| 엔드포인트 | 용도 |
|----------|------|
| `FftcSclasIndutyFntnStatsService/getSclaIndutyFntnOutStats` | 외식 업종 15개 가맹 가입비 통계 |
| `FftcIndutyStusStatsService/getIndutySttusOutStats` | 외식 업종 개황 (브랜드수, 가맹점수, 폐점률) |
| `FftcIndutyAvrRankStatsService/getIndutyAvrOutRankStats` | 브랜드별 창업비용 순위 (활성화 대기) |

## 갱신 방법

1. 해당 갱신 링크 접속 → 로그인
2. 마이페이지 → 활용신청 현황
3. "연장 신청" 버튼 클릭
4. `.env` 파일에 새 키 반영 (키가 변경될 경우)

## 주의사항

- `DATA_GO_KR_API_KEY`는 공정위 4건 + 지식재산처 1건 **공용 키**
- data.go.kr 키는 **2년 주기** 갱신 — 2028년 2월 갱신 필요
- `KOSIS_API_KEY`는 만료 없음 (통계청 공유서비스)
- `FTC_FRANCHISE_API_KEY`는 franchise.ftc.go.kr 전용 (data.go.kr과 별도)
- `.env` 파일은 절대 git에 커밋하지 않음 (`.gitignore`에 등록됨)
