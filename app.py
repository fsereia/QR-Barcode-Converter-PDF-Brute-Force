#!/usr/bin/env python3
"""
app.py — Leitor Sereia (v2): ícone no tray que lê QR Code / código de barras
e destrava PDFs protegidos com os CPFs/CNPJs das lojas.

Modos de execução
-----------------
  python app.py                 -> inicia o app no tray (uso normal)
  python app.py --settings      -> abre a janela de cadastro de CPFs/CNPJs
  python app.py --area          -> seleção de área da tela pra ler QR/barras
  python app.py --unlock ARQ    -> destrava um PDF (usado pelo botão-direito,
                                    pelo 'Enviar para' e pelo arrastar-no-ícone)

As janelas (área, config, resultado do PDF) rodam como processos separados
de propósito: assim o tkinter sempre roda na thread principal do seu próprio
processo e funciona igual no Windows e no Mac, sem conflito com o tray.

Multiplataforma: Windows e macOS (o menu de botão-direito é só Windows).
"""

from __future__ import annotations

import os
import sys
import threading


# ---------------------------------------------------------------------------
# App empacotado (PyInstaller): faz o pyzbar achar a libzbar embutida
# ---------------------------------------------------------------------------

def _patch_zbar_for_frozen() -> None:
    """
    Fora do Windows, o pyzbar carrega a libzbar via find_library('zbar'), que
    só funciona se a lib estiver instalada no sistema (ex.: Homebrew). No app
    empacotado a libzbar vem embutida, mas o find_library não a enxerga numa
    máquina sem Homebrew. Aqui, quando rodando congelado, apontamos o loader do
    pyzbar direto pra lib embutida. Precisa rodar ANTES de importar pyzbar.
    """
    if not getattr(sys, "frozen", False):
        return
    import glob
    from ctypes import cdll

    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(sys.executable)
    cands = glob.glob(os.path.join(base, "libzbar*.dylib")) or \
        glob.glob(os.path.join(base, "**", "libzbar*.dylib"), recursive=True)
    if not cands:
        return
    try:
        from pyzbar import zbar_library
        _lib = cdll.LoadLibrary(cands[0])
        zbar_library.load = lambda: (_lib, [])
    except Exception as e:
        print(f"(aviso: não consegui pré-carregar a libzbar embutida: {e})")


_patch_zbar_for_frozen()


# ---------------------------------------------------------------------------
# Utilitários comuns
# ---------------------------------------------------------------------------

def _here() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _base_command() -> list[str]:
    """Comando base pra relançar este app em outro modo (lida com .exe e .py)."""
    if getattr(sys, "frozen", False):          # empacotado pelo PyInstaller
        return [sys.executable]
    return [sys.executable, os.path.join(_here(), "app.py")]


def _launch(mode_flag: str, *extra: str) -> None:
    import subprocess
    subprocess.Popen(_base_command() + [mode_flag, *extra], close_fds=True)


def _copy_text(text: str) -> None:
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        # fallback tkinter (sempre disponível)
        try:
            import tkinter as tk
            r = tk.Tk(); r.withdraw()
            r.clipboard_clear(); r.clipboard_append(text); r.update()
            r.destroy()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Modo: destravar PDF (--unlock)  — usado pelo botão-direito / enviar-para / drag
# ---------------------------------------------------------------------------

def mode_unlock(pdf_path: str) -> int:
    import tkinter as tk
    from tkinter import messagebox
    from core import config_store, pdf_unlock

    root = tk.Tk(); root.withdraw()

    if not pdf_path or not os.path.isfile(pdf_path):
        messagebox.showerror("Leitor Sereia", f"Arquivo não encontrado:\n{pdf_path}")
        return 2

    cfg = config_store.load()
    ids = cfg.as_identifier_objects()
    if not ids:
        messagebox.showwarning(
            "Leitor Sereia — cadastre os números",
            "Você ainda não cadastrou nenhum CPF/CNPJ das lojas.\n\n"
            "Abra o app no tray → 'Cadastrar CPFs/CNPJs' e preencha antes de destravar.",
        )
        return 3

    res = pdf_unlock.unlock(pdf_path, ids, save_copy=cfg.save_unlocked_copy,
                            overwrite=cfg.overwrite_original)
    if res.ok:
        if res.had_user_password:
            msg = (f"✅ Senha encontrada!\n\n"
                   f"Loja/sócio: {res.identifier_label}\n"
                   f"Regra: {res.rule}\n"
                   f"(testou {res.tried} combinação(ões))")
        else:
            msg = "✅ Este PDF não tinha senha de abertura (só permissões)."
        if res.saved_to:
            if res.overwritten:
                msg += f"\n\nOriginal substituído pela versão sem senha:\n{res.saved_to}"
            else:
                msg += f"\n\nCópia sem senha salva em:\n{res.saved_to}"
        messagebox.showinfo("Leitor Sereia — PDF destravado", msg)
        return 0
    else:
        messagebox.showerror("Leitor Sereia — não consegui", res.error or "Falha desconhecida.")
        return 1


