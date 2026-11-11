# Leitor Sereia — gerar e usar no Windows

O app é o mesmo do Mac; só o jeito de empacotar muda. O `.exe` **precisa ser
gerado numa máquina Windows** — o PyInstaller não cria um `.exe` a partir do Mac.

---

## 1. Pré-requisito: Python

Instale o **Python 3.10 ou mais novo** pelo site oficial:
https://www.python.org/downloads/

> Na primeira tela do instalador, **marque a caixa "Add Python to PATH"** antes
> de clicar em Install. O instalador do python.org já traz a interface gráfica
> (tkinter) embutida — no Windows não precisa instalar nada à parte para isso.

Para conferir, abra o **Prompt de Comando** e rode:

```
python --version
```

Deve mostrar algo como `Python 3.12.x`.

---

## 2. Pegar o projeto

Baixe o projeto do GitHub (botão **Code → Download ZIP** e extraia), ou, se tiver
o Git instalado:

```
git clone https://github.com/fsereia/QR-Barcode-Converter-PDF-Brute-Force.git
```

---

## 3. Gerar o executável

Dentro da pasta do projeto, **dê dois cliques em `build_windows.bat`** (ou rode
ele pelo Prompt de Comando). Ele cria o ambiente, instala tudo e empacota.

No fim, o app estará em:

```
dist\LeitorSereia.exe
```

Esse `.exe` é autossuficiente: dá para copiar para outro PC Windows e rodar lá,
sem instalar Python.

---

## 4. Rodar sem gerar o executável (teste rápido)

Se quiser só testar sem empacotar:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python app.py
```

---

## 5. Como usar

- Ao abrir o `LeitorSereia.exe`, ele vira um **ícone na bandeja** (canto inferior
  direito, perto do relógio). Tudo é feito pelo menu desse ícone.
- **Atalhos globais** (`Ctrl+Shift+Q` e `Ctrl+Shift+4`): funcionam no Windows sem
  precisar de administrador.
- **Destravar PDF no clique direito:** no menu do ícone → *Instalar menu
  botão-direito (.pdf)*. Depois, clique direito num PDF → *Destravar PDF (Leitor
  Sereia)*. Também aparece em *Enviar para*.
- **Arrastar e soltar:** no menu → *Destravar PDF / Cadastrar CPFs-CNPJs*, você
  cadastra os CPFs/CNPJs e arrasta o PDF para dentro da janela. A caixa
  *Substituir o original* decide se apaga a versão com senha ou salva uma cópia
  `_sem_senha.pdf` ao lado.

---

## 6. (Opcional) Instalador de verdade

O `.exe` já roda sozinho. Se quiser um **instalador** com assistente (atalho no
Menu Iniciar etc.), o caminho usual é o **Inno Setup** (gratuito):
https://jrsoftware.org/isinfo.php — ele empacota o `dist\LeitorSereia.exe` num
`setup.exe`. Posso preparar o script do Inno Setup se você quiser esse passo.

Para o Windows parar de avisar "aplicativo de origem desconhecida" (SmartScreen),
seria preciso **assinar o `.exe`** com um certificado de code signing — opcional
e pago, dá para deixar para depois.
