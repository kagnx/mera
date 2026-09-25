# GitHub Release v1.2.4 — Varlık Listesi

Yayın hedefi: `v1.2.4` etiketi · Tarih: 18.09.2026 · Önceki yayın: v1.2.1
Tüm varlıklar **aynı PyInstaller derlemesinden** üretilmiştir (sürüm tutarlılığı doğrulandı).

## Yüklenecek varlıklar (4 dosya, ~634 MB)

| # | Varlık | Boyut | Kaynak yolu | Amaç |
|---|--------|-------|-------------|------|
| 1 | `MERA_BIS_PRO_Setup_v1.2.4.exe` | 221.473.976 B (211,2 MB) | `installer/Output/` | Son kullanıcı kurulum sihirbazı (kısayollar + kaldırıcı) |
| 2 | `MERA_BIS_PRO_v1.2.4.exe` | 222.144.936 B (211,9 MB) | `dist/release/` | Taşınabilir tek dosya (kurulumsuz) |
| 3 | `MERA_BIS_PRO_1.2.4.zip` | 221.200.259 B (210,9 MB) | `updates/` | Uygulama içi offline güncelleme paketi (ağ paylaşımına konur) |
| 4 | `SHA256SUMS_v1.2.4.txt` | — | proje kökü | Sağlama toplamları (doğrulama) |

> İçerideki tek dosya: `MERA_BIS_PRO.exe` (updates zip'i, uygulama içi
> güncelleyicinin beklediği biçim). İçerideki exe **imzalıdır** — güncelleme
> akışında imza zip'ten bağımsız olarak korunur; zip'in bütünlüğü manifest
> SHA-256 ile denetlenir.

## Doğrulama durumu

| Denetim | Sonuç |
|---------|-------|
| Setup ProductVersion = 1.2.4 | ✅ (PowerShell `VersionInfo`) |
| Exe ProductVersion = 1.2.4 | ✅ (PyInstaller sürüm kaynağı) |
| Manifest sürümü = 1.2.4 | ✅ (`updates/manifest.json`) |
| Zip SHA-256 = manifest SHA-256 | ✅ `f4b4d399…cc1b2413` |
| Setup ≡ exe içeriği | ✅ (ISCC, `dist/MERA_BIS_PRO.exe` 1.2.4 ile derlendi) |
| SHA256SUMS dosyası doğrulaması | ✅ exe ve zip `sha256sum -c` → OK |
| Authenticode imzası (3 exe) | ✅ `Valid` — gömülü imza (`Signature Index: 0`), imzalayan `CN=MERA-BIS PRO Code Signing (TEST)` |
| RFC3161 zaman damgası | ✅ DigiCert SHA256 RSA4096 Timestamp Responder 2026 (sertifika süresi geçse bile imza geçerli kalır) |
| Sertifika güven zinciri | ⚠️ **Test sertifikası** — self-signed (yerel `Root` deposuna ekli); üretimde kanıtlanmış CA sertifikasına geçilmeli |

## SHA-256 özetleri

```
8de4b93a05fd8384aea3f224947b3065e9e7e45fc5e3c985caad947725db9747  MERA_BIS_PRO_v1.2.4.exe
f4b4d399d6cab79e2b18a77c692f3f133acbd63fc630f4846d650723cc1b2413  MERA_BIS_PRO_1.2.4.zip
07387433095e5d5fa04bbd06e6960159394bb2cab88f938948f8c646af5a00a6  MERA_BIS_PRO_Setup_v1.2.4.exe
```

## Yayın komutu

> **Önemli:** Derleme klasörü git deposu değildir. Önce projenin git klonunda
> (veya `git init` + `git remote add origin …` yapılmış bir dizinde)
> `gh auth login` durumunda olduğunuzdan emin olun; ardından 4 varlığı ve
> `RELEASE_NOTES_v1.2.4.md` dosyasını o dizine kopyalayın.

```bash
# 0) (tek seferlik) klon + varlık kopyalama
git clone https://github.com/<org>/mera-bis-pro.git && cd mera-bis-pro
copy "D:\turkiye_mera_otomasyonu\installer\Output\MERA_BIS_PRO_Setup_v1.2.4.exe" .
copy "D:\turkiye_mera_otomasyonu\dist\release\MERA_BIS_PRO_v1.2.4.exe" .
copy "D:\turkiye_mera_otomasyonu\updates\MERA_BIS_PRO_1.2.4.zip" .
copy "D:\turkiye_mera_otomasyonu\SHA256SUMS_v1.2.4.txt" .

# 1) etiket + yayın (etiket otomatik oluşturulur)
gh release create v1.2.4 \
  "MERA_BIS_PRO_Setup_v1.2.4.exe" \
  "MERA_BIS_PRO_v1.2.4.exe" \
  "MERA_BIS_PRO_1.2.4.zip" \
  "SHA256SUMS_v1.2.4.txt" \
  --title "MERA-BİS PRO v1.2.4" \
  --notes-file RELEASE_NOTES_v1.2.4.md
```

Ön izleme (yükleme olmadan): `gh release view v1.2.4`
Taslak olarak oluşturma: komuta `--draft` ekleyin.

### Hazır araç: `tools/publish_draft_release.ps1`

Staging klasörünü (`dist/release/gh_release_v1.2.4/`) doğrular — varlık
varlığı + SHA-256 paritesi — ve taslak release'i oluşturur; git klonu
gerektirmez (`-R` bayrağı ile çalışır):

```powershell
# Plan modu (yükleme yok, denetim + komut çıktısı):
powershell -NoProfile -ExecutionPolicy Bypass -File tools\publish_draft_release.ps1 -Repo "<org>/mera-bis-pro"

# Gerçek taslak yükleme:
powershell -NoProfile -ExecutionPolicy Bypass -File tools\publish_draft_release.ps1 -Repo "<org>/mera-bis-pro" -Publish
```

Çıkış kodları: 0 tamam · 2 gh yok (winget komutu basar) · 3 kimlik yok ·
4/5 varlık veya SHA hatası (yayın engellenir) · 6 gh komutu başarısız.
Web'de yayınlama: `gh release edit v1.2.4 -R <org>/mera-bis-pro --draft=false`.

## Güncelleme paketi için ek not

`updates/` klasörünü ağ paylaşımına dağıtan kurumlar, zip'i indirip
`updates/manifest.json` dosyasını zip ile **aynı klasörde** tutmalıdır —
uygulama içi güncelleyici sürümü ve SHA-256'yı manifestten denetler
(bütünlük kapısı: tests/test_update_e2e.py).
