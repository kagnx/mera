# MERA-BİS PRO v1.2.4 — Sürüm Notları (GitHub Release gövdesi)

> Bu dosya `gh release create --notes-file` ile doğrudan kullanılır.
> Hedef etiket: `v1.2.4` · Tarih: 18.09.2026 · Önceki yayın: v1.2.1

---

## 🌱 MERA-BİS PRO v1.2.4

Türkiye Mera ve Otlatma Alanları Bilgi Sistemi — dağıtılabilir sürüm.

### ⭐ Bu sürümde öne çıkanlar

- **Kurumsal dağıtım desteği**: Microsoft Intune (Win32), GPO başlangıç betiği
  ve MSI/MST senaryoları için tam kılavuz; genişletilmiş sessiz kurulum
  parametreleri (`/ALLUSERS`, `/CURRENTUSER`, `/LOG`, `/TASKS`, `/LOADINF`…)
- **Kurulum sihirbazı iyileştirmeleri**: kurulum günlüğü (`SetupLogging`),
  sessiz yükseltmede açık uygulamayı otomatik kapatma, `--skip-version`
  uyumlu çıktı doğrulama düzeltmesi
- **Authenticode kod imzalama** derleme zincirinde: PFX veya sertifika
  deposu, SHA256 + RFC3161 zaman damgası, CI kilidi (`--require-sign`)
- **Vejetasyon ölçüm/gözlem modülü** (v1.2.0): mera başına zaman serisi
  ölçüm kayıtları, trend grafiği, CSV dışa aktarma
- **Offline güncelleme sistemi** (v1.1.0): manifest + SHA-256 bütünlük
  kapısı, otomatik yedek + geri alma (rollback), ağ paylaşımı kaynağı

### 📥 Kurulum

| Yol | Kimin için |
|-----|-----------|
| `MERA_BIS_PRO_Setup_v1.2.4.exe` | Son kullanıcılar — çift tıkla kurulum, kısayollar + kaldırıcı |
| `MERA_BIS_PRO_v1.2.4.exe` | Taşınabilir kullanım — kurulum gerekmez, tek dosya |
| `MERA_BIS_PRO_1.2.4.zip` | Uygulama içi güncelleme paketi (ağ paylaşımına konur) |

Kurumsal dağıtım (Intune/GPO): [ENTERPRISE_DEPLOYMENT.md](ENTERPRISE_DEPLOYMENT.md)
Sessiz kurulum: `MERA_BIS_PRO_Setup_v1.2.4.exe /VERYSILENT /NORESTART /SUPPRESSMSGBOXES`

### 🔐 Sağlama toplamları (SHA-256)

```
8de4b93a05fd8384aea3f224947b3065e9e7e45fc5e3c985caad947725db9747  MERA_BIS_PRO_v1.2.4.exe
f4b4d399d6cab79e2b18a77c692f3f133acbd63fc630f4846d650723cc1b2413  MERA_BIS_PRO_1.2.4.zip
07387433095e5d5fa04bbd06e6960159394bb2cab88f938948f8c646af5a00a6  MERA_BIS_PRO_Setup_v1.2.4.exe
```

### 📋 Değişiklik günlüğü (v1.2.1 → v1.2.4)

**Added / Eklendi**
- Kurumsal dağıtım kılavuzu: Intune Win32 paketleme, GPO bilgisayar
  başlangıç betiği, MSI/MST yol haritası, algılama kuralı (PowerShell),
  çıkış kodları tablosu, dağıtım yöneticisi kontrol listesi
- Sessiz kurulum yönergeleri: `SetupLogging`, `CloseApplications`,
  `RestartApplications=no`, `AllowNoIcons`,
  `PrivilegesRequiredOverridesAllowed=commandline`
- Authenticode imzalama modülü (`tools/codesign.py`) + derleme zinciri
  entegrasyonu — exe artefaktları Authenticode + DigiCert RFC3161 zaman
  damgasıyla imzalanır; zip bütünlüğü manifest SHA-256 ile korunur
- Kurulum sihirbazına kurumsal kılavuzun kopyalanması

**Fixed / Düzeltildi**
- `build_installer.py` çıktı doğrulaması: `{#MyAppVersion}` yer tutucusu
  gerçek sürümle çözümlenmiyordu — her başarılı derleme "doğrulanamadı"
  sanılıyordu (v1.2.3'te düzeltildi)
- ISS sürüm damgası artık derleme öncesi `build_data/version.json` ile
  otomatik eşitleniyor (tek doğruluk kaynağı)

### 🧪 Kalite

- 12 test paketi + GUI smoke: **553+ kontrol, 0 başarısız**
- Uçtan uca güncelleme senaryosu (eski→yeni + rollback): 30/30
- Veri güvenliği: yükseltme/kaldırma `%APPDATA%\MeraBisPro` verilerini korur

### 📦 Sistem gereksinimleri

Windows 10/11 (64 bit) · İnternet bağlantısı yalnızca harita karoları için
· Yönetici hakları gerekmez (varsayılan kurulum kullanıcı bazlıdır)

---

**Tam changelog**: v1.2.1…v1.2.4 arasındaki tüm commit'ler için
`CHANGELOG.md` dosyasına bakın.
