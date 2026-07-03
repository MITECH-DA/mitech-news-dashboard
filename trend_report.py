# -*- coding: utf-8 -*-
"""
트렌드 리포트 스크립트
실행 방법: python trend_report.py --days 7

DB에 쌓인 tagged_articles를 집계해서:
  - 카테고리별 기사 수
  - 최다 언급 회사 / 기술 / 적응증
  - 경쟁사 언급 기사 목록
  - 감성 분포
를 콘솔에 출력하고, CSV로도 내보낸다.
"""
import argparse
import csv
import io
import os
from collections import Counter
from datetime import datetime, timedelta

import storage

CSV_FIELDNAMES = ["published_date", "source", "title", "url", "image_url", "category",
                   "companies", "products", "technologies", "indications",
                   "competitor_flag", "sentiment", "summary"]


def collect_period_data(days):
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    articles = storage.get_tagged_articles_between(start_date, end_date)
    return articles, start_date, end_date


def build_report(articles):
    category_counter = Counter(a["category"] for a in articles if a["category"])
    company_counter = Counter()
    tech_counter = Counter()
    indication_counter = Counter()
    sentiment_counter = Counter(a["sentiment"] for a in articles if a["sentiment"])
    competitor_articles = []

    for a in articles:
        company_counter.update(a["companies"])
        tech_counter.update(a["technologies"])
        indication_counter.update(a["indications"])
        if a["competitor_flag"]:
            competitor_articles.append(a)

    return {
        "total": len(articles),
        "by_category": category_counter,
        "top_companies": company_counter.most_common(10),
        "top_technologies": tech_counter.most_common(10),
        "top_indications": indication_counter.most_common(10),
        "sentiment": sentiment_counter,
        "competitor_articles": competitor_articles,
    }


def print_report(report, start_date, end_date):
    print(f"\n{'='*60}")
    print(f"  의료기기 뉴스 트렌드 리포트 ({start_date} ~ {end_date})")
    print(f"{'='*60}")
    print(f"\n총 기사 수: {report['total']}건\n")

    print("[카테고리별 분포]")
    for cat, cnt in report["by_category"].most_common():
        print(f"  {cat}: {cnt}건")

    print("\n[최다 언급 회사 Top 10]")
    for name, cnt in report["top_companies"]:
        print(f"  {name}: {cnt}회")

    print("\n[최다 언급 기술 Top 10]")
    for name, cnt in report["top_technologies"]:
        print(f"  {name}: {cnt}회")

    print("\n[최다 언급 적응증 Top 10]")
    for name, cnt in report["top_indications"]:
        print(f"  {name}: {cnt}회")

    print("\n[감성 분포]")
    for sentiment, cnt in report["sentiment"].most_common():
        print(f"  {sentiment}: {cnt}건")

    print(f"\n[경쟁사 관련 기사: {len(report['competitor_articles'])}건]")
    for a in report["competitor_articles"][:15]:
        print(f"  - [{a['category']}] {a['title']} ({a['source']}, {a['published_date']})")
    print()


def build_csv_text(articles):
    """기사 리스트를 CSV 텍스트(문자열)로 변환. 파일 저장과 대시보드 JS 생성 양쪽에서 재사용."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    for a in articles:
        row = dict(a)
        for field in ("companies", "products", "technologies", "indications"):
            row[field] = ", ".join(row[field])
        writer.writerow({k: row.get(k, "") for k in CSV_FIELDNAMES})
    return buf.getvalue()


def export_csv(articles, filename="trend_report.csv"):
    if not articles:
        print("내보낼 기사가 없어 CSV를 생성하지 않았습니다.")
        return
    csv_text = build_csv_text(articles)
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        f.write(csv_text)
    print(f"CSV 저장 완료: {filename}")


def export_dashboard_js(articles, filename="dashboard/dashboard_data.js"):
    """대시보드(index.html)가 파일을 열자마자 자동으로 데이터를 표시할 수 있도록,
    CSV와 동일한 내용을 JS 상수(REPORT_DATA)로 감싸서 저장한다.
    <script src="dashboard_data.js">로 로드하면 file:// 환경에서도 CORS 제약 없이 동작한다.
    """
    if not articles:
        print("내보낼 기사가 없어 대시보드 데이터를 생성하지 않았습니다.")
        return
    csv_text = build_csv_text(articles)
    # 백틱/역슬래시가 CSV 값에 포함될 경우 템플릿 리터럴이 깨지므로 이스케이프 처리
    escaped = csv_text.replace("\\", "\\\\").replace("`", "\\`")

    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(
            "// trend_report.py가 자동 생성한 파일입니다. 직접 수정하지 마세요.\n"
            "// index.html이 이 파일을 로드해서 CSV 업로드 없이 최신 데이터를 자동으로 보여줍니다.\n"
            "const REPORT_DATA = `" + escaped + "`;\n"
            "const REPORT_GENERATED_AT = \"" + datetime.now().strftime("%Y-%m-%d %H:%M") + "\";\n"
        )
    print(f"대시보드 데이터 저장 완료: {filename} (index.html을 열면 자동으로 반영됩니다)")


def main():
    parser = argparse.ArgumentParser(description="의료기기 뉴스 트렌드 리포트 생성")
    parser.add_argument("--days", type=int, default=7, help="집계 기간 (기본 7일)")
    parser.add_argument("--csv", type=str, default="trend_report.csv", help="CSV 출력 파일명")
    parser.add_argument("--dashboard-js", type=str, default="dashboard/dashboard_data.js",
                         help="대시보드 자동 로드용 JS 파일 경로 (기본: dashboard/dashboard_data.js)")
    parser.add_argument("--no-dashboard", action="store_true",
                         help="대시보드 데이터 파일을 생성하지 않으려면 지정")
    args = parser.parse_args()

    articles, start_date, end_date = collect_period_data(args.days)
    report = build_report(articles)
    print_report(report, start_date, end_date)
    export_csv(articles, args.csv)
    if not args.no_dashboard:
        export_dashboard_js(articles, args.dashboard_js)


if __name__ == "__main__":
    main()
