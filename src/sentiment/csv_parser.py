import pandas as pd
from pathlib import Path

COLUMN_MAP = {
    "ASIN": "asin",
    "asin": "asin",
    "Asin": "asin",
    "评论标题": "title",
    "标题": "title",
    "title": "title",
    "评论内容": "content",
    "内容": "content",
    "content": "content",
    "review_text": "content",
    "评分": "rating",
    "rating": "rating",
    "星级": "rating",
    "评论日期": "date",
    "日期": "date",
    "date": "date",
    "review_date": "date",
    "已验证购买": "verified",
    "verified": "verified",
    "已验证": "verified",
    "品牌": "brand",
    "brand": "brand",
    "变体": "variant",
    "variant": "variant",
    "变体信息": "variant",
}


def load_seller_jing_csv(filepath: Path) -> pd.DataFrame:
    """加载卖家精灵导出的CSV，自动处理编码和列名映射。"""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")

    # 尝试UTF-8，失败则GBK/GB18030
    for encoding in ("utf-8", "utf-8-sig", "gbk", "gb18030", "latin1"):
        try:
            df = pd.read_csv(filepath, encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        raise ValueError(f"无法解码文件 {filepath}，请检查文件编码")

    # 标准化列名：去除首尾空格，映射到英文
    df.columns = df.columns.str.strip()
    rename_map = {}
    for col in df.columns:
        mapped = COLUMN_MAP.get(col.strip())
        if mapped:
            rename_map[col] = mapped
    df = df.rename(columns=rename_map)

    # 检查必需列
    required = {"asin", "content"}
    missing = required - set(df.columns)
    if missing:
        available = list(df.columns)
        raise ValueError(
            f"CSV缺少必需列: {missing}。可用列: {available}。"
            f"请确认导出的是评论数据（而非关键词或ASIN数据）。"
        )

    # 填充缺失的可选列
    if "title" not in df.columns:
        df["title"] = ""
    if "rating" not in df.columns:
        df["rating"] = None
    if "date" not in df.columns:
        df["date"] = ""
    if "verified" not in df.columns:
        df["verified"] = ""
    if "brand" not in df.columns:
        df["brand"] = ""
    if "variant" not in df.columns:
        df["variant"] = ""

    # 清洗：content为空的行标记为空字符串
    df["content"] = df["content"].fillna("").astype(str)
    df["title"] = df["title"].fillna("").astype(str)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    return df


def split_reviews_by_asin(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """按ASIN分组，返回 {asin: DataFrame} 字典。"""
    groups = {}
    for asin, group in df.groupby("asin"):
        asin_str = str(asin).strip()
        if asin_str and asin_str != "nan":
            groups[asin_str] = group.reset_index(drop=True)
    return groups


def prepare_review_batches(
    df: pd.DataFrame, batch_size: int = 20
) -> list[list[dict]]:
    """将评论拆分为批次，每批约batch_size条，供API调用。"""
    reviews = []
    for _, row in df.iterrows():
        content = str(row.get("content", "")).strip()
        if not content:
            continue
        review = {
            "title": str(row.get("title", "")).strip(),
            "content": content,
            "rating": int(row["rating"]) if pd.notna(row.get("rating")) else None,
            "date": str(row.get("date", "")).strip(),
            "verified": str(row.get("verified", "")).strip(),
            "variant": str(row.get("variant", "")).strip(),
        }
        reviews.append(review)

    batches = []
    for i in range(0, len(reviews), batch_size):
        batches.append(reviews[i : i + batch_size])
    return batches
