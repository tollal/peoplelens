# peoplelens

![tests](https://github.com/tollal/peoplelens/actions/workflows/tests.yml/badge.svg)

**Dağınık İK dosyalarını güvenilir, testli metriklere çeviren açık kaynaklı bir İK analitiği kütüphanesi.**

Her şirket İK verisini farklı biçimde dışarı aktarır ve her dosya kirlidir. `peoplelens`, ortaya tek bir standart veri modeli koyar: bir şirketin dosyasını küçük bir YAML eşleme dosyasıyla tarif edersiniz; üstündeki kalite kontrolleri ve metrik tanımları ise hiç değişmeden çalışır.

> Bu depodaki tüm veriler **sentetiktir**. Depoya gerçek çalışan verisi yüklenmemiştir ve yüklenmemelidir.

## Nasıl çalışır

```
Ham dosya (CSV / Excel)
        |   YAML eşleme dosyası (şirket başına bir tane)
        v
  Standart çalışan tablosu    <- şema doğrulama
        |
        +--> Veri kalitesi motoru   (14 kontrol, hata / uyarı, kalite skoru)
        +--> Temel temizlik         (güvenli onarımlar, her adım raporlanır)
        +--> Metrik kütüphanesi     (headcount, FTE, işe giriş, ayrılma, turnover)
        +--> Elde tutma analizi     (Kaplan-Meier)
        +--> Türkiye modülü         (kıdem / ihbar tazminatı, bilanço yükümlülüğü)
        +--> Dashboard              (Streamlit)
```

## Görünüm

![Headcount](docs/headcount_trend.png)
![Turnover](docs/turnover_by_department.png)
![Veri kalitesi](docs/data_quality_report.png)

Son grafik, içine bilerek hata eklenmiş bir dosyadan geliyor. Testler, **eklenen her hatanın tam sayısıyla bulunduğunu** ve temiz bir şirkette sıfır yanlış alarm çıktığını doğrular. (Kontrol adları kodda İngilizce tutulmuştur.)

## Hızlı başlangıç

```bash
git clone https://github.com/tollal/peoplelens.git
cd peoplelens
uv sync
uv run pytest
uv run python examples/demo.py
```

```python
from peoplelens.mapping import load_company
from peoplelens.quality import run_checks, quality_score
from peoplelens.metrics import turnover_by

df, notlar = load_company("examples/sirket_a_ham.csv", "examples/sirket_a.yaml")
print(quality_score(df, "2026-09-30"))
print(run_checks(df, "2026-09-30"))
print(turnover_by(df, "2025-10-01", "2026-09-30"))
```

## Yeni bir şirketi eklemek

`examples/sirket_a.yaml` dosyasını kopyalayıp sütun adlarını değiştirmeniz yeterlidir. Örnek, Türkiye tarzı bir dışa aktarımı işler: noktalı virgülle ayrılmış alanlar, `gg.aa.yyyy` tarihler, `45.000,50` biçiminde maaşlar ve yerel çıkış nedenleri (`İstifa`, `İşten Çıkarma`) `voluntary` / `involuntary` olarak eşlenir. Dosyada olmayan isteğe bağlı sütunlar varsayılan değerle doldurulur ve yapılan her dönüşüm sessizce geçilmek yerine not olarak raporlanır.

Excel dosyaları için bir kez `uv add openpyxl` çalıştırmanız yeterlidir.

## Metrik tanımları

Tanımlar `src/peoplelens/metrics.py` içindeki açıklamalarda yazılıdır ve testlerle korunur.

- **Headcount:** Bir tarihte aktif çalışan sayısı. `termination_date` son çalışma günüdür ve o gün aktif sayılır.
- **Turnover oranı:** Dönemdeki ayrılanlar / ortalama headcount. Ortalama = (dönem başı + dönem sonu) / 2. İsteğe bağlı yıllıklandırma ve gönüllü / gönülsüz ayrımı vardır.

## Türkiye modülü

Kıdem tazminatı ve ihbar tazminatı hesapları, yasal tavan tablosuyla birlikte gelir. "Herkes bugün işten ayrılsa ne ödememiz gerekir?" sorusunu çalışan ve departman bazında yanıtlar.

```python
from peoplelens.turkey import severance_liability, liability_summary

liab = severance_liability(df, "2026-09-30")
print(liab["gross_liability"].sum())
print(liability_summary(liab))
```

Notlar:

- Tavan tablosu `turkey.py` içindedir ve her Ocak ile Temmuz ayında güncellenmelidir. Tablodaki dönemlerin dışındaki tarihlerde kod tahmin yürütmek yerine hata verir.
- Hesaplanan yükümlülük bir **üst sınırdır**; aktüeryal TMS 19 karşılığının yerine geçmez.
- Maaş, giydirilmiş brüt ücret kabul edilir.
- Bu modül hukuki danışmanlık değildir.

## Elde tutma analizi

Kaplan-Meier eğrileri, "işe girenlerin yüzde kaçı 6, 12 ve 24. ayda hâlâ şirkette?" sorusunu departman bazında yanıtlar. Yöntem, sentetik şirket üretecinin bilinen gerçek eğrisine karşı doğrulanmıştır.

```python
from peoplelens.attrition import retention_table

print(retention_table(df, "2026-09-30", cohort_start="2021-10-01"))
```

Hayatta kalma yanlılığını önlemek için yalnızca analiz penceresinin içinde işe girenler kullanılır.

## Dashboard

```bash
uv sync --extra dashboard
uv run streamlit run dashboard/app.py
```

Dört sekme vardır: genel bakış (KPI'lar, aylık headcount, departman bazlı turnover), veri kalitesi (skor, bulunan sorunlar, temizlik adımları, temiz CSV indirme), elde tutma (Kaplan-Meier tablo ve eğriler) ve Türkiye kıdem modülü. Dahili sentetik şirketi kullanabilir ya da kendi dosyanızı bir eşleme YAML'ıyla birlikte yükleyebilirsiniz. Uygulama yerelde çalışır, yüklenen dosyalar bilgisayarınızdan çıkmaz. Ayarlanabilir minimum büyüklüğün altındaki gruplar gizlenir.

## Gizlilik

İK verisi kişisel veridir. Gerçek veriyi depo dışında tutun (`data/` klasörü ve `*.xlsx` dosyaları git tarafından yok sayılır) ve yerel mevzuata uyun (Türkiye'de KVKK, AB'de GDPR).

## Yol haritası

- [x] Standart şema ve doğrulama
- [x] Sentetik şirket üreteci
- [x] Veri kalitesi motoru
- [x] Temel metrikler
- [x] Eşleme motoru (CSV / Excel -> standart tablo)
- [x] Temel temizlik
- [x] Elde tutma analizi (Kaplan-Meier)
- [x] Türkiye modülü: kıdem ve ihbar tazminatı, bilanço yükümlülüğü
- [x] Etkileşimli dashboard (Streamlit)
- [x] Minimum grup büyüklüğü kuralı (dashboard)
- [ ] Ücret eşitliği analizi (pay equity)
- [ ] Ayrılma tahmini (açıklanabilir model)
- [ ] Türkiye modülü: asgari ücret etkisi
- [ ] Anonimleştirme katmanı
- [ ] Vaka çalışmaları
- [ ] PyPI yayını

---
[Tolga](https://github.com/tollal) tarafından geliştirilmektedir.