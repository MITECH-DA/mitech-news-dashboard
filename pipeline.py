# -*- coding: utf-8 -*-
"""
메인 파이프라인
실행 방법: python pipeline.py

흐름:
  1. RSS + 네이버뉴스 API 수집
  2. 기존 DB 대비 + 배치 내부 중복 제거
  3. 네이버 기사 이미지 보강 (og:image, best-effort)
  4. boilerplate 제거 (정제)
  5. raw_articles 테이블에 저장
  6. 아직 태깅 안 된 기사에 대해 LLM 태깅 실행
  7. tagged_articles 테이블에 저장

cron으로 매일 아침 실행하는 것을 권장 (예: 매일 08:00)
  0 8 * * * cd /path/to/mitech_news_pipeline && python3 pipeline.py >> pipeline.log 2>&1
"""
import logging

import config
import storage
import collector
import cleaner
import tagger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run_collection_and_cleaning():
    """1~5단계: 수집 -> 관련성 필터 -> 중복제거 -> 이미지 보강 -> 정제 -> 저장."""
    logger.info("=== 1. 수집 시작 ===")
    rss_articles = collector.fetch_all_rss()
    naver_articles = collector.fetch_all_naver()
    logger.info(f"총 수집: {len(rss_articles) + len(naver_articles)}건 (RSS {len(rss_articles)} + 네이버 {len(naver_articles)})")

    # 네이버 검색은 boolean을 지원하지 않아 결과가 느슨하게 잡히므로,
    # 네이버 소스에만 관련성 키워드 필터를 적용해 노이즈를 제거한다.
    # RSS(MassDevice 등)는 이미 의료기기 전문 매체이므로 필터를 적용하지 않는다.
    before = len(naver_articles)
    naver_articles = cleaner.filter_relevant(naver_articles)
    logger.info(f"네이버 관련성 필터: {before}건 -> {len(naver_articles)}건 (제외: {before - len(naver_articles)}건)")

    all_articles = rss_articles + naver_articles

    if not all_articles:
        logger.warning("수집된 기사가 없습니다. 소스 설정을 확인하세요.")
        return 0

    logger.info("=== 2. 중복 제거 ===")
    existing_urls = storage.get_existing_urls()
    all_articles = [a for a in all_articles if a["url"] not in existing_urls]  # URL 완전 중복 우선 제거

    existing_titles = [title for _, title in storage.get_existing_titles()]
    deduped = cleaner.dedup_batch(all_articles, existing_titles=existing_titles)
    logger.info(f"중복 제거 후: {len(deduped)}건 (제거됨: {len(all_articles) - len(deduped)}건)")

    # 네이버 뉴스 검색 API는 썸네일을 안 줘서 image_url이 항상 비어있음.
    # 실제로 저장될(필터·중복제거를 통과한) 기사에 대해서만 원문 페이지에서
    # og:image를 best-effort로 가져와 보강한다 (불필요한 요청 최소화).
    logger.info("=== 3. 네이버 기사 이미지 보강 (og:image) ===")
    deduped = collector.enrich_images(deduped)

    logger.info("=== 4. 정제 (boilerplate 제거) ===")
    cleaned = [cleaner.clean_article(a) for a in deduped]

    logger.info("=== 5. DB 저장 ===")
    saved_count = 0
    for article in cleaned:
        article_id = storage.insert_raw_article(
            source=article["source"],
            title=article["title"],
            url=article["url"],
            published_date=article["published_date"],
            raw_text=article["raw_text"],
            image_url=article.get("image_url", ""),
        )
        if article_id:
            saved_count += 1
    logger.info(f"신규 저장: {saved_count}건")
    return saved_count


def run_tagging():
    """6~7단계: 미태깅 기사 LLM 태깅 -> 저장."""
    logger.info("=== 6. LLM 태깅 대상 조회 ===")
    untagged = storage.get_untagged_articles()
    logger.info(f"태깅 대상: {len(untagged)}건")

    if not untagged:
        return 0

    logger.info("=== 7. LLM 태깅 실행 ===")
    tag_results = tagger.tag_batch(untagged)

    for article_id, tag_result in tag_results:
        storage.insert_tagged_article(article_id, tag_result)

    logger.info(f"태깅 완료: {len(tag_results)}/{len(untagged)}건")
    return len(tag_results)


def main():
    storage.init_db()
    saved = run_collection_and_cleaning()
    tagged = run_tagging()
    logger.info(f"=== 파이프라인 완료: 신규 수집 {saved}건, 태깅 {tagged}건 ===")


if __name__ == "__main__":
    main()
