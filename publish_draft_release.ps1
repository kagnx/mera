#Requires -Version 5.1
<#
.SYNOPSIS
  MERA-BIS PRO - GitHub Release taslak (draft) yayin araci.

.DESCRIPTION
  Staging klasorundeki varliklari dogrular (dosya varligi + SHA-256 parite),
  gh CLI ve kimlik durumunu denetler, taslak release olusturur.
  -Publish verilmedigi surece yalnizca PLAN cikarir; hicbir sey yuklemez.

  gh CLI yoksa winget kurulum komutunu ve el ile adimlari yazar (exit 2).
  Kimlik yoksa gh auth login yonergesini yazar (exit 3).

  Surum tek kaynagi build_data/version.json'dir: -Version verilmezse surum
  oradan okunur (staging adi, varlik adlari ve tag otomatik turetilir).

  NOT: -R (repo) bayragiyla calisir; yerel git klonu GEREKMEZ. Tag varsayilan
  dalin ucuna isaret eder. Release her zaman --draft olusturulur (inceleme
  sonrasi "gh release edit v<surum> --draft=false" veya web'den yayinlanir).

.EXAMPLE
  # Plan modu (yukleme yok, surum version.json'dan otomatik):
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\publish_draft_release.ps1 -Repo "org/mera-bis-pro"

  # Surumu elle gecersiz kilma:
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\publish_draft_release.ps1 -Repo "org/mera-bis-pro" -Version 1.2.21

  # Gercek yukleme:
  powershell -NoProfile -ExecutionPolicy Bypass -File tools\publish_draft_release.ps1 -Repo "org/mera-bis-pro" -Publish
#>
param(
    # Not: Mandatory KULLANILMAZ — verilmezse etkileşimli sorup otomasyonda
    # (CI/sessiz çalıştırma) süreci asılı bırakır. Bunun yerine aşağıda açık
    # doğrulama yapılır: boşsa net mesajla hemen çıkar.
    [Parameter(Mandatory = $false)]
    [AllowEmptyString()]
    [string]$Repo = "",

    [string]$Version = "",

    [string]$Staging = "",

    [switch]$Publish
)

$ErrorActionPreference = "Stop"

# --- Repo dogrulamasi (etkileşimsiz) ---------------------------------------
# owner/repo biçimi zorunlu; eksikse süreç ASILI kalmadan net mesajla çıkar.
if ($env:MERA_RELEASE_REPO -and -not $Repo) { $Repo = $env:MERA_RELEASE_REPO }
if (-not $Repo) {
    Write-Host "HATA: -Repo verilmedi (owner/repo biciminde)." -ForegroundColor Red
    Write-Host ""
    Write-Host "Kullanim:"
    Write-Host "  powershell -File tools/publish_draft_release.ps1 -Repo OWNER/REPO [-Publish]"
    Write-Host "Kalici atama (opsiyonel):"
    Write-Host '  setx MERA_RELEASE_REPO "OWNER/REPO"   # sonraki calistirmalarda otomatik okunur'
    exit 7
}
if ($Repo -notmatch "^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$") {
    Write-Host ("HATA: -Repo owner/repo biciminde olmali, alinan: " + $Repo) -ForegroundColor Red
    Write-Host "Ornek: -Repo kurum-adim/mera-bis-pro"
    exit 7
}

# --- Yollar ---------------------------------------------------------------
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# --- Surum: verilmemisse build_data/version.json'dan oku -------------------
if (-not $Version) {
    $verFile = Join-Path $ProjectRoot (Join-Path "build_data" "version.json")
    if (-not (Test-Path -LiteralPath $verFile)) {
        Write-Error ("version.json bulunamadi: " + $verFile + " (-Version ile belirtin)")
        exit 6
    }
    try {
        $parsed = Get-Content -LiteralPath $verFile -Raw | ConvertFrom-Json
        $Version = ([string]$parsed.version).Trim()
    } catch {
        Write-Error ("version.json okunamadi: " + $_.Exception.Message)
        exit 6
    }
    if (-not $Version) {
        Write-Error "version.json'da gecerli 'version' alani yok."
        exit 6
    }
    Write-Host ("Surum   : " + $Version + "  (version.json'dan okundu)")
}

if (-not $Staging) {
    $Staging = Join-Path $ProjectRoot (Join-Path "dist\release" ("gh_release_v" + $Version))
}
$SetupName    = "MERA_BIS_PRO_Setup_v$Version.exe"
$PortableName = "MERA_BIS_PRO_v$Version.exe"
$ZipName      = "MERA_BIS_PRO_$Version.zip"
$SumsName     = "SHA256SUMS_v$Version.txt"
$NotesName    = "RELEASE_NOTES_v$Version.md"
$Tag          = "v$Version"

Write-Host "=== MERA-BIS PRO GitHub Release yayin araci ==="
Write-Host ("Repo    : " + $Repo)
Write-Host ("Tag     : " + $Tag + "  (draft)")
Write-Host ("Staging : " + $Staging)
Write-Host ""

# --- 1) Staging klasoru ve varliklari -------------------------------------
if (-not (Test-Path -LiteralPath $Staging)) {
    Write-Error ("Staging klasoru yok: " + $Staging)
    exit 4
}
$assets = @()
foreach ($name in @($SetupName, $PortableName, $ZipName, $SumsName, $NotesName)) {
    $p = Join-Path $Staging $name
    if (-not (Test-Path -LiteralPath $p)) {
        Write-Error ("Eksik varlik: " + $p)
        exit 4
    }
    $assets += $p
}
Write-Host "[1/4] Varliklar tamam (5 dosya)."

# --- 2) SHA-256 parite dogrulamasi ----------------------------------------
$sumsPath = Join-Path $Staging $SumsName
$mismatch = 0
foreach ($line in Get-Content -LiteralPath $sumsPath) {
    if (-not $line.Trim()) { continue }
    $parts = $line -split "\s+", 2
    $expected = $parts[0].ToLower()
    # sha256sum binary-mode yazar ' *dosya' (yıldız önekli); texte-mode ' dosya'.
    # Her iki biçimi de kabul et: öndeki ayraç+yıldız önekini temizle.
    $fname = $parts[1].Trim()
    if ($fname.StartsWith("*")) { $fname = $fname.Substring(1) }
    $actual = (Get-FileHash -LiteralPath (Join-Path $Staging $fname) -Algorithm SHA256).Hash.ToLower()
    if ($actual -ne $expected) {
        Write-Host ("  UYUSMAZLIK: " + $fname + "  beklenen=" + $expected + "  gercek=" + $actual)
        $mismatch++
    } else {
        Write-Host ("  OK: " + $fname)
    }
}
if ($mismatch -gt 0) {
    Write-Error ("SHA-256 paritesi bozuk (" + $mismatch + " dosya) - YAYINMAYIN.")
    exit 5
}
Write-Host "[2/4] SHA-256 paritesi dogrulandi."

# --- 3) gh CLI denetimi ----------------------------------------------------
$gh = Get-Command gh -ErrorAction SilentlyContinue
if (-not $gh) {
    Write-Host ""
    Write-Host "[3/4] gh CLI BULUNAMADI." -ForegroundColor Yellow
    Write-Host "Kurulum (winget):"
    Write-Host "  winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements"
    Write-Host "Kurulumdan sonra yeni terminal acip tekrar deneyin. El ile akis:"
    Write-Host ("  gh auth login")
    Write-Host ("  gh release create $Tag " + $SetupName + " " + $PortableName + " " + $ZipName + " " + $SumsName + " -R " + $Repo + " --draft --title ""MERA-BIS PRO v" + $Version + """ --notes-file " + $NotesName)
    exit 2
}
Write-Host ("[3/4] gh CLI bulundu: " + $gh.Source)

# Windows PowerShell 5.1'de dogrudan 2>&1, EAP=Stop altinda ErrorRecord
# gurultusu uretir; stderr'i cmd katmaninda birlestir (cikti duz metin olur).
$authOut = (cmd /c "gh auth status 2>&1" | Out-String)
Write-Host $authOut.TrimEnd()
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "GitHub kimlik dogrulamasi YOK. Calistirin: gh auth login" -ForegroundColor Yellow
    Write-Host "Gerekli kapsam: repo (varlik yukleme + release olusturma)."
    exit 3
}
Write-Host "      Kimlik dogrulamasi: TAMAM."

# --- 4) Plan veya yayin ----------------------------------------------------
Write-Host "[4/4] " -NoNewline
if (-not $Publish) {
    Write-Host "PLAN MODU (-Publish verilmedi, yukleme yapilmaz)."
    Write-Host ""
    Write-Host "Calistirilacak komut:"
    Write-Host ("  gh release create $Tag -R " + $Repo + " --draft --title ""MERA-BIS PRO v" + $Version + """ --notes-file """ + (Join-Path $Staging $NotesName) + """")
    foreach ($a in @($SetupName, $PortableName, $ZipName, $SumsName)) {
        Write-Host ("    yuklenecek: " + (Join-Path $Staging $a))
    }
    Write-Host ""
    Write-Host "Gercek yukleme icin: -Publish anahtariyla tekrar calistirin."
    exit 0
}

Write-Host "TASLAK RELEASE OLUSTURULUYOR..."
& gh release create $Tag `
    (Join-Path $Staging $SetupName) `
    (Join-Path $Staging $PortableName) `
    (Join-Path $Staging $ZipName) `
    (Join-Path $Staging $SumsName) `
    -R $Repo --draft --title ("MERA-BIS PRO v" + $Version) `
    --notes-file (Join-Path $Staging $NotesName)
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Release olusturma BASARISIZ (kod $LASTEXITCODE)." -ForegroundColor Red
    Write-Host "Release zaten varsa: gh release view $Tag -R $Repo  /  silmek icin:"
    Write-Host ("  gh release delete $Tag -R " + $Repo + " --yes")
    exit 6
}

Write-Host ""
Write-Host "=== TASLAK YAYIN TAMAM ===" -ForegroundColor Green
& gh release view $Tag -R $Repo --json name,isDraft,url | Write-Host
Write-Host ("Web'de yayinlamak icin: gh release edit $Tag -R " + $Repo + " --draft=false")
exit 0
