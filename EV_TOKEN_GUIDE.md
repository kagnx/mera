# EV Sertifikası & Donanım Token (USB/HSM) Kılavuzu

MERA-BİS PRO derleme zinciri kod imzası için iki kip destekler. EV
sertifikaların özel anahtarı **çıkarılamaz** (CA/bulut HSM kısıtı) — bu kılavuz,
o anahtara erişimi `signtool`'a Windows sertifika deposu üzerinden nasıl
verileceğini anlatır. Altyapı: `tools/codesign.py` (bkz. DEPLOYMENT.md §5).

## 1. Hangi kip benim için uygun?

| | **PFX kipi** (dosya) | **Donanım token kipi** (EV) |
|---|---|---|
| Sertifika türü | OV veya EV (yedeklenebilir) | Genellikle **EV** |
| Özel anahtar | `.pfx` dosyasında | **Token/HSM'de kilitli** (çıkarılamaz) |
| Anahtar erişimi | Parola (`MERA_SIGN_PFX_PASSWORD`) | PIN istemi / sürücü (parola env'i gerekmez) |
| Yapılandırma | `pfx` + `pfx_password_env` alanları | `sha1` alanı (parmak izi) |
| `signtool /f` | ✅ | ❌ kullanılmaz |
| `signtool /sha1` | ❌ | ✅ |
| SmartScreen itibarı | Yavaş birikir (OV) | Hızlı (EV: donanım anahtarı itibarı) |
| Derleme makinesi | Herhangi biri | **Fiziksel token'ın bağlı olduğu** makine |
| Kaldırma/kayıp riski | PFX dosyası çalınabilir | Token kaybı = sertifika iptali + yeniden issuance |

> **Kural:** `sha1` alanı doluysa zincir `/sha1` kipini kullanır ve **parola
> ortam değişkeni aramaz** — token PIN'i imzalama anında sürücü tarafından
> sorulur (Bölüm 5).

## 2. Sertifika deposuna aktarım (tek seferlik)

Windows'a takılan token, sürücüsü kuruluysa sertifikasını otomatik olarak
kullanıcı deposuna yansıtır (`certmgr.msc` → Kişisel → Sertifikalar).
Otomatik görünmezse:

### 2.1 Sürücü kurulumu

| Token / HSM | Sürücü / Araç |
|---|---|
| SafeNet eToken / Thales | SafeNet Authentication Client (SAC) |
| Yubico (YubiKey FIPS / YubiHSM) | YubiKey Smart Card Minidriver + YubiKey Manager |
| DigiCert token (SafeNet tabanlı) | DigiCert token utility / SAC |
| Sectigo / SSL.com token'ları | Tedarikçinin token utility'si |
| Bulut HSM (Azure Key Vault, DigiCert ONE) | `KSP` + bulut kimi sağlayıcının SDK'sı (Bölüm 8) |

### 2.2 Elle içe aktarma (gerekirse)

1. `certmgr.msc` → Kişisel → Sertifikalar → Tüm Görevler → İçe Aktar
2. Token utility'sinin ürettiği `.cer`/`.pfx` sarmalayıcıyı seçin
3. "Anahtarı güçlü koru" işaretlemesine gerek yok; hedef: **Kişisel**

Sertifika görünmüyorsa: `certutil -user -store My` ile doğrulayın.

## 3. Parmak izini (SHA1) bulma

Derleme zincirinin `sha1` alanına yazılacak değer — **sertifika SHA1
parmak izi**:

```powershell
# Kullanıcı deposunda ara (konu adına göre süz)
Get-ChildItem Cert:\CurrentUser\My |
    Where-Object { $_.Subject -match "Turkiye Mera" } |
    Format-List Subject, Thumbprint, NotAfter

# Tüm kişisel sertifikaların parmak izleri + bitiş tarihleri
Get-ChildItem Cert:\CurrentUser\My |
    Select-Object Thumbprint, Subject, NotAfter |
    Sort-Object NotAfter -Descending
```

Alternatif: `certmgr.msc` → sertifika → Ayrıntılar → Parmak izi
(boşlukları silin — zincir zaten `replace(" ", "")` yapar).

**Doğru sertifikayı seçme:** kod imza (Code Signing) amaçlı olmalı —
`Enhanced Key Usage = Code Signing (1.3.6.1.5.5.7.3.3)`. Birden çok token
takılıysa `signtool sign /sha1 <izi> ...` komutu yalnızca bu izli sertifikayı
kullanır; yanlış sertifika seçimi "no certificate found" hatası verir.

## 4. Derleme zinciri yapılandırması

### 4.1 Ortam değişkeni yolu (önerilen)

```powershell
# Kalıcı (kullanıcı bazlı):
setx MERA_SIGN_SHA1 "<parmak izi, boşluksuz>"
# İsteğe bağlı: farklı zaman damgası sunucusu
# setx MERA_SIGN_TIMESTAMP "http://timestamp.digicert.com"
```

### 4.2 Yapılandırma dosyası yolu

`build_data/signing.json`:

```json
{
  "pfx": "",
  "pfx_password_env": "MERA_SIGN_PFX_PASSWORD",
  "sha1": "3a7b2c9d84e1f05a6b8c7d2e1f0a9b8c7d6e5f4a",
  "timestamp_url": "http://timestamp.digicert.com"
}
```

(Şablon: `build_data/signing.example.json` — `_kip2_donanim_token` bölümü.)

### 4.3 Çalıştırma

```bash
python tools/build_release.py --require-sign    # CI: imzasız derleme engellenir
python tools/codesign.py sign dist/MERA_BIS_PRO.exe   # PIN istemi token'dan gelir
python tools/codesign.py verify dist/MERA_BIS_PRO.exe
```

Zincir her iki kipte de `/fd SHA256` (dosya özeti), `/tr <sunucu>` (RFC3161
zaman damgası) ve `/td SHA256` (damga özeti) parametrelerini kullanır;
EV kipinde ek olarak `/sha1 <parmak izi>` ile depodaki token sertifikası
seçilir (PFX `/f` yolu hiç kullanılmaz).

## 5. PIN ve etkileşim kuralları

- **Oturum ilk imzalaması:** token CSP/KSP'si PIN istemi penceresi açar
  (ekranda bir kez). Bazı sürücüler "hatırla" seçeneği sunar.
- **Unattended/CI:** etkileşimli PIN istemi istenmiyorsa:
  - SafeNet SAC: token utility'de "PIN caching" süresini uzatın
  - Yubico: `ykman` ile PIV PIN önbelleği
  - **Dikkat:** PIN'i ortam değişkenine/dosyaya koymak, anahtarın
    çıkarılamazlığı avantajını azaltır — yalnızca izole CI runner'da ve
    kısa süreli kabul edin.
- **Zaman aşımı:** PIN istemi 2 dakika boyunca yanıtlanmazsa `signtool`
  hata verir → derleme `maybe_sign` üzerinden anlaşılır hata raporlar.
- **Çoklu imza:** zincir exe → zip → setup sırasıyla imzalar; PIN önbelleği
  açıksa tek istem yeter.

## 6. Doğrulama

```powershell
signtool verify /pa /v dist\MERA_BIS_PRO.exe
Get-AuthenticodeSignature dist\MERA_BIS_PRO.exe | Format-List *
```

Uygulama içi denetim: imzalı derlemede MERA-BİS PRO açılışta `Valid` görür ve
güvenlik uyarısı **göstermez** (bkz. `core/signature_check.py`). İmzasız
derlemede modal `NotSigned` uyarısı görünür — bu istenen davranıştır.

## 7. CI / otomasyon stratejisi

Donanım token CI'da doğrudan kullanılamaz (fiziksel USB). Seçenekler:

| Seçenek | Nasıl | Değerlendirme |
|---|---|---|
| **Derleme sunucusu + token** | Jenkinks/GitHub self-hosted runner'ın USB portuna token bağlanır; PIN önbelleği ile | Basit; token fiziksel olarak makinede kalır |
| **Bulut imza servisi** (DigiCert KeyLocker, Azure Trusted Signing, SSL.com eSigner) | KSA anahtar bulutta; CI HTTP ile imzalar | CI için ideal; EV düzeyi itibar; ek maliyet |
| **Yerelde imzala, CI'da paketle** | Geliştirici makinesinde `codesign.py sign` → imzalı dosya CI'a gider | En basit; insan adımı gerekir |

**Kilit ilkesi:** CI'da `--require-sign` kullanıyorsanız ve token yoksa,
derleme bilinçli başarısız olmalı — imzasız yayın asla otomatik oluşmamalı.

## 8. Bulut HSM köprüsü (Azure Key Vault / DigiCert ONE)

Bulut HSM kullanan kurumlar için Windows sertifika deposuna sanal sertifika
takılır:

1. Sağlayıcının **KSP/CSP**'sini kurun (ör. Azure Key Vault KSP, DigiCert
   KeyLocker KSP)
