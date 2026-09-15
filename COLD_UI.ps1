param(
    [ValidateSet("Build", "Deploy", "Activate", "Rollback")]
    [string]$Mode = "Build",

    [string]$GameRoot = $PSScriptRoot,

    [ValidateRange(1, 3)]
    [int]$Stage = 3,

    [ValidateRange(0.0, 1.0)]
    [double]$Strength = 0.72,

    [switch]$Force,

    [switch]$RemoveOverlay
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
$ToolRoot = Join-Path $RepoRoot "tools\cold_ui"
$BuildRoot = Join-Path $RepoRoot "build"
$OverlayBuild = Join-Path $BuildRoot "Data-UI-Cold"
$PreviewRoot = Join-Path $BuildRoot "cold-ui-preview"
$PrepareReport = Join-Path $BuildRoot "cold-ui-report.json"
$ExtractReport = Join-Path $BuildRoot "cold-ui-slf-extract-report.json"
$ExtractRoot = Join-Path $BuildRoot "cold-ui-base-extract"
$DeployRoot = Join-Path $GameRoot "Data-UI-Cold"
$VfsPath = Join-Path $GameRoot "vfs_config.Vengeance.ini"

function Get-PythonCommand {
    foreach ($candidate in @("python", "py")) {
        try {
            $cmd = Get-Command $candidate -ErrorAction Stop
            return [pscustomobject]@{
                Exe = $cmd.Source
                Prefix = if ($candidate -eq "py") { @("-3") } else { @() }
            }
        } catch {}
    }
    throw "Python 3 was not found on PATH."
}

function Invoke-Python {
    param([string[]]$Arguments)
    $py = Get-PythonCommand
    $exe = $py.Exe
    $prefix = @($py.Prefix)
    & $exe @prefix @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $exe $($Arguments -join ' ')"
    }
}

function Ensure-Pillow {
    $py = Get-PythonCommand
    $exe = $py.Exe
    $prefix = @($py.Prefix)

    & $exe @prefix -c "import PIL" 2>$null
    if ($LASTEXITCODE -eq 0) { return }

    Write-Host "Pillow not found; installing it for the current Python environment..."
    & $exe @prefix -m pip install pillow
    if ($LASTEXITCODE -ne 0) {
        throw "Could not install Pillow."
    }
}

function Assert-ColdUiBuild {
    if (-not (Test-Path $PrepareReport)) {
        throw "Cold UI report was not generated: $PrepareReport"
    }

    $report = Get-Content -Raw $PrepareReport | ConvertFrom-Json
    $bad = @($report.assets | Where-Object {
        $_.status -eq "missing-source" -or
        ($_.status -eq "optional-missing-source" -and -not $_.optional) -or
        ($_.PSObject.Properties.Name -contains "structural_bytes_identical" -and $_.structural_bytes_identical -eq $false) -or
        ($_.policy -eq "preserve" -and
            $_.PSObject.Properties.Name -contains "input_sha256" -and
            $_.PSObject.Properties.Name -contains "output_sha256" -and
            $_.input_sha256 -ne $_.output_sha256)
    })

    if ($bad.Count -gt 0) {
        $names = ($bad | ForEach-Object { $_.mount_path }) -join ", "
        throw "Cold UI validation failed for: $names"
    }

    $expected = @($report.assets | Where-Object { $_.status -ne "missing-source" -and $_.status -ne "optional-missing-source" }).Count
    $actual = @(Get-ChildItem $OverlayBuild -Recurse -File | Where-Object { $_.Name -ne ".cold_ui_state.json" }).Count

    if ($actual -lt $expected) {
        throw "Cold UI output is incomplete: expected at least $expected files, found $actual."
    }

    Write-Host "Validated cold UI build: $expected manifest assets."
}

