import json
import time
from pathlib import Path

import pandas as pd
from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, MODEL
from src.sentiment.csv_parser import prepare_review_batches

SYSTEM_PROMPT = """你是一位亚马逊产品评论分析专家。你的任务是从用户评论中提取结构化的市场洞察。

请分析以下评论，输出JSON格式结果，包含以下字段：

{
  "pain_points": [
    {"theme": "痛点主题", "frequency": 出现次数, "severity": "high/medium/low",
     "examples": ["原文摘录1", "原文摘录2"]}
  ],
  "praise_points": [
    {"theme": "好评主题", "frequency": 出现次数, "examples": ["原文摘录1"]}
  ],
  "feature_requests": [
    {"theme": "用户期望的功能", "frequency": 出现次数, "examples": ["原文摘录1"]}
  ],
  "quality_issues": [
    {"theme": "质量问题", "frequency": 出现次数, "severity": "high/medium/low"}
  ],
  "sentiment_summary": {
    "overall": "positive/negative/mixed",
    "avg_rating": 平均分,
    "key_insight": "一句话总结"
  }
}

注意：
- 只输出纯JSON，不要加markdown代码块包裹
- 频率基于评论中实际出现的次数
- severity根据对使用体验的影响程度判断
- 尽量保留原文摘录作为证据
- 如果评论内容不足以判断，对应数组可以为空"""


def _get_client() -> Anthropic:
    return Anthropic(
        api_key=ANTHROPIC_API_KEY,
        base_url=ANTHROPIC_BASE_URL,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry=retry_if_exception_type(Exception),
)
def analyze_review_batch(
    client: Anthropic,
    reviews: list[dict],
    product_category: str = "",
) -> dict:
    """发送一批评论到Claude API进行分析，返回解析后的字典。"""
    review_text_parts = []
    for i, r in enumerate(reviews, 1):
        rating_str = f" [{r['rating']}星]" if r.get("rating") else ""
        verified_str = " [已验证购买]" if r.get("verified") else ""
        variant_str = f" [变体:{r['variant']}]" if r.get("variant") else ""
        title = f"标题: {r['title']}\n" if r.get("title") else ""
        review_text_parts.append(
            f"---评论{i}{rating_str}{verified_str}{variant_str}---\n"
            f"{title}内容: {r['content']}"
        )

    review_text = "\n\n".join(review_text_parts)
    category_line = f"产品品类: {product_category}\n\n" if product_category else ""

    user_message = f"{category_line}请分析以下{len(reviews)}条评论：\n\n{review_text}"

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text.strip()

    # 处理可能被markdown包裹的响应
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        # 去掉首行 ```json 和末行 ```
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        raw_text = "\n".join(lines)

    return json.loads(raw_text)


def analyze_all_reviews(
    asin: str,
    reviews_df: pd.DataFrame,
    product_category: str = "",
) -> dict:
    """对一个ASIN的所有评论进行批量分析，合并结果。"""
    client = _get_client()
    batches = prepare_review_batches(reviews_df, batch_size=20)

    if not batches:
        return {
            "asin": asin,
            "total_reviews": 0,
            "analyzed_batches": 0,
            "pain_points": [],
            "praise_points": [],
            "feature_requests": [],
            "quality_issues": [],
            "sentiment_summary": {"overall": "unknown", "avg_rating": None, "key_insight": "无有效评论"},
        }

    batch_results = []
    for i, batch in enumerate(batches):
        print(f"  ASIN {asin}: 分析批次 {i+1}/{len(batches)} ({len(batch)}条评论)")
        result = analyze_review_batch(client, batch, product_category)
        batch_results.append(result)
        if i < len(batches) - 1:
            time.sleep(1)  # 批次间延迟，避免限流

    merged = _merge_batch_results(batch_results)
    merged["asin"] = asin
    merged["total_reviews"] = len(reviews_df)
    merged["analyzed_batches"] = len(batches)
    return merged


def _merge_batch_results(batch_results: list[dict]) -> dict:
    """合并多个批次的分析结果，按theme聚合。"""
    pain_map: dict[str, dict] = {}
    praise_map: dict[str, dict] = {}
    feature_map: dict[str, dict] = {}
    quality_map: dict[str, dict] = {}
    ratings = []

    for result in batch_results:
        for pp in result.get("pain_points", []):
            theme = pp["theme"]
            if theme not in pain_map:
                pain_map[theme] = {"theme": theme, "frequency": 0, "severity": pp.get("severity", "medium"), "examples": []}
            pain_map[theme]["frequency"] += pp.get("frequency", 1)
            pain_map[theme]["examples"].extend(pp.get("examples", [])[:2])

        for pp in result.get("praise_points", []):
            theme = pp["theme"]
            if theme not in praise_map:
                praise_map[theme] = {"theme": theme, "frequency": 0, "examples": []}
            praise_map[theme]["frequency"] += pp.get("frequency", 1)
            praise_map[theme]["examples"].extend(pp.get("examples", [])[:2])

        for fr in result.get("feature_requests", []):
            theme = fr["theme"]
            if theme not in feature_map:
                feature_map[theme] = {"theme": theme, "frequency": 0, "examples": []}
            feature_map[theme]["frequency"] += fr.get("frequency", 1)
            feature_map[theme]["examples"].extend(fr.get("examples", [])[:2])

        for qi in result.get("quality_issues", []):
            theme = qi["theme"]
            if theme not in quality_map:
                quality_map[theme] = {"theme": theme, "frequency": 0, "severity": qi.get("severity", "medium")}
            quality_map[theme]["frequency"] += qi.get("frequency", 1)

        summary = result.get("sentiment_summary", {})
        if summary.get("avg_rating") is not None:
            ratings.append(summary["avg_rating"])

    # 按频率排序，截取前10个example
    pain_list = sorted(pain_map.values(), key=lambda x: x["frequency"], reverse=True)
    praise_list = sorted(praise_map.values(), key=lambda x: x["frequency"], reverse=True)
    feature_list = sorted(feature_map.values(), key=lambda x: x["frequency"], reverse=True)
    quality_list = sorted(quality_map.values(), key=lambda x: x["frequency"], reverse=True)

    for item in pain_list + praise_list + feature_list:
        item["examples"] = item["examples"][:5]

    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else None

    return {
        "pain_points": pain_list,
        "praise_points": praise_list,
        "feature_requests": feature_list,
        "quality_issues": quality_list,
        "sentiment_summary": {
            "overall": _infer_overall(pain_list, praise_list),
            "avg_rating": avg_rating,
            "key_insight": "",
        },
    }


def _infer_overall(pain_points: list, praise_points: list) -> str:
    pain_total = sum(p.get("frequency", 0) for p in pain_points)
    praise_total = sum(p.get("frequency", 0) for p in praise_points)
    if praise_total > pain_total * 1.5:
        return "positive"
    elif pain_total > praise_total * 1.5:
        return "negative"
    return "mixed"
