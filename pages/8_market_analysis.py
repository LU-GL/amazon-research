import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.market.excel_parser import (
    load_market_excel, compute_market_overview, compute_brand_analysis,
    compute_price_segments, compute_material_analysis, generate_recommendation,
)
from src.ui.theme import inject_global_css, section_header, divider, metric_card, PLOTLY_TEMPLATE, COLORS

st.set_page_config(page_title="市场调研分析", layout="wide")
inject_global_css()

section_header("市场调研分析", "上传卖家精灵市场调研Excel，自动生成选品方向报告")

divider()

# === 文件上传 ===
uploaded = st.file_uploader("上传市场调研Excel", type=["xlsx", "xls"], label_visibility="collapsed")

if not uploaded:
    st.info("请上传卖家精灵导出的市场调研Excel文件（.xlsx）。")
    st.stop()

# 解析文件
import tempfile, os
tmp_dir = tempfile.mkdtemp()
tmp_path = os.path.join(tmp_dir, uploaded.name)
with open(tmp_path, "wb") as f:
    f.write(uploaded.getbuffer())

try:
    data = load_market_excel(tmp_path)
except Exception as e:
    st.error(f"Excel解析失败: {e}")
    st.stop()

products = data.get("products", pd.DataFrame())
keywords = data.get("keywords", pd.DataFrame())
competitors = data.get("competitors", {})
user_profile = data.get("user_profile", {})
profit = data.get("profit", {})
sub_markets = data.get("sub_markets", pd.DataFrame())

if products.empty:
    st.warning("未找到「数据源」sheet或数据为空。")
    st.stop()

# === 顶部指标 ===
overview = compute_market_overview(products)
c1, c2, c3, c4 = st.columns(4)
metric_card(overview["total_products"], "分析产品数", c1)
metric_card(f"{overview['total_monthly_sales']:,}", "月总销量", c2)
metric_card(f"${overview['avg_price']}", "平均价格", c3)
metric_card(f"{overview['avg_rating']} 星", "平均评分", c4)

divider()

# === Tabs ===
tab_overview, tab_brand, tab_product, tab_keyword, tab_user, tab_rec = st.tabs([
    "市场总览", "品牌分析", "产品分析", "关键词", "用户画像", "选品建议"
])

