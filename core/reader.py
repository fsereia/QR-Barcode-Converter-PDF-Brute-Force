"""
reader.py — Núcleo de leitura de QR Code e código de barras do Leitor Sereia.

Lê a partir de uma imagem (print da tela, imagem colada, arquivo) tanto
QR Code quanto códigos de barras 1D (EAN-13/8, Code128, Code39, ITF —
inclusive o código de barras de boleto de 44 dígitos).

Usa pyzbar (lib zbar) pra decodificar e OpenCV pra uma cadeia de
pré-processamento: se a imagem crua não decodifica, tenta escala de cinza,
binarização, ampliação e inversão antes de desistir. Isso aumenta muito a
taxa de acerto em prints de tela e fotos tortas.

Depende de: pyzbar, opencv-python(-headless), pillow, numpy
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image
from pyzbar import pyzbar


@dataclass
class DecodeHit:
    type: str          # "QRCODE", "EAN13", "CODE128", "I25", ...
    data: str          # conteúdo decodificado (texto)
    friendly_type: str # nome amigável em PT


_FRIENDLY = {
    "QRCODE": "QR Code",
    "EAN13": "Código de barras EAN-13",
    "EAN8": "Código de barras EAN-8",
    "UPCA": "Código de barras UPC-A",
    "UPCE": "Código de barras UPC-E",
    "CODE128": "Código de barras Code 128",
    "CODE39": "Código de barras Code 39",
    "CODE93": "Código de barras Code 93",
    "I25": "Código de barras (boleto / ITF)",
    "ITF": "Código de barras (boleto / ITF)",
    "CODABAR": "Código de barras Codabar",
    "PDF417": "PDF417",
    "DATABAR": "GS1 DataBar",
}


def _friendly(t: str) -> str:
    return _FRIENDLY.get(t.upper(), f"Código ({t})")


def _pil_to_cv(img: Image.Image) -> np.ndarray:
    """PIL -> ndarray (grayscale uint8)."""
    if img.mode != "L":
        img = img.convert("L")
    return np.array(img)


def _decode_raw(gray: np.ndarray) -> list[DecodeHit]:
    hits: list[DecodeHit] = []
    for sym in pyzbar.decode(gray):
        try:
            data = sym.data.decode("utf-8")
        except UnicodeDecodeError:
            data = sym.data.decode("latin-1", errors="replace")
        hits.append(DecodeHit(type=sym.type, data=data, friendly_type=_friendly(sym.type)))
    return hits


def _preprocess_variants(gray: np.ndarray):
    """Gera variações da imagem pra tentar decodificar (cadeia de fallback)."""
    import cv2  # import tardio: só quando realmente decodifica

    yield gray  # 1) crua (em cinza)

    # 2) Otsu (binarização automática) — ótimo p/ prints com fundo claro
    try:
        _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        yield otsu
    except cv2.error:
        pass

    # 3) ampliada 2x — ajuda códigos pequenos em prints de tela
    try:
        big = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        yield big
        _, big_otsu = cv2.threshold(big, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        yield big_otsu
    except cv2.error:
        pass

    # 4) threshold adaptativo — p/ iluminação irregular (foto de papel)
    try:
        adap = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 31, 10)
        yield adap
    except cv2.error:
        pass

    # 5) invertida — p/ código claro em fundo escuro
    yield cv2.bitwise_not(gray)


def decode_image(img: Image.Image) -> list[DecodeHit]:
    """
    Decodifica QR/barras de uma imagem PIL. Retorna todos os códigos
    encontrados (deduplicados por type+data). Lista vazia = nada encontrado.
    """
    gray = _pil_to_cv(img)
    found: dict[tuple[str, str], DecodeHit] = {}

    for variant in _preprocess_variants(gray):
        for hit in _decode_raw(variant):
            found[(hit.type, hit.data)] = hit
        if found:
            # achou em alguma variante; não precisa esgotar as mais pesadas
            break

    return list(found.values())


def decode_file(path: str) -> list[DecodeHit]:
    with Image.open(path) as im:
        return decode_image(im.copy())


def best_text(hits: list[DecodeHit]) -> str:
    """Junta o conteúdo de todos os códigos achados em texto pronto pro clipboard."""
    if not hits:
        return ""
    if len(hits) == 1:
        return hits[0].data
    return "\n".join(h.data for h in hits)
