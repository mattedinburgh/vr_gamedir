param(
  [switch]$Revert
)
$ErrorActionPreference = "Stop"
$PilotRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$GameRoot = Resolve-Path (Join-Path $PilotRoot "..\..")
$PilotItems = Join-Path $PilotRoot "Data-AIMv53\BigItems"
$LiveItems = Join-Path $GameRoot "Data-AIMv53\BigItems"
$Backup = Join-Path $PilotRoot "_backup\Data-AIMv53\BigItems"

if ($Revert) {
  if (-not (Test-Path $Backup)) { throw "No pilot backup exists." }
  Get-ChildItem $Backup -Filter "*.STI" | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $LiveItems $_.Name) -Force
    Write-Host "restored $($_.Name)"
  }
  exit 0
}

New-Item -ItemType Directory -Force -Path $Backup | Out-Null
$copied = 0
Get-ChildItem $PilotItems -Filter "*.STI" | ForEach-Object {
  $dst = Join-Path $LiveItems $_.Name
  if (-not (Test-Path $dst)) { throw "Live icon missing: $dst" }
  $srcHash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
  $dstHash = (Get-FileHash $dst -Algorithm SHA256).Hash
  if ($srcHash -ne $dstHash) {
    $bak = Join-Path $Backup $_.Name
    if (-not (Test-Path $bak)) { Copy-Item $dst $bak }
    Copy-Item $_.FullName $dst -Force
    $copied++
    Write-Host "installed $($_.Name)"
  } else {
    Write-Host "unchanged $($_.Name)"
  }
}
Write-Host "Pilot install complete: $copied changed icon(s)."
