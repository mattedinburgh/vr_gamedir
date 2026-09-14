param(
    [ValidateRange(1,3)]
    [int]$Stage = 1,

    [ValidateRange(0.0,1.0)]
    [double]$Strength = 0.72,

    [string]$GameRoot = "",

    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$ToolRoot = Join-Path $RepoRoot "tools\cold_ui"
$OutputRoot = Join-Path $RepoRoot "build\Data-UI-ColdPilot"
$PreviewRoot = Join-Path $RepoRoot "build\cold-ui-preview"
$Report = Join-Path $RepoRoot "build\cold-ui-report.json"

function Invoke-Python {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

    $Py = Get-Command py -ErrorAction SilentlyContinue
    if ($Py) {
        & $Py.Source -3 @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE" }
        return
    }

    $Python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $Python) {
        throw "Python 3 was not found in PATH."
    }

    & $Python.Source @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python command failed with exit code $LASTEXITCODE" }
}

Write-Host "Vengeance cold UI pilot preparation"
Write-Host "  Stage:    $Stage"
Write-Host "  Strength: $Strength"
Write-Host "  Repo:     $RepoRoot"
Write-Host ""
Write-Host "SAFETY: this script only writes under the repository build\ directory."
Write-Host "It does not edit vfs_config.Vengeance.ini, copy files into the game, or launch JA2."
Write-Host ""

# Preview/raster generation uses Pillow. Do not silently alter the Python environment.
try {
    Invoke-Python "-c" "import PIL"
}
catch {
    throw "Pillow is required. Install it explicitly with: python -m pip install pillow"
}

if ($Stage -ge 3) {
    if ([string]::IsNullOrWhiteSpace($GameRoot)) {
        throw "Stage 3 requires -GameRoot because it reads selected UI source files from Data\Interface.slf and Data\Laptop.slf."
    }

    $ResolvedGameRoot = (Resolve-Path $GameRoot).Path
    $ResolvedRepoRoot = (Resolve-Path $RepoRoot).Path

    if ($ResolvedRepoRoot.StartsWith($ResolvedGameRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        Write-Host "Game root contains the repository; extraction still writes only under build\." -ForegroundColor Yellow
    }

    $BridgeArgs = @(
        (Join-Path $ToolRoot "extract_slf_ui.py"),
        "--game-root", $ResolvedGameRoot,
        "--manifest", (Join-Path $ToolRoot "slf_bridge_manifest.json"),
        "--output-root", (Join-Path $RepoRoot "build\cold-ui-base-extract")
    )
    Invoke-Python @BridgeArgs
}

$PrepareArgs = @(
    (Join-Path $ToolRoot "prepare_cold_ui.py"),
    "--manifest", (Join-Path $ToolRoot "manifest.json"),
    "--source-root", $RepoRoot,
    "--output-root", $OutputRoot,
    "--stage", "$Stage",
    "--strength", "$Strength",
    "--write",
    "--previews",
    "--preview-root", $PreviewRoot,
    "--report", $Report
)

if ($Force) {
    $PrepareArgs += "--force"
}

Invoke-Python @PrepareArgs

Write-Host ""
Write-Host "Prepared. Nothing was deployed or launched." -ForegroundColor Green
Write-Host "Overlay:  $OutputRoot"
Write-Host "Previews: $PreviewRoot"
Write-Host "Report:   $Report"
