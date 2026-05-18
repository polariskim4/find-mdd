const fs = require('fs');
const cheerio = require('cheerio');
const s = fs.readFileSync('naver-fincf1001.html', 'utf8');
const $ = cheerio.load(s);
$('table').each((ti, table)=>{
  console.log('TABLE', ti, 'caption', $(table).find('caption').text().trim());
  $(table).find('tr').slice(0,12).each((ri, tr)=>{
    const row = $(tr).find('th,td').map((i, cell)=>$(cell).text().trim()).get().join(' | ');
    console.log('ROW', ri, row);
  });
  console.log('----');
});
