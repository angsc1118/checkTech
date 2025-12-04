import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import timedelta

# --- 頁面設定 ---
st.set_page_config(page_title="股市技術情境驗證器", layout="wide")

# --- 核心邏輯：12種情境定義 ---
def get_scenario_analysis(slope, position, alignment):
    """
    根據三個因子返回情境描述與推論
    slope: '上彎', '持平', '下彎'
    position: '之上', '之下'
    alignment: '多頭排列', '無'
    """
    key = (slope, position, alignment)
    
    # 定義 12 種情境 (ID, 描述, 推論, 狀態標籤顏色)
    scenarios = {
        # --- 月線上彎 ---
        ('上彎', '之上', '多頭排列'): (1, "主升段 / 強勢股", "【最強多頭】最佳買點或續抱，拉回不破均線皆是買點。", "🟢 多頭"),
        ('上彎', '之上', '無'):       (2, "初升段 / 震盪走高", "【震盪盤堅】短期強勢，但長線架構未成，短多操作。", "🟡 震盪偏多"),
        ('上彎', '之下', '多頭排列'): (3, "回檔修正 (黃金坑)", "【找買點】俗稱回馬槍。趨勢仍好僅股價回檔，找支撐低接。", "🟢 多頭回檔"),
        ('上彎', '之下', '無'):       (4, "多頭轉弱 / 做頭", "【多單離場】上方無保護，趨勢可能轉弱。", "🟠 轉弱警戒"),
        
        # --- 月線持平 ---
        ('持平', '之上', '多頭排列'): (5, "強勢整理 / 蓄勢", "【準備噴出】賣壓消化完畢，突破前兆。", "🟢 蓄勢待發"),
        ('持平', '之上', '無'):       (6, "箱型整理 (區間上緣)", "【觀望/短打】隨時可能被打回箱型下緣，防假突破。", "⚪ 盤整觀望"),
        ('持平', '之下', '多頭排列'): (7, "假跌破 / 深度洗盤", "【觀察支撐】需在3日內站回，否則破壞結構。", "🟠 觀察支撐"),
        ('持平', '之下', '無'):       (8, "弱勢整理 (區間下緣)", "【偏空看待】無支撐力，容易演變成續跌。", "🔴 盤整偏空"),
        
        # --- 月線下彎 ---
        ('下彎', '之上', '多頭排列'): (9, "矛盾 / 極端V轉", "【罕見/警戒】極短線暴漲，留意劇烈波動 (理論矛盾區)。", "🟣 特殊情境"),
        ('下彎', '之上', '無'):       (10, "空頭反彈 (逃命波)", "【找賣點】蓋頭反壓，容易誘多殺多。", "🔴 空頭反彈"),
        ('下彎', '之下', '多頭排列'): (11, "矛盾 / 急殺", "【結構破壞】多頭遭崩盤式急殺，趨勢毀滅開始 (理論矛盾區)。", "🟣 特殊情境"),
        ('下彎', '之下', '無'):       (12, "主跌段 / 空頭排列", "【絕對空頭】趨勢向下、均線壓制，切勿接刀。", "⚫ 絕對空頭"),
    }
    
    return scenarios.get(key, (0, "未知情境", "無法判斷", "⚪ 未知"))

# --- 主程式 ---
def main():
    st.title("📈 股價技術線型情境驗證 (12 Scenarios)")
    st.markdown("""
    此工具依據 **月線角度**、**股價位置**、**均線排列** 三大因子，自動判定當日屬於哪一種技術面情境。
    """)

    # 1. 側邊欄參數輸入
    with st.sidebar:
        st.header("參數設定")
        ticker = st.text_input("股票代號", value="2330.TW", help="台股請加 .TW (例如 2330.TW)")
        
        # 日期選擇
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_input = st.date_input("起始日期")
        with col_d2:
            end_input = st.date_input("結束日期")
            
        run_btn = st.button("開始分析", type="primary")

    # 2. 驗證邏輯
    date_diff = (end_input - start_input).days
    
    if run_btn:
        if date_diff > 10:
            st.error(f"⚠️ 日期區間過長 ({date_diff} 天)。為了顯示效能，請限制在 10 天以內。")
        elif date_diff < 0:
            st.error("⚠️ 結束日期不能早於起始日期。")
        else:
            analyze_stock(ticker, start_input, end_input)

