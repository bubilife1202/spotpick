# Builder Curation - Version History

> 버전 업데이트 기록 및 변경사항 추적

---

## Version Summary

| Version | Date | Status | Key Changes |
|---------|------|--------|-------------|
| v0.1.0 | 2026-02-03 | Released | 초기 프로젝트 구조 생성 |
| v0.2.0 | 2026-02-03 | Released | 서울시 API 데이터 수집 완료 |
| v0.3.0 | 2026-02-04 | Released | 64개 필드 데이터 가공 |
| v0.4.0 | 2026-02-04 | **Current** | Gemini 챗봇 + API 통합 |

---

## [v0.4.0] - 2026-02-04 16:30 KST

### Added
- Gemini 2.5 Flash 기반 대화형 창업 상담 서비스
- 64개 필드 전체 활용 추천 로직
- 시간대/요일/연령대/성별 분석 기능
- `/api/chat` 엔드포인트 추가
- 시스템 프롬프트 강화 (64개 필드 활용 명시)

### Changed
- `chat_service.py` - 시간대/연령대/성별 선호 추출 로직 추가
- `data_service.py` - 64개 필드 기반 추천 응답 구조 개선
- 응답 템플릿에 피크 시간대, 고객층 분석 포함

### Technical Details
- Model: `gemini-2.5-flash`
- API Key: `.env`에서 로드
- 데이터: 1,077개 상권, 15,625개 점포

---

## [v0.3.0] - 2026-02-04 14:00 KST

### Added
- `scripts/analyze_seoul_data.py` 풀버전 (64개 필드)
- `data/processed/coffee_districts.json` 가공 데이터
- `data/processed/summary.json` 요약 통계 + 6년 트렌드

### Data Fields (64개)
```
기본 (3): district_code, district_name, district_type
매출 (2): monthly_sales, monthly_transactions
시간대별 (6): time_00_06 ~ time_21_24
요일별 (7): mon ~ sun
성별 (2): male_sales, female_sales
연령대별 (6): age_10 ~ age_60
경쟁 (4): store_count, new/closed/franchise_stores
분석 (4): peak_time, peak_day, main_age_group, survival_rate
비율 (30+): 각종 ratio 필드
```

---

## [v0.2.0] - 2026-02-03 22:00 KST

### Added
- 서울시 우리마을가게 상권분석 API 연동
- `scripts/collect_seoul_api.py` 데이터 수집 스크립트
- 매출 데이터: 27,492건 (2019Q1~2025Q3)
- 점포 데이터: 40,499건

### Data Storage
- `data/seoul/sales_*.json` - 분기별 매출 데이터
- `data/seoul/stores_*.json` - 분기별 점포 데이터

---

## [v0.1.0] - 2026-02-03 18:00 KST

### Added
- 프로젝트 초기 구조 생성
- FastAPI 백엔드 기본 구조
- Next.js 프론트엔드 기본 구조
- 데이터베이스 모델 정의
- API 라우트 스켈레톤

### Project Structure
```
builder_curation/
├── api/          # FastAPI 백엔드
├── web/          # Next.js 프론트엔드
├── collectors/   # 데이터 수집 모듈
├── analysis/     # 분석 엔진
├── database/     # DB 모델
└── scripts/      # 유틸리티 스크립트
```

---

## Roadmap

### v0.5.0 (Planned)
- [ ] 챗봇 UI 프론트엔드 구현
- [ ] 스트리밍 응답 API
- [ ] Rate Limiting

### v0.6.0 (Planned)
- [ ] 온보딩 플로우
- [ ] 데이터 시각화 차트

### v1.0.0 (Target)
- [ ] ML 성공 예측 모델
- [ ] 프리미엄 기능
- [ ] 프로덕션 배포

---

*Last Updated: 2026-02-04 16:32 KST*
