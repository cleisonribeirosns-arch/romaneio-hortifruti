import base64
from datetime import datetime, time, timedelta
import io
import os
import pandas as pd
from PIL import Image
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
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
from zoneinfo import ZoneInfo

# Tenta importar fitz (PyMuPDF) para conversão visual e renderização de PDF em imagem
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Tenta importar psycopg2 para suporte ao PostgreSQL permanente
try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

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
    page_title="HortiControl Supernova - Recebimento Hortifrúti",
    page_icon=logo_icon if logo_icon else "📦",
    layout="wide",
)

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# ---------------------------------------------------------
# CONEXÃO SEGURA COM BANCO DE DADOS
# ---------------------------------------------------------
def get_db_connection():
    if HAS_POSTGRES and "database" in st.secrets and "db_url" in st.secrets["database"]:
        try:
            conn = psycopg2.connect(st.secrets["database"]["db_url"], connect_timeout=5)
            return conn, "postgres"
        except Exception as e:
            st.error(f"Erro crítico ao conectar no PostgreSQL (Neon): {e}")
            raise e
    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
    return conn, "sqlite"

# ---------------------------------------------------------
# FUNÇÃO DE SPINNER / FEEDBACK COM LOGOTIPO DO SUPERNOVA
# ---------------------------------------------------------
def spinner_supernova(mensagem="A carregar dados do Supernova..."):
    logo_path_spin = None
    for nome in ["logo_romaneio.png.jpg", "logo_romaneio.png", "logo.png", "Tela de login.jpeg"]:
        if os.path.exists(nome):
            logo_path_spin = nome
            break
    if logo_path_spin:
        with open(logo_path_spin, "rb") as img_f:
            b64_spin = base64.b64encode(img_f.read()).decode()
        return st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 15px; background: rgba(20, 24, 30, 0.95); padding: 15px 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2); margin: 15px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
            <img src="data:image/jpeg;base64,{b64_spin}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; animation: pulse 1.5s infinite;" />
            <span style="color: #FFFFFF; font-weight: 800; font-size: 15px; letter-spacing: 0.5px;">{mensagem}</span>
        </div>
        <style>
        @keyframes pulse {{
            0% {{ transform: scale(0.95); opacity: 0.8; }}
            50% {{ transform: scale(1.05); opacity: 1; filter: drop-shadow(0 0 8px #4CAF50); }}
            100% {{ transform: scale(0.95); opacity: 0.8; }}
        }}
        </style>
        """, unsafe_allow_html=True)
    else:
        return st.spinner(mensagem)

# ---------------------------------------------------------
# FUNÇÃO DE PERSISTÊNCIA DE ANEXOS (BASE64 NO BANCO)
# ---------------------------------------------------------
def salvar_arquivo_fisico_do_b64(caminho_alvo, b64_str):
    if not caminho_alvo or not b64_str:
        return
    try:
        if not os.path.exists(caminho_alvo) or os.path.getsize(caminho_alvo) == 0:
            diretorio = os.path.dirname(caminho_alvo)
            if diretorio and not os.path.exists(diretorio):
                os.makedirs(diretorio)
            with open(caminho_alvo, "wb") as f_out:
                f_out.write(base64.b64decode(b64_str))
    except Exception:
        pass

# ---------------------------------------------------------
# MODAL DE VISUALIZAÇÃO DE ANEXOS
# ---------------------------------------------------------
@st.dialog("🖼️ Visualizador de Documentos", width="large")
def exibir_foto_modal(caminho_foto, b64_dados=None):
    if not caminho_foto and b64_dados:
        caminho_foto = os.path.join("uploads", "documento_anexado.pdf")
    if b64_dados:
        salvar_arquivo_fisico_do_b64(caminho_foto, b64_dados)
    if caminho_foto and os.path.exists(caminho_foto) and os.path.getsize(caminho_foto) > 0:
        nome_arquivo = os.path.basename(caminho_foto)
        is_pdf = caminho_foto.lower().endswith(".pdf")
        ext_tag = "PDF" if is_pdf else "IMG"
        bg_tag_color = "#EA4335" if is_pdf else "#4285F4"
        st.markdown(f"""
        <div style="background-color: #202124; padding: 12px 18px; border-radius: 8px 8px 0 0; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #3c4043; margin-bottom: 15px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="background-color: {bg_tag_color}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{ext_tag}</span>
                <span style="color: #ffffff; font-weight: 600; font-size: 15px;">{nome_arquivo}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if is_pdf:
            pdf_renderizado = False
            if HAS_PYMUPDF:
                try:
                    doc_pdf = fitz.open(caminho_foto)
                    total_paginas = len(doc_pdf)
                    st.markdown(f"<p style='text-align: center; color: #9aa0a6; font-size: 13px; margin-bottom: 12px;'>PDF convertido visualmente • {total_paginas} página(s)</p>", unsafe_allow_html=True)
                    for page_index in range(total_paginas):
                        page = doc_pdf[page_index]
                        pix = page.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("png")
                        st.markdown(f"""
                        <div style="background-color: #2d2e30; padding: 6px; border-radius: 6px; margin-bottom: 6px; text-align: center; border: 1px solid #3c4043;">
                            <p style="color: #bdc1c6; font-size: 12px; margin: 0; font-weight: bold;">Página {page_index + 1} de {total_paginas}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.image(img_bytes, use_container_width=True)
                    pdf_renderizado = True
                except Exception as e:
                    st.warning(f"Erro ao processar páginas do PDF: {e}")
            if not pdf_renderizado:
                st.markdown("""
                <div style="background-color: #2d2e30; padding: 20px; border-radius: 8px; text-align: center; border: 1px solid #3c4043; margin-bottom: 15px;">
                    <p style="color: #ffffff; font-size: 15px; font-weight: bold; margin-bottom: 8px;">Visualização direta de PDF restrita pelo navegador</p>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("---")
                with open(caminho_foto, "rb") as f_pdf:
                    st.download_button(
                        label=f"📥 Descarregar Ficheiro PDF Original ({nome_arquivo})",
                        data=f_pdf.read(),
                        file_name=nome_arquivo,
                        mime="application/pdf",
                        type="primary"
                    )
        else:
            st.image(caminho_foto, use_container_width=True, caption="Documento Anexado")
            with open(caminho_foto, "rb") as f_img:
                img_bytes = f_img.read()
                st.download_button(
                    label=f"📥 Descarregar Imagem ({nome_arquivo})",
                    data=img_bytes,
                    file_name=nome_arquivo,
                    mime="application/jpeg",
                    type="primary"
                )
    else:
        st.error("Ficheiro de anexo não encontrado no servidor ou o registo não possui conteúdo binário válido.")

# ---------------------------------------------------------
# 2. ESTILOS E PADRÃO VISUAL
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

b64_img = ""
if bg_login_path:
    with open(bg_login_path, "rb") as img_f:
        b64_img = base64.b64encode(img_f.read()).decode()

if b64_img:
    css_fundo = f"""
    .stApp {{
        background-image: linear-gradient(rgba(10,12,10,0.92), rgba(10,12,10,0.92)), url("data:image/jpeg;base64,{b64_img}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
    }}
    """
else:
    css_fundo = """
    .stApp {
        background: linear-gradient(135deg, #121417 0%, #1A1D24 100%) !important;
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
    h1, h2, h3, h4, h5, h6, p, span, div, label {{
        color: #FFFFFF !important;
        text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8) !important;
    }}
    .stApp label, .stMarkdown, div[data-testid="stMarkdownContainer"] p {{
        font-size: 14px !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
    }}
    div[data-testid="stRadio"] > div {{
        background: transparent !important;
        padding: 0px !important;
        border: none !important;
        box-shadow: none !important;
        gap: 12px !important;
        flex-wrap: wrap !important;
        display: flex !important;
    }}
    div[data-testid="stRadio"] label {{
        background: linear-gradient(135deg, rgba(28, 32, 38, 0.95), rgba(18, 21, 26, 0.98)) !important;
        padding: 14px 20px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.4) !important;
        margin-bottom: 6px !important;
        transition: all 0.2s ease-in-out !important;
        cursor: pointer !important;
        flex: 1 1 auto !important;
        min-width: 210px !important;
        justify-content: center !important;
    }}
    div[data-testid="stRadio"] label:hover {{
        background: linear-gradient(135deg, rgba(38, 44, 52, 0.98), rgba(24, 28, 34, 1)) !important;
        border-color: rgba(255, 255, 255, 0.35) !important;
        transform: translateY(-2px) !important;
    }}
    div[data-testid="stRadio"] label[data-checked="true"] {{
        background: linear-gradient(135deg, #2D3748, #1A202C) !important;
        border: 1px solid rgba(255, 255, 255, 0.8) !important;
        box-shadow: 0px 6px 16px rgba(0, 0, 0, 0.6) !important;
    }}
    div[data-testid="stRadio"] label p {{
        color: #FFFFFF !important;
        font-size: 14px !important;
        font-weight: 800 !important;
    }}
    div[data-testid="stExpander"] {{
        background: rgba(20, 24, 30, 0.9) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 8px !important;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.4) !important;
    }}
    img[data-testid="stImage"] {{
        background: transparent !important;
        mix-blend-mode: multiply !important;
        filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.4)) !important;
        max-width: 85px !important;
        width: 100% !important;
        height: auto !important;
        margin: 0 auto !important;
        display: block !important;
    }}
    .titulo-logo {{
        font-size: 2rem !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
        margin-bottom: 0px !important;
        font-family: 'Arial Black', Gadget, sans-serif !important;
    }}
    .palavra-sup-mercado {{
        color: #4CAF50 !important;
        font-size: 1.2rem !important;
        font-weight: 800 !important;
        font-style: italic !important;
    }}
    .palavra-super {{
        color: #81C784 !important;
        font-style: italic !important;
    }}
    .palavra-nova {{
        color: #FF5252 !important;
        font-style: italic !important;
    }}
    .palavra-cidade {{
        color: #FFFFFF !important;
        font-style: italic !important;
        font-family: 'Brush Script MT', cursive, sans-serif !important;
        font-size: 2.5rem !important;
    }}
    div[data-baseweb="input"] input,
    div[data-baseweb="base-input"] input,
    div[data-testid="stDateInput"] input,
    div[data-baseweb="select"] input,
    textarea {{
        color: #111111 !important;
        -webkit-text-fill-color: #111111 !important;
        background-color: #F8F9FA !important;
        font-weight: bold !important;
        font-size: 14px !important;
        border-radius: 6px !important;
    }}
    div[data-baseweb="input"],
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] {{
        background-color: #F8F9FA !important;
        border-radius: 6px !important;
        border: 2px solid #4A5568 !important;
    }}
    div[data-baseweb="select"] span {{
        color: #111111 !important;
        font-weight: bold !important;
    }}
    div[data-testid="stFileUploader"],
    div[data-testid="stFileUploader"] section {{
        background: rgba(30, 35, 42, 0.85) !important;
        border: 2px solid rgba(255, 255, 255, 0.4) !important;
        border-radius: 8px !important;
    }}
    button[kind="primary"], .stButton > button[kind="primary"] {{
        background-color: #2D3748 !important;
        color: #FFFFFF !important;
        border: 2px solid #FFFFFF !important;
        font-weight: bold !important;
        font-size: 15px !important;
        border-radius: 8px !important;
        width: 100% !important;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.5) !important;
    }}
    button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {{
        background-color: #4A5568 !important;
        border-color: #FFFFFF !important;
    }}
    {css_fundo}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. BANCO DE DADOS (PERSISTÊNCIA COMPLETA E MIGRAÇÃO)
# ---------------------------------------------------------
def init_db():
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    if db_type == "postgres":
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255) NOT NULL,
            login VARCHAR(255) UNIQUE NOT NULL,
            senha VARCHAR(255) NOT NULL,
            perfil VARCHAR(255) NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id SERIAL PRIMARY KEY,
            codigo_barras VARCHAR(255),
            codigo_produto VARCHAR(255) UNIQUE,
            nome VARCHAR(255) UNIQUE NOT NULL,
            unidade_padrao VARCHAR(50) NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS fornecedores (
            id SERIAL PRIMARY KEY,
            codigo_fornecedor VARCHAR(255) UNIQUE,
            cnpj VARCHAR(255),
            nome VARCHAR(255) UNIQUE NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS romaneios (
            id SERIAL PRIMARY KEY,
            numero_romaneio VARCHAR(255) UNIQUE NOT NULL,
            loja VARCHAR(255) NOT NULL,
            loja_origem VARCHAR(255),
            loja_destino VARCHAR(255),
            data_recebimento VARCHAR(50) NOT NULL,
            fornecedor VARCHAR(255),
            codigo_fornecedor VARCHAR(255),
            telefone_fornecedor VARCHAR(255),
            conferente VARCHAR(255) NOT NULL,
            pagamento_a_vista VARCHAR(50) NOT NULL,
            data_pagamento VARCHAR(50),
            caminho_foto TEXT,
            assinatura_conferente TEXT,
            assinatura_entregador TEXT,
            status_nota VARCHAR(50) DEFAULT 'Pendente',
            tipo_operacao VARCHAR(50) DEFAULT 'Compra',
            observacoes TEXT,
            foto_b64 TEXT,
            ass_conf_b64 TEXT,
            ass_ent_b64 TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS romaneio_itens (
            id SERIAL PRIMARY KEY,
            romaneio_id INTEGER NOT NULL REFERENCES romaneios(id) ON DELETE CASCADE,
            produto VARCHAR(255) NOT NULL,
            quantidade REAL NOT NULL,
            unidade VARCHAR(50) NOT NULL,
            valor_unitario REAL,
            valor_total REAL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bonificacoes (
            id SERIAL PRIMARY KEY,
            numero_nota VARCHAR(255) NOT NULL,
            loja VARCHAR(255) NOT NULL,
            data_entrada VARCHAR(50) NOT NULL,
            valor_bonificacao REAL NOT NULL,
            status VARCHAR(100) NOT NULL,
            produto_hortifruti VARCHAR(255) NOT NULL,
            caminho_anexo TEXT,
            tipo_bonificacao VARCHAR(100) DEFAULT 'Bonificação',
            anexo_b64 TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS baixas_avarias (
            id SERIAL PRIMARY KEY,
            loja_baixa VARCHAR(255) NOT NULL,
            data_baixa VARCHAR(50) NOT NULL,
            ref_bon_transferen VARCHAR(255) NOT NULL,
            nf_baixa TEXT,
            nf_b_entrada VARCHAR(255) NOT NULL,
            produto_hortifruti VARCHAR(255) NOT NULL,
            quantidade_kg_cx REAL NOT NULL,
            valor_total_avaria REAL NOT NULL,
            saldo_restante_nota REAL NOT NULL,
            saldo_total_disponivel REAL NOT NULL,
            nf_baixa_b64 TEXT
        )
        """)
        cursor.execute("ALTER TABLE bonificacoes ADD COLUMN IF NOT EXISTS anexo_b64 TEXT;")
        cursor.execute("ALTER TABLE romaneios ADD COLUMN IF NOT EXISTS foto_b64 TEXT;")
        cursor.execute("ALTER TABLE romaneios ADD COLUMN IF NOT EXISTS ass_conf_b64 TEXT;")
        cursor.execute("ALTER TABLE romaneios ADD COLUMN IF NOT EXISTS ass_ent_b64 TEXT;")
        cursor.execute("ALTER TABLE baixas_avarias ADD COLUMN IF NOT EXISTS nf_baixa_b64 TEXT;")
        cursor.execute("SELECT * FROM usuarios WHERE login = %s", ('908',))
        if not cursor.fetchone():
            cursor.execute("DELETE FROM usuarios WHERE login = %s", ('admin',))
            cursor.execute(
                "INSERT INTO usuarios (nome, login, senha, perfil) VALUES (%s, %s, %s, %s)",
                ('Administrador', '908', '0332', 'Gestor')
            )
    else:
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
        CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_fornecedor TEXT UNIQUE,
            cnpj TEXT,
            nome TEXT UNIQUE NOT NULL
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS romaneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_romaneio TEXT UNIQUE NOT NULL,
            loja TEXT NOT NULL,
            loja_origem TEXT,
            loja_destino TEXT,
            data_recebimento TEXT NOT NULL,
            fornecedor TEXT,
            codigo_fornecedor TEXT,
            telefone_fornecedor TEXT,
            conferente TEXT NOT NULL,
            pagamento_a_vista TEXT NOT NULL,
            data_pagamento TEXT,
            caminho_foto TEXT,
            assinatura_conferente TEXT,
            assinatura_entregador TEXT,
            status_nota TEXT DEFAULT 'Pendente',
            tipo_operacao TEXT DEFAULT 'Compra',
            observacoes TEXT,
            foto_b64 TEXT,
            ass_conf_b64 TEXT,
            ass_ent_b64 TEXT
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
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bonificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_nota TEXT NOT NULL,
            loja TEXT NOT NULL,
            data_entrada TEXT NOT NULL,
            valor_bonificacao REAL NOT NULL,
            status TEXT NOT NULL,
            produto_hortifruti TEXT NOT NULL,
            caminho_anexo TEXT,
            tipo_bonificacao TEXT DEFAULT 'Bonificação',
            anexo_b64 TEXT
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS baixas_avarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loja_baixa TEXT NOT NULL,
            data_baixa TEXT NOT NULL,
            ref_bon_transferen TEXT NOT NULL,
            nf_baixa TEXT,
            nf_b_entrada TEXT NOT NULL,
            produto_hortifruti TEXT NOT NULL,
            quantidade_kg_cx REAL NOT NULL,
            valor_total_avaria REAL NOT NULL,
            saldo_restante_nota REAL NOT NULL,
            saldo_total_disponivel REAL NOT NULL,
            nf_baixa_b64 TEXT
        )
        """)
        try: cursor.execute("ALTER TABLE bonificacoes ADD COLUMN anexo_b64 TEXT;")
        except Exception: pass
        try: cursor.execute("ALTER TABLE romaneios ADD COLUMN foto_b64 TEXT;")
        except Exception: pass
        try: cursor.execute("ALTER TABLE romaneios ADD COLUMN ass_conf_b64 TEXT;")
        except Exception: pass
        try: cursor.execute("ALTER TABLE romaneios ADD COLUMN ass_ent_b64 TEXT;")
        except Exception: pass
        try: cursor.execute("ALTER TABLE baixas_avarias ADD COLUMN nf_baixa_b64 TEXT;")
        except Exception: pass
        cursor.execute("SELECT * FROM usuarios WHERE login = '908'")
        if not cursor.fetchone():
            cursor.execute("DELETE FROM usuarios WHERE login = 'admin'")
            cursor.execute(
                "INSERT INTO usuarios (nome, login, senha, perfil) VALUES ('Administrador', '908', '0332', 'Gestor')"
            )
    conn.commit()
    conn.close()

init_db()

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def fazer_login(login_ou_nome, senha):
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    if db_type == "postgres":
        cursor.execute(
            "SELECT id, nome, perfil, login FROM usuarios WHERE (login = %s OR LOWER(nome) = LOWER(%s)) AND senha = %s",
            (login_ou_nome.strip(), login_ou_nome.strip(), senha),
        )
    else:
        cursor.execute(
            "SELECT id, nome, perfil, login FROM usuarios WHERE (login = ? OR nome COLLATE NOCASE = ?) AND senha = ?",
            (login_ou_nome.strip(), login_ou_nome.strip(), senha),
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
# GERADORES DE PDF
# ---------------------------------------------------------
def gerar_pdf_romaneio(romaneio_data, itens_data, path_conf=None, path_ent=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
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
    if logo_path and os.path.exists(logo_path):
        logo_img_header = RLImage(logo_path, width=70, height=50)
    else:
        logo_img_header = Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
    
    tipo_op_pdf = romaneio_data.get('tipo_operacao', 'Compra')
    header_table = Table([[logo_img_header, Paragraph(f"<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>HortiControl - Romaneio de Recebimento ({tipo_op_pdf.upper()})", styles["Normal"]), Paragraph(f"<b>ROM:</b> {romaneio_data['numero_romaneio']}<br/><b>Data:</b> {romaneio_data['data_recebimento']}", styles["Normal"])]], colWidths=[80, 300, 160])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey)]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    loja_txt_pdf = romaneio_data.get('loja', '')
    if tipo_op_pdf.lower() in ['transferência', 'transferência/bonificação']:
        loja_txt_pdf = f"Origem: {romaneio_data.get('loja_origem', '')} -> Destino: {romaneio_data.get('loja_destino', '')}"
    info_data = [
        [Paragraph(f"<b>Tipo de Operação:</b> {tipo_op_pdf}", styles["Normal"]), Paragraph(f"<b>Fornecedor:</b> {romaneio_data.get('fornecedor','')}", styles["Normal"])],
        [Paragraph(f"<b>Cód. Fornecedor:</b> {romaneio_data.get('codigo_fornecedor','')}", styles["Normal"]), Paragraph(f"<b>Telefone:</b> {romaneio_data.get('telefone_fornecedor','')}", styles["Normal"])],
        [Paragraph(f"<b>Loja / Rota:</b> {loja_txt_pdf}", styles["Normal"]), Paragraph(f"<b>Conferente:</b> {romaneio_data.get('conferente','')}", styles["Normal"])],
        [Paragraph(f"<b>Pagamento à Vista:</b> {romaneio_data.get('pagamento_a_vista','')}", styles["Normal"]), Paragraph(f"<b>Data Pagamento:</b> {romaneio_data.get('data_pagamento','')}" if romaneio_data.get("pagamento_a_vista") == "NÃO" else "", styles["Normal"])],
    ]
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke)]))
    story.append(info_table)
    
    if romaneio_data.get('observacoes'):
        story.append(Spacer(1, 8))
        obs_table = Table([[Paragraph(f"<b>Informações Adicionais / Observações:</b><br/>{romaneio_data.get('observacoes')}", styles["Normal"])]], colWidths=[540])
        obs_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.append(obs_table)
        
    story.append(Spacer(1, 15))
    table_content = [[Paragraph("Item", style_header_center), Paragraph("Descrição do Produto", style_header_left), Paragraph("Qtd / Peso", style_header_center), Paragraph("UND", style_header_center), Paragraph("Vl. Unit", style_header_left), Paragraph("Total", style_header_left)]]
    total_geral = 0.0
    for idx, item in enumerate(itens_data, 1):
        v_unit = float(item[4]) if len(item) > 4 and item[4] is not None else 0.0
        v_tot = float(item[5]) if len(item) > 5 and item[5] is not None else 0.0
        qtd_val = float(item[2]) if len(item) > 2 and item[2] is not None else 0.0
        total_geral += v_tot
        table_content.append([Paragraph(str(idx), style_center), Paragraph(str(item[1]), style_left), Paragraph(fmt_ptbr(qtd_val, 3), style_center), Paragraph(str(item[3]), style_center), Paragraph(f"R$ {fmt_ptbr(v_unit, 2)}", style_left), Paragraph(f"R$ {fmt_ptbr(v_tot, 2)}", style_left)])
    itens_table = Table(table_content, colWidths=[35, 215, 75, 50, 75, 90])
    itens_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D3748")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(itens_table)
    story.append(Spacer(1, 8))
    
    total_table = Table([[f"TOTAL GERAL DO ROMANEIO: R$ {fmt_ptbr(total_geral, 2)}"]], colWidths=[540])
    total_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1A202C")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.whitesmoke), ("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(total_table)
    story.append(Spacer(1, 15))
    
    path_conf_transp = remover_fundo_branco(path_conf)
    path_ent_transp = remover_fundo_branco(path_ent)
    img_conf_pdf = None
    if path_conf_transp and os.path.exists(path_conf_transp):
        try: img_conf_pdf = RLImage(path_conf_transp, width=180, height=45)
        except Exception: pass
    img_ent_pdf = None
    if path_ent_transp and os.path.exists(path_ent_transp):
        try: img_ent_pdf = RLImage(path_ent_transp, width=180, height=45)
        except Exception: pass
        
    col_conf_cell = [img_conf_pdf if img_conf_pdf else Spacer(1, 45), Paragraph(f"<b>Assinatura do Conferente:</b><br/>{romaneio_data.get('conferente','')}", styles["Normal"])]
    col_ent_cell = [img_ent_pdf if img_ent_pdf else Spacer(1, 45), Paragraph(f"<b>Assinatura do Entregador / Fornecedor:</b><br/>{romaneio_data.get('fornecedor','')}", styles["Normal"])]
    ass_table = Table([[col_conf_cell, col_ent_cell]], colWidths=[270, 270])
    ass_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.append(ass_table)
    doc.build(story)
    buffer.seek(0)
    return buffer

def gerar_pdf_produtos(produtos_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
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
    if logo_path and os.path.exists(logo_path):
        logo_img_header = RLImage(logo_path, width=70, height=50)
    else:
        logo_img_header = Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
    header_table = Table([[logo_img_header, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>HortiControl - Relatório de Produtos Cadastrados", styles["Normal"]), Paragraph(f"<b>Data:</b> {datetime.now(ZoneInfo('America/Manaus')).strftime('%d/%m/%Y')}<br/><b>Total:</b> {len(produtos_data)}", styles["Normal"])]], colWidths=[80, 310, 150])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("ALIGN", (0, 0), (0, 0), "CENTER"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey)]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    table_content = [[Paragraph("Item", style_header_center), Paragraph("Cód. Produto", style_header_center), Paragraph("Código de Barras", style_header_center), Paragraph("Nome do Produto", style_header_left), Paragraph("UND", style_header_center)]]
    for idx, p in enumerate(produtos_data, 1):
        table_content.append([Paragraph(str(idx), style_center), Paragraph(str(p[2] or "S/N"), style_center), Paragraph(str(p[1] or "S/N"), style_center), Paragraph(str(p[3]), style_left), Paragraph(str(p[4]), style_center)])
    prod_table = Table(table_content, colWidths=[35, 95, 125, 235, 50])
    prod_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D3748")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(prod_table)
    doc.build(story)
    buffer.seek(0)
    return buffer

def gerar_pdf_bonificacoes(df_bonf_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    style_left = ParagraphStyle('Left', parent=styles['Normal'], alignment=0, fontName='Helvetica', fontSize=8)
    style_center = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontName='Helvetica', fontSize=8)
    style_header_left = ParagraphStyle('HLeft', parent=styles['Normal'], alignment=0, fontName='Helvetica-Bold', fontSize=8, textColor=colors.whitesmoke)
    style_header_center = ParagraphStyle('HCenter', parent=styles['Normal'], alignment=1, fontName='Helvetica-Bold', fontSize=8, textColor=colors.whitesmoke)
    
    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio.png", "logo_romaneio", "logo", "Tela de login"]:
            pos_p = f"{prefixo}.{ext}" if not prefixo.endswith(f".{ext}") else prefixo
            if os.path.exists(pos_p):
                logo_path = pos_p
                break
        if logo_path: break
    logo_img_header = RLImage(logo_path, width=70, height=50) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
    header_table = Table([[logo_img_header, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>HortiControl - Relatório de Controle de Bonificação", styles["Normal"]), Paragraph(f"<b>Data Emissão:</b> {datetime.now(ZoneInfo('America/Manaus')).strftime('%d/%m/%Y %H:%M')}<br/><b>Total Registros:</b> {len(df_bonf_data)}", styles["Normal"])]], colWidths=[80, 310, 150])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey)]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    table_content = [[Paragraph("N° Nota", style_header_center), Paragraph("Tipo", style_header_center), Paragraph("Loja", style_header_center), Paragraph("Data Entrada", style_header_center), Paragraph("Valor (R$)", style_header_left), Paragraph("Status", style_header_center), Paragraph("Produto Hortifrúti", style_header_left)]]
    tot_val = 0.0
    for _, r in df_bonf_data.iterrows():
        v_b = float(r["valor_bonificacao"]) if r["valor_bonificacao"] else 0.0
        tot_val += v_b
        t_bonf = r.get("tipo_bonificacao", "Bonificação")
        table_content.append([Paragraph(str(r["numero_nota"]), style_center), Paragraph(str(t_bonf), style_center), Paragraph(str(r["loja"]), style_center), Paragraph(str(r["data_entrada"]), style_center), Paragraph(f"R$ {fmt_ptbr(v_b, 2)}", style_left), Paragraph(str(r["status"]), style_center), Paragraph(str(r["produto_hortifruti"]), style_left)])
    bonf_table = Table(table_content, colWidths=[55, 65, 65, 85, 70, 80, 120])
    bonf_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D3748")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(bonf_table)
    story.append(Spacer(1, 10))
    total_table = Table([[f"VALOR TOTAL BONIFICADO / TRANSFERIDO: R$ {fmt_ptbr(tot_val, 2)}"]], colWidths=[540])
    total_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1A202C")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.whitesmoke), ("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(total_table)
    doc.build(story)
    buffer.seek(0)
    return buffer

def gerar_pdf_baixas(df_baixas_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    story = []
    styles = getSampleStyleSheet()
    style_left = ParagraphStyle('Left', parent=styles['Normal'], alignment=0, fontName='Helvetica', fontSize=8)
    style_center = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontName='Helvetica', fontSize=8)
    style_header_left = ParagraphStyle('HLeft', parent=styles['Normal'], alignment=0, fontName='Helvetica-Bold', fontSize=8, textColor=colors.whitesmoke)
    style_header_center = ParagraphStyle('HCenter', parent=styles['Normal'], alignment=1, fontName='Helvetica-Bold', fontSize=8, textColor=colors.whitesmoke)
    
    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio.png", "logo_romaneio", "logo", "Tela de login"]:
            pos_p = f"{prefixo}.{ext}" if not prefixo.endswith(f".{ext}") else prefixo
            if os.path.exists(pos_p):
                logo_path = pos_p
                break
        if logo_path: break
    logo_img_header = RLImage(logo_path, width=70, height=45) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
    header_table = Table([[logo_img_header, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>HortiControl - Registro de Baixas de Avarias", styles["Normal"]), Paragraph(f"<b>Data Emissão:</b> {datetime.now(ZoneInfo('America/Manaus')).strftime('%d/%m/%Y %H:%M')}<br/><b>Total Registros:</b> {len(df_baixas_data)}", styles["Normal"])]], colWidths=[80, 520, 192])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey)]))
    story.append(header_table)
    story.append(Spacer(1, 12))
    table_content = [[
        Paragraph("LOJAS", style_header_center),
        Paragraph("Data Baixa", style_header_center),
        Paragraph("Ref. Bon. transferen", style_header_center),
        Paragraph("NF da baixa", style_header_center),
        Paragraph("NF de B. ENTRADA", style_header_center),
        Paragraph("Produto Hortifrúti", style_header_left),
        Paragraph("Qtd (kg/cx)", style_header_center),
        Paragraph("Valor Total Avaria (R$)", style_header_left),
        Paragraph("Saldo", style_header_left),
        Paragraph("Saldo Total Utilizado", style_header_left)
    ]]
    tot_val_avarias = 0.0
    for _, r in df_baixas_data.iterrows():
        v_av = float(r["valor_total_avaria"]) if r["valor_total_avaria"] else 0.0
        tot_val_avarias += v_av
        s_nota = float(r["saldo_restante_nota"]) if r["saldo_restante_nota"] else 0.0
        s_util = float(r.get("saldo_total_utilizado", 0.0))
        qtd_val = float(r["quantidade_kg_cx"]) if r["quantidade_kg_cx"] else 0.0
        table_content.append([
            Paragraph(str(r["loja_baixa"]), style_center),
            Paragraph(str(r["data_baixa"]), style_center),
            Paragraph(str(r["ref_bon_transferen"]), style_center),
            Paragraph(str(r["nf_baixa"] if r["nf_baixa"] else "S/Anexo"), style_center),
            Paragraph(str(r["nf_b_entrada"]), style_center),
            Paragraph(str(r["produto_hortifruti"]), style_left),
            Paragraph(fmt_ptbr(qtd_val, 3), style_center),
            Paragraph(f"R$ {fmt_ptbr(v_av, 2)}", style_left),
            Paragraph(f"R$ {fmt_ptbr(s_nota, 2)}", style_left),
            Paragraph(f"R$ {fmt_ptbr(s_util, 2)}", style_left),
        ])
    baixas_table = Table(table_content, colWidths=[70, 95, 85, 75, 85, 120, 60, 85, 65, 52])
    baixas_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2D3748")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(baixas_table)
    story.append(Spacer(1, 10))
    total_table = Table([[f"VALOR TOTAL DAS AVARIAS: R$ {fmt_ptbr(tot_val_avarias, 2)}"]], colWidths=[792])
    total_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1A202C")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.whitesmoke), ("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(total_table)
    doc.build(story)
    buffer.seek(0)
    return buffer

def gerar_pdf_relatorio_gerencial_bi(metrics_dict, df_bonf_sub, df_baixas_sub):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    story = []
    styles = getSampleStyleSheet()
    style_left = ParagraphStyle('Left', parent=styles['Normal'], alignment=0, fontName='Helvetica', fontSize=8)
    style_center = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontName='Helvetica', fontSize=8)
    style_header_center = ParagraphStyle('HCenter', parent=styles['Normal'], alignment=1, fontName='Helvetica-Bold', fontSize=8, textColor=colors.whitesmoke)
    
    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio.png", "logo_romaneio", "logo", "Tela de login"]:
            pos_p = f"{prefixo}.{ext}" if not prefixo.endswith(f".{ext}") else prefixo
            if os.path.exists(pos_p):
                logo_path = pos_p
                break
        if logo_path: break
    logo_img = RLImage(logo_path, width=65, height=40) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA</b>", styles["Normal"])
    header = Table([[logo_img, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>Relatório Gerencial de Bonificações, Transferências e Prevenção de Perdas (BI)", styles["Normal"]), Paragraph(f"<b>Emissão:</b> {datetime.now(ZoneInfo('America/Manaus')).strftime('%d/%m/%Y %H:%M')}", styles["Normal"])]], colWidths=[75, 530, 187])
    header.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("BACKGROUND", (0,0), (-1,-1), colors.lightgrey)]))
    story.append(header)
    story.append(Spacer(1, 10))
    kpi_summary = [
        [Paragraph("<b>Tot. Bonificado (R$)</b>", style_header_center), Paragraph("<b>Tot. Transferido (R$)</b>", style_header_center), Paragraph("<b>Avarias Bonificadas / Salvas (R$)</b>", style_header_center), Paragraph("<b>Taxa Cobertura (%)</b>", style_header_center), Paragraph("<b>Saldo Remanescente (R$)</b>", style_header_center)],
        [
            Paragraph(f"R$ {fmt_ptbr(metrics_dict['tot_bonf'], 2)}", style_center),
            Paragraph(f"R$ {fmt_ptbr(metrics_dict['tot_transf'], 2)}", style_center),
            Paragraph(f"R$ {fmt_ptbr(metrics_dict['tot_avaria'], 2)}", style_center),
            Paragraph(f"{fmt_ptbr(metrics_dict['taxa_cobertura'], 2)}%", style_center),
            Paragraph(f"R$ {fmt_ptbr(metrics_dict['saldo_restante'], 2)}", style_center),
        ]
    ]
    t_kpi = Table(kpi_summary, colWidths=[158, 158, 160, 158, 158])
    t_kpi.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1A202C")), ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(t_kpi)
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>1. Resumo Analítico de Entradas e Bonificações Filtradas</b>", styles["Heading3"]))
    tb_b = [[Paragraph("N° Nota", style_header_center), Paragraph("Tipo", style_header_center), Paragraph("Loja", style_header_center), Paragraph("Data", style_header_center), Paragraph("Valor (R$)", style_header_center), Paragraph("Status", style_header_center), Paragraph("Produto", style_header_center)]]
    for _, r in df_bonf_sub.head(15).iterrows():
        tb_b.append([
            Paragraph(str(r["numero_nota"]), style_center),
            Paragraph(str(r.get("tipo_bonificacao", "Bonificação")), style_center),
            Paragraph(str(r["loja"]), style_center),
            Paragraph(str(r["data_entrada"]), style_center),
            Paragraph(f"R$ {fmt_ptbr(r['valor_bonificacao'], 2)}", style_center),
            Paragraph(str(r["status"]), style_center),
            Paragraph(str(r["produto_hortifruti"]), style_left)
        ])
    table_b = Table(tb_b, colWidths=[65, 95, 95, 95, 80, 90, 272])
    table_b.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2D3748")), ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(table_b)
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>2. Resumo de Baixas de Avarias Compensadas (Evitando Perdas Físicas e Financeiras)</b>", styles["Heading3"]))
    tb_bx = [[Paragraph("Loja", style_header_center), Paragraph("Data", style_header_center), Paragraph("Ref. Bon.", style_header_center), Paragraph("NF Ent.", style_header_center), Paragraph("Produto", style_header_center), Paragraph("Qtd (kg/cx)", style_header_center), Paragraph("Valor Avaria (R$)", style_header_center)]]
    for _, r in df_baixas_sub.head(15).iterrows():
        tb_bx.append([
            Paragraph(str(r["loja_baixa"]), style_center),
            Paragraph(str(r["data_baixa"]), style_center),
            Paragraph(str(r["ref_bon_transferen"]), style_center),
            Paragraph(str(r["nf_b_entrada"]), style_center),
            Paragraph(str(r["produto_hortifruti"]), style_left),
            Paragraph(fmt_ptbr(r["quantidade_kg_cx"], 3), style_center),
            Paragraph(f"R$ {fmt_ptbr(r['valor_total_avaria'], 2)}", style_center)
        ])
    table_bx = Table(tb_bx, colWidths=[90, 95, 90, 80, 237, 80, 120])
    table_bx.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2D3748")), ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(table_bx)
    doc.build(story)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# 4. TELA DE LOGIN
# ---------------------------------------------------------
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

if st.session_state["usuario_logado"] is None:
    logo_display = None
    for nome in ["logo_romaneio.png.jpg", "logo_romaneio.png", "logo.png", "Tela de login.jpeg"]:
        if os.path.exists(nome):
            logo_display = nome
            break
    col_vazia_esq, col_central, col_vazia_dir = st.columns([0.1, 3.8, 0.1])
    with col_central:
        if logo_display:
            col_logo, col_titulo = st.columns([0.45, 3.55], vertical_alignment="center")
            with col_logo:
                st.image(logo_display, use_container_width=True)
            with col_titulo:
                st.markdown("""<div class='titulo-logo'><span class='palavra-sup-mercado'>Supermercado</span><br><span class='palavra-super'>SUPER</span> <span class='palavra-nova'>NOVA</span><br><span class='palavra-cidade'>Cidade</span></div>""", unsafe_allow_html=True)
                st.markdown("<h3>HortiControl - Sistema de Recebimento Hortifrúti</h3>", unsafe_allow_html=True)
        else:
            st.markdown("""<div class='titulo-logo'><span class='palavra-sup-mercado'>Supermercado</span><br><span class='palavra-super'>SUPER</span> <span class='palavra-nova'>NOVA</span><br><span class='palavra-cidade'>Cidade</span></div>""", unsafe_allow_html=True)
            st.markdown("<h3>HortiControl - Sistema de Recebimento Hortifrúti</h3>", unsafe_allow_html=True)
            
        with st.form("form_login"):
            login_input = st.text_input("Usuário / Login ou Nome Completo", value="", placeholder="Digite seu usuário ou nome...")
            senha_input = st.text_input("Senha", type="password", value="", placeholder="Digite sua senha...")
            loja_login_sel = st.selectbox(
                "Selecione a Loja de Atuação",
                ["", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"],
                index=0
            )
            btn_entrar = st.form_submit_button("Entrar no Sistema", type="primary")
            if btn_entrar:
                if not loja_login_sel:
                    st.error("Por favor, selecione a loja em que você está atuando antes de entrar.")
                else:
                    spinner_supernova("Validando acesso no Supernova...")
                    usuario = fazer_login(login_input, senha_input)
                    if usuario:
                        st.session_state["usuario_logado"] = {
                            "id": usuario[0],
                            "nome": usuario[1],
                            "perfil": usuario[2],
                            "login": usuario[3],
                            "loja_atual": loja_login_sel
                        }
                        st.success(f"Bem-vindo(a), {usuario[1]} na {loja_login_sel}!")
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
else:
    user_info = st.session_state["usuario_logado"]
    perfil_db = str(user_info.get("perfil", "")).strip().lower()
    is_admin = (user_info["login"].lower() == "908" or "gestor" in perfil_db or "adm" in perfil_db)
    loja_atual_usuario = user_info.get("loja_atual", "Não definida")
    st.markdown("---")
    col_info_usr, col_logout = st.columns([3.5, 1.5], vertical_alignment="center")
    with col_info_usr:
        tipo_perfil_txt = "👑 Gestor / Administrador" if is_admin else f"👤 Conferente ({loja_atual_usuario})"
        st.markdown(f"**Usuário:** {user_info['nome']} &nbsp;|&nbsp; **Perfil:** {tipo_perfil_txt}")
    with col_logout:
        if st.button("🚪 Sair", type="secondary", key="btn_sair_sistema_principal"):
            st.session_state["usuario_logado"] = None
            st.rerun()
            
    opcoes_menu_map = {
        "📋 Romaneio de Recebimento": "Romaneio de Recebimento - Hortifrúti",
        "🔍 Consultar Romaneios": "Consultar Romaneios",
        "🛒 Controle de Bonificação": "Controle de Bonificação",
        "📉 Baixa de Avarias": "Controle de Baixa de Avarias"
    }
    if is_admin:
        opcoes_menu_map.update({
            "📊 Relatórios & BI": "Relatórios & Gráficos",
            "⚙️ Cadastros": "Gerenciar Cadastros (Produtos)",
            "👥 Usuários": "Gerenciar Usuários & Permissões"
        })
    menu_selecionado_label = st.radio(
        "Menu de Navegação Principal",
        list(opcoes_menu_map.keys()),
        horizontal=True,
        label_visibility="collapsed"
    )
    menu = opcoes_menu_map[menu_selecionado_label]
    st.markdown("---")
    
    if menu == "Romaneio de Recebimento - Hortifrúti":
        st.title("📋 Romaneio de Recebimento - Hortifrúti")
        if "form_key_suffix" not in st.session_state: st.session_state["form_key_suffix"] = 0
        if "item_key_suffix" not in st.session_state: st.session_state["item_key_suffix"] = 0
        k_suffix = st.session_state["form_key_suffix"]
        i_suffix = st.session_state["item_key_suffix"]

        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nome, unidade_padrao, codigo_produto, codigo_barras FROM produtos ORDER BY nome")
        produtos_lista = cursor.fetchall()
        cursor.execute("SELECT nome, codigo_fornecedor FROM fornecedores ORDER BY nome")
        fornecedores_lista = cursor.fetchall()
        conn.close()

        prod_dict = {}
        for p in produtos_lista:
            c_prod = p[2] if p[2] and str(p[2]).strip() else "S/Cód"
            c_bar = p[3] if p[3] and str(p[3]).strip() else "S/Barras"
            label = f"{c_prod} | Barras: {c_bar} | {p[0]}"
            prod_dict[label] = (p[0], p[1] if p[1] else "KG")
        prod_nomes_keys = list(prod_dict.keys())

        forn_por_nome = {}
        forn_nomes_keys = []
        for f in fornecedores_lista:
            nome_f = f[0]
            cod_f = str(f[1]).strip() if f[1] else ""
            forn_nomes_keys.append(nome_f)
            forn_por_nome[nome_f] = cod_f

        if f"val_cod_forn_{k_suffix}" not in st.session_state: st.session_state[f"val_cod_forn_{k_suffix}"] = ""
        if f"val_sel_forn_{k_suffix}" not in st.session_state: st.session_state[f"val_sel_forn_{k_suffix}"] = ""

        def atualizar_por_select():
            s_selecionado = st.session_state.get(f"sel_forn_{k_suffix}", "")
            st.session_state[f"val_sel_forn_{k_suffix}"] = s_selecionado
            novo_cod = ""
            if s_selecionado in forn_por_nome:
                novo_cod = forn_por_nome[s_selecionado]
            st.session_state[f"val_cod_forn_{k_suffix}"] = novo_cod
            st.session_state[f"in_cod_forn_{k_suffix}"] = novo_cod

        with st.expander("1. Cabeçalho do Recebimento", expanded=True):
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if f"num_rom_auto_{k_suffix}" not in st.session_state:
                    data_hoje_str = datetime.now(ZoneInfo("America/Manaus")).strftime("%Y%m%d%H%M%S")
                    st.session_state[f"num_rom_auto_{k_suffix}"] = f"ROM-{data_hoje_str}"
                num_romaneio = st.text_input("Número do Romaneio", value=st.session_state[f"num_rom_auto_{k_suffix}"], disabled=True, key=f"num_rom_{k_suffix}")
                tipo_operacao = st.selectbox("Tipo de Operação", ["", "Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"], index=0, key=f"tipo_op_{k_suffix}", placeholder="Selecione o tipo...", on_change=lambda: st.rerun())
            with col2:
                data_rec_val = st.date_input("Data do Recebimento", value=datetime.now(ZoneInfo("America/Manaus")), format="DD/MM/YYYY", key=f"data_rec_{k_suffix}")
                data_rec_str = data_rec_val.strftime("%d/%m/%Y") if data_rec_val else ""
                if tipo_operacao in ["Transferência", "Transferência/Bonificação"]:
                    loja_origem = st.selectbox("Loja de Origem (Saiu)", ["", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"], index=0, placeholder="Selecione a origem...", key=f"loja_orig_{k_suffix}")
                    loja_destino = st.selectbox("Loja de Destino (Entrou)", ["", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"], index=0, placeholder="Selecione o destino...", key=f"loja_dest_{k_suffix}")
                    loja = f"{loja_origem} -> {loja_destino}"
                else:
                    loja_origem = ""
                    loja_destino = ""
                    lista_lojas_opc = ["", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                    idx_loja_login = lista_lojas_opc.index(loja_atual_usuario) if loja_atual_usuario in lista_lojas_opc else 0
                    loja = st.selectbox("Loja", lista_lojas_opc, index=idx_loja_login, placeholder="Selecione a loja...", key=f"loja_{k_suffix}")
            with col3:
                idx_sel = 0
                atual_sel = st.session_state[f"val_sel_forn_{k_suffix}"]
                if atual_sel in forn_nomes_keys:
                    idx_sel = forn_nomes_keys.index(atual_sel) + 1
                fornecedor_sel = st.selectbox("Fornecedor / Entregador Cadastrado", options=[""] + forn_nomes_keys, index=idx_sel, placeholder="Selecione o fornecedor...", key=f"sel_forn_{k_suffix}", on_change=atualizar_por_select)
                if f"in_cod_forn_{k_suffix}" not in st.session_state:
                    st.session_state[f"in_cod_forn_{k_suffix}"] = st.session_state[f"val_cod_forn_{k_suffix}"]
                cod_fornecedor = st.text_input("Código do Fornecedor (Automático)", key=f"in_cod_forn_{k_suffix}", disabled=True)

            col_tel1, col_tel2 = st.columns([2, 2])
            with col_tel1:
                tel_key = f"tel_input_{k_suffix}"
                if tel_key not in st.session_state: st.session_state[tel_key] = ""
                def formatar_tel():
                    val = st.session_state.get(tel_key, "")
                    raw = "".join(filter(str.isdigit, val))
                    if len(raw) > 11: raw = raw[:11]
                    fmt = ""
                    if len(raw) > 0: fmt += f"({raw[:2]}"
                    if len(raw) >= 3: fmt += f") {raw[2:7]}"
                    if len(raw) >= 8: fmt += f"-{raw[7:]}"
                    st.session_state[tel_key] = fmt
                tel_fornecedor = st.text_input("Telefone de Contato (Opcional)", value="", placeholder="(00) 00000-0000", key=tel_key, on_change=formatar_tel)
            with col_tel2:
                pag_a_vista = st.selectbox("Pagamento à Vista?", ["", "SIM", "NÃO"], index=0, placeholder="Selecione...", key=f"pag_vista_{k_suffix}")
            
            fornecedor = fornecedor_sel
            data_pag_str = ""
            if pag_a_vista == "NÃO":
                data_pag_val = st.date_input("Data para Pagamento", value=None, format="DD/MM/YYYY", key=f"data_pag_{k_suffix}")
                data_pag_str = data_pag_val.strftime("%d/%m/%Y") if data_pag_val else ""
            conferente = st.text_input("Responsável Rec. Físico", value=user_info["nome"], disabled=True, key=f"conf_{k_suffix}")

        st.subheader("2. Itens do Recebimento")
        if "itens_romaneio" not in st.session_state: st.session_state["itens_romaneio"] = []

        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns([2.5, 1.2, 1.2, 1.2, 1])
        with col_p1:
            prod_label_sel = st.selectbox("Produto / Código / Barras", options=[""] + prod_nomes_keys, index=0, placeholder="Selecione o produto...", key=f"prod_sel_{k_suffix}_{i_suffix}")
            prod_nome_real = prod_dict[prod_label_sel][0] if prod_label_sel and prod_label_sel != "" and prod_dict else ""
        with col_p2:
            und_padrao = prod_dict[prod_label_sel][1] if prod_label_sel and prod_label_sel != "" and prod_dict else "KG"
            und_sel = st.selectbox("UND", ["KG", "UNID", "GRM", "CX"], index=(["KG", "UNID", "GRM", "CX"].index(und_padrao) if und_padrao in ["KG", "UNID", "GRM", "CX"] else 0), key=f"und_sel_{k_suffix}_{i_suffix}")
        with col_p3:
            qtd_str_input = st.text_input("Qtd / Peso", value="", placeholder="0,000", key=f"qtd_{k_suffix}_{i_suffix}")
        with col_p4:
            val_unit_str_input = st.text_input("Valor Unit. (R$)", value="", placeholder="0,00", key=f"vunit_{k_suffix}_{i_suffix}")
        with col_p5:
            st.write("")
            st.write("")
            if st.button("➕ Add", type="primary", key=f"btn_add_{k_suffix}_{i_suffix}"):
                try: qtd_input = float(qtd_str_input.replace(".", "").replace(",", ".")) if qtd_str_input else 0.0
                except ValueError: qtd_input = 0.0
                try: val_unit_val = float(val_unit_str_input.replace(".", "").replace(",", ".")) if val_unit_str_input else 0.0
                except ValueError: val_unit_val = 0.0
                if not prod_nome_real: st.warning("Selecione um produto antes de adicionar.")
                elif qtd_input <= 0: st.warning("Informe uma quantidade maior que zero.")
                else:
                    v_tot = qtd_input * val_unit_val
                    st.session_state["itens_romaneio"].append({"produto": prod_nome_real, "quantidade": qtd_input, "unidade": und_sel, "valor_unitario": val_unit_val, "valor_total": v_tot})
                    st.session_state["item_key_suffix"] += 1
                    st.rerun()

        if st.session_state["itens_romaneio"]:
            st.markdown("**Itens adicionados:**")
            dados_tabela = [{"Item": i, "Descrição do Produto": itm["produto"], "Qtd / Peso": fmt_ptbr(itm['quantidade'], 3), "UND": itm["unidade"], "Vl. Unit": f"R$ {fmt_ptbr(itm['valor_unitario'], 2)}", "Total": f"R$ {fmt_ptbr(itm['valor_total'], 2)}"} for i, itm in enumerate(st.session_state["itens_romaneio"], 1)]
            st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True, hide_index=True)

            col_rem_labels, col_rem_btns = st.columns([3, 1])
            with col_rem_labels:
                item_para_remover = st.selectbox("Selecionar Item para Remover", options=range(1, len(st.session_state["itens_romaneio"]) + 1), format_func=lambda x: f"Item {x}: {st.session_state['itens_romaneio'][x-1]['produto']}", key=f"sel_rem_{k_suffix}")
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

        st.subheader("3. Anexo de Foto da Mercadoria / Nota Fiscal")
        fotos_upload = st.file_uploader("Foto da Mercadoria / Nota Fiscal", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True, key=f"fotos_{k_suffix}")

        st.subheader("4. Informações Adicionais / Observações")
        observacoes_romaneio = st.text_area("Observações sobre a carga, qualidade ou divergências", value="", placeholder="Insira observações relevantes aqui...", key=f"obs_{k_suffix}")

        st.subheader("5. Assinatura Digital")
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
                key=f"canv_conf_{k_suffix}"
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
                key=f"canv_ent_{k_suffix}"
            )

        if st.button("✅ Salvar Romaneio", type="primary", key=f"btn_salvar_{k_suffix}"):
            num_rom_final = st.session_state[f"num_rom_auto_{k_suffix}"]
            forn_final = fornecedor if isinstance(fornecedor, str) else ""
            cod_forn_val = st.session_state[f"val_cod_forn_{k_suffix}"]
            if not forn_final.strip(): st.error("Selecione o fornecedor na lista cadastrada.")
            elif not data_rec_str: st.error("A Data do Recebimento é obrigatória!")
            elif tipo_operacao in ["Transferência", "Transferência/Bonificação"] and (not loja_origem or not loja_destino): st.error("Selecione a Loja de Origem e a Loja de Destino!")
            elif tipo_operacao not in ["Transferência", "Transferência/Bonificação"] and not loja: st.error("Selecione a loja!")
            elif pag_a_vista == "NÃO" and not data_pag_str: st.error("A Data para Pagamento é obrigatória para compras a prazo!")
            elif not st.session_state["itens_romaneio"]: st.error("Adicione itens ao romaneio.")
            else:
                spinner_supernova("Salvando romaneio no Supernova...")
                try:
                    if not os.path.exists("uploads"): os.makedirs("uploads")
                    path_ass_conf = ""
                    b64_conf = ""
                    if canvas_conf.image_data is not None and canvas_conf.image_data.sum() > 0:
                        img_c = Image.fromarray(canvas_conf.image_data.astype("uint8"))
                        path_ass_conf = os.path.join("uploads", f"ass_conf_{num_rom_final}.png")
                        img_c.save(path_ass_conf)
                        with open(path_ass_conf, "rb") as f_ac:
                            b64_conf = base64.b64encode(f_ac.read()).decode('utf-8')

                    path_ass_ent = ""
                    b64_ent = ""
                    if canvas_ent.image_data is not None and canvas_ent.image_data.sum() > 0:
                        img_e = Image.fromarray(canvas_ent.image_data.astype("uint8"))
                        path_ass_ent = os.path.join("uploads", f"ass_ent_{num_rom_final}.png")
                        img_e.save(path_ass_ent)
                        with open(path_ass_ent, "rb") as f_ae:
                            b64_ent = base64.b64encode(f_ae.read()).decode('utf-8')

                    caminho_foto_salva = ""
                    b64_foto = ""
                    if fotos_upload:
                        for f in fotos_upload:
                            path_f = os.path.join("uploads", f.name)
                            f_bytes = f.getbuffer()
                            with open(path_f, "wb") as f_out: f_out.write(f_bytes)
                            caminho_foto_salva = path_f
                            b64_foto = base64.b64encode(f_bytes).decode('utf-8')

                    conn, db_type = get_db_connection()
                    cursor = conn.cursor()
                    if db_type == "postgres":
                        cursor.execute("""
                        INSERT INTO romaneios (numero_romaneio, loja, loja_origem, loja_destino,
                        data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista,
                        data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador, status_nota, tipo_operacao,
                        observacoes, foto_b64, ass_conf_b64, ass_ent_b64)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                        """, (num_rom_final, loja, loja_origem, loja_destino, data_rec_str, forn_final, cod_forn_val, tel_fornecedor, user_info["nome"], pag_a_vista, data_pag_str, caminho_foto_salva, path_ass_conf, path_ass_ent, 'Pendente', tipo_operacao, observacoes_romaneio, b64_foto, b64_conf, b64_ent))
                        romaneio_id = cursor.fetchone()[0]
                    else:
                        cursor.execute("""
                        INSERT INTO romaneios (numero_romaneio, loja, loja_origem, loja_destino,
                        data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista,
                        data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador, status_nota, tipo_operacao,
                        observacoes, foto_b64, ass_conf_b64, ass_ent_b64)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (num_rom_final, loja, loja_origem, loja_destino, data_rec_str, forn_final, cod_forn_val, tel_fornecedor, user_info["nome"], pag_a_vista, data_pag_str, caminho_foto_salva, path_ass_conf, path_ass_ent, 'Pendente', tipo_operacao, observacoes_romaneio, b64_foto, b64_conf, b64_ent))
                        romaneio_id = cursor.lastrowid

                    itens_salvos_pdf = []
                    for itm in st.session_state["itens_romaneio"]:
                        if db_type == "postgres":
                            cursor.execute("INSERT INTO romaneio_itens (romaneio_id, produto, quantidade, unidade, valor_unitario, valor_total) VALUES (%s, %s, %s, %s, %s, %s)", (romaneio_id, itm["produto"], itm["quantidade"], itm["unidade"], itm["valor_unitario"], itm["valor_total"]))
                        else:
                            cursor.execute("INSERT INTO romaneio_itens (romaneio_id, produto, quantidade, unidade, valor_unitario, valor_total) VALUES (?, ?, ?, ?, ?, ?)", (romaneio_id, itm["produto"], itm["quantidade"], itm["unidade"], itm["valor_unitario"], itm["valor_total"]))
                        itens_salvos_pdf.append([None, itm["produto"], itm["quantidade"], itm["unidade"], itm["valor_unitario"], itm["valor_total"]])

                    conn.commit()
                    conn.close()

                    romaneio_dict_atual = {
                        "numero_romaneio": num_rom_final,
                        "data_recebimento": data_rec_str,
                        "fornecedor": forn_final,
                        "codigo_fornecedor": cod_forn_val,
                        "telefone_fornecedor": tel_fornecedor,
                        "loja": loja,
                        "loja_origem": loja_origem,
                        "loja_destino": loja_destino,
                        "conferente": user_info["nome"],
                        "pagamento_a_vista": pag_a_vista,
                        "data_pagamento": data_pag_str,
                        "tipo_operacao": tipo_operacao,
                        "observacoes": observacoes_romaneio
                    }
                    pdf_buffer_novo = gerar_pdf_romaneio(romaneio_dict_atual, itens_salvos_pdf, path_ass_conf, path_ass_ent)
                    st.session_state["ultimo_pdf_bytes"] = pdf_buffer_novo.getvalue()
                    st.session_state["ultimo_num_romaneio"] = num_rom_final
                    st.session_state["itens_romaneio"] = []
                    st.session_state["form_key_suffix"] += 1
                    st.session_state["item_key_suffix"] = 0
                    st.success(f"Romaneio {num_rom_final} gerado e salvo com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar romaneio: {e}")

        if "ultimo_pdf_bytes" in st.session_state and "ultimo_num_romaneio" in st.session_state:
            st.markdown("---")
            st.success(f"📄 Romaneio **{st.session_state['ultimo_num_romaneio']}** pronto para download!")
            st.download_button(
                label=f"📥 Descarregar PDF - {st.session_state['ultimo_num_romaneio']}",
                data=st.session_state["ultimo_pdf_bytes"],
                file_name=f"{st.session_state['ultimo_num_romaneio']}.pdf",
                mime="application/pdf",
                type="primary"
            )

    elif menu == "Consultar Romaneios":
        st.title("🔍 Consultar & Gerenciar Romaneios de Recebimento")
        conn, db_type = get_db_connection()
        df_rom = pd.read_sql_query("SELECT * FROM romaneios ORDER BY id DESC", conn)
        df_all_itens = pd.read_sql_query("SELECT romaneio_id, SUM(valor_total) as valor_total_rom FROM romaneio_itens GROUP BY romaneio_id", conn)
        conn.close()

        if df_rom.empty:
            st.info("Nenhum romaneio registrado no sistema.")
        else:
            if not df_all_itens.empty:
                df_rom = df_rom.merge(df_all_itens, left_on="id", right_on="romaneio_id", how="left")
                df_rom["valor_total_rom"] = df_rom["valor_total_rom"].fillna(0.0)
            else:
                df_rom["valor_total_rom"] = 0.0

            lista_lojas_sistema = ["LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
            if not is_admin and loja_atual_usuario in lista_lojas_sistema:
                lojas_para_exibir = [loja_atual_usuario]
            else:
                lojas_para_exibir = lista_lojas_sistema

            tabs_lojas = st.tabs([f"🏪 {l}" for l in lojas_para_exibir])
            for idx_l, loja_nome in enumerate(lojas_para_exibir):
                with tabs_lojas[idx_l]:
                    st.markdown(f"### 📋 Romaneios - {loja_nome}")
                    df_loja_atual = df_rom[
                        df_rom["loja"].str.contains(loja_nome, case=False, na=False) |
                        df_rom.get("loja_destino", pd.Series(dtype=str)).str.contains(loja_nome, case=False, na=False)
                    ].copy()

                    if df_loja_atual.empty:
                        st.info(f"Nenhum romaneio registrado para a {loja_nome}.")
                    else:
                        tipos_operacao_disponiveis = ["TODOS OS TIPOS", "Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"]
                        subtabs_tipo = st.tabs([f"📌 {t}" for t in tipos_operacao_disponiveis])
                        for idx_t, tipo_op in enumerate(tipos_operacao_disponiveis):
                            with subtabs_tipo[idx_t]:
                                if tipo_op == "TODOS OS TIPOS":
                                    df_tipo_atual = df_loja_atual.copy()
                                else:
                                    df_tipo_atual = df_loja_atual[df_loja_atual["tipo_operacao"].str.contains(tipo_op, case=False, na=False)].copy()

                                if df_tipo_atual.empty:
                                    st.markdown("<p style='color: #9aa0a6; font-style: italic; padding: 10px;'>Nenhum romaneio encontrado nesta categoria.</p>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"**Total de registros em '{tipo_op}':** {len(df_tipo_atual)}")
                                    df_planilha = df_tipo_atual.copy()
                                    df_planilha["Valor Total"] = df_planilha["valor_total_rom"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")

                                    df_planilha_show = df_planilha.rename(columns={
                                        "numero_romaneio": "N° Romaneio",
                                        "tipo_operacao": "Tipo Operação",
                                        "loja": "Loja",
                                        "data_recebimento": "Data Recebimento",
                                        "fornecedor": "Fornecedor",
                                        "conferente": "Conferente",
                                        "status_nota": "Status Atual"
                                    })
                                    cols_view = df_planilha_show[["N° Romaneio", "Tipo Operação", "Loja", "Data Recebimento", "Fornecedor", "Conferente", "Valor Total", "Status Atual"]]
                                    cols_view.index = range(1, len(cols_view) + 1)
                                    st.dataframe(cols_view, use_container_width=True, height=280)

                                    st.markdown("---")
                                    st.subheader("⚙️ Gerenciador de Romaneio: Visualizar Anexo, Atualizar Status e Editar (Admin)")
                                    opcoes_rom_gerenciar = [(row["id"], f"Romaneio {row['numero_romaneio']} | Status: {row.get('status_nota','Pendente')} | Fornecedor: {row['fornecedor'] or 'N/A'} | Data: {row['data_recebimento']}") for _, row in df_tipo_atual.iterrows()]
                                    chave_tab = f"{loja_nome}_{tipo_op}".replace(" ", "_").replace("/", "_")
                                    rom_sel_tuple = st.selectbox(
                                        "Selecione o Romaneio na Planilha para Ações",
                                        options=opcoes_rom_gerenciar,
                                        format_func=lambda x: x[1],
                                        key=f"sel_rom_planilha_{chave_tab}"
                                    )
                                    if rom_sel_tuple:
                                        id_rom_sel = rom_sel_tuple[0]
                                        row_sel = df_tipo_atual[df_tipo_atual["id"] == id_rom_sel].iloc[0]
                                        chv_elem = f"{chave_tab}_{id_rom_sel}"

                                        col_anx, col_st, col_pdf_act = st.columns([2, 2.5, 2.5])
                                        with col_anx:
                                            st.markdown("**📎 Coluna de Anexo**")
                                            cam_foto = row_sel.get('caminho_foto', '')
                                            b64_foto_rom = row_sel.get('foto_b64', '')
                                            if cam_foto or b64_foto_rom:
                                                if st.button("🖼️ Visualizar Nota / Anexo", key=f"btn_ver_anx_grid_{chv_elem}", type="primary"):
                                                    exibir_foto_modal(cam_foto, b64_foto_rom)
                                            else:
                                                st.info("Sem anexo anexado.")

                                        with col_st:
                                            st.markdown("**📌 Coluna de Mudança de Status**")
                                            opcoes_status_rom = ["Pendente", "Nota Emitida", "Trocado", "Lançado"]
                                            st_atual = row_sel.get("status_nota", "Pendente")
                                            idx_st_padr = opcoes_status_rom.index(st_atual) if st_atual in opcoes_status_rom else 0
                                            col_sel_s, col_btn_s = st.columns([1.8, 1.2])
                                            with col_sel_s:
                                                novo_st_sel = st.selectbox("Status", opcoes_status_rom, index=idx_st_padr, key=f"sel_st_grid_{chv_elem}", label_visibility="collapsed")
                                            with col_btn_s:
                                                if st.button("💾 Salvar Status", key=f"btn_st_grid_{chv_elem}"):
                                                    spinner_supernova("Atualizando status...")
                                                    try:
                                                        conn_st, db_t_st = get_db_connection()
                                                        cur_st = conn_st.cursor()
                                                        cur_st.execute(
                                                            "UPDATE romaneios SET status_nota = %s WHERE id = %s" if db_t_st == "postgres" else "UPDATE romaneios SET status_nota = ? WHERE id = ?",
                                                            (novo_st_sel, int(id_rom_sel) if db_t_st == "postgres" else id_rom_sel)
                                                        )
                                                        conn_st.commit()
                                                        conn_st.close()
                                                        st.success("Status atualizado com sucesso!")
                                                        st.rerun()
                                                    except Exception as e: st.error(f"Erro ao salvar status: {e}")

                                        with col_pdf_act:
                                            st.markdown("**📄 Relatório PDF / Exclusão**")
                                            conn_i, db_t_i = get_db_connection()
                                            df_itens_r = pd.read_sql_query("SELECT produto, quantidade, unidade, valor_unitario, valor_total FROM romaneio_itens WHERE romaneio_id = %s" if db_t_i == "postgres" else "SELECT produto, quantidade, unidade, valor_unitario, valor_total FROM romaneio_itens WHERE romaneio_id = ?", conn_i, params=(int(id_rom_sel) if db_t_i == "postgres" else id_rom_sel,))
                                            conn_i.close()

                                            pdf_buf = gerar_pdf_romaneio(row_sel.to_dict(), [(None, r['produto'], r['quantidade'], r['unidade'], r['valor_unitario'], r['valor_total']) for _, r in df_itens_r.iterrows()], row_sel.get("assinatura_conferente"), row_sel.get("assinatura_entregador"))
                                            col_dl_p, col_del_p = st.columns([2, 1])
                                            with col_dl_p:
                                                st.download_button(
                                                    label="📥 Baixar PDF",
                                                    data=pdf_buf,
                                                    file_name=f"{row_sel['numero_romaneio']}.pdf",
                                                    mime="application/pdf",
                                                    key=f"btn_pdf_grid_{chv_elem}"
                                                )
                                            with col_del_p:
                                                if is_admin:
                                                    if st.button("🗑️", key=f"btn_del_grid_{chv_elem}", help="Excluir Romaneio", type="secondary"):
                                                        spinner_supernova("Excluindo romaneio...")
                                                        try:
                                                            conn_del, db_t_del = get_db_connection()
                                                            cur_del = conn_del.cursor()
                                                            cur_del.execute("DELETE FROM romaneio_itens WHERE romaneio_id = %s" if db_t_del == "postgres" else "DELETE FROM romaneio_itens WHERE romaneio_id = ?", (int(id_rom_sel) if db_t_del == "postgres" else id_rom_sel,))
                                                            cur_del.execute("DELETE FROM romaneios WHERE id = %s" if db_t_del == "postgres" else "DELETE FROM romaneios WHERE id = ?", (int(id_rom_sel) if db_t_del == "postgres" else id_rom_sel,))
                                                            conn_del.commit()
                                                            conn_del.close()
                                                            st.success("Excluído com sucesso!")
                                                            st.rerun()
                                                        except Exception as e: st.error(f"Erro: {e}")

                                        with st.expander(f"📦 Ver Itens Cadastrados no Romaneio {row_sel['numero_romaneio']}", expanded=False):
                                            if not df_itens_r.empty:
                                                df_itens_show = df_itens_r.copy()
                                                df_itens_show['Qtd / Peso'] = df_itens_show['quantidade'].apply(lambda x: fmt_ptbr(x, 3))
                                                df_itens_show['Vl. Unit'] = df_itens_show['valor_unitario'].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                                                df_itens_show['Total'] = df_itens_show['valor_total'].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                                                st.dataframe(df_itens_show[['produto', 'Qtd / Peso', 'unidade', 'Vl. Unit', 'Total']], use_container_width=True, hide_index=True)
                                            else:
                                                st.info("Nenhum item vinculado a este romaneio.")

                                        if is_admin:
                                            with st.expander(f"✏️ Editar Romaneio {row_sel['numero_romaneio']} (Apenas Administrador)", expanded=False):
                                                with st.form(f"form_edicao_romaneio_admin_{chv_elem}"):
                                                    st.markdown(f"**Edição dos Dados do Romaneio {row_sel['numero_romaneio']}**")
                                                    col_ed_r1, col_ed_r2, col_ed_r3 = st.columns(3)
                                                    with col_ed_r1:
                                                        novo_forn_ed = st.text_input("Fornecedor", value=row_sel["fornecedor"] or "")
                                                        novo_cod_forn_ed = st.text_input("Cód. Fornecedor", value=row_sel["codigo_fornecedor"] or "")
                                                    with col_ed_r2:
                                                        novo_tel_ed = st.text_input("Telefone Fornecedor", value=row_sel["telefone_fornecedor"] or "")
                                                        novo_tipo_op_ed = st.selectbox("Tipo Operação", ["Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"], index=(["Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"].index(row_sel["tipo_operacao"]) if row_sel["tipo_operacao"] in ["Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"] else 0))
                                                    with col_ed_r3:
                                                        novo_pag_v_ed = st.selectbox("Pagamento à Vista?", ["SIM", "NÃO"], index=(0 if row_sel["pagamento_a_vista"] == "SIM" else 1))
                                                        nova_dt_pag_ed = st.text_input("Data Pagamento", value=row_sel["data_pagamento"] or "")
                                                    novas_obs_ed = st.text_area("Observações", value=row_sel["observacoes"] or "")
                                                    novo_anexo_rom_up = st.file_uploader("Substituir Nota / Anexo (Opcional)", type=["pdf", "png", "jpg", "jpeg"], key=f"up_edit_rom_{chv_elem}")
                                                    btn_salvar_ed_rom = st.form_submit_button("💾 Salvar Alterações do Romaneio", type="primary")

                                                    if btn_salvar_ed_rom:
                                                        spinner_supernova("Salvando alterações do romaneio...")
                                                        try:
                                                            path_foto_ed = row_sel.get("caminho_foto", "")
                                                            b64_foto_ed = row_sel.get("foto_b64", "")
                                                            if novo_anexo_rom_up:
                                                                path_foto_ed = os.path.join("uploads", f"ROM_EDIT_{row_sel['numero_romaneio']}_{novo_anexo_rom_up.name}")
                                                                b_up_rom = novo_anexo_rom_up.getbuffer()
                                                                with open(path_foto_ed, "wb") as f_out: f_out.write(b_up_rom)
                                                                b64_foto_ed = base64.b64encode(b_up_rom).decode('utf-8')

                                                            conn_urom, db_turom = get_db_connection()
                                                            cur_urom = conn_urom.cursor()
                                                            cur_urom.execute(
                                                                "UPDATE romaneios SET fornecedor = %s, codigo_fornecedor = %s, telefone_fornecedor = %s, tipo_operacao = %s, pagamento_a_vista = %s, data_pagamento = %s, observacoes = %s, caminho_foto = %s, foto_b64 = %s WHERE id = %s" if db_turom == "postgres" else "UPDATE romaneios SET fornecedor = ?, codigo_fornecedor = ?, telefone_fornecedor = ?, tipo_operacao = ?, pagamento_a_vista = ?, data_pagamento = ?, observacoes = ?, caminho_foto = ?, foto_b64 = ? WHERE id = ?",
                                                                (novo_forn_ed.strip(), novo_cod_forn_ed.strip(), novo_tel_ed.strip(), novo_tipo_op_ed, novo_pag_v_ed, nova_dt_pag_ed.strip(), novas_obs_ed.strip(), path_foto_ed, b64_foto_ed, int(id_rom_sel) if db_turom == "postgres" else id_rom_sel)
                                                            )
                                                            conn_urom.commit()
                                                            conn_urom.close()
                                                            st.success("Romaneio atualizado com sucesso pelo administrador!")
                                                            st.rerun()
                                                        except Exception as e: st.error(f"Erro ao editar romaneio: {e}")

    elif menu == "Controle de Bonificação":
        st.title("🛒 Controle de Bonificação Hortifrúti")
        conn_prod, db_p = get_db_connection()
        cursor_p = conn_prod.cursor()
        cursor_p.execute("SELECT codigo_produto, codigo_barras, nome FROM produtos ORDER BY nome")
        prods_cad = cursor_p.fetchall()
        conn_prod.close()

        lista_opcoes_prod = []
        for p in prods_cad:
            c_prod = p[0] if p[0] and str(p[0]).strip() else "S/Cód"
            c_bar = p[1] if p[1] and str(p[1]).strip() else "S/Barras"
            lista_opcoes_prod.append(f"{c_prod} | Barras: {c_bar} | {p[2]}")

        with st.expander("➕ Cadastrar Nova Bonificação", expanded=False):
            with st.form("form_cad_bonificacao", clear_on_submit=True):
                col_b1, col_b2, col_b3 = st.columns([1.5, 1.5, 1.5])
                with col_b1:
                    num_nota_bonf = st.text_input("N° Nota Fiscal", value="", placeholder="Número da nota...")
                    lista_lojas_cad_b = ["", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                    idx_l_cad_b = lista_lojas_cad_b.index(loja_atual_usuario) if loja_atual_usuario in lista_lojas_cad_b else 0
                    loja_bonf = st.selectbox("Loja", lista_lojas_cad_b, index=idx_l_cad_b, placeholder="Selecione a loja...", key="loja_bonf_sel")
                with col_b2:
                    valor_bonf_str = st.text_input("Valor da Bonificação (R$)", value="", placeholder="0,00")
                    tipo_bonf_sel = st.selectbox("Tipo de Bonificação", ["", "Bonificação", "Transferência de Bonificação"], index=0, placeholder="Selecione o tipo...", key="tipo_bonf_input_sel")
                with col_b3:
                    prod_bonf = st.selectbox("Produto Hortifrúti", options=[""] + lista_opcoes_prod, index=0, placeholder="Selecione o produto...")
                    anexo_bonf = st.file_uploader("Anexar NF (PDF ou Imagem)", type=["pdf", "png", "jpg", "jpeg"])

                col_dt1, col_dt2, col_dt3 = st.columns([1.5, 1.5, 1.5])
                with col_dt1: status_bonf = st.selectbox("STATUS", ["", "Disponível", "Parcialmente Utilizada", "Totalmente Utilizada"], index=0, placeholder="Selecione o status...")
                with col_dt2: data_entrada_manual = st.date_input("Data de Entrada", value=datetime.now(ZoneInfo("America/Manaus")), format="DD/MM/YYYY")
                with col_dt3:
                    hora_auto = datetime.now(ZoneInfo("America/Manaus")).strftime('%H:%M:%S')
                    st.text_input("Hora de Entrada", value=hora_auto, disabled=True)

                dt_entrada_str = f"{data_entrada_manual.strftime('%d/%m/%Y')} {hora_auto}" if data_entrada_manual else ""
                if st.form_submit_button("✅ Salvar Bonificação", type="primary"):
                    if not num_nota_bonf.strip() or not loja_bonf or not prod_bonf or not status_bonf:
                        st.error("Preencha todos os campos obrigatórios.")
                    else:
                        spinner_supernova("Salvando bonificação...")
                        try: valor_bonf_val = float(valor_bonf_str.replace(".", "").replace(",", ".")) if valor_bonf_str else 0.0
                        except ValueError: valor_bonf_val = 0.0

                        path_anexo_bonf = ""
                        b64_anexo_bonf = ""
                        if anexo_bonf:
                            path_anexo_bonf = os.path.join("uploads", f"NF_{num_nota_bonf}_{anexo_bonf.name}")
                            anexo_bytes = anexo_bonf.getbuffer()
                            with open(path_anexo_bonf, "wb") as f_out: f_out.write(anexo_bytes)
                            b64_anexo_bonf = base64.b64encode(anexo_bytes).decode('utf-8')

                        try:
                            conn_b, db_tb = get_db_connection()
                            cursor_b = conn_b.cursor()
                            cursor_b.execute(
                                "INSERT INTO bonificacoes (numero_nota, loja, data_entrada, valor_bonificacao, status, produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)" if db_tb == "postgres" else "INSERT INTO bonificacoes (numero_nota, loja, data_entrada, valor_bonificacao, status, produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                (num_nota_bonf.strip(), loja_bonf, dt_entrada_str, valor_bonf_val, status_bonf, prod_bonf, path_anexo_bonf, tipo_bonf_sel, b64_anexo_bonf)
                            )
                            conn_b.commit()
                            conn_b.close()
                            st.success("Salvo com sucesso!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        st.markdown("---")
        st.subheader("📋 Registros de Bonificação e Consulta de Notas")
        lista_lojas_filtro_bonf = ["TODAS", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
        idx_filtro_bonf = 0
        if not is_admin and loja_atual_usuario in lista_lojas_filtro_bonf:
            idx_filtro_bonf = lista_lojas_filtro_bonf.index(loja_atual_usuario)

        with st.expander("🔍 Filtros de Busca", expanded=True):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1: f_nota = st.text_input("Filtrar por N° Nota", value="", placeholder="N° da nota...", key="f_nota_bonf")
            with f_col2: f_loja = st.selectbox("Filtrar por Loja", options=lista_lojas_filtro_bonf, index=idx_filtro_bonf, placeholder="Selecione...", key="f_loja_bonf")
            with f_col3: f_status = st.selectbox("Filtrar por Status", ["TODOS", "Disponível", "Parcialmente Utilizada", "Totalmente Utilizada"], placeholder="Selecione...", key="f_status_bonf")
            with f_col4: f_prod = st.text_input("Filtrar por Produto", value="", placeholder="Produto...", key="f_prod_bonf")

        conn_b_sel, db_tb_sel = get_db_connection()
        df_bonf = pd.read_sql_query("SELECT * FROM bonificacoes ORDER BY id DESC", conn_b_sel)
        conn_b_sel.close()

        if not df_bonf.empty:
            if f_nota.strip(): df_bonf = df_bonf[df_bonf["numero_nota"].str.contains(f_nota.strip(), case=False, na=False)]
            if f_loja != "TODAS": df_bonf = df_bonf[df_bonf["loja"] == f_loja]
            if f_status != "TODOS": df_bonf = df_bonf[df_bonf["status"] == f_status]
            if f_prod.strip(): df_bonf = df_bonf[df_bonf["produto_hortifruti"].str.contains(f_prod.strip(), case=False, na=False)]

            if not df_bonf.empty:
                tot_bonf_val = df_bonf["valor_bonificacao"].sum()
                tot_disp_val = df_bonf[df_bonf["status"] == "Disponível"]["valor_bonificacao"].sum()
                tot_parc_val = df_bonf[df_bonf["status"] == "Parcialmente Utilizada"]["valor_bonificacao"].sum()
                tot_util_val = df_bonf[df_bonf["status"] == "Totalmente Utilizada"]["valor_bonificacao"].sum()

                kpi_b1, kpi_b2, kpi_b3, kpi_b4 = st.columns(4)
                kpi_b1.metric("Total Bonificado", f"R$ {fmt_ptbr(tot_bonf_val, 2)}")
                kpi_b2.metric("Disponível", f"R$ {fmt_ptbr(tot_disp_val, 2)}")
                kpi_b3.metric("Parcialmente Utilizada", f"R$ {fmt_ptbr(tot_parc_val, 2)}")
                kpi_b4.metric("Totalmente Utilizada", f"R$ {fmt_ptbr(tot_util_val, 2)}")

                st.markdown("---")
                pdf_bonf_bytes = gerar_pdf_bonificacoes(df_bonf)
                st.download_button(
                    label="📥 Descarregar Relatório de Bonificação em PDF",
                    data=pdf_bonf_bytes,
                    file_name=f"Relatorio_Bonificacao_HortiControl_{datetime.now(ZoneInfo('America/Manaus')).strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    key="btn_download_pdf_bonf"
                )
                st.markdown("")

                df_bonf_tabela = df_bonf.copy()
                df_bonf_tabela["Valor (R$)"] = df_bonf_tabela["valor_bonificacao"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_bonf_tabela["Anexo"] = df_bonf_tabela.apply(lambda r: "📎 Disponível" if (r.get("caminho_anexo") and os.path.exists(r["caminho_anexo"])) or r.get("anexo_b64") else "Sem Anexo", axis=1)
                df_bonf_tabela = df_bonf_tabela.rename(columns={
                    "numero_nota": "N° Nota",
                    "tipo_bonificacao": "Tipo",
                    "loja": "Loja",
                    "data_entrada": "Data e Hora",
                    "status": "Status",
                    "produto_hortifruti": "Produto Hortifrúti"
                })
                cols_exibidas = df_bonf_tabela[["N° Nota", "Tipo", "Loja", "Data e Hora", "Valor (R$)", "Status", "Produto Hortifrúti", "Anexo"]]
                cols_exibidas.index = range(1, len(cols_exibidas) + 1)
                st.dataframe(cols_exibidas, use_container_width=True, height=350)

                st.markdown("---")
                st.subheader("⚙️ Abertura de Anexo, Edição & Exclusão de Registro")
                opcoes_notas_editar = [(row["id"], f"Nota N° {row['numero_nota']} - {row['loja']} | Status: {row['status']} ({row['data_entrada']})") for _, row in df_bonf.iterrows()]
                col_ed1, col_ed2 = st.columns(2)
                with col_ed1:
                    nota_selecionada_edicao = st.selectbox("Selecione o Registro para Gerenciar / Abrir Anexo", options=opcoes_notas_editar, format_func=lambda x: x[1], key="sel_registro_bonf_gerenciar")
                with col_ed2:
                    st.write("")
                    st.write("")
                    id_reg_atual = nota_selecionada_edicao[0]
                    reg_obj_atual = df_bonf[df_bonf["id"] == id_reg_atual].iloc[0]
                    caminho_nota_alvo = reg_obj_atual.get("caminho_anexo", "")
                    b64_anexo_reg = reg_obj_atual.get("anexo_b64", "")
                    if caminho_nota_alvo or b64_anexo_reg:
                        if st.button("🖼️ Abrir Anexo / Nota Fiscal", type="primary", key="btn_abrir_anexo_direto_tabela"):
                            exibir_foto_modal(caminho_nota_alvo, b64_anexo_reg)
                    else:
                        st.warning("Este registo não possui ficheiro de nota anexado.")

                with st.form("form_edicao_direta_bonificacao"):
                    st.markdown(f"**Editando Nota N° {reg_obj_atual['numero_nota']} ({reg_obj_atual['loja']})**")
                    data_atual_str = str(reg_obj_atual["data_entrada"]).split(" ")[0] if reg_obj_atual["data_entrada"] else ""
                    try: dt_obj_default = datetime.strptime(data_atual_str, "%d/%m/%Y").date()
                    except Exception: dt_obj_default = datetime.now(ZoneInfo("America/Manaus")).date()

                    col_e1, col_e2, col_e3, col_e4, col_e5 = st.columns(5)
                    with col_e1: novo_val_nota_str = st.text_input("Valor (R$)", value=str(reg_obj_atual["valor_bonificacao"]).replace(".", ","))
                    with col_e2:
                        lista_lojas_alt = ["LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                        idx_loja_alt = lista_lojas_alt.index(reg_obj_atual["loja"]) if reg_obj_atual["loja"] in lista_lojas_alt else 0
                        nova_loja_nota = st.selectbox("Loja", lista_lojas_alt, index=idx_loja_alt)
                    with col_e3: nova_data_input = st.date_input("Data de Entrada", value=dt_obj_default, format="DD/MM/YYYY")
                    with col_e4:
                        status_atuais_lst = ["Disponível", "Parcialmente Utilizada", "Totalmente Utilizada"]
                        idx_st_atual = status_atuais_lst.index(reg_obj_atual["status"]) if reg_obj_atual["status"] in status_atuais_lst else 0
                        novo_st_nota = st.selectbox("Status", status_atuais_lst, index=idx_st_atual)
                    with col_e5: novo_prod_nota = st.text_input("Produto Hortifrúti", value=reg_obj_atual["produto_hortifruti"])

                    novo_anexo_up = st.file_uploader("Substituir / Enviar Novo Anexo (Opcional)", type=["pdf", "png", "jpg", "jpeg"])
                    col_btn_up1, col_btn_up2 = st.columns(2)
                    with col_btn_up1: salvar_alt_bonf = st.form_submit_button("💾 Salvar Alterações", type="primary")
                    with col_btn_up2: excluir_bonf_btn = st.form_submit_button("🗑️ Excluir Bonificação", type="secondary")

                    if salvar_alt_bonf:
                        spinner_supernova("Salvando alterações...")
                        try:
                            val_f_edit = float(novo_val_nota_str.replace(".", "").replace(",", ".")) if novo_val_nota_str else reg_obj_atual["valor_bonificacao"]
                            hora_antiga = "00:00:00"
                            if len(str(reg_obj_atual["data_entrada"]).split(" ")) > 1:
                                hora_antiga = str(reg_obj_atual["data_entrada"]).split(" ")[1]
                            nova_data_str = f"{nova_data_input.strftime('%d/%m/%Y')} {hora_antiga}"

                            path_novo_arq = reg_obj_atual["caminho_anexo"]
                            b64_novo_arq = reg_obj_atual.get("anexo_b64", "")
                            if novo_anexo_up:
                                path_novo_arq = os.path.join("uploads", f"NF_EDIT_{reg_obj_atual['numero_nota']}_{novo_anexo_up.name}")
                                bytes_up = novo_anexo_up.getbuffer()
                                with open(path_novo_arq, "wb") as f_out: f_out.write(bytes_up)
                                b64_novo_arq = base64.b64encode(bytes_up).decode('utf-8')

                            conn_up_dir, db_t_upd = get_db_connection()
                            cursor_upd = conn_up_dir.cursor()
                            cursor_upd.execute(
                                "UPDATE bonificacoes SET valor_bonificacao = %s, loja = %s, data_entrada = %s, status = %s, produto_hortifruti = %s, caminho_anexo = %s, anexo_b64 = %s WHERE id = %s" if db_t_upd == "postgres" else "UPDATE bonificacoes SET valor_bonificacao = ?, loja = ?, data_entrada = ?, status = ?, produto_hortifruti = ?, caminho_anexo = ?, anexo_b64 = ? WHERE id = ?",
                                (val_f_edit, nova_loja_nota, nova_data_str, novo_st_nota, novo_prod_nota, path_novo_arq, b64_novo_arq, int(id_reg_atual) if db_t_upd == "postgres" else id_reg_atual)
                            )
                            conn_up_dir.commit()
                            conn_up_dir.close()
                            st.success("Registo atualizado com sucesso!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro ao atualizar: {e}")

                    if excluir_bonf_btn:
                        spinner_supernova("Excluindo bonificação...")
                        try:
                            conn_del_b, db_td_b = get_db_connection()
                            cursor_db = conn_del_b.cursor()
                            cursor_db.execute(
                                "DELETE FROM bonificacoes WHERE id = %s" if db_td_b == "postgres" else "DELETE FROM bonificacoes WHERE id = ?",
                                (int(id_reg_atual) if db_td_b == "postgres" else id_reg_atual,)
                            )
                            conn_del_b.commit()
                            conn_del_b.close()
                            st.success("Bonificação excluída com sucesso!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro ao excluir: {e}")
        else:
            st.info("Nenhuma bonificação encontrada.")

    elif menu == "Controle de Baixa de Avarias":
        st.title("📉 Registro de Baixas das Avarias")
        loja_ativa_sessao = user_info.get("loja_atual", "LOJA 02 NOVA CIDADE")
        if "baixa_form_suffix" not in st.session_state:
            st.session_state["baixa_form_suffix"] = 0
        bx_suf = st.session_state["baixa_form_suffix"]

        conn_bx_chk, db_tbx_chk = get_db_connection()
        df_baixar_hist = pd.read_sql_query("SELECT * FROM baixas_avarias", conn_bx_chk)
        conn_bx_chk.close()

        total_baixado_por_nota = {}
        if not df_baixar_hist.empty:
            totais_por_nf = df_baixar_hist.groupby("nf_b_entrada")["valor_total_avaria"].sum()
            for nf_e, val_bx in totais_por_nf.items():
                total_baixado_por_nota[str(nf_e)] = float(val_bx)

        conn_b_all, db_tb_all = get_db_connection()
        df_todas_bonf = pd.read_sql_query("SELECT * FROM bonificacoes", conn_b_all)
        if not df_todas_bonf.empty:
            cur_st_up = conn_b_all.cursor()
            for _, r_b in df_todas_bonf.iterrows():
                num_nf_b = str(r_b["numero_nota"])
                val_orig_b = float(r_b["valor_bonificacao"])
                baixado_b = total_baixado_por_nota.get(num_nf_b, 0.0)
                saldo_b = max(0.0, val_orig_b - baixado_b)
                if baixado_b <= 0: novo_st_auto = "Disponível"
                elif saldo_b > 0: novo_st_auto = "Parcialmente Utilizada"
                else: novo_st_auto = "Totalmente Utilizada"
                if r_b["status"] != novo_st_auto:
                    cur_st_up.execute(
                        "UPDATE bonificacoes SET status = %s WHERE id = %s" if db_tb_all == "postgres" else "UPDATE bonificacoes SET status = ? WHERE id = ?",
                        (novo_st_auto, int(r_b["id"]) if db_tb_all == "postgres" else r_b["id"])
                    )
            conn_b_all.commit()
        conn_b_all.close()

        conn_b_all2, db_tb_all2 = get_db_connection()
        df_todas_bonf = pd.read_sql_query("SELECT * FROM bonificacoes", conn_b_all2)
        conn_b_all2.close()

        dict_valor_orig_por_nf = {}
        if not df_todas_bonf.empty:
            for _, r_b in df_todas_bonf.iterrows():
                dict_valor_orig_por_nf[str(r_b["numero_nota"])] = float(r_b["valor_bonificacao"])

        if not df_todas_bonf.empty:
            df_bonf_loja02 = df_todas_bonf[df_todas_bonf["loja"].str.contains("02|NOVA CIDADE", case=False, na=False) & df_todas_bonf["status"].isin(["Disponível", "Parcialmente Utilizada"])]
        else:
            df_bonf_loja02 = pd.DataFrame()

        notas_com_saldo_loja02 = []
        saldo_geral_somado_loja02 = 0.0
        if not df_bonf_loja02.empty:
            for _, r_bonf in df_bonf_loja02.iterrows():
                num_nf_ent = str(r_bonf["numero_nota"])
                val_original = float(r_bonf["valor_bonificacao"])
                ja_baixado = total_baixado_por_nota.get(num_nf_ent, 0.0)
                saldo_restante_nota = max(0.0, val_original - ja_baixado)
                if saldo_restante_nota > 0:
                    saldo_geral_somado_loja02 += saldo_restante_nota
                    notas_com_saldo_loja02.append({
                        "nf_entrada": num_nf_ent,
                        "produto": r_bonf["produto_hortifruti"],
                        "valor_original": val_original,
                        "saldo_restante": saldo_restante_nota
                    })

        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; background: rgba(30, 35, 42, 0.9); padding: 12px 18px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.15); margin-bottom: 15px;">
            <span style="font-size: 20px;">💳</span>
            <span style="color: #FFFFFF; font-weight: 700; font-size: 15px;">Saldo Total Disponível (Referente às notas da Loja 02): R$ {fmt_ptbr(saldo_geral_somado_loja02, 2)}</span>
        </div>
        """, unsafe_allow_html=True)

        if notas_com_saldo_loja02:
            with st.expander("📌 Notas com Saldo Disponível (Loja 02 - Base para Baixas)", expanded=True):
                df_ns_show = pd.DataFrame(notas_com_saldo_loja02)
                df_ns_show["Valor Original (R$)"] = df_ns_show["valor_original"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_ns_show["Saldo Disponível (R$)"] = df_ns_show["saldo_restante"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_ns_show = df_ns_show.rename(columns={"nf_entrada": "N° Nota de Entrada", "produto": "Produto Hortifrúti"})
                st.dataframe(df_ns_show[["N° Nota de Entrada", "Produto Hortifrúti", "Valor Original (R$)", "Saldo Disponível (R$)"]], use_container_width=True, hide_index=True, height=200)

        conn_prod_v, db_pv = get_db_connection()
        cursor_pv = conn_prod_v.cursor()
        cursor_pv.execute("SELECT codigo_produto, codigo_barras, nome FROM produtos ORDER BY nome")
        prods_cad_v = cursor_pv.fetchall()
        conn_prod_v.close()
        lista_opcoes_prod_v = []
        for p in prods_cad_v:
            c_prod = p[0] if p[0] and str(p[0]).strip() else "S/Cód"
            c_bar = p[1] if p[1] and str(p[1]).strip() else "S/Barras"
            lista_opcoes_prod_v.append(f"{c_prod} | Barras: {c_bar} | {p[2]}")

        with st.expander("➕ Registrar Nova Baixa de Avaria", expanded=False):
            with st.form(f"form_registro_baixa_modelo_{bx_suf}", clear_on_submit=True):
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    lista_lojas_reg = ["LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                    idx_l_ativa = lista_lojas_reg.index(loja_ativa_sessao) if loja_ativa_sessao in lista_lojas_reg else 0
                    lojas_baixa_sel = st.selectbox("LOJAS", options=lista_lojas_reg, index=idx_l_ativa, key=f"bx_loja_{bx_suf}")
                    ref_bon_transf = st.text_input("Ref. Bon. transferen", value="", placeholder="Referência...", key=f"bx_ref_{bx_suf}")
                with col_m2:
                    opcoes_nf_entrada = [item["nf_entrada"] for item in notas_com_saldo_loja02] if notas_com_saldo_loja02 else ["Nenhuma Nota Disponível"]
                    nf_b_entrada_sel = st.selectbox("NF de B. ENTRADA", options=opcoes_nf_entrada, key=f"bx_nf_ent_{bx_suf}")
                    prod_hort_sel = st.selectbox("Produto Hortifrúti", options=[""] + lista_opcoes_prod_v, index=0, key=f"bx_prod_{bx_suf}")
                with col_m3:
                    qtd_kg_cx_str = st.text_input("Qtd (kg/cx)", value="", placeholder="0,000", key=f"bx_qtd_{bx_suf}")
                    valor_total_avaria_str = st.text_input("Valor Total Avaria (R$)", value="", placeholder="0,00", key=f"bx_val_{bx_suf}")
                    nf_baixa_file = st.file_uploader("NF da baixa (Anexo)", type=["pdf", "png", "jpg", "jpeg"], key=f"bx_file_{bx_suf}")

                col_dm1, col_dm2 = st.columns(2)
                with col_dm1: data_baixa_man = st.date_input("Data da Baixa", value=datetime.now(ZoneInfo("America/Manaus")), format="DD/MM/YYYY", key=f"bx_dt_{bx_suf}")
                with col_dm2:
                    hora_baixa_aut = datetime.now(ZoneInfo("America/Manaus")).strftime('%H:%M:%S')
                    st.text_input("Hora da Baixa", value=hora_baixa_aut, disabled=True, key=f"bx_hr_{bx_suf}")

                data_hora_baixa_str = f"{data_baixa_man.strftime('%d/%m/%Y')} {hora_baixa_aut}" if data_baixa_man else ""
                btn_enviar_baixa = st.form_submit_button("✅ Registrar Baixa", type="primary")

                if btn_enviar_baixa:
                    if not lojas_baixa_sel or not ref_bon_transf.strip() or nf_b_entrada_sel == "Nenhuma Nota Disponível" or not prod_hort_sel:
                        st.error("Preencha todos os campos obrigatórios.")
                    else:
                        spinner_supernova("Registrando baixa de avaria...")
                        try:
                            qtd_val_f = float(qtd_kg_cx_str.replace(".", "").replace(",", ".")) if qtd_kg_cx_str else 0.0
                            val_avaria_f = float(valor_total_avaria_str.replace(".", "").replace(",", ".")) if valor_total_avaria_str else 0.0
                        except ValueError:
                            qtd_val_f, val_avaria_f = 0.0, 0.0

                        nota_selecionada_dict = next((item for item in notas_com_saldo_loja02 if item["nf_entrada"] == nf_b_entrada_sel), None)
                        if not nota_selecionada_dict:
                            st.error("Nota de entrada inválida.")
                        elif val_avaria_f > nota_selecionada_dict["saldo_restante"]:
                            st.error("❌ O valor da avaria ultrapassa o saldo restante da nota da Loja 02!")
                        else:
                            path_nf_baixa = ""
                            b64_nf_baixa = ""
                            if nf_baixa_file:
                                path_nf_baixa = os.path.join("uploads", f"NF_BAIXA_{ref_bon_transf}_{nf_baixa_file.name}")
                                bytes_baixa = nf_baixa_file.getbuffer()
                                with open(path_nf_baixa, "wb") as f_out: f_out.write(bytes_baixa)
                                b64_nf_baixa = base64.b64encode(bytes_baixa).decode('utf-8')

                            saldo_disponivel_da_nota_referenciada = nota_selecionada_dict["saldo_restante"]
                            novo_saldo_restante_nota = saldo_disponivel_da_nota_referenciada - val_avaria_f
                            try:
                                conn_ins, db_tins = get_db_connection()
                                cursor_ins = conn_ins.cursor()
                                cursor_ins.execute(
                                    """
                                    INSERT INTO baixas_avarias (
                                        loja_baixa, data_baixa, ref_bon_transferen, nf_baixa,
                                        nf_b_entrada, produto_hortifruti, quantidade_kg_cx,
                                        valor_total_avaria, saldo_restante_nota, saldo_total_disponivel,
                                        nf_baixa_b64
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """ if db_tins == "postgres" else """
                                    INSERT INTO baixas_avarias (
                                        loja_baixa, data_baixa, ref_bon_transferen, nf_baixa,
                                        nf_b_entrada, produto_hortifruti, quantidade_kg_cx,
                                        valor_total_avaria, saldo_restante_nota, saldo_total_disponivel,
                                        nf_baixa_b64
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        lojas_baixa_sel, data_hora_baixa_str, ref_bon_transf.strip(),
                                        path_nf_baixa, nf_b_entrada_sel, prod_hort_sel, qtd_val_f, val_avaria_f,
                                        novo_saldo_restante_nota, saldo_disponivel_da_nota_referenciada, b64_nf_baixa
                                    )
                                )
                                if "02" not in lojas_baixa_sel and "NOVA CIDADE" not in lojas_baixa_sel:
                                    cursor_ins.execute(
                                        "UPDATE bonificacoes SET status = 'Totalmente Utilizada' WHERE numero_nota = %s" if db_tins == "postgres" else "UPDATE bonificacoes SET status = 'Totalmente Utilizada' WHERE numero_nota = ?",
                                        (nf_b_entrada_sel,)
                                    )
                                else:
                                    st_auto_l2 = "Totalmente Utilizada" if novo_saldo_restante_nota <= 0 else "Parcialmente Utilizada"
                                    cursor_ins.execute(
                                        "UPDATE bonificacoes SET status = %s WHERE numero_nota = %s" if db_tins == "postgres" else "UPDATE bonificacoes SET status = ? WHERE numero_nota = ?",
                                        (st_auto_l2, nf_b_entrada_sel)
                                    )
                                conn_ins.commit()
                                conn_ins.close()
                                st.session_state["baixa_form_suffix"] += 1
                                st.success("Baixa registrada com sucesso!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")

        st.markdown("---")
        st.subheader("📊 Planilha de Registro de Baixas das Avarias")
        lista_lojas_filtro_bx = ["TODAS", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
        idx_filtro_bx = 0
        if not is_admin and loja_atual_usuario in lista_lojas_filtro_bx:
            idx_filtro_bx = lista_lojas_filtro_bx.index(loja_atual_usuario)

        with st.expander("🔍 Filtros da Planilha de Baixas", expanded=True):
            fb1, fb2, fb3 = st.columns(3)
            with fb1: f_loja_bx = st.selectbox("Filtrar por Loja", options=lista_lojas_filtro_bx, index=idx_filtro_bx, placeholder="Selecione...")
            with fb2: f_ref_bx = st.text_input("Filtrar por Ref. Bon.", value="", placeholder="Referência...")
            with fb3: f_prod_bx = st.text_input("Filtrar por Produto", value="", placeholder="Produto...")

        conn_bx_view, db_tbx_v = get_db_connection()
        df_bx_table = pd.read_sql_query("SELECT * FROM baixas_avarias ORDER BY id DESC", conn_bx_view)
        conn_bx_view.close()

        if not df_bx_table.empty:
            if f_loja_bx != "TODAS": df_bx_table = df_bx_table[df_bx_table["loja_baixa"] == f_loja_bx]
            if f_ref_bx.strip(): df_bx_table = df_bx_table[df_bx_table["ref_bon_transferen"].str.contains(f_ref_bx.strip(), case=False, na=False)]
            if f_prod_bx.strip(): df_bx_table = df_bx_table[df_bx_table["produto_hortifruti"].str.contains(f_prod_bx.strip(), case=False, na=False)]

            if not df_bx_table.empty:
                df_display_plan = df_bx_table.copy()
                total_utilizado_por_nf = total_baixado_por_nota
                saldo_calculado_list = []
                utilizado_calculado_list = []
                for _, row_bx in df_display_plan.iterrows():
                    nf_ent_item = str(row_bx["nf_b_entrada"])
                    v_utilizado = total_utilizado_por_nf.get(nf_ent_item, float(row_bx["valor_total_avaria"]))
                    utilizado_calculado_list.append(v_utilizado)
                    v_original = dict_valor_orig_por_nf.get(nf_ent_item, 0.0)
                    if v_original > 0:
                        v_saldo_restante = max(0.0, v_original - v_utilizado)
                    else:
                        v_saldo_restante = float(row_bx["saldo_restante_nota"])
                    saldo_calculado_list.append(v_saldo_restante)

                df_display_plan["saldo_restante_calculado"] = saldo_calculado_list
                df_display_plan["saldo_total_utilizado"] = utilizado_calculado_list

                pdf_bytes_bx = gerar_pdf_baixas(df_display_plan)
                st.download_button(
                    label="📥 Descarregar Planilha de Baixas de Avarias em PDF",
                    data=pdf_bytes_bx,
                    file_name=f"Registro_Baixas_Avarias_HortiControl_{datetime.now(ZoneInfo('America/Manaus')).strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    key="btn_download_pdf_planilha_baixas"
                )
                st.markdown("")

                for _, r_bx in df_bx_table.iterrows():
                    if r_bx.get("nf_baixa_b64") and r_bx.get("nf_baixa"):
                        salvar_arquivo_fisico_do_b64(r_bx["nf_baixa"], r_bx["nf_baixa_b64"])

                df_display_plan["Qtd (kg/cx)"] = df_display_plan["quantidade_kg_cx"].apply(lambda x: fmt_ptbr(x, 3))
                df_display_plan["Valor Total Avaria (R$)"] = df_display_plan["valor_total_avaria"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_display_plan["Saldo"] = df_display_plan["saldo_restante_calculado"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_display_plan["Saldo Total Utilizado"] = df_display_plan["saldo_total_utilizado"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_display_plan["NF da baixa"] = df_display_plan.apply(lambda r: "Ver Anexo" if (r.get("nf_baixa") and os.path.exists(str(r["nf_baixa"]))) or r.get("nf_baixa_b64") else "S/Anexo", axis=1)

                df_display_plan = df_display_plan.rename(columns={
                    "loja_baixa": "LOJAS",
                    "data_baixa": "Data Baixa",
                    "ref_bon_transferen": "Ref. Bon. transferen",
                    "nf_b_entrada": "NF da b. ENTRADA",
                    "produto_hortifruti": "Produto Hortifrúti"
                })
                df_final_show = df_display_plan[["LOJAS", "Data Baixa", "Ref. Bon. transferen", "NF da baixa", "NF da b. ENTRADA", "Produto Hortifrúti", "Qtd (kg/cx)", "Valor Total Avaria (R$)", "Saldo", "Saldo Total Utilizado"]]
                df_final_show.index = range(1, len(df_final_show) + 1)
                st.dataframe(df_final_show, use_container_width=True, height=400)

                st.markdown("---")
                st.subheader("⚙️ Gerenciamento: Editar ou Excluir Registro de Baixa")
                opcoes_baixas_editar = [(row["id"], f"Loja: {row['loja_baixa']} | Ref: {row['ref_bon_transferen']} | NF Ent: {row['nf_b_entrada']} (R$ {fmt_ptbr(row['valor_total_avaria'], 2)})") for _, row in df_bx_table.iterrows()]
                if opcoes_baixas_editar:
                    baixa_selecionada_ed = st.selectbox("Selecione a Baixa para Editar ou Excluir", options=opcoes_baixas_editar, format_func=lambda x: x[1], key="sel_baixa_gerenciar_edicao")
                    if baixa_selecionada_ed:
                        id_bx_atual = baixa_selecionada_ed[0]
                        reg_bx_atual = df_bx_table[df_bx_table["id"] == id_bx_atual].iloc[0]

                        with st.form("form_edicao_baixa_avaria"):
                            st.markdown(f"**Editando Baixa (Ref: {reg_bx_atual['ref_bon_transferen']} - NF Entrada Atual: {reg_bx_atual['nf_b_entrada']})**")
                            col_eb1, col_eb2, col_eb3 = st.columns(3)
                            with col_eb1:
                                lista_lojas_eb = ["LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                                idx_l_eb = lista_lojas_eb.index(reg_bx_atual["loja_baixa"]) if reg_bx_atual["loja_baixa"] in lista_lojas_eb else 0
                                nova_loja_bx = st.selectbox("Loja da Baixa", lista_lojas_eb, index=idx_l_eb)
                                notas_disponiveis_edicao = [item["nf_entrada"] for item in notas_com_saldo_loja02]
                                if reg_bx_atual["nf_b_entrada"] not in notas_disponiveis_edicao:
                                    notas_disponiveis_edicao.insert(0, reg_bx_atual["nf_b_entrada"])
                                idx_nf_atual = notas_disponiveis_edicao.index(reg_bx_atual["nf_b_entrada"]) if reg_bx_atual["nf_b_entrada"] in notas_disponiveis_edicao else 0
                                nova_nf_b_entrada = st.selectbox("NF de B. ENTRADA", options=notas_disponiveis_edicao, index=idx_nf_atual)
                            with col_eb2:
                                novo_ref_bx = st.text_input("Ref. Bon. transferen", value=reg_bx_atual["ref_bon_transferen"])
                                novo_prod_bx = st.text_input("Produto Hortifrúti", value=reg_bx_atual["produto_hortifruti"])
                            with col_eb3:
                                novo_qtd_bx_str = st.text_input("Qtd (kg/cx)", value=str(reg_bx_atual["quantidade_kg_cx"]).replace(".", ","))
                                novo_val_bx_str = st.text_input("Valor Total Avaria (R$)", value=str(reg_bx_atual["valor_total_avaria"]).replace(".", ","))

                            novo_anexo_bx_up = st.file_uploader("Substituir NF da Baixa (Opcional)", type=["pdf", "png", "jpg", "jpeg"])
                            col_bnt_bx1, col_bnt_bx2 = st.columns(2)
                            with col_bnt_bx1: salvar_alt_bx = st.form_submit_button("💾 Salvar Alterações da Baixa", type="primary")
                            with col_bnt_bx2: excluir_bx_btn = st.form_submit_button("🗑️ Excluir Registo de Baixa", type="secondary")

                            if salvar_alt_bx:
                                spinner_supernova("Atualizando baixa...")
                                try:
                                    q_f_ed = float(novo_qtd_bx_str.replace(".", "").replace(",", ".")) if novo_qtd_bx_str else reg_bx_atual["quantidade_kg_cx"]
                                    v_f_ed = float(novo_val_bx_str.replace(".", "").replace(",", ".")) if novo_val_bx_str else reg_bx_atual["valor_total_avaria"]
                                    path_nf_bx_ed = reg_bx_atual.get("nf_baixa", "")
                                    b64_nf_bx_ed = reg_bx_atual.get("nf_baixa_b64", "")
                                    if novo_anexo_bx_up:
                                        path_nf_bx_ed = os.path.join("uploads", f"NF_BAIXA_EDIT_{novo_ref_bx}_{novo_anexo_bx_up.name}")
                                        bytes_bx_up = novo_anexo_bx_up.getbuffer()
                                        with open(path_nf_bx_ed, "wb") as f_out: f_out.write(bytes_bx_up)
                                        b64_nf_bx_ed = base64.b64encode(bytes_bx_up).decode('utf-8')

                                    nota_edit_dict = next((item for item in notas_com_saldo_loja02 if item["nf_entrada"] == nova_nf_b_entrada), None)
                                    saldo_disp_edit = nota_edit_dict["saldo_restante"] if nota_edit_dict else reg_bx_atual["saldo_total_disponivel"]
                                    novo_saldo_restante_ed = saldo_disp_edit - v_f_ed

                                    conn_up_bx, db_t_upbx = get_db_connection()
                                    cur_upbx = conn_up_bx.cursor()
                                    cur_upbx.execute(
                                        "UPDATE baixas_avarias SET loja_baixa = %s, ref_bon_transferen = %s, nf_b_entrada = %s, produto_hortifruti = %s, quantidade_kg_cx = %s, valor_total_avaria = %s, saldo_restante_nota = %s, saldo_total_disponivel = %s, nf_baixa = %s, nf_baixa_b64 = %s WHERE id = %s" if db_t_upbx == "postgres" else "UPDATE baixas_avarias SET loja_baixa = ?, ref_bon_transferen = ?, nf_b_entrada = ?, produto_hortifruti = ?, quantidade_kg_cx = ?, valor_total_avaria = ?, saldo_restante_nota = ?, saldo_total_disponivel = ?, nf_baixa = ?, nf_baixa_b64 = ? WHERE id = ?",
                                        (nova_loja_bx, novo_ref_bx.strip(), nova_nf_b_entrada, novo_prod_bx, q_f_ed, v_f_ed, novo_saldo_restante_ed, saldo_disp_edit, path_nf_bx_ed, b64_nf_bx_ed, int(id_bx_atual) if db_t_upbx == "postgres" else id_bx_atual)
                                    )
                                    conn_up_bx.commit()
                                    conn_up_bx.close()
                                    st.success("Baixa atualizada com sucesso!")
                                    st.rerun()
                                except Exception as e: st.error(f"Erro ao atualizar baixa: {e}")

                            if excluir_bx_btn:
                                spinner_supernova("Excluindo baixa...")
                                try:
                                    conn_del_bx, db_td_bx = get_db_connection()
                                    cur_delbx = conn_del_bx.cursor()
                                    cur_delbx.execute(
                                        "DELETE FROM baixas_avarias WHERE id = %s" if db_td_bx == "postgres" else "DELETE FROM baixas_avarias WHERE id = ?",
                                        (int(id_bx_atual) if db_td_bx == "postgres" else id_bx_atual,)
                                    )
                                    conn_del_bx.commit()
                                    conn_del_bx.close()
                                    st.success("Baixa excluída com sucesso!")
                                    st.rerun()
                                except Exception as e: st.error(f"Erro ao excluir baixa: {e}")

                st.markdown("---")
                st.subheader("🖼️ Visualizar Anexo de Baixa")
                opcoes_baixas_ver = [(row["id"], f"Loja: {row['loja_baixa']} | Ref: {row['ref_bon_transferen']} | NF Entrada: {row['nf_b_entrada']}") for _, row in df_bx_table.iterrows() if row.get("nf_baixa") or row.get("nf_baixa_b64")]
                if opcoes_baixas_ver:
                    escolha_bx_ver = st.selectbox("Selecione a baixa para abrir o comprovativo/anexo", options=opcoes_baixas_ver, format_func=lambda x: x[1], placeholder="Selecione...")
                    if escolha_bx_ver:
                        reg_bx_escolhido = df_bx_table[df_bx_table["id"] == escolha_bx_ver[0]].iloc[0]
                        if st.button("🖼️ Abrir Anexo da Baixa Selecionada", type="primary"):
                            exibir_foto_modal(reg_bx_escolhido.get("nf_baixa", ""), reg_bx_escolhido.get("nf_baixa_b64", ""))
                else:
                    st.info("Nenhuma baixa com anexo disponível.")
        else:
            st.info("Nenhum registo de baixa encontrado.")

    elif menu == "Relatórios & Gráficos" and is_admin:
        st.title("📊 Relatórios & Business Intelligence (BI) Executive")
        tab_bi_receb, tab_bi_bonf_avaria = st.tabs([
            "📦 BI de Recebimento de Cargas",
            "🏷️ BI Bonificações, Transferências & Prevenção de Perdas"
        ])
        conn, db_type = get_db_connection()
        df_roms = pd.read_sql_query("SELECT * FROM romaneios", conn)
        df_itens = pd.read_sql_query("SELECT * FROM romaneio_itens", conn)
        df_bonf_rel = pd.read_sql_query("SELECT * FROM bonificacoes", conn)
        df_baixas_rel = pd.read_sql_query("SELECT * FROM baixas_avarias", conn)
        conn.close()

        with tab_bi_receb:
            if df_roms.empty or df_itens.empty:
                st.warning("Ainda não existem dados de recebimento cadastrados.")
            else:
                df_roms['data_dt'] = pd.to_datetime(df_roms['data_recebimento'], format='%d/%m/%Y', errors='coerce')
                df_full = df_itens.merge(df_roms, left_on='romaneio_id', right_on='id', suffixes=('_item', '_romaneio'))

                st.markdown("### 🔍 Filtros da Análise Gerencial")
                col_f0, col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1, 1, 1, 1])
                with col_f0:
                    lista_tipos_op_bi = ["TODOS OS TIPOS", "Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"]
                    tipo_op_bi_sel = st.selectbox("Tipo de Operação", options=lista_tipos_op_bi, index=0, key="rel_filter_tipo_op")
                with col_f1: loja_sel = st.selectbox("Filtrar por Loja", ["TODAS AS LOJAS"] + list(df_roms["loja"].unique()), placeholder="Selecione...", key="rel_filter_loja")
                with col_f2: prod_sel = st.selectbox("Filtrar por Produto", ["TODOS OS PRODUTOS"] + sorted(list(df_itens["produto"].unique())), placeholder="Selecione...", key="rel_filter_prod")
                with col_f3:
                    dt_min = df_roms['data_dt'].min() if not df_roms['data_dt'].isna().all() else datetime.now(ZoneInfo("America/Manaus"))
                    dt_inicio = st.date_input("Data Início", value=dt_min, format="DD/MM/YYYY", key="rel_filter_dt_ini")
                with col_f4:
                    dt_max = df_roms['data_dt'].max() if not df_roms['data_dt'].isna().all() else datetime.now(ZoneInfo("America/Manaus"))
                    dt_fim = st.date_input("Data Fim", value=dt_max, format="DD/MM/YYYY", key="rel_filter_dt_fim")

                df_filtrado = df_full.copy()
                if tipo_op_bi_sel != "TODOS OS TIPOS":
                    df_filtrado = df_filtrado[df_filtrado["tipo_operacao"].str.contains(tipo_op_bi_sel, case=False, na=False)]
                if loja_sel != "TODAS AS LOJAS":
                    df_filtrado = df_filtrado[df_filtrado["loja"].str.contains(loja_sel, case=False, na=False) | df_filtrado.get("loja_destino", pd.Series(dtype=str)).str.contains(loja_sel, case=False, na=False)]
                if prod_sel != "TODOS OS PRODUTOS":
                    df_filtrado = df_filtrado[df_filtrado["produto"] == prod_sel]
                if dt_inicio and dt_fim:
                    df_filtrado = df_filtrado[(df_filtrado["data_dt"] >= pd.to_datetime(dt_inicio)) & (df_filtrado["data_dt"] <= pd.to_datetime(dt_fim))]

                if df_filtrado.empty:
                    st.info("Nenhum registo encontrado para os filtros selecionados.")
                else:
                    st.markdown("---")
                    st.subheader("📊 Indicadores Principais & Análise por Operação (KPIs no Período)")
                    tot_recebido = df_filtrado['valor_total'].sum()
                    num_roms = df_filtrado['numero_romaneio'].nunique()
                    val_troca = df_filtrado[df_filtrado['tipo_operacao'].str.contains("Troca por Troca", case=False, na=False)]['valor_total'].sum()
                    val_transf = df_filtrado[df_filtrado['tipo_operacao'].str.contains("Transferência", case=False, na=False)]['valor_total'].sum()

                    df_bx_periodo = df_baixas_rel.copy()
                    if not df_bx_periodo.empty:
                        df_bx_periodo['data_dt'] = pd.to_datetime(df_bx_periodo['data_baixa'].str.split(' ').str[0], format='%d/%m/%Y', errors='coerce')
                        if loja_sel != "TODAS AS LOJAS":
                            df_bx_periodo = df_bx_periodo[df_bx_periodo['loja_baixa'].str.contains(loja_sel, case=False, na=False)]
                        if prod_sel != "TODOS OS PRODUTOS":
                            df_bx_periodo = df_bx_periodo[df_bx_periodo['produto_hortifruti'] == prod_sel]
                        if dt_inicio and dt_fim:
                            df_bx_periodo = df_bx_periodo[(df_bx_periodo['data_dt'] >= pd.to_datetime(dt_inicio)) & (df_bx_periodo['data_dt'] <= pd.to_datetime(dt_fim))]
                    val_perdas_evitadas = df_bx_periodo['valor_total_avaria'].sum() if not df_bx_periodo.empty else 0.0

                    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
                    kpi1.metric("Valor Total Recebido", f"R$ {fmt_ptbr(tot_recebido, 2)}")
                    kpi2.metric("Entradas no Período", f"{num_roms} romaneios")
                    kpi3.metric("Total Transferências", f"R$ {fmt_ptbr(val_transf, 2)}")
                    kpi4.metric("Total Troca por Troca", f"R$ {fmt_ptbr(val_troca, 2)}")
                    kpi5.metric("Perdas Evitadas", f"R$ {fmt_ptbr(val_perdas_evitadas, 2)}", delta="Economia", delta_color="normal")

                    st.markdown("---")
                    col_g1, col_g2 = st.columns(2)
                    with col_g1:
                        st.markdown("#### Top Produtos por Valor no Período (R$)")
                        top_prods_val = df_filtrado.groupby("produto")["valor_total"].sum().nlargest(10).reset_index()
                        fig_val = px.bar(top_prods_val, x="produto", y="valor_total", text_auto=".2f", color="valor_total", color_continuous_scale="Greens")
                        fig_val.update_layout(xaxis_title="Produto", yaxis_title="Total (R$)", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                        st.plotly_chart(fig_val, use_container_width=True)
                    with col_g2:
                        st.markdown("#### Top Produtos por Quantidade/Peso no Período")
                        top_prods_qtd = df_filtrado.groupby("produto")["quantidade"].sum().nlargest(10).reset_index()
                        fig_qtd = px.bar(top_prods_qtd, x="produto", y="quantidade", text_auto=".2f", color="quantidade", color_continuous_scale="Reds")
                        fig_qtd.update_layout(xaxis_title="Produto", yaxis_title="Qtd / Peso", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                        st.plotly_chart(fig_qtd, use_container_width=True)

                    st.markdown("---")
                    st.subheader("📈 Gráfico de Quantidades Movimentadas por Tipo de Operação no Período")
                    if not df_filtrado.empty:
                        df_qtd_op = df_filtrado.groupby(["produto", "tipo_operacao"])["quantidade"].sum().reset_index()
                        fig_qtd_op = px.bar(
                            df_qtd_op, x="produto", y="quantidade", color="tipo_operacao",
                            barmode="group", text_auto=".2f",
                            labels={"produto": "Produto", "quantidade": "Quantidade / Peso Total", "tipo_operacao": "Tipo de Operação"}
                        )
                        fig_qtd_op.update_layout(xaxis_title="Produto", yaxis_title="Quantidade Movimentada", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                        st.plotly_chart(fig_qtd_op, use_container_width=True)
                    else:
                        st.info("Sem dados de quantidade por operação para o período.")

                    st.markdown("---")
                    st.subheader("🛡️ Gráfico de Perdas Evitadas (Avarias Compensadas por Loja/Produto)")
                    if not df_bx_periodo.empty:
                        df_bx_grp_loja = df_bx_periodo.groupby("loja_baixa")["valor_total_avaria"].sum().reset_index()
                        fig_perdas = px.bar(
                            df_bx_grp_loja, x="loja_baixa", y="valor_total_avaria", text_auto=".2f",
                            color="valor_total_avaria", color_continuous_scale="Purples",
                            labels={"loja_baixa": "Loja", "valor_total_avaria": "Valor Evitado (R$)"}
                        )
                        fig_perdas.update_layout(xaxis_title="Loja", yaxis_title="Perdas Evitadas (R$)", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                        st.plotly_chart(fig_perdas, use_container_width=True)
                    else:
                        st.info("Nenhum registo de perdas evitadas/avarias encontrado para o período e filtros selecionados.")

                    st.markdown("---")
                    st.download_button(
                        label="📥 Descarregar Relatório Consolidado (Excel / CSV)",
                        data=df_filtrado.to_csv(index=False, sep=';').encode('utf-8-sig'),
                        file_name=f"Relatorio_Hortifruti_HortiControl_{datetime.now(ZoneInfo('America/Manaus')).strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        type="primary",
                        key="btn_download_csv_relatorio"
                    )

        with tab_bi_bonf_avaria:
            st.subheader("📈 Análise Executiva de Bonificações, Transferências & Mitigação de Perdas")
            st.markdown("Visão consolidada para a alta gerência sobre a **eficiência do processo de conferência, bonificação e aproveitamento de avarias** para a saúde financeira do supermercado.")
            with st.expander("🔍 Filtros Avançados para Apresentação à Liderança", expanded=True):
                col_bi_f1, col_bi_f2, col_bi_f3, col_bi_f4 = st.columns(4)
                todas_lojas_bi = sorted(list(set(df_bonf_rel['loja'].dropna().unique()).union(set(df_baixas_rel['loja_baixa'].dropna().unique()))))
                with col_bi_f1: bi_loja_sel = st.selectbox("Filtrar por Loja", ["TODAS AS LOJAS"] + todas_lojas_bi, key="bi_sel_loja")
                todos_prods_bi = sorted(list(set(df_bonf_rel['produto_hortifruti'].dropna().unique()).union(set(df_baixas_rel['produto_hortifruti'].dropna().unique()))))
                with col_bi_f2: bi_prod_sel = st.selectbox("Filtrar por Produto", ["TODOS OS PRODUTOS"] + todos_prods_bi, key="bi_sel_prod")
                with col_bi_f3: bi_tipo_sel = st.selectbox("Tipo de Operação Bonificada", ["TODOS", "Bonificação", "Transferência de Bonificação"], key="bi_sel_tipo")
                with col_bi_f4: bi_periodo = st.selectbox("Período de Análise", ["Todo o Histórico", "Últimos 30 dias", "Últimos 90 dias", "Ano Atual"], key="bi_sel_periodo")

            df_b_sub = df_bonf_rel.copy()
            df_bx_sub = df_baixas_rel.copy()

            if not df_b_sub.empty:
                df_b_sub['data_dt'] = pd.to_datetime(df_b_sub['data_entrada'].str.split(' ').str[0], format='%d/%m/%Y', errors='coerce')
                if bi_loja_sel != "TODAS AS LOJAS": df_b_sub = df_b_sub[df_b_sub['loja'] == bi_loja_sel]
                if bi_prod_sel != "TODOS OS PRODUTOS": df_b_sub = df_b_sub[df_b_sub['produto_hortifruti'] == bi_prod_sel]
                if bi_tipo_sel != "TODOS": df_b_sub = df_b_sub[df_b_sub.get('tipo_bonificacao', 'Bonificação') == bi_tipo_sel]
                if bi_periodo == "Últimos 30 dias": df_b_sub = df_b_sub[df_b_sub['data_dt'] >= (datetime.now() - timedelta(days=30))]
                elif bi_periodo == "Últimos 90 dias": df_b_sub = df_b_sub[df_b_sub['data_dt'] >= (datetime.now() - timedelta(days=90))]
                elif bi_periodo == "Ano Atual": df_b_sub = df_b_sub[df_b_sub['data_dt'].dt.year == datetime.now().year]

            if not df_bx_sub.empty:
                df_bx_sub['data_dt'] = pd.to_datetime(df_bx_sub['data_baixa'].str.split(' ').str[0], format='%d/%m/%Y', errors='coerce')
                if bi_loja_sel != "TODAS AS LOJAS": df_bx_sub = df_bx_sub[df_bx_sub['loja_baixa'] == bi_loja_sel]
                if bi_prod_sel != "TODOS OS PRODUTOS": df_bx_sub = df_bx_sub[df_bx_sub['produto_hortifruti'] == bi_prod_sel]
                if bi_periodo == "Últimos 30 dias": df_bx_sub = df_bx_sub[df_bx_sub['data_dt'] >= (datetime.now() - timedelta(days=30))]
                elif bi_periodo == "Últimos 90 dias": df_bx_sub = df_bx_sub[df_bx_sub['data_dt'] >= (datetime.now() - timedelta(days=90))]
                elif bi_periodo == "Ano Atual": df_bx_sub = df_bx_sub[df_bx_sub['data_dt'].dt.year == datetime.now().year]

            v_tot_bonf = df_b_sub[df_b_sub.get('tipo_bonificacao', 'Bonificação') == 'Bonificação']['valor_bonificacao'].sum() if not df_b_sub.empty else 0.0
            v_tot_transf = df_b_sub[df_b_sub.get('tipo_bonificacao', 'Bonificação') == 'Transferência de Bonificação']['valor_bonificacao'].sum() if not df_b_sub.empty else 0.0
            v_tot_entradas = df_b_sub['valor_bonificacao'].sum() if not df_b_sub.empty else 0.0
            v_tot_avarias_salvas = df_bx_sub['valor_total_avaria'].sum() if not df_bx_sub.empty else 0.0
            taxa_cobertura = (v_tot_avarias_salvas / v_tot_entradas * 100) if v_tot_entradas > 0 else 0.0
            v_saldo_remanescente = max(0.0, v_tot_entradas - v_tot_avarias_salvas)

            st.markdown("---")
            st.markdown("### 🏆 Painel de Impacto Executivo")
            kpi_e1, kpi_e2, kpi_e3, kpi_e4, kpi_e5 = st.columns(5)
            kpi_e1.metric("1. Entradas Bonificadas", f"R$ {fmt_ptbr(v_tot_bonf, 2)}", help="Valor total obtido diretamente com fornecedores")
            kpi_e2.metric("2. Transferências", f"R$ {fmt_ptbr(v_tot_transf, 2)}", help="Valor total redistribuído entre lojas da rede")
            kpi_e3.metric("3. Perdas Evitadas (Avarias)", f"R$ {fmt_ptbr(v_tot_avarias_salvas, 2)}", delta=f"{fmt_ptbr(v_tot_avarias_salvas, 2)} Salvos", delta_color="normal", help="Valor de perdas físicas amortizadas por saldo de bonificação")
            kpi_e4.metric("4. Taxa de Cobertura", f"{fmt_ptbr(taxa_cobertura, 2)}%", help="Porcentagem de bonificações convertida em amortização de perdas")
            kpi_e5.metric("5. Saldo Remanescente", f"R$ {fmt_ptbr(v_saldo_remanescente, 2)}", help="Saldo de bonificação ainda disponível para compensação")

            st.markdown(f"""
            <div style="background: rgba(46, 125, 50, 0.25); border: 1px solid #4CAF50; border-radius: 8px; padding: 12px 18px; margin: 15px 0;">
                <span style="color: #81C784; font-weight: bold; font-size: 15px;">🛡️ Mensagem para Liderança:</span>
                <span style="color: #FFFFFF; font-size: 14px;"> O processo de acompanhamento de bonificações já garantiu uma <b>recuperação direta de R$ <span style="color: #FFF; font-weight: bold;">{fmt_ptbr(v_tot_avarias_salvas, 2)}</span> em avarias que seriam registradas como prejuízo líquido direto para a empresa.</b></span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 📊 Gráficos Analíticos de Desempenho & Quantidades Evitadas")
            bg_bi1, bg_bi2 = st.columns(2)
            with bg_bi1:
                st.markdown("#### Entradas por Tipo e Loja (R$)")
                if not df_b_sub.empty:
                    fig_lojas = px.bar(
                        df_b_sub, x="loja", y="valor_bonificacao", color="tipo_bonificacao",
                        barmode="group", text_auto=".2f",
                        color_discrete_map={"Bonificação": "#4CAF50", "Transferência de Bonificação": "#2196F3"}
                    )
                    fig_lojas.update_layout(xaxis_title="Loja", yaxis_title="Valor (R$)", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                    st.plotly_chart(fig_lojas, use_container_width=True)
                else: st.info("Sem dados para a combinação de filtros.")

            with bg_bi2:
                st.markdown("#### Avarias Bonificadas por Loja (Economia Gerada)")
                if not df_bx_sub.empty:
                    df_bx_grp = df_bx_sub.groupby("loja_baixa")["valor_total_avaria"].sum().reset_index()
                    fig_avarias = px.bar(df_bx_grp, x="loja_baixa", y="valor_total_avaria", text_auto=".2f", color="valor_total_avaria", color_continuous_scale="Purples")
                    fig_avarias.update_layout(xaxis_title="Loja da Baixa", yaxis_title="Avaria Coberta (R$)", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                    st.plotly_chart(fig_avarias, use_container_width=True)
                else: st.info("Sem dados de baixas para os filtros.")

            st.markdown("#### 📦 Quantidade (Kg / Unidades / Caixas) de Produtos com Perdas Evitadas por Baixas")
            if not df_bx_sub.empty:
                df_bx_qtd_prod = df_bx_sub.groupby("produto_hortifruti")["quantidade_kg_cx"].sum().reset_index()
                fig_qtd_avarias = px.bar(
                    df_bx_qtd_prod, x="produto_hortifruti", y="quantidade_kg_cx", text_auto=".3f",
                    color="quantidade_kg_cx", color_continuous_scale="Greens",
                    labels={"produto_hortifruti": "Produto", "quantidade_kg_cx": "Quantidade Total (Kg/Unid/Cx)"}
                )
                fig_qtd_avarias.update_layout(xaxis_title="Produto", yaxis_title="Volume Salvo (Qtd/Peso)", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                st.plotly_chart(fig_qtd_avarias, use_container_width=True)
            else: st.info("Sem dados de quantidades de avarias para o período.")

            bg_bi3, bg_bi4 = st.columns(2)
            with bg_bi3:
                st.markdown("#### Top Produtos Beneficiados por Bonificação")
                if not df_b_sub.empty:
                    df_p_bonf = df_b_sub.groupby("produto_hortifruti")["valor_bonificacao"].sum().nlargest(7).reset_index()
                    fig_prod_b = px.bar(df_p_bonf, y="produto_hortifruti", x="valor_bonificacao", orientation="h", text_auto=".2f", color="valor_bonificacao", color_continuous_scale="Teal")
                    fig_prod_b.update_layout(xaxis_title="Total (R$)", yaxis_title="Produto", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                    st.plotly_chart(fig_prod_b, use_container_width=True)
                else: st.info("Sem dados de produtos.")

            with bg_bi4:
                st.markdown("#### Distribuição do Status de Notas de Bonificação")
                if not df_b_sub.empty:
                    fig_st_pie = px.pie(df_b_sub, names="status", values="valor_bonificacao", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig_st_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                    st.plotly_chart(fig_st_pie, use_container_width=True)
                else: st.info("Sem status para exibir.")

            st.markdown("---")
            st.markdown("### 📄 Geração de Relatório Executivo em PDF")
            metrics_dict = {
                "tot_bonf": v_tot_bonf,
                "tot_transf": v_tot_transf,
                "tot_avaria": v_tot_avarias_salvas,
                "taxa_cobertura": taxa_cobertura,
                "saldo_restante": v_saldo_remanescente
            }
            pdf_bi_bytes = gerar_pdf_relatorio_gerencial_bi(metrics_dict, df_b_sub, df_bx_sub)
            col_pdf_bi1, col_pdf_bi2 = st.columns([3, 1])
            with col_pdf_bi1:
                st.markdown("Gere um relatório em PDF para apresentações de resultados em reuniões com a diretoria.")
            with col_pdf_bi2:
                st.download_button(
                    label="📥 Baixar PDF Executivo",
                    data=pdf_bi_bytes,
                    file_name=f"Relatorio_Executivo_Lideranca_HortiControl_{datetime.now(ZoneInfo('America/Manaus')).strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    key="btn_download_executivo_bi"
                )

    elif menu == "Gerenciar Cadastros (Produtos)" and is_admin:
        st.title("⚙️ Gerenciamento e Cadastro (Produtos & Fornecedores)")
        tab_prod, tab_forn = st.tabs(["📦 Cadastro de Produtos", "🏢 Cadastro de Fornecedores"])
        with tab_prod:
            with st.expander("➕ Cadastrar Novo Produto", expanded=False):
                with st.form("cad_prod_form", clear_on_submit=True):
                    col_cp1, col_cp2, col_cp3, col_cp4 = st.columns([2, 2, 3, 1.5])
                    with col_cp1: cod_prod_input = st.text_input("Código do Produto", value="", placeholder="Cód...")
                    with col_cp2: cod_bar_input = st.text_input("Código de Barras", value="", placeholder="Código de barras...")
                    with col_cp3: nome_p = st.text_input("Nome do Produto *", value="", placeholder="Nome do produto...")
                    with col_cp4: und_p = st.selectbox("Unidade", ["KG", "UNID", "GRM", "CX"], index=0)
                    if st.form_submit_button("➕ Cadastrar Produto", type="primary"):
                        if not nome_p.strip(): st.error("O Nome é obrigatório.")
                        else:
                            spinner_supernova("Cadastrando produto...")
                            conn, db_type = get_db_connection()
                            cursor = conn.cursor()
                            try:
                                cursor.execute("INSERT INTO produtos (codigo_barras, codigo_produto, nome, unidade_padrao) VALUES (%s, %s, %s, %s)" if db_type == "postgres" else "INSERT INTO produtos (codigo_barras, codigo_produto, nome, unidade_padrao) VALUES (?, ?, ?, ?)", (cod_bar_input.strip() if cod_bar_input else None, cod_prod_input.strip() if cod_prod_input else None, nome_p.strip().upper(), und_p))
                                conn.commit()
                                st.success("Cadastrado com sucesso!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                            finally: conn.close()
            st.markdown("---")
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos ORDER BY nome")
            produtos_cadastrados = cursor.fetchall()
            conn.close()

            if produtos_cadastrados:
                produtos_com_id_ajustado = [(i, p[1], p[2], p[3], p[4], p[0]) for i, p in enumerate(produtos_cadastrados, 1)]
                df_produtos = pd.DataFrame(produtos_com_id_ajustado, columns=["ID", "Código de Barras", "Código do Produto", "Nome do Produto", "Unidade Padrão", "ID_Real"])
                st.download_button(
                    label="📥 Descarregar Relatório de Produtos em PDF",
                    data=gerar_pdf_produtos(produtos_cadastrados),
                    file_name=f"Relatorio_Produtos_HortiControl_{datetime.now(ZoneInfo('America/Manaus')).strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
                st.markdown("")
                st.dataframe(df_produtos[["ID", "Código do Produto", "Código de Barras", "Nome do Produto", "Unidade Padrão"]], use_container_width=True, hide_index=True, height=250)

                st.markdown("### ✏️ Editar ou Excluir Produto")
                opcoes_edit_prod = [(p[5], f"{p[3]} (Cód: {p[2] or 'S/Cód'})") for p in produtos_com_id_ajustado]
                prod_sel_ed = st.selectbox("Selecione o produto para editar ou excluir", options=opcoes_edit_prod, format_func=lambda x: x[1], key="sel_prod_editar")
                if prod_sel_ed:
                    id_p_ed = prod_sel_ed[0]
                    conn_p_det, db_tp_det = get_db_connection()
                    cur_pd = conn_p_det.cursor()
                    cur_pd.execute("SELECT codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos WHERE id = %s" if db_tp_det == "postgres" else "SELECT codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos WHERE id = ?", (int(id_p_ed) if db_tp_det == "postgres" else id_p_ed,))
                    dados_p_atual = cur_pd.fetchone()
                    conn_p_det.close()
                    if dados_p_atual:
                        with st.form("form_edit_produto"):
                            ep_cod_bar = st.text_input("Código de Barras", value=dados_p_atual[0] or "")
                            ep_cod_prod = st.text_input("Código do Produto", value=dados_p_atual[1] or "")
                            ep_nome = st.text_input("Nome do Produto", value=dados_p_atual[2] or "")
                            lista_unds = ["KG", "UNID", "GRM", "CX"]
                            idx_u = lista_unds.index(dados_p_atual[3]) if dados_p_atual[3] in lista_unds else 0
                            ep_und = st.selectbox("Unidade", lista_unds, index=idx_u)
                            col_bp1, col_bp2 = st.columns(2)
                            with col_bp1: btn_salvar_prod = st.form_submit_button("💾 Salvar Alterações", type="primary")
                            with col_bp2: btn_excluir_prod = st.form_submit_button("🗑️ Excluir Produto", type="secondary")

                            if btn_salvar_prod:
                                spinner_supernova("Atualizando produto...")
                                try:
                                    conn_up_p, db_tup = get_db_connection()
                                    cur_upp = conn_up_p.cursor()
                                    cur_upp.execute(
                                        "UPDATE produtos SET codigo_barras = %s, codigo_produto = %s, nome = %s, unidade_padrao = %s WHERE id = %s" if db_tup == "postgres" else "UPDATE produtos SET codigo_barras = ?, codigo_produto = ?, nome = ?, unidade_padrao = ? WHERE id = ?",
                                        (ep_cod_bar.strip(), ep_cod_prod.strip(), ep_nome.strip().upper(), ep_und, int(id_p_ed) if db_tup == "postgres" else id_p_ed)
                                    )
                                    conn_up_p.commit()
                                    conn_up_p.close()
                                    st.success("Produto atualizado com sucesso!")
                                    st.rerun()
                                except Exception as e: st.error(f"Erro ao atualizar: {e}")

                            if btn_excluir_prod:
                                spinner_supernova("Excluindo produto...")
                                try:
                                    conn_del_p, db_tdp = get_db_connection()
                                    cur_delp = conn_del_p.cursor()
                                    cur_delp.execute("DELETE FROM produtos WHERE id = %s" if db_tdp == "postgres" else "DELETE FROM produtos WHERE id = ?", (int(id_p_ed) if db_tdp == "postgres" else id_p_ed,))
                                    conn_del_p.commit()
                                    conn_del_p.close()
                                    st.success("Produto excluído com sucesso!")
                                    st.rerun()
                                except Exception as e: st.error(f"Erro ao excluir: {e}")
            else: st.info("Nenhum produto cadastrado.")

        with tab_forn:
            with st.expander("➕ Cadastrar Novo Fornecedor", expanded=False):
                with st.form("cad_forn_form", clear_on_submit=True):
                    col_fc1, col_fc2, col_fc3 = st.columns([2, 2, 3])
                    with col_fc1: f_cod_input = st.text_input("Código", value="", placeholder="Código...")
                    with col_fc2: f_cnpj_input = st.text_input("CNPJ", value="", placeholder="00.000.000/0000-00")
                    with col_fc3: f_nome_input = st.text_input("Nome / Razão Social *", value="", placeholder="Razão social...")
                    if st.form_submit_button("➕ Cadastrar Fornecedor", type="primary"):
                        if not f_nome_input.strip(): st.error("O Nome é obrigatório.")
                        else:
                            spinner_supernova("Cadastrando fornecedor...")
                            conn, db_type = get_db_connection()
                            cursor = conn.cursor()
                            try:
                                cursor.execute("INSERT INTO fornecedores (codigo_fornecedor, cnpj, nome) VALUES (%s, %s, %s)" if db_type == "postgres" else "INSERT INTO fornecedores (codigo_fornecedor, cnpj, nome) VALUES (?, ?, ?)", (f_cod_input.strip() if f_cod_input else None, f_cnpj_input.strip() if f_cnpj_input else None, f_nome_input.strip().upper()))
                                conn.commit()
                                st.success("Cadastrado com sucesso!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                            finally: conn.close()
            st.markdown("---")
            conn, db_type = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, codigo_fornecedor, cnpj, nome FROM fornecedores ORDER BY nome")
            fornecedores_cadastrados = cursor.fetchall()
            conn.close()

            if fornecedores_cadastrados:
                forn_com_id_ajustado = [(i, f[1], f[2], f[3], f[0]) for i, f in enumerate(fornecedores_cadastrados, 1)]
                df_forn_show = pd.DataFrame(forn_com_id_ajustado, columns=["ID", "Código", "CNPJ", "Nome do Fornecedor", "ID_Real"])
                st.dataframe(df_forn_show[["ID", "Código", "CNPJ", "Nome do Fornecedor"]], use_container_width=True, hide_index=True, height=250)

                st.markdown("### ✏️ Editar ou Excluir Fornecedor")
                opcoes_edit_forn = [(f[4], f"{f[3]} (Cód: {f[1] or 'S/Cód'})") for f in forn_com_id_ajustado]
                forn_sel_ed = st.selectbox("Selecione o fornecedor para editar ou excluir", options=opcoes_edit_forn, format_func=lambda x: x[1], key="sel_forn_editar")
                if forn_sel_ed:
                    id_f_ed = forn_sel_ed[0]
                    conn_f_det, db_tf_det = get_db_connection()
                    cur_fd = conn_f_det.cursor()
                    cur_fd.execute("SELECT codigo_fornecedor, cnpj, nome FROM fornecedores WHERE id = %s" if db_tf_det == "postgres" else "SELECT codigo_fornecedor, cnpj, nome FROM fornecedores WHERE id = ?", (int(id_f_ed) if db_tf_det == "postgres" else id_f_ed,))
                    dados_f_atual = cur_fd.fetchone()
                    conn_f_det.close()
                    if dados_f_atual:
                        with st.form("form_edit_fornecedor"):
                            ef_cod = st.text_input("Código do Fornecedor", value=dados_f_atual[0] or "")
                            ef_cnpj = st.text_input("CNPJ", value=dados_f_atual[1] or "")
                            ef_nome = st.text_input("Nome / Razão Social", value=dados_f_atual[2] or "")
                            col_bf1, col_bf2 = st.columns(2)
                            with col_bf1: btn_salvar_forn = st.form_submit_button("💾 Salvar Alterações", type="primary")
                            with col_bf2: btn_excluir_forn = st.form_submit_button("🗑️ Excluir Fornecedor", type="secondary")

                            if btn_salvar_forn:
                                spinner_supernova("Atualizando fornecedor...")
                                try:
                                    conn_up_f, db_tupf = get_db_connection()
                                    cur_upf = conn_up_f.cursor()
                                    cur_upf.execute(
                                        "UPDATE fornecedores SET codigo_fornecedor = %s, cnpj = %s, nome = %s WHERE id = %s" if db_tupf == "postgres" else "UPDATE fornecedores SET codigo_fornecedor = ?, cnpj = ?, nome = ? WHERE id = ?",
                                        (ef_cod.strip(), ef_cnpj.strip(), ef_nome.strip().upper(), int(id_f_ed) if db_tupf == "postgres" else id_f_ed)
                                    )
                                    conn_up_f.commit()
                                    conn_up_f.close()
                                    st.success("Fornecedor atualizado com sucesso!")
                                    st.rerun()
                                except Exception as e: st.error(f"Erro ao atualizar: {e}")

                            if btn_excluir_forn:
                                spinner_supernova("Excluindo fornecedor...")
                                try:
                                    conn_del_f, db_tdf = get_db_connection()
                                    cur_delf = conn_del_f.cursor()
                                    cur_delf.execute("DELETE FROM fornecedores WHERE id = %s" if db_tdf == "postgres" else "DELETE FROM fornecedores WHERE id = ?", (int(id_f_ed) if db_tdf == "postgres" else id_f_ed,))
                                    conn_del_f.commit()
                                    conn_del_f.close()
                                    st.success("Fornecedor excluído com sucesso!")
                                    st.rerun()
                                except Exception as e: st.error(f"Erro ao excluir: {e}")
            else: st.info("Nenhum fornecedor cadastrado.")

    elif menu == "Gerenciar Usuários & Permissões" and is_admin:
        st.title("👥 Gerenciamento de Usuários e Permissões")
        with st.expander("➕ Cadastrar Novo Usuário", expanded=False):
            with st.form("cad_usuario_form", clear_on_submit=True):
                col_u1, col_u2, col_u3, col_u4 = st.columns([2.5, 2, 2, 1.5])
                with col_u1: novo_nome = st.text_input("Nome Completo", value="", placeholder="Nome...")
                with col_u2: novo_login = st.text_input("Login", value="", placeholder="Login...")
                with col_u3: nova_senha = st.text_input("Senha", type="password", value="", placeholder="Senha...")
                with col_u4: novo_perfil = st.selectbox("Perfil", ["Conferente", "Gestor"], index=0, placeholder="Selecione...")
                if st.form_submit_button("➕ Cadastrar", type="primary"):
                    if not novo_nome.strip() or not novo_login.strip() or not nova_senha.strip():
                        st.error("Preencha todos os campos.")
                    else:
                        spinner_supernova("Cadastrando usuário...")
                        conn, db_type = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("INSERT INTO usuarios (nome, login, senha, perfil) VALUES (%s, %s, %s, %s)" if db_type == "postgres" else "INSERT INTO usuarios (nome, login, senha, perfil) VALUES (?, ?, ?, ?)", (novo_nome.strip(), novo_login.strip(), nova_senha.strip(), novo_perfil))
                            conn.commit()
                            st.success("Cadastrado com sucesso!")
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")
                        finally: conn.close()
        st.markdown("---")
        conn, db_type = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, login, senha, perfil FROM usuarios ORDER BY id")
        usuarios_cadastrados = cursor.fetchall()
        conn.close()

        if usuarios_cadastrados:
            usuarios_com_id_ajustado = [(i, u[1], u[2], u[3], u[4], u[0]) for i, u in enumerate(usuarios_cadastrados, 1)]
            df_usuarios = pd.DataFrame(usuarios_com_id_ajustado, columns=["ID", "Nome Completo", "Login", "Senha", "Perfil", "ID_Real"])
            st.dataframe(df_usuarios[["ID", "Nome Completo", "Login", "Senha", "Perfil"]], use_container_width=True, hide_index=True, height=250)

            st.markdown("### ✏️ Editar ou Excluir Utilizador")
            opcoes_edit_usr = [(u[5], f"{u[1]} (Login: {u[2]})") for u in usuarios_com_id_ajustado]
            usr_sel_ed = st.selectbox("Selecione o utilizador para editar ou excluir", options=opcoes_edit_usr, format_func=lambda x: x[1], key="sel_usr_editar")
            if usr_sel_ed:
                id_u_ed = usr_sel_ed[0]
                conn_u_det, db_tu_det = get_db_connection()
                cur_ud = conn_u_det.cursor()
                cur_ud.execute("SELECT nome, login, senha, perfil FROM usuarios WHERE id = %s" if db_tu_det == "postgres" else "SELECT nome, login, senha, perfil FROM usuarios WHERE id = ?", (int(id_u_ed) if db_tu_det == "postgres" else id_u_ed,))
                dados_u_atual = cur_ud.fetchone()
                conn_u_det.close()
                if dados_u_atual:
                    with st.form("form_edit_usuario"):
                        eu_nome = st.text_input("Nome Completo", value=dados_u_atual[0] or "")
                        eu_login = st.text_input("Login", value=dados_u_atual[1] or "")
                        eu_senha = st.text_input("Senha", type="password", value=dados_u_atual[2] or "")
                        perfis_lst = ["Conferente", "Gestor"]
                        idx_per = perfis_lst.index(dados_u_atual[3]) if dados_u_atual[3] in perfis_lst else 0
                        eu_perfil = st.selectbox("Perfil", perfis_lst, index=idx_per)
                        col_bu1, col_bu2 = st.columns(2)
                        with col_bu1: btn_salvar_usr = st.form_submit_button("💾 Salvar Alterações", type="primary")
                        with col_bu2: btn_excluir_usr = st.form_submit_button("🗑️ Excluir Utilizador", type="secondary")

                        if btn_salvar_usr:
                            spinner_supernova("Atualizando utilizador...")
                            try:
                                conn_up_u, db_tupu = get_db_connection()
                                cur_upu = conn_up_u.cursor()
                                cur_upu.execute(
                                    "UPDATE usuarios SET nome = %s, login = %s, senha = %s, perfil = %s WHERE id = %s" if db_tupu == "postgres" else "UPDATE usuarios SET nome = ?, login = ?, senha = ?, perfil = ? WHERE id = ?",
                                    (eu_nome.strip(), eu_login.strip(), eu_senha.strip(), eu_perfil, int(id_u_ed) if db_tupu == "postgres" else id_u_ed)
                                )
                                conn_up_u.commit()
                                conn_up_u.close()
                                st.success("Utilizador atualizado com sucesso!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao atualizar: {e}")

                        if btn_excluir_usr:
                            spinner_supernova("Excluindo utilizador...")
                            try:
                                conn_del_u, db_tdu = get_db_connection()
                                cur_delu = conn_del_u.cursor()
                                cur_delu.execute("DELETE FROM usuarios WHERE id = %s" if db_tdu == "postgres" else "DELETE FROM usuarios WHERE id = ?", (int(id_u_ed) if db_tdu == "postgres" else id_u_ed,))
                                conn_del_u.commit()
                                conn_del_u.close()
                                st.success("Utilizador excluído com sucesso!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro ao excluir: {e}")
        else: st.info("Nenhum usuário cadastrado.")
