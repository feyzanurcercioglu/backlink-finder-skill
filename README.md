# backlink-finder

Inbound Digital'in aylık backlink operasyonunu yürüten [Claude Code](https://claude.com/claude-code)
skill'i. Markanın o ayki bütçesi, aracıların mecra listesi ve son 6 ayda çalışılan sitelerle;
SEOmonitor'dan kelime seçer, uygun siteleri bulur, site-kelime eşleştirmesini yapar ve
markaya iletilmeden önce kontrol edilen internal Excel'i ("Marka için Hazırlanan Format") üretir.

## Neden

Aylık backlink planında iki karar zaman alır ve hataya açıktır: hangi kelimeye link alınacağı
ve hangi sitenin gerçekten markaya uygun olduğu. Aracı listelerindeki DR değerleri güncel değil,
"Tema" sütunları çoğu zaman anlamsız ("Var", "Yok", "Karma"), yüksek DR'lı sitelerin bir kısmı
trafiksiz link çiftlikleri. Bu skill kararları metriğe değil kanıta dayandırır: kelimeyi
SEOmonitor'daki öncelik grubundan ve sıra dalgalanmasından, siteyi menüsündeki kategoriden ve
Ahrefs'in o günkü verisinden seçer.

## Akış

1. **Girdiler sorulur:** marka, bütçe, aracı mecra Excel'i (her sayfa bir aracı), son 6 ayda
   çalışılan siteler. Veri dönemi çalışma ayından önceki takvim ayıdır (Ekim çalışması → 1-30 Eylül)
2. **Havuz:** üç aracının sayfaları birleştirilir, aynı site birden fazla aracıdaysa en ucuz
   "markaya yansıtılacak fiyat" alınır. Son 6 ay listesi, dil ve bütçe filtreleri uygulanır
3. **Kelime seçimi (SEOmonitor):** markanın öncelik grubundaki ("Önemli Kelimeler", "KPI" vb.)
   jenerik kategori kelimeleri; önce ay içinde sırası dalgalananlar, sonra çekirdek ana kategoriler.
   İlk 3'teki kelimeler, sezon dışı kategoriler, aksesuar gibi yan kategoriler ve ürün/blog
   sayfasına sıralananlar alınmaz
4. **Site seçimi:** tüm havuzda menü kategorisi taranır (`category_scan.py`, ~600 site yaklaşık
   1 dakika); menüsünde markanın dikeyiyle doğrudan eşleşen kategori olmayan site önerilmez
   (moda markası → Moda, kozmetik → Güzellik/Makyaj, teknoloji → Teknoloji)
5. **Doğrulama:** DR ve trafik Ahrefs'ten o gün çekilir (DR 25 altı elenir), PBN kalıbı
   (yüzlerce referring domain + sıfır trafik) ve bahis/yetişkin içeriği elenir, kategori menüde
   WebFetch ile teyit edilir
6. **Bütçe:** site ücreti + site başına 750 TL içerik; toplam bütçeyi aşmaz ve en az ~%87'sini
   kullanır. Kurallar bütçeyi doldurmak için gevşetilmez
7. **Önce sohbette sunulur**, revizeler alınır, onay sonrası Excel üretilir

## Çıktı

`backlink_plan_<marka>_<Ay_Yıl>.xlsx`, tek sayfa ("Ekim 2026"), üç blok:

| Blok | Sütunlar | Kime |
|---|---|---|
| Plan | Domain, DR, Site Ücreti, İçerik Ücreti, Keyword, URL, İçerik, Yayınlanan Link + "Total: X TL + KDV" | Markaya giden kısım |
| Fiyat | Domain, DR, net fiyat, %20 fiyat, Mecra, Not, Yayın Kategorisi | Internal, markaya göndermeden silinir |
| Kelime | Keyword, Volume, Rank, Change, Landing Page, Sessions | Internal, markaya göndermeden silinir |

## Kurulum

