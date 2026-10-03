# Ahrefs kotası dolduğunda DataForSEO ile devam

Ahrefs MCP çağrıları kota/limit hatası verirse ("API units", "limit", "quota", "insufficient", 402/403/429)
ya da çalışma başındaki kota kontrolünde kalan birim yetersizse, Ahrefs'i bırak ve aynı kontrolleri
DataForSEO MCP ile yap. **Önce kullanıcıya yaz:**

> "Ahrefs MCP kotası dolduğu için DataForSEO ile devam ediyorum. DR yerine DataForSEO'nun domain
> verileri kullanılacak; Excel'de bu siteler 'DataForSEO' notuyla işaretlenecek."

DataForSEO MCP bağlı değilse kullanıcıya söyle ve bekle: "Ahrefs kotası dolu ve DataForSEO MCP bağlı değil;
kota yenilenene kadar ya da DataForSEO bağlanana kadar site doğrulaması yapamıyorum." Doğrulanmamış site önerme.

## Ahrefs → DataForSEO karşılıkları

| Amaç | Ahrefs | DataForSEO (MCP araç adları sunucuya göre değişebilir) |
|---|---|---|
| Trafik + kelime sayısı (toplu) | `batch-analysis` | `dataforseo_labs_google_domain_rank_overview` (location_code 2792, language_code "tr"): `metrics.organic.etv` = tahmini trafik, `metrics.organic.count` = kelime sayısı. Birden fazla site için `dataforseo_labs_bulk_traffic_estimation` |
| Otorite (DR yerine) | `domain_rating` | `backlinks_summary` / `backlinks_bulk_ranks`: `rank` (0-1000 ölçeği, DR ile birebir değil). Referring domain: `referring_domains` |
| Sıralanan kelimeler (zararlı tarama, ilk 5 sorgu) | `site-explorer-organic-keywords` | `dataforseo_labs_google_ranked_keywords` (target = domain, location_code 2792, language_code "tr") |
| 18 ay organik geçmiş | `site-explorer-metrics-history` | `dataforseo_labs_google_historical_rank_overview`: aylık `metrics.organic.etv` |

## Zararlı kelime filtresi (ranked_keywords)

DataForSEO bir istekte en fazla 8 filtre koşulunu kabul eder; terimleri 3 isteğe böl:

```json
["keyword_data.keyword","like","%seks%"],"or",["keyword_data.keyword","like","%sex%"],"or",["keyword_data.keyword","like","%porno%"],"or",["keyword_data.keyword","like","%sikiş%"]
```
```json
["keyword_data.keyword","like","%ifşa%"],"or",["keyword_data.keyword","like","%çıplak%"],"or",["keyword_data.keyword","like","%escort%"],"or",["keyword_data.keyword","like","%erotik%"]
```
```json
["keyword_data.keyword","like","%bahis%"],"or",["keyword_data.keyword","like","%casino%"],"or",["keyword_data.keyword","like","%iddaa%"],"or",["keyword_data.keyword","like","%deneme bonusu%"]
```

İlk 5 sorgu için: `filters: ["ranked_serp_element.serp_item.rank_group","<=",5]`, `order_by: ["keyword_data.keyword_info.search_volume,desc"]`, limit 20.

## site_kontrol.py girdisine çevirme

`ahrefs_kontrol.json` ile aynı yapıyı kullan (dosya adı değişmez):
- `history`: `[{"date": "<yıl-ay-01>", "org_traffic": <metrics.organic.etv>}]`
- `harmful`: `[{"keyword": keyword_data.keyword, "best_position": ranked_serp_element.serp_item.rank_group, "volume": keyword_data.keyword_info.search_volume}]`

## DR 25 kuralı ve Excel

DataForSEO'da Ahrefs DR'ı yoktur. Bu durumda:
- DR sütununa aracı listesindeki DR'ı yaz, plan JSON'da sitenin `dr_kaynak` alanını `"aracı (Ahrefs doğrulanamadı)"` yap;
  Inbound Notu'ndaki trafik değeri DataForSEO'dan gelir ("aylık ~X organik trafik (DataForSEO)").
- Aracı DR'ı 25 altındaysa ya da DataForSEO `rank` çok düşükse (ör. < 100) siteyi önerme.
- Sunumda bu siteleri "Ahrefs ile doğrulanamadı, DataForSEO verisi" diye işaretle; kota yenilenince Ahrefs ile
  yeniden kontrol edilmesini öner.
