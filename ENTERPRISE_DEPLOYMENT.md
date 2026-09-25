# MERA-BİS PRO — Kurumsal Dağıtım Kılavuzu (GPO / Intune / MSI)

Bu belge, MERA-BİS PRO'nun kurumsal ortamlarda (Microsoft Intune, Group Policy,
SCCM/MECM) uçtan uca dağıtımını anlatır. Genel derleme ve kullanıcı dağıtımı
için bkz. [DEPLOYMENT.md](DEPLOYMENT.md).

---

## 1. Dağıtım modeli genel bakış

MERA-BİS PRO setup.exe'si **Inno Setup 6** tabanlıdır. İki kurulum bağlamını
destekler:

| Bağlam | Komut anahtarı | Kurulum yeri | Kayıt defteri | Yönetici gerekir |
|--------|----------------|--------------|---------------|------------------|
| Kullanıcı başına (varsayılan) | `/CURRENTUSER` | `%LocalAppData%\Programs\MERA-BIS PRO` | HKCU | Hayır |
| Makine başına | `/ALLUSERS` | `%ProgramFiles%\MERA-BIS PRO` | HKLM | Evet |

Veri dizini her iki bağlamda kullanıcıya göredir: `%APPDATA%\MeraBisPro`
(veritabanı, yedekler, loglar). Kaldırıcı bu dizini **asla silmez**.

**Öneri:** Kullanıcı bazlı yönetim için **Intune Win32** (Bölüm 4), makine
bazlı toplu kurulum için **GPO + /ALLUSERS** (Bölüm 5) kullanın.

---

## 2. Sessiz kurulum parametreleri (tam liste)

### 2.1 Temel sessiz kurulum

```bat
MERA_BIS_PRO_Setup_v1.2.3.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES
```

### 2.2 Parametre tablosu

| Parametre | Etki | Kurumsal öneri |
|-----------|------|----------------|
| `/VERYSILENT` | Hiçbir sihirbaz penceresi gösterilmez | ✅ Her zaman kullanın |
| `/SILENT` | Sadece ilerleme penceresi gösterilir | Kullanıcı bilgilendirmesi istenirse |
| `/NORESTART` | Kurulum sonrası yeniden başlatma yapmaz | ✅ Her zaman kullanın |
| `/SUPPRESSMSGBOXES` | Sessiz kurulumda soru mesajlarını otomatik yanıtlar | ✅ Her zaman kullanın |
| `/CURRENTUSER` | Kullanıcı bazlı kurulumu zorlar (HKCU) | Intune kullanıcı bağlamı |
| `/ALLUSERS` | Makine bazlı kurulumu zorlar (HKLM, yönetici ister) | GPO/SCCM sistem bağlamı |
| `/DIR="yol"` | Kurulum dizinini değiştirir | Standart disk görüntüsü kullanan ortamlar |
| `/GROUP="ad"` | Başlat menüsü grup adını değiştirir | Gerekirse |
| `/NOICONS` | Kısayol oluşturmaz | VDI/kiosk imajlarında |
| `/LANG=tr` veya `/LANG=en` | Sihirbaz dilini zorlar | `/VERYSILENT` ile etkisizdir |
| `/TASKS="desktopicon"` | Yalnızca seçilen görevleri yapar | Örn. sadece masaüstü kısayolu |
| `/TASKS=""` | Hiçbir ek görev yapmaz (kısayol yok) | VDI/kiosk |
| `/LOG="yol"` | Kurulum günlüğünü özel yola yazar | ✅ Intune/GPO tanılaması için kullanın |
| `/CLOSEAPPLICATIONS` | Çalışan uygulamayı kurulum öncesi kapatır | Varsayılan açık (`CloseApplications=yes`) |
| `/FORCECLOSEAPPLICATIONS` | Uygulamayı sormadan zorla kapatır | Bakım pencerelerinde |
| `/RESTARTEXITCODE` | Yeniden başlatma gerekiyorsa çıkış kodu **3010** döner | Intune beklenen dönüş kodlarına ekleyin |
| `/SAVEINF="yol"` | Seçimleri INF dosyasına kaydeder | Şablon oluşturma |
| `/LOADINF="yol"` | Seçimleri INF dosyasından okur | Şablonla toplu kurulum |

> `/TASKS` değerleri: `desktopicon` (masaüstü kısayolu), `startupicon`
> (Windows başlangıcında aç). Varsayılan kurulumda ikisi de işaretsizdir.

### 2.3 Hazır komut satırları

