import base64
from datetime import datetime, timedelta
import io
import os
import pandas as pd
from PIL import Image
import plotly.express as px
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
from streamlit_drawable_canvas import st_canvas

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
logo_icon = None
for nome in [
    "logo_romaneio.png.jpg",
    "logo_romaneio.png",
    "logo.png",
    "Tela de login.jpeg",
    "tela_de_login.jpeg",
]:
    if os.path.exists(nome):
        logo_icon = nome
        break
st.set_page_config(
    page_title="Supermercado Supernova Cidade - Recebimento Hortifrúti",
    page_icon=logo_icon if logo_icon else "🥦",
    layout="wide",
)
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# ---------------------------------------------------------
# MODAL PARA VER FOTO EM TELA CHEIA (DIALOG)
# ---------------------------------------------------------
@st.dialog("📷 Visualização da Foto Anexada", width="large")
def exibir_foto_modal(caminho_foto):
    if os.path.exists(caminho_foto):
        st.image(caminho_foto, use_container_width=True, caption="Comprovante / Nota Anexada")
    else:
        st.error("Arquivo de imagem não encontrado no servidor.")

# ---------------------------------------------------------
# 2. ESTILOS CSS DA TELA DE LOGIN E DO PAINEL
# ---------------------------------------------------------
bg_login_path = None
for nome_bg in [
    "Tela-de-login.jpeg.ico",
    "Tela-de-login.jpeg",
    "Tela de login.jpeg",
    "Tela de login.jpeg.jpeg",
    "tela_de_login.jpeg",
]:
    if os.path.exists(nome_bg):
        bg_login_path = nome_bg
        break

if bg_login_path:
    with open(bg_login_path, "rb") as img_f:
        b64_img = base64.b64encode(img_f.read()).decode()
    css_fundo = f"""
        .stApp {{
            background-image: linear-gradient(rgba(27,94,32,0.85), rgba(198,40,40,0.85)), url("data:image/jpeg;base64,{b64_img}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}
    """
else:
    css_fundo = """
        .stApp {
            background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 50%, #C62828 100%) !important;
            background-attachment: fixed !important;
        }
    """

st.markdown(
    f"""
    <style>
    footer, div[data-testid="stToolbar"], div[class*="viewerBadge"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    header[data-testid="stHeader"] {{
        background-color: transparent !important;
    }}
    img[data-testid="stImage"] {{
        background: transparent !important;
        mix-blend-mode: multiply !important;
        filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.4)) !important;
        max-width: 95px !important;
        width: 100% !important;
        height: auto !important;
        margin: 0 auto !important;
        display: block !important;
    }}
    .titulo-logo {{
        font-size: 2.6rem !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
        margin-bottom: 0px !important;
        font-family: 'Arial Black', Gadget, sans-serif !important;
    }}
    .palavra-sup-mercado {{
        color: #2E7D32 !important;
        font-size: 1.35rem !important;
        font-weight: 800 !important;
        font-style: italic !important;
        text-shadow: 
            -1.5px -1.5px 0 #134617, 1.5px -1.5px 0 #134617, -1.5px 1.5px 0 #134617, 1.5px 1.5px 0 #134617,
            2px 2px 3px rgba(0, 0, 0, 0.5) !important;
    }}
    .palavra-super {{
        color: #2E7D32 !important;
        font-style: italic !important;
        text-shadow: 
            -1.5px -1.5px 0 #134617, 1.5px -1.5px 0 #134617, -1.5px 1.5px 0 #134617, 1.5px 1.5px 0 #134617,
            2px 2px 3px rgba(0, 0, 0, 0.5) !important;
    }}
    .palavra-nova {{
        color: #FF3D00 !important;
        font-style: italic !important;
        text-shadow: 
            -1.5px -1.5px 0 #FFEB3B, 1.5px -1.5px 0 #FFEB3B, -1.5px 1.5px 0 #FFEB3B, 1.5px 1.5px 0 #FFEB3B,
            -3px -3px 0 #B71C1C, 3px -3px 0 #B71C1C, -3px 3px 0 #B71C1C, 3px 3px 0 #B71C1C,
            3px 3px 5px rgba(0, 0, 0, 0.6) !important;
    }}
    .palavra-cidade {{
        color: #111111 !important;
        font-style: italic !important;
        font-family: 'Brush Script MT', cursive, sans-serif !important;
        font-size: 3.2rem !important;
        text-shadow: 2px 3px 4px rgba(0, 0, 0, 0.8), -1.5px -1.5px 0 #FFF, 1.5px -1.5px 0 #FFF, -1.5px 1.5px 0 #FFF, 1.5px 1.5px 0 #FFF !important;
    }}
    .stApp h3 {{
        color: #000000 !important;
        text-shadow: -1px -1px 0 #FFF, 1px -1px 0 #FFF, -1px 1px 0 #FFF, 1px 1px 0 #FFF, 2px 2px 4px rgba(255,255,255,0.9) !important;
        font-weight: 800 !important;
        font-size: 1.3rem !important;
        margin-top: 2px !important;
        margin-bottom: 8px !important;
    }}
    .stApp label {{
        color: #FFFFFF !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.9) !important;
        font-size: 15px !important;
        font-weight: bold !important;
    }}
    div[data-baseweb="input"] input {{
        color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 6px !important;
        font-size: 15px !important;
    }}
    button[kind="primary"], .stButton > button[kind="primary"] {{
        background-color: #1B5E20 !important;
        color: #FFFFFF !important;
        border: 2px solid #FFFFFF !important;
        font-weight: bold !important;
        font-size: 16px !important;
        border-radius: 8px !important;
        width: 100% !important;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.4) !important;
    }}
    button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {{
        background-color: #2E7D32 !important;
        border-color: #FFFFFF !important;
    }}
    {css_fundo}
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. BANCO DE DADOS E CATÁLOGO
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
            caminho_foto TEXT,
            assinatura_conferente TEXT,
            assinatura_entregador TEXT
        )
    """)
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
    
    cursor.execute("SELECT * FROM usuarios WHERE login = '908'")
    if not cursor.fetchone():
        cursor.execute("DELETE FROM usuarios WHERE login = 'admin'")
        cursor.execute(
            "INSERT INTO usuarios (nome, login, senha, perfil) VALUES"
            " ('Administrador', '908', '0332', 'Gestor')"
        )
    conn.commit()
    conn.close()

init_db()

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

def fmt_ptbr(val, decimais=2):
    try:
        f = float(val)
        s = f"{f:,.3f}" if decimais == 3 else f"{f:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"

def remover_fundo_branco(caminho_imagem):
    if not caminho_imagem or not os.path.exists(caminho_imagem):
        return caminho_imagem
    try:
        img = Image.open(caminho_imagem).convert("RGBA")
        datas = img.getdata()
        newData = []
        for item in datas:
            if item[0] > 200 and item[1] > 200 and item[2] > 200:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        img.putdata(newData)
        caminho_transparente = caminho_imagem.replace(".png", "_transp.png")
        img.save(caminho_transparente, "PNG")
        return caminho_transparente
    except Exception:
        return caminho_imagem

