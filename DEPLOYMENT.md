# MERA-BİS PRO — Dağıtım ve Güncelleme Kılavuzu

Bu belge, uygulamayı son kullanıcıya dağıtılabilir seviyeye getirmek için
gereken derleme, paketleme ve güncelleme adımlarını açıklar.

## 1. Sürümlendirme

Sürümün tek kaynağı `build_data/version.json` dosyasıdır. Her PyInstaller
derlemesinde patch sürümü otomatik artar (`MERA_BIS_PRO.spec` içinde).
Manuel artırma:

```bash
python versioning.py bump          # 1.1.0 -> 1.1.1
python versioning.py bump minor    # 1.1.0 -> 1.2.0
python versioning.py bump major    # 1.1.0 -> 2.0.0
```

Sürüm ve derleme tarihi, Hakkında diyaloğunda görüntülenir ve Windows dosya
özelliklerine (FileVersion/ProductVersion) yazılır.

## 2. Derleme ve paketleme (tek komut)

```bash
python tools/build_release.py                # testler + derleme + updates paketi
python tools/build_release.py --part minor   # minor sürüm artırarak
python tools/build_release.py --skip-tests   # testleri atlayarak (hızlı deneme)
python tools/build_release.py --skip-package # yalnızca derleme
```

Çıktılar:

| Çıktı | Yol |
|-------|-----|
| Tek dosya exe | `dist/MERA_BIS_PRO.exe` |
| Sürüm damgalı dağıtım kopyası | `dist/release/MERA_BIS_PRO_v<sürüm>.exe` |
| Offline güncelleme paketi | `updates/MERA_BIS_PRO_<sürüm>.zip` |
| Güncelleme manifesti | `updates/manifest.json` |

Derleme öncesi test paketi otomatik koşar; herhangi bir test başarısızsa
derleme durur.

## 3. Windows kurulum sihirbazı (setup.exe)

Inno Setup ile tek dosyalık `setup.exe` üretilir: kısayollar, kaldırıcı ve
veri koruma garantisini içerir.

### Kurulum gereksinimi (derleme makinesi)

- [Inno Setup 6](https://jrsoftware.org/isdl.php) veya `choco install innosetup`

### Derleme

```bash
python tools/build_installer.py          # dist exe'sinden setup.exe üretir
python tools/build_release.py --installer  # tam zincir: test+derle+updates+setup
```

Çıktı: `installer/Output/MERA_BIS_PRO_Setup_v<sürüm>.exe`

### Sihirbazın özellikleri

| Özellik | Davranış |
|---------|----------|
| Yönetici hakları | Gerekmez (`PrivilegesRequired=lowest`, HKCU kurulumu) |
| Kurulum yeri | `{autopf}\MERA-BIS PRO` (kullanıcı bazlı Program Files) |
| Masaüstü kısayolu | İsteğe bağlı onay kutusu |
| Başlangıçta açılma | İsteğe bağlı onay kutusu |
| Başlat menüsü | Program grubu + kaldırıcı kısayolu |
| Diller | Türkçe (varsayılan) ve İngilizce |
| Kaldırıcı | Denetim Masası'ndan tam kaldırma; çalışıyorsa uygulamayı kapatır |
| Veri güvenliği | Kaldırma `%APPDATA%\MeraBisPro` altındaki veritabanı/yedek/logları **silmeyez** |
| Sessiz kurulum | `setup.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES` — tüm parametreler: [ENTERPRISE_DEPLOYMENT.md](ENTERPRISE_DEPLOYMENT.md) |
| Kurumsal dağıtım | Intune Win32 / GPO / MSI-MST senaryoları: [ENTERPRISE_DEPLOYMENT.md](ENTERPRISE_DEPLOYMENT.md) |
| Sürüm damgası | `build_installer.py` her derlemede ISS sürümünü `build_data/version.json`'dan eşitler |

### Windows dosya özellikleri

Setup ve uygulama exe'leri sürüm bilgisi taşır (sağ tık → Özellikler →
Ayrıntılar): ProductName, FileVersion, ProductVersion, CompanyName.

