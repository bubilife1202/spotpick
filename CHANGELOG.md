# Changelog

## [2.0.0] - 2026-02-06

### 🎯 Major: 대화 중심 UX로 전면 재설계

**목표**: 검색 폼 중심 → 대화 중심 UX 전환으로 사용자 경험 90점+ 달성

### ✨ New Features

#### Backend (API)
- **Structured Chat Response**: `/api/v1/chat` 엔드포인트가 구조화된 JSON 반환
  - `reply`: AI 텍스트 응답
  - `recommendations`: 추천 상권 카드 데이터
  - `charts`: 시간대/요일/연령대/성별 차트 데이터
  - `suggested_questions`: 컨텍스트 기반 후속 질문
  - `context`: 대화에서 추출한 사용자 선호도
- **Context-Aware Logic**: 최근 10개 메시지에서 컨텍스트 추출 및 누적
  - 지역, 예산, 업종, 시간대, 연령대, 성별 선호도 추적
  - 컨텍스트 기반 추천 필터링

#### Frontend (Components)
- **ChatChart.tsx**: 4종 차트 (time/day/age/gender), 확장/축소, 그라디언트 디자인
- **MiniMap.tsx**: 채팅 내 미니 지도, 마커 클릭 팝업, 전체화면 확대
- **SuggestedQuestions.tsx**: 3가지 variant (default/minimal/inline), 키보드 내비게이션
- **RecommendationCard compact mode**: 채팅용 컴팩트 카드, AI 질문 버튼
- **SearchMode.tsx**: 기존 검색 UI를 폴백 모드로 분리

#### Frontend (Main UI)
- **page.tsx 전면 재설계**: 
  - 초기 화면: 영웅 섹션 + InitialQuestions
  - 대화 시작 후: 풀 채팅 인터페이스
  - 구조화된 응답 렌더링 (카드, 차트, 지도, 추천 질문)

### 🔧 Technical Changes
- TypeScript 타입 정의 (`/web/src/types/chat.ts`)
- chat-api.ts 확장 (구조화된 메시지 지원)
- Python 3.9 호환성 (`from __future__ import annotations`)

### 📊 Metrics
- Frontend Build: ✅ 성공 (124KB bundle)
- Backend Syntax: ✅ 통과
- API Response: ✅ 구조화된 JSON 반환 확인

---

## [0.4.0] - Previous Version

- 검색 폼 기반 UI
- 별도 ChatInterface 모달
- 평가 점수: 66.9점 (C등급)
