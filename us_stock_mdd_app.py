import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go

def get_mdd(prices):
    """MDD(Maximum Drawdown) 계산 함수"""
    if prices.empty:
        return None
    # 누적 최댓값 계산
    cumulative_max = prices.cummax()
    # 현재가 대비 낙폭 계산
    drawdown = (prices / cumulative_max) - 1.0
    # 최대 낙폭 산출
    mdd = drawdown.min()
    return mdd

def main():
    st.set_page_config(page_title="미국주식 MDD 계산기", layout="wide")

    st.title("🇺🇸 미국 주식 기간별 MDD 계산기")
    st.write("미국 주식 및 ETF의 Ticker를 입력하여 최근 1년부터 10년까지의 최대 낙폭(MDD)을 확인하세요.")

    # 사이드바 입력창
    with st.sidebar:
        st.header("설정")
        ticker_input = st.text_input("Ticker 입력 (예: AAPL, SPY, QQQ)", value="SPY").upper()
        submit = st.button("계산하기")

    if ticker_input:
        with st.spinner(f"{ticker_input} 데이터를 불러오는 중..."):
            try:
                # MDD 계산을 위해 최대 10년 + 여유분 데이터를 가져옴
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365 * 11) # 약 11년치
                
                # Ticker 입력값의 공백 제거 및 데이터 다운로드
                data = yf.download(ticker_input.strip(), start=start_date, end=end_date, progress=False) # progress=False 추가하여 다운로드 메시지 숨김

                if data.empty:
                    st.error("데이터를 찾을 수 없습니다. Ticker를 다시 확인해 주세요.")
                    return
                
                # yfinance 버전에 따라 컬럼이 MultiIndex로 반환되는 경우 처리
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)

                # 'Adj Close'가 없으면 'Close'를 사용하도록 유연하게 대응
                if 'Adj Close' in data.columns:
                    adj_close = data['Adj Close']
                elif 'Close' in data.columns:
                    adj_close = data['Close']
                else:
                    st.error("주가 데이터(Adj Close 또는 Close)를 찾을 수 없습니다.")
                    return
                
                # 데이터가 너무 적으면 오류 방지
                if len(adj_close) < 2:
                    st.error("데이터 포인트가 너무 적어 MDD를 계산할 수 없습니다. 더 긴 기간을 선택하거나 다른 Ticker를 시도해 보세요.")
                    return

                # 기간 설정 (1, 2, 3, 5, 10년)
                periods = {
                    "1년": 365,
                    "2년": 365 * 2,
                    "3년": 365 * 3,
                    "5년": 365 * 5,
                    "10년": 365 * 10 # 10년치 데이터가 없으면 yfinance가 자동으로 가능한 최대치를 가져옴
                }

                results_for_display = []
                results_for_table = []
                current_date = adj_close.index[-1]
                current_price = adj_close.iloc[-1]

                for label, days in periods.items():
                    target_date = current_date - timedelta(days=days)
                    # 해당 기간만큼 데이터 슬라이싱
                    period_data = adj_close[adj_close.index >= target_date]
                    
                    # 해당 기간의 데이터가 충분한지 확인 (최소 2개 이상)
                    if len(period_data) > 1:
                        mdd_val = get_mdd(period_data)
                        # Series 형태일 경우 값만 추출
                        if isinstance(mdd_val, pd.Series):
                            mdd_val = mdd_val.iloc[0]

                        # 해당 기간 내 고점 대비 현재 주가 등락률 계산
                        peak_price_in_period = period_data.max()
                        current_vs_peak_drawdown = (current_price - peak_price_in_period) / peak_price_in_period * 100
                        
                        results_for_display.append({"기간": label, "MDD_Display": f"{mdd_val * 100:.1f}% (<span style='color:red;'>{current_vs_peak_drawdown:.1f}%</span>)"})
                        results_for_table.append({"기간": label, "MDD": f"{mdd_val * 100:.1f}%", "고점대비 등락률": f"{current_vs_peak_drawdown:.1f}%"})
                    else:
                        results_for_display.append({"기간": label, "MDD_Display": "데이터 부족"})
                        results_for_table.append({"기간": label, "MDD": "데이터 부족", "고점대비 등락률": "데이터 부족"})

                # 결과 표시 (상단 지표)
                st.subheader(f"📊 {ticker_input} 기간별 MDD 결과")
                cols = st.columns(len(results_for_display))
                for i, res in enumerate(results_for_display):
                    cols[i].markdown(f"<div style='font-size: 0.9em; color: #666;'>{res['기간']}</div>", unsafe_allow_html=True)
                    cols[i].markdown(f"<div style='font-size: 1.5em; font-weight: bold;'>{res['MDD_Display']}</div>", unsafe_allow_html=True)

                # 테이블 표시
                df_res_table = pd.DataFrame(results_for_table)
                st.table(df_res_table.set_index("기간"))

                # 차트 시각화
                st.subheader("📈 주가 흐름 (최근 10년)")
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=adj_close.index, y=adj_close.values.flatten(), mode='lines', name='Adj Close'))
                fig.update_layout(
                    hovermode='x unified',
                    xaxis_title="날짜",
                    yaxis_title="주가 (USD)",
                    template="plotly_white"
                )
                st.plotly_chart(fig, use_container_width=True)

                # 드로우다운 차트 (최근 10년 기준)
                st.subheader("📉 Drawdown (낙폭) 차트")
                cum_max_10y = adj_close.cummax()
                drawdown_10y = (adj_close / cum_max_10y) - 1.0
                
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(x=drawdown_10y.index, y=drawdown_10y.values.flatten() * 100, 
                                            fill='tozeroy', mode='lines', name='Drawdown (%)', line=dict(color='red')))
                fig_dd.update_layout(
                    xaxis_title="날짜",
                    yaxis_title="낙폭 (%)",
                    template="plotly_white"
                )
                st.plotly_chart(fig_dd, use_container_width=True)

            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
