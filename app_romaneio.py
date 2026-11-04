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
import fitz # PyMuPDF
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
&quot;logo_romaneio.png.jpg&quot;,

&quot;logo_romaneio.png&quot;,
&quot;logo.png&quot;,
&quot;Tela de login.jpeg&quot;,
&quot;tela_de_login.jpeg&quot;,
]:
if os.path.exists(nome):
logo_icon = nome
break
st.set_page_config(
page_title=&quot;HortiControl Supernova - Recebimento Hortifrúti&quot;,
page_icon=logo_icon if logo_icon else &quot;��&quot;,
layout=&quot;wide&quot;,
)
if not os.path.exists(&quot;uploads&quot;):
os.makedirs(&quot;uploads&quot;)
# ---------------------------------------------------------
# CONEXÃO SEGURA COM BANCO DE DADOS
# ---------------------------------------------------------
def get_db_connection():
if HAS_POSTGRES and &quot;database&quot; in st.secrets and &quot;db_url&quot; in st.secrets[&quot;database&quot;]:
try:
conn = psycopg2.connect(st.secrets[&quot;database&quot;][&quot;db_url&quot;], connect_timeout=5)
return conn, &quot;postgres&quot;
except Exception as e:
st.error(f&quot;Erro crítico ao conectar no PostgreSQL (Neon): {e}&quot;)
raise e
conn = sqlite3.connect(&quot;romaneio_hortifruti.db&quot;, timeout=10)
return conn, &quot;sqlite&quot;
# ---------------------------------------------------------
# FUNÇÃO DE SPINNER / FEEDBACK COM LOGOTIPO DO SUPERNOVA
# ---------------------------------------------------------
def spinner_supernova(mensagem=&quot;A carregar dados do Supernova...&quot;):
logo_path_spin = None
for nome in [&quot;logo_romaneio.png.jpg&quot;, &quot;logo_romaneio.png&quot;, &quot;logo.png&quot;, &quot;Tela de login.jpeg&quot;]:
if os.path.exists(nome):
logo_path_spin = nome
break
if logo_path_spin:
with open(logo_path_spin, &quot;rb&quot;) as img_f:
b64_spin = base64.b64encode(img_f.read()).decode()
return st.markdown(f&quot;&quot;&quot;
&lt;div style=&quot;display: flex; align-items: center; justify-content: center; gap: 15px; background:
rgba(20, 24, 30, 0.95); padding: 15px 25px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.2);
margin: 15px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.5);&quot;&gt;
&lt;img src=&quot;data:image/jpeg;base64,{b64_spin}&quot; style=&quot;width: 40px; height: 40px; border-radius:
50%; object-fit: cover; animation: pulse 1.5s infinite;&quot; /&gt;
&lt;span style=&quot;color: #FFFFFF; font-weight: 800; font-size: 15px; letter-spacing:
0.5px;&quot;&gt;{mensagem}&lt;/span&gt;
&lt;/div&gt;
&lt;style&gt;
@keyframes pulse {{
0% {{ transform: scale(0.95); opacity: 0.8; }}
50% {{ transform: scale(1.05); opacity: 1; filter: drop-shadow(0 0 8px #4CAF50); }}
100% {{ transform: scale(0.95); opacity: 0.8; }}

}}
&lt;/style&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
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
with open(caminho_alvo, &quot;wb&quot;) as f_out:
f_out.write(base64.b64decode(b64_str))
except Exception:
pass
# ---------------------------------------------------------
# MODAL DE VISUALIZAÇÃO DE ANEXOS
# ---------------------------------------------------------
@st.dialog(&quot;�� Visualizador de Documentos&quot;, width=&quot;large&quot;)
def exibir_foto_modal(caminho_foto, b64_dados=None):
if not caminho_foto and b64_dados:
caminho_foto = os.path.join(&quot;uploads&quot;, &quot;documento_anexado.pdf&quot;)
if b64_dados:
salvar_arquivo_fisico_do_b64(caminho_foto, b64_dados)
if caminho_foto and os.path.exists(caminho_foto) and os.path.getsize(caminho_foto) &gt; 0:
nome_arquivo = os.path.basename(caminho_foto)
is_pdf = caminho_foto.lower().endswith(&quot;.pdf&quot;)
ext_tag = &quot;PDF&quot; if is_pdf else &quot;IMG&quot;
bg_tag_color = &quot;#EA4335&quot; if is_pdf else &quot;#4285F4&quot;
st.markdown(f&quot;&quot;&quot;
&lt;div style=&quot;background-color: #202124; padding: 12px 18px; border-radius: 8px 8px 0 0; display: flex;
align-items: center; justify-content: space-between; border-bottom: 1px solid #3c4043; margin-bottom: 15px;&quot;&gt;
&lt;div style=&quot;display: flex; align-items: center; gap: 12px;&quot;&gt;
&lt;span style=&quot;background-color: {bg_tag_color}; color: white; padding: 4px 8px; border-radius:
4px; font-weight: bold; font-size: 11px;&quot;&gt;{ext_tag}&lt;/span&gt;
&lt;span style=&quot;color: #ffffff; font-weight: 600; font-size: 15px;&quot;&gt;{nome_arquivo}&lt;/span&gt;
&lt;/div&gt;
&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
if is_pdf:
pdf_renderizado = False
if HAS_PYMUPDF:
try:
doc_pdf = fitz.open(caminho_foto)
total_paginas = len(doc_pdf)
st.markdown(f&quot;&lt;p style=&#39;text-align: center; color: #9aa0a6; font-size: 13px; margin-
bottom: 12px;&#39;&gt;PDF convertido visualmente • {total_paginas} página(s)&lt;/p&gt;&quot;, unsafe_allow_html=True)

for page_index in range(total_paginas):
page = doc_pdf[page_index]
pix = page.get_pixmap(dpi=150)
img_bytes = pix.tobytes(&quot;png&quot;)
st.markdown(f&quot;&quot;&quot;
&lt;div style=&quot;background-color: #2d2e30; padding: 6px; border-radius: 6px; margin-
bottom: 6px; text-align: center; border: 1px solid #3c4043;&quot;&gt;
&lt;p style=&quot;color: #bdc1c6; font-size: 12px; margin: 0; font-weight: bold;&quot;&gt;Página
{page_index + 1} de {total_paginas}&lt;/p&gt;
&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
st.image(img_bytes, use_container_width=True)
pdf_renderizado = True
except Exception as e:
st.warning(f&quot;Erro ao processar páginas do PDF: {e}&quot;)
if not pdf_renderizado:
st.markdown(&quot;&quot;&quot;
&lt;div style=&quot;background-color: #2d2e30; padding: 20px; border-radius: 8px; text-align: center;
border: 1px solid #3c4043; margin-bottom: 15px;&quot;&gt;
&lt;p style=&quot;color: #ffffff; font-size: 15px; font-weight: bold; margin-bottom:
8px;&quot;&gt;Visualização direta de PDF restrita pelo navegador&lt;/p&gt;
&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
st.markdown(&quot;---&quot;)
with open(caminho_foto, &quot;rb&quot;) as f_pdf:
st.download_button(
label=f&quot;�� Descarregar Ficheiro PDF Original ({nome_arquivo})&quot;,
data=f_pdf.read(),
file_name=nome_arquivo,
mime=&quot;application/pdf&quot;,
type=&quot;primary&quot;
)
else:
st.image(caminho_foto, use_container_width=True, caption=&quot;Documento Anexado&quot;)
with open(caminho_foto, &quot;rb&quot;) as f_img:
img_bytes = f_img.read()
st.download_button(
label=f&quot;�� Descarregar Imagem ({nome_arquivo})&quot;,
data=img_bytes,
file_name=nome_arquivo,
mime=&quot;application/jpeg&quot;,
type=&quot;primary&quot;
)
else:
st.error(&quot;Ficheiro de anexo não encontrado no servidor ou o registo não possui conteúdo binário
válido.&quot;)
# ---------------------------------------------------------
# 2. ESTILOS E PADRÃO VISUAL
# ---------------------------------------------------------
bg_login_path = None
for nome_bg in [
&quot;Tela-de-login.jpeg.ico&quot;,
&quot;Tela-de-login.jpeg&quot;,
&quot;Tela de login.jpeg&quot;,
&quot;Tela de login.jpeg.jpeg&quot;,
&quot;tela_de_login.jpeg&quot;,
]:

if os.path.exists(nome_bg):
bg_login_path = nome_bg
break
b64_img = &quot;&quot;
if bg_login_path:
with open(bg_login_path, &quot;rb&quot;) as img_f:
b64_img = base64.b64encode(img_f.read()).decode()
if b64_img:
css_fundo = f&quot;&quot;&quot;
.stApp {{
background-image: linear-gradient(rgba(10,12,10,0.92), rgba(10,12,10,0.92)),
url(&quot;data:image/jpeg;base64,{b64_img}&quot;) !important;
background-size: cover !important;
background-position: center !important;
background-repeat: no-repeat !important;
background-attachment: fixed !important;
}}
&quot;&quot;&quot;
else:
css_fundo = &quot;&quot;&quot;
.stApp {
background: linear-gradient(135deg, #121417 0%, #1A1D24 100%) !important;
background-attachment: fixed !important;
}
&quot;&quot;&quot;
st.markdown(
f&quot;&quot;&quot;
&lt;style&gt;
footer, div[data-testid=&quot;stToolbar&quot;], div[class*=&quot;viewerBadge&quot;] {{
display: none !important;
visibility: hidden !important;
}}
header[data-testid=&quot;stHeader&quot;] {{
background-color: transparent !important;
}}
h1, h2, h3, h4, h5, h6, p, span, div, label {{
color: #FFFFFF !important;
text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.8) !important;
}}
.stApp label, .stMarkdown, div[data-testid=&quot;stMarkdownContainer&quot;] p {{
font-size: 14px !important;
font-weight: 700 !important;
color: #FFFFFF !important;
}}
div[data-testid=&quot;stRadio&quot;] &gt; div {{
background: transparent !important;
padding: 0px !important;
border: none !important;
box-shadow: none !important;
gap: 12px !important;
flex-wrap: wrap !important;
display: flex !important;
}}

div[data-testid=&quot;stRadio&quot;] label {{
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
div[data-testid=&quot;stRadio&quot;] label:hover {{
background: linear-gradient(135deg, rgba(38, 44, 52, 0.98), rgba(24, 28, 34, 1)) !important;
border-color: rgba(255, 255, 255, 0.35) !important;
transform: translateY(-2px) !important;
}}
div[data-testid=&quot;stRadio&quot;] label[data-checked=&quot;true&quot;] {{
background: linear-gradient(135deg, #2D3748, #1A202C) !important;
border: 1px solid rgba(255, 255, 255, 0.8) !important;
box-shadow: 0px 6px 16px rgba(0, 0, 0, 0.6) !important;
}}
div[data-testid=&quot;stRadio&quot;] label p {{
color: #FFFFFF !important;
font-size: 14px !important;
font-weight: 800 !important;
}}
div[data-testid=&quot;stExpander&quot;] {{
background: rgba(20, 24, 30, 0.9) !important;
border: 1px solid rgba(255, 255, 255, 0.15) !important;
border-radius: 8px !important;
box-shadow: 0px 4px 10px rgba(0,0,0,0.4) !important;
}}
img[data-testid=&quot;stImage&quot;] {{
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
font-family: &#39;Arial Black&#39;, Gadget, sans-serif !important;
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
font-family: &#39;Brush Script MT&#39;, cursive, sans-serif !important;
font-size: 2.5rem !important;
}}
div[data-baseweb=&quot;input&quot;] input,
div[data-baseweb=&quot;base-input&quot;] input,
div[data-testid=&quot;stDateInput&quot;] input,
div[data-baseweb=&quot;select&quot;] input,
textarea {{
color: #111111 !important;
-webkit-text-fill-color: #111111 !important;
background-color: #F8F9FA !important;
font-weight: bold !important;
font-size: 14px !important;
border-radius: 6px !important;
}}
div[data-baseweb=&quot;input&quot;],
div[data-baseweb=&quot;base-input&quot;],
div[data-baseweb=&quot;select&quot;] {{
background-color: #F8F9FA !important;
border-radius: 6px !important;
border: 2px solid #4A5568 !important;
}}
div[data-baseweb=&quot;select&quot;] span {{
color: #111111 !important;
font-weight: bold !important;
}}
div[data-testid=&quot;stFileUploader&quot;],
div[data-testid=&quot;stFileUploader&quot;] section {{
background: rgba(30, 35, 42, 0.85) !important;
border: 2px solid rgba(255, 255, 255, 0.4) !important;
border-radius: 8px !important;
}}
button[kind=&quot;primary&quot;], .stButton &gt; button[kind=&quot;primary&quot;] {{
background-color: #2D3748 !important;
color: #FFFFFF !important;
border: 2px solid #FFFFFF !important;
font-weight: bold !important;
font-size: 15px !important;
border-radius: 8px !important;
width: 100% !important;
box-shadow: 0px 4px 8px rgba(0,0,0,0.5) !important;

}}
button[kind=&quot;primary&quot;]:hover, .stButton &gt; button[kind=&quot;primary&quot;]:hover {{
background-color: #4A5568 !important;
border-color: #FFFFFF !important;
}}
{css_fundo}
&lt;/style&gt;
&quot;&quot;&quot;,
unsafe_allow_html=True,
)
# ---------------------------------------------------------
# 3. BANCO DE DADOS (PERSISTÊNCIA COMPLETA E MIGRAÇÃO)
# ---------------------------------------------------------
def init_db():
conn, db_type = get_db_connection()
cursor = conn.cursor()
if db_type == &quot;postgres&quot;:
cursor.execute(&quot;&quot;&quot;
CREATE TABLE IF NOT EXISTS usuarios (
id SERIAL PRIMARY KEY,
nome VARCHAR(255) NOT NULL,
login VARCHAR(255) UNIQUE NOT NULL,
senha VARCHAR(255) NOT NULL,
perfil VARCHAR(255) NOT NULL
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
CREATE TABLE IF NOT EXISTS produtos (
id SERIAL PRIMARY KEY,
codigo_barras VARCHAR(255),
codigo_produto VARCHAR(255) UNIQUE,
nome VARCHAR(255) UNIQUE NOT NULL,
unidade_padrao VARCHAR(50) NOT NULL
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
CREATE TABLE IF NOT EXISTS fornecedores (
id SERIAL PRIMARY KEY,
codigo_fornecedor VARCHAR(255) UNIQUE,
cnpj VARCHAR(255),
nome VARCHAR(255) UNIQUE NOT NULL
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
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
status_nota VARCHAR(50) DEFAULT &#39;Pendente&#39;,
tipo_operacao VARCHAR(50) DEFAULT &#39;Compra&#39;,
observacoes TEXT,
foto_b64 TEXT,
ass_conf_b64 TEXT,
ass_ent_b64 TEXT
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
CREATE TABLE IF NOT EXISTS romaneio_itens (
id SERIAL PRIMARY KEY,
romaneio_id INTEGER NOT NULL REFERENCES romaneios(id) ON DELETE CASCADE,
produto VARCHAR(255) NOT NULL,
quantidade REAL NOT NULL,
unidade VARCHAR(50) NOT NULL,
valor_unitario REAL,
valor_total REAL
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
CREATE TABLE IF NOT EXISTS bonificacoes (
id SERIAL PRIMARY KEY,
numero_nota VARCHAR(255) NOT NULL,
loja VARCHAR(255) NOT NULL,
data_entrada VARCHAR(50) NOT NULL,
valor_bonificacao REAL NOT NULL,
status VARCHAR(100) NOT NULL,
produto_hortifruti VARCHAR(255) NOT NULL,
caminho_anexo TEXT,
tipo_bonificacao VARCHAR(100) DEFAULT &#39;Bonificação&#39;,
anexo_b64 TEXT
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
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
&quot;&quot;&quot;)
cursor.execute(&quot;ALTER TABLE bonificacoes ADD COLUMN IF NOT EXISTS anexo_b64 TEXT;&quot;)
cursor.execute(&quot;ALTER TABLE romaneios ADD COLUMN IF NOT EXISTS foto_b64 TEXT;&quot;)
cursor.execute(&quot;ALTER TABLE romaneios ADD COLUMN IF NOT EXISTS ass_conf_b64 TEXT;&quot;)
cursor.execute(&quot;ALTER TABLE romaneios ADD COLUMN IF NOT EXISTS ass_ent_b64 TEXT;&quot;)
cursor.execute(&quot;ALTER TABLE baixas_avarias ADD COLUMN IF NOT EXISTS nf_baixa_b64 TEXT;&quot;)
cursor.execute(&quot;SELECT * FROM usuarios WHERE login = %s&quot;, (&#39;908&#39;,))
if not cursor.fetchone():

cursor.execute(&quot;DELETE FROM usuarios WHERE login = %s&quot;, (&#39;admin&#39;,))
cursor.execute(
&quot;INSERT INTO usuarios (nome, login, senha, perfil) VALUES (%s, %s, %s, %s)&quot;,
(&#39;Administrador&#39;, &#39;908&#39;, &#39;0332&#39;, &#39;Gestor&#39;)
)
else:
cursor.execute(&quot;&quot;&quot;
CREATE TABLE IF NOT EXISTS usuarios (
id INTEGER PRIMARY KEY AUTOINCREMENT,
nome TEXT NOT NULL,
login TEXT UNIQUE NOT NULL,
senha TEXT NOT NULL,
perfil TEXT NOT NULL
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
CREATE TABLE IF NOT EXISTS produtos (
id INTEGER PRIMARY KEY AUTOINCREMENT,
codigo_barras TEXT,
codigo_produto TEXT UNIQUE,
nome TEXT UNIQUE NOT NULL,
unidade_padrao TEXT NOT NULL
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
CREATE TABLE IF NOT EXISTS fornecedores (
id INTEGER PRIMARY KEY AUTOINCREMENT,
codigo_fornecedor TEXT UNIQUE,
cnpj TEXT,
nome TEXT UNIQUE NOT NULL
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
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
status_nota TEXT DEFAULT &#39;Pendente&#39;,
tipo_operacao TEXT DEFAULT &#39;Compra&#39;,
observacoes TEXT,
foto_b64 TEXT,
ass_conf_b64 TEXT,
ass_ent_b64 TEXT
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
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
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
CREATE TABLE IF NOT EXISTS bonificacoes (
id INTEGER PRIMARY KEY AUTOINCREMENT,
numero_nota TEXT NOT NULL,
loja TEXT NOT NULL,
data_entrada TEXT NOT NULL,
valor_bonificacao REAL NOT NULL,
status TEXT NOT NULL,
produto_hortifruti TEXT NOT NULL,
caminho_anexo TEXT,
tipo_bonificacao TEXT DEFAULT &#39;Bonificação&#39;,
anexo_b64 TEXT
)
&quot;&quot;&quot;)
cursor.execute(&quot;&quot;&quot;
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
&quot;&quot;&quot;)
try: cursor.execute(&quot;ALTER TABLE bonificacoes ADD COLUMN anexo_b64 TEXT;&quot;)
except Exception: pass
try: cursor.execute(&quot;ALTER TABLE romaneios ADD COLUMN foto_b64 TEXT;&quot;)
except Exception: pass
try: cursor.execute(&quot;ALTER TABLE romaneios ADD COLUMN ass_conf_b64 TEXT;&quot;)
except Exception: pass
try: cursor.execute(&quot;ALTER TABLE romaneios ADD COLUMN ass_ent_b64 TEXT;&quot;)
except Exception: pass
try: cursor.execute(&quot;ALTER TABLE baixas_avarias ADD COLUMN nf_baixa_b64 TEXT;&quot;)
except Exception: pass
cursor.execute(&quot;SELECT * FROM usuarios WHERE login = &#39;908&#39;&quot;)
if not cursor.fetchone():
cursor.execute(&quot;DELETE FROM usuarios WHERE login = &#39;admin&#39;&quot;)
cursor.execute(
&quot;INSERT INTO usuarios (nome, login, senha, perfil) VALUES (&#39;Administrador&#39;, &#39;908&#39;, &#39;0332&#39;,
&#39;Gestor&#39;)&quot;
)
conn.commit()

conn.close()
init_db()
if &quot;usuario_logado&quot; not in st.session_state:
st.session_state[&quot;usuario_logado&quot;] = None
def fazer_login(login_ou_nome, senha):
conn, db_type = get_db_connection()
cursor = conn.cursor()
if db_type == &quot;postgres&quot;:
cursor.execute(
&quot;SELECT id, nome, perfil, login FROM usuarios WHERE (login = %s OR LOWER(nome) = LOWER(%s)) AND
senha = %s&quot;,
(login_ou_nome.strip(), login_ou_nome.strip(), senha),
)
else:
cursor.execute(
&quot;SELECT id, nome, perfil, login FROM usuarios WHERE (login = ? OR nome COLLATE NOCASE = ?) AND
senha = ?&quot;,
(login_ou_nome.strip(), login_ou_nome.strip(), senha),
)
usr = cursor.fetchone()
conn.close()
return usr
def fmt_ptbr(val, decimais=2):
try:
f = float(val)
s = f&quot;{f:,.3f}&quot; if decimais == 3 else f&quot;{f:,.2f}&quot;
return s.replace(&quot;,&quot;, &quot;X&quot;).replace(&quot;.&quot;, &quot;,&quot;).replace(&quot;X&quot;, &quot;.&quot;)
except Exception:
return &quot;0,00&quot;
def remover_fundo_branco(caminho_imagem):
if not caminho_imagem or not os.path.exists(caminho_imagem):
return caminho_imagem
try:
img = Image.open(caminho_imagem).convert(&quot;RGBA&quot;)
datas = img.getdata()
newData = []
for item in datas:
if item[0] &gt; 200 and item[1] &gt; 200 and item[2] &gt; 200:
newData.append((255, 255, 255, 0))
else:
newData.append(item)
img.putdata(newData)
caminho_transparente = caminho_imagem.replace(&quot;.png&quot;, &quot;_transp.png&quot;)
img.save(caminho_transparente, &quot;PNG&quot;)
return caminho_transparente
except Exception:
return caminho_imagem
# ---------------------------------------------------------
# GERADORES DE PDF
# ---------------------------------------------------------
def gerar_pdf_romaneio(romaneio_data, itens_data, path_conf=None, path_ent=None):
buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30,
bottomMargin=30)

story = []
styles = getSampleStyleSheet()
style_left = ParagraphStyle(&#39;Left&#39;, parent=styles[&#39;Normal&#39;], alignment=0, fontName=&#39;Helvetica&#39;,
fontSize=9)
style_center = ParagraphStyle(&#39;Center&#39;, parent=styles[&#39;Normal&#39;], alignment=1, fontName=&#39;Helvetica&#39;,
fontSize=9)
style_header_left = ParagraphStyle(&#39;HLeft&#39;, parent=styles[&#39;Normal&#39;], alignment=0, fontName=&#39;Helvetica-
Bold&#39;, fontSize=9, textColor=colors.whitesmoke)
style_header_center = ParagraphStyle(&#39;HCenter&#39;, parent=styles[&#39;Normal&#39;], alignment=1,
fontName=&#39;Helvetica-Bold&#39;, fontSize=9, textColor=colors.whitesmoke)
logo_path = None
for ext in [&quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;, &quot;PNG&quot;, &quot;JPG&quot;, &quot;JPEG&quot;]:
for prefixo in [&quot;logo_romaneio.png&quot;, &quot;logo_romaneio&quot;, &quot;logo&quot;, &quot;Tela de login&quot;, &quot;tela_de_login&quot;]:
pos_p = f&quot;{prefixo}.{ext}&quot; if not prefixo.endswith(f&quot;.{ext}&quot;) else prefixo
if os.path.exists(pos_p):
logo_path = pos_p
break
if logo_path:
break
if logo_path and os.path.exists(logo_path):
logo_img_header = RLImage(logo_path, width=70, height=50)
else:
logo_img_header = Paragraph(&quot;&lt;b&gt;SUPERNOVA&lt;br/&gt;CIDADE&lt;/b&gt;&quot;, styles[&quot;Normal&quot;])
tipo_op_pdf = romaneio_data.get(&#39;tipo_operacao&#39;, &#39;Compra&#39;)
header_table = Table([[logo_img_header, Paragraph(f&quot;&lt;b&gt;SUPERMERCADO SUPERNOVA CIDADE&lt;/b&gt;&lt;br/&gt;HortiControl
- Romaneio de Recebimento ({tipo_op_pdf.upper()})&quot;, styles[&quot;Normal&quot;]), Paragraph(f&quot;&lt;b&gt;ROM:&lt;/b&gt;
{romaneio_data[&#39;numero_romaneio&#39;]}&lt;br/&gt;&lt;b&gt;Data:&lt;/b&gt; {romaneio_data[&#39;data_recebimento&#39;]}&quot;,
styles[&quot;Normal&quot;])]], colWidths=[80, 300, 160])
header_table.setStyle(TableStyle([(&quot;VALIGN&quot;, (0, 0), (-1, -1), &quot;MIDDLE&quot;), (&quot;ALIGN&quot;, (0, 0), (0, 0),
&quot;CENTER&quot;), (&quot;GRID&quot;, (0, 0), (-1, -1), 0.5, colors.grey), (&quot;BACKGROUND&quot;, (0, 0), (-1, -1),
colors.lightgrey)]))
story.append(header_table)
story.append(Spacer(1, 10))
loja_txt_pdf = romaneio_data.get(&#39;loja&#39;, &#39;&#39;)
if tipo_op_pdf.lower() in [&#39;transferência&#39;, &#39;transferência/bonificação&#39;]:
loja_txt_pdf = f&quot;Origem: {romaneio_data.get(&#39;loja_origem&#39;, &#39;&#39;)} -&gt; Destino:
{romaneio_data.get(&#39;loja_destino&#39;, &#39;&#39;)}&quot;
info_data = [
[Paragraph(f&quot;&lt;b&gt;Tipo de Operação:&lt;/b&gt; {tipo_op_pdf}&quot;, styles[&quot;Normal&quot;]),
Paragraph(f&quot;&lt;b&gt;Fornecedor:&lt;/b&gt; {romaneio_data.get(&#39;fornecedor&#39;,&#39;&#39;)}&quot;, styles[&quot;Normal&quot;])],
[Paragraph(f&quot;&lt;b&gt;Cód. Fornecedor:&lt;/b&gt; {romaneio_data.get(&#39;codigo_fornecedor&#39;,&#39;&#39;)}&quot;, styles[&quot;Normal&quot;]),
Paragraph(f&quot;&lt;b&gt;Telefone:&lt;/b&gt; {romaneio_data.get(&#39;telefone_fornecedor&#39;,&#39;&#39;)}&quot;, styles[&quot;Normal&quot;])],
[Paragraph(f&quot;&lt;b&gt;Loja / Rota:&lt;/b&gt; {loja_txt_pdf}&quot;, styles[&quot;Normal&quot;]), Paragraph(f&quot;&lt;b&gt;Conferente:&lt;/b&gt;
{romaneio_data.get(&#39;conferente&#39;,&#39;&#39;)}&quot;, styles[&quot;Normal&quot;])],
[Paragraph(f&quot;&lt;b&gt;Pagamento à Vista:&lt;/b&gt; {romaneio_data.get(&#39;pagamento_a_vista&#39;,&#39;&#39;)}&quot;,
styles[&quot;Normal&quot;]), Paragraph(f&quot;&lt;b&gt;Data Pagamento:&lt;/b&gt; {romaneio_data.get(&#39;data_pagamento&#39;,&#39;&#39;)}&quot; if
romaneio_data.get(&quot;pagamento_a_vista&quot;) == &quot;NÃO&quot; else &quot;&quot;, styles[&quot;Normal&quot;])],
]
info_table = Table(info_data, colWidths=[270, 270])
info_table.setStyle(TableStyle([(&quot;GRID&quot;, (0, 0), (-1, -1), 0.5, colors.grey), (&quot;VALIGN&quot;, (0, 0), (-1, -
1), &quot;MIDDLE&quot;), (&quot;BACKGROUND&quot;, (0, 0), (-1, -1), colors.whitesmoke)]))
story.append(info_table)
if romaneio_data.get(&#39;observacoes&#39;):

story.append(Spacer(1, 8))
obs_table = Table([[Paragraph(f&quot;&lt;b&gt;Informações Adicionais /
Observações:&lt;/b&gt;&lt;br/&gt;{romaneio_data.get(&#39;observacoes&#39;)}&quot;, styles[&quot;Normal&quot;])]], colWidths=[540])
obs_table.setStyle(TableStyle([(&quot;GRID&quot;, (0, 0), (-1, -1), 0.5, colors.grey), (&quot;BACKGROUND&quot;, (0, 0),
(-1, -1), colors.whitesmoke), (&quot;BOTTOMPADDING&quot;, (0, 0), (-1, -1), 6)]))
story.append(obs_table)
story.append(Spacer(1, 15))
table_content = [[Paragraph(&quot;Item&quot;, style_header_center), Paragraph(&quot;Descrição do Produto&quot;,
style_header_left), Paragraph(&quot;Qtd / Peso&quot;, style_header_center), Paragraph(&quot;UND&quot;, style_header_center),
Paragraph(&quot;Vl. Unit&quot;, style_header_left), Paragraph(&quot;Total&quot;, style_header_left)]]
total_geral = 0.0
for idx, item in enumerate(itens_data, 1):
v_unit = float(item[4]) if len(item) &gt; 4 and item[4] is not None else 0.0
v_tot = float(item[5]) if len(item) &gt; 5 and item[5] is not None else 0.0
qtd_val = float(item[2]) if len(item) &gt; 2 and item[2] is not None else 0.0
total_geral += v_tot
table_content.append([Paragraph(str(idx), style_center), Paragraph(str(item[1]), style_left),
Paragraph(fmt_ptbr(qtd_val, 3), style_center), Paragraph(str(item[3]), style_center), Paragraph(f&quot;R$
{fmt_ptbr(v_unit, 2)}&quot;, style_left), Paragraph(f&quot;R$ {fmt_ptbr(v_tot, 2)}&quot;, style_left)])
itens_table = Table(table_content, colWidths=[35, 215, 75, 50, 75, 90])
itens_table.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0, 0), (-1, 0), colors.HexColor(&quot;#2D3748&quot;)), (&quot;VALIGN&quot;,
(0, 0), (-1, -1), &quot;MIDDLE&quot;), (&quot;BOTTOMPADDING&quot;, (0, 0), (-1, -1), 5), (&quot;GRID&quot;, (0, 0), (-1, -1), 0.5,
colors.grey)]))
story.append(itens_table)
story.append(Spacer(1, 8))
total_table = Table([[f&quot;TOTAL GERAL DO ROMANEIO: R$ {fmt_ptbr(total_geral, 2)}&quot;]], colWidths=[540])
total_table.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0, 0), (-1, -1), colors.HexColor(&quot;#1A202C&quot;)),
(&quot;TEXTCOLOR&quot;, (0, 0), (-1, -1), colors.whitesmoke), (&quot;ALIGN&quot;, (0, 0), (-1, -1), &quot;RIGHT&quot;), (&quot;FONTNAME&quot;, (0,
0), (-1, -1), &quot;Helvetica-Bold&quot;), (&quot;FONTSIZE&quot;, (0, 0), (-1, -1), 10), (&quot;BOTTOMPADDING&quot;, (0, 0), (-1, -1),
6)]))
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
col_conf_cell = [img_conf_pdf if img_conf_pdf else Spacer(1, 45), Paragraph(f&quot;&lt;b&gt;Assinatura do
Conferente:&lt;/b&gt;&lt;br/&gt;{romaneio_data.get(&#39;conferente&#39;,&#39;&#39;)}&quot;, styles[&quot;Normal&quot;])]
col_ent_cell = [img_ent_pdf if img_ent_pdf else Spacer(1, 45), Paragraph(f&quot;&lt;b&gt;Assinatura do Entregador /
Fornecedor:&lt;/b&gt;&lt;br/&gt;{romaneio_data.get(&#39;fornecedor&#39;,&#39;&#39;)}&quot;, styles[&quot;Normal&quot;])]
ass_table = Table([[col_conf_cell, col_ent_cell]], colWidths=[270, 270])
ass_table.setStyle(TableStyle([(&quot;GRID&quot;, (0, 0), (-1, -1), 0.5, colors.grey), (&quot;VALIGN&quot;, (0, 0), (-1, -1),
&quot;BOTTOM&quot;), (&quot;ALIGN&quot;, (0, 0), (-1, -1), &quot;CENTER&quot;), (&quot;BOTTOMPADDING&quot;, (0, 0), (-1, -1), 8)]))
story.append(ass_table)
doc.build(story)
buffer.seek(0)

return buffer
def gerar_pdf_produtos(produtos_data):
buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30,
bottomMargin=30)
story = []
styles = getSampleStyleSheet()
style_left = ParagraphStyle(&#39;Left&#39;, parent=styles[&#39;Normal&#39;], alignment=0, fontName=&#39;Helvetica&#39;,
fontSize=9)
style_center = ParagraphStyle(&#39;Center&#39;, parent=styles[&#39;Normal&#39;], alignment=1, fontName=&#39;Helvetica&#39;,
fontSize=9)
style_header_left = ParagraphStyle(&#39;HLeft&#39;, parent=styles[&#39;Normal&#39;], alignment=0, fontName=&#39;Helvetica-
Bold&#39;, fontSize=9, textColor=colors.whitesmoke)
style_header_center = ParagraphStyle(&#39;HCenter&#39;, parent=styles[&#39;Normal&#39;], alignment=1,
fontName=&#39;Helvetica-Bold&#39;, fontSize=9, textColor=colors.whitesmoke)
logo_path = None
for ext in [&quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;, &quot;PNG&quot;, &quot;JPG&quot;, &quot;JPEG&quot;]:
for prefixo in [&quot;logo_romaneio.png&quot;, &quot;logo_romaneio&quot;, &quot;logo&quot;, &quot;Tela de login&quot;, &quot;tela_de_login&quot;]:
pos_p = f&quot;{prefixo}.{ext}&quot; if not prefixo.endswith(f&quot;.{ext}&quot;) else prefixo
if os.path.exists(pos_p):
logo_path = pos_p
break
if logo_path:
break
if logo_path and os.path.exists(logo_path):
logo_img_header = RLImage(logo_path, width=70, height=50)
else:
logo_img_header = Paragraph(&quot;&lt;b&gt;SUPERNOVA&lt;br/&gt;CIDADE&lt;/b&gt;&quot;, styles[&quot;Normal&quot;])
header_table = Table([[logo_img_header, Paragraph(&quot;&lt;b&gt;SUPERMERCADO SUPERNOVA CIDADE&lt;/b&gt;&lt;br/&gt;HortiControl
- Relatório de Produtos Cadastrados&quot;, styles[&quot;Normal&quot;]), Paragraph(f&quot;&lt;b&gt;Data:&lt;/b&gt;
{datetime.now(ZoneInfo(&#39;America/Manaus&#39;)).strftime(&#39;%d/%m/%Y&#39;)}&lt;br/&gt;&lt;b&gt;Total:&lt;/b&gt; {len(produtos_data)}&quot;,
styles[&quot;Normal&quot;])]], colWidths=[80, 310, 150])
header_table.setStyle(TableStyle([(&quot;VALIGN&quot;, (0, 0), (-1, -1), &quot;MIDDLE&quot;), (&quot;ALIGN&quot;, (0, 0), (0, 0),
&quot;CENTER&quot;), (&quot;GRID&quot;, (0, 0), (-1, -1), 0.5, colors.grey), (&quot;BACKGROUND&quot;, (0, 0), (-1, -1),
colors.lightgrey)]))
story.append(header_table)
story.append(Spacer(1, 15))
table_content = [[Paragraph(&quot;Item&quot;, style_header_center), Paragraph(&quot;Cód. Produto&quot;, style_header_center),
Paragraph(&quot;Código de Barras&quot;, style_header_center), Paragraph(&quot;Nome do Produto&quot;, style_header_left),
Paragraph(&quot;UND&quot;, style_header_center)]]
for idx, p in enumerate(produtos_data, 1):
table_content.append([Paragraph(str(idx), style_center), Paragraph(str(p[2] or &quot;S/N&quot;), style_center),
Paragraph(str(p[1] or &quot;S/N&quot;), style_center), Paragraph(str(p[3]), style_left), Paragraph(str(p[4]),
style_center)])
prod_table = Table(table_content, colWidths=[35, 95, 125, 235, 50])
prod_table.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0, 0), (-1, 0), colors.HexColor(&quot;#2D3748&quot;)), (&quot;VALIGN&quot;,
(0, 0), (-1, -1), &quot;MIDDLE&quot;), (&quot;BOTTOMPADDING&quot;, (0, 0), (-1, -1), 5), (&quot;GRID&quot;, (0, 0), (-1, -1), 0.5,
colors.grey)]))
story.append(prod_table)
doc.build(story)
buffer.seek(0)
return buffer

def gerar_pdf_bonificacoes(df_bonf_data):
buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30,
bottomMargin=30)
story = []
styles = getSampleStyleSheet()
style_left = ParagraphStyle(&#39;Left&#39;, parent=styles[&#39;Normal&#39;], alignment=0, fontName=&#39;Helvetica&#39;,
fontSize=8)
style_center = ParagraphStyle(&#39;Center&#39;, parent=styles[&#39;Normal&#39;], alignment=1, fontName=&#39;Helvetica&#39;,
fontSize=8)
style_header_left = ParagraphStyle(&#39;HLeft&#39;, parent=styles[&#39;Normal&#39;], alignment=0, fontName=&#39;Helvetica-
Bold&#39;, fontSize=8, textColor=colors.whitesmoke)
style_header_center = ParagraphStyle(&#39;HCenter&#39;, parent=styles[&#39;Normal&#39;], alignment=1,
fontName=&#39;Helvetica-Bold&#39;, fontSize=8, textColor=colors.whitesmoke)
logo_path = None
for ext in [&quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;, &quot;PNG&quot;, &quot;JPG&quot;, &quot;JPEG&quot;]:
for prefixo in [&quot;logo_romaneio.png&quot;, &quot;logo_romaneio&quot;, &quot;logo&quot;, &quot;Tela de login&quot;]:
pos_p = f&quot;{prefixo}.{ext}&quot; if not prefixo.endswith(f&quot;.{ext}&quot;) else prefixo
if os.path.exists(pos_p):
logo_path = pos_p
break
if logo_path: break
logo_img_header = RLImage(logo_path, width=70, height=50) if logo_path and os.path.exists(logo_path) else
Paragraph(&quot;&lt;b&gt;SUPERNOVA&lt;br/&gt;CIDADE&lt;/b&gt;&quot;, styles[&quot;Normal&quot;])
header_table = Table([[logo_img_header, Paragraph(&quot;&lt;b&gt;SUPERMERCADO SUPERNOVA CIDADE&lt;/b&gt;&lt;br/&gt;HortiControl
- Relatório de Controle de Bonificação&quot;, styles[&quot;Normal&quot;]), Paragraph(f&quot;&lt;b&gt;Data Emissão:&lt;/b&gt;
{datetime.now(ZoneInfo(&#39;America/Manaus&#39;)).strftime(&#39;%d/%m/%Y %H:%M&#39;)}&lt;br/&gt;&lt;b&gt;Total Registros:&lt;/b&gt;
{len(df_bonf_data)}&quot;, styles[&quot;Normal&quot;])]], colWidths=[80, 310, 150])
header_table.setStyle(TableStyle([(&quot;VALIGN&quot;, (0, 0), (-1, -1), &quot;MIDDLE&quot;), (&quot;GRID&quot;, (0, 0), (-1, -1), 0.5,
colors.grey), (&quot;BACKGROUND&quot;, (0, 0), (-1, -1), colors.lightgrey)]))
story.append(header_table)
story.append(Spacer(1, 15))
table_content = [[Paragraph(&quot;N° Nota&quot;, style_header_center), Paragraph(&quot;Tipo&quot;, style_header_center),
Paragraph(&quot;Loja&quot;, style_header_center), Paragraph(&quot;Data Entrada&quot;, style_header_center), Paragraph(&quot;Valor
(R$)&quot;, style_header_left), Paragraph(&quot;Status&quot;, style_header_center), Paragraph(&quot;Produto Hortifrúti&quot;,
style_header_left)]]
tot_val = 0.0
for _, r in df_bonf_data.iterrows():
v_b = float(r[&quot;valor_bonificacao&quot;]) if r[&quot;valor_bonificacao&quot;] else 0.0
tot_val += v_b
t_bonf = r.get(&quot;tipo_bonificacao&quot;, &quot;Bonificação&quot;)
table_content.append([Paragraph(str(r[&quot;numero_nota&quot;]), style_center), Paragraph(str(t_bonf),
style_center), Paragraph(str(r[&quot;loja&quot;]), style_center), Paragraph(str(r[&quot;data_entrada&quot;]), style_center),
Paragraph(f&quot;R$ {fmt_ptbr(v_b, 2)}&quot;, style_left), Paragraph(str(r[&quot;status&quot;]), style_center),
Paragraph(str(r[&quot;produto_hortifruti&quot;]), style_left)])
bonf_table = Table(table_content, colWidths=[55, 65, 65, 85, 70, 80, 120])
bonf_table.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0, 0), (-1, 0), colors.HexColor(&quot;#2D3748&quot;)), (&quot;VALIGN&quot;,
(0, 0), (-1, -1), &quot;MIDDLE&quot;), (&quot;GRID&quot;, (0, 0), (-1, -1), 0.5, colors.grey)]))
story.append(bonf_table)
story.append(Spacer(1, 10))
total_table = Table([[f&quot;VALOR TOTAL BONIFICADO / TRANSFERIDO: R$ {fmt_ptbr(tot_val, 2)}&quot;]],
colWidths=[540])
total_table.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0, 0), (-1, -1), colors.HexColor(&quot;#1A202C&quot;)),

(&quot;TEXTCOLOR&quot;, (0, 0), (-1, -1), colors.whitesmoke), (&quot;ALIGN&quot;, (0, 0), (-1, -1), &quot;RIGHT&quot;), (&quot;FONTNAME&quot;, (0,
0), (-1, -1), &quot;Helvetica-Bold&quot;), (&quot;FONTSIZE&quot;, (0, 0), (-1, -1), 9)]))
story.append(total_table)
doc.build(story)
buffer.seek(0)
return buffer
def gerar_pdf_baixas(df_baixas_data):
buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=25, leftMargin=25, topMargin=25,
bottomMargin=25)
story = []
styles = getSampleStyleSheet()
style_left = ParagraphStyle(&#39;Left&#39;, parent=styles[&#39;Normal&#39;], alignment=0, fontName=&#39;Helvetica&#39;,
fontSize=8)
style_center = ParagraphStyle(&#39;Center&#39;, parent=styles[&#39;Normal&#39;], alignment=1, fontName=&#39;Helvetica&#39;,
fontSize=8)
style_header_left = ParagraphStyle(&#39;HLeft&#39;, parent=styles[&#39;Normal&#39;], alignment=0, fontName=&#39;Helvetica-
Bold&#39;, fontSize=8, textColor=colors.whitesmoke)
style_header_center = ParagraphStyle(&#39;HCenter&#39;, parent=styles[&#39;Normal&#39;], alignment=1,
fontName=&#39;Helvetica-Bold&#39;, fontSize=8, textColor=colors.whitesmoke)
logo_path = None
for ext in [&quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;, &quot;PNG&quot;, &quot;JPG&quot;, &quot;JPEG&quot;]:
for prefixo in [&quot;logo_romaneio.png&quot;, &quot;logo_romaneio&quot;, &quot;logo&quot;, &quot;Tela de login&quot;]:
pos_p = f&quot;{prefixo}.{ext}&quot; if not prefixo.endswith(f&quot;.{ext}&quot;) else prefixo
if os.path.exists(pos_p):
logo_path = pos_p
break
if logo_path: break
logo_img_header = RLImage(logo_path, width=70, height=45) if logo_path and os.path.exists(logo_path) else
Paragraph(&quot;&lt;b&gt;SUPERNOVA&lt;br/&gt;CIDADE&lt;/b&gt;&quot;, styles[&quot;Normal&quot;])
header_table = Table([[logo_img_header, Paragraph(&quot;&lt;b&gt;SUPERMERCADO SUPERNOVA CIDADE&lt;/b&gt;&lt;br/&gt;HortiControl
- Registro de Baixas de Avarias&quot;, styles[&quot;Normal&quot;]), Paragraph(f&quot;&lt;b&gt;Data Emissão:&lt;/b&gt;
{datetime.now(ZoneInfo(&#39;America/Manaus&#39;)).strftime(&#39;%d/%m/%Y %H:%M&#39;)}&lt;br/&gt;&lt;b&gt;Total Registros:&lt;/b&gt;
{len(df_baixas_data)}&quot;, styles[&quot;Normal&quot;])]], colWidths=[80, 520, 192])
header_table.setStyle(TableStyle([(&quot;VALIGN&quot;, (0, 0), (-1, -1), &quot;MIDDLE&quot;), (&quot;GRID&quot;, (0, 0), (-1, -1), 0.5,
colors.grey), (&quot;BACKGROUND&quot;, (0, 0), (-1, -1), colors.lightgrey)]))
story.append(header_table)
story.append(Spacer(1, 12))
table_content = [[
Paragraph(&quot;LOJAS&quot;, style_header_center),
Paragraph(&quot;Data Baixa&quot;, style_header_center),
Paragraph(&quot;Ref. Bon. transferen&quot;, style_header_center),
Paragraph(&quot;NF da baixa&quot;, style_header_center),
Paragraph(&quot;NF de B. ENTRADA&quot;, style_header_center),
Paragraph(&quot;Produto Hortifrúti&quot;, style_header_left),
Paragraph(&quot;Qtd (kg/cx)&quot;, style_header_center),
Paragraph(&quot;Valor Total Avaria (R$)&quot;, style_header_left),
Paragraph(&quot;Saldo&quot;, style_header_left),
Paragraph(&quot;Saldo Total Utilizado&quot;, style_header_left)
]]
tot_val_avarias = 0.0
for _, r in df_baixas_data.iterrows():
v_av = float(r[&quot;valor_total_avaria&quot;]) if r[&quot;valor_total_avaria&quot;] else 0.0
tot_val_avarias += v_av

s_nota = float(r[&quot;saldo_restante_nota&quot;]) if r[&quot;saldo_restante_nota&quot;] else 0.0
s_util = float(r.get(&quot;saldo_total_utilizado&quot;, 0.0))
qtd_val = float(r[&quot;quantidade_kg_cx&quot;]) if r[&quot;quantidade_kg_cx&quot;] else 0.0
table_content.append([
Paragraph(str(r[&quot;loja_baixa&quot;]), style_center),
Paragraph(str(r[&quot;data_baixa&quot;]), style_center),
Paragraph(str(r[&quot;ref_bon_transferen&quot;]), style_center),
Paragraph(str(r[&quot;nf_baixa&quot;] if r[&quot;nf_baixa&quot;] else &quot;S/Anexo&quot;), style_center),
Paragraph(str(r[&quot;nf_b_entrada&quot;]), style_center),
Paragraph(str(r[&quot;produto_hortifruti&quot;]), style_left),
Paragraph(fmt_ptbr(qtd_val, 3), style_center),
Paragraph(f&quot;R$ {fmt_ptbr(v_av, 2)}&quot;, style_left),
Paragraph(f&quot;R$ {fmt_ptbr(s_nota, 2)}&quot;, style_left),
Paragraph(f&quot;R$ {fmt_ptbr(s_util, 2)}&quot;, style_left),
])
baixas_table = Table(table_content, colWidths=[70, 95, 85, 75, 85, 120, 60, 85, 65, 52])
baixas_table.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0, 0), (-1, 0), colors.HexColor(&quot;#2D3748&quot;)), (&quot;VALIGN&quot;,
(0, 0), (-1, -1), &quot;MIDDLE&quot;), (&quot;GRID&quot;, (0, 0), (-1, -1), 0.5, colors.grey)]))
story.append(baixas_table)
story.append(Spacer(1, 10))
total_table = Table([[f&quot;VALOR TOTAL DAS AVARIAS: R$ {fmt_ptbr(tot_val_avarias, 2)}&quot;]], colWidths=[792])
total_table.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0, 0), (-1, -1), colors.HexColor(&quot;#1A202C&quot;)),
(&quot;TEXTCOLOR&quot;, (0, 0), (-1, -1), colors.whitesmoke), (&quot;ALIGN&quot;, (0, 0), (-1, -1), &quot;RIGHT&quot;), (&quot;FONTNAME&quot;, (0,
0), (-1, -1), &quot;Helvetica-Bold&quot;), (&quot;FONTSIZE&quot;, (0, 0), (-1, -1), 9)]))
story.append(total_table)
doc.build(story)
buffer.seek(0)
return buffer
def gerar_pdf_relatorio_gerencial_bi(metrics_dict, df_bonf_sub, df_baixas_sub):
buffer = io.BytesIO()
doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=25, leftMargin=25, topMargin=25,
bottomMargin=25)
story = []
styles = getSampleStyleSheet()
style_left = ParagraphStyle(&#39;Left&#39;, parent=styles[&#39;Normal&#39;], alignment=0, fontName=&#39;Helvetica&#39;,
fontSize=8)
style_center = ParagraphStyle(&#39;Center&#39;, parent=styles[&#39;Normal&#39;], alignment=1, fontName=&#39;Helvetica&#39;,
fontSize=8)
style_header_center = ParagraphStyle(&#39;HCenter&#39;, parent=styles[&#39;Normal&#39;], alignment=1,
fontName=&#39;Helvetica-Bold&#39;, fontSize=8, textColor=colors.whitesmoke)
logo_path = None
for ext in [&quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;, &quot;PNG&quot;, &quot;JPG&quot;, &quot;JPEG&quot;]:
for prefixo in [&quot;logo_romaneio.png&quot;, &quot;logo_romaneio&quot;, &quot;logo&quot;, &quot;Tela de login&quot;]:
pos_p = f&quot;{prefixo}.{ext}&quot; if not prefixo.endswith(f&quot;.{ext}&quot;) else prefixo
if os.path.exists(pos_p):
logo_path = pos_p
break
if logo_path: break
logo_img = RLImage(logo_path, width=65, height=40) if logo_path and os.path.exists(logo_path) else
Paragraph(&quot;&lt;b&gt;SUPERNOVA&lt;/b&gt;&quot;, styles[&quot;Normal&quot;])
header = Table([[logo_img, Paragraph(&quot;&lt;b&gt;SUPERMERCADO SUPERNOVA CIDADE&lt;/b&gt;&lt;br/&gt;Relatório Gerencial de
Bonificações, Transferências e Prevenção de Perdas (BI)&quot;, styles[&quot;Normal&quot;]), Paragraph(f&quot;&lt;b&gt;Emissão:&lt;/b&gt;

{datetime.now(ZoneInfo(&#39;America/Manaus&#39;)).strftime(&#39;%d/%m/%Y %H:%M&#39;)}&quot;, styles[&quot;Normal&quot;])]], colWidths=[75,
530, 187])
header.setStyle(TableStyle([(&quot;VALIGN&quot;, (0,0), (-1,-1), &quot;MIDDLE&quot;), (&quot;GRID&quot;, (0,0), (-1,-1), 0.5,
colors.grey), (&quot;BACKGROUND&quot;, (0,0), (-1,-1), colors.lightgrey)]))
story.append(header)
story.append(Spacer(1, 10))
kpi_summary = [
[Paragraph(&quot;&lt;b&gt;Tot. Bonificado (R$)&lt;/b&gt;&quot;, style_header_center), Paragraph(&quot;&lt;b&gt;Tot. Transferido
(R$)&lt;/b&gt;&quot;, style_header_center), Paragraph(&quot;&lt;b&gt;Avarias Bonificadas / Salvas (R$)&lt;/b&gt;&quot;, style_header_center),
Paragraph(&quot;&lt;b&gt;Taxa Cobertura (%)&lt;/b&gt;&quot;, style_header_center), Paragraph(&quot;&lt;b&gt;Saldo Remanescente (R$)&lt;/b&gt;&quot;,
style_header_center)],
[
Paragraph(f&quot;R$ {fmt_ptbr(metrics_dict[&#39;tot_bonf&#39;], 2)}&quot;, style_center),
Paragraph(f&quot;R$ {fmt_ptbr(metrics_dict[&#39;tot_transf&#39;], 2)}&quot;, style_center),
Paragraph(f&quot;R$ {fmt_ptbr(metrics_dict[&#39;tot_avaria&#39;], 2)}&quot;, style_center),
Paragraph(f&quot;{fmt_ptbr(metrics_dict[&#39;taxa_cobertura&#39;], 2)}%&quot;, style_center),
Paragraph(f&quot;R$ {fmt_ptbr(metrics_dict[&#39;saldo_restante&#39;], 2)}&quot;, style_center),
]
]
t_kpi = Table(kpi_summary, colWidths=[158, 158, 160, 158, 158])
t_kpi.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0,0), (-1,0), colors.HexColor(&quot;#1A202C&quot;)), (&quot;GRID&quot;, (0,0), (-
1,-1), 0.5, colors.grey), (&quot;VALIGN&quot;, (0,0), (-1,-1), &quot;MIDDLE&quot;)]))
story.append(t_kpi)
story.append(Spacer(1, 12))
story.append(Paragraph(&quot;&lt;b&gt;1. Resumo Analítico de Entradas e Bonificações Filtradas&lt;/b&gt;&quot;,
styles[&quot;Heading3&quot;]))
tb_b = [[Paragraph(&quot;N° Nota&quot;, style_header_center), Paragraph(&quot;Tipo&quot;, style_header_center),
Paragraph(&quot;Loja&quot;, style_header_center), Paragraph(&quot;Data&quot;, style_header_center), Paragraph(&quot;Valor (R$)&quot;,
style_header_center), Paragraph(&quot;Status&quot;, style_header_center), Paragraph(&quot;Produto&quot;, style_header_center)]]
for _, r in df_bonf_sub.head(15).iterrows():
tb_b.append([
Paragraph(str(r[&quot;numero_nota&quot;]), style_center),
Paragraph(str(r.get(&quot;tipo_bonificacao&quot;, &quot;Bonificação&quot;)), style_center),
Paragraph(str(r[&quot;loja&quot;]), style_center),
Paragraph(str(r[&quot;data_entrada&quot;]), style_center),
Paragraph(f&quot;R$ {fmt_ptbr(r[&#39;valor_bonificacao&#39;], 2)}&quot;, style_center),
Paragraph(str(r[&quot;status&quot;]), style_center),
Paragraph(str(r[&quot;produto_hortifruti&quot;]), style_left)
])
table_b = Table(tb_b, colWidths=[65, 95, 95, 95, 80, 90, 272])
table_b.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0,0), (-1,0), colors.HexColor(&quot;#2D3748&quot;)), (&quot;GRID&quot;, (0,0),
(-1,-1), 0.5, colors.grey), (&quot;VALIGN&quot;, (0,0), (-1,-1), &quot;MIDDLE&quot;)]))
story.append(table_b)
story.append(Spacer(1, 12))
story.append(Paragraph(&quot;&lt;b&gt;2. Resumo de Baixas de Avarias Compensadas (Evitando Perdas Físicas e
Financeiras)&lt;/b&gt;&quot;, styles[&quot;Heading3&quot;]))
tb_bx = [[Paragraph(&quot;Loja&quot;, style_header_center), Paragraph(&quot;Data&quot;, style_header_center), Paragraph(&quot;Ref.
Bon.&quot;, style_header_center), Paragraph(&quot;NF Ent.&quot;, style_header_center), Paragraph(&quot;Produto&quot;,
style_header_center), Paragraph(&quot;Qtd (kg/cx)&quot;, style_header_center), Paragraph(&quot;Valor Avaria (R$)&quot;,
style_header_center)]]
for _, r in df_baixas_sub.head(15).iterrows():
tb_bx.append([
Paragraph(str(r[&quot;loja_baixa&quot;]), style_center),
Paragraph(str(r[&quot;data_baixa&quot;]), style_center),
Paragraph(str(r[&quot;ref_bon_transferen&quot;]), style_center),
Paragraph(str(r[&quot;nf_b_entrada&quot;]), style_center),
Paragraph(str(r[&quot;produto_hortifruti&quot;]), style_left),

Paragraph(fmt_ptbr(r[&quot;quantidade_kg_cx&quot;], 3), style_center),
Paragraph(f&quot;R$ {fmt_ptbr(r[&#39;valor_total_avaria&#39;], 2)}&quot;, style_center)
])
table_bx = Table(tb_bx, colWidths=[90, 95, 90, 80, 237, 80, 120])
table_bx.setStyle(TableStyle([(&quot;BACKGROUND&quot;, (0,0), (-1,0), colors.HexColor(&quot;#2D3748&quot;)), (&quot;GRID&quot;, (0,0),
(-1,-1), 0.5, colors.grey), (&quot;VALIGN&quot;, (0,0), (-1,-1), &quot;MIDDLE&quot;)]))
story.append(table_bx)
doc.build(story)
buffer.seek(0)
return buffer
# ---------------------------------------------------------
# 4. TELA DE LOGIN
# ---------------------------------------------------------
if &quot;usuario_logado&quot; not in st.session_state:
st.session_state[&quot;usuario_logado&quot;] = None
if st.session_state[&quot;usuario_logado&quot;] is None:
logo_display = None
for nome in [&quot;logo_romaneio.png.jpg&quot;, &quot;logo_romaneio.png&quot;, &quot;logo.png&quot;, &quot;Tela de login.jpeg&quot;]:
if os.path.exists(nome):
logo_display = nome
break
col_vazia_esq, col_central, col_vazia_dir = st.columns([0.1, 3.8, 0.1])
with col_central:
if logo_display:
col_logo, col_titulo = st.columns([0.45, 3.55], vertical_alignment=&quot;center&quot;)
with col_logo:
st.image(logo_display, use_container_width=True)
with col_titulo:
st.markdown(&quot;&quot;&quot;&lt;div class=&#39;titulo-logo&#39;&gt;&lt;span class=&#39;palavra-sup-
mercado&#39;&gt;Supermercado&lt;/span&gt;&lt;br&gt;&lt;span class=&#39;palavra-super&#39;&gt;SUPER&lt;/span&gt; &lt;span class=&#39;palavra-
nova&#39;&gt;NOVA&lt;/span&gt;&lt;br&gt;&lt;span class=&#39;palavra-cidade&#39;&gt;Cidade&lt;/span&gt;&lt;/div&gt;&quot;&quot;&quot;, unsafe_allow_html=True)
st.markdown(&quot;&lt;h3&gt;HortiControl - Sistema de Recebimento Hortifrúti&lt;/h3&gt;&quot;,
unsafe_allow_html=True)
else:
st.markdown(&quot;&quot;&quot;&lt;div class=&#39;titulo-logo&#39;&gt;&lt;span class=&#39;palavra-sup-
mercado&#39;&gt;Supermercado&lt;/span&gt;&lt;br&gt;&lt;span class=&#39;palavra-super&#39;&gt;SUPER&lt;/span&gt; &lt;span class=&#39;palavra-
nova&#39;&gt;NOVA&lt;/span&gt;&lt;br&gt;&lt;span class=&#39;palavra-cidade&#39;&gt;Cidade&lt;/span&gt;&lt;/div&gt;&quot;&quot;&quot;, unsafe_allow_html=True)
st.markdown(&quot;&lt;h3&gt;HortiControl - Sistema de Recebimento Hortifrúti&lt;/h3&gt;&quot;, unsafe_allow_html=True)
with st.form(&quot;form_login&quot;):
login_input = st.text_input(&quot;Usuário / Login ou Nome Completo&quot;, value=&quot;&quot;, placeholder=&quot;Digite seu
usuário ou nome...&quot;)
senha_input = st.text_input(&quot;Senha&quot;, type=&quot;password&quot;, value=&quot;&quot;, placeholder=&quot;Digite sua
senha...&quot;)
loja_login_sel = st.selectbox(
&quot;Selecione a Loja de Atuação&quot;,
[&quot;&quot;, &quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA 04 MANOA&quot;, &quot;LOJA 05
ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;],
index=0
)
btn_entrar = st.form_submit_button(&quot;Entrar no Sistema&quot;, type=&quot;primary&quot;)
if btn_entrar:
if not loja_login_sel:
st.error(&quot;Por favor, selecione a loja em que você está atuando antes de entrar.&quot;)

else:
spinner_supernova(&quot;Validando acesso no Supernova...&quot;)
usuario = fazer_login(login_input, senha_input)
if usuario:
st.session_state[&quot;usuario_logado&quot;] = {
&quot;id&quot;: usuario[0],
&quot;nome&quot;: usuario[1],
&quot;perfil&quot;: usuario[2],
&quot;login&quot;: usuario[3],
&quot;loja_atual&quot;: loja_login_sel
}
st.success(f&quot;Bem-vindo(a), {usuario[1]} na {loja_login_sel}!&quot;)
st.rerun()
else:
st.error(&quot;Usuário ou senha incorretos.&quot;)
else:
user_info = st.session_state[&quot;usuario_logado&quot;]
perfil_db = str(user_info.get(&quot;perfil&quot;, &quot;&quot;)).strip().lower()
is_admin = (user_info[&quot;login&quot;].lower() == &quot;908&quot; or &quot;gestor&quot; in perfil_db or &quot;adm&quot; in perfil_db)
loja_atual_usuario = user_info.get(&quot;loja_atual&quot;, &quot;Não definida&quot;)
st.markdown(&quot;---&quot;)
col_info_usr, col_logout = st.columns([3.5, 1.5], vertical_alignment=&quot;center&quot;)
with col_info_usr:
tipo_perfil_txt = &quot;�� Gestor / Administrador&quot; if is_admin else f&quot;�� Conferente ({loja_atual_usuario})&quot;
st.markdown(f&quot;**Usuário:** {user_info[&#39;nome&#39;]} &amp;nbsp;|&amp;nbsp; **Perfil:** {tipo_perfil_txt}&quot;)
with col_logout:
if st.button(&quot;�� Sair&quot;, type=&quot;secondary&quot;, key=&quot;btn_sair_sistema_principal&quot;):
st.session_state[&quot;usuario_logado&quot;] = None
st.rerun()
opcoes_menu_map = {
&quot;�� Romaneio de Recebimento&quot;: &quot;Romaneio de Recebimento - Hortifrúti&quot;,
&quot;�� Consultar Romaneios&quot;: &quot;Consultar Romaneios&quot;,
&quot;�� Controle de Bonificação&quot;: &quot;Controle de Bonificação&quot;,
&quot;�� Baixa de Avarias&quot;: &quot;Controle de Baixa de Avarias&quot;
}
if is_admin:
opcoes_menu_map.update({
&quot;�� Relatórios &amp; BI&quot;: &quot;Relatórios &amp; Gráficos&quot;,
&quot;���� Cadastros&quot;: &quot;Gerenciar Cadastros (Produtos)&quot;,
&quot;�� Usuários&quot;: &quot;Gerenciar Usuários &amp; Permissões&quot;
})
menu_selecionado_label = st.radio(
&quot;Menu de Navegação Principal&quot;,
list(opcoes_menu_map.keys()),
horizontal=True,
label_visibility=&quot;collapsed&quot;
)
menu = opcoes_menu_map[menu_selecionado_label]
st.markdown(&quot;---&quot;)
if menu == &quot;Romaneio de Recebimento - Hortifrúti&quot;:
st.title(&quot;�� Romaneio de Recebimento - Hortifrúti&quot;)
if &quot;form_key_suffix&quot; not in st.session_state: st.session_state[&quot;form_key_suffix&quot;] = 0
if &quot;item_key_suffix&quot; not in st.session_state: st.session_state[&quot;item_key_suffix&quot;] = 0
k_suffix = st.session_state[&quot;form_key_suffix&quot;]
i_suffix = st.session_state[&quot;item_key_suffix&quot;]

conn, db_type = get_db_connection()
cursor = conn.cursor()
cursor.execute(&quot;SELECT nome, unidade_padrao, codigo_produto, codigo_barras FROM produtos ORDER BY
nome&quot;)
produtos_lista = cursor.fetchall()
cursor.execute(&quot;SELECT nome, codigo_fornecedor FROM fornecedores ORDER BY nome&quot;)
fornecedores_lista = cursor.fetchall()
conn.close()
prod_dict = {}
for p in produtos_lista:
c_prod = p[2] if p[2] and str(p[2]).strip() else &quot;S/Cód&quot;
c_bar = p[3] if p[3] and str(p[3]).strip() else &quot;S/Barras&quot;
label = f&quot;{c_prod} | Barras: {c_bar} | {p[0]}&quot;
prod_dict[label] = (p[0], p[1] if p[1] else &quot;KG&quot;)
prod_nomes_keys = list(prod_dict.keys())
forn_por_nome = {}
forn_nomes_keys = []
for f in fornecedores_lista:
nome_f = f[0]
cod_f = str(f[1]).strip() if f[1] else &quot;&quot;
forn_nomes_keys.append(nome_f)
forn_por_nome[nome_f] = cod_f
if f&quot;val_cod_forn_{k_suffix}&quot; not in st.session_state: st.session_state[f&quot;val_cod_forn_{k_suffix}&quot;] =
&quot;&quot;
if f&quot;val_sel_forn_{k_suffix}&quot; not in st.session_state: st.session_state[f&quot;val_sel_forn_{k_suffix}&quot;] =
&quot;&quot;
def atualizar_por_select():
s_selecionado = st.session_state.get(f&quot;sel_forn_{k_suffix}&quot;, &quot;&quot;)
st.session_state[f&quot;val_sel_forn_{k_suffix}&quot;] = s_selecionado
novo_cod = &quot;&quot;
if s_selecionado in forn_por_nome:
novo_cod = forn_por_nome[s_selecionado]
st.session_state[f&quot;val_cod_forn_{k_suffix}&quot;] = novo_cod
st.session_state[f&quot;in_cod_forn_{k_suffix}&quot;] = novo_cod
with st.expander(&quot;1. Cabeçalho do Recebimento&quot;, expanded=True):
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
if f&quot;num_rom_auto_{k_suffix}&quot; not in st.session_state:
data_hoje_str = datetime.now(ZoneInfo(&quot;America/Manaus&quot;)).strftime(&quot;%Y%m%d%H%M%S&quot;)
st.session_state[f&quot;num_rom_auto_{k_suffix}&quot;] = f&quot;ROM-{data_hoje_str}&quot;
num_romaneio = st.text_input(&quot;Número do Romaneio&quot;,
value=st.session_state[f&quot;num_rom_auto_{k_suffix}&quot;], disabled=True, key=f&quot;num_rom_{k_suffix}&quot;)
tipo_operacao = st.selectbox(&quot;Tipo de Operação&quot;, [&quot;&quot;, &quot;Compra&quot;, &quot;Bonificação&quot;,
&quot;Transferência&quot;, &quot;Transferência/Bonificação&quot;, &quot;Troca por Troca&quot;], index=0, key=f&quot;tipo_op_{k_suffix}&quot;,
placeholder=&quot;Selecione o tipo...&quot;, on_change=lambda: st.rerun())
with col2:
data_rec_val = st.date_input(&quot;Data do Recebimento&quot;,
value=datetime.now(ZoneInfo(&quot;America/Manaus&quot;)), format=&quot;DD/MM/YYYY&quot;, key=f&quot;data_rec_{k_suffix}&quot;)
data_rec_str = data_rec_val.strftime(&quot;%d/%m/%Y&quot;) if data_rec_val else &quot;&quot;
if tipo_operacao in [&quot;Transferência&quot;, &quot;Transferência/Bonificação&quot;]:

loja_origem = st.selectbox(&quot;Loja de Origem (Saiu)&quot;, [&quot;&quot;, &quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA
CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA 04 MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;],
index=0, placeholder=&quot;Selecione a origem...&quot;, key=f&quot;loja_orig_{k_suffix}&quot;)
loja_destino = st.selectbox(&quot;Loja de Destino (Entrou)&quot;, [&quot;&quot;, &quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA
CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA 04 MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;],
index=0, placeholder=&quot;Selecione o destino...&quot;, key=f&quot;loja_dest_{k_suffix}&quot;)
loja = f&quot;{loja_origem} -&gt; {loja_destino}&quot;
else:
loja_origem = &quot;&quot;
loja_destino = &quot;&quot;
lista_lojas_opc = [&quot;&quot;, &quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA
04 MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;]
idx_loja_login = lista_lojas_opc.index(loja_atual_usuario) if loja_atual_usuario in
lista_lojas_opc else 0
loja = st.selectbox(&quot;Loja&quot;, lista_lojas_opc, index=idx_loja_login, placeholder=&quot;Selecione
a loja...&quot;, key=f&quot;loja_{k_suffix}&quot;)
with col3:
idx_sel = 0
atual_sel = st.session_state[f&quot;val_sel_forn_{k_suffix}&quot;]
if atual_sel in forn_nomes_keys:
idx_sel = forn_nomes_keys.index(atual_sel) + 1
fornecedor_sel = st.selectbox(&quot;Fornecedor / Entregador Cadastrado&quot;, options=[&quot;&quot;] +
forn_nomes_keys, index=idx_sel, placeholder=&quot;Selecione o fornecedor...&quot;, key=f&quot;sel_forn_{k_suffix}&quot;,
on_change=atualizar_por_select)
if f&quot;in_cod_forn_{k_suffix}&quot; not in st.session_state:
st.session_state[f&quot;in_cod_forn_{k_suffix}&quot;] =
st.session_state[f&quot;val_cod_forn_{k_suffix}&quot;]
cod_fornecedor = st.text_input(&quot;Código do Fornecedor (Automático)&quot;,
key=f&quot;in_cod_forn_{k_suffix}&quot;, disabled=True)
col_tel1, col_tel2 = st.columns([2, 2])
with col_tel1:
tel_key = f&quot;tel_input_{k_suffix}&quot;
if tel_key not in st.session_state: st.session_state[tel_key] = &quot;&quot;
def formatar_tel():
val = st.session_state.get(tel_key, &quot;&quot;)
raw = &quot;&quot;.join(filter(str.isdigit, val))
if len(raw) &gt; 11: raw = raw[:11]
fmt = &quot;&quot;
if len(raw) &gt; 0: fmt += f&quot;({raw[:2]}&quot;
if len(raw) &gt;= 3: fmt += f&quot;) {raw[2:7]}&quot;
if len(raw) &gt;= 8: fmt += f&quot;-{raw[7:]}&quot;
st.session_state[tel_key] = fmt
tel_fornecedor = st.text_input(&quot;Telefone de Contato (Opcional)&quot;, value=&quot;&quot;, placeholder=&quot;(00)
00000-0000&quot;, key=tel_key, on_change=formatar_tel)
with col_tel2:
pag_a_vista = st.selectbox(&quot;Pagamento à Vista?&quot;, [&quot;&quot;, &quot;SIM&quot;, &quot;NÃO&quot;], index=0,
placeholder=&quot;Selecione...&quot;, key=f&quot;pag_vista_{k_suffix}&quot;)
fornecedor = fornecedor_sel
data_pag_str = &quot;&quot;
if pag_a_vista == &quot;NÃO&quot;:

data_pag_val = st.date_input(&quot;Data para Pagamento&quot;, value=None, format=&quot;DD/MM/YYYY&quot;,
key=f&quot;data_pag_{k_suffix}&quot;)
data_pag_str = data_pag_val.strftime(&quot;%d/%m/%Y&quot;) if data_pag_val else &quot;&quot;
conferente = st.text_input(&quot;Responsável Rec. Físico&quot;, value=user_info[&quot;nome&quot;], disabled=True,
key=f&quot;conf_{k_suffix}&quot;)
st.subheader(&quot;2. Itens do Recebimento&quot;)
if &quot;itens_romaneio&quot; not in st.session_state: st.session_state[&quot;itens_romaneio&quot;] = []
col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns([2.5, 1.2, 1.2, 1.2, 1])
with col_p1:
prod_label_sel = st.selectbox(&quot;Produto / Código / Barras&quot;, options=[&quot;&quot;] + prod_nomes_keys,
index=0, placeholder=&quot;Selecione o produto...&quot;, key=f&quot;prod_sel_{k_suffix}_{i_suffix}&quot;)
prod_nome_real = prod_dict[prod_label_sel][0] if prod_label_sel and prod_label_sel != &quot;&quot; and
prod_dict else &quot;&quot;
with col_p2:
und_padrao = prod_dict[prod_label_sel][1] if prod_label_sel and prod_label_sel != &quot;&quot; and
prod_dict else &quot;KG&quot;
und_sel = st.selectbox(&quot;UND&quot;, [&quot;KG&quot;, &quot;UNID&quot;, &quot;GRM&quot;, &quot;CX&quot;], index=([&quot;KG&quot;, &quot;UNID&quot;, &quot;GRM&quot;,
&quot;CX&quot;].index(und_padrao) if und_padrao in [&quot;KG&quot;, &quot;UNID&quot;, &quot;GRM&quot;, &quot;CX&quot;] else 0),
key=f&quot;und_sel_{k_suffix}_{i_suffix}&quot;)
with col_p3:
qtd_str_input = st.text_input(&quot;Qtd / Peso&quot;, value=&quot;&quot;, placeholder=&quot;0,000&quot;,
key=f&quot;qtd_{k_suffix}_{i_suffix}&quot;)
with col_p4:
val_unit_str_input = st.text_input(&quot;Valor Unit. (R$)&quot;, value=&quot;&quot;, placeholder=&quot;0,00&quot;,
key=f&quot;vunit_{k_suffix}_{i_suffix}&quot;)
with col_p5:
st.write(&quot;&quot;)
st.write(&quot;&quot;)
if st.button(&quot;➕ Add&quot;, type=&quot;primary&quot;, key=f&quot;btn_add_{k_suffix}_{i_suffix}&quot;):
try: qtd_input = float(qtd_str_input.replace(&quot;.&quot;, &quot;&quot;).replace(&quot;,&quot;, &quot;.&quot;)) if qtd_str_input
else 0.0
except ValueError: qtd_input = 0.0
try: val_unit_val = float(val_unit_str_input.replace(&quot;.&quot;, &quot;&quot;).replace(&quot;,&quot;, &quot;.&quot;)) if
val_unit_str_input else 0.0
except ValueError: val_unit_val = 0.0
if not prod_nome_real: st.warning(&quot;Selecione um produto antes de adicionar.&quot;)
elif qtd_input &lt;= 0: st.warning(&quot;Informe uma quantidade maior que zero.&quot;)
else:
v_tot = qtd_input * val_unit_val
st.session_state[&quot;itens_romaneio&quot;].append({&quot;produto&quot;: prod_nome_real, &quot;quantidade&quot;:
qtd_input, &quot;unidade&quot;: und_sel, &quot;valor_unitario&quot;: val_unit_val, &quot;valor_total&quot;: v_tot})
st.session_state[&quot;item_key_suffix&quot;] += 1
st.rerun()
if st.session_state[&quot;itens_romaneio&quot;]:
st.markdown(&quot;**Itens adicionados:**&quot;)
dados_tabela = [{&quot;Item&quot;: i, &quot;Descrição do Produto&quot;: itm[&quot;produto&quot;], &quot;Qtd / Peso&quot;:
fmt_ptbr(itm[&#39;quantidade&#39;], 3), &quot;UND&quot;: itm[&quot;unidade&quot;], &quot;Vl. Unit&quot;: f&quot;R$ {fmt_ptbr(itm[&#39;valor_unitario&#39;],
2)}&quot;, &quot;Total&quot;: f&quot;R$ {fmt_ptbr(itm[&#39;valor_total&#39;], 2)}&quot;} for i, itm in
enumerate(st.session_state[&quot;itens_romaneio&quot;], 1)]
st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True, hide_index=True)
col_rem_labels, col_rem_btns = st.columns([3, 1])
with col_rem_labels:
item_para_remover = st.selectbox(&quot;Selecionar Item para Remover&quot;, options=range(1,
len(st.session_state[&quot;itens_romaneio&quot;]) + 1), format_func=lambda x: f&quot;Item {x}:
{st.session_state[&#39;itens_romaneio&#39;][x-1][&#39;produto&#39;]}&quot;, key=f&quot;sel_rem_{k_suffix}&quot;)

with col_rem_btns:
st.write(&quot;&quot;)
st.write(&quot;&quot;)
if st.button(&quot;��️ Remover&quot;, key=f&quot;btn_rem_esp_{k_suffix}&quot;, type=&quot;secondary&quot;):
st.session_state[&quot;itens_romaneio&quot;].pop(item_para_remover - 1)
st.rerun()
total_geral_temp = sum(itm[&#39;valor_total&#39;] for itm in st.session_state[&quot;itens_romaneio&quot;])
st.markdown(f&quot;### **Total Geral: R$ {fmt_ptbr(total_geral_temp, 2)}**&quot;)
if st.button(&quot;��️ Limpar Todos os Itens&quot;, type=&quot;secondary&quot;, key=f&quot;btn_del_itens_{k_suffix}&quot;):
st.session_state[&quot;itens_romaneio&quot;] = []
st.rerun()
st.subheader(&quot;3. Anexo de Foto da Mercadoria / Nota Fiscal&quot;)
fotos_upload = st.file_uploader(&quot;Foto da Mercadoria / Nota Fiscal&quot;, type=[&quot;jpg&quot;, &quot;jpeg&quot;, &quot;png&quot;,
&quot;pdf&quot;], accept_multiple_files=True, key=f&quot;fotos_{k_suffix}&quot;)
st.subheader(&quot;4. Informações Adicionais / Observações&quot;)
observacoes_romaneio = st.text_area(&quot;Observações sobre a carga, qualidade ou divergências&quot;, value=&quot;&quot;,
placeholder=&quot;Insira observações relevantes aqui...&quot;, key=f&quot;obs_{k_suffix}&quot;)
st.subheader(&quot;5. Assinatura Digital&quot;)
col_ass1, col_ass2 = st.columns(2)
with col_ass1:
st.write(&quot;**Assinatura do Conferente**&quot;)
canvas_conf = st_canvas(
stroke_width=3,
stroke_color=&quot;#000000&quot;,
background_color=&quot;#FFFFFF&quot;,
height=120,
width=280,
drawing_mode=&quot;freedraw&quot;,
return_image_data=True,
key=f&quot;canv_conf_{k_suffix}&quot;
)
with col_ass2:
st.write(&quot;**Assinatura do Entregador / Fornecedor**&quot;)
canvas_ent = st_canvas(
stroke_width=3,
stroke_color=&quot;#000000&quot;,
background_color=&quot;#FFFFFF&quot;,
height=120,
width=280,
drawing_mode=&quot;freedraw&quot;,
return_image_data=True,
key=f&quot;canv_ent_{k_suffix}&quot;
)
if st.button(&quot;✅ Salvar Romaneio&quot;, type=&quot;primary&quot;, key=f&quot;btn_salvar_{k_suffix}&quot;):
num_rom_final = st.session_state[f&quot;num_rom_auto_{k_suffix}&quot;]
forn_final = fornecedor if isinstance(fornecedor, str) else &quot;&quot;
cod_forn_val = st.session_state[f&quot;val_cod_forn_{k_suffix}&quot;]
if not forn_final.strip(): st.error(&quot;Selecione o fornecedor na lista cadastrada.&quot;)
elif not data_rec_str: st.error(&quot;A Data do Recebimento é obrigatória!&quot;)
elif tipo_operacao in [&quot;Transferência&quot;, &quot;Transferência/Bonificação&quot;] and (not loja_origem or not
loja_destino): st.error(&quot;Selecione a Loja de Origem e a Loja de Destino!&quot;)
elif tipo_operacao not in [&quot;Transferência&quot;, &quot;Transferência/Bonificação&quot;] and not loja:
st.error(&quot;Selecione a loja!&quot;)
elif pag_a_vista == &quot;NÃO&quot; and not data_pag_str: st.error(&quot;A Data para Pagamento é obrigatória
para compras a prazo!&quot;)

elif not st.session_state[&quot;itens_romaneio&quot;]: st.error(&quot;Adicione itens ao romaneio.&quot;)
else:
spinner_supernova(&quot;Salvando romaneio no Supernova...&quot;)
try:
if not os.path.exists(&quot;uploads&quot;): os.makedirs(&quot;uploads&quot;)
path_ass_conf = &quot;&quot;
b64_conf = &quot;&quot;
if canvas_conf.image_data is not None:
img_c = Image.fromarray(canvas_conf.image_data.astype(&quot;uint8&quot;))
path_ass_conf = os.path.join(&quot;uploads&quot;, f&quot;ass_conf_{num_rom_final}.png&quot;)
img_c.save(path_ass_conf)
with open(path_ass_conf, &quot;rb&quot;) as f_ac:
b64_conf = base64.b64encode(f_ac.read()).decode(&#39;utf-8&#39;)
path_ass_ent = &quot;&quot;
b64_ent = &quot;&quot;
if canvas_ent.image_data is not None:
img_e = Image.fromarray(canvas_ent.image_data.astype(&quot;uint8&quot;))
path_ass_ent = os.path.join(&quot;uploads&quot;, f&quot;ass_ent_{num_rom_final}.png&quot;)
img_e.save(path_ass_ent)
with open(path_ass_ent, &quot;rb&quot;) as f_ae:
b64_ent = base64.b64encode(f_ae.read()).decode(&#39;utf-8&#39;)
caminho_foto_salva = &quot;&quot;
b64_foto = &quot;&quot;
if fotos_upload:
for f in fotos_upload:
path_f = os.path.join(&quot;uploads&quot;, f.name)
f_bytes = f.getbuffer()
with open(path_f, &quot;wb&quot;) as f_out: f_out.write(f_bytes)
caminho_foto_salva = path_f
b64_foto = base64.b64encode(f_bytes).decode(&#39;utf-8&#39;)
conn, db_type = get_db_connection()
cursor = conn.cursor()
if db_type == &quot;postgres&quot;:
cursor.execute(&quot;&quot;&quot;
INSERT INTO romaneios (numero_romaneio, loja, loja_origem, loja_destino,
data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista,
data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador, status_nota, tipo_operacao,
observacoes, foto_b64, ass_conf_b64, ass_ent_b64)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
%s, %s) RETURNING id
&quot;&quot;&quot;, (num_rom_final, loja, loja_origem, loja_destino, data_rec_str, forn_final,
cod_forn_val, tel_fornecedor, user_info[&quot;nome&quot;], pag_a_vista, data_pag_str, caminho_foto_salva,
path_ass_conf, path_ass_ent, &#39;Pendente&#39;, tipo_operacao, observacoes_romaneio, b64_foto, b64_conf, b64_ent))
romaneio_id = cursor.fetchone()[0]
else:
cursor.execute(&quot;&quot;&quot;
INSERT INTO romaneios (numero_romaneio, loja, loja_origem, loja_destino,
data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista,
data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador, status_nota, tipo_operacao,
observacoes, foto_b64, ass_conf_b64, ass_ent_b64)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
&quot;&quot;&quot;, (num_rom_final, loja, loja_origem, loja_destino, data_rec_str, forn_final,
cod_forn_val, tel_fornecedor, user_info[&quot;nome&quot;], pag_a_vista, data_pag_str, caminho_foto_salva,
path_ass_conf, path_ass_ent, &#39;Pendente&#39;, tipo_operacao, observacoes_romaneio, b64_foto, b64_conf, b64_ent))
romaneio_id = cursor.lastrowid
itens_salvos_pdf = []

for itm in st.session_state[&quot;itens_romaneio&quot;]:
if db_type == &quot;postgres&quot;:
cursor.execute(&quot;INSERT INTO romaneio_itens (romaneio_id, produto, quantidade,
unidade, valor_unitario, valor_total) VALUES (%s, %s, %s, %s, %s, %s)&quot;, (romaneio_id, itm[&quot;produto&quot;],
itm[&quot;quantidade&quot;], itm[&quot;unidade&quot;], itm[&quot;valor_unitario&quot;], itm[&quot;valor_total&quot;]))
else:
cursor.execute(&quot;INSERT INTO romaneio_itens (romaneio_id, produto, quantidade,
unidade, valor_unitario, valor_total) VALUES (?, ?, ?, ?, ?, ?)&quot;, (romaneio_id, itm[&quot;produto&quot;],
itm[&quot;quantidade&quot;], itm[&quot;unidade&quot;], itm[&quot;valor_unitario&quot;], itm[&quot;valor_total&quot;]))
itens_salvos_pdf.append([None, itm[&quot;produto&quot;], itm[&quot;quantidade&quot;], itm[&quot;unidade&quot;],
itm[&quot;valor_unitario&quot;], itm[&quot;valor_total&quot;]])
conn.commit()
conn.close()
romaneio_dict_atual = {&quot;numero_romaneio&quot;: num_rom_final, &quot;data_recebimento&quot;:
data_rec_str, &quot;fornecedor&quot;: forn_final, &quot;codigo_fornecedor&quot;: cod_forn_val, &quot;telefone_fornecedor&quot;:
tel_fornecedor, &quot;loja&quot;: loja, &quot;loja_origem&quot;: loja_origem, &quot;loja_destino&quot;: loja_destino, &quot;conferente&quot;:
user_info[&quot;nome&quot;], &quot;pagamento_a_vista&quot;: pag_a_vista, &quot;data_pagamento&quot;: data_pag_str, &quot;tipo_operacao&quot;:
tipo_operacao, &quot;observacoes&quot;: observacoes_romaneio}
pdf_buffer_novo = gerar_pdf_romaneio(romaneio_dict_atual, itens_salvos_pdf,
path_ass_conf, path_ass_ent)
st.session_state[&quot;ultimo_pdf_bytes&quot;] = pdf_buffer_novo.getvalue()
st.session_state[&quot;ultimo_num_romaneio&quot;] = num_rom_final
st.session_state[&quot;itens_romaneio&quot;] = []
st.session_state[&quot;form_key_suffix&quot;] += 1
st.session_state[&quot;item_key_suffix&quot;] = 0
st.success(f&quot;Romaneio {num_rom_final} gerado e salvo com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao salvar romaneio: {e}&quot;)
if &quot;ultimo_pdf_bytes&quot; in st.session_state and &quot;ultimo_num_romaneio&quot; in st.session_state:
st.markdown(&quot;---&quot;)
st.success(f&quot;�� Romaneio **{st.session_state[&#39;ultimo_num_romaneio&#39;]}** pronto para download!&quot;)
st.download_button(label=f&quot;�� Descarregar PDF - {st.session_state[&#39;ultimo_num_romaneio&#39;]}&quot;
data=st.session_state[&quot;ultimo_pdf_bytes&quot;], file_name=f&quot;{st.session_state[&#39;ultimo_num_romaneio&#39;]}.pdf&quot;,
mime=&quot;application/pdf&quot;, type=&quot;primary&quot;)
elif menu == &quot;Consultar Romaneios&quot;:
st.title(&quot;�� Consultar &amp; Gerenciar Romaneios de Recebimento&quot;)
conn, db_type = get_db_connection()
df_rom = pd.read_sql_query(&quot;SELECT * FROM romaneios ORDER BY id DESC&quot;, conn)
df_all_itens = pd.read_sql_query(&quot;SELECT romaneio_id, SUM(valor_total) as valor_total_rom FROM
romaneio_itens GROUP BY romaneio_id&quot;, conn)
conn.close()
if df_rom.empty:
st.info(&quot;Nenhum romaneio registrado no sistema.&quot;)
else:
if not df_all_itens.empty:
df_rom = df_rom.merge(df_all_itens, left_on=&quot;id&quot;, right_on=&quot;romaneio_id&quot;, how=&quot;left&quot;)
df_rom[&quot;valor_total_rom&quot;] = df_rom[&quot;valor_total_rom&quot;].fillna(0.0)
else:
df_rom[&quot;valor_total_rom&quot;] = 0.0
lista_lojas_sistema = [&quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA 04
MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;]
if not is_admin and loja_atual_usuario in lista_lojas_sistema:
lojas_para_exibir = [loja_atual_usuario]

else:
lojas_para_exibir = lista_lojas_sistema
tabs_lojas = st.tabs([f&quot;�� {l}&quot; for l in lojas_para_exibir])
for idx_l, loja_nome in enumerate(lojas_para_exibir):
with tabs_lojas[idx_l]:
st.markdown(f&quot;### �� Romaneios - {loja_nome}&quot;)
df_loja_atual = df_rom[
df_rom[&quot;loja&quot;].str.contains(loja_nome, case=False, na=False) |
df_rom.get(&quot;loja_destino&quot;, pd.Series(dtype=str)).str.contains(loja_nome, case=False,
na=False)
].copy()
if df_loja_atual.empty:
st.info(f&quot;Nenhum romaneio registrado para a {loja_nome}.&quot;)
else:
tipos_operacao_disponiveis = [&quot;TODOS OS TIPOS&quot;, &quot;Compra&quot;, &quot;Bonificação&quot;,
&quot;Transferência&quot;, &quot;Transferência/Bonificação&quot;, &quot;Troca por Troca&quot;]
subtabs_tipo = st.tabs([f&quot;�� {t}&quot; for t in tipos_operacao_disponiveis])
for idx_t, tipo_op in enumerate(tipos_operacao_disponiveis):
with subtabs_tipo[idx_t]:
if tipo_op == &quot;TODOS OS TIPOS&quot;:
df_tipo_atual = df_loja_atual.copy()
else:
df_tipo_atual =
df_loja_atual[df_loja_atual[&quot;tipo_operacao&quot;].str.contains(tipo_op, case=False, na=False)].copy()
if df_tipo_atual.empty:
st.markdown(f&quot;&lt;p style=&#39;color: #9aa0a6; font-style: italic; padding:
10px;&#39;&gt;Nenhum romaneio encontrado nesta categoria.&lt;/p&gt;&quot;, unsafe_allow_html=True)
else:
st.markdown(f&quot;**Total de registros em &#39;{tipo_op}&#39;:**
{len(df_tipo_atual)}&quot;)
# EXIBIÇÃO EM PLANILHA CONSOLIDADA
df_planilha = df_tipo_atual.copy()
df_planilha[&quot;Anexo&quot;] = df_planilha.apply(lambda r: &quot;�� Disponível&quot; i
(r.get(&quot;caminho_foto&quot;) and os.path.exists(str(r[&quot;caminho_foto&quot;]))) or r.get(&quot;foto_b64&quot;) else &quot;Sem Anexo&quot;,
axis=1)
df_planilha[&quot;Valor Total&quot;] = df_planilha[&quot;valor_total_rom&quot;].apply(lambda
x: f&quot;R$ {fmt_ptbr(x, 2)}&quot;)
df_planilha_show = df_planilha.rename(columns={
&quot;numero_romaneio&quot;: &quot;N° Romaneio&quot;,
&quot;tipo_operacao&quot;: &quot;Tipo Operação&quot;,
&quot;loja&quot;: &quot;Loja&quot;,
&quot;data_recebimento&quot;: &quot;Data Recebimento&quot;,
&quot;fornecedor&quot;: &quot;Fornecedor&quot;,
&quot;conferente&quot;: &quot;Conferente&quot;,
&quot;status_nota&quot;: &quot;Status Atual&quot;
})
cols_view = df_planilha_show[[&quot;N° Romaneio&quot;, &quot;Tipo Operação&quot;, &quot;Loja&quot;,
&quot;Data Recebimento&quot;, &quot;Fornecedor&quot;, &quot;Conferente&quot;, &quot;Valor Total&quot;, &quot;Status Atual&quot;, &quot;Anexo&quot;]]
cols_view.index = range(1, len(cols_view) + 1)
st.dataframe(cols_view, use_container_width=True, height=280)

st.markdown(&quot;---&quot;)
st.subheader(&quot;⚙️ Gerenciador de Romaneio: Visualizar Anexo, Atualizar
Status e Editar (Admin)&quot;)
opcoes_rom_gerenciar = [(row[&quot;id&quot;], f&quot;Romaneio {row[&#39;numero_romaneio&#39;]} |
Status: {row.get(&#39;status_nota&#39;,&#39;Pendente&#39;)} | Fornecedor: {row[&#39;fornecedor&#39;] or &#39;N/A&#39;} | Data:
{row[&#39;data_recebimento&#39;]}&quot;) for _, row in df_tipo_atual.iterrows()]
chave_tab = f&quot;{loja_nome}_{tipo_op}&quot;.replace(&quot; &quot;, &quot;_&quot;).replace(&quot;/&quot;, &quot;_&quot;)
rom_sel_tuple = st.selectbox(
&quot;Selecione o Romaneio na Planilha para Ações&quot;,
options=opcoes_rom_gerenciar,
format_func=lambda x: x[1],
key=f&quot;sel_rom_planilha_{chave_tab}&quot;
)
if rom_sel_tuple:
id_rom_sel = rom_sel_tuple[0]
row_sel = df_tipo_atual[df_tipo_atual[&quot;id&quot;] == id_rom_sel].iloc[0]
chv_elem = f&quot;{chave_tab}_{id_rom_sel}&quot;
# COLUNAS LADO A LADO: COLUNA PARA VER ANEXO E COLUNA PARA ALTERAR
STATUS
col_anx, col_st, col_pdf_act = st.columns([2, 2.5, 2.5])
with col_anx:
st.markdown(&quot;**�� Coluna de Anexo**&quot;)
cam_foto = row_sel.get(&#39;caminho_foto&#39;, &#39;&#39;)
b64_foto_rom = row_sel.get(&#39;foto_b64&#39;, &#39;&#39;)
if cam_foto or b64_foto_rom:
if st.button(&quot;�� Visualizar Nota / Anexo&quot;
key=f&quot;btn_ver_anx_grid_{chv_elem}&quot;, type=&quot;primary&quot;):
exibir_foto_modal(cam_foto, b64_foto_rom)
else:
st.info(&quot;Sem anexo anexado.&quot;)
with col_st:
st.markdown(&quot;**�� Coluna de Mudança de Status**&quot;)
opcoes_status_rom = [&quot;Pendente&quot;, &quot;Nota Emitida&quot;, &quot;Trocado&quot;,
&quot;Lançado&quot;]
st_atual = row_sel.get(&quot;status_nota&quot;, &quot;Pendente&quot;)
idx_st_padr = opcoes_status_rom.index(st_atual) if st_atual in
opcoes_status_rom else 0
col_sel_s, col_btn_s = st.columns([1.8, 1.2])
with col_sel_s:
novo_st_sel = st.selectbox(&quot;Status&quot;, opcoes_status_rom,
index=idx_st_padr, key=f&quot;sel_st_grid_{chv_elem}&quot;, label_visibility=&quot;collapsed&quot;)
with col_btn_s:
if st.button(&quot;�� Salvar Status&quot;
key=f&quot;btn_st_grid_{chv_elem}&quot;):
spinner_supernova(&quot;Atualizando status...&quot;)
try:
conn_st, db_t_st = get_db_connection()
cur_st = conn_st.cursor()
cur_st.execute(
&quot;UPDATE romaneios SET status_nota = %s WHERE id =
%s&quot; if db_t_st == &quot;postgres&quot; else &quot;UPDATE romaneios SET status_nota = ? WHERE id = ?&quot;,
(novo_st_sel, int(id_rom_sel) if db_t_st ==
&quot;postgres&quot; else id_rom_sel)

)
conn_st.commit()
conn_st.close()
st.success(&quot;Status atualizado com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao salvar status:
{e}&quot;)
with col_pdf_act:
st.markdown(&quot;**�� Relatório PDF / Exclusão**&quot;)
conn_i, db_t_i = get_db_connection()
df_itens_r = pd.read_sql_query(&quot;SELECT produto, quantidade,
unidade, valor_unitario, valor_total FROM romaneio_itens WHERE romaneio_id = %s&quot; if db_t_i == &quot;postgres&quot; else
&quot;SELECT produto, quantidade, unidade, valor_unitario, valor_total FROM romaneio_itens WHERE romaneio_id = ?&quot;,
conn_i, params=(int(id_rom_sel) if db_t_i == &quot;postgres&quot; else id_rom_sel,))
conn_i.close()
pdf_buf = gerar_pdf_romaneio(row_sel.to_dict(), [(None,
r[&#39;produto&#39;], r[&#39;quantidade&#39;], r[&#39;unidade&#39;], r[&#39;valor_unitario&#39;], r[&#39;valor_total&#39;]) for _, r in
df_itens_r.iterrows()], row_sel.get(&quot;assinatura_conferente&quot;), row_sel.get(&quot;assinatura_entregador&quot;))
col_dl_p, col_del_p = st.columns([2, 1])
with col_dl_p:
st.download_button(label=f&quot;�� Baixar PDF&quot;, data=pdf_buf
file_name=f&quot;{row_sel[&#39;numero_romaneio&#39;]}.pdf&quot;, mime=&quot;application/pdf&quot;, key=f&quot;btn_pdf_grid_{chv_elem}&quot;)
with col_del_p:
if is_admin:
if st.button(&quot;��️&quot;, key=f&quot;btn_del_grid_{chv_elem}&quot;
help=&quot;Excluir Romaneio&quot;, type=&quot;secondary&quot;):
spinner_supernova(&quot;Excluindo romaneio...&quot;)
try:
conn_del, db_t_del = get_db_connection()
cur_del = conn_del.cursor()
cur_del.execute(&quot;DELETE FROM romaneio_itens WHERE
romaneio_id = %s&quot; if db_t_del == &quot;postgres&quot; else &quot;DELETE FROM romaneio_itens WHERE romaneio_id = ?&quot;,
(int(id_rom_sel) if db_t_del == &quot;postgres&quot; else id_rom_sel,))
cur_del.execute(&quot;DELETE FROM romaneios WHERE id =
%s&quot; if db_t_del == &quot;postgres&quot; else &quot;DELETE FROM romaneios WHERE id = ?&quot;, (int(id_rom_sel) if db_t_del ==
&quot;postgres&quot; else id_rom_sel,))
conn_del.commit()
conn_del.close()
st.success(&quot;Excluído com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro: {e}&quot;)
# ITENS DO ROMANEIO SELECIONADO
with st.expander(f&quot;�� Ver Itens Cadastrados no Romanei
{row_sel[&#39;numero_romaneio&#39;]}&quot;, expanded=False):
if not df_itens_r.empty:
df_itens_show = df_itens_r.copy()
df_itens_show[&#39;Qtd / Peso&#39;] =
df_itens_show[&#39;quantidade&#39;].apply(lambda x: fmt_ptbr(x, 3))
df_itens_show[&#39;Vl. Unit&#39;] =
df_itens_show[&#39;valor_unitario&#39;].apply(lambda x: f&quot;R$ {fmt_ptbr(x, 2)}&quot;)
df_itens_show[&#39;Total&#39;] =
df_itens_show[&#39;valor_total&#39;].apply(lambda x: f&quot;R$ {fmt_ptbr(x, 2)}&quot;)
st.dataframe(df_itens_show[[&#39;produto&#39;, &#39;Qtd / Peso&#39;,
&#39;unidade&#39;, &#39;Vl. Unit&#39;, &#39;Total&#39;]], use_container_width=True, hide_index=True)
else:
st.info(&quot;Nenhum item vinculado a este romaneio.&quot;)

# OPÇÃO DE EDIÇÃO DE ROMANEIO REINSTAURADA PARA O ADMINISTRADOR
if is_admin:
with st.expander(f&quot;✏️ Editar Romaneio
{row_sel[&#39;numero_romaneio&#39;]} (Apenas Administrador)&quot;, expanded=False):
with st.form(f&quot;form_edicao_romaneio_admin_{chv_elem}&quot;):
st.markdown(f&quot;**Edição dos Dados do Romaneio
{row_sel[&#39;numero_romaneio&#39;]}**&quot;)
col_ed_r1, col_ed_r2, col_ed_r3 = st.columns(3)
with col_ed_r1:
novo_forn_ed = st.text_input(&quot;Fornecedor&quot;,
value=row_sel[&quot;fornecedor&quot;] or &quot;&quot;)
novo_cod_forn_ed = st.text_input(&quot;Cód. Fornecedor&quot;,
value=row_sel[&quot;codigo_fornecedor&quot;] or &quot;&quot;)
with col_ed_r2:
novo_tel_ed = st.text_input(&quot;Telefone Fornecedor&quot;,
value=row_sel[&quot;telefone_fornecedor&quot;] or &quot;&quot;)
novo_tipo_op_ed = st.selectbox(&quot;Tipo Operação&quot;,
[&quot;Compra&quot;, &quot;Bonificação&quot;, &quot;Transferência&quot;, &quot;Transferência/Bonificação&quot;, &quot;Troca por Troca&quot;], index=([&quot;Compra&quot;,
&quot;Bonificação&quot;, &quot;Transferência&quot;, &quot;Transferência/Bonificação&quot;, &quot;Troca por
Troca&quot;].index(row_sel[&quot;tipo_operacao&quot;]) if row_sel[&quot;tipo_operacao&quot;] in [&quot;Compra&quot;, &quot;Bonificação&quot;,
&quot;Transferência&quot;, &quot;Transferência/Bonificação&quot;, &quot;Troca por Troca&quot;] else 0))
with col_ed_r3:
novo_pag_v_ed = st.selectbox(&quot;Pagamento à Vista?&quot;,
[&quot;SIM&quot;, &quot;NÃO&quot;], index=(0 if row_sel[&quot;pagamento_a_vista&quot;] == &quot;SIM&quot; else 1))
nova_dt_pag_ed = st.text_input(&quot;Data Pagamento&quot;,
value=row_sel[&quot;data_pagamento&quot;] or &quot;&quot;)
novas_obs_ed = st.text_area(&quot;Observações&quot;,
value=row_sel[&quot;observacoes&quot;] or &quot;&quot;)
novo_anexo_rom_up = st.file_uploader(&quot;Substituir Nota /
Anexo (Opcional)&quot;, type=[&quot;pdf&quot;, &quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;], key=f&quot;up_edit_rom_{chv_elem}&quot;)
btn_salvar_ed_rom = st.form_submit_button(&quot;�� Salva
Alterações do Romaneio&quot;, type=&quot;primary&quot;)
if btn_salvar_ed_rom:
spinner_supernova(&quot;Salvando alterações do
romaneio...&quot;)
try:
path_foto_ed = row_sel.get(&quot;caminho_foto&quot;, &quot;&quot;)
b64_foto_ed = row_sel.get(&quot;foto_b64&quot;, &quot;&quot;)
if novo_anexo_rom_up:
path_foto_ed = os.path.join(&quot;uploads&quot;,
f&quot;ROM_EDIT_{row_sel[&#39;numero_romaneio&#39;]}_{novo_anexo_rom_up.name}&quot;)
b_up_rom = novo_anexo_rom_up.getbuffer()
with open(path_foto_ed, &quot;wb&quot;) as f_out:
f_out.write(b_up_rom)
b64_foto_ed =
base64.b64encode(b_up_rom).decode(&#39;utf-8&#39;)
conn_urom, db_turom = get_db_connection()
cur_urom = conn_urom.cursor()
cur_urom.execute(
&quot;UPDATE romaneios SET fornecedor = %s,
codigo_fornecedor = %s, telefone_fornecedor = %s, tipo_operacao = %s, pagamento_a_vista = %s, data_pagamento
= %s, observacoes = %s, caminho_foto = %s, foto_b64 = %s WHERE id = %s&quot; if db_turom == &quot;postgres&quot; else
&quot;UPDATE romaneios SET fornecedor = ?, codigo_fornecedor = ?, telefone_fornecedor = ?, tipo_operacao = ?,
pagamento_a_vista = ?, data_pagamento = ?, observacoes = ?, caminho_foto = ?, foto_b64 = ? WHERE id = ?&quot;,

(novo_forn_ed.strip(),
novo_cod_forn_ed.strip(), novo_tel_ed.strip(), novo_tipo_op_ed, novo_pag_v_ed, nova_dt_pag_ed.strip(),
novas_obs_ed.strip(), path_foto_ed, b64_foto_ed, int(id_rom_sel) if db_turom == &quot;postgres&quot; else id_rom_sel)
)
conn_urom.commit()
conn_urom.close()
st.success(&quot;Romaneio atualizado com sucesso pelo
administrador!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao editar
romaneio: {e}&quot;)
# ---------------------------------------------------------
# 6. CONTROLE DE BONIFICAÇÃO
# ---------------------------------------------------------
elif menu == &quot;Controle de Bonificação&quot;:
st.title(&quot;�� Controle de Bonificação Hortifrúti&quot;)
conn_prod, db_p = get_db_connection()
cursor_p = conn_prod.cursor()
cursor_p.execute(&quot;SELECT codigo_produto, codigo_barras, nome FROM produtos ORDER BY nome&quot;)
prods_cad = cursor_p.fetchall()
conn_prod.close()
lista_opcoes_prod = []
for p in prods_cad:
c_prod = p[0] if p[0] and str(p[0]).strip() else &quot;S/Cód&quot;
c_bar = p[1] if p[1] and str(p[1]).strip() else &quot;S/Barras&quot;
lista_opcoes_prod.append(f&quot;{c_prod} | Barras: {c_bar} | {p[2]}&quot;)
with st.expander(&quot;➕ Cadastrar Nova Bonificação&quot;, expanded=False):
with st.form(&quot;form_cad_bonificacao&quot;, clear_on_submit=True):
col_b1, col_b2, col_b3 = st.columns([1.5, 1.5, 1.5])
with col_b1:
num_nota_bonf = st.text_input(&quot;N° Nota Fiscal&quot;, value=&quot;&quot;, placeholder=&quot;Número da
nota...&quot;)
lista_lojas_cad_b = [&quot;&quot;, &quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA
04 MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;]
idx_l_cad_b = lista_lojas_cad_b.index(loja_atual_usuario) if loja_atual_usuario in
lista_lojas_cad_b else 0
loja_bonf = st.selectbox(&quot;Loja&quot;, lista_lojas_cad_b, index=idx_l_cad_b,
placeholder=&quot;Selecione a loja...&quot;, key=&quot;loja_bonf_sel&quot;)
with col_b2:
valor_bonf_str = st.text_input(&quot;Valor da Bonificação (R$)&quot;, value=&quot;&quot;, placeholder=&quot;0,00&quot;)
tipo_bonf_sel = st.selectbox(&quot;Tipo de Bonificação&quot;, [&quot;&quot;, &quot;Bonificação&quot;, &quot;Transferência de
Bonificação&quot;], index=0, placeholder=&quot;Selecione o tipo...&quot;, key=&quot;tipo_bonf_input_sel&quot;)
with col_b3:
prod_bonf = st.selectbox(&quot;Produto Hortifrúti&quot;, options=[&quot;&quot;] + lista_opcoes_prod, index=0,
placeholder=&quot;Selecione o produto...&quot;)
anexo_bonf = st.file_uploader(&quot;Anexar NF (PDF ou Imagem)&quot;, type=[&quot;pdf&quot;, &quot;png&quot;, &quot;jpg&quot;,
&quot;jpeg&quot;])
col_dt1, col_dt2, col_dt3 = st.columns([1.5, 1.5, 1.5])
with col_dt1: status_bonf = st.selectbox(&quot;STATUS&quot;, [&quot;&quot;, &quot;Disponível&quot;, &quot;Parcialmente
Utilizada&quot;, &quot;Totalmente Utilizada&quot;], index=0, placeholder=&quot;Selecione o status...&quot;)
with col_dt2: data_entrada_manual = st.date_input(&quot;Data de Entrada&quot;,
value=datetime.now(ZoneInfo(&quot;America/Manaus&quot;)), format=&quot;DD/MM/YYYY&quot;)
with col_dt3:
hora_auto = datetime.now(ZoneInfo(&quot;America/Manaus&quot;)).strftime(&#39;%H:%M:%S&#39;)
st.text_input(&quot;Hora de Entrada&quot;, value=hora_auto, disabled=True)

dt_entrada_str = f&quot;{data_entrada_manual.strftime(&#39;%d/%m/%Y&#39;)} {hora_auto}&quot; if
data_entrada_manual else &quot;&quot;
if st.form_submit_button(&quot;✅ Salvar Bonificação&quot;, type=&quot;primary&quot;):
if not num_nota_bonf.strip() or not loja_bonf or not prod_bonf or not status_bonf:
st.error(&quot;Preencha todos os campos obrigatórios.&quot;)
else:
spinner_supernova(&quot;Salvando bonificação...&quot;)
try: valor_bonf_val = float(valor_bonf_str.replace(&quot;.&quot;, &quot;&quot;).replace(&quot;,&quot;, &quot;.&quot;)) if
valor_bonf_str else 0.0
except ValueError: valor_bonf_val = 0.0
path_anexo_bonf = &quot;&quot;
b64_anexo_bonf = &quot;&quot;
if anexo_bonf:
path_anexo_bonf = os.path.join(&quot;uploads&quot;,
f&quot;NF_{num_nota_bonf}_{anexo_bonf.name}&quot;)
anexo_bytes = anexo_bonf.getbuffer()
with open(path_anexo_bonf, &quot;wb&quot;) as f_out: f_out.write(anexo_bytes)
b64_anexo_bonf = base64.b64encode(anexo_bytes).decode(&#39;utf-8&#39;)
try:
conn_b, db_tb = get_db_connection()
cursor_b = conn_b.cursor()
cursor_b.execute(
&quot;INSERT INTO bonificacoes (numero_nota, loja, data_entrada,
valor_bonificacao, status, produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64) VALUES (%s, %s,
%s, %s, %s, %s, %s, %s, %s)&quot; if db_tb == &quot;postgres&quot; else &quot;INSERT INTO bonificacoes (numero_nota, loja,
data_entrada, valor_bonificacao, status, produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)&quot;,
(num_nota_bonf.strip(), loja_bonf, dt_entrada_str, valor_bonf_val,
status_bonf, prod_bonf, path_anexo_bonf, tipo_bonf_sel, b64_anexo_bonf)
)
conn_b.commit()
conn_b.close()
st.success(&quot;Salvo com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro: {e}&quot;)
st.markdown(&quot;---&quot;)
st.subheader(&quot;�� Registros de Bonificação e Consulta de Notas&quot;)
lista_lojas_filtro_bonf = [&quot;TODAS&quot;, &quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA
04 MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;]
idx_filtro_bonf = 0
if not is_admin and loja_atual_usuario in lista_lojas_filtro_bonf:
idx_filtro_bonf = lista_lojas_filtro_bonf.index(loja_atual_usuario)
with st.expander(&quot;�� Filtros de Busca&quot;, expanded=True):
f_col1, f_col2, f_col3, f_col4 = st.columns(4)
with f_col1: f_nota = st.text_input(&quot;Filtrar por N° Nota&quot;, value=&quot;&quot;, placeholder=&quot;N° da nota...&quot;,
key=&quot;f_nota_bonf&quot;)
with f_col2: f_loja = st.selectbox(&quot;Filtrar por Loja&quot;, options=lista_lojas_filtro_bonf,
index=idx_filtro_bonf, placeholder=&quot;Selecione...&quot;, key=&quot;f_loja_bonf&quot;)
with f_col3: f_status = st.selectbox(&quot;Filtrar por Status&quot;, [&quot;TODOS&quot;, &quot;Disponível&quot;, &quot;Parcialmente
Utilizada&quot;, &quot;Totalmente Utilizada&quot;], placeholder=&quot;Selecione...&quot;, key=&quot;f_status_bonf&quot;)
with f_col4: f_prod = st.text_input(&quot;Filtrar por Produto&quot;, value=&quot;&quot;, placeholder=&quot;Produto...&quot;,
key=&quot;f_prod_bonf&quot;)

conn_b_sel, db_tb_sel = get_db_connection()
df_bonf = pd.read_sql_query(&quot;SELECT * FROM bonificacoes ORDER BY id DESC&quot;, conn_b_sel)
conn_b_sel.close()
if not df_bonf.empty:
if f_nota.strip(): df_bonf = df_bonf[df_bonf[&quot;numero_nota&quot;].str.contains(f_nota.strip(),
case=False, na=False)]
if f_loja != &quot;TODAS&quot;: df_bonf = df_bonf[df_bonf[&quot;loja&quot;] == f_loja]
if f_status != &quot;TODOS&quot;: df_bonf = df_bonf[df_bonf[&quot;status&quot;] == f_status]
if f_prod.strip(): df_bonf = df_bonf[df_bonf[&quot;produto_hortifruti&quot;].str.contains(f_prod.strip(),
case=False, na=False)]
if not df_bonf.empty:
tot_bonf_val = df_bonf[&quot;valor_bonificacao&quot;].sum()
tot_disp_val = df_bonf[df_bonf[&quot;status&quot;] == &quot;Disponível&quot;][&quot;valor_bonificacao&quot;].sum()
tot_parc_val = df_bonf[df_bonf[&quot;status&quot;] == &quot;Parcialmente Utilizada&quot;][&quot;valor_bonificacao&quot;].sum()
tot_util_val = df_bonf[df_bonf[&quot;status&quot;] == &quot;Totalmente Utilizada&quot;][&quot;valor_bonificacao&quot;].sum()
kpi_b1, kpi_b2, kpi_b3, kpi_b4 = st.columns(4)
kpi_b1.metric(&quot;Total Bonificado&quot;, f&quot;R$ {fmt_ptbr(tot_bonf_val, 2)}&quot;)
kpi_b2.metric(&quot;Disponível&quot;, f&quot;R$ {fmt_ptbr(tot_disp_val, 2)}&quot;)
kpi_b3.metric(&quot;Parcialmente Utilizada&quot;, f&quot;R$ {fmt_ptbr(tot_parc_val, 2)}&quot;)
kpi_b4.metric(&quot;Totalmente Utilizada&quot;, f&quot;R$ {fmt_ptbr(tot_util_val, 2)}&quot;)
st.markdown(&quot;---&quot;)
pdf_bonf_bytes = gerar_pdf_bonificacoes(df_bonf)
st.download_button(
label=&quot;�� Descarregar Relatório de Bonificação em PDF&quot;,
data=pdf_bonf_bytes,
file_name=f&quot;Relatorio_Bonificacao_HortiControl_{datetime.now(ZoneInfo(&#39;America/Manaus&#39;)).strftime(&#39;%Y%m%d&#39;)}.
pdf&quot;,
mime=&quot;application/pdf&quot;,
type=&quot;primary&quot;,
key=&quot;btn_download_pdf_bonf&quot;
)
st.markdown(&quot;&quot;)
df_bonf_tabela = df_bonf.copy()
df_bonf_tabela[&quot;Valor (R$)&quot;] = df_bonf_tabela[&quot;valor_bonificacao&quot;].apply(lambda x: f&quot;R$
{fmt_ptbr(x, 2)}&quot;)
df_bonf_tabela[&quot;Anexo&quot;] = df_bonf_tabela.apply(lambda r: &quot;�� Disponível&quot; i
(r.get(&quot;caminho_anexo&quot;) and os.path.exists(r[&quot;caminho_anexo&quot;])) or r.get(&quot;anexo_b64&quot;) else &quot;Sem Anexo&quot;,
axis=1)
df_bonf_tabela = df_bonf_tabela.rename(columns={
&quot;numero_nota&quot;: &quot;N° Nota&quot;,
&quot;tipo_bonificacao&quot;: &quot;Tipo&quot;,
&quot;loja&quot;: &quot;Loja&quot;,
&quot;data_entrada&quot;: &quot;Data e Hora&quot;,
&quot;status&quot;: &quot;Status&quot;,
&quot;produto_hortifruti&quot;: &quot;Produto Hortifrúti&quot;
})
cols_exibidas = df_bonf_tabela[[&quot;N° Nota&quot;, &quot;Tipo&quot;, &quot;Loja&quot;, &quot;Data e Hora&quot;, &quot;Valor (R$)&quot;, &quot;Status&quot;,
&quot;Produto Hortifrúti&quot;, &quot;Anexo&quot;]]
cols_exibidas.index = range(1, len(cols_exibidas) + 1)
st.dataframe(cols_exibidas, use_container_width=True, height=350)

st.markdown(&quot;---&quot;)
st.subheader(&quot;�� Abertura de Anexo, Edição &amp; Exclusão de Registro&quot;)
opcoes_notas_editar = [(row[&quot;id&quot;], f&quot;Nota N° {row[&#39;numero_nota&#39;]} - {row[&#39;loja&#39;]} | Status:
{row[&#39;status&#39;]} ({row[&#39;data_entrada&#39;]})&quot;) for _, row in df_bonf.iterrows()]
col_ed1, col_ed2 = st.columns(2)
with col_ed1:
nota_selecionada_edicao = st.selectbox(&quot;Selecione o Registro para Gerenciar / Abrir Anexo&quot;,
options=opcoes_notas_editar, format_func=lambda x: x[1], key=&quot;sel_registro_bonf_gerenciar&quot;)
with col_ed2:
st.write(&quot;&quot;)
st.write(&quot;&quot;)
id_reg_atual = nota_selecionada_edicao[0]
reg_obj_atual = df_bonf[df_bonf[&quot;id&quot;] == id_reg_atual].iloc[0]
caminho_nota_alvo = reg_obj_atual.get(&quot;caminho_anexo&quot;, &quot;&quot;)
b64_anexo_reg = reg_obj_atual.get(&quot;anexo_b64&quot;, &quot;&quot;)
if caminho_nota_alvo or b64_anexo_reg:
if st.button(&quot;�� Abrir Anexo / Nota Fiscal&quot;, type=&quot;primary&quot;
key=&quot;btn_abrir_anexo_direto_tabela&quot;):
exibir_foto_modal(caminho_nota_alvo, b64_anexo_reg)
else:
st.warning(&quot;Este registo não possui ficheiro de nota anexado.&quot;)
with st.form(&quot;form_edicao_direta_bonificacao&quot;):
st.markdown(f&quot;**Editando Nota N° {reg_obj_atual[&#39;numero_nota&#39;]} ({reg_obj_atual[&#39;loja&#39;]})**&quot;)
data_atual_str = str(reg_obj_atual[&quot;data_entrada&quot;]).split(&quot; &quot;)[0] if
reg_obj_atual[&quot;data_entrada&quot;] else &quot;&quot;
try:
dt_obj_default = datetime.strptime(data_atual_str, &quot;%d/%m/%Y&quot;).date()
except Exception:
dt_obj_default = datetime.now(ZoneInfo(&quot;America/Manaus&quot;)).date()
col_e1, col_e2, col_e3, col_e4, col_e5 = st.columns(5)
with col_e1:
novo_val_nota_str = st.text_input(&quot;Valor (R$)&quot;,
value=str(reg_obj_atual[&quot;valor_bonificacao&quot;]).replace(&quot;.&quot;, &quot;,&quot;))
with col_e2:
lista_lojas_alt = [&quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA 04
MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;]
idx_loja_alt = lista_lojas_alt.index(reg_obj_atual[&quot;loja&quot;]) if reg_obj_atual[&quot;loja&quot;] in
lista_lojas_alt else 0
nova_loja_nota = st.selectbox(&quot;Loja&quot;, lista_lojas_alt, index=idx_loja_alt)
with col_e3:
nova_data_input = st.date_input(&quot;Data de Entrada&quot;, value=dt_obj_default,
format=&quot;DD/MM/YYYY&quot;)
with col_e4:
status_atuais_lst = [&quot;Disponível&quot;, &quot;Parcialmente Utilizada&quot;, &quot;Totalmente Utilizada&quot;]
idx_st_atual = status_atuais_lst.index(reg_obj_atual[&quot;status&quot;]) if
reg_obj_atual[&quot;status&quot;] in status_atuais_lst else 0
novo_st_nota = st.selectbox(&quot;Status&quot;, status_atuais_lst, index=idx_st_atual)
with col_e5:
novo_prod_nota = st.text_input(&quot;Produto Hortifrúti&quot;,
value=reg_obj_atual[&quot;produto_hortifruti&quot;])
novo_anexo_up = st.file_uploader(&quot;Substituir / Enviar Novo Anexo (Opcional)&quot;, type=[&quot;pdf&quot;,
&quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;])

col_btn_up1, col_btn_up2 = st.columns(2)
with col_btn_up1:
salvar_alt_bonf = st.form_submit_button(&quot;�� Salvar Alterações&quot;, type=&quot;primary&quot;)
with col_btn_up2:
excluir_bonf_btn = st.form_submit_button(&quot;��️ Excluir Bonificação&quot;, type=&quot;secondary&quot;)
if salvar_alt_bonf:
spinner_supernova(&quot;Salvando alterações...&quot;)
try:
val_f_edit = float(novo_val_nota_str.replace(&quot;.&quot;, &quot;&quot;).replace(&quot;,&quot;, &quot;.&quot;)) if
novo_val_nota_str else reg_obj_atual[&quot;valor_bonificacao&quot;]
hora_antiga = &quot;00:00:00&quot;
if len(str(reg_obj_atual[&quot;data_entrada&quot;]).split(&quot; &quot;)) &gt; 1:
hora_antiga = str(reg_obj_atual[&quot;data_entrada&quot;]).split(&quot; &quot;)[1]
nova_data_str = f&quot;{nova_data_input.strftime(&#39;%d/%m/%Y&#39;)} {hora_antiga}&quot;
path_novo_arq = reg_obj_atual[&quot;caminho_anexo&quot;]
b64_novo_arq = reg_obj_atual.get(&quot;anexo_b64&quot;, &quot;&quot;)
if novo_anexo_up:
path_novo_arq = os.path.join(&quot;uploads&quot;,
f&quot;NF_EDIT_{reg_obj_atual[&#39;numero_nota&#39;]}_{novo_anexo_up.name}&quot;)
bytes_up = novo_anexo_up.getbuffer()
with open(path_novo_arq, &quot;wb&quot;) as f_out: f_out.write(bytes_up)
b64_novo_arq = base64.b64encode(bytes_up).decode(&#39;utf-8&#39;)
conn_up_dir, db_t_upd = get_db_connection()
cursor_upd = conn_up_dir.cursor()
cursor_upd.execute(
&quot;UPDATE bonificacoes SET valor_bonificacao = %s, loja = %s, data_entrada = %s,
status = %s, produto_hortifruti = %s, caminho_anexo = %s, anexo_b64 = %s WHERE id = %s&quot; if db_t_upd ==
&quot;postgres&quot; else &quot;UPDATE bonificacoes SET valor_bonificacao = ?, loja = ?, data_entrada = ?, status = ?,
produto_hortifruti = ?, caminho_anexo = ?, anexo_b64 = ? WHERE id = ?&quot;,
(val_f_edit, nova_loja_nota, nova_data_str, novo_st_nota, novo_prod_nota,
path_novo_arq, b64_novo_arq, int(id_reg_atual) if db_t_upd == &quot;postgres&quot; else id_reg_atual)
)
conn_up_dir.commit()
conn_up_dir.close()
st.success(&quot;Registo atualizado com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao atualizar: {e}&quot;)
if excluir_bonf_btn:
spinner_supernova(&quot;Excluindo bonificação...&quot;)
try:
conn_del_b, db_td_b = get_db_connection()
cursor_db = conn_del_b.cursor()
cursor_db.execute(
&quot;DELETE FROM bonificacoes WHERE id = %s&quot; if db_td_b == &quot;postgres&quot; else &quot;DELETE
FROM bonificacoes WHERE id = ?&quot;,
(int(id_reg_atual) if db_td_b == &quot;postgres&quot; else id_reg_atual,)
)
conn_del_b.commit()
conn_del_b.close()
st.success(&quot;Bonificação excluída com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao excluir: {e}&quot;)
else: st.info(&quot;Nenhuma bonificação encontrada.&quot;)
# ---------------------------------------------------------

# 7. CONTROLE DE BAIXA DE AVARIAS
# ---------------------------------------------------------
elif menu == &quot;Controle de Baixa de Avarias&quot;:
st.title(&quot;�� Registro de Baixas das Avarias&quot;)
loja_ativa_sessao = user_info.get(&quot;loja_atual&quot;, &quot;LOJA 02 NOVA CIDADE&quot;)
if &quot;baixa_form_suffix&quot; not in st.session_state:
st.session_state[&quot;baixa_form_suffix&quot;] = 0
bx_suf = st.session_state[&quot;baixa_form_suffix&quot;]
conn_bx_chk, db_tbx_chk = get_db_connection()
df_baixar_hist = pd.read_sql_query(&quot;SELECT * FROM baixas_avarias&quot;, conn_bx_chk)
conn_bx_chk.close()
total_baixado_por_nota = {}
if not df_baixar_hist.empty:
totais_por_nf = df_baixar_hist.groupby(&quot;nf_b_entrada&quot;)[&quot;valor_total_avaria&quot;].sum()
for nf_e, val_bx in totais_por_nf.items():
total_baixado_por_nota[str(nf_e)] = float(val_bx)
conn_b_all, db_tb_all = get_db_connection()
df_todas_bonf = pd.read_sql_query(&quot;SELECT * FROM bonificacoes&quot;, conn_b_all)
if not df_todas_bonf.empty:
cur_st_up = conn_b_all.cursor()
for _, r_b in df_todas_bonf.iterrows():
num_nf_b = str(r_b[&quot;numero_nota&quot;])
val_orig_b = float(r_b[&quot;valor_bonificacao&quot;])
baixado_b = total_baixado_por_nota.get(num_nf_b, 0.0)
saldo_b = max(0.0, val_orig_b - baixado_b)
if baixado_b &lt;= 0:
novo_st_auto = &quot;Disponível&quot;
elif saldo_b &gt; 0:
novo_st_auto = &quot;Parcialmente Utilizada&quot;
else:
novo_st_auto = &quot;Totalmente Utilizada&quot;
if r_b[&quot;status&quot;] != novo_st_auto:
cur_st_up.execute(
&quot;UPDATE bonificacoes SET status = %s WHERE id = %s&quot; if db_tb_all == &quot;postgres&quot; else
&quot;UPDATE bonificacoes SET status = ? WHERE id = ?&quot;,
(novo_st_auto, int(r_b[&quot;id&quot;]) if db_tb_all == &quot;postgres&quot; else r_b[&quot;id&quot;])
)
conn_b_all.commit()
conn_b_all.close()
conn_b_all2, db_tb_all2 = get_db_connection()
df_todas_bonf = pd.read_sql_query(&quot;SELECT * FROM bonificacoes&quot;, conn_b_all2)
conn_b_all2.close()
dict_valor_orig_por_nf = {}
if not df_todas_bonf.empty:
for _, r_b in df_todas_bonf.iterrows():
dict_valor_orig_por_nf[str(r_b[&quot;numero_nota&quot;])] = float(r_b[&quot;valor_bonificacao&quot;])
if not df_todas_bonf.empty:
df_bonf_loja02 = df_todas_bonf[df_todas_bonf[&quot;loja&quot;].str.contains(&quot;02|NOVA CIDADE&quot;, case=False,
na=False) &amp; df_todas_bonf[&quot;status&quot;].isin([&quot;Disponível&quot;, &quot;Parcialmente Utilizada&quot;])]
else:

df_bonf_loja02 = pd.DataFrame()
notas_com_saldo_loja02 = []
saldo_geral_somado_loja02 = 0.0
if not df_bonf_loja02.empty:
for _, r_bonf in df_bonf_loja02.iterrows():
num_nf_ent = str(r_bonf[&quot;numero_nota&quot;])
val_original = float(r_bonf[&quot;valor_bonificacao&quot;])
ja_baixado = total_baixado_por_nota.get(num_nf_ent, 0.0)
saldo_restante_nota = max(0.0, val_original - ja_baixado)
if saldo_restante_nota &gt; 0:
saldo_geral_somado_loja02 += saldo_restante_nota
notas_com_saldo_loja02.append({
&quot;nf_entrada&quot;: num_nf_ent,
&quot;produto&quot;: r_bonf[&quot;produto_hortifruti&quot;],
&quot;valor_original&quot;: val_original,
&quot;saldo_restante&quot;: saldo_restante_nota
})
st.markdown(f&quot;&quot;&quot;
&lt;div style=&quot;display: flex; align-items: center; gap: 10px; background: rgba(30, 35, 42, 0.9);
padding: 12px 18px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.15); margin-bottom: 15px;&quot;&gt;
&lt;span style=&quot;font-size: 20px;&quot;&gt;��&lt;/span&gt;
&lt;span style=&quot;color: #FFFFFF; font-weight: 700; font-size: 15px;&quot;&gt;Saldo Total Disponível
(Referente às notas da Loja 02): R$ {fmt_ptbr(saldo_geral_somado_loja02, 2)}&lt;/span&gt;
&lt;/div&gt;
&quot;&quot;&quot;, unsafe_allow_html=True)
if notas_com_saldo_loja02:
with st.expander(&quot;�� Notas com Saldo Disponível (Loja 02 - Base para Baixas)&quot;, expanded=True):
df_ns_show = pd.DataFrame(notas_com_saldo_loja02)
df_ns_show[&quot;Valor Original (R$)&quot;] = df_ns_show[&quot;valor_original&quot;].apply(lambda x: f&quot;R$
{fmt_ptbr(x, 2)}&quot;)
df_ns_show[&quot;Saldo Disponível (R$)&quot;] = df_ns_show[&quot;saldo_restante&quot;].apply(lambda x: f&quot;R$
{fmt_ptbr(x, 2)}&quot;)
df_ns_show = df_ns_show.rename(columns={&quot;nf_entrada&quot;: &quot;N° Nota de Entrada&quot;, &quot;produto&quot;:
&quot;Produto Hortifrúti&quot;})
st.dataframe(df_ns_show[[&quot;N° Nota de Entrada&quot;, &quot;Produto Hortifrúti&quot;, &quot;Valor Original (R$)&quot;,
&quot;Saldo Disponível (R$)&quot;]], use_container_width=True, hide_index=True, height=200)
conn_prod_v, db_pv = get_db_connection()
cursor_pv = conn_prod_v.cursor()
cursor_pv.execute(&quot;SELECT codigo_produto, codigo_barras, nome FROM produtos ORDER BY nome&quot;)
prods_cad_v = cursor_pv.fetchall()
conn_prod_v.close()
lista_opcoes_prod_v = []
for p in prods_cad_v:
c_prod = p[0] if p[0] and str(p[0]).strip() else &quot;S/Cód&quot;
c_bar = p[1] if p[1] and str(p[1]).strip() else &quot;S/Barras&quot;
lista_opcoes_prod_v.append(f&quot;{c_prod} | Barras: {c_bar} | {p[2]}&quot;)
with st.expander(&quot;➕ Registrar Nova Baixa de Avaria&quot;, expanded=False):
with st.form(f&quot;form_registro_baixa_modelo_{bx_suf}&quot;, clear_on_submit=True):
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
lista_lojas_reg = [&quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA 04
MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;]

idx_l_ativa = lista_lojas_reg.index(loja_ativa_sessao) if loja_ativa_sessao in
lista_lojas_reg else 0
lojas_baixa_sel = st.selectbox(&quot;LOJAS&quot;, options=lista_lojas_reg, index=idx_l_ativa,
key=f&quot;bx_loja_{bx_suf}&quot;)
ref_bon_transf = st.text_input(&quot;Ref. Bon. transferen&quot;, value=&quot;&quot;,
placeholder=&quot;Referência...&quot;, key=f&quot;bx_ref_{bx_suf}&quot;)
with col_m2:
opcoes_nf_entrada = [item[&quot;nf_entrada&quot;] for item in notas_com_saldo_loja02] if
notas_com_saldo_loja02 else [&quot;Nenhuma Nota Disponível&quot;]
nf_b_entrada_sel = st.selectbox(&quot;NF de B. ENTRADA&quot;, options=opcoes_nf_entrada,
key=f&quot;bx_nf_ent_{bx_suf}&quot;)
prod_hort_sel = st.selectbox(&quot;Produto Hortifrúti&quot;, options=[&quot;&quot;] + lista_opcoes_prod_v,
index=0, key=f&quot;bx_prod_{bx_suf}&quot;)
with col_m3:
qtd_kg_cx_str = st.text_input(&quot;Qtd (kg/cx)&quot;, value=&quot;&quot;, placeholder=&quot;0,000&quot;,
key=f&quot;bx_qtd_{bx_suf}&quot;)
valor_total_avaria_str = st.text_input(&quot;Valor Total Avaria (R$)&quot;, value=&quot;&quot;,
placeholder=&quot;0,00&quot;, key=f&quot;bx_val_{bx_suf}&quot;)
nf_baixa_file = st.file_uploader(&quot;NF da baixa (Anexo)&quot;, type=[&quot;pdf&quot;, &quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;],
key=f&quot;bx_file_{bx_suf}&quot;)
col_dm1, col_dm2 = st.columns(2)
with col_dm1: data_baixa_man = st.date_input(&quot;Data da Baixa&quot;,
value=datetime.now(ZoneInfo(&quot;America/Manaus&quot;)), format=&quot;DD/MM/YYYY&quot;, key=f&quot;bx_dt_{bx_suf}&quot;)
with col_dm2:
hora_baixa_aut = datetime.now(ZoneInfo(&quot;America/Manaus&quot;)).strftime(&#39;%H:%M:%S&#39;)
st.text_input(&quot;Hora da Baixa&quot;, value=hora_baixa_aut, disabled=True,
key=f&quot;bx_hr_{bx_suf}&quot;)
data_hora_baixa_str = f&quot;{data_baixa_man.strftime(&#39;%d/%m/%Y&#39;)} {hora_baixa_aut}&quot; if
data_baixa_man else &quot;&quot;
btn_enviar_baixa = st.form_submit_button(&quot;✅ Registrar Baixa&quot;, type=&quot;primary&quot;)
if btn_enviar_baixa:
if not lojas_baixa_sel or not ref_bon_transf.strip() or nf_b_entrada_sel == &quot;Nenhuma Nota
Disponível&quot; or not prod_hort_sel:
st.error(&quot;Preencha todos os campos obrigatórios.&quot;)
else:
spinner_supernova(&quot;Registrando baixa de avaria...&quot;)
try:
qtd_val_f = float(qtd_kg_cx_str.replace(&quot;.&quot;, &quot;&quot;).replace(&quot;,&quot;, &quot;.&quot;)) if
qtd_kg_cx_str else 0.0
val_avaria_f = float(valor_total_avaria_str.replace(&quot;.&quot;, &quot;&quot;).replace(&quot;,&quot;, &quot;.&quot;))
if valor_total_avaria_str else 0.0
except ValueError:
qtd_val_f, val_avaria_f = 0.0, 0.0
nota_selecionada_dict = next((item for item in notas_com_saldo_loja02 if
item[&quot;nf_entrada&quot;] == nf_b_entrada_sel), None)
if not nota_selecionada_dict:
st.error(&quot;Nota de entrada inválida.&quot;)
elif val_avaria_f &gt; nota_selecionada_dict[&quot;saldo_restante&quot;]:
st.error(f&quot;❌ O valor da avaria ultrapassa o saldo restante da nota da Loja 02!&quot;)
else:
path_nf_baixa = &quot;&quot;
b64_nf_baixa = &quot;&quot;
if nf_baixa_file:

path_nf_baixa = os.path.join(&quot;uploads&quot;,
f&quot;NF_BAIXA_{ref_bon_transf}_{nf_baixa_file.name}&quot;)
bytes_baixa = nf_baixa_file.getbuffer()
with open(path_nf_baixa, &quot;wb&quot;) as f_out: f_out.write(bytes_baixa)
b64_nf_baixa = base64.b64encode(bytes_baixa).decode(&#39;utf-8&#39;)
saldo_disponivel_da_nota_referenciada = nota_selecionada_dict[&quot;saldo_restante&quot;]
novo_saldo_restante_nota = saldo_disponivel_da_nota_referenciada - val_avaria_f
try:
conn_ins, db_tins = get_db_connection()
cursor_ins = conn_ins.cursor()
cursor_ins.execute(
&quot;&quot;&quot;
INSERT INTO baixas_avarias (
loja_baixa, data_baixa, ref_bon_transferen, nf_baixa,
nf_b_entrada, produto_hortifruti, quantidade_kg_cx,
valor_total_avaria, saldo_restante_nota, saldo_total_disponivel,
nf_baixa_b64
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
&quot;&quot;&quot; if db_tins == &quot;postgres&quot; else &quot;&quot;&quot;
INSERT INTO baixas_avarias (
loja_baixa, data_baixa, ref_bon_transferen, nf_baixa,
nf_b_entrada, produto_hortifruti, quantidade_kg_cx,
valor_total_avaria, saldo_restante_nota, saldo_total_disponivel,
nf_baixa_b64
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
&quot;&quot;&quot;,
(
lojas_baixa_sel, data_hora_baixa_str, ref_bon_transf.strip(),
path_nf_baixa,
nf_b_entrada_sel, prod_hort_sel, qtd_val_f, val_avaria_f,
novo_saldo_restante_nota, saldo_disponivel_da_nota_referenciada, b64_nf_baixa
)
)
if &quot;02&quot; not in lojas_baixa_sel and &quot;NOVA CIDADE&quot; not in lojas_baixa_sel:
cursor_ins.execute(
&quot;UPDATE bonificacoes SET status = &#39;Totalmente Utilizada&#39; WHERE
numero_nota = %s&quot; if db_tins == &quot;postgres&quot; else &quot;UPDATE bonificacoes SET status = &#39;Totalmente Utilizada&#39;
WHERE numero_nota = ?&quot;,
(nf_b_entrada_sel,)
)
else:
st_auto_l2 = &quot;Totalmente Utilizada&quot; if novo_saldo_restante_nota &lt;= 0 else
&quot;Parcialmente Utilizada&quot;
cursor_ins.execute(
&quot;UPDATE bonificacoes SET status = %s WHERE numero_nota = %s&quot; if
db_tins == &quot;postgres&quot; else &quot;UPDATE bonificacoes SET status = ? WHERE numero_nota = ?&quot;,
(st_auto_l2, nf_b_entrada_sel)
)
conn_ins.commit()
conn_ins.close()
st.session_state[&quot;baixa_form_suffix&quot;] += 1
st.success(&quot;Baixa registrada com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro: {e}&quot;)

st.markdown(&quot;---&quot;)
st.subheader(&quot;�� Planilha de Registro de Baixas das Avarias&quot;)
lista_lojas_filtro_bx = [&quot;TODAS&quot;, &quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;, &quot;LOJA 04
MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;]
idx_filtro_bx = 0
if not is_admin and loja_atual_usuario in lista_lojas_filtro_bx:
idx_filtro_bx = lista_lojas_filtro_bx.index(loja_atual_usuario)
with st.expander(&quot;�� Filtros da Planilha de Baixas&quot;, expanded=True):
fb1, fb2, fb3 = st.columns(3)
with fb1: f_loja_bx = st.selectbox(&quot;Filtrar por Loja&quot;, options=lista_lojas_filtro_bx,
index=idx_filtro_bx, placeholder=&quot;Selecione...&quot;)
with fb2: f_ref_bx = st.text_input(&quot;Filtrar por Ref. Bon.&quot;, value=&quot;&quot;,
placeholder=&quot;Referência...&quot;)
with fb3: f_prod_bx = st.text_input(&quot;Filtrar por Produto&quot;, value=&quot;&quot;, placeholder=&quot;Produto...&quot;)
conn_bx_view, db_tbx_v = get_db_connection()
df_bx_table = pd.read_sql_query(&quot;SELECT * FROM baixas_avarias ORDER BY id DESC&quot;, conn_bx_view)
conn_bx_view.close()
if not df_bx_table.empty:
if f_loja_bx != &quot;TODAS&quot;: df_bx_table = df_bx_table[df_bx_table[&quot;loja_baixa&quot;] == f_loja_bx]
if f_ref_bx.strip(): df_bx_table =
df_bx_table[df_bx_table[&quot;ref_bon_transferen&quot;].str.contains(f_ref_bx.strip(), case=False, na=False)]
if f_prod_bx.strip(): df_bx_table =
df_bx_table[df_bx_table[&quot;produto_hortifruti&quot;].str.contains(f_prod_bx.strip(), case=False, na=False)]
if not df_bx_table.empty:
df_display_plan = df_bx_table.copy()
total_utilizado_por_nf = total_baixado_por_nota
saldo_calculado_list = []
utilizado_calculado_list = []
for _, row_bx in df_display_plan.iterrows():
nf_ent_item = str(row_bx[&quot;nf_b_entrada&quot;])
v_utilizado = total_utilizado_por_nf.get(nf_ent_item, float(row_bx[&quot;valor_total_avaria&quot;]))
utilizado_calculado_list.append(v_utilizado)
v_original = dict_valor_orig_por_nf.get(nf_ent_item, 0.0)
if v_original &gt; 0:
v_saldo_restante = max(0.0, v_original - v_utilizado)
else:
v_saldo_restante = float(row_bx[&quot;saldo_restante_nota&quot;])
saldo_calculado_list.append(v_saldo_restante)
df_display_plan[&quot;saldo_restante_calculado&quot;] = saldo_calculado_list
df_display_plan[&quot;saldo_total_utilizado&quot;] = utilizado_calculado_list
pdf_bytes_bx = gerar_pdf_baixas(df_display_plan)
st.download_button(
label=&quot;�� Descarregar Planilha de Baixas de Avarias em PDF&quot;,
data=pdf_bytes_bx,
file_name=f&quot;Registro_Baixas_Avarias_HortiControl_{datetime.now(ZoneInfo(&#39;America/Manaus&#39;)).strftime(&#39;%Y%m%d&#39;)
}.pdf&quot;,
mime=&quot;application/pdf&quot;,
type=&quot;primary&quot;,
key=&quot;btn_download_pdf_planilha_baixas&quot;

)
st.markdown(&quot;&quot;)
for _, r_bx in df_bx_table.iterrows():
if r_bx.get(&quot;nf_baixa_b64&quot;) and r_bx.get(&quot;nf_baixa&quot;):
salvar_arquivo_fisico_do_b64(r_bx[&quot;nf_baixa&quot;], r_bx[&quot;nf_baixa_b64&quot;])
df_display_plan[&quot;Qtd (kg/cx)&quot;] = df_display_plan[&quot;quantidade_kg_cx&quot;].apply(lambda x: fmt_ptbr(x,
3))
df_display_plan[&quot;Valor Total Avaria (R$)&quot;] = df_display_plan[&quot;valor_total_avaria&quot;].apply(lambda
x: f&quot;R$ {fmt_ptbr(x, 2)}&quot;)
df_display_plan[&quot;Saldo&quot;] = df_display_plan[&quot;saldo_restante_calculado&quot;].apply(lambda x: f&quot;R$
{fmt_ptbr(x, 2)}&quot;)
df_display_plan[&quot;Saldo Total Utilizado&quot;] = df_display_plan[&quot;saldo_total_utilizado&quot;].apply(lambda
x: f&quot;R$ {fmt_ptbr(x, 2)}&quot;)
df_display_plan[&quot;NF da baixa&quot;] = df_display_plan.apply(lambda r: &quot;Ver Anexo&quot; if
(r.get(&quot;nf_baixa&quot;) and os.path.exists(str(r[&quot;nf_baixa&quot;]))) or r.get(&quot;nf_baixa_b64&quot;) else &quot;S/Anexo&quot;, axis=1)
df_display_plan = df_display_plan.rename(columns={
&quot;loja_baixa&quot;: &quot;LOJAS&quot;,
&quot;data_baixa&quot;: &quot;Data Baixa&quot;,
&quot;ref_bon_transferen&quot;: &quot;Ref. Bon. transferen&quot;,
&quot;nf_b_entrada&quot;: &quot;NF da b. ENTRADA&quot;,
&quot;produto_hortifruti&quot;: &quot;Produto Hortifrúti&quot;
})
df_final_show = df_display_plan[[&quot;LOJAS&quot;, &quot;Data Baixa&quot;, &quot;Ref. Bon. transferen&quot;, &quot;NF da baixa&quot;,
&quot;NF da b. ENTRADA&quot;, &quot;Produto Hortifrúti&quot;, &quot;Qtd (kg/cx)&quot;, &quot;Valor Total Avaria (R$)&quot;, &quot;Saldo&quot;, &quot;Saldo Total
Utilizado&quot;]]
df_final_show.index = range(1, len(df_final_show) + 1)
st.dataframe(df_final_show, use_container_width=True, height=400)
st.markdown(&quot;---&quot;)
st.subheader(&quot;�� Gerenciamento: Editar ou Excluir Registro de Baixa&quot;)
opcoes_baixas_editar = [(row[&quot;id&quot;], f&quot;Loja: {row[&#39;loja_baixa&#39;]} | Ref:
{row[&#39;ref_bon_transferen&#39;]} | NF Ent: {row[&#39;nf_b_entrada&#39;]} (R$ {fmt_ptbr(row[&#39;valor_total_avaria&#39;], 2)})&quot;)
for _, row in df_bx_table.iterrows()]
if opcoes_baixas_editar:
baixa_selecionada_ed = st.selectbox(&quot;Selecione a Baixa para Editar ou Excluir&quot;,
options=opcoes_baixas_editar, format_func=lambda x: x[1], key=&quot;sel_baixa_gerenciar_edicao&quot;)
if baixa_selecionada_ed:
id_bx_atual = baixa_selecionada_ed[0]
reg_bx_atual = df_bx_table[df_bx_table[&quot;id&quot;] == id_bx_atual].iloc[0]
with st.form(&quot;form_edicao_baixa_avaria&quot;):
st.markdown(f&quot;**Editando Baixa (Ref: {reg_bx_atual[&#39;ref_bon_transferen&#39;]} - NF
Entrada Atual: {reg_bx_atual[&#39;nf_b_entrada&#39;]})**&quot;)
col_eb1, col_eb2, col_eb3 = st.columns(3)
with col_eb1:
lista_lojas_eb = [&quot;LOJA 01 CD&quot;, &quot;LOJA 02 NOVA CIDADE&quot;, &quot;LOJA 03 TERRA NOVA&quot;,
&quot;LOJA 04 MANOA&quot;, &quot;LOJA 05 ZUMBI&quot;, &quot;LOJA 06 OSWALDO FROTA&quot;, &quot;LOJA 07 MOSAICO&quot;]
idx_l_eb = lista_lojas_eb.index(reg_bx_atual[&quot;loja_baixa&quot;]) if
reg_bx_atual[&quot;loja_baixa&quot;] in lista_lojas_eb else 0
nova_loja_bx = st.selectbox(&quot;Loja da Baixa&quot;, lista_lojas_eb, index=idx_l_eb)

notas_disponiveis_edicao = [item[&quot;nf_entrada&quot;] for item in
notas_com_saldo_loja02]
if reg_bx_atual[&quot;nf_b_entrada&quot;] not in notas_disponiveis_edicao:
notas_disponiveis_edicao.insert(0, reg_bx_atual[&quot;nf_b_entrada&quot;])
idx_nf_atual = notas_disponiveis_edicao.index(reg_bx_atual[&quot;nf_b_entrada&quot;]) if
reg_bx_atual[&quot;nf_b_entrada&quot;] in notas_disponiveis_edicao else 0
nova_nf_b_entrada = st.selectbox(&quot;NF de B. ENTRADA&quot;,
options=notas_disponiveis_edicao, index=idx_nf_atual)
with col_eb2:
novo_ref_bx = st.text_input(&quot;Ref. Bon. transferen&quot;,
value=reg_bx_atual[&quot;ref_bon_transferen&quot;])
novo_prod_bx = st.text_input(&quot;Produto Hortifrúti&quot;,
value=reg_bx_atual[&quot;produto_hortifruti&quot;])
with col_eb3:
novo_qtd_bx_str = st.text_input(&quot;Qtd (kg/cx)&quot;,
value=str(reg_bx_atual[&quot;quantidade_kg_cx&quot;]).replace(&quot;.&quot;, &quot;,&quot;))
novo_val_bx_str = st.text_input(&quot;Valor Total Avaria (R$)&quot;,
value=str(reg_bx_atual[&quot;valor_total_avaria&quot;]).replace(&quot;.&quot;, &quot;,&quot;))
novo_anexo_bx_up = st.file_uploader(&quot;Substituir NF da Baixa (Opcional)&quot;, type=[&quot;pdf&quot;,
&quot;png&quot;, &quot;jpg&quot;, &quot;jpeg&quot;])
col_bnt_bx1, col_bnt_bx2 = st.columns(2)
with col_bnt_bx1:
salvar_alt_bx = st.form_submit_button(&quot;�� Salvar Alterações da Baixa&quot;
type=&quot;primary&quot;)
with col_bnt_bx2:
excluir_bx_btn = st.form_submit_button(&quot;��️ Excluir Registo de Baixa&quot;
type=&quot;secondary&quot;)
if salvar_alt_bx:
spinner_supernova(&quot;Atualizando baixa...&quot;)
try:
q_f_ed = float(novo_qtd_bx_str.replace(&quot;.&quot;, &quot;&quot;).replace(&quot;,&quot;, &quot;.&quot;)) if
novo_qtd_bx_str else reg_bx_atual[&quot;quantidade_kg_cx&quot;]
v_f_ed = float(novo_val_bx_str.replace(&quot;.&quot;, &quot;&quot;).replace(&quot;,&quot;, &quot;.&quot;)) if
novo_val_bx_str else reg_bx_atual[&quot;valor_total_avaria&quot;]
path_nf_bx_ed = reg_bx_atual.get(&quot;nf_baixa&quot;, &quot;&quot;)
b64_nf_bx_ed = reg_bx_atual.get(&quot;nf_baixa_b64&quot;, &quot;&quot;)
if novo_anexo_bx_up:
path_nf_bx_ed = os.path.join(&quot;uploads&quot;,
f&quot;NF_BAIXA_EDIT_{novo_ref_bx}_{novo_anexo_bx_up.name}&quot;)
bytes_bx_up = novo_anexo_bx_up.getbuffer()
with open(path_nf_bx_ed, &quot;wb&quot;) as f_out: f_out.write(bytes_bx_up)
b64_nf_bx_ed = base64.b64encode(bytes_bx_up).decode(&#39;utf-8&#39;)
nota_edit_dict = next((item for item in notas_com_saldo_loja02 if
item[&quot;nf_entrada&quot;] == nova_nf_b_entrada), None)
saldo_disp_edit = nota_edit_dict[&quot;saldo_restante&quot;] if nota_edit_dict else
reg_bx_atual[&quot;saldo_total_disponivel&quot;]
novo_saldo_restante_ed = saldo_disp_edit - v_f_ed
conn_up_bx, db_t_upbx = get_db_connection()
cur_upbx = conn_up_bx.cursor()
cur_upbx.execute(
&quot;UPDATE baixas_avarias SET loja_baixa = %s, ref_bon_transferen = %s,
nf_b_entrada = %s, produto_hortifruti = %s, quantidade_kg_cx = %s, valor_total_avaria = %s,
saldo_restante_nota = %s, saldo_total_disponivel = %s, nf_baixa = %s, nf_baixa_b64 = %s WHERE id = %s&quot; if

db_t_upbx == &quot;postgres&quot; else &quot;UPDATE baixas_avarias SET loja_baixa = ?, ref_bon_transferen = ?, nf_b_entrada
= ?, produto_hortifruti = ?, quantidade_kg_cx = ?, valor_total_avaria = ?, saldo_restante_nota = ?,
saldo_total_disponivel = ?, nf_baixa = ?, nf_baixa_b64 = ? WHERE id = ?&quot;,
(nova_loja_bx, novo_ref_bx.strip(), nova_nf_b_entrada, novo_prod_bx,
q_f_ed, v_f_ed, novo_saldo_restante_ed, saldo_disp_edit, path_nf_bx_ed, b64_nf_bx_ed, int(id_bx_atual) if
db_t_upbx == &quot;postgres&quot; else id_bx_atual)
)
conn_up_bx.commit()
conn_up_bx.close()
st.success(&quot;Baixa atualizada com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao atualizar baixa: {e}&quot;)
if excluir_bx_btn:
spinner_supernova(&quot;Excluindo baixa...&quot;)
try:
conn_del_bx, db_td_bx = get_db_connection()
cur_delbx = conn_del_bx.cursor()
cur_delbx.execute(
&quot;DELETE FROM baixas_avarias WHERE id = %s&quot; if db_td_bx == &quot;postgres&quot; else
&quot;DELETE FROM baixas_avarias WHERE id = ?&quot;,
(int(id_bx_atual) if db_td_bx == &quot;postgres&quot; else id_bx_atual,)
)
conn_del_bx.commit()
conn_del_bx.close()
st.success(&quot;Baixa excluída com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao excluir baixa: {e}&quot;)
st.markdown(&quot;---&quot;)
st.subheader(&quot;�� Visualizar Anexo de Baixa&quot;)
opcoes_baixas_ver = [(row[&quot;id&quot;], f&quot;Loja: {row[&#39;loja_baixa&#39;]} | Ref: {row[&#39;ref_bon_transferen&#39;]} |
NF Entrada: {row[&#39;nf_b_entrada&#39;]}&quot;) for _, row in df_bx_table.iterrows() if row.get(&quot;nf_baixa&quot;) or
row.get(&quot;nf_baixa_b64&quot;)]
if opcoes_baixas_ver:
escolha_bx_ver = st.selectbox(&quot;Selecione a baixa para abrir o comprovativo/anexo&quot;,
options=opcoes_baixas_ver, format_func=lambda x: x[1], placeholder=&quot;Selecione...&quot;)
if escolha_bx_ver:
reg_bx_escolhido = df_bx_table[df_bx_table[&quot;id&quot;] == escolha_bx_ver[0]].iloc[0]
if st.button(&quot;�� Abrir Anexo da Baixa Selecionada&quot;, type=&quot;primary&quot;):
exibir_foto_modal(reg_bx_escolhido.get(&quot;nf_baixa&quot;, &quot;&quot;),
reg_bx_escolhido.get(&quot;nf_baixa_b64&quot;, &quot;&quot;))
else:
st.info(&quot;Nenhuma baixa com anexo disponível.&quot;)
else:
st.info(&quot;Nenhum registo de baixa encontrado.&quot;)
elif menu == &quot;Relatórios &amp; Gráficos&quot; and is_admin:
st.title(&quot;�� Relatórios &amp; Business Intelligence (BI) Executive&quot;)
tab_bi_receb, tab_bi_bonf_avaria = st.tabs([
&quot;�� BI de Recebimento de Cargas&quot;,
&quot;�� BI Bonificações, Transferências &amp; Prevenção de Perdas&quot;
])
conn, db_type = get_db_connection()
df_roms = pd.read_sql_query(&quot;SELECT * FROM romaneios&quot;, conn)
df_itens = pd.read_sql_query(&quot;SELECT * FROM romaneio_itens&quot;, conn)
df_bonf_rel = pd.read_sql_query(&quot;SELECT * FROM bonificacoes&quot;, conn)
df_baixas_rel = pd.read_sql_query(&quot;SELECT * FROM baixas_avarias&quot;, conn)

conn.close()
with tab_bi_receb:
if df_roms.empty or df_itens.empty:
st.warning(&quot;Ainda não existem dados de recebimento cadastrados.&quot;)
else:
df_roms[&#39;data_dt&#39;] = pd.to_datetime(df_roms[&#39;data_recebimento&#39;], format=&#39;%d/%m/%Y&#39;,
errors=&#39;coerce&#39;)
df_full = df_itens.merge(df_roms, left_on=&#39;romaneio_id&#39;, right_on=&#39;id&#39;, suffixes=(&#39;_item&#39;,
&#39;_romaneio&#39;))
st.markdown(&quot;### �� Filtros da Análise Gerencial&quot;)
col_f0, col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1, 1, 1, 1])
with col_f0:
lista_tipos_op_bi = [&quot;TODOS OS TIPOS&quot;, &quot;Compra&quot;, &quot;Bonificação&quot;, &quot;Transferência&quot;,
&quot;Transferência/Bonificação&quot;, &quot;Troca por Troca&quot;]
tipo_op_bi_sel = st.selectbox(&quot;Tipo de Operação&quot;, options=lista_tipos_op_bi, index=0,
key=&quot;rel_filter_tipo_op&quot;)
with col_f1: loja_sel = st.selectbox(&quot;Filtrar por Loja&quot;, [&quot;TODAS AS LOJAS&quot;] +
list(df_roms[&quot;loja&quot;].unique()), placeholder=&quot;Selecione...&quot;, key=&quot;rel_filter_loja&quot;)
with col_f2: prod_sel = st.selectbox(&quot;Filtrar por Produto&quot;, [&quot;TODOS OS PRODUTOS&quot;] +
sorted(list(df_itens[&quot;produto&quot;].unique())), placeholder=&quot;Selecione...&quot;, key=&quot;rel_filter_prod&quot;)
with col_f3:
dt_min = df_roms[&#39;data_dt&#39;].min() if not df_roms[&#39;data_dt&#39;].isna().all() else
datetime.now(ZoneInfo(&quot;America/Manaus&quot;))
dt_inicio = st.date_input(&quot;Data Início&quot;, value=dt_min, format=&quot;DD/MM/YYYY&quot;,
key=&quot;rel_filter_dt_ini&quot;)
with col_f4:
dt_max = df_roms[&#39;data_dt&#39;].max() if not df_roms[&#39;data_dt&#39;].isna().all() else
datetime.now(ZoneInfo(&quot;America/Manaus&quot;))
dt_fim = st.date_input(&quot;Data Fim&quot;, value=dt_max, format=&quot;DD/MM/YYYY&quot;,
key=&quot;rel_filter_dt_fim&quot;)
df_filtrado = df_full.copy()
if tipo_op_bi_sel != &quot;TODOS OS TIPOS&quot;:
df_filtrado = df_filtrado[df_filtrado[&quot;tipo_operacao&quot;].str.contains(tipo_op_bi_sel,
case=False, na=False)]
if loja_sel != &quot;TODAS AS LOJAS&quot;:
df_filtrado = df_filtrado[df_filtrado[&quot;loja&quot;].str.contains(loja_sel, case=False,
na=False) | df_filtrado.get(&quot;loja_destino&quot;, pd.Series(dtype=str)).str.contains(loja_sel, case=False,
na=False)]
if prod_sel != &quot;TODOS OS PRODUTOS&quot;:
df_filtrado = df_filtrado[df_filtrado[&quot;produto&quot;] == prod_sel]
if dt_inicio and dt_fim:
df_filtrado = df_filtrado[(df_filtrado[&quot;data_dt&quot;] &gt;= pd.to_datetime(dt_inicio)) &amp;
(df_filtrado[&quot;data_dt&quot;] &lt;= pd.to_datetime(dt_fim))]
if df_filtrado.empty:
st.info(&quot;Nenhum registo encontrado para os filtros selecionados.&quot;)
else:
st.markdown(&quot;---&quot;)
st.subheader(&quot;�� Indicadores Principais &amp; Análise por Operação (KPIs no Período)&quot;)
tot_recebido = df_filtrado[&#39;valor_total&#39;].sum()
num_roms = df_filtrado[&#39;numero_romaneio&#39;].nunique()
val_troca = df_filtrado[df_filtrado[&#39;tipo_operacao&#39;].str.contains(&quot;Troca por Troca&quot;,
case=False, na=False)][&#39;valor_total&#39;].sum()
val_transf = df_filtrado[df_filtrado[&#39;tipo_operacao&#39;].str.contains(&quot;Transferência&quot;,
case=False, na=False)][&#39;valor_total&#39;].sum()

df_bx_periodo = df_baixas_rel.copy()
if not df_bx_periodo.empty:
df_bx_periodo[&#39;data_dt&#39;] = pd.to_datetime(df_bx_periodo[&#39;data_baixa&#39;].str.split(&#39;
&#39;).str[0], format=&#39;%d/%m/%Y&#39;, errors=&#39;coerce&#39;)
if loja_sel != &quot;TODAS AS LOJAS&quot;:
df_bx_periodo = df_bx_periodo[df_bx_periodo[&#39;loja_baixa&#39;].str.contains(loja_sel,
case=False, na=False)]
if prod_sel != &quot;TODOS OS PRODUTOS&quot;:
df_bx_periodo = df_bx_periodo[df_bx_periodo[&#39;produto_hortifruti&#39;] == prod_sel]
if dt_inicio and dt_fim:
df_bx_periodo = df_bx_periodo[(df_bx_periodo[&#39;data_dt&#39;] &gt;=
pd.to_datetime(dt_inicio)) &amp; (df_bx_periodo[&#39;data_dt&#39;] &lt;= pd.to_datetime(dt_fim))]
val_perdas_evitadas = df_bx_periodo[&#39;valor_total_avaria&#39;].sum() if not
df_bx_periodo.empty else 0.0
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
kpi1.metric(&quot;Valor Total Recebido&quot;, f&quot;R$ {fmt_ptbr(tot_recebido, 2)}&quot;)
kpi2.metric(&quot;Entradas no Período&quot;, f&quot;{num_roms} romaneios&quot;)
kpi3.metric(&quot;Total Transferências&quot;, f&quot;R$ {fmt_ptbr(val_transf, 2)}&quot;)
kpi4.metric(&quot;Total Troca por Troca&quot;, f&quot;R$ {fmt_ptbr(val_troca, 2)}&quot;)
kpi5.metric(&quot;Perdas Evitadas&quot;, f&quot;R$ {fmt_ptbr(val_perdas_evitadas, 2)}&quot;,
delta=&quot;Economia&quot;, delta_color=&quot;normal&quot;)
st.markdown(&quot;---&quot;)
col_g1, col_g2 = st.columns(2)
with col_g1:
st.markdown(&quot;#### Top Produtos por Valor no Período (R$)&quot;)
top_prods_val =
df_filtrado.groupby(&quot;produto&quot;)[&quot;valor_total&quot;].sum().nlargest(10).reset_index()
fig_val = px.bar(top_prods_val, x=&quot;produto&quot;, y=&quot;valor_total&quot;, text_auto=&quot;.2f&quot;,
color=&quot;valor_total&quot;, color_continuous_scale=&quot;Greens&quot;)
fig_val.update_layout(xaxis_title=&quot;Produto&quot;, yaxis_title=&quot;Total (R$)&quot;,
plot_bgcolor=&quot;rgba(0,0,0,0)&quot;, paper_bgcolor=&quot;rgba(0,0,0,0)&quot;, font_color=&quot;#FFFFFF&quot;)
st.plotly_chart(fig_val, use_container_width=True)
with col_g2:
st.markdown(&quot;#### Top Produtos por Quantidade/Peso no Período&quot;)
top_prods_qtd =
df_filtrado.groupby(&quot;produto&quot;)[&quot;quantidade&quot;].sum().nlargest(10).reset_index()
fig_qtd = px.bar(top_prods_qtd, x=&quot;produto&quot;, y=&quot;quantidade&quot;, text_auto=&quot;.2f&quot;,
color=&quot;quantidade&quot;, color_continuous_scale=&quot;Reds&quot;)
fig_qtd.update_layout(xaxis_title=&quot;Produto&quot;, yaxis_title=&quot;Qtd / Peso&quot;,
plot_bgcolor=&quot;rgba(0,0,0,0)&quot;, paper_bgcolor=&quot;rgba(0,0,0,0)&quot;, font_color=&quot;#FFFFFF&quot;)
st.plotly_chart(fig_qtd, use_container_width=True)
st.markdown(&quot;---&quot;)
st.subheader(&quot;�� Gráfico de Quantidades Movimentadas por Tipo de Operação no Período&quot;)
if not df_filtrado.empty:
df_qtd_op = df_filtrado.groupby([&quot;produto&quot;,
&quot;tipo_operacao&quot;])[&quot;quantidade&quot;].sum().reset_index()
fig_qtd_op = px.bar(
df_qtd_op, x=&quot;produto&quot;, y=&quot;quantidade&quot;, color=&quot;tipo_operacao&quot;,
barmode=&quot;group&quot;, text_auto=&quot;.2f&quot;,
labels={&quot;produto&quot;: &quot;Produto&quot;, &quot;quantidade&quot;: &quot;Quantidade / Peso Total&quot;,
&quot;tipo_operacao&quot;: &quot;Tipo de Operação&quot;}
)
fig_qtd_op.update_layout(xaxis_title=&quot;Produto&quot;, yaxis_title=&quot;Quantidade Movimentada&quot;,
plot_bgcolor=&quot;rgba(0,0,0,0)&quot;, paper_bgcolor=&quot;rgba(0,0,0,0)&quot;, font_color=&quot;#FFFFFF&quot;)

st.plotly_chart(fig_qtd_op, use_container_width=True)
else:
st.info(&quot;Sem dados de quantidade por operação para o período.&quot;)
st.markdown(&quot;---&quot;)
st.subheader(&quot;��️ Gráfico de Perdas Evitadas (Avarias Compensadas por Loja/Produto)&quot;)
if not df_bx_periodo.empty:
df_bx_grp_loja =
df_bx_periodo.groupby(&quot;loja_baixa&quot;)[&quot;valor_total_avaria&quot;].sum().reset_index()
fig_perdas = px.bar(
df_bx_grp_loja, x=&quot;loja_baixa&quot;, y=&quot;valor_total_avaria&quot;, text_auto=&quot;.2f&quot;,
color=&quot;valor_total_avaria&quot;, color_continuous_scale=&quot;Purples&quot;,
labels={&quot;loja_baixa&quot;: &quot;Loja&quot;, &quot;valor_total_avaria&quot;: &quot;Valor Evitado (R$)&quot;}
)
fig_perdas.update_layout(xaxis_title=&quot;Loja&quot;, yaxis_title=&quot;Perdas Evitadas (R$)&quot;,
plot_bgcolor=&quot;rgba(0,0,0,0)&quot;, paper_bgcolor=&quot;rgba(0,0,0,0)&quot;, font_color=&quot;#FFFFFF&quot;)
st.plotly_chart(fig_perdas, use_container_width=True)
else:
st.info(&quot;Nenhum registo de perdas evitadas/avarias encontrado para o período e
filtros selecionados.&quot;)
st.markdown(&quot;---&quot;)
st.download_button(label=&quot;�� Descarregar Relatório Consolidado (Excel / CSV)&quot;
data=df_filtrado.to_csv(index=False, sep=&#39;;&#39;).encode(&#39;utf-8-sig&#39;),
file_name=f&quot;Relatorio_Hortifruti_HortiControl_{datetime.now(ZoneInfo(&#39;America/Manaus&#39;)).strftime(&#39;%Y%m%d&#39;)}.c
sv&quot;, mime=&quot;text/csv&quot;, type=&quot;primary&quot;, key=&quot;btn_download_csv_relatorio&quot;)
with tab_bi_bonf_avaria:
st.subheader(&quot;�� Análise Executiva de Bonificações, Transferências &amp; Mitigação de Perdas&quot;)
st.markdown(&quot;Visão consolidada para a alta gerência sobre a **eficiência do processo de
conferência, bonificação e aproveitamento de avarias** para a saúde financeira do supermercado.&quot;)
with st.expander(&quot;�� Filtros Avançados para Apresentação à Liderança&quot;, expanded=True):
col_bi_f1, col_bi_f2, col_bi_f3, col_bi_f4 = st.columns(4)
todas_lojas_bi =
sorted(list(set(df_bonf_rel[&#39;loja&#39;].dropna().unique()).union(set(df_baixas_rel[&#39;loja_baixa&#39;].dropna().unique(
)))))
with col_bi_f1:
bi_loja_sel = st.selectbox(&quot;Filtrar por Loja&quot;, [&quot;TODAS AS LOJAS&quot;] + todas_lojas_bi,
key=&quot;bi_sel_loja&quot;)
todos_prods_bi =
sorted(list(set(df_bonf_rel[&#39;produto_hortifruti&#39;].dropna().unique()).union(set(df_baixas_rel[&#39;produto_hortifr
uti&#39;].dropna().unique()))))
with col_bi_f2:
bi_prod_sel = st.selectbox(&quot;Filtrar por Produto&quot;, [&quot;TODOS OS PRODUTOS&quot;] + todos_prods_bi,
key=&quot;bi_sel_prod&quot;)
with col_bi_f3:
bi_tipo_sel = st.selectbox(&quot;Tipo de Operação Bonificada&quot;, [&quot;TODOS&quot;, &quot;Bonificação&quot;,
&quot;Transferência de Bonificação&quot;], key=&quot;bi_sel_tipo&quot;)
with col_bi_f4:
bi_periodo = st.selectbox(&quot;Período de Análise&quot;, [&quot;Todo o Histórico&quot;, &quot;Últimos 30 dias&quot;,
&quot;Últimos 90 dias&quot;, &quot;Ano Atual&quot;], key=&quot;bi_sel_periodo&quot;)
df_b_sub = df_bonf_rel.copy()
df_bx_sub = df_baixas_rel.copy()

if not df_b_sub.empty:
df_b_sub[&#39;data_dt&#39;] = pd.to_datetime(df_b_sub[&#39;data_entrada&#39;].str.split(&#39; &#39;).str[0],
format=&#39;%d/%m/%Y&#39;, errors=&#39;coerce&#39;)
if bi_loja_sel != &quot;TODAS AS LOJAS&quot;: df_b_sub = df_b_sub[df_b_sub[&#39;loja&#39;] == bi_loja_sel]
if bi_prod_sel != &quot;TODOS OS PRODUTOS&quot;: df_b_sub = df_b_sub[df_b_sub[&#39;produto_hortifruti&#39;] ==
bi_prod_sel]
if bi_tipo_sel != &quot;TODOS&quot;: df_b_sub = df_b_sub[df_b_sub.get(&#39;tipo_bonificacao&#39;,
&#39;Bonificação&#39;) == bi_tipo_sel]
if bi_periodo == &quot;Últimos 30 dias&quot;:
df_b_sub = df_b_sub[df_b_sub[&#39;data_dt&#39;] &gt;= (datetime.now() - timedelta(days=30))]
elif bi_periodo == &quot;Últimos 90 dias&quot;:
df_b_sub = df_b_sub[df_b_sub[&#39;data_dt&#39;] &gt;= (datetime.now() - timedelta(days=90))]
elif bi_periodo == &quot;Ano Atual&quot;:
df_b_sub = df_b_sub[df_b_sub[&#39;data_dt&#39;].dt.year == datetime.now().year]
if not df_bx_sub.empty:
df_bx_sub[&#39;data_dt&#39;] = pd.to_datetime(df_bx_sub[&#39;data_baixa&#39;].str.split(&#39; &#39;).str[0],
format=&#39;%d/%m/%Y&#39;, errors=&#39;coerce&#39;)
if bi_loja_sel != &quot;TODAS AS LOJAS&quot;: df_bx_sub = df_bx_sub[df_bx_sub[&#39;loja_baixa&#39;] ==
bi_loja_sel]
if bi_prod_sel != &quot;TODOS OS PRODUTOS&quot;: df_bx_sub = df_bx_sub[df_bx_sub[&#39;produto_hortifruti&#39;]
== bi_prod_sel]
if bi_periodo == &quot;Últimos 30 dias&quot;:
df_bx_sub = df_bx_sub[df_bx_sub[&#39;data_dt&#39;] &gt;= (datetime.now() - timedelta(days=30))]
elif bi_periodo == &quot;Últimos 90 dias&quot;:
df_bx_sub = df_bx_sub[df_bx_sub[&#39;data_dt&#39;] &gt;= (datetime.now() - timedelta(days=90))]
elif bi_periodo == &quot;Ano Atual&quot;:
df_bx_sub = df_bx_sub[df_bx_sub[&#39;data_dt&#39;].dt.year == datetime.now().year]
v_tot_bonf = df_b_sub[df_b_sub.get(&#39;tipo_bonificacao&#39;, &#39;Bonificação&#39;) ==
&#39;Bonificação&#39;][&#39;valor_bonificacao&#39;].sum() if not df_b_sub.empty else 0.0
v_tot_transf = df_b_sub[df_b_sub.get(&#39;tipo_bonificacao&#39;, &#39;Bonificação&#39;) == &#39;Transferência de
Bonificação&#39;][&#39;valor_bonificacao&#39;].sum() if not df_b_sub.empty else 0.0
v_tot_entradas = df_b_sub[&#39;valor_bonificacao&#39;].sum() if not df_b_sub.empty else 0.0
v_tot_avarias_salvas = df_bx_sub[&#39;valor_total_avaria&#39;].sum() if not df_bx_sub.empty else 0.0
taxa_cobertura = (v_tot_avarias_salvas / v_tot_entradas * 100) if v_tot_entradas &gt; 0 else 0.0
v_saldo_remanescente = max(0.0, v_tot_entradas - v_tot_avarias_salvas)
st.markdown(&quot;---&quot;)
st.markdown(&quot;### �� Painel de Impacto Executivo&quot;)
kpi_e1, kpi_e2, kpi_e3, kpi_e4, kpi_e5 = st.columns(5)
kpi_e1.metric(&quot;1. Entradas Bonificadas&quot;, f&quot;R$ {fmt_ptbr(v_tot_bonf, 2)}&quot;, help=&quot;Valor total
obtido diretamente com fornecedores&quot;)
kpi_e2.metric(&quot;2. Transferências&quot;, f&quot;R$ {fmt_ptbr(v_tot_transf, 2)}&quot;, help=&quot;Valor total
redistribuído entre lojas da rede&quot;)
kpi_e3.metric(&quot;3. Perdas Evitadas (Avarias)&quot;, f&quot;R$ {fmt_ptbr(v_tot_avarias_salvas, 2)}&quot;,
delta=f&quot;{fmt_ptbr(v_tot_avarias_salvas, 2)} Salvos&quot;, delta_color=&quot;normal&quot;, help=&quot;Valor de perdas físicas
amortizadas por saldo de bonificação&quot;)
kpi_e4.metric(&quot;4. Taxa de Cobertura&quot;, f&quot;{fmt_ptbr(taxa_cobertura, 2)}%&quot;, help=&quot;Porcentagem de
bonificações convertida em amortização de perdas&quot;)
kpi_e5.metric(&quot;5. Saldo Remanescente&quot;, f&quot;R$ {fmt_ptbr(v_saldo_remanescente, 2)}&quot;, help=&quot;Saldo de
bonificação ainda disponível para compensação&quot;)
st.markdown(&quot;&quot;&quot;
&lt;div style=&quot;background: rgba(46, 125, 50, 0.25); border: 1px solid #4CAF50; border-radius: 8px;
padding: 12px 18px; margin: 15px 0;&quot;&gt;

&lt;span style=&quot;color: #81C784; font-weight: bold; font-size: 15px;&quot;&gt;��️ Mensagem para
Liderança:&lt;/span&gt;
&lt;span style=&quot;color: #FFFFFF; font-size: 14px;&quot;&gt; O processo de acompanhamento de bonificações
já garantiu uma &lt;b&gt;recuperação direta de R$ &lt;/span&gt;
&lt;span style=&quot;color: #FFF; font-weight: bold;&quot;&gt;{}&lt;/span&gt;
&lt;span style=&quot;color: #FFFFFF;&quot;&gt; em avarias que seriam registradas como prejuízo líquido direto
para a empresa.&lt;/span&gt;
&lt;/div&gt;
&quot;&quot;&quot;.format(fmt_ptbr(v_tot_avarias_salvas, 2)), unsafe_allow_html=True)
st.markdown(&quot;---&quot;)
st.markdown(&quot;### �� Gráficos Analíticos de Desempenho &amp; Quantidades Evitadas&quot;)
bg_bi1, bg_bi2 = st.columns(2)
with bg_bi1:
st.markdown(&quot;#### Entradas por Tipo e Loja (R$)&quot;)
if not df_b_sub.empty:
fig_lojas = px.bar(
df_b_sub, x=&quot;loja&quot;, y=&quot;valor_bonificacao&quot;, color=&quot;tipo_bonificacao&quot;,
barmode=&quot;group&quot;, text_auto=&quot;.2f&quot;,
color_discrete_map={&quot;Bonificação&quot;: &quot;#4CAF50&quot;, &quot;Transferência de Bonificação&quot;:
&quot;#2196F3&quot;}
)
fig_lojas.update_layout(xaxis_title=&quot;Loja&quot;, yaxis_title=&quot;Valor (R$)&quot;,
plot_bgcolor=&quot;rgba(0,0,0,0)&quot;, paper_bgcolor=&quot;rgba(0,0,0,0)&quot;, font_color=&quot;#FFFFFF&quot;)
st.plotly_chart(fig_lojas, use_container_width=True)
else:
st.info(&quot;Sem dados para a combinação de filtros.&quot;)
with bg_bi2:
st.markdown(&quot;#### Avarias Bonificadas por Loja (Economia Gerada)&quot;)
if not df_bx_sub.empty:
df_bx_grp = df_bx_sub.groupby(&quot;loja_baixa&quot;)[&quot;valor_total_avaria&quot;].sum().reset_index()
fig_avarias = px.bar(df_bx_grp, x=&quot;loja_baixa&quot;, y=&quot;valor_total_avaria&quot;, text_auto=&quot;.2f&quot;,
color=&quot;valor_total_avaria&quot;, color_continuous_scale=&quot;Purples&quot;)
fig_avarias.update_layout(xaxis_title=&quot;Loja da Baixa&quot;, yaxis_title=&quot;Avaria Coberta (R$)&quot;,
plot_bgcolor=&quot;rgba(0,0,0,0)&quot;, paper_bgcolor=&quot;rgba(0,0,0,0)&quot;, font_color=&quot;#FFFFFF&quot;)
st.plotly_chart(fig_avarias, use_container_width=True)
else:
st.info(&quot;Sem dados de baixas para os filtros.&quot;)
st.markdown(&quot;#### �� Quantidade (Kg / Unidades / Caixas) de Produtos com Perdas Evitadas po
Baixas&quot;)
if not df_bx_sub.empty:
df_bx_qtd_prod =
df_bx_sub.groupby(&quot;produto_hortifruti&quot;)[&quot;quantidade_kg_cx&quot;].sum().reset_index()
fig_qtd_avarias = px.bar(
df_bx_qtd_prod, x=&quot;produto_hortifruti&quot;, y=&quot;quantidade_kg_cx&quot;, text_auto=&quot;.3f&quot;,
color=&quot;quantidade_kg_cx&quot;, color_continuous_scale=&quot;Greens&quot;,
labels={&quot;produto_hortifruti&quot;: &quot;Produto&quot;, &quot;quantidade_kg_cx&quot;: &quot;Quantidade Total
(Kg/Unid/Cx)&quot;}
)
fig_qtd_avarias.update_layout(xaxis_title=&quot;Produto&quot;, yaxis_title=&quot;Volume Salvo (Qtd/Peso)&quot;,
plot_bgcolor=&quot;rgba(0,0,0,0)&quot;, paper_bgcolor=&quot;rgba(0,0,0,0)&quot;, font_color=&quot;#FFFFFF&quot;)
st.plotly_chart(fig_qtd_avarias, use_container_width=True)
else:
st.info(&quot;Sem dados de quantidades de avarias para o período.&quot;)
bg_bi3, bg_bi4 = st.columns(2)
with bg_bi3:

st.markdown(&quot;#### Top Produtos Beneficiados por Bonificação&quot;)
if not df_b_sub.empty:
df_p_bonf =
df_b_sub.groupby(&quot;produto_hortifruti&quot;)[&quot;valor_bonificacao&quot;].sum().nlargest(7).reset_index()
fig_prod_b = px.bar(df_p_bonf, y=&quot;produto_hortifruti&quot;, x=&quot;valor_bonificacao&quot;,
orientation=&quot;h&quot;, text_auto=&quot;.2f&quot;, color=&quot;valor_bonificacao&quot;, color_continuous_scale=&quot;Teal&quot;)
fig_prod_b.update_layout(xaxis_title=&quot;Total (R$)&quot;, yaxis_title=&quot;Produto&quot;,
plot_bgcolor=&quot;rgba(0,0,0,0)&quot;, paper_bgcolor=&quot;rgba(0,0,0,0)&quot;, font_color=&quot;#FFFFFF&quot;)
st.plotly_chart(fig_prod_b, use_container_width=True)
else:
st.info(&quot;Sem dados de produtos.&quot;)
with bg_bi4:
st.markdown(&quot;#### Distribuição do Status de Notas de Bonificação&quot;)
if not df_b_sub.empty:
fig_st_pie = px.pie(df_b_sub, names=&quot;status&quot;, values=&quot;valor_bonificacao&quot;, hole=0.4,
color_discrete_sequence=px.colors.qualitative.Pastel)
fig_st_pie.update_layout(plot_bgcolor=&quot;rgba(0,0,0,0)&quot;, paper_bgcolor=&quot;rgba(0,0,0,0)&quot;,
font_color=&quot;#FFFFFF&quot;)
st.plotly_chart(fig_st_pie, use_container_width=True)
else:
st.info(&quot;Sem status para exibir.&quot;)
st.markdown(&quot;---&quot;)
st.markdown(&quot;### �� Geração de Relatório Executivo em PDF&quot;)
metrics_dict = {
&quot;tot_bonf&quot;: v_tot_bonf,
&quot;tot_transf&quot;: v_tot_transf,
&quot;tot_avaria&quot;: v_tot_avarias_salvas,
&quot;taxa_cobertura&quot;: taxa_cobertura,
&quot;saldo_restante&quot;: v_saldo_remanescente
}
pdf_bi_bytes = gerar_pdf_relatorio_gerencial_bi(metrics_dict, df_b_sub, df_bx_sub)
col_pdf_bi1, col_pdf_bi2 = st.columns([3, 1])
with col_pdf_bi1:
st.markdown(&quot;Gere um relatório em PDF para apresentações de resultados em reuniões com a
diretoria.&quot;)
with col_pdf_bi2:
st.download_button(
label=&quot;�� Baixar PDF Executivo&quot;,
data=pdf_bi_bytes,
file_name=f&quot;Relatorio_Executivo_Lideranca_HortiControl_{datetime.now(ZoneInfo(&#39;America/Manaus&#39;)).strftime(&#39;%Y
%m%d_%H%M&#39;)}.pdf&quot;,
mime=&quot;application/pdf&quot;,
type=&quot;primary&quot;,
key=&quot;btn_download_executivo_bi&quot;
)
elif menu == &quot;Gerenciar Cadastros (Produtos)&quot; and is_admin:
st.title(&quot;���� Gerenciamento e Cadastro (Produtos &amp; Fornecedores)&quot;)
tab_prod, tab_forn = st.tabs([&quot;�� Cadastro de Produtos&quot;, &quot;�� Cadastro de Fornecedores&quot;])
with tab_prod:
with st.expander(&quot;➕ Cadastrar Novo Produto&quot;, expanded=False):
with st.form(&quot;cad_prod_form&quot;, clear_on_submit=True):
col_cp1, col_cp2, col_cp3, col_cp4 = st.columns([2, 2, 3, 1.5])
with col_cp1: cod_prod_input = st.text_input(&quot;Código do Produto&quot;, value=&quot;&quot;,
placeholder=&quot;Cód...&quot;)

with col_cp2: cod_bar_input = st.text_input(&quot;Código de Barras&quot;, value=&quot;&quot;,
placeholder=&quot;Código de barras...&quot;)
with col_cp3: nome_p = st.text_input(&quot;Nome do Produto *&quot;, value=&quot;&quot;, placeholder=&quot;Nome do
produto...&quot;)
with col_cp4: und_p = st.selectbox(&quot;Unidade&quot;, [&quot;KG&quot;, &quot;UNID&quot;, &quot;GRM&quot;, &quot;CX&quot;], index=0)
if st.form_submit_button(&quot;➕ Cadastrar Produto&quot;, type=&quot;primary&quot;):
if not nome_p.strip(): st.error(&quot;O Nome é obrigatório.&quot;)
else:
spinner_supernova(&quot;Cadastrando produto...&quot;)
conn, db_type = get_db_connection()
cursor = conn.cursor()
try:
cursor.execute(&quot;INSERT INTO produtos (codigo_barras, codigo_produto, nome,
unidade_padrao) VALUES (%s, %s, %s, %s)&quot; if db_type == &quot;postgres&quot; else &quot;INSERT INTO produtos (codigo_barras,
codigo_produto, nome, unidade_padrao) VALUES (?, ?, ?, ?)&quot;, (cod_bar_input.strip() if cod_bar_input else
None, cod_prod_input.strip() if cod_prod_input else None, nome_p.strip().upper(), und_p))
conn.commit()
st.success(&quot;Cadastrado com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro: {e}&quot;)
finally: conn.close()
st.markdown(&quot;---&quot;)
conn, db_type = get_db_connection()
cursor = conn.cursor()
cursor.execute(&quot;SELECT id, codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos
ORDER BY nome&quot;)
produtos_cadastrados = cursor.fetchall()
conn.close()
if produtos_cadastrados:
produtos_com_id_ajustado = [(i, p[1], p[2], p[3], p[4], p[0]) for i, p in
enumerate(produtos_cadastrados, 1)]
df_produtos = pd.DataFrame(produtos_com_id_ajustado, columns=[&quot;ID&quot;, &quot;Código de Barras&quot;,
&quot;Código do Produto&quot;, &quot;Nome do Produto&quot;, &quot;Unidade Padrão&quot;, &quot;ID_Real&quot;])
st.download_button(label=&quot;�� Descarregar Relatório de Produtos em PDF&quot;
data=gerar_pdf_produtos(produtos_cadastrados),
file_name=f&quot;Relatorio_Produtos_HortiControl_{datetime.now(ZoneInfo(&#39;America/Manaus&#39;)).strftime(&#39;%Y%m%d&#39;)}.pdf
&quot;, mime=&quot;application/pdf&quot;, type=&quot;primary&quot;)
st.markdown(&quot;&quot;)
st.dataframe(df_produtos[[&quot;ID&quot;, &quot;Código do Produto&quot;, &quot;Código de Barras&quot;, &quot;Nome do Produto&quot;,
&quot;Unidade Padrão&quot;]], use_container_width=True, hide_index=True, height=250)
st.markdown(&quot;### ✏️ Editar ou Excluir Produto&quot;)
opcoes_edit_prod = [(p[5], f&quot;{p[3]} (Cód: {p[2] or &#39;S/Cód&#39;})&quot;) for p in
produtos_com_id_ajustado]
prod_sel_ed = st.selectbox(&quot;Selecione o produto para editar ou excluir&quot;,
options=opcoes_edit_prod, format_func=lambda x: x[1], key=&quot;sel_prod_editar&quot;)
if prod_sel_ed:
id_p_ed = prod_sel_ed[0]
conn_p_det, db_tp_det = get_db_connection()
cur_pd = conn_p_det.cursor()
cur_pd.execute(&quot;SELECT codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos
WHERE id = %s&quot; if db_tp_det == &quot;postgres&quot; else &quot;SELECT codigo_barras, codigo_produto, nome, unidade_padrao
FROM produtos WHERE id = ?&quot;, (int(id_p_ed) if db_tp_det == &quot;postgres&quot; else id_p_ed,))
dados_p_atual = cur_pd.fetchone()
conn_p_det.close()
if dados_p_atual:
with st.form(&quot;form_edit_produto&quot;):

ep_cod_bar = st.text_input(&quot;Código de Barras&quot;, value=dados_p_atual[0] or &quot;&quot;)
ep_cod_prod = st.text_input(&quot;Código do Produto&quot;, value=dados_p_atual[1] or &quot;&quot;)
ep_nome = st.text_input(&quot;Nome do Produto&quot;, value=dados_p_atual[2] or &quot;&quot;)
lista_unds = [&quot;KG&quot;, &quot;UNID&quot;, &quot;GRM&quot;, &quot;CX&quot;]
idx_u = lista_unds.index(dados_p_atual[3]) if dados_p_atual[3] in lista_unds else
0
ep_und = st.selectbox(&quot;Unidade&quot;, lista_unds, index=idx_u)
col_bp1, col_bp2 = st.columns(2)
with col_bp1: btn_salvar_prod = st.form_submit_button(&quot;�� Salvar Alterações&quot;
type=&quot;primary&quot;)
with col_bp2: btn_excluir_prod = st.form_submit_button(&quot;��️ Excluir Produto&quot;
type=&quot;secondary&quot;)
if btn_salvar_prod:
spinner_supernova(&quot;Atualizando produto...&quot;)
try:
conn_up_p, db_tup = get_db_connection()
cur_upp = conn_up_p.cursor()
cur_upp.execute(
&quot;UPDATE produtos SET codigo_barras = %s, codigo_produto = %s, nome =
%s, unidade_padrao = %s WHERE id = %s&quot; if db_tup == &quot;postgres&quot; else &quot;UPDATE produtos SET codigo_barras = ?,
codigo_produto = ?, nome = ?, unidade_padrao = ? WHERE id = ?&quot;,
(ep_cod_bar.strip(), ep_cod_prod.strip(), ep_nome.strip().upper(),
ep_und, int(id_p_ed) if db_tup == &quot;postgres&quot; else id_p_ed)
)
conn_up_p.commit()
conn_up_p.close()
st.success(&quot;Produto atualizado com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao atualizar: {e}&quot;)
if btn_excluir_prod:
spinner_supernova(&quot;Excluindo produto...&quot;)
try:
conn_del_p, db_tdp = get_db_connection()
cur_delp = conn_del_p.cursor()
cur_delp.execute(&quot;DELETE FROM produtos WHERE id = %s&quot; if db_tdp ==
&quot;postgres&quot; else &quot;DELETE FROM produtos WHERE id = ?&quot;, (int(id_p_ed) if db_tdp == &quot;postgres&quot; else id_p_ed,))
conn_del_p.commit()
conn_del_p.close()
st.success(&quot;Produto excluído com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao excluir: {e}&quot;)
else: st.info(&quot;Nenhum produto cadastrado.&quot;)
with tab_forn:
with st.expander(&quot;➕ Cadastrar Novo Fornecedor&quot;, expanded=False):
with st.form(&quot;cad_forn_form&quot;, clear_on_submit=True):
col_fc1, col_fc2, col_fc3 = st.columns([2, 2, 3])
with col_fc1: f_cod_input = st.text_input(&quot;Código&quot;, value=&quot;&quot;, placeholder=&quot;Código...&quot;)
with col_fc2: f_cnpj_input = st.text_input(&quot;CNPJ&quot;, value=&quot;&quot;,
placeholder=&quot;00.000.000/0000-00&quot;)
with col_fc3: f_nome_input = st.text_input(&quot;Nome / Razão Social *&quot;, value=&quot;&quot;,
placeholder=&quot;Razão social...&quot;)
if st.form_submit_button(&quot;➕ Cadastrar Fornecedor&quot;, type=&quot;primary&quot;):
if not f_nome_input.strip(): st.error(&quot;O Nome é obrigatório.&quot;)
else:
spinner_supernova(&quot;Cadastrando fornecedor...&quot;)

conn, db_type = get_db_connection()
cursor = conn.cursor()
try:
cursor.execute(&quot;INSERT INTO fornecedores (codigo_fornecedor, cnpj, nome)
VALUES (%s, %s, %s)&quot; if db_type == &quot;postgres&quot; else &quot;INSERT INTO fornecedores (codigo_fornecedor, cnpj, nome)
VALUES (?, ?, ?)&quot;, (f_cod_input.strip() if f_cod_input else None, f_cnpj_input.strip() if f_cnpj_input else
None, f_nome_input.strip().upper()))
conn.commit()
st.success(&quot;Cadastrado com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro: {e}&quot;)
finally: conn.close()
st.markdown(&quot;---&quot;)
conn, db_type = get_db_connection()
cursor = conn.cursor()
cursor.execute(&quot;SELECT id, codigo_fornecedor, cnpj, nome FROM fornecedores ORDER BY nome&quot;)
fornecedores_cadastrados = cursor.fetchall()
conn.close()
if fornecedores_cadastrados:
forn_com_id_ajustado = [(i, f[1], f[2], f[3], f[0]) for i, f in
enumerate(fornecedores_cadastrados, 1)]
df_forn_show = pd.DataFrame(forn_com_id_ajustado, columns=[&quot;ID&quot;, &quot;Código&quot;, &quot;CNPJ&quot;, &quot;Nome do
Fornecedor&quot;, &quot;ID_Real&quot;])
st.dataframe(df_forn_show[[&quot;ID&quot;, &quot;Código&quot;, &quot;CNPJ&quot;, &quot;Nome do Fornecedor&quot;]],
use_container_width=True, hide_index=True, height=250)
st.markdown(&quot;### ✏️ Editar ou Excluir Fornecedor&quot;)
opcoes_edit_forn = [(f[4], f&quot;{f[3]} (Cód: {f[1] or &#39;S/Cód&#39;})&quot;) for f in forn_com_id_ajustado]
forn_sel_ed = st.selectbox(&quot;Selecione o fornecedor para editar ou excluir&quot;,
options=opcoes_edit_forn, format_func=lambda x: x[1], key=&quot;sel_forn_editar&quot;)
if forn_sel_ed:
id_f_ed = forn_sel_ed[0]
conn_f_det, db_tf_det = get_db_connection()
cur_fd = conn_f_det.cursor()
cur_fd.execute(&quot;SELECT codigo_fornecedor, cnpj, nome FROM fornecedores WHERE id = %s&quot; if
db_tf_det == &quot;postgres&quot; else &quot;SELECT codigo_fornecedor, cnpj, nome FROM fornecedores WHERE id = ?&quot;,
(int(id_f_ed) if db_tf_det == &quot;postgres&quot; else id_f_ed,))
dados_f_atual = cur_fd.fetchone()
conn_f_det.close()
if dados_f_atual:
with st.form(&quot;form_edit_fornecedor&quot;):
ef_cod = st.text_input(&quot;Código do Fornecedor&quot;, value=dados_f_atual[0] or &quot;&quot;)
ef_cnpj = st.text_input(&quot;CNPJ&quot;, value=dados_f_atual[1] or &quot;&quot;)
ef_nome = st.text_input(&quot;Nome / Razão Social&quot;, value=dados_f_atual[2] or &quot;&quot;)
col_bf1, col_bf2 = st.columns(2)
with col_bf1: btn_salvar_forn = st.form_submit_button(&quot;�� Salvar Alterações&quot;
type=&quot;primary&quot;)
with col_bf2: btn_excluir_forn = st.form_submit_button(&quot;��️ Excluir Fornecedor&quot;
type=&quot;secondary&quot;)
if btn_salvar_forn:
spinner_supernova(&quot;Atualizando fornecedor...&quot;)
try:
conn_up_f, db_tupf = get_db_connection()
cur_upf = conn_up_f.cursor()
cur_upf.execute(

&quot;UPDATE fornecedores SET codigo_fornecedor = %s, cnpj = %s, nome = %s
WHERE id = %s&quot; if db_tupf == &quot;postgres&quot; else &quot;UPDATE fornecedores SET codigo_fornecedor = ?, cnpj = ?, nome =
? WHERE id = ?&quot;,
(ef_cod.strip(), ef_cnpj.strip(), ef_nome.strip().upper(),
int(id_f_ed) if db_tupf == &quot;postgres&quot; else id_f_ed)
)
conn_up_f.commit()
conn_up_f.close()
st.success(&quot;Fornecedor atualizado com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao atualizar: {e}&quot;)
if btn_excluir_forn:
spinner_supernova(&quot;Excluindo fornecedor...&quot;)
try:
conn_del_f, db_tdf = get_db_connection()
cur_delf = conn_del_f.cursor()
cur_delf.execute(&quot;DELETE FROM fornecedores WHERE id = %s&quot; if db_tdf ==
&quot;postgres&quot; else &quot;DELETE FROM fornecedores WHERE id = ?&quot;, (int(id_f_ed) if db_tdf == &quot;postgres&quot; else
id_f_ed,))
conn_del_f.commit()
conn_del_f.close()
st.success(&quot;Fornecedor excluído com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao excluir: {e}&quot;)
else: st.info(&quot;Nenhum fornecedor cadastrado.&quot;)
elif menu == &quot;Gerenciar Usuários &amp; Permissões&quot; and is_admin:
st.title(&quot;�� Gerenciamento de Usuários e Permissões&quot;)
with st.expander(&quot;➕ Cadastrar Novo Usuário&quot;, expanded=False):
with st.form(&quot;cad_usuario_form&quot;, clear_on_submit=True):
col_u1, col_u2, col_u3, col_u4 = st.columns([2.5, 2, 2, 1.5])
with col_u1: novo_nome = st.text_input(&quot;Nome Completo&quot;, value=&quot;&quot;, placeholder=&quot;Nome...&quot;)
with col_u2: novo_login = st.text_input(&quot;Login&quot;, value=&quot;&quot;, placeholder=&quot;Login...&quot;)
with col_u3: nova_senha = st.text_input(&quot;Senha&quot;, type=&quot;password&quot;, value=&quot;&quot;,
placeholder=&quot;Senha...&quot;)
with col_u4: novo_perfil = st.selectbox(&quot;Perfil&quot;, [&quot;Conferente&quot;, &quot;Gestor&quot;], index=0,
placeholder=&quot;Selecione...&quot;)
if st.form_submit_button(&quot;➕ Cadastrar&quot;, type=&quot;primary&quot;):
if not novo_nome.strip() or not novo_login.strip() or not nova_senha.strip():
st.error(&quot;Preencha todos os campos.&quot;)
else:
spinner_supernova(&quot;Cadastrando usuário...&quot;)
conn, db_type = get_db_connection()
cursor = conn.cursor()
try:
cursor.execute(&quot;INSERT INTO usuarios (nome, login, senha, perfil) VALUES (%s, %s,
%s, %s)&quot; if db_type == &quot;postgres&quot; else &quot;INSERT INTO usuarios (nome, login, senha, perfil) VALUES (?, ?, ?,
?)&quot;, (novo_nome.strip(), novo_login.strip(), nova_senha.strip(), novo_perfil))
conn.commit()
st.success(&quot;Cadastrado com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro: {e}&quot;)
finally: conn.close()
st.markdown(&quot;---&quot;)
conn, db_type = get_db_connection()
cursor = conn.cursor()
cursor.execute(&quot;SELECT id, nome, login, senha, perfil FROM usuarios ORDER BY id&quot;)
usuarios_cadastrados = cursor.fetchall()

conn.close()
if usuarios_cadastrados:
usuarios_com_id_ajustado = [(i, u[1], u[2], u[3], u[4], u[0]) for i, u in
enumerate(usuarios_cadastrados, 1)]
df_usuarios = pd.DataFrame(usuarios_com_id_ajustado, columns=[&quot;ID&quot;, &quot;Nome Completo&quot;, &quot;Login&quot;,
&quot;Senha&quot;, &quot;Perfil&quot;, &quot;ID_Real&quot;])
st.dataframe(df_usuarios[[&quot;ID&quot;, &quot;Nome Completo&quot;, &quot;Login&quot;, &quot;Senha&quot;, &quot;Perfil&quot;]],
use_container_width=True, hide_index=True, height=250)
st.markdown(&quot;### ✏️ Editar ou Excluir Utilizador&quot;)
opcoes_edit_usr = [(u[5], f&quot;{u[1]} (Login: {u[2]})&quot;) for u in usuarios_com_id_ajustado]
usr_sel_ed = st.selectbox(&quot;Selecione o utilizador para editar ou excluir&quot;,
options=opcoes_edit_usr, format_func=lambda x: x[1], key=&quot;sel_usr_editar&quot;)
if usr_sel_ed:
id_u_ed = usr_sel_ed[0]
conn_u_det, db_tu_det = get_db_connection()
cur_ud = conn_u_det.cursor()
cur_ud.execute(&quot;SELECT nome, login, senha, perfil FROM usuarios WHERE id = %s&quot; if db_tu_det
== &quot;postgres&quot; else &quot;SELECT nome, login, senha, perfil FROM usuarios WHERE id = ?&quot;, (int(id_u_ed) if db_tu_det
== &quot;postgres&quot; else id_u_ed,))
dados_u_atual = cur_ud.fetchone()
conn_u_det.close()
if dados_u_atual:
with st.form(&quot;form_edit_usuario&quot;):
eu_nome = st.text_input(&quot;Nome Completo&quot;, value=dados_u_atual[0] or &quot;&quot;)
eu_login = st.text_input(&quot;Login&quot;, value=dados_u_atual[1] or &quot;&quot;)
eu_senha = st.text_input(&quot;Senha&quot;, type=&quot;password&quot;, value=dados_u_atual[2] or &quot;&quot;)
perfis_lst = [&quot;Conferente&quot;, &quot;Gestor&quot;]
idx_per = perfis_lst.index(dados_u_atual[3]) if dados_u_atual[3] in perfis_lst else 0
eu_perfil = st.selectbox(&quot;Perfil&quot;, perfis_lst, index=idx_per)
col_bu1, col_bu2 = st.columns(2)
with col_bu1: btn_salvar_usr = st.form_submit_button(&quot;�� Salvar Alterações&quot;
type=&quot;primary&quot;)
with col_bu2: btn_excluir_usr = st.form_submit_button(&quot;��️ Excluir Utilizador&quot;
type=&quot;secondary&quot;)
if btn_salvar_usr:
spinner_supernova(&quot;Atualizando utilizador...&quot;)
try:
conn_up_u, db_tupu = get_db_connection()
cur_upu = conn_up_u.cursor()
cur_upu.execute(
&quot;UPDATE usuarios SET nome = %s, login = %s, senha = %s, perfil = %s WHERE
id = %s&quot; if db_tupu == &quot;postgres&quot; else &quot;UPDATE usuarios SET nome = ?, login = ?, senha = ?, perfil = ?&quot;,
(eu_nome.strip(), eu_login.strip(), eu_senha.strip(), eu_perfil,
int(id_u_ed) if db_tupu == &quot;postgres&quot; else id_u_ed)
)
conn_up_u.commit()
conn_up_u.close()
st.success(&quot;Utilizador atualizado com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao atualizar: {e}&quot;)
if btn_excluir_usr:
spinner_supernova(&quot;Excluindo utilizador...&quot;)
try:
conn_del_u, db_tdu = get_db_connection()

cur_delu = conn_del_u.cursor()
cur_delu.execute(&quot;DELETE FROM usuarios WHERE id = %s&quot; if db_tdu == &quot;postgres&quot;
else &quot;DELETE FROM usuarios WHERE id = ?&quot;, (int(id_u_ed) if db_tdu == &quot;postgres&quot; else id_u_ed,))
conn_del_u.commit()
conn_del_u.close()
st.success(&quot;Utilizador excluído com sucesso!&quot;)
st.rerun()
except Exception as e: st.error(f&quot;Erro ao excluir: {e}&quot;)
else: st.info(&quot;Nenhum usuário cadastrado.&quot;)
