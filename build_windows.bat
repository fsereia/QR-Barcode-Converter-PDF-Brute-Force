@echo off
REM ================================================================
REM  Leitor Sereia v2 - gera o LeitorSereia.exe (Windows)
REM
REM  Rode este arquivo numa maquina Windows (de dois cliques ou no
REM  Prompt de Comando). Pre-requisito: Python 3.10+ instalado do
REM  site python.org COM a opcao "Add Python to PATH" marcada
REM  (o instalador do python.org ja traz o tkinter embutido).
REM
REM  O script cria um ambiente .venv, instala as dependencias e
REM  empacota tudo (zbar, tkinter, arrastar-e-soltar, atalhos) num
REM  unico dist\LeitorSereia.exe.
REM
REM  Obs: o PyInstaller NAO cruza de um sistema pro outro. Este .exe
REM  so pode ser gerado no Windows; o app do Mac sai do build_mac.sh.
REM ================================================================
setlocal
cd /d "%~dp0"

echo [1/4] Preparando o ambiente Python (.venv)...
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv 2>nul
  if not exist ".venv\Scripts\python.exe" python -m venv .venv
)
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo ERRO: nao consegui criar o ambiente Python. Instale o Python 3.10+ do
  echo python.org marcando "Add Python to PATH" e rode de novo.
  pause
  exit /b 1
)

echo [2/4] Instalando dependencias...
"%PY%" -m pip install --upgrade pip
"%PY%" -m pip install -r requirements.txt pyinstaller pywin32
if errorlevel 1 (
  echo ERRO ao instalar dependencias. Veja as mensagens acima.
  pause
  exit /b 1
)

echo [3/4] Empacotando com o PyInstaller...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name LeitorSereia ^
  --icon assets\icon.ico ^
  --add-data "assets;assets" ^
  --collect-all tkinterdnd2 ^
  --collect-all pyzbar ^
  --collect-submodules pynput ^
  app.py

echo [4/4] Verificando o resultado...
if exist "dist\LeitorSereia.exe" (
  echo.
  echo Pronto! O executavel esta em:  dist\LeitorSereia.exe
  echo.
  echo Para usar:
  echo   - De dois cliques em dist\LeitorSereia.exe ^(aparece um icone na bandeja,
  echo     perto do relogio^).
  echo   - No menu do icone, "Instalar menu botao-direito ^(.pdf^)" ativa o clique
  echo     direito nos PDFs para destravar.
  echo.
  echo Para distribuir, copie o LeitorSereia.exe ^(ele e autossuficiente^).
) else (
  echo ERRO: o build falhou - nao encontrei dist\LeitorSereia.exe.
  echo Veja as mensagens do PyInstaller acima.
  pause
  exit /b 1
)
pause
endlocal
