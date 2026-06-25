import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime


class CaixaSupermercado:
    def __init__(self, root):
        self.root = root
        self.root.title("Caixa - Supermercado")
        self.root.geometry("950x650")
        self.root.minsize(850, 600)
        self.root.configure(bg="#fff0f5")

        # Lista de itens da venda atual: cada item é um dict
        self.itens = []
        self.contador_item = 0

        self._configurar_estilos()
        self._montar_interface()
        self._atualizar_totais()

        # Atalhos de teclado
        self.root.bind("<F2>", lambda e: self.entry_codigo.focus_set())
        self.root.bind("<F4>", lambda e: self.finalizar_venda())
        self.root.bind("<F8>", lambda e: self.cancelar_venda())

    # ------------------------------------------------------------------
    # ESTILO
    # ------------------------------------------------------------------
    def _configurar_estilos(self):
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass

        estilo.configure("Titulo.TLabel", font=("Segoe UI", 18, "bold"),
                          background="#880e4f", foreground="white")
        estilo.configure("Sub.TLabel", font=("Segoe UI", 10),
                          background="#880e4f", foreground="#f8bbd0")
        estilo.configure("Campo.TLabel", font=("Segoe UI", 10, "bold"),
                          background="#fff0f5")
        estilo.configure("Total.TLabel", font=("Segoe UI", 22, "bold"),
                          background="#fff0f5", foreground="#d6336c")
        estilo.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        estilo.configure("Acao.TButton", font=("Segoe UI", 10, "bold"), padding=8)

    # ------------------------------------------------------------------
    # INTERFACE
    # ------------------------------------------------------------------
    def _montar_interface(self):
        # ----- Cabeçalho -----
        cabecalho = tk.Frame(self.root, bg="#880e4f", height=70)
        cabecalho.pack(fill="x")
        ttk.Label(cabecalho, text="🛒 Caixa do Supermercado", style="Titulo.TLabel").pack(
            side="left", padx=20, pady=15)
        self.lbl_data_hora = ttk.Label(cabecalho, text="", style="Sub.TLabel")
        self.lbl_data_hora.pack(side="right", padx=20)
        self._atualizar_relogio()

        # ----- Corpo principal (dividido em 2 colunas) -----
        corpo = tk.Frame(self.root, bg="#fff0f5")
        corpo.pack(fill="both", expand=True, padx=15, pady=10)
        corpo.columnconfigure(0, weight=3)
        corpo.columnconfigure(1, weight=1)
        corpo.rowconfigure(0, weight=1)

        # ===== Coluna esquerda: entrada de produtos + tabela =====
        esquerda = tk.Frame(corpo, bg="#fff0f5")
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # --- Formulário de inclusão de item ---
        form = tk.LabelFrame(esquerda, text="Adicionar Produto", bg="#ffffff",
                              font=("Segoe UI", 10, "bold"), padx=10, pady=10)
        form.pack(fill="x", pady=(0, 10))

        for c in range(6):
            form.columnconfigure(c, weight=1)

        ttk.Label(form, text="Código:", style="Campo.TLabel", background="#ffffff").grid(
            row=0, column=0, sticky="w")
        self.entry_codigo = tk.Entry(form, font=("Segoe UI", 11))
        self.entry_codigo.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Nome do produto:", style="Campo.TLabel", background="#ffffff").grid(
            row=0, column=1, sticky="w")
        self.entry_nome = tk.Entry(form, font=("Segoe UI", 11))
        self.entry_nome.grid(row=1, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Preço (R$):", style="Campo.TLabel", background="#ffffff").grid(
            row=0, column=2, sticky="w")
        self.entry_preco = tk.Entry(form, font=("Segoe UI", 11))
        self.entry_preco.grid(row=1, column=2, sticky="ew", padx=(0, 8))

        ttk.Label(form, text="Qtd.:", style="Campo.TLabel", background="#ffffff").grid(
            row=0, column=3, sticky="w")
        self.entry_qtd = tk.Entry(form, font=("Segoe UI", 11))
        self.entry_qtd.insert(0, "1")
        self.entry_qtd.grid(row=1, column=3, sticky="ew", padx=(0, 8))

        btn_add = tk.Button(form, text="➕ Adicionar (Enter)", bg="#d6336c", fg="white",
                             font=("Segoe UI", 10, "bold"), relief="flat",
                             command=self.adicionar_item, cursor="hand2")
        btn_add.grid(row=1, column=4, sticky="ew", padx=(0, 8))

        btn_limpar_campos = tk.Button(form, text="Limpar campos", bg="#f48fb1", fg="white",
                                       font=("Segoe UI", 10), relief="flat",
                                       command=self._limpar_campos_produto, cursor="hand2")
        btn_limpar_campos.grid(row=1, column=5, sticky="ew")

        # Enter em qualquer campo do formulário adiciona o item
        for campo in (self.entry_codigo, self.entry_nome, self.entry_preco, self.entry_qtd):
            campo.bind("<Return>", lambda e: self.adicionar_item())

        # --- Tabela de itens (carrinho) ---
        tabela_frame = tk.LabelFrame(esquerda, text="Itens da Compra", bg="#ffffff",
                                      font=("Segoe UI", 10, "bold"), padx=5, pady=5)
        tabela_frame.pack(fill="both", expand=True)

        colunas = ("codigo", "nome", "preco", "qtd", "subtotal")
        self.tabela = ttk.Treeview(tabela_frame, columns=colunas, show="headings",
                                    selectmode="browse")
        self.tabela.heading("codigo", text="Código")
        self.tabela.heading("nome", text="Produto")
        self.tabela.heading("preco", text="Preço Unit.")
        self.tabela.heading("qtd", text="Qtd.")
        self.tabela.heading("subtotal", text="Subtotal")

        self.tabela.column("codigo", width=80, anchor="center")
        self.tabela.column("nome", width=260, anchor="w")
        self.tabela.column("preco", width=100, anchor="e")
        self.tabela.column("qtd", width=60, anchor="center")
        self.tabela.column("subtotal", width=110, anchor="e")

        scroll = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll.set)
        self.tabela.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # Duplo clique remove o item selecionado
        self.tabela.bind("<Double-1>", lambda e: self.remover_item_selecionado())

        btn_remover = tk.Button(esquerda, text="🗑️ Remover item selecionado (duplo clique na tabela)",
                                 bg="#ad1457", fg="white", font=("Segoe UI", 9, "bold"),
                                 relief="flat", command=self.remover_item_selecionado,
                                 cursor="hand2")
        btn_remover.pack(fill="x", pady=(8, 0))

        # ===== Coluna direita: totais, desconto e pagamento =====
        direita = tk.Frame(corpo, bg="#fff0f5")
        direita.grid(row=0, column=1, sticky="nsew")

        resumo = tk.LabelFrame(direita, text="Resumo da Venda", bg="#ffffff",
                                font=("Segoe UI", 10, "bold"), padx=12, pady=12)
        resumo.pack(fill="x")

        ttk.Label(resumo, text="Quantidade de itens:", background="#ffffff",
                  font=("Segoe UI", 10)).pack(anchor="w")
        self.lbl_qtd_itens = tk.Label(resumo, text="0", bg="#ffffff",
                                       font=("Segoe UI", 14, "bold"))
        self.lbl_qtd_itens.pack(anchor="w", pady=(0, 10))

        ttk.Label(resumo, text="Subtotal:", background="#ffffff",
                  font=("Segoe UI", 10)).pack(anchor="w")
        self.lbl_subtotal = tk.Label(resumo, text="R$ 0,00", bg="#ffffff",
                                      font=("Segoe UI", 14, "bold"))
        self.lbl_subtotal.pack(anchor="w", pady=(0, 10))

        # --- Desconto ---
        desconto_frame = tk.LabelFrame(direita, text="Desconto", bg="#ffffff",
                                        font=("Segoe UI", 10, "bold"), padx=12, pady=12)
        desconto_frame.pack(fill="x", pady=10)

        self.tipo_desconto = tk.StringVar(value="valor")
        linha_radio = tk.Frame(desconto_frame, bg="#ffffff")
        linha_radio.pack(fill="x")
        tk.Radiobutton(linha_radio, text="R$", variable=self.tipo_desconto, value="valor",
                        bg="#ffffff", command=self._atualizar_totais).pack(side="left")
        tk.Radiobutton(linha_radio, text="%", variable=self.tipo_desconto, value="percentual",
                        bg="#ffffff", command=self._atualizar_totais).pack(side="left")

        self.entry_desconto = tk.Entry(desconto_frame, font=("Segoe UI", 11))
        self.entry_desconto.insert(0, "0")
        self.entry_desconto.pack(fill="x", pady=(6, 0))
        self.entry_desconto.bind("<KeyRelease>", lambda e: self._atualizar_totais())

        # --- Total ---
        total_frame = tk.Frame(direita, bg="#fff0f5")
        total_frame.pack(fill="x", pady=10)
        ttk.Label(total_frame, text="TOTAL A PAGAR", style="Campo.TLabel").pack(anchor="w")
        self.lbl_total = ttk.Label(total_frame, text="R$ 0,00", style="Total.TLabel")
        self.lbl_total.pack(anchor="w")

        # --- Pagamento ---
        pagamento_frame = tk.LabelFrame(direita, text="Pagamento", bg="#ffffff",
                                         font=("Segoe UI", 10, "bold"), padx=12, pady=12)
        pagamento_frame.pack(fill="x")

        self.forma_pagamento = tk.StringVar(value="Dinheiro")
        combo_pagamento = ttk.Combobox(pagamento_frame, textvariable=self.forma_pagamento,
                                        values=["Dinheiro", "Cartão de Débito",
                                                "Cartão de Crédito", "Pix"],
                                        state="readonly", font=("Segoe UI", 10))
        combo_pagamento.pack(fill="x")
        combo_pagamento.bind("<<ComboboxSelected>>", lambda e: self._atualizar_campo_troco())

        ttk.Label(pagamento_frame, text="Valor recebido (R$):", background="#ffffff",
                  font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))
        self.entry_recebido = tk.Entry(pagamento_frame, font=("Segoe UI", 11))
        self.entry_recebido.pack(fill="x")
        self.entry_recebido.bind("<KeyRelease>", lambda e: self._atualizar_troco())

        ttk.Label(pagamento_frame, text="Troco:", background="#ffffff",
                  font=("Segoe UI", 10)).pack(anchor="w", pady=(10, 0))
        self.lbl_troco = tk.Label(pagamento_frame, text="R$ 0,00", bg="#ffffff",
                                   font=("Segoe UI", 13, "bold"), fg="#c2185b")
        self.lbl_troco.pack(anchor="w")

        # --- Botões de ação ---
        acoes_frame = tk.Frame(direita, bg="#fff0f5")
        acoes_frame.pack(fill="x", pady=15)

        tk.Button(acoes_frame, text="✅ Finalizar Venda (F4)", bg="#d6336c", fg="white",
                   font=("Segoe UI", 11, "bold"), relief="flat", height=2,
                   command=self.finalizar_venda, cursor="hand2").pack(fill="x", pady=(0, 8))

        tk.Button(acoes_frame, text="✖ Cancelar Venda (F8)", bg="#880e4f", fg="white",
                   font=("Segoe UI", 10, "bold"), relief="flat",
                   command=self.cancelar_venda, cursor="hand2").pack(fill="x")

        # Status bar
        self.status = tk.Label(self.root, text="Pronto. F2: focar código | F4: finalizar | F8: cancelar",
                                bg="#fce4ec", anchor="w", font=("Segoe UI", 9), padx=10)
        self.status.pack(fill="x", side="bottom")

        self.entry_codigo.focus_set()

    # ------------------------------------------------------------------
    # RELÓGIO
    # ------------------------------------------------------------------
    def _atualizar_relogio(self):
        agora = datetime.now().strftime("%d/%m/%Y  %H:%M:%S")
        self.lbl_data_hora.configure(text=agora)
        self.root.after(1000, self._atualizar_relogio)

    # ------------------------------------------------------------------
    # AÇÕES DE PRODUTO
    # ------------------------------------------------------------------
    def adicionar_item(self):
        codigo = self.entry_codigo.get().strip()
        nome = self.entry_nome.get().strip()
        preco_txt = self.entry_preco.get().strip().replace(",", ".")
        qtd_txt = self.entry_qtd.get().strip().replace(",", ".")

        if not nome:
            messagebox.showwarning("Campo obrigatório", "Informe o nome do produto.")
            self.entry_nome.focus_set()
            return

        try:
            preco = float(preco_txt)
            if preco <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Preço inválido", "Informe um preço válido, maior que zero.\nEx.: 4.99")
            self.entry_preco.focus_set()
            return

        try:
            qtd = float(qtd_txt)
            if qtd <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Quantidade inválida", "Informe uma quantidade válida, maior que zero.")
            self.entry_qtd.focus_set()
            return

        if not codigo:
            self.contador_item += 1
            codigo = f"AVU-{self.contador_item:03d}"  # código avulso automático

        subtotal = preco * qtd
        item_id = self.tabela.insert("", "end", values=(
            codigo, nome, self._fmt_moeda(preco), self._fmt_qtd(qtd), self._fmt_moeda(subtotal)
        ))
        self.itens.append({
            "id": item_id, "codigo": codigo, "nome": nome,
            "preco": preco, "qtd": qtd, "subtotal": subtotal
        })

        self._limpar_campos_produto()
        self._atualizar_totais()
        self.status.configure(text=f"Item '{nome}' adicionado.")
        self.entry_codigo.focus_set()

    def remover_item_selecionado(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showinfo("Nenhum item selecionado", "Selecione um item na tabela para remover.")
            return
        item_id = selecionado[0]
        self.itens = [i for i in self.itens if i["id"] != item_id]
        self.tabela.delete(item_id)
        self._atualizar_totais()
        self.status.configure(text="Item removido.")

    def _limpar_campos_produto(self):
        self.entry_codigo.delete(0, "end")
        self.entry_nome.delete(0, "end")
        self.entry_preco.delete(0, "end")
        self.entry_qtd.delete(0, "end")
        self.entry_qtd.insert(0, "1")

    # ------------------------------------------------------------------
    # TOTAIS / DESCONTO / TROCO
    # ------------------------------------------------------------------
    def _calcular_subtotal(self):
        return sum(i["subtotal"] for i in self.itens)

    def _calcular_desconto(self, subtotal):
        try:
            valor = float(self.entry_desconto.get().strip().replace(",", "."))
        except ValueError:
            valor = 0.0
        if valor < 0:
            valor = 0.0

        if self.tipo_desconto.get() == "percentual":
            valor = min(valor, 100)
            return subtotal * (valor / 100)
        else:
            return min(valor, subtotal)

    def _atualizar_totais(self):
        subtotal = self._calcular_subtotal()
        desconto = self._calcular_desconto(subtotal)
        total = max(subtotal - desconto, 0)

        self.lbl_qtd_itens.configure(text=str(len(self.itens)))
        self.lbl_subtotal.configure(text=self._fmt_moeda(subtotal))
        self.lbl_total.configure(text=self._fmt_moeda(total))

        self._atualizar_troco()

    def _atualizar_campo_troco(self):
        if self.forma_pagamento.get() != "Dinheiro":
            self.entry_recebido.delete(0, "end")
            self.entry_recebido.configure(state="disabled")
        else:
            self.entry_recebido.configure(state="normal")
        self._atualizar_troco()

    def _atualizar_troco(self):
        total_txt = self.lbl_total.cget("text")
        total = self._parse_moeda(total_txt)

        if self.forma_pagamento.get() != "Dinheiro":
            self.lbl_troco.configure(text="—")
            return

        try:
            recebido = float(self.entry_recebido.get().strip().replace(",", "."))
        except ValueError:
            recebido = 0.0

        troco = recebido - total
        if troco < 0:
            self.lbl_troco.configure(text="Valor insuficiente", fg="#880e4f")
        else:
            self.lbl_troco.configure(text=self._fmt_moeda(troco), fg="#c2185b")

    # ------------------------------------------------------------------
    # FINALIZAR / CANCELAR
    # ------------------------------------------------------------------
    def finalizar_venda(self):
        if not self.itens:
            messagebox.showwarning("Venda vazia", "Adicione ao menos um produto antes de finalizar a venda.")
            return

        total = self._parse_moeda(self.lbl_total.cget("text"))

        if self.forma_pagamento.get() == "Dinheiro":
            try:
                recebido = float(self.entry_recebido.get().strip().replace(",", "."))
            except ValueError:
                recebido = -1
            if recebido < total:
                messagebox.showwarning("Pagamento insuficiente",
                                        "O valor recebido em dinheiro é menor que o total da compra.")
                return
            troco_msg = f"\nTroco: {self.lbl_troco.cget('text')}"
        else:
            troco_msg = ""

        resumo = (
            f"Venda finalizada com sucesso!\n\n"
            f"Itens: {len(self.itens)}\n"
            f"Total: {self.lbl_total.cget('text')}\n"
            f"Forma de pagamento: {self.forma_pagamento.get()}"
            f"{troco_msg}"
        )
        messagebox.showinfo("Venda finalizada", resumo)
        self._nova_venda()

    def cancelar_venda(self):
        if not self.itens:
            return
        if messagebox.askyesno("Cancelar venda", "Tem certeza que deseja cancelar a venda atual?\nTodos os itens serão removidos."):
            self._nova_venda()
            self.status.configure(text="Venda cancelada.")

    def _nova_venda(self):
        self.itens.clear()
        for linha in self.tabela.get_children():
            self.tabela.delete(linha)
        self.entry_desconto.delete(0, "end")
        self.entry_desconto.insert(0, "0")
        self.entry_recebido.configure(state="normal")
        self.entry_recebido.delete(0, "end")
        self.forma_pagamento.set("Dinheiro")
        self._limpar_campos_produto()
        self._atualizar_totais()
        self.entry_codigo.focus_set()
        self.status.configure(text="Pronto para uma nova venda.")

    # ------------------------------------------------------------------
    # UTILITÁRIOS
    # ------------------------------------------------------------------
    @staticmethod
    def _fmt_moeda(valor):
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _fmt_qtd(qtd):
        if qtd == int(qtd):
            return str(int(qtd))
        return f"{qtd:.3f}".rstrip("0").rstrip(".")

    @staticmethod
    def _parse_moeda(texto):
        limpo = texto.replace("R$", "").strip().replace(".", "").replace(",", ".")
        try:
            return float(limpo)
        except ValueError:
            return 0.0


if __name__ == "__main__":
    root = tk.Tk()
    app = CaixaSupermercado(root)
    root.mainloop()