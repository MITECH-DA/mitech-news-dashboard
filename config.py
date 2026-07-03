# -*- coding: utf-8 -*-
"""
설정 파일
- RSS 소스, DB 경로, API 키(.env에서 로드) 등 전역 설정을 관리합니다.
- 실제 배포 시 이 파일의 값들만 조정하면 됩니다.
"""
import os
from dotenv import load_dotenv

load_dotenv()  # .env 파일에서 환경변수 로드

# ── API 키 (반드시 .env 파일에 설정, 코드에 직접 넣지 말 것) ──────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# ── DB 설정 ────────────────────────────────────────────────────────────
# 1차 검증은 SQLite로. MySQL로 전환 시 storage.py의 get_connection()만 교체하면 됨.
DB_PATH = os.getenv("DB_PATH", "mitech_news.db")

# ── RSS 소스 목록 ──────────────────────────────────────────────────────
# category는 소스 성격 힌트(태깅 전 참고용), 실제 기사 분류는 LLM이 다시 판단함
RSS_SOURCES = [
    {
        "name": "MassDevice",
        "url": "https://www.massdevice.com/feed/",
        "region": "US",
    },
    {
        "name": "MedTech Dive",
        "url": "https://www.medtechdive.com/feeds/news/",
        "region": "US",
    },
    {
        "name": "Medical Design & Outsourcing",
        "url": "https://www.medicaldesignandoutsourcing.com/feed/",
        "region": "US",
    },
    {
        "name": "MDDI (MD+DI)",
        "url": "https://www.mddionline.com/rss.xml",
        "region": "US",
    },
    # 국내 소스는 네이버 뉴스 API로 별도 수집 (아래 NAVER_SEARCH_KEYWORDS 참고)
]

# 네이버 뉴스 검색 API는 query 파라미터에 AND/OR/괄호 같은 boolean 연산자를 지원하지 않습니다.
# (query는 검색창에 문자열 하나를 입력하는 것과 동일하게 동작 — 구조화된 쿼리 파싱 없음)
# 그래서 "주제어 그룹 x 맥락어 그룹"을 파이썬에서 조합해 여러 번 호출하는 방식으로 우회합니다.
# 예: 주제어 ["의료기기","디지털 헬스케어"] x 맥락어 ["식약처","FDA","투자","허가"]
#     -> "의료기기 식약처", "의료기기 FDA", "의료기기 투자", "의료기기 허가",
#        "디지털 헬스케어 식약처", "디지털 헬스케어 FDA", ... 총 8개 쿼리로 호출
# 네이버 검색은 공백으로 구분된 여러 단어를 입력하면 대략 AND에 가깝게 동작합니다(전부 포함된 결과 위주로 반환).
NAVER_TOPIC_TERMS = [
    "의료기기",
    "디지털 헬스케어",
    "의료 AI",
    "스텐트",
]
NAVER_CONTEXT_TERMS = [
    "식약처",
    "FDA",
    "투자",
    "허가",
    "승인",
]

# 위 두 그룹의 곱집합으로 실제 검색 쿼리 리스트를 생성합니다.
# 그룹 크기를 곱한 만큼 API 호출 횟수가 늘어나므로(4 x 5 = 20회) 일일 호출 한도(25,000회)를 고려해 조절하세요.
NAVER_SEARCH_KEYWORDS = [
    f"{topic} {context}" for topic in NAVER_TOPIC_TERMS for context in NAVER_CONTEXT_TERMS
]

# 조합 없이 그 자체로 검색하고 싶은 단독 키워드가 있다면 여기 추가 (선택)
NAVER_SEARCH_KEYWORDS += [
    "비혈관성 스텐트",
    "식약처 인증 의료기기",
]

# ── 관심 키워드 (경쟁사/기술) ───────────────────────────────────────────
# 경쟁사 모니터링, 기술 트렌드 태깅 시 참고용 화이트리스트.
# 실제 추출은 LLM이 자유 추출하되, 이 목록과 매칭되면 별도 플래그를 답니다.
COMPETITOR_KEYWORDS = [
    "Boston Scientific", "Abbott", "Medtronic", "Terumo",
    "Cook Medical", "Biosensors", "Microport", "S&G Biotech",
    "Taewoong Medical",
]

# 자사명 (경쟁사 매칭에서 제외하고, 자사 언급 기사만 별도로 추적하고 싶을 때 사용)
OWN_COMPANY_KEYWORDS = ["M.I.Tech", "MITech", "엠아이텍"]

TECH_KEYWORDS = [
    "biodegradable stent", "drug-eluting stent", "self-expanding stent",
    "AI diagnosis", "AI imaging", "생분해성", "약물방출스텐트",
]

# ── 관련성 필터 (네이버 검색 결과 노이즈 제거용) ─────────────────────────
# 네이버 뉴스 검색은 AND/OR를 지원하지 않아(config.py 상단 설명 참고) 결과가 느슨하게 잡힙니다.
# 제목/요약에 아래 키워드가 하나도 없으면 "의료기기와 동떨어진 기사"로 판단해 수집 단계에서 제외합니다.
# RSS 소스(MassDevice, MedTech Dive 등)는 이미 의료기기 전문 매체라 이 필터를 적용하지 않고,
# 네이버 검색 결과에만 적용합니다 (느슨한 키워드 조합 검색이 노이즈의 원인이므로).
RELEVANCE_KEYWORDS = [
    "의료기기", "의료 기기", "메디컬 디바이스", "스텐트", "카테터", "임플란트",
    "의료용", "체외진단", "IVD", "의료 AI", "디지털 헬스케어", "헬스케어 기기",
    "식약처", "FDA", "CE 인증", "의료기기 허가", "의료기기 인증", "의료기기 승인",
    "바이오메디컬", "의공학", "메드테크", "medtech", "medical device", "healthcare",
]
# ── 기사 분류 카테고리 (LLM 태깅 시 강제 선택지) ─────────────────────────
CATEGORIES = [
    "규제/인허가",
    "M&A/투자",
    "임상시험",
    "신제품출시",
    "리콜/이슈",
    "실적/경영",
    "R&D/기술",
    "기타",
]

# ── LLM 설정 ───────────────────────────────────────────────────────────
CLAUDE_MODEL = "claude-sonnet-5"

# ── 수집 주기 관련 ─────────────────────────────────────────────────────
REQUEST_TIMEOUT = 10  # 초
USER_AGENT = "Mozilla/5.0 (MITech-NewsPipeline/1.0)"
