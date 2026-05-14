import json
from pathlib import Path


def compare_across_asins(asin_analyses: dict[str, dict]) -> dict:
    """跨ASIN对比分析：找出共同痛点、差异点、市场机会。"""
    # 收集所有ASIN的痛点/好评/f需求
    all_pain_themes: dict[str, dict] = {}
    all_praise_themes: dict[str, dict] = {}
    all_feature_themes: dict[str, dict] = {}

    for asin, analysis in asin_analyses.items():
        for pp in analysis.get("pain_points", []):
            theme = pp["theme"]
            if theme not in all_pain_themes:
                all_pain_themes[theme] = {"theme": theme, "frequency": 0, "asins": [], "severity": pp.get("severity", "medium")}
            all_pain_themes[theme]["frequency"] += pp.get("frequency", 0)
            all_pain_themes[theme]["asins"].append(asin)

        for pp in analysis.get("praise_points", []):
            theme = pp["theme"]
            if theme not in all_praise_themes:
                all_praise_themes[theme] = {"theme": theme, "frequency": 0, "asins": []}
            all_praise_themes[theme]["frequency"] += pp.get("frequency", 0)
            all_praise_themes[theme]["asins"].append(asin)

        for fr in analysis.get("feature_requests", []):
            theme = fr["theme"]
            if theme not in all_feature_themes:
                all_feature_themes[theme] = {"theme": theme, "frequency": 0, "asins": []}
            all_feature_themes[theme]["frequency"] += fr.get("frequency", 0)
            all_feature_themes[theme]["asins"].append(asin)

    # 排序
    common_pains = sorted(
        [v for v in all_pain_themes.values() if len(v["asins"]) > 1],
        key=lambda x: x["frequency"], reverse=True
    )
    unique_pains = sorted(
        [v for v in all_pain_themes.values() if len(v["asins"]) == 1],
        key=lambda x: x["frequency"], reverse=True
    )
    common_praises = sorted(
        all_praise_themes.values(), key=lambda x: x["frequency"], reverse=True
    )
    opportunities = sorted(
        all_feature_themes.values(), key=lambda x: x["frequency"], reverse=True
    )

    return {
        "common_pain_points": common_pains[:10],
        "unique_pain_points": unique_pains[:10],
        "common_praise_points": common_praises[:10],
        "feature_opportunities": opportunities[:10],
        "total_asins": len(asin_analyses),
        "insights": _generate_insights(common_pains, unique_pains, opportunities),
    }


def _generate_insights(common_pains: list, unique_pains: list, opportunities: list) -> list[str]:
    """基于数据生成简要洞察。"""
    insights = []
    if common_pains:
        top = common_pains[0]
        insights.append(
            f"市场共性痛点: '{top['theme']}'影响了{len(top['asins'])}个竞品，"
            f"出现{top['frequency']}次，是最大的市场机会点"
        )
    if unique_pains:
        for p in unique_pains[:3]:
            insights.append(
                f"差异化机会: '{p['theme']}'仅出现在{p['asins'][0]}中，"
                f"解决此问题可获得竞争优势"
            )
    if opportunities:
        top_req = opportunities[0]
        insights.append(
            f"用户最期望的功能: '{top_req['theme']}'，"
            f"被{len(top_req['asins'])}个产品的用户提及{top_req['frequency']}次"
        )
    return insights


def export_sentiment_results(
    asin_analyses: dict[str, dict],
    comparison: dict,
    output_path: Path,
) -> Path:
    """导出情感分析结果到JSON文件。"""
    output = {
        "asin_analyses": asin_analyses,
        "comparison": comparison,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"分析结果已保存到: {output_path}")
    return output_path


def save_sentiment_to_db(asin_analyses: dict[str, dict], comparison: dict, run_id: int):
    """将情感分析结果持久化到SQLite。"""
    from src.db.engine import get_session
    from src.db.repositories import ProductRepo, SentimentRepo

    session = get_session()
    try:
        product_repo = ProductRepo(session)
        sentiment_repo = SentimentRepo(session)
        for asin, analysis in asin_analyses.items():
            product = product_repo.get_or_create(asin)
            sentiment_repo.save_analysis(run_id, product.id, analysis)
        sentiment_repo.save_comparison(run_id, comparison)
        session.commit()
    finally:
        session.close()
