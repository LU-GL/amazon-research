"""全局UI主题和共享组件 - 浅色高对比度主题。"""

import streamlit as st

# === 设计令牌 - 浅色主题 ===
COLORS = {
    "bg_page": "#F8F9FA",
    "bg_card": "#FFFFFF",
    "bg_card_hover": "#F1F3F5",
    "bg_sidebar": "#FFFFFF",
    "accent": "#E67E22",
    "accent_dim": "#D35400",
    "success": "#27AE60",
    "danger": "#E74C3C",
    "warning": "#F39C12",
    "info": "#2980B9",
    "text_primary": "#2C3E50",
    "text_secondary": "#5D6D7E",
    "text_muted": "#95A5A6",
    "border": "#DEE2E6",
    "border_accent": "#E67E22",
    "gradient_start": "#E67E22",
    "gradient_end": "#D35400",
    "pain": "#E74C3C",
    "praise": "#27AE60",
    "feature": "#2980B9",
    "quality": "#E67E22",
}

PLOTLY_TEMPLATE = {
    "layout": {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"family": "'Noto Sans SC', 'Microsoft YaHei', sans-serif", "color": COLORS["text_primary"], "size": 13},
        "colorway": [COLORS["accent"], COLORS["success"], COLORS["info"], COLORS["danger"],
                     "#8E44AD", "#1ABC9C", "#E74C3C", "#3498DB"],
        "xaxis": {"gridcolor": "#ECF0F1", "zerolinecolor": "#ECF0F1"},
        "yaxis": {"gridcolor": "#ECF0F1", "zerolinecolor": "#ECF0F1"},
        "margin": {"t": 40, "b": 40, "l": 10, "r": 10},
    }
}


