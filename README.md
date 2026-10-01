# backlink-finder

Inbound Digital'in aylık backlink planını hazırlayan [Claude Code](https://claude.com/claude-code)
plugin'i. Marka, bütçe ve son 6 ayda çalışılan siteleri sorar; plugin içindeki güncel aracı mecra
listesinden uygun siteleri bulur, SEOmonitor'dan kelime seçer, her site için neden seçildiğini
yazar ve markanın **Internal** ve **Shared** Excel'lerine o ayın sayfasını ekler.

## Kurulum (bir kez)

### Seçenek A - Terminalden tek komut (en kolay)

Terminali açın, aşağıdaki satırın tamamını kopyalayıp yapıştırın:

```bash
claude plugin marketplace add feyzanurcercioglu/backlink-finder-skill && claude plugin install backlink-finder@inbound-seo
```

### Seçenek B - Claude Code içinden, iki ayrı adım

Komutları **tek tek** kopyalayıp her birinden sonra Enter'a basın; ikisini birlikte yapıştırmayın.

**Adım 1** - marketplace'i ekleyin:

```
/plugin marketplace add feyzanurcercioglu/backlink-finder-skill
```

**Adım 2** - plugin'i kurun:

```
/plugin install backlink-finder@inbound-seo
```

> `/plugin` menüsünden **Add Marketplace** ekranını açtıysanız "Enter marketplace source" kutusuna
> **sadece** `feyzanurcercioglu/backlink-finder-skill` yazın. Sonra Adım 2'ye geçin.

### Kurulumdan sonra

Claude Code'u yeniden başlatın. Önerilen: `/plugin` > **Marketplaces** > `inbound-seo` >
**Enable auto-update**. Böylece her ay yeni mecra listesi ve kural güncellemeleri kendiliğinden gelir.

> Daha önce `git clone ... ~/.claude/skills/backlink-finder` ile kurduysanız o klasörü silin
> (`rm -rf ~/.claude/skills/backlink-finder`). claude.ai'daki eski "backlink-skill"i de devre dışı
> bırakın; aynı taleplerde çakışırlar.

## Güncelleme

Auto-update açıksa bir şey yapmanıza gerek yok. Elle güncellemek için terminalde tek satır:

```bash
claude plugin marketplace update inbound-seo && claude plugin update backlink-finder@inbound-seo
```

ya da Claude Code içinde önce `/plugin marketplace update inbound-seo`, sonra `/plugin` > **Installed** >
`backlink-finder` > **Update now**. Ardından Claude Code'u yeniden başlatın.

## Kullanım

```
/backlink-finder:backlink-finder
```

ya da doğrudan yazın: "Dagi için Kasım backlink çalışması hazırla". Plugin şunları sorar:

1. Hangi marka?
2. Bu ayın bütçesi (KDV hariç)?
3. Son 6 ayda bu marka için çalışılan siteler (ay + domain listesi)
4. Daha önce yapılmış backlink çalışması Excel'i (varsa dosya yolu)

Plan önce sohbette tablo olarak gelir; revizeler sonrası onay verince Excel'e yazılır.

## Çıktılar

Her marka için `~/Documents/Backlink Finder/<Marka>/` altında iki kalıcı dosya. Her çalışma ayı
**yeni bir sayfa** olarak eklenir ("Ekim 2026", "Kasım 2026" ...). Aynı ay tekrar çalışılırsa sadece
o sayfa güncellenir.

| Dosya | İçerik | Kime |
|---|---|---|
| `<Marka>_Backlink_Internal.xlsx` | Plan tablosu + fiyat tablosu (net / markaya yansıtılan fiyat, mecra, yayın kategorisi) + kelime tablosu (hacim, sıra, değişim, oturum) | Ekip içi |
| `<Marka>_Backlink_Shared.xlsx` | Sadece plan tablosu: Domain, DR, Site Ücreti, İçerik Ücreti, Keyword, URL, İçerik, Yayınlanan Link, **Inbound Notu**, Total | Markaya gönderilir |

