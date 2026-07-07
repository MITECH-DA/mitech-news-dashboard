# -*- coding: utf-8 -*-
"""
[YYYY.MM.DD] OOO 모니터링 → [자사]/[경쟁사]/[업계] → [출처] 제목 + URL
형식의 텍스트 모니터링 로그를 파싱해서 tagger.py(Claude API)로 태깅한 뒤 DB에 저장하는 스크립트.

기대하는 입력 형식 (반복 가능, 날짜 블록 여러 개를 한 번에 붙여넣어도 됨):

  [2026.07.06] 엠아이텍 모니터링
  [자사]
  특이사항 없음
  [경쟁사]
  [아시아경제] 휴이노, AI CDSS '바이탈 피카소' 식약처 제조인증 획득
  https://buly.kr/58UezTV
  [업계]
  [뉴시스] "스텐트시술 해야 하나요?"…AI가 1분 만에 판단
  https://buly.kr/C0CDFIT

  [2026.07.07] 엠아이텍 모니터링
  ...

처리 규칙:
  - [자사]/[경쟁사]/[업계] 섹션 헤더를 만나면 이후 기사들의 monitoring_type으로 기록
  - "특이사항 없음"처럼 기사가 없는 줄은 건너뜀
  - [경쟁사] 섹션의 기사는 competitor_flag를 무조건 True로 강제 (사람이 이미 분류한 값을 신뢰)
  - [자사]/[업계] 섹션은 tagger.py의 자동 판단(회사명이 COMPETITOR_KEYWORDS에 있으면 True)을 그대로 따름
  - 본문 없이 제목만 있으므로, tagger.py에는 제목만 전달함 (본문 기반보다 정확도는 떨어질 수 있음)
  - category가 '기타'인 기사는 config.RELEVANCE_KEYWORDS 관련성 필터를 통과해야 저장됨
  - 이미 DB에 있는 url은 건너뜀
  - 저장 전 원문 URL에서 og:image를 best-effort로 가져와 image_url을 채움 (--no-image로 생략 가능)

실행 방법:
  python parse_monitoring_log.py log.txt              # 파싱 결과만 확인 (API 호출 없음, dry-run)
  python parse_monitoring_log.py log.txt --apply       # 실제로 Claude API 태깅 + DB 저장
  cat log.txt | python parse_monitoring_log.py --apply # 파일 대신 표준입력으로도 가능
"""
import argparse
import re
import sys
import time

import cleaner
import collector
import config
import storage
import tagger

SECTION_NAMES = ("자사", "경쟁사", "업계")

DATE_RE = re.compile(r"^\[(\d{4})\.(\d{2})\.(\d{2})\]")
SECTION_RE = re.compile(r"^\[(" + "|".join(SECTION_NAMES) + r")\]\s*$")
SOURCE_TITLE_RE = re.compile(r"^\[([^\]]+)\]\s*(.+)$")
URL_RE = re.compile(r"^https?://\S+$")
NO_ITEM_RE = re.compile(r"^특이\s*사항\s*없음$")


def parse_log(text):
    """텍스트 로그를 파싱해서 기사 dict 리스트로 반환.
    각 dict: {published_date, source, title, url, monitoring_type}
    """
    articles = []
    current_date = None
    current_section = None
    pending = None  # {"source":..., "title":...} - URL을 기다리는 중인 기사

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        m = DATE_RE.match(line)
        if m:
            current_date = "-".join(m.groups())
            current_section = None
            pending = None
            continue

        m = SECTION_RE.match(line)
        if m:
            current_section = m.group(1)
            pending = None
            continue

        if NO_ITEM_RE.match(line):
            pending = None
            continue

        if pending is None:
            m = SOURCE_TITLE_RE.match(line)
            if m and current_date:
                pending = {"source": m.group(1).strip(), "title": m.group(2).strip()}
            # 날짜/섹션 없이 나오는 잡음 라인은 무시
            continue

        # pending이 있는 상태에서 다음 줄은 URL이어야 함
        if URL_RE.match(line):
            articles.append({
                "published_date": current_date,
                "source": pending["source"],
                "title": pending["title"],
                "url": line,
                "monitoring_type": current_section or "",
            })
            pending = None
        else:
            # URL이 와야 할 자리에 다른 텍스트가 오면(형식이 어긋난 경우) 그냥 버리고 새로 시작
            pending = None

    return articles


