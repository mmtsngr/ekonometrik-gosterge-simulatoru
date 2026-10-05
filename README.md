# Ekonometrik Gösterge Simülatörü

Kur geçişkenliği ve faiz–enflasyon dinamiklerini tarayıcıda, kurulum gerektirmeden incelemek için açık kaynaklı bir araç.

**Canlı sürüm:** `https://<kullanici-adi>.github.io/<depo-adi>/`

Uygulama iki sekmeden oluşur:

- **Teorik model.** Kalibre edilmiş küçük açık ekonomi modeli. Kur geçişkenliği, Taylor kuralı katsayıları ve atalet parametreleriyle oynayın; etki-tepki yolları anında güncellenir. Bir senaryoyu sabitleyip yenisiyle üst üste karşılaştırabilirsiniz.
- **Türkiye verisi (VAR).** TCMB EVDS verisiyle tahmin edilen üç değişkenli VAR (kur, enflasyon, politika faizi). Örneklem, gecikme ve Cholesky sıralaması değiştirilebilir; güven bantları bootstrap ile hesaplanır, kur şokunda birikimli geçişkenlik oranı da gösterilir.

Uygulama [Shinylive](https://shiny.posit.co/py/docs/shinylive.html) ile tamamen tarayıcıda (WebAssembly) çalışır. Sunucu gerekmez, GitHub Pages üzerinden ücretsiz yayınlanır.

## Kurulum (bir kez)

1. Bu depoyu kendi hesabınıza kopyalayın (fork ya da yeni depo).
2. **Settings → Pages → Source** bölümünde **GitHub Actions** seçin.
3. [evds3.tcmb.gov.tr](https://evds3.tcmb.gov.tr) üzerinden ücretsiz API anahtarı alın (profil sayfası → "Copy API Key").
4. **Settings → Secrets and variables → Actions** bölümüne `EVDS_API_KEY` adıyla ekleyin.
5. **Actions → Veriyi güncelle ve yayınla → Run workflow** ile ilk çalıştırmayı başlatın.

Bundan sonra iş akışı her ayın 6'sında veriyi kendiliğinden günceller ve siteyi yeniden yayınlar.

## Yerelde çalıştırma

```bash
pip install -r requirements.txt
export EVDS_API_KEY=...            # Windows: set EVDS_API_KEY=...
python scripts/veri_cek.py         # app/data/turkiye_aylik.csv oluşturur
shiny run app/app.py               # http://127.0.0.1:8000
```

Statik sürümü yerelde denemek için:

```bash
pip install shinylive
shinylive export app site
python -m http.server --directory site 8008
```

## Yapı

```
app/
  app.py          Arayüz ve sunucu mantığı
  model.py        Kalibre model, VAR tahmini, Cholesky, bootstrap (yalnızca numpy)
  yontem.md       Uygulamadaki "Yöntem ve uyarılar" sekmesi
  data/           EVDS'den üretilen aylık veri
scripts/
  veri_cek.py     EVDS3 veri çekme ve TÜFE baz zincirleme
tests/            Model ve VAR testleri
.github/workflows/guncelle-ve-yayinla.yml
```

## Veri

| Değişken | EVDS kodu | Dönüşüm |
|---|---|---|
| USD/TRY | `TP.DK.USD.A.YTL` | aylık ortalama, 100·Δlog |
| TÜFE (2003=100) | `TP.FG.J0` | aylık, 100·Δlog |
| TÜFE (2025=100) | `TP.TUKFIY2025.GENEL` | eski serinin bittiği yerden zincirlenir |
| Politika faizi | `TP.APIFON4` | TCMB ağırlıklı ortalama fonlama maliyeti, aylık ortalama |

Seri kodları `scripts/veri_cek.py` içindeki `SERILER` sözlüğünden değiştirilebilir.

## Yöntemsel uyarılar

Ayrıntılar uygulamanın "Yöntem ve uyarılar" sekmesinde. Kısaca: doğrusal VAR, Türkiye'de asimetrik ve rejime bağlı olan kur geçişkenliğinin ortalamasını verir; 2018, 2021–2023 ve 2023 sonrası rejimler tek örneklemde birleştiğinde katsayılar hiçbir rejimi tam yansıtmayabilir; Cholesky sıralaması veriden çıkmayan bir varsayımdır. Araç öğretim ve keşif amaçlıdır.

## Lisans

MIT. Ayrıntılar `LICENSE` dosyasında.
