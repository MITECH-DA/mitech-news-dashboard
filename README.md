# MITech 의료기기 뉴스 트렌드 분석 파이프라인

매일 쏟아지는 의료기기 뉴스(RSS + 네이버 뉴스)를 수집 → 정제 → LLM 태깅 → 트렌드 집계까지
자동화하는 최소 기능(MVP) 파이프라인입니다.

## 구조

```
mitech_news_pipeline/
├── config.py         # RSS 소스, 키워드, 카테고리, API 키 등 전역 설정
├── collector.py       # RSS/네이버뉴스 수집
├── cleaner.py         # 중복 제거, boilerplate 제거
├── tagger.py           # Claude API로 회사/제품/기술/카테고리 구조화 태깅
├── storage.py          # SQLite 저장 (raw_articles, tagged_articles)
├── pipeline.py         # 전체 흐름 오케스트레이션 (매일 실행할 스크립트)
├── trend_report.py     # 기간별 트렌드 집계 리포트 (콘솔 + CSV)
├── requirements.txt
└── .env.example
```

## 설치

```bash
pip install -r requirements.txt
cp .env.example .env
# .env 파일 열어서 ANTHROPIC_API_KEY 등 채우기
```

## 실행

```bash
# 1. 매일 수집+정제+태깅 실행
python pipeline.py

# 2. 최근 7일 트렌드 리포트 출력 (기본값)
python trend_report.py --days 7

# 3. 최근 30일 리포트를 다른 파일명으로 저장
python trend_report.py --days 30 --csv monthly_trend.csv
```

## cron으로 자동화하기 (매일 오전 8시 실행)

```bash
crontab -e
# 아래 줄 추가
0 8 * * * cd /path/to/mitech_news_pipeline && /usr/bin/python3 pipeline.py >> pipeline.log 2>&1
```

## 인터랙티브 HTML 대시보드

`dashboard/` 폴더에 `trend_report.csv`를 시각화하는 standalone HTML 대시보드가 있습니다.

```
dashboard/
├── index.html       # 대시보드 본체 (이 파일을 브라우저로 열면 됩니다)
├── dashboard.js       # 필터링·집계·차트/네트워크 렌더링 로직
└── sample_data.js      # 미리보기용 샘플 데이터
```

### 사용법 (자동 로드)

`trend_report.py`를 실행하면 CSV와 함께 `dashboard/dashboard_data.js`가 자동으로 생성됩니다.
이후 `dashboard/index.html`을 열면 **업로드 없이 곧바로 최신 데이터가 표시**됩니다.

```bash
python trend_report.py --days 7
# -> trend_report.csv, dashboard/dashboard_data.js 둘 다 생성됨
```

1. 위 명령을 실행합니다.
2. `dashboard/index.html`을 더블클릭해서 브라우저로 엽니다 (서버 불필요).
3. 데이터가 자동으로 표시됩니다. 헤더에 "생성 YYYY-MM-DD HH:MM" 시각이 함께 표시되어 최신 여부를 바로 확인할 수 있습니다.
4. 이미 대시보드를 열어둔 상태라면 파이프라인을 재실행한 뒤 **브라우저를 새로고침**해야 최신 데이터가 반영됩니다 (자동 갱신은 아님).
5. 다른 CSV(예: 지난주 리포트)를 보고 싶다면 헤더의 "다른 CSV 불러오기" 링크를 눌러 수동 업로드 화면으로 전환할 수 있습니다.
6. 대시보드 데이터 파일을 만들고 싶지 않다면 `python trend_report.py --no-dashboard`로 CSV만 생성할 수 있습니다.

> `dashboard_data.js`는 `trend_report.py`가 매번 덮어쓰는 파일이라 git에 커밋하지 않는 것을 권장합니다 (`.gitignore`에 추가).

### 사용법 (수동 업로드, 대안)

