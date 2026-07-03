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