## 4. Uygulamayı son kullanıcıya dağıtma

1. `dist/release/MERA_BIS_PRO_v<sürüm>.exe` dosyasını tek başına dağıtın —
   kurulum gerekmez, dosya her klasörde çalışır.
2. Uygulama veritabanını kalıcı olarak `%APPDATA%\MeraBisPro\mera_otomasyonu.db`
   altında tutar; yedekler `%APPDATA%\MeraBisPro\backups\` klasörüne yazılır.
3. Kullanıcı verileri exe'nin yanında tutulmaz; exe'nin üzerine yazılan
   güncellemeler veri kaybı oluşturmaz.
4. Uygulama paketli modda tek örnek kilidi ile çalışır: aynı makinede
   ikinci bir kopya açılamaz.
5. Loglar `%APPDATA%\MeraBisPro\logs\merabis.log` dosyasına yazılır; destek
   taleplerinde bu dosya istenmelidir.

## 5. Kod imzalama (Authenticode)

İmzalı derlemeler SmartScreen uyarısı vermez ve kurumsal dağıtımda güven polisi
için gereklidir. Derleme zinciri, imza yapılandırması varsa **exe + güncelleme
zip'i + setup.exe** dosyalarını otomatik imzalar.

### Hazırlık (tek seferlik)

1. Windows SDK kurun (signtool dahil gelir) — `choco install windows-sdk` veya
   [SDK indirmesi](https://developer.microsoft.com/windows/downloads/windows-sdk/).
2. Kod imza sertifikanızı (OV/EV) alın; PFX dosyasını güvenli bir yere koyun
   (örn. `C:\sertifikalar\merabis.pfx`).
3. Parolayı **ortam değişkeni** olarak ayarlayın (asla dosyaya yazmayın):

```powershell
setx MERA_SIGN_PFX "C:\sertifikalar\merabis.pfx"
setx MERA_SIGN_PFX_PASSWORD "<PFX parolanız>"
# Alternatif: sertifika deposundaki imzayı parmak iziyle kullanın
# setx MERA_SIGN_SHA1 "<sertifika SHA1 parmak izi, boşluksuz>"
```

### Kullanım

```bash
python tools/build_release.py                  # yapılandırma varsa otomatik imzalar
python tools/build_release.py --require-sign   # CI: imzasız derlemeyi ENGELLER
python tools/build_release.py --no-sign        # imzalamayı atla
python tools/build_installer.py --sign         # yalnızca setup.exe'yi imzala

# Elle imzalama / doğrulama
python tools/codesign.py sign dist/MERA_BIS_PRO.exe
python tools/codesign.py verify dist/MERA_BIS_PRO.exe
python tools/codesign.py status installer/Output/MERA_BIS_PRO_Setup_v1.2.2.exe
```

### Davranış kuralları

| Kural | Detay |
|-------|-------|
| Parola güvenliği | PFX parolası yalnızca `MERA_SIGN_PFX_PASSWORD` ortam değişkeninden okunur; hiçbir dosyaya/komut satırına/loglara yazılmaz |
| Zaman damgası | RFC3161 (`timestamp.digicert.com`); imza sertifika süresi dolsa da geçerli kalır |
| İmza sırası | exe → zip paketi (manifest SHA imzalı zip'e göre) → setup.exe |
| Yapılandırma | `build_data/signing.json` (örnek: `signing.example.json`); ortam değişkenleri dosyayı ezer |
| CI kilidi | `--require-sign` ile imzasız derleme hata verir |
| Eksik yapılandırma | Yerel derlemede uyarı verip imzasız devam eder |
| EV sertifikaları | Donanım token (USB/HSM) zorunluysa `MERA_SIGN_SHA1` kipi kullanılır; parola env'i gerekmez (PIN'i token sürücüsü sorar). Tam kılavuz: [EV_TOKEN_GUIDE.md](EV_TOKEN_GUIDE.md) |

### Doğrulama

Derleme sonrası: dosyaya sağ tık → Özellikler → Dijital İmzalar sekmesinde
"Bu dijital imza geçerli" yazmalı. Komutla: `python tools/codesign.py verify <dosya>`.

### EV sertifikası / donanım token

EV sertifikaların özel anahtarı USB token veya HSM'de kilitlidir ve
çıkarılamaz; imza, Windows sertifika deposundaki sertifikanın SHA1 parmak
iziyle (`/sha1` kipi) yapılır. Depoya aktarım, parmak izi çıkarma, PIN
yönetimi, bulut HSM köprüsü (Azure Trusted Signing / DigiCert KeyLocker) ve
sorun giderme için: [EV_TOKEN_GUIDE.md](EV_TOKEN_GUIDE.md).

## 6. GitHub Actions CI (test + derleme + imzalama + yayın)

`.github/workflows/release.yml` — üç job'luk zincir:

```
test (win, Py 3.12+3.13 matrix)  →  build (win)  →  release (ubuntu)
  14 test paketi + smoke_gui         PyInstaller         SHA256SUMS
  QT_QPA_PLATFORM=offscreen          + Inno Setup        + gh release create
                                     + imzalama
