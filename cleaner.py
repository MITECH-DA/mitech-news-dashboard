# -*- coding: utf-8 -*-
"""
정제 모듈
- 제목 유사도 기반 중복 필터링
- boilerplate(광고 문구, 저작권 표기, 기자 서명 등) 제거
"""
import re
from difflib import SequenceMatcher

import config

# 흔히 등장하는 boilerplate 패턴 (필요시 계속 추가)
BOILERPLATE_PATTERNS = [
    r"Sign up for.*?newsletter\.?",
    r"Subscribe to.*?(newsletter|updates)\.?",
    r"Read more at.*?\.",
    r"이 기사는.*?무단전재.*?금지",
    r"저작권자.*?무단.*?재배포.*?금지",
    r"기자\s*=\s*\S+@\S+\.\S+",  # 기자 이메일 서명
    r"Copyright\s*©.*?\d{4}.*?rights reserved\.?",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in BOILERPLATE_PATTERNS]


def remove_boilerplate(text):
    """정규식 기반으로 흔한 boilerplate 문구를 제거."""
    if not text:
        return ""
    cleaned = text
    for pattern in _COMPILED_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    # 다중 공백/줄바꿈 정리
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_title(title):
    """비교를 위해 제목을 소문자화 + 특수문자 제거."""
    t = title.lower()
    t = re.sub(r"[^\w\s가-힣]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_similarity(title_a, title_b):
    """0~1 사이 유사도 점수 (SequenceMatcher 기반)."""
    return SequenceMatcher(None, normalize_title(title_a), normalize_title(title_b)).ratio()


def is_duplicate(new_title, existing_titles, threshold=0.85):
    """new_title이 existing_titles(list of str) 중 하나와 threshold 이상 유사하면 True.

    참고: 기사 수가 매우 많아지면(수만 건 이상) O(n) 비교가 느려질 수 있음.
    그 경우 MinHash/LSH 같은 근사 중복 탐지로 교체 권장. 현재 규모(일 20~30건)에서는 충분히 빠름.
    """
    for existing in existing_titles:
        if title_similarity(new_title, existing) >= threshold:
            return True
    return False


def is_relevant(article, keywords=None):
    """제목+요약에 의료기기 관련 키워드가 하나도 없으면 False (노이즈로 판단).

    네이버 뉴스 검색처럼 boolean 검색을 지원하지 않는 소스에서 느슨하게 잡힌
    엉뚱한 기사(정치/증시/스포츠 후원 등)를 수집 단계에서 걸러내기 위한 안전망.
    RSS 소스(MassDevice 등 의료기기 전문 매체)는 이미 신뢰할 수 있는 소스이므로
    호출하는 쪽(pipeline.py)에서 네이버 소스에만 이 함수를 적용한다.
    """
    keywords = keywords or config.RELEVANCE_KEYWORDS
    haystack = (article.get("title", "") + " " + article.get("raw_text", "")).lower()
    return any(kw.lower() in haystack for kw in keywords)


def filter_relevant(articles, keywords=None):
    """기사 리스트에서 관련 없는 기사를 제외하고 반환."""
    return [a for a in articles if is_relevant(a, keywords)]


def clean_article(article):
    """단일 기사 dict의 raw_text에서 boilerplate 제거 후 반환 (in-place 아님, 새 dict 반환)."""
    cleaned = dict(article)
    cleaned["raw_text"] = remove_boilerplate(article.get("raw_text", ""))
    return cleaned


def dedup_batch(articles, existing_titles=None, threshold=0.85):
    """수집된 기사 리스트에서 배치 내부 중복 + 기존 DB 대비 중복을 모두 제거.

    Args:
        articles: collector가 반환한 기사 dict 리스트
        existing_titles: DB에 이미 존재하는 제목 리스트 (storage.get_existing_titles()로 조회)
        threshold: 유사도 임계값

    Returns:
        중복이 제거된 기사 리스트
    """
    existing_titles = list(existing_titles or [])
    result = []
    seen_titles = []

    for article in articles:
        title = article["title"]
        if is_duplicate(title, existing_titles, threshold) or is_duplicate(title, seen_titles, threshold):
            continue
        result.append(article)
        seen_titles.append(title)

    return result
