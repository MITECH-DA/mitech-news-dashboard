# -*- coding: utf-8 -*-
"""
수집 모듈
- RSS 피드 파싱 (feedparser)
- 네이버 뉴스 검색 API 호출
- 필요시 기사 본문 페이지를 직접 크롤링 (RSS description이 짧은 경우 보완용)
"""
import time
import logging
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def extract_image_url(entry, summary_html=""):
    """RSS 항목에서 대표 이미지 URL을 best-effort로 추출.
    media:thumbnail / media:content / enclosure / 본문 내 첫 <img> 순으로 시도.
    못 찾으면 빈 문자열 반환 (대시보드에서 단색 카드로 대체됨).
    """
    try:
        thumbs = entry.get("media_thumbnail")
        if thumbs and isinstance(thumbs, list) and thumbs[0].get("url"):
            return thumbs[0]["url"]

        media_contents = entry.get("media_content")
        if media_contents and isinstance(media_contents, list):
            for m in media_contents:
                if m.get("url") and ("image" in (m.get("type") or "") or not m.get("type")):
                    return m["url"]

        for link in entry.get("links", []):
            if link.get("rel") == "enclosure" and "image" in (link.get("type") or ""):
                return link.get("href", "")

        if summary_html:
            soup = BeautifulSoup(summary_html, "html.parser")
            img = soup.find("img")
            if img and img.get("src"):
                return img["src"]
    except Exception:
        pass
    return ""


def fetch_rss_articles(source_name, feed_url):
    """단일 RSS 피드를 파싱해서 기사 리스트(dict)를 반환.
    실패해도 파이프라인 전체가 죽지 않도록 예외를 잡아서 빈 리스트 반환.
    """
    articles = []
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo and not feed.entries:
            logger.warning(f"[{source_name}] RSS 파싱 실패 또는 항목 없음: {feed_url}")
            return articles

        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            # feedparser가 이미 구조화해준 published_parsed(struct_time)를 우선 사용
            published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
            published_str = entry.get("published", "") or entry.get("updated", "")
            summary = entry.get("summary", "") or entry.get("description", "")

            articles.append({
                "source": source_name,
                "title": title,
                "url": link,
                "published_date": normalize_date(published_str, published_struct),
                "raw_text": strip_html(summary),
                "image_url": extract_image_url(entry, summary),
            })
    except Exception as e:
        logger.error(f"[{source_name}] RSS 수집 중 오류: {e}")
    return articles


def fetch_all_rss():
    """config.RSS_SOURCES에 정의된 모든 피드를 수집."""
    all_articles = []
    for src in config.RSS_SOURCES:
        logger.info(f"수집 중: {src['name']}")
        articles = fetch_rss_articles(src["name"], src["url"])
        logger.info(f"  -> {len(articles)}건 수집")
        all_articles.extend(articles)
        time.sleep(0.5)  # 매체 서버 부담 완화
    return all_articles


def fetch_naver_news(keyword, display=20):
    """네이버 뉴스 검색 API 호출.
    NAVER_CLIENT_ID / NAVER_CLIENT_SECRET이 .env에 설정되어 있어야 동작.
    (https://developers.naver.com 에서 애플리케이션 등록 후 발급)
    """
    if not config.NAVER_CLIENT_ID or not config.NAVER_CLIENT_SECRET:
        logger.warning("네이버 API 키가 설정되지 않아 국내 뉴스 수집을 건너뜁니다.")
        return []

    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": config.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": config.NAVER_CLIENT_SECRET,
    }
    params = {"query": keyword, "display": display, "sort": "date"}

    articles = []
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("items", []):
            articles.append({
                "source": "Naver News",
                "title": strip_html(item.get("title", "")),
                "url": item.get("originallink") or item.get("link"),
                "published_date": normalize_date(item.get("pubDate", "")),
                "raw_text": strip_html(item.get("description", "")),
                "image_url": "",  # 네이버 뉴스 검색 API는 썸네일을 제공하지 않음
            })
    except Exception as e:
        logger.error(f"네이버 뉴스 API 호출 실패 (키워드: {keyword}): {e}")
    return articles


def fetch_all_naver():
    """config.NAVER_SEARCH_KEYWORDS 전체에 대해 네이버 뉴스 검색."""
    all_articles = []
    for kw in config.NAVER_SEARCH_KEYWORDS:
        logger.info(f"네이버 뉴스 검색 중: {kw}")
        articles = fetch_naver_news(kw)
        logger.info(f"  -> {len(articles)}건 수집")
        all_articles.extend(articles)
        time.sleep(0.3)
    return all_articles


def extract_og_image(url):
    """기사 원문 페이지에서 og:image(없으면 twitter:image) 메타태그를 best-effort로 추출.
    네이버 뉴스 검색 API가 썸네일을 제공하지 않아서, 원문 URL로 직접 접속해
    대표 이미지를 가져오는 용도. 실패해도 파이프라인이 죽지 않도록 예외를 삼킨다.
    """
    try:
        headers = {"User-Agent": config.USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        og = soup.find("meta", attrs={"property": "og:image"})
        if og and og.get("content"):
            return og["content"].strip()

        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw and tw.get("content"):
            return tw["content"].strip()
    except Exception as e:
        logger.warning(f"og:image 추출 실패 ({url}): {e}")
    return ""


def enrich_images(articles):
    """네이버 소스이면서 image_url이 비어있는 기사에 대해서만 og:image를 보강.
    RSS 소스는 이미 collector 단계에서 이미지를 추출했으므로 건드리지 않는다.
    필터/중복제거를 통과한 기사에만 호출하는 것을 권장 (불필요한 요청 최소화).
    """
    enriched_count = 0
    for article in articles:
        if article.get("source") == "Naver News" and not article.get("image_url"):
            image_url = extract_og_image(article["url"])
            if image_url:
                article["image_url"] = image_url
                enriched_count += 1
            time.sleep(0.3)  # 대상 사이트 서버 부담 완화
    logger.info(f"네이버 기사 이미지 보강: {enriched_count}건")
    return articles


def fetch_full_text(url):
    """RSS 요약이 너무 짧을 때, 기사 원문 페이지에서 본문을 직접 추출 (best-effort).
    사이트마다 구조가 달라 완벽하지 않으므로, <article> 또는 <p> 태그 기반으로 단순 추출.
    """
    try:
        headers = {"User-Agent": config.USER_AGENT}
        resp = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        article_tag = soup.find("article")
        container = article_tag if article_tag else soup

        paragraphs = [p.get_text(strip=True) for p in container.find_all("p")]
        text = " ".join(p for p in paragraphs if len(p) > 20)  # 너무 짧은 문단(캡션 등) 제외
        return text[:5000]  # 과도한 길이 방지
    except Exception as e:
        logger.warning(f"본문 크롤링 실패 ({url}): {e}")
        return ""


def strip_html(text):
    """간단한 HTML 태그 제거."""
    if not text:
        return ""
    return BeautifulSoup(text, "html.parser").get_text(separator=" ", strip=True)


def normalize_date(date_str="", date_struct=None):
    """다양한 형식의 날짜(문자열 또는 struct_time)를 'YYYY-MM-DD'로 통일.
    파싱 실패 시 오늘 날짜를 반환한다.
    """
    if date_struct:
        try:
            return datetime(*date_struct[:6]).strftime("%Y-%m-%d")
        except Exception:
            pass
    if date_str:
        try:
            return dateutil_parser.parse(date_str).strftime("%Y-%m-%d")
        except Exception:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