# ---------------------------------------------------------------------------
# Modo: configurações (--settings)
# ---------------------------------------------------------------------------

def mode_settings() -> int:
    from settings_window import open_settings
    open_settings()
    return 0


# ---------------------------------------------------------------------------
# Leitura de QR / código de barras
# ---------------------------------------------------------------------------

def _flash(message: str, ok: bool = True, ms: int = 1700) -> None:
    """Aviso rápido que some sozinho — não trava o fluxo pra recortes seguidos."""
    import tkinter as tk
    try:
        win = tk.Tk()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-alpha", 0.95)
        except tk.TclError:
            pass
        bg = "#19c37d" if ok else "#d9534f"
        frame = tk.Frame(win, bg=bg, padx=18, pady=12)
        frame.pack()
        tk.Label(frame, text=message, bg=bg, fg="white",
                 font=("Segoe UI", 11, "bold"), justify="left", wraplength=420).pack()
        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        win.geometry(f"{w}x{h}+{sw - w - 24}+32")  # canto superior direito
        win.after(ms, win.destroy)
        win.mainloop()
    except Exception:
        print(message)


def mode_area() -> int:
    """
    Captura a tela primeiro, MOSTRA a captura (com um véu escuro por cima, não
    uma tela preta) e deixa você arrastar sobre o código. O recorte é cortado
    da captura em alta resolução (lida com Retina), decodificado e copiado.
    """
    import tkinter as tk
    from tkinter import messagebox
    from PIL import ImageTk
    from core.screen import capture_fullscreen
    from core.reader import decode_image, best_text

    shot = capture_fullscreen()
    if shot is None:
        root = tk.Tk(); root.withdraw()
        messagebox.showwarning(
            "Leitor Sereia — permissão de tela",
            "Não consegui capturar a tela.\n\n"
            "Ative o Leitor Sereia em:\n"
            "Ajustes do Sistema → Privacidade e Segurança → Gravação de Tela\n\n"
            "Vou abrir essa tela de ajustes. Depois de ligar, tente de novo.")
        root.destroy()
        _open_privacy_pane("Privacy_ScreenCapture")
        return 0

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.configure(bg="black")
    sw = root.winfo_screenwidth() or shot.width
    sh = root.winfo_screenheight() or shot.height
    # escala pixels-da-captura -> pontos-da-tela (Retina: scale ~2)
    scale_x = shot.width / sw
    scale_y = shot.height / sh
    disp = shot if shot.size == (sw, sh) else shot.resize((sw, sh))
    tkimg = ImageTk.PhotoImage(disp)

    canvas = tk.Canvas(root, cursor="cross", highlightthickness=0, bg="black")
    canvas.pack(fill="both", expand=True)
    canvas.create_image(0, 0, anchor="nw", image=tkimg)
    canvas.image = tkimg  # evita o garbage collector comer a imagem
    canvas.create_rectangle(0, 0, sw, sh, fill="black", stipple="gray50", outline="")
    canvas.create_text(sw // 2, 28, text="Arraste sobre o código  •  ESC cancela",
                       fill="white", font=("Helvetica", 15, "bold"))

    sel = {}
    rect = {"id": None, "x0": 0, "y0": 0}

    def on_down(e):
        rect["x0"], rect["y0"] = e.x, e.y
        if rect["id"]:
            canvas.delete(rect["id"])
        rect["id"] = canvas.create_rectangle(e.x, e.y, e.x, e.y, outline="#19c37d", width=2)

    def on_move(e):
        if rect["id"]:
            canvas.coords(rect["id"], rect["x0"], rect["y0"], e.x, e.y)

    def on_up(e):
        sel["box"] = (min(rect["x0"], e.x), min(rect["y0"], e.y),
                      max(rect["x0"], e.x), max(rect["y0"], e.y))
        root.destroy()

    def on_esc(_):
        sel.clear()
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_down)
    canvas.bind("<B1-Motion>", on_move)
    canvas.bind("<ButtonRelease-1>", on_up)
    root.bind("<Escape>", on_esc)
    root.mainloop()

    box = sel.get("box")
    if not box or (box[2] - box[0] < 4) or (box[3] - box[1] < 4):
        return 0  # cancelado

    px = (int(box[0] * scale_x), int(box[1] * scale_y),
          int(box[2] * scale_x), int(box[3] * scale_y))
    crop = shot.crop(px)

    hits = decode_image(crop)
    # a imagem é descartada aqui: só o texto é guardado/copiado.
    if hits:
        from core import history
        text = best_text(hits)
        _copy_text(text)
        history.add_many(hits)
        preview = text if len(text) <= 160 else text[:157] + "…"
        _flash(f"Lido e copiado:\n{preview}", ok=True)
    else:
        _flash("Nada encontrado nesse recorte.", ok=False)
    return 0


