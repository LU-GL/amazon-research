"""报告生成入口脚本。

用法:
    python scripts/03_generate_report.py --sentiment output/sentiment_results.json --listings data/raw_listings/
    python scripts/03_generate_report.py --sentiment output/sentiment_results.json --category "宠物用品"
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.analysis.competitive_matrix import build_competitive_matrix, load_listings_from_dir, load_sentiment_results
from src.report.excel_writer import write_competitive_excel
from src.report.pptx_writer import write_market_research_ppt
from src.config import OUTPUT_DIR, RAW_LISTINGS_DIR


def main():
    parser = argparse.ArgumentParser(description="生成竞品分析报告")
    parser.add_argument("--sentiment", "-s", required=True, help="情感分析结果JSON路径")
    parser.add_argument("--listings", "-l", default=None, help="Listing JSON目录路径（默认: data/raw_listings/）")
    parser.add_argument("--seller-jing", default=None, help="卖家精灵CSV路径（可选，补充数据）")
    parser.add_argument("--category", "-c", default="", help="产品品类")
    parser.add_argument("--output-dir", "-o", default=None, help="输出目录（默认: output/）")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    listings_dir = Path(args.listings) if args.listings else RAW_LISTINGS_DIR

    # 加载数据
    print("[1/4] 加载情感分析结果...")
    sentiment_data = load_sentiment_results(Path(args.sentiment))
    print(f"  共 {len(sentiment_data)} 个ASIN的情感数据")

    print("[2/4] 加载Listing数据...")
    listing_data = load_listings_from_dir(listings_dir)
    print(f"  共 {len(listing_data)} 个ASIN的Listing数据")

    seller_jing_df = None
    if args.seller_jing:
        from src.sentiment.csv_parser import load_seller_jing_csv
        seller_jing_df = load_seller_jing_csv(Path(args.seller_jing))
        print(f"  卖家精灵数据: {len(seller_jing_df)} 行")

    # 构建竞品矩阵
    print("[3/4] 构建竞品矩阵...")
    matrix_df = build_competitive_matrix(listing_data, sentiment_data, seller_jing_df)
    print(f"  矩阵: {len(matrix_df)} 行 x {len(matrix_df.columns)} 列")

    # 加载跨ASIN对比数据
    import json
    comparison = None
    sentiment_path = Path(args.sentiment)
    if sentiment_path.exists():
        with open(sentiment_path, "r", encoding="utf-8") as f:
            full_data = json.load(f)
        comparison = full_data.get("comparison")

    # 生成报告
    print("[4/4] 生成报告...")
    excel_path = write_competitive_excel(matrix_df, sentiment_data, comparison,
                                         output_dir / "competitive_matrix.xlsx")
    pptx_path = write_market_research_ppt(matrix_df, sentiment_data, comparison,
                                           args.category, output_dir / "market_research.pptx")

    print(f"\n报告生成完成!")
    print(f"  Excel: {excel_path}")
    print(f"  PPT:   {pptx_path}")


if __name__ == "__main__":
    main()