function Build-ColdUi {
    Ensure-Pillow
    New-Item -ItemType Directory -Force -Path $BuildRoot | Out-Null

    Invoke-Python @((Join-Path $ToolRoot "test_policy.py"))

    if ($Stage -ge 3) {
        if (-not (Test-Path (Join-Path $GameRoot "Data\Interface.slf"))) {
            throw "Stage 3 requires the user's original Data\Interface.slf under GameRoot: $GameRoot"
        }
        if (-not (Test-Path (Join-Path $GameRoot "Data\Laptop.slf"))) {
            throw "Stage 3 requires the user's original Data\Laptop.slf under GameRoot: $GameRoot"
        }

        $extractArgs = @(
            (Join-Path $ToolRoot "extract_slf_ui.py"),
            "--game-root", $GameRoot,
            "--manifest", (Join-Path $ToolRoot "slf_bridge_manifest.json"),
            "--output-root", $ExtractRoot,
            "--report", $ExtractReport
        )
        if ($Force) { $extractArgs += "--force" }
        Invoke-Python $extractArgs
    }

    $prepareArgs = @(
        (Join-Path $ToolRoot "prepare_cold_ui.py"),
        "--manifest", (Join-Path $ToolRoot "manifest.json"),
        "--source-root", $RepoRoot,
        "--output-root", $OverlayBuild,
        "--stage", "$Stage",
        "--strength", ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:0.####}", $Strength)),
        "--write",
        "--previews",
        "--preview-root", $PreviewRoot,
        "--report", $PrepareReport
    )
    if ($Force) { $prepareArgs += "--force" }
    Invoke-Python $prepareArgs

    Assert-ColdUiBuild
}

