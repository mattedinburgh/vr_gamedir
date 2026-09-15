param(
    [string]$GameRoot = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoRoot = $PSScriptRoot

$validator = Join-Path $RepoRoot "VALIDATE_AMBIENCE.ps1"
if (Test-Path $validator) {
    & $validator -RepoRoot $RepoRoot
    if ($LASTEXITCODE -ne 0) { throw "Ambience validation failed; deployment aborted." }
}

function Resolve-GameRoot {
    param([string]$Requested)

    if ($Requested) {
        return (Resolve-Path $Requested).Path
    }

    $candidates = @()
    if ($env:VR_GAME_ROOT) { $candidates += $env:VR_GAME_ROOT }
    $candidates += (Split-Path $RepoRoot -Parent)
    $candidates += "C:\VENGENCE\Jagged Alliance 2"

    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        if ((Test-Path (Join-Path $candidate "Data-Vengeance")) -or
            (Test-Path (Join-Path $candidate "ja2.exe")) -or
            (Test-Path (Join-Path $candidate "JA2.exe"))) {
            return (Resolve-Path $candidate).Path
        }
    }

    throw "Could not locate the Vengeance game root. Pass -GameRoot 'C:\path\to\Jagged Alliance 2' or set VR_GAME_ROOT."
}

function Test-SameFile {
    param([string]$Source, [string]$Destination)

    if (-not (Test-Path $Destination)) { return $false }

    $src = Get-Item $Source
    $dst = Get-Item $Destination
    if ($src.Length -ne $dst.Length) { return $false }

    return ((Get-FileHash -Algorithm SHA256 $Source).Hash -eq
            (Get-FileHash -Algorithm SHA256 $Destination).Hash)
}

function Copy-ChangedFile {
    param([string]$Source, [string]$Destination)

    $destinationDir = Split-Path $Destination -Parent
    if (-not (Test-Path $destinationDir)) {
        New-Item -ItemType Directory -Force -Path $destinationDir | Out-Null
    }

    if (-not $Force -and (Test-SameFile $Source $Destination)) {
        $script:Skipped++
        return
    }

    Copy-Item -Force $Source $Destination
    $script:Copied++
    Write-Host ("  updated  " + $Destination)
}

$GameRoot = Resolve-GameRoot $GameRoot
$Copied = 0
$Skipped = 0

Write-Host "Vengeance ambience incremental deploy"
Write-Host ("Source: " + $RepoRoot)
Write-Host ("Game:   " + $GameRoot)
if ($Force) { Write-Host "Mode:   FORCE" } else { Write-Host "Mode:   changed/new files only" }

$manifest = @(
    "Data-Vengeance\SectorAmbience.ini"
)

foreach ($relative in $manifest) {
    $src = Join-Path $RepoRoot $relative
    if (-not (Test-Path $src)) { throw "Missing source file: $src" }
    Copy-ChangedFile $src (Join-Path $GameRoot $relative)
}

$assetRoots = @(
    "Data-Vengeance\Sounds\VR_Ambience"
)

foreach ($relativeRoot in $assetRoots) {
    $sourceRoot = Join-Path $RepoRoot $relativeRoot
    if (-not (Test-Path $sourceRoot)) { throw "Missing source directory: $sourceRoot" }

    Get-ChildItem -File -Recurse $sourceRoot | ForEach-Object {
        $relative = $_.FullName.Substring($RepoRoot.Length).TrimStart('\')
        Copy-ChangedFile $_.FullName (Join-Path $GameRoot $relative)
    }
}

Write-Host ""
Write-Host ("Ambience deploy complete: {0} updated, {1} unchanged." -f $Copied, $Skipped)
Write-Host "Use -Force only for clean recovery or when you deliberately want every ambience file recopied."
