import base64
from datetime import datetime
import io
import json
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
import requests
import sqlite3
import streamlit as st
import urllib.parse

# ---------------------------------------------------------
# PROCURA DINÂMICA PELA LOGO / ÍCONE
# ---------------------------------------------------------
logo_path = None
for nome in [
    "logo.png",
    "logo_romaneio.png",
    "logo.jpg",
    "logo.jpeg",
    "logo_romaneio.jpg",
    "logo_romaneio.jpeg",
    "Tela de login.png",
    "Tela de login.jpeg",
    "Tela de login.jpg",
    "tela_de_login.png",
    "tela_de_login.jpeg",
    "tela_de_login.jpg",
]:
  if os.path.exists(nome):
    logo_path = nome
    break

st.set_page_config(
    page_title="Romaneio hortifruti",
    page_icon=logo_path if logo_path else "🥦",
    layout="wide",
)

# ---------------------------------------------------------
# CONFIGURAÇÃO DE ÍCONE NATIVO E PWA (NOME E LOGO SUPERNOVA)
# ---------------------------------------------------------
icon_data_url = ""
if logo_path:
  mime_type = "image/png" if logo_path.lower().endswith(".png") else "image/jpeg"
  with open(logo_path, "rb") as f:
    encoded_logo = base64.b64encode(f.read()).decode()
    icon_data_url = f"data:{mime_type};base64,{encoded_logo}"

manifest_data = {
    "name": "Romaneio hortifruti",
    "short_name": "Romaneio hortifruti",
    "start_url": ".",
    "display": "standalone",
    "background_color": "#1A365D",
    "theme_color": "#1A365D",
    "icons": [
        {"src": icon_data_url, "sizes": "192x192", "type": "image/png"},
        {"src": icon_data_url, "sizes": "512x512", "type": "image/png"},
    ],
}

