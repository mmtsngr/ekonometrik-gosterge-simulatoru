### Bu araç ne yapar, ne yapmaz

İki farklı soruyu yan yana koyar. **Teorik model** sekmesi "parametreler şöyle olsaydı ekonomi şoka nasıl tepki verirdi?" sorusunu, **Türkiye verisi** sekmesi "veri, belirli tanımlama varsayımları altında ne söylüyor?" sorusunu yanıtlar. İkisi aynı şey değildir; aradaki fark aracın öğretmek istediği şeydir.

### Teorik model

Geriye dönük (Rudebusch-Svensson tipi) küçük açık ekonomi modeli:

- Çıktı açığı: yₜ = ρy·yₜ₋₁ − σ(iₜ₋₁ − πₜ₋₁) + δ·qₜ₋₁ + εʸ
- Enflasyon: πₜ = ρπ·πₜ₋₁ + κ·yₜ₋₁ + γ·Δeₜ + εᵖ
- Politika faizi: iₜ = ρi·iₜ₋₁ + (1 − ρi)(φπ·πₜ + φy·yₜ) + εⁱ
- Nominal kur: Δeₜ = −θ(iₜ − πₜ) + εᵉ
- Reel kur: qₜ = qₜ₋₁ + Δeₜ − πₜ

Değişkenler denge değerinden sapma olarak ölçülür; birimler göstermeliktir. Model ileriye dönük beklentiler içermez. Bu bilinçli bir tercihtir: her parametre birleşimi tek bir çözüm üretir ve kullanıcı belirsizlik (indeterminacy) bölgelerine düşmez. Bedeli şudur: beklenti kanalı ve politika güvenilirliği modelde yoktur. İleriye dönük Yeni Keynesyen modellerde geçerli olan Taylor ilkesi (φπ > 1) burada aynı biçimde işlemez; kararlılığı ekrandaki "en büyük kök" değerinden izleyin.

Varsayılan parametreler ders amaçlı yuvarlak değerlerdir; Türkiye için tahmin edilmiş değerler değildir.

### Türkiye verisi (VAR)

- **Veri:** TCMB EVDS. USD/TRY (aylık ortalama), TÜFE (2003=100 ve 2025=100 serilerinin aylık değişimleri zincirlenmiştir), TCMB ağırlıklı ortalama fonlama maliyeti.
- **Model:** Sabit terimli (isteğe bağlı mevsim kuklalı) indirgenmiş VAR(p), EKK tahmini.
- **Tanımlama:** Cholesky ayrıştırması. Sıralamada soldaki değişken, sağdakilere aynı ay içinde tepki vermez. Varsayılan sıralama (kur → enflasyon → faiz), Merkez Bankası'nın aynı ay içinde kur ve fiyatlara tepki verebildiğini varsayar.
- **Güven bantları:** Kalıntıların yeniden örneklendiği özyinelemeli bootstrap; patlayan çekilişler atılır.
- **Geçişkenlik oranı:** h dönem sonra, kur şokunun enflasyon üzerindeki birikimli etkisinin kur üzerindeki birikimli etkisine oranı.

### Bilinmesi gereken sınırlar

1. **Doğrusallık.** Türkiye'de kur geçişkenliği asimetrik ve dönemden döneme değişkendir (değer kaybının büyüklüğüne, enflasyon düzeyine ve politika rejimine bağlıdır). Doğrusal VAR bunun ortalamasını verir.
2. **Yapısal kırılmalar.** 2018 kur krizi, 2021–2023 düşük faiz dönemi ve 2023 sonrası sıkılaşma farklı rejimlerdir. Tek bir örneklemde birleştirildiklerinde katsayılar hiçbir rejimi tam yansıtmayabilir. Örneklem kaydırıcısıyla bunu doğrudan görebilirsiniz.
3. **Durağanlık.** Türkiye'de aylık enflasyon bazı dönemlerde durağan değildir; uzun örneklemlerde en büyük kök 1'e yaklaşabilir.
4. **Tanımlama.** Cholesky sıralaması bir varsayımdır, veriden çıkmaz. Farklı sıralamalar farklı hikâyeler anlatıyorsa, sonuç sıralamaya duyarlıdır ve öyle raporlanmalıdır.
5. **Fiyat bulmacası.** Faiz şokuna enflasyonun ilk aylarda artarak tepki vermesi, küçük VAR'larda sık görülen bir tanımlama sorunudur; bir bulgu olarak yorumlanmamalıdır.

Bu araç öğretim ve keşif içindir; politika değerlendirmesi ya da yayın düzeyinde tahmin için tasarlanmamıştır.
