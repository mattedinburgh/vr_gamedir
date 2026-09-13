@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem A3 tropical farm remake deployment for the standard nested checkout:
rem   repo : C:\VENGENCE\Jagged Alliance 2\00000
rem   game : C:\VENGENCE\Jagged Alliance 2
rem
rem Copies the authored A3 map plus the complete reusable true-colour farm kit.
rem The source-side hero composer still requires the latest Release Win32 EXE.

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

set "MAPSRC=%REPO%Data-Maps-Tiles\maps"
set "MAPDST=%GAME%\Data-Maps-Tiles\maps"
set "TILESRC=%REPO%Data-Maps-Tiles\Tilesets\38"
set "TILEDST=%GAME%\Data-Maps-Tiles\Tilesets\38"

if not exist "%MAPSRC%\A3.dat" (
    echo ERROR: Source A3.dat not found.
    pause
    exit /b 1
)
if not exist "%TILESRC%" (
    echo ERROR: Source tileset 38 not found.
    pause
    exit /b 1
)

if not exist "%MAPDST%" mkdir "%MAPDST%"
if not exist "%TILEDST%" mkdir "%TILEDST%"

echo.
echo A3 tropical farm remake deployment
echo Source repo : %REPO%
echo Active game : %GAME%
echo.

set "FAIL=0"

copy /Y "%MAPSRC%\A3.dat" "%MAPDST%\A3.dat" >nul
if errorlevel 1 (
    echo COPY FAILED: A3.dat
    set "FAIL=1"
) else (
    fc /b "%MAPSRC%\A3.dat" "%MAPDST%\A3.dat" >nul
    if errorlevel 1 (
        echo VERIFY FAILED: A3.dat
        set "FAIL=1"
    ) else (
        echo OK: maps\A3.dat
    )
)

rem Runtime-required true-colour families used by TileEngine/worlddef.cpp.
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
echo A3 DATA DEPLOYED AND VERIFIED.
echo.
echo Source-side hero pass included in the matching vr_source branch:
echo   - six irregular crop fields
echo   - dense mature crop beds and harvested breaks
echo   - tractor/trampled access corridors
echo   - two open cattle paddocks
echo   - irrigation junctions and field breaches
echo   - denser working farmyard compositions
echo   - hand-directed hero landmarks and roof detail
echo   - expanded runtime cattle herd with clear animal footprints
echo.
echo IMPORTANT:
echo   Build and deploy the latest vr_source Release Win32 executable before testing.
echo   Test A3 from a fresh sector load/new entry so runtime dressing is regenerated.
echo.
pause
exit /b 0
