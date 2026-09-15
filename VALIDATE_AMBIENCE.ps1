param(
    [string]$RepoRoot = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
$iniPath = Join-Path $RepoRoot "Data-Vengeance\SectorAmbience.ini"
if (-not (Test-Path $iniPath)) { throw "Missing $iniPath" }

$lines = Get-Content -LiteralPath $iniPath
$sections = @{}
$current = ""
foreach ($line in $lines) {
    if ($line -match '^\s*\[(.+?)\]\s*$') {
        $current = $Matches[1]
        $sections[$current] = $true
    }
}

$assetRefs = 0
$profileRefs = 0
$errors = New-Object System.Collections.Generic.List[string]
$current = ""

function Resolve-AmbienceAsset {
    param([string]$Value)

    $relative = $Value.Trim() -replace '/', '\'
    if ($relative -match '^(?i)(Sounds|AMBIENT)\\') {
        $relative = "Data-Vengeance\$relative"
    }
    return (Join-Path $RepoRoot $relative)
}

foreach ($line in $lines) {
    if ($line -match '^\s*\[(.+?)\]\s*$') {
        $current = $Matches[1]
        continue
    }

    if ($line -notmatch '^\s*([^;][^=]*?)\s*=\s*(.*?)\s*$') { continue }
    $key = $Matches[1].Trim()
    $value = $Matches[2].Trim()
    if (-not $value) { continue }

    if ($key -match '_(LOOP|SOUND_\d+)$') {
        $assetRefs++
        $path = Resolve-AmbienceAsset $value
        if (-not (Test-Path -LiteralPath $path)) {
            $errors.Add("Missing asset: [$current] $key = $value")
            continue
        }

        if ([IO.Path]::GetExtension($path) -ieq ".wav") {
            $stream = [IO.File]::OpenRead($path)
            try {
                if ($stream.Length -lt 12) {
                    $errors.Add("Invalid WAV (too short): $value")
                } else {
                    $header = New-Object byte[] 12
                    [void]$stream.Read($header, 0, 12)
                    $riff = [Text.Encoding]::ASCII.GetString($header, 0, 4)
                    $wave = [Text.Encoding]::ASCII.GetString($header, 8, 4)
                    if ($riff -ne "RIFF" -or $wave -ne "WAVE") {
                        $errors.Add("Invalid WAV header: $value")
                    }
                }
            } finally {
                $stream.Dispose()
            }
        }
    }

    if ($current -eq "SECTOR_OVERRIDES" -or $current -eq "TILESET_PROFILES") {
        $profileRefs++
        if (-not $sections.ContainsKey("PROFILE_$value")) {
            $errors.Add("Missing profile: [$current] $key = $value")
        }
    }
}

if ($errors.Count -gt 0) {
    Write-Host "Ambience validation FAILED" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host ("  " + $_) -ForegroundColor Red }
    exit 1
}

Write-Host ("Ambience validation PASS: {0} asset refs, {1} profile refs, 0 missing." -f $assetRefs, $profileRefs)
exit 0
