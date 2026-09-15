@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem A3 tropical farm remake deployment for the standard nested checkout:
rem   repo : C:\VENGENCE\Jagged Alliance 2\00000
rem   game : C:\VENGENCE\Jagged Alliance 2
rem
rem Graphics-only A3 deployment. The authored A3.dat is NEVER copied or replaced.
rem This script deploys visual assets only; map geometry/placement stays authoritative.

set "REPO=%~dp0"
for %%I in ("%REPO%..") do set "GAME=%%~fI"

if not exist "%GAME%\JA2_EN_Release.exe" (
    echo.
    echo ERROR: Active game executable was not found:
    echo   %GAME%\JA2_EN_Release.exe
    echo.
    echo Expected checkout layout:
    echo   C:\VENGENCE\Jagged Alliance 2\00000
    pause
    exit /b 1
)

set "TILESRC=%REPO%Data-Maps-Tiles\Tilesets\38"
set "TILEDST=%GAME%\Data-Maps-Tiles\Tilesets\38"

if not exist "%TILESRC%" (
    echo ERROR: Source tileset 38 not found.
    pause
    exit /b 1
)

if not exist "%TILEDST%" mkdir "%TILEDST%"

echo.
echo A3 tropical farm remake deployment
echo Source repo : %REPO%
echo Active game : %GAME%
echo.

set "FAIL=0"

echo MAP SAFETY: A3.dat is not copied. Existing authored map remains untouched.
echo.
rem Reusable visual-only farm library. These assets carry no JSD and cannot
rem alter collision, LOS, pathing, cover or authored map placement by themselves.
for %%F in (
    VR_CROP_MASTER.b1tc
    A3_MUD_RUTS.b1tc
    A3_LANDMARKS.b1tc
    A3_FIELD_STONES.b1tc
    A3_WOOD_YARD.b1tc
    A3_EDGE_WEEDS.b1tc
    A3_IRRIGATION.b1tc
    A3_FARM_JUNK.b1tc
) do (
    if not exist "%TILESRC%\%%F" (
        echo MISSING REQUIRED ASSET: %%F
        set "FAIL=1"
    ) else (
        copy /Y "%TILESRC%\%%F" "%TILEDST%\%%F" >nul
        if errorlevel 1 (
            echo COPY FAILED: %%F
            set "FAIL=1"
        ) else (
            fc /b "%TILESRC%\%%F" "%TILEDST%\%%F" >nul
            if errorlevel 1 (
                echo VERIFY FAILED: %%F
                set "FAIL=1"
            ) else (
                echo OK: Tilesets\38\%%F
            )
        )
    )
)

rem Copy the broader A3/VR crop vocabulary as well.  Not every family is consumed
rem by A3 today; these are retained as a reusable rural-sector library.
for %%F in ("%TILESRC%\A3_*.b1tc" "%TILESRC%\VR_CROP_*.b1tc") do (
    if exist "%%~fF" copy /Y "%%~fF" "%TILEDST%\%%~nxF" >nul
)

if "%FAIL%"=="1" (
    echo.
    echo A3 deployment FAILED. Do not test this pass until the missing/copy error is fixed.
    pause
    exit /b 2
)

echo.
echo A3 VISUAL ASSETS DEPLOYED AND VERIFIED.
echo.
echo SAFETY INVARIANTS:
echo   - A3.dat was not modified or copied.
echo   - No runtime map dressing is expected or required.
echo   - Visual profiles must not add/remove/relocate map nodes or placements.
echo   - Structural replacement art must keep canonical STI/JSD geometry.
echo.
echo IMPORTANT:
echo   Build and deploy the latest vr_source Release Win32 executable before testing.
echo   Load A3 normally; visual overrides should appear without changing sector layout.
echo.
pause
exit /b 0