# ---------------------------------------------------------
# 4. GERADOR DE PDF DE ROMANEIO
# ---------------------------------------------------------
def gerar_pdf_romaneio(romaneio_data, itens_data, path_conf=None, path_ent=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    story = []
    styles = getSampleStyleSheet()
    
    style_left = ParagraphStyle('Left', parent=styles['Normal'], alignment=0, fontName='Helvetica', fontSize=9)
    style_center = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontName='Helvetica', fontSize=9)
    style_header_left = ParagraphStyle('HLeft', parent=styles['Normal'], alignment=0, fontName='Helvetica-Bold', fontSize=9, textColor=colors.whitesmoke)
    style_header_center = ParagraphStyle('HCenter', parent=styles['Normal'], alignment=1, fontName='Helvetica-Bold', fontSize=9, textColor=colors.whitesmoke)
    
    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio.png", "logo_romaneio", "logo", "Tela de login", "tela_de_login"]:
            pos_p = f"{prefixo}.{ext}" if not prefixo.endswith(f".{ext}") else prefixo
            if os.path.exists(pos_p):
                logo_path = pos_p
                break
        if logo_path:
            break

    def add_watermark(canvas_obj, doc_obj):
        if logo_path and os.path.exists(logo_path):
            canvas_obj.saveState()
            try:
                canvas_obj.setFillAlpha(0.12)
                canvas_obj.drawImage(
                    logo_path,
                    letter[0] / 2 - 140,
                    letter[1] / 2 + 30,
                    width=280,
                    height=280,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass
            canvas_obj.restoreState()

    if logo_path and os.path.exists(logo_path):
        logo_img_header = RLImage(logo_path, width=70, height=50)
    else:
        logo_img_header = Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])

    header_table = Table(
        [
            [
                logo_img_header,
                Paragraph(
                    "<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>Romaneio de Recebimento - Hortifrúti",
                    styles["Normal"],
                ),
                Paragraph(
                    f"<b>ROM:</b> {romaneio_data['numero_romaneio']}<br/><b>Data:</b> {romaneio_data['data_recebimento']}",
                    styles["Normal"],
                ),
            ]
        ],
        colWidths=[80, 300, 160],
    )
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 10))
    info_data = [
        [
            Paragraph(f"<b>Fornecedor:</b> {romaneio_data.get('fornecedor','')}", styles["Normal"]),
            Paragraph(f"<b>Cód. Fornecedor:</b> {romaneio_data.get('codigo_fornecedor','')}", styles["Normal"]),
        ],
        [
            Paragraph(f"<b>Telefone:</b> {romaneio_data.get('telefone_fornecedor','')}", styles["Normal"]),
            Paragraph(f"<b>Loja:</b> {romaneio_data.get('loja','')}", styles["Normal"]),
        ],
        [
            Paragraph(f"<b>Conferente:</b> {romaneio_data.get('conferente','')}", styles["Normal"]),
            Paragraph(f"<b>Pagamento à Vista:</b> {romaneio_data.get('pagamento_a_vista','')}", styles["Normal"]),
        ],
    ]
    if romaneio_data.get("pagamento_a_vista") == "NÃO" and romaneio_data.get("data_pagamento"):
        info_data.append([
            Paragraph(f"<b>Data para Pagamento:</b> {romaneio_data.get('data_pagamento','')}", styles["Normal"]),
            Paragraph("", styles["Normal"]),
        ])
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
        ])
    )
    story.append(info_table)
    story.append(Spacer(1, 15))
    table_content = [
        [
            Paragraph("Item", style_header_center),
            Paragraph("Descrição do Produto", style_header_left),
            Paragraph("Qtd / Peso", style_header_center),
            Paragraph("UND", style_header_center),
            Paragraph("Vl. Unit", style_header_left),
            Paragraph("Total", style_header_left)
        ]
    ]
    
    total_geral = 0.0
    for idx, item in enumerate(itens_data, 1):
        v_unit = float(item[4]) if len(item) > 4 and item[4] is not None else 0.0
        v_tot = float(item[5]) if len(item) > 5 and item[5] is not None else 0.0
        qtd_val = float(item[2]) if len(item) > 2 and item[2] is not None else 0.0
        total_geral += v_tot
        
        table_content.append([
            Paragraph(str(idx), style_center),
            Paragraph(str(item[1]), style_left),
            Paragraph(fmt_ptbr(qtd_val, 3), style_center),
            Paragraph(str(item[3]), style_center),
            Paragraph(f"R$ {fmt_ptbr(v_unit, 2)}", style_left),
            Paragraph(f"R$ {fmt_ptbr(v_tot, 2)}", style_left),
        ])
        
    itens_table = Table(table_content, colWidths=[35, 215, 75, 50, 75, 90])
    itens_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ])
    )
    story.append(itens_table)
    story.append(Spacer(1, 8))
    total_table = Table(
        [[f"TOTAL GERAL DO ROMANEIO: R$ {fmt_ptbr(total_geral, 2)}"]], colWidths=[540]
    )
    total_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#C62828")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(total_table)
    story.append(Spacer(1, 15))
    
    path_conf_transp = remover_fundo_branco(path_conf)
    path_ent_transp = remover_fundo_branco(path_ent)
    img_conf_pdf = None
    if path_conf_transp and os.path.exists(path_conf_transp):
        try:
            img_conf_pdf = RLImage(path_conf_transp, width=180, height=45)
        except Exception:
            pass
    img_ent_pdf = None
    if path_ent_transp and os.path.exists(path_ent_transp):
        try:
            img_ent_pdf = RLImage(path_ent_transp, width=180, height=45)
        except Exception:
            pass
            
    col_conf_cell = [
        img_conf_pdf if img_conf_pdf else Spacer(1, 45),
        Paragraph(f"<b>Assinatura do Conferente:</b><br/>{romaneio_data.get('conferente','')}", styles["Normal"]),
    ]
    col_ent_cell = [
        img_ent_pdf if img_ent_pdf else Spacer(1, 45),
        Paragraph(f"<b>Assinatura do Entregador / Fornecedor:</b><br/>{romaneio_data.get('fornecedor','')}", styles["Normal"]),
    ]
    ass_table = Table([[col_conf_cell, col_ent_cell]], colWidths=[270, 270])
    ass_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    story.append(ass_table)
    doc.build(story, onFirstPage=add_watermark, onLaterPages=add_watermark)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# 4B. GERADOR DE PDF DE RELATÓRIO DE PRODUTOS CADASTRADOS