```

### Tetikleme

| Yol | Davranış |
|-----|----------|
| `v*` etiketi push | test → build → release otomatik |
| Actions → Run workflow | opsiyonlu: `skip_tests`, `skip_release`, `require_sign` |
| PR/push (etiketsiz) | yalnızca test job'u koşmaz — iş akışı etiket/dispatch'e bağlıdır |

### İmzalama secret'ları (Repository Settings → Secrets and variables → Actions)

| Secret | Anlamı |
|--------|--------|
| `SIGN_CERT_SHA1` | Sertifika deposundaki kod imza sertifikasının SHA1 parmak izi (donanım token/EV/bulut KSP) |
| `SIGN_TIMESTAMP_URL` | (opsiyonel) RFC3161 sunucusu; varsayılan `timestamp.digicert.com` |

Secret tanımlıysa derleme otomatik imzalar ve **CI içi doğrulama** yapar:
`Get-AuthenticodeSignature` NotSigned dönerse iş akışı hata verir.
Tanımlı değilse imzasız derleme uyarıyla geçer (`require_sign` girişiyle
engellenebilir). PFX parolası CI'da kullanılmaz; donanım/bulut anahtar
kipi önerilir (bkz. EV_TOKEN_GUIDE.md §7).

### Derleme notları

- **Otomatik changelog**: her derlemede son `v*` etiketinden bu yana
  commit'ler kategorize edilip `CHANGELOG.md`'ye yeni sürüm bölümü olarak
  eklenir (`tools/gen_changelog.py`, conventional commit önekleri:
  `feat:` → Eklendi, `fix:` → Düzeltildi…). `--no-changelog` ile atlanır;
  git deposu/etiket yoksa uyarıyla geçer. CI'da tam geçmiş için
  `actions/checkout` `fetch-depth: 0` kullanın.
- `requirements.txt` tüm iş akışlarında pip cache ile kullanılır.
- Inno Setup `choco install innosetup` ile kurulur; `build_installer.py`
  bulur ve sürüm damgası atar.
- Spec her derlemede patch sürümünü artırır; etiket v1.2.6 ise üretilen
  sürüm bunun bir altı olabilir — release adımı etiketi yalnızca varlık
  adlandırmasında kullanır, sürüm doğrulaması build adımındadır.
- Artefaktlar her çalıştırmada `mera-bis-pro-build` adıyla 14 gün saklanır;
  release job'u yalnızca etiketli çalıştırmada varlık yükler.

### İlk kurulum kontrol listesi

- [ ] `requirements.txt` sürümleri derleme makinesiyle aynı mı?
- [ ] Secret'lar tanımlı mı? (imzasız yayın istenmiyorsa)
- [ ] İlk etiket: `git tag v1.2.6 && git push origin v1.2.6`
- [ ] Actions sekmesinde üç job'un da yeşil olduğunu doğrula
- [ ] Release varlıklarında SHA256SUMS.txt `sha256sum -c` geçiyor mu?
- [ ] Yeni paket ağ paylaşımına §7.3 sırasıyla dağıtıldı mı? (zip önce, manifest sonra)
- [ ] Paylaşım doğrulaması §7.4 betiği "PAYLAŞIM TUTARLI" dedi mi?
- [ ] GitHub Release taslağı `tools/publish_draft_release.ps1` ile hazırlandı mı? (varlık + SHA paritesi otomatik denetlenir; klon gerekmez)

## 7. Offline güncelleme dağıtımı (ağ paylaşımı yayını)

### 7.1 Yayın akışı (genel bakış)

```
[1] Derleme          [2] Yayın            [3] Ağ dağıtımı        [4] Kullanıcı
build_release.py  →  gh release create →  robocopy updates   →  Ctrl+U veya
--installer          (GitHub Releases)     \\sunucu\MeraBisUpdates   açılışta otomatik
     │                    │                      │                 denetim
     └─ updates/          └─ kalıcı arşiv        └─ manifest.json      │
        + manifest            + SHA256SUMS           + zip          sürüm denetimi
