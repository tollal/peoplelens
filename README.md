# PeopleLens

**PeopleLens**, dağınık İK verilerini temizleyen, standartlaştıran ve karar desteğine dönüştüren açık kaynak bir **People Analytics / HR Analytics** ürünüdür.

Ham CSV / Excel dosyalarını ortak bir çalışan veri modeline dönüştürür, veri kalitesini kontrol eder ve workforce, retention, compensation ve Türkiye kıdem analizlerini tek bir yapıda sunar.

> Bu repodaki tüm veriler sentetiktir. Gerçek çalışan verisi içermez.

---

## Ne yapar?

PeopleLens şu problemleri çözmek için geliştirildi:

- farklı formatlarda gelen İK dosyalarını standartlaştırma
- eksik, hatalı ve tutarsız verileri tespit etme
- headcount, FTE, işe giriş, çıkış ve turnover hesaplama
- çalışan elde tutma analizi
- maaş ve ücret dağılımı analizi
- gender pay gap analizi
- compa-ratio ve salary midpoint analizi
- salary outlier tespiti
- Türkiye kıdem tazminatı yükümlülüğü hesaplama

---

## Nasıl çalışır?

```text
Ham İK Verisi
      ↓
Mapping / Standardizasyon
      ↓
Şema Doğrulama
      ↓
Veri Kalitesi Kontrolleri
      ↓
Temizlik ve Dönüşüm
      ↓
People Analytics Metrikleri
      ↓
Dashboard ve Karar Desteği