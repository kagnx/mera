# Changelog

Bu projedeki tüm önemli değişiklikler bu dosyada belgelenir.
Biçim [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) temelli olup
sürümler [Semantik Sürümlendirme](https://semver.org/lang/tr/) izler.

## [1.2.4] — 2026-09-18

### Düzeltildi
- `tools/build_installer.py` çıktı doğrulaması: ISS'teki `{#MyAppVersion}`
  yer tutucusu gerçek sürümle çözümlenmiyordu; başarılı derlemeler
  "çıktı doğrulanamadı" hatası veriyordu. Yer tutucu artık derleyici
  parametresinden, o yoksa ISS `#define` satırından çözümlenir
  (`--skip-version` akışıyla uyumlu).

### Eklendi
- GitHub Releases yayın altyapısı: `RELEASE_NOTES_v1.2.4.md` gövdesi,
  varlık listesi ve SHA-256 sağlama toplamları.
- Çıktı yolu çözümlemesi için 3 yeni statik test (`test_installer_script`).

## [1.2.3] — 2026-09-18

### Eklendi
- **Kurumsal dağıtım kılavuzu** (`ENTERPRISE_DEPLOYMENT.md`): Intune Win32
  paketleme (`install.ps1` + `IntuneWinAppUtil`), GPO bilgisayar başlangıç
  betiği, MSI/MST yol haritası, PowerShell algılama kuralı (sabit AppId ile
  süperrassal yükseltme), çıkış kodları tablosu, dağıtım yöneticisi kontrol
  listesi, kurumsal sorun giderme.
- Genişletilmiş sessiz kurulum parametreleri ve belgeleri: `/ALLUSERS`,
  `/CURRENTUSER`, `/LOG=`, `/TASKS`, `/NOICONS`, `/LOADINF`, `/SAVEINF`,
  `/RESTARTEXITCODE` (3010).
- Kurulum betiğine kurumsal yönergeler: `SetupLogging=yes`,
  `CloseApplications=yes`, `RestartApplications=no`, `AllowNoIcons=yes`,
  `PrivilegesRequiredOverridesAllowed=commandline`.
- Setup artık `ENTERPRISE_DEPLOYMENT.md`'yi de uygulama dizinine kopyalar.

## [1.2.2] — 2026-09-17

### Eklendi
- **Authenticode kod imzalama** (`tools/codesign.py`): signtool bulucu
  (PATH + Windows SDK + Chocolatey/Scoop), PFX veya sertifika deposu
  (`/sha1`) kipleri, SHA256 özet + RFC3161 zaman damgası, imza doğrulama.
- Derleme zinciri imzalama entegrasyonu: `build_release.py` exe → zip paketi
  → setup.exe sırasıyla imzalar; `--no-sign` / `--require-sign` bayrakları
  (CI'da imzasız derlemeyi engelleyen kilit).
- Parola güvenliği: PFX parolası yalnızca ortam değişkeninden
  (`MERA_SIGN_PFX_PASSWORD`) okunur; dosyaya/loga yazılmaz.
- `build_data/signing.example.json` şablonu ve `tests/test_codesign.py`
  (25 kontrol: komut üretimi, yapılandırma önceliği, parola gizliliği).

## [1.2.1] — 2026-09-17

### Eklendi
- İlk paketli derleme (PyInstaller onefile, v1.2.0 kod tabanı).
- Uçtan uca güncelleme senaryo testi (`tests/test_update_e2e.py`, 30 kontrol):
  eski kurulum ↔ yeni updates paketi, bozuk paket reddi, yükleme, rollback,
  yedek saklama politikası; `build_release.py` test zincirine eklendi.

### Düzeltildi
- Güncelleme yedeği adı çakışması: saniye çözünürlüklü damga, aynı saniyede
  yapılan güncellemelerin yedeklerini eziyordu — damga mikrosaniyeli hale
  getirildi (`app_backup_..._%f`).

## [1.2.0] — 2026-09-17

### Eklendi
- **Vejetasyon Ölçüm ve Gözlem Kayıtları modülü**: yeni
  `vegetation_measurements` tablosu (tarih, kuru ot verimi, örtü yüzdesi,
  ortalama boy, dominant bitkiler, gözlemci, yöntem, notlar),
  `(pasture_id, m_date)` indeksi ve mera silinince cascade davranışı
  (`PRAGMA foreign_keys = ON`).
- DB metotları: `add/get/update/delete_measurement`, `latest_measurement`,
  `measurements_export_rows`.
- Yeni GUI görünümü (`gui/measurements_view.py`): kayıt formu, düzenleme
  modu, renk tonlu liste, matplotlib çift eksenli trend grafiği,
  CSV dışa aktarma.
- 32 yeni i18n anahtarı (tr/en); Yedekleme→sayfa 6, Denetim→sayfa 7.

## [1.1.0] — 2026-09-17

### Eklendi
- **Offline güncelleme sistemi**: manifest tabanlı sürüm denetimi
  (`core/update_checker.py`), SHA-256 + boyut bütünlük kapısı, zip
  yol-geçişi koruması, uygulama + veritabanı yedeği, otomatik geri alma
  (rollback), son 3 yedeği saklama, güvenli yeniden başlatma.
- Güncelleme kaynağı: yerel klasör veya `\\sunucu\paylasim` (UNC);
  QSettings ile kalıcı; açılışta sessiz denetim + durum çubuğu bildirimi.
- Dağıtım araçları: `tools/build_release.py` (test → PyInstaller →
  updates paketi tek komut), `tools/make_update_package.py`, `DEPLOYMENT.md`.
- Menü çubuğu (Dosya/Araçlar/Yardım) + kısayollar (F1, Ctrl+U, Ctrl+Q),
  durum çubuğu (kayıt sayısı + kural sürümü + güncelleme bildirimi).
- Loglama (`logs/merabis.log`), global exception hook, tek örnek kilidi
  (paketli modda).

### Düzeltildi
- Tabloda sayısal sıralama (`NumericItem`) — "1.000" < "900" hatası;
  JSON dışa aktarmanın iki kez bağlanması; CSV/JSON dışa aktarmanın
  filtreyi yok sayması; bozuk yedek dosyasından geri yüklerken çökme
  (`sqlite3.DatabaseError`); okunmaz durum renkleri.

## [1.0.0] — 2026-09-16

### Eklendi
- İlk sürüm: PyQt6 + SQLite tabanlı mera bilgi sistemi — harita görünümü
  (Leaflet), analiz & istatistik, mera veri listesi, otlatma hesaplayıcısı,
  rotasyon planlayıcı, yedekleme, veri denetimi, 81 il örnek verisi,
  Türkçe/İngilizce arayüz.

[1.2.4]: https://github.com/turkiye-mera-otomasyonu/mera-bis-pro/releases/tag/v1.2.4
[1.2.3]: https://github.com/turkiye-mera-otomasyonu/mera-bis-pro/releases/tag/v1.2.3
[1.2.2]: https://github.com/turkiye-mera-otomasyonu/mera-bis-pro/releases/tag/v1.2.2
[1.2.1]: https://github.com/turkiye-mera-otomasyonu/mera-bis-pro/releases/tag/v1.2.1
[1.2.0]: https://github.com/turkiye-mera-otomasyonu/mera-bis-pro/releases/tag/v1.2.0
[1.1.0]: https://github.com/turkiye-mera-otomasyonu/mera-bis-pro/releases/tag/v1.1.0
[1.0.0]: https://github.com/turkiye-mera-otomasyonu/mera-bis-pro/releases/tag/v1.0.0
