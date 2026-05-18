const express = require('express');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const cheerio = require('cheerio');

const app = express();
const PORT = process.env.PORT || 3000;
const DATA_FILE = path.resolve(__dirname, 'krx_list.json');

const BENCHMARK_STOCKS = [
  { code: '005930', name: '삼성전자' },
  { code: '000660', name: 'SK하이닉스' },
  { code: '005380', name: '현대차' },
  { code: '373220', name: 'LG에너지솔루션' },
  { code: '105560', name: 'KB금융' },
  { code: '000720', name: '현대건설' },
  { code: '034020', name: '두산에너빌리티' },
  { code: '196170', name: '알테오젠' },
  { code: '247540', name: '에코프로비엠' },
  { code: '240810', name: '원익IPS' }
];

let companies = [];

function normalize(text) {
  return text ? text.replace(/\s+/g, '').toLowerCase() : '';
}

function formatMarketCap(value) {
  if (value == null || Number.isNaN(Number(value))) return null;
  // Naver itemSummary.marketSum is returned in 100,000 KRW units,
  // so convert to 억원 before formatting.
  return formatKoreanWon(Number(value) / 100);
}

function parseNumber(value) {
  if (value == null) return null;
  const text = value.toString().replace(/[^0-9.-]/g, '');
  if (!text) return null;
  const num = Number(text);
  return Number.isNaN(num) ? null : num;
}

function formatPercent(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return null;
  return `${Number(value).toFixed(digits)}%`;
}

function formatDecimal(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return null;
  return Number(value).toFixed(digits);
}

function formatKoreanWon(value) {
  if (value == null || Number.isNaN(Number(value))) return null;
  const amount = Math.abs(Math.floor(Number(value)));
  const jo = Math.floor(amount / 10000);
  const eok = amount % 10000;
  const sign = Number(value) < 0 ? '-' : '';
  if (jo > 0) {
    const eokFormatted = eok >= 1000 ? eok.toLocaleString('en-US') : String(eok).padStart(4, '0');
    return `${sign}${jo.toLocaleString()}조 ${eokFormatted}억원`;
  }
  return `${sign}${amount.toLocaleString()}억원`;
}

function formatLargeNumber(value) {
  if (value == null || Number.isNaN(Number(value))) return null;
  return Number(value).toLocaleString('en-US');
}

function getLatestActualIndexes(years) {
  const actualYears = years
    .map((year, index) => ({ year, index }))
    .filter(({ year }) => !/\(E\)|\bE\b/.test(year));
  if (actualYears.length >= 2) {
    return [actualYears[actualYears.length - 1].index, actualYears[actualYears.length - 2].index];
  }
  const last = years.length - 1;
  return [last, Math.max(0, last - 1)];
}

function parseNaverCompFinancials(html) {
  const $ = cheerio.load(html);
  const table = $('table').toArray().find(table => {
    return $(table).find('td,th').filter((_, cell) => $(cell).text().trim() === '매출액').length > 0;
  });

  if (!table) return null;

  const rows = $(table)
    .find('tr')
    .toArray()
    .map(tr =>
      $(tr)
        .find('th,td')
        .toArray()
        .map(cell => $(cell).text().trim().replace(/\s+/g, ' '))
    );

  const headerRow = rows.find(row => row.some(cell => /\d{4}\/\d{2}/.test(cell)));
  if (!headerRow) return null;

  const years = headerRow.slice(1).map(cell => cell.trim());
  const dataRows = rows.filter(row => row[0] && row[0] !== headerRow[0] && !/\d{4}\/\d{2}/.test(row[0]) && row.length > 1);
  const rowMap = dataRows.reduce((acc, row) => {
    const label = row[0].replace(/\s+/g, '');
    acc[label] = row.slice(1, 1 + years.length).map(parseNumber);
    return acc;
  }, {});

  const revenue = rowMap['매출액'];
  const operatingProfit = rowMap['영업이익'];
  if (!revenue || !operatingProfit) return null;

  const [lastIndex, priorIndex] = getLatestActualIndexes(years);
  const latestRevenue = revenue[lastIndex];
  const priorRevenue = revenue[priorIndex];
  const latestProfit = operatingProfit[lastIndex];
  const priorProfit = operatingProfit[priorIndex];

  const revenueGrowth = priorRevenue > 0 ? ((latestRevenue - priorRevenue) / priorRevenue) * 100 : null;
  const profitGrowth = priorProfit > 0 ? ((latestProfit - priorProfit) / priorProfit) * 100 : null;
  const operatingMargin = latestRevenue > 0 ? (latestProfit / latestRevenue) * 100 : null;

  return {
    revenue: formatKoreanWon(latestRevenue),
    operatingProfit: formatKoreanWon(latestProfit),
    operatingMargin: formatPercent(operatingMargin),
    revenueGrowth: formatPercent(revenueGrowth),
    profitGrowth: formatPercent(profitGrowth),
    rawRevenueGrowth: revenueGrowth,
    rawProfitGrowth: profitGrowth
  };
}

