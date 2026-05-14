"""一次性迁移脚本：将已有的JSON文件导入SQLite数据库。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import RAW_LISTINGS_DIR, OUTPUT_DIR, SELLER_JING_DIR
from src.db.engine import init_db, get_session
from src.db.repositories import ProductRepo, ReviewRepo, SentimentRepo, AnalysisRunRepo
from src.sentiment.csv_parser import load_seller_jing_csv, split_reviews_by_asin


def migrate_listings(session):
    """导入 data/raw_listings/ 下的所有JSON。"""
    repo = ProductRepo(session)
    count = repo.import_listings_from_dir(RAW_LISTINGS_DIR)
    print(f"  导入 {count} 个产品listing")
    return count


def migrate_reviews(session):
    """导入 data/seller_jing/ 下的CSV评论。"""
    product_repo = ProductRepo(session)
    review_repo = ReviewRepo(session)
    total = 0
    seller_dir = Path(SELLER_JING_DIR)
    if not seller_dir.exists():
        print("  seller_jing目录不存在，跳过")
        return 0
    for csv_file in seller_dir.glob("*.csv"):
        print(f"  处理: {csv_file.name}")
        df = load_seller_jing_csv(csv_file)
        asin_groups = split_reviews_by_asin(df)
        for asin, reviews_df in asin_groups.items():
            product = product_repo.get_or_create(asin)
            count = review_repo.import_from_dataframe(product.id, reviews_df)
            total += count
    session.commit()
    print(f"  导入 {total} 条评论")
    return total


def migrate_sentiment(session):
    """导入 output/sentiment_results.json 分析结果。"""
    sentiment_file = OUTPUT_DIR / "sentiment_results.json"
    if not sentiment_file.exists():
        print("  sentiment_results.json不存在，跳过")
        return 0

    with open(sentiment_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    asin_analyses = data.get("asin_analyses", {})
    comparison = data.get("comparison", {})

    if not asin_analyses:
        print("  无分析数据，跳过")
        return 0

    run_repo = AnalysisRunRepo(session)
    product_repo = ProductRepo(session)
    sentiment_repo = SentimentRepo(session)

    run = run_repo.create("sentiment", category="迁移导入")
    run_repo.start(run.id)

    for asin, analysis in asin_analyses.items():
        product = product_repo.get_or_create(asin)
        sentiment_repo.save_analysis(run.id, product.id, analysis)

    if comparison:
        sentiment_repo.save_comparison(run.id, comparison)

    run_repo.complete(run.id, asins_analyzed=len(asin_analyses))
    session.commit()
    print(f"  导入 {len(asin_analyses)} 个ASIN的分析结果")
    return len(asin_analyses)


def main():
    print("=== JSON → SQLite 数据迁移 ===\n")
    init_db()
    print("数据库表已创建\n")

    session = get_session()
    try:
        print("[1/3] 迁移Listing数据...")
        migrate_listings(session)

        print("[2/3] 迁移评论数据...")
        migrate_reviews(session)

        print("[3/3] 迁移情感分析结果...")
        migrate_sentiment(session)

        print("\n迁移完成!")
    finally:
        session.close()


if __name__ == "__main__":
    main()
