"""
history_window.py — Janela do histórico de leituras (QR / código de barras).

Lista o que já foi lido (texto, tipo e hora), deixa copiar qualquer linha com
um clique e limpar o histórico. A imagem do print nunca é guardada — só o texto.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from core import history


def _copy(text: str) -> None:
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        r = tk.Tk(); r.withdraw()
        r.clipboard_clear(); r.clipboard_append(text); r.update(); r.destroy()


class HistoryWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Leitor Sereia — Histórico de leituras")
        root.geometry("640x460")
        root.minsize(520, 360)

        ttk.Label(root, padding=(12, 10), justify="left",
                  text="Tudo que o leitor já converteu. Clique numa linha e em 'Copiar' "
                       "(ou dê duplo-clique) pra usar depois.").pack(fill="x")

        cols = ("ts", "type", "data")
        self.tree = ttk.Treeview(root, columns=cols, show="headings")
        self.tree.heading("ts", text="Quando")
        self.tree.heading("type", text="Tipo")
        self.tree.heading("data", text="Conteúdo lido")
        self.tree.column("ts", width=140, anchor="w")
        self.tree.column("type", width=160, anchor="w")
        self.tree.column("data", width=320, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        self.tree.bind("<Double-1>", lambda e: self._copy_selected())

        self._entries: list[dict] = []
        self._reload()

        btns = ttk.Frame(root, padding=12)
        btns.pack(fill="x")
        ttk.Button(btns, text="Copiar selecionado", command=self._copy_selected).pack(side="left")
        ttk.Button(btns, text="Atualizar", command=self._reload).pack(side="left", padx=8)
        ttk.Button(btns, text="Limpar histórico", command=self._clear).pack(side="left")
        ttk.Button(btns, text="Fechar", command=root.destroy).pack(side="right")

    def _reload(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._entries = list(reversed(history.load()))  # mais recente no topo
        for e in self._entries:
            data = e.get("data", "")
            preview = data if len(data) <= 80 else data[:77] + "…"
            self.tree.insert("", "end", values=(e.get("ts", ""), e.get("type", ""), preview))

    def _copy_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if 0 <= idx < len(self._entries):
            _copy(self._entries[idx].get("data", ""))

    def _clear(self):
        if messagebox.askyesno("Limpar histórico", "Apagar todo o histórico de leituras?",
                               parent=self.root):
            history.clear()
            self._reload()


def open_history():
    root = tk.Tk()
    HistoryWindow(root)
    root.mainloop()


if __name__ == "__main__":
    open_history()
