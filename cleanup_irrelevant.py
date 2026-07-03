# -*- coding: utf-8 -*-
"""
기존 DB에 이미 쌓인 '기타' 카테고리 기사 중, 의료기기와 관련 없어 보이는
노이즈 기사를 찾아 삭제하는 1회성 정리 스크립트.

'기타'로 분류됐다고 전부 삭제하지는 않습니다 — 개중에는 LLM이 잘못 분류한
진짜 의료기기 기사도 섞여 있을 수 있어서, config.RELEVANCE_KEYWORDS로 한 번 더
걸러서 "제목/본문에 의료기기 관련 키워드가 하나도 없는 기사"만 삭제 후보로 잡습니다.

실행 방법:
  python cleanup_irrelevant.py            # 삭제 후보 목록만 확인 (dry-run)
  python cleanup_irrelevant.py --apply     # 실제로 삭제 (확인 프롬프트 있음)
"""
import argparse

import cleaner
import storage


def main():
    parser = argparse.ArgumentParser(description="'기타' 카테고리 노이즈 기사 정리")
    parser.add_argument("--apply", action="store_true", help="지정하면 실제로 삭제 실행 (기본은 dry-run)")
    parser.add_argument("--category", type=str, default="기타", help="정리 대상 카테고리 (기본: 기타)")
    args = parser.parse_args()

    storage.init_db()
    candidates = storage.get_articles_by_category(args.category)
    print(f"'{args.category}' 카테고리 기사 총 {len(candidates)}건")

    to_delete = []
    to_keep = []
    for a in candidates:
        check = {"title": a["title"], "raw_text": a.get("raw_text") or ""}
        if cleaner.is_relevant(check):
            to_keep.append(a)
        else:
            to_delete.append(a)

    print(f"  - 삭제 후보(노이즈로 판단): {len(to_delete)}건")
    print(f"  - 유지(관련 키워드 있음, LLM 재분류 검토 권장): {len(to_keep)}건")

    if to_keep:
        print("\n[유지되는 기사 - 카테고리 재태깅을 검토해보세요]")
        for a in to_keep:
            print(f"  - {a['title']} ({a['source']}, {a['published_date']})")

    if not to_delete:
        print("\n삭제할 노이즈 기사가 없습니다.")
        return

    print("\n[삭제 후보]")
    for a in to_delete:
        print(f"  - {a['title']} ({a['source']}, {a['published_date']})")

    if not args.apply:
        print(f"\n(dry-run) 실제로 삭제하려면: python cleanup_irrelevant.py --apply")
        return

    confirm = input(f"\n위 {len(to_delete)}건을 정말 삭제하시겠습니까? (yes 입력): ")
    if confirm.strip().lower() != "yes":
        print("취소되었습니다.")
        return

    ids = [a["id"] for a in to_delete]
    deleted_count = storage.delete_articles(ids)
    print(f"삭제 완료: {deleted_count}건")


if __name__ == "__main__":
    main()