manifest_json = json.dumps(manifest_data)
manifest_base64 = base64.b64encode(manifest_json.encode()).decode()

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
        background-image: linear-gradient(rgba(0,0,0,0.65), rgba(0,0,0,0.65)), url("data:image/jpeg;base64,{encoded_string}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
    }}
  """

st.markdown(
    f"""
    <head>
        <title>Romaneio hortifruti</title>
        <link rel="manifest" href="data:application/manifest+json;base64,{manifest_base64}">
        <link rel="icon" type="image/png" href="{icon_data_url}">
        <link rel="shortcut icon" type="image/png" href="{icon_data_url}">
        <link rel="apple-touch-icon" href="{icon_data_url}">
        <meta name="apple-mobile-web-app-title" content="Romaneio hortifruti">
        <meta name="apple-mobile-web-app-capable" content="yes">
    </head>
    <style>
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    footer {{
        visibility: hidden !important;
    }}
    .stApp > div:first-child {{
        background: transparent !important;
    }}
    iframe[title="streamlit_feedback.feedback"] {{
        display: none !important;
    }}
    div[data-testid="stToolbar"], button[kind="header"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    .viewerBadge_container__1QSob, .styles_viewerBadge__1yG5_, [data-testid="stStatusWidget"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    {css_fundo}
    </style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# FUNÇÃO DE NOTIFICAÇÃO VIA WHATSAPP (GRUPO LOGÍSTICA)
# ---------------------------------------------------------
def enviar_notificacao_whatsapp(
    num_romaneio, loja, fornecedor, total, conferente
):
  api_url = st.session_state.get("zap_api_url", "").strip()
  api_token = st.session_state.get("zap_token", "").strip()
  id_grupo = st.session_state.get("zap_id_grupo", "").strip()

  if not api_url or not id_grupo:
    return

  texto_msg = (
      f"🚨 *NOVO ROMANEIO HORTIFRÚTI* 🚨\n\n"
      f"• *Romaneio:* {num_romaneio}\n"
      f"• *Loja:* {loja}\n"
      f"• *Fornecedor:* {fornecedor}\n"
      f"• *Valor Total:* R$ {total:,.2f}\n"
      f"• *Conferente:* {conferente}"
  )

  headers = {"Content-Type": "application/json"}
  if api_token:
    headers["apikey"] = api_token
    headers["token"] = api_token

  payload = {
      "number": id_grupo,
      "group": id_grupo,
      "message": texto_msg,
      "text": texto_msg,
  }

  try:
    requests.post(api_url, json=payload, headers=headers, timeout=5)
  except Exception:
    pass


# ---------------------------------------------------------
# FUNÇÃO GERADORA DE PDF (MARCA D'ÁGUA CENTRALIZADA)
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

  def desenhar_marca_dagua(canvas, doc_obj):
    if logo_path:
      canvas.saveState()
      canvas.setFillAlpha(0.08)
      canvas.drawImage(
          logo_path,
          126,
          420,
          width=360,
          height=200,
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
  if logo_path:
    st.image(logo_path, width=180)

  st.title("Sistema de Recebimento Hortifrúti")
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

  if user_info["perfil"] == "Gestor":
    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
    total_romaneios_db = pd.read_sql_query(
        "SELECT COUNT(*) as qtd FROM romaneios", conn
    ).iloc[0]["qtd"]
    conn.close()

    st.sidebar.divider()
    st.sidebar.markdown(
        f"🔔 **Painel de Alertas:**<br>📦 Total de Romaneios Registrados:"
        f" **{total_romaneios_db}**",
        unsafe_allow_html=True,
    )

  if st.sidebar.button("Sair / Logout"):
    st.session_state["usuario_logado"] = None
    st.rerun()

  st.sidebar.divider()

  opcoes_menu = ["Novo Romaneio (Recebimento)", "Consultar Romaneios"]
  if user_info["perfil"] == "Gestor":
    opcoes_menu.extend([
        "Relatórios & Gráficos",
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
              "A quantidade/peso do produto é obrigatoria e deve ser maior"
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

        total_romaneio_valor = 0.0
        for item in st.session_state["itens_romaneio"]:
          total_romaneio_valor += item["valor_total"]
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

        enviar_notificacao_whatsapp(
            num_romaneio, loja, fornecedor, total_romaneio_valor, conferente
        )

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

  # --- MÓDULO 3: RELATÓRIOS E GRÁFICOS (Gestor Apenas) ---
  elif (
      menu == "Relatórios & Gráficos"
      and user_info["perfil"] == "Gestor"
  ):
    st.title("📊 Relatórios de Recebimentos e Análise Gráfica")

    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
    query_geral = """
        SELECT r.numero_romaneio, r.loja, r.data_recebimento, r.fornecedor, r.conferente,
               i.produto, i.quantidade, i.unidade, i.valor_unitario, i.valor_total
        FROM romaneios r
        JOIN romaneio_itens i ON r.id = i.romaneio_id
    """
    df_completo = pd.read_sql_query(query_geral, conn)
    conn.close()

    if not df_completo.empty:
      df_completo["data_dt"] = pd.to_datetime(
          df_completo["data_recebimento"], format="%d/%m/%Y", errors="coerce"
      )

      st.subheader("⚙️ Filtros de Pesquisa")
      col_f1, col_f2, col_f3 = st.columns(3)
      with col_f1:
        min_date = (
            df_completo["data_dt"].min().date()
            if not df_completo["data_dt"].isna().all()
            else datetime.now().date()
        )
        max_date = (
            df_completo["data_dt"].max().date()
            if not df_completo["data_dt"].isna().all()
            else datetime.now().date()
        )
        data_inicio = st.date_input(
            "Data Inicial", value=min_date, format="DD/MM/YYYY"
        )
      with col_f2:
        data_fim = st.date_input(
            "Data Final", value=max_date, format="DD/MM/YYYY"
        )
      with col_f3:
        lojas_disponiveis = ["Todas"] + list(df_completo["loja"].unique())
        loja_filtro = st.selectbox("Filtrar por Loja", lojas_disponiveis)

      mask = (df_completo["data_dt"].dt.date >= data_inicio) & (
          df_completo["data_dt"].dt.date <= data_fim
      )
      if loja_filtro != "Todas":
        mask = mask & (df_completo["loja"] == loja_filtro)

      df_filtrado = df_completo.loc[mask].copy()

      st.divider()

      if not df_filtrado.empty:
        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
          st.metric(
              "Total de Romaneios", df_filtrado["numero_romaneio"].nunique()
          )
        with col_m2:
          st.metric(
              "Volume / Qtd Total",
              f"{df_filtrado['quantidade'].sum():,.3f}",
          )
        with col_m3:
          st.metric(
              "Valor Total Acumulado",
              f"R$ {df_filtrado['valor_total'].sum():,.2f}",
          )

        st.write("")
        tab_r1, tab_r2 = st.tabs(["📋 Tabela de Dados", "📈 Análise Gráfica"])

        with tab_r1:
          st.subheader("Dados Detalhados do Período")
          st.dataframe(df_filtrado.drop(columns=["data_dt"]), width="stretch")

          csv_data = (
              df_filtrado.drop(columns=["data_dt"])
              .to_csv(index=False)
              .encode("utf-8")
          )
          st.download_button(
              label="📥 Baixar Relatório Filtrado (CSV)",
              data=csv_data,
              file_name=f"relatorio_hortifruti_{data_inicio}_a_{data_fim}.csv",
              mime="text/csv",
          )

        with tab_r2:
          st.subheader("Gráficos de Desempenho e Recebimento")

          st.markdown("### 🏢 Custo/Valor Total por Loja")
          df_loja = (
              df_filtrado.groupby("loja")["valor_total"].sum().reset_index()
          )
          st.bar_chart(df_loja.set_index("loja"))

          st.markdown("### 🥦 Top 10 Produtos Mais Recebidos (Qtd/Peso)")
          df_prod = (
              df_filtrado.groupby("produto")["quantidade"]
              .sum()
              .reset_index()
          )
          df_prod = df_prod.sort_values(
              by="quantidade", ascending=False
          ).head(10)
          st.bar_chart(df_prod.set_index("produto"))

          st.markdown("### 🚚 Volume Financeiro por Fornecedor")
          df_forn = (
              df_filtrado.groupby("fornecedor")["valor_total"]
              .sum()
              .reset_index()
          )
          df_forn = df_forn.sort_values(
              by="valor_total", ascending=False
          ).head(10)
          st.bar_chart(df_forn.set_index("fornecedor"))
      else:
        st.warning(
            "Nenhum registro encontrado para o período ou loja selecionados."
        )
    else:
      st.info("Ainda não há romaneios cadastrados para gerar relatórios.")

  # --- MÓDULO 4: GERENCIAR PRODUTOS (Gestor Apenas) ---
  elif (
      menu == "Gerenciar Cadastros (Produtos)"
      and user_info["perfil"] == "Gestor"
  ):
    st.sidebar.subheader("⚙️ Alerta WhatsApp (Grupo)")
    with st.sidebar.expander(
        "Configurar Grupo 'Logística Hortifruti-Nova Cidade'"
    ):
      st.session_state["zap_api_url"] = st.text_input(
          "URL da API / Webhook", value=st.session_state.get("zap_api_url", "")
      )
      st.session_state["zap_token"] = st.text_input(
          "Token / Chave da API",
          value=st.session_state.get("zap_token", ""),
          type="password",
      )
      st.session_state["zap_id_grupo"] = st.text_input(
          "ID do Grupo (Ex: 120363...@g.us)",
          value=st.session_state.get("zap_id_grupo", ""),
      )
      st.success("Configuração do grupo salva em sessão!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🖼️ Gerenciar Logotipos (PDF)")

    arquivos_logos = [
        f
        for f in os.listdir()
        if f.lower().endswith((".png", ".jpg", ".jpeg"))
        and f
        not in [
            "Tela de login.jpeg",
            "Tela de login.jpg",
            "tela_de_login.jpeg",
            "tela_de_login.jpg",
            "login_bg.jpg",
            "login_bg.png",
        ]
    ]

    if arquivos_logos:
      st.sidebar.markdown("---")
      st.sidebar.write("**Logotipos Ativos:**")
      for logo_nome in arquivos_logos:
        col_lg1, col_lg2 = st.sidebar.columns([3, 1])
        with col_lg1:
          st.image(logo_nome, caption=logo_nome, width=80)
        with col_lg2:
          if st.button(
              "🗑️", key=f"del_logo_{logo_nome}", help=f"Excluir {logo_nome}"
          ):
            try:
              os.remove(logo_nome)
              st.sidebar.success(f"Logo '{logo_nome}' excluída!")
              st.rerun()
            except Exception as e:
              st.sidebar.error(f"Erro ao excluir: {e}")
      st.sidebar.markdown("---")

    logo_files = st.sidebar.file_uploader(
        "Enviar Nova(s) Logo(s) (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="logo_upload",
    )
    if logo_files:
      for logo_file in logo_files:
        with open(logo_file.name, "wb") as f:
          f.write(logo_file.getbuffer())
      st.sidebar.success(f"{len(logo_files)} arquivo(s) salvo(s) com sucesso!")
      st.rerun()

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
            cursor.execute(
                "DELETE FROM produtos WHERE id = ?", (prod_dados_sel[0],)
            )
            conn.commit()
            conn.close()
            st.success(f"Produto '{prod_dados_sel[3]}' excluído com sucesso!")
            st.rerun()

  # --- MÓDULO 5: GERENCIAR USUÁRIOS (Gestor Apenas) ---
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
              cursor.execute(
                  "DELETE FROM usuarios WHERE id = ?", (user_dados[0],)
              )
              conn.commit()
              conn.close()
              st.success(f"Usuário '{user_dados[1]}' excluído com sucesso!")
              st.rerun()
