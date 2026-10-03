"""SEOmonitor keyword verisini jenerik-öncelikli skorlar.

Kullanım:
    python keyword_select.py --in seomonitor_kw.json --brand dagi [--top 15] --out kw_scored.json \
        [--profile ../brands/dagi_com_tr.json] [--volatility volatility.json]

Girdi: SEOmonitor'dan çekilmiş satırların normalize edilmiş listesi:
    [{"keyword": "külot", "search_volume": 74000, "rank": 11, "change": 2,
      "landing_page": "https://www.marka.com/collections/kulot", "sessions": 480}, ...]

Mantık:
  - Brand içeren kelimeler elenir.
  - Jenerik = kategori adının kendisi (külot, erkek külot). Niteleyici ek içerenler
    (fiyatları, modelleri, en iyi, nasıl, ucuz, ...) jenerik sayılmaz, ciddi puan kaybeder.
  - Hacim log ölçekte ağırlıklandırılır (hacim önemli ama tek başına belirleyici değil).
  - Dönem sonu sırası ilk 3'te (--min-rank, varsayılan 4) olan kelime ELENİR: zaten ilk 3'te, backlink'e gerek yok.
  - Rank 4-20 bandı en değerli (link ile itilebilir), 30+ uzak.
  - Landing page blog/ürün/arama sayfasıysa (barkodla biten ürün URL'leri dahil) ciddi puan kaybeder (backlink kategori sayfasına gider).
  - Marka profili verilirse: SEOmonitor'daki öncelikli gruplardan (priority_group_ids, ör. "Önemli Kelimeler")
    birinde olmayan kelime ELENİR; landing'i secondary_category_paths (ör. aksesuar/çorap) altındaysa ELENİR.
    Girdi satırlarında "groups" alanı (SEOmonitor'un virgüllü grup id listesi) bulunmalı.
  - Dalgalanma (--volatility): dönem içi günlük sıra aralığı ve değişim sayısı. Sırası oynayan kelime,
    link desteğiyle sabitlenebilecek kelimedir; en güçlü öncelik sinyallerinden biridir.
  - Kategori katmanı (profil core_category_paths / minor_category_paths): çekirdek ana kategoriye giden
    kelime öne, alt/sezonluk kategoriye giden geriye alınır (Dagi: erkek atlet > termal içlik).
  - Sezon puanlanmaz; Claude çalışma ayına göre yorumlar (Ekim'de mayo/bikini sezon dışı vb.).
"""
import argparse
import json
import math
import re

MODIFIERS = [
    'fiyat', 'fiyatı', 'fiyatları', 'fiyatlari', 'model', 'modeli', 'modelleri', 'çeşit', 'çeşitleri',
    'en iyi', 'en ucuz', 'ucuz', 'indirim', 'indirimli', 'kampanya', 'öneri', 'önerileri', 'tavsiye',
    'yorum', 'yorumları', 'nasıl', 'nedir', 'ne işe yarar', 'nerede', 'satın al', 'online', 'sipariş',
    'kombin', 'kombinleri', 'trend', 'trendleri', '2024', '2025', '2026', '2027', 'kaç', 'hangi',
    'vs', 'karşılaştırma', 'resimleri', 'fotoğrafları',
]


def is_generic(kw):
    k = kw.lower()
    words = k.split()
    if len(words) > 3:
        return False
    return not any(re.search(rf'(^|\s){re.escape(m)}(\s|$)', k) for m in MODIFIERS)