```

| Adım | Sorumlu | Araç | Doğrulama |
|------|---------|------|-----------|
| 1. Derleme | Geliştirici/CI | `build_release.py --installer` veya `v*` etiketi (§6) | exe/setup/zip/manifest aynı sürümde (§2) |
| 2. Yayın | Geliştirici | `gh release create` + `SHA256SUMS.txt` | Release varlık listesi |
| 3. Ağ dağıtımı | Yayın yöneticisi | `robocopy` → UNC paylaşım (§7.3) | §7.4 paylaşımda SHA eşleşmesi |
| 4. Pilot | 1-2 kullanıcı | Ctrl+U | Yükleme + başarılı açılış |
| 5. Tam yayın | Tüm kullanıcılar | Açılışta otomatik denetim (~2,5 sn) | Durum çubuğu bildirimi |

### 7.2 Ağ paylaşımı hazırlığı (tek seferlik)

```
\\sunucu\MeraBisUpdates\          (veya DFS: \\kurum\merabis\updates)
    manifest.json              ← sürüm doğruluk kaynağı
    MERA_BIS_PRO_1.2.8.zip     ← güncel paket
    archive\                   ← eski sürüm zipleri (rollback için)
```

İzinler (SMB paylaşım + NTFS):

| Hesap | Paylaşım izni | NTFS izni |
|-------|---------------|-----------|
| `KURUM\MeraBisYayincilar` (yayın yöneticileri) | Değiştir | Yaz |
| `KURUM\Domain Users` (tüm kullanıcılar) | Oku | Oku ve çalıştır |

- Kullanıcılar **yalnızca okur**; manifest/zip'i yalnızca yayın yöneticisi
  yazar (bütünlüğü bozma riskini kapatır).
- Uygulama paylaşıma yazmaz; yedekler kullanıcının kendi
  `%APPDATA%\MeraBisPro\updates\backups\` altına yazılır.

### 7.3 Yönetici dağıtım adımları (her yeni sürümde)

```bash
python tools/make_update_package.py --notes "Sürüm açıklaması..."
```

Paylaşıma dağıtım — **zip ÖNCE, manifest SONRA** kuralına dikkat:

```bat
rem 1) Yeni paketi kopyala
robocopy updates \\sunucu\MeraBisUpdates MERA_BIS_PRO_1.2.8.zip /NP

rem 2) Eski zip'i arşive taşı (rollback amaçlı saklanır)
move \\sunucu\MeraBisUpdates\MERA_BIS_PRO_1.2.7.zip \\sunucu\MeraBisUpdates\archive\

