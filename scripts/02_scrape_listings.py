"""Listing数据采集入口脚本。

用法:
    python scripts/02_scrape_listings.py --asins B08XYZ1234 B08ABC5678
    python scripts/02_scrape_listings.py --asin-file data/asins.txt
    python scripts/02_scrape_listings.py --asin-file data/asins.txt --with-reviews
    python scripts/02_scrape_listings.py --asin-file data/asins.txt --marketplace https://www.amazon.co.jp
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scraper.listing_scraper import scrape_listings
from src.scraper.review_scraper import scrape_all_reviews
from src.config import RAW_LISTINGS_DIR, RAW_REVIEWS_DIR


def main():
    parser = argparse.ArgumentParser(description="Amazon Listing/评论采集")
    parser.add_argument("--asins", nargs="*", default=None, help="ASIN列表（空格分隔）")
    parser.add_argument("--asin-file", default=None, help="ASIN文件路径（每行一个ASIN）")
    parser.add_argument("--with-reviews", action="store_true", help="同时抓取评论")
    parser.add_argument("--marketplace", default="https://www.amazon.com", help="Amazon站点URL")
    parser.add_argument("--max-review-pages", type=int, default=10, help="每个ASIN最多抓取评论页数")
    parser.add_argument("--output-dir", default=None, help="输出目录（默认: data/raw_listings/）")
    args = parser.parse_args()

    # 收集ASIN列表
    asins = []
    if args.asins:
        asins.extend(args.asins)
    if args.asin_file:
        with open(args.asin_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    asins.append(line)

    if not asins:
        print("错误: 请提供ASIN列表 (--asins) 或ASIN文件 (--asin-file)")
        sys.exit(1)

    asins = list(dict.fromkeys(asins))  # 去重保序
    output_dir = Path(args.output_dir) if args.output_dir else RAW_LISTINGS_DIR

    print(f"共 {len(asins)} 个ASIN待采集")
    print(f"输出目录: {output_dir}")

    # 抓取listing
    print("\n[1/2] 抓取Listing数据...")
    results = asyncio.run(scrape_listings(asins, output_dir, args.marketplace))
    success = sum(1 for v in results.values() if "error" not in v)
    print(f"  成功: {success}/{len(asins)}")

    # 抓取评论（可选）
    if args.with_reviews:
        print("\n[2/2] 抓取评论数据...")
        for asin in asins:
            print(f"\n--- {asin} ---")
            asyncio.run(scrape_all_reviews(
                asin, max_pages=args.max_review_pages,
                output_dir=RAW_REVIEWS_DIR, marketplace=args.marketplace,
            ))
    else:
        print("\n[2/2] 跳过评论抓取（使用 --with-reviews 启用）")

    print(f"\n完成! 数据保存在: {output_dir}")


if __name__ == "__main__":
    main()
