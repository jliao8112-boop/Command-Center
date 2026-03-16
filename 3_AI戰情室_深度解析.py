# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import datetime
import time
import re

# --- 1. 系統環境與 UI 設定 ---
st.set_page_config(page_title="AI 戰情室", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&family=Noto+Sans+TC:wght@500;700;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans TC', sans-serif; }
    
    .ai-header {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .report-box {
        background: #F8FAFC; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0;
        font-size: 1rem; line-height: 1.6; color: #1E293B;
    }
    /* 手機版優化 */
    @media (max-width: 768px) {
        .ai-header { padding: 15px; }
        .ai-header h2 { font-size: 1.4rem; }
        .report-box { padding: 15px; font-size: 0.95rem; }
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 核心 AI 引擎邏輯 (移植自 ai_engine.py) ---
def fetch_news_summary(api_key, stock_id, stock_name):
    """使用 Gemini 抓取最新新聞摘要"""
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": f"請用繁體中文搜尋並摘要「台股 {stock_id} {stock_name}」最近的重要新聞，包含：最新財報、法人評等、重大訊息、產業動態、題材催化劑。請條列最多 8 則，每則 2~3 句，並標明來源與日期（若有）。若無相關新聞，回覆「查無近期新聞」。"}]}],
            "tools": [{"google_search": {}}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
        }
        response = requests.post(f"{url}?key={api_key}", headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            candidates = result.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                texts = [p.get("text", "") for p in parts if "text" in p]
                news_text = "\n".join(texts).strip()
                if news_text: return news_text
        return ""
    except Exception: return ""

def analyze_stock_trend(api_key, stock_id, stock_name, df):
    """AI 深度分析引擎"""
    if not api_key: return "⚠️ 請先輸入 API Key"
    
    try:
        essential_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'MA20', 'MA100', '外資', '投信', '融資餘額']
        valid_cols = [c for c in essential_cols if c in df.columns]
        recent_df = df[valid_cols].tail(30).copy()  
        current_price = round(df['close'].iloc[-1], 2)
        
        def classify_kbar(row):
            o, h, l, c = row['open'], row['high'], row['low'], row['close']
            body = abs(c - o)
            total_range = h - l
            if total_range < 0.001: return '一字線'
            upper_shadow = h - c if c >= o else h - o
            lower_shadow = o - l if c >= o else c - l
            body_ratio = body / total_range if total_range > 0 else 0
            chg_pct = abs(c - o) / o * 100 if o > 0 else 0  
            
            if body_ratio < 0.05:  
                if total_range / o < 0.003: return '一字線'
                elif upper_shadow < total_range * 0.1 and lower_shadow > body * 2: return 'T字線'
                elif lower_shadow < total_range * 0.1 and upper_shadow > body * 2: return '倒T線'
                else: return '十字線'
            
            shadow_ratio = (upper_shadow + lower_shadow) / total_range
            if shadow_ratio <= 0.2:
                if c > o: return '大紅K' if body_ratio > 0.7 and chg_pct >= 7 else '中紅K' if body_ratio > 0.4 and chg_pct >= 3 else '小紅K'
                else: return '大黑K' if body_ratio > 0.7 and chg_pct >= 7 else '中黑K' if body_ratio > 0.4 and chg_pct >= 3 else '小黑K'
            elif upper_shadow > body * 2 and lower_shadow < body * 0.3: return '倒鎚紅K' if c >= o else '倒鎚黑K'
            elif lower_shadow > body * 2 and upper_shadow < body * 0.3: return '紅K鎚子' if c >= o else '黑K鎚子'
            else: return '紡錘紅K' if c >= o else '紡錘黑K'
        
        recent_df['K線'] = recent_df.apply(classify_kbar, axis=1)
        
        for col in recent_df.columns:
            if col not in ['date', 'K線']:
                if col in ['volume','外資','投信','自營商','主力合計','融資餘額','融券餘額']:
                    recent_df[col] = pd.to_numeric(recent_df[col], errors='coerce').fillna(0).round(0).astype(int)
                else:
                    recent_df[col] = pd.to_numeric(recent_df[col], errors='coerce').round(2)
        
        recent_data = recent_df.to_string(index=False)

        prompt = f"""
        你是股神等級的「台股首席參謀長」，針對「{stock_id} {stock_name}」進行嚴謹診斷。
        1. 均線週期：僅限 MA20、MA100。
        2. 時間表達：禁止寫死年份，使用動態描述。
        3. 數字格式：阿拉伯數字。
        4. 禁止提到「你」。禁止投資指示用語（建議買進/賣出），改用「若欲操作可參考」。
        
        請建立「核心決策面板」：
        現價：{current_price} 元
        甜甜價：（依據支撐位客觀推算）
        目標價：（依據壓力區客觀推算）
        預估啟動時間：（推測發動時機）
        
        接著輸出五大章節：
        第一章：K線型態精密掃描
        第二章：均線與趨勢結構
        第三章：大戶籌碼與散戶動向
        第四章：產業與基本面展望
        第五章：最終操作策略
        
        **近 30 日完整數據**
        {recent_data}
        """
        
        news_summary = fetch_news_summary(api_key, stock_id, stock_name)
        if news_summary:
            prompt += f"\n---\n**【最新新聞摘要】**\n{news_summary}\n請在第四章適當引用。"

        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        model_name = "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        
        response = requests.post(f"{url}?key={api_key}", headers=headers, json=payload, timeout=90)
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return f"{text}\n\n---\n*分析模型: {model_name}*"
        return f"❌ 模組連線失敗，請檢查 API Key 或網路狀態。代碼: {response.status_code}"

    except Exception as e:
        return f"系統錯誤: {str(e)}"

# --- 3. UI 介面 ---
def main():
    st.markdown("<div class='ai-header'><h2 style='margin:0;'>🧠 AI 股市戰情室：全方位深度解析</h2><p style='margin:0; opacity:0.8;'>搭載 Google Gemini 引擎，結合技術面、籌碼面與即時新聞</p></div>", unsafe_allow_html=True)

    # 側邊欄設定
    st.sidebar.markdown("### 🔑 系統授權")
    
    # 🌟 新增：取得金鑰的超連結
    st.sidebar.markdown("[🔗 點此免費取得 Gemini API Key](https://aistudio.google.com/app/apikey)")
    
    # 🌟 新增：自動讀取雲端 Secrets 機制
    default_api_key = ""
    # 嘗試從 Streamlit Secrets 中讀取，如果有就自動填入
    if "GEMINI_API_KEY" in st.secrets:
        default_api_key = st.secrets["GEMINI_API_KEY"]

    # 輸入框預設值改為 default_api_key
    api_key = st.sidebar.text_input("請輸入或確認 Gemini API Key", type="password", value=default_api_key, help="若您已在雲端後台設定 Secrets，此處將自動填入。")
    st.sidebar.markdown("---")
    
    st.sidebar.markdown("### 🎯 目標鎖定")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        m_sid = st.text_input("股票代碼", value="2330")
    with col2:
        m_name = st.text_input("股票名稱", value="台積電")

    if st.sidebar.button("🚀 啟動深度解析", use_container_width=True):
        if not api_key:
            st.error("⚠️ 啟動失敗：請先在左側邊欄輸入 Gemini API Key。")
            return
        
        with st.spinner(f"正在連線全球資料庫與 AI 引擎，對 {m_name} 進行掃描，這大約需要 15-30 秒..."):
            try:
                # 抓取數據 (移植自 app.py 邏輯)
                symbol = f"{m_sid}.TW"
                df = yf.download(symbol, period="200d", interval="1d", progress=False)
                if df.empty or len(df) < 20:
                    df = yf.download(f"{m_sid}.TWO", period="200d", interval="1d", progress=False)
                
                if df.empty:
                    st.error("❌ 查無此股票代碼的數據，請確認後再試。")
                    return

                # 數據整理
                df = df.reset_index()
                df.columns = [col[0].lower() if isinstance(df.columns, pd.MultiIndex) else col.lower() for col in df.columns]
                df['MA20'] = df['close'].rolling(window=20).mean()
                df['MA100'] = df['close'].rolling(window=100).mean()
                df['外資'] = np.random.randint(-1000, 1000, len(df)) # 依照原代碼的模擬設定
                
                # 執行分析
                report = analyze_stock_trend(api_key, m_sid, m_name, df)
                
                st.markdown("<div class='report-box'>", unsafe_allow_html=True)
                st.markdown(report)
                st.markdown("</div>", unsafe_allow_html=True)
                st.success("✅ 戰情報告生成完畢！")
                
            except Exception as e:
                st.error(f"執行時發生錯誤: {e}")

if __name__ == "__main__":
    main()