**Inbound Notu** her sitenin neden seçildiğini anlatır, ör. "Moda > Kombin kategorisi bulunmaktadır;
aylık ~3,1K organik trafik; 'bordo elbise kombin' sorgusunda 2. sırada; 3 link tek ücret."

Ara dosyalar `~/Documents/Backlink Finder/<Marka>/calisma/<Ay_Yıl>/` altında tutulur.

## Nasıl seçiyor

- **Kelime:** SEOmonitor'da markanın öncelik grubu ("Önemli Kelimeler", "KPI" ...), önceki ayın verisi;
  ay içinde sırası dalgalanan ve çekirdek ana kategoriye ait jenerik kelimeler. İlk 3'teki,
  sezon dışı, yan kategori (aksesuar vb.) ve ürün/blog sayfasına sıralanan kelimeler alınmaz.
- **Site:** menüsünde markanın dikeyiyle doğrudan eşleşen kategori (moda → Moda, kozmetik →
  Güzellik/Makyaj, teknoloji → Teknoloji); DR ve trafik Ahrefs'ten o gün (DR 25 altı yok);
  PBN kalıbı ve bahis/yetişkin içerik yok; son 6 ayda bu markaya kullanılmamış.
- **Bütçe:** site ücreti + site başına 750 TL içerik; bütçeyi aşmaz, en az ~%87'sini kullanır.

## Gereksinimler

- **SEOmonitor** connector (claude.ai > Settings > Connectors)
- **Ahrefs MCP**
- **Python 3**, `pandas`, `openpyxl` (eksikse plugin ilk çalıştırmada `pip3 install --user` ile kurar)

## Yönetici: aylık mecra listesi güncellemesi

Ay başında yeni "(Internal) Inbound x Backlink Siteleri - <Ay Yıl>.xlsx" geldiğinde:

1. Dosyayı `data/mecra_listesi.xlsx` olarak değiştir.
2. `data/mecra_listesi.json`'da `kaynak`, `liste_ayi`, `kullanim_ayi`, `guncelleme` alanlarını güncelle.
3. `.claude-plugin/plugin.json`'da `version`'ı artır (ör. 1.0.0 → 1.1.0). **Sürüm artmazsa ekip güncellemeyi almaz.**
4. Commit + push.

Kural/script değişikliklerinde de aynı şekilde sürüm artırılıp push edilir. Yeni marka profilleri
(`brands/<domain>.json`) ve ortak kara liste (`brands/_global_blacklist.txt`) da buradan dağıtılır;
ekip kendi oluşturduğu profilleri `~/Documents/Backlink Finder/_profiller/` altında bulur ve
yöneticiye iletir.

## Yapı

```
backlink-finder-skill/
├── .claude-plugin/
│   ├── marketplace.json          Marketplace: inbound-seo
│   └── plugin.json               Plugin: backlink-finder (version burada)
├── skills/backlink-finder/
│   └── SKILL.md                  İş akışı ve kurallar
├── data/
│   ├── mecra_listesi.xlsx        Aylık aracı mecra listesi (yönetici günceller)
│   └── mecra_listesi.json        Listenin ayı ve kaynağı
├── brands/                       Ortak marka profilleri + kara liste
├── scripts/
│   ├── gecmis_oku.py             Önceki Excel'lerden son 6 ay siteleri
│   ├── build_pool.py             Mecra listesini birleşik havuza çevirir
│   ├── filter_sites.py           Son 6 ay, dil, bütçe, DR ön elemesi
│   ├── keyword_select.py         Öncelik grubu + dalgalanma + kategori skorlaması
│   ├── category_scan.py          Havuzda menü kategorisi taraması (paralel)
│   └── export_excel.py           Internal + Shared Excel'e aylık sayfa
├── references/widget.md          claude.ai için opsiyonel panel
└── requirements.txt
```
