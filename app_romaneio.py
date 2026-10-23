import base64
from datetime import datetime, timedelta
import io
import os
import pandas as pd
from PIL import Image
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

# Garante que a pasta de uploads/fotos exista sempre
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# ---------------------------------------------------------
# FUNÇÃO PARA VER FOTO EM TELA CHEIA (DIALOG MODAL)
# ---------------------------------------------------------
@st.dialog("📷 Visualização da Foto Anexada", width="large")
def exibir_foto_modal(caminho_foto):
    if os.path.exists(caminho_foto):
        st.image(caminho_foto, use_container_width=True, caption="Comprovante / Nota Anexada")
    else:
        st.error("Arquivo de imagem não encontrado no servidor.")

# ---------------------------------------------------------
# 2. ESTILOS CSS E VISUAL DO SISTEMA
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

css_fundo = ""
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
        max-width: 85px !important;
        width: 100% !important;
        height: auto !important;
        margin: 0 auto !important;
        display: block !important;
    }}

    .titulo-logo {{
        font-size: 2.4rem !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
        margin-bottom: 0px !important;
        font-family: 'Arial Black', Gadget, sans-serif !important;
    }}

    .palavra-sup-mercado {{
        color: #2E7D32 !important;
        font-size: 1.25rem !important;
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
            -1.5px -1.5px 0 #FFEB3B, 1.5px -1.5px 0 #FFEB3B, -1.5px -1.5px 0 #FFEB3B, 1.5px -1.5px 0 #FFEB3B,
            -3px -3px 0 #B71C1C, 3px -3px 0 #B71C1C, -3px 3px 0 #B71C1C, 3px 3px 0 #B71C1C,
            3px 3px 5px rgba(0, 0, 0, 0.6) !important;
    }}

    .palavra-cidade {{
        color: #111111 !important;
        font-style: italic !important;
        font-family: 'Brush Script MT', cursive, sans-serif !important;
        font-size: 3.0rem !important;
        text-shadow: 2px 3px 4px rgba(0, 0, 0, 0.8), -1.5px -1.5px 0 #FFF, 1.5px -1.5px 0 #FFF, -1.5px 1.5px 0 #FFF, 1.5px 1.5px 0 #FFF !important;
    }}

    .stApp h3 {{
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important;
        font-weight: 800 !important;
        font-size: 1.4rem !important;
        margin-top: 4px !important;
        margin-bottom: 10px !important;
    }}

    .stApp label {{
        color: #FFFFFF !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.9) !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }}

    div[data-baseweb="input"] input {{
        color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 6px !important;
        font-size: 15px !important;
    }}

    div[data-baseweb="input"] input::placeholder {{
        color: transparent !important;
    }}

    div[data-testid="stRadio"] label p {{
        font-size: 1.1rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.9) !important;
    }}

    div[data-testid="stRadio"] div[role="radiogroup"] {{
        background-color: rgba(0, 0, 0, 0.4) !important;
        padding: 8px 12px !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
    }}

    div[data-testid="stExpander"] summary span p {{
        font-size: 1.15rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        text-shadow: 1px 1px 3px rgba(0,0,0,0.9) !important;
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
    
    @media only screen and (max-width: 768px) {{
        .stDataFrame {{
            font-size: 11px !important;
            overflow-x: auto !important;
        }}
        div[data-testid="stHorizontalBlock"] {{
            flex-direction: column !important;
        }}
    }}
    {css_fundo}
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 3. BANCO DE DADOS E CATÁLOGO (PRODUTOS OFICIAIS CISS)
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
    
    cursor.execute("DELETE FROM produtos WHERE codigo_produto = 'S/N' OR codigo_barras = 'S/N' OR codigo_produto IS NULL OR codigo_barras IS NULL")
    
    cursor.execute("SELECT * FROM usuarios WHERE login = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (nome, login, senha, perfil) VALUES"
            " ('Administrador', 'admin', '1234', 'Gestor')"
        )
    
    produtos_iniciais = [
        ("58063", "82405", "ABACATE AVOCADO KG", "KG"),
        ("5884", "28920", "ABACATE FORTUNA KG", "KG"),
        ("17510", "48903", "ABACATE GEADA KG", "KG"),
        ("2240", "165651", "ABACATE MARGARIDA KG", "KG"),
        ("9034", "163887", "ABACATE REGIONAL KG", "KG"),
        ("73677", "90217", "ABACAXI FATIADO KG", "KG"),
        ("2387", "165662", "ABACAXI KG PERDA", "KG"),
        ("69496", "66294", "ABACAXI POTE KG", "KG"),
        ("6156", "30531", "ABACAXI UN", "UN"),
        ("50760", "79258", "ABOBORA MORANGA KG", "KG"),
        ("17503", "48887", "ABOBRINHA CABOTIA KG", "KG"),
        ("77170", "91644", "ABOBRINHA CABOTIA EMB KG", "KG"),
        ("76982", "91637", "ABOBRINHA EMBALADA KG", "KG"),
        ("77040", "91641", "ABOBRINHA ITALIANA EMB KG", "KG"),
        ("3667", "165723", "ABOBRINHA ITALIANA KG", "KG"),
        ("2356", "165659", "ABOBRINHA KG", "KG"),
        ("76470", "91172", "ACELGA EMBALADA KG", "KG"),
        ("34982", "165739", "ACELGA KG", "KG"),
        ("76074", "91146", "ALECRIM EMBALADO KG", "KG"),
        ("54195", "80659", "ALECRIM KG", "KG"),
        ("7898910073589", "165340", "ALFACE AMERICANA UN", "UN"),
        ("7898941929046", "90269", "ALFACE AMERICANA BURITI UN", "UN"),
        ("386296", "165339", "ALFACE ROXA UN", "UN"),
        ("7890000070881", "90849", "ALFACE VERMELHA BURITI UN", "UN"),
        ("7898941929398", "90270", "ALFACE VIVA BABY UN", "UN"),
        ("76111", "91149", "ALHO PORO EMB KG", "KG"),
        ("54003", "80530", "ALHO PORO KG", "KG"),
        ("75299", "90724", "ALHO ROXO EMBALADO KG", "KG"),
        ("4275", "187484", "ALHO ROXO KG", "KG"),
        ("564083", "56407", "ALHO TIPO 7 UN", "UN"),
        ("75794", "90997", "AMEIXA FRESCA EMB KG", "KG"),
        ("2417", "165665", "AMEIXA FRESCA KG", "KG"),
        ("42581", "165144", "AMEIXA SECA S/CA KG", "KG"),
        ("182", "131307", "BANANA NANICA KG", "KG"),
        ("1038", "165575", "BANANA PACOVAN KG", "KG"),
        ("2073", "165634", "BANANA PRATA KG", "KG"),
        ("75022", "32795", "BATATA DOCE BRANCA A VACUO KG", "KG"),
        ("7832", "90703", "BATATA DOCE BRANCA EMBALADA KG", "KG"),
        ("2219", "165648", "BATATA DOCE BRANCA KG", "KG"),
        ("75244", "32798", "BATATA DOCE ROXA A VACUO KG", "KG"),
        ("7856", "90705", "BATATA DOCE ROXA EMBALADA KG", "KG"),
        ("5104", "28298", "BATATA DOCE ROXA KG", "KG"),
        ("22699", "58117", "BATATA LAVADA KG", "KG"),
        ("88022", "92532", "BATATA PORT TIPO B PCT KG", "KG"),
        ("88688", "92830", "BATATA PORTUGUE PALITO KG", "KG"),
        ("88749", "92831", "BATATA PORTUGUES CUBOS KG", "KG"),
        ("2233", "163880", "BATATA PORTUGUESA KG", "KG"),
        ("27090", "28477", "BATATA PORTUGUESA KG VACUO KG", "KG"),
        ("1152722", "11075015", "BATATA PORTUGUESA PCT UN", "UN"),
        ("74629", "90472", "BATATA PORTUGUESA PCT KG", "KG"),
        ("22002", "165110", "BATATINHA KG", "KG"),
        ("45100", "71383", "BERINJELA EMBALADA KG", "KG"),
        ("2349", "165658", "BERINJELA KG", "KG"),
        ("39888", "66295", "BETERRABA EMBALADA KG", "KG"),
        ("2165", "165643", "BETERRABA KG", "KG"),
        ("75831", "90998", "BROCOLIS EMBALADO KG", "KG"),
        ("3223", "165707", "BROCOLIS KG", "KG"),
        ("75886", "91000", "BROCOLIS NINJA EMB KG", "KG"),
        ("4480", "165766", "BROCOLIS NINJA KG", "KG"),
        ("57776", "82392", "CAQUI KG", "KG"),
        ("2691", "165686", "CARA KG", "KG"),
        ("88770", "19440", "CEBOLA FATIADA KG", "KG"),
        ("2028", "165629", "CEBOLA KG", "KG"),
        ("743525", "74351", "CEBOLA PALITO PCT UN", "UN"),
        ("74643", "90475", "CEBOLA PCT KG", "KG"),
        ("58568", "131277", "CEBOLA PCT UND UN", "UN"),
        ("68192", "165176", "CEBOLA PEROLA KG", "KG"),
        ("674", "131654", "CEBOLA ROXA KG", "KG"),
        ("18906", "56095", "CEBOLA ROXA PCT UN", "UN"),
        ("371636", "37162", "CEBOLINHA H&C HORTICULTURA UN", "UN"),
        ("49009", "66298", "CENOURA EMBALADA KG", "KG"),
        ("2226", "165649", "CENOURA KG", "KG"),
        ("18944", "66297", "CENOURA RALADA KG", "KG"),
        ("8303", "33219", "CEREJA KG", "KG"),
        ("2127", "165639", "CHEIRO VERDE UN", "UN"),
        ("68918", "37144", "CHICORIA H&C HORTICULTURA UN", "UN"),
        ("88947", "92891", "CHUCHU EMBALADO KG", "KG"),
        ("949", "165567", "CHUCHU KG", "KG"),
        ("74483", "90318", "COCO SECO EMBALADO 1UN UN", "UN"),
        ("6705", "165863", "COCO SECO UN", "UN"),
        ("2547", "19862", "COCO VERDE UN", "UN"),
        ("68833", "37164", "COENTRO H&C HORTICULTURA UN", "UN"),
        ("37327", "30539", "CORRIJA-ME KG", "KG"),
        ("37860", "32801", "CORRIJA-ME KG", "KG"),
        ("76142", "91151", "COUVE FLOR EMB KG", "KG"),
        ("28929", "63050", "COUVE FLOR KG", "KG"),
        ("2172", "165644", "COUVE UN", "UN"),
        ("74957", "83708", "CUPUACU KG", "KG"),
        ("89661", "93154", "DUETO DE FRU ESPECIAIS KG", "KG"),
        ("89647", "93143", "DUETO DE FRUTAS KG", "KG"),
        ("76104", "91148", "ESPINAFRE EMBALADO KG", "KG"),
        ("1298", "131275", "ESPINAFRE KG", "KG"),
        ("644105", "64409", "FECULA KG PROD KG", "KG"),
        ("66051", "25096", "FEIJÃO VAGEM KG", "KG"),
        ("2202", "165647", "FEIJAO VERDE UN", "UN"),
        ("7898336950150", "28006", "FRUTA CRISTALIZADA PEROLA 10KG UN", "UN"),
        ("2400", "165664", "FRUTAS CRISTALIZAS KG", "KG"),
        ("88923", "92889", "GENGIBRE EMBALADO KG", "KG"),
        ("22392", "166819", "GENGIBRE KG", "KG"),
        ("4268", "165758", "GOIABA KG", "KG"),
        ("798190027999", "62293", "GOMA DE MANDIOCA AMAZONICA 1KG UN", "UN"),
        ("798190189116", "62294", "GOMA DE MANDIOCA C/ CAST AMAZONICA 800G UN", "UN"),
        ("798190189123", "62295", "GOMA DE MANDIOCA C/ CHIA AMAZONICA 800G UN", "UN"),
        ("9942", "165989", "GOMA DE TAPIOCA KG", "KG"),
        ("76005", "91142", "HORTELA EMBALADA KG", "KG"),
        ("68543", "88267", "HORTELA H&C HORTICULTURA UN", "UN"),
        ("3247", "165708", "HORTELA KG", "KG"),
        ("6385", "31519", "INGREDIENTES P/ MAIONESE KG", "KG"),
        ("4565", "137074", "INHAME KG", "KG"),
        ("3094", "25097", "JAMBU UN", "UN"),
        ("12508", "36027", "JENIPAPO KG", "KG"),
        ("7023", "66299", "JERIMUM EMBALADO KG", "KG"),
        ("2196", "165646", "JERIMUM KG", "KG"),
        ("75497", "90796", "KIT CALDEIRADA KG", "KG"),
        ("76630", "91274", "KIT CENOURA E BETERRABA KG", "KG"),
        ("59220", "19444", "KIT COZIDAO KG", "KG"),
        ("86899", "92193", "KIT JERIMUM E CENOURA KG", "KG"),
        ("9195", "34569", "KIT LEGUMES KG", "KG"),
        ("7184", "32262", "KIT SOPA KG", "KG"),
        ("86929", "92218", "KIT TOMATE E PIMENTAO KG", "KG"),
        ("86981", "92220", "KIT TOMATE PIME PEPINO KG", "KG"),
        ("7898060740744", "36483", "KIWI IMPORTADO 600G BDJ UN", "UN"),
        ("8747", "165943", "KIWI KG", "KG"),
        ("9690", "35740", "LARANJA BAHIA KG", "KG"),
        ("6200", "165656", "LARANJA PACOTE C/12UN PT", "PT"),
        ("61827", "86243", "LARANJA PAULISTA PCT KG", "KG"),
        ("2080", "165635", "LARANJA REGIONAL KG", "KG"),
        ("74919", "90481", "LARANJA REGIONAL PCT KG", "KG"),
        ("2059", "165632", "LIMAO KG", "KG"),
        ("74926", "90482", "LIMAO PCT KG", "KG"),
        ("14571", "38737", "LIMAO SICILIANO KG", "KG"),
        ("7898060740072", "44550", "MACA FUJI PAP PCT DIVERTIDAS 1KG UN", "UN"),
        ("75787", "90996", "MACA GRANNY SMITH EMB KG", "KG"),
        ("4381", "28078", "MACA GRANNY SMITH KG", "KG"),
        ("447638", "44762", "MACA IMPORTADA ENTRADA UN", "UN"),
        ("4312", "28071", "MACA KG", "KG"),
        ("1007", "165572", "MACA RED KG", "KG"),
        ("2332", "165657", "MACAXEIRA KG", "KG"),
        ("74148", "90247", "MAMAO EMBALADO KG", "KG"),
        ("2363", "165660", "MAMAO KG", "KG"),
        ("7887", "66300", "MAMAO POTE KG", "KG"),
        ("57851", "82393", "MANGA ROSA KG", "KG"),
        ("201", "178998", "MANGA TOMMY KG", "KG"),
        ("6521", "66301", "MANGA TOMMY POTE KG", "KG"),
        ("76012", "91143", "MANJERICAO EMBALADO KG", "KG"),
        ("68475", "88266", "MANJERICAO H&C HORTICULTURA UN", "UN"),
        ("56601", "81476", "MANJERICAO KG", "KG"),
        ("2264", "165653", "MARACUJA KG", "KG"),
        ("777", "132909", "MASTRUZ MACO UN", "UN"),
        ("73974", "90219", "MATERIA PRIMA MANIPULACAO KG", "KG"),
        ("18296", "66305", "MAXIXE BDJ KG", "KG"),
        ("2158", "165642", "MAXIXE KG", "KG"),
        ("12942", "36449", "MELANCIA BABY KG", "KG"),
        ("87803", "92489", "MELANCIA EMBALADA KG", "KG"),
        ("75404", "24094", "MELANCIA KG", "KG"),
        ("29087", "66291", "MELANCIA POTE KG", "KG"),
        ("13048", "36451", "MELAO COMUM GAIA KG", "KG"),
        ("2370", "165661", "MELAO COMUM KG", "KG"),
        ("29889", "66304", "MELAO COMUM POTE KG", "KG"),
        ("12973", "36450", "MELAO DINO KG", "KG"),
        ("21128", "167057", "MELAO FAMOSA KG", "KG"),
        ("5074", "28214", "MELAO GALIA KG", "KG"),
        ("409", "131464", "MELAO PELE DE SAPO KG", "KG"),
        ("17817", "131253", "MELAO REI KG", "KG"),
        ("60974", "84505", "MEXERICA MURCOTE KG", "KG"),
        ("17909", "136368", "MILHO VERDE C/ CASCA UN", "UN"),
        ("73783", "90218", "MILHO VERDE S/ CASCA UN", "UN"),
        ("29018", "19438", "MIX DE FRUTAS POTE KG", "KG"),
        ("8686", "165939", "MORANGO BDJ KG", "KG"),
        ("76487", "91174", "MORANGO EMBALADO KG", "KG"),
        ("8280", "165936", "NECTARINA KG", "KG"),
        ("4213", "28000", "NOZES S/ CASCA KG", "KG"),
        ("74285", "90251", "PEPINO COMUM EMBALADO KG", "KG"),
        ("2066", "165633", "PEPINO COMUM KG", "KG"),
        ("88626", "92819", "PEPINO SALADA EMB KG", "KG"),
        ("3490", "27463", "PEPINO SALADA KG", "KG"),
        ("4398", "28079", "PERA DANJOU KG", "KG"),
        ("6118", "30308", "PERA PORTUGUESA KG", "KG"),
        ("2448", "165667", "PESSEGO KG", "KG"),
        ("89388", "93015", "PIMENTA BOLINHA EMB KG", "KG"),
        ("7898927907525", "90921", "PIMENTA CAMBUCI FRUTAMINA 150G UN", "UN"),
        ("61810", "86177", "PIMENTA CAMBUCI KG", "KG"),
        ("31455", "66306", "PIMENTA DE CHEIRO EMB KG", "KG"),
        ("675369", "163735", "PIMENTA DE CHEIRO KG", "KG"),
        ("4138", "165577", "PIMENTA DEDO DE MOCA KG", "KG"),
        ("75718", "90992", "PIMENTA MALAGUETA EMB KG", "KG"),
        ("11303", "131271", "PIMENTA MALAGUETA KG", "KG"),
        ("75732", "90994", "PIMENTA MURUPI EMB KG", "KG"),
        ("932", "165566", "PIMENTA MURUPI KG", "KG"),
        ("7896806502564", "82967", "PIMENTAO AMARELO BLOCK 1UN UN", "UN"),
        ("13666", "19839", "PIMENTAO AMARELO ENTRADA KG", "KG"),
        ("6859", "165871", "PIMENTAO COLORIDO EMB KG", "KG"),
        ("703", "165548", "PIMENTAO COLORIDO KG", "KG"),
        ("45421", "66307", "PIMENTAO VERDE EMB KG", "KG"),
        ("2110", "165638", "PIMENTAO VERDE KG", "KG"),
        ("37549", "28487", "PIMENTAO VERDE KG CORRIJA-ME", "KG"),
        ("7896806502519", "82966", "PIMENTAO VERMELHO BLOCK 1UN UN", "UN"),
        ("15295", "40184", "PITAYA KG", "KG"),
        ("74971", "90692", "PITAYA POTE KG", "KG"),
        ("89180", "92977", "POLPA DE GOIABA KG", "KG"),
        ("17831", "44361", "POLPA DE MACAXEIRA KG", "KG"),
        ("74230", "90250", "POLPA DE MARACUJA KG", "KG"),
        ("76548", "91263", "QUIABO EMBALADO KG", "KG"),
        ("2134", "165640", "QUIABO KG", "KG"),
        ("1793", "165614", "RABANETE KG", "KG"),
        ("5142", "178999", "RAMBUTAN BDJ KG", "KG"),
        ("76227", "91156", "REPOLHO ROXO EMB KG", "KG"),
        ("4459", "165764", "REPOLHO ROXO KG", "KG"),
        ("76319", "91157", "REPOLHO VERDE EMB KG", "KG"),
        ("2097", "165636", "REPOLHO VERDE KG", "KG"),
        ("8310", "33215", "ROMA KG", "KG"),
        ("76098", "91147", "RUCULA EMBALADA KG", "KG"),
        ("68666", "88269", "RUCULA H&C HORTICULTURA UN", "UN"),
        ("3254", "165709", "RUCULA KG", "KG"),
        ("67843", "19449", "SALADA KG", "KG"),
        ("76050", "91145", "SALSA EMBALADA KG", "KG"),
        ("68635", "88268", "SALSA H&C HORTICULTURA UN", "UN"),
        ("9621", "165976", "SALSA KG", "KG"),
        ("6191514300190", "68676", "TAMARA FIT C/CAROCO 200G UN", "UN"),
        ("75541", "90798", "TANGERINA IMPORTADA EMBALADA KG", "KG"),
        ("2516", "165674", "TANGERINA IMPORTADA KG", "KG"),
        ("2515", "170718", "TANGERINA REGIONAL KG", "KG"),
        ("75985", "91003", "TOMATE CEREJA EMB KG", "KG"),
        ("25362", "178003", "TOMATE CEREJA KG", "KG"),
        ("1175", "41418", "TOMATE KG", "KG"),
        ("908009", "90799", "TUCUPI 2L UN", "UN"),
        ("609963080069", "44160", "UVA BLACK S/SEMENTE 250G UN", "UN"),
        ("892131", "78420", "UVA BRANCA DOCE 500G UN", "UN"),
        ("7908046701451", "87639", "UVA BRANCA DOCE UVA S/ SEMENTE 500G UN", "UN"),
        ("7898957749492", "66509", "UVA CAPPELLARO KIDS VITORIA 250G UN", "UN"),
        ("4329", "28073", "UVA CRIMSON KG", "KG"),
        ("751320764126", "39599", "UVA CRIMSON TET 500G UN", "UN"),
        ("7908046710477", "72075", "UVA FRUTAYA BRANCA S/ SEMENTE 500G UN", "UN"),
        ("7908046710491", "72076", "UVA FRUTAYA PRETA S/ SEMENTE 500G UN", "UN"),
        ("7898954999012", "33333", "UVA GRANDVALLE 500G UN", "UN"),
        ("7898956087021", "33222", "UVA MIDNIGHT 250G VITORIA UN", "UN"),
        ("4343", "28074", "UVA MIDNIGHT KG", "KG"),
        ("751320764102", "35155", "UVA MIDNIGHT TET 500G UN", "UN"),
        ("7908046701567", "84591", "UVA MISTA DOCE UVA 500G UN", "UN"),
        ("751320764140", "33221", "UVA MISTA TET 500G UN", "UN"),
        ("2394", "165663", "UVA PASSA KG", "KG"),
        ("7896291950550", "48350", "UVA PASSAS PRETA 10KG UN", "UN"),
        ("7898598810476", "51400", "UVA PASSAS PRETA S/S CX 10 KGS UN", "UN"),
        ("7908046701338", "79594", "UVA PRETA DOCE UVA C/ SEMENTE 500G UN", "UN"),
        ("7908046701222", "78419", "UVA PRETA DOCE UVA S/ SEMENTE 500G UN", "UN"),
        ("7908046707880", "84592", "UVA PRETA SEM SEMENTE DOCE UVA 250G UN", "UN"),
        ("7898962939062", "90062", "UVA PRETA VITORIA CANASTRA S/SEMENT 500G UN", "UN"),
        ("2462", "165669", "UVA RED GLOBE KG", "KG"),
        ("751320764195", "131357", "UVA RED GLOBE TET 500G UN", "UN"),
        ("5555", "165840", "UVA THOMPSON KG", "KG"),
        ("751320764133", "38027", "UVA THOMPSON TET 500G UN", "UN"),
        ("7898965049027", "90061", "UVA VERDE CANASTRA S/SEMENTE 500G UN", "UN"),
        ("609963080076", "44403", "UVA VERDE THOMPSON 250G UN", "UN"),
        ("7908046701468", "73566", "UVA VERMELHA DOCE UVA S/ SEMENTE 500G UN", "UN"),
        ("7898938321617", "92390", "UVA VITORIA MIMO DOCE S/SEMENTE 400G UN", "UN"),
        ("83492", "19448", "VINAGRETE KG", "KG")
    ]
    
    for cod_b, cod_p, nome_prod, und_p in produtos_iniciais:
        try:
            cursor.execute(
                "INSERT OR IGNORE INTO produtos (codigo_barras, codigo_produto, nome, unidade_padrao) VALUES (?, ?, ?, ?)",
                (cod_b, cod_p, nome_prod, und_p)
            )
        except Exception:
            pass

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
        if decimais == 3:
            s = f"{f:,.3f}"
        else:
            s = f"{f:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return s
    except Exception:
        return "0,00"

def remover_fundo_branco(caminho_imagem):
    """Converte o fundo branco de uma imagem de assinatura em transparente."""
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
# 4
