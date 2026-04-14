# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. 系統環境與 UI 設定 ---
st.set_page_config(page_title="量化戰情室 v36.0 (EMA 旗艦版)", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&family=Noto+Sans+TC:wght@500;700;900&family=JetBrains+Mono:wght@600;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans TC', sans-serif; }
    
    .ai-header {
        background: linear-gradient(135deg, #0F2027 0%, #203A43 50%, #2C5364 100%);
        color: white; padding: 20px; border-radius: 12px; margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 8px solid #10B981;
    }
    
    .price-grid { display: flex; justify-content: space-between; background: #F8FAFC; padding: 20px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #F1F5F9; }
    .price-box { text-align: center; width: 24%; }
    .price-label { font-size: 0.85rem; color: #64748B; font-weight: 800; margin-bottom: 6px; }
    .price-val { font-family: 'JetBrains Mono', monospace; font-size: 1.8rem; font-weight: 900; letter-spacing: -0.5px; }
    
    .report-box { background-color: #F8FAFC; padding: 20px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 20px; }
    .report-chapter { margin-top: 0; color: #0F172A; font-weight: 900; font-size: 1.2rem; display: flex; align-items: center; gap: 8px; }
    .report-list { font-size: 0.95rem; color: #334155; padding-left: 20px; line-height: 1.7; }
    .report-text { font-size: 0.95rem; color: #334155; line-height: 1.7; }
    
    @media (max-width: 768px) {
        .price-grid { flex-wrap: wrap; gap: 15px; }
        .price-box { width: 48%; }
        .price-val { font-size: 1.4rem; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ⚡ 零延遲機制：強制刷新
# ==========================================
if st.sidebar.button("🔄 強制清除快取 (獲取最新報價)", type="primary", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("✅ 快取已清除！")
st.sidebar.divider()

@st.cache_data(ttl=60, show_spinner=False)
def fetch_stock_data(sid, is_us):
    symbol = sid if is_us else f"{sid}.TW"
    df = yf.download(symbol, period="300d", interval="1d", progress=False)
    if df.empty and not is_us:
        symbol = f"{sid}.TWO"
        df = yf.download(symbol, period="300d", interval="1d", progress=False)
    return df

def analyze_intraday_ticks(sid, is_us):
    """盤中即時大單量測引擎 (使用 1 分K 模擬 Tick 大單淨流向)"""
    try:
        if is_us:
            ticker = str(sid)
            df_1m = yf.Ticker(ticker).history(period="1d", interval="1m")
        else:
            ticker = f"{sid}.TW"
            df_1m = yf.Ticker(ticker).history(period="1d", interval="1m")
            if df_1m.empty:
                ticker = f"{sid}.TWO"
                df_1m = yf.Ticker(ticker).history(period="1d", interval="1m")
        
        if df_1m.empty or len(df_1m) < 5:
            return "數據不足", 0

        avg_vol_1m = df_1m['Volume'].mean()
        if avg_vol_1m == 0: return "量能極凍", 0
        
        large_threshold = avg_vol_1m * 2
        large_buys = df_1m[(df_1m['Volume'] > large_threshold) & (df_1m['Close'] > df_1m['Open'])]['Volume'].sum()
        large_sells = df_1m[(df_1m['Volume'] > large_threshold) & (df_1m['Close'] < df_1m['Open'])]['Volume'].sum()
        
        net_large_orders = large_buys - large_sells
        
        if net_large_orders > 0 and large_buys > avg_vol_1m * 3:
            return "🟢 大戶低接 (錯殺洗盤)", net_large_orders
        elif net_large_orders < 0 and large_sells > avg_vol_1m * 3:
            return "🔴 大戶倒貨 (真實破線)", net_large_orders
        else:
            return "🟡 散戶無序出局", net_large_orders
            
    except Exception as e:
        return "獲取失敗", 0

# --- 2. 演算法核心：全面 EMA 化 ---
def calculate_professional_indicators(df):
    df = df.ffill()
    
    # 🚀 全面切換為 EMA
    df['EMA8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['EMA34'] = df['close'].ewm(span=34, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA144'] = df['close'].ewm(span=144, adjust=False).mean()
    df['Vol_MA20'] = df['volume'].rolling(window=20).mean()
    
    df['BB_Mid'] = df['close'].rolling(window=20).mean()
    df['BB_Std'] = df['close'].rolling(window=20).std()
    df['BB_Lower'] = df['BB_Mid'] - 2 * df['BB_Std']
    df['BB_Upper'] = df['BB_Mid'] + 2 * df['BB_Std']
    df['BB_Width'] = np.where(df['BB_Mid'] > 0, (df['BB_Upper'] - df['BB_Lower']) / df['BB_Mid'], 0)
    
    df['H-L'] = df['high'] - df['low']
    df['H-PC'] = abs(df['high'] - df['close'].shift(1))
    df['L-PC'] = abs(df['low'] - df['close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['ATR14'] = df['TR'].rolling(window=14).mean()
    
    return df.dropna()

def generate_pro_quant_report(stock_id, stock_name, df, is_us):
    try:
        latest = df.iloc[-1]
        
        close = float(latest['close'])
        open_p = float(latest['open'])
        ema8 = float(latest['EMA8'])
        ema34 = float(latest['EMA34'])
        ema21 = float(latest['EMA21'])
        ema144 = float(latest['EMA144'])
        vol_today = float(latest['volume'])
        vol_ma20 = float(latest['Vol_MA20'])
        atr = float(latest['ATR14'])
        bb_lower = float(latest['BB_Lower'])
        bb_width = float(latest['BB_Width'])
        
        curr_sym = "US$" if is_us else "NT$"
        
        high_60d = float(df['high'].tail(60).max())
        drop_from_high = (high_60d - close) / high_60d if high_60d > 0 else 0
        is_healthy_pullback = drop_from_high <= 0.20
        
        vol_ratio = vol_today / vol_ma20 if vol_ma20 > 0 else 1
        if vol_ratio >= 1.5: vol_status = "🔥 爆量 (大於均量 1.5 倍)"
        elif vol_ratio <= 0.7: vol_status = "💤 極度量縮 (小於均量 0.7 倍)"
        else: vol_status = "⚖️ 溫和常態量"

        is_vcp = (bb_width < 0.12) and (vol_ratio < 0.8)
        is_high_vol_drop = (close < ema8) and (vol_today > vol_ma20)
        is_uptrend_aligned = close > ema8 and ema8 > ema34

        tick_status, net_large_vol = analyze_intraday_ticks(stock_id, is_us)

        # 🚀 參照新版多空邏輯判定
        if is_high_vol_drop:
            if "大戶倒貨" in tick_status:
                trend_status = "🔴 破線空頭 (大戶棄守)"
                action_plan = "爆量跌破且偵測到【大戶倒貨】，主力已撤退，請嚴格執行無條件停損！"
                timing = f"盤中大單淨流出 {net_large_vol:,.0f}，需等待籌碼徹底沉澱。"
                def_p, sweet_p, target_p = round(ema34 - atr, 2), round(ema34 * 0.95, 2), round(ema34, 2)
            elif "大戶低接" in tick_status:
                trend_status = "🟡 破線洗盤 (大戶承接)"
                action_plan = "跌破防線但【大戶低接】，極可能是刻意洗盤！防護網放寬，不急於盤中停損。"
                timing = f"盤中大單淨流入 {net_large_vol:,.0f}，觀察尾盤是否站回防守價再動作。"
                def_p, sweet_p, target_p = round(ema34 - (atr * 1.5), 2), round(ema34 * 0.98, 2), round(ema34 * 1.05, 2)
            else:
                trend_status = "🔴 破線空頭 (散戶恐慌)"
                action_plan = "爆量跌破，大戶未明顯承接，建議先退出觀望。"
                timing = "需等待量縮止跌與底部分型。"
                def_p, sweet_p, target_p = round(ema34 - atr, 2), round(ema34 * 0.95, 2), round(ema34, 2)
            alloc_c, alloc_s, alloc_d = "10%", "30%", "60%"
        elif is_uptrend_aligned:
            trend_status = "🟢 右側強勢 (衝刺中)"
            def_p = round(ema8 - (atr * 0.8), 2)
            sweet_p = round(ema8 + (atr * 0.3), 2)
            target_p = round(close + (atr * 3.0), 2)
            alloc_c, alloc_s, alloc_d = "40%", "40%", "20%"
            action_plan = "強勢動能軌道，啟動 EMA8 動態追蹤止盈。大盤綠燈時可順勢狙擊。"
            timing = "隨時可能帶量創高，重點觀察突破時是否具備 1.5 倍以上均量。"
        elif close > ema34:
            trend_status = "🟡 震盪整理期"
            def_p = round(ema34 - (atr * 0.5), 2)
            sweet_p = round(ema34 * 1.01, 2)
            target_p = round(close + (atr * 2.5), 2)
            alloc_c, alloc_s, alloc_d = "20%", "50%", "30%"
            action_plan = "回測 34EMA 防線。大盤綠黃燈時，若出現下影線且量縮，可於伏擊區試單。"
            timing = "方向收斂中，等待長紅/長黑K棒突破，並伴隨【爆量】訊號以確認新趨勢。"
        else:
            trend_status = "🔴 左側尋底 (弱勢)"
            sweet_p = round(max(ema144, bb_lower), 2) if ema144 > 0 else bb_lower
            recent_low = float(df['low'].tail(10).min())
            def_p = round(min(recent_low, ema34 - atr), 2)
            target_p = round(ema34, 2)
            alloc_c, alloc_s, alloc_d = "10%", "60%", "30%"
            action_plan = f"跌破波段防線。建議等殺盤至伏擊區 ({sweet_p}) 附近左側建倉。"
            timing = "跌勢未止，需等待至少 1-2 週的底部分型與爆量洗盤訊號。"
            
        base_price = close if close >= def_p else sweet_p
        risk_val = abs(base_price - def_p)
        if risk_val <= 0: risk_val = atr
        reward_val = abs(target_p - base_price)
        rr_ratio = round(reward_val / risk_val, 2)

        # 綜合勝率推算
        prob = 40
        if close > ema8: prob += 15
        elif close > ema34: prob += 5
        if is_vcp: prob += 15
        if vol_ratio < 0.8: prob += 10
        if is_high_vol_drop: prob -= 30
        if not is_healthy_pullback: prob -= 40
        
        # 🚀 戰略重構：盤中籌碼擁有絕對否決權 (強制降評防護機制)
        if "大戶倒貨" in tick_status:
            prob -= 40  # 扣減 40 分，確保其絕對無法進入第一線主將清單
        elif "大戶低接" in tick_status:
            prob += 10  # 籌碼健康度提升，加分
            
        prob = min(max(prob, 10), 95)
        
        is_volume_breakout = (vol_today > vol_ma20 * 2.5) and (close > open_p)
        is_wall_intact = close > ema34

        if is_uptrend_aligned:
            module_s_status = "🏃‍♂️ <b style='color:#BE123C;'>動能爆發 (啟動追蹤止盈)</b>。主升段加速中。"
            module_s_action = f"股價已進入強勢區，請將防守線無條件上移至 EMA8 (<b>{ema8:.2f}</b>)，執行『獲利奔跑，跌破即收』戰術。"
        elif is_volume_breakout:
            module_s_status = "🔥 <b style='color:#E11D48;'>地基爆量起漲！</b>大戶資金進駐。"
            module_s_action = f"若買進，將波段生命線 <b>{ema34:.2f}</b> 設為底線，收盤未跌破前絕不賣出。"
        elif is_wall_intact:
            module_s_status = "🛡️ <b style='color:#059669;'>承重牆穩固</b>。趨勢持續向上。"
            module_s_action = f"若已有獲利可執行「3-2 分批停利」。剩下部位死守承重牆 <b>{ema34:.2f}</b>，跌破才結案。"
        else:
            module_s_status = "⚠️ <b style='color:#DC2626;'>工程停工 (跌破承重牆)</b>。"
            module_s_action = f"現價已低於 EMA34 ({ema34:.2f})，波段多頭暫歇，建議資金迴避或嚴格停損。"
            
        return {
            "prob": prob, "rr": rr_ratio, "alloc_c": alloc_c, "alloc_s": alloc_s, "alloc_d": alloc_d,
            "curr": curr_sym, "price": close, "sweet": sweet_p, "defense": def_p, "target": target_p,
            "atr": atr, "vol_status": vol_status, "vol_today": vol_today, "vol_ma20": vol_ma20,
            "ema21": ema21, "ema144": ema144, "ema34": ema34, "ema8": ema8,
            "trend_status": trend_status, "action_plan": action_plan, "timing": timing, 
            "module_s_status": module_s_status, "module_s_action": module_s_action,
            "tick_status": tick_status, "is_healthy_pullback": is_healthy_pullback, "drop_from_high": drop_from_high,
            "is_high_vol_drop": is_high_vol_drop, "is_uptrend_aligned": is_uptrend_aligned
        }
    except Exception as e:
        return None

# --- 3. UI 介面與報告渲染 ---
def main():
    st.markdown("<div class='ai-header'><h2 style='margin:0;'>⚡ 量化戰情室：法人級極速推演 (EMA 旗艦版)</h2><p style='margin:0; opacity:0.8;'>搭載 EMA 全頻追蹤、大單透視與洗盤防禦系統</p></div>", unsafe_allow_html=True)

    col1, col2 = st.sidebar.columns(2)
    with col1: m_sid = st.text_input("股票代碼", value="1815").upper().strip()
    with col2: m_name = st.text_input("股票名稱", value="")

    if st.sidebar.button("🚀 啟動極速推演", use_container_width=True):
        with st.spinner(f"正在擷取 {m_name if m_name else m_sid} 數據，執行專業量化模型運算..."):
            try:
                is_us = any(c.isalpha() for c in m_sid)
                df = fetch_stock_data(m_sid, is_us)
                
                if df.empty:
                    st.error("❌ 查無此股票代碼的數據，請確認後再試。")
                    return

                df = df.reset_index()
                df.columns = [col[0].lower() if isinstance(df.columns, pd.MultiIndex) else col.lower() for col in df.columns]
                df = calculate_professional_indicators(df)
                
                if df.empty:
                    st.error("❌ 該標的歷史資料不足 (需滿 144 個交易日以建立基準線)，請更換分析標的。")
                    return
                
                res = generate_pro_quant_report(m_sid, m_name, df, is_us)
                if not res:
                    st.error("❌ 運算過程發生錯誤，請稍後再試。")
                    return
                
                st.success(f"✅ 掃描完成！綜合勝率: **{res['prob']}%** | 盈虧比: **{res['rr']:.2f}**")
                
                sweet_val_html = f"{res['curr']}{res['sweet']:.2f}"
                sweet_label_html = f"🍯 伏擊區 ({res['alloc_s']})"
                is_long = res['target'] > res['defense']
                
                if is_long and res['price'] < res['sweet']:
                    sweet_val_html = f"<span style='text-decoration: line-through; color: #94A3B8;'>{res['curr']}{res['sweet']:.2f}</span> <span style='color: #DC2626; font-size: 0.85rem;'>⚠️破線</span>"
                    sweet_label_html = f"<span style='color: #DC2626;'>⚠️ 支撐失效</span> ({res['alloc_s']})"
                elif not is_long and res['price'] > res['sweet']:
                    sweet_val_html = f"<span style='text-decoration: line-through; color: #94A3B8;'>{res['curr']}{res['sweet']:.2f}</span> <span style='color: #DC2626; font-size: 0.85rem;'>⚠️突破</span>"
                    sweet_label_html = f"<span style='color: #DC2626;'>⚠️ 壓力失效</span> ({res['alloc_s']})"

                st.markdown("### 📊 戰術價位分析")
                price_panel = f"""
                <div class='price-grid'>
                <div class='price-box'><div class='price-label'>💎 現價 ({res['alloc_c']})</div><div class='price-val' style='color:#1E40AF;'>{res['curr']}{res['price']:.2f}</div></div>
                <div class='price-box'><div class='price-label'>{sweet_label_html}</div><div class='price-val' style='color:#D97706;'>{sweet_val_html}</div></div>
                <div class='price-box'><div class='price-label'>🛡️ 防守價 ({res['alloc_d']})</div><div class='price-val' style='color:#DC2626;'>{res['curr']}{res['defense']:.2f}</div></div>
                <div class='price-box'><div class='price-label'>🎯 目標價</div><div class='price-val' style='color:#059669;'>{res['curr']}{res['target']:.2f}</div></div>
                </div>
                """
                st.markdown(price_panel, unsafe_allow_html=True)
                
                # ==========================================
                # 🚀 終極改寫機制：偵測致命風險並重構報告 (與 v32 戰術指揮官同步)
                # ==========================================
                has_major_risk = ("大戶倒貨" in res.get('tick_status', '')) or (not res.get('is_healthy_pullback', True)) or res.get('is_high_vol_drop', False)

                if has_major_risk:
                    ch2_trend = "🚨 短線動能破壞 (觸發系統防禦機制)"
                    ch2_tactics = "<span style='color:#DC2626; font-weight:bold;'>系統強制取消買進許可！</span>日線雖偏多，但盤中偵測到主力派發或高檔重挫，短線籌碼已轉弱。"
                    ch2_timing = "需等待籌碼徹底沉澱，盤中大單重新翻紅且日線收實體紅K。"
                    ch2_discipline = f"強烈建議空手觀望。若已持倉，將防守極限上移至 EMA8 ({res['ema8']:.2f})，跌破無條件撤退！"
                    
                    module_s_status = "⚠️ <b style='color:#DC2626;'>警報響起 (籌碼與技術背離)</b>。隨時可能反轉下殺。"
                    module_s_action = f"放棄原波段防守。立刻執行「觸價即砍」，跌破 <b>{res['ema8']:.2f}</b> 全數結清，絕不留戀。"
                    
                    risk_warnings = []
                    if "大戶倒貨" in res.get('tick_status', ''): risk_warnings.append("● 盤中偵測到【大戶倒貨】，反彈逢高派發，籌碼正在流向散戶。")
                    if not res.get('is_healthy_pullback', True): risk_warnings.append(f"● 距離近期高點已重挫 {res.get('drop_from_high',0)*100:.1f}%，上方套牢冤魂多，慎防A轉逃命波。")
                    if res.get('is_high_vol_drop', False): risk_warnings.append("● 爆量跌破短均線，短線賣壓沉重。")
                    
                    risk_html = f"""
<hr style="border-top: 2px dashed #DC2626; margin: 15px 0;">
<h4 style="margin-top: 0; color: #DC2626;">🚨 第四章：盤中動能警報與洗盤對策</h4>
<div style="background-color: #FEF2F2; border-left: 5px solid #DC2626; padding: 12px; border-radius: 4px; font-size: 0.9rem; color: #7F1D1D; line-height: 1.6;">
    <b>⚠️ 系統降評原因 (最高權重)：</b><br>
    {'<br>'.join(risk_warnings)}<br>
    <i style="color:#B91C1C;">*系統已強制扣減該標的之綜合勝率，確保其退出第一線主將清單。</i><br><br>
    <b>🛑 修正後操作指南：</b><br>
    1. <b>空手者 (取消原伏擊計畫)：</b> 即使股價跌至伏擊區也【嚴禁買進】！因為殺盤動能可能未止。<br>
    2. <b>右側確認標準 (何時可重新關注)：</b> 必須等待 3 日內盤中大單重新「翻紅」，且日線收出「實體紅K」站回短均線，才視為洗盤結束。<br>
    3. <b>已持倉者：</b> 建議立即減碼 1/2 以保全戰果，剩餘部位死守 EMA8 (<b>{res['ema8']:.2f}</b>)。
</div>
"""
                else:
                    ch2_trend = res['trend_status']
                    ch2_tactics = res['action_plan']
                    ch2_timing = res['timing']
                    ch2_discipline = f"跌破防守價 <b>({res['defense']:.2f})</b> 無條件撤退。期望盈虧比 <b>1:{res['rr']:.2f}</b>。"
                    module_s_status = res['module_s_status']
                    module_s_action = res['module_s_action']
                    risk_html = "" 

                report_html = f"""
<div class='report-box'>
<h4 class='report-chapter'>📖 第一章：波動率與量價結構</h4>
<ul class='report-list'>
    <li><b>ATR 日均波動：</b> 約 <b>{res['atr']:.2f} 元</b>。防護網已納入此寬容值以防洗盤。</li>
    <li><b>今日量能狀態：</b> <b>{res['vol_status']}</b><br>(成交: {int(res['vol_today']):,} / 均量: {int(res['vol_ma20']):,})</li>
    <li><b>盤中大單監控：</b> <b style="color:#D97706;">{res.get('tick_status', '無')}</b></li>
    <li><b>短線生命線 (EMA21)：</b> {res['ema21']:.2f} 元。</li>
    <li><b>牛熊分界線 (EMA144)：</b> {res['ema144']:.2f} 元。</li>
</ul>
<hr style='border-top: 1px solid #E2E8F0; margin: 20px 0;'>
<h4 class='report-chapter'>📖 第二章：系統最終戰略指示 ({ch2_trend})</h4>
<div class='report-text'>
    <p style='margin-bottom: 10px;'><b>🎯 戰術定調：</b> {ch2_tactics}</p>
    <p style='margin-bottom: 10px;'><b>⏳ 發動契機：</b> {ch2_timing}</p>
    <p style='margin-bottom: 0;'><b>⚠️ 紀律準則：</b> {ch2_discipline}</p>
</div>
<hr style='border-top: 1px solid #E2E8F0; margin: 20px 0;'>
<h4 class='report-chapter'>🏗️ 第三章：模組 S (波段承重牆)</h4>
<ul class='report-list' style='margin-bottom: 0;'>
    <li><b>波段生命線 (EMA34)：</b> <span style='color:#DC2626; font-weight:bold;'>{res['ema34']:.2f} 元</span></li>
    <li><b>模組狀態：</b> {module_s_status}</li>
    <li><b>執行紀律：</b> {module_s_action}</li>
</ul>
{risk_html}
</div>
"""
                st.markdown(report_html, unsafe_allow_html=True)
                
            except Exception as e:
                st.error(f"執行時發生錯誤: {e}")

if __name__ == "__main__":
    main()