**Intune (kullanıcı bağlamı, kurulum günlüklü):**
```bat
MERA_BIS_PRO_Setup_v1.2.3.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES /LOG="%TEMP%\MeraBisPro_install.log"
```

**GPO bilgisayar başlangıç betiği (makine bağlamı):**
```bat
\\sunucu\paylasim\MERA_BIS_PRO_Setup_v1.2.3.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES /ALLUSERS /LOG="C:\Windows\Temp\MeraBisPro_install.log"
```

**VDI altın imaj (kısayolsuz):**
```bat
MERA_BIS_PRO_Setup_v1.2.3.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES /NOICONS /TASKS=""
```

**Sessiz kaldırma (kaldırıcı yolunu kayıt defterinden okuyun):**
```bat
"%LocalAppData%\Programs\MERA-BIS PRO\unins000.exe" /VERYSILENT /NORESTART /SUPPRESSMSGBOXES /LOG="%TEMP%\MeraBisPro_uninstall.log"
```

---

## 3. Çıkış kodları

| Kod | Anlam | Intune aksiyonu |
|-----|-------|-----------------|
| `0` | Kurulum tamamlandı | Başarı |
| `1` | Kurulum başlatılamadı (bozuk indirme, kilit) | Başarısız |
| `2` | Kullanıcı kurulumu iptal etti | Başarısız |
| `3` | Ölümcül hata | Başarısız |
| `4` | Kurulum sırasında hata (dosya kilitli, izin) | Başarısız — log dosyasını inceleyin |
| `3010` | Başarılı; yeniden başlatma gerekli (`/RESTARTEXITCODE` ile) | Başarı (beklenen kodlara ekleyin) |

---

## 4. Microsoft Intune (Win32 uygulaması) — önerilen yöntem

### 4.1 Paketi hazırlama

1. [Microsoft Win32 Content Prep Tool](https://github.com/Microsoft/Microsoft-Win32-Content-Prep-Tool)'u indirin.
2. Aşağıdaki yapıda bir klasör oluşturun:

```
IntunePackage\
├── MERA_BIS_PRO_Setup_v1.2.3.exe
└── install.ps1
```

3. `install.ps1` içerik:

```powershell
$setup = Join-Path $PSScriptRoot "MERA_BIS_PRO_Setup_v1.2.3.exe"
$log = Join-Path $env:TEMP "MeraBisPro_install.log"
$proc = Start-Process -FilePath $setup -ArgumentList @(
    "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES",
    "/LOG=`"$log`""
) -Wait -PassThru
exit $proc.ExitCode
```

4. Paketleyin:

```powershell
.\IntuneWinAppUtil.exe -c .\IntunePackage -s .\IntunePackage\install.ps1 -o .\Output
```

### 4.2 Intune'da uygulama oluşturma

| Alan | Değer |
|------|-------|
| **Yükleme komutu** | `install.ps1` (veya doğrudan `setup.exe /VERYSILENT ...`) |
| **Kaldırma komutu** | `"%PathToUninstaller%" /VERYSILENT /NORESTART` — kaldırıcı yolu sürümle değişmez, kayıt defterindeki `QuietUninstallString` değerini kullanın |
| **Yükleme davranışı** | Kullanıcı (per-user kurulum için) veya Sistem (`/ALLUSERS` ile) |
| **Cihaz yeniden başlatma** | Yükleme davranışına göre |

**Dönüş kodları:** `0` başarı; ek olarak `3010` beklenen kod olarak ekleyin
(`/RESTARTEXITCODE` kullanıyorsanız).

### 4.3 Algılama kuralı

**Yöntem A — Özel PowerShell (sürüm karşılaştırmalı, önerilen):**

```powershell
$appIds = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{6F2A9C41-8B7D-4E63-9A15-3C2B7A91D8E4}_is1",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{6F2A9C41-8B7D-4E63-9A15-3C2B7A91D8E4}_is1",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{6F2A9C41-8B7D-4E63-9A15-3C2B7A91D8E4}_is1"
)
foreach ($key in $appIds) {
    $props = Get-ItemProperty -Path $key -ErrorAction SilentlyContinue
    if ($props -and [version]($props.DisplayVersion) -ge [version]"1.2.3") {
        exit 0
    }
}
exit 1
```

> Sürümü dağıttığınız paket sürümüyle değiştirin. AppId
> `{6F2A9C41-8B7D-4E63-9A15-3C2B7A91D8E4}` sabittir — tüm sürümlerde aynıdır,
> yükseltmeler mevcut kurulumun **üzerine** yapılır ve kullanıcı verisi korunur.

**Yöntem B — Dosya algılama:**

| Alan | Değer |
|------|-------|
| Yol | `%LocalAppData%\Programs\MERA-BIS PRO` (kullanıcı) veya `C:\Program Files\MERA-BIS PRO` (sistem) |
| Dosya | `MERA_BIS_PRO.exe` |
| Algılama | Dosya veya klasör var + Tarih sürümü ≥ `1.2.3` |

### 4.4 Atamalar

- **Gerekli (Required)** → hedef kullanıcı/cihaz grubu (otomatik kurulum)
- **Uygulamalar için şirket portalı** → istekle kurulum
- Teslim süresi: kullanıcı bağlamında oturum açıldığında tetiklenir.

---

## 5. Group Policy (GPO) senaryosu

### 5.1 Makine bazlı kurulum (bilgisayar başlangıç betiği)

1. Setup.exe'yi paylaşıma koyun: `\\domain\netlogon\merabis\` (veya DFS).
2. `GPO → Bilgisayar Yapılandırması → Windows Ayarları → Betikler →
   Başlangıç` altına aşağıdaki betiği ekleyin:

```bat
@echo off
set SETUP=\\domain\netlogon\merabis\MERA_BIS_PRO_Setup_v1.2.3.exe
set KEY=HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{6F2A9C41-8B7D-4E63-9A15-3C2B7A91D8E4}_is1

