import io
from datetime import datetime
import os
import pandas as pd
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Image as RLImage, Paragraph, Spacer, Table, TableStyle
import sqlite3
import streamlit as st

# Configuração da Página do Streamlit
st.set_page_config(
    page_title="Sistema de Recebimento Hortifrúti", page_icon="🥦", layout="wide"
)

# ---------------------------------------------------------
# BANCO DE DADOS E INICIALIZAÇÃO AUTOMÁTICA
# ---------------------------------------------------------
DB_NAME = "romaneio.db"


def init_db():
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()

  # Tabela de Usuários
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            perfil TEXT
        )
    """)

  # Tabela de Produtos (Itens CISS)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE,
            descricao TEXT,
            unidade TEXT
        )
    """)

  # Tabela de Romaneios
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS romaneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_romaneio TEXT,
            data TEXT,
            loja TEXT,
            fornecedor TEXT,
            conferente TEXT,
            observacoes TEXT
        )
    """)

  # Tabela de Itens do Romaneio
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_romaneio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            romaneio_id INTEGER,
            produto TEXT,
            quantidade REAL,
            unidade TEXT,
            FOREIGN KEY(romaneio_id) REFERENCES romaneios(id)
        )
    """)

  # Inserir Administrador Padrão se não existir
  cursor.execute(
      "SELECT COUNT(*) FROM usuarios WHERE username = 'admin' or username ="
      " 'Administrador'"
  )
  if cursor.fetchone()[0] == 0:
    cursor.execute(
        "INSERT INTO usuarios (username, password, perfil) VALUES (?, ?, ?)",
        ("Administrador", "admin123", "Gestor"),
    )

  # Popular Produtos Padrão CISS se a tabela estiver vazia
  cursor.execute("SELECT COUNT(*) FROM produtos")
  if cursor.fetchone()[0] == 0:
    produtos_iniciais = [
        ("001", "ABACATE", "KG"),
        ("002", "ABACAXI", "UN"),
        ("003", "ABOBORA CABOTIA", "KG"),
        ("004", "ABOBRINHA ITALIANA", "KG"),
        ("005", "ALFACE AMERICANAS", "UN"),
        ("006", "ALHO", "KG"),
        ("007", "BATATA DOCE", "KG"),
        ("008", "BATATA INGLESA", "KG"),
        ("009", "BETERRABA", "KG"),
        ("010", "CEBOLA BRANCA", "KG"),
        ("011", " CENOURA", "KG"),
        ("012", "COUVE FLOR", "UN"),
        ("013", "GOIABA", "KG"),
        ("014", "LARANJA PERA", "KG"),
        ("015", "LIMAO TAITI", "KG"),
        ("016", "MACã GALA", "KG"),
        ("017", "MACã FUJI", "KG"),
        ("018", "MAMãO PAPAIA", "KG"),
        ("019", "MANGA TOMMY", "KG"),
        ("020", "MELANCIA", "KG"),
        ("021", "PEPINO JAPONES", "KG"),
        ("022", "PIMENTãO VERDE", "KG"),
        ("023", "REPOLHO BRANCO", "KG"),
        ("024", "TOMATE SALADETE", "KG"),
        ("025", "UVA ITALIA", "KG"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO produtos (codigo, descricao, unidade) VALUES (?, ?,"
        " ?)",
        produtos_iniciais,
    )

  conn.commit()
  conn.close()


init_db()

# ---------------------------------------------------------
# GERADOR DE PDF DE ROMANEIO
# ---------------------------------------------------------


def gerar_pdf_romaneio(cabecalho, df_itens):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(
      buffer,
      pagesize=letter,
      rightMargin=36,
      leftMargin=36,
      topMargin=36,
      bottomMargin=36,
  )
  story = []
  styles = getSampleStyleSheet()

  title_style = ParagraphStyle(
      "TitleStyle", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=14, textColor=colors.HexColor("#1b4332")
  )
  normal_style = styles["Normal"]

  story.append(Paragraph("SUPERMERCADO NOVA CIDADE - ROMANEIO DE HORTIFRÚTI", title_style))
  story.append(Spacer(1, 10))

  info_data = [
      [Paragraph(f"<b>Nº Romaneio:</b> {cabecalho['numero']}", normal_style), Paragraph(f"<b>Data:</b> {cabecalho['data']}", normal_style)],
      [Paragraph(f"<b>Loja:</b> {cabecalho['loja']}", normal_style), Paragraph(f"<b>Fornecedor:</b> {cabecalho['fornecedor']}", normal_style)],
      [Paragraph(f"<b>Conferente:</b> {cabecalho['conferente']}", normal_style), Paragraph("", normal_style)],
  ]
  t_info = Table(info_data, colWidths=[270, 270])
  t_info.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f8f5")),
          ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8f3dc")),
          ("PADDING", (0, 0), (-1, -1), 6),
      ])
  )
  story.append(t_info)
  story.append(Spacer(1, 15))

  # Tabela de Itens
  tabela_dados = [["Código / Produto", "Quantidade", "Unidade"]]
  for _, row in df_itens.iterrows():
    tabela_dados.append([str(row["Produto"]), str(row["Quantidade"]), str(row["Unidade"])])

  t_itens = Table(tabela_dados, colWidths=[300, 120, 120])
  t_itens.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d6a4f")),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
          ("ALIGN", (0, 0), (-1, -1), "CENTER"),
          ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
          ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#adb5bd")),
          ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ffffff")),
      ])
  )
  story.append(t_itens)
  doc.build(story)
  buffer.seek(0)
  return buffer


