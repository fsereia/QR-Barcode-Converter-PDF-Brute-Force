"""
mac_integration.py — Ação Rápida do Finder (menu de botão-direito) no macOS.

Equivalente Mac do windows_integration.py. Instala, SÓ PRO USUÁRIO ATUAL
(em ~/Library/Services, sem senha de admin), um Serviço / Ação Rápida:

    Botão direito num .pdf  ->  Ações Rápidas  ->  "Destravar PDF (Leitor Sereia)"

Por baixo é um workflow do Automator ("Run Shell Script") que chama este app
com  --unlock  no arquivo selecionado. Tudo reversível: uninstall() apaga a
pasta do serviço. Não mexe em nada de sistema.

Este módulo só faz sentido no macOS; as funções viram no-op em outros SOs.
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys


SERVICE_NAME = "Destravar PDF (Leitor Sereia)"


def _is_mac() -> bool:
    return sys.platform == "darwin"


def _services_dir() -> str:
    d = os.path.expanduser("~/Library/Services")
    os.makedirs(d, exist_ok=True)
    return d


def _workflow_path() -> str:
    return os.path.join(_services_dir(), f"{SERVICE_NAME}.workflow")


def _command_target() -> tuple[str, str]:
    """(executável, caminho_do_script). Script vazio quando empacotado (.app)."""
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    python = sys.executable  # o python do venv que está rodando agora
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "app.py"))
    return python, script


def _shell_command() -> str:
    exe, script = _command_target()
    if script:
        inner = f'"{exe}" "{script}" --unlock "$f"'
    else:
        inner = f'"{exe}" --unlock "$f"'
    # input chega como argumentos (inputMethod=1); roda pra cada arquivo.
    return f'for f in "$@"; do\n  {inner}\ndone\n'


def _info_plist() -> dict:
    return {
        "NSServices": [
            {
                "NSMenuItem": {"default": SERVICE_NAME},
                "NSMessage": "runWorkflowAsService",
                "NSRequiredContext": {"NSApplicationIdentifier": "com.apple.finder"},
                "NSSendFileTypes": ["com.adobe.pdf"],
            }
        ]
    }


def _wflow_plist() -> dict:
    return {
        "AMApplicationBuild": "523",
        "AMApplicationVersion": "2.10",
        "AMDocumentVersion": "2",
        "actions": [
            {
                "action": {
                    "AMAccepts": {
                        "Container": "List",
                        "Optional": True,
                        "Types": ["com.apple.cocoa.string"],
                    },
                    "AMActionVersion": "2.0.3",
                    "AMApplication": ["Automator"],
                    "AMParameterProperties": {
                        "COMMAND_STRING": {},
                        "CheckedForUserDefaultShell": {},
                        "inputMethod": {},
                        "shell": {},
                        "source": {},
                    },
                    "AMProvides": {
                        "Container": "List",
                        "Types": ["com.apple.cocoa.string"],
                    },
                    "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
                    "ActionName": "Run Shell Script",
                    "ActionParameters": {
                        "COMMAND_STRING": _shell_command(),
                        "CheckedForUserDefaultShell": True,
                        "inputMethod": 1,        # 1 = passar input como argumentos ($@)
                        "shell": "/bin/bash",
                        "source": "",
                    },
                    "BundleIdentifier": "com.apple.Automator.RunShellScript",
                    "CFBundleVersion": "2.0.3",
                    "CanShowSelectedItemsWhenRun": False,
                    "CanShowWhenRun": True,
                    "Category": ["AMCategoryUtilities"],
                    "Class Name": "RunShellScriptAction",
                    "InputUUID": "A1B2C3D4-0001-0001-0001-000000000001",
                    "Keywords": ["Shell"],
                    "OutputUUID": "A1B2C3D4-0001-0001-0001-000000000002",
                    "UUID": "A1B2C3D4-0001-0001-0001-000000000003",
                    "UnlocalizedApplications": ["Automator"],
                    "arguments": {},
                    "isViewVisible": 1,
                },
                "isViewVisible": 1,
            }
        ],
        "connectors": {},
        "workflowMetaData": {
            "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceProcessesInput": 0,
            "systemImageName": "NSActionTemplate",
            "useAutomaticInputType": 0,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }


def install() -> str:
    """Instala a Ação Rápida no Finder. Retorna mensagem de status."""
    if not _is_mac():
        return "Ação Rápida de botão-direito só existe no macOS."

    wf = _workflow_path()
    contents = os.path.join(wf, "Contents")
    os.makedirs(contents, exist_ok=True)

    with open(os.path.join(contents, "Info.plist"), "wb") as f:
        plistlib.dump(_info_plist(), f)
    with open(os.path.join(contents, "document.wflow"), "wb") as f:
        plistlib.dump(_wflow_plist(), f)

    # Pede pro sistema reindexar os serviços (sem isso às vezes demora a aparecer).
    try:
        subprocess.run(
            ["/System/Library/CoreServices/pbs", "-flush"],
            check=False, capture_output=True, timeout=10,
        )
    except Exception:
        pass

    return ("Ação Rápida instalada. No Finder: botão direito num .pdf → "
            "'Ações Rápidas' (ou 'Serviços') → 'Destravar PDF (Leitor Sereia)'. "
            "Se não aparecer na hora, pode levar alguns segundos ou exigir relogar.")


def uninstall() -> str:
    if not _is_mac():
        return "Nada a remover fora do macOS."
    wf = _workflow_path()
    if os.path.isdir(wf):
        shutil.rmtree(wf, ignore_errors=True)
    try:
        subprocess.run(
            ["/System/Library/CoreServices/pbs", "-flush"],
            check=False, capture_output=True, timeout=10,
        )
    except Exception:
        pass
    return "Ação Rápida removida."


def is_installed() -> bool:
    return _is_mac() and os.path.isdir(_workflow_path())
