"""竞品矩阵构建模块。

合并listing数据、评论分析结果、卖家精灵指标，生成竞品对比DataFrame。
"""
import json
from pathlib import Path

import pandas as pd


def build_competitive_matrix(
    listing_data: dict[str, dict],
    sentiment_data: dict[str, dict],
    seller_jing_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """构建竞品矩阵DataFrame，每行一个ASIN。"""
    all_asins = set(list(listing_data.keys()) + list(sentiment_data.keys()))
    rows = []

    for asin in sorted(all_asins):
        listing = listing_data.get(asin, {})
        sentiment = sentiment_data.get(asin, {})

        row = {"ASIN": asin}

        # Listing数据
        row["标题"] = listing.get("title", "")
        row["品牌"] = listing.get("brand", "")
        row["价格"] = listing.get("price", "")
        row["评分"] = listing.get("rating", "")
        row["评论数"] = listing.get("review_count", "")
        row["BSR"] = _format_bsr(listing.get("bsr", []))
        row["五点描述"] = "\n".join(listing.get("bullet_points", [])[:5])

        # 情感分析数据
        pain_points = sentiment.get("pain_points", [])
        praise_points = sentiment.get("praise_points", [])
        feature_requests = sentiment.get("feature_requests", [])
        quality_issues = sentiment.get("quality_issues", [])
        summary = sentiment.get("sentiment_summary", {})

        row["核心痛点1"] = pain_points[0]["theme"] if len(pain_points) > 0 else ""
        row["痛点1频次"] = pain_points[0].get("frequency", 0) if len(pain_points) > 0 else 0
        row["核心痛点2"] = pain_points[1]["theme"] if len(pain_points) > 1 else ""
        row["痛点2频次"] = pain_points[1].get("frequency", 0) if len(pain_points) > 1 else 0
        row["核心痛点3"] = pain_points[2]["theme"] if len(pain_points) > 2 else ""
        row["痛点3频次"] = pain_points[2].get("frequency", 0) if len(pain_points) > 2 else 0

        row["好评主题1"] = praise_points[0]["theme"] if len(praise_points) > 0 else ""
        row["好评主题2"] = praise_points[1]["theme"] if len(praise_points) > 1 else ""

        row["功能需求"] = "; ".join(fr["theme"] for fr in feature_requests[:3])
        row["质量问题"] = "; ".join(qi["theme"] for qi in quality_issues[:3])
        row["整体评价"] = summary.get("overall", "")
        row["分析评分"] = summary.get("avg_rating", "")
        row["关键洞察"] = summary.get("key_insight", "")

        # 卖家精灵补充数据（如果提供）
        if seller_jing_df is not None and "asin" in seller_jing_df.columns:
            sj_data = seller_jing_df[seller_jing_df["asin"] == asin]
            if not sj_data.empty:
                for col in sj_data.columns:
                    if col not in ("asin",) and col not in row:
                        row[f"SJ_{col}"] = sj_data.iloc[0].get(col, "")

        rows.append(row)

    return pd.DataFrame(rows)


def _format_bsr(bsr_list: list[dict]) -> str:
    """格式化BSR信息为字符串。"""
    if not bsr_list:
        return ""
    parts = []
    for bsr in bsr_list[:3]:
        rank = bsr.get("rank", "")
        cat = bsr.get("category", "")
        parts.append(f"#{rank} in {cat}")
    return "; ".join(parts)


def load_listings_from_dir(listings_dir: Path) -> dict[str, dict]:
    """从目录加载所有listing JSON文件。"""
    listings_dir = Path(listings_dir)
    data = {}
    if not listings_dir.exists():
        return data
    for f in listings_dir.glob("*.json"):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                listing = json.load(fh)
                asin = listing.get("asin", f.stem)
                data[asin] = listing
        except (json.JSONDecodeError, IOError):
            continue
    return data


def load_sentiment_results(sentiment_path: Path) -> dict[str, dict]:
    """加载情感分析结果JSON。"""
    sentiment_path = Path(sentiment_path)
    if not sentiment_path.exists():
        return {}
    with open(sentiment_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("asin_analyses", {})


def load_listings_from_db(session) -> dict[str, dict]:
    """从DB加载所有产品listing数据，返回与load_listings_from_dir相同格式。"""
    from src.db.repositories import ProductRepo
    repo = ProductRepo(session)
    products = repo.list_all()
    result = {}
    for p in products:
        result[p.asin] = {
            "asin": p.asin,
            "title": p.title or "",
            "brand": p.brand or "",
            "price": p.price,
            "rating": p.rating,
            "review_count": p.review_count,
            "bullet_points": p.bullet_points or [],
            "bsr": p.bsr or [],
            "images": p.images or [],
        }
    return result


def load_sentiment_from_db(run_id: int) -> dict[str, dict]:
    """从DB加载情感分析结果，返回与load_sentiment_results相同格式。"""
    from src.db.engine import get_session
    from src.db.repositories import SentimentRepo
    session = get_session()
    try:
        repo = SentimentRepo(session)
        return repo.to_asin_analyses_dict(run_id)
    finally:
        session.close()
