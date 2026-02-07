# OpenClaw 브라우저(Playwright) 활성화 가이드

## 1단계: Playwright 설치

```bash
# npm 방식 (권장)
npm install -g playwright
npx playwright install chromium

# 또는 pip 방식
pip install playwright
playwright install chromium
```

> `playwright install` 하면 Chromium 브라우저를 자동 다운로드함 (~200MB)

## 2단계: OpenClaw 브라우저 도구 활성화

터미널에서:

```bash
openclaw configure --section web
```

인터랙티브 메뉴가 나오면:
- `browser` → **enabled: true**
- `headless` → **true** (백그라운드 실행) 또는 **false** (브라우저 보이게)

### 수동 설정 (openclaw.json 직접 편집)

설정 파일 위치 확인:
```bash
openclaw config path
```

보통:
- macOS: `~/.config/openclaw/openclaw.json`
- Linux: `~/.config/openclaw/openclaw.json`

파일 열어서 아래 추가:

```json
{
  "browser": {
    "enabled": true,
    "headless": true,
    "defaultViewport": {
      "width": 1280,
      "height": 720
    }
  },
  "web_search": {
    "enabled": true,
    "provider": "duckduckgo"
  }
}
```

## 3단계: 게이트웨이 재시작

```bash
# OpenClaw 재시작
openclaw stop
openclaw start
```

## 4단계: 테스트

OpenClaw 채팅에서:
```
오늘 네이버 실시간 검색어 알려줘
```

또는:
```
https://naver.com 에 들어가서 스크린샷 찍어줘
```

브라우저 도구가 활성화되면 navigate, snapshot, screenshot, act(클릭/입력) 전부 사용 가능.

## 웹 검색도 같이 쓰기 (Brave Search 무료)

1. https://brave.com/search/api 가입 (무료 2,000회/월)
2. API 키 받기
3. 환경변수 설정:
```bash
export BRAVE_API_KEY="너의_API_키"
```
또는 openclaw.json에:
```json
{
  "web_search": {
    "enabled": true,
    "provider": "brave",
    "apiKey": "너의_API_키"
  }
}
```

## 트러블슈팅

### Playwright 감지 안 될 때
```bash
# Playwright 경로 확인
npx playwright --version

# 브라우저 설치 확인
npx playwright install --dry-run
```

### 권한 문제
```bash
# macOS에서 Chromium 실행 허용
xattr -cr ~/Library/Caches/ms-playwright/
```

### headless 모드 안 될 때
```json
{
  "browser": {
    "enabled": true,
    "headless": false,
    "executablePath": "/usr/bin/chromium-browser"
  }
}
```
