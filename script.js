const form = document.getElementById('search-form');
const stockNameInput = document.getElementById('stock-name');
const resultSection = document.getElementById('result');
const messageText = document.getElementById('message');
const resultName = document.getElementById('result-name');
const resultMarketcap = document.getElementById('result-marketcap');
const resultRevenue = document.getElementById('result-revenue');
const resultOperatingProfit = document.getElementById('result-operating-profit');
const resultPer = document.getElementById('result-per');
const resultPbr = document.getElementById('result-pbr');
const resultOperatingMargin = document.getElementById('result-operating-margin');
const resultRevenueGrowth = document.getElementById('result-revenue-growth');
const resultProfitGrowth = document.getElementById('result-profit-growth');
const resultNaverLink = document.getElementById('result-naver-link');
const chartImage = document.getElementById('monthly-chart-img');
const benchmarkSection = document.getElementById('benchmark');
const benchmarkMessage = document.getElementById('benchmark-message');
const benchmarkTableBody = document.querySelector('#benchmark-table tbody');

let benchmarkItems = [];
let latestSearchStock = null;
let benchmarkReady = false;

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const query = stockNameInput.value.trim();
  if (!query) {
    showMessage('종목명을 입력해주세요.');
    hideResult();
    return;
  }

  showMessage('조회 중입니다...');
  hideResult();

  try {
    const searchRes = await fetch(`/api/search?query=${encodeURIComponent(query)}`);
    if (!searchRes.ok) {
      const errorData = await searchRes.json();
      showMessage(errorData.error || '종목을 찾을 수 없습니다.');
      return;
    }

    const searchData = await searchRes.json();
    const stockRes = await fetch(`/api/stock?code=${encodeURIComponent(searchData.code)}`);
    if (!stockRes.ok) {
      const errorData = await stockRes.json();
      showMessage(errorData.error || '데이터를 가져오지 못했습니다.');
      return;
    }

    const stockData = await stockRes.json();
    showStock(stockData, searchData.name, searchData.code);
  } catch (error) {
    showMessage('서버와 통신할 수 없습니다. 서버를 실행했는지 확인하세요.');
  }
});

async function loadBenchmarks() {
  try {
    const res = await fetch('/api/benchmarks');
    if (!res.ok) {
      benchmarkMessage.textContent = '벤치마크 정보를 불러올 수 없습니다.';
      return;
    }
    benchmarkItems = await res.json();
    benchmarkReady = true;
    if (latestSearchStock) {
      renderBenchmarkTable(benchmarkItems, latestSearchStock);
      benchmarkSection.classList.remove('hidden');
    }
  } catch (error) {
    benchmarkMessage.textContent = '벤치마크 정보를 불러올 수 없습니다.';
  }
}

function renderBenchmarkTable(items, searchStock = null) {
  const sortedItems = [...items].sort((a, b) => (b.marketCapValue || 0) - (a.marketCapValue || 0));
  const rows = sortedItems.map(item => {
    if (item.error) {
      return `<tr><td>${escapeHtml(item.name)}</td><td colspan="9">${escapeHtml(item.error)}</td></tr>`;
    }
    return `<tr>
      <td>${escapeHtml(item.name)}</td>
      <td>${escapeHtml(item.marketCap || '정보 없음')}</td>
      <td>${escapeHtml(item.revenue || '정보 없음')}</td>
      <td>${escapeHtml(item.operatingProfit || '정보 없음')}</td>
      <td>${escapeHtml(item.per || '정보 없음')}</td>
      <td>${escapeHtml(item.pbr || '정보 없음')}</td>
      <td>${escapeHtml(item.operatingMargin || '정보 없음')}</td>
      <td>${escapeHtml(item.revenueGrowth || '정보 없음')}</td>
      <td>${escapeHtml(item.profitGrowth || '정보 없음')}</td>
    </tr>`;
  });

  if (searchStock) {
    rows.push(`<tr class="highlight">
      <td>${escapeHtml(searchStock.name)} (검색)</td>
      <td>${escapeHtml(searchStock.marketCap || '정보 없음')}</td>
      <td>${escapeHtml(searchStock.revenue || '정보 없음')}</td>
      <td>${escapeHtml(searchStock.operatingProfit || '정보 없음')}</td>
      <td>${escapeHtml(searchStock.per || '정보 없음')}</td>
      <td>${escapeHtml(searchStock.pbr || '정보 없음')}</td>
      <td>${escapeHtml(searchStock.operatingMargin || '정보 없음')}</td>
      <td>${escapeHtml(searchStock.revenueGrowth || '정보 없음')}</td>
      <td>${escapeHtml(searchStock.profitGrowth || '정보 없음')}</td>
    </tr>`);
  }

  benchmarkTableBody.innerHTML = rows.join('');
}

function showStock(stock, name, code) {
  resultName.textContent = name;
  resultMarketcap.textContent = stock.marketCap || '정보 없음';
  resultRevenue.textContent = stock.revenue || '정보 없음';
  resultOperatingProfit.textContent = stock.operatingProfit || '정보 없음';
  resultPer.textContent = stock.per || '정보 없음';
  resultPbr.textContent = stock.pbr || '정보 없음';
  resultOperatingMargin.textContent = stock.operatingMargin || '정보 없음';
  resultRevenueGrowth.textContent = stock.revenueGrowth || '정보 없음';
  resultProfitGrowth.textContent = stock.profitGrowth || '정보 없음';
  resultNaverLink.href = stock.naverLink || '#';
  resultNaverLink.textContent = stock.naverLink ? '네이버증권 열기' : '정보 없음';
  chartImage.src = getNaverMonthlyChartUrl(code);
  chartImage.alt = `${name} 네이버 월봉 차트`;
  messageText.textContent = '';
  resultSection.classList.remove('hidden');

  latestSearchStock = {
    code,
    name,
    marketCap: stock.marketCap,
    marketCapValue: stock.marketCapValue,
    revenue: stock.revenue,
    operatingProfit: stock.operatingProfit,
    per: stock.per,
    pbr: stock.pbr,
    operatingMargin: stock.operatingMargin,
    revenueGrowth: stock.revenueGrowth,
    profitGrowth: stock.profitGrowth
  };

  if (benchmarkReady) {
    renderBenchmarkTable(benchmarkItems, latestSearchStock);
    benchmarkSection.classList.remove('hidden');
  }
}

function getNaverMonthlyChartUrl(code) {
  return `https://ssl.pstatic.net/imgfinance/chart/item/candle/month/${code}.png?sidcode=${Date.now()}`;
}

function hideResult() {
  resultSection.classList.add('hidden');
}

function showMessage(text) {
  messageText.textContent = text;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

loadBenchmarks();
