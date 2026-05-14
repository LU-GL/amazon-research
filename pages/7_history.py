import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from src.db.engine import init_db, get_session
from src.db.repositories import AnalysisRunRepo, SentimentRepo
from src.ui.theme import inject_global_css, section_header, divider, status_badge, COLORS, metric_card

st.set_page_config(page_title="历史记录", layout="wide")
inject_global_css()

section_header("历史记录", "所有分析运行的完整记录")

divider()

session = get_session()
try:
    run_repo = AnalysisRunRepo(session)
    runs = run_repo.list_all()

    if not runs:
        st.info("暂无分析记录。")
    else:
        # 运行列表
        rows = []
        for r in runs:
            rows.append({
                "ID": r.id,
                "类型": r.run_type,
                "品类": r.category or "—",
                "状态": status_badge(r.status),
                "ASIN": r.asins_analyzed,
                "评论": r.total_reviews,
                "创建": r.created_at.strftime("%m-%d %H:%M") if r.created_at else "—",
                "完成": r.completed_at.strftime("%m-%d %H:%M") if r.completed_at else "—",
            })
        st.markdown(pd.DataFrame(rows).to_html(escape=False, index=False), unsafe_allow_html=True)

        divider()

        # 详情查看
        section_header("运行详情")
        run_ids = [r.id for r in runs]
        selected_id = st.selectbox("选择Run ID查看", run_ids)

        sentiment_repo = SentimentRepo(session)
        sentiment_data = sentiment_repo.to_asin_analyses_dict(selected_id)
        comparison = sentiment_repo.get_comparison(selected_id)

        if sentiment_data:
            # 汇总指标
            total_reviews = sum(a.get("total_reviews", 0) for a in sentiment_data.values())
            total_pain = sum(len(a.get("pain_points", [])) for a in sentiment_data.values())
            total_praise = sum(len(a.get("praise_points", [])) for a in sentiment_data.values())

            c1, c2, c3, c4 = st.columns(4)
            metric_card(len(sentiment_data), "ASIN数", c1)
            metric_card(total_reviews, "评论总数", c2)
            metric_card(total_pain, "痛点主题", c3)
            metric_card(total_praise, "好评主题", c4)

            st.markdown("")

            for asin, analysis in sentiment_data.items():
                summary = analysis.get("sentiment_summary", {})
                overall = summary.get("overall", "?")
                color = {"positive": COLORS["praise"], "negative": COLORS["pain"], "mixed": COLORS["warning"]}.get(overall, COLORS["text_muted"])

                with st.expander(f"{asin}  ·  {overall}  ·  {analysis.get('total_reviews', 0)}条评论"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("评论数", analysis.get("total_reviews", 0))
                    c2.metric("评分", summary.get("avg_rating", "—"))
                    c3.metric("整体", overall)

                    col_pain, col_praise = st.columns(2)
                    with col_pain:
                        if analysis.get("pain_points"):
                            st.markdown("**痛点**")
                            for pp in analysis["pain_points"][:5]:
                                sev = pp.get("severity", "")
                                sev_color = {"high": COLORS["danger"], "medium": COLORS["warning"], "low": COLORS["info"]}.get(sev, COLORS["text_muted"])
                                st.markdown(f'<div style="padding:4px 0;border-bottom:1px solid #DEE2E6;">'
                                            f'{pp["theme"]} <span style="color:{sev_color};font-size:0.8rem;">{sev} {pp.get("frequency", 0)}</span></div>',
                                            unsafe_allow_html=True)

                    with col_praise:
                        if analysis.get("praise_points"):
                            st.markdown("**好评**")
                            for pp in analysis["praise_points"][:5]:
                                st.markdown(f'<div style="padding:4px 0;border-bottom:1px solid #DEE2E6;">'
                                            f'{pp["theme"]} <span style="color:{COLORS["praise"]};font-size:0.8rem;">{pp.get("frequency", 0)}</span></div>',
                                            unsafe_allow_html=True)

                    if analysis.get("feature_requests"):
                        st.markdown("**功能需求**")
                        for fr in analysis["feature_requests"][:5]:
                            st.markdown(f'<div style="padding:4px 0;border-bottom:1px solid #DEE2E6;">'
                                        f'{fr["theme"]} <span style="color:{COLORS["feature"]};font-size:0.8rem;">{fr.get("frequency", 0)}</span></div>',
                                        unsafe_allow_html=True)
        else:
            st.info("该批次无分析数据。")

finally:
    session.close()