def score(row, brand_tokens, volat=None, core=(), minor=(), min_rank=4):
    k = row['keyword'].lower()
    if any(b in k for b in brand_tokens):
        return None
    rank = row.get('rank')
    vol = row.get('search_volume') or 0
    if rank is None or rank < min_rank or rank > 50 or vol <= 0:
        return None
    s = 0.0
    generic = is_generic(k)
    s += 40 if generic else 0
    s += 5 if len(k.split()) <= 2 else 0           # kısa kafa terim bonusu
    s += min(30, 6 * math.log10(max(vol, 10)))      # 1.000→18, 10.000→24, 100.000→30
    if rank <= 10:
        s += 20
    elif 11 <= rank <= 20:
        s += 15
    elif 21 <= rank <= 30:
        s += 8
    lp = (row.get('landing_page') or '').lower()
    if re.search(r'/(blogs?|products?|urun|search|arama)/', lp) or re.search(r'-\d{8,}/?$', lp):
        s -= 30                                      # kategori sayfası değil: link kategoriye gitmeli
    ch = row.get('change')
    if isinstance(ch, (int, float)) and ch < 0:
        s += 5                                       # düşüş yaşayan kelime, desteğe ihtiyaç var
    if volat:
        spread = min(volat.get('range', 0), 30)      # 100'e tek günlük düşüşler aşırı şişirmesin
        s += min(25, spread * 1.2 + min(volat.get('moves', 0), 25) * 0.3)
    if any(c in lp for c in core):
        s += 20
    elif any(m in lp for m in minor):
        s -= 15
    return round(s, 1), generic


def rng(v):
    return f"{v['min']}-{v['max']}" if v else '-'


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--brand', required=True, help='Virgülle ayrılmış marka token\'ları (ör: dagi,dağı)')
    ap.add_argument('--top', type=int, default=15)
    ap.add_argument('--out', default='kw_scored.json')
    ap.add_argument('--profile', help='Marka profili JSON (priority_group_ids, secondary/core/minor_category_paths)')
    ap.add_argument('--last-kw', help='Geçen ay backlink alan kelimeler (her satıra bir kelime ya da "ay\\tkelime"); ELENİR')
    ap.add_argument('--min-rank', type=int, default=4, help='Bu sıradan iyi (küçük) kelimeler elenir; varsayılan ilk 3 hariç')
    ap.add_argument('--volatility', help='Dönem içi günlük sıra dalgalanması JSON (keyword -> range, moves, ...)')
    a = ap.parse_args()
    rows = json.load(open(a.inp, encoding='utf-8'))
    if a.profile:
        prof = json.load(open(a.profile, encoding='utf-8'))
        pg = {str(g) for g in prof.get('priority_group_ids', [])}
        sec = [x.lower() for x in prof.get('secondary_category_paths', [])]
        before = len(rows)
        if pg:
            rows = [r for r in rows if pg & set(str(r.get('groups') or '').split(','))]
        rows = [r for r in rows if not any(x in (r.get('landing_page') or '').lower() for x in sec)]
        print(f'Profil filtresi: {before} → {len(rows)} kelime (öncelikli grup + ana kategori)')
    brand = [b.strip().lower() for b in a.brand.split(',') if b.strip()]
    vols = json.load(open(a.volatility, encoding='utf-8')) if a.volatility else {}
    core = minor = ()
    if a.profile:
        core = [x.lower() for x in prof.get('core_category_paths', [])]
        minor = [x.lower() for x in prof.get('minor_category_paths', [])]
    last_kw = set()
    if a.last_kw:
        for line in open(a.last_kw, encoding='utf-8'):
            k = line.strip().split('\t')[-1].strip().lower()
            if k:
                last_kw.add(k)
        before = len(rows)
        rows = [r for r in rows if r['keyword'].strip().lower() not in last_kw]
        print(f'Geçen ay backlink alan kelimeler çıkarıldı: {before - len(rows)} kelime')
    out = []
    for r in rows:
        res = score(r, brand, vols.get(r['keyword']), core, minor, a.min_rank)
        if res:
            r['score'], r['generic'] = res
            out.append(r)
    out.sort(key=lambda r: (-r['score'], -(r.get('search_volume') or 0)))
    json.dump(out, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'{len(rows)} kelime → {len(out)} uygun ({sum(r["generic"] for r in out)} jenerik)')
    print(f'{"keyword":28} {"hacim":>8} {"rank":>5} {"chg":>5} {"aralık":>9} {"jen":>4} {"skor":>5}  landing')
    for r in out[:a.top]:
        print(f'{r["keyword"][:28]:28} {r.get("search_volume", 0):>8} {r.get("rank", "-"):>5} '
              f'{str(r.get("change", "")):>5} {rng(vols.get(r["keyword"])):>9} {"✓" if r["generic"] else "-":>4} '
              f'{r["score"]:>5}  {r.get("landing_page", "")}')