rem Zaten bu sürüm veya üstü kuruluysa çık
for /f "tokens=2,*" %%A in ('reg query "%KEY%" /v DisplayVersion 2^>nul ^| findstr DisplayVersion') do set INSTALLED=%%B
if defined INSTALLED if "%INSTALLED%" geq "1.2.3" exit /b 0

"%SETUP%" /VERYSILENT /NORESTART /SUPPRESSMSGBOXES /ALLUSERS /LOG="C:\Windows\Temp\MeraBisPro_install.log"
exit /b %ERRORLEVEL%
```

3. Betiği **bilgisayar başlangıcında** çalışacak şekilde atayın (Sistem
   bağlamı, yönetici hakları otomatik vardır).
4. Yükseltme için sürüm damgasını güncelleyin — AppId sabit olduğu için
   kurulum üzerine yazar, veriler korunur.

> **Not:** Bilgisayar başlangıç betiği *kurulumu* makine bazlı yapar;
> uygulama ilk oturum açışında her kullanıcı için kendi
> `%APPDATA%\MeraBisPro` veri dizinini oluşturur.

### 5.2 Kullanıcı bazlı kurulum (oturum açma betiği)

Yönetici haklarının bulunmadığı ortamlarda `GPO → Kullanıcı Yapılandırması →
Windows Ayarları → Betikler → Oturum Aç` ile `/ALLUSERS` olmadan
(`/CURRENTUSER`) dağıtın. Kurulum `%LocalAppData%\Programs` altına yapılır ve
yönetici parolası istemez.

### 5.3 MSI / MST dönüşümü (GPO Yazılım Yükleme)

GPO'nun klasik **Yazılım Yükleme** düğümü yalnızca `.msi` kabul eder; Inno
Setup doğrudan MSI üretmez. MSI zorunluysa iki yol:

| Yol | Nasıl | Değerlendirme |
|-----|-------|---------------|
| **A. MSI sarmalayıcı** (ör. ücretsiz MSI Wrapper araçları) | setup.exe'yi sessiz kurulum çalıştıran bir MSI kabuğuna sarın; MST ile parametre verin | Hızlı; ancak kaldırma kaydı iki katmana düşer (MSI + Inno). Pilot ile test edin |
| **B. Intune'a geçiş** (önerilen) | MSI zorunluluğunu ortadan kaldırın; Intune Win32 zaten setup.exe destekler | Tek kaldırma kaydı, sürüm algılama, raporlama |

**MST örneği (yol A için):** Sarmalayıcı MSI'ın özel eylemi
`MERA_BIS_PRO_Setup.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES /ALLUSERS`
parametrelerini çağırmalı; dönüş kodu 0/3010 dışındaysa MSI başarısız dönmelidir.
GPO → Yazılım Yükleme → Gelişmiş dağıtım ile MST atayın.

---

## 6. Veri konumları ve kullanıcı profilleri

| Veri | Yol | Davranış |
|------|-----|----------|
| Veritabanı | `%APPDATA%\MeraBisPro\mera_otomasyonu.db` | Kaldırmada korunur; yükseltmede korunur |
| Yedekler | `%APPDATA%\MeraBisPro\backups\` | Kaldırmada korunur |
| Loglar | `%APPDATA%\MeraBisPro\logs\merabis.log` | Destek taleplerinde istenir |
| Kurulum günlüğü | `%TEMP%\MeraBisPro_install.log` (`/LOG=` ile) | Dağıtım teşhisi |
| Kilit | `%APPDATA%\MeraBisPro\merabis.lock` | Tek örnek kilidi |

- `%APPDATA%` dolaşım (roaming) profildir: 81 mera kayıtlı veritabanı
  birkaç MB'dir ve profil boyutu için sorun oluşturmaz.
- Yönetilen bilgisayarda kullanıcı ilk açılışta uygulama, eski kurulumlardan
  veri devralma sihirbazını önerir (bkz. DEPLOYMENT.md).
- Uygulama içi güncelleme kaynağı olarak ağ paylaşımı kullanılacaksa
  paylaşım izinleri, `robocopy` dağıtım sırası (zip önce, manifest sonra),
  paylaşım üzerinde SHA doğrulaması ve sık hatalar: **DEPLOYMENT.md §7**
  (ağ paylaşımı yayını).

---

## 7. Yükseltme stratejisi

1. AppId sabittir → her yeni sürüm aynı paketi üzerine kurar; kullanıcı verisi
   ve ayarlar (dil, güncelleme kaynağı) korunur.
2. `CloseApplications=yes` sayesinde açık uygulama sessiz yükseltmede
   otomatik kapatılır; çalışmayan veri kaybı oluşmaz.
3. Intune'da yeni sürümü **aynı uygulamanın** yeni paketi olarak güncelleyin
   (süperrassal davranış: algılama kuralı yeni sürümü görünce yükler).
4. GPO senaryosunda betikteki sürüm damgasını (`1.2.3`) güncelleyin.
5. Çekilme (rollback): önceki sürüm setup.exe'si aynı şekilde üzerine kurulur;
   veritabanı şeması geriye dönük uyumludur.

---

## 8. Dağıtım yöneticisi kontrol listesi

- [ ] Setup.exe Authenticode imzalı mı? (`signtool verify /v /pa setup.exe` — EV token kılavuzu: [EV_TOKEN_GUIDE.md](EV_TOKEN_GUIDE.md))
- [ ] Sessiz kurulum test makinesinde uyarısız tamamlandı mı? (çıkış kodu 0)
- [ ] `/LOG=` günlüğü yazıldı mı, hata var mı?
- [ ] Algılama kuralı doğru sürümü buluyor mu? (PowerShell betiği elle koşuldu)
- [ ] Sessiz **yükseltme** (eski sürüm → yeni sürüm) kullanıcı verisini korudu mu?
- [ ] Sessiz kaldırma sonrası `%APPDATA%\MeraBisPro` duruyor mu?
- [ ] Uygulama ilk açılışta kurulumdan bağımsız çalışıyor mu (log/yedek dizinleri oluştu mu)?
- [ ] VDI altın imajda `/NOICONS /TASKS=""` ile kısayolsuz kuruldu mu?

## 9. Kurumsal sorun giderme

| Belirti | Olası neden / çözüm |
|---------|---------------------|
| Intune "yükleme başarısız", kod 4 | Kurulum günlüğünü okuyun: genelde dosya kilidi (`CloseApplications` devre dışı bırakılmış) veya hedef dizin izni |
| Kod 1, "başlatılamadı" | Setup.exe bozuk indirilmiş; paket hash'ini ve imzayı doğrulayın |
| Algılama her zaman "kurulu değil" diyor | Per-user kurulum + sistem bağlamı karışmış: `/ALLUSERS` ile HKLM, `/CURRENTUSER` ile HKCU denetleyin |
| GPO betiği çalışmıyor | Bilgisayar başlangıç betiği mi atandı (kullanıcı değil)? Paylaşım erişimi "Bilgisayarlar" grubuna açık mı? |
| Kullanıcı bazlı kurulum ikinci kullanıcıda bulunamıyor | Per-user kurulum kullanıcıya özeldir; makine bazlı için `/ALLUSERS` kullanın |
| Yükseltmeden sonra eski sürüm algılanıyor | Algılama kuralındaki sürümü yeni pakete eşitleyin |
| Setup.exe SmartScreen engeli | İmza doğrulamasını kontrol edin (DEPLOYMENT.md §5); EV sertifika itibarı hızlı geçer |
