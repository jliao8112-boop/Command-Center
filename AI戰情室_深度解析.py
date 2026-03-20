# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd

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
    .highlight-blue { color: #2563EB; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 🚀 升級 1：加入 Streamlit 快取機制 (暫存 60 秒)，大幅降低 Yahoo API 阻擋機率
@st.cache_data(ttl=60, show_spinner=False)
def fetch_stock_data(sid, is_us):
    symbol = sid if is_us else f"{sid}.TW"
    df = yf.download(symbol, period="250d", interval="1d", progress=False)
    
    # 若為台股且 .TW 抓不到，嘗試上櫃 .TWO
    if df.empty and not is_us:
        symbol = f"{sid}.TWO"
        df = yf.download(symbol, period="250d", interval="1d", progress=False)
    return df

# --- 2. 演算法核心：法人級量化模組 ---
def calculate_professional_indicators(df):
    """計算均線、均量與 ATR 真實波動"""
    # 🚀 升級 2：使用 ffill() 填補盤中報價產生的 NaN，不需再依賴易被擋的 fast_info
    df = df.ffill()
    
    df['MA21'] = df['close'].rolling(window=21).mean()
    df['MA144'] = df['close'].rolling(window=144).mean()
    df['Vol_MA20'] = df['volume'].rolling(window=20).mean()
    
    df['H-L'] = df['high'] - df['low']
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR14'] = df['TR'].rolling(window=14).mean()
    
    return df.dropna()

def generate_pro_quant_report(stock_id, stock_name, df):
    """專業操作邏輯引擎"""
    try:
        latest = df.iloc[-1]
        
        current_price = latest['close']
        ma21 = latest['MA21']
        ma144 = latest['MA144']
        vol_today = latest['volume']
        vol_ma20 = latest['Vol_MA20']
        atr = latest['ATR14']
        
        # 量價動能判定
        vol_ratio = vol_today / vol_ma20 if vol_ma20 > 0 else 1
        if vol_ratio >= 1.5: vol_status = "🔥 爆量 (大於均量 1.5 倍)"
        elif vol_ratio <= 0.7: vol_status = "💤 極度量縮 (小於均量 0.7 倍)"
        else: vol_status = "⚖️ 溫和常態量"

        # 專業戰略推演與價位計算
        if current_price > ma21 and ma21 > ma144:
            trend_status = "🟢 多頭主升段 (強勢)"
            defense_price = ma21 - atr
            sweet_price = ma21 + (atr * 0.5)
            
            risk = current_price - defense_price
            if risk <= 0: risk = atr 
            target_price = current_price + (risk * 2)
            
            action_plan = f"趨勢強勢。若現價追價，需承擔 {risk:.2f} 元風險。建議等待拉回至【甜甜價】附近，配合【{vol_status}】的量縮狀態測試支撐再行佈局。"
            timing = "隨時可能帶量創高，重點觀察突破時是否具備 1.5 倍以上均量。"
            
        elif current_price < ma21 and ma21 < ma144:
            trend_status = "🔴 空頭發散 (弱勢)"
            defense_price = ma21 + atr
            sweet_price = ma21 - (atr * 0.5)
            
            risk = defense_price - current_price
            if risk <= 0: risk = atr
            target_price = current_price - (risk * 2)
            
            action_plan = f"空方格局，均線下壓。嚴格禁止逆勢摸底買多。積極者可於反彈至【甜甜價】無力時，順勢佈局空單。"
            timing = "跌勢未止，需等待至少 1-2 週的底部分型與爆量洗盤訊號。"
            
        else:
            trend_status = "🟡 震盪整理期 (均線糾結)"
            defense_price = current_price - (atr * 1.5)
            sweet_price = min(ma21, ma144)
            
            risk = current_price - defense_price
            if risk <= 0: risk = atr
            target_price = current_price + (risk * 1.5)
            
            action_plan = "目前處於趨勢轉換或中繼整理階段。主力籌碼交換中，建議採用【箱型戰法】，跌破防守價嚴格停損，不宜戀戰。"
            timing = f"方向收斂中，等待長紅/長黑K棒突破，並伴隨【爆量】訊號以確認新趨勢。"

        rr_ratio = abs(target_price - current_price) / abs(current_price - defense_price + 0.01)

        # 🚀 同步主系統：動態破線警告防呆機制
        is_long = target_price > defense_price
        sweet_display = f"<span class='highlight-blue'>{sweet_price:.2f} 元</span>"
        
        if is_long and current_price < sweet_price:
            sweet_display = f"<span style='text-decoration: line-through; color: #94A3B8;'>{sweet_price:.2f} 元</span> <span style='color: #DC2626; font-weight: bold;'>⚠️ 支撐失效 (破線)</span>"
        elif not is_long and current_price > sweet_price:
            sweet_display = f"<span style='text-decoration: line-through; color: #94A3B8;'>{sweet_price:.2f} 元</span> <span style='color: #DC2626; font-weight: bold;'>⚠️ 壓力失效 (突破)</span>"

        # 組裝專業報告 (全面套用 :.2f 強制過濾多餘小數點)
        report = f"""
### 🎯 專業操盤手決策面板
* **現價：** {current_price:.2f} 元 ({trend_status})
* **🍯 甜甜價 (合理建倉區)：** {sweet_display}
* **🛡️ 防守價 (ATR動態停損)：** <span class='highlight-red'>{defense_price:.2f} 元</span>
* **🚀 目標價 (滿足 1:{rr_ratio:.1f} 盈虧比)：** <span class='highlight-green'>{target_price:.2f} 元</span>
* **⏳ 發動契機：** {timing}

---

### 第一章：波動率與量價結構
* **ATR 日均波動幅度：** 目前個股每日平均震盪約 **{atr:.2f} 元**。防守價已納入此波動寬容值，防範主力洗盤。
* **今日量能狀態：** **{vol_status}** (今日成交量：{int(vol_today):,} / 20日均量：{int(vol_ma20):,})。
* **短線生命線 (MA21)：** {ma21:.2f} 元。
* **牛熊分界線 (MA144)：** {ma144:.2f} 元。

### 第二章：系統最終戰略指示
**戰術定調：** {action_plan}

**紀律準則：** 1. 專業交易的核心是【風險控制】。若股價收盤跌破防守價 ({defense_price:.2f} 元)，代表本次戰術推演失效，請無條件撤退。
2. 目前設定的期望盈虧比為 **1 : {rr_ratio:.1f}**。若到達目標價，建議分批獲利了結，或將停損點上移至成本價，立於不敗之地。
        """
        return report

    except Exception as e:
        return f"運算錯誤: {str(e)}"

# --- 3. UI 介面 ---
def main():
    st.markdown("<div class='ai-header'><h2 style='margin:0;'>⚡ 量化戰情室：法人級極速推演</h2><p style='margin:0; opacity:0.8;'>搭載 ATR 動態停損、量價動能與 R/R 盈虧比策略，抗 Yahoo 封鎖快取版</p></div>", unsafe_allow_html=True)

    st.sidebar.markdown("### 🎯 目標鎖定")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        m_sid = st.text_input("股票代碼", value="1815").upper().strip()
    with col2:
        m_name = st.text_input("股票名稱", value="")

    st.sidebar.info("💡 **「抗封鎖模式」**啟動。系統已掛載記憶體快取，確保穩定抓取上櫃與上市即時報價，不再觸發 Rate Limit。")

    if st.sidebar.button("🚀 啟動極速推演", use_container_width=True):
        with st.spinner(f"正在擷取 {m_name} 數據，執行專業量化模型運算..."):
            try:
                is_us = any(c.isalpha() for c in m_sid)
                
                # 🚀 呼叫帶有快取機制的抓取函數
                df = fetch_stock_data(m_sid, is_us)
                
                if df.empty:
                    st.error("❌ 查無此股票代碼的數據，請確認後再試。")
                    return

                # 數據整理 (處理 yfinance 回傳的多層級 MultiIndex)
                df = df.reset_index()
                df.columns = [col[0].lower() if isinstance(df.columns, pd.MultiIndex) else col.lower() for col in df.columns]
                
                # 計算專業指標
                df = calculate_professional_indicators(df)
                
                if len(df) < 2:
                    st.error("❌ 該標的歷史資料不足 (需滿 144 個交易日以建立基準線)，請更換分析標的。")
                    return
                
                # 呼叫專業量化引擎
                report = generate_pro_quant_report(m_sid, m_name, df)
                
                st.markdown("<div class='report-box'>", unsafe_allow_html=True)
                st.markdown(report, unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.success("✅ 法人級量化戰情報告生成完畢！")
                
            except Exception as e:
                st.error(f"執行時發生錯誤: {e}")

if __name__ == "__main__":
    main()