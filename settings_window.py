"""
settings_window.py — Janela (tkinter) pra cadastrar os CPFs/CNPJs por loja.

Pensada pra ser simples o bastante pro escritório usar: cada linha tem um
RÓTULO (ex.: "CNPJ Asics Londrina") e o NÚMERO. O app testa variações comuns
desses números ao destravar um PDF. Nada sai da máquina.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core import config_store
from core import pdf_unlock


def _run_unlock_dialog(parent, cfg: config_store.Config, pdf_path: str | None = None):
    """Abre um PDF (ou usa o caminho dado), destrava e mostra o resultado."""
    if pdf_path is None:
        pdf_path = filedialog.askopenfilename(
            title="Escolha o PDF protegido",
            filetypes=[("PDF", "*.pdf"), ("Todos", "*.*")],
        )
    if not pdf_path:
        return

    ids = cfg.as_identifier_objects()
    if not ids:
        messagebox.showwarning(
            "Sem identificadores",
            "Você ainda não cadastrou nenhum CPF/CNPJ.\n"
            "Cadastre os números das lojas/sócios antes de destravar.",
            parent=parent,
        )
        return

    res = pdf_unlock.unlock(pdf_path, ids, save_copy=cfg.save_unlocked_copy)
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
        root.geometry("560x460")
        root.minsize(480, 380)

        header = ttk.Label(
            root,
            text="Cadastre os CPFs dos sócios e os CNPJs das lojas, com um rótulo claro.\n"
                 "Quando um PDF protegido abrir, o app te diz de qual loja ele é.",
            justify="left", padding=(12, 10),
        )
        header.pack(fill="x")

        # tabela
        cols = ("label", "value")
        self.tree = ttk.Treeview(root, columns=cols, show="headings", height=10)
        self.tree.heading("label", text="Rótulo (loja / sócio)")
        self.tree.heading("value", text="CPF / CNPJ")
        self.tree.column("label", width=300)
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

        # botões de baixo
        btns = ttk.Frame(root, padding=12)
        btns.pack(fill="x")
        ttk.Button(btns, text="Remover selecionado", command=self._remove).pack(side="left")
        ttk.Button(btns, text="Destravar um PDF agora…",
                   command=lambda: _run_unlock_dialog(root, self.cfg)).pack(side="left", padx=8)
        ttk.Button(btns, text="Salvar e fechar", command=self._save_close).pack(side="right")

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
        self.e_label.delete(0, "end")
        self.e_value.delete(0, "end")
        self._reload()

    def _remove(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        self.cfg.remove_identifier(idx)
        self._reload()

    def _save_close(self):
        config_store.save(self.cfg)
        self.root.destroy()


def open_settings(cfg: config_store.Config | None = None):
    """Abre a janela de config de forma autônoma (bloqueante)."""
    if cfg is None:
        cfg = config_store.load()
    root = tk.Tk()
    SettingsWindow(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    open_settings()
