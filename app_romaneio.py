import base64
from datetime import datetime, time, timedelta
import io
import os
import pandas as pd
from PIL import Image
import plotly.express as px
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

# Tenta importar fitz (PyMuPDF) para renderizar PDFs como imagens sem bloqueio do navegador
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

# ---------------------------------------------------------
# FUNÇÃO DE PERSISTÊNCIA DE ANEXOS (BASE64 NO BANCO)
# ---------------------------------------------------------
def salvar_arquivo_fisico_do_b64(caminho_alvo, b64_str):
    if not caminho_alvo or not b64_str:
        return
    try:
        if not os.path.exists(caminho_alvo):
            diretorio = os.path.dirname(caminho_alvo)
            if diretorio and not os.path.exists(diretorio):
                os.makedirs(diretorio)
            with open(caminho_alvo, "wb") as f_out:
                f_out.write(base64.b64decode(b64_str))
    except Exception:
        pass

# ---------------------------------------------------------
# MODAL DE VISUALIZAÇÃO DE ANEXOS (ESTILO GOOGLE DRIVE SEGURO)
# ---------------------------------------------------------
@st.dialog("📄 Visualizador de Documentos", width="large")
def exibir_foto_modal(caminho_foto, b64_dados=None):
    if b64_dados:
        salvar_arquivo_fisico_do_b64(caminho_foto, b64_dados)
        
    if os.path.exists(caminho_foto):
        nome_arquivo = os.path.basename(caminho_foto)
        is_pdf = caminho_foto.lower().endswith(".pdf")
        
        ext_tag = "PDF" if is_pdf else "IMG"
        bg_tag_color = "#EA4335" if is_pdf else "#4285F4"
        
        # Barra superior estilo Google Drive (Dark Header)
        st.markdown(f"""
        <div style="background-color: #202124; padding: 12px 18px; border-radius: 8px 8px 0 0; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #3c4043; margin-bottom: 15px;">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="background-color: {bg_tag_color}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 11px;">{ext_tag}</span>
                <span style="color: #ffffff; font-weight: 600; font-size: 15px;">{nome_arquivo}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if is_pdf:
            if HAS_PYMUPDF:
                try:
                    doc_pdf = fitz.open(caminho_foto)
                    total_paginas = len(doc_pdf)
                    
                    st.markdown(f"<p style='text-align: center; color: #9aa0a6; font-size: 13px; margin-bottom: 12px;'>Exibindo documento • {total_paginas} página(s)</p>", unsafe_allow_html=True)
                    
                    for page_index in range(total_paginas):
                        page = doc_pdf[page_index]
                        pix = page.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("png")
                        
                        st.markdown(f"""
                        <div style="background-color: #2d2e30; padding: 10px; border-radius: 6px; margin-bottom: 10px; text-align: center; border: 1px solid #3c4043;">
                            <p style="color: #bdc1c6; font-size: 12px; margin: 0; font-weight: bold;">Página {page_index + 1} de {total_paginas}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.image(img_bytes, use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao renderizar PDF como imagem: {e}")
            else:
                st.warning("A biblioteca PyMuPDF não está instalada no ambiente para renderizar o PDF visualmente.")
            
            st.markdown("---")
            with open(caminho_foto, "rb") as f_pdf:
                st.download_button(
                    label=f"📥 Baixar Ficheiro PDF ({nome_arquivo})",
                    data=f_pdf.read(),
                    file_name=nome_arquivo,
                    mime="application/pdf",
                    type="primary"
                )
        else:
            st.markdown(f"""
            <div style="background-color: #2d2e30; padding: 10px; border-radius: 6px; margin-bottom: 10px; text-align: center; border: 1px solid #3c4043;">
                <p style="color: #bdc1c6; font-size: 12px; margin: 0; font-weight: bold;">Visualização de Imagem / Comprovante</p>
            </div>
            """, unsafe_allow_html=True)
            st.image(caminho_foto, use_container_width=True, caption="Documento / Nota Fiscal Anexada")
            with open(caminho_foto, "rb") as f_img:
                img_bytes = f_img.read()
            st.download_button(
                label=f"📥 Baixar Imagem ({nome_arquivo})",
                data=img_bytes,
                file_name=nome_arquivo,
                mime="application/jpeg",
                type="primary"
            )
    else:
        st.error("Ficheiro de anexo não encontrado no servidor.")

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
                nome VARCHAR(255) UNIQUE NOT NULL,
                contato VARCHAR(255)
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
                nome TEXT UNIQUE NOT NULL,
                contato TEXT
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

    def add_watermark(canvas_obj, doc_obj):
        if logo_path and os.path.exists(logo_path):
            canvas_obj.saveState()
            try:
                canvas_obj.setFillAlpha(0.12)
                canvas_obj.drawImage(logo_path, letter[0] / 2 - 140, letter[1] / 2 + 30, width=280, height=280, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
            canvas_obj.restoreState()

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
    doc.build(story, onFirstPage=add_watermark, onLaterPages=add_watermark)
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

    header_table = Table([[logo_img_header, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>HortiControl - Relatório de Produtos Cadastrados", styles["Normal"]), Paragraph(f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y')}<br/><b>Total:</b> {len(produtos_data)}", styles["Normal"])]], colWidths=[80, 310, 150])
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
    header_table = Table([[logo_img_header, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>HortiControl - Relatório de Controle de Bonificação", styles["Normal"]), Paragraph(f"<b>Data Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/><b>Total Registros:</b> {len(df_bonf_data)}", styles["Normal"])]], colWidths=[80, 310, 150])
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
    header_table = Table([[logo_img_header, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>HortiControl - Registro de Baixas de Avarias", styles["Normal"]), Paragraph(f"<b>Data Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/><b>Total Registros:</b> {len(df_baixas_data)}", styles["Normal"])]], colWidths=[80, 520, 192])
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
        Paragraph("Saldo Total disponível", style_header_left)
    ]]
    
    tot_val_avarias = 0.0
    for _, r in df_baixas_data.iterrows():
        v_av = float(r["valor_total_avaria"]) if r["valor_total_avaria"] else 0.0
        tot_val_avarias += v_av
        s_nota = float(r["saldo_restante_nota"]) if r["saldo_restante_nota"] else 0.0
        s_disp = float(r["saldo_total_disponivel"]) if r["saldo_total_disponivel"] else 0.0
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
            Paragraph(f"R$ {fmt_ptbr(s_disp, 2)}", style_left),
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
        tipo_perfil_txt = "🔒 Gestor / Administrador" if is_admin else f"👤 Conferente ({loja_atual_usuario})"
        st.markdown(f"**Usuário:** {user_info['nome']} &nbsp;|&nbsp; **Perfil:** {tipo_perfil_txt}")
    with col_logout:
        if st.button("🚪 Sair", type="secondary", key="btn_sair_sistema_principal"):
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
                    data_hoje_str = datetime.now().strftime("%Y%m%d%H%M%S")
                    st.session_state[f"num_rom_auto_{k_suffix}"] = f"ROM-{data_hoje_str}"
                
                num_romaneio = st.text_input("Número do Romaneio", value=st.session_state[f"num_rom_auto_{k_suffix}"], disabled=True, key=f"num_rom_{k_suffix}")
                tipo_operacao = st.selectbox("Tipo de Operação", ["", "Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"], index=0, key=f"tipo_op_{k_suffix}", placeholder="Selecione o tipo...", on_change=lambda: st.rerun())

            with col2:
                data_rec_val = st.date_input("Data do Recebimento", value=datetime.now(), format="DD/MM/YYYY", key=f"data_rec_{k_suffix}")
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
        fotos_upload = st.file_uploader("Foto da Mercadoria / Nota Fiscal", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key=f"fotos_{k_suffix}")
        
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
                try:
                    if not os.path.exists("uploads"): os.makedirs("uploads")
                    path_ass_conf = ""
                    b64_conf = ""
                    if canvas_conf.image_data is not None:
                        img_c = Image.fromarray(canvas_conf.image_data.astype("uint8"))
                        path_ass_conf = os.path.join("uploads", f"ass_conf_{num_rom_final}.png")
                        img_c.save(path_ass_conf)
                        with open(path_ass_conf, "rb") as f_ac:
                            b64_conf = base64.b64encode(f_ac.read()).decode('utf-8')
                    
                    path_ass_ent = ""
                    b64_ent = ""
                    if canvas_ent.image_data is not None:
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
                    st.success(f"Romaneio {num_rom_final} gerado e salvo com sucesso!")
                    st.rerun()
                except Exception as e: st.error(f"Erro ao salvar romaneio: {e}")
                    
        if "ultimo_pdf_bytes" in st.session_state and "ultimo_num_romaneio" in st.session_state:
            st.markdown("---")
            st.success(f"📄 Romaneio **{st.session_state['ultimo_num_romaneio']}** pronto para download!")
            st.download_button(label=f"📥 Baixar PDF - {st.session_state['ultimo_num_romaneio']}", data=st.session_state["ultimo_pdf_bytes"], file_name=f"{st.session_state['ultimo_num_romaneio']}.pdf", mime="application/pdf", type="primary")
            
    elif menu == "Consultar Romaneios":
        st.title("🔍 Consulta de Romaneios")
        
        lista_lojas_filtro = ["TODAS AS LOJAS", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
        idx_loja_padrao_filtro = 0
        if not is_admin and loja_atual_usuario in lista_lojas_filtro:
            idx_loja_padrao_filtro = lista_lojas_filtro.index(loja_atual_usuario)

        lista_tipos_op_filtro = ["TODOS OS TIPOS", "Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"]

        with st.expander("🔍 Filtrar Romaneios", expanded=True):
            col_f0, col_f_op, col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1.2, 1, 1, 1, 1])
            with col_f0: filtro_loja_sel = st.selectbox("Filtrar por Loja", options=lista_lojas_filtro, index=idx_loja_padrao_filtro, placeholder="Selecione...")
            with col_f_op: filtro_tipo_op_sel = st.selectbox("Tipo de Operação", options=lista_tipos_op_filtro, index=0, placeholder="Selecione...")
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
            st.markdown(f"**Total de romaneios encontrados:** {len(df_rom)}")
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
                    with col_dl: st.download_button(label=f"📥 Baixar PDF - {row['numero_romaneio']}", data=pdf_buffer, file_name=f"{row['numero_romaneio']}.pdf", mime="application/pdf", key=f"pdf_btn_cons_{row['id']}")
                    with col_del:
                        if st.button("🗑️ Excluir", key=f"btn_excluir_rom_{row['id']}", type="secondary"):
                            try:
                                conn_del, db_t_del = get_db_connection()
                                cursor_del = conn_del.cursor()
                                cursor_del.execute("DELETE FROM romaneio_itens WHERE romaneio_id = %s" if db_t_del == "postgres" else "DELETE FROM romaneio_itens WHERE romaneio_id = ?", (int(row["id"]) if db_t_del == "postgres" else row["id"],))
                                cursor_del.execute("DELETE FROM romaneios WHERE id = %s" if db_t_del == "postgres" else "DELETE FROM romaneios WHERE id = ?", (int(row["id"]) if db_t_del == "postgres" else row["id"],))
                                conn_del.commit()
                                conn_del.close()
                                st.success("Excluído com sucesso!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
        else: st.info("Nenhum romaneio encontrado.")

    # ---------------------------------------------------------
    # 6. CONTROLE DE BONIFICAÇÃO
    # ---------------------------------------------------------
    elif menu == "Controle de Bonificação":
        st.title("🎁 Controle de Bonificação Hortifrúti")
        
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
                with col_dt2: data_entrada_manual = st.date_input("Data de Entrada", value=datetime.now(), format="DD/MM/YYYY")
                with col_dt3:
                    hora_auto = datetime.now().strftime('%H:%M:%S')
                    st.text_input("Hora de Entrada", value=hora_auto, disabled=True)
                
                dt_entrada_str = f"{data_entrada_manual.strftime('%d/%m/%Y')} {hora_auto}" if data_entrada_manual else ""
                
                if st.form_submit_button("✅ Salvar Bonificação", type="primary"):
                    if not num_nota_bonf.strip() or not loja_bonf or not prod_bonf or not status_bonf:
                        st.error("Preencha todos os campos obrigatórios.")
                    else:
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
                label="📥 Baixar Relatório de Bonificação em PDF",
                data=pdf_bonf_bytes,
                file_name=f"Relatorio_Bonificacao_HortiControl_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                type="primary",
                key="btn_download_pdf_bonf"
            )
            st.markdown("")
            
            df_bonf_tabela = df_bonf.copy()
            df_bonf_tabela["Valor (R$)"] = df_bonf_tabela["valor_bonificacao"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
            df_bonf_tabela["Anexo"] = df_bonf_tabela.apply(lambda r: "📄 Disponível" if (r.get("caminho_anexo") and os.path.exists(r["caminho_anexo"])) or r.get("anexo_b64") else "Sem Anexo", axis=1)
            
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
            st.subheader("📄 Abertura de Anexo & Edição de Registro")
            
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
                    if st.button("📄 Abrir Anexo / Nota Fiscal", type="primary", key="btn_abrir_anexo_direto_tabela"):
                        exibir_foto_modal(caminho_nota_alvo, b64_anexo_reg)
                else:
                    st.warning("Este registro não possui arquivo de nota anexado.")

            with st.form("form_edicao_direta_bonificacao"):
                st.markdown(f"**Editando Nota N° {reg_obj_atual['numero_nota']} ({reg_obj_atual['loja']})**")
                col_e1, col_e2, col_e3 = st.columns(3)
                with col_e1:
                    novo_val_nota_str = st.text_input("Valor (R$)", value=str(reg_obj_atual["valor_bonificacao"]).replace(".", ","))
                with col_e2:
                    status_atuais_lst = ["Disponível", "Parcialmente Utilizada", "Totalmente Utilizada"]
                    idx_st_atual = status_atuais_lst.index(reg_obj_atual["status"]) if reg_obj_atual["status"] in status_atuais_lst else 0
                    novo_st_nota = st.selectbox("Status", status_atuais_lst, index=idx_st_atual)
                with col_e3:
                    novo_prod_nota = st.text_input("Produto Hortifrúti", value=reg_obj_atual["produto_hortifruti"])
                
                novo_anexo_up = st.file_uploader("Substituir / Enviar Novo Anexo (Opcional)", type=["pdf", "png", "jpg", "jpeg"])
                
                if st.form_submit_button("💾 Salvar Alterações do Registro", type="primary"):
                    try:
                        val_f_edit = float(novo_val_nota_str.replace(".", "").replace(",", ".")) if novo_val_nota_str else reg_obj_atual["valor_bonificacao"]
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
                            "UPDATE bonificacoes SET valor_bonificacao = %s, status = %s, produto_hortifruti = %s, caminho_anexo = %s, anexo_b64 = %s WHERE id = %s" if db_t_upd == "postgres" else "UPDATE bonificacoes SET valor_bonificacao = ?, status = ?, produto_hortifruti = ?, caminho_anexo = ?, anexo_b64 = ? WHERE id = ?",
                            (val_f_edit, novo_st_nota, novo_prod_nota, path_novo_arq, b64_novo_arq, int(id_reg_atual) if db_t_upd == "postgres" else id_reg_atual)
                        )
                        conn_up_dir.commit()
                        conn_up_dir.close()
                        st.success("Registro atualizado com sucesso!")
                        st.rerun()
                    except Exception as e: st.error(f"Erro ao atualizar: {e}")
        else: st.info("Nenhuma bonificação encontrada.")

    # ---------------------------------------------------------
    # 7. CONTROLE DE BAIXA DE AVARIAS
    # ---------------------------------------------------------
    elif menu == "Controle de Baixa de Avarias":
        st.title("📉 Registro de Baixas das Avarias")
        loja_ativa_sessao = user_info.get("loja_atual", "LOJA 02 NOVA CIDADE")
        
        conn_b_all, db_tb_all = get_db_connection()
        df_todas_bonf = pd.read_sql_query("SELECT * FROM bonificacoes", conn_b_all)
        conn_b_all.close()
        
        df_bonf_loja = df_todas_bonf[df_todas_bonf["loja"].str.contains(loja_ativa_sessao.replace("LOJA ", ""), case=False, na=False) & df_todas_bonf["status"].isin(["Disponível", "Parcialmente Utilizada"])] if not df_todas_bonf.empty else pd.DataFrame()
        
        conn_bx_chk, db_tbx_chk = get_db_connection()
        df_baixar_hist = pd.read_sql_query("SELECT * FROM baixas_avarias", conn_bx_chk)
        conn_bx_chk.close()
        
        total_baixado_por_nota = {}
        if not df_baixar_hist.empty:
            totais_por_nf = df_baixar_hist.groupby("nf_b_entrada")["valor_total_avaria"].sum()
            for nf_e, val_bx in totais_por_nf.items():
                total_baixado_por_nota[str(nf_e)] = float(val_bx)
                
        notas_com_saldo_loja = []
        saldo_total_disp_loja = 0.0
        
        if not df_bonf_loja.empty:
            for _, r_bonf in df_bonf_loja.iterrows():
                num_nf_ent = str(r_bonf["numero_nota"])
                val_original = float(r_bonf["valor_bonificacao"])
                ja_baixado = total_baixado_por_nota.get(num_nf_ent, 0.0)
                saldo_restante_nota = max(0.0, val_original - ja_baixado)
                
                if saldo_restante_nota > 0:
                    saldo_total_disp_loja += saldo_restante_nota
                    notas_com_saldo_loja.append({
                        "nf_entrada": num_nf_ent,
                        "produto": r_bonf["produto_hortifruti"],
                        "valor_original": val_original,
                        "saldo_restante": saldo_restante_nota
                    })

        st.info(f"💡 **Saldo Total Disponível para a {loja_ativa_sessao}: R$ {fmt_ptbr(saldo_total_disp_loja, 2)}**")
        
        if notas_com_saldo_loja:
            with st.expander(f"📌 Notas com Saldo Disponível ({loja_ativa_sessao})", expanded=True):
                df_ns_show = pd.DataFrame(notas_com_saldo_loja)
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
            with st.form("form_registro_baixa_modelo", clear_on_submit=True):
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    lista_lojas_reg = ["LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                    idx_l_ativa = lista_lojas_reg.index(loja_ativa_sessao) if loja_ativa_sessao in lista_lojas_reg else 0
                    lojas_baixa_sel = st.selectbox("LOJAS", options=lista_lojas_reg, index=idx_l_ativa, placeholder="Selecione...")
                    ref_bon_transf = st.text_input("Ref. Bon. transferen", value="", placeholder="Referência...")
                with col_m2:
                    nf_b_entrada_sel = st.selectbox("NF de B. ENTRADA", options=[item["nf_entrada"] for item in notas_com_saldo_loja] if notas_com_saldo_loja else ["Nenhuma Nota Disponível"], placeholder="Selecione a nota...")
                    prod_hort_sel = st.selectbox("Produto Hortifrúti", options=[""] + lista_opcoes_prod_v, index=0, placeholder="Selecione o produto...")
                with col_m3:
                    qtd_kg_cx_str = st.text_input("Qtd (kg/cx)", value="", placeholder="0,000")
                    valor_total_avaria_str = st.text_input("Valor Total Avaria (R$)", value="", placeholder="0,00")
                    
                nf_baixa_file = st.file_uploader("NF da baixa (Anexo)", type=["pdf", "png", "jpg", "jpeg"])
                
                col_dm1, col_dm2 = st.columns(2)
                with col_dm1: data_baixa_man = st.date_input("Data da Baixa", value=datetime.now(), format="DD/MM/YYYY")
                with col_dm2:
                    hora_baixa_aut = datetime.now().strftime('%H:%M:%S')
                    st.text_input("Hora da Baixa", value=hora_baixa_aut, disabled=True)
                    
                data_hora_baixa_str = f"{data_baixa_man.strftime('%d/%m/%Y')} {hora_baixa_aut}" if data_baixa_man else ""
                
                if st.form_submit_button("✅ Registrar Baixa", type="primary"):
                    if not lojas_baixa_sel or not ref_bon_transf.strip() or nf_b_entrada_sel == "Nenhuma Nota Disponível" or not prod_hort_sel:
                        st.error("Preencha todos os campos obrigatórios.")
                    else:
                        try:
                            qtd_val_f = float(qtd_kg_cx_str.replace(".", "").replace(",", ".")) if qtd_kg_cx_str else 0.0
                            val_avaria_f = float(valor_total_avaria_str.replace(".", "").replace(",", ".")) if valor_total_avaria_str else 0.0
                        except ValueError:
                            qtd_val_f, val_avaria_f = 0.0, 0.0
                            
                        nota_selecionada_dict = next((item for item in notas_com_saldo_loja if item["nf_entrada"] == nf_b_entrada_sel), None)
                        if not nota_selecionada_dict:
                            st.error("Nota de entrada inválida.")
                        elif val_avaria_f > nota_selecionada_dict["saldo_restante"]:
                            st.error(f"❌ O valor da avaria ultrapassa o saldo restante da nota!")
                        else:
                            path_nf_baixa = ""
                            b64_nf_baixa = ""
                            if nf_baixa_file:
                                path_nf_baixa = os.path.join("uploads", f"NF_BAIXA_{ref_bon_transf}_{nf_baixa_file.name}")
                                bytes_baixa = nf_baixa_file.getbuffer()
                                with open(path_nf_baixa, "wb") as f_out: f_out.write(bytes_baixa)
                                b64_nf_baixa = base64.b64encode(bytes_baixa).decode('utf-8')
                                
                            novo_saldo_nota = nota_selecionada_dict["saldo_restante"] - val_avaria_f
                            novo_saldo_total_disp = saldo_total_disp_loja - val_avaria_f
                            
                            try:
                                conn_ins, db_tins = get_db_connection()
                                cursor_ins = conn_ins.cursor()
                                cursor_ins.execute(
                                    """
                                    INSERT INTO baixas_avarias (
                                        loja_baixa, data_baixa, ref_bon_transferen, nf_baixa, 
                                        nf_b_entrada, produto_hortifruti, quantidade_kg_cx, 
                                        valor_total_avaria, saldo_restante_nota, saldo_total_disponivel, nf_baixa_b64
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """ if db_tins == "postgres" else """
                                    INSERT INTO baixas_avarias (
                                        loja_baixa, data_baixa, ref_bon_transferen, nf_baixa, 
                                        nf_b_entrada, produto_hortifruti, quantidade_kg_cx, 
                                        valor_total_avaria, saldo_restante_nota, saldo_total_disponivel, nf_baixa_b64
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """,
                                    (
                                        lojas_baixa_sel, data_hora_baixa_str, ref_bon_transf.strip(), path_nf_baixa,
                                        nf_b_entrada_sel, prod_hort_sel, qtd_val_f, val_avaria_f, novo_saldo_nota, novo_saldo_total_disp, b64_nf_baixa
                                    )
                                )
                                conn_ins.commit()
                                conn_ins.close()
                                st.success("Baixa registrada com sucesso!")
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                                
        st.markdown("---")
        st.subheader("📋 Planilha de Registro de Baixas das Avarias")
        
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
            pdf_bytes_bx = gerar_pdf_baixas(df_bx_table)
            st.download_button(
                label="📥 Baixar Planilha de Baixas de Avarias em PDF",
                data=pdf_bytes_bx,
                file_name=f"Registro_Baixas_Avarias_HortiControl_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                type="primary",
                key="btn_download_pdf_planilha_baixas"
            )
            st.markdown("")
            
            for _, r_bx in df_bx_table.iterrows():
                if r_bx.get("nf_baixa_b64") and r_bx.get("nf_baixa"):
                    salvar_arquivo_fisico_do_b64(r_bx["nf_baixa"], r_bx["nf_baixa_b64"])
            
            df_display_plan = df_bx_table.copy()
            df_display_plan["Qtd (kg/cx)"] = df_display_plan["quantidade_kg_cx"].apply(lambda x: fmt_ptbr(x, 3))
            df_display_plan["Valor Total Avaria (R$)"] = df_display_plan["valor_total_avaria"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
            df_display_plan["Saldo"] = df_display_plan["saldo_restante_nota"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
            df_display_plan["Saldo Total disponível"] = df_display_plan["saldo_total_disponivel"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
            df_display_plan["NF da baixa"] = df_display_plan.apply(lambda r: "Ver Anexo" if (r.get("nf_baixa") and os.path.exists(str(r["nf_baixa"]))) or r.get("nf_baixa_b64") else "S/Anexo", axis=1)
            
            df_display_plan = df_display_plan.rename(columns={
                "loja_baixa": "LOJAS",
                "data_baixa": "Data Baixa",
                "ref_bon_transferen": "Ref. Bon. transferen",
                "nf_b_entrada": "NF da b. ENTRADA",
                "produto_hortifruti": "Produto Hortifrúti"
            })
            
            df_final_show = df_display_plan[["LOJAS", "Data Baixa", "Ref. Bon. transferen", "NF da baixa", "NF da b. ENTRADA", "Produto Hortifrúti", "Qtd (kg/cx)", "Valor Total Avaria (R$)", "Saldo", "Saldo Total disponível"]]
            df_final_show.index = range(1, len(df_final_show) + 1)
            
            st.dataframe(df_final_show, use_container_width=True, height=400)
            
            st.markdown("---")
            st.subheader("📄 Visualizar Anexo de Baixa")
            opcoes_baixas_ver = [(row["id"], f"Loja: {row['loja_baixa']} | Ref: {row['ref_bon_transferen']} | NF Entrada: {row['nf_b_entrada']}") for _, row in df_bx_table.iterrows() if row.get("nf_baixa") or row.get("nf_baixa_b64")]
            if opcoes_baixas_ver:
                escolha_bx_ver = st.selectbox("Selecione a baixa para abrir o comprovante/anexo", options=opcoes_baixas_ver, format_func=lambda x: x[1], placeholder="Selecione...")
                if escolha_bx_ver:
                    reg_bx_escolhido = df_bx_table[df_bx_table["id"] == escolha_bx_ver[0]].iloc[0]
                    if st.button("📄 Abrir Anexo da Baixa Selecionada", type="primary"):
                        exibir_foto_modal(reg_bx_escolhido.get("nf_baixa", ""), reg_bx_escolhido.get("nf_baixa_b64", ""))
            else:
                st.info("Nenhuma baixa com anexo disponível.")
        else:
            st.info("Nenhum registo de baixa encontrado.")

    elif menu == "Relatórios & Gráficos" and is_admin:
        st.title("📊 Relatórios e Análise Gerencial de Recebimento")
        conn, db_type = get_db_connection()
        df_roms = pd.read_sql_query("SELECT * FROM romaneios", conn)
        df_itens = pd.read_sql_query("SELECT * FROM romaneio_itens", conn)
        df_bonf_rel = pd.read_sql_query("SELECT * FROM bonificacoes", conn)
        df_baixas_rel = pd.read_sql_query("SELECT * FROM baixas_avarias", conn)
        conn.close()
        
        if df_roms.empty or df_itens.empty:
            st.warning("Ainda não existem dados de recebimento cadastrados.")
        else:
            df_roms['data_dt'] = pd.to_datetime(df_roms['data_recebimento'], format='%d/%m/%Y', errors='coerce')
            df_full = df_itens.merge(df_roms, left_on='romaneio_id', right_on='id', suffixes=('_item', '_romaneio'))
            st.markdown("### 🔍 Filtros da Análise Gerencial")
            col_f1, col_f2, col_f3, col_f4 = st.columns([1, 1, 1, 1])
            with col_f1: loja_sel = st.selectbox("Filtrar por Loja", ["TODAS AS LOJAS"] + list(df_roms["loja"].unique()), placeholder="Selecione...", key="rel_filter_loja")
            with col_f2: prod_sel = st.selectbox("Filtrar por Produto", ["TODOS OS PRODUTOS"] + sorted(list(df_itens["produto"].unique())), placeholder="Selecione...", key="rel_filter_prod")
            with col_f3:
                dt_min = df_roms['data_dt'].min() if not df_roms['data_dt'].isna().all() else datetime.now()
                dt_inicio = st.date_input("Data Início", value=dt_min, format="DD/MM/YYYY", key="rel_filter_dt_ini")
            with col_f4:
                dt_max = df_roms['data_dt'].max() if not df_roms['data_dt'].isna().all() else datetime.now()
                dt_fim = st.date_input("Data Fim", value=dt_max, format="DD/MM/YYYY", key="rel_filter_dt_fim")
                
            df_filtrado = df_full.copy()
            if loja_sel != "TODAS AS LOJAS": df_filtrado = df_filtrado[df_filtrado["loja"] == loja_sel]
            if prod_sel != "TODOS OS PRODUTOS": df_filtrado = df_filtrado[df_filtrado["produto"] == prod_sel]
            if dt_inicio and dt_fim: df_filtrado = df_filtrado[(df_filtrado["data_dt"] >= pd.to_datetime(dt_inicio)) & (df_filtrado["data_dt"] <= pd.to_datetime(dt_fim))]
                
            if df_filtrado.empty: st.info("Nenhum registo encontrado.")
            else:
                st.markdown("---")
                st.subheader("📈 Indicadores Principais (KPIs)")
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                kpi1.metric("Valor Total Recebido", f"R$ {fmt_ptbr(df_filtrado['valor_total'].sum(), 2)}")
                kpi2.metric("Total de Romaneios", f"{df_filtrado['numero_romaneio'].nunique()} romaneios")
                kpi3.metric("Qtd / Peso Total", f"{fmt_ptbr(df_filtrado['quantidade'].sum(), 3)}")
                kpi4.metric("Principal Fornecedor", str(df_filtrado.groupby("fornecedor")["valor_total"].sum().idxmax() if not df_filtrado.empty else "N/A"))
                st.markdown("---")
                
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    top_prods_val = df_filtrado.groupby("produto")["valor_total"].sum().nlargest(10).reset_index()
                    fig_val = px.bar(top_prods_val, x="produto", y="valor_total", text_auto=".2f", color="valor_total", color_continuous_scale="Greens")
                    fig_val.update_layout(xaxis_title="Produto", yaxis_title="Total (R$)", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                    st.plotly_chart(fig_val, use_container_width=True)
                with col_g2:
                    top_prods_qtd = df_filtrado.groupby("produto")["quantidade"].sum().nlargest(10).reset_index()
                    fig_qtd = px.bar(top_prods_qtd, x="produto", y="quantidade", text_auto=".2f", color="quantidade", color_continuous_scale="Reds")
                    fig_qtd.update_layout(xaxis_title="Produto", yaxis_title="Qtd / Peso", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                    st.plotly_chart(fig_qtd, use_container_width=True)
                
                st.download_button(label="📥 Baixar Relatório Consolidado (Excel / CSV)", data=df_filtrado.to_csv(index=False, sep=';').encode('utf-8-sig'), file_name=f"Relatorio_Hortifruti_HortiControl_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary", key="btn_download_csv_relatorio")

    elif menu == "Gerenciar Cadastros (Produtos)" and is_admin:
        st.title("📦🚚 Gerenciamento e Cadastro (Produtos & Fornecedores)")
        tab_prod, tab_forn = st.tabs(["📦 Cadastro de Produtos", "🚚 Cadastro de Fornecedores"])
        
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
                            conn, db_type = get_db_connection()
                            cursor = conn.cursor()
                            try:
                                cursor.execute("INSERT INTO produtos (codigo_produto, codigo_barras, nome, unidade_padrao) VALUES (%s, %s, %s, %s)" if db_type == "postgres" else "INSERT INTO produtos (codigo_produto, codigo_barras, nome, unidade_padrao) VALUES (?, ?, ?, ?)", (cod_prod_input.strip() if cod_prod_input else None, cod_bar_input.strip() if cod_bar_input else None, nome_p.strip().upper(), und_p))
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
                st.download_button(label="📥 Baixar Relatório de Produtos em PDF", data=gerar_pdf_produtos(produtos_cadastrados), file_name=f"Relatorio_Produtos_HortiControl_{datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf", type="primary")
                st.markdown("")
                st.dataframe(df_produtos[["ID", "Código do Produto", "Código de Barras", "Nome do Produto", "Unidade Padrão"]], use_container_width=True, hide_index=True, height=300)
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
            cursor.execute("SELECT id, codigo_fornecedor, cnpj, nome, contato FROM fornecedores ORDER BY nome")
            fornecedores_cadastrados = cursor.fetchall()
            conn.close()
            
            if fornecedores_cadastrados:
                forn_com_id_ajustado = [(i, f[1], f[2], f[3], f[4], f[0]) for i, f in enumerate(fornecedores_cadastrados, 1)]
                df_forn_show = pd.DataFrame(forn_com_id_ajustado, columns=["ID", "Código", "CNPJ", "Nome do Fornecedor", "Contato", "ID_Real"])
                st.dataframe(df_forn_show[["ID", "Código", "CNPJ", "Nome do Fornecedor", "Contato"]], use_container_width=True, hide_index=True, height=300)
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
                    if not novo_nome.strip() or not novo_login.strip() or not nova_senha.strip(): st.error("Preencha todos os campos.")
                    else:
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
        else: st.info("Nenhum usuário cadastrado.")
