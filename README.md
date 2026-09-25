# 🌱 MERA-BİS PRO

**Türkiye Mera ve Otlatma Alanları Bilgi Sistemi**
*Turkey Pasture and Grazing Areas Information System (MERA-BIS PRO)*

[![Sürüm](https://img.shields.io/badge/s%C3%BCr%C3%BCm-1.2.29-green)](CHANGELOG.md)
[![Lisans](https://img.shields.io/badge/lisans-MIT-blue)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-lightgrey)](#kurulum)
[![Python](https://img.shields.io/badge/Python-3.12%2B-yellow)](#kaynaktan-derleme)

---

**MERA-BİS PRO**, Türkiye'deki mera ve otlatma alanlarının kaydını tutan, analiz
eden ve otlatma planlamasını destekleyen masaüstü uygulamasıdır. 81 ilin mera
verilerini harita üzerinde görselleştirir; vejetasyon ölçümlerini, otlatma
hesaplarını ve rotasyon planlarını tek sistemde toplar.

- **Programlayan:** kagnx — Kaldırım Mühendisi
- **Lisans:** MIT ([LICENSE](LICENSE))
- **Güncel sürüm:** v1.2.29 (kaynak) · v1.2.28 (dağıtım)
- **Platform:** Windows 10/11 (x64)

---

## ✨ Özellikler

| Modül | Açıklama |
|-------|----------|
| 🗺️ **Harita Görünümü** | Leaflet tabanlı interaktif Türkiye haritası; mera poligonları, il sınırları, karanlık mod, popup'ta alan/son ölçüm/sparkline |
| 📊 **Analiz & İstatistik** | İl ve mera bazlı istatistikler, grafiksel analizler |
| 📋 **Mera Veri Listesi** | 81 il için mera kayıtlarının tablo halinde yönetimi |
| 🧮 **Otlatma Hesaplayıcısı** | BBHB (Büyükbaş Hayvan Birimi), ot ihtiyacı ve otlatma kapasitesi hesapları |
| 🔄 **Rotasyon Planı** | Pad bazlı otlatma rotasyonu planlama |
| 🌿 **Vejetasyon Ölçümleri** | Zaman serisi ölçüm kayıtları (kuru ot verimi, örtü yüzdesi, ortalama boy); trend grafikleri ve ölçüm diyaloğu |
| 🧾 **Denetim İzi (Audit Log)** | Haritadan yapılan ölçüm ekleme/düzenleme kayıtları; kaynak/tarih filtresi ve CSV dışa aktarma |
| 📐 **Veri Denetimi** | Poligon alanı ile kayıtlı alan arasındaki >%25 sapmaları raporlayan tutarlılık denetimi |
| 💾 **Yedekleme** | Veritabanı yedekleme ve geri yükleme |
| 🌐 **Çok Dilli** | Türkçe / İngilizce (çalışma anında değiştirilebilir) |
| 🌙 **Karanlık Mod** | Harita karolarına CSS filtresi + popup teması; menüden seçilebilir |
| 🔁 **Güncelleme Sistemi** | Uygulama içi güncelleme: SHA-256 doğrulamalı paket, otomatik yedek, geri alma (rollback) |
| 🧙 **Veri Taşıma Sihirbazı** | Eski MERA-BİS PRO kurulumundan verilerin otomatik devralınması |
| 🏢 **Kurumsal Dağıtım** | Sessiz kurulum, GPO/Intune/MSI senaryoları ([ENTERPRISE_DEPLOYMENT.md](ENTERPRISE_DEPLOYMENT.md)) |

---

## 📦 Kurulum

### Son Kullanıcı (önerilen)

1. [Releases](../../releases) sayfasından **`MERA_BIS_PRO_Setup_v1.2.28.exe`** indirin.
2. İndirilen dosyanın SHA-256 özetini `SHA256SUMS_v1.2.28.txt` ile karşılaştırın:

   ```powershell
   Get-FileHash MERA_BIS_PRO_Setup_v1.2.28.exe -Algorithm SHA256
   ```

3. Kurulum sihirbazını çalıştırın — yönetici yetkisi gerekmez (HKCU'ya kurulur).
   Kısayollar: Başlat menüsü → MERA-BİS PRO. Masaüstü/başlangıç kısayolları
   isteğe bağlıdır (varsayılan kapalı).
4. İlk açılışta eski bir MERA-BİS PRO kurulumu varsa **veri taşıma sihirbazı**
   otomatik önerir; mera ve ölçüm kayıtlarınız devralınır.

### Taşınabilir Kullanım (kurulumsuz)

`MERA_BIS_PRO_v1.2.28.exe` tek dosyalık taşınabilir sürümdür — USB bellekten bile
çalışır, kayıt defterine yazmaz.

### Sessiz / Kurumsal Kurulum

```powershell
MERA_BIS_PRO_Setup_v1.2.28.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES
# Hedef dizin belirtmek için:
MERA_BIS_PRO_Setup_v1.2.28.exe /VERYSILENT /DIR="D:\MeraBisPro"
```

GPO, Intune (Win32) ve MSI/MST senaryoları için
[ENTERPRISE_DEPLOYMENT.md](ENTERPRISE_DEPLOYMENT.md) ve
[DEPLOYMENT.md](DEPLOYMENT.md) kılavuzlarına bakın.

> **Not:** Uygulama şu anda test sertifikasıyla imzalıdır; üretim dağıtımında
> kanıtlanmış CA sertifikası kullanılır. İmzasız/test imzalı pakette uygulama
> açılışta sizi bilgilendirir.

---

## 🚀 Kaynaktan Çalıştırma

### Gereksinimler

- Windows 10/11
- Python 3.12+ (geliştirmede 3.14 kullanılıyor)
- pip

### Adımlar

```bash
git clone <repo-url> mera-bis-pro
cd mera-bis-pro

python -m venv .venv
.venv\Scripts\activate          # Windows

pip install -r requirements.txt

python main.py
```

### Testler

```bash
python tests/smoke_gui.py                 # GUI duman testi (132 kontrol)
python tests/test_update_e2e.py           # Güncelleme akışı (sentetik paket)
python tests/test_update_artifacts_e2e.py # Gerçek artefakt E2E (varsa koşar, yoksa SKIP)
python tests/test_clean_dist.py           # dist temizlik aracı
python tools/build_release.py             # Tüm paket + derleme zinciri
```

---

## 🏗️ Derleme ve Dağıtım

Tek komutla tam zincir: **testler → PyInstaller derlemesi (otomatik patch bump)
→ Authenticode imzalama → updates paketi + manifest → Inno Setup kurulum
sihirbazı → arşivleme**.

```bash
python tools/build_release.py
```

Üretilen varlıklar:

| Varlık | Yol |
|--------|-----|
| Taşınabilir exe | `dist/release/MERA_BIS_PRO_v<sürüm>.exe` |
| Güncelleme paketi | `updates/MERA_BIS_PRO_<sürüm>.zip` + `updates/manifest.json` |
| Kurulum sihirbazı | `installer/Output/MERA_BIS_PRO_Setup_v<sürüm>.exe` |
| GitHub Release staging | `dist/release/gh_release_v<sürüm>/` (SHA256SUMS + sürüm notlarıyla) |

Detaylı kılavuzlar:

- [DEPLOYMENT.md](DEPLOYMENT.md) — derleme, imzalama, yayın akışı, kalite kanıtları
- [ENTERPRISE_DEPLOYMENT.md](ENTERPRISE_DEPLOYMENT.md) — GPO/Intune/MSI kurumsal senaryolar
- [EV_TOKEN_GUIDE.md](EV_TOKEN_GUIDE.md) — EV sertifikası & donanım token (USB/HSM) imzalama
- [CHANGELOG.md](CHANGELOG.md) — sürüm geçmişi

### Sürümlendirme

Sürümün tek kaynağı `build_data/version.json`'dur; her PyInstaller derlemesinde
patch sürümü otomatik artar. Manuel artırma:

```bash
python versioning.py bump          # 1.2.29 -> 1.2.30
python versioning.py bump minor    # 1.2.29 -> 1.3.0
python versioning.py bump major    # 1.2.29 -> 2.0.0
python versioning.py show
```

---

## 📁 Proje Yapısı

```
├── main.py                  # Giriş noktası (logging, tek örnek kilidi, DPI)
├── gui/                     # PyQt6 arayüz katmanı
│   ├── main_window.py       # Ana pencere, kenar çubuğu gezinmesi
│   ├── map_view.py          # Leaflet/QtWebEngine harita görünümü
│   ├── measurements_view.py # Vejetasyon ölçüm kayıtları
│   ├── audit_view.py        # Denetim izi + veri tutarlılık raporu
│   ├── migration_wizard.py  # Veritabanı taşıma sihirbazı (QWizard)
│   └── ...
├── core/                    # İş mantığı (güncelleme, imza denetimi, ...)
├── database/                # Veri katmanı + taşıma servisi
├── i18n.py                  # Türkçe/İngilizce çeviri sözlüğü
├── styles/                  # QSS temaları
├── tests/                   # Test paketi (GUI duman, E2E, birim)
├── tools/                   # Derleme/dağıtım araçları (build_release, codesign, ...)
├── installer/               # Inno Setup betiği ve çıktıları
└── build_data/              # version.json, sertifika yapılandırması
```

---

## 📜 Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır — ayrıntılar için
[LICENSE](LICENSE) dosyasına bakın.

```
Copyright (c) 2026 kagnx
```

MIT Lisansı kısa özetle: yazılımı kullanma, kopyalama, değiştirme, dağıtma ve
satma hakkını herkese ücretsiz verir; tek koşul telif ve izin bildiriminin
kopyalarda korunmasıdır. Yazılım "olduğu gibi" sağlanır, garanti verilmez.

---

## 📞 Destek

Hata bildirimi ve öneriler için depo **Issues** sekmesini kullanın. Uygulama
içindeki loglar `%APPDATA%\MeraBisPro\logs\merabis.log` altında birikir; hata
bildirimlerinde bu dosyayı eklemeniz teşhisi hızlandırır.
