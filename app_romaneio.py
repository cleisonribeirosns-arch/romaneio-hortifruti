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

  # Estilos customizados
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

  # Verificar se existe logo da empresa na pasta
  logo_path = None
  for ext in ["png", "jpg", "jpeg"]:
    if os.path.exists(f"logo.{ext}"):
      logo_path = f"logo.{ext}"
      break
    elif os.path.exists(f"logo_empresa.{ext}"):
      logo_path = f"logo_empresa.{ext}"
      break

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

  # Tabela de Informações Gerais (Cabeçalho do Romaneio)
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

  # Tabela de Itens
  table_data = [[
      "Produto / Description",
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

  # Total Geral
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

  # Assinaturas
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

  doc.build(story)
  buffer.seek(0)
  return buffer.getvalue()


# Configuração da página Streamlit
st.set_page_config(
    page_title="Recebimento Hortifrúti", page_icon="🥦", layout="wide"
)


# Inicialização do banco de dados SQLite
def init_db():
  conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
  cursor = conn.cursor()

  # Tabela de Usuários
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL -- 'Gestor' ou 'Operador'
        )
    """)

  # Tabela de Produtos
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_barras TEXT,
            codigo_produto TEXT UNIQUE,
            nome TEXT UNIQUE NOT NULL,
            unidade_padrao TEXT NOT NULL
        )
    """)

  # Migração automática para colunas de produtos
  cursor.execute("PRAGMA table_info(produtos)")
  columns = [column[1] for column in cursor.fetchall()]
  if "codigo_produto" not in columns:
    cursor.execute("ALTER TABLE produtos ADD COLUMN codigo_produto TEXT")
  if "codigo_barras" not in columns:
    cursor.execute("ALTER TABLE produtos ADD COLUMN codigo_barras TEXT")

  # Tabela de Romaneios (Cabeçalho)
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

  # Tabela de Itens do Romaneio
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

  # Inserir usuário Gestor padrão se não existir
  cursor.execute("SELECT * FROM usuarios WHERE login = 'admin'")
  if not cursor.fetchone():
    cursor.execute(
        "INSERT INTO usuarios (nome, login, senha, perfil) VALUES"
        " ('Administrador', 'admin', '1234', 'Gestor')"
    )

  # Atualizar/Popular a base de dados com todos os produtos do inventário
  cursor.execute(
      "SELECT COUNT(*) FROM produtos WHERE codigo_produto IS NOT NULL AND"
      " codigo_barras IS NOT NULL"
  )
  if cursor.fetchone()[0] == 0:
    cursor.execute(
        "DELETE FROM produtos"
    )  # Limpa a tabela antiga para atualizar totalmente
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

# Diretório para salvar fotos
if not os.path.exists("uploads"):
  os.makedirs("uploads")

# Controle de Sessão de Login
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
  st.title("🥦 Sistema de Recebimento Hortifrúti")
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
  # Usuário Logado - Barra Lateral
  user_info = st.session_state["usuario_logado"]
  st.sidebar.markdown(f"**Usuário:** {user_info['nome']}")
  st.sidebar.markdown(f"**Perfil:** {user_info['perfil']}")

  if st.sidebar.button("Sair / Logout"):
    st.session_state["usuario_logado"] = None
    st.rerun()

  st.sidebar.divider()

  # Navegação por Permissão
  opcoes_menu = ["Novo Romaneio (Recebimento)", "Consultar Romaneios"]
  if user_info["perfil"] == "Gestor":
    opcoes_menu.extend([
        "Gerenciar Cadastros (Produtos)",
        "Gerenciar Usuários & Permissões",
    ])

  menu = st.sidebar.radio("Navegação", opcoes_menu)

  # --- MÓDULO 1: NOVO ROMANEIO (Lançamento Operacional) ---
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
      st.markdown(f"
