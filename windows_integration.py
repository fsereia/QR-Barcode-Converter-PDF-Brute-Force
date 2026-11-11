"""
windows_integration.py — Menu botão-direito e "Enviar para" no Windows.

Registra, SÓ PRO USUÁRIO ATUAL (HKEY_CURRENT_USER, sem precisar de admin),
uma entrada no menu de contexto dos arquivos .pdf:

    Botão direito num .pdf  ->  "Destravar PDF (Leitor Sereia)"

e também cria um atalho em "Enviar para", pra você mandar o PDF pro app.

Tudo reversível: uninstall() remove as entradas. Não mexe em nada de sistema.

Este módulo só faz sentido no Windows; as funções viram no-op em outros SOs.
"""

from __future__ import annotations

import os
import sys


MENU_KEY = r"Software\Classes\SystemFileAssociations\.pdf\shell\LeitorSereiaUnlock"
MENU_LABEL = "Destravar PDF (Leitor Sereia)"


def _is_windows() -> bool:
    return sys.platform.startswith("win")


def _command_target() -> tuple[str, str]:
    """
    Retorna (executavel, prefixo_de_args) pra montar o comando do menu.

    - Se estiver rodando como .exe gerado pelo PyInstaller: usa o próprio .exe.
    - Se estiver rodando como script .py: usa pythonw.exe + caminho do script.
    """
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    # script: prefere pythonw (sem janela de console)
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    python = pyw if os.path.exists(pyw) else sys.executable
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "app.py"))
    return python, f'"{script}" '


def _icon_path() -> str | None:
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
    return p if os.path.exists(p) else None


def install() -> str:
    """Instala o menu de contexto e o atalho Enviar-para. Retorna mensagem de status."""
    if not _is_windows():
        return "Integração de botão-direito só existe no Windows."

    import winreg

    exe, arg_prefix = _command_target()
    command = f'"{exe}" {arg_prefix}--unlock "%1"'

    # 1) Menu de contexto do .pdf (por usuário)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, MENU_KEY) as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, MENU_LABEL)
        icon = _icon_path()
        if icon:
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, icon)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, MENU_KEY + r"\command") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)

    # 2) Atalho em "Enviar para"
    sendto_msg = _install_sendto(exe, arg_prefix)

    return f"Menu de botão-direito instalado para .pdf. {sendto_msg}"


def _install_sendto(exe: str, arg_prefix: str) -> str:
    """Cria um atalho .lnk em shell:sendto apontando pro app."""
    try:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return "(Enviar-para: APPDATA não encontrado, pulei.)"
        sendto = os.path.join(appdata, r"Microsoft\Windows\SendTo")
        if not os.path.isdir(sendto):
            return "(Enviar-para: pasta não encontrada, pulei.)"
        lnk = os.path.join(sendto, "Destravar PDF (Leitor Sereia).lnk")

        # Cria o atalho via COM (pywin32) se disponível; senão, via VBScript.
        target = exe
        arguments = f'{arg_prefix}--unlock'
        try:
            import win32com.client  # type: ignore
            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortcut(lnk)
            sc.TargetPath = target
            sc.Arguments = arguments
            icon = _icon_path()
            if icon:
                sc.IconLocation = icon
            sc.Save()
            return "Atalho em 'Enviar para' criado."
        except ImportError:
            return _install_sendto_vbs(lnk, target, arguments)
    except Exception as e:  # nunca derruba o install principal por causa do sendto
        return f"(Enviar-para falhou: {e})"


def _install_sendto_vbs(lnk: str, target: str, arguments: str) -> str:
    import subprocess
    import tempfile
    vbs = f'''
Set sh = CreateObject("WScript.Shell")
Set sc = sh.CreateShortcut("{lnk}")
sc.TargetPath = "{target}"
sc.Arguments = "{arguments}"
sc.Save
'''
    with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False, encoding="utf-8") as f:
        f.write(vbs)
        path = f.name
    try:
        subprocess.run(["cscript", "//nologo", path], check=True)
        return "Atalho em 'Enviar para' criado."
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def uninstall() -> str:
    """Remove o menu de contexto e o atalho Enviar-para."""
    if not _is_windows():
        return "Nada a remover fora do Windows."

    import winreg

    # remove command e depois a chave
    for sub in (MENU_KEY + r"\command", MENU_KEY):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except FileNotFoundError:
            pass
        except OSError:
            pass

    # remove atalho sendto
    try:
        appdata = os.environ.get("APPDATA")
        if appdata:
            lnk = os.path.join(appdata, r"Microsoft\Windows\SendTo",
                               "Destravar PDF (Leitor Sereia).lnk")
            if os.path.exists(lnk):
                os.remove(lnk)
    except OSError:
        pass

    return "Menu de botão-direito e atalho removidos."


def is_installed() -> bool:
    if not _is_windows():
        return False
    import winreg
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, MENU_KEY).Close()
        return True
    except OSError:
        return False
