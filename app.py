
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# ============== Optional: Akshare for China A-shares ==================
# We try to import akshare. If not available (or fails on Streamlit Cloud),
# the app will still run and allow CSV upload or manual ticker input.
try:
    import akshare as ak
    AK_AVAILABLE = True
except Exception as e:
    AK_AVAILABLE = False

st.set_page_config(page_title="量化选股工具（Demo）", layout="wide")

st.title("📈 量化选股工具（Demo）")
st.caption("基于简化的打分模型：成交量缩放、均线形态、突破、套牢盘、事件/题材（示意）+ 负面因子")

with st.expander("👀 模型说明 / Scoring Logic"):
    st.markdown("""
- **基础得分 S**（0-100 量纲）：
  - 成交量缩放（0-20）
  - 均线形态（0-20）：MA20 > MA60加分
  - 20日新高突破（0-15）
  - 站上MA60（上方套牢盘）（0-10）
  - 形态/枢轴（简化实现）（0-15）
- **Δ（0-10）**：题材/事件（本 Demo 用占位逻辑，可接入公告/新闻/热点板块）
- **P 负面因子**：未收复前高、形态差等（本 Demo 实现一个“距60日最高价过远”的扣分）
- **综合分**：`Total = S + Δ * 2.7 - P`
- ⚠️ 演示用途，不构成投资建议。可按需替换为你的正式规则与数据源。
""")

# ===================== Sidebar controls =====================
st.sidebar.header("参数设置")
limit = st.sidebar.slider("测试股票数量（仅为演示用途）", 20, 300, 80, step=10)
days_back = st.sidebar.slider("回溯天数", 60, 250, 120, step=10)
end_date = datetime.today().strftime("%Y%m%d")
start_date = (datetime.today() - timedelta(days=days_back)).strftime("%Y%m%d")

use_ak = st.sidebar.checkbox("使用 Akshare 获取A股（若不可用请取消勾选）", value=True if AK_AVAILABLE else False)
custom_codes = st.sidebar.text_area("自定义股票代码列表（逗号分隔）。A股示例：000001,600000；或留空使用自动列表。")

uploaded = st.sidebar.file_uploader("或上传历史行情CSV（含列：date, open, high, low, close, volume）", type=["csv"])

# ===================== Data Helpers =====================
@st.cache_data(show_spinner=False, ttl=3600)
def get_stock_list(limit):
    if use_ak and AK_AVAILABLE:
        df = ak.stock_info_a_code_name()
        codes = df["code"].astype(str).tolist()
        return codes[:limit]
    else:
        # Fallback: provide a small demo list (ETF/US tickers won't use akshare)
        demo = ["000001", "600000", "600519", "000651", "000333", "601318", "600036", "600104",
                "002415", "300750", "000002", "601398", "601988", "601939", "000858", "600030",
                "600009", "600028", "600837", "600048", "600585", "601633", "601888", "002475",
                "000726", "601012", "601899", "002352", "603288", "600196"]
        return demo[:limit]

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_hist(code, start_date, end_date):
    if uploaded is not None:
        df = pd.read_csv(uploaded)
        df = df.rename(columns={
            "日期": "date", "收盘": "close", "开盘": "open",
            "最高": "high", "最低": "low", "成交量": "volume"
        })
        df["date"] = pd.to_datetime(df["date"]).dt.date
        return df

    if use_ak and AK_AVAILABLE:
        try:
            df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                    start_date=start_date, end_date=end_date, adjust="qfq")
            df = df.rename(columns={"日期": "date", "收盘": "close", "开盘": "open",
                                    "最高": "high", "最低": "low", "成交量": "volume"})
            df["date"] = pd.to_datetime(df["date"]).dt.date
            return df
        except Exception as e:
            return None
    # If no data source, return None
    return None

