#!/bin/bash
# ================================================================
#  Leitor Sereia v2 - gera o app no macOS
#  Rode num Mac, depois de instalar as dependencias (veja o README).
#  IMPORTANTE: no Mac o pyzbar precisa da lib zbar:  brew install zbar
# ================================================================
set -e
cd "$(dirname "$0")"

echo "[1/4] Verificando zbar (brew)..."
if ! brew list zbar >/dev/null 2>&1; then
  echo "  -> instalando zbar via Homebrew..."
  brew install zbar
fi

echo "[2/4] Instalando dependencias Python..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller

echo "[3/4] Gerando o app..."
# No Mac, o pyzbar precisa achar a libzbar do brew. O hook abaixo embute ela.
ZBAR_LIB="$(brew --prefix zbar)/lib/libzbar.dylib"
pyinstaller --noconfirm --clean --onefile --windowed \
  --name LeitorSereia \
  --icon assets/icon.png \
  --add-data "assets:assets" \
  --add-binary "${ZBAR_LIB}:." \
  app.py

echo "[4/4] Pronto!"
echo "O app esta em:  dist/LeitorSereia"
echo ""
echo "Obs: no primeiro uso, o macOS vai pedir permissao de Acessibilidade"
echo "para o atalho global funcionar (Ajustes > Privacidade > Acessibilidade)."