파이프라인 없이 다른 환경에서 만든 CSV를 확인하고 싶을 때는 `dashboard/index.html`을 열고 "다른 CSV 불러오기" → CSV 파일을 드래그 앤 드롭하거나 선택하면 됩니다. 데이터는 브라우저 안에서만 처리되고 외부로 전송되지 않습니다. 구조를 먼저 확인하고 싶다면 "샘플 데이터로 미리보기" 버튼을 눌러보세요.

### 포함된 시각화

- **최신 주요 기사**: 최근 6건을 카드뉴스 형태(3x2 그리드)로 보여줍니다. 뉴스 원문에서 추출된 대표 이미지가 있으면 배경으로, 없으면 단색 카드로 표시되며 카테고리(색상 구분)와 제목이 이미지 하단에 오버레이됩니다. 카드 클릭 시 원문으로 이동.
- **기사량 추이**: 카테고리별 일별/주별 발행량 (스택 바 차트)
- **최다 언급 키워드**: 회사/기술/적응증 전환 가능한 빈도 차트
- **카테고리 분포**: 도넛 차트
- **인텔리전스 맵**: 회사·기술·적응증의 동시 언급 관계를 보여주는 D3 force-directed 네트워크 그래프 (드래그·호버로 탐색 가능)

기간·카테고리·키워드 검색 필터를 적용하면 모든 시각화가 실시간으로 함께 갱신됩니다.

> 카드뉴스의 대표 이미지는 `collector.py`가 RSS 항목의 media:thumbnail / media:content / enclosure / 본문 내 첫 `<img>` 순으로 best-effort 추출합니다(네이버 뉴스 검색 API는 썸네일을 제공하지 않아 항상 공백). 이미지가 없는 기사는 카테고리 색상이 반영된 단색 카드로 자동 대체됩니다.

### 검증 내용

- Playwright로 실제 브라우저 렌더링 테스트 완료 (콘솔 에러 없음)
- 샘플 데이터(24건) 기준 CSV 파싱, 필터링, 네트워크 노드/엣지 생성 로직을 Node.js로 별도 단위 검증
- 카테고리 필터 적용 시 KPI·테이블이 정확히 갱신되는 것 확인
- `dashboard_data.js` 자동 생성 및 자동 로드 흐름 검증: 백틱·역슬래시가 포함된 기사 제목으로 이스케이프 처리 테스트, 파일 존재/부재 양쪽 케이스에서 정상 폴백(업로드 화면 표시) 확인, "다른 CSV 불러오기" 링크 동작 확인

### 다음 확장 아이디어

- pptxgenjs 파이프라인과 연결해서 주간 리포트 슬라이드에 스크린샷 자동 삽입
- 시계열 차트에 "전주 대비 증감률" 같은 지표 추가
- 인텔리전스 맵 노드 클릭 시 하단 테이블을 해당 키워드 기사만 필터링하도록 연동



## 다음 확장 단계

