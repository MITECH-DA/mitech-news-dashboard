# -*- coding: utf-8 -*-
"""
외부 모니터링 도구에서 수동으로 받은 CSV(monitored_articles.csv 형식)를 DB로 가져오는 스크립트.

이 CSV는 이미 category/companies/products/technologies/indications가 태깅된 상태로 오므로,
collector.py + tagger.py를 거치지 않고 raw_articles + tagged_articles에 바로 저장한다.
(sentiment/summary는 이 소스에 없는 필드라 빈 값으로 저장됨)

기대 컬럼(탭 또는 콤마 구분, 순서 무관):
  published_date, source, title, url, image_url, category,
  companies, products, technologies, indications, competitor_flag,
  monitoring_type, crawl_status

처리 규칙:
  - crawl_status가 'ok'가 아닌 행은 기본적으로 건너뜀 (--include-failed로 포함 가능)
  - 이미 DB에 있는 url은 건너뜀 (중복 수집 방지)
  - category가 '기타'인 행은 config.RELEVANCE_KEYWORDS 관련성 필터를 통과해야 저장됨
    (다른 소스와 동일한 노이즈 제거 기준 적용)

실행 방법:
  python import_monitored_csv.py monitored_articles.csv              # dry-run (몇 건 들어갈지만 확인)
  python import_monitored_csv.py monitored_articles.csv --apply       # 실제로 DB에 저장
"""
import argparse
import csv
import io

import cleaner
import storage

# CSV가 콤마로 구분한 다중값 필드를 저장할 때 리스트로 변환
MULTI_VALUE_FIELDS = ("companies", "products", "technologies", "indications")

# 이 인코딩들을 순서대로 시도한다 (엑셀에서 내보낸 한글 CSV는 보통 cp949 아니면 utf-8-sig)
CANDIDATE_ENCODINGS = ("utf-8-sig", "cp949", "utf-8")


def _read_text(path):
    """여러 인코딩을 시도해서 파일을 텍스트로 읽는다."""
    last_error = None
    for enc in CANDIDATE_ENCODINGS:
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
    raise last_error


def _detect_delimiter(text):
    """첫 줄을 보고 탭/콤마 중 어느 쪽으로 구분됐는지 판단."""
    first_line = text.split("\n", 1)[0]
    return "\t" if first_line.count("\t") > first_line.count(",") else ","


def load_rows(path):
    text = _read_text(path)
    delimiter = _detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    return rows, reader.fieldnames


def split_multi(value):
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def main():
    parser = argparse.ArgumentParser(description="외부 모니터링 CSV를 DB로 가져오기")
    parser.add_argument("csv_path", help="가져올 CSV(또는 TSV) 파일 경로")
    parser.add_argument("--apply", action="store_true", help="지정하면 실제로 DB에 저장 (기본은 dry-run)")
    parser.add_argument("--include-failed", action="store_true", help="crawl_status가 ok가 아닌 행도 포함")
    parser.add_argument("--include-irrelevant", action="store_true", help="'기타' 카테고리 관련성 필터를 건너뛰고 전부 포함")
    args = parser.parse_args()

    storage.init_db()
    rows, fieldnames = load_rows(args.csv_path)
    print(f"파일 읽기 완료: {len(rows)}건 (컬럼: {', '.join(fieldnames)})")

    existing_urls = storage.get_existing_urls()

    skipped_failed = 0
    skipped_duplicate = 0
    skipped_irrelevant = 0
    to_import = []

    for row in rows:
        if not args.include_failed and row.get("crawl_status", "ok") != "ok":
            skipped_failed += 1
            continue
        url = (row.get("url") or "").strip()
        if not url or url in existing_urls:
            skipped_duplicate += 1
            continue
        category = (row.get("category") or "기타").strip() or "기타"
        if category == "기타" and not args.include_irrelevant:
            check = {"title": row.get("title", ""), "raw_text": row.get("title", "")}
            if not cleaner.is_relevant(check):
                skipped_irrelevant += 1
                continue
        to_import.append(row)

    print(f"  - crawl_status 제외: {skipped_failed}건")
    print(f"  - 중복 url 제외: {skipped_duplicate}건")
    print(f"  - 관련성 필터 제외('기타' 중): {skipped_irrelevant}건")
    print(f"  -> 최종 가져올 기사: {len(to_import)}건")

    if not to_import:
        print("가져올 기사가 없습니다.")
        return

    if not args.apply:
        print("\n(dry-run) 실제로 저장하려면: python import_monitored_csv.py <파일> --apply")
        return

    saved = 0
    for row in to_import:
        article_id = storage.insert_raw_article(
            source=row.get("source", "").strip(),
            title=row.get("title", "").strip(),
            url=row.get("url", "").strip(),
            published_date=row.get("published_date", "").strip(),
            raw_text=row.get("title", "").strip(),  # 이 소스는 본문 텍스트를 안 주므로 제목으로 대체
            image_url=row.get("image_url", "").strip(),
        )
        if article_id is None:
            continue  # 방금 사이에 이미 저장된 경우(동시 실행 등) 대비

        tag_result = {
            "category": (row.get("category") or "기타").strip() or "기타",
            "companies": split_multi(row.get("companies")),
            "products": split_multi(row.get("products")),
            "technologies": split_multi(row.get("technologies")),
            "indications": split_multi(row.get("indications")),
            "competitor_flag": str(row.get("competitor_flag", "0")).strip() in ("1", "true", "True"),
            "sentiment": "",   # 이 소스는 감성 분석 결과가 없음
            "summary": "",     # 이 소스는 요약이 없음
        }
        storage.insert_tagged_article(article_id, tag_result)
        saved += 1

    print(f"\n저장 완료: {saved}건")


if __name__ == "__main__":
    main()
