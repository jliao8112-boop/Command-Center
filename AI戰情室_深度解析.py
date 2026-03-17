# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- 1. 系統環境與 UI 設定 ---
st.set_page_config(page_title="量化戰情室", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&family=Noto+Sans+TC:wght@500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans TC', sans-serif; }
    
    .ai-header {
        background: linear-gradient(135deg, #0F2027 0%, #203A43 50%, #2C5364 100%);
        color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 8px solid #10B981;
    }
    .report-box {
        background: #F8FAFC; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0;
        font-size: 1rem; line-height: 1.6; color: #1E293B;
    }
    .highlight-red { color: #DC2626; font-weight: bold; }
    .highlight-green { color: #059669; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 2. 演算法核心：無需 AI 的純量化推演 ---
def generate_quant_report(stock_id, stock_name, df):
    """純量化邏輯引擎，直接算出策略與價位"""
    try:
        # 取得最新與昨天的資料
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = round(latest['close'], 2)
        ma20 = round(latest['MA20'], 2)
        ma100 = round(latest['MA100'], 2)
        
        # 1. 趨勢與陣型判定
        if current_price > ma20 and ma20 > ma100:
            trend_status = "🟢 強勢多頭排列"
            action_plan = "順勢操作，拉回月線(MA20)附近皆是佈局良機。"
            sweet_price = round(ma20 * 1.01, 2) # 月線上緣
            defense_price = round(ma20 * 0.98, 2) # 跌破月線停損
            target_price = round(current_price * 1.15, 2) # 抓 15% 漲幅
            timing = "隨時可能發動，注意帶量突破"
        elif current_price < ma20 and ma20 < ma100:
            trend_status = "🔴 弱勢空頭排列"
            action_plan = "空方壓制，嚴禁無腦接刀，建議觀望或反彈遇壓作空。"
            sweet_price = round(current_price * 0.9, 2) # 離現價很遠的摸底價
            defense_price = round(current_price * 0.95, 2)
            target_price = round(ma20 * 0.98, 2) # 反彈碰到月線就跑
            timing = "仍在測底階段，需等待至少 5-8 日量縮築底"
        elif current_price > ma100 and current_price < ma20:
            trend_status = "🟡 回測長線支撐"
            action_plan = "短空長多，正回測季線(MA100)支撐，可嘗試小部位試單。"
            sweet_price = round(ma100 * 1.02, 2)
            defense_price = round(ma100 * 0.98, 2)
            target_price = round(ma20, 2)
            timing = "等待 3-5 日確認支撐不破"
        else:
            trend_status = "🟠 區間震盪整理"
            action_plan = "均線糾結，無明顯方向。建議採取區間高出低進策略。"
            sweet_price = round(min(ma20, ma100), 2)
            defense_price = round(sweet_price * 0.97, 2)
            target_price = round(max(ma20, ma100) * 1.05, 2)
            timing = "方向未明，需等待大紅K表態"

        # 2. K線狀態簡易判斷
        is_red = latest['close'] > latest['open']
        k_color = "收紅K" if is_red else "收黑K"
        
        # 3. 組裝報告
        report = f"""
### 🎯 核心量化決策面板
* **現價：** {current_price} 元 ({trend_status})
* **🍯 甜甜價 (建倉參考)：** {sweet_price} 元
* **🛡️ 防守價 (風控撤退)：** <span class='highlight-red'>{defense_price} 元</span>
* **🚀 目標價 (波段預期)：** <span class='highlight-green'>{target_price} 元</span>
* **⏳ 預估啟動時間：** {timing}

---

### 第一章：技術結構掃描
* **最新收盤狀態：** 今日{k_color}，收盤價 {current_price}。昨日收盤為 {round(prev['close'], 2)}。
* **短線防線 (MA20 月線)：** 目前位於 {ma20} 元。
* **長線防線 (MA100 季/半年線)：** 目前位於 {ma100} 元。
* **均線相對位置：** {'股價已站上月線' if current_price > ma20 else '股價遭到月線壓制'}，且{'長線趨勢向上' if ma20 > ma100 else '長線趨勢向下'}。

### 第二章：系統最終戰略指示
基於目前的演算法模型判定，此標的屬於 **{trend_status}** 格局。
**指揮部行動代號：** {action_plan}

> ⚠️ 戰情室提醒：此版本為純量化演算法推演，無使用外部 AI 讀取新聞，決策依據純粹為價格與均線力道，請搭配個人紀律執行停損。
        """
        return report

    except Exception as e:
        return f"運算錯誤: {str(e)}"

# --- 3. UI 介面 ---
def main():
    st.markdown("<div class='ai-header'><h2 style='margin:0;'>⚡ 量化戰情室：極速推演系統</h2><p style='margin:0; opacity:0.8;'>純演算法驅動，無外部 API 依賴，軍規級穩定秒殺分析</p></div>", unsafe_allow_html=True)

    st.sidebar.markdown("### 🎯 目標鎖定")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        m_sid = st.text_input("股票代碼", value="2330").upper()
    with col2:
        m_name = st.text_input("股票名稱", value="台積電")

    st.sidebar.info("💡 目前為**「純量化無人機模式」**。無須輸入金鑰，系統將直接使用內部演算法推算支撐與壓力位。")

    if st.sidebar.button("🚀 啟動極速推演", use_container_width=True):
        with st.spinner(f"正在擷取 {m_name} 數據，執行量化模型運算..."):
            try:
                # 抓取數據
                is_us = any(c.isalpha() for c in m_sid)
                symbol = m_sid if is_us else f"{m_sid}.TW"
                
                df = yf.download(symbol, period="100d", interval="1d", progress=False)
                if df.empty and not is_us:
                    df = yf.download(f"{m_sid}.TWO", period="100d", interval="1d", progress=False)
                
                if df.empty:
                    st.error("❌ 查無此股票代碼的數據，請確認後再試。")
                    return

                # 數據整理
                df = df.reset_index()
                df.columns = [col[0].lower() if isinstance(df.columns, pd.MultiIndex) else col.lower() for col in df.columns]
                
                # 計算基礎均線
                df['MA20'] = df['close'].rolling(window=20).mean()
                df['MA100'] = df['close'].rolling(window=100).mean()
                df = df.dropna() # 移除計算均線產生的空值
                
                # 呼叫量化引擎
                report = generate_quant_report(m_sid, m_name, df)
                
                st.markdown("<div class='report-box'>", unsafe_allow_html=True)
                st.markdown(report, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.success("✅ 量化戰情報告生成完畢！")
                
            except Exception as e:
                st.error(f"執行時發生錯誤: {e}")

if __name__ == "__main__":
    main()