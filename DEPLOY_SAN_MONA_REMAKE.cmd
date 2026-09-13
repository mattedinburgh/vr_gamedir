@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem San Mona full remake deployment for the standard nested checkout:
rem   repo : C:\VENGENCE\Jagged Alliance 2\00000
rem   game : C:\VENGENCE\Jagged Alliance 2
rem
rem Deploys the remastered C5/C6/D4/D5 maps and the D4/D5 underground route.
rem It does not touch saves or profiles.

set "REPO=%~dp0"
for %%I in ("%REPO%..") do set "GAME=%%~fI"

if not exist "%GAME%\JA2_EN_Release.exe" (
    echo.
    echo ERROR: Active game executable was not found:
    echo   %GAME%\JA2_EN_Release.exe
    echo.
    echo This script expects the vr_gamedir checkout directly inside the active
    echo Jagged Alliance 2 folder, e.g. C:\VENGENCE\Jagged Alliance 2\00000.
    pause
    exit /b 1
)

set "SRC=%REPO%Data-Maps-Tiles\maps"
set "DST=%GAME%\Data-Maps-Tiles\maps"

if not exist "%SRC%" (
    echo ERROR: Source maps folder not found:
    echo   %SRC%
    pause
    exit /b 1
)

if not exist "%DST%" mkdir "%DST%"

echo.
echo San Mona full remake deployment
echo Source: %SRC%
echo Target: %DST%
echo.

set "FAIL=0"
for %%F in (
    c5.dat
    C6.DAT
    D4.DAT
    D5.DAT
    D4_B1.DAT
    D5_B1.DAT
) do (
    if not exist "%SRC%\%%F" (
        echo MISSING SOURCE: %%F
        set "FAIL=1"
    ) else (
        copy /Y "%SRC%\%%F" "%DST%\%%F" >nul
        if errorlevel 1 (
            echo COPY FAILED: %%F
            set "FAIL=1"
        ) else (
            fc /b "%SRC%\%%F" "%DST%\%%F" >nul
            if errorlevel 1 (
                echo VERIFY FAILED: %%F
                set "FAIL=1"
            ) else (
                echo OK: %%F
            )
        )
    )
)

if "%FAIL%"=="1" (
    echo.
    echo San Mona deployment incomplete. Do not test the remaster yet.
    pause
    exit /b 2
)

if exist "%REPO%SAN_MONA_FULL_REMAKE_2026-09-13.txt" (
    copy /Y "%REPO%SAN_MONA_FULL_REMAKE_2026-09-13.txt" "%GAME%\SAN_MONA_FULL_REMAKE_2026-09-13.txt" >nul
)

echo.
echo San Mona full remakeed maps deployed successfully.
echo.
echo IMPORTANT:
echo   Build/deploy the latest vr_source Release Win32 executable as well.
echo   The source-side pass supplies San Mona district grading and sparse roof detail.
echo.
echo Test sectors:
echo   C5  - vice/commerce strip
echo   C6  - Angel/commercial district with fire-scarred north
echo   D4  - abandoned mine approaches
echo   D5  - boxing club / Kingpin district
echo   D4_B1 and D5_B1 - underground stash route
echo.
echo Active game:
echo   %GAME%\JA2_EN_Release.exe
echo.
pause
exit /b 0