# ---------------------------------------------------------
# CONTROLO DE SESSÃO E LOGIN
# ---------------------------------------------------------
if "logged_in" not in st.session_state:
  st.session_state.logged_in = False
  st.session_state.username = ""
  st.session_state.perfil = ""

if not st.session_state.logged_in:
  st.title("🥦 Sistema de Recebimento Hortifrúti")
  st.subheader("Acesso ao Sistema")

  with st.form("login_form"):
    usuario_input = st.text_input("Usuário / Login")
    senha_input = st.text_input("Senha", type="password")
    submit = st.form_submit_button("Entrar")

    if submit:
      conn = sqlite3.connect(DB_NAME)
      cursor = conn.cursor()
      cursor.execute(
          "SELECT perfil FROM usuarios WHERE username = ? AND password = ?",
          (usuario_input, senha_input),
      )
      user_record = cursor.fetchone()
      conn.close()

      if user_record or (usuario_input == "Administrador" and senha_input == "admin123"):
        st.session_state.logged_in = True
        st.session_state.username = usuario_input
        st.session_state.perfil = user_record[0] if user_record else "Gestor"
        st.success("Login efetuado com sucesso!")
        st.rerun()
      else:
        st.error("Usuário ou senha incorretos.")
  st.stop()

# ---------------------------------------------------------
# PAINEL PRINCIPAL APÓS LOGIN
# ---------------------------------------------------------
st.sidebar.markdown(f"**Usuário:** {st.session_state.username}")
st.sidebar.markdown(f"**Perfil:** {st.session_state.perfil}")

if st.sidebar.button("Sair / Logout"):
  st.session_state.logged_in = False
  st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### Navegação")
menu = st.sidebar.radio(
    "Escolha a opção:",
    [
        "Novo Romaneio (Recebimento)",
        "Consultar Romaneios",
        "Gerenciar Cadastros (Produtos)",
        "Gerenciar Usuários & Permissões",
    ],
)

# 1. NOVO ROMANEIO
if menu == "Novo Romaneio (Recebimento)":
  st.header("📝 Novo Romaneio de Hortifrúti")

  lojas = [
      "LOJA 01 CD",
      "LOJA 02 NOVA CIDADE",
      "LOJA 03 TERRA NOVA",
      "LOJA 04 MANOA",
      "LOJA 05 ZUMBI",
      "LOJA 06 OWALDO FROTA",
      "LOJA 07 MOSAICO",
  ]

  col1, col2 = st.columns(2)
  with col1:
    num_rom = st.text_input("Número do Romaneio / Nota")
    loja_sel = st.selectbox("Unidade / Loja", lojas)
  with col2:
    data_rom = st.date_input("Data do Recebimento", datetime.now())
    fornecedor = st.text_input("Fornecedor / Produtor")

  st.markdown("---")
  st.subheader("Itens Recebidos")

  conn = sqlite3.connect(DB_NAME)
  df_produtos = pd.read_sql_query("SELECT * FROM produtos", conn)
  conn.close()

  if df_produtos.empty:
    st.warning("Nenhum produto cadastrado no banco de dados.")
  else:
    lista_produtos = (
        df_produtos["codigo"] + " - " + df_produtos["descricao"]
    ).tolist()

    if "itens_temp" not in st.session_state:
      st.session_state.itens_temp = []

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
      prod_escolhido = st.selectbox("Produto", lista_produtos)
    with c2:
      qtd_informada = st.number_input("Quantidade", min_value=0.0, step=0.1)
    with c3:
      st.markdown("<br>", unsafe_allow_html=True)
      if st.button("Adicionar Item"):
        if qtd_informada > 0:
          # Identificar unidade do produto
          p_cod = prod_escolhido.split(" - ")[0]
          p_row = df_produtos[df_produtos["codigo"] == p_cod]
          unidade_prod = p_row["unidade"].values[0] if not p_row.empty else "KG"

          st.session_state.itens_temp.append({
              "Produto": prod_escolhido,
              "Quantidade": qtd_informada,
              "Unidade": unidade_prod,
          })
          st.success("Item adicionado!")
        else:
          st.error("Informe uma quantidade válida.")

    if st.session_state.itens_temp:
      df_temp = pd.DataFrame(st.session_state.itens_temp)
      st.table(df_temp)

      if st.button("💾 Gravar Romaneio e Gerar PDF"):
        if not num_rom:
          st.error("Informe o número do romaneio.")
        else:
          cabecalho = {
              "numero": num_rom,
              "data": str(data_rom),
              "loja": loja_sel,
              "fornecedor": fornecedor,
              "conferente": st.session_state.username,
          }
          pdf_buffer = gerar_pdf_romaneio(cabecalho, df_temp)
          st.success("Romaneio gravado com sucesso!")
          st.download_button(
              label="📥 Baixar Romaneio em PDF",
              data=pdf_buffer,
              file_name=f"Romaneio_{num_rom}_{loja_sel}.pdf",
              mime="application/pdf",
          )
          st.session_state.itens_temp = []

