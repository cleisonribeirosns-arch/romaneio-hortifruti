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

# Tenta importar fitz (PyMuPDF)
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Tenta importar psycopg2
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
    page_icon=logo_icon if logo_icon else "🥦",
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

@st.dialog("📄 Visualizador de Documentos", width="large")
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
# ESTILOS VISUAIS
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
# INICIALIZAÇÃO DE BANCO
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
                senha TEXT UNIQUE NOT NULL,
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

    def add_watermark(canvas_obj, doc_obj):
        if logo_path and os.path.exists(logo_path):
            canvas_obj.saveState()
            try:
                canvas_obj.setFillAlpha(0.12)
                canvas_obj.drawImage(logo_path, letter[0] / 2 - 140, letter[1] / 2 + 30, width=280, height=280, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
            canvas_obj.restoreState()

    logo_img_header = RLImage(logo_path, width=70, height=50) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
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
        [Paragraph(f"<b>Loja / Pasta:</b> {loja_txt_pdf}", styles["Normal"]), Paragraph(f"<b>Conferente:</b> {romaneio_data.get('conferente','')}", styles["Normal"])],
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
    doc.build(story, onFirstPage=add_watermark, onLaterPages=add_watermark)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# TELA DE LOGIN
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

        with st.form("form_login"):
            login_input = st.text_input("Usuário / Login ou Nome Completo", value="", placeholder="Digite seu usuário ou nome...")
            senha_input = st.text_input("Senha", type="password", value="", placeholder="Digite sua senha...")
            
            # SELEÇÃO INICIAL DA LOJA EM QUE O CONFERENTE IRÁ ATUAR NESTA SESSÃO
            loja_login_sel = st.selectbox(
                "Selecione a Loja em que vai operar hoje", 
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
    loja_atual_usuario = user_info.get("loja_atual", "LOJA 02 NOVA CIDADE")
    
    st.markdown("---")
    col_info_usr, col_logout = st.columns([3.5, 1.5], vertical_alignment="center")
    with col_info_usr:
        tipo_perfil_txt = "🔒 Gestor / Administrador" if is_admin else f"👤 Conferente Em Operação"
        st.markdown(f"**Usuário:** {user_info['nome']} &nbsp;|&nbsp; **Perfil:** {tipo_perfil_txt} &nbsp;|&nbsp; 📁 **Pasta de Trabalho:** <span style='color: #4CAF50; font-weight: bold;'>{loja_atual_usuario}</span>", unsafe_allow_html=True)
    with col_logout:
        if st.button("🚪 Sair / Trocar de Loja", type="secondary", key="btn_sair_sistema_principal"):
            st.session_state["usuario_logado"] = None
            st.rerun()
            
    opcoes_menu_map = {
        "📋 Romaneio de Recebimento": "Romaneio de Recebimento - Hortifrúti",
        "🔍 Consultar Romaneios": "Consultar Romaneios",
        "🎁 Controle de Bonificação": "Controle de Bonificação",
        "📉 Baixa de Avarias": "Controle de Baixa de Avarias"
    }
    if is_admin:
        opcoes_menu_map.update({
            "📊 Relatórios & BI": "Relatórios & Gráficos",
            "📦🚚 Cadastros": "Gerenciar Cadastros (Produtos)",
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
    
    # ---------------------------------------------------------
    # ROMANEIO DE RECEBIMENTO
    # ---------------------------------------------------------
    if menu == "Romaneio de Recebimento - Hortifrúti":
        st.title("📋 Novo Romaneio de Recebimento")
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
        forn_por_nome = {f[0]: (str(f[1]).strip() if f[1] else "") for f in fornecedores_lista}
        forn_nomes_keys = list(forn_por_nome.keys())

        if f"val_cod_forn_{k_suffix}" not in st.session_state: st.session_state[f"val_cod_forn_{k_suffix}"] = ""
        if f"val_sel_forn_{k_suffix}" not in st.session_state: st.session_state[f"val_sel_forn_{k_suffix}"] = ""

        def atualizar_por_select():
            s_selecionado = st.session_state.get(f"sel_forn_{k_suffix}", "")
            st.session_state[f"val_sel_forn_{k_suffix}"] = s_selecionado
            novo_cod = forn_por_nome.get(s_selecionado, "")
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
                    loja = st.selectbox("Loja / Pasta de Destino da Carga", lista_lojas_opc, index=idx_loja_login, placeholder="Selecione a loja...", key=f"loja_{k_suffix}")

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
            canvas_conf = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#FFFFFF", height=120, width=280, drawing_mode="freedraw", return_image_data=True, key=f"canv_conf_{k_suffix}")
        with col_ass2:
            st.write("**Assinatura do Entregador / Fornecedor**")
            canvas_ent = st_canvas(stroke_width=3, stroke_color="#000000", background_color="#FFFFFF", height=120, width=280, drawing_mode="freedraw", return_image_data=True, key=f"canv_ent_{k_suffix}")
            
        if st.button("✅ Salvar Romaneio na Pasta da Loja", type="primary", key=f"btn_salvar_{k_suffix}"):
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
                spinner_supernova("Salvando romaneio na pasta correspondente...")
                try:
                    path_ass_conf, b64_conf = "", ""
                    if canvas_conf.image_data is not None:
                        img_c = Image.fromarray(canvas_conf.image_data.astype("uint8"))
                        path_ass_conf = os.path.join("uploads", f"ass_conf_{num_rom_final}.png")
                        img_c.save(path_ass_conf)
                        with open(path_ass_conf, "rb") as f_ac: b64_conf = base64.b64encode(f_ac.read()).decode('utf-8')
                    
                    path_ass_ent, b64_ent = "", ""
                    if canvas_ent.image_data is not None:
                        img_e = Image.fromarray(canvas_ent.image_data.astype("uint8"))
                        path_ass_ent = os.path.join("uploads", f"ass_ent_{num_rom_final}.png")
                        img_e.save(path_ass_ent)
                        with open(path_ass_ent, "rb") as f_ae: b64_ent = base64.b64encode(f_ae.read()).decode('utf-8')
                    
                    caminho_foto_salva, b64_foto = "", ""
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
                            INSERT INTO romaneios (numero_romaneio, loja, loja_origem, loja_destino, data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista, data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador, status_nota, tipo_operacao, observacoes, foto_b64, ass_conf_b64, ass_ent_b64) 
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                        """, (num_rom_final, loja, loja_origem, loja_destino, data_rec_str, forn_final, cod_forn_val, tel_fornecedor, user_info["nome"], pag_a_vista, data_pag_str, caminho_foto_salva, path_ass_conf, path_ass_ent, 'Pendente', tipo_operacao, observacoes_romaneio, b64_foto, b64_conf, b64_ent))
                        romaneio_id = cursor.fetchone()[0]
                    else:
                        cursor.execute("""
                            INSERT INTO romaneios (numero_romaneio, loja, loja_origem, loja_destino, data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista, data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador, status_nota, tipo_operacao, observacoes, foto_b64, ass_conf_b64, ass_ent_b64) 
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
                    
                    romaneio_dict_atual = {"numero_romaneio": num_rom_final, "data_recebimento": data_rec_str, "fornecedor": forn_final, "codigo_fornecedor": cod_forn_val, "telefone_fornecedor": tel_fornecedor, "loja": loja, "loja_origem": loja_origem, "loja_destino": loja_destino, "conferente": user_info["nome"], "pagamento_a_vista": pag_a_vista, "data_pagamento": data_pag_str, "tipo_operacao": tipo_operacao, "observacoes": observacoes_romaneio}
                    pdf_buffer_novo = gerar_pdf_romaneio(romaneio_dict_atual, itens_salvos_pdf, path_ass_conf, path_ass_ent)
                    st.session_state["ultimo_pdf_bytes"] = pdf_buffer_novo.getvalue()
                    st.session_state["ultimo_num_romaneio"] = num_rom_final
                    st.session_state["itens_romaneio"] = []
                    st.session_state["form_key_suffix"] += 1
                    st.session_state["item_key_suffix"] = 0
                    st.success(f"Romaneio {num_rom_final} salvo com sucesso na pasta da {loja}!")
                    st.rerun()
                except Exception as e: st.error(f"Erro ao salvar romaneio: {e}")
                    
        if "ultimo_pdf_bytes" in st.session_state and "ultimo_num_romaneio" in st.session_state:
            st.markdown("---")
            st.success(f"📄 Romaneio **{st.session_state['ultimo_num_romaneio']}** pronto para download!")
            st.download_button(label=f"📥 Descarregar PDF - {st.session_state['ultimo_num_romaneio']}", data=st.session_state["ultimo_pdf_bytes"], file_name=f"{st.session_state['ultimo_num_romaneio']}.pdf", mime="application/pdf", type="primary")

    # ---------------------------------------------------------
    # CONSULTA DE ROMANEIOS POR PASTA DA LOJA
    # ---------------------------------------------------------
    elif menu == "Consultar Romaneios":
        st.title("🔍 Consulta e Pastas por Loja")
        
        lista_lojas_filtro = ["TODAS AS LOJAS", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
        
        # Padrão: já seleciona a pasta da loja que o usuário está atuando
        idx_loja_padrao_filtro = 0
        if loja_atual_usuario in lista_lojas_filtro:
            idx_loja_padrao_filtro = lista_lojas_filtro.index(loja_atual_usuario)

        lista_tipos_op_filtro = ["TODOS OS TIPOS", "Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"]

        with st.expander("📁 Selecionar Pasta de Loja & Filtros", expanded=True):
            col_f0, col_f_op, col_f1, col_f2, col_f3, col_f4 = st.columns([1.3, 1.2, 1, 1, 1, 1])
            with col_f0: filtro_loja_sel = st.selectbox("Pasta / Loja", options=lista_lojas_filtro, index=idx_loja_padrao_filtro, help="Exibe apenas os romaneios da pasta selecionada")
            with col_f_op: filtro_tipo_op_sel = st.selectbox("Tipo de Operação", options=lista_tipos_op_filtro, index=0)
            with col_f1: filtro_num = st.text_input("Número do Romaneio", value="", placeholder="Ex: ROM-...")
            with col_f2: filtro_forn = st.text_input("Fornecedor / Entregador", value="", placeholder="Nome do fornecedor...")
            with col_f3: filtro_cod_forn = st.text_input("Código do Fornecedor", value="", placeholder="Código...")
            with col_f4:
                filtro_data_val = st.date_input("Data do Recebimento", value=None, format="DD/MM/YYYY")
                filtro_data_str = filtro_data_val.strftime("%d/%m/%Y") if filtro_data_val else ""
                
        conn, db_type = get_db_connection()
        df_rom = pd.read_sql_query("SELECT * FROM romaneios ORDER BY id DESC", conn)
        conn.close()
        
        if not df_rom.empty:
            if filtro_loja_sel != "TODAS AS LOJAS":
                df_rom = df_rom[df_rom["loja"].str.contains(filtro_loja_sel, case=False, na=False) | df_rom.get("loja_destino", pd.Series(dtype=str)).str.contains(filtro_loja_sel, case=False, na=False)]
            if filtro_tipo_op_sel != "TODOS OS TIPOS":
                df_rom = df_rom[df_rom["tipo_operacao"].str.contains(filtro_tipo_op_sel, case=False, na=False)]
            if filtro_num.strip(): df_rom = df_rom[df_rom["numero_romaneio"].str.contains(filtro_num.strip(), case=False, na=False)]
            if filtro_forn.strip(): df_rom = df_rom[df_rom["fornecedor"].str.contains(filtro_forn.strip(), case=False, na=False)]
            if filtro_cod_forn.strip(): df_rom = df_rom[df_rom["codigo_fornecedor"].astype(str).str.contains(filtro_cod_forn.strip(), case=False, na=False)]
            if filtro_data_str: df_rom = df_rom[df_rom["data_recebimento"] == filtro_data_str]
                
        if not df_rom.empty:
            st.markdown(f"📁 **Romaneios na pasta '{filtro_loja_sel}':** {len(df_rom)} registro(s)")
            st.markdown("---")
            
            df_rom_resumo = df_rom[["numero_romaneio", "tipo_operacao", "loja", "data_recebimento", "fornecedor", "conferente", "status_nota"]].rename(columns={
                "numero_romaneio": "N° Romaneio",
                "tipo_operacao": "Tipo",
                "loja": "Loja",
                "data_recebimento": "Data",
                "fornecedor": "Fornecedor",
                "conferente": "Conferente",
                "status_nota": "Status"
            })
            st.dataframe(df_rom_resumo, use_container_width=True, hide_index=True, height=250)
            st.markdown("---")

            for idx, row in df_rom.iterrows():
                fornecedor_txt = row['fornecedor'] if row['fornecedor'] else 'N/A'
                if row['codigo_fornecedor'] and str(row['codigo_fornecedor']).strip(): fornecedor_txt += f" (Cód: {row['codigo_fornecedor']})"
                
                status_atual_nota = row.get("status_nota", "Pendente")
                if status_atual_nota == "Nota Emitida":
                    icone_status = "🟢 Nota Emitida"
                elif status_atual_nota == "Trocado":
                    icone_status = "🟠 Trocado"
                elif status_atual_nota == "Lançado":
                    icone_status = "🔵 Lançado"
                else:
                    icone_status = "🔴 Pendente"

                tipo_op_reg = row.get("tipo_operacao", "Compra")
                
                with st.expander(f"Romaneio: {row['numero_romaneio']} | [{tipo_op_reg.upper()}] | {icone_status} | Fornecedor: {fornecedor_txt} | Data: {row['data_recebimento']}"):
                    col_st1, col_st2 = st.columns([2, 3])
                    with col_st1:
                        opcoes_status_rom = ["Pendente", "Nota Emitida", "Trocado", "Lançado"]
                        idx_status_padrao = opcoes_status_rom.index(status_atual_nota) if status_atual_nota in opcoes_status_rom else 0
                        novo_status_nota = st.selectbox("Status do Romaneio", opcoes_status_rom, index=idx_status_padrao, key=f"status_nota_{row['id']}")
                    with col_st2:
                        st.write("")
                        st.write("")
                        if st.button("💾 Salvar Status", key=f"btn_salvar_status_{row['id']}"):
                            spinner_supernova("Atualizando status...")
                            try:
                                conn_st, db_t_st = get_db_connection()
                                cur_st = conn_st.cursor()
                                cur_st.execute(
                                    "UPDATE romaneios SET status_nota = %s WHERE id = %s" if db_t_st == "postgres" else "UPDATE romaneios SET status_nota = ? WHERE id = ?",
                                    (novo_status_nota, int(row["id"]) if db_t_st == "postgres" else row["id"])
                                )
                                conn_st.commit()
                                conn_st.close()
                                st.success("Status atualizado!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                    
                    st.markdown("---")
                    loja_exibicao = row['loja']
                    if tipo_op_reg.lower() in ['transferência', 'transferência/bonificação'] and row.get('loja_origem'):
                        loja_exibicao = f"Origem: {row['loja_origem']} -> Destino: {row['loja_destino']}"
                    
                    st.write(f"**Tipo:** {tipo_op_reg} | **Loja:** {loja_exibicao}")
                    st.write(f"**Conferente:** {row['conferente']} | **Pagamento à Vista:** {row['pagamento_a_vista']}")
                    if row.get('observacoes'): st.write(f"**Observações:** {row['observacoes']}")
                    
                    if row.get('caminho_foto') or row.get('foto_b64'):
                        st.write("")
                        if st.button("📄 Visualizar Nota / Anexo", key=f"btn_ampliar_foto_{row['id']}", type="primary"): 
                            exibir_foto_modal(row['caminho_foto'], row.get('foto_b64'))
                            
                    conn_i, db_t_i = get_db_connection()
                    df_itens = pd.read_sql_query("SELECT produto, quantidade, unidade, valor_unitario, valor_total FROM romaneio_itens WHERE romaneio_id = %s" if db_t_i == "postgres" else "SELECT produto, quantidade, unidade, valor_unitario, valor_total FROM romaneio_itens WHERE romaneio_id = ?", conn_i, params=(int(row["id"]) if db_t_i == "postgres" else row["id"],))
                    conn_i.close()
                    
                    df_itens_ex = df_itens.copy()
                    df_itens_ex['Qtd / Peso'] = df_itens_ex['quantidade'].apply(lambda x: fmt_ptbr(x, 3))
                    df_itens_ex['Vl. Unit'] = df_itens_ex['valor_unitario'].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                    df_itens_ex['Total'] = df_itens_ex['valor_total'].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                    st.dataframe(df_itens_ex[['produto', 'Qtd / Peso', 'unidade', 'Vl. Unit', 'Total']], use_container_width=True, height=200)
                    
                    st.markdown(f"**Total do Romaneio: R$ {fmt_ptbr(df_itens['valor_total'].sum(), 2)}**")
                    pdf_buffer = gerar_pdf_romaneio(row.to_dict(), [(None, r['produto'], r['quantidade'], r['unidade'], r['valor_unitario'], r['valor_total']) for _, r in df_itens.iterrows()], row.get("assinatura_conferente"), row.get("assinatura_entregador"))
                    
                    col_dl, col_del = st.columns([4, 1])
                    with col_dl: st.download_button(label=f"📥 Descarregar PDF - {row['numero_romaneio']}", data=pdf_buffer, file_name=f"{row['numero_romaneio']}.pdf", mime="application/pdf", key=f"pdf_btn_cons_{row['id']}")
                    with col_del:
                        if st.button("🗑️ Excluir", key=f"btn_excluir_rom_{row['id']}", type="secondary"):
                            spinner_supernova("Excluindo romaneio...")
                            try:
                                conn_del, db_t_del = get_db_connection()
                                cursor_del = conn_del.cursor()
                                cursor_del.execute("DELETE FROM romaneio_itens WHERE romaneio_id = %s" if db_t_del == "postgres" else "DELETE FROM romaneio_itens WHERE romaneio_id = ?", (int(row["id"]) if db_t_del == "postgres" else row["id"],))
                                cursor_del.execute("DELETE FROM romaneios WHERE id = %s" if db_t_del == "postgres" else "DELETE FROM romaneios WHERE id = ?", (int(row["id"]) if db_t_del == "postgres" else row["id"],))
                                conn_del.commit()
                                conn_del.close()
                                st.success("Romaneio excluído com sucesso!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
        else: st.info(f"Nenhum romaneio encontrado na pasta '{filtro_loja_sel}'.")
