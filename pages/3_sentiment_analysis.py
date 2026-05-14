import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.db.engine import init_db, get_session
from src.db.repositories import ProductRepo, ReviewRepo, AnalysisRunRepo
from src.sentiment.analyzer import analyze_all_reviews
from src.sentiment.aggregator import compare_across_asins, save_sentiment_to_db
from src.ui.theme import inject_global_css, section_header, divider, metric_card, COLORS

st.set_page_config(page_title="评论分析", layout="wide")
inject_global_css()

section_header("评论情感分析", "Claude AI 深度挖掘用户评论痛点与机会")

divider()

session = get_session()
try:
    product_repo = ProductRepo(session)
    review_repo = ReviewRepo(session)

    products = product_repo.list_all()
    products_with_reviews = [(p, review_repo.count_by_product(p.id)) for p in products if review_repo.count_by_product(p.id) > 0]

    if not products_with_reviews:
        st.warning("暂无评论数据。请先在「数据导入」页面上传CSV。")
    else:
        # 配置区
        col_config, col_info = st.columns([2, 1])

        with col_config:
            st.markdown("### 分析配置")
            options = {f"{p.asin} ({count}条)": p for p, count in products_with_reviews}
            selected_labels = st.multiselect("选择要分析的产品", list(options.keys()), default=list(options.keys()))
            category = st.text_input("产品品类（可选）", placeholder="如：宠物用品、厨房工具...")

        with col_info:
            st.markdown("### 信息")
            selected_count = len(selected_labels)
            total_reviews = sum(count for label, (p, count) in zip(options.keys(), products_with_reviews) if label in selected_labels)
            st.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-radius:12px;padding:20px;">
                <div style="color:#95A5A6;font-size:0.85rem;">待分析</div>
                <div style="font-size:1.8rem;font-weight:700;color:#E67E22;margin:8px 0;">{selected_count} <span style="font-size:0.9rem;color:#95A5A6;">个ASIN</span></div>
                <div style="color:#5D6D7E;font-size:0.85rem;">共 {total_reviews} 条评论</div>
                <div style="color:#95A5A6;font-size:0.8rem;margin-top:12px;">预计消耗 ~{total_reviews // 20 + selected_count} 次API调用</div>
            </div>
            """, unsafe_allow_html=True)

        selected_products = [options[label] for label in selected_labels]

        if st.button("开始分析", type="primary", disabled=len(selected_products) == 0):
            run_repo = AnalysisRunRepo(session)
            run = run_repo.create("sentiment", category)
            run_repo.start(run.id)
            session.commit()

            progress = st.progress(0)
            log_container = st.container()

            asin_analyses = {}
            total = len(selected_products)

            for i, product in enumerate(selected_products):
                with log_container:
                    st.markdown(f"""
                    <div style="background:#FEF9E7;border-left:3px solid #E67E22;padding:12px 16px;margin:8px 0;border-radius:0 8px 8px 0;">
                        <span style="color:#E67E22;font-weight:600;">[{i+1}/{total}]</span>
                        <span style="color:#2C3E50;"> {product.asin}</span>
                        <span style="color:#95A5A6;font-size:0.85rem;margin-left:8px;">分析中...</span>
                    </div>
                    """, unsafe_allow_html=True)

                reviews_df = review_repo.to_dataframe(product.id)
                if reviews_df.empty:
                    continue

                try:
                    analysis = analyze_all_reviews(product.asin, reviews_df, category)
                    asin_analyses[product.asin] = analysis

                    pain_count = len(analysis.get("pain_points", []))
                    praise_count = len(analysis.get("praise_points", []))
                    log_container.markdown(f"""
                    <div style="background:#D5F5E3;border-left:3px solid #27AE60;padding:12px 16px;margin:8px 0;border-radius:0 8px 8px 0;">
                        <span style="color:#27AE60;font-weight:600;">{product.asin}</span>
                        <span style="color:#5D6D7E;">完成: {pain_count}个痛点, {praise_count}个好评</span>
                    </div>
                    """, unsafe_allow_html=True)
                except Exception as e:
                    log_container.error(f"{product.asin}: 分析失败 - {e}")

                progress.progress((i + 1) / total)
                if i < total - 1:
                    time.sleep(2)

            # 跨ASIN对比 + 保存
            if asin_analyses:
                with st.spinner("生成跨ASIN对比..."):
                    comparison = compare_across_asins(asin_analyses)
                    save_sentiment_to_db(asin_analyses, comparison, run.id)
                    run_repo.complete(run.id, asins_analyzed=len(asin_analyses),
                                      total_reviews=sum(a.get("total_reviews", 0) for a in asin_analyses.values()))
                    session.commit()

                progress.progress(1.0)
                divider()

                # 结果摘要
                section_header("分析完成", f"Run #{run.id}")
                c1, c2, c3, c4 = st.columns(4)
                metric_card(len(asin_analyses), "分析ASIN", c1)
                metric_card(len(comparison.get("common_pain_points", [])), "共同痛点", c2)
                metric_card(len(comparison.get("feature_opportunities", [])), "功能需求", c3)
                metric_card(len(comparison.get("insights", [])), "关键洞察", c4)

                if comparison.get("insights"):
                    st.markdown("### 关键洞察")
                    for insight in comparison["insights"]:
                        st.markdown(f"""
                        <div style="background:#FFFFFF;border:1px solid #DEE2E6;border-radius:8px;padding:12px 16px;margin:6px 0;">
                            {insight}
                        </div>
                        """, unsafe_allow_html=True)

                st.success("结果已保存到数据库。可前往「竞品矩阵」或「洞察分析」查看。")

finally:
    session.close()
