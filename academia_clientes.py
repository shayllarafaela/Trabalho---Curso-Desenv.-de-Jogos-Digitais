"""
Cadastro de Academia (Matrícula de Clientes)
----------------------------------------------
Aplicação para cadastrar pessoas que estão se matriculando na academia,
com tkinter + sqlite3 (banco de dados local).

Funcionalidades:
- Cadastrar cliente (nome, data de nascimento, CPF, telefone, e-mail,
  endereço, plano contratado, modalidade, data de início, status)
- Listar todos os clientes cadastrados em uma tabela
- Buscar/filtrar por nome ou CPF
- Editar cliente selecionado
- Excluir cliente selecionado (com confirmação)
- Validações de campos obrigatórios e formato (data, CPF, e-mail)
- Cálculo automático da idade e da data de vencimento do plano
- Dados salvos em arquivo local "academia_clientes.db" (persistem entre execuções)

Basta executar: python3 cadastro_academia.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import re
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "academia_clientes.db")

# Duração de cada plano em dias (usado para calcular o vencimento)
DURACAO_PLANOS = {
    "Mensal": 30,
    "Trimestral": 90,
    "Semestral": 180,
    "Anual": 365,
}

MODALIDADES = ["Musculação", "Crossfit", "Funcional", "Natação", "Lutas",
               "Pilates", "Yoga", "Spinning", "Dança", "Outra"]


class BancoDados:
    """Camada simples de acesso ao banco de dados SQLite."""

    def __init__(self, caminho=DB_PATH):
        self.conexao = sqlite3.connect(caminho)
        self._criar_tabela()

    def _criar_tabela(self):
        self.conexao.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                data_nascimento TEXT NOT NULL,
                cpf TEXT NOT NULL UNIQUE,
                telefone TEXT,
                email TEXT,
                endereco TEXT,
                plano TEXT NOT NULL,
                modalidade TEXT NOT NULL,
                data_inicio TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Ativo'
            )
        """)
        self.conexao.commit()

    def inserir(self, dados):
        cursor = self.conexao.execute("""
            INSERT INTO clientes (nome, data_nascimento, cpf, telefone, email, endereco,
                                   plano, modalidade, data_inicio, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dados)
        self.conexao.commit()
        return cursor.lastrowid

    def atualizar(self, id_cliente, dados):
        self.conexao.execute("""
            UPDATE clientes
            SET nome=?, data_nascimento=?, cpf=?, telefone=?, email=?, endereco=?,
                plano=?, modalidade=?, data_inicio=?, status=?
            WHERE id=?
        """, (*dados, id_cliente))
        self.conexao.commit()

    def excluir(self, id_cliente):
        self.conexao.execute("DELETE FROM clientes WHERE id=?", (id_cliente,))
        self.conexao.commit()

    def listar(self, filtro=""):
        if filtro:
            cursor = self.conexao.execute(
                "SELECT * FROM clientes WHERE nome LIKE ? OR cpf LIKE ? ORDER BY nome",
                (f"%{filtro}%", f"%{filtro}%")
            )
        else:
            cursor = self.conexao.execute("SELECT * FROM clientes ORDER BY nome")
        return cursor.fetchall()

    def cpf_existe(self, cpf, ignorar_id=None):
        if ignorar_id:
            cursor = self.conexao.execute(
                "SELECT id FROM clientes WHERE cpf=? AND id<>?", (cpf, ignorar_id))
        else:
            cursor = self.conexao.execute("SELECT id FROM clientes WHERE cpf=?", (cpf,))
        return cursor.fetchone() is not None


class CadastroAcademia:
    def __init__(self, root):
        self.root = root
        self.root.title("Cadastro de Academia - Matrícula de Clientes")
        self.root.geometry("1050x680")
        self.root.minsize(950, 620)
        self.root.configure(bg="#f4f6f8")

        self.banco = BancoDados()
        self.id_em_edicao = None

        self._configurar_estilos()
        self._montar_interface()
        self._atualizar_tabela()

    # ------------------------------------------------------------------
    def _configurar_estilos(self):
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 17, "bold"),
                          background="#14213d", foreground="white")
        estilo.configure("Campo.TLabel", font=("Segoe UI", 10, "bold"), background="#ffffff")
        estilo.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    # ------------------------------------------------------------------
    def _montar_interface(self):
        cabecalho = tk.Frame(self.root, bg="#14213d", height=65)
        cabecalho.pack(fill="x")
        ttk.Label(cabecalho, text="🏋️ Cadastro de Clientes da Academia", style="Titulo.TLabel").pack(
            padx=20, pady=14, anchor="w")

        corpo = tk.Frame(self.root, bg="#f4f6f8")
        corpo.pack(fill="both", expand=True, padx=15, pady=10)
        corpo.columnconfigure(0, weight=2)
        corpo.columnconfigure(1, weight=3)
        corpo.rowconfigure(0, weight=1)

        # ===== Coluna esquerda: formulário =====
        self.form_frame = tk.LabelFrame(corpo, text="Dados da Matrícula", bg="#ffffff",
                                         font=("Segoe UI", 11, "bold"), padx=15, pady=15)
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.form_frame.columnconfigure(0, weight=1)
        self.form_frame.columnconfigure(1, weight=1)

        ttk.Label(self.form_frame, text="Nome completo *", style="Campo.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.entry_nome = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_nome.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(self.form_frame, text="Data de nascimento *  (dd/mm/aaaa)", style="Campo.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 2))
        ttk.Label(self.form_frame, text="CPF *  (000.000.000-00)", style="Campo.TLabel").grid(
            row=2, column=1, sticky="w", pady=(0, 2), padx=(8, 0))

        self.entry_nascimento = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_nascimento.grid(row=3, column=0, sticky="ew", pady=(0, 2))
        self.entry_nascimento.bind("<KeyRelease>", lambda e: self._atualizar_idade())

        self.entry_cpf = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_cpf.grid(row=3, column=1, sticky="ew", pady=(0, 2), padx=(8, 0))

        self.lbl_idade = tk.Label(self.form_frame, text="Idade: -", bg="#ffffff",
                                   font=("Segoe UI", 9, "italic"), fg="#555")
        self.lbl_idade.grid(row=4, column=0, sticky="w", pady=(0, 8))

        ttk.Label(self.form_frame, text="Telefone  (00) 00000-0000", style="Campo.TLabel").grid(
            row=5, column=0, sticky="w", pady=(0, 2))
        ttk.Label(self.form_frame, text="E-mail", style="Campo.TLabel").grid(
            row=5, column=1, sticky="w", pady=(0, 2), padx=(8, 0))

        self.entry_telefone = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_telefone.grid(row=6, column=0, sticky="ew", pady=(0, 8))
        self.entry_email = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_email.grid(row=6, column=1, sticky="ew", pady=(0, 8), padx=(8, 0))

        ttk.Label(self.form_frame, text="Endereço", style="Campo.TLabel").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.entry_endereco = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_endereco.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        ttk.Label(self.form_frame, text="Plano *", style="Campo.TLabel").grid(
            row=9, column=0, sticky="w", pady=(0, 2))
        ttk.Label(self.form_frame, text="Modalidade *", style="Campo.TLabel").grid(
            row=9, column=1, sticky="w", pady=(0, 2), padx=(8, 0))

        self.combo_plano = ttk.Combobox(self.form_frame, state="readonly", font=("Segoe UI", 10),
                                         values=list(DURACAO_PLANOS.keys()))
        self.combo_plano.grid(row=10, column=0, sticky="ew", pady=(0, 8))
        self.combo_plano.set("Mensal")
        self.combo_plano.bind("<<ComboboxSelected>>", lambda e: self._atualizar_vencimento())

        self.combo_modalidade = ttk.Combobox(self.form_frame, state="readonly", font=("Segoe UI", 10),
                                              values=MODALIDADES)
        self.combo_modalidade.grid(row=10, column=1, sticky="ew", pady=(0, 8), padx=(8, 0))
        self.combo_modalidade.set("Musculação")

        ttk.Label(self.form_frame, text="Data de início *  (dd/mm/aaaa)", style="Campo.TLabel").grid(
            row=11, column=0, sticky="w", pady=(0, 2))
        ttk.Label(self.form_frame, text="Status", style="Campo.TLabel").grid(
            row=11, column=1, sticky="w", pady=(0, 2), padx=(8, 0))

        self.entry_inicio = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_inicio.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.entry_inicio.grid(row=12, column=0, sticky="ew", pady=(0, 2))
        self.entry_inicio.bind("<KeyRelease>", lambda e: self._atualizar_vencimento())

        self.combo_status = ttk.Combobox(self.form_frame, state="readonly", font=("Segoe UI", 10),
                                          values=["Ativo", "Inativo", "Trancado"])
        self.combo_status.grid(row=12, column=1, sticky="ew", pady=(0, 2), padx=(8, 0))
        self.combo_status.set("Ativo")

        self.lbl_vencimento = tk.Label(self.form_frame, text="Vencimento do plano: -", bg="#ffffff",
                                        font=("Segoe UI", 9, "italic"), fg="#555")
        self.lbl_vencimento.grid(row=13, column=0, columnspan=2, sticky="w", pady=(2, 8))
        self._atualizar_vencimento()

        # Botões do formulário
        botoes_form = tk.Frame(self.form_frame, bg="#ffffff")
        botoes_form.grid(row=14, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.btn_salvar = tk.Button(botoes_form, text="💾 Matricular Cliente", bg="#2a9d8f",
                                     fg="white", font=("Segoe UI", 10, "bold"), relief="flat",
                                     height=2, command=self.salvar, cursor="hand2")
        self.btn_salvar.pack(fill="x", pady=(0, 8))

        self.btn_cancelar_edicao = tk.Button(botoes_form, text="Cancelar edição", bg="#adb5bd",
                                              fg="white", font=("Segoe UI", 9), relief="flat",
                                              command=self._cancelar_edicao, cursor="hand2")
        self.lbl_modo = tk.Label(self.form_frame, text="", bg="#ffffff", fg="#e76f51",
                                  font=("Segoe UI", 9, "bold"))
        self.lbl_modo.grid(row=15, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # ===== Coluna direita: busca + tabela =====
        direita = tk.Frame(corpo, bg="#f4f6f8")
        direita.grid(row=0, column=1, sticky="nsew")
        direita.rowconfigure(1, weight=1)
        direita.columnconfigure(0, weight=1)

        busca_frame = tk.Frame(direita, bg="#f4f6f8")
        busca_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(busca_frame, text="🔍 Buscar por nome ou CPF:", background="#f4f6f8",
                  font=("Segoe UI", 10)).pack(side="left")
        self.entry_busca = tk.Entry(busca_frame, font=("Segoe UI", 10))
        self.entry_busca.pack(side="left", fill="x", expand=True, padx=8)
        self.entry_busca.bind("<KeyRelease>", lambda e: self._atualizar_tabela())

        tabela_frame = tk.LabelFrame(direita, text="Clientes Matriculados", bg="#ffffff",
                                      font=("Segoe UI", 11, "bold"), padx=5, pady=5)
        tabela_frame.grid(row=1, column=0, sticky="nsew")
        tabela_frame.rowconfigure(0, weight=1)
        tabela_frame.columnconfigure(0, weight=1)

        colunas = ("nome", "plano", "modalidade", "vencimento", "status")
        self.tabela = ttk.Treeview(tabela_frame, columns=colunas, show="headings")
        self.tabela.heading("nome", text="Nome")
        self.tabela.heading("plano", text="Plano")
        self.tabela.heading("modalidade", text="Modalidade")
        self.tabela.heading("vencimento", text="Vencimento")
        self.tabela.heading("status", text="Status")

        self.tabela.column("nome", width=190)
        self.tabela.column("plano", width=90, anchor="center")
        self.tabela.column("modalidade", width=110)
        self.tabela.column("vencimento", width=95, anchor="center")
        self.tabela.column("status", width=80, anchor="center")

        scroll = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll.set)
        self.tabela.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        # Botões de ação
        acoes_frame = tk.Frame(direita, bg="#f4f6f8")
        acoes_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        tk.Button(acoes_frame, text="✏️ Editar selecionado", bg="#457b9d", fg="white",
                   font=("Segoe UI", 10, "bold"), relief="flat",
                   command=self.preparar_edicao, cursor="hand2").pack(side="left", expand=True,
                                                                       fill="x", padx=(0, 5))
        tk.Button(acoes_frame, text="🗑️ Excluir selecionado", bg="#e63946", fg="white",
                   font=("Segoe UI", 10, "bold"), relief="flat",
                   command=self.excluir, cursor="hand2").pack(side="left", expand=True,
                                                                fill="x", padx=(5, 0))

        self.status = tk.Label(self.root, text="Pronto.", bg="#dfe6e9", anchor="w",
                                font=("Segoe UI", 9), padx=10)
        self.status.pack(fill="x", side="bottom")

    # ------------------------------------------------------------------
    # VALIDAÇÕES E UTILITÁRIOS
    # ------------------------------------------------------------------
    @staticmethod
    def _data_valida(texto, permitir_futuro=False):
        try:
            data = datetime.strptime(texto, "%d/%m/%Y")
            if not permitir_futuro and data > datetime.now():
                return False
            return True
        except ValueError:
            return False

    @staticmethod
    def _calcular_idade(texto):
        try:
            nascimento = datetime.strptime(texto, "%d/%m/%Y")
            hoje = datetime.now()
            idade = hoje.year - nascimento.year - (
                (hoje.month, hoje.day) < (nascimento.month, nascimento.day)
            )
            return idade
        except ValueError:
            return None

    @staticmethod
    def _email_valido(email):
        if not email:
            return True
        return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) is not None

    @staticmethod
    def _cpf_valido_formato(cpf):
        somente_numeros = re.sub(r"\D", "", cpf)
        return len(somente_numeros) == 11

    def _atualizar_idade(self):
        texto = self.entry_nascimento.get().strip()
        idade = self._calcular_idade(texto)
        if idade is not None and idade >= 0:
            self.lbl_idade.configure(text=f"Idade: {idade} anos")
        else:
            self.lbl_idade.configure(text="Idade: -")

    def _atualizar_vencimento(self):
        texto = self.entry_inicio.get().strip()
        plano = self.combo_plano.get()
        try:
            inicio = datetime.strptime(texto, "%d/%m/%Y")
            dias = DURACAO_PLANOS.get(plano, 30)
            vencimento = inicio + timedelta(days=dias)
            self.lbl_vencimento.configure(text=f"Vencimento do plano: {vencimento.strftime('%d/%m/%Y')}")
        except ValueError:
            self.lbl_vencimento.configure(text="Vencimento do plano: -")

    @staticmethod
    def _calcular_vencimento_str(data_inicio_str, plano):
        try:
            inicio = datetime.strptime(data_inicio_str, "%d/%m/%Y")
            dias = DURACAO_PLANOS.get(plano, 30)
            return (inicio + timedelta(days=dias)).strftime("%d/%m/%Y")
        except ValueError:
            return "-"

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def _coletar_dados_formulario(self):
        return {
            "nome": self.entry_nome.get().strip(),
            "nascimento": self.entry_nascimento.get().strip(),
            "cpf": self.entry_cpf.get().strip(),
            "telefone": self.entry_telefone.get().strip(),
            "email": self.entry_email.get().strip(),
            "endereco": self.entry_endereco.get().strip(),
            "plano": self.combo_plano.get().strip(),
            "modalidade": self.combo_modalidade.get().strip(),
            "inicio": self.entry_inicio.get().strip(),
            "status": self.combo_status.get().strip(),
        }

    def salvar(self):
        dados = self._coletar_dados_formulario()

        if not dados["nome"]:
            messagebox.showwarning("Campo obrigatório", "Informe o nome completo do cliente.")
            self.entry_nome.focus_set()
            return

        if not dados["nascimento"] or not self._data_valida(dados["nascimento"]):
            messagebox.showwarning("Data inválida",
                                    "Informe uma data de nascimento válida no formato dd/mm/aaaa.\n"
                                    "A data não pode ser no futuro.")
            self.entry_nascimento.focus_set()
            return

        if not dados["cpf"]:
            messagebox.showwarning("Campo obrigatório", "Informe o CPF do cliente.")
            self.entry_cpf.focus_set()
            return

        if not self._cpf_valido_formato(dados["cpf"]):
            messagebox.showwarning("CPF inválido", "O CPF deve conter 11 números.\nEx.: 000.000.000-00")
            self.entry_cpf.focus_set()
            return

        if not self._email_valido(dados["email"]):
            messagebox.showwarning("E-mail inválido", "Informe um e-mail válido ou deixe o campo vazio.")
            self.entry_email.focus_set()
            return

        if not dados["inicio"] or not self._data_valida(dados["inicio"], permitir_futuro=True):
            messagebox.showwarning("Data inválida", "Informe uma data de início válida no formato dd/mm/aaaa.")
            self.entry_inicio.focus_set()
            return

        if not dados["plano"]:
            messagebox.showwarning("Campo obrigatório", "Selecione o plano contratado.")
            return

        if not dados["modalidade"]:
            messagebox.showwarning("Campo obrigatório", "Selecione a modalidade desejada.")
            return

        if self.banco.cpf_existe(dados["cpf"], ignorar_id=self.id_em_edicao):
            messagebox.showwarning("CPF já cadastrado", "Já existe um cliente cadastrado com esse CPF.")
            self.entry_cpf.focus_set()
            return

        valores = (dados["nome"], dados["nascimento"], dados["cpf"], dados["telefone"],
                   dados["email"], dados["endereco"], dados["plano"], dados["modalidade"],
                   dados["inicio"], dados["status"])

        if self.id_em_edicao is None:
            self.banco.inserir(valores)
            messagebox.showinfo("Sucesso", f"Cliente '{dados['nome']}' matriculado com sucesso!")
            self.status.configure(text=f"Cliente '{dados['nome']}' matriculado.")
        else:
            self.banco.atualizar(self.id_em_edicao, valores)
            messagebox.showinfo("Sucesso", f"Cadastro de '{dados['nome']}' atualizado com sucesso!")
            self.status.configure(text=f"Cliente '{dados['nome']}' atualizado.")
            self._cancelar_edicao()

        self._limpar_formulario()
        self._atualizar_tabela()

    def preparar_edicao(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showinfo("Nenhuma seleção", "Selecione um cliente na tabela para editar.")
            return

        id_cliente = self.tabela.item(selecionado[0], "tags")[0]
        registro = self.banco.conexao.execute(
            "SELECT * FROM clientes WHERE id=?", (id_cliente,)
        ).fetchone()

        if not registro:
            messagebox.showerror("Erro", "Não foi possível localizar este registro.")
            return

        (self.id_em_edicao, nome, nascimento, cpf, telefone, email,
         endereco, plano, modalidade, inicio, status) = registro

        self.entry_nome.delete(0, "end"); self.entry_nome.insert(0, nome)
        self.entry_nascimento.delete(0, "end"); self.entry_nascimento.insert(0, nascimento)
        self.entry_cpf.delete(0, "end"); self.entry_cpf.insert(0, cpf)
        self.entry_telefone.delete(0, "end"); self.entry_telefone.insert(0, telefone or "")
        self.entry_email.delete(0, "end"); self.entry_email.insert(0, email or "")
        self.entry_endereco.delete(0, "end"); self.entry_endereco.insert(0, endereco or "")
        self.combo_plano.set(plano or "Mensal")
        self.combo_modalidade.set(modalidade or "Musculação")
        self.entry_inicio.delete(0, "end"); self.entry_inicio.insert(0, inicio)
        self.combo_status.set(status or "Ativo")
        self._atualizar_idade()
        self._atualizar_vencimento()

        self.btn_salvar.configure(text="💾 Salvar Alterações", bg="#e76f51")
        self.btn_cancelar_edicao.pack(fill="x")
        self.lbl_modo.configure(text=f"✏️ Editando: {nome}")
        self.entry_nome.focus_set()

    def _cancelar_edicao(self):
        self.id_em_edicao = None
        self.btn_salvar.configure(text="💾 Matricular Cliente", bg="#2a9d8f")
        self.btn_cancelar_edicao.pack_forget()
        self.lbl_modo.configure(text="")
        self._limpar_formulario()

    def excluir(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showinfo("Nenhuma seleção", "Selecione um cliente na tabela para excluir.")
            return

        valores = self.tabela.item(selecionado[0], "values")
        id_cliente = self.tabela.item(selecionado[0], "tags")[0]
        nome = valores[0]

        if messagebox.askyesno("Confirmar exclusão",
                                f"Tem certeza que deseja excluir o cadastro de '{nome}'?\n"
                                f"Esta ação não pode ser desfeita."):
            self.banco.excluir(id_cliente)
            self._atualizar_tabela()
            self.status.configure(text=f"Cliente '{nome}' excluído.")
            if self.id_em_edicao == int(id_cliente):
                self._cancelar_edicao()

    def _limpar_formulario(self):
        self.entry_nome.delete(0, "end")
        self.entry_nascimento.delete(0, "end")
        self.entry_cpf.delete(0, "end")
        self.entry_telefone.delete(0, "end")
        self.entry_email.delete(0, "end")
        self.entry_endereco.delete(0, "end")
        self.combo_plano.set("Mensal")
        self.combo_modalidade.set("Musculação")
        self.entry_inicio.delete(0, "end")
        self.entry_inicio.insert(0, datetime.now().strftime("%d/%m/%Y"))
        self.combo_status.set("Ativo")
        self.lbl_idade.configure(text="Idade: -")
        self._atualizar_vencimento()

    def _atualizar_tabela(self):
        for linha in self.tabela.get_children():
            self.tabela.delete(linha)

        filtro = self.entry_busca.get().strip()
        registros = self.banco.listar(filtro)
        for registro in registros:
            (id_cliente, nome, nascimento, cpf, telefone, email,
             endereco, plano, modalidade, inicio, status) = registro
            vencimento = self._calcular_vencimento_str(inicio, plano)
            self.tabela.insert("", "end",
                                values=(nome, plano, modalidade, vencimento, status),
                                tags=(str(id_cliente),))

        self.status.configure(text=f"{len(registros)} cliente(s) encontrado(s).")


if __name__ == "__main__":
    root = tk.Tk()
    app = CadastroAcademia(root)
    root.mainloop()