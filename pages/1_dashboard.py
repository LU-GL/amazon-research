import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from src.db.engine import init_db, get_session
from src.db.repositories import ProductRepo, ReviewRepo
from src.ui.theme import inject_global_css, metric_card, section_header, divider, PLOTLY_TEMPLATE

st.set_page_config(page_title="数据总览", layout="wide")
inject_global_css()

section_header("数据总览", "已导入产品及评论数据统计")

session = get_session()
try:
    product_repo = ProductRepo(session)
    review_repo = ReviewRepo(session)
    products = product_repo.list_all()

    if not products:
        st.info("暂无产品数据。请前往「上传CSV」页面导入数据。")
    else:
        # 指标卡
        c1, c2, c3 = st.columns(3)
        metric_card(len(products), "产品总数", c1)
        metric_card(review_repo.count_all(), "评论总数", c2)
        avg_reviews = review_repo.count_all() // max(len(products), 1)
        metric_card(avg_reviews, "平均评论/产品", c3)

        divider()

        # 产品列表
        col_left, col_right = st.columns([3, 2])

        with col_left:
            section_header("产品列表")
            data = []
            for p in products:
                count = review_repo.count_by_product(p.id)
                data.append({
                    "ASIN": p.asin,
                    "标题": (p.title or "—")[:40],
                    "品牌": p.brand or "—",
                    "价格": f"${p.price:.2f}" if p.price else "—",
                    "评分": f"{p.rating:.1f}" if p.rating else "—",
                    "评论数": count,
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True, height=400)

        with col_right:
            section_header("评论分布")
            asin_data = []
            for p in products:
                count = review_repo.count_by_product(p.id)
                if count > 0:
                    asin_data.append({"ASIN": p.asin, "评论数": count})

            if asin_data:
                df_chart = pd.DataFrame(asin_data).sort_values("评论数", ascending=True).tail(15)
                fig = px.bar(df_chart, x="评论数", y="ASIN", orientation="h",
                             template="plotly_white")
                fig.update_layout(**PLOTLY_TEMPLATE["layout"])
                fig.update_layout(height=max(300, len(df_chart) * 35), margin={"t": 10, "b": 10})
                fig.update_traces(marker_color="#E67E22", marker_line_width=0)
                st.plotly_chart(fig, use_container_width=True)

finally:
    session.close()
