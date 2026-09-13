@echo off
setlocal EnableExtensions

rem Emergency A3 rollback to original authored Vengeance sector.
rem Expected layout:
rem   game root : C:\VENGENCE\Jagged Alliance 2
rem   vr_gamedir: C:\VENGENCE\Jagged Alliance 2\00000

set "REPO=%~dp0"
for %%I in ("%REPO%..") do set "GAME=%%~fI"

set "SRCMAP=%REPO%Data-Maps-Tiles\maps\A3.dat"
set "DSTMAP=%GAME%\Data-Maps-Tiles\maps\A3.dat"
set "TILE38=%GAME%\Data-Maps-Tiles\Tilesets\38"

echo.
echo A3 ORIGINAL-SECTOR ROLLBACK
echo Repo      : %REPO%
echo Game root : %GAME%
echo.

if not exist "%SRCMAP%" (
    echo ERROR: original A3.dat is missing from repository:
    echo   %SRCMAP%
    pause
    exit /b 1
)

if not exist "%GAME%\JA2_EN_Release.exe" (
    echo ERROR: game root was not detected:
    echo   %GAME%
    pause
    exit /b 2
)

if not exist "%GAME%\Data-Maps-Tiles\maps" mkdir "%GAME%\Data-Maps-Tiles\maps"

copy /Y "%SRCMAP%" "%DSTMAP%" >nul
if errorlevel 1 (
    echo ERROR: failed to restore A3.dat.
    pause
    exit /b 3
)

rem Remove only the eight experimental replacement families that the broken
rem A3 runtime profile could hijack. With these absent, even an older EXE falls
rem back to the authored tileset imagery instead of drawing the bad panels.
for %%F in (
    "VR_CROP_MASTER"
    "A3_MUD_RUTS"
    "A3_LANDMARKS"
    "A3_FIELD_STONES"
    "A3_WOOD_YARD"
    "A3_EDGE_WEEDS"
    "A3_IRRIGATION"
    "A3_FARM_JUNK"
) do (
    if exist "%TILE38%\%%~F.b1tc" del /Q "%TILE38%\%%~F.b1tc"
    if exist "%TILE38%\%%~F.sti"  del /Q "%TILE38%\%%~F.sti"
)

echo.
echo A3 rollback deployed.
echo - original A3.dat restored
echo - experimental A3 replacement families removed from live Tileset 38
echo.
echo For the permanent source-side rollback, rebuild Release Win32 after pulling
echo vr_source commit 9094d202d8d45d9b1b27fdf22660b424cc8c0a8f or later.
echo.
pause
exit /b 0