def inject_global_css():
    """注入全局自定义CSS。"""
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

    /* 强制浅色基础 */
    [data-testid="stAppViewContainer"],
    .stApp,
    .main {{
        background: {COLORS["bg_page"]} !important;
        color: {COLORS["text_primary"]} !important;
    }}

    /* 全局文字覆盖 */
    .stApp p, .stApp span, .stApp li, .stApp td, .stApp th,
    .stApp label, .stApp div, .stApp .stMarkdown {{
        color: {COLORS["text_primary"]} !important;
    }}
    .stApp .stMarkdown p {{
        color: {COLORS["text_secondary"]} !important;
    }}

    /* 侧边栏 */
    section[data-testid="stSidebar"] {{
        background: {COLORS["bg_sidebar"]} !important;
        border-right: 1px solid {COLORS["border"]};
    }}
    section[data-testid="stSidebar"] * {{
        color: {COLORS["text_primary"]} !important;
    }}
    section[data-testid="stSidebar"] .stPageLink label {{
        color: {COLORS["text_secondary"]} !important;
    }}
    section[data-testid="stSidebar"] .stPageLink label:hover {{
        color: {COLORS["accent"]} !important;
    }}

    /* 指标卡片 */
    .metric-card {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        transition: all 0.2s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }}
    .metric-card:hover {{
        border-color: {COLORS["accent"]};
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    .metric-value {{
        font-size: 2.2rem;
        font-weight: 700;
        color: {COLORS["accent"]} !important;
        line-height: 1.2;
    }}
    .metric-label {{
        font-size: 0.85rem;
        color: {COLORS["text_muted"]} !important;
        margin-top: 6px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    /* 标题 */
    h1, h2, h3 {{
        color: {COLORS["text_primary"]} !important;
        font-weight: 700 !important;
    }}

    /* 按钮 */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]});
        color: #FFFFFF !important;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 10px 28px;
        box-shadow: 0 2px 8px rgba(230,126,34,0.3);
    }}
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 16px rgba(230,126,34,0.4);
    }}
    .stButton > button {{
        color: {COLORS["text_primary"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 8px !important;
    }}

    /* 输入框 */
    .stTextInput input, .stSelectbox, .stMultiSelect {{
        color: {COLORS["text_primary"]} !important;
    }}

    /* DataFrame */
    .stDataFrame {{
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid {COLORS["border"]};
    }}

    /* 进度条 */
    .stProgress > div > div > div > div {{
        background: linear-gradient(90deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]});
    }}

    /* Tab */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        border-bottom: 2px solid {COLORS["border"]};
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        color: {COLORS["text_muted"]} !important;
        font-weight: 500;
    }}
    .stTabs [aria-selected="true"] {{
        color: {COLORS["accent"]} !important;
        border-bottom: 2px solid {COLORS["accent"]};
        font-weight: 600;
    }}

    /* 文件上传 */
    .stFileUploader {{
        border: 2px dashed {COLORS["border"]} !important;
        border-radius: 12px !important;
        background: {COLORS["bg_card"]} !important;
    }}
    .stFileUploader:hover {{
        border-color: {COLORS["accent"]} !important;
    }}

    /* Expander */
    .stExpander {{
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 8px !important;
        background: {COLORS["bg_card"]} !important;
    }}

    /* 下载按钮 */
    .stDownloadButton > button {{
        background: {COLORS["bg_card"]} !important;
        border: 1px solid {COLORS["border"]} !important;
        border-radius: 8px !important;
        color: {COLORS["text_primary"]} !important;
        font-weight: 500;
    }}
    .stDownloadButton > button:hover {{
        border-color: {COLORS["accent"]} !important;
        color: {COLORS["accent"]} !important;
    }}

    /* 消息提示 */
    .stSuccess {{
        background: #D5F5E3 !important;
        border: 1px solid {COLORS["success"]}55 !important;
        border-radius: 8px !important;
    }}
    .stSuccess * {{ color: #1E8449 !important; }}
    .stError {{
        background: #FADBD8 !important;
        border: 1px solid {COLORS["danger"]}55 !important;
        border-radius: 8px !important;
    }}
    .stError * {{ color: #922B21 !important; }}
    .stWarning {{
        background: #FEF9E7 !important;
        border: 1px solid {COLORS["warning"]}55 !important;
        border-radius: 8px !important;
    }}
    .stWarning * {{ color: #7D6608 !important; }}
    .stInfo {{
        background: #D6EAF8 !important;
        border: 1px solid {COLORS["info"]}55 !important;
        border-radius: 8px !important;
    }}
    .stInfo * {{ color: #1B4F72 !important; }}

    /* Streamlit指标 */
    [data-testid="stMetric"] {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 10px;
        padding: 16px;
    }}
    [data-testid="stMetricValue"] {{
        color: {COLORS["text_primary"]} !important;
        font-weight: 700 !important;
    }}
    [data-testid="stMetricLabel"] {{
        color: {COLORS["text_secondary"]} !important;
    }}

    /* 隐藏默认元素 */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)


def metric_card(value, label, col=None):
    """渲染指标卡片。"""
    target = col if col else st
    target.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def section_header(title, subtitle=None):
    """渲染带副标题的区块头。"""
    sub = f'<p style="color:{COLORS["text_muted"]};margin-top:-8px;font-size:0.9rem;">{subtitle}</p>' if subtitle else ""
    st.markdown(f"<h2 style='margin-bottom:4px;'>{title}</h2>{sub}", unsafe_allow_html=True)


def divider():
    """渲染分隔线。"""
    st.markdown(f"<hr style='border-color:{COLORS['border']};margin:24px 0;'>", unsafe_allow_html=True)


def badge(text, color="accent"):
    """渲染标签徽章。"""
    c = COLORS.get(color, color)
    return f'<span style="background:{c}22;color:{c};padding:2px 10px;border-radius:20px;font-size:0.8rem;font-weight:500;">{text}</span>'


def status_badge(status):
    """根据状态返回对应颜色的徽章。"""
    color_map = {
        "completed": COLORS["success"],
        "running": COLORS["info"],
        "pending": COLORS["warning"],
        "failed": COLORS["danger"],
    }
    c = color_map.get(status, COLORS["text_muted"])
    return f'<span style="background:{c}18;color:{c};padding:3px 12px;border-radius:20px;font-size:0.8rem;font-weight:600;">{status}</span>'