# ---------------------------------------------------------
def gerar_pdf_produtos(produtos_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )
    story = []
    styles = getSampleStyleSheet()
    
    style_left = ParagraphStyle('Left', parent=styles['Normal'], alignment=0, fontName='Helvetica', fontSize=9)
    style_center = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontName='Helvetica', fontSize=9)
    style_header_left = ParagraphStyle('HLeft', parent=styles['Normal'], alignment=0, fontName='Helvetica-Bold', fontSize=9, textColor=colors.whitesmoke)
    style_header_center = ParagraphStyle('HCenter', parent=styles['Normal'], alignment=1, fontName='Helvetica-Bold', fontSize=9, textColor=colors.whitesmoke)
    
    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio.png", "logo_romaneio", "logo", "Tela de login", "tela_de_login"]:
            pos_p = f"{prefixo}.{ext}" if not prefixo.endswith(f".{ext}") else prefixo
            if os.path.exists(pos_p):
                logo_path = pos_p
                break
        if logo_path:
            break

    def add_watermark(canvas_obj, doc_obj):
        if logo_path and os.path.exists(logo_path):
            canvas_obj.saveState()
            try:
                canvas_obj.setFillAlpha(0.12)
                canvas_obj.drawImage(
                    logo_path,
                    letter[0] / 2 - 140,
                    letter[1] / 2 + 30,
                    width=280,
                    height=280,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass
            canvas_obj.restoreState()

    if logo_path and os.path.exists(logo_path):
        logo_img_header = RLImage(logo_path, width=70, height=50)
    else:
        logo_img_header = Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])

    header_table = Table(
        [
            [
                logo_img_header,
                Paragraph(
                    "<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>Relatório de Produtos Cadastrados - Almoxarifado / Hortifrúti",
                    styles["Normal"],
                ),
                Paragraph(
                    f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y')}<br/><b>Total:</b> {len(produtos_data)}",
                    styles["Normal"],
                ),
            ]
        ],
        colWidths=[80, 310, 150],
    )
    header_table.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey),
        ])
    )
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    table_content = [
        [
            Paragraph("Item", style_header_center),
            Paragraph("Cód. Produto", style_header_center),
            Paragraph("Código de Barras", style_header_center),
            Paragraph("Nome do Produto", style_header_left),
            Paragraph("UND", style_header_center)
        ]
    ]
    
    for idx, p in enumerate(produtos_data, 1):
        table_content.append([
            Paragraph(str(idx), style_center),
            Paragraph(str(p[2] or "S/N"), style_center),
            Paragraph(str(p[1] or "S/N"), style_center),
            Paragraph(str(p[3]), style_left),
            Paragraph(str(p[4]), style_center),
        ])
        
    prod_table = Table(table_content, colWidths=[35, 95, 125, 235, 50])
    prod_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ])
    )
    story.append(prod_table)
    doc.build(story, onFirstPage=add_watermark, onLaterPages=add_watermark)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# 5. TELA DE LOGIN (ESTILO ORIGINAL DA ETAPA 2)
