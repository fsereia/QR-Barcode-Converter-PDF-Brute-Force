"""
config_store.py — Configuração local do Leitor Sereia.

Guarda, SÓ NA MÁQUINA do usuário, a lista de identificadores (CPFs dos
sócios / CNPJs das lojas) rotulados por loja, mais algumas preferências.
Nada daqui é transmitido pra lugar nenhum.

Local do arquivo:
  Windows: %APPDATA%\\LeitorSereia\\config.json
  macOS:   ~/Library/Application Support/LeitorSereia/config.json
  Linux:   ~/.config/LeitorSereia/config.json
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, asdict, field


APP_DIRNAME = "LeitorSereia"
DEFAULT_HOTKEY = "ctrl+shift+q"          # ler a tela inteira (rápido)
DEFAULT_HOTKEY_REGION = "ctrl+shift+4"  # recortar área da tela (estilo Mac Cmd+Shift+4)


def config_dir() -> str:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    d = os.path.join(base, APP_DIRNAME)
    os.makedirs(d, exist_ok=True)
    return d


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


@dataclass
class Config:
    identifiers: list[dict] = field(default_factory=list)   # [{"label":..,"value":..}]
    hotkey: str = DEFAULT_HOTKEY                 # ler tela inteira
    hotkey_region: str = DEFAULT_HOTKEY_REGION   # recortar área
    save_unlocked_copy: bool = True

    # ---- identifiers ----
    def add_identifier(self, label: str, value: str) -> None:
        label, value = label.strip(), value.strip()
        if not label or not value:
            return
        self.identifiers.append({"label": label, "value": value})

    def remove_identifier(self, index: int) -> None:
        if 0 <= index < len(self.identifiers):
            self.identifiers.pop(index)

    def as_identifier_objects(self):
        # importação tardia pra evitar ciclo
        from .pdf_unlock import Identifier
        return [Identifier(d["label"], d["value"]) for d in self.identifiers]


def load() -> Config:
    path = config_path()
    if not os.path.exists(path):
        return Config()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Config(
            identifiers=data.get("identifiers", []),
            hotkey=data.get("hotkey", DEFAULT_HOTKEY),
            hotkey_region=data.get("hotkey_region", DEFAULT_HOTKEY_REGION),
            save_unlocked_copy=bool(data.get("save_unlocked_copy", True)),
        )
    except (json.JSONDecodeError, OSError):
        # config corrompida: não derruba o app, começa limpo (mas preserva backup)
        try:
            os.replace(path, path + ".corrompido")
        except OSError:
            pass
        return Config()


def save(cfg: Config) -> None:
    path = config_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(asdict(cfg), f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    # permissão restrita quando o SO permite (Unix)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
