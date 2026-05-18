const axios = require('axios');
(async()=>{
  const url='https://navercomp.wisereport.co.kr/common/BandChart3.aspx?cmp_cd=005930&gubun=1';
  try {
    const res = await axios.get(url, { headers: { 'User-Agent':'Mozilla/5.0', Referer:'https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd=005930' }, responseType:'text' });
    console.log('status', res.status, 'len', res.data.length);
    console.log(res.data.slice(0,200));
    const data = JSON.parse(res.data);
    console.log('keys', Object.keys(data));
    console.log('price len', data.bandChart1.price.length);
  } catch(e) {
    console.error('err', e.message);
    if(e.response){ console.error('status', e.response.status, 'len', e.response.data && e.response.data.length); }
  }
})();