def mode_history() -> int:
    from history_window import open_history
    open_history()
    return 0


def _read_fullscreen_then_area() -> None:
    """
    Tenta ler a tela inteira primeiro (rápido, sem janela). Se não achar nada,
    abre a seleção de área. Roda numa thread do processo do tray.
    """
    from core.screen import capture_fullscreen
    from core.reader import decode_image, best_text

    img = capture_fullscreen()
    if img is None:
        _notify("Permissão de tela necessária",
                "Ative o Leitor Sereia em Ajustes > Privacidade e Segurança > Gravação de Tela.")
        if sys.platform == "darwin":
            _open_privacy_pane("Privacy_ScreenCapture")
        return
    try:
        hits = decode_image(img)
    except Exception as e:
        _notify("Erro na leitura", str(e))
        return
    if hits:
        from core import history
        text = best_text(hits)
        _copy_text(text)
        history.add_many(hits)
        _notify("Copiado!", text[:180])
        return
    # nada na tela inteira -> seleção de área manual (processo próprio)
    _launch("--area")


def _open_privacy_pane(anchor: str) -> None:
    """Abre o painel de privacidade do macOS (anchor: Privacy_ScreenCapture
    ou Privacy_Accessibility). No-op fora do Mac."""
    if sys.platform != "darwin":
        return
    import subprocess
    try:
        subprocess.Popen(["open", f"x-apple.systempreferences:com.apple.preference.security?{anchor}"])
    except Exception:
        pass


def _read_clipboard_image() -> None:
    try:
        from PIL import ImageGrab
        from core.reader import decode_image, best_text
        img = ImageGrab.grabclipboard()
        if img is None or isinstance(img, list):
            _notify("Leitor Sereia", "Não há imagem na área de transferência.")
            return
        hits = decode_image(img)
        if hits:
            from core import history
            text = best_text(hits)
            _copy_text(text)
            history.add_many(hits)
            _notify("Copiado!", text[:180])
        else:
            _notify("Leitor Sereia", "Nenhum QR/código de barras na imagem colada.")
    except Exception as e:
        _notify("Erro", str(e))


# ---------------------------------------------------------------------------
# Notificação (toast) a partir do processo do tray
# ---------------------------------------------------------------------------

_ICON_REF = {"icon": None}
_HOTKEY_REF = {"listener": None}


# ---------------------------------------------------------------------------
# Atalhos globais (pynput) — multiplataforma
# ---------------------------------------------------------------------------

def _hotkey_to_pynput(hk: str) -> str:
    """Converte 'ctrl+shift+q' (formato do config) pro formato do pynput
    ('<ctrl>+<shift>+q'). Modificadores viram <...>, teclas de 1 caractere
    ficam como estão, e nomes maiores (f2, space…) viram <f2>, <space>."""
    mods = {
        "ctrl": "<ctrl>", "control": "<ctrl>",
        "shift": "<shift>",
        "alt": "<alt>", "option": "<alt>", "opt": "<alt>",
        "cmd": "<cmd>", "command": "<cmd>", "super": "<cmd>",
        "win": "<cmd>", "windows": "<cmd>", "meta": "<cmd>",
    }
    out = []
    for t in (hk or "").lower().replace(" ", "").split("+"):
        if not t:
            continue
        if t in mods:
            out.append(mods[t])
        elif len(t) == 1:
            out.append(t)
        else:
            out.append(f"<{t}>")
    return "+".join(out)


def _notify(title: str, message: str) -> None:
    icon = _ICON_REF.get("icon")
    try:
        if icon is not None:
            icon.notify(message, title)
            return
    except Exception:
        pass
    print(f"[{title}] {message}")


# ---------------------------------------------------------------------------
# Modo tray (padrão)
# ---------------------------------------------------------------------------

