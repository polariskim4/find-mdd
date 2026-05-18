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
                data = yf.download(ticker_input.strip(), start=start_date, end=end_date)

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
                
                # 기간 설정 (1, 2, 3, 5, 10년)
                periods = {
                    "1년": 365,
                    "2년": 365 * 2,
                    "3년": 365 * 3,
                    "5년": 365 * 5,
                    "10년": 365 * 10
                }

                results = []
                current_date = adj_close.index[-1]

                for label, days in periods.items():
                    target_date = current_date - timedelta(days=days)
                    # 해당 기간만큼 데이터 슬라이싱
                    period_data = adj_close[adj_close.index >= target_date]
                    
                    if len(period_data) > 0:
                        mdd_val = get_mdd(period_data)
                        # Series 형태일 경우 값만 추출
                        if isinstance(mdd_val, pd.Series):
                            mdd_val = mdd_val.iloc[0]
                        results.append({"기간": label, "MDD": f"{mdd_val * 100:.2f}%"})
                    else:
                        results.append({"기간": label, "MDD": "데이터 부족"})

                # 결과 표시 (상단 지표)
                st.subheader(f"📊 {ticker_input} 기간별 MDD 결과")
                cols = st.columns(len(results))
                for i, res in enumerate(results):
                    cols[i].metric(res["기간"], res["MDD"])

                # 테이블 표시
                df_res = pd.DataFrame(results)
                st.table(df_res.set_index("기간"))

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
