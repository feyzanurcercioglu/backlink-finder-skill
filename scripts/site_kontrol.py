"""Aday sitelerin Ahrefs verisinden güvenlik kararı verir: zararlı sorgu ve yeni/şüpheli geçmiş.

Girdi (Claude Ahrefs MCP çağrılarından doldurur), JSON:
{
  "site.com": {
    "history":  [{"date": "2025-04-01", "org_traffic": 7088}, ...],          # site-explorer-metrics-history, aylık, son 18 ay
    "harmful":  [{"keyword": "...", "best_position": 5, "volume": 100}, ...] # site-explorer-organic-keywords, zararlı terim filtresiyle
  }
}

Kullanım:
    python site_kontrol.py --in ahrefs_kontrol.json [--out site_kontrol.csv]

Kararlar:
  ELE    - cinsel/bahis vb. sorguda ilk 20'de sıralama, ya da bu tür 3+ sorgu
         - yeni site: anlamlı organik trafik (>= 100 ve şimdikinin %10'u) son 3 ay içinde başlamış
  DIKKAT - son ay trafiği önceki 6 ayın medyanının 3 katından fazla (ani sıçrama)
         - zirveye göre %75+ düşüş (çöken site)
  TEMIZ  - diğerleri
Yanlış alarm veren masum kelimeler (unisex, seksek, essex ...) ALLOW listesiyle elenir.
"""
import argparse
import json
import re
import statistics as st

import pandas as pd

# Ahrefs organic-keywords "where" filtresinde kullanılacak terimler (SKILL.md'de hazır JSON var)
TERMS = ['seks', 'sex', 'porno', 'porn', 'sikiş', 'sikis', 'ifşa', 'ifsa', 'çıplak', 'ciplak', 'escort', 'eskort',
         'erotik', 'xxx', 'nude', '+18', 'bahis', 'casino', 'kumar', 'iddaa', 'slot', 'deneme bonusu', 'bet giriş',
         'canlı bahis', 'bonus veren']
ALLOW = re.compile(r'(unisex|seksek|essex|middlesex|sussex|sextant|seksen|transeks|homoseks|biseks|aseks|heteroseks|kumarki|kumarhane filmi)', re.I)
TERM_RE = re.compile('|'.join(re.escape(t) for t in TERMS), re.I)


def judge(domain, d):
    reasons, level = [], 'TEMIZ'
    bad = [k for k in d.get('harmful', [])
           if TERM_RE.search(k['keyword']) and not ALLOW.search(k['keyword'])]
    top = [k for k in bad if (k.get('best_position') or 999) <= 20]
    if top or len(bad) >= 3:
        level = 'ELE'
        ex = sorted(top or bad, key=lambda k: k.get('best_position') or 999)[:3]
        reasons.append('zararlı sorgu: ' + '; '.join(f"'{k['keyword']}' {k.get('best_position')}." for k in ex)
                       + (f' (toplam {len(bad)})' if len(bad) > 3 else ''))
    h = [x.get('org_traffic') or 0 for x in sorted(d.get('history', []), key=lambda x: x['date'])]
    if h:
        cur = h[-1]
        thr = max(100, cur * 0.10)
        first = next((i for i, v in enumerate(h) if v >= thr), None)
        if first is not None and len(h) - first <= 3 and len(h) >= 6:
            level = 'ELE'
            reasons.append(f'yeni site: anlamlı trafik son {len(h) - first} ayda başlamış')
        prev = h[-7:-1]
        if len(prev) >= 3 and st.median(prev) > 0 and cur > 3 * st.median(prev):
            if level != 'ELE':
                level = 'DIKKAT'
            reasons.append(f'ani sıçrama: son ay {cur:,} / önceki 6 ay medyanı {st.median(prev):,.0f}')
        peak = max(h)
        if peak > 0 and cur < peak * 0.25:
            if level != 'ELE':
                level = 'DIKKAT'
            reasons.append(f'çöküş: zirve {peak:,} → son {cur:,}')
    return {'domain': domain, 'karar': level, 'gerekce': ' | '.join(reasons) or '-',
            'trafik_son': h[-1] if h else None, 'zararli_sorgu_sayisi': len(bad)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--out', default='site_kontrol.csv')
    a = ap.parse_args()
    data = json.load(open(a.inp, encoding='utf-8'))
    rows = [judge(dom, d) for dom, d in data.items()]
    df = pd.DataFrame(rows).sort_values('karar')
    df.to_csv(a.out, index=False)
    print(df.to_string(index=False, max_colwidth=110))
