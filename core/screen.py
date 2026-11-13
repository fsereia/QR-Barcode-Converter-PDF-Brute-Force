"""
screen.py — Captura de tela multiplataforma do Leitor Sereia.

No macOS usa a API moderna (Quartz / CoreGraphics), que:
  - é a forma suportada de capturar a tela nas versões atuais do macOS;
  - faz o sistema MOSTRAR o pedido de permissão de "Gravação de Tela" e
    adicionar o app à lista de Ajustes (a API antiga via `screencapture`
    muitas vezes só falhava calada);
  - lida com telas Retina (devolve a imagem em pixels reais).

Em Windows/Linux usa o PIL.ImageGrab.

Todas as funções devolvem um PIL.Image RGB, ou None se a captura falhou
(tipicamente permissão de Gravação de Tela ainda não concedida no Mac).
"""

from __future__ import annotations

import sys

from PIL import Image


def capture_fullscreen() -> "Image.Image | None":
    """Captura a tela principal inteira. None se não foi possível."""
    if sys.platform == "darwin":
        return _capture_quartz()
    return _capture_pil()


def capture_region(bbox: tuple[int, int, int, int]) -> "Image.Image | None":
    """Captura uma região (x0, y0, x1, y1) em PIXELS da tela principal."""
    if sys.platform == "darwin":
        full = _capture_quartz()
        if full is None:
            return None
        x0, y0, x1, y1 = bbox
        x0, x1 = sorted((max(0, x0), min(full.width, x1)))
        y0, y1 = sorted((max(0, y0), min(full.height, y1)))
        if x1 - x0 < 1 or y1 - y0 < 1:
            return None
        return full.crop((x0, y0, x1, y1))
    return _capture_pil(bbox)


# ---------------------------------------------------------------------------
# macOS (Quartz)
# ---------------------------------------------------------------------------

def _capture_quartz() -> "Image.Image | None":
    try:
        from Quartz import (
            CGMainDisplayID, CGDisplayCreateImage,
            CGImageGetWidth, CGImageGetHeight, CGImageGetBytesPerRow,
            CGImageGetDataProvider, CGDataProviderCopyData,
        )
        cg = CGDisplayCreateImage(CGMainDisplayID())
        if cg is None:
            return None
        w = CGImageGetWidth(cg)
        h = CGImageGetHeight(cg)
        bpr = CGImageGetBytesPerRow(cg)
        data = CGDataProviderCopyData(CGImageGetDataProvider(cg))
        buf = bytes(data)
        # A ordem de bytes do CoreGraphics é BGRA; 'bpr' cobre padding de linha.
        img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", bpr, 1)
        return img.convert("RGB")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Windows / Linux (PIL)
# ---------------------------------------------------------------------------

def _capture_pil(bbox=None) -> "Image.Image | None":
    try:
        from PIL import ImageGrab
        try:
            img = ImageGrab.grab(bbox=bbox, all_screens=True)
        except TypeError:
            img = ImageGrab.grab(bbox=bbox)
        return img.convert("RGB") if img is not None else None
    except Exception:
        return None