2. Sertifikayı deponun `CurrentUser\My` bölgesine sanal olarak kaydedin
3. Parmak izini Bölüm 3'teki gibi alın — zincir farkını hissetmez
4. CI'da KSP'nin kimlik doğrulaması (Service Principal / API token) —
   yine ortam değişkeniyle, asla dosyaya yazılmadan

`signtool`, `/sha1` ile bu sanal sertifikayı seçer; imza isteği KSP üzerinden
buluta gider, anahtar makineye inmez.

## 9. Sorun giderme

| Belirti | Neden / Çözüm |
|---|---|
| `signtool error: No certificates were found that met all the given criteria` | Parmak izi yanlış veya sertifika depoda değil: `Get-ChildItem Cert:\CurrentUser\My` ile karşılaştırın. `Cert:\LocalMachine\My`'de ise `signtool /csp` + `/csp` kipi veya yönetici deposu gerekir |
| İmza komutu asılı kalıyor | Token PIN istemi arka planda açılmış olabilir; görev çubuğunu kontrol edin veya PIN caching'i etkinleştirin |
| `Keyset does not exist` / `NTE_BAD_KEYSET` | Sürücü servisi çalışmıyor (SAC/ykman agent); servisi başlatın |
| İmza geçerli ama "Unknown EKU" | Sertifika Code Signing EKU'suna sahip değil; CA ile görüşün |
| İmza sonrası dosya boyutu değişmedi, imza görünmüyor | AV/EDR imza bölümünü karantinaya almış olabilir; exclusions'a derleme dizinini ekleyin |
| Token'ı çıkarınca imzalama devam ediyor | Normal: PIN önbelleği açık. Kapatın veya token'ı çıkarın |
| `timestamp.digicert.com` erişilemiyor | Ağ proxy'si RFC3161'i engelliyor olabilir; `MERA_SIGN_TIMESTAMP` ile kurum içi RFC3161 sunucusuna geçin |
| `sha1` kipinde "password not found" hatası | Eski davranış: 1.2.5 öncesi zincir SHA1 kipinde de parola istiyordu — güncel `codesign.py` bu hatayı düzeltir (PARMAK İZİ YETERLİ) |

## 10. Güvenlik başlangıç kuralları

- Özel anahtar **asla dışarı çıkmaz**: PFX'e dönüştürme/dışa aktarma denemeleri
  EV sertifikada CA tarafından zaten engellenir
- Token'ı derleme dışı zamanlarda güvenli kilitli yerde saklayın
- Parmak izi (SHA1) gizli değildir — sertifikanın kamusal kimliğidir; ancak
  yapılandırma dosyasına yazılmışsa `signing.json` sürüm kontrolüne girmemeli
  (`signing.example.json` şablon olarak depolanır)
- Kayıp/çalıntı durumunda CA'ya **hemen iptal** bildirimi + yeni sertifika
- Zaman damgası sunucusu erişilebilir olmalı; damgasız imza, sertifika süresi
  bitince geçersizleşir
