import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from src.db.engine import init_db, get_session
from src.db.repositories import AnalysisRunRepo, SentimentRepo
from src.analysis.competitive_matrix import build_competitive_matrix, load_listings_from_db
from src.report.excel_writer import write_competitive_excel
from src.ui.theme import inject_global_css, section_header, divider, COLORS

st.set_page_config(page_title="竞品矩阵", layout="wide")
inject_global_css()

section_header("竞品矩阵", "多维度产品对比分析")

divider()

session = get_session()
try:
    run_repo = AnalysisRunRepo(session)
    runs = [r for r in run_repo.list_recent(50) if r.status == "completed"]

    if not runs:
        st.warning("暂无已完成的分析。请先运行评论分析。")
    else:
        run_options = {f"#{r.id} | {r.category or r.run_type} | {r.created_at.strftime('%m-%d %H:%M') if r.created_at else '-'}": r.id for r in runs}
        col_sel, col_btn = st.columns([3, 1])
        with col_sel:
            selected_label = st.selectbox("分析批次", list(run_options.keys()))
        run_id = run_options[selected_label]

        sentiment_repo = SentimentRepo(session)
        sentiment_data = sentiment_repo.to_asin_analyses_dict(run_id)
        listing_data = load_listings_from_db(session)

        if not sentiment_data:
            st.warning("该批次无情感分析数据。")
        else:
            matrix_df = build_competitive_matrix(listing_data, sentiment_data)
            comparison = sentiment_repo.get_comparison(run_id)

            # 概览指标
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("产品数", len(matrix_df))
            c2.metric("有痛点", sum(1 for _, r in matrix_df.iterrows() if r.get("核心痛点1")))
            c3.metric("共同痛点", len(comparison.get("common_pain_points", [])) if comparison else 0)
            c4.metric("洞察数", len(comparison.get("insights", [])) if comparison else 0)

            divider()

            # 矩阵表格 - 带颜色标记
            section_header("对比矩阵")

            # 显示核心列
            display_cols = ["ASIN", "品牌", "标题", "价格", "评分", "评论数",
                           "核心痛点1", "核心痛点2", "好评主题1", "整体评价"]
            available = [c for c in display_cols if c in matrix_df.columns]
            display_df = matrix_df[available]

            st.dataframe(
                display_df, use_container_width=True, hide_index=True,
                height=min(600, 50 + len(display_df) * 40),
            )

            divider()

            # 下载区
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                tmp_dir = Path(tempfile.mkdtemp())
                excel_path = write_competitive_excel(matrix_df, sentiment_data, comparison, tmp_dir / "matrix.xlsx")
                with open(excel_path, "rb") as f:
                    st.download_button(
                        "下载完整 Excel 报告",
                        data=f.read(),
                        file_name="competitive_matrix.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

finally:
    session.close()