```bash
git clone https://github.com/feyzanurcercioglu/backlink-finder-skill.git \
  ~/.claude/skills/backlink-finder
pip3 install -r ~/.claude/skills/backlink-finder/requirements.txt
```

Claude Code'u yeniden başlatın. Skill `/backlink-finder` olarak görünür; "Dagi için Ekim
backlink listesi hazırla, bütçe 10.000" gibi taleplerde kendiliğinden devreye girer.

**Güncelleme:**

```bash
git -C ~/.claude/skills/backlink-finder pull
```

> claude.ai hesabınızda eski "backlink-skill" yüklüyse kaldırın ya da devre dışı bırakın;
> iki sürüm aynı taleplerde çakışır.

## Gereksinimler

- **SEOmonitor MCP** (claude.ai connector) - kelime, sıra, günlük sıra, oturum verisi
- **Ahrefs MCP** - DR/trafik doğrulama (`batch-analysis`), zararlı site kontrolü
- **WebFetch** - site menüsü ve içerik teyidi
- **Python 3** ve `pandas`, `openpyxl` (`requirements.txt`)

## Kullanım

Her ay şu dört bilgiyle başlayın:

```
Flormar için Ekim listesi hazırla, bütçe 15.000.
Mecra listesi: ~/Downloads/(Internal) Inbound x Backlink Siteleri - Eylül 2026.xlsx
Son 6 ayda çalışılan siteler:
Nisan 2026  webanne.com
Mayıs 2026  kadin.com.tc
...
```

Çalışma dosyaları ve Excel, Claude Code'u açtığınız klasörde `calisma/<marka>_<Ay_Yıl>/`
altına yazılır.

## Marka profilleri

`brands/<domain>.json` her marka için öncelik grubunu, ana/yan kategorileri, sezonları ve
eşleşen site kategorilerini tutar (örnek: `brands/dagi_com_tr.json`, `brands/flormar_com_tr.json`).
Profili olmayan marka için skill ilk çalıştırmada bunları çıkarıp onaya sunar. Yeni ya da
güncellenen profilleri repoya gönderin ki ekip aynı bilgiyle çalışsın.

`brands/_global_blacklist.txt` marka fark etmeksizin önerilmeyecek zararlı sitelerin listesidir.

## Yapı

```
backlink-finder/
├── SKILL.md                    Ana iş akışı ve kurallar
├── README.md
├── requirements.txt
├── brands/
│   ├── _global_blacklist.txt   Zararlı site kara listesi
│   ├── dagi_com_tr.json        Marka profili
│   └── flormar_com_tr.json     Marka profili
├── references/
│   └── widget.md               claude.ai için opsiyonel interaktif panel
└── scripts/
    ├── build_pool.py           Aracı Excel'ini birleşik havuza çevirir
    ├── filter_sites.py         Son 6 ay, dil, bütçe, DR ön elemesi
    ├── keyword_select.py       Öncelik grubu + dalgalanma + kategori katmanı skorlaması
    ├── category_scan.py        Havuzda menü kategorisi taraması (paralel)
    └── export_excel.py         "Marka için Hazırlanan Format" Excel'i
```

Scriptler tek başına da çalışır:

```bash
S=~/.claude/skills/backlink-finder/scripts
python3 $S/build_pool.py "mecra.xlsx" --out calisma/pool.csv
python3 $S/filter_sites.py --pool calisma/pool.csv --exclude son6ay.txt --budget 15000 --out calisma/candidates.csv
python3 $S/category_scan.py --in calisma/candidates.csv --terms "guzellik,makyaj,cilt-bakimi" --out calisma/category_hits.csv
python3 $S/keyword_select.py --in kw_raw.json --brand flormar --profile ~/.claude/skills/backlink-finder/brands/flormar_com_tr.json --volatility volatility.json
python3 $S/export_excel.py plan.json --out backlink_plan_flormar_Ekim_2026.xlsx
```
