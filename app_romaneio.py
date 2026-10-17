import base64
from datetime import datetime
import io
import os
import pandas as pd
import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image as RLImage,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
import sqlite3
import streamlit as st

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA E CSS (FUNDO DE LOGIN + OCULTAR TOPO)
# ---------------------------------------------------------
logo_page_icon = (
    "logo_romaneio.png" if os.path.exists("logo_romaneio.png") else "logo.png"
)
if not os.path.exists(logo_page_icon):
  logo_page_icon = "🛒"

st.set_page_config(
    page_title="Romaneio Hortifruti", page_icon=logo_page_icon, layout="wide"
)

# Procura dinamicamente pela imagem de fundo de login na pasta
bg_login_path = None
for nome_possivel in [
    "Tela de login.jpeg",
    "Tela de login.jpg",
    "tela_de_login.jpeg",
    "tela_de_login.jpg",
    "login_bg.jpg",
    "login_bg.png",
]:
  if os.path.exists(nome_possivel):
    bg_login_path = nome_possivel
    break

css_fundo = ""
if bg_login_path:
  with open(bg_login_path, "rb") as image_file:
    encoded_string = base64.b64encode(image_file.read()).decode()
  css_fundo = f"""
    .stApp {{
        background-image: linear-gradient(rgba(0,0,0,0.65), rgba(0,0,0,0.65)), url("data:image/jpeg;base64,{encoded_string}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
    }}
  """