00. **관련성 필터 (노이즈 제거)**: 네이버 뉴스 검색은 boolean을 지원하지 않아 결과가 느슨하게 잡힙니다(정치/증시/스포츠 후원 기사 등이 섞여 들어옴). `config.RELEVANCE_KEYWORDS`에 없는 키워드면 네이버 소스 기사만 수집 단계에서 자동 제외됩니다(`cleaner.is_relevant()` / `pipeline.py`). RSS 소스(MassDevice 등)는 이미 의료기기 전문 매체이므로 이 필터를 적용하지 않습니다. 이미 DB에 쌓인 "기타" 카테고리 노이즈는 `python cleanup_irrelevant.py`(dry-run) → `python cleanup_irrelevant.py --apply`로 정리할 수 있습니다. 단, 진짜 의료기기 기사인데 LLM이 "기타"로 잘못 태깅한 경우는 삭제하지 않고 유지하니, 그 목록은 카테고리 재태깅을 검토해보세요.
000. **네이버 기사 이미지 보강**: 네이버 뉴스 검색 API는 썸네일을 제공하지 않아서, 필터·중복제거를 통과한 네이버 소스 기사에 한해 원문 페이지의 `og:image`(없으면 `twitter:image`) 메타태그를 best-effort로 가져옵니다(`collector.enrich_images()`, `pipeline.py` 3단계). RSS 소스는 건드리지 않습니다. 사이트에 따라 자바스크립트 렌더링이 필요하거나 크롤링을 막아둔 경우 이미지를 못 가져올 수 있는데, 이 경우 대시보드는 자동으로 단색 카드로 대체합니다. 기사 수가 많으면 원문 페이지를 하나씩 요청하는 만큼 파이프라인 실행 시간이 늘어날 수 있습니다.
0. **네이버 검색 쿼리는 boolean을 지원하지 않습니다**: `query` 파라미터에 AND/OR/괄호를 넣어도 구조화된 쿼리로 해석되지 않고 문자열 그대로 취급됩니다. `config.py`의 `NAVER_TOPIC_TERMS` x `NAVER_CONTEXT_TERMS` 조합처럼, 원하는 boolean 로직을 파이썬에서 미리 곱집합으로 풀어서 여러 번 호출하는 방식을 씁니다. 그룹 크기를 곱한 만큼 호출 횟수가 늘어나니(예: 4×5=20회) 일일 호출 한도(기본 25,000회)를 넘지 않게 조절하세요.
1. **RSS 소스 추가**: `config.py`의 `RSS_SOURCES`에 매체 추가 (MedTech Insight, 식약처 보도자료 등).
   식약처처럼 RSS가 없는 사이트는 `collector.py`에 전용 크롤러 함수를 추가해야 합니다
   (사이트 구조가 바뀔 수 있으므로 별도 유지보수 필요).
2. **MySQL 전환**: `storage.py`의 `get_connection()` 함수만 `mysql-connector-python`으로
   교체하면 나머지 코드는 거의 그대로 사용 가능합니다. 스키마(`SCHEMA` 변수)의
   `AUTOINCREMENT` → `AUTO_INCREMENT` 정도만 손보면 됩니다.
3. **주간 자동 리포트**: `trend_report.py` 실행 결과를 Slack/이메일로 발송하거나,
   pptxgenjs 파이프라인과 연결해 주간 슬라이드 자동 생성까지 확장 가능합니다.
4. **시계열/네트워크 시각화**: `trend_report.py`가 만드는 CSV를 Python(matplotlib/plotly)이나
   인터랙티브 HTML 대시보드로 넘기면, 이전에 논의했던 "키워드 시계열 추이", "회사-기술 네트워크" 시각화로
   바로 이어집니다.
5. **정확도 검증**: 초기 1~2주는 LLM 태깅 결과를 사람이 샘플링해서 검수하고,
   `tagger.py`의 `SYSTEM_PROMPT`를 계속 다듬는 걸 권장합니다 (분류 정확도가 가장 중요한 부분).

## 설계 메모 (검증 내용)

- `collector.py`: 로컬 샘플 RSS로 파싱/날짜 정규화 로직 검증 완료
  (실제 매체 서버 접근은 이 환경 네트워크 정책상 테스트 불가 — 태준님 환경에서 최초 1회 확인 필요)
- `cleaner.py`: boilerplate 제거, 제목 유사도 기반 중복 탐지 검증 완료
- `storage.py`: 테이블 생성, 삽입, 중복 URL 처리, 미태깅 조회 검증 완료
- `tagger.py`: JSON 파싱/후처리(카테고리 검증, 경쟁사 플래그) 로직 검증 완료
  (실제 Claude API 호출은 태준님의 API 키로 첫 실행 시 확인 필요)
- `pipeline.py` + `trend_report.py`: mock 데이터로 전체 흐름 end-to-end 검증 완료