function Sync-ColdUiOverlay {
    if (-not (Test-Path $OverlayBuild)) {
        throw "Build overlay does not exist: $OverlayBuild"
    }

    New-Item -ItemType Directory -Force -Path $DeployRoot | Out-Null
    $statePath = Join-Path $DeployRoot ".cold_ui_deploy_state.json"

    $previous = @()
    if (Test-Path $statePath) {
        try {
            $state = Get-Content -Raw $statePath | ConvertFrom-Json
            $previous = @($state.files)
        } catch {
            Write-Warning "Could not read previous cold UI deployment state; continuing conservatively."
        }
    }

    $current = New-Object System.Collections.Generic.List[string]
    $copied = 0
    $skipped = 0

    Get-ChildItem $OverlayBuild -Recurse -File |
        Where-Object { $_.Name -ne ".cold_ui_state.json" } |
        ForEach-Object {
            $relative = $_.FullName.Substring($OverlayBuild.Length).TrimStart("\", "/")
            $current.Add($relative)
            $dst = Join-Path $DeployRoot $relative
            $dstDir = Split-Path -Parent $dst
            New-Item -ItemType Directory -Force -Path $dstDir | Out-Null

            $same = $false
            if (Test-Path $dst) {
                $same = (Get-FileHash $_.FullName -Algorithm SHA256).Hash -eq
                        (Get-FileHash $dst -Algorithm SHA256).Hash
            }

            if ($same -and -not $Force) {
                $skipped++
            } else {
                Copy-Item $_.FullName $dst -Force
                $copied++
            }
        }

    $removed = 0
    foreach ($relative in $previous) {
        if ($current -notcontains $relative) {
            $stale = Join-Path $DeployRoot $relative
            if (Test-Path $stale) {
                Remove-Item $stale -Force
                $removed++
            }
        }
    }

    $state = [ordered]@{
        version = 1
        stage = $Stage
        strength = $Strength
        files = @($current | Sort-Object)
    }
    $state | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $statePath

    Write-Host "Cold UI incremental deployment: copied=$copied unchanged=$skipped stale-removed=$removed"
}

function Set-ColdUiActivation {
    param([bool]$Enabled)

    if (-not (Test-Path $VfsPath)) {
        throw "Vengeance VFS configuration not found: $VfsPath"
    }

    $text = Get-Content -Raw $VfsPath
    $newline = if ($text.Contains("`r`n")) { "`r`n" } else { "`n" }

    if ($Enabled) {
        $backup = "$VfsPath.cold-ui.pre-activation.bak"
        if (-not (Test-Path $backup)) {
            Copy-Item $VfsPath $backup
        }

        $profilesRegex = '(?im)^PROFILES\s*=\s*(.+)$'
        $match = [regex]::Match($text, $profilesRegex)
        if (-not $match.Success) {
            throw "Could not find PROFILES line in $VfsPath"
        }

        $profiles = @($match.Groups[1].Value.Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        if ($profiles -notcontains "coldui") {
            $newProfiles = New-Object System.Collections.Generic.List[string]
            foreach ($p in $profiles) {
                $newProfiles.Add($p)
                if ($p -ieq "ui") { $newProfiles.Add("coldui") }
            }
            if ($newProfiles -notcontains "coldui") { $newProfiles.Add("coldui") }
            $replacement = "PROFILES = " + ($newProfiles -join ", ")
            $text = [regex]::Replace($text, $profilesRegex, $replacement, 1)
        }

        if ($text -notmatch '(?im)^\[PROFILE_coldui\]\s*$') {
            $block = @(
                "",
                "[PROFILE_coldui]",
                "NAME = Vengeance Cold UI",
                "LOCATIONS = datacoldui_dir",
                "PROFILE_ROOT = "
            ) -join $newline
            $text += $newline + $block + $newline
        }

        if ($text -notmatch '(?im)^\[LOC_datacoldui_dir\]\s*$') {
            $block = @(
                "",
                "[LOC_datacoldui_dir]",
                "TYPE = DIRECTORY",
                "PATH = Data-UI-Cold",
                "MOUNT_POINT = "
            ) -join $newline
            $text += $newline + $block + $newline
        }

        Set-Content -Path $VfsPath -Value $text -Encoding Default
        Write-Host "Cold UI VFS profile activated after the existing UI layer."
        return
    }

    $profilesRegex = '(?im)^PROFILES\s*=\s*(.+)$'
    $match = [regex]::Match($text, $profilesRegex)
    if ($match.Success) {
        $profiles = @($match.Groups[1].Value.Split(",") |
            ForEach-Object { $_.Trim() } |
            Where-Object { $_ -and $_ -ine "coldui" })
        $replacement = "PROFILES = " + ($profiles -join ", ")
        $text = [regex]::Replace($text, $profilesRegex, $replacement, 1)
    }

    foreach ($section in @("PROFILE_coldui", "LOC_datacoldui_dir")) {
        $pattern = "(?ims)^\[$([regex]::Escape($section))\]\s*.*?(?=^\[|\z)"
        $text = [regex]::Replace($text, $pattern, "")
    }

    Set-Content -Path $VfsPath -Value ($text.TrimEnd() + $newline) -Encoding Default
    Write-Host "Cold UI VFS profile disabled."
}

switch ($Mode) {
    "Build" {
        Build-ColdUi
        Write-Host "Build complete. Nothing was copied into the live game profile."
    }
    "Deploy" {
        Build-ColdUi
        Sync-ColdUiOverlay
        Write-Host "Overlay deployed but NOT activated."
    }
    "Activate" {
        Build-ColdUi
        Sync-ColdUiOverlay
        Set-ColdUiActivation -Enabled $true
        Write-Host "Cold UI build, incremental deployment and activation complete."
    }
    "Rollback" {
        Set-ColdUiActivation -Enabled $false
        if ($RemoveOverlay -and (Test-Path $DeployRoot)) {
            Remove-Item $DeployRoot -Recurse -Force
            Write-Host "Removed deployed cold UI overlay: $DeployRoot"
        } else {
            Write-Host "Overlay files were left in place; they are inactive because the VFS profile is disabled."
        }
    }
}
