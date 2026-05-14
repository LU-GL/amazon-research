"""一键运行完整分析流程。

用法:
    python scripts/run_all.py --category "宠物用品" --asin-file data/asins.txt --seller-jing-csv data/seller_jing/export.csv
    python scripts/run_all.py --seller-jing-csv data/seller_jing/export.csv  # 仅用CSV数据
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import RAW_LISTINGS_DIR, RAW_REVIEWS_DIR, OUTPUT_DIR, SELLER_JING_DIR
from src.sentiment.csv_parser import load_seller_jing_csv, split_reviews_by_asin
from src.sentiment.analyzer import analyze_all_reviews
from src.sentiment.aggregator import compare_across_asins, export_sentiment_results, save_sentiment_to_db
from src.scraper.listing_scraper import scrape_listings
from src.analysis.competitive_matrix import build_competitive_matrix, load_listings_from_dir
from src.report.excel_writer import write_competitive_excel
from src.report.pptx_writer import write_market_research_ppt
from src.db.engine import init_db, get_session
from src.db.repositories import ProductRepo, ReviewRepo, AnalysisRunRepo


def main():
    parser = argparse.ArgumentParser(description="亚马逊市调分析 - 一键运行")
    parser.add_argument("--category", "-c", default="", help="产品品类")
    parser.add_argument("--asin-file", default=None, help="ASIN文件路径（每行一个）")
    parser.add_argument("--asins", nargs="*", default=None, help="ASIN列表（空格分隔）")
    parser.add_argument("--seller-jing-csv", default=None, help="卖家精灵导出CSV路径")
    parser.add_argument("--marketplace", default="https://www.amazon.com", help="Amazon站点")
    parser.add_argument("--output-dir", default=None, help="输出目录")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # ===== Step 1: 收集ASIN列表 =====
    print("=" * 60)
    print("Step 1: 收集ASIN列表")
    print("=" * 60)

    asins = []
    if args.asins:
        asins.extend(args.asins)
    if args.asin_file:
        with open(args.asin_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    asins.append(line)

    # 从卖家精灵CSV中提取ASIN
    seller_jing_df = None
    if args.seller_jing_csv:
        print(f"加载卖家精灵CSV: {args.seller_jing_csv}")
        seller_jing_df = load_seller_jing_csv(Path(args.seller_jing_csv))
        csv_asins = seller_jing_df["asin"].unique().tolist()
        asins.extend(csv_asins)
        print(f"  CSV中包含 {len(csv_asins)} 个ASIN, {len(seller_jing_df)} 条评论")

    asins = list(dict.fromkeys(asins))  # 去重保序
    if not asins:
        print("错误: 没有找到任何ASIN。请通过 --asins, --asin-file 或 --seller-jing-csv 提供。")
        sys.exit(1)

    print(f"共 {len(asins)} 个唯一ASIN")

    # 初始化DB
    init_db()
    db_session = get_session()
    run_repo = AnalysisRunRepo(db_session)
    product_repo = ProductRepo(db_session)
    review_repo = ReviewRepo(db_session)
    run = run_repo.create("full_pipeline", args.category)
    run_repo.start(run.id)
    db_session.commit()

    # ===== Step 2: 采集Listing数据 =====
    print("\n" + "=" * 60)
    print("Step 2: 采集Listing数据")
    print("=" * 60)

    listing_data = asyncio.run(scrape_listings(asins, RAW_LISTINGS_DIR, args.marketplace))
    success = sum(1 for v in listing_data.values() if "error" not in v)
    print(f"Listing采集完成: {success}/{len(asins)} 成功")

    # ===== Step 3: 评论情感分析 =====
    print("\n" + "=" * 60)
    print("Step 3: 评论情感分析")
    print("=" * 60)

    sentiment_path = output_dir / "sentiment_results.json"
    asin_analyses = {}

    if seller_jing_df is not None:
        asin_groups = split_reviews_by_asin(seller_jing_df)
        total = len(asin_groups)
        print(f"开始分析 {total} 个ASIN的评论...")

        for i, (asin, reviews_df) in enumerate(asin_groups.items(), 1):
            print(f"\n--- [{i}/{total}] ASIN: {asin} ({len(reviews_df)}条评论) ---")
            analysis = analyze_all_reviews(asin, reviews_df, args.category)
            asin_analyses[asin] = analysis
            print(f"  完成: {len(analysis.get('pain_points', []))}痛点, {len(analysis.get('praise_points', []))}好评")
            if i < total:
                time.sleep(2)

        # 跨ASIN对比 + 写入DB
        comparison = compare_across_asins(asin_analyses)
        export_sentiment_results(asin_analyses, comparison, sentiment_path)
        save_sentiment_to_db(asin_analyses, comparison, run.id)
        run_repo.complete(run.id, asins_analyzed=len(asin_analyses),
                          total_reviews=sum(a.get("total_reviews", 0) for a in asin_analyses.values()))
        db_session.commit()
        db_session.close()
    else:
        # 尝试加载已有分析结果
        if sentiment_path.exists():
            print(f"加载已有情感分析结果: {sentiment_path}")
            with open(sentiment_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            asin_analyses = data.get("asin_analyses", {})
            comparison = data.get("comparison")
        else:
            print("警告: 无评论数据（未提供 --seller-jing-csv），跳过情感分析")
            comparison = None

    # ===== Step 4: 生成报告 =====
    print("\n" + "=" * 60)
    print("Step 4: 生成报告")
    print("=" * 60)

    matrix_df = build_competitive_matrix(listing_data, asin_analyses, seller_jing_df)

    excel_path = write_competitive_excel(
        matrix_df, asin_analyses, comparison,
        output_dir / "competitive_matrix.xlsx",
    )
    pptx_path = write_market_research_ppt(
        matrix_df, asin_analyses, comparison, args.category,
        output_dir / "market_research.pptx",
    )

    # ===== 完成 =====
    print("\n" + "=" * 60)
    print("全部完成!")
    print("=" * 60)
    print(f"  Listing数据: {RAW_LISTINGS_DIR}")
    print(f"  情感分析:    {sentiment_path}")
    print(f"  竞品矩阵:    {excel_path}")
    print(f"  市调PPT:     {pptx_path}")


if __name__ == "__main__":
    main()
