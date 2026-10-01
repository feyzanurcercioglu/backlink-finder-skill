"""Ay başında gelen aracı (mecra) Excel'ini tek bir birleşik tabloya çevirir.
Dosyada her sayfa bir aracıdır (ör. Whitepress, Exclion, LinkRaiser).

Kullanım:
    python build_pool.py <havuz.xlsx> --out pool.csv

Çıktı sütunları:
    domain, dr, sale_price, net_price, source, link_count, traffic, category, notes

- sale_price: sayfadaki "Markaya yansıtılacak fiyat" sütunu. Fiyat asla tahmin edilmez.
- net_price: mecranın bize fiyatı (bulunabilirse). Internal fiyat tablosunda kullanılır.
- Aynı domain birden fazla mecrada varsa en düşük sale_price'lı kayıt tutulur (bestPrice).
"""
import argparse
import re
import sys
import unicodedata

import pandas as pd


def norm_domain(v):
    s = str(v).strip().lower()
    s = re.sub(r'^https?://', '', s)
    s = re.sub(r'^www\.', '', s)
    return s.split('/')[0].strip()


def parse_link_count(text):
    """Metinden link sayısını çıkarır. Bulamazsa None döner (caller varsayılan atar)."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    s = unicodedata.normalize('NFC', str(text)).lower()
    if 'sınırsız' in s or 'sinirsiz' in s:
        return 99
    m = re.search(r'number of links[^\d]*(\d+)', s) or re.search(r'(\d+)\s*(link|bağlant|baglant)', s)
    if m:
        return int(m.group(1))
    if re.search(r'tek\s+(link|dofollow|bağlant|baglant)', s):
        return 1
    if 'birden fazla' in s or 'çoklu bağlantı' in s:
        return 3
    m = re.fullmatch(r'\s*(\d+)\s*', s)
    return int(m.group(1)) if m else None


def to_float(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r'[^\d,\.]', '', str(v))
    if not s:
        return None
    # TR formatı: 4.700,50 -> 4700.50
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.') if len(s.split(',')[-1]) <= 2 else s.replace(',', '')
    elif s.count('.') == 1 and len(s.split('.')[-1]) == 3:
        s = s.replace('.', '')
    try:
        return float(s)
    except ValueError:
        return None


def find_col(df, *candidates, exclude=()):
    """Sütun adını esnek bul (büyük/küçük harf ve boşluk duyarsız, içerir eşleşmesi)."""
    cols = {c: str(c).strip().lower() for c in df.columns}
    for cand in candidates:
        cand = cand.lower()
        for c, low in cols.items():
            if low == cand:
                return c
    for cand in candidates:
        cand = cand.lower()
        for c, low in cols.items():
            if cand in low and not any(e in low for e in exclude):
                return c
    return None


DOMAIN_COLS = ['Domain', 'URL', 'Site', 'Site Adı', 'Siteler', 'Mecra', 'Website', 'Web Sitesi', 'Target']
DR_COLS = ['DR', 'Ahrefs DR', 'Ahrefs D.R', 'Domain Rating', 'D.R', 'Güncel DR']
SALE_COLS = ['Markaya Yansıtılacak Fiyat', 'markaya yansıtılacak', 'yansıtılacak fiyat', '% Eklenen Fiyat',
             'eklenen fiyat', 'satılacağı fiyat', 'satış fiyatı']
NET_COLS = ['Net Fiyat', 'Fiyat', 'Price', 'Ücret', 'Maliyet']
LINKCOUNT_COLS = ['Link Sayısı', 'NUMBER OF LINKS', 'Number of links']
NOTE_COLS = ['Notlar', 'Not', 'SECTION', 'Açıklama']
TRAFFIC_COLS = ['Trafik', 'Traffic', 'Aylık Trafik', 'AHREFS ORGANIC TRAFFIC', 'Organic Traffic', 'Organic / Traffic',
                'Güncel Trafik']
CAT_COLS = ['Kategori', 'Mecra Teması', 'Tema', 'Category']


def find_cols_all(df, candidates, exclude=()):
    """Adaylardan herhangi biriyle eşleşen TÜM sütunları sayfadaki sırasıyla döndürür."""
    cands = [c.lower() for c in candidates]
    out = []
    for c in df.columns:
        low = str(c).strip().lower()
        if any(e in low for e in exclude):
            continue
        if low in cands or any(len(cd) > 2 and cd in low for cd in cands):
            out.append(c)
    return out


def pick_trusted(cols):
    """Aracı listelerindeki DR/trafik güvenilir değil. Kullanıcının eklediği sütunu seç:
    adında 'güncel' geçen ya da (birden fazla varsa) en sağdaki. Tek sütun varsa o aracının
    kendi değeridir -> güvenilir sayılmaz (None, aracı sütunu)."""
    if not cols:
        return None, None
    for c in cols:
        if 'güncel' in str(c).lower() or 'guncel' in str(c).lower():
            return c, cols[0] if cols[0] != c else None
    if len(cols) > 1:
        return cols[-1], cols[0]
    return None, cols[0]


def source_name(sheet):
    """Sayfa adını aracı adına çevirir: 'Whitepress +' -> 'Whitepress'."""
    return re.sub(r'[\s+]+$', '', sheet).strip() or sheet


def read_metrics(path):
    """Kullanıcının verdiği DR/trafik dosyası (xlsx/csv, ör. Ahrefs Batch Analysis export'u).
    domain -> {'dr', 'traffic'} döndürür. Tüm sayfalar okunur."""
    frames = pd.read_excel(path, sheet_name=None).values() if path.endswith(('.xlsx', '.xls')) \
        else [pd.read_csv(path, sep=None, engine='python')]
    out = {}
    for df in frames:
        dcol = find_col(df, *DOMAIN_COLS, exclude=('teması', 'tema'))
        drc = find_cols_all(df, DR_COLS, exclude=('url rating', 'ur'))
        trc = find_cols_all(df, TRAFFIC_COLS, exclude=('value', 'değer', 'paid', 'ücretli'))
        if dcol is None or (not drc and not trc):
            continue
        for _, r in df.iterrows():
            if pd.isna(r[dcol]):
                continue
            d = norm_domain(r[dcol])
            dr = to_float(r[drc[-1]]) if drc else None
            tr = to_float(r[trc[-1]]) if trc else None
            out[d] = {'dr': dr, 'traffic': tr}
    return out


def build(path, metrics=None):
    """Her sayfa bir aracı (mecra) kabul edilir. Sütunlar esnek eşleştirilir.

    DR/trafik önceliği: metrics dosyası > sayfadaki kullanıcı sütunu (güncel / en sağdaki) >
    yok (None). Aracının kendi DR'ı yalnızca dr_list olarak referans tutulur, karar için kullanılmaz.
    """
    metrics = metrics or {}
    xls = pd.ExcelFile(path)
    records, report = [], []
    for sheet in xls.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet)
        source = source_name(sheet)
        dcol = find_col(df, *DOMAIN_COLS, exclude=('teması', 'tema'))
        sale = find_col(df, *SALE_COLS)
        dr_t, dr_l = pick_trusted(find_cols_all(df, DR_COLS, exclude=('url rating',)))
        tr_t, tr_l = pick_trusted(find_cols_all(df, TRAFFIC_COLS, exclude=('value', 'değer')))
        net = find_col(df, *NET_COLS, exclude=('eklenen', 'satılacağı', 'yansıtılacak', 'satış'))
        lccol = find_col(df, *LINKCOUNT_COLS)
        lcol = find_col(df, *NOTE_COLS, exclude=('number of links', 'link sayısı'))
        ccol = find_col(df, *CAT_COLS)
        if dcol is None or sale is None:
            report.append(f'  - "{sheet}": domain veya "markaya yansıtılacak fiyat" sütunu bulunamadı, atlandı '
                          f'(sütunlar: {list(df.columns)[:10]})')
            continue
        n = 0
        for _, r in df.iterrows():
            if pd.isna(r[dcol]):
                continue
            sp = to_float(r[sale])
            if not sp:
                continue
            d = norm_domain(r[dcol])
            m = metrics.get(d, {})
            dr = m.get('dr') if m.get('dr') is not None else (to_float(r[dr_t]) if dr_t is not None else None)
            tr = m.get('traffic') if m.get('traffic') is not None else (to_float(r[tr_t]) if tr_t is not None else None)
            dr_src = 'dosya' if m.get('dr') is not None else ('sayfa' if dr is not None else None)
            lc_raw = r[lcol] if lcol is not None else None
            records.append({
                'domain': d,
                'dr': int(dr) if dr is not None else None,  # None = kullanıcıdan/Ahrefs'ten gelmeli
                'traffic': tr,
                'dr_source': dr_src,
                'dr_list': to_float(r[dr_l]) if dr_l is not None else None,  # aracının DR'ı, sadece referans
                'sale_price': sp,
                'net_price': to_float(r[net]) if net is not None else None,
                'source': source,
                'link_count': (parse_link_count(r[lccol]) if lccol is not None else None)
                              or parse_link_count(lc_raw) or 1,
                'category': r[ccol] if ccol is not None else None,
                'notes': lc_raw,
                'lang_en': bool(re.search(r'\b(en|eng|english|global)\b', sheet.lower())),
            })
            n += 1
        cols = f'fiyat: "{sale}"'
        cols += f', DR: "{dr_t}"' if dr_t is not None else ', DR: kullanıcı sütunu yok'
        cols += f', trafik: "{tr_t}"' if tr_t is not None else ', trafik: kullanıcı sütunu yok'
        report.append(f'  - {source}: {n} site ({cols})')
    raw = pd.DataFrame(records)
    # drop_duplicates: satırı bütün olarak tutar (groupby.first sütunları farklı satırlardan karıştırır)
    best = raw.sort_values('sale_price').drop_duplicates('domain', keep='first').reset_index(drop=True)
    return raw, best, report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('excel')
    ap.add_argument('--metrics', action='append', default=[],
                    help='Kullanıcının verdiği DR/trafik dosyası (xlsx/csv). Birden fazla verilebilir.')
    ap.add_argument('--out', default='pool.csv')
    a = ap.parse_args()
    metrics = {}
    for mp in a.metrics:
        metrics.update(read_metrics(mp))
    raw, best, report = build(a.excel, metrics)
    best.to_csv(a.out, index=False)
    print('✓ Backlink havuzu yüklendi:')
    print('\n'.join(report))
    print(f'  Toplam: {len(raw)} kayıt → {len(best)} unique domain (bestPrice ile)')
    if a.metrics:
        hit = best['domain'].isin(metrics.keys()).sum()
        print(f'  DR/trafik dosyası: {len(metrics)} domain, havuzla eşleşen {hit}')
    missing_dr = best['dr'].isna().sum()
    if missing_dr:
        print(f'  ⚠ {missing_dr} domain için güvenilir DR yok (aracı DR\'ı kullanılmaz; '
              f'kullanıcıdan liste istenmeli ya da Ahrefs ile çekilmeli)')
    print(f'  → {a.out}')
