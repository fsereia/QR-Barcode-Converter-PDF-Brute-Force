"""
history.py — Histórico local de leituras (QR / código de barras).

Guarda SÓ O TEXTO lido (a imagem do print é descartada), com data/hora e
tipo, pra você copiar e colar depois. Fica na mesma pasta de config, local.

Limite padrão: 200 entradas (as mais antigas caem fora).
"""

from __future__ import annotations

import json
import os
from datetime import datetime

from .config_store import config_dir

HISTORY_LIMIT = 200


def _history_path() -> str:
    return os.path.join(config_dir(), "history.json")


def load() -> list[dict]:
    path = _history_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list[dict]) -> None:
    path = _history_path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries[-HISTORY_LIMIT:], f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def add(data: str, friendly_type: str, raw_type: str = "") -> None:
    """Adiciona uma leitura ao histórico (ignora duplicata imediata)."""
    if not data:
        return
    entries = load()
    if entries and entries[-1].get("data") == data:
        return  # mesma leitura repetida em sequência: não duplica
    entries.append({
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": friendly_type,
        "raw_type": raw_type,
        "data": data,
    })
    _save(entries)


def add_many(hits) -> None:
    """Adiciona vários DecodeHit de uma vez."""
    for h in hits:
        add(h.data, h.friendly_type, getattr(h, "type", ""))


def clear() -> None:
    _save([])
