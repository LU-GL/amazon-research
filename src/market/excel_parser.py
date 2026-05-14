"""市场调研Excel解析器 - 解析卖家精灵导出的市场调研报告。"""

import pandas as pd


def load_market_excel(file_path: str) -> dict:
    """加载市场调研Excel所有sheet，返回结构化数据。"""
    xls = pd.ExcelFile(file_path, engine="openpyxl")
    result = {"sheets": xls.sheet_names}

    for name in xls.sheet_names:
        if name == "数据源":
            result["products"] = _parse_products(xls, name)
        elif name == "套装拆分":
            result["sub_markets"] = _parse_sub_markets(xls, name)
        elif name == "竞品分析":
            result["competitors"] = _parse_competitors(xls, name)
        elif name == "用户画像":
            result["user_profile"] = _parse_user_profile(xls, name)
        elif name == "利润计算":
            result["profit"] = _parse_profit(xls, name)
        elif name == "市场调研":
            result["keywords"] = _parse_keywords(xls, name)

    return result


def _parse_products(xls, sheet_name) -> pd.DataFrame:
    """解析数据源sheet - 产品列表。"""
    df = pd.read_excel(xls, sheet_name=sheet_name)
    # 清理列名
    df.columns = [c.strip() for c in df.columns]
    return df


def _parse_sub_markets(xls, sheet_name) -> pd.DataFrame:
    """解析套装拆分sheet - 细分市场数据。"""
    df = pd.read_excel(xls, sheet_name=sheet_name, header=1)
    # 只保留有数据的行
    df = df.dropna(subset=[df.columns[0]])
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _parse_competitors(xls, sheet_name) -> dict:
    """解析竞品分析sheet - 竞品对比。"""
    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    competitors = {}
    for col_idx in range(1, min(df.shape[1], 5)):
        # Row 3 (0-indexed) = ASIN row
        asin = df.iloc[3, col_idx]
        if pd.isna(asin):
            continue
        asin = str(asin).strip()
        comp = {}
        for row_idx in range(1, df.shape[0]):
            label = df.iloc[row_idx, 0]
            val = df.iloc[row_idx, col_idx]
            if pd.notna(label) and pd.notna(val):
                label_str = str(label).strip()
                val_str = str(val).strip()
                if val_str.startswith("=") or not val_str:
                    continue
                comp[label_str] = val_str
        competitors[asin] = comp
    return competitors


def _parse_user_profile(xls, sheet_name) -> dict:
    """解析用户画像sheet。"""
    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    result = {
        "user_groups": [],
        "scenarios": [],
        "motivations": [],
        "unmet_needs": [],
    }

    current_section = None
    for _, row in df.iterrows():
        vals = [str(v) if pd.notna(v) else "" for v in row]
        first = vals[0].strip()

        if first == "主要用户群体":
            current_section = "user_groups"
            continue
        elif first == "使用场景":
            current_section = "scenarios"
            continue
        elif first == "购买动机":
            current_section = "motivations"
            continue
        elif first == "未被满足的需求":
            current_section = "unmet_needs"
            continue

        # 跳过表头行
        if first in ("群体", "描述") or (first == "" and vals[1] == "" and vals[2] == ""):
            continue
        if first == "原因" or first == "特征" or first == "需求":
            continue

        if current_section and first:
            entry = {"name": first}
            if vals[1]:
                entry["detail"] = vals[1]
            if len(vals) > 2 and vals[2]:
                entry["reason"] = vals[2]
            result[current_section].append(entry)

    return result


def _parse_profit(xls, sheet_name) -> dict:
    """解析利润计算sheet。"""
    df = pd.read_excel(xls, sheet_name=sheet_name)
    if df.empty:
        return {}

    # 第一行是标签行
    labels = [str(c).strip() for c in df.columns]
    values = df.iloc[0].tolist()

    profit = {}
    for label, val in zip(labels, values):
        if pd.notna(val) and label and not label.startswith("Unnamed"):
            profit[label] = val
    return profit


def _parse_keywords(xls, sheet_name) -> pd.DataFrame:
    """解析市场调研sheet中的关键词数据。"""
    df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
    # 关键词数据从 row 93 开始
    kw_start = None
    for i, row in df.iterrows():
        vals = [str(v) if pd.notna(v) else "" for v in row]
        if "关键词" in vals[0] and "搜索量" in str(vals):
            kw_start = i
            break

    if kw_start is None:
        return pd.DataFrame()

    kw_df = pd.read_excel(
        xls, sheet_name=sheet_name, header=kw_start, nrows=50
    )
    kw_df = kw_df.dropna(subset=[kw_df.columns[0]])
    return kw_df


