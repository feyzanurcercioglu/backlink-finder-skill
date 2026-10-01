# İnteraktif Panel (opsiyonel, claude.ai)

Claude Code'da plan markdown tablo olarak sunulur; bu panel sadece claude.ai'da ve kullanıcı isterse kullanılır. Panel, SKILL.md'deki akışın görsel karşılığıdır; iş kuralları (son 6 ay, DR 25, zararlı site, 750 TL içerik, bütçe) aynen geçerlidir.

### Widget Yapısı

- **Üst form (sabit):** TARGET, BUDGET, DR MIN (varsayılan 25), SON 6 AY LİSTESİ, NOTE, KEYWORDS
- **Aksiyonlar:** ACQUIRE TARGETS / UPLOAD PAYLOAD / UNIFIED DOMAINS sayacı
- **Sol sidebar:** SYSTEM LOG (skill ne yaptığını gösterir)
- **4 sekme:**
  1. PAYLOAD DB: Excel havuzu, sheet kartları, arama+filtre
  2. SCAN KW: SEOmonitor keyword'leri (önceki ay), jenerik etiketli, checkbox seçim
  3. ACQUIRE: Bütçeye göre site eşleşmeleri; son 6 ay / DR<25 / zararlı nedeniyle elenenler ayrı listede, checkbox, kw atamalar
  4. PREVIEW: Müşteri Excel formatında önizleme (birleştirilmiş hücreler)

### Tema

- Ana çerçeve: `#EEEDFE` (lila mor)
- Form alanı: `#F5F4FE` (çok hafif lila)
- Tablolar: `#FFFFFF` (kontrast için beyaz)
- Tablo başlıkları: `#CECBF6` (orta mor)
- Ana aksiyon: `#534AB7` (mor)
- İkincil aksiyon: `#5DCAA5` (cyan/teal)
- Multi-link badge: `#F4C0D1` (pembe)
- Trend: ▲ `#3B6D11` yeşil, ▼ `#A32D2D` kırmızı

### Etkileşim Akışı

- Form alanları doldurulur → ACQUIRE TARGETS basılır → skill çalışır
- Skill her adımda SYSTEM LOG'a satır ekler
- Sekmeler ilgili sekmeye otomatik geçer (PREVIEW son aşama)
- PREVIEW'da EXCEL EXPORT butonu son adıma götürür

### Widget HTML Şablonu

```html
<style>
.term { font-family: 'JetBrains Mono', 'SF Mono', Menlo, monospace; background: #EEEDFE; border: 1px solid #AFA9EC; border-radius: 12px; overflow: hidden; }
.term-form { padding: 14px 16px; background: #F5F4FE; border-bottom: 1px solid #CECBF6; }
.term-input { font-family: inherit; font-size: 13px; padding: 6px 10px; border: 1px solid #CECBF6; background: #fff; color: #26215C; border-radius: 4px; }
.term-btn-primary { color: #534AB7; border: 1px solid #534AB7; background: #fff; padding: 8px 14px; border-radius: 4px; font-family: inherit; font-size: 12px; cursor: pointer; letter-spacing: 0.05em; font-weight: 500; }
.term-btn-cyan { color: #0F6E56; border: 1px solid #5DCAA5; background: #fff; padding: 8px 14px; border-radius: 4px; font-family: inherit; font-size: 12px; cursor: pointer; letter-spacing: 0.05em; font-weight: 500; }
.data-tbl { width: 100%; border-collapse: collapse; font-family: inherit; font-size: 11px; background: #fff; border-radius: 6px; overflow: hidden; }
.data-tbl th { background: #CECBF6; color: #26215C; padding: 8px 10px; text-align: left; font-weight: 500; letter-spacing: 0.05em; font-size: 10px; }
.data-tbl td { padding: 7px 10px; border-bottom: 1px solid #EEEDFE; color: #2C2C2A; }
.multi-tag { display: inline-block; padding: 1px 6px; border-radius: 8px; font-size: 9px; font-weight: 500; background: #F4C0D1; color: #72243E; margin-left: 4px; }
.dr-pill { display: inline-block; padding: 1px 6px; border-radius: 8px; font-size: 10px; font-weight: 500; }
</style>
<!-- Form + Tabs + Sidebar + Panes -->
<!-- Tam HTML yapısı için terminal widget'ın referans kodu kullanılır -->
```


### Widget Yeniden Render Kuralı (KRİTİK)

Sohbet uzadıkça widget yukarı kayar ve bulması zorlaşır. Bu yüzden:

**Otomatik yeniden render:**
- Her büyük adımdan sonra (her ana adım tamamlandığında) widget'ı **alta yeniden render et**, eski state'i koruyarak
- Site değiştirme, keyword düzenleme gibi her kullanıcı aksiyonundan sonra **güncellenmiş widget'ı tekrar göster**

**Manuel komut:**
Kullanıcı şunlardan birini yazarsa widget'ı en güncel state'iyle altta yeniden çiz:
- "widget tekrar"
- "widget aç"
- "panel aç"
- "widget göster"
- "ekran tekrar"

Yeniden render ederken:
- Form alanları doldurulu olmalı (TARGET, BUDGET, vb. son girilen değerler)
- Hangi sekme aktifse onunla aç (PAYLOAD DB / SCAN KW / ACQUIRE / PREVIEW)
- SCAN KW dolu ise dolu olarak göster
- ACQUIRE'da seçilmiş siteler işaretli olmalı
- SYSTEM LOG'a "widget reloaded" satırı ekle

Bu kural sayesinde kullanıcı her zaman widget'ı **alt mesajda** bulabilir, yukarı scroll etmesi gerekmez.

