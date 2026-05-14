import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
from src.db.engine import init_db, get_session
from src.db.repositories import ProductRepo, ReviewRepo, AnalysisRunRepo
from src.ui.theme import inject_global_css, metric_card, section_header, divider, status_badge

st.set_page_config(page_title="Amazon 市场研究", page_icon="", layout="wide")
inject_global_css()
init_db()

st.markdown(f"""
<div style="text-align:center;padding:40px 0 20px;">
    <h1 style="font-size:2.6rem;letter-spacing:-1px;margin-bottom:4px;">Amazon 市场研究系统</h1>
    <p style="color:#5D6D7E;font-size:1.05rem;margin-top:0;">竞品分析 · 评论挖掘 · 市场洞察</p>
</div>
""", unsafe_allow_html=True)

divider()

session = get_session()
try:
    product_repo = ProductRepo(session)
    review_repo = ReviewRepo(session)
    run_repo = AnalysisRunRepo(session)

    c1, c2, c3, c4 = st.columns(4)
    metric_card(product_repo.count(), "产品数量", c1)
    metric_card(review_repo.count_all(), "评论总数", c2)
    metric_card(run_repo.count(), "分析次数", c3)
    runs = run_repo.list_recent(1)
    metric_card(runs[0].status if runs else "—", "最近状态", c4)

    divider()
    section_header("最近分析运行", "最近10次分析任务执行记录")

    runs = run_repo.list_recent(10)
    if runs:
        rows = []
        for r in runs:
            rows.append({
                "ID": r.id,
                "类型": r.run_type,
                "品类": r.category or "—",
                "状态": status_badge(r.status),
                "ASIN数": r.asins_analyzed,
                "评论数": r.total_reviews,
                "创建时间": r.created_at.strftime("%m-%d %H:%M") if r.created_at else "—",
            })
        df = pd.DataFrame(rows)
        st.markdown(df.to_html(escape=False, index=False, classes="data-table"),
                    unsafe_allow_html=True)
    else:
        st.info("暂无分析记录。请先导入数据并运行分析。")

    divider()
    section_header("快速操作")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.page_link("pages/2_upload_csv.py", label="上传CSV数据")
    with c2:
        st.page_link("pages/3_sentiment_analysis.py", label="开始评论分析")
    with c3:
        st.page_link("pages/8_market_analysis.py", label="市场调研分析")
    with c4:
        st.page_link("pages/6_reports.py", label="下载报告")

finally:
    session.close()
