import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from src.db.engine import init_db, get_session
from src.db.repositories import ProductRepo, ReviewRepo
from src.sentiment.csv_parser import load_review_file, split_reviews_by_asin
from src.ui.theme import inject_global_css, section_header, divider, badge

st.set_page_config(page_title="数据导入", layout="wide")
inject_global_css()

section_header("数据导入", "上传卖家精灵CSV/Excel或导入已有listing数据")

divider()

# === 文件上传 ===
st.markdown(f"""
<div style="margin-bottom:16px;">
    <h3>上传评论数据文件</h3>
    <p style="color:#5D6D7E;margin-top:-8px;">支持 CSV / Excel (.xlsx / .xls) 格式，自动识别编码和列名</p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "拖拽或点击上传文件",
    type=["csv", "xlsx", "xls"],
    label_visibility="collapsed",
)

if uploaded_file:
    import tempfile
    tmp_dir = tempfile.mkdtemp()
    tmp_path = Path(tmp_dir) / uploaded_file.name
    with open(tmp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    try:
        df = load_review_file(tmp_path)
        asin_groups = split_reviews_by_asin(df)

        c1, c2, c3 = st.columns(3)
        c1.metric("总评论数", len(df))
        c2.metric("ASIN数量", len(asin_groups))
        c3.metric("文件大小", f"{uploaded_file.size / 1024:.1f} KB")

        divider()

        # 预览
        section_header("数据预览")
        st.dataframe(df.head(20), use_container_width=True, height=350)

        # ASIN统计
        section_header("ASIN 评论统计")
        asin_stats = [{"ASIN": a, "评论数": len(g)} for a, g in asin_groups.items()]
        st.dataframe(pd.DataFrame(asin_stats), use_container_width=True, hide_index=True)

        # 导入选区
        section_header("选择导入范围")
        all_asins = list(asin_groups.keys())
        selected_asins = st.multiselect("选择要导入的ASIN", all_asins, default=all_asins)

        col_import, col_analyze = st.columns(2)

        with col_import:
            if st.button("导入到数据库", type="primary", disabled=len(selected_asins) == 0):
                session = get_session()
                try:
                    product_repo = ProductRepo(session)
                    review_repo = ReviewRepo(session)
                    total_imported = 0

                    progress = st.progress(0)
                    status = st.empty()

                    for i, asin in enumerate(selected_asins):
                        status.text(f"导入中: {asin} ({i+1}/{len(selected_asins)})")
                        product = product_repo.get_or_create(asin)
                        count = review_repo.import_from_dataframe(product.id, asin_groups[asin])
                        total_imported += count
                        progress.progress((i + 1) / len(selected_asins))

                    session.commit()
                    status.empty()
                    st.success(f"导入完成: **{total_imported}** 条评论, **{len(selected_asins)}** 个ASIN")
                    st.session_state["imported_asins"] = selected_asins
                except Exception as e:
                    session.rollback()
                    st.error(f"导入失败: {e}")
                finally:
                    session.close()

        with col_analyze:
            imported = st.session_state.get("imported_asins", [])
            if imported:
                st.markdown(f"""
                <div style="background:#D5F5E3;border:1px solid #27AE6055;border-radius:8px;padding:14px 18px;margin-top:28px;">
                    <span style="color:#27AE60;font-weight:600;">已导入 {len(imported)} 个ASIN</span>
                </div>
                """, unsafe_allow_html=True)
                if st.button("开始分析", type="primary"):
                    st.switch_page("pages/3_sentiment_analysis.py")

    except Exception as e:
        st.error(f"文件解析失败: {e}")

divider()

# === JSON导入 ===
section_header("导入已有Listing数据", "从 data/raw_listings/ 目录读取JSON文件")
if st.button("导入 Listing JSON"):
    session = get_session()
    try:
        from src.config import RAW_LISTINGS_DIR
        product_repo = ProductRepo(session)
        count = product_repo.import_listings_from_dir(RAW_LISTINGS_DIR)
        if count > 0:
            st.success(f"成功导入 **{count}** 个产品listing")
        else:
            st.warning("未找到可导入的JSON文件")
    except Exception as e:
        st.error(f"导入失败: {e}")
    finally:
        session.close()