rem 3) Manifesti EN SON kopyala — sürümü anında duyurur
robocopy updates \\sunucu\MeraBisUpdates manifest.json /NP
```

> **Neden manifest en son?** Kullanıcılar açılışta otomatik denetim
> yaptığından manifest kopyalanır kopyalanmaz güncellemeyi görmeye başlar;
> manifest ilk konursa yarım kopyalanmış zip'e işaret edebilir. Buna rağmen
> bütünlük kapısı (SHA-256) bozuk paketi reddeder — kullanıcı hata görür ama
> verisi asla bozulmaz; sıralama yine de doğru yapılmalıdır.

### 7.4 Paylaşım üzerinde doğrulama

```powershell
$unc = "\\sunucu\MeraBisUpdates"
$manifest = Get-Content "$unc\manifest.json" | ConvertFrom-Json
"manifest sürümü : " + $manifest.version
"manifest zip    : " + $manifest.file
$gercek = (Get-FileHash "$unc\$($manifest.file)" -Algorithm SHA256).Hash.ToLower()
"kayıtlı sha256  : " + $manifest.sha256
"gerçek sha256   : " + $gercek
if ($gercek -eq $manifest.sha256) { "SONUÇ: PAYLAŞIM TUTARLI" } else { "SONUÇ: EŞLEŞMEZ — DAĞITMAYIN"; exit 1 }
```

Ayrıca paylaşım yolunun standart kullanıcı hesabıyla (yöneticiyle değil)
okunabildiğini bir istemcide test edin.

### 7.4b GitHub Releases taslak yayını (publish_draft_release.ps1)

Staging klasörü (`dist/release/gh_release_v<sürüm>/`) derlemeden sonra
elle kurulur: 3 varlık (exe, zip, setup) + `SHA256SUMS_v<sürüm>.txt` +
`RELEASE_NOTES_v<sürüm>.md`. Sonra:

```powershell
# Plan modu (yüklemez): varlık seti + SHA-256 paritesi + gh CLI denetimi
powershell -File tools/publish_draft_release.ps1 -Repo OWNER/REPO

