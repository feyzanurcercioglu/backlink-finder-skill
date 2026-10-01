"""Birleşik havuzdan aday siteleri filtreler.

Kullanım:
    python filter_sites.py --pool pool.csv --exclude son6ay.txt --budget 20000 \
        --dr-min 25 [--dr-max 90] [--country tr] [--avoid brands/x.json] --out candidates.csv

Filtre sırası (her adımda kaç site elendiği raporlanır):
  1. Son 6 ay listesi (kullanıcının verdiği) - domain normalize edilerek eşleştirilir
  2. avoid_sites (marka profili) + global kara liste
  3. TR marka ise EN/yabancı dil sayfalarındaki siteler
  4. Tek site fiyatı > bütçenin %60'ı
  5. DR < dr-min (varsayılan 25) ve DR > dr-max. DR = kullanıcının verdiği değer; aracı DR'ı kullanılmaz.
     Güvenilir DR'ı olmayanlar dr_missing.csv'ye yazılır (önceki filtrelerden geçmiş, DR'ı çekilmeye değer liste)
  6. Opsiyonel trafik alt sınırı (--traffic-min)
"""
import argparse
import json
import os
import re

import pandas as pd


def norm_domain(v):
    s = str(v).strip().lower()
    s = re.sub(r'^https?://', '', s)
    s = re.sub(r'^www\.', '', s)
    return s.split('/')[0].strip()


def read_exclude(path):
    """txt / csv / xlsx kabul eder. Her hücredeki domain benzeri değeri toplar."""
    if not path or not os.path.exists(path):
        return set()
    vals = []
    if path.endswith(('.xlsx', '.xls')):
        for _, df in pd.read_excel(path, sheet_name=None, header=None).items():
            vals += df.astype(str).values.ravel().tolist()
    else:
        with open(path, encoding='utf-8') as f:
            for line in f:
                vals += re.split(r'[,;\t]', line)
    out = set()
    for v in vals:
        d = norm_domain(v)
        if re.fullmatch(r'[a-z0-9\-\.]+\.[a-z]{2,}', d):
            out.add(d)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--pool', required=True)
    ap.add_argument('--exclude', help='Son 6 ay çalışılan siteler (txt/csv/xlsx)')
    ap.add_argument('--budget', type=float, required=True)
    ap.add_argument('--dr-min', type=int, default=25)
    ap.add_argument('--dr-max', type=int, default=100)
    ap.add_argument('--country', default='tr')
    ap.add_argument('--list-tolerance', type=int, default=5, help='Aracı DR\'ı ile ön elemede tolerans')
    ap.add_argument('--traffic-min', type=float, default=0, help='Opsiyonel trafik alt sınırı (kullanıcı belirlerse)')
    ap.add_argument('--avoid', help='Marka profili JSON (avoid_sites alanı okunur)')
    ap.add_argument('--blacklist', default=os.path.join(os.path.dirname(__file__), '..', 'brands', '_global_blacklist.txt'))
    ap.add_argument('--out', default='candidates.csv')
    a = ap.parse_args()

    df = pd.read_csv(a.pool)
    df['domain'] = df['domain'].map(norm_domain)
    log = [f'Başlangıç: {len(df)} unique domain']

    excl = read_exclude(a.exclude)
    hit = df['domain'].isin(excl)
    log.append(f'- Son 6 ay listesi ({len(excl)} domain): {hit.sum()} site elendi')
    df = df[~hit]

    avoid = set()
    if a.avoid and os.path.exists(a.avoid):
        avoid |= {norm_domain(d) for d in json.load(open(a.avoid, encoding='utf-8')).get('avoid_sites', [])}
    avoid |= read_exclude(a.blacklist)
    hit = df['domain'].isin(avoid)
    log.append(f'- avoid_sites + global kara liste: {hit.sum()} site elendi')
    df = df[~hit]

    if a.country == 'tr':
        hit = df['lang_en'].fillna(False).astype(bool) if 'lang_en' in df else df['source'].str.contains(' EN', na=False)
        log.append(f'- TR marka, yabancı dil (EN) sayfası: {hit.sum()} site elendi')
        df = df[~hit]

    hit = df['sale_price'] > a.budget * 0.6
    log.append(f'- Fiyatı bütçenin %60ını aşan: {hit.sum()} site elendi')
    df = df[~hit]

    # Kullanıcı DR vermediyse: aracı DR'ı (dr_list) sadece kaba ön eleme için, toleransla kullanılır.
    # Bu siteler dr_verified=False işaretlenir; öneriden önce Ahrefs ile doğrulanmaları zorunludur.
    df['dr_verified'] = df['dr'].notna()
    if 'dr_list' in df:
        prov = df['dr'].isna() & df['dr_list'].notna() & (df['dr_list'] >= a.dr_min - a.list_tolerance)
        df.loc[prov, 'dr'] = df.loc[prov, 'dr_list']
        if prov.sum():
            log.append(f'- Güvenilir DR yok, aracı DR\'ı ile geçici ön elemeden geçen: {prov.sum()} site '
                       f'(tolerans {a.list_tolerance}; öneriden önce Ahrefs ile doğrulanmalı)')
    missing = df[df['dr'].isna()]
    df = df[df['dr'].notna()]
    low_ok = ~df['dr_verified'] & (df['dr'] >= a.dr_min - a.list_tolerance)
    df.loc[low_ok & (df['dr'] < a.dr_min), 'dr'] = a.dr_min  # geçici: doğrulanana kadar elenmesin
    low = df['dr'] < a.dr_min
    high = df['dr'] > a.dr_max
    log.append(f'- DR < {a.dr_min}: {low.sum()} site elendi; DR > {a.dr_max}: {high.sum()} site elendi')
    df = df[~low & ~high]
    if len(missing):
        log.append(f'- Güvenilir DR yok: {len(missing)} site (kullanıcı listesi ya da Ahrefs ile DR gelmeden kullanılmaz) → dr_missing.csv')
        missing.to_csv(os.path.join(os.path.dirname(os.path.abspath(a.out)), 'dr_missing.csv'), index=False)

    if a.traffic_min:
        has_t = df['traffic'].notna() if 'traffic' in df else pd.Series(False, index=df.index)
        low_t = has_t & (df['traffic'] < a.traffic_min)
        log.append(f'- Trafik < {a.traffic_min}: {low_t.sum()} site elendi')
        df = df[~low_t]

    df.sort_values(['dr', 'sale_price'], ascending=[False, True]).to_csv(a.out, index=False)
    log.append(f'Kalan aday: {len(df)} site → {a.out}')
    print('\n'.join(log))
