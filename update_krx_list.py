import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

KRX_LIST_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
OUTPUT_FILE = Path("krx_list.json")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}


def fetch_krx_list():
    response = requests.get(KRX_LIST_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    text = response.content.decode("euc-kr", errors="ignore")
    soup = BeautifulSoup(text, "html.parser")
    table = soup.find("table", class_="bbs_tb")
    if table is None:
        raise RuntimeError("KRX company list table not found in downloaded data.")

    companies = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        name = cells[0].get_text(strip=True)
        market = cells[1].get_text(strip=True)
        code = cells[2].get_text(strip=True)
        if not name or not code:
            continue
        companies.append({"companyName": name, "market": market, "code": code})

    return companies


def save_json(companies):
    OUTPUT_FILE.write_text(json.dumps(companies, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    companies = fetch_krx_list()
    if not companies:
        raise RuntimeError("No companies were parsed from the KRX list download.")

    save_json(companies)
    print(f"Saved {len(companies)} companies to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
