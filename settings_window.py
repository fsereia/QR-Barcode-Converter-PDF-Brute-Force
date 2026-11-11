"""
settings_window.py — Janela (tkinter) pra cadastrar os CPFs/CNPJs por loja
e destravar PDFs (escolhendo o arquivo OU arrastando ele pra dentro da janela).

Pensada pra ser simples o bastante pro escritório usar: cada linha tem um
RÓTULO (ex.: "CNPJ Asics Londrina") e o NÚMERO. O app testa variações comuns
desses números ao destravar um PDF. Nada sai da máquina.

Arrastar-e-soltar: usa a extensão tkinterdnd2 quando ela está instalada. Se
não estiver, a janela continua funcionando normalmente — só sem a área de
arrastar; aí use o botão "Destravar um PDF agora…".
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core import config_store
from core import pdf_unlock


# ---------------------------------------------------------------------------
# Suporte opcional a arrastar-e-soltar (tkinterdnd2)
# ---------------------------------------------------------------------------

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _HAS_DND = True
except Exception:
    TkinterDnD = None
    DND_FILES = None
    _HAS_DND = False


def _make_root() -> tk.Tk:
    """Cria a janela raiz com suporte a arrastar-e-soltar, se disponível."""
    if _HAS_DND:
        return TkinterDnD.Tk()
    return tk.Tk()


def _parse_drop_paths(root: tk.Misc, raw: str) -> list[str]:
    """Converte o texto cru de um 'drop' numa lista de caminhos.

    O tkdnd entrega algo como '{/pasta com espaço/a.pdf} /b.pdf'. O splitlist
    do Tcl já cuida das chaves e dos espaços pra gente.
    """
    try:
        return [p for p in root.tk.splitlist(raw) if p]
    except Exception:
        return [raw.strip("{}")] if raw else []


# ---------------------------------------------------------------------------
# Destravar um PDF e mostrar o resultado
# ---------------------------------------------------------------------------

def _do_unlock(parent, cfg: config_store.Config, pdf_path: str, overwrite: bool):
    ids = cfg.as_identifier_objects()
    if not ids:
        messagebox.showwarning(
            "Sem identificadores",
            "Você ainda não cadastrou nenhum CPF/CNPJ.\n"
            "Cadastre os números das lojas/sócios antes de destravar.",
            parent=parent,
        )
        return

    if not pdf_path or not os.path.isfile(pdf_path):
        messagebox.showerror("Leitor Sereia", f"Arquivo não encontrado:\n{pdf_path}", parent=parent)
        return
    if not pdf_path.lower().endswith(".pdf"):
        if not messagebox.askyesno(
            "Não parece um PDF",
            f"O arquivo não termina em .pdf:\n{os.path.basename(pdf_path)}\n\nTentar mesmo assim?",
            parent=parent,
        ):
            return

    if overwrite:
        if not messagebox.askyesno(
            "Substituir o original?",
            f"Isto vai salvar a versão SEM senha POR CIMA do arquivo original:\n\n"
            f"{os.path.basename(pdf_path)}\n\n"
            f"A versão com senha deixa de existir. Continuar?",
            icon="warning", parent=parent,
        ):
            return

    res = pdf_unlock.unlock(pdf_path, ids, save_copy=cfg.save_unlocked_copy, overwrite=overwrite)
    if res.ok:
        if res.had_user_password:
            msg = (
                f"✅ Senha encontrada!\n\n"
                f"Loja/sócio: {res.identifier_label}\n"
                f"Regra: {res.rule}\n"
                f"(testou {res.tried} combinação(ões))\n"
            )
        else:
            msg = "✅ Este PDF não tinha senha de abertura (só permissões).\n"
        if res.saved_to:
            if res.overwritten:
                msg += f"\nOriginal substituído pela versão sem senha:\n{res.saved_to}"
            else:
                msg += f"\nCópia sem senha salva em:\n{res.saved_to}"
        messagebox.showinfo("Leitor Sereia — PDF destravado", msg, parent=parent)
    else:
        messagebox.showerror("Leitor Sereia — não consegui", res.error or "Falha desconhecida.",
                             parent=parent)


class SettingsWindow:
    def __init__(self, root: tk.Tk, cfg: config_store.Config):
        self.root = root
        self.cfg = cfg
        root.title("Leitor Sereia — CPFs/CNPJs das lojas")
        root.geometry("600x620")
        root.minsize(520, 520)

        header = ttk.Label(
            root,
            text="Cadastre os CPFs dos sócios e os CNPJs das lojas, com um rótulo claro.\n"
                 "Quando um PDF protegido abrir, o app te diz de qual loja ele é.",
            justify="left", padding=(12, 10),
        )
        header.pack(fill="x")

        # tabela
        cols = ("label", "value")
        self.tree = ttk.Treeview(root, columns=cols, show="headings", height=8)
        self.tree.heading("label", text="Rótulo (loja / sócio)")
        self.tree.heading("value", text="CPF / CNPJ")
        self.tree.column("label", width=320)
        self.tree.column("value", width=200)
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self._reload()

        # linha de adição
        addframe = ttk.Frame(root, padding=(12, 0))
        addframe.pack(fill="x")
        ttk.Label(addframe, text="Rótulo:").grid(row=0, column=0, sticky="w")
        self.e_label = ttk.Entry(addframe, width=28)
        self.e_label.grid(row=0, column=1, padx=4)
        ttk.Label(addframe, text="Número:").grid(row=0, column=2, sticky="w")
        self.e_value = ttk.Entry(addframe, width=20)
        self.e_value.grid(row=0, column=3, padx=4)
        ttk.Button(addframe, text="Adicionar", command=self._add).grid(row=0, column=4, padx=4)
        self.e_value.bind("<Return>", lambda _e: self._add())

        ttk.Button(root, text="Remover selecionado", command=self._remove).pack(
            anchor="w", padx=12, pady=(6, 4))

        ttk.Separator(root, orient="horizontal").pack(fill="x", padx=12, pady=6)

        # ---- área de destravar PDF ----
        unlock_area = ttk.LabelFrame(root, text="Destravar PDF", padding=12)
        unlock_area.pack(fill="x", padx=12, pady=(0, 8))

        self.overwrite_var = tk.BooleanVar(value=bool(cfg.overwrite_original))
        ttk.Checkbutton(
            unlock_area,
            text="Substituir o original (apaga a versão com senha)",
            variable=self.overwrite_var,
            command=self._on_toggle_overwrite,
        ).pack(anchor="w", pady=(0, 8))

        # zona de arrastar
        self.drop = tk.Label(
            unlock_area,
            text=("⬇  Arraste um PDF aqui para destravar\n(ou use o botão abaixo)"
                  if _HAS_DND else
                  "Arrastar-e-soltar indisponível — use o botão abaixo."),
            relief="groove", bd=2, padx=10, pady=22, justify="center",
            fg="#444", bg="#f2f2f2",
        )
        self.drop.pack(fill="x", pady=(0, 8))
        if _HAS_DND:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<Drop>>", self._on_drop)
            self.drop.dnd_bind("<<DragEnter>>", lambda _e: self.drop.config(bg="#dff0e2"))
            self.drop.dnd_bind("<<DragLeave>>", lambda _e: self.drop.config(bg="#f2f2f2"))

        ttk.Button(unlock_area, text="Escolher um PDF…",
                   command=self._pick_and_unlock).pack(anchor="w")

        # botão de baixo
        btns = ttk.Frame(root, padding=12)
        btns.pack(fill="x")
        ttk.Button(btns, text="Salvar e fechar", command=self._save_close).pack(side="right")

    # ---- tabela ----
    def _reload(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for d in self.cfg.identifiers:
            self.tree.insert("", "end", values=(d["label"], d["value"]))

    def _add(self):
        label = self.e_label.get().strip()
        value = self.e_value.get().strip()
        if not label or not value:
            messagebox.showwarning("Faltou dado", "Preencha rótulo e número.", parent=self.root)
            return
        self.cfg.add_identifier(label, value)
        config_store.save(self.cfg)
        self.e_label.delete(0, "end")
        self.e_value.delete(0, "end")
        self._reload()

    def _remove(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self.cfg.remove_identifier(idx)
        config_store.save(self.cfg)
        self._reload()

    # ---- destravar ----
    def _on_toggle_overwrite(self):
        self.cfg.overwrite_original = bool(self.overwrite_var.get())
        config_store.save(self.cfg)

    def _pick_and_unlock(self):
        path = filedialog.askopenfilename(
            title="Escolha o PDF protegido",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")],
        )
        if path:
            _do_unlock(self.root, self.cfg, path, self.overwrite_var.get())

    def _on_drop(self, event):
        self.drop.config(bg="#f2f2f2")
        paths = _parse_drop_paths(self.root, event.data)
        if not paths:
            return
        for p in paths:
            _do_unlock(self.root, self.cfg, p, self.overwrite_var.get())

    def _save_close(self):
        config_store.save(self.cfg)
        self.root.destroy()


def open_settings(cfg: config_store.Config | None = None):
    """Abre a janela de config de forma autônoma (bloqueante)."""
    if cfg is None:
        cfg = config_store.load()
    root = _make_root()
    SettingsWindow(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    open_settings()