def compute_market_overview(df: pd.DataFrame) -> dict:
    """从产品数据计算市场总览指标。"""
    if df.empty:
        return {}

    return {
        "total_products": len(df),
        "total_monthly_sales": int(df["月销量"].sum()),
        "avg_monthly_sales": int(df["月销量"].mean()),
        "avg_price": round(df["价格($)"].mean(), 2),
        "median_price": round(df["价格($)"].median(), 2),
        "avg_rating": round(df["评分"].mean(), 2),
        "avg_reviews": int(df["评分数"].mean()),
        "avg_margin": round(df["毛利率"].mean() * 100, 1) if "毛利率" in df.columns else None,
        "brand_count": df["品牌"].nunique(),
        "seller_count": df["BuyBox卖家"].nunique() if "BuyBox卖家" in df.columns else None,
    }


def compute_brand_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """按品牌聚合分析。"""
    if df.empty:
        return pd.DataFrame()

    brand_stats = df.groupby("品牌").agg(
        product_count=("ASIN", "count"),
        total_sales=("月销量", "sum"),
        avg_sales=("月销量", "mean"),
        avg_price=("价格($)", "mean"),
        avg_rating=("评分", "mean"),
        avg_reviews=("评分数", "mean"),
    ).sort_values("total_sales", ascending=False).reset_index()

    brand_stats["avg_price"] = brand_stats["avg_price"].round(2)
    brand_stats["avg_rating"] = brand_stats["avg_rating"].round(2)
    brand_stats["sales_share_%"] = (
        brand_stats["total_sales"] / brand_stats["total_sales"].sum() * 100
    ).round(1)

    return brand_stats


def compute_price_segments(df: pd.DataFrame) -> pd.DataFrame:
    """价格分段分析。"""
    if df.empty:
        return pd.DataFrame()

    bins = [0, 50, 80, 120, 200, 500]
    labels = ["<$50", "$50-80", "$80-120", "$120-200", ">$200"]
    df = df.copy()
    df["价格段"] = pd.cut(df["价格($)"], bins=bins, labels=labels)

    seg = df.groupby("价格段", observed=True).agg(
        count=("ASIN", "count"),
        avg_sales=("月销量", "mean"),
        avg_rating=("评分", "mean"),
        avg_margin=("毛利率", "mean"),
    ).reset_index()

    seg["avg_sales"] = seg["avg_sales"].round(0).astype(int)
    seg["avg_rating"] = seg["avg_rating"].round(2)
    seg["avg_margin"] = (seg["avg_margin"] * 100).round(1)
    return seg


def compute_material_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """材质+涂层组合分析。"""
    if df.empty:
        return pd.DataFrame()

    combo = df.groupby(["材质", "不沾涂层"]).agg(
        count=("ASIN", "count"),
        total_sales=("月销量", "sum"),
        avg_sales=("月销量", "mean"),
        avg_price=("价格($)", "mean"),
        avg_rating=("评分", "mean"),
    ).sort_values("total_sales", ascending=False).reset_index()

    combo["avg_sales"] = combo["avg_sales"].round(0).astype(int)
    combo["avg_price"] = combo["avg_price"].round(2)
    combo["avg_rating"] = combo["avg_rating"].round(2)
    return combo


def generate_recommendation(data: dict) -> dict:
    """根据数据自动生成选品方向建议。"""
    products = data.get("products", pd.DataFrame())
    if products.empty:
        return {}

    material_stats = compute_material_analysis(products)
    price_seg = compute_price_segments(products)
    brand_stats = compute_brand_analysis(products)

    # 寻找机会区间：有一定销量、价格适中、竞争较少
    price_opportunities = price_seg[price_seg["count"] <= 30].sort_values(
        "avg_sales", ascending=False
    )

    # 材质差异化：非主流材质
    main_material = material_stats.iloc[0]["材质"] if len(material_stats) > 0 else "压铸铝"
    alt_materials = material_stats[material_stats["材质"] != main_material]

    # 非头部品牌分析
    top_brand = brand_stats.iloc[0]["品牌"] if len(brand_stats) > 0 else "CAROTE"

    return {
        "market_summary": _summarize_market(products),
        "material_direction": alt_materials.to_dict("records") if len(alt_materials) > 0 else [],
        "price_opportunities": price_opportunities.to_dict("records") if len(price_opportunities) > 0 else [],
        "main_competitor": top_brand,
    }


def _summarize_market(df: pd.DataFrame) -> str:
    """生成市场摘要文字。"""
    total = len(df)
    brands = df["品牌"].nunique()
    avg_price = df["价格($)"].mean()
    avg_sales = df["月销量"].mean()
    main_material = df["材质"].value_counts().index[0] if len(df) > 0 else "未知"
    main_coating = df["不沾涂层"].value_counts().index[0] if len(df) > 0 else "未知"

    return (
        f"共{total}个产品、{brands}个品牌，"
        f"均价${avg_price:.0f}，月均销量{avg_sales:.0f}件。"
        f"主流材质为{main_material}，涂层以{main_coating}为主。"
    )
