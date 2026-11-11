"""
pdf_unlock.py — Núcleo de destravar PDF do Leitor Sereia.

Faz DUAS coisas, usando apenas os identificadores que o próprio usuário
cadastrou localmente (CPFs dos sócios / CNPJs das lojas):

  1. Descobre qual senha abre um PDF protegido -> e com isso identifica
     de qual loja/sócio o documento é (porque cada identificador tem rótulo).
  2. Salva uma cópia do PDF SEM senha (nunca sobrescreve o original).

Nenhum dado sai da máquina. Isto NÃO quebra criptografia: apenas testa
senhas conhecidas do próprio dono, exatamente como ele faria à mão.

Depende de: pikepdf
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Iterable

import pikepdf


# ---------------------------------------------------------------------------
# Geração de candidatos de senha a partir de um identificador (CPF/CNPJ)
# ---------------------------------------------------------------------------

def _only_digits(s: str) -> str:
    return re.sub(r"\D", "", s or "")


def _format_cpf(d: str) -> str:
    return f"{d[0:3]}.{d[3:6]}.{d[6:9]}-{d[9:11]}"


def _format_cnpj(d: str) -> str:
    return f"{d[0:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


def password_variations(raw_value: str) -> list[tuple[str, str]]:
    """
    Recebe um identificador cru (CPF, CNPJ, ou qualquer string) e devolve
    uma lista de (senha_candidata, descrição_da_regra), já deduplicada e
    ordenada das convenções mais comuns pras menos comuns.

    A descrição é o que deixa o resultado útil: quando a senha bate, o app
    diz tanto a LOJA (pelo rótulo do identificador) quanto a REGRA usada
    (ex.: "5 primeiros do CPF"), pra você aprender o padrão de cada fornecedor.
    """
    d = _only_digits(raw_value)
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(pw: str, desc: str) -> None:
        if pw and pw not in seen:
            seen.add(pw)
            out.append((pw, desc))

    # Sempre vale tentar o valor exato que a pessoa digitou (pode ser uma
    # senha custom de fornecedor, não um CPF/CNPJ).
    if raw_value and raw_value.strip():
        add(raw_value.strip(), "valor exato cadastrado")

    if len(d) == 11:  # CPF
        add(d[0:5], "5 primeiros do CPF")
        add(d, "CPF completo (11 dígitos)")
        add(d[0:6], "6 primeiros do CPF")
        add(_format_cpf(d), "CPF formatado")
        add(d[0:3], "3 primeiros do CPF")
        add(d[-4:], "4 últimos do CPF")
        add(d[-2:], "2 últimos do CPF (dígito verificador)")
    elif len(d) == 14:  # CNPJ
        add(d[0:8], "raiz do CNPJ (8 primeiros)")
        add(d, "CNPJ completo (14 dígitos)")
        add(d[0:5], "5 primeiros do CNPJ")
        add(d[0:6], "6 primeiros do CNPJ")
        add(_format_cnpj(d), "CNPJ formatado")
        add(d[0:4], "4 primeiros do CNPJ")
        add(d[-6:], "6 últimos do CNPJ (filial+DV)")
        add(d[-4:], "4 últimos do CNPJ")
    elif d:
        # Número de tamanho não-padrão: tenta ele inteiro e os 5/6 primeiros.
        add(d, "número completo cadastrado")
        add(d[0:5], "5 primeiros")
        add(d[0:6], "6 primeiros")

    return out


# ---------------------------------------------------------------------------
# Identificadores cadastrados pelo usuário
# ---------------------------------------------------------------------------

@dataclass
class Identifier:
    """Um CPF/CNPJ (ou senha custom) cadastrado, com rótulo da loja/sócio."""
    label: str          # ex.: "CNPJ Asics Londrina", "CPF Felippe"
    value: str          # o número cru


@dataclass
class UnlockResult:
    ok: bool
    pdf_path: str
    password: str | None = None
    identifier_label: str | None = None      # qual loja/sócio
    rule: str | None = None                  # qual regra bateu
    saved_to: str | None = None              # cópia sem senha
    had_user_password: bool = True
    tried: int = 0
    error: str | None = None


def _candidate_list(identifiers: Iterable[Identifier]) -> list[tuple[str, str, str]]:
    """Expande todos os identificadores em (senha, rótulo, regra), deduplicando
    por senha mas preservando a primeira origem (rótulo+regra)."""
    seen: set[str] = set()
    result: list[tuple[str, str, str]] = []
    for ident in identifiers:
        for pw, rule in password_variations(ident.value):
            if pw not in seen:
                seen.add(pw)
                result.append((pw, ident.label, rule))
    return result


def find_password(pdf_path: str, identifiers: Iterable[Identifier]) -> UnlockResult:
    """
    Testa a senha vazia e depois cada candidato derivado dos identificadores.
    Retorna no primeiro que abrir o PDF.
    """
    identifiers = list(identifiers)

    # 1) Sem senha de abertura? (pode ter só senha de permissões)
    try:
        with pikepdf.open(pdf_path):
            return UnlockResult(
                ok=True, pdf_path=pdf_path, password="",
                identifier_label=None, rule="sem senha de abertura",
                had_user_password=False, tried=0,
            )
    except pikepdf.PasswordError:
        pass
    except Exception as e:  # arquivo corrompido, não é PDF, etc.
        return UnlockResult(ok=False, pdf_path=pdf_path, error=f"Não consegui abrir o arquivo: {e}")

    # 2) Testa candidatos
    candidates = _candidate_list(identifiers)
    tried = 0
    for pw, label, rule in candidates:
        tried += 1
        try:
            with pikepdf.open(pdf_path, password=pw):
                return UnlockResult(
                    ok=True, pdf_path=pdf_path, password=pw,
                    identifier_label=label, rule=rule,
                    had_user_password=True, tried=tried,
                )
        except pikepdf.PasswordError:
            continue
        except Exception as e:
            return UnlockResult(ok=False, pdf_path=pdf_path, tried=tried,
                                error=f"Erro ao testar senha: {e}")

    return UnlockResult(
        ok=False, pdf_path=pdf_path, tried=tried,
        error="Nenhum CPF/CNPJ cadastrado abriu este PDF. "
              "Confira se o identificador da loja certa está cadastrado.",
    )


def _unlocked_output_path(pdf_path: str) -> str:
    base, ext = os.path.splitext(pdf_path)
    candidate = f"{base}_sem_senha{ext or '.pdf'}"
    i = 2
    while os.path.exists(candidate):
        candidate = f"{base}_sem_senha_{i}{ext or '.pdf'}"
        i += 1
    return candidate


def save_without_password(pdf_path: str, password: str, out_path: str | None = None) -> str:
    """
    Abre com a senha correta e salva uma cópia SEM criptografia.
    Nunca sobrescreve o original: cria <nome>_sem_senha.pdf.
    Retorna o caminho salvo.
    """
    if out_path is None:
        out_path = _unlocked_output_path(pdf_path)
    with pikepdf.open(pdf_path, password=password or "") as pdf:
        # save() sem encryption= remove qualquer proteção.
        pdf.save(out_path)
    return out_path


def unlock(pdf_path: str, identifiers: Iterable[Identifier], save_copy: bool = True) -> UnlockResult:
    """Fluxo completo: acha a senha e (opcional) salva cópia sem senha."""
    res = find_password(pdf_path, identifiers)
    if res.ok and save_copy:
        try:
            res.saved_to = save_without_password(pdf_path, res.password or "")
        except Exception as e:
            res.error = f"Achei a senha mas falhei ao salvar a cópia: {e}"
    return res
