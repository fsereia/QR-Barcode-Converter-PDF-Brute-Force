@echo off
REM ================================================================
REM  Leitor Sereia v2 - gera o LeitorSereia.exe (Windows)
REM  Rode este arquivo numa maquina Windows, depois de instalar as
REM  dependencias (veja o README).
REM ================================================================
setlocal

echo [1/3] Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller pywin32

echo [2/3] Gerando o executavel...
pyinstaller --noconfirm --clean --onefile --windowed ^
  --name LeitorSereia ^
  --icon assets\icon.ico ^
  --add-data "assets;assets" ^
  app.py

echo [3/3] Pronto!
echo O executavel esta em:  dist\LeitorSereia.exe
echo.
echo Dica: rode o LeitorSereia.exe uma vez, abra o menu do icone no tray
echo e clique em "Instalar menu botao-direito (.pdf)".
pause
endlocal