def analyze_stock(ticker, start_date, end_date):
    try:
        with st.spinner(f'正在分析 {ticker} 的技術線型...'):
            # 3. 資料取得 (多抓 100 天以計算均線)
            fetch_start = start_date - timedelta(days=120)
            # yfinance end date is exclusive
            df = yf.download(ticker, start=fetch_start, end=end_date + timedelta(days=1), progress=False)
            
            if df.empty:
                st.error(f"找不到 {ticker} 的資料，請確認代號是否正確。")
                return
            
            # 處理 MultiIndex Columns (yfinance v0.2+ 可能會出現)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 4. 計算技術指標
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA10'] = df['Close'].rolling(window=10).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean() # 月線
            df['MA60'] = df['Close'].rolling(window=60).mean() # 季線
            
            # 計算月線斜率 (今日MA20 - 昨日MA20)
            df['MA20_Slope_Val'] = df['MA20'].diff()

            # 5. 篩選出使用者指定的日期區間
            # 轉換 index 為 date 物件以便比較
            mask = (df.index.date >= start_date) & (df.index.date <= end_date)
            target_df = df.loc[mask].copy()

            if target_df.empty:
                st.warning("選定區間內無交易資料 (可能是假日)。")
                return

            results = []

            # 6. 逐日判定情境
            for date_idx, row in target_df.iterrows():
                close = row['Close']
                ma5, ma10, ma20, ma60 = row['MA5'], row['MA10'], row['MA20'], row['MA60']
                slope_val = row['MA20_Slope_Val']

                # 判定 A: 月線角度 (設定微小閾值 0.05% 視為持平)
                slope_threshold = ma20 * 0.0005 
                if slope_val > slope_threshold:
                    slope_status = "上彎"
                elif slope_val < -slope_threshold:
                    slope_status = "下彎"
                else:
                    slope_status = "持平"

                # 判定 B: 收盤價與月線
                pos_status = "之上" if close > ma20 else "之下"

                # 判定 C: 均線排列 (四線多頭: 5 > 10 > 20 > 60)
                if (ma5 > ma10) and (ma10 > ma20) and (ma20 > ma60):
                    align_status = "多頭排列"
                else:
                    align_status = "無"

                # 取得情境結論
                sid, desc, conclusion, tag = get_scenario_analysis(slope_status, pos_status, align_status)

                results.append({
                    "日期": date_idx.strftime('%Y-%m-%d'),
                    "收盤價": close,
                    "趨勢標籤": tag,
                    "情境編號": sid,
                    "情境描述": desc,
                    "操作推論": conclusion,
                    # 以下為隱藏欄位供 debug 或進階顯示用
                    "月線斜率": slope_status,
                    "股價位置": pos_status,
                    "均線狀態": align_status
                })

            # 7. 結果呈現
            result_df = pd.DataFrame(results)
            
            # 顯示摘要資訊
            st.subheader(f"📊 {ticker} 分析結果")
            
            # 使用 st.dataframe 進行格式化顯示
            st.dataframe(
                result_df, 
                use_container_width=True,
                column_config={
                    "日期": st.column_config.TextColumn("日期"),
                    "收盤價": st.column_config.NumberColumn("收盤價", format="%.2f"),
                    "情境編號": st.column_config.NumberColumn("ID", width="small"),
                    "情境描述": st.column_config.TextColumn("當下情境", width="medium"),
                    "操作推論": st.column_config.TextColumn("操作推論 (Action)", width="large"),
                    "趨勢標籤": st.column_config.TextColumn("狀態", width="small"),
                },
                hide_index=True
            )

            # 8. 顯示輔助圖表
            st.write("---")
            st.caption("輔助走勢圖 (收盤價 vs 月線 vs 季線)")
            chart_data = target_df[['Close', 'MA20', 'MA60']]
            st.line_chart(chart_data, color=["#FF0000", "#00FF00", "#0000FF"]) # 紅K, 綠月, 藍季

    except Exception as e:
        st.error(f"發生錯誤: {str(e)}")

if __name__ == "__main__":
    main()
