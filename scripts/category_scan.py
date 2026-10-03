"""Aday sitelerin ana sayfasını paralel indirip menü/kategori linklerinde markanın dikeyine
karşılık gelen kategoriyi arar. Kategori eşleşmesi kuralının ilk, toplu elemesidir; çıkan eşleşmeler
sunumdan önce yine WebFetch ile (menüde gerçekten kategori mi, sayfa içi blok mu) teyit edilir.

Kullanım:
    python category_scan.py --in candidates.csv --terms "guzellik,makyaj,cilt-bakimi,kozmetik" \
        [--max-price 7750] [--min-price 0] [--workers 24] --out category_hits.csv

Çıktı: domain, sale_price, link_count, source, status, matches (bulunan kategori URL'leri), bahis_sinyali,
      haber_menusu / haber_sitesi (Gündem, Son Dakika, Asayiş, Siyaset... menüsü: haber sitesi, ana plana alınmaz)
"""
import argparse
import concurrent.futures as cf
import re
import ssl
import urllib.request
from urllib.parse import urljoin, urlparse

import pandas as pd

UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'
BET = re.compile(r'(bahis|casino|iddaa|deneme bonusu|slot oyun|canlı bahis|bet[0-9]{2,})', re.I)
NEWS_MENU = ['gundem', 'son-dakika', 'sondakika', 'asayis', 'siyaset', 'politika', 'yerel', 'dunya', 'turkiye',
             'ekonomi', 'spor', 'resmi-ilanlar', 'yazarlar', 'koseyazarlari']
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def tr_fold(s):
    return (s.lower().replace('ı', 'i').replace('ğ', 'g').replace('ü', 'u').replace('ş', 's')
            .replace('ö', 'o').replace('ç', 'c').replace('İ', 'i'))


def fetch(domain, timeout=12):
    for url in (f'https://www.{domain}/', f'https://{domain}/'):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept-Language': 'tr-TR,tr;q=0.9'})
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.status, r.geturl(), r.read(800_000).decode('utf-8', 'ignore')
        except Exception as e:  # noqa: BLE001
            err = str(e)[:60]
    return None, None, err


def scan(domain, terms):
    status, final, html = fetch(domain)
    if status is None:
        return {'domain': domain, 'status': f'hata: {html}', 'matches': '', 'bahis_sinyali': ''}
    host = urlparse(final).netloc
    hits = set()
    for href, text in re.findall(r'<a[^>]+href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        full = urljoin(final, href)
        if urlparse(full).netloc not in (host, host.replace('www.', ''), 'www.' + host):
            continue
        path = tr_fold(urlparse(full).path)
        label = tr_fold(re.sub(r'<[^>]+>', ' ', text)).strip()
        # kategori benzeri kısa yol: /guzellik, /kategori/guzellik/makyaj, /haberler/guzellik/ ...
        if path.count('/') > 5 or re.search(r'\d{4,}', path):
            continue
        for t in terms:
            if re.search(rf'(^|/|-){re.escape(t)}(/|-|$)', path) or (len(label) < 30 and t.replace('-', ' ') in label):
                hits.add(full.split('?')[0])
    bet = BET.findall(html)
    paths = {tr_fold(urlparse(urljoin(final, h)).path).strip('/').split('/')[-1]
             for h in re.findall(r'<a[^>]+href=["\']([^"\'#]+)', html, re.I)}
    news_hits = [n for n in NEWS_MENU if any(p == n or p.startswith(n + '-') or p.endswith('-' + n) for p in paths)]
    return {'domain': domain, 'status': status, 'matches': ' | '.join(sorted(hits)[:6]),
            'bahis_sinyali': ','.join(sorted({b.lower() for b in bet}))[:60],
            'haber_menusu': len(news_hits) >= 3}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--terms', required=True, help='Virgüllü, Türkçe karakter katlanmış (guzellik,makyaj,cilt-bakimi)')
    ap.add_argument('--max-price', type=float, default=1e12)
    ap.add_argument('--min-price', type=float, default=0)
    ap.add_argument('--workers', type=int, default=24)
    ap.add_argument('--out', default='category_hits.csv')
    a = ap.parse_args()
    df = pd.read_csv(a.inp)
    df = df[(df['sale_price'] <= a.max_price) & (df['sale_price'] >= a.min_price)]
    terms = [tr_fold(t.strip()) for t in a.terms.split(',') if t.strip()]
    rows = []
    with cf.ThreadPoolExecutor(a.workers) as ex:
        for res in ex.map(lambda d: scan(d, terms), df['domain']):
            rows.append(res)
    out = df.merge(pd.DataFrame(rows), on='domain')
    out.to_csv(a.out, index=False)
    hit = out[out['matches'] != '']
    print(f'{len(df)} site tarandı → {len(hit)} sitede eşleşen kategori linki, '
          f'{(out["status"].astype(str).str.startswith("hata")).sum()} site açılamadı')
    if 'haber_sitesi' in out:
        out['haber_sitesi'] = out['haber_sitesi'].fillna(False).astype(bool) | out['haber_menusu'].fillna(False).astype(bool)
    else:
        out['haber_sitesi'] = out['haber_menusu']
    out.to_csv(a.out, index=False)
    hit = out[out['matches'] != '']
    print(f'  Haber sitesi (ana plana alınmaz): {int(hit["haber_sitesi"].sum())} / {len(hit)}')
    cols = ['domain', 'sale_price', 'link_count', 'source', 'haber_sitesi', 'matches', 'bahis_sinyali']
    print(hit.sort_values('sale_price')[cols].to_string(index=False, max_colwidth=90))
