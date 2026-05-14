"""评论情感分析入口脚本。

用法:
    python scripts/01_analyze_sentiment.py --input data/seller_jing/export.csv --category "宠物用品"
    python scripts/01_analyze_sentiment.py --input data/seller_jing/export.csv  # 不指定品类
"""
import argparse
import sys
import time
from pathlib import Path

# 确保项目根目录在sys.path中
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sentiment.csv_parser import load_seller_jing_csv, split_reviews_by_asin
from src.sentiment.analyzer import analyze_all_reviews
from src.sentiment.aggregator import compare_across_asins, export_sentiment_results, save_sentiment_to_db
from src.config import OUTPUT_DIR
from src.db.engine import init_db, get_session
from src.db.repositories import ProductRepo, AnalysisRunRepo


def main():
    parser = argparse.ArgumentParser(description="亚马逊评论情感分析")
    parser.add_argument("--input", "-i", required=True, help="卖家精灵导出的CSV文件路径")
    parser.add_argument("--category", "-c", default="", help="产品品类（可选，帮助AI更好理解上下文）")
    parser.add_argument("--output", "-o", default=None, help="输出JSON路径（默认: output/sentiment_results.json）")
    parser.add_argument("--asins", nargs="*", default=None, help="只分析指定的ASIN（空格分隔）")
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else OUTPUT_DIR / "sentiment_results.json"

    # Step 1: 加载CSV
    print(f"[1/4] 加载CSV: {args.input}")
    df = load_seller_jing_csv(Path(args.input))
    print(f"  共 {len(df)} 条评论")

    # Step 2: 按ASIN分组
    print("[2/4] 按ASIN分组...")
    asin_groups = split_reviews_by_asin(df)

    if args.asins:
        asin_groups = {k: v for k, v in asin_groups.items() if k in args.asins}

    print(f"  共 {len(asin_groups)} 个ASIN")
    for asin, group in asin_groups.items():
        print(f"    {asin}: {len(group)} 条评论")

    # Step 3: 初始化DB并创建运行记录
    init_db()
    db_session = get_session()
    run_repo = AnalysisRunRepo(db_session)
    product_repo = ProductRepo(db_session)
    run = run_repo.create("sentiment", args.category)
    run_repo.start(run.id)
    db_session.commit()
    print(f"  DB运行记录: run_id={run.id}")

    # Step 4: 逐ASIN分析
    print("[4/4] 开始Claude API评论分析...")
    asin_analyses = {}
    total = len(asin_groups)
    for i, (asin, reviews_df) in enumerate(asin_groups.items(), 1):
        print(f"\n--- ASIN {i}/{total}: {asin} ---")
        analysis = analyze_all_reviews(asin, reviews_df, args.category)
        asin_analyses[asin] = analysis
        pain_count = len(analysis.get("pain_points", []))
        praise_count = len(analysis.get("praise_points", []))
        print(f"  完成: {pain_count}个痛点, {praise_count}个好评主题")
        if i < total:
            time.sleep(2)  # ASIN间延迟

    # Step 5: 跨ASIN对比 + 导出JSON + 写入DB
    print("\n[5/5] 生成跨ASIN对比分析...")
    comparison = compare_across_asins(asin_analyses)
    export_sentiment_results(asin_analyses, comparison, output_path)
    save_sentiment_to_db(asin_analyses, comparison, run.id)
    run_repo.complete(run.id, asins_analyzed=len(asin_analyses),
                      total_reviews=sum(a.get("total_reviews", 0) for a in asin_analyses.values()))
    db_session.commit()
    db_session.close()

    # 打印摘要
    print("\n" + "=" * 60)
    print("分析摘要")
    print("=" * 60)
    print(f"分析ASIN数: {comparison['total_asins']}")
    print(f"共同痛点数: {len(comparison['common_pain_points'])}")
    print(f"差异化痛点: {len(comparison['unique_pain_points'])}")
    print(f"功能需求:   {len(comparison['feature_opportunities'])}")
    if comparison.get("insights"):
        print("\n关键洞察:")
        for insight in comparison["insights"]:
            print(f"  - {insight}")
    print(f"\n完整结果: {output_path}")


if __name__ == "__main__":
    main()
