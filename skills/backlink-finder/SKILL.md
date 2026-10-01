---
name: backlink-finder
description: Inbound Digital'in aylık backlink planını hazırlar. Kullanıcıya marka, bütçe, son 6 ayda çalışılan siteler ve önceki backlink Excel'lerini sorar; plugin'deki güncel aracı mecra listesini (Whitepress/Exclion/LinkRaiser) kullanır; SEOmonitor'dan önceki ayın verisiyle öncelik grubundaki, dalgalanan, ilk 3 dışındaki jenerik kategori kelimelerini seçer; menüsünde markanın dikeyiyle doğrudan eşleşen kategori olan, Ahrefs ile doğrulanmış DR 25+, zararsız ve son 6 ayda kullanılmamış sitelerle bütçeyi dolduran plan kurar; her site için Inbound Notu yazar ve markanın Internal + Shared Excel'ine o ayın sayfasını ekler. Backlink planı, aylık backlink çalışması, link building, site/mecra seçimi, "X markası için kasım backlink", "bu ayın backlinkleri" gibi taleplerde mutlaka kullan; "backlink" geçmese bile markaya aylık link/mecra önerisi isteniyorsa tetikle. Toxic link/disavow bu skill'in işi değildir.
---

# Backlink Finder - Inbound Digital

Her ay markalar için backlink çalışması yapılır. Bu skill o ayın planını üretir: hangi siteden, hangi kelimeye, hangi URL'e link alınacağı, neden o sitenin seçildiği ve maliyeti. Çıktı, markanın iki Excel'ine o ayın sayfası olarak yazılır: **Internal** (ekip kontrolü için tam versiyon) ve **Shared** (markayla paylaşılan plan tablosu).

İş akışının özü üç karara dayanır:
1. **Hangi kelimeler?** SEOmonitor'da bir önceki ayın verisine bakılır, jenerik kategori kelimeleri seçilir.
2. **Hangi siteler?** Aracı havuzundan; DR 25+, zararsız, sektörle uyumlu ve son 6 ayda bu markaya kullanılmamış siteler.
3. **Bütçe dolu mu?** Site ücreti + içerik başına 750 TL; toplam "TL + KDV" bütçeyi aşmaz ve bütçenin en az ~%87'sini kullanır (15.000 → 13.000-15.000).

## Gereksinimler

- **SEOmonitor MCP** (`mcp__claude_ai_SeoMonitor__*`) - kelime, sıra, değişim, hacim, oturum verisi. Birincil ve zorunlu kaynak.
- **Ahrefs MCP** (`mcp__ahrefs__*`) - önerilecek her sitenin DR ve trafiğini öneri anında doğrulamak (`batch-analysis`), sitenin hangi sorgularda ilk 5'te olduğunu bulmak (`site-explorer-organic-keywords`) ve zararlı site kontrolü.
- WebFetch / web arama - aday sitelerin menü ve içerik kontrolü.
- Python 3 + `pandas`, `openpyxl`. İlk adımda `python3 -c "import pandas, openpyxl"` ile kontrol et; eksikse `pip3 install --user pandas openpyxl` çalıştır.

## Dosya konumları

