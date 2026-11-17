@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
echo ==========================================
echo  TermFinale Windows 一键打包
echo ==========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 没有找到 Python。
  echo 请先安装 Python 3.12，安装时勾选 "Add python.exe to PATH"。
  echo 下载：https://www.python.org/downloads/release/python-31210/
  pause
  exit /b 1
)

python -c "import sys; v=sys.version_info; print('Python', v.major, v.minor, v.micro); sys.exit(0 if (3,10) <= (v.major,v.minor) < (3,14) else 1)"
if errorlevel 1 (
  echo.
  echo [警告] 当前 Python 不是 3.10 - 3.13，建议安装 Python 3.12 再打包。
  echo 继续可能失败。按任意键仍要继续，或关闭窗口去安装 3.12。
  pause
)

if not exist ".venv" (
  echo [1/4] 创建虚拟环境...
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo [2/4] 安装依赖（第一次需要几分钟）...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo [错误] 依赖安装失败，请截图发给作者。
  pause
  exit /b 1
)

echo [3/4] 开始打包（约 3-10 分钟）...
python tools\build.py
if errorlevel 1 (
  echo [错误] 打包失败，请把窗口里的报错截图发给作者。
  pause
  exit /b 1
)

set /p VER=<VERSION
if "%VER%"=="" set VER=0.4.0

echo [4/4] 压缩产物...
if exist "dist\TermFinale\TermFinale.exe" (
  powershell -NoProfile -Command "Compress-Archive -Path 'dist\TermFinale\*' -DestinationPath 'TermFinale-%VER%-win-x64.zip' -Force"
  echo.
  echo ==========================================
  echo  完成！
  echo  压缩包：%CD%\TermFinale-%VER%-win-x64.zip
  echo  把这个 zip 文件发回给作者即可。
  echo ==========================================
) else (
  echo [错误] 没有找到 dist\TermFinale\TermFinale.exe
)
pause
