# Builder Curation

데이터 기반 창업 위치 추천 플랫폼

## 서버 실행 (v2.0.0)

| 서비스 | 포트 | URL |
|--------|------|-----|
| API Server | **8002** | http://localhost:8002 |
| Web Server | **3030** | http://localhost:3030 |

```bash
# API 서버 실행
cd /Users/cozac/Code/builder_curation
source .venv/bin/activate
uvicorn api.app:app --host 0.0.0.0 --port 8002

# Web 서버 실행 (다른 터미널)
cd /Users/cozac/Code/builder_curation/web
npm run dev
```

## 개요

Builder Curation은 성공한 매장들의 데이터를 분석하여 창업 위치를 추천하는 서비스입니다.

### 핵심 기능

- **위치 분석**: 유동인구, 경쟁 밀도, 임대료 등 위치별 상세 분석
- **성공 예측**: 성공한 매장 데이터 기반 생존율 및 성공 확률 예측
- **맞춤 추천**: 예산과 조건에 맞는 최적의 위치 TOP N 추천

## 프로젝트 구조

```
builder_curation/
├── collectors/           # 데이터 수집 모듈
│   ├── public_data/      # 공공데이터 API (소상공인, 통계청)
│   ├── crawlers/         # 웹 크롤러 (네이버 플레이스)
│   └── common/           # 공통 유틸리티
├── database/             # 데이터베이스 모델 및 연결
│   ├── models.py         # SQLAlchemy 모델
│   └── migrations/       # Alembic 마이그레이션
├── analysis/             # 분석 엔진
│   ├── scoring/          # 성공 점수 계산
│   ├── features/         # 특성 추출
│   └── models/           # 예측 모델
├── api/                  # FastAPI 서버
│   └── routes/           # API 엔드포인트
├── web/                  # Next.js 프론트엔드
│   └── src/
├── scripts/              # 실행 스크립트
└── infrastructure/       # 인프라 설정
```

## 시작하기

### 요구사항

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16
- Redis 7

### 설치

```bash
# 저장소 클론
git clone https://github.com/your/builder-curation.git
cd builder-curation

# Python 의존성 설치
pip install -e ".[dev]"

# 프론트엔드 의존성 설치
cd web && npm install && cd ..

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 설정
```

### Docker로 실행

```bash
# 전체 서비스 실행
docker-compose up -d

# API 서버만 실행
docker-compose up api

# 데이터 수집 실행
docker-compose --profile collector up collector
```

### 로컬 개발

```bash
# PostgreSQL, Redis 실행
docker-compose up -d db redis

# API 서버 실행
uvicorn api.app:app --reload --reload-dir api --port 8002

# 프론트엔드 개발 서버
cd web && npm run dev
```

## API 엔드포인트

### 추천

- `POST /api/v1/recommendations` - 위치 추천 받기
- `GET /api/v1/recommendations/analyze` - 특정 위치 분석

### 매장

- `GET /api/v1/stores` - 매장 목록 조회
- `GET /api/v1/stores/{id}` - 매장 상세 정보
- `GET /api/v1/stores/{id}/success-factors` - 성공 요인 분석

### 지역

- `GET /api/v1/areas` - 지역 목록
- `GET /api/v1/areas/{code}` - 지역 통계
- `GET /api/v1/areas/{code}/trends` - 지역 트렌드

## 데이터 소스

### 공공데이터

| 소스 | 데이터 | API |
|------|--------|-----|
| 소상공인진흥공단 | 상권정보, 업종별 매출 | data.go.kr |
| 통계청 KOSIS | 인구, 가구, 소득 | kosis.kr |
| 국토교통부 | 실거래가, 공시지가 | data.go.kr |

### 크롤링 (공개 정보)

| 소스 | 데이터 |
|------|--------|
| 네이버 플레이스 | 매장 정보, 리뷰, 평점 |

## 성공 점수 계산

```
성공 점수 = 
    생존 점수 × 0.4 +
    리뷰 점수 × 0.3 +
    성장 점수 × 0.2 +
    안정성 점수 × 0.1
```

### 생존 점수
- 36개월 이상: 1.0
- 24개월 이상: 0.8
- 12개월 이상: 0.6
- 6개월 이상: 0.4
- 6개월 미만: 0.2

### 리뷰 점수
- 평점 (최대 5.0) × 0.7
- 리뷰 수 (최대 500개 기준) × 0.3

## 환경 변수

| 변수 | 설명 | 필수 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 연결 URL | O |
| `REDIS_URL` | Redis 연결 URL | O |
| `DATA_GO_KR_API_KEY` | 공공데이터포털 API 키 | O |
| `NAVER_CLIENT_ID` | 네이버 API 클라이언트 ID | - |
| `NAVER_CLIENT_SECRET` | 네이버 API 시크릿 | - |

## 라이선스

MIT License