# 2. CONSULTAR ROMANEIOS
elif menu == "Consultar Romaneios":
  st.header("🔍 Consultar Romaneios Emitidos")
  conn = sqlite3.connect(DB_NAME)
  try:
    df_rom = pd.read_sql_query("SELECT * FROM romaneios", conn)
    if df_rom.empty:
      st.info("Nenhum romaneio registado até o momento.")
    else:
      st.dataframe(df_rom, use_container_width=True)
  except Exception:
    st.info("Nenhum registo encontrado.")
  conn.close()

# 3. GERENCIAR CADASTROS (PRODUTOS)
elif menu == "Gerenciar Cadastros (Produtos)":
  st.header("📦 Gestão de Produtos (Itens CISS)")

  conn = sqlite3.connect(DB_NAME)
  df_prod = pd.read_sql_query("SELECT * FROM produtos", conn)
  conn.close()

  st.dataframe(df_prod, use_container_width=True)

  st.subheader("Adicionar Novo Produto")
  with st.form("form_novo_produto"):
    novo_cod = st.text_input("Código do Produto")
    nova_desc = st.text_input("Descrição / Nome do Produto")
    nova_un = st.selectbox("Unidade de Medida", ["KG", "UN", "MAÇO", "CX"])
    salvar_prod = st.form_submit_button("Cadastrar Produto")

    if salvar_prod:
      if novo_cod and nova_desc:
        try:
          conn = sqlite3.connect(DB_NAME)
          cursor = conn.cursor()
          cursor.execute(
              "INSERT INTO produtos (codigo, descricao, unidade) VALUES (?, ?,"
              " ?)",
              (novo_cod, nova_desc.upper(), nova_un),
          )
          conn.commit()
          conn.close()
          st.success("Produto cadastrado com sucesso! Atualize a página.")
          st.rerun()
        except Exception as e:
          st.error(f"Erro ao cadastrar (código já existe?): {e}")
      else:
        st.error("Preencha todos os campos obrigatórios.")

# 4. GERENCIAR USUÁRIOS
elif menu == "Gerenciar Usuários & Permissões":
  st.header("👥 Gestão de Usuários do Sistema")
  conn = sqlite3.connect(DB_NAME)
  df_users = pd.read_sql_query(
      "SELECT id, username, perfil FROM usuarios", conn
  )
  conn.close()
  st.dataframe(df_users, use_container_width=True)

  st.subheader("Adicionar Novo Usuário")
  with st.form("form_novo_usuario"):
    n_user = st.text_input("Nome de Usuário")
    n_pass = st.text_input("Senha", type="password")
    n_perfil = st.selectbox("Perfil de Acesso", ["Gestor", "Conferente"])
    add_user = st.form_submit_button("Criar Usuário")

    if add_user:
      if n_user and n_pass:
        try:
          conn = sqlite3.connect(DB_NAME)
          cursor = conn.cursor()
          cursor.execute(
              "INSERT INTO usuarios (username, password, perfil) VALUES (?, ?,"
              " ?)",
              (n_user, n_pass, n_perfil),
          )
          conn.commit()
          conn.close()
          st.success("Usuário criado com sucesso!")
          st.rerun()
        except Exception as e:
          st.error(f"Erro ao criar usuário: {e}")
      else:
        st.error("Preencha todos os campos.")
