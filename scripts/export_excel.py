"""Onaylanan backlink planını markanın Internal ve Shared Excel'lerine aylık sayfa olarak yazar.

Kullanım:
    python export_excel.py plan.json --internal "<Marka>_Backlink_Internal.xlsx" --shared "<Marka>_Backlink_Shared.xlsx"

Dosya yoksa oluşturulur; varsa açılır ve çalışma ayı adında (ör. "Kasım 2026") yeni sayfa eklenir.
Aynı ayın sayfası zaten varsa (revizyon) silinip yeniden yazılır; diğer ayların sayfalarına dokunulmaz.

plan.json:
{
  "brand_domain": "dagi.com.tr", "brand_name": "dagi", "month_year": "Ekim 2026",
  "sites": [
    {"domain": "annelertoplandik.com", "dr": 33, "traffic": 383197, "site_price": 4550, "net_price": 3789.25,
     "content_price": 750, "source": "Whitepress",
     "category": "Eğlence > Moda", "category_url": "https://annelertoplandik.com/blog/category/eglence/moda/",
     "inbound_note": "Eğlence > Moda kategorisi var; aylık ~383K organik trafik; 'bebek kıyafetleri' sorgusunda 2. sırada",
     "keywords": [{"kw": "kadın pijama takımı", "url": "/collections/kadin-pijama-takimi-modelleri"}]}
  ],
  "keywords": [{"kw": "kadın pijama takımı", "volume": 12100, "rank": 8, "change": -3,
                "url": "/collections/kadin-pijama-takimi-modelleri", "sessions": null}]
}

Sayfa yapısı:
  Blok 1 (Internal + Shared) - Plan: Domain | DR | Site Ücreti | İçerik Ücreti | Keyword | URL | İçerik |
           Yayınlanan Link | Inbound Notu. Site başına renkli blok, çok linkli sitede A-D, G-I birleşik,
           altta "Total: X TL + KDV".
  Blok 2 (sadece Internal) - Fiyat: Domain | DR | net fiyat | %20 fiyat | Mecra | Not | Yayın Kategorisi
  Blok 3 (sadece Internal) - Kelime (SEOmonitor): Keyword | Volume | Rank | Change | Landing Page | Sessions
"""
import argparse
import json

import os
import platform
import re
import subprocess

from openpyxl import Workbook, load_workbook
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


def write_sheet(ws, plan, internal=True):
    base = 'https://www.' + plan['brand_domain'].replace('https://', '').replace('www.', '').strip('/')

    # ---- Blok 1: plan (Internal + Shared)
    header(ws, 1, ['Domain', 'DR', 'Site Ücreti', 'İçerik Ücreti', 'Keyword', 'URL', 'İçerik', 'Yayınlanan Link',
                   'Inbound Notu'], '666666')
    row, total = 2, 0
    for idx, s in enumerate(plan['sites']):
        fill = SITE_FILLS[idx % 2]
        kws = s['keywords'] or [{'kw': '', 'url': ''}]
        start = row
        for k in kws:
            for col in range(1, 10):
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
        note = ws.cell(row=start, column=9, value=s.get('inbound_note'))
        note.alignment = Alignment(vertical='center', wrap_text=True)
        total += s['site_price'] + s.get('content_price', 750)
        if end > start:
            for col in (1, 2, 3, 4, 7, 8, 9):
                ws.merge_cells(start_row=start, start_column=col, end_row=end, end_column=col)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
    c = ws.cell(row=row, column=1, value=f'Total: {tr_num(total)} TL + KDV')
    for col in range(1, 5):
        style(ws.cell(row=row, column=col), fill='666666')
    c.font = Font(name='Arial', size=10, bold=True, color='FFFFFF')
    c.alignment = Alignment(horizontal='right', vertical='center')
    widths = [22, 8, 12, 12, 18, 40, 28, 40, 60]
    if not internal:
        for col, w in zip('ABCDEFGHI', widths):
            ws.column_dimensions[col].width = w
        return total

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

    for col, w in zip('ABCDEFGHI', widths):
        ws.column_dimensions[col].width = w
    return total


AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']


def month_key(title):
    m = re.match(r'\s*(\S+)\s+(\d{4})', title)
    if m and m.group(1).capitalize() in AYLAR:
        return int(m.group(2)) * 12 + AYLAR.index(m.group(1).capitalize())
    return None


def export_to(path, plan, internal):
    """Markanın Excel'ine ayın sayfasını ekler (varsa yeniden yazar), sayfaları kronolojik sıralar."""
    title = plan['month_year']
    if os.path.exists(path):
        wb = load_workbook(path)
        if title in wb.sheetnames:
            del wb[title]
        ws = wb.create_sheet(title)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        wb = Workbook()
        ws = wb.active
        ws.title = title
    total = write_sheet(ws, plan, internal)
    known = [w for w in wb._sheets if month_key(w.title) is not None]
    other = [w for w in wb._sheets if month_key(w.title) is None]
    wb._sheets = sorted(known, key=lambda w: month_key(w.title)) + other
    wb.active = wb._sheets.index(ws)
    wb.save(path)
    return total


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('--internal', required=True, help='<Marka>_Backlink_Internal.xlsx (3 blok)')
    ap.add_argument('--shared', required=True, help='<Marka>_Backlink_Shared.xlsx (sadece plan tablosu)')
    ap.add_argument('--open', action='store_true', help='Yazdıktan sonra iki dosyayı varsayılan uygulamada (Excel) aç')
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding='utf-8'))
    missing = [s['domain'] for s in plan['sites'] if not s.get('inbound_note')]
    if missing:
        print(f'⚠ Inbound Notu boş: {", ".join(missing)}')
    total = export_to(a.internal, plan, internal=True)
    export_to(a.shared, plan, internal=False)
    print(f'✓ {plan["month_year"]} sayfası yazıldı | {len(plan["sites"])} site, toplam {tr_num(total)} TL + KDV')
    print(f'  Internal: {a.internal}')
    print(f'  Shared:   {a.shared}')
    if a.open:
        for f in (a.internal, a.shared):
            try:
                if platform.system() == 'Darwin':
                    subprocess.run(['open', f], check=False)
                elif platform.system() == 'Windows':
                    os.startfile(f)  # noqa
                else:
                    subprocess.run(['xdg-open', f], check=False)
            except Exception as e:  # noqa: BLE001
                print(f'  (açılamadı: {e})')
        print('  Excel dosyaları açıldı.')
