param([switch]$Revert)
$ErrorActionPreference = "Stop"
$PackRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$GameRoot = Resolve-Path (Join-Path $PackRoot "..\..")
$Payload = Join-Path $PackRoot "Data-AIMv53"
$Live = Join-Path $GameRoot "Data-AIMv53"
$Backup = Join-Path $PackRoot "_backup\Data-AIMv53"

if ($Revert) {
  if (-not (Test-Path $Backup)) { throw "No Save23 icon backup exists." }
  Get-ChildItem $Backup -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($Backup.Length).TrimStart("\")
    $dst = Join-Path $Live $rel
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dst) | Out-Null
    Copy-Item $_.FullName $dst -Force
    Write-Host "restored $rel"
  }
  exit 0
}

$changed = 0
Get-ChildItem $Payload -Recurse -File | ForEach-Object {
  $rel = $_.FullName.Substring($Payload.Length).TrimStart("\")
  $dst = Join-Path $Live $rel
  if (-not (Test-Path $dst)) { throw "Live asset missing: $rel" }
  $srcHash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
  $dstHash = (Get-FileHash $dst -Algorithm SHA256).Hash
  if ($srcHash -ne $dstHash) {
    $bak = Join-Path $Backup $rel
    if (-not (Test-Path $bak)) {
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $bak) | Out-Null
      Copy-Item $dst $bak
    }
    Copy-Item $_.FullName $dst -Force
    $changed++
    Write-Host "installed $rel"
  } else {
    Write-Host "unchanged $rel"
  }
}
Write-Host "Save23 icon install complete: $changed changed file(s)."