# Taslak yayını (gh auth login gerektirir, kapsam: repo)
powershell -File tools/publish_draft_release.ps1 -Repo OWNER/REPO -Publish
```

- Sürüm verilmezse `build_data/version.json`'dan okunur; staging yolu,
  varlık adları ve `v<sürüm>` etiketi otomatik türetilir.
- `-Repo` verilmezse betik **asılı kalmaz**: kullanım örneğiyle hemen
  çıkar (exit 7). Kalıcı atama: `setx MERA_RELEASE_REPO "OWNER/REPO"`
  (ortam değişkeni otomatik okunur; CI'da secret/vars ile uygundur).
- Çıkış kodları: 0 ok · 2 gh CLI yok · 3 kimlik yok · 4 staging/varlık
  eksik · 5 SHA paritesi bozuk (YAYINMAYIN) · 6 version.json okunamadı ·
  7 Repo eksik/bozuk biçim.

### 7.5 Kullanıcı tarafı

Uygulama içinde **Araçlar → Güncellemeleri Denetle... (Ctrl+U)**:

1. Kaynak olarak `\\sunucu\MeraBisUpdates` yolunu girin (bir kez girilir,
   QSettings ile kalıcı saklanır).
2. "Denetle" — uygulama manifestteki sürümü kendi sürümüyle karşılaştırır.
3. "Güncellemeyi Yükle" — paket SHA-256 ile doğrulanır, mevcut uygulama
   yedeklenir (`updates/backups/app_backup_*`), yeni dosyalar yazılır.
4. Uygulama kapanır, restarter yeni sürümü başlatır. İlk açılışta güncelleme
   bilgisi gösterilir.

Ayrıca paketli modda açılıştan ~2,5 sn sonra sessiz denetim yapılır; yeni
sürüm varsa durum çubuğunda turuncu bildirim görünür.

### 7.6 Güvenlik ve geri alma

- Paket, manifestteki SHA-256 özeti eşleşmezse yüklenmez.
- Yükleme öncesi veritabanı yedeği alınır (`db_before_update_*.db`).
- Sorun olursa "↩️ Geri Al" butonu son yedeği geri koyar.
- Son 3 uygulama yedeği saklanır; eskileri otomatik silinir.
- Zip içi yol geçişi (path traversal) girişimleri reddedilir.
- Paylaşımda yazma izni yalnızca yayın yöneticilerindedir (§7.2); kullanıcı
  kaynak dosyalarını değiştiremez.
- Rollback zinciri: uygulama yedeği (otomatik) → paylaşım arşivindeki eski
  zip (§7.3 adım 2) → GitHub Releases'taki eski setup (kalıcı arşiv).

### 7.7 Sık hatalar

| Belirti | Neden / Çözüm |
|---------|---------------|
| "Güncelleme kaynağı bulunamadı" | UNC yolu yanlış, paylaşım erişilemez veya manifest yok — §7.4 doğrulamasını paylaşım üzerinde koşun |
| Kullanıcı hâlâ eski sürümü görüyor | manifest.json kopyalanmamış (adım 3 atlanmış) veya sürüm artırılmamış; `versioning.py show` ile karşılaştırın |
| "Paket bütünlüğü doğrulanamadı" | Zip tam kopyalanmadan manifest yayınlanmış — zip'i yeniden kopyalayıp §7.4 ile doğrulayın |
| Yönetici paylaşuma yazamıyor | `MeraBisYayincilar` grubuna üyelik / NTFS Yaz izni eksik |
| Zip paylaşımda var ama "dosya bozuk" | SMB önbelleği eski içerik verebilir; istemcide `dir \\sunucu\MeraBisUpdates` ile boyutu karşılaştırın |

## 8. Kalite kontrol (QA) listesi

Dağıtım öncesi:

```bash
python tests/test_update_checker.py   # güncelleme servisi birim testleri
python tests/test_update_e2e.py       # iki taraflı uçtan uca güncelleme senaryosu
python tests/test_installer_script.py # kurulum betiği doğrulaması
python tests/test_codesign.py         # kod imzalama modülü
python tests/test_backup.py           # yedekleme/geri yükleme
python tests/test_db_manager.py       # veri katmanı
python tests/test_validation.py       # doğrulama kuralları
QT_QPA_PLATFORM=offscreen python tests/smoke_gui.py   # GUI uçtan uca
```

Elle doğrulama:

- [ ] Hakkında diyaloğunda sürüm ve derleme tarihi doğru mu?
- [ ] Windows dosya özellikleri (sağ tık → Özellikler → Ayrıntılar) doğru mu?
- [ ] Yeni kayıt ekleme, düzenleme, silme çalışıyor mu?
- [ ] Yedek al → kayıt sil → geri yükle döngüsü veri kaybı yaratıyor mu?
- [ ] CSV/JSON dışa aktarma filtrelenmiş veriyi mi veriyor?
- [ ] Güncelleme diyaloğu kaynak modda uyarı gösteriyor mu?
- [ ] İngilizceye geçişte menüler ve güncelleme diyaloğu çevriliyor mu?
- [ ] Eski sürümden yeni sürüme geçişte kullanıcı verisi korunuyor mu? (tests/test_update_e2e.py)
- [ ] İmzalı derlemede Dijital İmzalar sekmesi "geçerli" diyor mu?
- [ ] Setup.exe sessiz kurulumda (/VERYSILENT) uyarı vermeden kuruluyor mu?
- [ ] Ağ paylaşımı dağıtımı uçtan uca: §7.3 adımları → pilot kullanıcı Ctrl+U ile güncelleyebiliyor mu? (§7.1 akışı)
- [ ] Paylaşımdaki manifest/zip SHA-256 eşleşiyor mu? (§7.4)
- [ ] Kaldırdıktan sonra %APPDATA%\MeraBisPro verileri duruyor mu?
- [ ] Kurulumdan sonra masaüstü/başlat kısayolları çalışıyor mu?

## 9. Doğrulanmış kalite kanıtları (sürüm v1.2.28)

v1.2.28 dağıtım zinciri uçtan uca sınanmıştır; bu bölüm hem kanıt
kaydıdır hem de her yeni sürümde tekrarlanacak yöntemlerin referansıdır.

### 9.1 Sessiz kurulum + kaldırma (gerçek setup.exe)

Belgelenmiş kurumsal komut izole dizinde çalıştırıldı:

```bat
MERA_BIS_PRO_Setup_v1.2.28.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES ^
  /DIR="D:\kurulum_testi" /LOG="D:\kurulum_testi\setup.log"
