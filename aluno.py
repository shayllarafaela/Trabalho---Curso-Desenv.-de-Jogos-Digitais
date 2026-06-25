"""
Cadastro de Aluno
------------------
Aplicação para cadastrar e gerenciar alunos (de escola, curso, academia, etc.),
com tkinter + sqlite3 (banco de dados local).

Funcionalidades:
- Cadastrar aluno (nome, data de nascimento, CPF, telefone, e-mail, endereço, turma/curso, status)
- Listar todos os alunos em uma tabela
- Buscar/filtrar por nome ou CPF
- Editar aluno selecionado
- Excluir aluno selecionado (com confirmação)
- Validações de campos obrigatórios e formato (data, CPF, e-mail)
- Cálculo automático da idade a partir da data de nascimento
- Dados salvos em arquivo local "alunos.db" (persistem entre execuções)

Basta executar: python3 cadastro_aluno.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import re
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alunos.db")


class BancoDados:
    """Camada simples de acesso ao banco de dados SQLite."""

    def __init__(self, caminho=DB_PATH):
        self.conexao = sqlite3.connect(caminho)
        self._criar_tabela()

    def _criar_tabela(self):
        self.conexao.execute("""
            CREATE TABLE IF NOT EXISTS alunos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                data_nascimento TEXT NOT NULL,
                cpf TEXT NOT NULL UNIQUE,
                telefone TEXT,
                email TEXT,
                endereco TEXT,
                turma TEXT,
                status TEXT NOT NULL DEFAULT 'Ativo'
            )
        """)
        self.conexao.commit()

    def inserir(self, dados):
        cursor = self.conexao.execute("""
            INSERT INTO alunos (nome, data_nascimento, cpf, telefone, email, endereco, turma, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, dados)
        self.conexao.commit()
        return cursor.lastrowid

    def atualizar(self, id_aluno, dados):
        self.conexao.execute("""
            UPDATE alunos
            SET nome=?, data_nascimento=?, cpf=?, telefone=?, email=?, endereco=?, turma=?, status=?
            WHERE id=?
        """, (*dados, id_aluno))
        self.conexao.commit()

    def excluir(self, id_aluno):
        self.conexao.execute("DELETE FROM alunos WHERE id=?", (id_aluno,))
        self.conexao.commit()

    def listar(self, filtro=""):
        if filtro:
            cursor = self.conexao.execute(
                "SELECT * FROM alunos WHERE nome LIKE ? OR cpf LIKE ? ORDER BY nome",
                (f"%{filtro}%", f"%{filtro}%")
            )
        else:
            cursor = self.conexao.execute("SELECT * FROM alunos ORDER BY nome")
        return cursor.fetchall()

    def cpf_existe(self, cpf, ignorar_id=None):
        if ignorar_id:
            cursor = self.conexao.execute(
                "SELECT id FROM alunos WHERE cpf=? AND id<>?", (cpf, ignorar_id))
        else:
            cursor = self.conexao.execute("SELECT id FROM alunos WHERE cpf=?", (cpf,))
        return cursor.fetchone() is not None


