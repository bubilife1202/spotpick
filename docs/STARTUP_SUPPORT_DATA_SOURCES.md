# 한국 정부 창업 지원사업 데이터 수집 가이드

## 목차
1. [K-Startup API](#1-k-startup-api)
2. [중소벤처기업부 지원사업 목록](#2-중소벤처기업부-지원사업-목록)
3. [소상공인시장진흥공단 API](#3-소상공인시장진흥공단-api)
4. [서울시 열린데이터광장](#4-서울시-열린데이터광장)
5. [기업마당(Bizinfo)](#5-기업마당bizinfo)
6. [크롤링 가능 소스](#6-크롤링-가능-소스)
7. [Python 코드 예제](#7-python-코드-예제)

---

## 1. K-Startup API

### 개요
창업진흥원에서 운영하는 K-Startup 포털의 공식 OpenAPI로, 창업지원사업 공고, 통계, 콘텐츠 등을 제공합니다.

### API 정보
- **Base URL**: `https://apis.data.go.kr/B552735/kisedKstartupService01`
- **인증 방식**: ServiceKey (공공데이터포털 발급)
- **응답 형식**: JSON, XML (returnType 파라미터로 선택)
- **트래픽 제한**: 개발계정 월 10,000건

### 엔드포인트

| 엔드포인트 | 기능 | URL |
|-----------|------|-----|
| `/getAnnouncementInformation01` | 지원사업 공고 조회 | 사업명, 모집기간, 지원대상, 지역, 신청방법 |
| `/getBusinessInformation01` | 통합공고 사업 조회 | 지원예산, 지원내용, 지원특징, 대상정보 |
| `/getStatisticalInformation01` | 통계보고서 조회 | 창업 통계 자료 |
| `/getContentInformation01` | 콘텐츠 정보 조회 | 제목, 등록일, 조회수, 파일명 |

### 주요 응답 필드 (공고 정보)
```json
{
  "currentCount": 10,
  "matchCount": 156,
  "totalCount": 156,
  "data": [
    {
      "사업명": "예비창업패키지",
      "사업유형": "사업화",
      "사업개요": "...",
      "지원대상": "예비창업자",
      "모집기간시작": "2026-01-01",
      "모집기간종료": "2026-02-28",
      "지원지역": "전국",
      "신청방법": "K-Startup 온라인 접수",
      "담당부서": "창업진흥원",
      "연락처": "042-480-XXXX"
    }
  ]
}
```

### 활용 신청
1. [공공데이터포털](https://www.data.go.kr/data/15125364/openapi.do) 회원가입
2. "창업진흥원_K-Startup" 검색 후 활용신청
3. 승인 후 인증키 발급 (마이페이지 > 오픈API > 인증키 발급현황)

---

## 2. 중소벤처기업부 지원사업 목록

### 개요
중소벤처기업부에서 제공하는 중소기업 지원사업 목록 데이터셋입니다.

### 데이터 정보
- **형식**: CSV 파일, OpenAPI (XML/JSON)
- **데이터 건수**: 14,388건
- **업데이트 주기**: 연간
- **비용**: 무료
- **라이선스**: 공공저작물 출처표시

### 제공 필드 (9개 항목)
1. **번호**: 일련번호
2. **분야**: 금융, 기술, 인력, 수출, 내수, 창업, 경영, 기타 (8종)
3. **사업명**: 지원사업 명칭
4. **신청시작일자**: 접수 시작일
5. **신청종료일자**: 접수 마감일
6. **소관기관**: 주무 부처/기관
7. **수행기관**: 실제 집행 기관
8. **등록일자**: 데이터 등록일
9. **상세URL**: 상세 정보 링크

### 다운로드 방법
- **파일 다운로드**: 로그인 없이 다운로드 가능
- **API 활용**: 회원가입 및 활용신청 필요
- **URL**: https://www.data.go.kr/data/3034791/fileData.do

---

## 3. 소상공인시장진흥공단 API

### 개요
전국 상가업소 정보를 제공하는 API로, 국세청/카드사 데이터 기반입니다.

### API 정보
- **Base URL**: `https://apis.data.go.kr/B553077/api/open/sdsc2`
- **인증 방식**: ServiceKey (공공데이터포털 발급)
- **응답 형식**: JSON, XML
- **트래픽 제한**:
  - 개발계정: 일 1,000건
  - 운영계정: 일 100,000건 (신청 필요)

### 주요 엔드포인트

| 엔드포인트 | 기능 | 주요 파라미터 |
|-----------|------|--------------|
| `/storeListInDong` | 행정동 단위 상가업소 조회 | divId(행정동코드), pageNo, numOfRows |
| `/storeOne` | 단일 상가업소 상세 조회 | key(업소번호) |
| `/storeListInRadius` | 반경 내 업소 조회 | cx(경도), cy(위도), radius(최대2km) |
| `/storeListInRectangle` | 사각형 영역 업소 조회 | minx, miny, maxx, maxy |
| `/storeListInArea` | 상권 내 업소 조회 | key(상권번호) |
| `/largeUpjongList` | 업종 대분류 목록 | ServiceKey |
| `/middleUpjongList` | 업종 중분류 목록 | indsLclsCd(대분류코드) |

### 응답 필드
- **상호명**: 업소 이름
- **주소**: 지번주소, 도로명주소
- **경위도**: 위도(lat), 경도(lon)
- **업종정보**: 업종코드, 업종명, 표준산업분류코드/명
- **위치정보**: 건물관리번호, 동/층/호 정보
- **상권정보**: 상권코드, 상권명

### 활용 신청
1. [공공데이터포털](https://www.data.go.kr/data/15012005/openapi.do) 접속
2. "소상공인시장진흥공단_상가(상권)정보" 검색
3. 개발계정 활용신청 (자동승인, 약 30분 소요)
4. 운영계정 전환 신청 (트래픽 확대 필요 시)

---

## 4. 서울시 열린데이터광장

### 개요
서울시에서 제공하는 공공데이터 플랫폼으로, 상권 분석 및 소상공인 지원 관련 데이터를 제공합니다.

### API 정보
- **Base URL**: `http://openapi.seoul.go.kr:8088`
- **인증 방식**: API Key (서울 열린데이터광장 발급)
- **응답 형식**: JSON, XML
- **URL 형식**: `{BASE_URL}/{API_KEY}/{응답형식}/{서비스명}/{시작번호}/{종료번호}/{필터}`

### 주요 서비스

| 서비스명 | 기능 | 주요 필드 |
|---------|------|----------|
| `VwsmTrdarSelngQq` | 상권 분기별 추정매출 | 업종, 분기, 매출금액, 건수 |
| `VwsmTrdarStorQq` | 상권 분기별 점포현황 | 업종, 분기, 점포수, 개폐업수 |
| 경제관 데이터 | 지역별 경제 흐름 | 업종분포, 소득/소비, 성장/쇠퇴 |

### 활용 신청
1. [서울 열린데이터광장](https://data.seoul.go.kr) 회원가입
2. 원하는 데이터셋 검색 후 활용신청
3. API 인증키 발급 (마이페이지)

---

## 5. 기업마당(Bizinfo)

### 개요
중소기업 정책정보 통합 포털로, 창업지원사업 공고를 통합 제공합니다.

### 데이터 정보
- **웹사이트**: https://www.bizinfo.go.kr
- **API URL**: https://www.bizinfo.go.kr/web/lay1/program/S1T175C174/apiDetail.do?id=bizinfoApi
- **제공 정보**: 지원사업 공고, 행사정보, 정책뉴스, 입법/행정예고

### 주요 기능
- 기관별/분야별 최신 지원사업 공고
- 2026년 중앙부처 및 지자체 창업지원사업 통합공고
- RestAPI 기반 JSON/XML 자동변환 제공

### 데이터 카테고리
- 사업화 지원
- 시설·공간·보육
- 멘토링·컨설팅·교육
- 행사·네트워킹
- 글로벌진출
- 융자
- 기술개발(R&D)
- 인력 지원

---

## 6. 크롤링 가능 소스

### 6.1 K-Startup 포털 (www.k-startup.go.kr)

**크롤링 대상**:
- 사업공고 목록: `/web/contents/biznotice.do`
- 통합공고: 2026년 창업지원사업 상세페이지

**주요 데이터**:
- 사업명, 사업유형, 주관기관
- 신청기간, 지원대상, 지원내용
- 지원규모, 신청방법

**크롤링 방법**: Selenium (JavaScript 렌더링 필요) 또는 requests + BeautifulSoup

### 6.2 중소벤처24 (www.smes.go.kr)

**크롤링 대상**:
- 지원사업 검색: `/main/policyInfoSearch`

**주요 데이터**:
- 분야별 지원사업 목록
- 기관, 사업명, 예산, 신청기간

### 6.3 창업진흥원 (www.kised.or.kr)

**크롤링 대상**:
- 사업공고: `/menu.es?mid=a10302000000`

**주요 데이터**:
- 예비창업패키지, 초기창업패키지 등
- 공고문 PDF, 신청안내

---

## 7. Python 코드 예제

### 7.1 K-Startup API 조회

```python
import requests
import json
from typing import Dict, List

class KStartupAPI:
    """K-Startup OpenAPI 클라이언트"""

    BASE_URL = "https://apis.data.go.kr/B552735/kisedKstartupService01"

    def __init__(self, service_key: str):
        self.service_key = service_key

    def get_announcements(
        self,
        page: int = 1,
        per_page: int = 10,
        return_type: str = "json"
    ) -> Dict:
        """지원사업 공고 목록 조회

        Args:
            page: 페이지 번호
            per_page: 페이지당 결과 수
            return_type: 응답 형식 (json/xml)

        Returns:
            API 응답 딕셔너리
        """
        endpoint = f"{self.BASE_URL}/getAnnouncementInformation01"
        params = {
            "serviceKey": self.service_key,
            "page": page,
            "perPage": per_page,
            "returnType": return_type
        }

        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API 요청 실패: {e}")
            return {}

    def get_all_announcements(self) -> List[Dict]:
        """모든 지원사업 공고 수집"""
        all_data = []
        page = 1

        while True:
            result = self.get_announcements(page=page, per_page=100)

            if not result or "data" not in result:
                break

            data = result["data"]
            if not data:
                break

            all_data.extend(data)

            # 마지막 페이지 확인
            if result.get("currentCount", 0) < 100:
                break

            page += 1
            print(f"페이지 {page} 수집 중... (총 {len(all_data)}건)")

        return all_data


# 사용 예제
if __name__ == "__main__":
    # 공공데이터포털에서 발급받은 인증키 입력
    SERVICE_KEY = "YOUR_SERVICE_KEY_HERE"

    api = KStartupAPI(SERVICE_KEY)

    # 첫 페이지 조회
    announcements = api.get_announcements(page=1, per_page=10)

    print(f"총 {announcements.get('totalCount', 0)}건의 공고가 있습니다.")
    print("\n최근 공고:")
    for item in announcements.get("data", [])[:5]:
        print(f"- {item.get('사업명')}")
        print(f"  기간: {item.get('모집기간시작')} ~ {item.get('모집기간종료')}")
        print(f"  대상: {item.get('지원대상')}")
        print()
```

### 7.2 소상공인시장진흥공단 API 조회

```python
import requests
from typing import List, Dict

class SmallBusinessAPI:
    """소상공인시장진흥공단 상가정보 API 클라이언트"""

    BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2"

    def __init__(self, service_key: str):
        self.service_key = service_key

    def get_stores_in_dong(
        self,
        div_id: str,
        page_no: int = 1,
        num_of_rows: int = 100
    ) -> Dict:
        """행정동 단위 상가업소 조회

        Args:
            div_id: 행정동 코드 (예: 1168010100 = 서울 강남구 역삼1동)
            page_no: 페이지 번호
            num_of_rows: 페이지당 결과 수

        Returns:
            API 응답 딕셔너리
        """
        endpoint = f"{self.BASE_URL}/storeListInDong"
        params = {
            "serviceKey": self.service_key,
            "divId": div_id,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "type": "json"
        }

        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API 요청 실패: {e}")
            return {}

    def get_stores_in_radius(
        self,
        longitude: float,
        latitude: float,
        radius: int = 500
    ) -> List[Dict]:
        """반경 내 상가업소 조회

        Args:
            longitude: 경도
            latitude: 위도
            radius: 반경 (미터, 최대 2000)

        Returns:
            업소 정보 리스트
        """
        endpoint = f"{self.BASE_URL}/storeListInRadius"
        params = {
            "serviceKey": self.service_key,
            "cx": longitude,
            "cy": latitude,
            "radius": min(radius, 2000),
            "type": "json"
        }

        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data.get("body", {}).get("items", [])
        except requests.RequestException as e:
            print(f"API 요청 실패: {e}")
            return []


# 사용 예제
if __name__ == "__main__":
    SERVICE_KEY = "YOUR_SERVICE_KEY_HERE"

    api = SmallBusinessAPI(SERVICE_KEY)

    # 서울 강남구 역삼1동 상가 조회
    result = api.get_stores_in_dong(div_id="1168010100", page_no=1, num_of_rows=10)

    print(f"조회 결과: {result.get('totalCount', 0)}건")
    for store in result.get("body", {}).get("items", [])[:5]:
        print(f"\n상호: {store.get('상호명')}")
        print(f"업종: {store.get('상권업종명')}")
        print(f"주소: {store.get('도로명주소')}")
        print(f"위치: {store.get('위도')}, {store.get('경도')}")
```

### 7.3 서울시 열린데이터광장 API 조회

```python
import requests
import json
from pathlib import Path
from typing import List, Dict

class SeoulOpenDataAPI:
    """서울 열린데이터광장 API 클라이언트"""

    BASE_URL = "http://openapi.seoul.go.kr:8088"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_sales_by_quarter(
        self,
        quarter: str,
        start: int = 1,
        end: int = 1000
    ) -> List[Dict]:
        """상권 분기별 추정매출 조회

        Args:
            quarter: 분기 (예: "20261" = 2026년 1분기)
            start: 시작 인덱스
            end: 종료 인덱스

        Returns:
            매출 데이터 리스트
        """
        service_name = "VwsmTrdarSelngQq"
        url = f"{self.BASE_URL}/{self.api_key}/json/{service_name}/{start}/{end}/{quarter}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if service_name in data:
                return data[service_name].get("row", [])
            return []
        except requests.RequestException as e:
            print(f"API 요청 실패: {e}")
            return []

    def collect_quarter_data(
        self,
        service_name: str,
        quarter: str,
        industry_filter: List[str] = None
    ) -> Dict[str, List]:
        """분기 데이터 전체 수집 (업종별 필터링)

        Args:
            service_name: 서비스명 (VwsmTrdarSelngQq, VwsmTrdarStorQq)
            quarter: 분기
            industry_filter: 필터링할 업종코드 리스트

        Returns:
            업종코드별 데이터 딕셔너리
        """
        # 전체 건수 확인
        url = f"{self.BASE_URL}/{self.api_key}/json/{service_name}/1/1/{quarter}"
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            total = data[service_name].get("list_total_count", 0)
        except Exception:
            return {}

        print(f"전체 {total:,}건 중 필터링 시작...")

        by_industry = {code: [] for code in (industry_filter or [])}
        page_size = 1000

        for start in range(1, total + 1, page_size):
            end = min(start + page_size - 1, total)
            rows = self.get_data_page(service_name, start, end, quarter)

            for row in rows:
                code = row.get("SVC_INDUTY_CD", "")
                if not industry_filter or code in industry_filter:
                    if code not in by_industry:
                        by_industry[code] = []
                    by_industry[code].append(row)

            if start % 10000 == 1:
                filtered_count = sum(len(v) for v in by_industry.values())
                print(f"  {start:,}/{total:,} 처리 중... ({filtered_count}건)")

        return by_industry

    def get_data_page(
        self,
        service_name: str,
        start: int,
        end: int,
        quarter: str
    ) -> List[Dict]:
        """페이지 단위 데이터 조회"""
        url = f"{self.BASE_URL}/{self.api_key}/json/{service_name}/{start}/{end}/{quarter}"
        try:
            response = requests.get(url, timeout=30)
            data = response.json()
            if service_name in data:
                return data[service_name].get("row", [])
        except Exception as e:
            print(f"에러: {e}")
        return []


# 사용 예제
if __name__ == "__main__":
    API_KEY = "YOUR_API_KEY_HERE"

    api = SeoulOpenDataAPI(API_KEY)

    # 2026년 1분기 매출 데이터 조회
    sales_data = api.get_sales_by_quarter(quarter="20261", start=1, end=100)

    print(f"조회된 데이터: {len(sales_data)}건")
    for item in sales_data[:3]:
        print(f"\n상권명: {item.get('TRDAR_NM')}")
        print(f"업종: {item.get('SVC_INDUTY_NM')}")
        print(f"매출금액: {item.get('SELNG_AMT', 0):,}원")
        print(f"매출건수: {item.get('SELNG_CNT', 0):,}건")
```

### 7.4 중소벤처기업부 CSV 파일 다운로드 및 파싱

```python
import requests
import csv
from io import StringIO
from typing import List, Dict
from datetime import datetime

class SMEProgramDownloader:
    """중소벤처기업부 지원사업 데이터 다운로더"""

    # 공공데이터포털 파일 데이터 URL
    FILE_URL = "https://www.data.go.kr/cmm/cmm/fileDownload.do"

    def download_csv(self, dataset_id: str = "3034791") -> List[Dict]:
        """CSV 파일 다운로드 및 파싱

        Args:
            dataset_id: 데이터셋 ID (중소기업지원사업목록)

        Returns:
            지원사업 데이터 리스트
        """
        params = {
            "atchFileId": dataset_id
        }

        try:
            response = requests.get(self.FILE_URL, params=params, timeout=60)
            response.encoding = "utf-8"

            # CSV 파싱
            csv_data = StringIO(response.text)
            reader = csv.DictReader(csv_data)

            programs = []
            for row in reader:
                programs.append({
                    "번호": row.get("번호", ""),
                    "분야": row.get("분야", ""),
                    "사업명": row.get("사업명", ""),
                    "신청시작일": row.get("신청시작일자", ""),
                    "신청종료일": row.get("신청종료일자", ""),
                    "소관기관": row.get("소관기관", ""),
                    "수행기관": row.get("수행기관", ""),
                    "등록일자": row.get("등록일자", ""),
                    "상세URL": row.get("상세URL", "")
                })

            return programs
        except Exception as e:
            print(f"다운로드 실패: {e}")
            return []

    def filter_by_category(
        self,
        programs: List[Dict],
        category: str = "창업"
    ) -> List[Dict]:
        """분야별 필터링"""
        return [p for p in programs if category in p.get("분야", "")]

    def filter_active_programs(
        self,
        programs: List[Dict]
    ) -> List[Dict]:
        """현재 진행 중인 사업 필터링"""
        today = datetime.now().strftime("%Y%m%d")
        active = []

        for p in programs:
            start = p.get("신청시작일", "").replace("-", "")
            end = p.get("신청종료일", "").replace("-", "")

            if start <= today <= end:
                active.append(p)

        return active


# 사용 예제
if __name__ == "__main__":
    downloader = SMEProgramDownloader()

    # 전체 데이터 다운로드
    print("중소기업 지원사업 데이터 다운로드 중...")
    all_programs = downloader.download_csv()

    print(f"총 {len(all_programs)}건의 지원사업이 있습니다.")

    # 창업 분야 필터링
    startup_programs = downloader.filter_by_category(all_programs, "창업")
    print(f"창업 분야: {len(startup_programs)}건")

    # 현재 진행 중인 사업
    active_programs = downloader.filter_active_programs(startup_programs)
    print(f"현재 진행 중: {len(active_programs)}건")

    # 상위 5개 출력
    print("\n현재 진행 중인 창업 지원사업:")
    for p in active_programs[:5]:
        print(f"\n사업명: {p['사업명']}")
        print(f"기간: {p['신청시작일']} ~ {p['신청종료일']}")
        print(f"소관기관: {p['소관기관']}")
        print(f"URL: {p['상세URL']}")
```

### 7.5 웹 크롤링 (K-Startup 포털)

```python
import time
from typing import List, Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

class KStartupCrawler:
    """K-Startup 포털 크롤러 (Selenium 사용)"""

    BASE_URL = "https://www.k-startup.go.kr"

    def __init__(self, headless: bool = True):
        options = webdriver.ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        self.driver = webdriver.Chrome(options=options)

    def __del__(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def get_announcements(self, max_pages: int = 5) -> List[Dict]:
        """사업공고 목록 크롤링

        Args:
            max_pages: 최대 페이지 수

        Returns:
            공고 데이터 리스트
        """
        announcements = []

        url = f"{self.BASE_URL}/web/contents/biznotice.do"
        self.driver.get(url)

        for page in range(1, max_pages + 1):
            print(f"페이지 {page} 크롤링 중...")

            # 페이지 로딩 대기
            time.sleep(2)

            # HTML 파싱
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # 공고 목록 추출 (실제 선택자는 사이트 구조에 맞게 수정 필요)
            items = soup.select(".notice-list .notice-item")

            for item in items:
                try:
                    announcement = {
                        "제목": item.select_one(".title").text.strip(),
                        "주관기관": item.select_one(".agency").text.strip(),
                        "신청기간": item.select_one(".period").text.strip(),
                        "링크": self.BASE_URL + item.select_one("a")["href"]
                    }
                    announcements.append(announcement)
                except Exception as e:
                    print(f"항목 파싱 실패: {e}")
                    continue

            # 다음 페이지로 이동
            try:
                next_btn = self.driver.find_element(By.CSS_SELECTOR, ".pagination .next")
                next_btn.click()
                time.sleep(1)
            except:
                print("마지막 페이지입니다.")
                break

        return announcements

    def get_announcement_detail(self, url: str) -> Dict:
        """공고 상세 정보 크롤링"""
        self.driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(self.driver.page_source, "html.parser")

        detail = {
            "사업명": soup.select_one(".title").text.strip(),
            "주관기관": soup.select_one(".agency").text.strip(),
            "신청기간": soup.select_one(".period").text.strip(),
            "지원대상": soup.select_one(".target").text.strip(),
            "지원내용": soup.select_one(".content").text.strip(),
            "문의처": soup.select_one(".contact").text.strip()
        }

        return detail


# 사용 예제 (Selenium 필요)
if __name__ == "__main__":
    # 주의: 실제 사용 시 robots.txt 확인 및 API 우선 사용 권장
    crawler = KStartupCrawler(headless=True)

    # 공고 목록 크롤링
    announcements = crawler.get_announcements(max_pages=3)

    print(f"총 {len(announcements)}건의 공고를 수집했습니다.")

    for item in announcements[:5]:
        print(f"\n제목: {item['제목']}")
        print(f"기관: {item['주관기관']}")
        print(f"기간: {item['신청기간']}")
```

### 7.6 통합 데이터 수집 파이프라인

```python
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

class StartupSupportDataCollector:
    """창업 지원사업 데이터 통합 수집기"""

    def __init__(
        self,
        kstartup_key: str,
        smallbiz_key: str,
        seoul_key: str,
        output_dir: str = "./startup_data"
    ):
        self.kstartup_api = KStartupAPI(kstartup_key)
        self.smallbiz_api = SmallBusinessAPI(smallbiz_key)
        self.seoul_api = SeoulOpenDataAPI(seoul_key)
        self.sme_downloader = SMEProgramDownloader()

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect_all(self) -> Dict[str, List]:
        """모든 소스에서 데이터 수집"""
        print("=" * 60)
        print("창업 지원사업 데이터 통합 수집 시작")
        print(f"수집 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        results = {}

        # 1. K-Startup API
        print("\n[1/3] K-Startup 공고 수집 중...")
        results["kstartup"] = self.kstartup_api.get_all_announcements()
        print(f"  → {len(results['kstartup'])}건 수집 완료")

        # 2. 중소벤처기업부 CSV
        print("\n[2/3] 중소벤처기업부 지원사업 다운로드 중...")
        all_programs = self.sme_downloader.download_csv()
        results["sme_all"] = all_programs
        results["sme_startup"] = self.sme_downloader.filter_by_category(
            all_programs, "창업"
        )
        results["sme_active"] = self.sme_downloader.filter_active_programs(
            results["sme_startup"]
        )
        print(f"  → 전체: {len(results['sme_all'])}건")
        print(f"  → 창업: {len(results['sme_startup'])}건")
        print(f"  → 진행중: {len(results['sme_active'])}건")

        # 3. 통합 데이터 생성
        print("\n[3/3] 통합 데이터 생성 중...")
        results["integrated"] = self.integrate_data(results)
        print(f"  → {len(results['integrated'])}건 통합 완료")

        # 결과 저장
        self.save_results(results)

        print("\n" + "=" * 60)
        print("수집 완료!")
        print(f"저장 경로: {self.output_dir}")
        print("=" * 60)

        return results

    def integrate_data(self, results: Dict) -> List[Dict]:
        """데이터 통합 및 정규화"""
        integrated = []

        # K-Startup 데이터 정규화
        for item in results.get("kstartup", []):
            integrated.append({
                "source": "K-Startup",
                "title": item.get("사업명", ""),
                "agency": item.get("담당부서", ""),
                "category": item.get("사업유형", ""),
                "target": item.get("지원대상", ""),
                "period_start": item.get("모집기간시작", ""),
                "period_end": item.get("모집기간종료", ""),
                "region": item.get("지원지역", ""),
                "contact": item.get("연락처", ""),
                "description": item.get("사업개요", "")
            })

        # 중소벤처기업부 데이터 정규화
        for item in results.get("sme_active", []):
            integrated.append({
                "source": "중소벤처기업부",
                "title": item.get("사업명", ""),
                "agency": item.get("소관기관", ""),
                "category": item.get("분야", ""),
                "target": "",
                "period_start": item.get("신청시작일", ""),
                "period_end": item.get("신청종료일", ""),
                "region": "",
                "contact": "",
                "description": "",
                "detail_url": item.get("상세URL", "")
            })

        return integrated

    def save_results(self, results: Dict):
        """결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for key, data in results.items():
            filename = self.output_dir / f"{key}_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  저장: {filename}")


# 통합 수집 실행
if __name__ == "__main__":
    collector = StartupSupportDataCollector(
        kstartup_key="YOUR_KSTARTUP_KEY",
        smallbiz_key="YOUR_SMALLBIZ_KEY",
        seoul_key="YOUR_SEOUL_KEY",
        output_dir="./data/startup_support"
    )

    results = collector.collect_all()

    # 통계 출력
    print("\n통합 데이터 통계:")
    print(f"  K-Startup: {len(results['kstartup'])}건")
    print(f"  중소벤처기업부: {len(results['sme_active'])}건")
    print(f"  통합: {len(results['integrated'])}건")
```

---

## 8. 환경 설정

### 8.1 필요한 라이브러리 설치

```bash
# 기본 라이브러리
pip install requests beautifulsoup4 python-dotenv

# 크롤링용 (선택)
pip install selenium webdriver-manager
```

### 8.2 환경 변수 설정 (.env)

```bash
# 공공데이터포털 인증키
KSTARTUP_SERVICE_KEY=your_kstartup_key
SMALLBIZ_SERVICE_KEY=your_smallbiz_key

# 서울 열린데이터광장 인증키
SEOUL_API_KEY=your_seoul_api_key
```

### 8.3 사용 예제

```python
import os
from dotenv import load_dotenv

load_dotenv()

# API 클라이언트 초기화
kstartup_api = KStartupAPI(os.getenv("KSTARTUP_SERVICE_KEY"))
smallbiz_api = SmallBusinessAPI(os.getenv("SMALLBIZ_SERVICE_KEY"))
seoul_api = SeoulOpenDataAPI(os.getenv("SEOUL_API_KEY"))

# 데이터 수집
announcements = kstartup_api.get_all_announcements()
print(f"수집 완료: {len(announcements)}건")
```

---

## 9. 주의사항

### 9.1 API 사용 제한
- **트래픽 제한**: 개발/운영 계정별 일일 요청 제한 준수
- **요청 간격**: 과도한 요청으로 인한 차단 방지 (0.2~1초 간격 권장)
- **타임아웃**: 네트워크 오류 대비 적절한 타임아웃 설정 (30초 권장)

### 9.2 크롤링 시 유의사항
- **robots.txt 확인**: 크롤링 허용 여부 사전 확인
- **API 우선 사용**: 공식 API가 있는 경우 크롤링 대신 API 사용
- **서버 부하 고려**: 적절한 요청 간격 설정
- **법적 책임**: 저작권 및 개인정보 보호법 준수

### 9.3 데이터 품질
- **데이터 검증**: 수집 후 필수 필드 존재 여부 확인
- **중복 제거**: 여러 소스에서 수집 시 중복 데이터 정리
- **정규화**: 일관된 형식으로 데이터 변환 (날짜, 금액 등)

---

## 10. 참고 링크

### 공식 API 문서
- [공공데이터포털](https://www.data.go.kr)
- [K-Startup API](https://www.data.go.kr/data/15125364/openapi.do)
- [소상공인시장진흥공단 API](https://www.data.go.kr/data/15012005/openapi.do)
- [서울 열린데이터광장](https://data.seoul.go.kr)

### 관련 포털
- [K-Startup 창업지원포털](https://www.k-startup.go.kr)
- [기업마당](https://www.bizinfo.go.kr)
- [중소벤처24](https://www.smes.go.kr)
- [창업진흥원](https://www.kised.or.kr)

### 라이브러리
- [PublicDataReader](https://github.com/WooilJeong/PublicDataReader) - 공공데이터 조회 파이썬 라이브러리
- [Requests](https://requests.readthedocs.io) - HTTP 라이브러리
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) - HTML 파싱
- [Selenium](https://selenium-python.readthedocs.io) - 웹 자동화

---

## 마치며

이 가이드는 2026년 2월 기준으로 작성되었으며, API 스펙 변경 시 공식 문서를 참조하시기 바랍니다.

데이터 수집 후에는 반드시 데이터 품질 검증 및 정규화 작업을 수행하고, 개인정보가 포함된 경우 관련 법규를 준수해야 합니다.

문의사항이나 추가 정보가 필요한 경우 각 기관의 고객센터나 공공데이터포털 문의 게시판을 이용하시기 바랍니다.
