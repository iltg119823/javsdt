$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not $IsWindows -and $env:OS -ne 'Windows_NT') { throw 'Build this package on Windows x64.' }
python -m pip install -r requirements.txt 'pyinstaller>=6.11,<7'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
python -m unittest discover -s tests -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
python -m PyInstaller --noconfirm --clean --onedir --contents-directory . --name JavSDT --paths src --hidden-import CreateIni --hidden-import Youma --add-data 'src/StaticFiles;StaticFiles' --icon src/StaticFiles/javsdt.ico packaging/windows_entry.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
& ./dist/JavSDT/JavSDT.exe --self-test
if ($LASTEXITCODE -ne 0) { throw 'Packaged executable smoke test failed.' }
Copy-Item MAINTENANCE.md dist/JavSDT/
Copy-Item README.md dist/JavSDT/
Copy-Item LICENSE dist/JavSDT/
Copy-Item packaging/RepairActors.bat dist/JavSDT/
Copy-Item packaging/ConfigureSites.bat dist/JavSDT/
Copy-Item packaging/JELLYFIN-ACTORS.md dist/JavSDT/
Copy-Item packaging/JAVDB-SITES.md dist/JavSDT/
Copy-Item packaging/WINDOWS-README.txt dist/JavSDT/README-FIRST.txt
python -m pip freeze | Out-File -Encoding utf8 dist/JavSDT/build-dependencies.txt
Compress-Archive -Path dist/JavSDT -DestinationPath dist/JavSDT-Windows10-x64.zip -Force