async function fetchNaverCompFinancials(code) {
  const referer = `https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd=${code}`;
  const url = `https://navercomp.wisereport.co.kr/v2/company/ajax/cF1001.aspx?cmp_cd=${code}&fin_typ=4&freq_typ=Y&extY=0&extQ=0&encparam=ZVlSV1hTL1ZESGlaeUhIdXo4ZXVMQT09`;
  const response = await axios.get(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0',
      Referer: referer
    }
  });
  return parseNaverCompFinancials(response.data);
}

async function getStockMetrics(code) {
  const summaryUrl = `https://api.finance.naver.com/service/itemSummary.naver?itemcode=${code}`;
  const [summaryRes, financials] = await Promise.all([
    axios.get(summaryUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0',
        Referer: `https://finance.naver.com/item/main.nhn?code=${code}`
      }
    }),
    fetchNaverCompFinancials(code)
  ]);

  const summary = summaryRes.data;
  const perValue = summary.per != null ? Number(summary.per) : null;
  const pbrValue = summary.pbr != null ? Number(summary.pbr) : null;

  return {
    marketCap: formatMarketCap(summary.marketSum),
    marketCapValue: Number(summary.marketSum) / 100,
    per: perValue != null ? formatDecimal(perValue, 1) : null,
    pbr: pbrValue != null ? formatDecimal(pbrValue, 1) : null,
    revenue: financials.revenue,
    operatingProfit: financials.operatingProfit,
    operatingMargin: financials.operatingMargin,
    revenueGrowth: financials.revenueGrowth,
    profitGrowth: financials.profitGrowth,
    naverLink: `https://finance.naver.com/item/main.nhn?code=${code}`
  };
}

async function loadCompanies() {
  try {
    const content = fs.readFileSync(DATA_FILE, 'utf-8');
    companies = JSON.parse(content).map(item => ({
      ...item,
      normalizedName: normalize(item.companyName)
    }));
    console.log(`Loaded ${companies.length} companies from KRX JSON list.`);
  } catch (err) {
    console.error('Failed to load KRX list:', err.message);
    companies = [];
  }
}

app.use(express.static(path.join(__dirname)));

app.get('/api/search', (req, res) => {
  const query = (req.query.query || '').trim();
  if (!query) {
    return res.status(400).json({ error: 'query parameter required' });
  }
  const normalized = normalize(query);
  let company = companies.find(item => item.normalizedName === normalized);
  if (!company) {
    company = companies.find(item => item.normalizedName.includes(normalized));
  }
  if (!company) {
    const names = companies.slice(0, 30).map(item => item.companyName);
    return res.status(404).json({ error: '종목을 찾을 수 없습니다.', supported: names });
  }
  res.json({ code: company.code, name: company.companyName, market: company.market });
});

app.get('/api/stock', async (req, res) => {
  const code = (req.query.code || '').trim();
  if (!code) {
    return res.status(400).json({ error: 'code parameter required' });
  }
  try {
    const metrics = await getStockMetrics(code, true);
    res.json(metrics);
  } catch (error) {
    console.error('Stock fetch error:', error.message);
    res.status(500).json({ error: '종목 데이터를 가져오는 데 실패했습니다.' });
  }
});

app.get('/api/benchmarks', async (req, res) => {
  try {
    const items = await Promise.all(BENCHMARK_STOCKS.map(async stock => {
      try {
        const metrics = await getStockMetrics(stock.code, false);
        return { code: stock.code, name: stock.name, ...metrics };
      } catch (error) {
        return { code: stock.code, name: stock.name, error: '데이터 조회 실패' };
      }
    }));
    res.json(items);
  } catch (error) {
    console.error('Benchmark fetch error:', error.message);
    res.status(500).json({ error: '벤치마크 데이터를 가져오는 데 실패했습니다.' });
  }
});

loadCompanies().then(() => {
  app.listen(PORT, () => console.log(`Server listening on http://localhost:${PORT}`));
});