def tag_and_save(articles, include_irrelevant=False, enrich_image=True):
    """파싱된 기사를 이미지 보강 + tagger.py로 태깅 후 DB에 저장. 저장된 건수를 반환."""
    existing_urls = storage.get_existing_urls()
    saved = 0
    skipped_duplicate = 0
    skipped_irrelevant = 0

    for a in articles:
        if a["url"] in existing_urls:
            skipped_duplicate += 1
            continue

        # 모니터링 로그는 이미지를 안 주므로, 원문 페이지에서 og:image를 best-effort로 가져온다.
        image_url = ""
        if enrich_image:
            image_url = collector.extract_og_image(a["url"])
            time.sleep(0.3)  # 대상 사이트 서버 부담 완화

        print(f"태깅 중: [{a['monitoring_type']}] {a['title'][:50]}")
        tag_result = tagger.tag_article(a["title"], "")  # 본문 없이 제목만 전달
        if not tag_result:
            print(f"  -> 태깅 실패, 건너뜀: {a['title'][:50]}")
            continue

        if not include_irrelevant and tag_result["category"] == "기타":
            check = {"title": a["title"], "raw_text": ""}
            if not cleaner.is_relevant(check):
                skipped_irrelevant += 1
                print(f"  -> 관련성 필터 제외: {a['title'][:50]}")
                continue

        # 사람이 이미 분류한 [경쟁사] 섹션은 tagger의 자동 판단보다 우선한다
        if a["monitoring_type"] == "경쟁사":
            tag_result["competitor_flag"] = True
        elif a["monitoring_type"] == "자사":
            tag_result["competitor_flag"] = False
        # [업계]는 tagger가 COMPETITOR_KEYWORDS로 자동 판단한 값을 그대로 사용

        article_id = storage.insert_raw_article(
            source=a["source"],
            title=a["title"],
            url=a["url"],
            published_date=a["published_date"],
            raw_text=a["title"],
            image_url=image_url,
        )
        if article_id is None:
            continue

        storage.insert_tagged_article(article_id, tag_result)
        saved += 1
        time.sleep(0.3)  # Claude API 호출 완급 조절

    print()
    print(f"중복 제외: {skipped_duplicate}건 / 관련성 필터 제외: {skipped_irrelevant}건 / 저장: {saved}건")
    return saved


def main():
    parser = argparse.ArgumentParser(description="텍스트 모니터링 로그 파싱 + LLM 태깅 + DB 저장")
    parser.add_argument("log_file", nargs="?", help="로그 텍스트 파일 경로 (생략 시 표준입력으로 받음)")
    parser.add_argument("--apply", action="store_true", help="지정하면 Claude API로 실제 태깅 후 DB 저장 (기본은 dry-run)")
    parser.add_argument("--include-irrelevant", action="store_true", help="'기타' 카테고리 관련성 필터를 건너뛰고 전부 포함")
    parser.add_argument("--no-image", action="store_true", help="지정하면 og:image 보강을 건너뜀 (속도 우선)")
    args = parser.parse_args()

    if args.log_file:
        with open(args.log_file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    articles = parse_log(text)
    print(f"파싱된 기사: {len(articles)}건")

    by_section = {}
    for a in articles:
        by_section[a["monitoring_type"]] = by_section.get(a["monitoring_type"], 0) + 1
    for section, count in by_section.items():
        print(f"  - [{section or '미분류'}] {count}건")

    if not articles:
        print("파싱된 기사가 없습니다. 로그 형식을 확인해주세요.")
        return

    if not args.apply:
        print("\n(dry-run) 아래는 파싱 미리보기입니다. 실제 태깅/저장 없음.")
        for a in articles:
            print(f"  [{a['published_date']}][{a['monitoring_type']}] {a['source']} - {a['title'][:50]} ({a['url']})")
        print("\n실제로 Claude API 태깅 + DB 저장하려면: python parse_monitoring_log.py <파일> --apply")
        return

    storage.init_db()
    tag_and_save(articles, include_irrelevant=args.include_irrelevant, enrich_image=not args.no_image)


if __name__ == "__main__":
    main()
