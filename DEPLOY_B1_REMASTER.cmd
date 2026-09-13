@echo off
setlocal EnableExtensions

rem B1 remaster deployment for the standard nested checkout:
rem   repo : C:\VENGENCE\Jagged Alliance 2\00000
rem   game : C:\VENGENCE\Jagged Alliance 2
rem
rem The script derives both paths from its own location and never copies .git.

set "REPO=%~dp0"
for %%I in ("%REPO%..") do set "GAME=%%~fI"

if not exist "%GAME%\JA2_EN_Release.exe" (
    echo.
    echo ERROR: Active game executable was not found:
    echo   %GAME%\JA2_EN_Release.exe
    echo.
    echo Run this script from the vr_gamedir checkout located directly inside
    echo the active Jagged Alliance 2 folder.
    pause
    exit /b 1
)

set "SRC=%REPO%Data-Maps-Tiles\Tilesets\50"
set "DST=%GAME%\Data-Maps-Tiles\Tilesets\50"

if not exist "%SRC%" (
    echo ERROR: Source tileset folder not found:
    echo   %SRC%
    pause
    exit /b 1
)

if not exist "%DST%" mkdir "%DST%"

echo.
echo B1 remaster deployment
echo Source: %SRC%
echo Target: %DST%
echo.

rem Copy all B1-specific STI/JSD/B1TC assets. This preserves the original
rem authored game files and does not touch saves, profiles or repository data.
robocopy "%SRC%" "%DST%" B1_*.* /R:2 /W:1 /NFL /NDL /NJH /NJS /NP
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
    echo ERROR: robocopy failed with code %RC%.
    pause
    exit /b %RC%
)

rem B1 also uses these oil-rig-specific visual families.
for %%F in (
    Oil_decal.sti Oil_decal.b1tc
    Oil_Debris.sti Oil_Debris.b1tc
    Oil_Crane2.sti Oil_Crane2.b1tc
    Oil_Cranes.sti Oil_Cranes.b1tc
    Oil_furn.sti Oil_furn.b1tc
    Oil_lamp.sti Oil_lamp.b1tc
) do (
    if exist "%SRC%\%%F" copy /Y "%SRC%\%%F" "%DST%\%%F" >nul
)

echo Verifying key true-colour payloads...
set "FAIL=0"
for %%F in (
    B1_T_SAND1.b1tc
    B1_TR_WATER.b1tc
    B1_ROADTLE2.b1tc
    B1_WELFLOR3.b1tc
    B1_BUILD_36.b1tc
    B1_W-ROOF2.b1tc
    Oil_Crane2.b1tc
    Oil_Cranes.b1tc
    Oil_furn.b1tc
    Oil_lamp.b1tc
) do (
    if not exist "%DST%\%%F" (
        echo   MISSING: %%F
        set "FAIL=1"
    ) else (
        echo   OK: %%F
    )
)

if "%FAIL%"=="1" (
    echo.
    echo Deployment incomplete. Do not test B1 yet.
    pause
    exit /b 2
)

echo.
echo B1 remaster deployed successfully.
echo Active game:
echo   %GAME%\JA2_EN_Release.exe
echo.
echo After building the latest vr_source Release Win32 executable, launch the
echo game and enter B1. BlackBox_LastRun.log should report TRUECOLOR ACTIVE.
echo.
pause
exit /b 0
