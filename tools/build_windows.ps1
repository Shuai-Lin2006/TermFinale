# TermFinale Windows 构建脚本
# 在项目根目录运行：powershell -ExecutionPolicy Bypass -File tools\build_windows.ps1
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

python --version
if (-not (Test-Path ".venv")) { python -m venv .venv }
. .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

python tools\build.py
Write-Host "`n构建完成：dist\TermFinale\TermFinale.exe" -ForegroundColor Green
Write-Host "把整个 dist\TermFinale 文件夹压缩后发回即可。" -ForegroundColor Green