# ---------------------------------------------------------
if st.session_state["usuario_logado"] is None:
    logo_display = None
    for nome in ["logo_romaneio.png.jpg", "logo_romaneio.png", "logo.png", "Tela de login.jpeg"]:
        if os.path.exists(nome):
            logo_display = nome
            break
    col_vazia_esq, col_central, col_vazia_dir = st.columns([0.2, 3.6, 0.2])
    with col_central:
        if logo_display:
            col_logo, col_titulo = st.columns([0.45, 3.55], vertical_alignment="center")
            with col_logo:
                st.image(logo_display, use_container_width=True)
            with col_titulo:
                st.markdown(
                    """<div class='titulo-logo'>
                    <span class='palavra-sup-mercado'>Supermercado</span><br>
                    <span class='palavra-super'>SUPER</span> 
                    <span class='palavra-nova'>NOVA</span><br>
                    <span class='palavra-cidade'>Cidade</span>
                    </div>""",
                    unsafe_allow_html=True
                )
                st.markdown("<h3>Sistema de Recebimento Hortifrúti</h3>", unsafe_allow_html=True)
        else:
            st.markdown(
                """<div class='titulo-logo'>
                <span class='palavra-sup-mercado'>Supermercado</span><br>
                <span class='palavra-super'>SUPER</span> 
                <span class='palavra-nova'>NOVA</span><br>
                <span class='palavra-cidade'>Cidade</span>
                </div>""",
                unsafe_allow_html=True
            )
            st.markdown("<h3>Sistema de Recebimento Hortifrúti</h3>", unsafe_allow_html=True)
        with st.form("form_login"):
            login_input = st.text_input("Usuário / Login")
            senha_input = st.text_input("Senha", type="password")
            btn_entrar = st.form_submit_button("Entrar no Sistema", type="primary")
            if btn_entrar:
                usuario = fazer_login(login_input, senha_input)
                if usuario:
                    st.session_state["usuario_logado"] = {
                        "id": usuario[0],
                        "nome": usuario[1],
                        "perfil": usuario[2],
                        "login": login_input,
                    }
                    st.success(f"Bem-vindo(a), {usuario[1]}!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
else:
    # ---------------------------------------------------------
    # 6. PAINEL INTERNO COMPLETO
    # ---------------------------------------------------------
    user_info = st.session_state["usuario_logado"]
    perfil_db = str(user_info.get("perfil", "")).strip().lower()
    is_admin = (
        user_info["login"].lower() == "908"
        or "gestor" in perfil_db
        or "adm" in perfil_db
    )
    
    st.markdown("---")
    col_info_usr, col_logout = st.columns([4, 1], vertical_alignment="center")
    with col_info_usr:
        tipo_perfil_txt = "🔒 Gestor / Administrador" if is_admin else "👤 Conferente"
        st.markdown(f"**Usuário:** {user_info['nome']} &nbsp;|&nbsp; **Perfil:** {tipo_perfil_txt}")
    with col_logout:
        if st.button("🚪 Sair", type="secondary", key="btn_sair_sistema_principal"):
            st.session_state["usuario_logado"] = None
            st.rerun()
            
    opcoes_menu = ["Romaneio de Recebimento - Hortifrúti", "Consultar Romaneios"]
    if is_admin:
        opcoes_menu.extend([
            "Relatórios & Gráficos",
            "Gerenciar Cadastros (Produtos)",
            "Gerenciar Usuários & Permissões",
        ])
    
    menu = st.radio("Menu de Navegação Principal", opcoes_menu, horizontal=True, label_visibility="collapsed")
    st.markdown("---")
    
    if menu == "Romaneio de Recebimento - Hortifrúti":
        st.title("Romaneio de Recebimento - Hortifrúti")
        if "form_key_suffix" not in st.session_state:
            st.session_state["form_key_suffix"] = 0
        if "item_key_suffix" not in st.session_state:
            st.session_state["item_key_suffix"] = 0
        k_suffix = st.session_state["form_key_suffix"]
        i_suffix = st.session_state["item_key_suffix"]
        
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT nome, unidade_padrao, codigo_produto, codigo_barras FROM"
            " produtos ORDER BY nome"
        )
        produtos_lista = cursor.fetchall()
        conn.close()
        
        prod_dict = {}
        for p in produtos_lista:
            label = f"{p[0]} | Cód: {p[2] or 'S/N'} | Barras: {p[3] or 'S/N'}"
            prod_dict[label] = (p[0], p[1] if p[1] else "KG")
            
        prod_nomes_keys = list(prod_dict.keys())
        with st.expander("1. Cabeçalho do Recebimento", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                num_romaneio = st.text_input(
                    "Número do Romaneio",
                    value=f"ROM-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    key=f"num_rom_{k_suffix}",
                )
                loja = st.selectbox(
                    "Loja",
                    [
                        "LOJA 01 CD",
                        "LOJA 02 NOVA CIDADE",
                        "LOJA 03 TERRA NOVA",
                        "LOJA 04 MANOA",
                        "LOJA 05 ZUMBI",
                        "LOJA 06 OSWALDO FROTA",
                        "LOJA 07 MOSAICO",
                    ],
                    index=1,
                    key=f"loja_{k_suffix}",
                )
            with col2:
                data_rec_val = st.date_input(
                    "Data do Recebimento (Obrigatório)",
                    value=None,
                    format="DD/MM/YYYY",
                    key=f"data_rec_{k_suffix}",
                )
                data_rec_str = data_rec_val.strftime("%d/%m/%Y") if data_rec_val else ""
                fornecedor = st.text_input("Fornecedor / Entregador", key=f"forn_{k_suffix}")
            with col3:
                cod_fornecedor = st.text_input("Código do Fornecedor", key=f"cod_forn_{k_suffix}")
                
                tel_key = f"tel_input_{k_suffix}"
                if tel_key not in st.session_state:
                    st.session_state[tel_key] = ""
                def formatar_tel():
                    val = st.session_state.get(tel_key, "")
                    raw = "".join(filter(str.isdigit, val))
                    if len(raw) > 11:
                        raw = raw[:11]
                    
                    fmt = ""
                    if len(raw) > 0:
                        fmt += f"({raw[:2]}"
                    if len(raw) >= 3:
                        fmt += f") {raw[2:7]}"
                    if len(raw) >= 8:
                        fmt += f"-{raw[7:]}"
                    st.session_state[tel_key] = fmt
                tel_fornecedor = st.text_input(
                    "Telefone do Fornecedor",
                    placeholder="",
                    key=tel_key,
                    on_change=formatar_tel,
                )
            pag_a_vista = st.selectbox("Pagamento à Vista?", ["SIM", "NÃO"], key=f"pag_vista_{k_suffix}")
            
            data_pag_str = ""
            if pag_a_vista == "NÃO":
                data_pag_val = st.date_input(
                    "Data para Pagamento (Obrigatório)",
                    value=None,
                    format="DD/MM/YYYY",
                    key=f"data_pag_{k_suffix}",
                )
                data_pag_str = data_pag_val.strftime("%d/%m/%Y") if data_pag_val else ""
            conferente = st.text_input(
                "Responsável Rec. Físico",
                value=user_info["nome"],
                disabled=True,
                key=f"conf_{k_suffix}",
            )
            
        st.subheader("2. Itens do Recebimento")
        if "itens_romaneio" not in st.session_state:
            st.session_state["itens_romaneio"] = []
        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns(
            [3, 1.5, 1.5, 1.5, 1]
        )
        with col_p1:
            prod_label_sel = st.selectbox(
                "Produto / Código",
                options=prod_nomes_keys,
                index=None,
                placeholder="",
                key=f"prod_sel_{k_suffix}_{i_suffix}",
            )
            prod_nome_real = (
                prod_dict[prod_label_sel][0] if prod_label_sel and prod_dict else ""
            )
        with col_p2:
            und_padrao = (
                prod_dict[prod_label_sel][1]
                if prod_label_sel and prod_dict
                else "KG"
            )
            und_sel = st.selectbox(
                "UND",
                ["KG", "UNID", "GRM", "CX"],
                index=(
                    ["KG", "UNID", "GRM", "CX"].index(und_padrao)
                    if und_padrao in ["KG", "UNID", "GRM", "CX"]
                    else 0
                ),
                key=f"und_sel_{k_suffix}_{i_suffix}",
            )
        with col_p3:
            qtd_str_input = st.text_input(
                "Qtd / Peso",
                value="",
                placeholder="",
                key=f"qtd_{k_suffix}_{i_suffix}",
            )
        with col_p4:
            val_unit_str_input = st.text_input(
                "Valor Unit. (R$)",
                value="",
                placeholder="",
                key=f"vunit_{k_suffix}_{i_suffix}",
            )
        with col_p5:
            st.write("")
            st.write("")
            if st.button("➕ Add", type="primary", key=f"btn_add_{k_suffix}_{i_suffix}"):
                try:
                    qtd_limpa = qtd_str_input.replace(".", "").replace(",", ".") if qtd_str_input else "0"
                    qtd_input = float(qtd_limpa)
                except ValueError:
                    qtd_input = 0.0
                try:
                    vunit_limpo = val_unit_str_input.replace(".", "").replace(",", ".") if val_unit_str_input else "0"
                    val_unit_val = float(vunit_limpo)
                except ValueError:
                    val_unit_val = 0.0
                if not prod_nome_real:
                    st.warning("Selecione um produto antes de adicionar.")
                elif qtd_input <= 0:
                    st.warning("Informe uma quantidade maior que zero.")
                else:
                    v_tot = qtd_input * val_unit_val
                    st.session_state["itens_romaneio"].append({
                        "produto": prod_nome_real,
                        "quantidade": qtd_input,
                        "unidade": und_sel,
                        "valor_unitario": val_unit_val,
                        "valor_total": v_tot,
                    })
                    st.session_state["item_key_suffix"] += 1
                    st.rerun()
                    
        if st.session_state["itens_romaneio"]:
            st.markdown("**Itens adicionados:**")
            
            dados_tabela = []
            for i, itm in enumerate(st.session_state["itens_romaneio"], 1):
                dados_tabela.append({
                    "Item": i,
                    "Descrição do Produto": itm["produto"],
                    "Qtd / Peso": fmt_ptbr(itm['quantidade'], 3),
                    "UND": itm["unidade"],
                    "Vl. Unit": f"R$ {fmt_ptbr(itm['valor_unitario'], 2)}",
                    "Total": f"R$ {fmt_ptbr(itm['valor_total'], 2)}"
                })
            df_exibicao = pd.DataFrame(dados_tabela)
            
            st.dataframe(
                df_exibicao,
                use_container_width=True,
                hide_index=True,
            )
            
            col_rem_labels, col_rem_btns = st.columns([3, 1])
            with col_rem_labels:
                item_para_remover = st.selectbox(
                    "Selecionar Item para Remover",
                    options=range(1, len(st.session_state["itens_romaneio"]) + 1),
                    format_func=lambda x: f"Item {x}: {st.session_state['itens_romaneio'][x-1]['produto']}",
                    key=f"sel_rem_{k_suffix}"
                )
            with col_rem_btns:
                st.write("")
                st.write("")
                if st.button("🗑️ Remover", key=f"btn_rem_esp_{k_suffix}", type="secondary"):
                    st.session_state["itens_romaneio"].pop(item_para_remover - 1)
                    st.rerun()
            total_geral_temp = sum(itm['valor_total'] for itm in st.session_state["itens_romaneio"])
            st.markdown(f"### **Total Geral: R$ {fmt_ptbr(total_geral_temp, 2)}**")
            
            if st.button("🗑️ Limpar Todos os Itens", type="secondary", key=f"btn_del_itens_{k_suffix}"):
                st.session_state["itens_romaneio"] = []
                st.rerun()
                
        st.subheader("3. Anexo de Fotos / Comprovantes")
        fotos_upload = st.file_uploader(
            "Fotos da Nota / Canhoto",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=f"fotos_{k_suffix}",
        )
        
        st.subheader("4. Assinatura Digital")
        col_ass1, col_ass2 = st.columns(2)
        with col_ass1:
            st.write("**Assinatura do Conferente**")
            canvas_conf = st_canvas(
                stroke_width=3,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=120,
                width=280,
                drawing_mode="freedraw",
                return_image_data=True,
                key=f"canv_conf_{k_suffix}",
            )
        with col_ass2:
            st.write("**Assinatura do Entregador / Fornecedor**")
            canvas_ent = st_canvas(
                stroke_width=3,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=120,
                width=280,
                drawing_mode="freedraw",
                return_image_data=True,
                key=f"canv_ent_{k_suffix}",
            )
            
        if st.button("✅ Salvar Romaneio", type="primary", key=f"btn_salvar_{k_suffix}"):
            if not num_romaneio.strip() or not fornecedor.strip():
                st.error("Preencha o número do romaneio e o fornecedor.")
            elif not data_rec_str:
                st.error("A Data do Recebimento é obrigatória! Selecione a data no calendário.")
            elif pag_a_vista == "NÃO" and not data_pag_str:
                st.error("A Data para Pagamento é obrigatória para compras a prazo! Selecione a data.")
            elif not st.session_state["itens_romaneio"]:
                st.error("Adicione itens ao romaneio.")
            else:
                try:
                    if not os.path.exists("uploads"):
                        os.makedirs("uploads")
                    path_ass_conf = ""
                    if canvas_conf.image_data is not None:
                        img_c = Image.fromarray(canvas_conf.image_data.astype("uint8"))
                        path_ass_conf = os.path.join("uploads", f"ass_conf_{num_romaneio}.png")
                        img_c.save(path_ass_conf)
                    
                    path_ass_ent = ""
                    if canvas_ent.image_data is not None:
                        img_e = Image.fromarray(canvas_ent.image_data.astype("uint8"))
                        path_ass_ent = os.path.join("uploads", f"ass_ent_{num_romaneio}.png")
                        img_e.save(path_ass_ent)
                    
                    caminho_foto_salva = ""
                    if fotos_upload:
                        for f in fotos_upload:
                            path_f = os.path.join("uploads", f.name)
                            with open(path_f, "wb") as f_out:
                                f_out.write(f.getbuffer())
                            caminho_foto_salva = path_f
                    
                    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO romaneios (
                            numero_romaneio, loja, data_recebimento, fornecedor, 
                            codigo_fornecedor, telefone_fornecedor, conferente, 
                            pagamento_a_vista, data_pagamento, caminho_foto,
                            assinatura_conferente, assinatura_entregador
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            num_romaneio,
                            loja,
                            data_rec_str,
                            fornecedor,
                            cod_fornecedor,
                            tel_fornecedor,
                            user_info["nome"],
                            pag_a_vista,
                            data_pag_str,
                            caminho_foto_salva,
                            path_ass_conf,
                            path_ass_ent,
                        ),
                    )
                    romaneio_id = cursor.lastrowid
                    itens_salvos_pdf = []
                    for itm in st.session_state["itens_romaneio"]:
                        cursor.execute(
                            """
                            INSERT INTO romaneio_itens (
                                romaneio_id, produto, quantidade, unidade, valor_unitario, valor_total
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (
                                romaneio_id,
                                itm["produto"],
                                itm["quantidade"],
                                itm["unidade"],
                                itm["valor_unitario"],
                                itm["valor_total"],
                            ),
                        )
                        itens_salvos_pdf.append([
                            None,
                            itm["produto"],
                            itm["quantidade"],
                            itm["unidade"],
                            itm["valor_unitario"],
                            itm["valor_total"],
                        ])
                    conn.commit()
                    conn.close()
                    
                    romaneio_dict_atual = {
                        "numero_romaneio": num_romaneio,
                        "data_recebimento": data_rec_str,
                        "fornecedor": fornecedor,
                        "codigo_fornecedor": cod_fornecedor,
                        "telefone_fornecedor": tel_fornecedor,
                        "loja": loja,
                        "conferente": user_info["nome"],
                        "pagamento_a_vista": pag_a_vista,
                        "data_pagamento": data_pag_str,
                    }
                    
                    pdf_buffer_novo = gerar_pdf_romaneio(
                        romaneio_dict_atual, itens_salvos_pdf, path_ass_conf, path_ass_ent
                    )
                    
                    st.session_state["ultimo_pdf_bytes"] = pdf_buffer_novo.getvalue()
                    st.session_state["ultimo_num_romaneio"] = num_romaneio
                    
                    st.session_state["itens_romaneio"] = []
                    st.session_state["form_key_suffix"] += 1
                    st.session_state["item_key_suffix"] = 0
                    st.success(f"Romaneio {num_romaneio} salvo com sucesso!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao salvar romaneio: {e}")
                    
        if "ultimo_pdf_bytes" in st.session_state and "ultimo_num_romaneio" in st.session_state:
            st.markdown("---")
            st.success(f"📄 Romaneio **{st.session_state['ultimo_num_romaneio']}** pronto para download!")
            st.download_button(
                label=f"📥 Baixar PDF - {st.session_state['ultimo_num_romaneio']}",
                data=st.session_state["ultimo_pdf_bytes"],
                file_name=f"{st.session_state['ultimo_num_romaneio']}.pdf",
                mime="application/pdf",
                type="primary",
            )
            
    elif menu == "Consultar Romaneios":
        st.title("🔍 Consulta de Romaneios")
        
        with st.expander("🔍 Filtrar Romaneios", expanded=True):
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            with col_f1:
                filtro_num = st.text_input("Número do Romaneio", placeholder="Ex: ROM-...")
            with col_f2:
                filtro_forn = st.text_input("Fornecedor / Entregador", placeholder="Nome do fornecedor")
            with col_f3:
                filtro_cod_forn = st.text_input("Código do Fornecedor", placeholder="Cód. fornecedor")
            with col_f4:
                filtro_data_val = st.date_input("Data do Recebimento", value=None, format="DD/MM/YYYY")
                filtro_data_str = filtro_data_val.strftime("%d/%m/%Y") if filtro_data_val else ""
                
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_rom = pd.read_sql_query("SELECT * FROM romaneios ORDER BY id DESC", conn)
        conn.close()
        
        if not df_rom.empty:
            if filtro_num.strip():
                df_rom = df_rom[df_rom["numero_romaneio"].str.contains(filtro_num.strip(), case=False, na=False)]
            if filtro_forn.strip():
                df_rom = df_rom[df_rom["fornecedor"].str.contains(filtro_forn.strip(), case=False, na=False)]
            if filtro_cod_forn.strip():
                df_rom = df_rom[df_rom["codigo_fornecedor"].astype(str).str.contains(filtro_cod_forn.strip(), case=False, na=False)]
            if filtro_data_str:
                df_rom = df_rom[df_rom["data_recebimento"] == filtro_data_str]
                
        if not df_rom.empty:
            st.markdown(f"**Total de romaneios encontrados:** {len(df_rom)}")
            st.markdown("---")
            for idx, row in df_rom.iterrows():
                fornecedor_txt = row['fornecedor'] if row['fornecedor'] else 'N/A'
                if row['codigo_fornecedor'] and str(row['codigo_fornecedor']).strip():
                    fornecedor_txt += f" (Cód: {row['codigo_fornecedor']})"
                with st.expander(
                    f"Romaneio: {row['numero_romaneio']} | Fornecedor:"
                    f" {fornecedor_txt} | Data: {row['data_recebimento']}"
                ):
                    st.write(f"**Loja:** {row['loja']}")
                    st.write(
                        f"**Código do Fornecedor:** {row['codigo_fornecedor'] if row['codigo_fornecedor'] else 'N/A'} |"
                        f" **Telefone:** {row['telefone_fornecedor'] if row['telefone_fornecedor'] else 'N/A'}"
                    )
                    st.write(f"**Conferente:** {row['conferente']}")
                    st.write(
                        f"**Pagamento à Vista:** {row['pagamento_a_vista']} |"
                        f" **Data Pagamento:** {row['data_pagamento'] if row['data_pagamento'] else 'N/A'}"
                    )
                    
                    if row['caminho_foto'] and os.path.exists(row['caminho_foto']):
                        st.write("")
                        st.image(row['caminho_foto'], width=280, caption="Foto Anexada (Miniatura)")
                        if st.button("🔍 Ampliar Foto da Nota (Tela Cheia)", key=f"btn_ampliar_foto_{row['id']}"):
                            exibir_foto_modal(row['caminho_foto'])
                            
                    conn_i = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                    df_itens = pd.read_sql_query(
                        "SELECT produto, quantidade, unidade, valor_unitario,"
                        " valor_total FROM romaneio_itens WHERE romaneio_id = ?",
                        conn_i,
                        params=(row["id"],),
                    )
                    conn_i.close()
                    st.markdown("**Itens Conferidos:**")
                    
                    df_itens_ex = df_itens.copy()
                    df_itens_ex['Qtd / Peso'] = df_itens_ex['quantidade'].apply(lambda x: fmt_ptbr(x, 3))
                    df_itens_ex['Vl. Unit'] = df_itens_ex['valor_unitario'].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                    df_itens_ex['Total'] = df_itens_ex['valor_total'].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                    df_itens_ex = df_itens_ex[['produto', 'Qtd / Peso', 'unidade', 'Vl. Unit', 'Total']]
                    df_itens_ex.index = range(1, len(df_itens_ex) + 1)
                    
                    st.dataframe(df_itens_ex, use_container_width=True)
                    
                    total_rom = df_itens["valor_total"].sum()
                    st.markdown(f"**Total do Romaneio: R$ {fmt_ptbr(total_rom, 2)}**")
                    
                    romaneio_dict = row.to_dict()
                    itens_tuple_list = [
                        (None, r['produto'], r['quantidade'], r['unidade'], r['valor_unitario'], r['valor_total'])
                        for _, r in df_itens.iterrows()
                    ]
                    
                    pdf_buffer = gerar_pdf_romaneio(
                        romaneio_dict,
                        itens_tuple_list,
                        row.get("assinatura_conferente"),
                        row.get("assinatura_entregador"),
                    )
                    
                    col_dl, col_del = st.columns([4, 1])
                    with col_dl:
                        st.download_button(
                            label=f"📥 Baixar PDF - {row['numero_romaneio']}",
                            data=pdf_buffer,
                            file_name=f"{row['numero_romaneio']}.pdf",
                            mime="application/pdf",
                            key=f"pdf_btn_cons_{row['id']}",
                        )
                    with col_del:
                        if st.button("🗑️ Excluir Romaneio", key=f"btn_excluir_rom_{row['id']}", type="secondary", help="Excluir este romaneio incorreto/teste"):
                            try:
                                conn_del = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                                cursor_del = conn_del.cursor()
                                cursor_del.execute("DELETE FROM romaneio_itens WHERE romaneio_id = ?", (row["id"],))
                                cursor_del.execute("DELETE FROM romaneios WHERE id = ?", (row["id"],))
                                conn_del.commit()
                                conn_del.close()
                                st.success(f"Romaneio {row['numero_romaneio']} excluído com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir romaneio: {e}")
        else:
            st.info("Nenhum romaneio encontrado com os filtros informados.")
            
    elif menu == "Relatórios & Gráficos" and is_admin:
        st.title("📊 Relatórios e Análise Gerencial de Recebimento")
        
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_roms = pd.read_sql_query("SELECT * FROM romaneios", conn)
        df_itens = pd.read_sql_query("SELECT * FROM romaneio_itens", conn)
        conn.close()
        
        if df_roms.empty or df_itens.empty:
            st.warning("Ainda não existem dados de recebimento cadastrados para gerar relatórios e gráficos. Cadastre alguns romaneios na aba principal para visualizar a análise.")
        else:
            df_roms['data_dt'] = pd.to_datetime(df_roms['data_recebimento'], format='%d/%m/%Y', errors='coerce')
            df_full = df_itens.merge(df_roms, left_on='romaneio_id', right_on='id', suffixes=('_item', '_romaneio'))
            st.markdown("### 🔍 Filtros da Análise Gerencial")
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            
            with col_f1:
                lojas_disp = ["TODAS AS LOJAS"] + list(df_roms["loja"].unique())
                loja_sel = st.selectbox("Filtrar por Loja", lojas_disp, key="rel_filter_loja")
                
            with col_f2:
                prods_disp = ["TODOS OS PRODUTOS"] + sorted(list(df_itens["produto"].unique()))
                prod_sel = st.selectbox("Filtrar por Produto", prods_disp, key="rel_filter_prod")
                
            with col_f3:
                dt_min = df_roms['data_dt'].min() if not df_roms['data_dt'].isna().all() else datetime.now()
                dt_inicio = st.date_input("Data Início", value=dt_min, format="DD/MM/YYYY", key="rel_filter_dt_ini")
                
            with col_f4:
                dt_max = df_roms['data_dt'].max() if not df_roms['data_dt'].isna().all() else datetime.now()
                dt_fim = st.date_input("Data Fim", value=dt_max, format="DD/MM/YYYY", key="rel_filter_dt_fim")
                
            df_filtrado = df_full.copy()
            if loja_sel != "TODAS AS LOJAS":
                df_filtrado = df_filtrado[df_filtrado["loja"] == loja_sel]
            if prod_sel != "TODOS OS PRODUTOS":
                df_filtrado = df_filtrado[df_filtrado["produto"] == prod_sel]
            if dt_inicio and dt_fim:
                df_filtrado = df_filtrado[
                    (df_filtrado["data_dt"] >= pd.to_datetime(dt_inicio)) & 
                    (df_filtrado["data_dt"] <= pd.to_datetime(dt_fim))
                ]
                
            if df_filtrado.empty:
                st.info("Nenhum registro encontrado para os filtros selecionados.")
            else:
                st.markdown("---")
                st.subheader("📈 Indicadores Principais (KPIs)")
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                
                total_val = df_filtrado["valor_total"].sum()
                qtd_roms = df_filtrado["numero_romaneio"].nunique()
                qtd_peso_total = df_filtrado["quantidade"].sum()
                top_fornecedor = (
                    df_filtrado.groupby("fornecedor")["valor_total"].sum().idxmax() 
                    if not df_filtrado.empty else "N/A"
                )
                
                kpi1.metric("Valor Total Recebido", f"R$ {fmt_ptbr(total_val, 2)}")
                kpi2.metric("Total de Romaneios", f"{qtd_roms} romaneios")
                kpi3.metric("Qtd / Peso Total", f"{fmt_ptbr(qtd_peso_total, 3)}")
                kpi4.metric("Principal Fornecedor", str(top_fornecedor))
                st.markdown("---")
                st.subheader("📊 Visualizações Gráficas Profissionais (BI)")
                
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    st.markdown("**Top Produtos por Valor Financeiro (R$)**")
                    top_prods_val = df_filtrado.groupby("produto")["valor_total"].sum().nlargest(10).reset_index()
                    fig_val = px.bar(
                        top_prods_val, 
                        x="produto", 
                        y="valor_total",
                        text_auto=".2f",
                        color="valor_total",
                        color_continuous_scale="Greens"
                    )
                    fig_val.update_layout(
                        xaxis_title="Produto", 
                        yaxis_title="Total (R$)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#FFFFFF",
                        xaxis=dict(tickangle=-35, showgrid=True, gridcolor="rgba(255,255,255,0.2)"),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)")
                    )
                    st.plotly_chart(fig_val, use_container_width=True)
                    
                with col_g2:
                    st.markdown("**Top Produtos por Volume / Quantidade**")
                    top_prods_qtd = df_filtrado.groupby("produto")["quantidade"].sum().nlargest(10).reset_index()
                    fig_qtd = px.bar(
                        top_prods_qtd, 
                        x="produto", 
                        y="quantidade",
                        text_auto=".2f",
                        color="quantidade",
                        color_continuous_scale="Reds"
                    )
                    fig_qtd.update_layout(
                        xaxis_title="Produto", 
                        yaxis_title="Qtd / Peso",
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#FFFFFF",
                        xaxis=dict(tickangle=-35, showgrid=True, gridcolor="rgba(255,255,255,0.2)"),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)")
                    )
                    st.plotly_chart(fig_qtd, use_container_width=True)
                    
                col_g3, col_g4 = st.columns(2)
                with col_g3:
                    st.markdown("**Participação Financeira por Fornecedor (R$)**")
                    forn_val = df_filtrado.groupby("fornecedor")["valor_total"].sum().reset_index()
                    fig_forn = px.bar(
                        forn_val, 
                        x="fornecedor", 
                        y="valor_total",
                        text_auto=".2f",
                        color="valor_total",
                        color_continuous_scale="Viridis"
                    )
                    fig_forn.update_layout(
                        xaxis_title="Fornecedor", 
                        yaxis_title="Total (R$)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#FFFFFF",
                        xaxis=dict(tickangle=-35, showgrid=True, gridcolor="rgba(255,255,255,0.2)"),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)")
                    )
                    st.plotly_chart(fig_forn, use_container_width=True)
                    
                with col_g4:
                    st.markdown("**Evolução Diária dos Recebimentos (R$)**")
                    diario_val = df_filtrado.groupby("data_recebimento")["valor_total"].sum().reset_index()
                    fig_line = px.line(
                        diario_val, 
                        x="data_recebimento", 
                        y="valor_total",
                        markers=True,
                        line_shape="spline"
                    )
                    fig_line.update_traces(line_color="#1B5E20", line_width=3)
                    fig_line.update_layout(
                        xaxis_title="Data do Recebimento", 
                        yaxis_title="Total (R$)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        font_color="#FFFFFF",
                        xaxis=dict(tickangle=-35, showgrid=True, gridcolor="rgba(255,255,255,0.2)"),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.2)")
                    )
                    st.plotly_chart(fig_line, use_container_width=True)
                    
                st.markdown("---")
                st.subheader("📋 Tabela Consolidada & Exportação")
                
                df_export = df_filtrado[[
                    "numero_romaneio", "loja", "data_recebimento", "fornecedor", 
                    "produto", "quantidade", "unidade", "valor_unitario", "valor_total", "conferente"
                ]].copy()
                df_export['quantidade'] = df_export['quantidade'].apply(lambda x: fmt_ptbr(x, 3))
                df_export['valor_unitario'] = df_export['valor_unitario'].apply(lambda x: fmt_ptbr(x, 2))
                df_export['valor_total'] = df_export['valor_total'].apply(lambda x: fmt_ptbr(x, 2))
                
                df_export = df_export.rename(columns={
                    "numero_romaneio": "Romaneio",
                    "loja": "Loja",
                    "data_recebimento": "Data Rec.",
                    "fornecedor": "Fornecedor",
                    "produto": "Produto",
                    "quantidade": "Qtd/Peso",
                    "unidade": "UND",
                    "valor_unitario": "Vl. Unit (R$)",
                    "valor_total": "Vl. Total (R$)",
                    "conferente": "Conferente"
                })
                
                st.dataframe(df_export, use_container_width=True, hide_index=True)
                
                csv_buffer = df_export.to_csv(index=False, sep=';').encode('utf-8-sig')
                st.download_button(
                    label="📥 Baixar Relatório Consolidado (Excel / CSV)",
                    data=csv_buffer,
                    file_name=f"Relatorio_Hortifruti_Supernova_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    type="primary",
                    key="btn_download_csv_relatorio"
                )
    elif menu == "Gerenciar Cadastros (Produtos)" and is_admin:
        st.title("🥦 Gerenciamento e Cadastro de Produtos")
        
        with st.form("cad_prod_form", clear_on_submit=True):
            st.subheader("Cadastrar Novo Produto")
            col_cp1, col_cp2, col_cp3, col_cp4 = st.columns([2, 2, 3, 1.5])
            with col_cp1:
                cod_prod_input = st.text_input("Código do Produto")
            with col_cp2:
                cod_bar_input = st.text_input("Código de Barras")
            with col_cp3:
                nome_p = st.text_input("Nome do Produto (Obrigatório)")
            with col_cp4:
                und_p = st.selectbox("Unidade", ["KG", "UNID", "GRM", "CX"])
                
            btn_cad_prod = st.form_submit_button("➕ Cadastrar Produto", type="primary")
            if btn_cad_prod:
                if not nome_p.strip():
                    st.error("O Nome do Produto é obrigatório.")
                else:
                    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO produtos (codigo_produto, codigo_barras, nome, unidade_padrao) VALUES (?, ?, ?, ?)",
                            (cod_prod_input.strip() if cod_prod_input else None, cod_bar_input.strip() if cod_bar_input else None, nome_p.strip(), und_p),
                        )
                        conn.commit()
                        st.success(f"Produto '{nome_p.strip()}' cadastrado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Erro: Já existe um produto cadastrado com este Nome ou Código.")
                    except Exception as e:
                        st.error(f"Erro ao cadastrar produto: {e}")
                    finally:
                        conn.close()
                        
        st.markdown("---")
        st.subheader("📋 Produtos Cadastrados no Sistema")
        
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT id, codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos ORDER BY nome")
        produtos_cadastrados = cursor.fetchall()
        conn.close()
        
        if produtos_cadastrados:
            produtos_com_id_ajustado = [(i, p[1], p[2], p[3], p[4], p[0]) for i, p in enumerate(produtos_cadastrados, 1)]
            df_produtos = pd.DataFrame(produtos_com_id_ajustado, columns=["ID", "Código de Barras", "Código do Produto", "Nome do Produto", "Unidade Padrão", "ID_Real"])
            
            pdf_produtos_buf = gerar_pdf_produtos(produtos_cadastrados)
            st.download_button(
                label="📥 Baixar Relatório de Produtos em PDF",
                data=pdf_produtos_buf,
                file_name=f"Relatorio_Produtos_Supernova_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                type="primary",
            )
            st.markdown("")
            
            st.dataframe(df_produtos[["ID", "Código do Produto", "Código de Barras", "Nome do Produto", "Unidade Padrão"]], use_container_width=True, hide_index=True)
            
            st.markdown("### 🗑️ Excluir Produto")
            col_ex1, col_ex2 = st.columns([3, 1])
            with col_ex1:
                prod_para_excluir = st.selectbox(
                    "Selecione o produto para excluir",
                    options=produtos_com_id_ajustado,
                    format_func=lambda x: f"ID {x[0]} - {x[3]} (Cód: {x[2] or 'S/N'} | Barras: {x[1] or 'S/N'})"
                )
            with col_ex2:
                st.write("")
                st.write("")
                if st.button("🗑️ Excluir Selecionado", type="secondary", key="btn_del_prod_sel"):
                    try:
                        conn_del = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                        cursor_del = conn_del.cursor()
                        cursor_del.execute("DELETE FROM produtos WHERE id = ?", (prod_para_excluir[5],))
                        conn_del.commit()
                        conn_del.close()
                        st.success(f"Produto '{prod_para_excluir[3]}' excluído com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir produto: {e}")
        else:
            st.info("Nenhum produto cadastrado no momento.")
            
    elif menu == "Gerenciar Usuários & Permissões" and is_admin:
        st.title("👥 Gerenciamento de Usuários e Permissões")
        
        with st.form("cad_usuario_form", clear_on_submit=True):
            st.subheader("Cadastrar Novo Usuário / Conferente")
            col_u1, col_u2, col_u3, col_u4 = st.columns([2.5, 2, 2, 1.5])
            with col_u1:
                novo_nome = st.text_input("Nome Completo do Usuário")
            with col_u2:
                novo_login = st.text_input("Login de Acesso")
            with col_u3:
                nova_senha = st.text_input("Senha", type="password")
            with col_u4:
                novo_perfil = st.selectbox("Perfil", ["Conferente", "Gestor"])
                
            btn_cad_usuario = st.form_submit_button("➕ Cadastrar Usuário", type="primary")
            if btn_cad_usuario:
                if not novo_nome.strip() or not novo_login.strip() or not nova_senha.strip():
                    st.error("Preencha todos os campos obrigatórios para cadastrar o usuário.")
                else:
                    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO usuarios (nome, login, senha, perfil) VALUES (?, ?, ?, ?)",
                            (novo_nome.strip(), novo_login.strip(), nova_senha.strip(), novo_perfil)
                        )
                        conn.commit()
                        st.success(f"Usuário '{novo_nome.strip()}' cadastrado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Erro: Este Login já está em uso por outro usuário.")
                    except Exception as e:
                        st.error(f"Erro ao cadastrar usuário: {e}")
                    finally:
                        conn.close()
                        
        st.markdown("---")
        st.subheader("📋 Usuários Cadastrados no Sistema")
        
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, login, perfil FROM usuarios ORDER BY id")
        usuarios_cadastrados = cursor.fetchall()
        conn.close()
        
        if usuarios_cadastrados:
            usuarios_com_id_ajustado = [(i, u[1], u[2], u[3], u[0]) for i, u in enumerate(usuarios_cadastrados, 1)]
            df_usuarios = pd.DataFrame(usuarios_com_id_ajustado, columns=["ID", "Nome Completo", "Login", "Perfil", "ID_Real"])
            st.dataframe(df_usuarios[["ID", "Nome Completo", "Login", "Perfil"]], use_container_width=True, hide_index=True)
            
            st.markdown("### 🗑️ Excluir Usuário")
            col_ux1, col_ux2 = st.columns([3, 1])
            with col_ux1:
                usr_para_excluir = st.selectbox(
                    "Selecione o usuário para remover o acesso",
                    options=usuarios_com_id_ajustado,
                    format_func=lambda x: f"ID {x[0]} - {x[1]} (Login: {x[2]} - Perfil: {x[3]})",
                    key="sel_usr_del"
                )
            with col_ux2:
                st.write("")
                st.write("")
                if st.button("🗑️ Remover Usuário", type="secondary", key="btn_del_usr_sel"):
                    if str(usr_para_excluir[2]) == "908":
                        st.error("Atenção: Não é permitido excluir o usuário Administrador principal (908)!")
                    else:
                        try:
                            conn_del = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                            cursor_del = conn_del.cursor()
                            cursor_del.execute("DELETE FROM usuarios WHERE id = ?", (usr_para_excluir[4],))
                            conn_del.commit()
                            conn_del.close()
                            st.success(f"Usuário '{usr_para_excluir[1]}' removido com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao remover usuário: {e}")
        else:
            st.info("Nenhum usuário cadastrado.")
