"""Onaylanan backlink planını "Marka için Hazırlanan Format" Excel'ine yazar.

Kullanım:
    python export_excel.py plan.json [--out backlink_plan_dagi_Ekim_2026.xlsx]

plan.json:
{
  "brand_domain": "dagi.com.tr",
  "brand_name": "dagi",
  "month_year": "Ekim 2026",
  "sites": [
    {"domain": "maksatbilgi.com", "dr": 35, "site_price": 3550, "net_price": 2823.25,
     "content_price": 750, "source": "whitepress", "link_count": 3,
     "category": "Eğlence > Moda", "category_url": "https://site.com/kategori/moda/",
     "keywords": [{"kw": "gecelik", "url": "/collections/kadin-gecelik-modelleri"}, ...]}
  ],
  "keywords": [
    {"kw": "gecelik", "volume": 33100, "rank": 6, "change": -2,
     "url": "/collections/kadin-gecelik-modelleri", "sessions": 351}
  ]
}

Sheet yapısı (tek sheet, adı "Ay Yıl"):
  Blok 1 - Markaya giden plan: Domain | DR | Site Ücreti | İçerik Ücreti | Keyword | URL | İçerik | Yayınlanan Link
           Site başına renkli blok (sarı / mavi dönüşümlü), A-D ve G-H birleştirilmiş, altta "Total: X TL + KDV".
  Blok 2 - Internal fiyat tablosu: Domain | DR | net fiyat | %20 fiyat | Mecra | Not | Yayın Kategorisi (eşleşen kategori, linkli)
  Blok 3 - Keyword verisi (SEOmonitor): Keyword | Volume | Rank | Change | Landing Page | Sessions
"""
import argparse
import json

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

THIN = Side(border_style='thin', color='000000')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
SITE_FILLS = ['FFF2CC', 'CFE2F3']
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
VCENTER = Alignment(vertical='center', wrap_text=True)
CHANGE_FMT = '[Color3][<0] -0;[Color43][>0] +0; -'


def tr_num(n):
    return f'{n:,.0f}'


def full_url(base, path):
    if path.startswith('http'):
        return path
    return base.rstrip('/') + '/' + path.lstrip('/')


def path_of(url):
    if url.startswith('http'):
        url = '/' + url.split('://', 1)[1].split('/', 1)[-1] if '/' in url.split('://', 1)[1] else '/'
    return url


def header(ws, row, titles, fill, color='FFFFFF'):
    for i, t in enumerate(titles, 1):
        c = ws.cell(row=row, column=i, value=t)
        c.font = Font(name='Arial', size=10, bold=True, color=color)
        c.fill = PatternFill('solid', start_color=fill)
        c.alignment = CENTER
        c.border = BORDER


def style(c, fill=None, fmt=None, align=CENTER, color=None):
    c.font = Font(name='Arial', size=10, color=color)
    if fill:
        c.fill = PatternFill('solid', start_color=fill)
    if fmt:
        c.number_format = fmt
    c.alignment = align
    c.border = BORDER


def export(plan, out):
    base = 'https://www.' + plan['brand_domain'].replace('https://', '').replace('www.', '').strip('/')
    wb = Workbook()
    ws = wb.active
    ws.title = plan['month_year']

    # ---- Blok 1: markaya giden plan
    header(ws, 1, ['Domain', 'DR', 'Site Ücreti', 'İçerik Ücreti', 'Keyword', 'URL', 'İçerik', 'Yayınlanan Link'], '666666')
    row, total = 2, 0
    for idx, s in enumerate(plan['sites']):
        fill = SITE_FILLS[idx % 2]
        kws = s['keywords'] or [{'kw': '', 'url': ''}]
        start = row
        for k in kws:
            for col in range(1, 9):
                style(ws.cell(row=row, column=col), fill=fill)
            ws.cell(row=row, column=5, value=k['kw'])
            if k['url']:
                c = ws.cell(row=row, column=6, value=f'=HYPERLINK("{full_url(base, k["url"])}", "{path_of(k["url"])}")')
                style(c, fill=fill, align=VCENTER, color='1155CC')
            row += 1
        end = row - 1
        ws.cell(row=start, column=1, value=s['domain']).font = Font(name='Arial', size=10, color='0000FF')
        ws.cell(row=start, column=2, value=s['dr'])
        ws.cell(row=start, column=3, value=s['site_price']).number_format = '#,##0'
        ws.cell(row=start, column=4, value=s.get('content_price', 750)).number_format = '#,##0'
        total += s['site_price'] + s.get('content_price', 750)
        if end > start:
            for col in (1, 2, 3, 4, 7, 8):
                ws.merge_cells(start_row=start, start_column=col, end_row=end, end_column=col)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    c = ws.cell(row=row, column=1, value=f'Total: {tr_num(total)} TL + KDV')
    for col in range(1, 5):
        style(ws.cell(row=row, column=col), fill='666666')
    c.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
    c.alignment = Alignment(horizontal='right', vertical='center')

    # ---- Blok 2: internal fiyat tablosu
    row += 4
    header(ws, row, ['Domain', 'DR', 'net fiyat', '%20 fiyat', 'Mecra', 'Not', 'Yayın Kategorisi'], '999999')
    for s in plan['sites']:
        row += 1
        vals = [s['domain'], s['dr'], s.get('net_price'), s['site_price'], s['source'].lower(),
                f"{len(s['keywords'])} link"]
        for col, v in enumerate(vals, 1):
            style(ws.cell(row=row, column=col, value=v), fmt='#,##0.00' if col == 3 else ('#,##0' if col == 4 else None))
        cat, cat_url = s.get('category'), s.get('category_url')
        val = f'=HYPERLINK("{cat_url}", "{cat or cat_url}")' if cat_url else cat
        style(ws.cell(row=row, column=7, value=val), align=VCENTER, color='1155CC' if cat_url else None)

    # ---- Blok 3: keyword verisi
    row += 3
    header(ws, row, ['Keyword', 'Volume', 'Rank', 'Change', 'Landing Page', 'Sessions'], 'D9D9D9', color='000000')
    for k in plan['keywords']:
        row += 1
        style(ws.cell(row=row, column=1, value=k['kw']))
        style(ws.cell(row=row, column=2, value=k.get('volume')), fmt='#,##0')
        style(ws.cell(row=row, column=3, value=k.get('rank')))
        style(ws.cell(row=row, column=4, value=k.get('change')), fmt=CHANGE_FMT)
        style(ws.cell(row=row, column=5, value=f'=HYPERLINK("{full_url(base, k["url"])}", "{path_of(k["url"])}")'),
              align=VCENTER, color='1155CC')
        style(ws.cell(row=row, column=6, value=k.get('sessions')), fmt='#,##0')

    for col, w in zip('ABCDEFGH', [22, 8, 12, 12, 18, 40, 28, 58]):
        ws.column_dimensions[col].width = w
    wb.save(out)
    return out, total


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('--out')
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding='utf-8'))
    out = a.out or f"backlink_plan_{plan['brand_name']}_{plan['month_year'].replace(' ', '_')}.xlsx"
    path, total = export(plan, out)
    print(f'✓ {path} | {len(plan["sites"])} site, toplam {tr_num(total)} TL + KDV')