- **Plugin dizini** `${CLAUDE_PLUGIN_ROOT}`: scriptler `${CLAUDE_PLUGIN_ROOT}/scripts/`, ekipçe paylaşılan marka profilleri `${CLAUDE_PLUGIN_ROOT}/brands/`, aylık mecra listesi `${CLAUDE_PLUGIN_ROOT}/data/mecra_listesi.xlsx` (hangi ayın listesi olduğu `data/mecra_listesi.json` içinde). Bu dizin her güncellemede yeniden yazılır; **buraya hiçbir şey yazma**.
- **Kullanıcı dizini** `~/Documents/Backlink Finder/` (yoksa oluştur):
  - `<Marka>/<Marka>_Backlink_Internal.xlsx` ve `<Marka>/<Marka>_Backlink_Shared.xlsx` - markanın tüm aylarının Excel'leri, her ay bir sayfa ("Ekim 2026", "Kasım 2026"). Marka adı baş harfi büyük, boşluksuz (ör. `Dagi`, `Flormar`, `TurkcellPasaj`).
  - `<Marka>/calisma/<Ay_Yıl>/` - o ayın ara dosyaları (pool.csv, candidates.csv, kw json'ları, plan.json). Revizyonlarda yeniden hesaplamak için tutulur.
  - `_profiller/<domain_>.json` - kullanıcının oluşturduğu ya da düzelttiği marka profilleri (plugin'deki profilin önüne geçer); `_profiller/_global_blacklist.txt` - kullanıcının eklediği zararlı siteler.

Aşağıdaki komutlarda `$P="${CLAUDE_PLUGIN_ROOT}"`, `$U="$HOME/Documents/Backlink Finder"`, `$W="$U/<Marka>/calisma/<Ay_Yıl>"`.

## 0. Başlangıç: kullanıcıya sor

Skill çağrıldığında, mesajda verilmemiş olanları **tek bir mesajda** sor (eksik olanı varsayma):

1. **Hangi marka?** (domain ya da marka adı)
2. **Bu ayın bütçesi?** (TL, KDV hariç; her ay değişir, profildeki eski bütçeyi kullanma)
3. **Son 6 ayda bu marka için çalışılan siteler?** (ay + domain listesi yapıştırılabilir, ör. "Nisan 2026 webanne.com")
4. **Daha önce yapılmış backlink çalışması Excel'i var mı?** Varsa dosya yolunu ister (birden fazla olabilir). Bu dosyalardan geçmiş aylarda kullanılan siteler ve kelimeler okunur.

Sorarken şunları da bildir:
- Kullanılacak mecra listesi: `data/mecra_listesi.json`'daki `kaynak` ve `kullanim_ayi` (ör. "Eylül 2026 mecra listesi, Ekim çalışmaları için"). Çalışma ayı listenin `kullanim_ayi`'ndan farklıysa uyar: "Plugin'deki liste <ay> için; güncel listeyi plugin yöneticisi yükleyene kadar bununla mı devam edelim, yoksa elinde yeni liste dosyası var mı?" Kullanıcı yeni dosya verirse o dosyayı kullan.
- Markanın `$U/<Marka>/<Marka>_Backlink_Internal.xlsx` dosyası zaten varsa: "Önceki aylarınız (Ekim 2026, ...) bu dosyada; son 6 ayı oradan da okuyacağım, yeni ay ayrı sayfa olarak eklenecek."

Opsiyonel girdiler (sorma, verilirse kullan): çalışma ayı (varsayılan içinde bulunulan ay), kullanıcının belirlediği kelimeler, DR alt sınırı (varsayılan 25; 25'in altına ancak açık talimatla inilir), güncel DR/trafik listesi.

## Akış

```
[0] Marka, bütçe, son 6 ay siteleri, önceki çalışma Excel'leri → dönem tarihleri
[1] Geçmiş: önceki Excel'ler + markanın Internal Excel'i + kullanıcı listesi → son 6 ay (gecmis_oku.py)
[2] Plugin'deki mecra listesi → birleşik havuz (build_pool.py)
[3] Filtre: son 6 ay, kara listeler, dil, bütçe tavanı, DR ön eleme (filter_sites.py)
[4] SEOmonitor → önceki ayın kelimeleri → öncelik grubu + dalgalanma + kategori (keyword_select.py)
[5] Kategori taraması (category_scan.py) → menü teyidi → Ahrefs DR/trafik → güvenlik kontrolü (zararlı sorgu + 18 ay geçmiş, site_kontrol.py)
    → Inbound Notu araştırması → bütçe doluluğu → kelime ataması
[6] Planı sohbette sun, revize al
[7] Onay sonrası Internal + Shared Excel'e ayın sayfasını yaz (export_excel.py)
```

### 1. Dönem ve geçmiş

Çalışma ayı X ise SEOmonitor verisi **bir önceki takvim ayının 1'i ile son günü** arasındadır. Ekim çalışması → 1-30 Eylül; Mart çalışması → 1-28/29 Şubat. Excel sayfa adı çalışma ayıdır ("Ekim 2026"), veri dönemi değil. Kullanıcıya hangi dönemi kullandığını ilk planda yaz.

Son 6 ay listesi üç kaynağın birleşimidir:
1. Kullanıcının yapıştırdığı liste → `$W/son6ay_kullanici.txt` (her satıra bir domain).
2. Kullanıcının verdiği önceki çalışma Excel'leri ve markanın kendi Internal Excel'i:
   ```bash
   python3 "$P/scripts/gecmis_oku.py" --files "<önceki.xlsx>" "$U/<Marka>/<Marka>_Backlink_Internal.xlsx" \
     --month "<Ay Yıl>" --brand-domain <domain> --out "$W/son6ay_excel.txt"
   ```
   Script sayfa adından ayı okur ("Ekim 2026", "Ekim24", "Mart 2026"); ayı anlaşılamayan sayfaları raporlar, onları kullanıcıya sor.
3. İki liste arasında fark varsa (Excel'de var, kullanıcının listesinde yok ya da tersi) kullanıcıya göster; ikisini de hariç tutmak varsayılandır.

Önceki Excel'lerdeki kelimeler de faydalıdır: son aylarda hangi kelimeye kaç kez link alındığını görmek için oku (SEOmonitor'daki "Backlink 2026 > ..." gruplarıyla birlikte).

### 2. Havuz

```bash
python3 "$P/scripts/build_pool.py" "$P/data/mecra_listesi.xlsx" [--metrics "<dr_trafik_listesi>.xlsx"] --out "$W/pool.csv"
```

Kullanıcı kendi mecra dosyasını verdiyse `$P/data/mecra_listesi.xlsx` yerine onu kullan.

**DR ve trafik kaynağı:** Aracıların listelerinde yazan DR'lar doğru değil; nihai karar her zaman öneri anında Ahrefs'ten çekilen DR/trafikle verilir. Ön eleme için öncelik sırası: `--metrics` dosyası > sayfada kullanıcının eklediği sütun (adında "güncel" geçen ya da aynı sayfada birden fazla DR/trafik sütunu varsa en sağdaki) > yok. Aracının kendi DR'ı `dr_list` sütununda sadece referans olarak kalır.

Script her sayfayı bir aracı kabul eder, sütunları esnek eşleştirir (domain, DR, "Markaya yansıtılacak fiyat" / "% Eklenen Fiyat", net fiyat, not/link sayısı) ve aynı domain birden fazla aracıda varsa en düşük markaya yansıtılacak fiyatlı kaydı tutar. Rapordaki "atlandı" satırlarına bak: bir sayfanın fiyat sütunu bulunamadıysa sütun adlarını kullanıcıya göster ve hangisinin fiyat olduğunu sor. Fiyatı asla tahmin etme veya hesaplama; markaya yansıtılacak fiyat sadece Excel'den gelir.

Link sayısı notlardan okunur ("2 link", "3 bağlantı"); okunamazsa 1 kabul edilir. Fazladan link sözü olmayan siteye birden fazla kelime atamak, aracıyla sorun çıkarır.

### 3. Filtre

```bash
python3 "$P/scripts/filter_sites.py" --pool "$W/pool.csv" --exclude "$W/son6ay_kullanici.txt" "$W/son6ay_excel.txt" \
  --budget <bütçe> --dr-min 25 --avoid "<profil.json>" \
  --blacklist "$P/brands/_global_blacklist.txt" "$U/_profiller/_global_blacklist.txt" --out "$W/candidates.csv"
```

Script domain'leri normalize eder (https, www, alt sayfa, sondaki / temizlenir), böylece `https://www.site.com/yazi` ile `site.com` eşleşir. Rapordaki elenme sayılarını kullanıcıya aynen aktar; "son 6 ay nedeniyle 14 site elendi" bilgisi kontrol için önemli.

Kullanıcı DR vermediyse script aracı DR'ını (`dr_list`) sadece kaba ön eleme için 5 puan toleransla kullanır ve bu siteleri `dr_verified=False` işaretler. Bu siteler Ahrefs ile doğrulanmadan önerilmez (bkz. 5. adım).

Kullanıcı bir trafik alt sınırı belirtirse `--traffic-min <değer>` ekle; belirtmezse trafik filtre değil, zararlı site kontrolünde ve sıralamada sinyal olarak kullanılır.

### 4. Kelime seçimi (SEOmonitor)

1. `seomonitor_get_tracked_campaigns` (limit 100) ile markanın kampanyasını domain'den bul. Kampanyanın `primary_device` değerini not et ve sıraları o cihazdan al.
2. `seomonitor_get_keyword_data` - campaign_id, dönem tarihleri, `group_id: "0"`, `order_by: search_volume`, `order_direction: desc`, limit 1000. Close variation satırlarını (`main_keyword_id` dolu olanlar) çıkar. Brand grubu (`group_id: "-1"`) kelimelerini ayrıca çekip dışla.
3. Oturum (Sessions): önce `get_keyword_data` satırındaki `traffic_data.sessions` değerine bak; hepsi 0 ise `seomonitor_get_traffic_by_keywords` (aynı dönem, `segment: non-brand`) dene. Bu uç, kampanyaya Search Console bağlı değilse 403 döner; o durumda Sessions boş bırakılır ve kullanıcıya "kampanyada GSC bağlı değil, oturum verisi yok" diye not düşülür. Değer uydurma.
4. Satırları `[{keyword, search_volume, rank, change, landing_page, sessions}]` olarak bir JSON'a yaz. Rank, change ve landing için `ranking_data.<primary_device>.rank`, `.trend` ve `landing_pages.<primary_device>.current` alanlarını kullan. `trend` pozitifse yükseliş, negatifse düşüştür; işareti aynen aktar. Yanıt büyük olduğundan dosyaya düşerse Python ile oku, elle tarama.

5. **Dalgalanma:** `seomonitor_get_daily_keyword_ranks` ile öncelik grubunun (`group_id`) dönem içi günlük sıralarını çek (yanıt büyüktür, dosyadan Python ile oku). Primary device için her kelimenin min/max sırasını, aralığını (max-min) ve gün gün sıra değişim sayısını hesapla, `volatility.json` olarak kaydet (`{"boxer": {"min": 5, "max": 19, "range": 14, "moves": 21, ...}}`).

```bash
python3 "$P/scripts/keyword_select.py" --in "$W/kw_raw.json" --brand "<marka>,<marka varyasyonu>" --top 20 \
  --profile "<profil.json>" --volatility "$W/volatility.json" --out "$W/kw_scored.json"
```

**Öncelik sırası (kelime seçerken):**
1. **SEOmonitor'da dalgalanan kelimeler.** Ay içinde sırası oynayan kelime (ör. boxer 5-19 arası, 21 değişim) Google'ın henüz karar vermediği kelimedir; link desteğiyle üst sırada sabitlenebilir. Sırası sabit duran kelimeye (ör. termal içlik 6-9) link almak daha az etki yaratır. Dalgalanma ancak ilk 3 dışındaki kelimeler arasında öncelik verir (bkz. aşağıdaki ilk 3 kuralı). Tek günlük 100'e düşüşler takip hatası olabilir; aralığı 30 ile sınırla, tek başına karar verdirme.
2. **Çekirdek ana kategori.** Markanın asıl ürünleri (Dagi: sütyen, külot, boxer, atlet, fanila, pijama, gecelik, iç çamaşırı), alt ya da sezonluk kategorilerden (termal, jüpon, kombinezon, sabahlık) önce gelir. Örneğin Dagi'de erkek atlet, termal içlikten önceliklidir. Profilde `core_category_paths` ve `minor_category_paths` olarak tutulur. İlk çalıştırmada kullanıcıya onaylat.
3. Hacim, sıra bandı ve düşüş trendi.

**Markanın öncelikli kategorileri:** Backlink, markanın ana kategorilerine alınır; yan kategoriler (Dagi için Aksesuar altındaki çorap gibi) hacmi yüksek olsa bile seçilmez. Öncelik iki kaynaktan gelir ve profile kaydedilir:
1. **SEOmonitor grupları:** `seomonitor_get_keyword_groups` ile kampanyanın gruplarına bak. "Önemli Kelimeler", "KPI" (KPI 1, KPI 2…), "Öncelikli", "Hedef", "Jenerik" gibi öncelik bildiren grupları (Dagi: "Önemli Kelimeler"; Flormar: "KPI ALL" klasörü altındaki KPI grupları) ve kategori gruplarını (Kadın Sütyen, Pijama…) bul. Hangisinin öncelik grubu olduğunu ilk çalıştırmada kullanıcıya sorup onaylat; `priority_group_ids` olarak profile yaz. Kelime verisindeki `groups` alanını JSON'a taşı ki script süzebilsin.
2. **Markanın site menüsü:** Ana menüdeki üst kategoriler ana kategoridir; "Aksesuar", "Fırsatlar" gibi bölümlerin altındaki ürünler yan kategoridir. Yan kategorilerin URL parçalarını `secondary_category_paths` olarak profile yaz.

Profil verildiğinde script, öncelikli grupta olmayan ve landing'i yan kategoriye giden kelimeleri eler. Sunumda her kelimenin ana kategorisini ve Eylül içi sıra aralığını yaz (ör. "boxer - Erkek İç Giyim, 5-19 arası dalgalandı").

**Neden jenerik kelime:** Backlink, kategori sayfasının ana kelimesini güçlendirmek için alınır. "külot fiyatları", "külot modelleri" gibi niteleyicili kelimeler yerine kategori adının kendisi ("külot", "erkek külot") seçilir; bunlar hem en yüksek hacmi taşır hem de kategori sayfasının asıl hedefidir. Script niteleyici ekleri (fiyat, modelleri, en iyi, nasıl, ucuz, kampanya, yıl vb.) olan kelimeleri jenerik saymaz ve geriye atar; hacmi log ölçekte, sıra bandını (3-20 en değerli) ve düşüşü puana katar.

Skorlu listeden kelime seçerken kendi yargını da kullan:
- Landing page bir **kategori sayfası** olmalı (ürün, blog, arama sayfası değil; script bunları geriye atar. Ürün sayfası her zaman `/products/` içermez: Flormar'da ürün URL'leri barkodla biter, ör. `/...-goz-kalemi-kahverengi-8690604109050/`; script 8+ haneli sayıyla biten yolları da ürün sayar). Landing yoksa ya da yanlış sayfa sıralanıyorsa doğru kategori URL'ini sitede bulup kullanıcıya not düş.
- Aynı kategoriye giden iki jenerik kelime varsa (gecelik / kadın gecelik) ikisi de alınabilir ama farklı sitelere atanır.
- **İlk 3'teki kelimelere backlink alınmaz.** Dönem sonu sırası 1-3 olan kelime zaten ilk 3'te; ay içinde dalgalanmış olsa bile seçilmez (script `--min-rank 4` ile eler). Odak 4-20 bandıdır.
- **Sezon:** Veri bir önceki aydan gelir ama link çalışma ayında yayınlanır. Çalışma ayında sezonu kapanan kategorileri (Ekim'de mayo, bikini, plaj) skoru yüksek olsa bile alma; sezonu açılan kategorileri (Ekim'de pijama, gecelik, termal, külotlu çorap) öne al. Elediğin sezonluk kelimeleri sunumda gerekçesiyle belirt.

Seçerken markanın geçmiş backlink gruplarına da bak (ör. "Backlink 2026 > Haziran26"): son aylarda sık link alan kelime yerine, öncelikli grupta olup desteğe ihtiyaç duyan (düşüşte ya da 2. sayfada) kelimeleri öne al.

Kaç kelime gerektiği bütçeden çıkar: seçilen sitelerin toplam link kapasitesi kadar. Kelime sayısı kapasiteyi aşarsa en düşük skorlular çıkar.

### 5. Site seçimi ve kontrol

**Kategori eşleşmesi (en önemli kural):** Önerilen her sitenin menüsünde, markanın dikeyiyle **doğrudan eşleşen** bir kategori olmalı. İçerik o kategoride yayınlanacağı için link, markanın konusuyla aynı bağlamda durur; komşu bir konuda duran link hem okuyucuya hem Google'a alakasız görünür.

Önce markanın dikeyini ve ürün gamını çıkar (SEOmonitor landing page'leri ve markanın site menüsünden). Sonra adayları iki aşamada tara:

1. **Toplu tarama (script):** Filtreden geçen tüm adayların ana sayfasını paralel indirip menü/kategori linklerinde dikeyin terimlerini arar (~600 site yaklaşık 1 dakika). Domain adına veya aracı temasına göre ön eleme yapma; Flormar denemesinde uygun sitelerin çoğu "haber", "Var", "Karma" temalı çıktı.
   ```bash
   python3 "$P/scripts/category_scan.py" --in "$W/candidates.csv" --terms "guzellik,makyaj,cilt-bakimi,kozmetik" \
     --max-price <bütçe - mevcut plan - 750> --out "$W/category_hits.csv"
   ```
   Terimleri Türkçe karakterleri sadeleştirerek yaz (moda markası: `moda,giyim,stil,kombin`; teknoloji: `teknoloji,bilim-teknoloji,mobil`). Çıktıdaki `matches` sütununda tek bir yazı URL'i (ör. `/flormardan-yeni-koleksiyon...`) kategori değildir; `/kategori/guzellik/`, `/guzellik-bakim/`, `/moda-ve-guzellik` gibi kategori yolları adaydır. `bahis_sinyali` doluysa site ana sayfasında bahis/casino terimleri geçiyor demektir; ele ya da WebFetch ile bak.
2. **Menü teyidi (WebFetch):** Script'in bulduğu ve Ahrefs kontrolünden geçen adaylar için menüde gerçekten bu kategori var mı bak ve kategori adını birebir kaydet. Köşe yazısı, etiket sayfası ya da sayfa içi blok kategori sayılmaz (ör. egehaber "Güzellik ve Bakım Köşesi" bir yazar köşesi). Site WebFetch'e 403 dönüyor ya da açılmıyorsa menüsü doğrulanamaz; önerme (ör. birmilyonnokta.com). Kategori var ama sitenin ana konusu çok farklıysa (ör. örgü sitesi mimuu.com'da "Güzellik-Bakım") ya da kategoride neredeyse içerik yoksa (ör. doktorumnedio.com Güzellik'te 3 yazı) bunu sunumda belirt ve daha güçlü eşleşmeyi tercih et.

Eşleşme tablosu:

| Marka dikeyi | Eşleşen kategori (yeterli) | Eşleşmeyen (yetersiz) |
|---|---|---|
| Moda / giyim / iç giyim (Dagi) | Moda, Giyim, Stil, Kombin, Anne-Bebek Modası | Saç bakımı, Güzellik, Makyaj, Kişisel gelişim, Saat/aksesuar |
| Kozmetik / makyaj (Flormar) | Güzellik, Makyaj, Cilt Bakımı, Kişisel Bakım, Moda ve Güzellik | Moda (tek başına), Sağlık, köşe yazısı |
| Teknoloji / elektronik | Teknoloji, Bilim-Teknoloji, Mobil, Oyun (oyun ürünü ise) | Ekonomi, Genel haber |
| Ev / yapı / seramik (VitrA) | Dekorasyon, Ev-Yaşam, Mimari, Yapı | Genel yaşam, Magazin |
| Turizm / otel | Gezi, Seyahat, Tatil | Yerel haber |

Tabloda olmayan dikeylerde aynı mantığı kur: kategori adı markanın ürünlerini doğrudan anlatmalı.

- **Uygun:** Menüde doğrudan eşleşen kategori var (ana konu olarak ya da alt kategori olarak; ör. anne sitesinde Eğlence > "Moda").
- **Uygun değil:** Eşleşen kategori yok. Tek tük konu yazıları olması ("Sizden Gelenler" altında birkaç kombin yazısı), komşu kategori (moda markası için saç bakımı) ya da genel "Yaşam"/"Magazin" kategorisi yetmez. DR'ı ve trafiği ne kadar iyi olursa olsun önerilmez, yedek listeye de girmez.

Domain adından ya da aracının "Tema" sütunundan karar verme; aracı temaları ("Var", "Yok", "Karma", "diğer temalar") çoğu zaman anlamsızdır, "moda-guzellik" yazan site sadece saç bakımı sitesi çıkabilir. Sunumda her site için eşleşen kategorinin adını ve URL'ini yaz (ör. "Eğlence > Moda" - https://annelertoplandik.com/blog/category/eglence/moda/). Bu kategori aynı zamanda içeriğin yayınlanması istenecek kategoridir; plan JSON'da sitenin `category` ve `category_url` alanlarına yaz.

Bütçe aralığında kategorisi eşleşen site azsa önce aşağıdaki "Bütçe doluluğu" adımlarını uygula; uyumu gevşetme.

**DR/trafik doğrulama:** Kategori eşleşmesinden geçen kısa listeyi (tipik 10-30 site) `mcp__ahrefs__batch-analysis` ile tek seferde kontrol et (önce `mcp__ahrefs__doc` ile şemaya bak; `mode: subdomains`, `protocol: both`, `country: TR`, select: `domain_rating, org_traffic, org_keywords, refdomains, linked_domains`). Sunumda ve Excel'de bu DR kullanılır. Ahrefs DR'ı 25 altındaysa ele.

**Seçim mantığı:**
- Bütçe = Σ(site ücreti) + 750 TL × site sayısı. İçerik ücreti **site başına** (her sitede bir içerik yayınlanır), link sayısından bağımsızdır.
- **Bütçe doluluğu zorunlu:** Toplam bütçeyi aşamaz ve bütçenin en az ~%87'sini kullanmalı (15.000 TL için 13.000-15.000; 10.000 için 8.700-10.000). Yarısı boş bir plan (ör. 15.000'de 6.500) sunulmaz. Hedefe ulaşmadan önce sırayla:
  1. `category_scan.py`'yi tüm adaylar üzerinde çalıştır (fiyat sınırı = kalan bütçe - 750); tema/isim ön elemesi yapma.
  2. Kalan bütçeye tek başına oturan bir site (ör. 8.500 kalan → 7.750'lik 3 linkli site) ile iki-üç küçük siteyi karşılaştır; alan çeşitliliği ve trafik dengesine göre seç.
  3. Haber sitelerini de tara (en fazla 1-2, menüde Güzellik/Moda vb. kategorisi olanlar).
  Kurallar (kategori eşleşmesi, DR 25, zararlı site, son 6 ay) bütçeyi doldurmak için gevşetilmez. Bütün havuz tarandığı halde hedefe ulaşılamıyorsa, sunumda kaç sitenin hangi aşamada elendiğini göster ve kullanıcıya kuralı esnetecek seçenekleri sor (ör. "DR 20 olan yuksektopuklar eklenirse 13.750 olur").
- Öncelik: kategori eşleşmesi (zorunlu) > trafik/DR sağlığı > link başına maliyet (çok linkli siteler aynı fiyatla daha fazla kelime taşır).
- Haber/gazete siteleri pakette en fazla 1-2 adet; niş ve sektörel bloglar önce gelir.
- Aynı hedef URL'e giden kelimeler farklı sitelere dağıtılır (anchor ve kaynak çeşitliliği).
- Çok linkli sitede kelimeler tercihen farklı URL'lere gider.

**Site güvenlik kontrolü (zorunlu)** - plana ya da yedek listeye girecek **her** site için; havuzun tamamı için değil (maliyet yüksek). Bir site bu kontrolden geçmeden sunulmaz.

1. **PBN/link çiftliği kalıbı** (batch-analysis sonucundan): yüzlerce referring domain ama organik trafik ~0 (ör. 800 refdomain, 0 trafik) ya da DR yüksek ama refdomain çok az (ör. DR 65, 12 refdomain: şişirilmiş DR). Ele.
2. **Zararlı sorgu taraması (sitenin sıralama aldığı TÜM kelimelerde):** Menü ve ana sayfa temiz görünse bile site, forumu, yorumları ya da tek bir yazısı üzerinden cinsel/bahis sorgularında sıralanıyor olabilir. Ahrefs `site-explorer-organic-keywords` ile pozisyon filtresi olmadan, aşağıdaki terim filtresiyle çek (`target` = site, `mode: subdomains`, `country: tr`, `date` = dönem sonu, `select: keyword,best_position,volume,best_position_url`, `order_by: volume:desc`, `limit: 30`):
   ```json
   {"or":[{"field":"keyword","is":["isubstring","seks"]},{"field":"keyword","is":["isubstring","sex"]},{"field":"keyword","is":["isubstring","porno"]},{"field":"keyword","is":["isubstring","porn"]},{"field":"keyword","is":["isubstring","sikiş"]},{"field":"keyword","is":["isubstring","ifşa"]},{"field":"keyword","is":["isubstring","çıplak"]},{"field":"keyword","is":["isubstring","escort"]},{"field":"keyword","is":["isubstring","erotik"]},{"field":"keyword","is":["isubstring","xxx"]},{"field":"keyword","is":["isubstring","bahis"]},{"field":"keyword","is":["isubstring","casino"]},{"field":"keyword","is":["isubstring","kumar"]},{"field":"keyword","is":["isubstring","iddaa"]},{"field":"keyword","is":["isubstring","slot"]},{"field":"keyword","is":["isubstring","deneme bonusu"]},{"field":"keyword","is":["isubstring","bet giriş"]}]}
   ```
   Ayrıca filtresiz `best_position <= 5` ilk 20 sorguya bak (Inbound Notu için de gerekir); ilaç satışı, kripto/forex dolandırıcılığı, sahte belge gibi terim listesinde olmayan riskleri gözle kontrol et.
3. **Organik geçmiş:** Ahrefs `site-explorer-metrics-history` ile son 18 ayın aylık organik trafiği (`date_from` = 18 ay önce, `history_grouping: monthly`, `select: date,org_traffic`). Sadece son 1-3 aydır sıralama alan site (yeni açılmış, süresi dolmuş domainden canlandırılmış ya da link satışı için şişirilmiş) güvenilir değildir.
4. **Karar (script):** 2 ve 3'ün sonuçlarını `$W/ahrefs_kontrol.json`'a yaz (`{"site.com": {"history": [...], "harmful": [...]}}`) ve çalıştır:
   ```bash
   python3 "$P/scripts/site_kontrol.py" --in "$W/ahrefs_kontrol.json" --out "$W/site_kontrol.csv"
   ```
   - **ELE:** cinsel/bahis sorgusunda ilk 20'de sıralama ya da bu tür 3+ sorgu; anlamlı trafik son 3 ay içinde başlamış (yeni site). Plana ve yedek listeye alınmaz.
   - **DİKKAT:** son ay trafiği önceki 6 ayın medyanının 3 katından fazla (ani sıçrama) ya da zirveye göre %75+ düşüş (çöküş). Alınabilir ama sunumda gerekçesiyle belirtilir; kullanıcı karar verir.
   - Script masum eşleşmeleri (unisex, seksek, transeksüel, "kumarki" soyadı...) eler; yine de çıkan sorguları gözle doğrula, yanlış alarmı gerekçesiyle not et.

   Örnekler: annelertoplandik.com 383K trafikli büyük bir anne forumu, ama forum başlıkları üzerinden "… sikiş hikayeleri" 5., "… pornoları" 1., "… escort numarası" 7. sırada → ELE. begonya.com "… ifşa" sorgusunda 10. → ELE. doktorumnedio.com 17 ay boyunca aylık ~50-120 trafikle durup son ayda 4.722'ye çıkmış → ELE (yeni). beyruni.com zirveden %87 düşmüş → DİKKAT.
5. Ahrefs `site-explorer-outlinks-stats` / `linked-domains`: dış link verdiği domain sayısı içerik hacmine göre çok yüksekse link çiftliği.
6. Siteye WebFetch ile göz at: ana sayfa ve "sponsorlu/misafir yazı" sayfalarında alakasız konularda yoğun yazı, spin içerik, gizli bahis linkleri, hacklenmiş görüntü varsa ele.

Elenen her site için kısa gerekçe yaz ve kullanıcıya "yerel kara listeye (`$U/_profiller/_global_blacklist.txt`) ekleyeyim mi?" diye sor; eklenen siteleri plugin yöneticisine de iletmesini öner ki ortak listeye girsin; zararlı site marka fark etmeksizin zararlıdır. Sadece bu markayla uyumsuzsa marka profilinin `avoid_sites` alanı önerilir.

**Uyum kontrolü:** Domain adı ve kategoriden sitenin gerçek konusunu tahmin etme, doğrula (WebFetch / web arama). Örnek çıktı:
```
✗ begonya.com - Moda/Makyaj kategorileri var ama "… ifşa" sorgusunda 10. sırada
✓ annebebek.com.tr - anne-bebek dergisi, "Anne Bebek Modası" bölümü var
✗ hairist.com.tr - aracı teması "moda-guzellik" ama menüsü sadece saç bakımı; Moda kategorisi yok
✗ webanne.com - Kadın > Güzellik var, Moda kategorisi yok (birkaç dağınık kombin yazısı yetmez)
✗ kisiselgelisim.com - kişisel gelişim; trafiği iyi ama Moda kategorisi yok
✗ kadingirisim.com - 830 refdomain, 0 trafik (PBN kalıbı)
✗ istanbeautiful.com - adı güzellik gibi ama İstanbul gezi/medikal turizm sitesi; Güzellik kategorisi yok
✗ evosangels.com - "Sağlık & Güzellik" kategorisi var ama ana sayfada iddaa programları (bahis)
✗ snobmagazin.com - menüde "Moda ve Güzellik" var ama müstehcen magazin sorgularında 1. sırada (zararlı sorgu taraması)
✗ annelertoplandik.com - Moda kategorisi ve 383K trafik var ama forum başlıklarıyla cinsel sorgularda ilk 10'da
✓ mimuu.com - örgü/hobi ağırlıklı ama menüde "Güzellik - Bakım" kategorisi var, sorguları temiz
✗ ornekhaber.net - bahis anahtar kelimelerinde sıralanıyor (zararlı)
```
Uyumsuz/zararlı çıkan sitenin yerine havuzdan sıradaki uygun siteyi al ve aynı kontrollerden geçir.

**Inbound Notu (her site için zorunlu):** Plan tablosunda her sitenin yanında, o sitenin neden seçildiğini anlatan 1-2 cümlelik not yer alır; hem Internal'da hem Shared'da görünür, yani markanın da okuyacağı bir gerekçedir. Somut ve doğrulanmış verilerden kur, genel övgü yazma:
- **Kategori:** eşleşen menü kategorisi ("Moda > Kombin kategorisi bulunmaktadır").
- **Trafik/DR:** Ahrefs'ten o gün çekilen değer ("aylık ~10,7K organik trafik, DR 48").
- **Sorgu gücü:** sitenin markanın konusuyla ilgili bir sorguda ilk 5'te olması. `mcp__ahrefs__site-explorer-organic-keywords` ile (`target` = site, `country: tr`, `select: keyword,best_position,volume,best_position_url`, `where` ile `best_position <= 5`, hacme göre azalan, limit 50) çek; markanın kategorileriyle ilgili en yüksek hacimli 1-2 sorguyu seç ("'kombin önerileri' sorgusunda 3. sırada"). İlgili sorgu bulunmazsa bu kısmı yazma, uydurma.
- Varsa ek artı: çok link verip tek ücret alması ("3 link tek ücret"), kategori sayfasında uzun süre yayında kalması (aracı notundan).

Örnek: "Moda > Kombin kategorisi bulunmaktadır; aylık ~3,1K organik trafik; 'bordo elbise kombin' sorgusunda 2. sırada; 3 link tek ücret."

Marka ile paylaşıldığı için fiyat, marj, aracı adı ve PBN/eleme gibi iç değerlendirmeleri bu nota yazma.

### 6. Sunum ve revize

Kullanıcıya önce özet, sonra tablo:

```
Dagi - Ekim 2026 backlink planı (veri: 1-30 Eylül 2026, SEOmonitor)
Bütçe: 20.000 TL | Plan: 19.350 TL + KDV (6 site × 750 içerik dahil)
Havuz: 1.054 site → son 6 ay: -13, fiyat: -443, kategori eşleşmesi yok: -..., PBN: -..., zararlı sorgu: -..., yeni site: -..., DR<25 (Ahrefs): -... → N uygun aday
Güvenlik kontrolü: her site için zararlı sorgu + 18 ay geçmiş sonucu (TEMİZ / DİKKAT + gerekçe)

| Domain | DR (Ahrefs) | Trafik (Ahrefs) | Site Ücreti | İçerik | Keyword | Link verilecek URL (marka) | Yayın kategorisi (ad + URL) | Inbound Notu |
...
Seçilen kelimeler: | Keyword | Ana kategori | Hacim | Rank | Değişim | Ay içi aralık (dalgalanma) | Landing | Oturum |
Elenen sezonluk kelimeler, elenen siteler (gerekçeli: kategori yok / PBN / DR) ve yedek aday listesi (sadece kategorisi eşleşen siteler; bütçe dışı olanlar fiyatıyla)
```

Tabloda her kelimenin **link verilecek URL'i** (markanın kategori sayfası, tam yol) ve her sitenin **yayın kategorisi URL'i** mutlaka yer alır; ekip linki ve yayın yerini tablodan doğrudan kontrol edebilmeli. Sunmadan önce her iki URL tipini `curl -s -o /dev/null -L -w "%{http_code}"` ile kontrol et; 200 dönmeyen URL'i kullanma, doğrusunu bul.

Ardından sor: "Değiştirmek istediğin site/kelime var mı, yoksa Excel'i çıkarayım mı?" Revizede bütçeyi ve son 6 ay kuralını yeniden kontrol et.

claude.ai'da çalışılıyorsa ve kullanıcı isterse planı interaktif panel olarak da sunabilirsin; panel tasarımı `${CLAUDE_PLUGIN_ROOT}/references/widget.md` dosyasında.

### 7. Excel export (Internal + Shared, aylık sayfa)

Planı `$W/plan.json`'a yaz (şema `scripts/export_excel.py` başında; her sitede `inbound_note`, `category`, `category_url` dolu olmalı) ve çalıştır:

```bash
python3 "$P/scripts/export_excel.py" "$W/plan.json" \
  --internal "$U/<Marka>/<Marka>_Backlink_Internal.xlsx" \
  --shared   "$U/<Marka>/<Marka>_Backlink_Shared.xlsx"
```

Her marka için iki kalıcı dosya vardır; her çalışma ayı bu dosyalara **yeni bir sayfa** olarak eklenir ("Ekim 2026", sonra "Kasım 2026"...). Dosya yoksa oluşturulur. Aynı ayın sayfası zaten varsa (revizyon) yalnızca o sayfa yeniden yazılır, diğer aylara dokunulmaz. Sayfalar kronolojik sıralanır.

**Internal** (ekip içi, tam versiyon) - sayfada üç blok:
1. **Plan tablosu:** Domain | DR | Site Ücreti | İçerik Ücreti | Keyword | URL | İçerik | Yayınlanan Link | Inbound Notu. Her site renkli blok (sarı/mavi dönüşümlü); çok linkli sitelerde Domain, DR, ücretler, İçerik, Yayınlanan Link ve Inbound Notu hücreleri birleşik. URL `=HYPERLINK("https://www.marka.com/yol", "/yol")`. İçerik ve Yayınlanan Link boş bırakılır (yazım ve yayın sonrası ekip doldurur). Altında "Total: X TL + KDV".
2. **Fiyat tablosu:** Domain | DR | net fiyat | %20 fiyat (markaya yansıtılan) | Mecra | Not ("2 link") | Yayın Kategorisi (kategori URL'ine linkli).
3. **Kelime tablosu:** Keyword | Volume | Rank | Change | Landing Page | Sessions (SEOmonitor, veri dönemi).

**Shared** (markayla paylaşılan) - sayfada yalnızca 1. blok (plan tablosu + Inbound Notu + Total). Fiyat ve kelime blokları bu dosyada yoktur; markaya bu dosya gönderilir.

Teslimde iki dosyanın yolunu ve eklenen sayfa adını yaz. Markanın Internal dosyası sonraki ayların son 6 ay kontrolünde otomatik okunur; ayrı bir geçmiş kaydı tutmaya gerek yok.

## Marka profili

Profil arama sırası: önce `$U/_profiller/<domain_>.json` (kullanıcının yerel profili), yoksa `$P/brands/<domain_>.json` (plugin'le gelen ortak profil; ör. `dagi_com_tr.json`, `flormar_com_tr.json`). Plugin dizinine yazılmaz: yeni profil oluşturduğunda ya da ortak profili düzelttiğinde `$U/_profiller/` altına kaydet ve kullanıcıya "bu profili plugin yöneticisine ilet, ortak listeye eklensin" diye hatırlat. Profil yoksa ilk çalıştırmada markanın menüsünü ve SEOmonitor gruplarını inceleyip dikeyi, eşleşen site kategorilerini, öncelik gruplarını, ana/yan kategorileri ve sezonları çıkar; kullanıcıya onaylat, kaydet. Varsa her çalıştırmada kullan, kullanıcı düzeltirse güncelle.

```json
{
  "domain": "dagi.com.tr",
  "brand_tokens": ["dagi", "dağı"],
  "sector": "iç giyim",
  "vertical": "moda / iç giyim",
  "matching_site_categories": ["Moda", "Giyim", "Stil", "Kombin"],
  "priority_group_ids": [192130],
  "main_categories": ["İç Giyim", "Ev-Uyku Giyim", "Plaj Giyim", "Spor Giyim", "Günlük Giyim"],
  "secondary_category_paths": ["corap", "canta", "terlik", "sapka", "aksesuar"],
  "core_category_paths": ["boxer", "atlet", "fanila", "sutyen", "kulot", "tanga", "ic-giyim", "pijama", "gecelik"],
  "minor_category_paths": ["termal", "jupon", "kombinezon", "sabahlik"],
  "seasonal": {"Plaj Giyim": "Nisan-Ağustos", "Termal": "Ekim-Şubat"},
  "dr_min": 25,
  "content_fee": 750,
  "seomonitor_campaign_id": 110467,
  "avoid_sites": [],
  "notes": ""
}
```

Bütçe profile yazılmaz; her ay sorulur.

## Kurallar (özet)

1. **Son 6 ay:** Kullanıcının verdiği listedeki hiçbir site önerilmez, yedek listede bile.
2. **Kategori eşleşmesi:** Menüsünde markanın dikeyiyle doğrudan eşleşen kategori (moda markası → Moda; teknoloji → Teknoloji) olmayan site önerilmez, yedek listede de. Komşu kategori ya da dağınık yazılar yetmez.
3. **DR 25 altı** önerilmez. DR ve trafik öneri anında Ahrefs'ten doğrulanır; aracı listesindeki DR karar için kullanılmaz.
4. **Zararlı ya da yeni site önerilmez:** sıralama aldığı herhangi bir kelimede cinsel/bahis içerik varsa (ilk 20'de ya da 3+ sorgu), sadece son 1-3 aydır sıralama alıyorsa, PBN/link çiftliği ya da hacklenmiş ise. Her site `site_kontrol.py` ile değerlendirilir.
5. **Fiyat** sadece "Markaya yansıtılacak fiyat" sütunundan; içerik site başına 750 TL. Toplam bütçeyi aşmaz ve en az ~%87'sini kullanır.
6. **İlk 3'teki kelimeler** (dönem sonu sıra 1-3) seçilmez. **Kelimeler** markanın öncelikli gruplarından ve ana menü kategorilerinden seçilir; önce dalgalanan, sonra çekirdek kategori kelimeleri gelir; yan kategori kelimeleri (aksesuar vb.) seçilmez. Kelimeler SEOmonitor'dan, çalışma ayından önceki takvim ayı verisiyle. Jenerik kategori kelimeleri öncelikli, brand kelimeler hariç. Çalışma ayının sezonuna uymayan kategoriler alınmaz. Sıra/hacim asla tahmin edilmez; SEOmonitor'a erişilemezse kullanıcıdan export iste.
7. **Dil:** TR markada yabancı dil (EN) sayfasındaki siteler elenir.
8. **Inbound Notu** her sitede zorunlu; doğrulanmış kategori, trafik ve ilk 5 sorgu bilgisinden kurulur, fiyat/aracı/iç değerlendirme içermez.
9. **Çıktı** markanın `~/Documents/Backlink Finder/<Marka>/` altındaki Internal ve Shared Excel'lerine ayın sayfası olarak yazılır; plugin dizinine hiçbir şey yazılmaz.
10. **Çıktı dili** Türkçe; em dash yerine tire kullan.

## Hata durumları

- **SEOmonitor'da kampanya bulunamadı:** Kampanya listesini göster, hangisi olduğunu sor.
- **Mecra Excel'inde fiyat sütunu tanınmadı:** Sütun adlarını göster, sor.
- **Bütçe dolmuyor:** Önce "Bütçe doluluğu" adımlarını uygula (tüm havuzda kategori taraması dahil). Yine dolmuyorsa elenme dökümünü göster ve kural esnetme seçeneklerini sor; yarı boş planı kendiliğinden sunma.
- **Bütçe yetmiyor / aday çok az:** Kaç sitenin elendiğini aşama aşama göster, alternatif sun (DR üst sınırını açmak, bütçe artışı, link sayısı fazla sitelere yönelmek). DR 25 alt sınırını ve son 6 ay kuralını kendiliğinden gevşetme.
- **Mecra listesi eski ay için:** `data/mecra_listesi.json`'daki `kullanim_ayi` çalışma ayından farklıysa kullanıcıya söyle; yeni dosya verirse onu kullan, yoksa onayıyla mevcut listeyle devam et.
- **Excel dosyası açık/kilitli:** Kaydetme hatası alınırsa kullanıcıdan Excel'i kapatmasını iste ve tekrar çalıştır.
- **Son 6 ay listesi gelmedi:** Sor; kullanıcı "yok/ilk ay" derse markanın Internal Excel'ini ve verdiği önceki çalışma Excel'lerini kontrol edip devam et.
