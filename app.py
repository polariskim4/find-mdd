import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
import streamlit as st
from bs4 import BeautifulSoup

BENCHMARK_STOCKS = [
    {"code": "005930", "name": "삼성전자"},
    {"code": "000660", "name": "SK하이닉스"},
    {"code": "005380", "name": "현대차"},
    {"code": "373220", "name": "LG에너지솔루션"},
    {"code": "105560", "name": "KB금융"},
    {"code": "000720", "name": "현대건설"},
    {"code": "034020", "name": "두산에너빌리티"},
    {"code": "196170", "name": "알테오젠"},
    {"code": "247540", "name": "에코프로비엠"},
    {"code": "240810", "name": "원익IPS"},
]

COMPANY_FILE = Path("krx_list.json")
NAVER_SUMMARY_URL = "https://api.finance.naver.com/service/itemSummary.naver?itemcode={code}"
NAVER_COMP_URL = (
    "https://navercomp.wisereport.co.kr/v2/company/ajax/cF1001.aspx?"
    "cmp_cd={code}&fin_typ=4&freq_typ=Y&extY=0&extQ=0&"
    "encparam=ZVlSV1hTL1ZESGlaeUhIdXo4ZXVMQT09"
)
CHART_URL = (
    "https://ssl.pstatic.net/imgfinance/chart/item/candle/month/{code}.png?"
    "sidcode=1588806284147"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", (text or "")).lower()


@st.cache_data(show_spinner=False)
def load_companies():
    if not COMPANY_FILE.exists():
        st.error("krx_list.json 파일을 찾을 수 없습니다.")
        return []

    data = json.loads(COMPANY_FILE.read_text(encoding="utf-8"))
    return [
        {
            "company_name": item.get("companyName", ""),
            "market": item.get("market", ""),
            "code": item.get("code", ""),
            "normalized_name": normalize(item.get("companyName", "")),
        }
        for item in data
    ]


def search_company(query: str, companies: list[dict]):
    q = normalize(query)
    if not q:
        return None

    exact = next((c for c in companies if c["normalized_name"] == q), None)
    if exact:
        return exact

    if query.isdigit():
        exact_code = next((c for c in companies if c["code"] == query), None)
        if exact_code:
            return exact_code

    partial = next(
        (c for c in companies if q in c["normalized_name"] or q in c["code"]),
        None,
    )
    return partial


def parse_number(value):
    if value is None:
        return None
    text = re.sub(r"[^0-9.\-]", "", str(value))
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def format_korean_won(value):
    if value is None:
        return None
    try:
        amount = int(round(abs(float(value))))
    except (TypeError, ValueError):
        return None
    sign = "-" if float(value) < 0 else ""
    jo = amount // 10000
    eok = amount % 10000
    if jo > 0:
        if eok >= 1000:
            eok_formatted = f"{eok:,}"
        else:
            eok_formatted = str(eok).zfill(4)
        return f"{sign}{jo:,}조 {eok_formatted}억원"
    return f"{sign}{amount:,}억원"


def format_percent(value, digits=1):
    if value is None:
        return "정보 없음"
    try:
        return f"{float(value):.{digits}f}%"
    except (TypeError, ValueError):
        return "정보 없음"


def format_decimal(value, digits=1):
    if value is None:
        return "정보 없음"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "정보 없음"


def fetch_item_summary(code: str):
    url = NAVER_SUMMARY_URL.format(code=code)
    headers = {**HEADERS, "Referer": f"https://finance.naver.com/item/main.nhn?code={code}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def parse_navercomp_financials(html: str):
    soup = BeautifulSoup(html, "html.parser")
    table = None
    for candidate in soup.find_all("table"):
        if candidate.find(text="매출액"):
            table = candidate
            break

    if table is None:
        return None

    rows = []
    for tr in table.find_all("tr"):
        cells = [cell.get_text(strip=True).replace("\xa0", " ") for cell in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)

    header = next((row for row in rows if any(re.match(r"\d{4}/\d{2}", cell) for cell in row)), None)
    if header is None:
        return None

    years = [cell.strip() for cell in header[1:]]
    data = {}
    for row in rows:
        if row == header or not row[0] or re.match(r"\d{4}/\d{2}", row[0]):
            continue
        key = row[0].replace(" ", "")
        data[key] = [parse_number(cell) for cell in row[1 : 1 + len(years)]]

    revenue = data.get("매출액")
    operating_profit = data.get("영업이익")
    if not revenue or not operating_profit:
        return None

    actual_indices = [i for i, year in enumerate(years) if not re.search(r"\(E\)|\bE\b", year)]
    last = actual_indices[-1] if actual_indices else len(years) - 1
    prior = actual_indices[-2] if len(actual_indices) >= 2 else max(0, last - 1)

    latest_revenue = revenue[last]
    prior_revenue = revenue[prior]
    latest_profit = operating_profit[last]
    prior_profit = operating_profit[prior]

    revenue_growth = (
        (latest_revenue - prior_revenue) / prior_revenue * 100 if prior_revenue and prior_revenue > 0 else None
    )
    profit_growth = (
        (latest_profit - prior_profit) / prior_profit * 100 if prior_profit and prior_profit > 0 else None
    )
    operating_margin = (latest_profit / latest_revenue * 100 if latest_revenue and latest_revenue > 0 else None)

    return {
        "revenue": format_korean_won(latest_revenue),
        "operating_profit": format_korean_won(latest_profit),
        "operating_margin": format_percent(operating_margin),
        "revenue_growth": format_percent(revenue_growth),
        "profit_growth": format_percent(profit_growth),
    }


def fetch_navercomp_financials(code: str):
    url = NAVER_COMP_URL.format(code=code)
    headers = {**HEADERS, "Referer": f"https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={code}"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return parse_navercomp_financials(resp.text)


@st.cache_data(show_spinner=False)
def get_stock_metrics(code: str):
    summary = fetch_item_summary(code)
    financials = fetch_navercomp_financials(code)

    market_sum = summary.get("marketSum")
    market_cap_value = float(market_sum) / 100 if market_sum is not None else None
    market_cap = format_korean_won(market_cap_value)

    return {
        "market_cap": market_cap or "정보 없음",
        "market_cap_value": market_cap_value or 0,
        "per": format_decimal(summary.get("per"), 1),
        "pbr": format_decimal(summary.get("pbr"), 1),
        "revenue": financials["revenue"] if financials else "정보 없음",
        "operating_profit": financials["operating_profit"] if financials else "정보 없음",
        "operating_margin": financials["operating_margin"] if financials else "정보 없음",
        "revenue_growth": financials["revenue_growth"] if financials else "정보 없음",
        "profit_growth": financials["profit_growth"] if financials else "정보 없음",
        "naver_link": f"https://finance.naver.com/item/main.nhn?code={code}",
    }


def get_monthly_chart_url(code: str) -> str:
    return f"https://ssl.pstatic.net/imgfinance/chart/item/candle/month/{code}.png?sidcode=1588806284147"


def render_page_style():
    st.markdown(
        """
        <style>
        .search-result-box {
            border: 1px solid #e2e8f0;
            border-radius: 18px;
            padding: 18px;
            background: #f8fafc;
            margin-bottom: 24px;
        }
        .search-result-box h2 {
            margin: 0 0 12px;
        }
        .search-result-row {
            display: flex;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 14px;
        }
        .search-result-label {
            color: #475569;
            font-weight: 700;
        }
        .search-result-value {
            font-size: 1.05rem;
            font-weight: 700;
            text-align: right;
            white-space: nowrap;
        }
        .benchmark-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 18px;
        }
        .benchmark-table th,
        .benchmark-table td {
            border: 1px solid #e2e8f0;
            padding: 10px 12px;
        }
        .benchmark-table th {
            background: #f8fafc;
            text-align: left;
            font-weight: 700;
        }
        .benchmark-table td {
            text-align: right;
        }
        .benchmark-table td:first-child {
            text-align: left;
        }
        .benchmark-table .highlight-row {
            background: #eef2ff;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_stock_data(stock, metrics):
    st.markdown(
        f"""
        <div class='search-result-box'>
          <h2>{stock['company_name']} ({stock['code']})</h2>
          <div class='search-result-row'>
            <div>
              <div class='search-result-label'>시장</div>
              <div class='search-result-value'>{stock['market']}</div>
            </div>
            <div>
              <div class='search-result-label'>네이버증권</div>
              <div class='search-result-value'><a href='{metrics['naver_link']}' target='_blank' rel='noopener noreferrer'>바로가기</a></div>
            </div>
          </div>
          <div class='search-result-row'>
            <div>
              <div class='search-result-label'>시가총액</div>
              <div class='search-result-value'>{metrics['market_cap']}</div>
            </div>
            <div>
              <div class='search-result-label'>PER</div>
              <div class='search-result-value'>{metrics['per']}</div>
            </div>
            <div>
              <div class='search-result-label'>PBR</div>
              <div class='search-result-value'>{metrics['pbr']}</div>
            </div>
          </div>
          <div class='search-result-row'>
            <div>
              <div class='search-result-label'>매출액</div>
              <div class='search-result-value'>{metrics['revenue']}</div>
            </div>
            <div>
              <div class='search-result-label'>영업이익</div>
              <div class='search-result-value'>{metrics['operating_profit']}</div>
            </div>
            <div>
              <div class='search-result-label'>영업이익률</div>
              <div class='search-result-value'>{metrics['operating_margin']}</div>
            </div>
          </div>
          <div class='search-result-row'>
            <div>
              <div class='search-result-label'>매출성장률</div>
              <div class='search-result-value'>{metrics['revenue_growth']}</div>
            </div>
            <div>
              <div class='search-result-label'>이익성장률</div>
              <div class='search-result-value'>{metrics['profit_growth']}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 네이버 월봉 차트")
    st.image(get_monthly_chart_url(stock['code']), caption="네이버 월봉 차트", use_container_width=True)


@st.cache_data(show_spinner=False)
def load_benchmark_metrics():
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_stock = {
            executor.submit(get_stock_metrics, stock['code']): stock
            for stock in BENCHMARK_STOCKS
        }
        for future in as_completed(future_to_stock):
            stock = future_to_stock[future]
            try:
                bench_metrics = future.result()
                results.append(
                    {
                        "종목": stock["name"],
                        "시가총액": bench_metrics["market_cap"],
                        "매출액": bench_metrics["revenue"],
                        "영업이익": bench_metrics["operating_profit"],
                        "PER": bench_metrics["per"],
                        "PBR": bench_metrics["pbr"],
                        "영업이익률": bench_metrics["operating_margin"],
                        "매출성장률": bench_metrics["revenue_growth"],
                        "이익성장률": bench_metrics["profit_growth"],
                        "시장값": bench_metrics["market_cap_value"],
                    }
                )
            except Exception:
                results.append(
                    {
                        "종목": stock["name"],
                        "시가총액": "조회 실패",
                        "매출액": "-",
                        "영업이익": "-",
                        "PER": "-",
                        "PBR": "-",
                        "영업이익률": "-",
                        "매출성장률": "-",
                        "이익성장률": "-",
                        "시장값": 0,
                    }
                )
    return results


def render_benchmark_table(search_stock, metrics):
    rows = load_benchmark_metrics()
    rows.append(
        {
            "종목": f"{search_stock['company_name']} (검색)",
            "시가총액": metrics["market_cap"],
            "매출액": metrics["revenue"],
            "영업이익": metrics["operating_profit"],
            "PER": metrics["per"],
            "PBR": metrics["pbr"],
            "영업이익률": metrics["operating_margin"],
            "매출성장률": metrics["revenue_growth"],
            "이익성장률": metrics["profit_growth"],
            "시장값": metrics["market_cap_value"],
        }
    )

    rows.sort(key=lambda row: row["시장값"] or 0, reverse=True)

    header_cells = [
        "종목",
        "시가총액",
        "매출액",
        "영업이익",
        "PER",
        "PBR",
        "영업이익률",
        "매출성장률",
        "이익성장률",
    ]

    body_html = ""
    for row in rows:
        highlight = "highlight-row" if row["종목"].endswith("(검색)") else ""
        body_html += "<tr class='{}'>".format(highlight)
        body_html += f"<td>{row['종목']}</td>"
        for key in header_cells[1:]:
            body_html += f"<td>{row[key]}</td>"
        body_html += "</tr>"

    table_html = f"""
    <div>
      <h3>벤치마크 종목</h3>
      <p>검색 종목을 포함한 벤치마크 종목 비교표입니다.</p>
      <table class='benchmark-table'>
        <thead>
          <tr>{''.join(f'<th>{h}</th>' for h in header_cells)}</tr>
        </thead>
        <tbody>
          {body_html}
        </tbody>
      </table>
    </div>
    """

    st.markdown(table_html, unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="한국 주식 재무 정보 조회", layout="wide")
    render_page_style()
    st.title("한국 주식 재무 정보 조회")
    st.write("KRX 한글 종목명을 입력하면 Naver 금융 데이터를 기반으로 주요 지표를 조회합니다.")

    companies = load_companies()
    with st.form(key="search_form"):
        query = st.text_input("종목명 또는 종목코드", "")
        submit = st.form_submit_button("조회")

    if not submit:
        st.info("종목명을 입력하고 조회 버튼을 클릭하면 벤치마크 비교가 표시됩니다.")
        return

    if not query.strip():
        st.warning("종목명을 입력해 주세요.")
        return

    stock = search_company(query, companies)
    if not stock:
        st.error("검색 결과가 없습니다. 정확한 한글 종목명을 입력해 주세요.")
        return

    with st.spinner("데이터를 불러오는 중입니다..."):
        try:
            metrics = get_stock_metrics(stock["code"])
        except Exception as exc:
            st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {exc}")
            return

    render_stock_data(stock, metrics)
    render_benchmark_table(stock, metrics)


if __name__ == "__main__":
    main()