```

- Çıkış kodu 0, log "Installation process succeeded. Need to restart
  Windows? No"; yönetici parolası gerekmedi (`PrivilegesRequired=lowest`,
  HKCU kaydı `DisplayVersion 1.2.28`).
- Kurulu exe PE 1.2.28 + Authenticode **Valid**; desktop/startup ikon
  görevleri sessiz modda varsayılan devre dışı.
- Kurulu uygulama canlı açıldı (pencere başlığı doğru, ~400-500 MB
  onfile RAM normali), `WM_CLOSE` ile ~9 sn'de zarif kapandı.
- `unins000.exe /VERYSILENT …` → çıkış 0; kurulum dizini, registry
  kaydı, Başlat menüsü grubu tamamen kalktı — artık sıfır.

> **Gotcha**: Git Bash `/VERYSILENT` gibi bayrakları
> `C:/Program Files/Git/VERYSILENT` yoluna çevirir ve sessiz mod sessizce
> düşer — kurulum sihirbazı etkileşim modda açılıp askıda kalır.
> Test için `cmd //c "… /VERYSILENT …"` sarmalayıcısını kullanın.
> PowerShell/cmd'den çalıştırmada sorun yoktur (kurumsal kılavuz
> etkilenmez).

**Otomatik sürüm (v1.2.33+)**: `build_data/e2e_setup_driver.py` sürücüsü bu
senaryoyu uçtan uca kendisi koşar — kurulum → PE/metadata/registry doğrulama →
canlı açılış ("Harita yüklendi ve hazır" log beklemesi) → zarif kapanış →
sessiz kaldırma + artık denetimi. `python build_data/e2e_setup_driver.py`
(veya test paketinde: `python tests/test_setup_artifacts_e2e.py`; setup.exe
yoksa SKIP olur). Sürücü ikinci bir gotcha yakaladı: `subprocess`+`cmd /c`
içinde tırnaklı `/DIR= /LOG=` bloğu Inno tarafından düzgün ayrıştırılamıyor —
sürücü bu yüzden PowerShell `Start-Process -ArgumentList` (dizi) kullanır;
ayrıca Windows PowerShell 5.1'de `Start-Process -LiteralPath` yoktur
(`-FilePath`).

### 9.2 Uçtan uca güncelleme + rollback (gerçek artefaktlar)

İki bağımsız kanıt:

1. **Otomatik**: `python tests/test_update_artifacts_e2e.py` —
   arşivdeki eski sürüm zip'inden çıkarılan gerçek imzalı PE + güncel
   updates paketiyle 16 kontrol: algılama (`update_available` /
   `up_to_date` ikilemi) → manifest↔zip SHA/boyut paritesi → SHA kapısı
   (bozuk özet `ValueError`) → `apply_update` (aşamalar, restart
   işareti, yedekte eski exe birebir) → `rollback_last_update` (eski
   exe birebir geri, işaret temiz). Artefakt yoksa SKIP — derlemeyi
   engellemez; her derlemede koşar.
2. **Elle**: `build_data/e2e_update_driver.py` (setup | check | apply |
   rollback) — PE sürüm damgasıyla kanıt: 1.2.24 → apply → **1.2.28**
   → rollback → **1.2.24**.

### 9.3 GitHub Release staging koruması (clean_dist)