st.markdown(
    f"""
    <style>
    /* Oculta totalmente o cabeçalho superior do Streamlit */
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    
    /* Oculta rodapé padrão */
    footer {{
        visibility: hidden !important;
    }}

    {css_fundo}
    </style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# FUNÇÃO GERADORA DE PDF (MARCA D'ÁGUA PERFEITAMENTE CENTRALIZADA)
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
      "TitleStyle",
      parent=styles["Heading1"],
      fontName="Helvetica-Bold",
      fontSize=13,
      leading=16,
      textColor=colors.HexColor("#1A365D"),
  )

  subtitle_style = ParagraphStyle(
      "SubTitleStyle",
      parent=styles["Normal"],
      fontName="Helvetica",
      fontSize=9,
      leading=12,
      textColor=colors.HexColor("#2D3748"),
  )

  logo_path = None
  for ext in ["png", "jpg", "jpeg"]:
    if os.path.exists(f"logo_romaneio.{ext}"):
      logo_path = f"logo_romaneio.{ext}"
      break
    elif os.path.exists(f"logo.{ext}"):
      logo_path = f"logo.{ext}"
      break

  def desenhar_marca_dagua(canvas, doc_obj):
    if logo_path:
      canvas.saveState()
      canvas.setFillAlpha(0.08)
      canvas.drawImage(
          logo_path,
          126,
          320,
          width=360,
          height=220,
          preserveAspectRatio=True,
          mask="auto",
      )
      canvas.restoreState()

  texto_empresa = Paragraph(
      "<b>SUPERMERCADO NOVA CIDADE / SUPER NOVA CIDADE</b><br/>Controle de"
      " Recebimento de Mercadorias - Hortifrúti",
      title_style,
  )

  if logo_path:
    img_logo = RLImage(logo_path, width=120, height=45)
    top_table_data = [[img_logo, texto_empresa]]
    top_table = Table(top_table_data, colWidths=[130, 410])
  else:
    top_table_data = [[texto_empresa]]
    top_table = Table(top_table_data, colWidths=[540])

  top_table.setStyle(
      TableStyle([
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
      ])
  )

  story.append(top_table)
  story.append(Spacer(1, 10))

  dados_cabecalho = [
      [
          Paragraph(f"<b>Nº Romaneio:</b> {cabecalho[1]}", subtitle_style),
          Paragraph(f"<b>Loja:</b> {cabecalho[2]}", subtitle_style),
          Paragraph(f"<b>Data Rec.:</b> {cabecalho[3]}", subtitle_style),
      ],
      [
          Paragraph(
              f"<b>Fornecedor:</b> {cabecalho[4]} (Cód: {cabecalho[5] or 'N/A'})",
              subtitle_style,
          ),
          Paragraph(
              f"<b>Tel. Fornecedor:</b> {cabecalho[6] or 'N/A'}", subtitle_style
          ),
          Paragraph(f"<b>Conferente:</b> {cabecalho[7]}", subtitle_style),
      ],
      [
          Paragraph(
              f"<b>Pagamento à Vista:</b> {cabecalho[8]}", subtitle_style
          ),
          Paragraph(
              f"<b>Data Pgto:</b> {cabecalho[9] or 'N/A'}", subtitle_style
          ),
          Paragraph("", subtitle_style),
      ],
  ]

  t_cabecalho = Table(dados_cabecalho, colWidths=[180, 180, 180])
  t_cabecalho.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
          ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
          ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
          ("TOPPADDING", (0, 0), (-1, -1), 6),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
          ("LEFTPADDING", (0, 0), (-1, -1), 6),
          ("RIGHTPADDING", (0, 0), (-1, -1), 6),
      ])
  )

  story.append(t_cabecalho)
  story.append(Spacer(1, 15))

  table_data = [[
      "Produto / Descrição",
      "Qtd / Peso",
      "Unidade",
      "Valor Unit. (R$)",
      "Valor Total (R$)",
  ]]

  for _, item in df_itens.iterrows():
    p_desc = Paragraph(str(item["produto"]), subtitle_style)
    q_val = (
        f"{item['quantidade']:,.3f}"
        .replace(",", "v")
        .replace(".", ",")
        .replace("v", ".")
    )
    u_val = str(item["unidade"])
    vu_val = (
        f"R$ {item['valor_unitario']:,.2f}"
        .replace(",", "v")
        .replace(".", ",")
        .replace("v", ".")
    )
    vt_val = (
        f"R$ {item['valor_total']:,.2f}"
        .replace(",", "v")
        .replace(".", ",")
        .replace("v", ".")
    )
    table_data.append([p_desc, q_val, u_val, vu_val, vt_val])

  tot_geral = df_itens["valor_total"].sum() if not df_itens.empty else 0.0
  tot_str = (
      f"R$ {tot_geral:,.2f}"
      .replace(",", "v")
      .replace(".", ",")
      .replace("v", ".")
  )
  table_data.append([
      Paragraph("<b>TOTAL GERAL</b>", subtitle_style),
      "",
      "",
      "",
      Paragraph(f"<b>{tot_str}</b>", subtitle_style),
  ])

  t_itens = Table(table_data, colWidths=[220, 80, 60, 90, 90])
  t_itens.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1A365D")),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
          ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
          ("FONTSIZE", (0, 0), (-1, 0), 9),
          ("ALIGN", (1, 0), (-1, -1), "CENTER"),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EDF2F7")),
          ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
          ("TOPPADDING", (0, 0), (-1, -1), 5),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
      ])
  )

  story.append(t_itens)
  story.append(Spacer(1, 35))

  dados_ass = [
      [
          "_______________________________________",
          "_______________________________________",
      ],
      ["Assinatura do Conferente", "Assinatura do Entregador / Fornecedor"],
  ]
  t_ass = Table(dados_ass, colWidths=[270, 270])
  t_ass.setStyle(
      TableStyle([
          ("ALIGN", (0, 0), (-1, -1), "CENTER"),
          ("FONTSIZE", (0, 0), (-1, -1), 8),
          ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#4A5568")),
      ])
  )

  story.append(t_ass)

  doc.build(
      story, onFirstPage=desenhar_marca_dagua, onLaterPages=desenhar_marca_dagua
  )
  buffer.seek(0)
  return buffer.getvalue()


# ---------------------------------------------------------
# INICIALIZAÇÃO DA BASE DE DADOS
# ---------------------------------------------------------
def init_db():
  conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
  cursor = conn.cursor()

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    """)

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_barras TEXT,
            codigo_produto TEXT UNIQUE,
            nome TEXT UNIQUE NOT NULL,
            unidade_padrao TEXT NOT NULL
        )
    """)

  cursor.execute("PRAGMA table_info(produtos)")
  columns = [column[1] for column in cursor.fetchall()]
  if "codigo_produto" not in columns:
    cursor.execute("ALTER TABLE produtos ADD COLUMN codigo_produto TEXT")
  if "codigo_barras" not in columns:
    cursor.execute("ALTER TABLE produtos ADD COLUMN codigo_barras TEXT")

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS romaneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_romaneio TEXT UNIQUE NOT NULL,
            loja TEXT NOT NULL,
            data_recebimento TEXT NOT NULL,
            fornecedor TEXT,
            codigo_fornecedor TEXT,
            telefone_fornecedor TEXT,
            conferente TEXT NOT NULL,
            pagamento_a_vista TEXT NOT NULL,
            data_pagamento TEXT,
            caminho_foto TEXT
        )
    """)

  cursor.execute("PRAGMA table_info(romaneios)")
  col_rom = [column[1] for column in cursor.fetchall()]
  if "caminho_foto" not in col_rom:
    cursor.execute("ALTER TABLE romaneios ADD COLUMN caminho_foto TEXT")

  cursor.execute("""
        CREATE TABLE IF NOT EXISTS romaneio_itens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            romaneio_id INTEGER NOT NULL,
            produto TEXT NOT NULL,
            quantidade REAL NOT NULL,
            unidade TEXT NOT NULL,
            valor_unitario REAL,
            valor_total REAL,
            FOREIGN KEY (romaneio_id) REFERENCES romaneios (id)
        )
    """)

  cursor.execute("SELECT * FROM usuarios WHERE login = 'admin'")
  if not cursor.fetchone():
    cursor.execute(
        "INSERT INTO usuarios (nome, login, senha, perfil) VALUES"
        " ('Administrador', 'admin', '1234', 'Gestor')"
    )

  cursor.execute(
      "SELECT COUNT(*) FROM produtos WHERE codigo_produto IS NOT NULL AND"
      " codigo_barras IS NOT NULL"
  )
  if cursor.fetchone()[0] == 0:
    cursor.execute("DELETE FROM produtos")
    produtos_iniciais = [
        ("5884", "28920", "ABACATE FORTUNA KG", "KG"),
        ("2240", "165651", "ABACATE MARGARIDA KG", "KG"),
        ("2387", "165662", "ABACAXI KG PERDA", "KG"),
        ("69496", "66294", "ABACAXI POTE KG", "KG"),
        ("6156", "30531", "ABACAXI UN", "UN"),
        ("17503", "48887", "ABOBRINHA CABOTIA KG", "KG"),
        ("77170", "91644", "ABOBRINHA CABOTIA EMB KG", "KG"),
        ("76982", "91637", "ABOBRINHA EMBALADA KG", "KG"),
        ("3667", "165723", "ABOBRINHA ITALIANA KG", "KG"),
        ("2356", "165659", "ABOBRINHA KG", "KG"),
        ("76074", "91146", "ALECRIM EMBALADO KG", "KG"),
        ("54195", "80659", "ALECRIM KG", "KG"),
        ("7898941929398", "90270", "ALFACE VIVA BABY UN", "UN"),
        ("76111", "91149", "ALHO PORO EMB KG", "KG"),
        ("54003", "80530", "ALHO PORO KG", "KG"),
        ("4275", "187484", "ALHO ROXO KG", "KG"),
        ("2417", "165665", "AMEIXA FRESCA KG", "KG"),
        ("42581", "165144", "AMEIXA SECA S/CA KG", "KG"),
        ("182", "131307", "BANANA NANICA KG", "KG"),
        ("1038", "165575", "BANANA PACOVAN KG", "KG"),
        ("2073", "165634", "BANANA PRATA KG", "KG"),
        ("2219", "165648", "BATATA DOCE BRANCA KG", "KG"),
        ("5104", "28298", "BATATA DOCE ROXA KG", "KG"),
        ("88688", "92830", "BATATA PORTUGUE PALITO KG", "KG"),
        ("2233", "163880", "BATATA PORTUGUESA KG", "KG"),
        ("2349", "165658", "BERINJELA KG", "KG"),
        ("2165", "165643", "BETERRABA KG", "KG"),
        ("75831", "90998", "BROCOLIS EMBALADO KG", "KG"),
        ("3223", "165707", "BROCOLIS KG", "KG"),
        ("4480", "165766", "BROCOLIS NINJA KG", "KG"),
        ("2691", "165686", "CARA KG", "KG"),
        ("2028", "165629", "CEBOLA KG", "KG"),
        ("68192", "165176", "CEBOLA PEROLA KG", "KG"),
        ("674", "131654", "CEBOLA ROXA KG", "KG"),
        ("2226", "165649", "CENOURA KG", "KG"),
        ("2127", "165639", "CHEIRO VERDE UN", "UN"),
        ("949", "165567", "CHUCHU KG", "KG"),
        ("74483", "90318", "COCO SECO EMBALADO 1UN", "UN"),
        ("6705", "165863", "COCO SECO UN", "UN"),
        ("76142", "91151", "COUVE FLOR EMB KG", "KG"),
        ("28929", "63050", "COUVE FLOR KG", "KG"),
        ("2172", "165644", "COUVE UN", "UN"),
        ("89647", "93143", "DUETO DE FRUTAS KG", "KG"),
        ("76104", "91148", "ESPINAFRE EMBALADO KG", "KG"),
        ("1298", "131275", "ESPINAFRE KG", "KG"),
        ("644105", "64409", "FECULA KG PROD", "KG"),
        ("66051", "25096", "FEIJAO VAGEM KG", "KG"),
        ("2202", "165647", "FEIJAO VERDE UN", "UN"),
        ("2400", "165664", "FRUTAS CRISTALIZAS KG", "KG"),
        ("88923", "92889", "GENGIBRE EMBALADO KG", "KG"),
        ("22392", "166819", "GENGIBRE KG", "KG"),
        ("4268", "165758", "GOIABA KG", "KG"),
        ("9942", "165989", "GOMA DE TAPIOCA KG", "KG"),
        ("76005", "91142", "HORTELA EMBALADA KG", "KG"),
        ("3247", "165708", "HORTELA KG", "KG"),
        ("6385", "31519", "INGREDIENTES P/ MAIONESE KG", "KG"),
        ("4565", "137074", "INHAME KG", "KG"),
        ("12508", "36027", "JENIPAPO KG", "KG"),
        ("2196", "165646", "JERIMUM KG", "KG"),
        ("75497", "90796", "KIT CALDEIRADA KG", "KG"),
        ("59220", "19444", "KIT COZIDAO KG", "KG"),
        ("86899", "92193", "KIT JERIMUM E CENOURA KG", "KG"),
        ("8747", "165943", "KIWI KG", "KG"),
        ("9690", "35740", "LARANJA BAHIA KG", "KG"),
        ("61827", "86243", "LARANJA PAULISTA PCT KG", "KG"),
        ("2080", "165635", "LARANJA REGIONAL KG", "KG"),
        ("2059", "165632", "LIMAO KG", "KG"),
        ("7898060740072", "44550", "MACA FUJI PAP PCT DIVERTIDAS 1KG", "UN"),
        ("4381", "28078", "MACA GRANNY SMITH KG", "KG"),
        ("4312", "28071", "MACA KG", "KG"),
        ("1007", "165575", "MACA RED KG", "KG"),
        ("2332", "165657", "MACAXEIRA KG", "KG"),
        ("2363", "165660", "MAMAO KG", "KG"),
        ("7887", "66300", "MAMAO POTE KG", "KG"),
        ("201", "178998", "MANGA TOMMY KG", "KG"),
        ("56601", "81476", "MANJERICAO KG", "KG"),
        ("2264", "165653", "MARACUJA KG", "KG"),
        ("2158", "165642", "MAXIXE KG", "KG"),
        ("75404", "24094", "MELANCIA KG", "KG"),
        ("2370", "165661", "MELAO COMUM KG", "KG"),
        ("21128", "167057", "MELAO FAMOSA", "KG"),
        ("409", "131464", "MELAO PELE DE SAPO KG", "KG"),
        ("17817", "131253", "MELAO REI KG", "KG"),
        ("60974", "84505", "MEXERICA MURCOTE KG", "KG"),
        ("8686", "165939", "MORANGO BDJ KG", "KG"),
        ("76487", "91174", "MORANGO EMBALADO KG", "KG"),
        ("7898141930736", "72270", "OVO DE CODORNA SAO PEDRO CARTELA 30 UD", "UN"),
        ("40141454058", "71563", "OVOS AMAZONAS BRANCO C/30UN", "UN"),
        ("7898963762515", "83316", "OVOS BRANCO JUMBO 10UND", "UN"),
        ("7898141930095", "1061835", "OVOS CARTELA C/06UN BRANCO SAO PEDRO", "UN"),
        ("7898141930064", "156391", "OVOS CARTELA C/12UN VERMELHO SAO PEDRO", "UN"),
        ("7898141930316", "156394", "OVOS CARTELA C/20UN BRANCO SAO PEDRO", "UN"),
        ("7898141930071", "156390", "OVOS CARTELA C/30UN BRANCO SAO PEDRO", "UN"),
        ("7898141930774", "60346", "OVOS CARTELA C/30UN VERMELHO SAO PEDRO.", "UN"),
        ("7418321747840", "79642", "OVOS DA FIFI CAIPIRA C/30UN", "UN"),
        ("7892830754139", "87996", "OVOS DA FIFI COLORIDO 12UN", "UN"),
        ("7148752245775", "87608", "OVOS DA FIFI COLORIDO 30UN", "UN"),
        ("7895552183508", "87998", "OVOS DA FIFI VERMELHO 12UN", "UN"),
        ("7898141930057", "10070", "OVOS SAO PEDRO BRANCO CARTELA C/12UN", "UN"),
        ("7895098581011", "21634", "OVOS SÃO PEDRO PREMIUM VERM 10UN", "UN"),
        ("7898141930101", "156392", "OVOS SAO PEDRO VERMELHO CARTELA C/6UN", "UN"),
        ("42882214403", "86069", "OVOS VERMELHO OVOS AMAZONAS C/30UN", "UN"),
        ("74285", "90251", "PEPINO COMUM EMBALADO KG", "KG"),
        ("2066", "165633", "PEPINO COMUM KG", "KG"),
        ("88626", "92819", "PEPINO SALADA EMB KG", "KG"),
        ("3490", "27463", "PEPINO SALADA KG", "KG"),
        ("4398", "28079", "PERA DANJOU KG", "KG"),
        ("31455", "66306", "PIMENTA DE CHEIRO EMB KG", "KG"),
        ("675369", "163735", "PIMENTA DE CHEIRO KG", "KG"),
        ("75732", "90994", "PIMENTA MURUPI EMB KG", "KG"),
        ("932", "165566", "PIMENTA MURUPI KG", "KG"),
        ("6859", "165871", "PIMENTAO COLORIDO EMB KG", "KG"),
        ("703", "165548", "PIMENTAO COLORIDO KG", "KG"),
        ("2110", "165638", "PIMENTAO VERDE KG", "KG"),
        ("15295", "40184", "PITAYA KG", "KG"),
        ("2134", "165640", "QUIABO KG", "KG"),
        ("4459", "165764", "REPOLHO ROXO KG", "KG"),
        ("76319", "91157", "REPOLHO VERDE EMB KG", "KG"),
        ("2097", "165636", "REPOLHO VERDE KG", "KG"),
        ("8310", "33215", "ROMA KG", "KG"),
        ("67843", "19449", "SALADA KG", "KG"),
        ("9621", "165976", "SALSA KG", "KG"),
        ("2516", "165674", "TANGERINA IMPORTADA KG", "KG"),
        ("1175", "41418", "TOMATE KG", "KG"),
        ("609963080069", "44160", "UVA BLACK S/SEMENTE 250G", "UN"),
        ("7898957749492", "66509", "UVA CAPPELLARO KIDS VITORIA 250G", "UN"),
        ("4343", "28074", "UVA MIDNIGHT KG", "KG"),
        ("751320764102", "35155", "UVA MIDNIGHT TET 500G", "UN"),
        ("751320764140", "33221", "UVA MISTA TET 500G", "UN"),
        ("2394", "165663", "UVA PASSA KG", "KG"),
        ("7896291950550", "48350", "UVA PASSAS PRETA 10KG", "UN"),
        ("7908046701338", "79594", "UVA PRETA DOCE UVA C/ SEMENTE 500G", "UN"),
        ("7898962939062", "90062", "UVA PRETA VITORIA CANASTRA S/SEMENT 500G", "UN"),
        ("751320764133", "38027", "UVA THOMPSON TET 500G", "UN"),
        ("609963080076", "44403", "UVA VERDE THOMPSON 250G", "UN"),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO produtos (codigo_barras, codigo_produto, nome,"
        " unidade_padrao) VALUES (?, ?, ?, ?)",
        produtos_iniciais,
    )

  conn.commit()
  conn.close()


init_db()

if not os.path.exists("uploads"):
  os.makedirs("uploads")

if "usuario_logado" not in st.session_state:
  st.session_state["usuario_logado"] = None


def fazer_login(login, senha):
  conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
  cursor = conn.cursor()
  cursor.execute(
      "SELECT id, nome, perfil FROM usuarios WHERE login = ? AND senha = ?",
      (login, senha),
  )
  usr = cursor.fetchone()
  conn.close()
  return usr


# --- TELA DE LOGIN ---
if st.session_state["usuario_logado"] is None:
  st.title("🛒 Sistema de Recebimento Hortifrúti")
  st.subheader("Acesso ao Sistema")

  with st.form("form_login"):
    login_input = st.text_input("Usuário / Login")
    senha_input = st.text_input("Senha", type="password")
    btn_entrar = st.form_submit_button("Entrar")

    if btn_entrar:
      usuario = fazer_login(login_input, senha_input)
      if usuario:
        st.session_state["usuario_logado"] = {
            "id": usuario[0],
            "nome": usuario[1],
            "perfil": usuario[2],
            "login": login_input,
        }
        st.success(f"Bem-vindo, {usuario[1]}!")
        st.rerun()
      else:
        st.error("Usuário ou senha incorretos.")

else:
  user_info = st.session_state["usuario_logado"]
  st.sidebar.markdown(f"**Usuário:** {user_info['nome']}")
  st.sidebar.markdown(f"**Perfil:** {user_info['perfil']}")

  if st.sidebar.button("Sair / Logout"):
    st.session_state["usuario_logado"] = None
    st.rerun()

  st.sidebar.divider()

  opcoes_menu = ["Novo Romaneio (Recebimento)", "Consultar Romaneios"]
  if user_info["perfil"] == "Gestor":
    opcoes_menu.extend([
        "Gerenciar Cadastros (Produtos)",
        "Gerenciar Usuários & Permissões",
    ])

  menu = st.sidebar.radio("Navegação", opcoes_menu)

  # --- MÓDULO 1: NOVO ROMANEIO ---
  if menu == "Novo Romaneio (Recebimento)":
    st.title("📋 Novo Romaneio de Recebimento")

    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT codigo_barras, codigo_produto, nome, unidade_padrao FROM"
        " produtos ORDER BY nome"
    )
    produtos_lista = cursor.fetchall()
    conn.close()

    prod_dict = {}
    for p in produtos_lista:
      cb = (
          p[0]
          if p[0] and str(p[0]).strip() not in ["None", "Nenhum", ""]
          else "S/N"
      )
      cp = (
          p[1]
          if p[1] and str(p[1]).strip() not in ["None", "Nenhum", ""]
          else "S/N"
      )
      label = f"{p[2]} (Cód: {cp} | Barras: {cb})"
      prod_dict[label] = (p[2], p[3])
    prod_nomes_keys = list(prod_dict.keys())

    with st.expander("1. Cabeçalho do Recebimento", expanded=True):
      col1, col2, col3 = st.columns(3)
      with col1:
        num_romaneio = st.text_input(
            "Número do Romaneio",
            value=f"ROM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        )
        loja = st.selectbox(
            "Loja",
            [
                "LOJA 01 CD",
                "LOJA 02 NOVA CIDADE",
                "LOJA 03 TERRA NOVA",
                "LOJA 04 MANOA",
                "LOJA 05 ZUMBI",
                "LOJA 06 OWALDO FROTA",
                "LOJA 07 MOSAICO",
            ],
            index=2,
        )
      with col2:
        data_rec = st.date_input(
            "Data do Recebimento", datetime.now(), format="DD/MM/YYYY"
        )
        fornecedor = st.text_input("Fornecedor / Entregador")
      with col3:
        cod_fornecedor = st.text_input("Código do Fornecedor")
        tel_fornecedor = st.text_input("Telefone do Fornecedor")

      col4, col5 = st.columns(2)
      with col4:
        pag_vista = st.radio(
            "Pagamento à Vista?", ["Sim", "Não"], horizontal=True
        )
      with col5:
        data_pagamento = (
            st.date_input("Data para Pagamento", None, format="DD/MM/YYYY")
            if pag_vista == "Não"
            else None
        )

      conferente = st.text_input(
          "Responsável Rec. Físico",
          value=user_info["nome"],
          disabled=True,
      )

    st.subheader("2. Itens do Recebimento")

    if "itens_romaneio" not in st.session_state:
      st.session_state["itens_romaneio"] = []

    col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(
        [3, 1.5, 1.5, 1.5, 1]
    )
    with col_p1:
      prod_label_sel = st.selectbox(
          "Produto",
          (
              prod_nomes_keys
              if prod_dict
              else ["Cadastre produtos no gestor"]
          ),
      )
      prod_nome_real = (
          prod_dict[prod_label_sel][0] if prod_dict else "Desconhecido"
      )
    with col_p2:
      und_padrao = prod_dict[prod_label_sel][1] if prod_dict else "KG"
      und_sel = st.selectbox(
          "UND",
          ["KG", "UNID", "GRM", "CX"],
          index=(
              ["KG", "UNID", "GRM", "CX"].index(und_padrao)
              if und_padrao in ["KG", "UNID", "GRM", "CX"]
              else 0
          ),
      )
    with col_p3:
      qtd_input = st.number_input("Qtd / Peso", min_value=0.0, step=0.1, format="%.3f")
    with col_p4:
      val_unit = st.number_input(
          "Valor Unit. (R$)", min_value=0.0, step=0.01, format="%.2f"
      )
    with col_p5:
      st.write("")
      st.write("")
      if st.button("➕ Add"):
        if qtd_input > 0:
          v_tot = qtd_input * val_unit
          st.session_state["itens_romaneio"].append({
              "produto": prod_nome_real,
              "quantidade": qtd_input,
              "unidade": und_sel,
              "valor_unitario": val_unit,
              "valor_total": v_tot,
          })
          st.rerun()
        else:
          st.warning(
              "A quantidade/peso do produto é obrigatória e deve ser maior"
              " que zero."
          )

    if st.session_state["itens_romaneio"]:
      df_itens = pd.DataFrame(st.session_state["itens_romaneio"])
      st.dataframe(df_itens, width="stretch")

      total_geral = df_itens["valor_total"].sum()
      st.markdown(f"### **Total Geral: R$ {total_geral:,.2f}**")

      if st.button("🗑️ Limpar Itens"):
        st.session_state["itens_romaneio"] = []
        st.rerun()

    st.subheader("3. Anexo de Comprovante / Foto")
    fotos_upload = st.file_uploader(
        "Anexar fotos da Nota / Canhoto / Mercadoria",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
    )

    if st.button("✅ Finalizar e Salvar Romaneio", type="primary"):
      if not num_romaneio.strip():
        st.error("O campo 'Número do Romaneio' é obrigatório.")
      elif not fornecedor.strip():
        st.error("O campo 'Fornecedor / Entregador' é obrigatório.")
      elif not st.session_state["itens_romaneio"]:
        st.error(
            "Adicione pelo menos um item ao romaneio antes de salvar."
        )
      elif not fotos_upload:
        st.error(
            "É obrigatório anexar pelo menos uma foto da Nota / Canhoto /"
            " Mercadoria antes de finalizar o romaneio."
        )
      else:
        caminhos_salvos = []
        for foto_upload in fotos_upload:
          caminho_foto = os.path.join(
              "uploads", f"{num_romaneio}_{foto_upload.name}"
          )
          with open(caminho_foto, "wb") as f:
            f.write(foto_upload.getbuffer())
          caminhos_salvos.append(caminho_foto)

        caminhos_str = ",".join(caminhos_salvos)

        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            """
                    INSERT INTO romaneios (numero_romaneio, loja, data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista, data_pagamento, caminho_foto)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
            (
                num_romaneio,
                loja,
                data_rec.strftime("%d/%m/%Y"),
                fornecedor,
                cod_fornecedor,
                tel_fornecedor,
                conferente,
                pag_vista,
                (
                    data_pagamento.strftime("%d/%m/%Y")
                    if data_pagamento
                    else None
                ),
                caminhos_str,
            ),
        )

        romaneio_id = cursor.lastrowid

        for item in st.session_state["itens_romaneio"]:
          cursor.execute(
              """
                        INSERT INTO romaneio_itens (romaneio_id, produto, quantidade, unidade, valor_unitario, valor_total)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
              (
                  romaneio_id,
                  item["produto"],
                  item["quantidade"],
                  item["unidade"],
                  item["valor_unitario"],
                  item["valor_total"],
              ),
          )

        conn.commit()
        conn.close()

        st.success(
            f"Romaneio {num_romaneio} e {len(fotos_upload)} foto(s) salvos com"
            " sucesso!"
        )
        st.session_state["itens_romaneio"] = []

  # --- MÓDULO 2: CONSULTAR ROMANEIOS ---
  elif menu == "Consultar Romaneios":
    st.title("🔍 Consulta e Impressão de Romaneios")

    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
    df_romaneios = pd.read_sql_query(
        "SELECT * FROM romaneios ORDER BY id DESC", conn
    )
    conn.close()

    if not df_romaneios.empty:
      st.dataframe(df_romaneios, width="stretch")

      romaneio_sel = st.selectbox(
          "Selecione o Romaneio para Detalhes / Impressão",
          df_romaneios["numero_romaneio"].tolist(),
      )
      if romaneio_sel:
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, numero_romaneio, loja, data_recebimento, fornecedor,"
            " codigo_fornecedor, telefone_fornecedor, conferente,"
            " pagamento_a_vista, data_pagamento, caminho_foto FROM romaneios"
            " WHERE numero_romaneio = ?",
            (romaneio_sel,),
        )
        cabecalho = cursor.fetchone()

        if cabecalho:
          r_id = cabecalho[0]
          df_det = pd.read_sql_query(
              "SELECT produto, quantidade, unidade, valor_unitario,"
              " valor_total FROM romaneio_itens WHERE romaneio_id = ?",
              conn,
              params=(r_id,),
          )
          conn.close()

          st.markdown("---")
          st.subheader(
              f"📄 Visualização para Impressão - Romaneio: {cabecalho[1]}"
          )

          texto_detalhes = (
              "**SUPERMERCADO NOVA CIDADE / SUPER NOVA CIDADE**<br>"
              f"**Loja:** {cabecalho[2]} | **Data do Recebimento:**"
              f" {cabecalho[3]}<br>**Fornecedor:** {cabecalho[4]} (Cód:"
              f" {cabecalho[5]} | Tel: {cabecalho[6]})<br>**Responsável Rec."
              f" Físico:** {cabecalho[7]}<br>**Pagamento à Vista:**"
              f" {cabecalho[8]}"
          )
          if cabecalho[8] == "Não":
            texto_detalhes += f" | Data Pgto: {cabecalho[9]}"

          st.markdown(texto_detalhes, unsafe_allow_html=True)

          st.write("### Itens Conferidos")
          st.dataframe(df_det, width="stretch")

          total_geral = df_det["valor_total"].sum() if not df_det.empty else 0.0
          st.markdown(f"### **Total Geral: R$ {total_geral:,.2f}**")

          if cabecalho[10]:
            caminhos_fotos = cabecalho[10].split(",")
            st.write("### Fotos / Comprovantes Anexados")
            cols_img = st.columns(len(caminhos_fotos))
            for idx, c_foto in enumerate(caminhos_fotos):
              if os.path.exists(c_foto):
                with cols_img[idx]:
                  st.image(
                      c_foto, caption=f"Foto {idx+1}", use_column_width=True
                  )

          pdf_bytes = gerar_pdf_romaneio(cabecalho, df_det)
          st.download_button(
              label="📄 Baixar Romaneio em PDF (Documento Oficial)",
              data=pdf_bytes,
              file_name=f"{romaneio_sel}.pdf",
              mime="application/pdf",
          )

          if user_info["perfil"] == "Gestor":
            st.write("")
            if st.button(
                f"🗑️ Excluir Romaneio {romaneio_sel} (Apenas Gestor)",
                type="secondary",
            ):
              conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
              cursor = conn.cursor()
              cursor.execute(
                  "DELETE FROM romaneio_itens WHERE romaneio_id = ?", (r_id,)
              )
              cursor.execute("DELETE FROM romaneios WHERE id = ?", (r_id,))
              conn.commit()
              conn.close()
              st.success(f"Romaneio {romaneio_sel} excluído com sucesso!")
              st.rerun()
    else:
      st.info("Nenhum romaneio registrado ainda.")

  # --- MÓDULO 3: GERENCIAR PRODUTOS (Gestor Apenas) ---
  elif (
      menu == "Gerenciar Cadastros (Produtos)"
      and user_info["perfil"] == "Gestor"
  ):
    st.sidebar.subheader("🖼️ Logotipo(s) da Empresa (PDF)")
    # accept_multiple_files=True ativado para permitir enviar mais de uma logo/imagem na barra lateral
    logo_files = st.sidebar.file_uploader(
        "Enviar Logo(s) do Romaneio (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="logo_upload",
    )
    if logo_files:
      for logo_file in logo_files:
        with open(logo_file.name, "wb") as f:
          f.write(logo_file.getbuffer())
      st.sidebar.success(
          f"{len(logo_files)} arquivo(s) de imagem guardado(s) com sucesso!"
      )

    st.title("📦 Cadastro e Gestão de Produtos (Hortifrúti)")

    tab_p1, tab_p2 = st.tabs(
        ["➕ Adicionar Novo Produto", "✏️ Editar ou Excluir Produto"]
    )

    with tab_p1:
      col1, col2 = st.columns(2)
      with col1:
        st.subheader("Adicionar Novo Produto")
        cod_barras = st.text_input("Código de Barras", key="cad_barras")
        cod_prod = st.text_input(
            "Código do Produto (ERP / Interno)", key="cad_cod"
        )
        novo_prod = st.text_input("Nome do Produto", key="cad_nome")
        und_padrao = st.selectbox(
            "Unidade Padrão", ["KG", "UNID", "GRM", "CX"], key="cad_und"
        )
        if st.button("Cadastrar Produto"):
          if novo_prod:
            try:
              conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
              cursor = conn.cursor()
              cursor.execute(
                  "INSERT INTO produtos (codigo_barras, codigo_produto, nome,"
                  " unidade_padrao) VALUES (?, ?, ?, ?)",
                  (cod_barras, cod_prod, novo_prod, und_padrao),
              )
              conn.commit()
              conn.close()
              st.success(f"Produto '{novo_prod}' cadastrado com sucesso!")
              st.rerun()
            except sqlite3.IntegrityError:
              st.error("Produto ou código já cadastrado.")
          else:
            st.warning("Preencha o nome do produto.")

      with col2:
        st.subheader("Produtos Cadastrados")
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_prod = pd.read_sql_query(
            "SELECT id, codigo_barras, codigo_produto, nome, unidade_padrao FROM"
            " produtos ORDER BY nome",
            conn,
        )
        conn.close()

        if not df_prod.empty:
          st.dataframe(df_prod, width="stretch")
        else:
          st.info("Nenhum produto cadastrado no momento.")

    with tab_p2:
      st.subheader("Editar ou Excluir Produto Cadastrado")
      conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
      cursor = conn.cursor()
      cursor.execute(
          "SELECT id, codigo_barras, codigo_produto, nome, unidade_padrao FROM"
          " produtos ORDER BY nome"
      )
      lista_produtos_db = cursor.fetchall()
      conn.close()

      if lista_produtos_db:
        prod_dict_db = {
            f"{p[3]} (Cód: {p[2]} | Barras: {p[1]}) - {p[4]}": p
            for p in lista_produtos_db
        }
        prod_selecionado_label = st.selectbox(
            "Selecione o Produto", list(prod_dict_db.keys())
        )
        prod_dados_sel = prod_dict_db[prod_selecionado_label]

        col_ep1, col_ep2 = st.columns(2)
        with col_ep1:
          edit_barras = st.text_input(
              "Código de Barras",
              value=prod_dados_sel[1] if prod_dados_sel[1] else "",
              key="edit_prod_barras",
          )
          edit_cod = st.text_input(
              "Código do Produto",
              value=prod_dados_sel[2] if prod_dados_sel[2] else "",
              key="edit_prod_cod",
          )
        with col_ep2:
          edit_nome = st.text_input(
              "Nome do Produto",
              value=prod_dados_sel[3],
              key="edit_prod_nome",
          )
          und_list = ["KG", "UNID", "GRM", "CX"]
          idx_und = (
              und_list.index(prod_dados_sel[4])
              if prod_dados_sel[4] in und_list
              else 0
          )
          edit_und = st.selectbox(
              "Unidade Padrão",
              und_list,
              index=idx_und,
              key="edit_prod_und",
          )

        st.write("")
        col_b_p1, col_b_p2 = st.columns([1, 1])
        with col_b_p1:
          if st.button("💾 Salvar Alterações no Produto"):
            if edit_nome:
              try:
                conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE produtos SET codigo_barras = ?, codigo_produto = ?,"
                    " nome = ?, unidade_padrao = ? WHERE id = ?",
                    (
                        edit_barras,
                        edit_cod,
                        edit_nome,
                        edit_und,
                        prod_dados_sel[0],
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Produto atualizado com sucesso!")
                st.rerun()
              except sqlite3.IntegrityError:
                st.error(
                    "Este nome ou código já está em uso por outro produto."
                )
            else:
              st.warning("O nome do produto não pode ficar em branco.")
        with col_b_p2:
          if st.button("🗑️ Excluir Produto", type="secondary"):
            conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM produtos WHERE id = ?", (prod_dados_sel[0],))
            conn.commit()
            conn.close()
            st.success(f"Produto '{prod_dados_sel[3]}' excluído com sucesso!")
            st.rerun()

  # --- MÓDULO 4: GERENCIAR USUÁRIOS (Gestor Apenas) ---
  elif (
      menu == "Gerenciar Usuários & Permissões"
      and user_info["perfil"] == "Gestor"
  ):
    st.title("👥 Controle de Usuários e Permissões")

    tab1, tab2 = st.tabs(
        ["➕ Cadastrar Novo Usuário", "🔑 Alterar Senha / Permissões"]
    )

    with tab1:
      col1, col2 = st.columns(2)
      with col1:
        st.subheader("Cadastrar Novo Usuário")
        nome_user = st.text_input("Nome Completo")
        login_user = st.text_input("Login de Acesso")
        senha_user = st.text_input("Senha", type="password")
        perfil_user = st.selectbox(
            "Perfil de Acesso", ["Operador", "Gestor"]
        )

        if st.button("Salvar Usuário"):
          if nome_user and login_user and senha_user:
            try:
              conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
              cursor = conn.cursor()
              cursor.execute(
                  "INSERT INTO usuarios (nome, login, senha, perfil) VALUES"
                  " (?, ?, ?, ?)",
                  (nome_user, login_user, senha_user, perfil_user),
              )
              conn.commit()
              conn.close()
              st.success(f"Usuário '{login_user}' cadastrado com sucesso!")
              st.rerun()
            except sqlite3.IntegrityError:
              st.error("Login já está em uso por outro usuário.")
          else:
            st.warning("Preencha todos os campos obrigatórios.")

      with col2:
        st.subheader("Usuários Cadastrados")
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_users = pd.read_sql_query(
            "SELECT id, nome, login, perfil FROM usuarios", conn
        )
        conn.close()

        if not df_users.empty:
          st.dataframe(df_users, width="stretch")
        else:
          st.info("Nenhum usuário cadastrado.")

    with tab2:
      st.subheader("Editar, Alterar Senha ou Excluir Usuário")
      conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
      cursor = conn.cursor()
      cursor.execute(
          "SELECT id, nome, login, senha, perfil FROM usuarios ORDER BY nome"
      )
      lista_usuarios = cursor.fetchall()
      conn.close()

      if lista_usuarios:
        user_dict = {
            f"{u[1]} ({u[2]}) - {u[4]}": u for u in lista_usuarios
        }
        user_selecionado_label = st.selectbox(
            "Selecione o Usuário", list(user_dict.keys())
        )
        user_dados = user_dict[user_selecionado_label]

        col_e1, col_e2 = st.columns(2)
        with col_e1:
          novo_nome = st.text_input(
              "Nome Completo", value=user_dados[1], key="edit_nome"
          )
          novo_login = st.text_input(
              "Login de Acesso", value=user_dados[2], key="edit_login"
          )
        with col_e2:
          novo_perfil = st.selectbox(
              "Perfil de Acesso",
              ["Operador", "Gestor"],
              index=0 if user_dados[4] == "Operador" else 1,
              key="edit_perfil",
          )
          nova_senha = st.text_input(
              "Nova Senha",
              value=user_dados[3],
              type="password",
              key="edit_senha",
          )

        st.write("")
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
          if st.button("💾 Salvar Alterações"):
            if novo_nome and novo_login and nova_senha:
              try:
                conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE usuarios SET nome = ?, login = ?, senha = ?, perfil"
                    " = ? WHERE id = ?",
                    (
                        novo_nome,
                        novo_login,
                        nova_senha,
                        novo_perfil,
                        user_dados[0],
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Usuário atualizado com sucesso!")
                st.rerun()
              except sqlite3.IntegrityError:
                st.error("Este login já está em uso por outro usuário.")
            else:
              st.warning("Preencha todos os campos obrigatórios.")
        with col_btn2:
          if st.button("🗑️ Excluir Usuário", type="secondary"):
            if user_dados[0] == user_info["id"]:
              st.error(
                  "Você não pode excluir o seu próprio usuário enquanto está"
                  " logado!"
              )
            else:
              conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
              cursor = conn.cursor()
              cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_dados[0],))
              conn.commit()
              conn.close()
              st.success(f"Usuário '{user_dados[1]}' excluído com sucesso!")
              st.rerun()