def compute_scores(df: pd.DataFrame):
    df = df.copy()
    df["ma10"] = df["close"].rolling(10).mean()
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma60"] = df["close"].rolling(60).mean()
    score = 0
    delta = 0
    penalty = 0

    # 成交量缩放（近1日 vs 近5日均量）
    if len(df) >= 5 and df["volume"].iloc[-5:].mean() > 0:
        vol_ratio = df["volume"].iloc[-1] / df["volume"].iloc[-5:].mean()
        if vol_ratio < 0.5:
            score += 20
        elif vol_ratio < 0.8:
            score += 10

    # 均线形态（MA20 > MA60）
    if not np.isnan(df["ma20"].iloc[-1]) and not np.isnan(df["ma60"].iloc[-1]):
        if df["ma20"].iloc[-1] > df["ma60"].iloc[-1]:
            score += 15
        else:
            score += 5

    # 突破：收盘创近20日新高
    if len(df) >= 20:
        if df["close"].iloc[-1] > df["high"].iloc[-20:-1].max():
            score += 15

    # 站上MA60（视为上方套牢压力减轻）
    if not np.isnan(df["ma60"].iloc[-1]):
        if df["close"].iloc[-1] >= df["ma60"].iloc[-1]:
            score += 10

    # 形态/枢轴（简化：MA10/20/60 多头排列则加）
    if not any(np.isnan([df["ma10"].iloc[-1], df["ma20"].iloc[-1], df["ma60"].iloc[-1]])):
        if df["ma10"].iloc[-1] > df["ma20"].iloc[-1] > df["ma60"].iloc[-1]:
            score += 15

    # 事件/题材（占位：若近10日涨幅位于样本上分位，则加分）
    if len(df) >= 10:
        ret10 = df["close"].iloc[-1] / df["close"].iloc[-10] - 1
        if ret10 > 0.08:
            delta += 6
        if ret10 > 0.15:
            delta += 4  # up to 10

    # 负面因子：距离60日最高价过远
    if len(df) >= 60:
        last_high = df["high"].iloc[-60:-1].max()
        if last_high > 0:
            ratio = df["close"].iloc[-1] / last_high
            if ratio < 0.9:
                penalty += 15
            elif ratio < 0.97:
                penalty += 5

    total = score + delta * 2.7 - penalty
    return score, delta, penalty, total

def score_one_code(code, start_date, end_date):
    df = fetch_hist(code, start_date, end_date)
    if df is None or df.empty:
        return None
    score, delta, penalty, total = compute_scores(df)
    return {
        "code": code,
        "close": float(df["close"].iloc[-1]),
        "score_S": float(score),
        "delta": float(delta),
        "penalty_P": float(penalty),
        "total": float(total),
    }, df

# ===================== Run =====================
col_run, col_note = st.columns([1,2])
with col_run:
    run_btn = st.button("🚀 运行选股模型")
with col_note:
    st.info("无Python也能用：把本仓库部署到 **Streamlit Cloud** 即可在线使用。支持Akshare自动取数；如失败，可上传CSV。")

if run_btn:
    if custom_codes.strip():
        codes = [c.strip() for c in custom_codes.split(",") if c.strip()]
    else:
        codes = get_stock_list(limit)

    rows = []
    hist_cache = {}
    prog = st.progress(0.0, text="正在计算打分…")
    for i, code in enumerate(codes):
        res = score_one_code(code, start_date, end_date)
        if res:
            row, hist = res
            rows.append(row)
            hist_cache[code] = hist
        prog.progress((i+1)/len(codes), text=f"正在计算：{code}")

    if len(rows) == 0:
        st.warning("没有得到任何结果。请尝试减少样本数量或上传CSV数据。")
    else:
        df_res = pd.DataFrame(rows).sort_values("total", ascending=False).reset_index(drop=True)
        st.success(f"完成！共 {len(df_res)} 只股票。")
        st.dataframe(df_res)

        # Top N bar chart
        topn = st.slider("可视化TopN", 5, min(30, len(df_res)), min(15, len(df_res)))
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(df_res["code"].head(topn), df_res["total"].head(topn))
        ax.set_xlabel("Total Score")
        ax.set_ylabel("Stock Code")
        ax.set_title("Top Stocks by Score")
        st.pyplot(fig)

        # Detail viewer
        st.subheader("🔍 单只股票明细")
        picked = st.selectbox("选择股票查看走势：", df_res["code"].tolist())
        if picked in hist_cache:
            h = hist_cache[picked]
            # line plot of close & MAs
            fig2, ax2 = plt.subplots(figsize=(10, 4))
            ax2.plot(h["date"], h["close"], label="Close")
            if "ma20" not in h.columns:  # recompute if needed
                h["ma20"] = h["close"].rolling(20).mean()
                h["ma60"] = h["close"].rolling(60).mean()
            ax2.plot(h["date"], h["ma20"], label="MA20")
            ax2.plot(h["date"], h["ma60"], label="MA60")
            ax2.set_title(f"{picked} Close & MAs")
            ax2.set_xlabel("Date")
            ax2.set_ylabel("Price")
            ax2.legend()
            st.pyplot(fig2)

        # Download
        csv_bytes = df_res.to_csv(index=False).encode("utf-8-sig")
        st.download_button("下载CSV结果", data=csv_bytes, file_name="quant_results.csv", mime="text/csv")
else:
    st.info("在侧边栏设置参数后，点击“运行选股模型”。如无法联网取数，可上传本地CSV（列：date, open, high, low, close, volume）。")

st.caption("© Demo app for educational purposes only. 不构成任何投资建议。")
