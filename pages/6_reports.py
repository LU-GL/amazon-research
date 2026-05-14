import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.db.engine import init_db, get_session
from src.db.repositories import AnalysisRunRepo, SentimentRepo
from src.analysis.competitive_matrix import build_competitive_matrix, load_listings_from_db
from src.report.excel_writer import write_competitive_excel
from src.report.pptx_writer import write_market_research_ppt
from src.ui.theme import inject_global_css, section_header, divider, COLORS

st.set_page_config(page_title="报告下载", layout="wide")
inject_global_css()

section_header("报告下载", "生成竞品矩阵Excel和市调PPT报告")

divider()

session = get_session()
try:
    run_repo = AnalysisRunRepo(session)
    runs = [r for r in run_repo.list_recent(50) if r.status == "completed"]

    if not runs:
        st.warning("暂无已完成的分析。请先运行评论分析。")
    else:
        run_options = {f"#{r.id} | {r.category or r.run_type} | {r.created_at.strftime('%m-%d %H:%M') if r.created_at else '-'}": r for r in runs}
        selected_label = st.selectbox("选择分析批次", list(run_options.keys()))
        run = run_options[selected_label]

        sentiment_repo = SentimentRepo(session)
        sentiment_data = sentiment_repo.to_asin_analyses_dict(run.id)
        comparison = sentiment_repo.get_comparison(run.id)
        listing_data = load_listings_from_db(session)
        matrix_df = build_competitive_matrix(listing_data, sentiment_data)

        st.markdown(f"""
        <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-radius:12px;padding:20px 24px;margin:16px 0;">
            <span style="color:#95A5A6;">批次</span>
            <span style="color:#E67E22;font-weight:700;margin-left:8px;">Run #{run.id}</span>
            <span style="color:#DEE2E6;margin-left:16px;">|</span>
            <span style="color:#2C3E50;margin-left:16px;">{len(sentiment_data)} 个ASIN</span>
            <span style="color:#DEE2E6;margin-left:16px;">|</span>
            <span style="color:#2C3E50;margin-left:16px;">{len(matrix_df.columns)} 个维度</span>
        </div>
        """, unsafe_allow_html=True)

        divider()

        col_excel, col_pptx = st.columns(2)

        with col_excel:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-radius:16px;padding:32px;text-align:center;min-height:260px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                <div style="font-size:3rem;margin-bottom:12px;"></div>
                <h3 style="margin:8px 0;color:#2C3E50;">竞品矩阵 Excel</h3>
                <p style="color:#5D6D7E;font-size:0.9rem;">5个Sheet：竞品矩阵 / 痛点分析 / 好评分析 / 机会点 / 原始数据</p>
                <div style="margin-top:16px;">
                    <span style="background:#D5F5E3;color:#27AE60;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;">.xlsx</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")
            tmp_dir = Path(tempfile.mkdtemp())
            excel_path = write_competitive_excel(matrix_df, sentiment_data, comparison, tmp_dir / "matrix.xlsx")
            with open(excel_path, "rb") as f:
                st.download_button(
                    "下载 Excel 报告",
                    data=f.read(),
                    file_name=f"competitive_matrix_run{run.id}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

        with col_pptx:
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-radius:16px;padding:32px;text-align:center;min-height:260px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                <div style="font-size:3rem;margin-bottom:12px;"></div>
                <h3 style="margin:8px 0;color:#2C3E50;">市调报告 PPT</h3>
                <p style="color:#5D6D7E;font-size:0.9rem;">9页幻灯片：封面 / 概览 / 矩阵 / 痛点 / 好评 / 机会 / 建议 / 附录</p>
                <div style="margin-top:16px;">
                    <span style="background:#D6EAF8;color:#2980B9;padding:4px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;">.pptx</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("")
            category = run.category or ""
            pptx_path = write_market_research_ppt(matrix_df, sentiment_data, comparison, category, tmp_dir / "report.pptx")
            with open(pptx_path, "rb") as f:
                st.download_button(
                    "下载 PPT 报告",
                    data=f.read(),
                    file_name=f"market_research_run{run.id}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )

finally:
    session.close()