class CadastroAluno:
    def __init__(self, root):
        self.root = root
        self.root.title("Cadastro de Aluno")
        self.root.geometry("1020x660")
        self.root.minsize(900, 600)
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
                          background="#3a0ca3", foreground="white")
        estilo.configure("Campo.TLabel", font=("Segoe UI", 10, "bold"), background="#ffffff")
        estilo.configure("Treeview", font=("Segoe UI", 10), rowheight=26)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    # ------------------------------------------------------------------
    def _montar_interface(self):
        cabecalho = tk.Frame(self.root, bg="#3a0ca3", height=65)
        cabecalho.pack(fill="x")
        ttk.Label(cabecalho, text="🎓 Cadastro de Alunos", style="Titulo.TLabel").pack(
            padx=20, pady=14, anchor="w")

        corpo = tk.Frame(self.root, bg="#f4f6f8")
        corpo.pack(fill="both", expand=True, padx=15, pady=10)
        corpo.columnconfigure(0, weight=2)
        corpo.columnconfigure(1, weight=3)
        corpo.rowconfigure(0, weight=1)

        # ===== Coluna esquerda: formulário =====
        self.form_frame = tk.LabelFrame(corpo, text="Dados do Aluno", bg="#ffffff",
                                         font=("Segoe UI", 11, "bold"), padx=15, pady=15)
        self.form_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.form_frame.columnconfigure(0, weight=1)

        ttk.Label(self.form_frame, text="Nome completo *", style="Campo.TLabel").pack(
            anchor="w", pady=(0, 2))
        self.entry_nome = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_nome.pack(fill="x")

        ttk.Label(self.form_frame, text="Data de nascimento *  (dd/mm/aaaa)", style="Campo.TLabel").pack(
            anchor="w", pady=(8, 2))
        self.entry_nascimento = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_nascimento.pack(fill="x")
        self.entry_nascimento.bind("<KeyRelease>", lambda e: self._atualizar_idade())

        self.lbl_idade = tk.Label(self.form_frame, text="Idade: -", bg="#ffffff",
                                   font=("Segoe UI", 9, "italic"), fg="#555")
        self.lbl_idade.pack(anchor="w", pady=(2, 0))

        ttk.Label(self.form_frame, text="CPF *  (ex: 000.000.000-00)", style="Campo.TLabel").pack(
            anchor="w", pady=(8, 2))
        self.entry_cpf = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_cpf.pack(fill="x")

        ttk.Label(self.form_frame, text="Telefone  (ex: (00) 00000-0000)", style="Campo.TLabel").pack(
            anchor="w", pady=(8, 2))
        self.entry_telefone = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_telefone.pack(fill="x")

        ttk.Label(self.form_frame, text="E-mail", style="Campo.TLabel").pack(anchor="w", pady=(8, 2))
        self.entry_email = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_email.pack(fill="x")

        ttk.Label(self.form_frame, text="Endereço", style="Campo.TLabel").pack(anchor="w", pady=(8, 2))
        self.entry_endereco = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_endereco.pack(fill="x")

        ttk.Label(self.form_frame, text="Turma / Curso", style="Campo.TLabel").pack(anchor="w", pady=(8, 2))
        self.entry_turma = tk.Entry(self.form_frame, font=("Segoe UI", 11))
        self.entry_turma.pack(fill="x")

        ttk.Label(self.form_frame, text="Status", style="Campo.TLabel").pack(anchor="w", pady=(8, 2))
        self.combo_status = ttk.Combobox(self.form_frame, state="readonly", font=("Segoe UI", 10),
                                          values=["Ativo", "Inativo", "Trancado", "Formado"])
        self.combo_status.pack(fill="x")
        self.combo_status.set("Ativo")

        # Botões do formulário
        botoes_form = tk.Frame(self.form_frame, bg="#ffffff")
        botoes_form.pack(fill="x", pady=(20, 0))

        self.btn_salvar = tk.Button(botoes_form, text="💾 Cadastrar Aluno", bg="#2a9d8f",
                                     fg="white", font=("Segoe UI", 10, "bold"), relief="flat",
                                     height=2, command=self.salvar, cursor="hand2")
        self.btn_salvar.pack(fill="x", pady=(0, 8))

        self.btn_cancelar_edicao = tk.Button(botoes_form, text="Cancelar edição", bg="#adb5bd",
                                              fg="white", font=("Segoe UI", 9), relief="flat",
                                              command=self._cancelar_edicao, cursor="hand2")
        self.lbl_modo = tk.Label(self.form_frame, text="", bg="#ffffff", fg="#e76f51",
                                  font=("Segoe UI", 9, "bold"))
        self.lbl_modo.pack(anchor="w", pady=(6, 0))

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

        tabela_frame = tk.LabelFrame(direita, text="Alunos Cadastrados", bg="#ffffff",
                                      font=("Segoe UI", 11, "bold"), padx=5, pady=5)
        tabela_frame.grid(row=1, column=0, sticky="nsew")
        tabela_frame.rowconfigure(0, weight=1)
        tabela_frame.columnconfigure(0, weight=1)

        colunas = ("nome", "idade", "cpf", "turma", "status")
        self.tabela = ttk.Treeview(tabela_frame, columns=colunas, show="headings")
        self.tabela.heading("nome", text="Nome")
        self.tabela.heading("idade", text="Idade")
        self.tabela.heading("cpf", text="CPF")
        self.tabela.heading("turma", text="Turma/Curso")
        self.tabela.heading("status", text="Status")

        self.tabela.column("nome", width=200)
        self.tabela.column("idade", width=60, anchor="center")
        self.tabela.column("cpf", width=130, anchor="center")
        self.tabela.column("turma", width=140)
        self.tabela.column("status", width=90, anchor="center")

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
    def _data_valida(texto):
        try:
            data = datetime.strptime(texto, "%d/%m/%Y")
            if data > datetime.now():
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
            "turma": self.entry_turma.get().strip(),
            "status": self.combo_status.get().strip(),
        }

    def salvar(self):
        dados = self._coletar_dados_formulario()

        if not dados["nome"]:
            messagebox.showwarning("Campo obrigatório", "Informe o nome completo do aluno.")
            self.entry_nome.focus_set()
            return

        if not dados["nascimento"] or not self._data_valida(dados["nascimento"]):
            messagebox.showwarning("Data inválida",
                                    "Informe uma data de nascimento válida no formato dd/mm/aaaa.\n"
                                    "A data não pode ser no futuro.")
            self.entry_nascimento.focus_set()
            return

        if not dados["cpf"]:
            messagebox.showwarning("Campo obrigatório", "Informe o CPF do aluno.")
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

        if self.banco.cpf_existe(dados["cpf"], ignorar_id=self.id_em_edicao):
            messagebox.showwarning("CPF já cadastrado", "Já existe um aluno cadastrado com esse CPF.")
            self.entry_cpf.focus_set()
            return

        valores = (dados["nome"], dados["nascimento"], dados["cpf"], dados["telefone"],
                   dados["email"], dados["endereco"], dados["turma"], dados["status"])

        if self.id_em_edicao is None:
            self.banco.inserir(valores)
            messagebox.showinfo("Sucesso", f"Aluno '{dados['nome']}' cadastrado com sucesso!")
            self.status.configure(text=f"Aluno '{dados['nome']}' cadastrado.")
        else:
            self.banco.atualizar(self.id_em_edicao, valores)
            messagebox.showinfo("Sucesso", f"Aluno '{dados['nome']}' atualizado com sucesso!")
            self.status.configure(text=f"Aluno '{dados['nome']}' atualizado.")
            self._cancelar_edicao()

        self._limpar_formulario()
        self._atualizar_tabela()

    def preparar_edicao(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showinfo("Nenhuma seleção", "Selecione um aluno na tabela para editar.")
            return

        id_aluno = self.tabela.item(selecionado[0], "tags")[0]
        registro = self.banco.conexao.execute(
            "SELECT * FROM alunos WHERE id=?", (id_aluno,)
        ).fetchone()

        if not registro:
            messagebox.showerror("Erro", "Não foi possível localizar este registro.")
            return

        self.id_em_edicao = registro[0]
        self.entry_nome.delete(0, "end"); self.entry_nome.insert(0, registro[1])
        self.entry_nascimento.delete(0, "end"); self.entry_nascimento.insert(0, registro[2])
        self.entry_cpf.delete(0, "end"); self.entry_cpf.insert(0, registro[3])
        self.entry_telefone.delete(0, "end"); self.entry_telefone.insert(0, registro[4] or "")
        self.entry_email.delete(0, "end"); self.entry_email.insert(0, registro[5] or "")
        self.entry_endereco.delete(0, "end"); self.entry_endereco.insert(0, registro[6] or "")
        self.entry_turma.delete(0, "end"); self.entry_turma.insert(0, registro[7] or "")
        self.combo_status.set(registro[8] or "Ativo")
        self._atualizar_idade()

        self.btn_salvar.configure(text="💾 Salvar Alterações", bg="#e76f51")
        self.btn_cancelar_edicao.pack(fill="x")
        self.lbl_modo.configure(text=f"✏️ Editando: {registro[1]}")
        self.entry_nome.focus_set()

    def _cancelar_edicao(self):
        self.id_em_edicao = None
        self.btn_salvar.configure(text="💾 Cadastrar Aluno", bg="#2a9d8f")
        self.btn_cancelar_edicao.pack_forget()
        self.lbl_modo.configure(text="")
        self._limpar_formulario()

    def excluir(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showinfo("Nenhuma seleção", "Selecione um aluno na tabela para excluir.")
            return

        valores = self.tabela.item(selecionado[0], "values")
        id_aluno = self.tabela.item(selecionado[0], "tags")[0]
        nome = valores[0]

        if messagebox.askyesno("Confirmar exclusão",
                                f"Tem certeza que deseja excluir o aluno '{nome}'?\nEsta ação não pode ser desfeita."):
            self.banco.excluir(id_aluno)
            self._atualizar_tabela()
            self.status.configure(text=f"Aluno '{nome}' excluído.")
            if self.id_em_edicao == int(id_aluno):
                self._cancelar_edicao()

    def _limpar_formulario(self):
        self.entry_nome.delete(0, "end")
        self.entry_nascimento.delete(0, "end")
        self.entry_cpf.delete(0, "end")
        self.entry_telefone.delete(0, "end")
        self.entry_email.delete(0, "end")
        self.entry_endereco.delete(0, "end")
        self.entry_turma.delete(0, "end")
        self.combo_status.set("Ativo")
        self.lbl_idade.configure(text="Idade: -")

    def _atualizar_tabela(self):
        for linha in self.tabela.get_children():
            self.tabela.delete(linha)

        filtro = self.entry_busca.get().strip()
        registros = self.banco.listar(filtro)
        for registro in registros:
            id_aluno, nome, nascimento, cpf, telefone, email, endereco, turma, status = registro
            idade = self._calcular_idade(nascimento)
            idade_texto = str(idade) if idade is not None else "-"
            self.tabela.insert("", "end",
                                values=(nome, idade_texto, cpf, turma or "-", status),
                                tags=(str(id_aluno),))

        self.status.configure(text=f"{len(registros)} aluno(s) encontrado(s).")


if __name__ == "__main__":
    root = tk.Tk()
    app = CadastroAluno(root)
    root.mainloop()