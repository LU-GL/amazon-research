import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.db.engine import init_db, get_session
from src.db.repositories import AnalysisRunRepo, SentimentRepo
from src.ui.theme import inject_global_css, section_header, divider, PLOTLY_TEMPLATE, COLORS

st.set_page_config(page_title="洞察分析", layout="wide")
inject_global_css()

section_header("洞察分析", "评论情感数据可视化")

divider()

session = get_session()
try:
    run_repo = AnalysisRunRepo(session)
    runs = [r for r in run_repo.list_recent(50) if r.status == "completed"]

    if not runs:
        st.warning("暂无已完成的分析。")
    else:
        run_options = {f"#{r.id} | {r.category or r.run_type} | {r.created_at.strftime('%m-%d %H:%M') if r.created_at else '-'}": r.id for r in runs}
        selected_label = st.selectbox("分析批次", list(run_options.keys()))
        run_id = run_options[selected_label]

        sentiment_repo = SentimentRepo(session)
        sentiment_data = sentiment_repo.to_asin_analyses_dict(run_id)
        comparison = sentiment_repo.get_comparison(run_id)

        # === 顶部汇总 ===
        total_pain = sum(len(a.get("pain_points", [])) for a in sentiment_data.values())
        total_praise = sum(len(a.get("praise_points", [])) for a in sentiment_data.values())
        total_feature = sum(len(a.get("feature_requests", [])) for a in sentiment_data.values())

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("痛点主题", total_pain)
        c2.metric("好评主题", total_praise)
        c3.metric("功能需求", total_feature)
        c4.metric("分析ASIN", len(sentiment_data))

        divider()

        tab_pain, tab_praise, tab_feature, tab_compare = st.tabs([
            "痛点分析", "好评分析", "功能需求", "跨ASIN对比"
        ])

        # === 痛点分析 ===
        with tab_pain:
            pain_rows = []
            for asin, analysis in sentiment_data.items():
                for pp in analysis.get("pain_points", []):
                    pain_rows.append({
                        "ASIN": asin, "主题": pp["theme"],
                        "频次": pp.get("frequency", 0),
                        "严重度": pp.get("severity", "medium"),
                    })
            if pain_rows:
                pain_df = pd.DataFrame(pain_rows)
                theme_agg = pain_df.groupby("主题")["频次"].sum().sort_values(ascending=False).head(12)

                col_chart, col_table = st.columns([1, 1])
                with col_chart:
                    st.markdown("#### 痛点频次 TOP 12")
                    fig = go.Figure(go.Bar(
                        x=theme_agg.values, y=theme_agg.index, orientation="h",
                        marker_color=COLORS["pain"],
                        text=theme_agg.values, textposition="outside",
                    ))
                    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
                    fig.update_layout(height=max(350, len(theme_agg) * 32), margin={"t": 10, "b": 10, "l": 10, "r": 40})
                    fig.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig, use_container_width=True)

                with col_table:
                    st.markdown("#### 痛点明细")
                    # 按严重度着色
                    def severity_color(row):
                        color = {"high": COLORS["danger"], "medium": COLORS["warning"], "low": COLORS["info"]}
                        c = color.get(row["严重度"], COLORS["text_muted"])
                        return f'<span style="color:{c};font-weight:600;">{row["严重度"]}</span>'

                    display = pain_df.sort_values("频次", ascending=False).head(15).copy()
                    display["严重度"] = display.apply(severity_color, axis=1)
                    st.markdown(display.to_html(escape=False, index=False), unsafe_allow_html=True)

                # 每个ASIN的痛点雷达图
                st.markdown("#### 各ASIN痛点分布")
                top_themes = theme_agg.head(8).index.tolist()
                radar_data = []
                for asin, analysis in sentiment_data.items():
                    pain_map = {pp["theme"]: pp.get("frequency", 0) for pp in analysis.get("pain_points", [])}
                    for theme in top_themes:
                        radar_data.append({"ASIN": asin, "主题": theme, "频次": pain_map.get(theme, 0)})

                if radar_data:
                    radar_df = pd.DataFrame(radar_data)
                    fig_heat = px.density_heatmap(
                        radar_df, x="主题", y="ASIN", z="频次",
                        color_continuous_scale=["#F8F9FA", "#E67E22"],
                        template="plotly_white",
                    )
                    fig_heat.update_layout(**PLOTLY_TEMPLATE["layout"])
                    fig_heat.update_layout(height=max(200, len(sentiment_data) * 40 + 80))
                    st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("无痛点数据")

        # === 好评分析 ===
        with tab_praise:
            praise_rows = []
            for asin, analysis in sentiment_data.items():
                for pp in analysis.get("praise_points", []):
                    praise_rows.append({"ASIN": asin, "主题": pp["theme"], "频次": pp.get("frequency", 0)})
            if praise_rows:
                praise_df = pd.DataFrame(praise_rows)
                theme_agg = praise_df.groupby("主题")["频次"].sum().sort_values(ascending=False).head(12)

                col_chart, col_table = st.columns([1, 1])
                with col_chart:
                    st.markdown("#### 好评主题 TOP 12")
                    fig = go.Figure(go.Bar(
                        x=theme_agg.values, y=theme_agg.index, orientation="h",
                        marker_color=COLORS["praise"],
                        text=theme_agg.values, textposition="outside",
                    ))
                    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
                    fig.update_layout(height=max(350, len(theme_agg) * 32), margin={"t": 10, "b": 10, "l": 10, "r": 40})
                    fig.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig, use_container_width=True)

                with col_table:
                    st.markdown("#### 好评明细")
                    st.dataframe(praise_df.sort_values("频次", ascending=False).head(15),
                                 use_container_width=True, hide_index=True)

                # 好评/痛点对比饼图
                st.markdown("#### 好评 vs 痛点占比")
                fig_pie = go.Figure(data=[
                    go.Pie(labels=["好评主题", "痛点主题", "功能需求"],
                           values=[total_praise, total_pain, total_feature],
                           marker=dict(colors=[COLORS["praise"], COLORS["pain"], COLORS["feature"]]),
                           hole=0.5,
                           textinfo="label+percent",
                           textfont=dict(size=14)),
                ])
                fig_pie.update_layout(**PLOTLY_TEMPLATE["layout"])
                fig_pie.update_layout(height=350)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("无好评数据")

        # === 功能需求 ===
        with tab_feature:
            fr_rows, qi_rows = [], []
            for asin, analysis in sentiment_data.items():
                for fr in analysis.get("feature_requests", []):
                    fr_rows.append({"ASIN": asin, "主题": fr["theme"], "频次": fr.get("frequency", 0), "类型": "功能需求"})
                for qi in analysis.get("quality_issues", []):
                    qi_rows.append({"ASIN": asin, "主题": qi["theme"], "频次": qi.get("frequency", 0), "严重度": qi.get("severity", ""), "类型": "质量问题"})

            if fr_rows or qi_rows:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 功能需求")
                    if fr_rows:
                        fr_df = pd.DataFrame(fr_rows)
                        theme_agg = fr_df.groupby("主题")["频次"].sum().sort_values(ascending=False).head(8)
                        fig = go.Figure(go.Bar(
                            x=theme_agg.values, y=theme_agg.index, orientation="h",
                            marker_color=COLORS["feature"],
                            text=theme_agg.values, textposition="outside",
                        ))
                        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
                        fig.update_layout(height=max(300, len(theme_agg) * 35), margin={"t": 10, "b": 10, "l": 10, "r": 40})
                        fig.update_yaxes(autorange="reversed")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("无功能需求数据")

                with col2:
                    st.markdown("#### 质量问题")
                    if qi_rows:
                        qi_df = pd.DataFrame(qi_rows).sort_values("频次", ascending=False).head(10)
                        st.dataframe(qi_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("无质量问题数据")

                if fr_rows:
                    st.markdown("#### 功能需求明细")
                    st.dataframe(pd.DataFrame(fr_rows).sort_values("频次", ascending=False).head(15),
                                 use_container_width=True, hide_index=True)
            else:
                st.info("无功能需求/质量问题数据")

        # === 跨ASIN对比 ===
        with tab_compare:
            if comparison:
                if comparison.get("insights"):
                    st.markdown("#### 关键洞察")
                    for insight in comparison["insights"]:
                        st.markdown(f"""
                        <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-left:3px solid #E67E22;
                             border-radius:0 8px 8px 0;padding:14px 18px;margin:8px 0;">
                            {insight}
                        </div>
                        """, unsafe_allow_html=True)

                col_left, col_right = st.columns(2)

                with col_left:
                    st.markdown("#### 共同痛点")
                    if comparison.get("common_pain_points"):
                        cp_data = [{"主题": p["theme"], "频次": p["frequency"],
                                    "涉及ASIN数": len(p.get("asins", [])),
                                    "严重度": p.get("severity", "")}
                                   for p in comparison["common_pain_points"][:10]]
                        st.dataframe(pd.DataFrame(cp_data), use_container_width=True, hide_index=True)
                    else:
                        st.info("无共同痛点")

                with col_right:
                    st.markdown("#### 差异化痛点")
                    if comparison.get("unique_pain_points"):
                        up_data = [{"主题": p["theme"], "频次": p["frequency"],
                                    "ASIN": p["asins"][0] if p.get("asins") else ""}
                                   for p in comparison["unique_pain_points"][:10]]
                        st.dataframe(pd.DataFrame(up_data), use_container_width=True, hide_index=True)
                    else:
                        st.info("无差异化痛点")

                if comparison.get("feature_opportunities"):
                    st.markdown("#### 功能需求机会")
                    fo_data = [{"主题": f["theme"], "频次": f["frequency"],
                                "涉及ASIN数": len(f.get("asins", []))}
                               for f in comparison["feature_opportunities"][:10]]
                    fo_df = pd.DataFrame(fo_data)
                    fig = go.Figure(go.Bar(
                        x=fo_df["频次"], y=fo_df["主题"], orientation="h",
                        marker_color=COLORS["feature"],
                        text=fo_df["频次"], textposition="outside",
                    ))
                    fig.update_layout(**PLOTLY_TEMPLATE["layout"])
                    fig.update_layout(height=max(300, len(fo_df) * 35), margin={"t": 10, "b": 10})
                    fig.update_yaxes(autorange="reversed")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("无对比数据")

finally:
    session.close()
