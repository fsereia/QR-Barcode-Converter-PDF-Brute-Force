#!/bin/bash
# ================================================================
#  Leitor Sereia v2 — gera o app (.app) e um instalador (.dmg) no macOS.
#  Rode num Mac:  bash build_mac.sh
#
#  Precisa do Homebrew. O script cuida do resto:
#   - instala a lib zbar (leitor de código de barras) se faltar;
#   - cria/usa o ambiente Python (.venv) com as dependências;
#   - empacota tudo com o PyInstaller (zbar, tkinter, arrastar-e-soltar);
#   - gera dist/LeitorSereia.app e dist/LeitorSereia.dmg.
#
#  Obs: o PyInstaller NÃO cruza de um SO pro outro. O .app só pode ser
#  gerado no Mac; o .exe do Windows é gerado pelo build_windows.bat no Windows.
# ================================================================
set -e
cd "$(dirname "$0")"

echo "[1/6] Verificando a lib zbar (Homebrew)..."
if ! brew list zbar >/dev/null 2>&1; then
  echo "  -> instalando zbar..."
  brew install zbar
fi

echo "[2/6] Preparando o ambiente Python (.venv)..."
if [ ! -x ".venv/bin/python" ]; then
  PYBIN="$(command -v python3.12 || command -v python3)"
  echo "  -> criando .venv com $PYBIN"
  "$PYBIN" -m venv .venv
fi
PY=".venv/bin/python"
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r requirements.txt pyinstaller >/dev/null

echo "[3/6] Preparando o ícone..."
ICON_ARG=""
if [ -f assets/icon.png ]; then
  if sips -s format icns assets/icon.png --out assets/icon.icns >/dev/null 2>&1; then
    ICON_ARG="--icon assets/icon.icns"
  else
    ICON_ARG="--icon assets/icon.png"
  fi
fi

echo "[4/6] Localizando a libzbar pra embutir..."
ZBAR_LIB="$(brew --prefix zbar)/lib/libzbar.dylib"
if [ ! -f "$ZBAR_LIB" ]; then
  # fallback: procura qualquer libzbar.*.dylib
  ZBAR_LIB="$(ls "$(brew --prefix zbar)"/lib/libzbar*.dylib 2>/dev/null | head -1)"
fi
echo "  -> $ZBAR_LIB"

echo "[5/6] Empacotando com o PyInstaller..."
"$PY" -m PyInstaller --noconfirm --clean --windowed \
  --name LeitorSereia \
  $ICON_ARG \
  --osx-bundle-identifier com.sereia.leitorsereia \
  --add-data "assets:assets" \
  --add-binary "${ZBAR_LIB}:." \
  --collect-all tkinterdnd2 \
  --collect-all pyzbar \
  --collect-submodules pynput \
  --collect-submodules Quartz \
  app.py

echo "[6/6] Gerando o .dmg..."
APP="dist/LeitorSereia.app"
if [ -d "$APP" ]; then
  rm -f dist/LeitorSereia.dmg
  hdiutil create -volname "Leitor Sereia" -srcfolder "$APP" \
    -ov -format UDZO dist/LeitorSereia.dmg >/dev/null
  echo ""
  echo "Pronto!"
  echo "  App:        $APP"
  echo "  Instalador: dist/LeitorSereia.dmg"
  echo ""
  echo "Para instalar: abra o .dmg e arraste o LeitorSereia pra pasta Aplicativos."
  echo "Na 1a abertura o macOS pode avisar 'desenvolvedor não identificado':"
  echo "  botão direito no app > Abrir > Abrir. (Some depois que o app for assinado.)"
  echo "Pros atalhos globais: Ajustes > Privacidade e Segurança > Acessibilidade > ligar o LeitorSereia."
else
  echo "ERRO: não encontrei $APP — algo falhou no PyInstaller acima."
  exit 1
fi
