# -*- coding: utf-8 -*-
"""
기존에 DB에 쌓인 네이버 소스 기사 중 image_url이 비어있는 기사에 대해
원문 페이지의 og:image를 소급으로 채워넣는 1회성 백필 스크립트.

collector.enrich_images()는 "새로 수집되는" 기사에만 적용되므로,
이 스크립트가 처음 나오기 전(=이미지 보강 기능 추가 전)에 쌓인 기존 기사들은
따로 이 스크립트를 한 번 돌려줘야 이미지가 채워집니다.

실행 방법:
  python backfill_images.py            # 몇 건이 대상인지만 확인 (dry-run)
  python backfill_images.py --apply     # 실제로 og:image를 가져와서 채움
"""
import argparse
import time

import collector
import storage


def main():
    parser = argparse.ArgumentParser(description="기존 네이버 기사 이미지 소급 보강")
    parser.add_argument("--apply", action="store_true", help="지정하면 실제로 og:image를 가져와 채움 (기본은 dry-run)")
    parser.add_argument("--source", type=str, default="Naver News", help="대상 소스 (기본: Naver News)")
    args = parser.parse_args()

    storage.init_db()
    targets = storage.get_articles_missing_image(args.source)
    print(f"'{args.source}' 소스 중 이미지 없는 기사: {len(targets)}건")

    if not targets:
        print("대상이 없습니다.")
        return

    if not args.apply:
        print("\n(dry-run) 실제로 채우려면: python backfill_images.py --apply")
        print("참고: 기사 수만큼 원문 페이지를 하나씩 요청하므로 시간이 걸릴 수 있습니다.")
        return

    filled = 0
    for i, article in enumerate(targets, 1):
        image_url = collector.extract_og_image(article["url"])
        if image_url:
            storage.update_image_url(article["id"], image_url)
            filled += 1
        if i % 20 == 0 or i == len(targets):
            print(f"진행: {i}/{len(targets)}건 처리, {filled}건 채워짐")
        time.sleep(0.3)  # 대상 사이트 서버 부담 완화

    print(f"\n백필 완료: {len(targets)}건 중 {filled}건에 이미지 채움 ({len(targets) - filled}건은 og:image를 찾지 못함)")


if __name__ == "__main__":
    main()