def run_tray() -> int:
    import pystray
    from PIL import Image
    from core import config_store

    # ícone
    icon_png = os.path.join(_here(), "assets", "icon.png")
    try:
        image = Image.open(icon_png)
    except Exception:
        image = Image.new("RGB", (64, 64), "#19c37d")

    def act_read(icon, item):
        threading.Thread(target=_read_fullscreen_then_area, daemon=True).start()

    def act_read_region(icon, item):
        _launch("--area")

    def act_read_clip(icon, item):
        threading.Thread(target=_read_clipboard_image, daemon=True).start()

    def act_history(icon, item):
        _launch("--history")

    def act_settings(icon, item):
        _launch("--settings")

    def _integration_module():
        if sys.platform == "darwin":
            import mac_integration as mi
            return mi
        import windows_integration as wi
        return wi

    def act_install_menu(icon, item):
        msg = _integration_module().install()
        _notify("Leitor Sereia", msg)

    def act_remove_menu(icon, item):
        msg = _integration_module().uninstall()
        _notify("Leitor Sereia", msg)

    def act_perm_screen(icon, item):
        # dispara uma captura (faz o macOS registrar/pedir a permissão) e abre o painel
        try:
            from core.screen import capture_fullscreen
            capture_fullscreen()
        except Exception:
            pass
        _open_privacy_pane("Privacy_ScreenCapture")

    def act_perm_accessibility(icon, item):
        _open_privacy_pane("Privacy_Accessibility")

    def act_quit(icon, item):
        lst = _HOTKEY_REF.get("listener")
        if lst is not None:
            try:
                lst.stop()
            except Exception:
                pass
        icon.stop()

    cfg = config_store.load()
    is_windows = sys.platform.startswith("win")
    is_mac = sys.platform == "darwin"
    menu_items = [
        pystray.MenuItem(f"Ler tela inteira  ({cfg.hotkey})", act_read, default=True),
        pystray.MenuItem(f"Recortar área da tela  ({cfg.hotkey_region})", act_read_region),
        pystray.MenuItem("Ler imagem colada (área de transferência)", act_read_clip),
        pystray.MenuItem("Ver histórico de leituras…", act_history),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Destravar PDF / Cadastrar CPFs-CNPJs…", act_settings),
    ]
    if is_windows:
        menu_items += [
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Instalar menu botão-direito (.pdf)", act_install_menu),
            pystray.MenuItem("Remover menu botão-direito (.pdf)", act_remove_menu),
        ]
    elif is_mac:
        menu_items += [
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Instalar Ação Rápida botão-direito (.pdf)", act_install_menu),
            pystray.MenuItem("Remover Ação Rápida botão-direito (.pdf)", act_remove_menu),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Permissão: Gravação de Tela…", act_perm_screen),
            pystray.MenuItem("Permissão: Acessibilidade (atalhos)…", act_perm_accessibility),
        ]
    menu_items += [pystray.Menu.SEPARATOR, pystray.MenuItem("Sair", act_quit)]

    icon = pystray.Icon("LeitorSereia", image, "Leitor Sereia", menu=pystray.Menu(*menu_items))
    _ICON_REF["icon"] = icon

    # atalhos globais (pynput: Windows sem admin; Mac pede permissão de Acessibilidade)
    def _hot_read():
        threading.Thread(target=_read_fullscreen_then_area, daemon=True).start()

    def _hot_area():
        _launch("--area")

    try:
        from pynput import keyboard as _kb
        hk_read = _hotkey_to_pynput(cfg.hotkey)
        hk_area = _hotkey_to_pynput(cfg.hotkey_region)
        mapping = {}
        if hk_read:
            mapping[hk_read] = _hot_read
        if hk_area and hk_area != hk_read:
            mapping[hk_area] = _hot_area
        listener = _kb.GlobalHotKeys(mapping)
        listener.daemon = True
        listener.start()
        _HOTKEY_REF["listener"] = listener
    except Exception as e:
        print(f"(atalho global indisponível: {e} — use o menu do tray). "
              f"No Mac, libere o app em Ajustes → Privacidade e Segurança → Acessibilidade.")

    icon.run()
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str]) -> int:
    if "--unlock" in argv:
        i = argv.index("--unlock")
        path = argv[i + 1] if i + 1 < len(argv) else ""
        if not path:  # chamado sem arquivo -> cai pra settings (tem botão de escolher)
            return mode_settings()
        return mode_unlock(path)
    if "--settings" in argv:
        return mode_settings()
    if "--area" in argv:
        return mode_area()
    if "--history" in argv:
        return mode_history()
    return run_tray()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