`clean_dist` aracı `dist/release/gh_release_*` klasörlerini **asla
arşivlemez/silmez**; dry-run çıktısında `staging (korunur): …` diye
raporlar. Koruma testleri `tests/test_clean_dist.py`'de (41 kontrol):
scan/plan/apply üç aşamada da staging'e dokunulmazlığı denetler — test
başındaki gerçek staging listesiyle karşılaştırma yapar. (Bu koruma,
v1.2.21 staging'inin harici temizlikte kaybolması sonrası eklendi.)

### 9.4 Canlı açılış + UIA doğrulaması

Dağıtım exe'si canlı başlatıldı; UIA otomasyon ağacı üzerinden doğrulandı:
menü çubuğu (3), gezinme düğmeleri (ad + geometri ile okunur — yüksek DPI
okunabilirlik düzeltmesi), gösterge paneli canlı verileri, Denetim
sayfasında "Poligon-Kayıtlı Alan Uyumu" özeti (`81 yer tutucu atlandı ·
0 uyumsuzluk`) ve APPDATA veritabanında `measurement_audit_log` şeması.
`WM_CLOSE` → log "Uygulama kapandı (kod 0)".

> Not: UIA girdi enjeksiyonu (menü/klavye gönderimi) kısıtlı olabilir;
> etkileşimli akışların kanıtı `smoke_gui` (132 kontrol) ve
> `smoke_map_check` (42 kontrol) otomatik paketlerindedir.

## 10. Derleme çıktı arşivleme ve temizlik

Her derleme `dist/`, `updates/` ve `installer/Output/` içine ~200 MB çıktı
bırakır; eski sürümler birikir. Strateji:

- **Güncel sürüm** (`build_data/version.json`) aktif dizinlerde kalır.
- **Eski sürümler** `archive/v<sürüm>/` altına SHA256SUMS.txt ile taşınır
  (rollback/destek için birebir kopya; `sha256sum -c` ile doğrulanabilir).
- **`build/`** yalnızca PyInstaller ara dosyalarıdır — her derlemede
  yeniden üretilir, silinmesinde sakınca yoktur.
- `dist/MERA_BIS_PRO.exe` (damgasız ana exe) arşivlenmez; her derlemede
  üzerine yazılır.

```bash
python tools/clean_dist.py                     # planı göster (dry-run)
python tools/clean_dist.py --apply             # eski sürümleri arşivle
python tools/clean_dist.py --apply --clean-build   # build/ ara dosyalarını da sil
python tools/clean_dist.py --keep 1.2.1        # belirli sürümü arşivleme
python tools/clean_dist.py --apply --purge-archive 1.2.1   # arşivden tamamen sil
```

`tools/build_release.py --archive-old` derleme sonrası aynı işlemleri
otomatik yapar (`--clean-build` ile birlikte).

> **Staging koruması**: `dist/release/gh_release_*` klasörleri (GitHub
> Release yayın varlıkları) temizlik aracı tarafından asla
> arşivlenmez/silinmez — dry-run çıktısında `staging (korunur)` olarak
> raporlanır. Detay: §9.3.

> Not: `archive/` klasörünü yedeklemenize gerek yoktur — her sürüm
> GitHub Releases'ta da bulunur; arşiv yalnızca çevrimdışı destek/rollback
> hızlandırıcıdır.

## 11. Sorun giderme

| Belirti | Olası neden / çözüm |
|---------|---------------------|
| "Uygulama zaten çalışıyor" uyarısı | Tek örnek kilidi aktif; açık pencereyi kullanın veya Görev Yöneticisi'nden kapatın |
| "Paket bütünlüğü doğrulanamadı" | Zip dosyası bozuk/eksik kopyalanmış; paketi yeniden kopyalayın |
| "Güncelleme kaynağı bulunamadı" | Kaynak yolu yanlış veya manifest.json eksik |
| Harita boş geliyor | İnternet gerekir (Leaflet kütüphanesi yereldir; karo servisi çevrimiçidir) |
| Veritabanı kilit hatası | Aynı anda iki örnek açık olmayacak; kilit dosyası `%APPDATA%\MeraBisPro\merabis.lock` |
| ISCC bulunamadı | Inno Setup 6'yı kurun veya PATH'e ekleyin; ayrıntılar: `tools/build_installer.py` |
| Setup eski sürümü gösteriyor | `build_installer.py` sürümü build_data/version.json'dan damgalar; önce sürümü artırın |
| "İmzalama başarısız" | Parola env'i (`MERA_SIGN_PFX_PASSWORD`) doğru mu? PFX süresi dolmuş mu? `signtool verify /v /pa <dosya>` çıktısına bakın |
| SmartScreen uyarısı devam ediyor | İmza EV değilse itibar birikmesi zaman alır; zaman damgalı olduğundan emin olun |
| Intune/GPO kurulumu başarısız | Kurulum günlüğüne (`/LOG=`) bakın; çıkış kodları ve çözümler: ENTERPRISE_DEPLOYMENT.md §3 ve §9 |