# ==================== 市场总览 ====================
with tab_overview:
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### 价格分布")
        fig = px.histogram(
            products, x="价格($)", nbins=20,
            template="plotly_white",
            color_discrete_sequence=[COLORS["accent"]],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        fig.update_layout(height=350, margin={"t": 10, "b": 10})
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("#### 月销量分布")
        fig = px.histogram(
            products, x="月销量", nbins=20,
            template="plotly_white",
            color_discrete_sequence=[COLORS["info"]],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        fig.update_layout(height=350, margin={"t": 10, "b": 10})
        st.plotly_chart(fig, use_container_width=True)

    # 价格段分析
    st.markdown("#### 价格段分析")
    price_seg = compute_price_segments(products)
    if not price_seg.empty:
        col_chart, col_table = st.columns([1, 1])
        with col_chart:
            fig = px.bar(
                price_seg, x="价格段", y="avg_sales",
                color="avg_sales",
                color_continuous_scale=["#FDEBD0", COLORS["accent"]],
                template="plotly_white",
            )
            fig.update_layout(**PLOTLY_TEMPLATE["layout"])
            fig.update_layout(height=300, margin={"t": 10, "b": 10}, coloraxis_showscale=False)
            fig.update_yaxes(title_text="月均销量")
            st.plotly_chart(fig, use_container_width=True)
        with col_table:
            display_seg = price_seg.copy()
            display_seg.columns = ["价格段", "产品数", "月均销量", "平均评分", "平均毛利率(%)"]
            st.dataframe(display_seg, use_container_width=True, hide_index=True)

    # 评分 vs 销量散点图
    st.markdown("#### 评分 vs 月销量")
    fig = px.scatter(
        products, x="评分", y="月销量",
        size="评分数", color="品牌",
        hover_data=["ASIN", "价格($)"],
        template="plotly_white",
        size_max=30,
    )
    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
    fig.update_layout(height=400, margin={"t": 10, "b": 10})
    st.plotly_chart(fig, use_container_width=True)

    # 细分市场对比
    if not sub_markets.empty:
        st.markdown("#### 细分市场对比")
        display_cols = []
        rename_map = {}
        for c in ["细分市场(翻译)", "月均销量", "平均价格($)", "平均评分数", "平均星级", "平均毛利率", "新品数量", "新品占比"]:
            if c in sub_markets.columns:
                display_cols.append(c)
                rename_map[c] = c
        if display_cols:
            sm = sub_markets[display_cols].head(10).copy()
            if "平均毛利率" in sm.columns:
                sm["平均毛利率"] = (sm["平均毛利率"] * 100).round(1)
            st.dataframe(sm, use_container_width=True, hide_index=True)

# ==================== 品牌分析 ====================
with tab_brand:
    brand_stats = compute_brand_analysis(products)
    if not brand_stats.empty:
        col_chart, col_table = st.columns([1, 1])

        with col_chart:
            st.markdown("#### 品牌销量 TOP 10")
            top10 = brand_stats.head(10)
            fig = go.Figure(go.Bar(
                x=top10["total_sales"], y=top10["品牌"], orientation="h",
                marker_color=COLORS["accent"],
                text=top10["total_sales"], textposition="outside",
            ))
            fig.update_layout(**PLOTLY_TEMPLATE["layout"])
            fig.update_layout(
                height=max(300, len(top10) * 36),
                margin={"t": 10, "b": 10, "l": 10, "r": 40},
            )
            fig.update_yaxes(autorange="reversed")
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.markdown("#### 品牌详情")
            display = brand_stats.head(10).copy()
            display.columns = ["品牌", "产品数", "总销量", "月均销量", "均价($)", "均评", "均评分数", "销量占比%"]
            st.dataframe(display, use_container_width=True, hide_index=True)

        # 品牌集中度饼图
        st.markdown("#### 品牌销量占比")
        top5 = brand_stats.head(5).copy()
        others_sales = brand_stats.iloc[5:]["total_sales"].sum() if len(brand_stats) > 5 else 0
        if others_sales > 0:
            top5 = pd.concat([top5, pd.DataFrame([{"品牌": "其他", "total_sales": others_sales}])], ignore_index=True)
        fig = px.pie(
            top5, values="total_sales", names="品牌",
            hole=0.45,
            color_discrete_sequence=[COLORS["accent"], COLORS["success"], COLORS["info"],
                                     COLORS["danger"], COLORS["warning"], COLORS["text_muted"]],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        fig.update_layout(height=350)
        fig.update_traces(textinfo="label+percent", textfont=dict(size=13))
        st.plotly_chart(fig, use_container_width=True)

        # 品牌-价格-销量气泡图
        st.markdown("#### 品牌定价 vs 销量气泡图")
        fig = px.scatter(
            brand_stats.head(15), x="avg_price", y="total_sales",
            size="product_count", color="品牌",
            hover_data=["avg_rating"],
            template="plotly_white",
            size_max=40,
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        fig.update_layout(height=400, margin={"t": 10, "b": 10})
        fig.update_xaxes(title_text="平均价格($)")
        fig.update_yaxes(title_text="总销量")
        st.plotly_chart(fig, use_container_width=True)

# ==================== 产品分析 ====================
with tab_product:
    mat_stats = compute_material_analysis(products)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 材质分布")
        mat_counts = products["材质"].value_counts()
        fig = px.pie(
            values=mat_counts.values, names=mat_counts.index,
            hole=0.45,
            color_discrete_sequence=[COLORS["accent"], COLORS["info"], COLORS["success"], COLORS["warning"]],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        fig.update_layout(height=300)
        fig.update_traces(textinfo="label+percent")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### 涂层分布")
        coat_counts = products["不沾涂层"].value_counts()
        fig = px.bar(
            x=coat_counts.values, y=coat_counts.index, orientation="h",
            color_discrete_sequence=[COLORS["info"]],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        fig.update_layout(height=300, margin={"t": 10, "b": 10, "l": 10, "r": 40})
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)

    # 材质+涂层组合
    if not mat_stats.empty:
        st.markdown("#### 材质 + 涂层组合分析")
        display_mat = mat_stats.copy()
        display_mat.columns = ["材质", "涂层", "产品数", "总销量", "月均销量", "均价($)", "均评分"]
        st.dataframe(display_mat, use_container_width=True, hide_index=True)

    # 上架时间分析
    st.markdown("#### 产品上架时间分布")
    if "上架时间区间" in products.columns:
        time_counts = products["上架时间区间"].value_counts()
        fig = px.bar(
            x=time_counts.index, y=time_counts.values,
            color_discrete_sequence=[COLORS["accent"]],
        )
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        fig.update_layout(height=300, margin={"t": 10, "b": 10})
        fig.update_xaxes(title_text="上架时间区间")
        fig.update_yaxes(title_text="产品数")
        st.plotly_chart(fig, use_container_width=True)

    # 产品列表
    st.markdown("#### 全部产品数据")
    display_cols = ["ASIN", "品牌", "商品标题", "价格($)", "月销量", "评分", "评分数",
                    "材质", "不沾涂层", "毛利率", "上架时间", "小类目"]
    available_cols = [c for c in display_cols if c in products.columns]
    st.dataframe(
        products[available_cols].sort_values("月销量", ascending=False),
        use_container_width=True, hide_index=True, height=400,
    )

# ==================== 关键词 ====================
with tab_keyword:
    if not keywords.empty:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 周搜索量 TOP 15")
            # 确保有正确的列名
            kw_col = keywords.columns[0]  # 关键词
            search_col = None
            click_col = None
            for c in keywords.columns:
                if "搜索" in str(c):
                    search_col = c
                if "点击" in str(c):
                    click_col = c

            if search_col:
                top_kw = keywords.sort_values(search_col, ascending=False).head(15)
                fig = go.Figure(go.Bar(
                    x=top_kw[search_col], y=top_kw[kw_col], orientation="h",
                    marker_color=COLORS["accent"],
                    text=top_kw[search_col], textposition="outside",
                ))
                fig.update_layout(**PLOTLY_TEMPLATE["layout"])
                fig.update_layout(
                    height=max(350, len(top_kw) * 30),
                    margin={"t": 10, "b": 10, "l": 10, "r": 50},
                )
                fig.update_yaxes(autorange="reversed")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### 关键词详情")
            display_kw = keywords.copy()
            display_kw.columns = [str(c) for c in display_kw.columns]
            st.dataframe(display_kw, use_container_width=True, hide_index=True, height=400)

        # 搜索量 vs 点击量散点
        if search_col and click_col:
            st.markdown("#### 搜索量 vs 点击量")
            fig = px.scatter(
                keywords, x=search_col, y=click_col,
                text=kw_col,
                template="plotly_white",
                color_discrete_sequence=[COLORS["accent"]],
            )
            fig.update_layout(**PLOTLY_TEMPLATE["layout"])
            fig.update_layout(height=400, margin={"t": 10, "b": 10})
            fig.update_traces(textposition="top center", textfont_size=9)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("未找到关键词数据。")

# ==================== 用户画像 ====================
with tab_user:
    if user_profile:
        col1, col2 = st.columns(2)

        with col1:
            if user_profile.get("user_groups"):
                st.markdown("#### 主要用户群体")
                for g in user_profile["user_groups"]:
                    detail = f" - {g['detail']}" if "detail" in g else ""
                    st.markdown(f"""
                    <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-left:3px solid #E67E22;
                         border-radius:0 8px 8px 0;padding:12px 16px;margin:6px 0;">
                        <strong>{g['name']}</strong>{detail}
                    </div>
                    """, unsafe_allow_html=True)

            if user_profile.get("scenarios"):
                st.markdown("#### 使用场景")
                for s in user_profile["scenarios"]:
                    reason = f" - {s.get('reason', '')}" if "reason" in s else ""
                    st.markdown(f"""
                    <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-left:3px solid #2980B9;
                         border-radius:0 8px 8px 0;padding:12px 16px;margin:6px 0;">
                        <strong>{s['name']}</strong>{reason}
                    </div>
                    """, unsafe_allow_html=True)

        with col2:
            if user_profile.get("motivations"):
                st.markdown("#### 购买动机")
                for m in user_profile["motivations"]:
                    st.markdown(f"""
                    <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-left:3px solid #27AE60;
                         border-radius:0 8px 8px 0;padding:12px 16px;margin:6px 0;">
                        <strong>{m['name']}</strong>
                    </div>
                    """, unsafe_allow_html=True)

            if user_profile.get("unmet_needs"):
                st.markdown("#### 未被满足的需求（机会点）")
                for n in user_profile["unmet_needs"]:
                    reason = f" - {n.get('reason', '')}" if "reason" in n else ""
                    st.markdown(f"""
                    <div style="background:#FADBD8;border:1px solid #E74C3C55;border-left:3px solid #E74C3C;
                         border-radius:0 8px 8px 0;padding:12px 16px;margin:6px 0;">
                        <strong style="color:#E74C3C;">{n['name']}</strong>{reason}
                    </div>
                    """, unsafe_allow_html=True)

        # 利润分析
        if profit:
            divider()
            st.markdown("#### 利润模型")
            pcol1, pcol2 = st.columns(2)
            with pcol1:
                profit_items = []
                for k, v in profit.items():
                    if isinstance(v, (int, float)):
                        profit_items.append({"项目": k, "数值": round(v, 4) if abs(v) < 1 else round(v, 2)})
                    else:
                        profit_items.append({"项目": k, "数值": str(v)})
                st.dataframe(pd.DataFrame(profit_items), use_container_width=True, hide_index=True)
            with pcol2:
                margin = profit.get("利润率")
                if margin is not None:
                    margin_pct = float(margin) * 100
                    color = COLORS["success"] if margin_pct > 0 else COLORS["danger"]
                    st.markdown(f"""
                    <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-radius:12px;padding:30px;text-align:center;">
                        <div style="font-size:0.9rem;color:#5D6D7E;">利润率</div>
                        <div style="font-size:3rem;font-weight:700;color:{color};">{margin_pct:.1f}%</div>
                        <div style="color:#95A5A6;font-size:0.85rem;margin-top:8px;">
                            {'盈利状态' if margin_pct > 0 else '亏损状态，需优化成本结构'}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("未找到用户画像数据。")

# ==================== 选品建议 ====================
with tab_rec:
    rec = generate_recommendation(data)

    st.markdown("#### 市场概况")
    st.markdown(f"""
    <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-radius:12px;padding:20px;">
        <p style="color:#2C3E50;font-size:1rem;line-height:1.8;">{rec.get('market_summary', '')}</p>
    </div>
    """, unsafe_allow_html=True)

    divider()

    # 竞品分析摘要
    if competitors:
        st.markdown("#### 竞品对标")
        comp_rows = []
        for asin, comp in competitors.items():
            comp_rows.append({
                "ASIN": asin,
                "品牌": comp.get("品牌", ""),
                "售价": comp.get("售价", ""),
                "月销量": comp.get("月销量", ""),
                "星级": comp.get("星级", ""),
                "材质": comp.get("材质", ""),
                "涂层": comp.get("涂层", ""),
                "排名": comp.get("小类排名", ""),
            })
        comp_df = pd.DataFrame(comp_rows)
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

        # 竞品优劣势
        for asin, comp in competitors.items():
            brand = comp.get("品牌", asin)
            advantage = comp.get("产品优势", "")
            disadvantage = comp.get("产品劣势", "")
            if advantage or disadvantage:
                with st.expander(f"{brand} ({asin}) - 优劣势分析"):
                    if advantage:
                        st.markdown(f"**优势:** {advantage}")
                    if disadvantage:
                        st.markdown(f"**劣势:** {disadvantage}")

    divider()

    # 差异化方向
    st.markdown("#### 差异化选品方向")

    directions = []

    # 材质方向
    alt_mats = rec.get("material_direction", [])
    if alt_mats:
        for m in alt_mats:
            directions.append({
                "方向": f"{m['材质']} + {m['不沾涂层']}",
                "产品数": m["count"],
                "月均销量": m["avg_sales"],
                "均价": f"${m['avg_price']}",
                "评分": m["avg_rating"],
            })

    # 未被满足的需求
    if user_profile.get("unmet_needs"):
        for n in user_profile["unmet_needs"]:
            directions.append({
                "方向": f"解决痛点: {n['name']}",
                "产品数": "-",
                "月均销量": "-",
                "均价": "-",
                "评分": "-",
            })

    if directions:
        st.dataframe(pd.DataFrame(directions), use_container_width=True, hide_index=True)

    # 最终建议
    st.markdown("#### 选品方向总结")

    rec_cards = []
    if user_profile.get("unmet_needs"):
        needs = [n["name"] for n in user_profile["unmet_needs"]]
        rec_cards.append({
            "title": "解决核心痛点",
            "items": needs,
            "color": COLORS["danger"],
        })

    if alt_mats:
        mat_items = [f"{m['材质']} + {m['不沾涂层']}" for m in alt_mats[:3]]
        rec_cards.append({
            "title": "材质差异化",
            "items": mat_items,
            "color": COLORS["info"],
        })

    if user_profile.get("user_groups"):
        groups = [g["name"] for g in user_profile["user_groups"]]
        rec_cards.append({
            "title": "目标用户",
            "items": groups,
            "color": COLORS["success"],
        })

    rec_cols = st.columns(min(len(rec_cards), 3))
    for i, card in enumerate(rec_cards):
        with rec_cols[i]:
            items_html = "".join(
                f'<li style="margin:4px 0;color:#5D6D7E;">{item}</li>'
                for item in card["items"]
            )
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-top:3px solid {card['color']};
                 border-radius:0 0 12px 12px;padding:20px;min-height:200px;">
                <h4 style="color:{card['color']};margin-bottom:12px;">{card['title']}</h4>
                <ul style="padding-left:20px;margin:0;">{items_html}</ul>
            </div>
            """, unsafe_allow_html=True)
