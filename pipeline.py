# -*- coding: utf-8 -*-
"""
메인 파이프라인 (텍스트 모니터링 로그 기반)
실행 방법: python pipeline.py <로그파일.txt>

흐름:
  1. 외부에서 뉴스 데이터 수집 (텍스트 모니터링 로그 txt 형식)
  2. 텍스트 모니터링 로그를 파싱, 뉴스기사 이미지 보강 (og:image, best-effort)
  3. LLM 태깅 후 tagged_articles 테이블에 저장

외부에서 사람이 직접 모니터링해서 텍스트로 넘겨주는 데이터가 유일한 수집 경로이므로,
RSS/네이버 API 자동 수집이나 배치 내부 중복 제거 단계는 없다.
(URL이 이미 DB에 있으면 조용히 건너뛰긴 하지만, 이는 안전장치일 뿐 별도의 "중복 제거" 단계는 아니다.
 raw_articles.url에 UNIQUE 제약이 걸려 있어 같은 로그를 실수로 두 번 넣어도 데이터가 겹쳐 쌓이지 않는다.)

실제 파싱/태깅 로직은 parse_monitoring_log.py에 있고, 여기서는 그걸 그대로 불러와 실행한다.
(같은 로직을 두 곳에서 관리하지 않기 위함 - 로그를 직접 다뤄보고 싶으면 parse_monitoring_log.py를
 dry-run으로 먼저 실행해서 파싱 결과를 미리 확인할 수 있다.)

cron으로 매일 아침 실행하는 것을 권장 (예: 매일 08:00, 그날의 로그 파일을 고정 경로에 저장해두고 실행)
  0 8 * * * cd /path/to/mitech_news_pipeline && python3 pipeline.py /path/to/today_log.txt >> pipeline.log 2>&1
"""
import argparse
import logging

import storage
import parse_monitoring_log as monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def run(log_path, include_irrelevant=False, enrich_image=True):
    """1~3단계: 로그 읽기 -> 파싱 -> 이미지 보강 -> LLM 태깅 -> 저장."""
    logger.info("=== 1. 외부 모니터링 로그 읽기 ===")
    with open(log_path, encoding="utf-8") as f:
        text = f.read()

    articles = monitor.parse_log(text)
    logger.info(f"파싱된 기사: {len(articles)}건")
    if not articles:
        logger.warning("파싱된 기사가 없습니다. 로그 형식을 확인하세요.")
        return 0

    by_section = {}
    for a in articles:
        by_section[a["monitoring_type"]] = by_section.get(a["monitoring_type"], 0) + 1
    for section, count in by_section.items():
        logger.info(f"  - [{section or '미분류'}] {count}건")

    logger.info("=== 2~3. 이미지 보강 + LLM 태깅 + DB 저장 ===")
    saved = monitor.tag_and_save(articles, include_irrelevant=include_irrelevant, enrich_image=enrich_image)
    return saved


def main():
    parser = argparse.ArgumentParser(description="텍스트 모니터링 로그 기반 뉴스 파이프라인")
    parser.add_argument("log_file", help="텍스트 모니터링 로그 파일 경로")
    parser.add_argument("--include-irrelevant", action="store_true", help="'기타' 카테고리 관련성 필터를 건너뛰고 전부 포함")
    parser.add_argument("--no-image", action="store_true", help="og:image 보강을 건너뜀 (속도 우선)")
    args = parser.parse_args()

    storage.init_db()
    saved = run(args.log_file, include_irrelevant=args.include_irrelevant, enrich_image=not args.no_image)
    logger.info(f"=== 파이프라인 완료: 신규 저장 {saved}건 ===")


if __name__ == "__main__":
    main()
