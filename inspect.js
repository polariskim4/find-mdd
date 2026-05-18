const fs = require('fs');
const cheerio = require('cheerio');
const s = fs.readFileSync('naver-fincf1001.html', 'utf8');
const $ = cheerio.load(s);
const spans = $('span');
console.log('spans', spans.length);
const classes = new Set();
spans.each((i, el) => {
  if (el.attribs && el.attribs.class) classes.add(el.attribs.class);
  if (i < 20) console.log(i, $.html(el));
});
console.log('classes', Array.from(classes).slice(0, 50));
