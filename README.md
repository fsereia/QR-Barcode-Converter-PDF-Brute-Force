# Leitor Sereia v2

App de bandeja (tray) que faz **duas coisas**, 100% offline, na própria máquina:

1. **Lê QR Code e código de barras** a partir de um print/recorte da tela ou de uma imagem colada — e copia o texto pra área de transferência.
2. **Destrava PDFs protegidos** usando os CPFs dos sócios / CNPJs das lojas que você cadastrou — e, de quebra, **diz de qual loja o documento é** e salva uma cópia sem senha.

Nada sai do computador. O destravador só testa senhas que **você** cadastrou (seus próprios CPF/CNPJ) — é o mesmo que você faria à mão, só que em 1 segundo.

---

## O que mudou da v1 (leitor de QR)

- Agora lê **código de barras 1D** também (EAN-13/8, Code128, Code39, ITF/boleto), não só QR.
- **Destravador de PDF** novo, com identificação da loja.
- **Atalho de recorte** estilo Mac (`Ctrl+Shift+4`) que captura, converte e **descarta a imagem**.
- **Histórico** de tudo que foi lido, pra copiar e colar depois.
- No Windows: **menu de botão-direito** no `.pdf` e atalho no **"Enviar para"**.

---

## Atalhos de teclado (globais)

| Atalho | O que faz |
|---|---|
| `Ctrl+Shift+Q` | Lê a **tela inteira** na hora. Se não achar nada, abre o recorte. |
| `Ctrl+Shift+4` | Abre a **mira de recorte** (estilo `Cmd+Shift+4` do Mac): você arrasta sobre o QR/código, ele converte, **joga a imagem fora** e copia o texto. |

Os dois guardam o resultado no **histórico**. Dá pra trocar os atalhos no `config.json`.

> **No Mac:** `Cmd+Shift+4` é o print nativo do próprio macOS, então lá o atalho de recorte do app fica em `Ctrl+Shift+4` (configurável). Atalho global no Mac exige dar permissão de **Acessibilidade** pro app.

---

## Como usar o destravador de PDF

1. No menu do tray → **"Destravar PDF / Cadastrar CPFs-CNPJs"**.
2. Cadastre cada CPF/CNPJ com um **rótulo claro** (ex.: `CNPJ Asics Londrina`, `CPF Felippe`).
3. Pronto. A partir daí, 3 jeitos de destravar um PDF (Windows):
   - **Botão direito** no arquivo `.pdf` → *Destravar PDF (Leitor Sereia)*.
   - **Enviar para** → *Destravar PDF (Leitor Sereia)*.
   - Ou pelo botão **"Destravar um PDF agora…"** dentro da janela de cadastro.

O app testa variações comuns de cada número (5 primeiros do CPF, CNPJ completo, raiz do CNPJ, etc.). Quando uma abre, ele mostra **a loja** e **a regra** que funcionou, e salva `arquivo_sem_senha.pdf` ao lado do original (**nunca sobrescreve** o original).

Pra ativar o menu de botão-direito: rode o app, e no menu do tray clique em **"Instalar menu botão-direito (.pdf)"** (não precisa de admin — é só pro seu usuário).

---

## Rodar sem compilar (teste rápido)

Precisa de Python 3.10+.

```bash
pip install -r requirements.txt
python app.py
```

No **Mac**, antes: `brew install zbar` (senão o leitor de código de barras não carrega).

---

## Gerar o executável

### Windows (`.exe`)
Dê dois cliques em **`build_windows.bat`** (ou rode no terminal). Sai em `dist\LeitorSereia.exe`.
Passo a passo completo (pré-requisitos, uso, instalador): veja **[WINDOWS.md](WINDOWS.md)**.

### macOS
No terminal: `bash build_mac.sh`. Sai em `dist/LeitorSereia`.

> O PyInstaller **não** compila de um SO pro outro: pra ter o `.exe` você roda o build no Windows, e pra ter o app Mac você roda no Mac.

---

## Onde ficam seus dados

Tudo numa pasta local, só sua:

- Windows: `%APPDATA%\LeitorSereia\`
- macOS: `~/Library/Application Support/LeitorSereia/`
- Linux: `~/.config/LeitorSereia/`

Arquivos: `config.json` (seus CPFs/CNPJs rotulados) e `history.json` (histórico de leituras — **só o texto**, nunca as imagens).

---

## Estrutura do projeto

```
sereia_tray_v2/
├── app.py                  # app do tray + modos --area/--settings/--history/--unlock
├── settings_window.py      # janela de cadastro de CPFs/CNPJs + destravar PDF
├── history_window.py       # janela do histórico de leituras
├── windows_integration.py  # menu botão-direito + "Enviar para" (Windows)
├── core/
│   ├── pdf_unlock.py        # acha a senha (CPF/CNPJ) e salva cópia sem senha
│   ├── reader.py            # decodifica QR + código de barras (pyzbar + OpenCV)
│   ├── config_store.py      # config local
│   └── history.py           # histórico local
├── assets/                 # ícone
├── requirements.txt
├── build_windows.bat
├── build_mac.sh
└── config.example.json
```

---

## Problemas comuns

- **"Unable to find zbar shared library" (Mac):** rode `brew install zbar` e gere o app de novo.
- **Atalho global não funciona (Mac):** dê permissão em *Ajustes → Privacidade e Segurança → Acessibilidade*.
- **Atalho global não funciona (Windows):** a lib `keyboard` às vezes precisa que o app seja aberto como administrador pra capturar teclas globais. Se não quiser, use o menu do tray ou o `Ctrl+Shift+4` só funcionando com o app em foco.
- **"Nenhum CPF/CNPJ abriu este PDF":** confira se o identificador da loja certa está cadastrado, ou se aquele fornecedor usa um padrão diferente (dá pra cadastrar a senha exata como um identificador).
