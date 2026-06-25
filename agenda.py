"""
Calendário com Agenda
-----------------------
Aplicação de calendário mensal com agenda de compromissos,
feita com tkinter + sqlite3 (banco de dados local).

Funcionalidades:
- Visualização de calendário mensal (navegação entre meses/anos)
- Dias com compromissos são destacados visualmente
- Clique em um dia para ver/adicionar compromissos daquele dia
- Cadastrar compromisso (título, horário, descrição, local)
- Editar e excluir compromissos
- Lista de compromissos do dia selecionado, ordenados por horário
- Botão "Hoje" para voltar rapidamente à data atual
- Dados salvos em arquivo local "agenda.db" (persistem entre execuções)

Não usa nenhuma biblioteca externa (sem tkcalendar) — calendário desenhado
manualmente com o módulo padrão "calendar" do Python.

Basta executar: python3 calendario_agenda.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import calendar
from datetime import date, datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agenda.db")

MESES_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
DIAS_SEMANA_PT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


class BancoDados:
    """Camada simples de acesso ao banco de dados SQLite."""

    def __init__(self, caminho=DB_PATH):
        self.conexao = sqlite3.connect(caminho)
        self._criar_tabela()

    def _criar_tabela(self):
        self.conexao.execute("""
            CREATE TABLE IF NOT EXISTS compromissos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                horario TEXT NOT NULL,
                titulo TEXT NOT NULL,
                local TEXT,
                descricao TEXT
            )
        """)
        self.conexao.commit()

    def inserir(self, dados):
        cursor = self.conexao.execute("""
            INSERT INTO compromissos (data, horario, titulo, local, descricao)
            VALUES (?, ?, ?, ?, ?)
        """, dados)
        self.conexao.commit()
        return cursor.lastrowid

    def atualizar(self, id_compromisso, dados):
        self.conexao.execute("""
            UPDATE compromissos
            SET data=?, horario=?, titulo=?, local=?, descricao=?
            WHERE id=?
        """, (*dados, id_compromisso))
        self.conexao.commit()

    def excluir(self, id_compromisso):
        self.conexao.execute("DELETE FROM compromissos WHERE id=?", (id_compromisso,))
        self.conexao.commit()

    def listar_por_data(self, data_str):
        cursor = self.conexao.execute(
            "SELECT * FROM compromissos WHERE data=? ORDER BY horario", (data_str,))
        return cursor.fetchall()

    def listar_dias_com_compromisso(self, ano, mes):
        """Retorna o conjunto de dias (int) do mês/ano que possuem ao menos um compromisso."""
        prefixo = f"{ano:04d}-{mes:02d}-"
        cursor = self.conexao.execute(
            "SELECT DISTINCT data FROM compromissos WHERE data LIKE ?", (f"{prefixo}%",))
        dias = set()
        for (data_str,) in cursor.fetchall():
            try:
                dias.add(int(data_str.split("-")[2]))
            except (IndexError, ValueError):
                continue
        return dias


class CalendarioAgenda:
    def __init__(self, root):
        self.root = root
        self.root.title("Calendário com Agenda")
        self.root.geometry("1000x650")
        self.root.minsize(900, 600)
        self.root.configure(bg="#f4f6f8")

        self.banco = BancoDados()

        hoje = date.today()
        self.ano_exibido = hoje.year
        self.mes_exibido = hoje.month
        self.data_selecionada = hoje

        self.id_em_edicao = None
        self.botoes_dias = {}  # mapeia dia (int) -> botão tkinter

        self._configurar_estilos()
        self._montar_interface()
        self._desenhar_calendario()
        self._carregar_compromissos_do_dia()

    # ------------------------------------------------------------------
    def _configurar_estilos(self):
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 17, "bold"),
                          background="#4c072d", foreground="white")
        estilo.configure("Campo.TLabel", font=("Segoe UI", 10, "bold"), background="#ffffff")
        estilo.configure("MesAno.TLabel", font=("Segoe UI", 14, "bold"), background="#ffffff")
        estilo.configure("Treeview", font=("Segoe UI", 10), rowheight=28)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    # ------------------------------------------------------------------
    def _montar_interface(self):
        cabecalho = tk.Frame(self.root, bg="#4c072f", height=65)
        cabecalho.pack(fill="x")
        ttk.Label(cabecalho, text="📅 Calendário com Agenda", style="Titulo.TLabel").pack(
            padx=20, pady=14, anchor="w")

        corpo = tk.Frame(self.root, bg="#f4f6f8")
        corpo.pack(fill="both", expand=True, padx=15, pady=10)
        corpo.columnconfigure(0, weight=3)
        corpo.columnconfigure(1, weight=2)
        corpo.rowconfigure(0, weight=1)

        # ===== Coluna esquerda: calendário =====
        esquerda = tk.Frame(corpo, bg="#f4f6f8")
        esquerda.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        nav_frame = tk.Frame(esquerda, bg="#ffffff", padx=10, pady=10)
        nav_frame.pack(fill="x")

        tk.Button(nav_frame, text="◀", font=("Segoe UI", 12, "bold"), width=3,
                   relief="flat", bg="#b2118f", fg="white", cursor="hand2",
                   command=self._mes_anterior).pack(side="left")

        self.lbl_mes_ano = ttk.Label(nav_frame, text="", style="MesAno.TLabel", anchor="center")
        self.lbl_mes_ano.pack(side="left", fill="x", expand=True)

        tk.Button(nav_frame, text="▶", font=("Segoe UI", 12, "bold"), width=3,
                   relief="flat", bg="#b21162", fg="white", cursor="hand2",
                   command=self._mes_seguinte).pack(side="right")

        tk.Button(nav_frame, text="Hoje", font=("Segoe UI", 9, "bold"),
                   relief="flat", bg="#d6066e", fg="white", cursor="hand2",
                   command=self._ir_para_hoje).pack(side="right", padx=(0, 10))

        self.grade_frame = tk.Frame(esquerda, bg="#ffffff", padx=10, pady=10)
        self.grade_frame.pack(fill="both", expand=True)

        legenda_frame = tk.Frame(esquerda, bg="#f4f6f8")
        legenda_frame.pack(fill="x", pady=(8, 0))
        bolinha = tk.Label(legenda_frame, text="●", fg="#ef476f", bg="#f4f6f8", font=("Segoe UI", 12))
        bolinha.pack(side="left")
        tk.Label(legenda_frame, text="Dia com compromisso(s) agendado(s)", bg="#f4f6f8",
                 font=("Segoe UI", 9)).pack(side="left", padx=(2, 0))

        # ===== Coluna direita: agenda do dia selecionado =====
        direita = tk.Frame(corpo, bg="#f4f6f8")
        direita.grid(row=0, column=1, sticky="nsew")
        direita.rowconfigure(2, weight=1)
        direita.columnconfigure(0, weight=1)

        self.lbl_dia_selecionado = tk.Label(direita, text="", bg="#f4f6f8",
                                             font=("Segoe UI", 13, "bold"), fg="#4c0735")
        self.lbl_dia_selecionado.grid(row=0, column=0, sticky="w", pady=(0, 8))

        # --- Formulário de compromisso ---
        form_frame = tk.LabelFrame(direita, text="Novo Compromisso", bg="#ffffff",
                                    font=("Segoe UI", 10, "bold"), padx=12, pady=12)
        form_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        form_frame.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)

        ttk.Label(form_frame, text="Horário *  (hh:mm)", style="Campo.TLabel").grid(
            row=0, column=0, sticky="w")
        self.entry_horario = tk.Entry(form_frame, font=("Segoe UI", 11))
        self.entry_horario.insert(0, "09:00")
        self.entry_horario.grid(row=1, column=0, sticky="ew", padx=(0, 8))

        ttk.Label(form_frame, text="Local", style="Campo.TLabel").grid(
            row=0, column=1, sticky="w")
        self.entry_local = tk.Entry(form_frame, font=("Segoe UI", 11))
        self.entry_local.grid(row=1, column=1, sticky="ew")

        ttk.Label(form_frame, text="Título *", style="Campo.TLabel").grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.entry_titulo = tk.Entry(form_frame, font=("Segoe UI", 11))
        self.entry_titulo.grid(row=3, column=0, columnspan=2, sticky="ew")

        ttk.Label(form_frame, text="Descrição", style="Campo.TLabel").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.text_descricao = tk.Text(form_frame, font=("Segoe UI", 10), height=3, wrap="word")
        self.text_descricao.grid(row=5, column=0, columnspan=2, sticky="ew")

        botoes_form = tk.Frame(form_frame, bg="#ffffff")
        botoes_form.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.btn_salvar = tk.Button(botoes_form, text="➕ Adicionar Compromisso", bg="#ff5fbc",
                                     fg="white", font=("Segoe UI", 10, "bold"), relief="flat",
                                     command=self.salvar_compromisso, cursor="hand2")
        self.btn_salvar.pack(fill="x", pady=(0, 6))

        self.btn_cancelar_edicao = tk.Button(botoes_form, text="Cancelar edição", bg="#adb5bd",
                                              fg="white", font=("Segoe UI", 9), relief="flat",
                                              command=self._cancelar_edicao, cursor="hand2")

        # --- Lista de compromissos do dia ---
        lista_frame = tk.LabelFrame(direita, text="Compromissos do Dia", bg="#ffffff",
                                     font=("Segoe UI", 10, "bold"), padx=5, pady=5)
        lista_frame.grid(row=2, column=0, sticky="nsew")
        lista_frame.rowconfigure(0, weight=1)
        lista_frame.columnconfigure(0, weight=1)

        colunas = ("horario", "titulo", "local")
        self.tabela = ttk.Treeview(lista_frame, columns=colunas, show="headings", height=8)
        self.tabela.heading("horario", text="Hora")
        self.tabela.heading("titulo", text="Compromisso")
        self.tabela.heading("local", text="Local")
        self.tabela.column("horario", width=60, anchor="center")
        self.tabela.column("titulo", width=160)
        self.tabela.column("local", width=100)

        scroll = ttk.Scrollbar(lista_frame, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll.set)
        self.tabela.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")

        self.tabela.bind("<<TreeviewSelect>>", self._mostrar_descricao_selecionada)

        self.lbl_descricao = tk.Label(direita, text="", bg="#f4f6f8", font=("Segoe UI", 9, "italic"),
                                       fg="#444", wraplength=320, justify="left", anchor="w")
        self.lbl_descricao.grid(row=3, column=0, sticky="ew", pady=(6, 0))

        acoes_frame = tk.Frame(direita, bg="#f4f6f8")
        acoes_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0))

        tk.Button(acoes_frame, text="✏️ Editar", bg="#9d4575", fg="white",
                   font=("Segoe UI", 10, "bold"), relief="flat",
                   command=self.preparar_edicao, cursor="hand2").pack(side="left", expand=True,
                                                                       fill="x", padx=(0, 5))
        tk.Button(acoes_frame, text="🗑️ Excluir", bg="#e63946", fg="white",
                   font=("Segoe UI", 10, "bold"), relief="flat",
                   command=self.excluir_compromisso, cursor="hand2").pack(side="left", expand=True,
                                                                            fill="x", padx=(5, 0))

        self.status = tk.Label(self.root, text="Pronto.", bg="#dfe6e9", anchor="w",
                                font=("Segoe UI", 9), padx=10)
        self.status.pack(fill="x", side="bottom")

    # ------------------------------------------------------------------
    # CALENDÁRIO (DESENHO DA GRADE)
    # ------------------------------------------------------------------
    def _desenhar_calendario(self):
        for widget in self.grade_frame.winfo_children():
            widget.destroy()
        self.botoes_dias.clear()

        self.lbl_mes_ano.configure(text=f"{MESES_PT[self.mes_exibido - 1]} de {self.ano_exibido}")

        for col, nome_dia in enumerate(DIAS_SEMANA_PT):
            cor_fonte = "#ef476f" if nome_dia == "Sáb" or nome_dia == "Dom" else "#073b4c"
            tk.Label(self.grade_frame, text=nome_dia, font=("Segoe UI", 10, "bold"),
                     bg="#ffffff", fg=cor_fonte).grid(row=0, column=col, sticky="nsew", pady=(0, 6))
            self.grade_frame.columnconfigure(col, weight=1)

        dias_com_compromisso = self.banco.listar_dias_com_compromisso(self.ano_exibido, self.mes_exibido)
        hoje = date.today()

        calendario_mes = calendar.Calendar(firstweekday=0)  # semana começa na segunda
        semanas = calendario_mes.monthdayscalendar(self.ano_exibido, self.mes_exibido)

        for linha, semana in enumerate(semanas, start=1):
            self.grade_frame.rowconfigure(linha, weight=1)
            for col, dia in enumerate(semana):
                if dia == 0:
                    tk.Label(self.grade_frame, bg="#ffffff").grid(row=linha, column=col, sticky="nsew")
                    continue

                eh_hoje = (dia == hoje.day and self.mes_exibido == hoje.month
                           and self.ano_exibido == hoje.year)
                eh_selecionado = (dia == self.data_selecionada.day
                                   and self.mes_exibido == self.data_selecionada.month
                                   and self.ano_exibido == self.data_selecionada.year)
                tem_compromisso = dia in dias_com_compromisso

                if eh_selecionado:
                    cor_fundo, cor_fonte = "#b2116a", "white"
                elif eh_hoje:
                    cor_fundo, cor_fonte = "#caf0f8", "#4c0735"
                else:
                    cor_fundo, cor_fonte = "#ffffff", "#4c073b"

                texto = str(dia)
                if tem_compromisso and not eh_selecionado:
                    texto += " ●"

                botao = tk.Button(self.grade_frame, text=texto, font=("Segoe UI", 10),
                                   bg=cor_fundo, fg=cor_fonte if not (tem_compromisso and not eh_selecionado) else "#ef476f",
                                   relief="flat", cursor="hand2", height=2,
                                   command=lambda d=dia: self._selecionar_dia(d))
                botao.grid(row=linha, column=col, sticky="nsew", padx=2, pady=2)
                self.botoes_dias[dia] = botao

    def _selecionar_dia(self, dia):
        self.data_selecionada = date(self.ano_exibido, self.mes_exibido, dia)
        self._cancelar_edicao()
        self._desenhar_calendario()
        self._carregar_compromissos_do_dia()

    def _mes_anterior(self):
        if self.mes_exibido == 1:
            self.mes_exibido = 12
            self.ano_exibido -= 1
        else:
            self.mes_exibido -= 1
        self._desenhar_calendario()

    def _mes_seguinte(self):
        if self.mes_exibido == 12:
            self.mes_exibido = 1
            self.ano_exibido += 1
        else:
            self.mes_exibido += 1
        self._desenhar_calendario()

    def _ir_para_hoje(self):
        hoje = date.today()
        self.ano_exibido = hoje.year
        self.mes_exibido = hoje.month
        self.data_selecionada = hoje
        self._cancelar_edicao()
        self._desenhar_calendario()
        self._carregar_compromissos_do_dia()

    # ------------------------------------------------------------------
    # AGENDA (COMPROMISSOS DO DIA)
    # ------------------------------------------------------------------
    @staticmethod
    def _horario_valido(texto):
        try:
            datetime.strptime(texto, "%H:%M")
            return True
        except ValueError:
            return False

    def _data_selecionada_str(self):
        return self.data_selecionada.strftime("%Y-%m-%d")

    def _carregar_compromissos_do_dia(self):
        dia_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
                      "Sexta-feira", "Sábado", "Domingo"][self.data_selecionada.weekday()]
        self.lbl_dia_selecionado.configure(
            text=f"{dia_semana}, {self.data_selecionada.strftime('%d/%m/%Y')}")

        for linha in self.tabela.get_children():
            self.tabela.delete(linha)

        compromissos = self.banco.listar_por_data(self._data_selecionada_str())
        for c in compromissos:
            id_c, data, horario, titulo, local, descricao = c
            self.tabela.insert("", "end", values=(horario, titulo, local or "-"), tags=(str(id_c),))

        self.lbl_descricao.configure(text="")
        self.status.configure(text=f"{len(compromissos)} compromisso(s) neste dia.")

    def _mostrar_descricao_selecionada(self, evento=None):
        selecionado = self.tabela.selection()
        if not selecionado:
            self.lbl_descricao.configure(text="")
            return
        id_c = self.tabela.item(selecionado[0], "tags")[0]
        registro = self.banco.conexao.execute(
            "SELECT descricao FROM compromissos WHERE id=?", (id_c,)
        ).fetchone()
        descricao = registro[0] if registro and registro[0] else "(sem descrição)"
        self.lbl_descricao.configure(text=f"📝 {descricao}")

    def salvar_compromisso(self):
        horario = self.entry_horario.get().strip()
        titulo = self.entry_titulo.get().strip()
        local = self.entry_local.get().strip()
        descricao = self.text_descricao.get("1.0", "end").strip()

        if not titulo:
            messagebox.showwarning("Campo obrigatório", "Informe o título do compromisso.")
            self.entry_titulo.focus_set()
            return

        if not horario or not self._horario_valido(horario):
            messagebox.showwarning("Horário inválido", "Informe um horário válido no formato hh:mm.\nEx.: 14:30")
            self.entry_horario.focus_set()
            return

        valores = (self._data_selecionada_str(), horario, titulo, local, descricao)

        if self.id_em_edicao is None:
            self.banco.inserir(valores)
            messagebox.showinfo("Sucesso", f"Compromisso '{titulo}' adicionado com sucesso!")
            self.status.configure(text=f"Compromisso '{titulo}' adicionado.")
        else:
            self.banco.atualizar(self.id_em_edicao, valores)
            messagebox.showinfo("Sucesso", f"Compromisso '{titulo}' atualizado com sucesso!")
            self.status.configure(text=f"Compromisso '{titulo}' atualizado.")
            self._cancelar_edicao()

        self._limpar_formulario()
        self._desenhar_calendario()
        self._carregar_compromissos_do_dia()

    def preparar_edicao(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showinfo("Nenhuma seleção", "Selecione um compromisso na lista para editar.")
            return

        id_c = self.tabela.item(selecionado[0], "tags")[0]
        registro = self.banco.conexao.execute(
            "SELECT * FROM compromissos WHERE id=?", (id_c,)
        ).fetchone()

        if not registro:
            messagebox.showerror("Erro", "Não foi possível localizar este compromisso.")
            return

        self.id_em_edicao, data, horario, titulo, local, descricao = registro

        self.entry_horario.delete(0, "end"); self.entry_horario.insert(0, horario)
        self.entry_local.delete(0, "end"); self.entry_local.insert(0, local or "")
        self.entry_titulo.delete(0, "end"); self.entry_titulo.insert(0, titulo)
        self.text_descricao.delete("1.0", "end"); self.text_descricao.insert("1.0", descricao or "")

        self.btn_salvar.configure(text="💾 Salvar Alterações", bg="#e76f51")
        self.btn_cancelar_edicao.pack(fill="x")
        self.entry_titulo.focus_set()

    def _cancelar_edicao(self):
        self.id_em_edicao = None
        self.btn_salvar.configure(text="➕ Adicionar Compromisso", bg="#06d6a0")
        self.btn_cancelar_edicao.pack_forget()
        self._limpar_formulario()

    def excluir_compromisso(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            messagebox.showinfo("Nenhuma seleção", "Selecione um compromisso na lista para excluir.")
            return

        valores = self.tabela.item(selecionado[0], "values")
        id_c = self.tabela.item(selecionado[0], "tags")[0]
        titulo = valores[1]

        if messagebox.askyesno("Confirmar exclusão",
                                f"Tem certeza que deseja excluir o compromisso '{titulo}'?"):
            self.banco.excluir(id_c)
            if self.id_em_edicao == int(id_c):
                self._cancelar_edicao()
            self._desenhar_calendario()
            self._carregar_compromissos_do_dia()
            self.status.configure(text=f"Compromisso '{titulo}' excluído.")

    def _limpar_formulario(self):
        self.entry_horario.delete(0, "end")
        self.entry_horario.insert(0, "09:00")
        self.entry_local.delete(0, "end")
        self.entry_titulo.delete(0, "end")
        self.text_descricao.delete("1.0", "end")


if __name__ == "__main__":
    root = tk.Tk()
    app = CalendarioAgenda(root)
    root.mainloop()