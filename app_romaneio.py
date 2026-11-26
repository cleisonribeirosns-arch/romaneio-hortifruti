import base64
from datetime import datetime, time, timedelta
import time as time_module
import io
import os
import sqlite3
import pandas as pd
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components
from streamlit_drawable_canvas import st_canvas
from zoneinfo import ZoneInfo
import hashlib
import json
import uuid
import re
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# ---------------------------------------------------------
# SISTEMA DE SEGURANÇA E HASH DE SENHAS
# ---------------------------------------------------------
def gerar_hash_senha(senha: str) -> str:
    salt = "SuperNovaHortiControlSalt2026"
    return hashlib.sha256((salt + senha).encode('utf-8')).hexdigest()

def verificar_senha(senha_digitada: str, senha_banco: str) -> bool:
    if senha_banco == senha_digitada:  
        return True
    return gerar_hash_senha(senha_digitada) == senha_banco

# ---------------------------------------------------------
# FUNÇÕES DE ÍCONE, LOGO E BASE64
# ---------------------------------------------------------
def buscar_caminho_icone_app():
    candidatos = [
        "icone_app.jpg",
        "icone_app.jpeg",
        "icone_app.png",
        "icone_app.jpg.jpeg",
        "logo_romaneio.png.jpg",
        "logo_romaneio.png",
        "logo_romaneio.jpg",
        "logo.png",
        "logo.jpg",
    ]
    for nome in candidatos:
        if os.path.exists(nome) and os.path.isfile(nome):
            return nome
    return None

def buscar_caminho_logo_empresa():
    candidatos_logo = [
        "logo_romaneio.png",
        "logo_romaneio.jpg",
        "logo_romaneio.png.jpg",
        "logo.png",
        "logo.jpg",
        "logo.jpeg",
        "tela de login padrao.jpeg",
        "tela de login padrao.jpg",
        "tela de login padrao.png",
    ]
    for nome in candidatos_logo:
        if os.path.exists(nome) and os.path.isfile(nome):
            return nome

    if os.path.exists("."):
        for arq in os.listdir("."):
            baixo = arq.lower()
            if os.path.isfile(arq) and "logo" in baixo and "icone" not in baixo:
                if baixo.endswith((".png", ".jpg", ".jpeg")):
                    return arq
    return None


def buscar_caminho_logo():
    logo_emp = buscar_caminho_logo_empresa()
    if logo_emp:
        return logo_emp
    return buscar_caminho_icone_app()

def obter_arquivo_b64_e_mime(caminho_imagem):
    if not caminho_imagem or not os.path.exists(caminho_imagem):
        return "", "image/jpeg"
    try:
        ext = os.path.splitext(caminho_imagem)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"
        with open(caminho_imagem, "rb") as f_img:
            b64_str = base64.b64encode(f_img.read()).decode("utf-8")
        return b64_str, mime
    except Exception:
        return "", "image/jpeg"

# ---------------------------------------------------------
# CONFIGURAÇÃO DE PÁGINA (ÍCONE E TÍTULO PERSONALIZADOS)
# ---------------------------------------------------------
icone_path_global = buscar_caminho_icone_app()
icone_pagina = "📦"
if icone_path_global:
    try:
        icone_pagina = Image.open(icone_path_global)
    except Exception:
        icone_pagina = "📦"

st.set_page_config(
    page_title="HortiControl - Supernova",
    page_icon=icone_pagina,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Identificador persistente deste navegador/aparelho. Não identifica a pessoa;
# permite guardar preferências locais no banco mesmo após trocar de usuário.
try:
    _device_id = str(st.query_params.get("hc_device", "")).strip()
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", _device_id):
        _device_id = str(uuid.uuid4())
        st.query_params["hc_device"] = _device_id
except Exception:
    _device_id = st.session_state.get("_hc_device_id") or str(uuid.uuid4())
    st.session_state["_hc_device_id"] = _device_id

@st.cache_data(show_spinner=False)
def obter_logo_transparente_b64(caminho_imagem):
    if not caminho_imagem or not os.path.exists(caminho_imagem):
        return ""
    try:
        from PIL import ImageDraw, ImageFilter
        img = Image.open(caminho_imagem).convert("RGBA")
        w, h = img.size
        px = img.load()

        # Amostra a cor média dos 4 cantos para identificar o fundo externo
        cantos = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
        bg_r = sum(c[0] for c in cantos) / 4.0
        bg_g = sum(c[1] for c in cantos) / 4.0
        bg_b = sum(c[2] for c in cantos) / 4.0

        visitado = set()
        fila = []
        for x in range(w):
            fila.append((x, 0))
            fila.append((x, h - 1))
        for y in range(h):
            fila.append((0, y))
            fila.append((w - 1, y))
        for pt in fila:
            visitado.add(pt)

        while fila:
            cx, cy = fila.pop(0)
            r, g, b, a = px[cx, cy]
            dist_bg = ((r - bg_r) ** 2 + (g - bg_g) ** 2 + (b - bg_b) ** 2) ** 0.5
            eh_claro_neutro = (r > 130 and g > 130 and b > 130 and (max(r, g, b) - min(r, g, b)) < 55)
            if a == 0 or dist_bg < 95 or eh_claro_neutro:
                px[cx, cy] = (255, 255, 255, 0)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visitado:
                        visitado.add((nx, ny))
                        fila.append((nx, ny))

        # Remove ilhas/fragmentos soltos pequenos desconectados do ícone principal
        alpha = img.getchannel("A")
        apx = alpha.load()
        comp_vis = set()
        componentes = []
        for yy in range(h):
            for xx in range(w):
                if apx[xx, yy] > 20 and (xx, yy) not in comp_vis:
                    q = [(xx, yy)]
                    comp_vis.add((xx, yy))
                    pts = []
                    while q:
                        qx, qy = q.pop(0)
                        pts.append((qx, qy))
                        for nx, ny in ((qx + 1, qy), (qx - 1, qy), (qx, qy + 1), (qx, qy - 1)):
                            if 0 <= nx < w and 0 <= ny < h and apx[nx, ny] > 20 and (nx, ny) not in comp_vis:
                                comp_vis.add((nx, ny))
                                q.append((nx, ny))
                    componentes.append(pts)

        if componentes:
            maior_comp = set(max(componentes, key=len))
            for yy in range(h):
                for xx in range(w):
                    if (xx, yy) not in maior_comp:
                        px[xx, yy] = (255, 255, 255, 0)

        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)
        cw, ch = img.size
        # Aplica recorte arredondado interno de segurança para eliminar halos brancos nas bordas
        margem = max(6, int(min(cw, ch) * 0.03))
        raio = max(18, int(min(cw, ch) * 0.20))
        mask = Image.new("L", (cw, ch), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(margem, margem), (cw - 1 - margem, ch - 1 - margem)], radius=raio, fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=1))
        img_limpa = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        img_limpa.paste(img, (0, 0), mask=mask)

        buffered = io.BytesIO()
        img_limpa.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception:
        return ""

logo_path_global = buscar_caminho_logo()
logo_b64_global_overlay = obter_logo_transparente_b64(logo_path_global) if logo_path_global else ""

# ---------------------------------------------------------
# CSS GLOBAL & ESTILO DA TELA DE TRANSIÇÃO COM A LOGO CORRIGIDA
# ---------------------------------------------------------
st.markdown(f"""
<style>
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}
.stDeployButton {{display:none;}}
[data-testid="stToolbar"] {{display: none !important;}}

/* Overlay de transição robusto com a logo centralizada */
.supernova-transition-overlay {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(14, 20, 12, 0.95);
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    z-index: 999999;
    color: #FFFFFF;
    font-family: sans-serif;
}}
.supernova-logo-pulse {{
    width: 120px;
    height: auto;
    margin-bottom: 20px;
    animation: pulseLogo 1.2s infinite ease-in-out;
    filter: drop-shadow(0px 15px 25px rgba(0,0,0,0.85)) drop-shadow(0px 5px 10px rgba(0,200,0,0.35));
}}
@keyframes pulseLogo {{
    0% {{ transform: scale(0.95); opacity: 0.8; }}
    50% {{ transform: scale(1.1); opacity: 1; }}
    100% {{ transform: scale(0.95); opacity: 0.8; }}
}}
</style>
""", unsafe_allow_html=True)

# Script JS para acionar a transição visual ao clicar em abas (pastas) e botões no frontend
img_tag_js = f'<img src="data:image/png;base64,{logo_b64_global_overlay}" class="supernova-logo-pulse" />' if logo_b64_global_overlay else '<div style="font-size: 40px; margin-bottom: 20px;">📦</div>'
components.html(f"""
<script>
(function() {{
    const parentDoc = window.parent.document;
    if (parentDoc.getElementById('supernova-js-transition-hook')) return;
    const marker = parentDoc.createElement('div');
    marker.id = 'supernova-js-transition-hook';
    marker.style.display = 'none';
    parentDoc.body.appendChild(marker);

    function dispararOverlayJS(texto) {{
        let existing = parentDoc.getElementById('supernova-dynamic-overlay');
        if (existing) existing.remove();
        const ov = parentDoc.createElement('div');
        ov.id = 'supernova-dynamic-overlay';
        ov.className = 'supernova-transition-overlay';
        ov.innerHTML = `{img_tag_js}<h3 style="color: #FFFFFF; font-weight: 600; letter-spacing: 0.5px;">${{texto}}</h3>`;
        parentDoc.body.appendChild(ov);
        setTimeout(() => {{
            if (ov && ov.parentNode) ov.remove();
        }}, 550);
    }}

    parentDoc.addEventListener('click', function(e) {{
        const tabBtn = e.target.closest('button[data-baseweb="tab"]');
        if (tabBtn) {{
            const label = tabBtn.innerText ? tabBtn.innerText.trim() : 'aba';
            dispararOverlayJS('Carregando ' + label + '...');
            return;
        }}
        const actionBtn = e.target.closest('button[kind="primary"], button[kind="secondary"]');
        if (actionBtn) {{
            const txt = actionBtn.innerText ? actionBtn.innerText.trim() : '';
            if (txt && !txt.includes('Descarregar') && !txt.includes('Baixar')) {{
                dispararOverlayJS('Processando...');
            }}
        }}
    }}, true);
}})();
</script>
""", height=0)

def spinner_supernova(mensagem="Processando transição...", duracao_minima=0.0):
    # Componente visual personalizado garantindo a exibição da transição com a logo
    img_tag = f'<img src="data:image/png;base64,{logo_b64_global_overlay}" class="supernova-logo-pulse" />' if logo_b64_global_overlay else '<div style="font-size: 40px; margin-bottom: 20px;">📦</div>'
    
    placeholder = st.empty()
    placeholder.markdown(f"""
    <div class="supernova-transition-overlay">
        {img_tag}
        <h3 style="color: #FFFFFF; font-weight: 600; letter-spacing: 0.5px;">{mensagem}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    class SpinnerContext:
        def __init__(self):
            self.start_time = time_module.time()
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed = time_module.time() - self.start_time
            if elapsed < duracao_minima:
                time_module.sleep(duracao_minima - elapsed)
            placeholder.empty()
            
    return SpinnerContext()



# ---------------------------------------------------------
# CSS MOBILE / WEBVIEW (CORREÇÃO DE FONTES E CONTRASTE NO APP)
# ---------------------------------------------------------
st.markdown("""
<style>
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    -webkit-text-size-adjust: 100% !important;
    text-size-adjust: 100% !important;
    overscroll-behavior-y: none !important;
    opacity: 1 !important;
    visibility: visible !important;
}

/* Garante legibilidade, tamanho e contraste das fontes no WebView Android */
.stApp,
.stApp p,
.stApp label,
.stApp li,
[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
[data-testid="stMarkdownContainer"] li,
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] span {
    font-size: 15px !important;
    line-height: 1.45 !important;
    opacity: 1 !important;
    visibility: visible !important;
}

.stApp h1, [data-testid="stHeading"] h1 {
    font-size: 1.65rem !important;
    line-height: 1.25 !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}

.stApp h2, [data-testid="stHeading"] h2 {
    font-size: 1.35rem !important;
    line-height: 1.25 !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}

.stApp h3, [data-testid="stHeading"] h3 {
    font-size: 1.15rem !important;
    line-height: 1.3 !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}

/* Campos, selects e botões com texto sempre legível no APK */
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span,
[data-testid="stExpander"] summary p,
[data-testid="stRadio"] label,
[data-testid="stRadio"] label p,
[data-testid="stRadio"] label span,
[data-baseweb="select"] > div,
[data-baseweb="select"] span,
input, textarea,
.stApp button,
.stApp button p,
.stApp button span {
    font-size: 15px !important;
    opacity: 1 !important;
    visibility: visible !important;
}

.stApp button {
    min-height: 44px !important;
    font-weight: 600 !important;
}

@media (max-width: 768px) {
    .stApp .main .block-container {
        padding-left: 0.75rem !important;
        padding-right: 0.75rem !important;
        padding-top: 0.7rem !important;
    }

    .stApp h1, [data-testid="stHeading"] h1 {
        font-size: 1.35rem !important;
    }

    .stApp h2, [data-testid="stHeading"] h2 {
        font-size: 1.15rem !important;
    }

    .stApp h3, [data-testid="stHeading"] h3 {
        font-size: 1.05rem !important;
    }
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# TEMA CLARO / ESCURO AUTOMÁTICO POR DISPOSITIVO (PRESERVANDO PLANO DE FUNDO)
# ---------------------------------------------------------
st.markdown("""
<style>
/* Transição suave apenas nos textos, rótulos e campos de preenchimento */
p, label, h1, h2, h3, h4,
[data-testid="stMarkdownContainer"] p,
[data-testid="stWidgetLabel"] label,
[data-testid="stWidgetLabel"] p,
input, textarea, select, [data-baseweb="select"] > div {
    transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}

/* ================= MODO ESCURO DO APARELHO ================= */
@media (prefers-color-scheme: dark) {
    :root {
        color-scheme: dark;
    }

    p, label, h1, h2, h3, h4,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p {
        color: #f9fafb !important;
    }

    input, textarea, select, [data-baseweb="select"] > div {
        background-color: #1e222b !important;
        color: #f9fafb !important;
        -webkit-text-fill-color: #f9fafb !important;
        border-color: #4b5563 !important;
    }

    input::placeholder, textarea::placeholder {
        color: #9ca3af !important;
        -webkit-text-fill-color: #9ca3af !important;
        opacity: 1 !important;
    }
}

/* ================= MODO CLARO DO APARELHO ================= */
@media (prefers-color-scheme: light) {
    :root {
        color-scheme: light;
    }

    p, label, h1, h2, h3, h4,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stWidgetLabel"] label,
    [data-testid="stWidgetLabel"] p {
        color: #111827 !important;
    }

    input, textarea, select, [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #111827 !important;
        -webkit-text-fill-color: #111827 !important;
        border-color: #cbd5e1 !important;
    }

    input::placeholder, textarea::placeholder {
        color: #64748b !important;
        -webkit-text-fill-color: #64748b !important;
        opacity: 1 !important;
    }
}

/* ================= AJUSTE PARA CELULAR / TABLET / COLETOR ================= */
@media (max-width: 768px) {
    input, textarea, select, [data-baseweb="select"] > div {
        min-height: 44px !important;
        font-size: 16px !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# CONFIGURAÇÃO DE PWA (USANDO icone_app.jpg)
# ---------------------------------------------------------
icone_b64, icone_mime = obter_arquivo_b64_e_mime(icone_path_global)
icone_src_pwa = f"data:{icone_mime};base64,{icone_b64}" if icone_b64 else (icone_path_global or "icone_app.jpg")

pwa_manifest_json = json.dumps({
    "name": "HortiControl Supernova",
    "short_name": "HortiControl",
    "start_url": ".",
    "display": "standalone",
    "background_color": "#0E140C",
    "theme_color": "#2E7D32",
    "icons": [
        {
            "src": icone_src_pwa,
            "sizes": "192x192",
            "type": icone_mime
        },
        {
            "src": icone_src_pwa,
            "sizes": "512x512",
            "type": icone_mime
        }
    ]
}, ensure_ascii=False)

pwa_manifest_code = f"""
<link rel="manifest" href="data:application/manifest+json;charset=utf-8,{pwa_manifest_json}">
<link rel="apple-touch-icon" sizes="180x180" href="{icone_src_pwa}">
<link rel="icon" type="{icone_mime}" href="{icone_src_pwa}">
<meta name="theme-color" content="#2E7D32">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="HortiControl">
"""
st.markdown(pwa_manifest_code, unsafe_allow_html=True)

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

try:
    from plyer import notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

# ---------------------------------------------------------
# FUNÇÕES DE CONEXÃO, CONTINGÊNCIA (NEON -> SUPABASE) E SINCRONIZAÇÃO AUTOMÁTICA
# ---------------------------------------------------------
def _obter_urls_postgres():
    if not HAS_POSTGRES or "database" not in st.secrets:
        return None, None
    db_sec = st.secrets["database"]
    neon_url = str(db_sec.get("db_url", "")).strip() or None
    supabase_url = (
        str(db_sec.get("backup_db_url", "")).strip()
        or str(db_sec.get("supabase_url", "")).strip()
        or str(db_sec.get("supabase_db_url", "")).strip()
        or None
    )
    return neon_url, supabase_url


def _conectar_pg_direto(url, timeout=15, tentativas=2):
    ultimo_erro = None
    for _ in range(tentativas):
        try:
            conn = psycopg2.connect(url, connect_timeout=timeout)
            return conn
        except Exception as e:
            ultimo_erro = e
            time_module.sleep(0.8)
    raise ultimo_erro


def _garantir_schema_postgres(conn):
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(255) NOT NULL,
        login VARCHAR(255) UNIQUE NOT NULL,
        senha VARCHAR(255) NOT NULL,
        perfil VARCHAR(255) NOT NULL,
        tema_bg VARCHAR(255) DEFAULT 'Logomarca Oficial Supernova',
        notif_desktop INTEGER DEFAULT 0,
        custom_bg_b64 TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wallpapers (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(255) UNIQUE NOT NULL,
        b64_dados TEXT NOT NULL
    )
    """)
    for alt_sql in [
        "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS tema_bg VARCHAR(255) DEFAULT 'Logomarca Oficial Supernova'",
        "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS notif_desktop INTEGER DEFAULT 0",
        "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS custom_bg_b64 TEXT",
    ]:
        try:
            cursor.execute(alt_sql)
        except Exception:
            pass

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
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS troca_avarias (
                id SERIAL PRIMARY KEY,
                numero_controle VARCHAR(100) UNIQUE NOT NULL,
                data_operacao VARCHAR(50) NOT NULL,
                setor_loja VARCHAR(255) NOT NULL,
                fornecedor VARCHAR(255) NOT NULL,
                conferente VARCHAR(255) NOT NULL,
                observacoes TEXT,
                assinatura_responsavel_b64 TEXT NOT NULL,
                assinatura_fornecedor_b64 TEXT NOT NULL,
                codigo_fornecedor VARCHAR(255),
                status VARCHAR(50) DEFAULT 'Troca pendente',
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
    """)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS troca_avarias_itens (
                id SERIAL PRIMARY KEY,
                troca_id INTEGER NOT NULL REFERENCES troca_avarias(id) ON DELETE CASCADE,
                codigo_produto VARCHAR(255),
                descricao_produto VARCHAR(500) NOT NULL,
                quantidade REAL NOT NULL,
                unidade VARCHAR(50) NOT NULL
            )
    """)
    for alt_sql2 in [
        "ALTER TABLE bonificacoes ADD COLUMN IF NOT EXISTS anexo_b64 TEXT",
        "ALTER TABLE romaneios ADD COLUMN IF NOT EXISTS foto_b64 TEXT",
        "ALTER TABLE baixas_avarias ADD COLUMN IF NOT EXISTS nf_baixa_b64 TEXT",
        "ALTER TABLE troca_avarias ADD COLUMN IF NOT EXISTS codigo_fornecedor VARCHAR(255)",
        "ALTER TABLE troca_avarias ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Troca pendente'",
    ]:
        try:
            cursor.execute(alt_sql2)
        except Exception:
            pass

    cursor.execute("SELECT 1 FROM usuarios WHERE login = %s", ("908",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (nome, login, senha, perfil, tema_bg, notif_desktop) VALUES (%s, %s, %s, %s, %s, %s)",
            ("Administrador", "908", gerar_hash_senha("0332"), "Gestor", "Logomarca Oficial Supernova", 0),
        )


def _garantir_tabelas_controle_contingencia(conn_reserva):
    cur = conn_reserva.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS _contingencia_sync_log (
        id SERIAL PRIMARY KEY,
        tabela VARCHAR(100) NOT NULL,
        chave_unica VARCHAR(500) NOT NULL,
        operacao VARCHAR(30) DEFAULT 'UPSERT',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        sincronizado INTEGER DEFAULT 0,
        sincronizado_em TIMESTAMP NULL,
        UNIQUE(tabela, chave_unica)
    )
    """)
    conn_reserva.commit()
    st.cache_data.clear()


def _registrar_pendencia_contingencia(conn_reserva, tabela, chave_unica, operacao="UPSERT"):
    _garantir_tabelas_controle_contingencia(conn_reserva)
    cur = conn_reserva.cursor()
    cur.execute(
        """
        INSERT INTO _contingencia_sync_log (tabela, chave_unica, operacao, sincronizado, sincronizado_em, criado_em)
        VALUES (%s, %s, %s, 0, NULL, CURRENT_TIMESTAMP)
        ON CONFLICT (tabela, chave_unica) DO UPDATE SET
            operacao = EXCLUDED.operacao,
            sincronizado = 0,
            sincronizado_em = NULL,
            criado_em = CURRENT_TIMESTAMP
        """,
        (str(tabela), str(chave_unica), str(operacao)),
    )


def _sincronizar_reserva_para_principal(conn_neon, conn_supabase):
    """
    Sincroniza automaticamente (idempotente / sem duplicidade) os dados gravados
    no Supabase durante contingência de volta para o Neon assim que o Neon volta.
    """
    _garantir_schema_postgres(conn_neon)
    _garantir_schema_postgres(conn_supabase)
    _garantir_tabelas_controle_contingencia(conn_supabase)

    cur_sup = conn_supabase.cursor()
    cur_neon = conn_neon.cursor()

    cur_sup.execute(
        "SELECT id, tabela, chave_unica, operacao FROM _contingencia_sync_log WHERE sincronizado = 0 ORDER BY id ASC"
    )
    pendentes = cur_sup.fetchall()
    if not pendentes:
        return 0

    sincronizados_ids = []

    for log_id, tabela, chave_unica, operacao in pendentes:
        try:
            if tabela == "usuarios":
                cur_sup.execute(
                    "SELECT nome, login, senha, perfil, tema_bg, notif_desktop, custom_bg_b64 FROM usuarios WHERE login = %s",
                    (chave_unica,),
                )
                row = cur_sup.fetchone()
                if row:
                    cur_neon.execute(
                        """
                        INSERT INTO usuarios (nome, login, senha, perfil, tema_bg, notif_desktop, custom_bg_b64)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (login) DO UPDATE SET
                            nome = EXCLUDED.nome,
                            senha = EXCLUDED.senha,
                            perfil = EXCLUDED.perfil,
                            tema_bg = EXCLUDED.tema_bg,
                            notif_desktop = EXCLUDED.notif_desktop,
                            custom_bg_b64 = EXCLUDED.custom_bg_b64
                        """,
                        row,
                    )

            elif tabela == "wallpapers":
                cur_sup.execute("SELECT nome, b64_dados FROM wallpapers WHERE nome = %s", (chave_unica,))
                row = cur_sup.fetchone()
                if row:
                    cur_neon.execute(
                        """
                        INSERT INTO wallpapers (nome, b64_dados)
                        VALUES (%s, %s)
                        ON CONFLICT (nome) DO UPDATE SET b64_dados = EXCLUDED.b64_dados
                        """,
                        row,
                    )

            elif tabela == "produtos":
                cur_sup.execute(
                    "SELECT codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos WHERE nome = %s",
                    (chave_unica,),
                )
                row = cur_sup.fetchone()
                if row:
                    cur_neon.execute(
                        """
                        INSERT INTO produtos (codigo_barras, codigo_produto, nome, unidade_padrao)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (nome) DO UPDATE SET
                            codigo_barras = COALESCE(EXCLUDED.codigo_barras, produtos.codigo_barras),
                            codigo_produto = COALESCE(EXCLUDED.codigo_produto, produtos.codigo_produto),
                            unidade_padrao = EXCLUDED.unidade_padrao
                        """,
                        row,
                    )

            elif tabela == "fornecedores":
                cur_sup.execute(
                    "SELECT codigo_fornecedor, cnpj, nome FROM fornecedores WHERE nome = %s",
                    (chave_unica,),
                )
                row = cur_sup.fetchone()
                if row:
                    cur_neon.execute(
                        """
                        INSERT INTO fornecedores (codigo_fornecedor, cnpj, nome)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (nome) DO UPDATE SET
                            codigo_fornecedor = COALESCE(EXCLUDED.codigo_fornecedor, fornecedores.codigo_fornecedor),
                            cnpj = COALESCE(EXCLUDED.cnpj, fornecedores.cnpj)
                        """,
                        row,
                    )

            elif tabela == "romaneios":
                cur_sup.execute(
                    """
                    SELECT id, numero_romaneio, loja, loja_origem, loja_destino,
                           data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor,
                           conferente, pagamento_a_vista, data_pagamento, caminho_foto,
                           assinatura_conferente, assinatura_entregador, status_nota,
                           tipo_operacao, observacoes, foto_b64, ass_conf_b64, ass_ent_b64
                    FROM romaneios WHERE numero_romaneio = %s
                    """,
                    (chave_unica,),
                )
                row = cur_sup.fetchone()
                if row:
                    sup_rom_id = row[0]
                    vals = row[1:]
                    cur_neon.execute(
                        """
                        INSERT INTO romaneios (
                            numero_romaneio, loja, loja_origem, loja_destino,
                            data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor,
                            conferente, pagamento_a_vista, data_pagamento, caminho_foto,
                            assinatura_conferente, assinatura_entregador, status_nota,
                            tipo_operacao, observacoes, foto_b64, ass_conf_b64, ass_ent_b64
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (numero_romaneio) DO UPDATE SET
                            loja = EXCLUDED.loja,
                            loja_origem = EXCLUDED.loja_origem,
                            loja_destino = EXCLUDED.loja_destino,
                            data_recebimento = EXCLUDED.data_recebimento,
                            fornecedor = EXCLUDED.fornecedor,
                            codigo_fornecedor = EXCLUDED.codigo_fornecedor,
                            telefone_fornecedor = EXCLUDED.telefone_fornecedor,
                            conferente = EXCLUDED.conferente,
                            pagamento_a_vista = EXCLUDED.pagamento_a_vista,
                            data_pagamento = EXCLUDED.data_pagamento,
                            caminho_foto = EXCLUDED.caminho_foto,
                            assinatura_conferente = EXCLUDED.assinatura_conferente,
                            assinatura_entregador = EXCLUDED.assinatura_entregador,
                            status_nota = EXCLUDED.status_nota,
                            tipo_operacao = EXCLUDED.tipo_operacao,
                            observacoes = EXCLUDED.observacoes,
                            foto_b64 = COALESCE(NULLIF(EXCLUDED.foto_b64, ''), romaneios.foto_b64),
                            ass_conf_b64 = COALESCE(NULLIF(EXCLUDED.ass_conf_b64, ''), romaneios.ass_conf_b64),
                            ass_ent_b64 = COALESCE(NULLIF(EXCLUDED.ass_ent_b64, ''), romaneios.ass_ent_b64)
                        RETURNING id
                        """,
                        vals,
                    )
                    neon_rom_id = cur_neon.fetchone()[0]
                    cur_sup.execute(
                        "SELECT produto, quantidade, unidade, valor_unitario, valor_total FROM romaneio_itens WHERE romaneio_id = %s ORDER BY id ASC",
                        (sup_rom_id,),
                    )
                    itens_sup = cur_sup.fetchall()
                    cur_neon.execute("DELETE FROM romaneio_itens WHERE romaneio_id = %s", (neon_rom_id,))
                    for it in itens_sup:
                        cur_neon.execute(
                            "INSERT INTO romaneio_itens (romaneio_id, produto, quantidade, unidade, valor_unitario, valor_total) VALUES (%s, %s, %s, %s, %s, %s)",
                            (neon_rom_id, it[0], it[1], it[2], it[3], it[4]),
                        )

            elif tabela == "troca_avarias":
                cur_sup.execute("""
                    SELECT numero_controle, data_operacao, setor_loja, fornecedor, conferente,
                           observacoes, assinatura_responsavel_b64, assinatura_fornecedor_b64,
                           codigo_fornecedor, status
                    FROM troca_avarias WHERE numero_controle = %s
                """, (chave_unica,))
                row_troca = cur_sup.fetchone()
                if row_troca:
                    cur_neon.execute("""
                        INSERT INTO troca_avarias
                        (numero_controle, data_operacao, setor_loja, fornecedor, conferente, observacoes,
                         assinatura_responsavel_b64, assinatura_fornecedor_b64, codigo_fornecedor, status)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (numero_controle) DO UPDATE SET
                            data_operacao = EXCLUDED.data_operacao,
                            setor_loja = EXCLUDED.setor_loja,
                            fornecedor = EXCLUDED.fornecedor,
                            conferente = EXCLUDED.conferente,
                            observacoes = EXCLUDED.observacoes,
                            assinatura_responsavel_b64 = EXCLUDED.assinatura_responsavel_b64,
                            assinatura_fornecedor_b64 = EXCLUDED.assinatura_fornecedor_b64,
                            codigo_fornecedor = EXCLUDED.codigo_fornecedor,
                            status = EXCLUDED.status
                        RETURNING id
                    """, row_troca)
                    neon_troca_id = cur_neon.fetchone()[0]
                    cur_sup.execute("SELECT codigo_produto, descricao_produto, quantidade, unidade FROM troca_avarias_itens WHERE troca_id = (SELECT id FROM troca_avarias WHERE numero_controle = %s) ORDER BY id", (chave_unica,))
                    itens_troca_sup = cur_sup.fetchall()
                    cur_neon.execute("DELETE FROM troca_avarias_itens WHERE troca_id = %s", (neon_troca_id,))
                    for item_t in itens_troca_sup:
                        cur_neon.execute("""
                            INSERT INTO troca_avarias_itens (troca_id, codigo_produto, descricao_produto, quantidade, unidade)
                            VALUES (%s,%s,%s,%s,%s)
                        """, (neon_troca_id, item_t[0], item_t[1], item_t[2], item_t[3]))

            elif tabela == "bonificacoes":
                partes = chave_unica.split("||", 2)
                if len(partes) == 3:
                    n_nota, n_loja, n_dt = partes
                    cur_sup.execute(
                        """
                        SELECT numero_nota, loja, data_entrada, valor_bonificacao, status,
                               produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64
                        FROM bonificacoes
                        WHERE numero_nota = %s AND loja = %s AND data_entrada = %s
                        ORDER BY id DESC LIMIT 1
                        """,
                        (n_nota, n_loja, n_dt),
                    )
                    row = cur_sup.fetchone()
                    if row:
                        cur_neon.execute(
                            "SELECT id FROM bonificacoes WHERE numero_nota = %s AND loja = %s AND data_entrada = %s LIMIT 1",
                            (n_nota, n_loja, n_dt),
                        )
                        ex = cur_neon.fetchone()
                        if ex:
                            cur_neon.execute(
                                """
                                UPDATE bonificacoes SET
                                    valor_bonificacao = %s, status = %s, produto_hortifruti = %s,
                                    caminho_anexo = %s, tipo_bonificacao = %s,
                                    anexo_b64 = COALESCE(NULLIF(%s, ''), anexo_b64)
                                WHERE id = %s
                                """,
                                (row[3], row[4], row[5], row[6], row[7], row[8], ex[0]),
                            )
                        else:
                            cur_neon.execute(
                                """
                                INSERT INTO bonificacoes (
                                    numero_nota, loja, data_entrada, valor_bonificacao, status,
                                    produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                row,
                            )

            elif tabela == "baixas_avarias":
                partes = chave_unica.split("||", 3)
                if len(partes) == 4:
                    b_loja, b_dt, b_ref, b_nf = partes
                    cur_sup.execute(
                        """
                        SELECT loja_baixa, data_baixa, ref_bon_transferen, nf_baixa, nf_b_entrada,
                               produto_hortifruti, quantidade_kg_cx, valor_total_avaria,
                               saldo_restante_nota, saldo_total_disponivel, nf_baixa_b64
                        FROM baixas_avarias
                        WHERE loja_baixa = %s AND data_baixa = %s AND ref_bon_transferen = %s AND nf_b_entrada = %s
                        ORDER BY id DESC LIMIT 1
                        """,
                        (b_loja, b_dt, b_ref, b_nf),
                    )
                    row = cur_sup.fetchone()
                    if row:
                        cur_neon.execute(
                            """
                            SELECT id FROM baixas_avarias
                            WHERE loja_baixa = %s AND data_baixa = %s AND ref_bon_transferen = %s AND nf_b_entrada = %s
                            LIMIT 1
                            """,
                            (b_loja, b_dt, b_ref, b_nf),
                        )
                        ex = cur_neon.fetchone()
                        if ex:
                            cur_neon.execute(
                                """
                                UPDATE baixas_avarias SET
                                    nf_baixa = %s, produto_hortifruti = %s, quantidade_kg_cx = %s,
                                    valor_total_avaria = %s, saldo_restante_nota = %s,
                                    saldo_total_disponivel = %s,
                                    nf_baixa_b64 = COALESCE(NULLIF(%s, ''), nf_baixa_b64)
                                WHERE id = %s
                                """,
                                (row[3], row[5], row[6], row[7], row[8], row[9], row[10], ex[0]),
                            )
                        else:
                            cur_neon.execute(
                                """
                                INSERT INTO baixas_avarias (
                                    loja_baixa, data_baixa, ref_bon_transferen, nf_baixa, nf_b_entrada,
                                    produto_hortifruti, quantidade_kg_cx, valor_total_avaria,
                                    saldo_restante_nota, saldo_total_disponivel, nf_baixa_b64
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                row,
                            )

            sincronizados_ids.append(log_id)
        except Exception:
            conn_neon.rollback()
            raise

    conn_neon.commit()
    st.cache_data.clear()
    for lid in sincronizados_ids:
        cur_sup.execute(
            "UPDATE _contingencia_sync_log SET sincronizado = 1, sincronizado_em = CURRENT_TIMESTAMP WHERE id = %s",
            (lid,),
        )
    conn_supabase.commit()
    st.cache_data.clear()
    return len(sincronizados_ids)


def _espelhar_base_para_reserva(conn_neon, conn_supabase):
    """Mantém o banco reserva (Supabase) aquecido e espelhado com os dados mestres e recentes do Neon."""
    _garantir_schema_postgres(conn_supabase)
    cur_n = conn_neon.cursor()
    cur_s = conn_supabase.cursor()

    cur_n.execute("SELECT nome, login, senha, perfil, tema_bg, notif_desktop, custom_bg_b64 FROM usuarios")
    for r in cur_n.fetchall():
        cur_s.execute(
            """
            INSERT INTO usuarios (nome, login, senha, perfil, tema_bg, notif_desktop, custom_bg_b64)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (login) DO UPDATE SET
                nome = EXCLUDED.nome, senha = EXCLUDED.senha, perfil = EXCLUDED.perfil,
                tema_bg = EXCLUDED.tema_bg, notif_desktop = EXCLUDED.notif_desktop, custom_bg_b64 = EXCLUDED.custom_bg_b64
            """,
            r,
        )

    cur_n.execute("SELECT codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos")
    for r in cur_n.fetchall():
        cur_s.execute(
            """
            INSERT INTO produtos (codigo_barras, codigo_produto, nome, unidade_padrao)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (nome) DO UPDATE SET
                codigo_barras = EXCLUDED.codigo_barras,
                codigo_produto = EXCLUDED.codigo_produto,
                unidade_padrao = EXCLUDED.unidade_padrao
            """,
            r,
        )

    cur_n.execute("SELECT codigo_fornecedor, cnpj, nome FROM fornecedores")
    for r in cur_n.fetchall():
        cur_s.execute(
            """
            INSERT INTO fornecedores (codigo_fornecedor, cnpj, nome)
            VALUES (%s, %s, %s)
            ON CONFLICT (nome) DO UPDATE SET
                codigo_fornecedor = EXCLUDED.codigo_fornecedor,
                cnpj = EXCLUDED.cnpj
            """,
            r,
        )

    cur_n.execute(
        """
        SELECT numero_nota, loja, data_entrada, valor_bonificacao, status,
               produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64
        FROM bonificacoes ORDER BY id DESC LIMIT 300
        """
    )
    for r in cur_n.fetchall():
        cur_s.execute(
            "SELECT id FROM bonificacoes WHERE numero_nota = %s AND loja = %s AND data_entrada = %s LIMIT 1",
            (r[0], r[1], r[2]),
        )
        ex = cur_s.fetchone()
        if ex:
            cur_s.execute(
                "UPDATE bonificacoes SET valor_bonificacao = %s, status = %s, produto_hortifruti = %s, tipo_bonificacao = %s WHERE id = %s",
                (r[3], r[4], r[5], r[7], ex[0]),
            )
        else:
            cur_s.execute(
                """
                INSERT INTO bonificacoes (
                    numero_nota, loja, data_entrada, valor_bonificacao, status,
                    produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                r,
            )

    conn_supabase.commit()
    st.cache_data.clear()


class _CursorContingenciaWrapper:
    def __init__(self, real_cursor, conn_reserva, em_contingencia):
        self._cur = real_cursor
        self._conn_reserva = conn_reserva
        self._em_contingencia = em_contingencia
        self._ultimo_romaneio_num = None

    def _rastrear_escrita(self, sql, params):
        if not self._em_contingencia or not sql:
            return
        sql_clean = " ".join(str(sql).strip().split())
        sql_up = sql_clean.upper()
        if not (sql_up.startswith("INSERT INTO") or sql_up.startswith("UPDATE ")):
            return
        p = tuple(params) if params is not None else ()
        try:
            if "INTO ROMANEIOS " in sql_up and len(p) >= 1:
                self._ultimo_romaneio_num = str(p[0])
                _registrar_pendencia_contingencia(self._conn_reserva, "romaneios", str(p[0]))
            elif "INTO ROMANEIO_ITENS " in sql_up and self._ultimo_romaneio_num:
                _registrar_pendencia_contingencia(self._conn_reserva, "romaneios", self._ultimo_romaneio_num)
            elif "UPDATE ROMANEIOS " in sql_up and len(p) >= 1:
                rid = p[-1]
                c_tmp = self._conn_reserva.cursor()
                c_tmp.execute("SELECT numero_romaneio FROM romaneios WHERE id = %s", (rid,))
                r_num = c_tmp.fetchone()
                if r_num:
                    _registrar_pendencia_contingencia(self._conn_reserva, "romaneios", str(r_num[0]))
            elif "INTO TROCA_AVARIAS " in sql_up and len(p) >= 1:
                _registrar_pendencia_contingencia(self._conn_reserva, "troca_avarias", str(p[0]))
            elif "INTO TROCA_AVARIAS_ITENS " in sql_up and len(p) >= 1:
                c_tmp = self._conn_reserva.cursor()
                c_tmp.execute("SELECT numero_controle FROM troca_avarias WHERE id = %s", (p[0],))
                r_troca = c_tmp.fetchone()
                if r_troca:
                    _registrar_pendencia_contingencia(self._conn_reserva, "troca_avarias", str(r_troca[0]))
            elif "INTO BONIFICACOES " in sql_up and len(p) >= 3:
                chave = f"{p[0]}||{p[1]}||{p[2]}"
                _registrar_pendencia_contingencia(self._conn_reserva, "bonificacoes", chave)
            elif "UPDATE BONIFICACOES " in sql_up:
                c_tmp = self._conn_reserva.cursor()
                if "WHERE ID = %S" in sql_up and len(p) >= 1:
                    c_tmp.execute("SELECT numero_nota, loja, data_entrada FROM bonificacoes WHERE id = %s", (p[-1],))
                    rb = c_tmp.fetchone()
                    if rb:
                        _registrar_pendencia_contingencia(self._conn_reserva, "bonificacoes", f"{rb[0]}||{rb[1]}||{rb[2]}")
                elif "TRIM(NUMERO_NOTA)" in sql_up and len(p) >= 1:
                    c_tmp.execute("SELECT numero_nota, loja, data_entrada FROM bonificacoes WHERE TRIM(numero_nota) = TRIM(%s)", (p[-1],))
                    for rb in c_tmp.fetchall():
                        _registrar_pendencia_contingencia(self._conn_reserva, "bonificacoes", f"{rb[0]}||{rb[1]}||{rb[2]}")
            elif "INTO BAIXAS_AVARIAS " in sql_up and len(p) >= 5:
                chave = f"{p[0]}||{p[1]}||{p[2]}||{p[4]}"
                _registrar_pendencia_contingencia(self._conn_reserva, "baixas_avarias", chave)
            elif "UPDATE BAIXAS_AVARIAS " in sql_up and len(p) >= 1:
                c_tmp = self._conn_reserva.cursor()
                c_tmp.execute("SELECT loja_baixa, data_baixa, ref_bon_transferen, nf_b_entrada FROM baixas_avarias WHERE id = %s", (p[-1],))
                rbx = c_tmp.fetchone()
                if rbx:
                    _registrar_pendencia_contingencia(self._conn_reserva, "baixas_avarias", f"{rbx[0]}||{rbx[1]}||{rbx[2]}||{rbx[3]}")
            elif "INTO PRODUTOS " in sql_up and len(p) >= 3:
                _registrar_pendencia_contingencia(self._conn_reserva, "produtos", str(p[2]))
            elif "UPDATE PRODUTOS " in sql_up and len(p) >= 3:
                _registrar_pendencia_contingencia(self._conn_reserva, "produtos", str(p[2]))
            elif "INTO FORNECEDORES " in sql_up and len(p) >= 3:
                _registrar_pendencia_contingencia(self._conn_reserva, "fornecedores", str(p[2]))
            elif "UPDATE FORNECEDORES " in sql_up and len(p) >= 3:
                _registrar_pendencia_contingencia(self._conn_reserva, "fornecedores", str(p[2]))
            elif "INTO USUARIOS " in sql_up and len(p) >= 2:
                _registrar_pendencia_contingencia(self._conn_reserva, "usuarios", str(p[1]))
            elif "UPDATE USUARIOS " in sql_up and len(p) >= 2:
                c_tmp = self._conn_reserva.cursor()
                c_tmp.execute("SELECT login FROM usuarios WHERE id = %s", (p[-1],))
                ru = c_tmp.fetchone()
                if ru:
                    _registrar_pendencia_contingencia(self._conn_reserva, "usuarios", str(ru[0]))
            elif "INTO WALLPAPERS " in sql_up and len(p) >= 1:
                _registrar_pendencia_contingencia(self._conn_reserva, "wallpapers", str(p[0]))
        except Exception:
            pass

    def execute(self, sql, params=None):
        res = self._cur.execute(sql, params) if params is not None else self._cur.execute(sql)
        self._rastrear_escrita(sql, params)
        return res

    def executemany(self, sql, seq_of_params):
        res = self._cur.executemany(sql, seq_of_params)
        for p in seq_of_params:
            self._rastrear_escrita(sql, p)
        return res

    def __getattr__(self, name):
        return getattr(self._cur, name)


class _ConnContingenciaWrapper:
    def __init__(self, real_conn, em_contingencia=False):
        self._conn = real_conn
        self._em_contingencia = em_contingencia

    def cursor(self, *args, **kwargs):
        return _CursorContingenciaWrapper(self._conn.cursor(*args, **kwargs), self._conn, self._em_contingencia)

    def __getattr__(self, name):
        return getattr(self._conn, name)


def tentar_reconciliacao_automatica(forcar=False):
    neon_url, supabase_url = _obter_urls_postgres()
    if not neon_url or not supabase_url:
        return 0
    agora = time_module.time()
    ultimo_check = st.session_state.get("_ultimo_sync_contingencia_ts", 0.0)
    if not forcar and (agora - ultimo_check) < 20:
        return 0
    st.session_state["_ultimo_sync_contingencia_ts"] = agora

    conn_n = None
    conn_s = None
    try:
        conn_n = _conectar_pg_direto(neon_url, timeout=12, tentativas=1)
        conn_s = _conectar_pg_direto(supabase_url, timeout=12, tentativas=1)
        qtd_sync = _sincronizar_reserva_para_principal(conn_n, conn_s)
        if qtd_sync > 0:
            st.session_state["_qtd_ultima_sincronizacao"] = qtd_sync
            st.session_state["_banco_ativo_modo"] = "Neon (Principal)"
        return qtd_sync
    except Exception:
        return 0
    finally:
        if conn_n:
            try:
                conn_n.close()
            except Exception:
                pass
        if conn_s:
            try:
                conn_s.close()
            except Exception:
                pass


def get_db_connection(ping_only=False):
    neon_url, supabase_url = _obter_urls_postgres()
    if neon_url:
        erro_neon = None
        try:
            conn_neon = _conectar_pg_direto(neon_url, timeout=18, tentativas=2)
            st.session_state["_banco_ativo_modo"] = "Neon (Principal)"
            if not ping_only and supabase_url:
                _agora_sync = time_module.time()
                if _agora_sync - st.session_state.get("_ultimo_check_sync_conn", 0.0) >= 60:
                    st.session_state["_ultimo_check_sync_conn"] = _agora_sync
                    try:
                        conn_sup_tmp = _conectar_pg_direto(supabase_url, timeout=8, tentativas=1)
                        try:
                            qtd_sinc = _sincronizar_reserva_para_principal(conn_neon, conn_sup_tmp)
                            if qtd_sinc > 0:
                                st.session_state["_qtd_ultima_sincronizacao"] = qtd_sinc
                        finally:
                            conn_sup_tmp.close()
                    except Exception:
                        pass
            return _ConnContingenciaWrapper(conn_neon, em_contingencia=False), "postgres"
        except Exception as e_neon:
            erro_neon = e_neon

        if supabase_url:
            try:
                conn_sup = _conectar_pg_direto(supabase_url, timeout=18, tentativas=2)
                _garantir_schema_postgres(conn_sup)
                _garantir_tabelas_controle_contingencia(conn_sup)
                conn_sup.commit()
                st.cache_data.clear()
                st.session_state["_banco_ativo_modo"] = "Supabase (Contingência Ativa)"
                if not ping_only:
                    st.warning("⚠️ Neon indisponível no momento. Modo contingência ativado no Supabase — tudo que for salvo será sincronizado automaticamente para o Neon assim que ele voltar.")
                return _ConnContingenciaWrapper(conn_sup, em_contingencia=True), "postgres"
            except Exception as e_sup:
                if not ping_only:
                    st.error(f"Erro crítico: Neon ({erro_neon}) e Supabase reserva ({e_sup}) indisponíveis.")
                raise e_sup

        if not ping_only:
            st.error(f"Erro crítico ao conectar no PostgreSQL (Neon): {erro_neon}")
        raise erro_neon

    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
    return conn, "sqlite"


def executar_keep_alive_banco():
    neon_url, supabase_url = _obter_urls_postgres()
    status_detalhes = []
    if neon_url:
        conn_n = None
        conn_s = None
        try:
            conn_n = _conectar_pg_direto(neon_url, timeout=15, tentativas=2)
            cur_n = conn_n.cursor()
            cur_n.execute("SELECT 1")
            cur_n.fetchone()
            conn_n.commit()
            st.cache_data.clear()
            status_detalhes.append("neon:ok")
        except Exception as e_n:
            status_detalhes.append(f"neon:err({e_n})")

        if supabase_url:
            try:
                conn_s = _conectar_pg_direto(supabase_url, timeout=15, tentativas=2)
                cur_s = conn_s.cursor()
                cur_s.execute("SELECT 1")
                cur_s.fetchone()
                conn_s.commit()
                st.cache_data.clear()
                status_detalhes.append("supabase:ok")
                if conn_n is not None:
                    sinc = _sincronizar_reserva_para_principal(conn_n, conn_s)
                    if sinc > 0:
                        status_detalhes.append(f"sync:{sinc}")
                    _espelhar_base_para_reserva(conn_n, conn_s)
                    status_detalhes.append("mirror:ok")
            except Exception as e_s:
                status_detalhes.append(f"supabase:err({e_s})")
            finally:
                if conn_s:
                    try:
                        conn_s.close()
                    except Exception:
                        pass
        if conn_n:
            try:
                conn_n.close()
            except Exception:
                pass
        return True, " | ".join(status_detalhes)

    conn, db_type = get_db_connection(ping_only=True)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return True, db_type
    finally:
        conn.close()


if st.query_params.get("ping") == "1":
    try:
        _, _db_t = executar_keep_alive_banco()
        st.write(f"OK - keep-alive & sync ativo ({_db_t})")
        st.stop()
    except Exception as _err_ping:
        st.write(f"PING_ERR: {_err_ping}")
        st.stop()


def parse_float_ptbr(valor_str):
    if not valor_str or not str(valor_str).strip():
        return 0.0
    try:
        limpo = str(valor_str).replace("R$", "").strip()
        if "." in limpo and "," in limpo:
            limpo = limpo.replace(".", "").replace(",", ".")
        elif "," in limpo:
            limpo = limpo.replace(",", ".")
        return float(limpo)
    except Exception:
        return 0.0

def emitir_notificacao_desktop_web(titulo, mensagem):
    js_code = f"""
    <script>
    if ("Notification" in window) {{
        if (Notification.permission === "granted") {{
            new Notification("{titulo}", {{ body: "{mensagem}", icon: "https://cdn-icons-png.flaticon.com/512/3602/3602145.png" }});
        }} else if (Notification.permission !== "denied") {{
            Notification.requestPermission().then(function (permission) {{
                if (permission === "granted") {{
                    new Notification("{titulo}", {{ body: "{mensagem}" }});
                }}
            }});
        }}
    }}
    </script>
    """
    components.html(js_code, height=0)

def enviar_notificacao_google_chat(mensagem):
    """Envia uma mensagem ao espaço do Google Chat e registra o resultado nos Logs."""
    try:
        webhook_url = st.secrets["google_chat"]["webhook_url"]

        if not webhook_url:
            print("GOOGLE CHAT ERRO: webhook_url está vazio nos Secrets.")
            return False

        webhook_url = str(webhook_url).strip()
        if not webhook_url.startswith("https://chat.googleapis.com/"):
            print("GOOGLE CHAT ERRO: endereço do webhook inválido. Verifique os Secrets.")
            return False

        payload = json.dumps(
            {"text": str(mensagem)},
            ensure_ascii=False
        ).encode("utf-8")

        requisicao = Request(
            webhook_url,
            data=payload,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            method="POST"
        )

        print("GOOGLE CHAT: iniciando envio da notificação...")
        with urlopen(requisicao, timeout=20) as resposta:
            status = resposta.status
            if 200 <= status < 300:
                print(f"GOOGLE CHAT SUCESSO: mensagem aceita. HTTP {status}.")
                return True

            print(f"GOOGLE CHAT ERRO: resposta HTTP {status}.")
            return False

    except KeyError as erro:
        print(f"GOOGLE CHAT ERRO: configuração ausente nos Secrets ({erro}).")
        return False
    except HTTPError as erro:
        # Não registrar a URL do webhook para evitar expor a chave/token nos Logs.
        try:
            detalhe = erro.read().decode("utf-8", errors="replace")
        except Exception:
            detalhe = "Não foi possível ler o detalhe da resposta."
        print(f"GOOGLE CHAT ERRO HTTP: código {erro.code}. Detalhe: {detalhe[:1000]}")
        return False
    except URLError as erro:
        print(f"GOOGLE CHAT ERRO DE CONEXÃO: {erro.reason}")
        return False
    except TimeoutError:
        print("GOOGLE CHAT ERRO: tempo limite de conexão excedido.")
        return False
    except Exception as erro:
        print(f"GOOGLE CHAT ERRO INESPERADO: {type(erro).__name__}: {erro}")
        return False

def disparar_notificacao_sistema(romaneio_dados, itens_lista):
    if HAS_PLYER:
        try:
            total_itens = len(itens_lista)
            primeiro_item = itens_lista[0]['produto'] if total_itens > 0 else "Diversos"
            loja_exibida = romaneio_dados.get('loja', '')
            fornecedor_exibido = romaneio_dados.get('fornecedor', '')
            num_rom = romaneio_dados.get('numero_romaneio', '')
            
            mensagem_detalhes = (
                f"Loja: {loja_exibida}\n"
                f"Fornecedor: {fornecedor_exibido}\n"
                f"Item Principal: {primeiro_item} (Total: {total_itens} itens)"
            )
            notification.notify(
                title=f"📋 Novo Romaneio {num_rom} Cadastrado!",
                message=mensagem_detalhes,
                app_name="HortiControl Supernova",
                timeout=10
            )
        except Exception:
            pass

    if st.session_state.get("notif_desktop_toggle", False):
        total_itens = len(itens_lista)
        num_rom = romaneio_dados.get('numero_romaneio', '')
        forn = romaneio_dados.get('fornecedor', '')
        emitir_notificacao_desktop_web(
            titulo=f"📋 Novo Romaneio {num_rom}!",
            mensagem=f"Fornecedor: {forn} | Total de itens: {total_itens}"
        )

def _normalizar_cabecalho_excel(valor):
    import unicodedata
    texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()

def _ler_excel_repositorio(nome_arquivo):
    """Lê planilhas XLSX versionadas junto do aplicativo no repositório."""
    caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), nome_arquivo)
    if not os.path.isfile(caminho):
        return []
    try:
        abas = pd.read_excel(caminho, sheet_name=None, dtype=str)
        return [df.dropna(how="all") for df in abas.values() if df is not None and not df.empty]
    except Exception as erro_excel:
        print(f"Não foi possível ler {nome_arquivo}: {type(erro_excel).__name__}: {erro_excel}")
        return []

def _achar_coluna_excel(df, tipo):
    """Identifica colunas por nomes completos e abreviados comuns nos cadastros."""
    colunas = [(col, _normalizar_cabecalho_excel(col)) for col in df.columns]

    def tem_codigo(norm):
        return "codigo" in norm or norm.startswith("cod ") or norm == "cod"

    if tipo == "nome_produto":
        # Prioriza descrição/nome do produto e evita colunas de código ou estoque.
        candidatos = []
        for original, norm in colunas:
            if any(x in norm for x in ("codigo", "cod ", "barra", "ean", "unidade", "preco", "valor", "estoque", "saldo")):
                continue
            pontos = 0
            if "produto" in norm: pontos += 5
            if "descricao" in norm or "descr" in norm: pontos += 4
            if "nome" in norm: pontos += 3
            if norm in ("item", "mercadoria"): pontos += 2
            if pontos: candidatos.append((pontos, original))
        if candidatos:
            return max(candidatos, key=lambda x: x[0])[1]

    elif tipo == "codigo_produto":
        candidatos = []
        for original, norm in colunas:
            if not tem_codigo(norm) and not any(x in norm for x in ("sku", "referencia")):
                continue
            if any(x in norm for x in ("barra", "ean", "fornecedor", "forn", "cnpj")):
                continue
            pontos = 1
            if "produto" in norm or "prod " in norm: pontos += 5
            if "interno" in norm or "item" in norm or "sku" in norm: pontos += 3
            if norm in ("codigo", "cod"): pontos += 2
            candidatos.append((pontos, original))
        if candidatos:
            return max(candidatos, key=lambda x: x[0])[1]

    elif tipo == "codigo_barras":
        for original, norm in colunas:
            if any(x in norm for x in ("barra", "ean", "gtin")):
                return original

    elif tipo == "unidade":
        for original, norm in colunas:
            if "unidade" in norm or norm in ("und", "un", "um"):
                return original

    elif tipo == "nome_fornecedor":
        candidatos = []
        for original, norm in colunas:
            if any(x in norm for x in ("codigo", "cod ", "cnpj", "cpf")):
                continue
            pontos = 0
            if "fornecedor" in norm or "forn " in norm: pontos += 5
            if "razao social" in norm or "nome fantasia" in norm: pontos += 5
            if "nome" in norm: pontos += 3
            if norm in ("empresa", "cliente"): pontos += 1
            if pontos: candidatos.append((pontos, original))
        if candidatos:
            return max(candidatos, key=lambda x: x[0])[1]

    elif tipo == "codigo_fornecedor":
        candidatos = []
        for original, norm in colunas:
            if not tem_codigo(norm):
                continue
            if any(x in norm for x in ("cnpj", "cpf", "barra")):
                continue
            pontos = 1
            if "fornecedor" in norm or "forn" in norm: pontos += 6
            if norm in ("codigo", "cod"): pontos += 2
            candidatos.append((pontos, original))
        if candidatos:
            return max(candidatos, key=lambda x: x[0])[1]
    return None


def _valor_excel_texto(valor):
    """Converte valores Excel em texto sem 'nan' ou sufixo .0 em códigos."""
    if valor is None or pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.lower() in ("nan", "none", "nat"):
        return ""
    if re.fullmatch(r"\d+\.0", texto):
        texto = texto[:-2]
    return texto

@st.cache_data(ttl=300, show_spinner=False)
def carregar_produtos_cached():
    produtos = []
    conn, db_type = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT codigo_produto, codigo_barras, nome, unidade_padrao FROM produtos ORDER BY nome ASC")
        produtos.extend(cursor.fetchall())
    finally:
        conn.close()

    # Inclui os produtos dos arquivos PRODUTOS.xlsx/PRODUTO ESTOQUE.xlsx
    # versionados no GitHub, mesmo que ainda não tenham sido cadastrados no banco.
    for nome_arquivo in ("PRODUTOS.xlsx", "PRODUTO ESTOQUE.xlsx"):
        for df in _ler_excel_repositorio(nome_arquivo):
            c_nome = _achar_coluna_excel(df, "nome_produto")
            c_cod = _achar_coluna_excel(df, "codigo_produto")
            c_bar = _achar_coluna_excel(df, "codigo_barras")
            c_un = _achar_coluna_excel(df, "unidade")
            if c_nome is None:
                continue
            for _, row in df.iterrows():
                nome = _valor_excel_texto(row.get(c_nome, ""))
                if not nome or nome.lower() in ("nan", "none", "produto", "descrição", "descricao"):
                    continue
                cod = _valor_excel_texto(row.get(c_cod, "")) if c_cod is not None else ""
                bar = _valor_excel_texto(row.get(c_bar, "")) if c_bar is not None else ""
                un = _valor_excel_texto(row.get(c_un, "")).upper() if c_un is not None else "KG"
                if cod.lower() == "nan": cod = ""
                if bar.lower() == "nan": bar = ""
                if not un or un.lower() == "nan": un = "KG"
                produtos.append((cod, bar, nome, un))

    # Deduplica por nome; mantém os dados do banco e completa códigos vazios pelo XLSX.
    unicos = {}
    for p in produtos:
        chave = _normalizar_cabecalho_excel(p[2])
        if not chave: continue
        if chave not in unicos:
            unicos[chave] = tuple(p)
        else:
            atual = list(unicos[chave])
            for i in (0, 1, 3):
                if (not atual[i] or str(atual[i]).lower() == "nan") and p[i]:
                    atual[i] = p[i]
            unicos[chave] = tuple(atual)
    return sorted(unicos.values(), key=lambda p: str(p[2]).casefold())

@st.cache_data(ttl=300, show_spinner=False)
def carregar_fornecedores_cached():
    fornecedores = []
    conn, db_type = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT nome, codigo_fornecedor FROM fornecedores ORDER BY nome ASC")
        fornecedores.extend(cursor.fetchall())
    finally:
        conn.close()

    # Inclui os fornecedores do arquivo FORNECEDORES.xlsx do repositório.
    for df in _ler_excel_repositorio("FORNECEDORES.xlsx"):
        c_nome = _achar_coluna_excel(df, "nome_fornecedor")
        c_cod = _achar_coluna_excel(df, "codigo_fornecedor")
        if c_nome is None:
            continue
        for _, row in df.iterrows():
            nome = str(row.get(c_nome, "") or "").strip()
            if not nome or nome.lower() in ("nan", "none", "fornecedor", "nome"):
                continue
            cod = str(row.get(c_cod, "") or "").strip() if c_cod is not None else ""
            if cod.lower() == "nan": cod = ""
            fornecedores.append((nome, cod))

    unicos = {}
    for f in fornecedores:
        chave = _normalizar_cabecalho_excel(f[0])
        if not chave: continue
        if chave not in unicos:
            unicos[chave] = tuple(f)
        elif not unicos[chave][1] and f[1]:
            unicos[chave] = (unicos[chave][0], f[1])
    return sorted(unicos.values(), key=lambda f: str(f[0]).casefold())

@st.cache_data(ttl=45, show_spinner=False)
def _carregar_romaneios_e_totais_cached():
    conn, _ = get_db_connection()
    try:
        df_rom = pd.read_sql_query("SELECT id, numero_romaneio, loja, loja_origem, loja_destino, data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista, data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador, status_nota, tipo_operacao, observacoes, ass_conf_b64, ass_ent_b64 FROM romaneios ORDER BY id DESC", conn)
        df_all_itens = pd.read_sql_query("SELECT romaneio_id, SUM(valor_total) as valor_total_rom FROM romaneio_itens GROUP BY romaneio_id", conn)
        return df_rom, df_all_itens
    finally:
        conn.close()

@st.cache_data(ttl=45, show_spinner=False)
def _carregar_bonificacoes_cached():
    conn, _ = get_db_connection()
    try:
        return pd.read_sql_query("SELECT id, numero_nota, loja, data_entrada, valor_bonificacao, status, produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64 FROM bonificacoes ORDER BY id DESC", conn)
    finally:
        conn.close()

@st.cache_data(ttl=45, show_spinner=False)
def _carregar_baixas_avarias_cached():
    conn, _ = get_db_connection()
    try:
        return pd.read_sql_query("SELECT id, loja_baixa, data_baixa, ref_bon_transferen, nf_baixa, nf_b_entrada, produto_hortifruti, quantidade_kg_cx, valor_total_avaria, saldo_restante_nota, saldo_total_disponivel, nf_baixa_b64 FROM baixas_avarias ORDER BY id DESC", conn)
    finally:
        conn.close()

@st.cache_data(ttl=45, show_spinner=False)
def _carregar_dados_bi_cached():
    conn, _ = get_db_connection()
    try:
        df_roms = pd.read_sql_query("SELECT id, numero_romaneio, loja, loja_destino, data_recebimento, tipo_operacao FROM romaneios ORDER BY id DESC", conn)
        df_itens = pd.read_sql_query("SELECT romaneio_id, produto, quantidade, valor_total FROM romaneio_itens", conn)
        df_bonf_rel = pd.read_sql_query("SELECT id, loja, data_entrada, valor_bonificacao, status, produto_hortifruti, tipo_bonificacao FROM bonificacoes ORDER BY id DESC", conn)
        df_baixas_rel = pd.read_sql_query("SELECT id, loja_baixa, data_baixa, produto_hortifruti, quantidade_kg_cx, valor_total_avaria FROM baixas_avarias ORDER BY id DESC", conn)
        return df_roms, df_itens, df_bonf_rel, df_baixas_rel
    finally:
        conn.close()

def remover_fundo_branco(caminho_imagem):
    if not caminho_imagem or not os.path.exists(caminho_imagem):
        return caminho_imagem
    try:
        img = Image.open(caminho_imagem).convert("RGBA")
        datas = list(img.getdata())
        newData = []
        for item in datas:
            if item[0] > 180 and item[1] > 180 and item[2] > 180:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        img.putdata(newData)
        caminho_transparente = caminho_imagem.replace(".png", "_transp.png")
        img.save(caminho_transparente, "PNG")
        return caminho_transparente
    except Exception:
        return caminho_imagem

def exibir_foto_modal(caminho_foto, b64_foto=None):
    if b64_foto:
        try:
            img_data = base64.b64decode(b64_foto)
            if img_data.startswith(b'%PDF'):
                st.success("📄 Documento PDF identificado.")
                st.download_button(
                    label="📥 Baixar / Visualizar PDF Anexado",
                    data=img_data,
                    file_name="documento_anexado.pdf",
                    mime="application/pdf"
                )
                return
            else:
                st.image(img_data, use_container_width=True)
                return
        except Exception:
            pass

    if caminho_foto and caminho_foto.lower().endswith('.pdf'):
        if os.path.exists(caminho_foto):
            with open(caminho_foto, "rb") as f_pdf:
                pdf_bytes = f_pdf.read()
            st.success("📄 Documento PDF identificado.")
            st.download_button(
                label="📥 Baixar / Visualizar PDF Anexado",
                data=pdf_bytes,
                file_name=os.path.basename(caminho_foto),
                mime="application/pdf"
            )
            return

    if caminho_foto and os.path.exists(caminho_foto):
        try:
            st.image(caminho_foto, use_container_width=True)
            return
        except Exception:
            pass
            
    st.warning("Arquivo de anexo não encontrado no servidor ou formato inválido.")

def desenhar_fundo_pdf(canvas_doc, doc_obj):
    logo_p = buscar_caminho_logo_empresa() or buscar_caminho_logo()
    if logo_p and os.path.exists(logo_p):
        try:
            canvas_doc.saveState()
            canvas_doc.setFillAlpha(0.12)
            w_pg, h_pg = doc_obj.pagesize
            w_img, h_img = 320, 220
            x = (w_pg - w_img) / 2
            y = (h_pg / 2) + 40
            canvas_doc.drawImage(logo_p, x, y, width=w_img, height=h_img, mask='auto', preserveAspectRatio=True)
            canvas_doc.restoreState()
        except Exception:
            canvas_doc.restoreState()

def _aplicar_mascara_data_str(valor):
    digitos = "".join(filter(str.isdigit, str(valor or "")))[:8]
    if len(digitos) <= 2:
        return digitos
    if len(digitos) <= 4:
        return f"{digitos[:2]}/{digitos[2:]}"
    return f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"

def seletor_data_unificado(label_titulo, key_prefix, dentro_de_form=False):
    hoje = datetime.now(ZoneInfo("America/Manaus"))
    st.markdown(f"**{label_titulo}**")
    txt_key = f"{key_prefix}_date_text_input"
    if txt_key not in st.session_state:
        st.session_state[txt_key] = hoje.strftime("%d/%m/%Y")

    def _formatar_data_digitada():
        st.session_state[txt_key] = _aplicar_mascara_data_str(st.session_state.get(txt_key, ""))

    if dentro_de_form:
        data_txt = st.text_input(
            label_titulo,
            key=txt_key,
            max_chars=10,
            placeholder="DD/MM/AAAA",
            label_visibility="collapsed"
        )
        data_txt_fmt = _aplicar_mascara_data_str(data_txt)
    else:
        data_txt = st.text_input(
            label_titulo,
            key=txt_key,
            max_chars=10,
            placeholder="DD/MM/AAAA",
            on_change=_formatar_data_digitada,
            label_visibility="collapsed"
        )
        data_txt_fmt = str(data_txt).strip()

    try:
        return datetime.strptime(data_txt_fmt.strip(), "%d/%m/%Y").date()
    except Exception:
        return None

def garantir_tabela_configuracoes_dispositivo():
    """Cria a tabela de preferências visuais vinculadas ao navegador/aparelho."""
    conn, db_type = get_db_connection()
    try:
        cur = conn.cursor()
        if db_type == "postgres":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes_dispositivo (
                    device_id VARCHAR(64) PRIMARY KEY,
                    fonte_cor VARCHAR(20) NOT NULL DEFAULT '#F8FAFC',
                    fonte_tamanho INTEGER NOT NULL DEFAULT 16,
                    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS configuracoes_dispositivo (
                    device_id TEXT PRIMARY KEY,
                    fonte_cor TEXT NOT NULL DEFAULT '#F8FAFC',
                    fonte_tamanho INTEGER NOT NULL DEFAULT 16,
                    atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
        st.cache_data.clear()
    finally:
        conn.close()


@st.cache_data(ttl=120, show_spinner=False)
def carregar_configuracoes_dispositivo(device_id):
    padrao = {"fonte_cor": "#F8FAFC", "fonte_tamanho": 16}
    conn, db_type = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT fonte_cor, fonte_tamanho FROM configuracoes_dispositivo WHERE device_id = %s" if db_type == "postgres" else
            "SELECT fonte_cor, fonte_tamanho FROM configuracoes_dispositivo WHERE device_id = ?",
            (device_id,)
        )
        row = cur.fetchone()
        if row:
            cor = str(row[0] or padrao["fonte_cor"])
            tamanho = max(12, min(24, int(row[1] or 16)))
            return {"fonte_cor": cor, "fonte_tamanho": tamanho}
        return padrao
    finally:
        conn.close()


def salvar_configuracoes_dispositivo(device_id, fonte_cor, fonte_tamanho):
    conn, db_type = get_db_connection()
    try:
        cur = conn.cursor()
        if db_type == "postgres":
            cur.execute("""
                INSERT INTO configuracoes_dispositivo (device_id, fonte_cor, fonte_tamanho, atualizado_em)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (device_id) DO UPDATE SET
                    fonte_cor = EXCLUDED.fonte_cor,
                    fonte_tamanho = EXCLUDED.fonte_tamanho,
                    atualizado_em = CURRENT_TIMESTAMP
            """, (device_id, fonte_cor, int(fonte_tamanho)))
        else:
            cur.execute("""
                INSERT INTO configuracoes_dispositivo (device_id, fonte_cor, fonte_tamanho, atualizado_em)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(device_id) DO UPDATE SET
                    fonte_cor = excluded.fonte_cor,
                    fonte_tamanho = excluded.fonte_tamanho,
                    atualizado_em = CURRENT_TIMESTAMP
            """, (device_id, fonte_cor, int(fonte_tamanho)))
        conn.commit()
        st.cache_data.clear()
        carregar_configuracoes_dispositivo.clear()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    conn, db_type = get_db_connection()
    try:
        cursor = conn.cursor()
        if db_type == "postgres":
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) NOT NULL,
                login VARCHAR(255) UNIQUE NOT NULL,
                senha VARCHAR(255) NOT NULL,
                perfil VARCHAR(255) NOT NULL,
                tema_bg VARCHAR(255) DEFAULT 'Logomarca Oficial Supernova',
                notif_desktop INTEGER DEFAULT 0,
                custom_bg_b64 TEXT
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallpapers (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(255) UNIQUE NOT NULL,
                b64_dados TEXT NOT NULL
            )
            """)
            try:
                cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS tema_bg VARCHAR(255) DEFAULT 'Logomarca Oficial Supernova'")
                cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS notif_desktop INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS custom_bg_b64 TEXT")
            except Exception:
                pass

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
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS troca_avarias (
                id SERIAL PRIMARY KEY,
                numero_controle VARCHAR(100) UNIQUE NOT NULL,
                data_operacao VARCHAR(50) NOT NULL,
                setor_loja VARCHAR(255) NOT NULL,
                fornecedor VARCHAR(255) NOT NULL,
                conferente VARCHAR(255) NOT NULL,
                observacoes TEXT,
                assinatura_responsavel_b64 TEXT NOT NULL,
                assinatura_fornecedor_b64 TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS troca_avarias_itens (
                id SERIAL PRIMARY KEY,
                troca_id INTEGER NOT NULL REFERENCES troca_avarias(id) ON DELETE CASCADE,
                codigo_produto VARCHAR(255),
                descricao_produto VARCHAR(500) NOT NULL,
                quantidade REAL NOT NULL,
                unidade VARCHAR(50) NOT NULL
            )
            """)
            try:
                cursor.execute("ALTER TABLE bonificacoes ADD COLUMN IF NOT EXISTS anexo_b64 TEXT")
                cursor.execute("ALTER TABLE romaneios ADD COLUMN IF NOT EXISTS foto_b64 TEXT")
                cursor.execute("ALTER TABLE baixas_avarias ADD COLUMN IF NOT EXISTS nf_baixa_b64 TEXT")
            except Exception:
                pass

            for _sql_troca_mig in ["ALTER TABLE troca_avarias ADD COLUMN IF NOT EXISTS codigo_fornecedor VARCHAR(255)", "ALTER TABLE troca_avarias ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'Troca pendente'"]:
                try:
                    cursor.execute(_sql_troca_mig)
                except Exception:
                    pass
            cursor.execute("SELECT * FROM usuarios WHERE login = %s", ('908',))
            usr_adm = cursor.fetchone()
            senha_hash_adm = gerar_hash_senha('0332')
            if not usr_adm:
                cursor.execute(
                    "INSERT INTO usuarios (nome, login, senha, perfil, tema_bg, notif_desktop) VALUES (%s, %s, %s, %s, %s, %s)",
                    ('Administrador', '908', senha_hash_adm, 'Gestor', 'Logomarca Oficial Supernova', 0)
                )
        else:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                login TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                perfil TEXT NOT NULL,
                tema_bg TEXT DEFAULT 'Logomarca Oficial Supernova',
                notif_desktop INTEGER DEFAULT 0,
                custom_bg_b64 TEXT
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS wallpapers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT UNIQUE NOT NULL,
                b64_dados TEXT NOT NULL
            )
            """)
            try:
                cursor.execute("ALTER TABLE usuarios ADD COLUMN tema_bg TEXT DEFAULT 'Logomarca Oficial Supernova'")
                cursor.execute("ALTER TABLE usuarios ADD COLUMN notif_desktop INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE usuarios ADD COLUMN custom_bg_b64 TEXT")
            except Exception:
                pass

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
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS troca_avarias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_controle TEXT UNIQUE NOT NULL,
                data_operacao TEXT NOT NULL,
                setor_loja TEXT NOT NULL,
                fornecedor TEXT NOT NULL,
                conferente TEXT NOT NULL,
                observacoes TEXT,
                assinatura_responsavel_b64 TEXT NOT NULL,
                assinatura_fornecedor_b64 TEXT NOT NULL,
                codigo_fornecedor TEXT,
                status TEXT DEFAULT 'Troca pendente',
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS troca_avarias_itens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                troca_id INTEGER NOT NULL,
                codigo_produto TEXT,
                descricao_produto TEXT NOT NULL,
                quantidade REAL NOT NULL,
                unidade TEXT NOT NULL,
                FOREIGN KEY (troca_id) REFERENCES troca_avarias(id) ON DELETE CASCADE
            )
            """)
            try:
                cursor.execute("ALTER TABLE bonificacoes ADD COLUMN anexo_b64 TEXT")
                cursor.execute("ALTER TABLE romaneios ADD COLUMN foto_b64 TEXT")
                cursor.execute("ALTER TABLE baixas_avarias ADD COLUMN nf_baixa_b64 TEXT")
            except Exception:
                pass

            for _sql_troca_mig in ["ALTER TABLE troca_avarias ADD COLUMN codigo_fornecedor TEXT", "ALTER TABLE troca_avarias ADD COLUMN status TEXT DEFAULT 'Troca pendente'"]:
                try:
                    cursor.execute(_sql_troca_mig)
                except Exception:
                    pass
            cursor.execute("SELECT * FROM usuarios WHERE login = '908'")
            usr_adm = cursor.fetchone()
            senha_hash_adm = gerar_hash_senha('0332')
            if not usr_adm:
                cursor.execute(
                    "INSERT INTO usuarios (nome, login, senha, perfil, tema_bg, notif_desktop) VALUES ('Administrador', '908', ?, 'Gestor', 'Logomarca Oficial Supernova', 0)",
                    (senha_hash_adm,)
                )
        conn.commit()
        st.cache_data.clear()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def manter_sessao_ativa_periodica():
    agora_ts = time_module.time()
    ultimo_ping = st.session_state.get("ultimo_keep_alive_ts", 0.0)
    if agora_ts - ultimo_ping >= 240:
        st.session_state["ultimo_keep_alive_ts"] = agora_ts
        try:
            executar_keep_alive_banco()
        except Exception:
            pass

if not st.session_state.get("_schema_inicializado"):
    init_db()
    garantir_tabela_configuracoes_dispositivo()
    st.session_state["_schema_inicializado"] = True
manter_sessao_ativa_periodica()

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def fazer_login(login_ou_nome, senha):
    conn, db_type = get_db_connection()
    try:
        cursor = conn.cursor()
        if db_type == "postgres":
            cursor.execute(
                "SELECT id, nome, perfil, login, senha, tema_bg, notif_desktop, custom_bg_b64 FROM usuarios WHERE login = %s OR LOWER(nome) = LOWER(%s)",
                (login_ou_nome.strip(), login_ou_nome.strip()),
            )
        else:
            cursor.execute(
                "SELECT id, nome, perfil, login, senha, tema_bg, notif_desktop, custom_bg_b64 FROM usuarios WHERE login = ? OR nome COLLATE NOCASE = ?",
                (login_ou_nome.strip(), login_ou_nome.strip()),
            )
        usr = cursor.fetchone()
        if usr:
            senha_banco = usr[4]
            if verificar_senha(senha, senha_banco):
                if senha_banco == senha:
                    hash_novo = gerar_hash_senha(senha)
                    cursor.execute(
                        "UPDATE usuarios SET senha = %s WHERE id = %s" if db_type == "postgres" else "UPDATE usuarios SET senha = ? WHERE id = ?",
                        (hash_novo, usr[0])
                    )
                    conn.commit()
                    st.cache_data.clear()
                return (usr[0], usr[1], usr[2], usr[3], usr[5], usr[6], usr[7])
        return None
    finally:
        conn.close()

def fmt_ptbr(val, decimais=2):
    try:
        f = float(val)
        s = f"{f:,.3f}" if decimais == 3 else f"{f:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"

def gerar_pdf_romaneio(romaneio_data, itens_data):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    style_left = ParagraphStyle('Left', parent=styles['Normal'], alignment=0, fontName='Helvetica', fontSize=9)
    style_center = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontName='Helvetica', fontSize=9)
    style_header_left = ParagraphStyle('HLeft', parent=styles['Normal'], alignment=0, fontName='Helvetica-Bold', fontSize=9, textColor=colors.whitesmoke)
    style_header_center = ParagraphStyle('HCenter', parent=styles['Normal'], alignment=1, fontName='Helvetica-Bold', fontSize=9, textColor=colors.whitesmoke)
    
    logo_path = buscar_caminho_logo()
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
    
    img_conf_pdf = None
    b64_conf = romaneio_data.get('ass_conf_b64', '')
    path_conf = romaneio_data.get('assinatura_conferente', '')
    
    if b64_conf:
        try:
            img_bytes = base64.b64decode(b64_conf)
            img_io = io.BytesIO(img_bytes)
            img_pil = Image.open(img_io).convert("RGBA")
            datas = list(img_pil.getdata())
            newData = []
            for item in datas:
                if item[0] > 180 and item[1] > 180 and item[2] > 180:
                    newData.append((255, 255, 255, 0))
                else:
                    newData.append(item)
            img_pil.putdata(newData)
            buf_clean = io.BytesIO()
            img_pil.save(buf_clean, format="PNG")
            buf_clean.seek(0)
            img_conf_pdf = RLImage(buf_clean, width=180, height=45)
        except Exception:
            pass
    elif path_conf and os.path.exists(path_conf):
        try:
            path_conf_transp = remover_fundo_branco(path_conf)
            img_conf_pdf = RLImage(path_conf_transp, width=180, height=45)
        except Exception:
            pass

    img_ent_pdf = None
    b64_ent = romaneio_data.get('ass_ent_b64', '')
    path_ent = romaneio_data.get('assinatura_entregador', '')
    
    if b64_ent:
        try:
            img_bytes_e = base64.b64decode(b64_ent)
            img_io_e = io.BytesIO(img_bytes_e)
            img_pil_e = Image.open(img_io_e).convert("RGBA")
            datas_e = list(img_pil_e.getdata())
            newData_e = []
            for item in datas_e:
                if item[0] > 180 and item[1] > 180 and item[2] > 180:
                    newData_e.append((255, 255, 255, 0))
                else:
                    newData_e.append(item)
            img_pil_e.putdata(newData_e)
            buf_clean_e = io.BytesIO()
            img_pil_e.save(buf_clean_e, format="PNG")
            buf_clean_e.seek(0)
            img_ent_pdf = RLImage(buf_clean_e, width=180, height=45)
        except Exception:
            pass
    elif path_ent and os.path.exists(path_ent):
        try:
            path_ent_transp = remover_fundo_branco(path_ent)
            img_ent_pdf = RLImage(path_ent_transp, width=180, height=45)
        except Exception:
            pass
        
    col_conf_cell = [img_conf_pdf if img_conf_pdf else Spacer(1, 45), Paragraph(f"<b>Assinatura do Conferente:</b><br/>{romaneio_data.get('conferente','')}", styles["Normal"])]
    col_ent_cell = [img_ent_pdf if img_ent_pdf else Spacer(1, 45), Paragraph(f"<b>Assinatura do Entregador / Fornecedor:</b><br/>{romaneio_data.get('fornecedor','')}", styles["Normal"])]
    ass_table = Table([[col_conf_cell, col_ent_cell]], colWidths=[270, 270])
    ass_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story.append(ass_table)
    
    doc.build(story, onFirstPage=desenhar_fundo_pdf, onLaterPages=desenhar_fundo_pdf)
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
    
    logo_path = buscar_caminho_logo()
    logo_img_header = RLImage(logo_path, width=70, height=50) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
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
    doc.build(story, onFirstPage=desenhar_fundo_pdf, onLaterPages=desenhar_fundo_pdf)
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
    
    logo_path = buscar_caminho_logo()
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
    doc.build(story, onFirstPage=desenhar_fundo_pdf, onLaterPages=desenhar_fundo_pdf)
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
    
    logo_path = buscar_caminho_logo()
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
        s_nota = float(r.get("saldo_restante_calculado", r["saldo_restante_nota"])) if r["saldo_restante_nota"] else 0.0
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
    doc.build(story, onFirstPage=desenhar_fundo_pdf, onLaterPages=desenhar_fundo_pdf)
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
    
    logo_path = buscar_caminho_logo()
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
    
    if not df_bonf_sub.empty:
        for _, r in df_bonf_sub.head(15).iterrows():
            num_nota_val = str(r["numero_nota"]) if "numero_nota" in r and pd.notna(r["numero_nota"]) else str(r.get("numero_romaneio", "N/A"))
            tipo_val = str(r.get("tipo_bonificacao", "Bonificação"))
            loja_val = str(r.get("loja", "N/A"))
            data_val = str(r.get("data_entrada", "N/A"))
            val_b_val = float(r["valor_bonificacao"]) if "valor_bonificacao" in r and pd.notna(r["valor_bonificacao"]) else 0.0
            status_val = str(r.get("status", "N/A"))
            prod_val = str(r.get("produto_hortifruti", "N/A"))

            tb_b.append([
                Paragraph(num_nota_val, style_center),
                Paragraph(tipo_val, style_center),
                Paragraph(loja_val, style_center),
                Paragraph(data_val, style_center),
                Paragraph(f"R$ {fmt_ptbr(val_b_val, 2)}", style_center),
                Paragraph(status_val, style_center),
                Paragraph(prod_val, style_left)
            ])
            
    table_b = Table(tb_b, colWidths=[65, 95, 95, 95, 80, 90, 272])
    table_b.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2D3748")), ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(table_b)
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>2. Resumo de Baixas de Avarias Compensadas (Evitando Perdas Físicas e Financeiras)</b>", styles["Heading3"]))
    
    tb_bx = [[Paragraph("Loja", style_header_center), Paragraph("Data", style_header_center), Paragraph("Ref. Bon.", style_header_center), Paragraph("NF Ent.", style_header_center), Paragraph("Produto", style_header_center), Paragraph("Qtd (kg/cx)", style_header_center), Paragraph("Valor Avaria (R$)", style_header_center)]]
    
    if not df_baixas_sub.empty:
        for _, r in df_baixas_sub.head(15).iterrows():
            loja_bx_val = str(r.get("loja_baixa", "N/A"))
            data_bx_val = str(r.get("data_baixa", "N/A"))
            ref_bx_val = str(r.get("ref_bon_transferen", "N/A"))
            nf_ent_val = str(r.get("nf_b_entrada", "N/A"))
            prod_bx_val = str(r.get("produto_hortifruti", "N/A"))
            qtd_bx_val = float(r["quantidade_kg_cx"]) if "quantidade_kg_cx" in r and pd.notna(r["quantidade_kg_cx"]) else 0.0
            val_av_val = float(r["valor_total_avaria"]) if "valor_total_avaria" in r and pd.notna(r["valor_total_avaria"]) else 0.0

            tb_bx.append([
                Paragraph(loja_bx_val, style_center),
                Paragraph(data_bx_val, style_center),
                Paragraph(ref_bx_val, style_center),
                Paragraph(nf_ent_val, style_center),
                Paragraph(prod_bx_val, style_left),
                Paragraph(fmt_ptbr(qtd_bx_val, 3), style_center),
                Paragraph(f"R$ {fmt_ptbr(val_av_val, 2)}", style_left)
            ])
            
    table_bx = Table(tb_bx, colWidths=[90, 95, 90, 80, 237, 80, 120])
    table_bx.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2D3748")), ("GRID", (0,0), (-1,-1), 0.5, colors.grey), ("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    story.append(table_bx)
    doc.build(story, onFirstPage=desenhar_fundo_pdf, onLaterPages=desenhar_fundo_pdf)
    buffer.seek(0)
    return buffer


# ==============================================================================
# MÓDULO CHATCONTROL - ASSISTENTE INTELIGENTE DE LOGÍSTICA & RELATÓRIOS
# ==============================================================================
LOJAS_MAP_CC = {
    "02": "Loja 02 - Nova Cidade",
    "nova cidade": "Loja 02 - Nova Cidade",
    "03": "Loja 03 - Terra Nova",
    "terra nova": "Loja 03 - Terra Nova",
    "04": "Loja 04 - Manoa",
    "manoa": "Loja 04 - Manoa",
    "05": "Loja 05 - Zumbi",
    "zumbi": "Loja 05 - Zumbi",
    "06": "Loja 06 - Oswaldo Frota",
    "oswaldo frota": "Loja 06 - Oswaldo Frota",
    "07": "Loja 07 - Mosaico",
    "mosaico": "Loja 07 - Mosaico",
}


def _cc_detectar_loja(texto_lower: str, lojas_disponiveis: list) -> str | None:
    for chave, padrao in LOJAS_MAP_CC.items():
        if re.search(rf"\b{re.escape(chave)}\b", texto_lower):
            for lj in lojas_disponiveis:
                if chave in lj.lower() or padrao.split("-")[-1].strip().lower() in lj.lower():
                    return lj
            return padrao
    for lj in lojas_disponiveis:
        if lj.lower() in texto_lower:
            return lj
    return None


def _cc_filtrar_periodo(df: pd.DataFrame, col_data: str, texto_lower: str) -> tuple[pd.DataFrame, str]:
    if df.empty or col_data not in df.columns:
        return df, "Todo o histórico"

    agora = datetime.now(ZoneInfo("America/Manaus"))
    datas = pd.to_datetime(df[col_data].astype(str).str.split(" ").str[0], format="%d/%m/%Y", errors="coerce")

    if "hoje" in texto_lower:
        return df[datas.dt.date == agora.date()], f"Hoje ({agora.strftime('%d/%m/%Y')})"
    if "ontem" in texto_lower:
        ontem = (agora - timedelta(days=1)).date()
        return df[datas.dt.date == ontem], f"Ontem ({ontem.strftime('%d/%m/%Y')})"
    if "7 dias" in texto_lower or "semana" in texto_lower:
        limite = (agora - timedelta(days=7)).replace(tzinfo=None)
        return df[datas >= limite], "Últimos 7 dias"
    if "30 dias" in texto_lower or "mês" in texto_lower or "mes" in texto_lower:
        limite = (agora - timedelta(days=30)).replace(tzinfo=None)
        return df[datas >= limite], "Últimos 30 dias"
    if "90 dias" in texto_lower or "trimestre" in texto_lower:
        limite = (agora - timedelta(days=90)).replace(tzinfo=None)
        return df[datas >= limite], "Últimos 90 dias"

    m_data = re.search(r"(\d{2}/\d{2}/\d{4})", texto_lower)
    if m_data:
        dt_alvo = pd.to_datetime(m_data.group(1), format="%d/%m/%Y", errors="coerce")
        if pd.notna(dt_alvo):
            return df[datas.dt.date == dt_alvo.date()], f"Data {m_data.group(1)}"

    return df, "Todo o histórico"


def _cc_gerar_excel_bytes(abas: dict) -> tuple[bytes, str, str]:
    try:
        import openpyxl  # noqa: F401
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            for nome_aba, df_aba in abas.items():
                nome_limpo = re.sub(r"[\\/*?:\[\]]", "_", nome_aba)[:31] or "Dados"
                df_export = df_aba.copy() if not df_aba.empty else pd.DataFrame({"Aviso": ["Sem registros no filtro"]})
                df_export.to_excel(writer, sheet_name=nome_limpo, index=False)
                ws = writer.sheets[nome_limpo]
                for col in ws.columns:
                    max_len = max(len(str(cell.value or "")) for cell in col)
                    ws.column_dimensions[col[0].column_letter].width = min(max(max_len + 3, 12), 45)
        buffer.seek(0)
        return buffer.getvalue(), "xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    except ImportError:
        primeiro_df = next(iter(abas.values())) if abas else pd.DataFrame()
        csv_bytes = primeiro_df.to_csv(index=False, sep=";").encode("utf-8-sig")
        return csv_bytes, "csv", "text/csv"


def _cc_gerar_pdf_dinamico(titulo_relatorio: str, subtitulo: str, df_dados: pd.DataFrame, resumo_rodape: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    story = []
    styles = getSampleStyleSheet()
    style_cell = ParagraphStyle("CCCell", parent=styles["Normal"], alignment=1, fontName="Helvetica", fontSize=8)
    style_head = ParagraphStyle("CCHead", parent=styles["Normal"], alignment=1, fontName="Helvetica-Bold", fontSize=8, textColor=colors.whitesmoke)

    logo_path = buscar_caminho_logo()
    logo_img = RLImage(logo_path, width=65, height=42) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA</b>", styles["Normal"])
    emissao = datetime.now(ZoneInfo("America/Manaus")).strftime("%d/%m/%Y %H:%M")

    header = Table(
        [[logo_img, Paragraph(f"<b>SUPERMERCADO SUPER NOVA CIDADE</b><br/>ChatControl • {titulo_relatorio}<br/><font size=8>{subtitulo}</font>", styles["Normal"]), Paragraph(f"<b>Emissão:</b> {emissao}<br/><b>Registros:</b> {len(df_dados)}", styles["Normal"])]],
        colWidths=[75, 535, 182],
    )
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey)]))
    story.append(header)
    story.append(Spacer(1, 12))

    if df_dados.empty:
        story.append(Paragraph("Nenhum registro encontrado para os filtros solicitados.", styles["Normal"]))
    else:
        df_pdf = df_dados.iloc[:, :9].head(150)
        col_w = 792.0 / max(len(df_pdf.columns), 1)
        tabela_rows = [[Paragraph(str(c), style_head) for c in df_pdf.columns]]
        for _, row in df_pdf.iterrows():
            tabela_rows.append([Paragraph(str(val if pd.notna(val) else "-"), style_cell) for val in row])

        tbl = Table(tabela_rows, colWidths=[col_w] * len(df_pdf.columns))
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F8")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(tbl)

    if resumo_rodape:
        story.append(Spacer(1, 10))
        foot = Table([[resumo_rodape]], colWidths=[792])
        foot.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1A202C")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        story.append(foot)

    doc.build(story, onFirstPage=desenhar_fundo_pdf, onLaterPages=desenhar_fundo_pdf)
    buffer.seek(0)
    return buffer.getvalue()


def _cc_processar_comando(prompt: str) -> dict:
    texto = prompt.strip()
    texto_lower = texto.lower()
    ts_str = datetime.now(ZoneInfo("America/Manaus")).strftime("%Y%m%d_%H%M")

    conn, _ = get_db_connection()
    try:
        df_bonf = pd.read_sql_query("SELECT id, numero_nota, loja, data_entrada, valor_bonificacao, status, produto_hortifruti, tipo_bonificacao FROM bonificacoes ORDER BY id DESC", conn)
        df_baixas = pd.read_sql_query("SELECT id, loja_baixa, data_baixa, ref_bon_transferen, nf_baixa, nf_b_entrada, produto_hortifruti, quantidade_kg_cx, valor_total_avaria, saldo_restante_nota, saldo_total_disponivel FROM baixas_avarias ORDER BY id DESC", conn)
        df_rom = pd.read_sql_query("""
            SELECT r.id, r.numero_romaneio, r.loja, r.data_recebimento, r.fornecedor, r.conferente, r.tipo_operacao, r.status_nota,
                   COALESCE(SUM(i.valor_total), 0) AS valor_total_romaneio, COUNT(i.id) AS qtd_itens
            FROM romaneios r
            LEFT JOIN romaneio_itens i ON i.romaneio_id = r.id
            GROUP BY r.id, r.numero_romaneio, r.loja, r.data_recebimento, r.fornecedor, r.conferente, r.tipo_operacao, r.status_nota
            ORDER BY r.id DESC
        """, conn)
    finally:
        conn.close()

    lojas_existentes = sorted(list(
        set(df_bonf["loja"].dropna().astype(str))
        | set(df_baixas["loja_baixa"].dropna().astype(str))
        | set(df_rom["loja"].dropna().astype(str))
    ))
    loja_filtro = _cc_detectar_loja(texto_lower, lojas_existentes)

    # 1. BAIXAS DE AVARIAS
    if any(k in texto_lower for k in ["avaria", "avarias", "baixa", "baixas", "perda", "perdas"]):
        df_f = df_baixas.copy()
        if loja_filtro and not df_f.empty:
            df_f = df_f[df_f["loja_baixa"].str.lower() == loja_filtro.lower()]
        df_f, lbl_periodo = _cc_filtrar_periodo(df_f, "data_baixa", texto_lower)

        tot_avaria = float(df_f["valor_total_avaria"].sum()) if not df_f.empty else 0.0
        tot_qtd = float(df_f["quantidade_kg_cx"].sum()) if not df_f.empty else 0.0
        escopo = f"**{loja_filtro}**" if loja_filtro else "**Todas as Lojas**"

        resposta = (
            f"### 📉 Relatório de Baixas de Avarias\n"
            f"- **Escopo:** {escopo} | **Período:** {lbl_periodo}\n"
            f"- **Registros encontrados:** {len(df_f)}\n"
            f"- **Volume total baixado:** {fmt_ptbr(tot_qtd, 3)} kg/cx\n"
            f"- **Valor total compensado:** **R$ {fmt_ptbr(tot_avaria, 2)}**\n\n"
            f"Os arquivos em **PDF** e **Excel** estão prontos para download abaixo."
        )
        pdf_bytes = gerar_pdf_baixas(df_f).getvalue()
        plan_bytes, plan_ext, plan_mime = _cc_gerar_excel_bytes({"Baixas_Avarias": df_f})
        return {
            "role": "assistant",
            "content": resposta,
            "df_preview": df_f[["loja_baixa", "data_baixa", "nf_b_entrada", "produto_hortifruti", "quantidade_kg_cx", "valor_total_avaria"]].head(15) if not df_f.empty else None,
            "files": [
                {"label": "📥 Baixar PDF - Baixas de Avarias", "data": pdf_bytes, "file_name": f"ChatControl_Baixas_Avarias_{ts_str}.pdf", "mime": "application/pdf"},
                {"label": f"📊 Baixar Planilha (.{plan_ext})", "data": plan_bytes, "file_name": f"ChatControl_Baixas_Avarias_{ts_str}.{plan_ext}", "mime": plan_mime},
            ],
        }

    # 2. BONIFICAÇÕES E SALDOS
    if any(k in texto_lower for k in ["bonifica", "saldo", "nota", "transferência", "transferencia"]):
        df_f = df_bonf.copy()
        if loja_filtro and not df_f.empty:
            df_f = df_f[df_f["loja"].str.lower() == loja_filtro.lower()]
        if "disponível" in texto_lower or "disponivel" in texto_lower or "saldo" in texto_lower:
            df_f = df_f[df_f["status"].isin(["Disponível", "Parcialmente Utilizada"])]
        df_f, lbl_periodo = _cc_filtrar_periodo(df_f, "data_entrada", texto_lower)

        tot_bonf = float(df_f["valor_bonificacao"].sum()) if not df_f.empty else 0.0
        escopo = f"**{loja_filtro}**" if loja_filtro else "**Todas as Lojas**"

        resposta = (
            f"### 🎁 Controle de Bonificações\n"
            f"- **Escopo:** {escopo} | **Período:** {lbl_periodo}\n"
            f"- **Notas listadas:** {len(df_f)}\n"
            f"- **Valor total bonificado/transferido:** **R$ {fmt_ptbr(tot_bonf, 2)}**\n\n"
            f"Arquivos gerados e disponíveis abaixo."
        )
        pdf_bytes = gerar_pdf_bonificacoes(df_f).getvalue()
        plan_bytes, plan_ext, plan_mime = _cc_gerar_excel_bytes({"Bonificacoes": df_f})
        return {
            "role": "assistant",
            "content": resposta,
            "df_preview": df_f[["numero_nota", "tipo_bonificacao", "loja", "data_entrada", "valor_bonificacao", "status", "produto_hortifruti"]].head(15) if not df_f.empty else None,
            "files": [
                {"label": "📥 Baixar PDF - Bonificações", "data": pdf_bytes, "file_name": f"ChatControl_Bonificacoes_{ts_str}.pdf", "mime": "application/pdf"},
                {"label": f"📊 Baixar Planilha (.{plan_ext})", "data": plan_bytes, "file_name": f"ChatControl_Bonificacoes_{ts_str}.{plan_ext}", "mime": plan_mime},
            ],
        }

    # 3. ROMANEIOS DE RECEBIMENTO
    if any(k in texto_lower for k in ["romaneio", "romaneios", "recebimento", "fornecedor", "compra"]):
        df_f = df_rom.copy()
        if loja_filtro and not df_f.empty:
            df_f = df_f[df_f["loja"].str.lower() == loja_filtro.lower()]
        df_f, lbl_periodo = _cc_filtrar_periodo(df_f, "data_recebimento", texto_lower)

        tot_rom = float(df_f["valor_total_romaneio"].sum()) if not df_f.empty else 0.0
        escopo = f"**{loja_filtro}**" if loja_filtro else "**Todas as Lojas**"

        resposta = (
            f"### 📋 Relatório de Romaneios de Recebimento\n"
            f"- **Escopo:** {escopo} | **Período:** {lbl_periodo}\n"
            f"- **Total de romaneios:** {len(df_f)}\n"
            f"- **Valor financeiro total:** **R$ {fmt_ptbr(tot_rom, 2)}**\n\n"
            f"Baixe o consolidado em **PDF** ou **Excel** abaixo."
        )
        df_exibir = df_f[["numero_romaneio", "loja", "data_recebimento", "fornecedor", "conferente", "tipo_operacao", "qtd_itens", "valor_total_romaneio"]].copy()
        df_exibir.columns = ["Romaneio", "Loja", "Data", "Fornecedor", "Conferente", "Operação", "Itens", "Total (R$)"]
        pdf_bytes = _cc_gerar_pdf_dinamico(
            "Relatório Consolidado de Romaneios",
            f"Escopo: {loja_filtro or 'Todas as Lojas'} | Período: {lbl_periodo}",
            df_exibir,
            f"TOTAL GERAL DOS ROMANEIOS: R$ {fmt_ptbr(tot_rom, 2)}",
        )
        plan_bytes, plan_ext, plan_mime = _cc_gerar_excel_bytes({"Romaneios": df_exibir})
        return {
            "role": "assistant",
            "content": resposta,
            "df_preview": df_exibir.head(15) if not df_exibir.empty else None,
            "files": [
                {"label": "📥 Baixar PDF - Romaneios", "data": pdf_bytes, "file_name": f"ChatControl_Romaneios_{ts_str}.pdf", "mime": "application/pdf"},
                {"label": f"📊 Baixar Planilha (.{plan_ext})", "data": plan_bytes, "file_name": f"ChatControl_Romaneios_{ts_str}.{plan_ext}", "mime": plan_mime},
            ],
        }

    # 4. RESUMO EXECUTIVO GERAL / BI
    df_b_sub = df_bonf.copy()
    df_bx_sub = df_baixas.copy()
    if loja_filtro:
        if not df_b_sub.empty:
            df_b_sub = df_b_sub[df_b_sub["loja"].str.lower() == loja_filtro.lower()]
        if not df_bx_sub.empty:
            df_bx_sub = df_bx_sub[df_bx_sub["loja_baixa"].str.lower() == loja_filtro.lower()]

    df_b_sub, lbl_periodo = _cc_filtrar_periodo(df_b_sub, "data_entrada", texto_lower)
    df_bx_sub, _ = _cc_filtrar_periodo(df_bx_sub, "data_baixa", texto_lower)

    v_tot_bonf = float(df_b_sub[df_b_sub.get("tipo_bonificacao", "Bonificação") == "Bonificação"]["valor_bonificacao"].sum()) if not df_b_sub.empty else 0.0
    v_tot_transf = float(df_b_sub[df_b_sub.get("tipo_bonificacao", "Bonificação") == "Transferência de Bonificação"]["valor_bonificacao"].sum()) if not df_b_sub.empty else 0.0
    v_tot_entradas = float(df_b_sub["valor_bonificacao"].sum()) if not df_b_sub.empty else 0.0
    v_tot_avarias = float(df_bx_sub["valor_total_avaria"].sum()) if not df_bx_sub.empty else 0.0
    taxa_cobertura = float((v_tot_avarias / v_tot_entradas * 100)) if v_tot_entradas > 0 else 0.0
    saldo_restante = float(max(0.0, v_tot_entradas - v_tot_avarias))

    metrics_dict = {
        "tot_bonf": v_tot_bonf,
        "tot_transf": v_tot_transf,
        "tot_avaria": v_tot_avarias,
        "taxa_cobertura": taxa_cobertura,
        "saldo_restante": saldo_restante,
    }
    escopo = f"**{loja_filtro}**" if loja_filtro else "**Todas as Lojas (Rede Super Nova Cidade)**"
    resposta = (
        f"### 🏆 Resumo Executivo Gerencial — HortiControl\n"
        f"- **Escopo:** {escopo} | **Período:** {lbl_periodo}\n"
        f"- **1. Entradas Bonificadas:** R$ {fmt_ptbr(v_tot_bonf, 2)}\n"
        f"- **2. Transferências:** R$ {fmt_ptbr(v_tot_transf, 2)}\n"
        f"- **3. Perdas Evitadas (Avarias Cobertas):** **R$ {fmt_ptbr(v_tot_avarias, 2)}**\n"
        f"- **4. Taxa de Cobertura:** {fmt_ptbr(taxa_cobertura, 2)}%\n"
        f"- **5. Saldo Remanescente:** **R$ {fmt_ptbr(saldo_restante, 2)}**\n\n"
        f"O **PDF Executivo** e a **Planilha Completa (.xlsx)** estão prontos para download abaixo."
    )
    pdf_bi_bytes = gerar_pdf_relatorio_gerencial_bi(metrics_dict, df_b_sub, df_bx_sub).getvalue()
    plan_bi_bytes, plan_bi_ext, plan_bi_mime = _cc_gerar_excel_bytes({
        "Resumo_KPIs": pd.DataFrame([metrics_dict]),
        "Bonificacoes": df_b_sub,
        "Baixas_Avarias": df_bx_sub,
        "Romaneios": df_rom,
    })
    return {
        "role": "assistant",
        "content": resposta,
        "df_preview": None,
        "files": [
            {"label": "📥 Baixar PDF Executivo (BI)", "data": pdf_bi_bytes, "file_name": f"ChatControl_Relatorio_Executivo_{ts_str}.pdf", "mime": "application/pdf"},
            {"label": f"📊 Baixar Planilha Completa (.{plan_bi_ext})", "data": plan_bi_bytes, "file_name": f"ChatControl_Dados_Completos_{ts_str}.{plan_bi_ext}", "mime": plan_bi_mime},
        ],
    }


def _cc_buscar_mascote():
    for candidato in [
        "mascote_chatcontrol.png",
        "mascote_chatcontrol.png.png",
        "mascote_chatcontrol.jpg",
        "mascote_chatcontrol.jpeg",
    ]:
        if os.path.exists(candidato) and os.path.isfile(candidato):
            return candidato
    if os.path.exists("."):
        for arq in os.listdir("."):
            if arq.lower().startswith("mascote_chatcontrol") and os.path.isfile(arq):
                return arq
    return None


def _cc_mascote_b64():
    caminho = _cc_buscar_mascote()
    if not caminho:
        return "", "image/png"
    return obter_arquivo_b64_e_mime(caminho)


def render_chat_control():
    b64_m, mime_m = _cc_mascote_b64()
    mascote_path = _cc_buscar_mascote()
    avatar_cc = mascote_path if mascote_path else "🍏"

    if b64_m:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:14px; margin-bottom:8px;">
                <img src="data:{mime_m};base64,{b64_m}"
                     style="width:58px; height:58px; border-radius:50%; object-fit:cover;
                            border:2px solid #4CAF50; box-shadow:0 4px 12px rgba(0,0,0,0.45);" />
                <div>
                    <h3 style="margin:0; padding:0;">ChatControl — Assistente Inteligente de Logística</h3>
                    <span style="font-size:13px; opacity:0.85;">
                        Solicite relatórios gerenciais, saldos de bonificação, baixas de avarias ou romaneios por loja e período.
                    </span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown("### 🍏 ChatControl — Assistente Inteligente de Logística")
        st.caption("Solicite relatórios gerenciais, saldos de bonificação, baixas de avarias ou romaneios por loja e período.")

    if "chatcontrol_mensagens" not in st.session_state:
        st.session_state["chatcontrol_mensagens"] = [
            {
                "role": "assistant",
                "content": (
                    "Olá! Sou o **ChatControl** do HortiControl. Posso consultar o banco de dados em tempo real e gerar relatórios prontos para download em **PDF** e **Excel**.\n\n"
                    "**Exemplos do que você pode pedir:**\n"
                    "- *\"Gerar relatório executivo geral\"*\n"
                    "- *\"Relatório de baixas de avarias da Loja 04 Manoa nos últimos 30 dias\"*\n"
                    "- *\"Mostrar saldo disponível de bonificações\"*\n"
                    "- *\"Romaneios recebidos hoje\"*"
                ),
                "df_preview": None,
                "files": [],
            }
        ]

    col_at1, col_at2, col_at3, col_at4 = st.columns(4)
    atalho_prompt = None
    if col_at1.button("📊 Resumo Executivo", use_container_width=True, key="cc_btn_exec"):
        atalho_prompt = "Gerar relatório executivo geral"
    if col_at2.button("🎁 Saldos Bonificação", use_container_width=True, key="cc_btn_bonf"):
        atalho_prompt = "Mostrar saldo disponível de bonificações"
    if col_at3.button("📉 Baixas de Avarias", use_container_width=True, key="cc_btn_avaria"):
        atalho_prompt = "Relatório de baixas de avarias"
    if col_at4.button("🗑️ Limpar Chat", use_container_width=True, key="cc_btn_limpar"):
        st.session_state["chatcontrol_mensagens"] = st.session_state["chatcontrol_mensagens"][:1]
        st.rerun()

    st.markdown("---")

    box_msgs = st.container(height=360)
    with box_msgs:
        for idx_msg, msg in enumerate(st.session_state["chatcontrol_mensagens"]):
            av = avatar_cc if msg["role"] == "assistant" else None
            with st.chat_message(msg["role"], avatar=av):
                st.markdown(msg["content"])
                if msg.get("df_preview") is not None and not msg["df_preview"].empty:
                    st.dataframe(msg["df_preview"], use_container_width=True, hide_index=True)
                arquivos = msg.get("files") or []
                if arquivos:
                    cols_dl = st.columns(len(arquivos))
                    for idx_f, arq in enumerate(arquivos):
                        with cols_dl[idx_f]:
                            st.download_button(
                                label=arq["label"],
                                data=arq["data"],
                                file_name=arq["file_name"],
                                mime=arq["mime"],
                                type="primary" if idx_f == 0 else "secondary",
                                key=f"cc_dl_{idx_msg}_{idx_f}",
                                use_container_width=True,
                            )

    prompt_usuario = st.chat_input("Digite sua solicitação para o ChatControl (ex: Relatório de avarias Loja 02)...")
    comando_final = atalho_prompt or prompt_usuario

    if comando_final:
        st.session_state["chatcontrol_mensagens"].append({
            "role": "user",
            "content": comando_final,
            "df_preview": None,
            "files": [],
        })
        with st.spinner("ChatControl consultando dados e gerando arquivos..."):
            resposta_bot = _cc_processar_comando(comando_final)
        st.session_state["chatcontrol_mensagens"].append(resposta_bot)
        st.rerun()


@st.dialog("🍏 ChatControl — Assistente Inteligente de Logística", width="large")
def _abrir_modal_chatcontrol():
    render_chat_control()


def render_widget_flutuante_chatcontrol():
    """Renderiza o botão flutuante discreto do ChatControl acima da barra inferior."""
    b64_m, mime_m = _cc_mascote_b64()
    icone_url = f"data:{mime_m};base64,{b64_m}" if b64_m else ""

    if icone_url:
        st.markdown(
            f"""
            <style>
            div.st-key-btn_flutuante_chatcontrol {{
                position: fixed !important;
                bottom: 84px !important;
                right: 20px !important;
                left: auto !important;
                z-index: 2147483647 !important;
                width: auto !important;
            }}
            div.st-key-btn_flutuante_chatcontrol button {{
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                width: 60px !important;
                height: 60px !important;
                min-height: 60px !important;
                padding: 0 !important;
                border-radius: 50% !important;
                border: 2px solid #4CAF50 !important;
                background-color: #0E140C !important;
                background-image: url("{icone_url}") !important;
                background-size: cover !important;
                background-repeat: no-repeat !important;
                background-position: center !important;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.7) !important;
                transition: transform 0.2s ease !important;
                overflow: hidden !important;
                position: relative !important;
                z-index: 2147483647 !important;
            }}
            div.st-key-btn_flutuante_chatcontrol button:hover {{
                transform: scale(1.07) !important;
            }}
            div.st-key-btn_flutuante_chatcontrol button::before,
            div.st-key-btn_flutuante_chatcontrol button::after,
            div.st-key-btn_flutuante_chatcontrol::before,
            div.st-key-btn_flutuante_chatcontrol::after {{
                display: none !important;
                content: none !important;
            }}
            div.st-key-btn_flutuante_chatcontrol button p,
            div.st-key-btn_flutuante_chatcontrol button span {{
                display: none !important;
                font-size: 0 !important;
                color: transparent !important;
                background: transparent !important;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            div.st-key-btn_flutuante_chatcontrol {
                position: fixed !important;
                bottom: 84px !important;
                right: 20px !important;
                left: auto !important;
                z-index: 2147483647 !important;
                width: auto !important;
            }
            div.st-key-btn_flutuante_chatcontrol button {
                border-radius: 50% !important;
                width: 56px !important;
                height: 56px !important;
                min-height: 56px !important;
                padding: 0 !important;
                border: 2px solid #4CAF50 !important;
                background-color: #1B5E20 !important;
                color: #FFFFFF !important;
                font-weight: 700 !important;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.7) !important;
                position: relative !important;
                z-index: 2147483647 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    if st.button("CC", key="btn_flutuante_chatcontrol", help="Abrir ChatControl"):
        _abrir_modal_chatcontrol()


def obter_css_fundo(tema_selecionado, custom_b64=""):
    if tema_selecionado == "Fundo Branco":
        return """
        <style>
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: #FFFFFF !important;
            color: #111827 !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label, .stApp li {
            color: #111827 !important;
        }
        </style>
        """
    elif tema_selecionado == "Verde Supernova (Escuro)":
        return """
        <style>
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: #0E140C !important;
            color: #F8FAFC !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label, .stApp li {
            color: #F8FAFC !important;
        }
        </style>
        """
    elif tema_selecionado == "Azul Corporativo Executivo":
        return """
        <style>
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: #0A192F !important;
            color: #F8FAFC !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label, .stApp li {
            color: #F8FAFC !important;
        }
        </style>
        """
    elif tema_selecionado == "Grafite High-Tech":
        return """
        <style>
        .stApp, [data-testid="stAppViewContainer"] {
            background-color: #181A1B !important;
            color: #F8FAFC !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label, .stApp li {
            color: #F8FAFC !important;
        }
        </style>
        """
    elif custom_b64:
        return f"""
        <style>
        .stApp, [data-testid="stAppViewContainer"] {{
            background-image: linear-gradient(rgba(0,0,0,0.72), rgba(0,0,0,0.72)), url("data:image/jpeg;base64,{custom_b64}");
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: #F8FAFC !important;
        }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label, .stApp li {{
            color: #F8FAFC !important;
        }}
        </style>
        """
    return """
    <style>
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp span, .stApp label, .stApp li {
        color: #F8FAFC !important;
    }
    </style>
    """

img_padrao_fundo = None
arquivos_raiz = os.listdir(".") if os.path.exists(".") else []
candidatos_prioritarios = [
    "tela de login padrao.jpeg",
    "tela de login padrao.jpg",
    "tela de login padrao.png",
    "tela de login padrao.jpeg.jpeg",
    "tela_de_login_padrao.jpeg",
    "tela_de_login_padrao.jpg",
    "tela_de_login_padrao.png",
]
for cand in candidatos_prioritarios:
    for arq in arquivos_raiz:
        if arq.lower() == cand.lower():
            img_padrao_fundo = arq
            break
    if img_padrao_fundo:
        break

if not img_padrao_fundo:
    for arq in arquivos_raiz:
        if "tela de login padrao" in arq.lower() or "tela_de_login_padrao" in arq.lower():
            img_padrao_fundo = arq
            break

b64_padrao_global = ""
if img_padrao_fundo:
    try:
        with open(img_padrao_fundo, "rb") as f_bg_glob:
            b64_padrao_global = base64.b64encode(f_bg_glob.read()).decode('utf-8')
    except Exception:
        pass

# ---------------------------------------------------------
# TELA DE LOGIN
# ---------------------------------------------------------
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

if st.session_state["usuario_logado"] is None:
    tema_login_padrao = st.session_state.get("tema_bg_selecionado", "Logomarca Oficial Supernova")
    b64_login_padrao = st.session_state.get("custom_bg_b64", b64_padrao_global)
    css_login = obter_css_fundo(tema_login_padrao, b64_login_padrao)
    if css_login:
        st.markdown(css_login, unsafe_allow_html=True)

    logo_display = buscar_caminho_icone_app()
    if not logo_display:
        for nome in ["logo_romaneio.png.jpg", "logo_romaneio.png", "logo.png", "tela de login padrao.jpeg", "Tela de login.jpeg.jpeg"]:
            if os.path.exists(nome):
                logo_display = nome
                break
            
    if logo_display:
        logo_b64_transp = obter_logo_transparente_b64(logo_display)
        if logo_b64_transp:
            st.markdown(
                f"""
                <div style="width: 100%; display: flex; justify-content: center; align-items: center; margin: 4px auto 18px auto; padding: 0; text-align: center;">
                    <img src="data:image/png;base64,{logo_b64_transp}" 
                         style="display: block; margin: 0 auto; max-height: 200px; max-width: 72vw; width: auto; height: auto;
                                filter: drop-shadow(0px 12px 22px rgba(0,0,0,0.85)) 
                                        drop-shadow(0px 4px 10px rgba(0,200,0,0.35));" />
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            b64_raw_lg, mime_raw_lg = obter_arquivo_b64_e_mime(logo_display)
            if b64_raw_lg:
                st.markdown(
                    f"""
                    <div style="width: 100%; display: flex; justify-content: center; align-items: center; margin: 4px auto 18px auto;">
                        <img src="data:{mime_raw_lg};base64,{b64_raw_lg}"
                             style="display: block; margin: 0 auto; width: 190px; max-width: 70vw; border-radius: 28px;" />
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    col_vazia_esq, col_central, col_vazia_dir = st.columns([0.1, 3.8, 0.1])
    with col_central:
                
        st.markdown("<h2 style='text-align: center; color: white;'>HortiControl - Sistema de Recebimento Hortifrúti</h2>", unsafe_allow_html=True)
            
        with st.form("form_login"):
            login_input = st.text_input("Usuário / Login ou Nome Completo", value="", placeholder="Digite seu usuário ou nome...")
            senha_input = st.text_input("Senha", type="password", value="", placeholder="Digite sua senha...")
            loja_login_sel = st.selectbox(
                "Selecione a Loja de Atuação",
                ["", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"],
                index=0
            )
            btn_entrar = st.form_submit_button("Entrar no Sistema", type="primary")
            if btn_entrar:
                if not loja_login_sel:
                    st.error("Por favor, selecione a loja em que você está atuando antes de entrar.")
                else:
                    with spinner_supernova("Validando acesso no Supernova..."):
                        usuario = fazer_login(login_input, senha_input)
                        if usuario:
                            st.session_state["usuario_logado"] = {
                                "id": usuario[0],
                                "nome": usuario[1],
                                "perfil": usuario[2],
                                "login": usuario[3],
                                "loja_atual": loja_login_sel
                            }
                            tema_usr_db = usuario[4] if usuario[4] else "Logomarca Oficial Supernova"
                            st.session_state["tema_bg_selecionado"] = tema_usr_db
                            st.session_state["notif_desktop_toggle"] = bool(usuario[5]) if usuario[5] is not None else False
                            
                            if usuario[6]:
                                st.session_state["custom_bg_b64"] = usuario[6]
                            elif tema_usr_db == "Logomarca Oficial Supernova":
                                st.session_state["custom_bg_b64"] = b64_padrao_global

                            st.success(f"Bem-vindo(a), {usuario[1]} na {loja_login_sel}!")
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")
else:
    user_info = st.session_state["usuario_logado"]
    perfil_db = str(user_info.get("perfil", "")).strip().lower()
    
    # Apenas o administrador/gestor pode alterar as preferências deste aparelho.
    is_admin = (str(user_info.get("login", "")).lower() == "908" or "gestor" in perfil_db or "adm" in perfil_db or "assistente" in perfil_db)
    is_auxiliar = ("auxiliar" in perfil_db)
    is_conferente = ("conferente" in perfil_db and not is_admin and not is_auxiliar)

    # Preferências são carregadas pelo ID do navegador, não pelo usuário logado.
    # Assim, após o administrador salvar e sair, o conferente verá o mesmo padrão.
    try:
        _prefs_device = carregar_configuracoes_dispositivo(_device_id)
    except Exception as _prefs_error:
        print(f"CONFIG DISPOSITIVO: não foi possível carregar preferências: {_prefs_error}")
        _prefs_device = {"fonte_cor": "#F8FAFC", "fonte_tamanho": 16}
    st.session_state["_fonte_cor_dispositivo"] = _prefs_device["fonte_cor"]
    st.session_state["_fonte_tamanho_dispositivo"] = _prefs_device["fonte_tamanho"]
    loja_atual_usuario = user_info.get("loja_atual", "Não definida")

    tema_selecionado_usuario = st.session_state.get("tema_bg_selecionado", "Logomarca Oficial Supernova")
    custom_bg_b64_usuario = st.session_state.get("custom_bg_b64", b64_padrao_global)
    
    if tema_selecionado_usuario == "Logomarca Oficial Supernova" and not custom_bg_b64_usuario:
        custom_bg_b64_usuario = b64_padrao_global
        st.session_state["custom_bg_b64"] = custom_bg_b64_usuario

    css_fundo_dinamico = obter_css_fundo(tema_selecionado_usuario, custom_bg_b64_usuario)
    if css_fundo_dinamico:
        st.markdown(css_fundo_dinamico, unsafe_allow_html=True)

    # Aplicar depois do tema para que a preferência do administrador prevaleça.
    st.markdown(f"""<style>
    .stApp, .stApp p, .stApp label, .stApp span, .stApp li,
    .stApp div[data-testid="stMarkdownContainer"],
    .stApp input, .stApp textarea, .stApp select,
    .stApp [data-testid="stMetricValue"] {{
        color: {_prefs_device['fonte_cor']} !important;
        font-size: {_prefs_device['fonte_tamanho']}px !important;
    }}
    </style>""", unsafe_allow_html=True)

    st.markdown("---")
    tipo_perfil_txt = f"👤 {user_info.get('perfil', 'Usuário')} ({loja_atual_usuario})"
    modo_bd_atual = st.session_state.get("_banco_ativo_modo", "Neon (Principal)")
    cor_bd_badge = "#2e7d32" if "Principal" in modo_bd_atual else "#ed6c02"
    st.markdown(
        f"**Usuário:** {user_info['nome']} &nbsp;|&nbsp; **Perfil:** {tipo_perfil_txt} &nbsp;|&nbsp; "
        f"<span style='background:{cor_bd_badge};color:#fff;padding:2px 8px;border-radius:10px;font-size:13px;'>🗄️ {modo_bd_atual}</span>",
        unsafe_allow_html=True,
    )
    qtd_sync_recente = st.session_state.pop("_qtd_ultima_sincronizacao", 0)
    if qtd_sync_recente > 0:
        st.success(f"🔄 {qtd_sync_recente} registro(s) salvos na contingência (Supabase) foram sincronizados automaticamente para o Neon!")

    _colunas_topo = st.columns([1.2, 1.2, 1.0] if is_admin else [1.2, 1.0], vertical_alignment="center")
    with _colunas_topo[0]:
        if st.button("🔄 Atualizar aplicativo", type="secondary", key="btn_atualizar_app_topo", use_container_width=True, help="Limpar caches, sincronizar e recarregar os dados"):
            with spinner_supernova("Atualizando aplicativo e dados..."):
                try:
                    st.cache_data.clear()
                except Exception:
                    for _cache_fn in (carregar_produtos_cached, carregar_fornecedores_cached):
                        try:
                            _cache_fn.clear()
                        except Exception:
                            pass
                try:
                    tentar_reconciliacao_automatica(forcar=True)
                except Exception as _refresh_error:
                    print(f"ATUALIZAR APP: falha na sincronização: {_refresh_error}")
            st.rerun()
    if is_admin:
        with _colunas_topo[1]:
            if st.button("⚙️ Configurações", type="primary", key="btn_abrir_config_topo", use_container_width=True):
                st.session_state["exibir_modal_config"] = not st.session_state.get("exibir_modal_config", False)
    with _colunas_topo[-1]:
        if st.button("🚪 Sair", type="secondary", key="btn_sair_sistema_principal", use_container_width=True):
            st.session_state["usuario_logado"] = None
            st.session_state["exibir_modal_config"] = False
            st.rerun()

    if is_admin and st.session_state.get("exibir_modal_config", False):
        with st.expander("⚙️ Configurações do Aplicativo & Planos de Fundo Múltiplos", expanded=True):
            st.markdown("### 🔤 Aparência das fontes deste aparelho")
            st.caption("Estas preferências ficam salvas neste navegador/aparelho. O administrador configura uma vez; depois o conferente pode entrar com o próprio usuário.")
            _prefs_atuais = carregar_configuracoes_dispositivo(_device_id)
            cfg_cor_fonte = st.color_picker("Cor das fontes", value=_prefs_atuais["fonte_cor"], key="cfg_cor_fonte_device")
            cfg_tamanho_fonte = st.slider("Tamanho das fontes", min_value=12, max_value=24, value=int(_prefs_atuais["fonte_tamanho"]), step=1, key="cfg_tamanho_fonte_device")
            if st.button("💾 Salvar aparência neste aparelho", type="primary", key="btn_salvar_aparencia_device"):
                try:
                    salvar_configuracoes_dispositivo(_device_id, cfg_cor_fonte, cfg_tamanho_fonte)
                    st.success("Aparência salva neste aparelho. Ela continuará ativa após sair do administrador e entrar com o usuário do conferente.")
                    st.rerun()
                except Exception as _save_style_error:
                    st.error(f"Não foi possível salvar a aparência: {_save_style_error}")

            st.markdown("---")
            st.markdown("### 📣 Teste de envio para o Google Chat")
            if st.button("Enviar mensagem de teste ao Google Chat", key="btn_testar_google_chat"):
                _teste_chat_ok = enviar_notificacao_google_chat(
                    f"✅ Teste do HortiControl Supernova realizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}."
                )
                if _teste_chat_ok:
                    st.success("O Google Chat aceitou a mensagem. Confira o espaço configurado.")
                else:
                    st.error("O envio falhou. Abra os Logs do Streamlit Cloud e procure por GOOGLE CHAT para ver o motivo.")

            st.markdown("---")
            st.markdown("### 🔔 Notificações Nativas")
            notif_desktop_toggle = st.toggle(
                "Ativar Notificações na Tela (Desktop / Navegador)", 
                value=st.session_state.get("notif_desktop_toggle", False),
                help="Exibe alertas flutuantes no canto da tela estilo pop-up quando novos romaneios forem cadastrados."
            )
            st.session_state["notif_desktop_toggle"] = notif_desktop_toggle

            if notif_desktop_toggle:
                components.html("""
                <script>
                if ("Notification" in window && Notification.permission !== "granted") {
                    Notification.requestPermission();
                }
                </script>
                """, height=0)

            st.markdown("---")
            st.markdown("### 🖼️ Gerenciamento de Múltiplos Wallpapers e Temas")
            
            conn_w, db_tw = get_db_connection()
            try:
                cur_w = conn_w.cursor()
                cur_w.execute("SELECT id, nome FROM wallpapers ORDER BY id DESC")
                lista_wallpapers_db = cur_w.fetchall()
            except Exception:
                lista_wallpapers_db = []
            finally:
                conn_w.close()

            nomes_wallpapers_db = [w[1] for w in lista_wallpapers_db]

            opcoes_temas_bg = [
                "Logomarca Oficial Supernova",
                "Fundo Branco",
                "Verde Supernova (Escuro)",
                "Azul Corporativo Executivo",
                "Grafite High-Tech",
                "Imagem Personalizada (Upload)"
            ] + [f"Galeria: {w}" for w in nomes_wallpapers_db]

            tema_atual = st.session_state.get("tema_bg_selecionado", "Logomarca Oficial Supernova")
            idx_tema = opcoes_temas_bg.index(tema_atual) if tema_atual in opcoes_temas_bg else 0
            
            sel_tema_bg = st.selectbox(
                "Selecione o Estilo / Papel de Parede do Sistema (Individual)",
                options=opcoes_temas_bg,
                index=idx_tema,
                key="sel_tema_bg_input"
            )
            st.session_state["tema_bg_selecionado"] = sel_tema_bg

            if sel_tema_bg == "Logomarca Oficial Supernova":
                st.session_state["custom_bg_b64"] = b64_padrao_global
            elif sel_tema_bg.startswith("Galeria: "):
                nome_escolhido = sel_tema_bg.replace("Galeria: ", "")
                conn_w2, db_tw2 = get_db_connection()
                try:
                    cur_w2 = conn_w2.cursor()
                    cur_w2.execute("SELECT b64_dados FROM wallpapers WHERE nome = %s" if db_tw2 == "postgres" else "SELECT b64_dados FROM wallpapers WHERE nome = ?", (nome_escolhido,))
                    res_w = cur_w2.fetchone()
                    if res_w:
                        st.session_state["custom_bg_b64"] = res_w[0]
                finally:
                    conn_w2.close()

            elif sel_tema_bg == "Imagem Personalizada (Upload)":
                up_bg_file = st.file_uploader("Enviar Nova Imagem de Fundo (JPG/PNG)", type=["jpg", "jpeg", "png"], key="up_custom_bg_file")
                nome_novo_wp = st.text_input("Nome para salvar este Wallpaper na Galeria (Opcional)", value="")
                if up_bg_file is not None:
                    try:
                        bg_bytes = up_bg_file.getbuffer()
                        b64_new_bg = base64.b64encode(bg_bytes).decode('utf-8')
                        st.session_state["custom_bg_b64"] = b64_new_bg

                        if nome_novo_wp.strip():
                            conn_ins_w, db_tins_w = get_db_connection()
                            cur_iw = conn_ins_w.cursor()
                            try:
                                cur_iw.execute(
                                    "INSERT INTO wallpapers (nome, b64_dados) VALUES (%s, %s)" if db_tins_w == "postgres" else "INSERT INTO wallpapers (nome, b64_dados) VALUES (?, ?)",
                                    (nome_novo_wp.strip(), b64_new_bg)
                                )
                                conn_ins_w.commit()
                                st.cache_data.clear()
                                st.success(f"Wallpaper '{nome_novo_wp}' salvo com sucesso na galeria!")
                            except Exception:
                                conn_ins_w.rollback()
                                st.warning("Já existe um wallpaper com esse nome. A imagem foi aplicada apenas na sessão.")
                            finally:
                                conn_ins_w.close()
                        else:
                            st.success("Imagem de fundo personalizada aplicada com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao processar imagem de fundo: {e}")
            
            col_salv_cfg1, col_salv_cfg2 = st.columns([2, 1])
            with col_salv_cfg1:
                if st.button("💾 Aplicar e Salvar Configurações", type="primary", key="btn_fechar_cfg_painel"):
                    with spinner_supernova("Salvando configurações..."):
                        conn_cfg, db_t_cfg = get_db_connection()
                        try:
                            cur_cfg = conn_cfg.cursor()
                            u_id = int(user_info["id"]) if db_t_cfg == "postgres" else user_info["id"]
                            bg_b64_val = st.session_state.get("custom_bg_b64", "")
                            notif_val = 1 if st.session_state.get("notif_desktop_toggle", False) else 0
                            tema_val = st.session_state.get("tema_bg_selecionado", "Logomarca Oficial Supernova")
                            
                            cur_cfg.execute(
                                "UPDATE usuarios SET tema_bg = %s, notif_desktop = %s, custom_bg_b64 = %s WHERE id = %s" if db_t_cfg == "postgres" else "UPDATE usuarios SET tema_bg = ?, notif_desktop = ?, custom_bg_b64 = ? WHERE id = ?",
                                (tema_val, notif_val, bg_b64_val, u_id)
                            )
                            conn_cfg.commit()
                            st.cache_data.clear()
                            st.session_state["exibir_modal_config"] = False
                            st.success("Configurações salvas permanentemente com sucesso!")
                            st.rerun()
                        except Exception as e:
                            conn_cfg.rollback()
                            st.error(f"Erro ao salvar configurações: {e}")
                        finally:
                            conn_cfg.close()

    if is_conferente:
        opcoes_menu_map = {
            "📋 Romaneio de Recebimento": "Romaneio de Recebimento - Hortifrúti",
            "🔄 Troca por Troca de Avarias": "Troca por Troca de Avarias",
            "🔎 Consultar Trocas": "Consultar Trocas"
        }
    elif is_auxiliar:
        opcoes_menu_map = {
            "📋 Romaneio de Recebimento": "Romaneio de Recebimento - Hortifrúti",
            "🔄 Troca por Troca de Avarias": "Troca por Troca de Avarias",
            "🗂️ Consultar Romaneios": "Consultar Romaneios",
            "🎁 Controle de Bonificação": "Controle de Bonificação",
            "🛒 Cadastros": "Gerenciar Cadastros (Produtos)"
        }
    else:
        opcoes_menu_map = {
            "📋 Romaneio de Recebimento": "Romaneio de Recebimento - Hortifrúti",
            "🔄 Troca por Troca de Avarias": "Troca por Troca de Avarias",
            "🗂️ Consultar Romaneios": "Consultar Romaneios",
            "🎁 Controle de Bonificação": "Controle de Bonificação",
            "📉 Baixa de Avarias": "Controle de Baixa de Avarias",
            "📊 Relatórios & BI": "Relatórios & Gráficos",
            "🛒 Cadastros": "Gerenciar Cadastros (Produtos)",
            "👥 Usuários": "Gerenciar Usuários & Permissões"
        }

    menu_selecionado_label = st.radio(
        "Menu de Navegação Principal",
        list(opcoes_menu_map.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="menu_navegacao_principal_radio"
    )
    menu = opcoes_menu_map[menu_selecionado_label]
    if "ultimo_menu_ativo" not in st.session_state:
        st.session_state["ultimo_menu_ativo"] = menu
    elif st.session_state["ultimo_menu_ativo"] != menu:
        st.session_state["ultimo_menu_ativo"] = menu
        with spinner_supernova(f"Abrindo {menu_selecionado_label}..."):
            pass
    st.markdown("---")
    

    # ---------------------------------------------------------
    # TROCA POR TROCA DE AVARIAS - FORMULÁRIO DIGITAL INDEPENDENTE
    # ---------------------------------------------------------
    def _canvas_assinatura_b64(canvas_obj):
        if canvas_obj is None or getattr(canvas_obj, "image_data", None) is None:
            return ""
        arr = canvas_obj.image_data.astype("uint8")
        # O canvas tem fundo branco; considera assinatura válida se houver pixels escuros.
        if not (arr[:, :, :3] < 235).any():
            return ""
        imagem = Image.fromarray(arr)
        buff = io.BytesIO()
        imagem.save(buff, format="PNG")
        return base64.b64encode(buff.getvalue()).decode("utf-8")

    def _pdf_termo_troca(dados, itens, assinatura_resp_b64, assinatura_forn_b64):
        buff = io.BytesIO()
        doc = SimpleDocTemplate(buff, pagesize=letter, rightMargin=34, leftMargin=34, topMargin=28, bottomMargin=28)
        styles = getSampleStyleSheet()
        story = []
        _logo_pdf_troca = buscar_caminho_logo()
        if _logo_pdf_troca and os.path.exists(_logo_pdf_troca):
            try:
                story.append(RLImage(_logo_pdf_troca, width=85, height=42))
                story.append(Spacer(1, 4))
            except Exception:
                pass
        story += [
            Paragraph("<b>SUPER NOVA CIDADE</b>", styles["Title"]),
            Paragraph("CNPJ: 34.551.382/0002-44", styles["Normal"]),
            Spacer(1, 8),
            Paragraph("<b>TERMO DE FORMALIZAÇÃO DE TROCA POR AVARIA</b>", styles["Heading2"]),
            Spacer(1, 10),
            Paragraph(f"<b>Data da Operação:</b> {dados['data']} &nbsp;&nbsp; <b>Número do Controle:</b> {dados['numero']}", styles["Normal"]),
            Paragraph(f"<b>Setor / Loja:</b> {dados['setor']} &nbsp;&nbsp; <b>Fornecedor:</b> {dados['fornecedor']}", styles["Normal"]),
            Spacer(1, 10),
            Paragraph("Pelo presente instrumento, as partes formalizam a substituição de produtos identificados com avarias, conforme listagem detalhada abaixo:", styles["Normal"]),
            Spacer(1, 8),
            Paragraph("<b>PRODUTOS TROCADOS</b>", styles["Heading3"])
        ]
        tabela_dados = [["CÓDIGO", "DESCRIÇÃO DO PRODUTO", "QUANTIDADE", "UNIDADE"]]
        for it in itens:
            tabela_dados.append([it.get("codigo", "") or "-", it["descricao"], f"{it['quantidade']:g}", it["unidade"]])
        tabela = Table(tabela_dados, colWidths=[90, 260, 85, 70], repeatRows=1)
        tabela.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#E8F0E8")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6)
        ]))
        story += [tabela, Spacer(1, 12), Paragraph("<b>OBSERVAÇÕES</b>", styles["Normal"]),
                  Paragraph((dados.get("observacoes") or "—").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), styles["Normal"]),
                  Spacer(1, 18)]
        def assinatura_img(b64):
            try:
                raw = base64.b64decode(b64)
                im = RLImage(io.BytesIO(raw), width=190, height=65)
                im._restrictSize(190, 65)
                return im
            except Exception:
                return ""
        sig_resp = assinatura_img(assinatura_resp_b64)
        sig_forn = assinatura_img(assinatura_forn_b64)
        assinaturas = Table([
            [sig_forn, sig_resp],
            ["________________________________", "________________________________"],
            ["REPRESENTANTE DO FORNECEDOR", "RESPONSÁVEL PELA AVARIA"]
        ], colWidths=[270, 270], rowHeights=[70, 20, 25])
        assinaturas.setStyle(TableStyle([
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "BOTTOM"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 4)
        ]))
        story += [assinaturas, Spacer(1, 14),
                  Paragraph("Este documento serve como comprovante de movimentação de estoque para fins de conferência e prestação de contas.", styles["Normal"])]
        doc.build(story)
        buff.seek(0)
        return buff.getvalue()

    if menu == "Troca por Troca de Avarias":
        _logo_troca = buscar_caminho_logo()
        _lc, _tc = st.columns([0.12, 3.88], vertical_alignment="center")
        with _lc:
            if _logo_troca and os.path.exists(_logo_troca): st.image(_logo_troca, width=48)
            else: st.markdown("🔄")
        with _tc: st.title("Troca por Troca de Avarias")
        st.caption("Registre a troca e acompanhe o status até a substituição ser concluída.")
        if "troca_itens_digitais" not in st.session_state: st.session_state["troca_itens_digitais"] = []
        if "troca_form_suffix" not in st.session_state: st.session_state["troca_form_suffix"] = 0
        sufixo_troca = st.session_state["troca_form_suffix"]
        data_troca = st.date_input("Data da Operação", value=datetime.now().date(), key=f"troca_data_{sufixo_troca}")
        numero_troca = st.text_input("Número do Controle", value=f"AV-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}", key=f"troca_num_{sufixo_troca}")
        setor_troca = st.text_input("Setor / Loja", value=str(loja_atual_usuario or ""), key=f"troca_setor_{sufixo_troca}")

        _forns_t = carregar_fornecedores_cached()
        _kf = f"troca_forn_sel_{sufixo_troca}"; _kfc = f"troca_forn_cod_{sufixo_troca}"
        def _troca_forn_change():
            _v = st.session_state.get(_kf); st.session_state[_kfc] = str(_v[1] or "") if _v else ""
        _forn_sel = st.selectbox("Fornecedor cadastrado", [None] + list(_forns_t),
            format_func=lambda x: "Selecione o fornecedor..." if x is None else f"{x[0]} | Código do fornecedor: {x[1] or 'Não informado'}",
            key=_kf, on_change=_troca_forn_change)
        if _kfc not in st.session_state: st.session_state[_kfc] = str(_forn_sel[1] or "") if _forn_sel else ""
        _cf1,_cf2=st.columns([2,1])
        with _cf1: st.text_input("Fornecedor selecionado", value=_forn_sel[0] if _forn_sel else "", disabled=True, key=f"troca_forn_show_{sufixo_troca}")
        with _cf2: st.text_input("Código do Fornecedor", key=_kfc, disabled=True)

        st.markdown("### Produtos avariados para troca")
        _prods_t = carregar_produtos_cached()
        _kp=f"troca_prod_sel_{sufixo_troca}"; _kpc=f"troca_prod_cod_{sufixo_troca}"; _kpbar=f"troca_prod_bar_{sufixo_troca}"
        def _troca_prod_change():
            _v=st.session_state.get(_kp); st.session_state[_kpc]=str(_v[0] or "") if _v else ""; st.session_state[_kpbar]=str(_v[1] or "") if _v else ""
        _prod_sel=st.selectbox("Produto cadastrado (código / barras / descrição)", [None]+list(_prods_t),
            format_func=lambda x: "Selecione o produto..." if x is None else f"{x[2]} | Código de barras: {x[1] or 'Não informado'} | Código interno: {x[0] or 'Não informado'}",
            key=_kp,on_change=_troca_prod_change)
        if _kpc not in st.session_state: st.session_state[_kpc]=str(_prod_sel[0] or "") if _prod_sel else ""
        if _kpbar not in st.session_state: st.session_state[_kpbar]=str(_prod_sel[1] or "") if _prod_sel else ""
        _cp1,_cp2=st.columns(2)
        with _cp1: st.text_input("Código do Produto",key=_kpc,disabled=True)
        with _cp2: st.text_input("Código de Barras",key=_kpbar,disabled=True)
        _units=["UN","UNID","CX","KG","GRM","PCT","FD","SC","LT","OUTRA"]
        _unit=str(_prod_sel[3] or "UN").upper() if _prod_sel else "UN"
        if _unit not in _units: _units.append(_unit)
        _q1,_q2=st.columns(2)
        with _q1: _qtd=st.number_input("Quantidade",min_value=0.001,value=1.0,step=1.0,key=f"troca_qtd_{sufixo_troca}")
        with _q2: _un=st.selectbox("Unidade",_units,index=_units.index(_unit),key=f"troca_un_{sufixo_troca}")
        if st.button("➕ Adicionar produto avariado",key=f"troca_add_{sufixo_troca}"):
            if not _prod_sel: st.warning("Selecione um produto cadastrado.")
            else:
                st.session_state["troca_itens_digitais"].append({"codigo":str(_prod_sel[0] or ""),"codigo_barras":str(_prod_sel[1] or ""),"descricao":str(_prod_sel[2]),"quantidade":float(_qtd),"unidade":_un})
                st.rerun()
        if st.session_state["troca_itens_digitais"]:
            st.dataframe(pd.DataFrame([{"Código":x["codigo"] or "—","Produto":x["descricao"],"Quantidade":x["quantidade"],"Unidade":x["unidade"]} for x in st.session_state["troca_itens_digitais"]]),use_container_width=True,hide_index=True)
            _ri=st.selectbox("Produto para remover",range(len(st.session_state["troca_itens_digitais"])),format_func=lambda i:f"{i+1}. {st.session_state['troca_itens_digitais'][i]['descricao']}",key=f"troca_rem_sel_{sufixo_troca}")
            if st.button("🗑️ Remover produto",key=f"troca_rem_{sufixo_troca}"): st.session_state["troca_itens_digitais"].pop(_ri); st.rerun()
        _obs_t=st.text_area("Observações",key=f"troca_obs_{sufixo_troca}")
        st.markdown("### Assinaturas digitais")
        _as1,_as2=st.columns(2)
        with _as1:
            st.write("**Responsável pela avaria / Conferente**")
            _sig_resp=st_canvas(stroke_width=3,stroke_color="#000000",background_color="#FFFFFF",height=120,width=280,drawing_mode="freedraw",return_image_data=True,key=f"troca_sig_resp_{sufixo_troca}")
        with _as2:
            st.write("**Representante do fornecedor**")
            _sig_forn=st_canvas(stroke_width=3,stroke_color="#000000",background_color="#FFFFFF",height=120,width=280,drawing_mode="freedraw",return_image_data=True,key=f"troca_sig_forn_{sufixo_troca}")

        if st.button("💾 Registrar Troca por Troca",type="primary",key=f"troca_salvar_{sufixo_troca}"):
            _sig_r_b64=_canvas_assinatura_b64(_sig_resp); _sig_f_b64=_canvas_assinatura_b64(_sig_forn)
            _forn=_forn_sel[0] if _forn_sel else ""; _cod_f=str(_forn_sel[1] or "") if _forn_sel else ""
            if not numero_troca.strip(): st.error("Informe o número de controle.")
            elif not setor_troca.strip() or not _forn: st.error("Selecione o fornecedor cadastrado e informe o setor/loja.")
            elif not st.session_state["troca_itens_digitais"]: st.error("Adicione pelo menos um produto.")
            elif not _sig_r_b64 or not _sig_f_b64: st.error("As duas assinaturas são obrigatórias.")
            else:
                _dados={"numero":numero_troca.strip(),"data":data_troca.strftime("%d/%m/%Y"),"setor":setor_troca.strip(),"fornecedor":_forn,"codigo_fornecedor":_cod_f,"observacoes":_obs_t}
                _conn_t=None
                try:
                    _conn_t,_db_t=get_db_connection(); _cur_t=_conn_t.cursor()
                    _sql_t="""INSERT INTO troca_avarias (numero_controle,data_operacao,setor_loja,fornecedor,codigo_fornecedor,conferente,observacoes,assinatura_responsavel_b64,assinatura_fornecedor_b64,status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""" if _db_t=="postgres" else """INSERT INTO troca_avarias (numero_controle,data_operacao,setor_loja,fornecedor,codigo_fornecedor,conferente,observacoes,assinatura_responsavel_b64,assinatura_fornecedor_b64,status) VALUES (?,?,?,?,?,?,?,?,?,?)"""
                    _vals=(_dados["numero"],_dados["data"],_dados["setor"],_forn,_cod_f,user_info["nome"],_obs_t,_sig_r_b64,_sig_f_b64,"Troca pendente")
                    _cur_t.execute(_sql_t,_vals); _id_t=_cur_t.fetchone()[0] if _db_t=="postgres" else _cur_t.lastrowid
                    for _it in st.session_state["troca_itens_digitais"]:
                        _sql_i="INSERT INTO troca_avarias_itens (troca_id,codigo_produto,descricao_produto,quantidade,unidade) VALUES (%s,%s,%s,%s,%s)" if _db_t=="postgres" else "INSERT INTO troca_avarias_itens (troca_id,codigo_produto,descricao_produto,quantidade,unidade) VALUES (?,?,?,?,?)"
                        _cur_t.execute(_sql_i,(_id_t,_it["codigo"],_it["descricao"],_it["quantidade"],_it["unidade"]))
                    _conn_t.commit(); st.cache_data.clear()
                    st.session_state["ultimo_pdf_troca_bytes"]=_pdf_termo_troca(_dados,st.session_state["troca_itens_digitais"],_sig_r_b64,_sig_f_b64)
                    st.session_state["ultimo_num_troca"]=_dados["numero"]
                    _itmsg="\n".join([f"• {it['descricao']} | cód. {it['codigo'] or 'N/A'} | {it['quantidade']:g} {it['unidade']}" for it in st.session_state["troca_itens_digitais"]])
                    _msg=("🔄 NOVA TROCA POR AVARIA REGISTRADA\n"+f"Controle: {_dados['numero']}\nData: {_dados['data']}\nSetor/Loja: {_dados['setor']}\nFornecedor: {_forn} (cód. {_cod_f or 'N/A'})\nResponsável: {user_info['nome']}\nStatus: Troca pendente\nItens:\n"+_itmsg)
                    _chat_ok=enviar_notificacao_google_chat(_msg)
                    if st.session_state.get("notif_desktop_toggle",False): emitir_notificacao_desktop_web(titulo=f"🔄 Troca pendente {_dados['numero']}",mensagem=f"Fornecedor: {_forn} | Itens: {len(st.session_state['troca_itens_digitais'])}")
                    st.session_state["troca_itens_digitais"]=[]; st.session_state["troca_form_suffix"]+=1
                    if _chat_ok: st.success(f"Troca {_dados['numero']} registrada e notificada no Google Chat. Status: Troca pendente.")
                    else: st.warning(f"Troca {_dados['numero']} registrada, mas o aviso no Google Chat não foi confirmado. Confira os Logs/Secrets.")
                    st.rerun()
                except Exception as _e_t:
                    try: _conn_t.rollback()
                    except Exception: pass
                    st.error(f"Não foi possível registrar a troca: {_e_t}")
                finally:
                    try:
                        if _conn_t: _conn_t.close()
                    except Exception: pass
        if "ultimo_pdf_troca_bytes" in st.session_state:
            st.success(f"Termo **{st.session_state.get('ultimo_num_troca','')}** pronto para download.")
            st.download_button("📥 Baixar Termo de Troca por Avaria (PDF)",data=st.session_state["ultimo_pdf_troca_bytes"],file_name=f"Termo_Troca_Avaria_{st.session_state.get('ultimo_num_troca','troca')}.pdf",mime="application/pdf",type="primary",key="download_termo_troca")

    if menu == "Consultar Trocas":
        st.title("🔎 Consultar Trocas por Avaria")
        st.caption("Consulte o registro individual e atualize o status quando a troca for concluída.")
        _conn_c,_db_c=get_db_connection()
        try:
            _df_t=pd.read_sql_query("SELECT id,numero_controle,data_operacao,setor_loja,fornecedor,codigo_fornecedor,conferente,observacoes,status FROM troca_avarias ORDER BY id DESC",_conn_c)
        finally: _conn_c.close()
        if _df_t.empty: st.info("Ainda não há trocas registradas.")
        else:
            _df_t["status"]=_df_t["status"].fillna("Troca pendente").replace("","Troca pendente")
            _show_t=_df_t.rename(columns={"numero_controle":"Nº Controle","data_operacao":"Data","setor_loja":"Setor/Loja","fornecedor":"Fornecedor","codigo_fornecedor":"Cód. Fornecedor","conferente":"Responsável","status":"Status"})
            st.dataframe(_show_t[["Nº Controle","Data","Setor/Loja","Fornecedor","Cód. Fornecedor","Responsável","Status"]],use_container_width=True,hide_index=True)
            _opts_t=[(int(r["id"]),f"{r['numero_controle']} | {r['fornecedor']} | {r['data_operacao']} | {r['status']}") for _,r in _df_t.iterrows()]
            _sel_t=st.selectbox("Selecione uma troca",_opts_t,format_func=lambda x:x[1],key="consulta_troca_individual")
            if _sel_t:
                _idc=_sel_t[0]; _rowc=_df_t[_df_t["id"]==_idc].iloc[0]
                st.markdown(f"### Controle {_rowc['numero_controle']}")
                st.write(f"**Fornecedor:** {_rowc['fornecedor']} | **Código:** {_rowc['codigo_fornecedor'] or 'N/A'}")
                st.write(f"**Setor/Loja:** {_rowc['setor_loja']} | **Responsável:** {_rowc['conferente']}")
                st.write(f"**Observações:** {_rowc['observacoes'] or '—'}")
                _conn_i,_=get_db_connection()
                try:
                    _q_i="SELECT codigo_produto,descricao_produto,quantidade,unidade FROM troca_avarias_itens WHERE troca_id = %s ORDER BY id" if _db_c=="postgres" else "SELECT codigo_produto,descricao_produto,quantidade,unidade FROM troca_avarias_itens WHERE troca_id = ? ORDER BY id"
                    _df_i=pd.read_sql_query(_q_i,_conn_i,params=(_idc,))
                finally: _conn_i.close()
                if not _df_i.empty: st.dataframe(_df_i.rename(columns={"codigo_produto":"Código","descricao_produto":"Produto","quantidade":"Quantidade","unidade":"Unidade"}),use_container_width=True,hide_index=True)
                _statusopts=["Troca pendente","Trocado"]; _curstatus=str(_rowc["status"] or "Troca pendente")
                _idxstatus=_statusopts.index(_curstatus) if _curstatus in _statusopts else 0
                _newstatus=st.selectbox("Status",_statusopts,index=_idxstatus,key=f"status_troca_{_idc}")
                if st.button("💾 Salvar status da troca",key=f"salvar_status_troca_{_idc}"):
                    _conn_s,_db_s=get_db_connection()
                    try:
                        _cur_s=_conn_s.cursor(); _cur_s.execute("UPDATE troca_avarias SET status = %s WHERE id = %s" if _db_s=="postgres" else "UPDATE troca_avarias SET status = ? WHERE id = ?",(_newstatus,int(_idc) if _db_s=="postgres" else _idc))
                        _conn_s.commit(); st.cache_data.clear(); st.success("Status atualizado."); st.rerun()
                    except Exception as _e_s:
                        _conn_s.rollback(); st.error(f"Erro ao atualizar status: {_e_s}")
                    finally: _conn_s.close()

    if menu == "Romaneio de Recebimento - Hortifrúti":
        logo_path_header = buscar_caminho_logo()
        col_tit_logo, col_tit_txt = st.columns([0.1, 3.9], vertical_alignment="center")
        with col_tit_logo:
            if logo_path_header and os.path.exists(logo_path_header):
                st.image(logo_path_header, width=45)
            else:
                st.markdown("📋")
        with col_tit_txt:
            st.title("Romaneio de Recebimento - Hortifrúti")

        if "form_key_suffix" not in st.session_state: st.session_state["form_key_suffix"] = 0
        if "item_key_suffix" not in st.session_state: st.session_state["item_key_suffix"] = 0
        k_suffix = st.session_state["form_key_suffix"]
        i_suffix = st.session_state["item_key_suffix"]

        with spinner_supernova("Carregando produtos e fornecedores..."):
            produtos_lista = carregar_produtos_cached()
            fornecedores_lista = carregar_fornecedores_cached()

        prod_dict = {}
        for p in produtos_lista:
            c_prod = p[0] if p[0] and str(p[0]).strip() else "S/Cód"
            c_bar = p[1] if p[1] and str(p[1]).strip() else "S/Barras"
            label = f"{c_prod} | Barras: {c_bar} | {p[2]}"
            prod_dict[label] = (p[2], p[3] if p[3] else "KG")
        prod_nomes_keys = list(prod_dict.keys())

        forn_por_nome = {}
        forn_nomes_keys = []
        for f in fornecedores_lista:
            nome_f = f[0]
            forn_nomes_keys.append(nome_f)
            forn_por_nome[nome_f] = str(f[1]).strip() if f[1] else ""

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
                tipo_operacao = st.selectbox("Tipo de Operação", ["", "Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"], index=0, key=f"tipo_op_{k_suffix}", placeholder="Selecione o tipo...")
            with col2:
                data_rec_val = seletor_data_unificado("Data do Recebimento", f"rec_{k_suffix}")
                data_rec_str = data_rec_val.strftime("%d/%m/%Y") if data_rec_val else ""

                if tipo_operacao in ["Transferência", "Transferência/Bonificação"]:
                    loja_origem = st.selectbox("Loja de Origem (Saiu)", ["", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"], index=0, placeholder="Selecione a origem...", key=f"loja_orig_{k_suffix}")
                    loja_destino = st.selectbox("Loja de Destino (Entrou)", ["", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"], index=0, placeholder="Selecione o destino...", key=f"loja_dest_{k_suffix}")
                    loja = f"{loja_origem} -> {loja_destino}"
                else:
                    loja_origem = ""
                    loja_destino = ""
                    lista_lojas_opc = ["", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
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
                cod_fornecedor = st.text_input("Código do Fornecedor", key=f"in_cod_forn_{k_suffix}", disabled=True)

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
                tel_fornecedor = st.text_input("Telefone de Contato (Opcional)", placeholder="", key=tel_key, on_change=formatar_tel)
            with col_tel2:
                pag_a_vista = st.selectbox("Pagamento à Vista?", ["", "SIM", "NÃO"], index=0, placeholder="Selecione...", key=f"pag_vista_{k_suffix}")
            
            fornecedor = fornecedor_sel
            data_pag_str = ""
            if pag_a_vista == "NÃO":
                data_pag_val = seletor_data_unificado("Data para Pagamento (Livre)", f"pag_{k_suffix}")
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
            qtd_str_input = st.text_input("Qtd / Peso", placeholder="", key=f"qtd_{k_suffix}_{i_suffix}")
        with col_p4:
            val_unit_str_input = st.text_input("Valor Unit. (R$)", placeholder="", key=f"vunit_{k_suffix}_{i_suffix}")
        with col_p5:
            st.write("")
            st.write("")
            if st.button("➕ Add", type="primary", key=f"btn_add_{k_suffix}_{i_suffix}"):
                qtd_input = parse_float_ptbr(qtd_str_input)
                val_unit_val = parse_float_ptbr(val_unit_str_input)
                if not prod_nome_real: st.warning("Selecione um produto antes de adicionar.")
                elif qtd_input <= 0: st.warning("Informe uma quantidade maior que zero.")
                else:
                    v_tot = float(qtd_input * val_unit_val)
                    st.session_state["itens_romaneio"].append({"produto": prod_nome_real, "quantidade": float(qtd_input), "unidade": und_sel, "valor_unitario": float(val_unit_val), "valor_total": float(v_tot)})
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

            total_geral_temp = sum(float(itm['valor_total']) for itm in st.session_state["itens_romaneio"])
            st.markdown(f"### **Total Geral: R$ {fmt_ptbr(total_geral_temp, 2)}**")

            if st.button("🗑️ Limpar Todos os Itens", type="secondary", key=f"btn_del_itens_{k_suffix}"):
                st.session_state["itens_romaneio"] = []
                st.rerun()

        st.subheader("3. Anexo de Foto da Mercadoria / Nota Fiscal")
        fotos_upload = st.file_uploader("Foto da Mercadoria / Nota Fiscal", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True, key=f"fotos_{k_suffix}")

        st.subheader("4. Informações Adicionais / Observações")
        observacoes_romaneio = st.text_area("Observações sobre a carga, qualidade ou divergências", placeholder="", key=f"obs_{k_suffix}")

        st.subheader("5. Assinatura Digital")
        col_ass1, col_ass2 = st.columns(2)
        with col_ass1:
            st.write("**Assinatura do Conferente**")
            canvas_conf = st_canvas(
                stroke_width=3, stroke_color="#000000", background_color="#FFFFFF",
                height=120, width=280, drawing_mode="freedraw", return_image_data=True, key=f"canv_conf_{k_suffix}"
            )
        with col_ass2:
            st.write("**Assinatura do Entregador / Fornecedor**")
            canvas_ent = st_canvas(
                stroke_width=3, stroke_color="#000000", background_color="#FFFFFF",
                height=120, width=280, drawing_mode="freedraw", return_image_data=True, key=f"canv_ent_{k_suffix}"
            )

        if st.button("✅ Salvar Romaneio", type="primary", key=f"btn_salvar_{k_suffix}"):
            num_rom_final = st.session_state[f"num_rom_auto_{k_suffix}"]
            forn_final = fornecedor if isinstance(fornecedor, str) else ""
            cod_forn_val = st.session_state[f"val_cod_forn_{k_suffix}"]
            if not forn_final.strip(): st.error("Selecione o fornecedor na lista cadastrada.")
            elif not data_rec_str: st.error("Informe uma Data do Recebimento válida no formato DD/MM/AAAA!")
            elif tipo_operacao in ["Transferência", "Transferência/Bonificação"] and (not loja_origem or not loja_destino): st.error("Selecione a Loja de Origem e a Loja de Destino!")
            elif tipo_operacao not in ["Transferência", "Transferência/Bonificação"] and not loja: st.error("Selecione a loja!")
            elif pag_a_vista == "NÃO" and not data_pag_str: st.error("A Data para Pagamento é obrigatória para compras a prazo!")
            elif not st.session_state["itens_romaneio"]: st.error("Adicione itens ao romaneio.")
            else:
                with spinner_supernova("Salvando romaneio no Supernova..."):
                    conn, db_type = get_db_connection()
                    try:
                        if not os.path.exists("uploads"): os.makedirs("uploads")
                        
                        path_ass_conf = ""
                        b64_conf_str = ""
                        if canvas_conf.image_data is not None:
                            img_c = Image.fromarray(canvas_conf.image_data.astype("uint8"))
                            path_ass_conf = os.path.join("uploads", f"ass_conf_{num_rom_final}.png")
                            img_c.save(path_ass_conf)
                            
                            buffered_c = io.BytesIO()
                            img_c.save(buffered_c, format="PNG")
                            b64_conf_str = base64.b64encode(buffered_c.getvalue()).decode("utf-8")

                        path_ass_ent = ""
                        b64_ent_str = ""
                        if canvas_ent.image_data is not None:
                            img_e = Image.fromarray(canvas_ent.image_data.astype("uint8"))
                            path_ass_ent = os.path.join("uploads", f"ass_ent_{num_rom_final}.png")
                            img_e.save(path_ass_ent)
                            
                            buffered_e = io.BytesIO()
                            img_e.save(buffered_e, format="PNG")
                            b64_ent_str = base64.b64encode(buffered_e.getvalue()).decode("utf-8")

                        caminho_foto_salva = ""
                        b64_foto_str = ""
                        if fotos_upload:
                            for f in fotos_upload:
                                path_f = os.path.join("uploads", f.name)
                                f_bytes = f.getbuffer()
                                with open(path_f, "wb") as f_out: f_out.write(f_bytes)
                                caminho_foto_salva = path_f
                                b64_foto_str = base64.b64encode(f_bytes).decode("utf-8")

                        cursor = conn.cursor()
                        if db_type == "postgres":
                            cursor.execute("""
                            INSERT INTO romaneios (numero_romaneio, loja, loja_origem, loja_destino,
                            data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista,
                            data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador, status_nota, tipo_operacao,
                            observacoes, foto_b64, ass_conf_b64, ass_ent_b64)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                            """, (num_rom_final, loja, loja_origem, loja_destino, data_rec_str, forn_final, cod_forn_val, tel_fornecedor, user_info["nome"], pag_a_vista, data_pag_str, caminho_foto_salva, path_ass_conf, path_ass_ent, 'Pendente', tipo_operacao, observacoes_romaneio, b64_foto_str, b64_conf_str, b64_ent_str))
                            romaneio_id = cursor.fetchone()[0]
                        else:
                            cursor.execute("""
                            INSERT INTO romaneios (numero_romaneio, loja, loja_origem, loja_destino,
                            data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista,
                            data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador, status_nota, tipo_operacao,
                            observacoes, foto_b64, ass_conf_b64, ass_ent_b64)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (num_rom_final, loja, loja_origem, loja_destino, data_rec_str, forn_final, cod_forn_val, tel_fornecedor, user_info["nome"], pag_a_vista, data_pag_str, caminho_foto_salva, path_ass_conf, path_ass_ent, 'Pendente', tipo_operacao, observacoes_romaneio, b64_foto_str, b64_conf_str, b64_ent_str))
                            romaneio_id = cursor.lastrowid

                        itens_salvos_pdf = []
                        for itm in st.session_state["itens_romaneio"]:
                            q_val = float(itm["quantidade"])
                            v_u_val = float(itm["valor_unitario"])
                            v_t_val = float(itm["valor_total"])
                            r_id_val = int(romaneio_id) if db_type == "postgres" else romaneio_id
                            
                            if db_type == "postgres":
                                cursor.execute("INSERT INTO romaneio_itens (romaneio_id, produto, quantidade, unidade, valor_unitario, valor_total) VALUES (%s, %s, %s, %s, %s, %s)", (r_id_val, str(itm["produto"]), q_val, str(itm["unidade"]), v_u_val, v_t_val))
                            else:
                                cursor.execute("INSERT INTO romaneio_itens (romaneio_id, produto, quantidade, unidade, valor_unitario, valor_total) VALUES (?, ?, ?, ?, ?, ?)", (r_id_val, str(itm["produto"]), q_val, str(itm["unidade"]), v_u_val, v_t_val))
                            itens_salvos_pdf.append([None, itm["produto"], q_val, itm["unidade"], v_u_val, v_t_val])

                        conn.commit()
                        st.cache_data.clear()

                        romaneio_dict_atual = {
                            "numero_romaneio": num_rom_final, "data_recebimento": data_rec_str,
                            "fornecedor": forn_final, "codigo_fornecedor": cod_forn_val,
                            "telefone_fornecedor": tel_fornecedor, "loja": loja,
                            "loja_origem": loja_origem, "loja_destino": loja_destino,
                            "conferente": user_info["nome"], "pagamento_a_vista": pag_a_vista,
                            "data_pagamento": data_pag_str, "tipo_operacao": tipo_operacao,
                            "observacoes": observacoes_romaneio,
                            "ass_conf_b64": b64_conf_str, "ass_ent_b64": b64_ent_str
                        }

                        disparar_notificacao_sistema(romaneio_dict_atual, st.session_state["itens_romaneio"])

                        itens_romaneio_chat = st.session_state["itens_romaneio"]
                        primeiro_item_chat = itens_romaneio_chat[0].get("produto", "Diversos") if itens_romaneio_chat else "Diversos"
                        mensagem_romaneio_chat = (
                            "📋 *NOVO ROMANEIO CADASTRADO*\n"
                            f"Número: {num_rom_final}\n"
                            f"Operação: {tipo_operacao}\n"
                            f"Loja: {loja or loja_destino or 'Não informada'}\n"
                            f"Fornecedor: {forn_final}\n"
                            f"Conferente: {user_info['nome']}\n"
                            f"Data de recebimento: {data_rec_str}\n"
                            f"Itens: {len(itens_romaneio_chat)}\n"
                            f"Primeiro item: {primeiro_item_chat}"
                        )
                        chat_romaneio_enviado = enviar_notificacao_google_chat(mensagem_romaneio_chat)

                        pdf_buffer_novo = gerar_pdf_romaneio(romaneio_dict_atual, itens_salvos_pdf)
                        st.session_state["ultimo_pdf_bytes"] = pdf_buffer_novo.getvalue()
                        st.session_state["ultimo_num_romaneio"] = num_rom_final
                        st.session_state["itens_romaneio"] = []
                        st.session_state["form_key_suffix"] += 1
                        st.session_state["item_key_suffix"] = 0
                        status_chat_rom = " Google Chat notificado." if chat_romaneio_enviado else " (Google Chat não notificado; confira os Secrets)."
                        st.success(f"Romaneio {num_rom_final} gerado e salvo com sucesso!" + status_chat_rom)
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Erro ao salvar romaneio: {e}")
                    finally:
                        conn.close()

        if "ultimo_pdf_bytes" in st.session_state and "ultimo_num_romaneio" in st.session_state:
            st.markdown("---")
            st.success(f"📄 Romaneio **{st.session_state['ultimo_num_romaneio']}** pronto para download!")
            st.download_button(
                label=f"📥 Descarregar PDF - {st.session_state['ultimo_num_romaneio']}",
                data=st.session_state["ultimo_pdf_bytes"],
                file_name=f"{st.session_state['ultimo_num_romaneio']}.pdf",
                mime="application/pdf", type="primary"
            )

    elif menu == "Consultar Romaneios":
        st.title("🗂️ Consultar & Gerenciar Romaneios de Recebimento")
        with spinner_supernova("Carregando romaneios..."):
            df_rom, df_all_itens = _carregar_romaneios_e_totais_cached()
            df_rom = df_rom.copy()
            df_all_itens = df_all_itens.copy()

        if df_rom.empty:
            st.info("Nenhum romaneio registrado no sistema.")
        else:
            if not df_all_itens.empty:
                df_rom = df_rom.merge(df_all_itens, left_on="id", right_on="romaneio_id", how="left")
                df_rom["valor_total_rom"] = df_rom["valor_total_rom"].fillna(0.0)
            else:
                df_rom["valor_total_rom"] = 0.0

            lista_lojas_sistema = ["LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
            if not is_admin and loja_atual_usuario in lista_lojas_sistema:
                lojas_para_exibir = [loja_atual_usuario]
            else:
                lojas_para_exibir = lista_lojas_sistema

            nomes_abas_lojas = []
            for l in lojas_para_exibir:
                df_l_check = df_rom[
                    df_rom["loja"].str.contains(l, case=False, na=False) |
                    df_rom.get("loja_destino", pd.Series(dtype=str)).str.contains(l, case=False, na=False)
                ]
                tem_pendente_loja = not df_l_check[df_l_check["status_nota"].str.strip().str.lower() == "pendente"].empty
                prefixo_sino = "🔔 " if tem_pendente_loja else ""
                nomes_abas_lojas.append(f"{prefixo_sino}🏪 {l}")

            tabs_lojas = st.tabs(nomes_abas_lojas)
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
                        tipos_operacao_map = {
                            "📋 TODOS OS TIPOS": "TODOS OS TIPOS",
                            "🛒 Compra": "Compra",
                            "🎁 Bonificação": "Bonificação",
                            "🚚 Transferência": "Transferência",
                            "📦 Transferência/Bonificação": "Transferência/Bonificação",
                            "🔄 Troca por Troca": "Troca por Troca"
                        }
                        
                        nomes_abas_tipos = []
                        for label_tp, tipo_val in tipos_operacao_map.items():
                            if tipo_val == "TODOS OS TIPOS":
                                df_tp_check = df_loja_atual.copy()
                            else:
                                if tipo_val == "Transferência":
                                    df_tp_check = df_loja_atual[df_loja_atual["tipo_operacao"].str.strip().str.lower() == "transferência"]
                                elif tipo_val == "Bonificação":
                                    df_tp_check = df_loja_atual[df_loja_atual["tipo_operacao"].str.strip().str.lower() == "bonificação"]
                                else:
                                    df_tp_check = df_loja_atual[df_loja_atual["tipo_operacao"].str.contains(tipo_val, case=False, na=False)]
                            
                            tem_pendente_tp = not df_tp_check[df_tp_check["status_nota"].str.strip().str.lower() == "pendente"].empty
                            sino_tp = "🔔 " if tem_pendente_tp else ""
                            nomes_abas_tipos.append(f"{sino_tp}{label_tp}")

                        subtabs_tipo = st.tabs(nomes_abas_tipos)
                        for idx_t, (label_aba, tipo_op_val) in enumerate(tipos_operacao_map.items()):
                            with subtabs_tipo[idx_t]:
                                if tipo_op_val == "TODOS OS TIPOS":
                                    df_tipo_atual = df_loja_atual.copy()
                                else:
                                    if tipo_op_val == "Transferência":
                                        df_tipo_atual = df_loja_atual[df_loja_atual["tipo_operacao"].str.strip().str.lower() == "transferência"].copy()
                                    elif tipo_op_val == "Bonificação":
                                        df_tipo_atual = df_loja_atual[df_loja_atual["tipo_operacao"].str.strip().str.lower() == "bonificação"].copy()
                                    else:
                                        df_tipo_atual = df_loja_atual[df_loja_atual["tipo_operacao"].str.contains(tipo_op_val, case=False, na=False)].copy()

                                if df_tipo_atual.empty:
                                    st.markdown(f"<p style='color: #9aa0a6; font-style: italic; padding: 10px;'>Nenhum romaneio encontrado na categoria '{tipo_op_val}'.</p>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"**Total de registros em '{tipo_op_val}':** {len(df_tipo_atual)}")
                                    df_planilha = df_tipo_atual.copy()
                                    df_planilha["Anexo"] = df_planilha.apply(lambda r: "📎 Disponível" if ((r.get("caminho_foto") and os.path.exists(str(r["caminho_foto"]))) or (r.get("foto_b64") and len(str(r["foto_b64"])) > 10)) else "Sem Anexo", axis=1)
                                    df_planilha["Valor Total"] = df_planilha["valor_total_rom"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")

                                    df_planilha_show = df_planilha.rename(columns={
                                        "numero_romaneio": "N° Romaneio", "tipo_operacao": "Tipo Operação",
                                        "loja": "Loja", "data_recebimento": "Data Recebimento",
                                        "fornecedor": "Fornecedor", "conferente": "Conferente", "status_nota": "Status Atual"
                                    })
                                    cols_view = df_planilha_show[["N° Romaneio", "Tipo Operação", "Loja", "Data Recebimento", "Fornecedor", "Conferente", "Valor Total", "Status Atual", "Anexo"]]
                                    cols_view.index = range(1, len(cols_view) + 1)
                                    st.dataframe(cols_view, use_container_width=True, height=280)

                                    st.markdown("---")
                                    st.subheader("⚙️ Gerenciador de Romaneio: Visualizar Anexo, Atualizar Status e Editar (Admin)")
                                    opcoes_rom_gerenciar = [(row["id"], f"Romaneio {row['numero_romaneio']} | Status: {row.get('status_nota','Pendente')} | Fornecedor: {row['fornecedor'] or 'N/A'} | Data: {row['data_recebimento']}") for _, row in df_tipo_atual.iterrows()]
                                    chave_tab = f"{loja_nome}_{tipo_op_val}".replace(" ", "_").replace("/", "_")
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
                                            if cam_foto or row_sel.get('foto_b64'):
                                                if st.button("🖼️ Visualizar Nota / Anexo", key=f"btn_ver_anx_grid_{chv_elem}", type="primary"):
                                                    with spinner_supernova("Carregando anexo..."):
                                                        conn_b64, _ = get_db_connection()
                                                        try:
                                                            cur_b64 = conn_b64.cursor()
                                                            cur_b64.execute("SELECT foto_b64 FROM romaneios WHERE id = %s" if HAS_POSTGRES else "SELECT foto_b64 FROM romaneios WHERE id = ?", (id_rom_sel,))
                                                            res_b64 = cur_b64.fetchone()
                                                        finally:
                                                            conn_b64.close()
                                                        exibir_foto_modal(cam_foto, res_b64[0] if res_b64 else row_sel.get('foto_b64'))
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
                                                    with spinner_supernova("Atualizando status..."):
                                                        conn_st, db_t_st = get_db_connection()
                                                        try:
                                                            cur_st = conn_st.cursor()
                                                            r_id_st = int(id_rom_sel) if db_t_st == "postgres" else id_rom_sel
                                                            cur_st.execute(
                                                                "UPDATE romaneios SET status_nota = %s WHERE id = %s" if db_t_st == "postgres" else "UPDATE romaneios SET status_nota = ? WHERE id = ?",
                                                                (str(novo_st_sel), r_id_st)
                                                            )
                                                            conn_st.commit()
                                                            st.cache_data.clear()
                                                            st.success("Status atualizado com sucesso!")
                                                            st.rerun()
                                                        except Exception as e:
                                                            conn_st.rollback()
                                                            st.error(f"Erro ao salvar status: {e}")
                                                        finally:
                                                            conn_st.close()

                                        with col_pdf_act:
                                            st.markdown("**📄 Relatório PDF / Exclusão**")
                                            conn_i, db_t_i = get_db_connection()
                                            try:
                                                r_id_i = int(id_rom_sel) if db_t_i == "postgres" else id_rom_sel
                                                df_itens_r = pd.read_sql_query("SELECT produto, quantidade, unidade, valor_unitario, valor_total FROM romaneio_itens WHERE romaneio_id = %s" if db_t_i == "postgres" else "SELECT produto, quantidade, unidade, valor_unitario, valor_total FROM romaneio_itens WHERE romaneio_id = ?", conn_i, params=(r_id_i,))
                                            finally:
                                                conn_i.close()

                                            pdf_buf = gerar_pdf_romaneio(row_sel.to_dict(), [(None, r['produto'], r['quantidade'], r['unidade'], r['valor_unitario'], r['valor_total']) for _, r in df_itens_r.iterrows()])
                                            col_dl_p, col_del_p = st.columns([2, 1])
                                            with col_dl_p:
                                                st.download_button(
                                                    label="📥 Baixar PDF", data=pdf_buf,
                                                    file_name=f"{row_sel['numero_romaneio']}.pdf", mime="application/pdf", key=f"btn_pdf_grid_{chv_elem}"
                                                )
                                            with col_del_p:
                                                if is_admin:
                                                    if st.button("🗑️", key=f"btn_del_grid_{chv_elem}", help="Excluir Romaneio", type="secondary"):
                                                        with spinner_supernova("Excluindo romaneio..."):
                                                            conn_del, db_t_del = get_db_connection()
                                                            try:
                                                                cur_del = conn_del.cursor()
                                                                r_id_del = int(id_rom_sel) if db_t_del == "postgres" else id_rom_sel
                                                                cur_del.execute("DELETE FROM romaneio_itens WHERE romaneio_id = %s" if db_t_del == "postgres" else "DELETE FROM romaneio_itens WHERE romaneio_id = ?", (r_id_del,))
                                                                cur_del.execute("DELETE FROM romaneios WHERE id = %s" if db_t_del == "postgres" else "DELETE FROM romaneios WHERE id = ?", (r_id_del,))
                                                                conn_del.commit()
                                                                st.cache_data.clear()
                                                                st.success("Excluído com sucesso!")
                                                                st.rerun()
                                                            except Exception as e:
                                                                conn_del.rollback()
                                                                st.error(f"Erro: {e}")
                                                            finally:
                                                                conn_del.close()

                                        with st.expander(f"📋 Ver Itens Cadastrados no Romaneio {row_sel['numero_romaneio']}", expanded=False):
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
                                                        with spinner_supernova("Salvando alterações do romaneio..."):
                                                            conn_urom, db_turom = get_db_connection()
                                                            try:
                                                                path_foto_ed = row_sel.get("caminho_foto", "")
                                                                b64_foto_ed = row_sel.get("foto_b64", "")
                                                                if novo_anexo_rom_up:
                                                                    if not os.path.exists("uploads"): os.makedirs("uploads")
                                                                    path_foto_ed = os.path.join("uploads", f"ROM_EDIT_{row_sel['numero_romaneio']}_{novo_anexo_rom_up.name}")
                                                                    b_up_rom = novo_anexo_rom_up.getbuffer()
                                                                    with open(path_foto_ed, "wb") as f_out: f_out.write(b_up_rom)
                                                                    b64_foto_ed = base64.b64encode(b_up_rom).decode("utf-8")

                                                                cur_urom = conn_urom.cursor()
                                                                r_id_urom = int(id_rom_sel) if db_turom == "postgres" else id_rom_sel
                                                                if novo_anexo_rom_up:
                                                                    cur_urom.execute(
                                                                        "UPDATE romaneios SET fornecedor = %s, codigo_fornecedor = %s, telefone_fornecedor = %s, tipo_operacao = %s, pagamento_a_vista = %s, data_pagamento = %s, observacoes = %s, caminho_foto = %s, foto_b64 = %s WHERE id = %s" if db_turom == "postgres" else "UPDATE romaneios SET fornecedor = ?, codigo_fornecedor = ?, telefone_fornecedor = ?, tipo_operacao = ?, pagamento_a_vista = ?, data_pagamento = ?, observacoes = ?, caminho_foto = ?, foto_b64 = ? WHERE id = ?",
                                                                        (novo_forn_ed.strip(), novo_cod_forn_ed.strip(), novo_tel_ed.strip(), novo_tipo_op_ed, novo_pag_v_ed, nova_dt_pag_ed.strip(), novas_obs_ed.strip(), path_foto_ed, b64_foto_ed, r_id_urom)
                                                                    )
                                                                else:
                                                                    cur_urom.execute(
                                                                        "UPDATE romaneios SET fornecedor = %s, codigo_fornecedor = %s, telefone_fornecedor = %s, tipo_operacao = %s, pagamento_a_vista = %s, data_pagamento = %s, observacoes = %s WHERE id = %s" if db_turom == "postgres" else "UPDATE romaneios SET fornecedor = ?, codigo_fornecedor = ?, telefone_fornecedor = ?, tipo_operacao = ?, pagamento_a_vista = ?, data_pagamento = ?, observacoes = ? WHERE id = ?",
                                                                        (novo_forn_ed.strip(), novo_cod_forn_ed.strip(), novo_tel_ed.strip(), novo_tipo_op_ed, novo_pag_v_ed, nova_dt_pag_ed.strip(), novas_obs_ed.strip(), r_id_urom)
                                                                    )
                                                                conn_urom.commit()
                                                                st.cache_data.clear()
                                                                st.success("Romaneio atualizado com sucesso pelo administrador!")
                                                                st.rerun()
                                                            except Exception as e:
                                                                conn_urom.rollback()
                                                                st.error(f"Erro ao editar romaneio: {e}")
                                                            finally:
                                                                conn_urom.close()

    elif menu == "Controle de Bonificação":
        with spinner_supernova("Carregando bonificações..."):
            st.title("🎁 Controle de Bonificação Hortifrúti")
            prods_cad = carregar_produtos_cached()

        lista_opcoes_prod = []
        for p in prods_cad:
            c_prod = p[0] if p[0] and str(p[0]).strip() else "S/Cód"
            c_bar = p[1] if p[1] and str(p[1]).strip() else "S/Barras"
            lista_opcoes_prod.append(f"{c_prod} | Barras: {c_bar} | {p[2]}")

        if "bonf_form_suf" not in st.session_state:
            st.session_state["bonf_form_suf"] = 0
        bf_suf = st.session_state["bonf_form_suf"]

        with st.expander("➕ Cadastrar Nova Bonificação", expanded=False):
            with st.form(f"form_cad_bonificacao_{bf_suf}", clear_on_submit=False):
                col_b1, col_b2, col_b3 = st.columns([1.5, 1.5, 1.5])
                with col_b1:
                    num_nota_bonf = st.text_input("N° Nota Fiscal", placeholder="", key=f"bonf_nota_{bf_suf}")
                    lista_lojas_cad_b = ["", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                    idx_l_cad_b = lista_lojas_cad_b.index(loja_atual_usuario) if loja_atual_usuario in lista_lojas_cad_b else 0
                    loja_bonf = st.selectbox("Loja", lista_lojas_cad_b, index=idx_l_cad_b, placeholder="Selecione a loja...", key=f"loja_bonf_sel_{bf_suf}")
                with col_b2:
                    valor_bonf_str = st.text_input("Valor da Bonificação (R$)", placeholder="", key=f"bonf_val_{bf_suf}")
                    tipo_bonf_sel = st.selectbox("Tipo de Bonificação", ["", "Bonificação", "Transferência de Bonificação"], index=0, placeholder="Selecione o tipo...", key=f"tipo_bonf_input_sel_{bf_suf}")
                with col_b3:
                    prod_bonf = st.selectbox("Produto Hortifrúti", options=[""] + lista_opcoes_prod, index=0, placeholder="Selecione o produto...", key=f"bonf_prod_{bf_suf}")
                    anexo_bonf = st.file_uploader("Anexar NF (PDF ou Imagem)", type=["pdf", "png", "jpg", "jpeg"], key=f"bonf_anx_{bf_suf}")

                col_dt1, col_dt2, col_dt3 = st.columns([1.5, 1.5, 1.5])
                with col_dt1: status_bonf = st.selectbox("STATUS", ["", "Disponível", "Parcialmente Utilizada", "Totalmente Utilizada"], index=0, placeholder="Selecione o status...", key=f"bonf_st_{bf_suf}")
                with col_dt2: 
                    data_entrada_manual = seletor_data_unificado("Data de Entrada (Livre)", f"cad_bonf_dt_{bf_suf}", dentro_de_form=True)
                with col_dt3:
                    hora_auto = datetime.now(ZoneInfo("America/Manaus")).strftime('%H:%M:%S')
                    st.text_input("Hora de Entrada", value=hora_auto, disabled=True, key=f"bonf_hr_{bf_suf}")

                dt_entrada_str = f"{data_entrada_manual.strftime('%d/%m/%Y')} {hora_auto}" if data_entrada_manual else ""
                if st.form_submit_button("✅ Salvar Bonificação", type="primary"):
                    if not num_nota_bonf.strip() or not loja_bonf or not prod_bonf or not status_bonf or not tipo_bonf_sel:
                        st.error("Preencha todos os campos obrigatórios, incluindo o Tipo de Bonificação.")
                    else:
                        with spinner_supernova("Salvando bonificação e blindando anexo..."):
                            valor_bonf_val = parse_float_ptbr(valor_bonf_str)

                            path_anexo_bonf = ""
                            b64_anexo_str = ""
                            if anexo_bonf:
                                if not os.path.exists("uploads"):
                                    os.makedirs("uploads")
                                path_anexo_bonf = os.path.join("uploads", f"NF_{num_nota_bonf}_{anexo_bonf.name}")
                                anexo_bytes = anexo_bonf.getbuffer()
                                with open(path_anexo_bonf, "wb") as f_out: 
                                    f_out.write(anexo_bytes)
                                b64_anexo_str = base64.b64encode(anexo_bytes).decode("utf-8")

                            conn_b, db_tb = get_db_connection()
                            try:
                                cursor_b = conn_b.cursor()
                                cursor_b.execute(
                                    "INSERT INTO bonificacoes (numero_nota, loja, data_entrada, valor_bonificacao, status, produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)" if db_tb == "postgres" else "INSERT INTO bonificacoes (numero_nota, loja, data_entrada, valor_bonificacao, status, produto_hortifruti, caminho_anexo, tipo_bonificacao, anexo_b64) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    (num_nota_bonf.strip(), loja_bonf, dt_entrada_str, float(valor_bonf_val), status_bonf, prod_bonf, path_anexo_bonf, tipo_bonf_sel, b64_anexo_str)
                                )
                                conn_b.commit()
                                st.cache_data.clear()
                                mensagem_bonificacao_chat = (
                                    "🎁 *NOVA BONIFICAÇÃO / TRANSFERÊNCIA CADASTRADA*\n"
                                    f"Nota fiscal: {num_nota_bonf.strip()}\n"
                                    f"Tipo: {tipo_bonf_sel}\n"
                                    f"Loja: {loja_bonf}\n"
                                    f"Produto: {prod_bonf}\n"
                                    f"Valor: R$ {valor_bonf_val:,.2f}\n"
                                    f"Status: {status_bonf}\n"
                                    f"Data de entrada: {dt_entrada_str}"
                                )
                                chat_bonificacao_enviado = enviar_notificacao_google_chat(mensagem_bonificacao_chat)
                                status_chat_bonf = " Google Chat notificado." if chat_bonificacao_enviado else " (Google Chat não notificado; confira os Secrets)."
                                st.session_state["bonf_form_suf"] += 1
                                st.success("Bonificação salva com sucesso com anexo persistido!" + status_chat_bonf)
                                st.rerun()
                            except Exception as e:
                                conn_b.rollback()
                                st.error(f"Erro: {e}")
                            finally:
                                conn_b.close()

        st.markdown("---")
        st.subheader("📋 Registros de Bonificação e Consulta de Notas")
        lista_lojas_filtro_bonf = ["TODAS", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
        idx_filtro_bonf = 0
        if not is_admin and loja_atual_usuario in lista_lojas_filtro_bonf:
            idx_filtro_bonf = lista_lojas_filtro_bonf.index(loja_atual_usuario)

        with st.expander("🔍 Filtros de Busca", expanded=True):
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1: f_nota = st.text_input("Filtrar por N° Nota", value="", placeholder="N° da nota...", key="f_nota_bonf")
            with f_col2: f_loja = st.selectbox("Filtrar por Loja", options=lista_lojas_filtro_bonf, index=idx_filtro_bonf, placeholder="Selecione...", key="f_loja_bonf")
            with f_col3: f_status = st.selectbox("Filtrar por Status", ["TODOS", "Disponível", "Parcialmente Utilizada", "Totalmente Utilizada"], placeholder="Selecione...", key="f_status_bonf")
            with f_col4: f_prod = st.text_input("Filtrar por Produto", value="", placeholder="Produto...", key="f_prod_bonf")

        with spinner_supernova("Carregando registros de bonificação..."):
            df_bonf = _carregar_bonificacoes_cached().copy()

        if not df_bonf.empty:
            if f_nota.strip(): df_bonf = df_bonf[df_bonf["numero_nota"].str.contains(f_nota.strip(), case=False, na=False)]
            if f_loja != "TODAS": df_bonf = df_bonf[df_bonf["loja"] == f_loja]
            if f_status != "TODOS": df_bonf = df_bonf[df_bonf["status"] == f_status]
            if f_prod.strip(): df_bonf = df_bonf[df_bonf["produto_hortifruti"].str.contains(f_prod.strip(), case=False, na=False)]

            subtabs_tipo_bonf = st.tabs(["🎁 Bonificações", "🔀 Transferências de Bonificação"])
            with subtabs_tipo_bonf[0]:
                df_bonf_puro = df_bonf[df_bonf.get("tipo_bonificacao", "Bonificação").str.strip().str.lower() == "bonificação"].copy()
                st.markdown(f"**Registros de Bonificação Pura:** {len(df_bonf_puro)}")
                if not df_bonf_puro.empty:
                    df_bp_show = df_bonf_puro.copy()
                    df_bp_show["Valor (R$)"] = df_bp_show["valor_bonificacao"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                    df_bp_show["Anexo"] = df_bp_show.apply(lambda r: "📎 Disponível" if ((r.get("caminho_anexo") and os.path.exists(r["caminho_anexo"])) or (r.get("anexo_b64") and len(str(r["anexo_b64"])) > 10)) else "Sem Anexo", axis=1)
                    df_bp_show = df_bp_show.rename(columns={"numero_nota": "N° Nota", "loja": "Loja", "data_entrada": "Data e Hora", "status": "Status", "produto_hortifruti": "Produto Hortifrúti"})
                    cols_ex_bp = df_bp_show[["N° Nota", "Loja", "Data e Hora", "Valor (R$)", "Status", "Produto Hortifrúti", "Anexo"]]
                    cols_ex_bp.index = range(1, len(cols_ex_bp) + 1)
                    st.dataframe(cols_ex_bp, use_container_width=True, height=280)
                else:
                    st.info("Nenhuma bonificação pura encontrada.")

            with subtabs_tipo_bonf[1]:
                df_bonf_transf = df_bonf[df_bonf.get("tipo_bonificacao", "").str.strip().str.lower() == "transferência de bonificação"].copy()
                st.markdown(f"**Registros de Transferência de Bonificação:** {len(df_bonf_transf)}")
                if not df_bonf_transf.empty:
                    df_bt_show = df_bonf_transf.copy()
                    df_bt_show["Valor (R$)"] = df_bt_show["valor_bonificacao"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                    df_bt_show["Anexo"] = df_bt_show.apply(lambda r: "📎 Disponível" if ((r.get("caminho_anexo") and os.path.exists(r["caminho_anexo"])) or (r.get("anexo_b64") and len(str(r["anexo_b64"])) > 10)) else "Sem Anexo", axis=1)
                    df_bt_show = df_bt_show.rename(columns={"numero_nota": "N° Nota", "loja": "Loja", "data_entrada": "Data e Hora", "status": "Status", "produto_hortifruti": "Produto Hortifrúti"})
                    cols_ex_bt = df_bt_show[["N° Nota", "Loja", "Data e Hora", "Valor (R$)", "Status", "Produto Hortifrúti", "Anexo"]]
                    cols_ex_bt.index = range(1, len(cols_ex_bt) + 1)
                    st.dataframe(cols_ex_bt, use_container_width=True, height=280)
                else:
                    st.info("Nenhuma transferência de bonificação encontrada.")

            tot_bonf_val = float(df_bonf["valor_bonificacao"].sum())
            tot_disp_val = float(df_bonf[df_bonf["status"] == "Disponível"]["valor_bonificacao"].sum())
            tot_parc_val = float(df_bonf[df_bonf["status"] == "Parcialmente Utilizada"]["valor_bonificacao"].sum())
            tot_util_val = float(df_bonf[df_bonf["status"] == "Totalmente Utilizada"]["valor_bonificacao"].sum())

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
                mime="application/pdf", type="primary", key="btn_download_pdf_bonf"
            )
            st.markdown("")

            st.markdown("---")
            st.subheader("⚙️ Abertura de Anexo, Edição & Exclusão de Registro")
            opcoes_notas_editar = [(row["id"], f"Nota N° {row['numero_nota']} - {row['loja']} | Status: {row['status']} ({row['data_entrada']})") for _, row in df_bonf.iterrows()]
            col_ed1, col_ed2 = st.columns(2)
            with col_ed1:
                nota_selecionada_edicao = st.selectbox("Selecione o Registro para Gerenciar / Abrir Anexo", options=opcoes_notas_editar, format_func=lambda x: x[1], key="sel_registro_bonf_gerenciar")
            with col_ed2:
                st.write("")
                st.write("")
                if opcoes_notas_editar:
                    id_reg_atual = nota_selecionada_edicao[0]
                    reg_obj_atual = df_bonf[df_bonf["id"] == id_reg_atual].iloc[0]
                    caminho_nota_alvo = reg_obj_atual.get("caminho_anexo", "")
                    if caminho_nota_alvo or reg_obj_atual.get("anexo_b64"):
                        if st.button("🖼️ Abrir Anexo / Nota Fiscal", type="primary", key="btn_abrir_anexo_direto_tabela"):
                            with spinner_supernova("Carregando arquivo anexado..."):
                                conn_b64, _ = get_db_connection()
                                try:
                                    cur_b64 = conn_b64.cursor()
                                    cur_b64.execute("SELECT anexo_b64 FROM bonificacoes WHERE id = %s" if HAS_POSTGRES else "SELECT anexo_b64 FROM bonificacoes WHERE id = ?", (id_reg_atual,))
                                    res_b64 = cur_b64.fetchone()
                                finally:
                                    conn_b64.close()
                                exibir_foto_modal(caminho_nota_alvo, res_b64[0] if res_b64 else reg_obj_atual.get("anexo_b64"))
                    else:
                        st.warning("Este registo não possui ficheiro de nota anexado.")

            if opcoes_notas_editar:
                with st.form("form_edicao_direta_bonificacao"):
                    st.markdown(f"**Editando Nota N° {reg_obj_atual['numero_nota']} ({reg_obj_atual['loja']})**")
                    data_atual_str = str(reg_obj_atual["data_entrada"]).split(" ")[0] if reg_obj_atual["data_entrada"] else ""
                    try: dt_obj_default = datetime.strptime(data_atual_str, "%d/%m/%Y").date()
                    except Exception: dt_obj_default = datetime.now(ZoneInfo("America/Manaus")).date()

                    col_e1, col_e2, col_e3, col_e4, col_e5 = st.columns(5)
                    with col_e1: novo_val_nota_str = st.text_input("Valor (R$)", value=str(reg_obj_atual["valor_bonificacao"]).replace(".", ","))
                    with col_e2:
                        lista_lojas_alt = ["LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                        idx_loja_alt = lista_lojas_alt.index(reg_obj_atual["loja"]) if reg_obj_atual["loja"] in lista_lojas_alt else 0
                        nova_loja_nota = st.selectbox("Loja", lista_lojas_alt, index=idx_loja_alt)
                    with col_e3: 
                        nova_data_input = seletor_data_unificado("Data de Entrada (Livre)", "edit_bonf_dt", dentro_de_form=True)
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
                        with spinner_supernova("Salvando alterações..."):
                            conn_up_dir, db_t_upd = get_db_connection()
                            try:
                                val_f_edit = parse_float_ptbr(novo_val_nota_str) if novo_val_nota_str else float(reg_obj_atual["valor_bonificacao"])
                                hora_antiga = "00:00:00"
                                if len(str(reg_obj_atual["data_entrada"]).split(" ")) > 1:
                                    hora_antiga = str(reg_obj_atual["data_entrada"]).split(" ")[1]
                                nova_data_str = f"{nova_data_input.strftime('%d/%m/%Y')} {hora_antiga}"

                                path_novo_arq = reg_obj_atual["caminho_anexo"]
                                b64_novo_arq = reg_obj_atual.get("anexo_b64", "")
                                if novo_anexo_up:
                                    if not os.path.exists("uploads"): os.makedirs("uploads")
                                    path_novo_arq = os.path.join("uploads", f"NF_EDIT_{reg_obj_atual['numero_nota']}_{novo_anexo_up.name}")
                                    bytes_up = novo_anexo_up.getbuffer()
                                    with open(path_novo_arq, "wb") as f_out: f_out.write(bytes_up)
                                    b64_novo_arq = base64.b64encode(bytes_up).decode("utf-8")

                                cursor_upd = conn_up_dir.cursor()
                                reg_id_b = int(id_reg_atual) if db_t_upd == "postgres" else id_reg_atual
                                if novo_anexo_up:
                                    cursor_upd.execute(
                                        "UPDATE bonificacoes SET valor_bonificacao = %s, loja = %s, data_entrada = %s, status = %s, produto_hortifruti = %s, caminho_anexo = %s, anexo_b64 = %s WHERE id = %s" if db_t_upd == "postgres" else "UPDATE bonificacoes SET valor_bonificacao = ?, loja = ?, data_entrada = ?, status = ?, produto_hortifruti = ?, caminho_anexo = ?, anexo_b64 = ? WHERE id = ?",
                                        (val_f_edit, nova_loja_nota, nova_data_str, novo_st_nota, novo_prod_nota, path_novo_arq, b64_novo_arq, reg_id_b)
                                    )
                                else:
                                    cursor_upd.execute(
                                        "UPDATE bonificacoes SET valor_bonificacao = %s, loja = %s, data_entrada = %s, status = %s, produto_hortifruti = %s WHERE id = %s" if db_t_upd == "postgres" else "UPDATE bonificacoes SET valor_bonificacao = ?, loja = ?, data_entrada = ?, status = ?, produto_hortifruti = ? WHERE id = ?",
                                        (val_f_edit, nova_loja_nota, nova_data_str, novo_st_nota, novo_prod_nota, reg_id_b)
                                    )
                                conn_up_dir.commit()
                                st.cache_data.clear()
                                st.success("Registo atualizado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                conn_up_dir.rollback()
                                st.error(f"Erro ao atualizar: {e}")
                            finally:
                                conn_up_dir.close()

                    if excluir_bonf_btn:
                        with spinner_supernova("Excluindo bonificação..."):
                            conn_del_b, db_td_b = get_db_connection()
                            try:
                                cursor_db = conn_del_b.cursor()
                                cursor_db.execute(
                                    "DELETE FROM bonificacoes WHERE id = %s" if db_td_b == "postgres" else "DELETE FROM bonificacoes WHERE id = ?",
                                    (int(id_reg_atual) if db_td_b == "postgres" else id_reg_atual,)
                                )
                                conn_del_b.commit()
                                st.cache_data.clear()
                                st.success("Bonificação excluída com sucesso!")
                                st.rerun()
                            except Exception as e:
                                conn_del_b.rollback()
                                st.error(f"Erro ao excluir: {e}")
                            finally:
                                conn_del_b.close()
        else:
            st.info("Nenhuma bonificação encontrada.")

    elif menu == "Controle de Baixa de Avarias":
        with spinner_supernova("Carregando baixas de avarias..."):
            st.title("📉 Registro de Baixas das Avarias")
        loja_ativa_sessao = user_info.get("loja_atual", "LOJA 02 NOVA CIDADE")
        if "baixa_form_suffix" not in st.session_state:
            st.session_state["baixa_form_suffix"] = 0
        bx_suf = st.session_state["baixa_form_suffix"]

        conn_bx_chk, db_tbx_chk = get_db_connection()
        try:
            df_baixar_hist = pd.read_sql_query("SELECT nf_b_entrada, ref_bon_transferen, valor_total_avaria FROM baixas_avarias", conn_bx_chk)
        finally:
            conn_bx_chk.close()

        total_baixado_por_nota = {}
        notas_transf_ja_utilizadas = set()
        if not df_baixar_hist.empty:
            totais_por_nf = df_baixar_hist.groupby("nf_b_entrada")["valor_total_avaria"].sum()
            for nf_e, val_bx in totais_por_nf.items():
                total_baixado_por_nota[str(nf_e).strip()] = float(val_bx)
            
            for _, r_bx in df_baixar_hist.iterrows():
                ref_transf_usada = str(r_bx["ref_bon_transferen"]).strip()
                if ref_transf_usada:
                    notas_transf_ja_utilizadas.add(ref_transf_usada)

        conn_b_all, db_tb_all = get_db_connection()
        try:
            df_todas_bonf = pd.read_sql_query("SELECT id, numero_nota, valor_bonificacao, status, loja, produto_hortifruti, tipo_bonificacao FROM bonificacoes ORDER BY id DESC", conn_b_all)
            if not df_todas_bonf.empty:
                cur_st_up = conn_b_all.cursor()
                for _, r_b in df_todas_bonf.iterrows():
                    num_nf_b = str(r_b["numero_nota"]).strip()
                    tipo_b_reg = str(r_b.get("tipo_bonificacao", "Bonificação")).strip().lower()
                    val_orig_b = float(r_b["valor_bonificacao"])
                    
                    if "transferência" in tipo_b_reg:
                        if num_nf_b in notas_transf_ja_utilizadas:
                            novo_st_auto = "Totalmente Utilizada"
                        else:
                            novo_st_auto = "Disponível"
                    else:
                        baixado_b = total_baixado_por_nota.get(num_nf_b, 0.0)
                        saldo_b = max(0.0, val_orig_b - baixado_b)
                        if saldo_b <= 0:
                            novo_st_auto = "Totalmente Utilizada"
                        elif baixado_b > 0:
                            novo_st_auto = "Parcialmente Utilizada"
                        else:
                            novo_st_auto = "Disponível"
                            
                    if r_b["status"] != novo_st_auto:
                        r_b_id = int(r_b["id"]) if db_tb_all == "postgres" else r_b["id"]
                        cur_st_up.execute(
                            "UPDATE bonificacoes SET status = %s WHERE id = %s" if db_tb_all == "postgres" else "UPDATE bonificacoes SET status = ? WHERE id = ?",
                            (novo_st_auto, r_b_id)
                        )
                conn_b_all.commit()
                st.cache_data.clear()
        except Exception:
            conn_b_all.rollback()
        finally:
            conn_b_all.close()

        dict_valor_orig_por_nf = {}
        if not df_todas_bonf.empty:
            for _, r_b in df_todas_bonf.iterrows():
                dict_valor_orig_por_nf[str(r_b["numero_nota"]).strip()] = float(r_b["valor_bonificacao"])

        notas_com_saldo_ativa = []
        notas_transf_ativa = []
        saldo_geral_somado_ativa = 0.0

        if not df_todas_bonf.empty:
            for _, r_bonf in df_todas_bonf.iterrows():
                num_nf_ent = str(r_bonf["numero_nota"]).strip()
                val_original = float(r_bonf["valor_bonificacao"])
                tipo_b_reg = str(r_bonf.get("tipo_bonificacao", "Bonificação"))
                loja_reg = str(r_bonf.get("loja", ""))
                
                item_dict = {
                    "nf_entrada": num_nf_ent,
                    "loja": loja_reg,
                    "produto": r_bonf.get("produto_hortifruti", "N/A"),
                    "valor_original": val_original
                }
                
                if "Transferência" in tipo_b_reg:
                    if num_nf_ent not in notas_transf_ja_utilizadas:
                        item_dict["saldo_restante"] = val_original
                        notas_transf_ativa.append(item_dict)
                else:
                    ja_baixado = total_baixado_por_nota.get(num_nf_ent, 0.0)
                    saldo_restante_nota = max(0.0, val_original - ja_baixado)
                    
                    if saldo_restante_nota > 0:
                        termo_loja = loja_ativa_sessao.split("-")[0].strip().upper()
                        if is_admin or termo_loja in loja_reg.upper():
                            saldo_geral_somado_ativa += saldo_restante_nota
                            item_dict["saldo_restante"] = saldo_restante_nota
                            notas_com_saldo_ativa.append(item_dict)

        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; background: rgba(30, 35, 42, 0.9); padding: 12px 18px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.15); margin-bottom: 15px;">
            <span style="font-size: 20px;">💳</span>
            <span style="color: #FFFFFF; font-weight: 700; font-size: 15px;">Saldo Total Disponível ({loja_ativa_sessao}): R$ {fmt_ptbr(saldo_geral_somado_ativa, 2)}</span>
        </div>
        """, unsafe_allow_html=True)

        if notas_com_saldo_ativa:
            with st.expander(f"📌 Notas de Bonificação com Saldo Disponível ({loja_ativa_sessao})", expanded=True):
                df_ns_show = pd.DataFrame(notas_com_saldo_ativa)
                df_ns_show["Valor Original (R$)"] = df_ns_show["valor_original"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_ns_show["Saldo Disponível (R$)"] = df_ns_show["saldo_restante"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_ns_show = df_ns_show.rename(columns={"nf_entrada": "N° Nota de Entrada", "produto": "Produto Hortifrúti"})
                st.dataframe(df_ns_show[["N° Nota de Entrada", "Produto Hortifrúti", "Valor Original (R$)", "Saldo Disponível (R$)"]], use_container_width=True, hide_index=True, height=180)

        if notas_transf_ativa:
            with st.expander("🔀 Planilha Separada: Notas de Transferência de Bonificação para Outras Lojas (Uso Único / Rastreio)", expanded=True):
                df_tr_show = pd.DataFrame(notas_transf_ativa)
                df_tr_show["Valor Original (R$)"] = df_tr_show["valor_original"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_tr_show["Saldo Disponível (R$)"] = df_tr_show["valor_original"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_tr_show = df_tr_show.rename(columns={"nf_entrada": "N° Nota de Transferência", "loja": "Loja Origem", "produto": "Produto Hortifrúti"})
                st.dataframe(df_tr_show[["N° Nota de Transferência", "Loja Origem", "Produto Hortifrúti", "Valor Original (R$)", "Saldo Disponível (R$)"]], use_container_width=True, hide_index=True, height=180)

        prods_cad_v = carregar_produtos_cached()
        lista_opcoes_prod_v = []
        for p in prods_cad_v:
            c_prod = p[0] if p[0] and str(p[0]).strip() else "S/Cód"
            c_bar = p[1] if p[1] and str(p[1]).strip() else "S/Barras"
            lista_opcoes_prod_v.append(f"{c_prod} | Barras: {c_bar} | {p[2]}")

        with st.expander("➕ Registrar Nova Baixa de Avaria", expanded=False):
            with st.form(f"form_registro_baixa_modelo_{bx_suf}", clear_on_submit=False):
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    lista_lojas_reg = ["LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                    idx_l_ativa = lista_lojas_reg.index(loja_ativa_sessao) if loja_ativa_sessao in lista_lojas_reg else 0
                    lojas_baixa_sel = st.selectbox("LOJAS", options=lista_lojas_reg, index=idx_l_ativa, key=f"bx_loja_{bx_suf}")
                    
                    opcoes_transf_ref = [item["nf_entrada"] for item in notas_transf_ativa] if notas_transf_ativa else []
                    opcoes_transf_ref_com_manual = ["-- Digitar Manualmente / Outra --"] + opcoes_transf_ref
                    
                    escolha_ref_transf = st.selectbox("Ref. Bon. transferen (Selecionar)", options=opcoes_transf_ref_com_manual, key=f"bx_ref_transf_sel_{bx_suf}")
                    
                    if escolha_ref_transf == "-- Digitar Manualmente / Outra --":
                        ref_bon_transf = st.text_input("Digite o N° da Nota de Transferência Manualmente", value="", key=f"bx_ref_transf_manual_{bx_suf}")
                    else:
                        ref_bon_transf = escolha_ref_transf
                with col_m2:
                    opcoes_nf_entrada = [item["nf_entrada"] for item in notas_com_saldo_ativa if not any(t["nf_entrada"] == item["nf_entrada"] for t in notas_transf_ativa)] if notas_com_saldo_ativa else ["Nenhuma Nota Disponível"]
                    nf_b_entrada_sel = st.selectbox("NF de B. ENTRADA", options=opcoes_nf_entrada, key=f"bx_nf_ent_{bx_suf}")
                    prod_hort_sel = st.selectbox("Produto Hortifrúti", options=[""] + lista_opcoes_prod_v, index=0, key=f"bx_prod_{bx_suf}")
                with col_m3:
                    qtd_kg_cx_str = st.text_input("Qtd (kg/cx)", value="", placeholder="0,000", key=f"bx_qtd_{bx_suf}")
                    valor_total_avaria_str = st.text_input("Valor Total Avaria (R$)", value="", placeholder="0,00", key=f"bx_val_{bx_suf}")
                    nf_baixa_file = st.file_uploader("NF da baixa (Anexo)", type=["pdf", "png", "jpg", "jpeg"], key=f"bx_file_{bx_suf}")

                col_dm1, col_dm2 = st.columns(2)
                with col_dm1: 
                    data_baixa_man = seletor_data_unificado("Data da Baixa (Livre)", f"bx_dt_{bx_suf}", dentro_de_form=True)
                with col_dm2:
                    hora_baixa_aut = datetime.now(ZoneInfo("America/Manaus")).strftime('%H:%M:%S')
                    st.text_input("Hora da Baixa", value=hora_baixa_aut, disabled=True, key=f"bx_hr_{bx_suf}")

                data_hora_baixa_str = f"{data_baixa_man.strftime('%d/%m/%Y')} {hora_baixa_aut}" if data_baixa_man else ""
                btn_enviar_baixa = st.form_submit_button("✅ Registrar Baixa", type="primary")

                if btn_enviar_baixa:
                    if not lojas_baixa_sel or not ref_bon_transf or ref_bon_transf == "-- Digitar Manualmente / Outra --" or nf_b_entrada_sel == "Nenhuma Nota Disponível" or not prod_hort_sel:
                        st.error("Preencha todos os campos obrigatórios (incluindo o número da nota de transferência).")
                    else:
                        with spinner_supernova("Registrando baixa de avaria e blindando anexo..."):
                            qtd_val_f = parse_float_ptbr(qtd_kg_cx_str)
                            val_avaria_f = parse_float_ptbr(valor_total_avaria_str)

                            todas_as_notas_com_saldo = notas_com_saldo_ativa + notas_transf_ativa
                            nota_selecionada_dict = next((item for item in todas_as_notas_com_saldo if item["nf_entrada"] == nf_b_entrada_sel), None)
                            if not nota_selecionada_dict:
                                st.error("Nota de entrada inválida.")
                            elif round(val_avaria_f, 2) > round(nota_selecionada_dict["saldo_restante"], 2):
                                st.error("❌ O valor da avaria ultrapassa o saldo restante da nota!")
                            else:
                                path_nf_baixa = ""
                                b64_nf_baixa = ""
                                if nf_baixa_file:
                                    if not os.path.exists("uploads"): os.makedirs("uploads")
                                    path_nf_baixa = os.path.join("uploads", f"NF_BAIXA_{ref_bon_transf}_{nf_baixa_file.name}")
                                    bytes_baixa = nf_baixa_file.getbuffer()
                                    with open(path_nf_baixa, "wb") as f_out: f_out.write(bytes_baixa)
                                    b64_nf_baixa = base64.b64encode(bytes_baixa).decode("utf-8")

                                saldo_disponivel_da_nota_referenciada = float(nota_selecionada_dict["saldo_restante"])
                                novo_saldo_restante_nota = float(saldo_disponivel_da_nota_referenciada - val_avaria_f)
                                conn_ins, db_tins = get_db_connection()
                                try:
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
                                            lojas_baixa_sel, data_hora_baixa_str, str(ref_bon_transf).strip(),
                                            path_nf_baixa, nf_b_entrada_sel, prod_hort_sel, float(qtd_val_f), float(val_avaria_f),
                                            float(novo_saldo_restante_nota), float(saldo_disponivel_da_nota_referenciada), b64_nf_baixa
                                        )
                                    )
                                    
                                    if novo_saldo_restante_nota <= 0:
                                        st_auto_l2 = "Totalmente Utilizada"
                                    else:
                                        st_auto_l2 = "Parcialmente Utilizada"

                                    cursor_ins.execute(
                                        "UPDATE bonificacoes SET status = %s WHERE TRIM(numero_nota) = TRIM(%s)" if db_tins == "postgres" else "UPDATE bonificacoes SET status = ? WHERE TRIM(numero_nota) = TRIM(?)",
                                        (st_auto_l2, str(nf_b_entrada_sel).strip())
                                    )

                                    cursor_ins.execute(
                                        "UPDATE bonificacoes SET status = 'Totalmente Utilizada' WHERE TRIM(numero_nota) = TRIM(%s) AND LOWER(tipo_bonificacao) LIKE '%%transferência%%'" if db_tins == "postgres" else "UPDATE bonificacoes SET status = 'Totalmente Utilizada' WHERE TRIM(numero_nota) = TRIM(?) AND LOWER(tipo_bonificacao) LIKE '%transferência%'",
                                        (str(ref_bon_transf).strip(),)
                                    )

                                    conn_ins.commit()
                                    st.cache_data.clear()
                                    mensagem_baixa_chat = (
                                        "📉 *NOVA BAIXA DE AVARIA REGISTRADA*\n"
                                        f"Loja: {lojas_baixa_sel}\n"
                                        f"Data: {data_hora_baixa_str}\n"
                                        f"Referência de bonificação/transferência: {str(ref_bon_transf).strip()}\n"
                                        f"NF de entrada: {nf_b_entrada_sel}\n"
                                        f"Produto: {prod_hort_sel}\n"
                                        f"Quantidade: {qtd_val_f:,.3f} kg/cx\n"
                                        f"Valor da avaria: R$ {val_avaria_f:,.2f}\n"
                                        f"Saldo restante da nota: R$ {novo_saldo_restante_nota:,.2f}"
                                    )
                                    _baixa_chat_ok = enviar_notificacao_google_chat(mensagem_baixa_chat)
                                    st.session_state["baixa_form_suffix"] += 1
                                    _status_baixa_chat = " Aviso enviado ao Google Chat." if _baixa_chat_ok else " Atenção: aviso não enviado ao Google Chat; consulte os Logs."
                                    st.success("Baixa registrada com sucesso e saldo atualizado!" + _status_baixa_chat)
                                    st.rerun()
                                except Exception as e:
                                    conn_ins.rollback()
                                    st.error(f"Erro: {e}")
                                finally:
                                    conn_ins.close()

        st.markdown("---")
        st.subheader("📊 Planilha de Registro de Baixas das Avarias")
        lista_lojas_filtro_bx = ["TODAS", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
        idx_filtro_bx = 0
        if not is_admin and loja_atual_usuario in lista_lojas_filtro_bx:
            idx_filtro_bx = lista_lojas_filtro_bx.index(loja_atual_usuario)

        with st.expander("🔍 Filtros da Planilha de Baixas", expanded=True):
            fb1, fb2, fb3 = st.columns(3)
            with fb1: f_loja_bx = st.selectbox("Filtrar por Loja", options=lista_lojas_filtro_bx, index=idx_filtro_bx, placeholder="Selecione...")
            with fb2: f_ref_bx = st.text_input("Filtrar por Ref. Bon.", value="", placeholder="Referência...")
            with fb3: f_prod_bx = st.text_input("Filtrar por Produto", value="", placeholder="Produto...")

        with spinner_supernova("Carregando tabela de baixas..."):
            df_bx_table = _carregar_baixas_avarias_cached().copy()

        if not df_bx_table.empty:
            if f_loja_bx != "TODAS": df_bx_table = df_bx_table[df_bx_table["loja_baixa"] == f_loja_bx]
            if f_ref_bx.strip(): df_bx_table = df_bx_table[df_bx_table["ref_bon_transferen"].str.contains(f_ref_bx.strip(), case=False, na=False)]
            if f_prod_bx.strip(): df_bx_table = df_bx_table[df_bx_table["produto_hortifruti"].str.contains(f_prod_bx.strip(), case=False, na=False)]

            if not df_bx_table.empty:
                df_display_plan = df_bx_table.copy()
                total_utilizado_por_nf = total_baixado_por_nota
                
                saldo_atual_por_nf, utilizado_total_por_nf = {}, {}
                for nf_ent_key, val_orig in dict_valor_orig_por_nf.items():
                    v_bx_total = total_utilizado_por_nf.get(str(nf_ent_key).strip(), 0.0)
                    utilizado_total_por_nf[str(nf_ent_key).strip()] = v_bx_total
                    saldo_atual_por_nf[str(nf_ent_key).strip()] = max(0.0, float(val_orig) - v_bx_total)

                saldo_calculado_list, utilizado_calculado_list = [], []
                for _, row_bx in df_display_plan.iterrows():
                    nf_ent_item = str(row_bx["nf_b_entrada"]).strip()
                    v_utilizado = utilizado_total_por_nf.get(nf_ent_item, float(row_bx["valor_total_avaria"]))
                    utilizado_calculado_list.append(v_utilizado)
                    v_saldo_atual_nota = saldo_atual_por_nf.get(nf_ent_item, float(row_bx["saldo_restante_nota"]))
                    saldo_calculado_list.append(v_saldo_atual_nota)

                df_display_plan["saldo_restante_calculado"] = saldo_calculado_list
                df_display_plan["saldo_total_utilizado"] = utilizado_calculado_list

                pdf_bytes_bx = gerar_pdf_baixas(df_display_plan)
                st.download_button(
                    label="📥 Descarregar Planilha de Baixas de Avarias em PDF",
                    data=pdf_bytes_bx,
                    file_name=f"Registro_Baixas_Avarias_HortiControl_{datetime.now(ZoneInfo('America/Manaus')).strftime('%Y%m%d')}.pdf",
                    mime="application/pdf", type="primary", key="btn_download_pdf_planilha_baixas"
                )
                st.markdown("")

                df_tabela_exibicao = df_display_plan.copy()
                df_tabela_exibicao["Anexo"] = df_tabela_exibicao.apply(lambda r: "📎 Disponível" if ((r.get("nf_baixa") and os.path.exists(str(r["nf_baixa"]))) or (r.get("nf_baixa_b64") and len(str(r["nf_baixa_b64"])) > 10)) else "Sem Anexo", axis=1)
                df_tabela_exibicao["Saldo"] = df_tabela_exibicao["saldo_restante_calculado"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_tabela_exibicao["Saldo Total Utilizado"] = df_tabela_exibicao["saldo_total_utilizado"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_tabela_exibicao["Valor Total Avaria (R$)"] = df_tabela_exibicao["valor_total_avaria"].apply(lambda x: f"R$ {fmt_ptbr(x, 2)}")
                df_tabela_exibicao["Qtd (kg/cx)"] = df_tabela_exibicao["quantidade_kg_cx"].apply(lambda x: fmt_ptbr(x, 3))
                
                df_tabela_final = df_tabela_exibicao.rename(columns={
                    "loja_baixa": "LOJAS", "data_baixa": "Data Baixa", "ref_bon_transferen": "Ref. Bon.",
                    "nf_b_entrada": "NF de B. ENTRADA", "produto_hortifruti": "Produto Hortifrúti",
                })

                cols_para_mostrar = ["LOJAS", "Data Baixa", "Ref. Bon.", "Anexo", "NF de B. ENTRADA", "Produto Hortifrúti", "Qtd (kg/cx)", "Valor Total Avaria (R$)", "Saldo", "Saldo Total Utilizado"]

                st.markdown("**Clique em qualquer linha da planilha abaixo para abrir instantaneamente o anexo correspondente:**")
                evento_selecao = st.dataframe(
                    df_tabela_final[cols_para_mostrar], 
                    use_container_width=True, hide_index=True, height=320,
                    on_select="rerun", selection_mode="single-row"
                )

                linhas_selecionadas = evento_selecao.get("selection", {}).get("rows", [])
                if linhas_selecionadas:
                    idx_selecionado = linhas_selecionadas[0]
                    reg_clicado = df_display_plan.iloc[idx_selecionado]
                    caminho_anexo_clicado = reg_clicado.get("nf_baixa", "")
                    
                    if caminho_anexo_clicado or reg_clicado.get("nf_baixa_b64"):
                        with spinner_supernova("Carregando anexo..."):
                            conn_b64_l, _ = get_db_connection()
                            try:
                                cur_b64_l = conn_b64_l.cursor()
                                cur_b64_l.execute("SELECT nf_baixa_b64 FROM baixas_avarias WHERE id = %s" if HAS_POSTGRES else "SELECT nf_baixa_b64 FROM baixas_avarias WHERE id = ?", (int(reg_clicado['id']),))
                                res_b64_l = cur_b64_l.fetchone()
                            finally:
                                conn_b64_l.close()
                            exibir_foto_modal(caminho_anexo_clicado, res_b64_l[0] if res_b64_l else reg_clicado.get("nf_baixa_b64"))

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
                                lista_lojas_eb = ["LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"]
                                idx_l_eb = lista_lojas_eb.index(reg_bx_atual["loja_baixa"]) if reg_bx_atual["loja_baixa"] in lista_lojas_eb else 0
                                nova_loja_bx = st.selectbox("Loja da Baixa", lista_lojas_eb, index=idx_l_eb)
                                notas_disponiveis_edicao = [item["nf_entrada"] for item in notas_com_saldo_ativa]
                                if reg_bx_atual["nf_b_entrada"] not in notas_disponiveis_edicao:
                                    notas_disponiveis_edicao.insert(0, reg_bx_atual["nf_b_entrada"])
                                idx_nf_atual = notas_disponiveis_edicao.index(reg_bx_atual["nf_b_entrada"]) if reg_bx_atual["nf_b_entrada"] in notas_disponiveis_edicao else 0
                                nova_nf_b_entrada = st.selectbox("NF de B. ENTRADA", options=notas_disponiveis_edicao, index=idx_nf_atual)
                            with col_eb2:
                                opcoes_transf_ref_ed = [item["nf_entrada"] for item in notas_transf_ativa] if notas_transf_ativa else [reg_bx_atual["ref_bon_transferen"]]
                                if reg_bx_atual["ref_bon_transferen"] not in opcoes_transf_ref_ed:
                                    opcoes_transf_ref_ed.insert(0, reg_bx_atual["ref_bon_transferen"])
                                idx_ref_atual = opcoes_transf_ref_ed.index(reg_bx_atual["ref_bon_transferen"]) if reg_bx_atual["ref_bon_transferen"] in opcoes_transf_ref_ed else 0
                                novo_ref_bx = st.selectbox("Ref. Bon. transferen", options=opcoes_transf_ref_ed, index=idx_ref_atual)
                                
                                novo_prod_bx = st.text_input("Produto Hortifrúti", value=reg_bx_atual["produto_hortifruti"])
                            with col_eb3:
                                novo_qtd_bx_str = st.text_input("Qtd (kg/cx)", value=str(reg_bx_atual["quantidade_kg_cx"]).replace(".", ","))
                                novo_val_bx_str = st.text_input("Valor Total Avaria (R$)", value=str(reg_bx_atual["valor_total_avaria"]).replace(".", ","))

                            novo_anexo_bx_up = st.file_uploader("Substituir NF da Baixa (Opcional)", type=["pdf", "png", "jpg", "jpeg"])
                            col_bnt_bx1, col_bnt_bx2 = st.columns(2)
                            with col_bnt_bx1: salvar_alt_bx = st.form_submit_button("💾 Salvar Alterações da Baixa", type="primary")
                            with col_bnt_bx2: excluir_bx_btn = st.form_submit_button("🗑️ Excluir Registo de Baixa", type="secondary")

                            if salvar_alt_bx:
                                with spinner_supernova("Atualizando baixa..."):
                                    conn_up_bx, db_t_upbx = get_db_connection()
                                    try:
                                        q_f_ed = parse_float_ptbr(novo_qtd_bx_str) if novo_qtd_bx_str else float(reg_bx_atual["quantidade_kg_cx"])
                                        v_f_ed = parse_float_ptbr(novo_val_bx_str) if novo_val_bx_str else float(reg_bx_atual["valor_total_avaria"])
                                        
                                        path_nf_bx_ed = reg_bx_atual.get("nf_baixa", "")
                                        b64_nf_bx_ed = reg_bx_atual.get("nf_baixa_b64", "")
                                        if novo_anexo_bx_up:
                                            if not os.path.exists("uploads"): os.makedirs("uploads")
                                            path_nf_bx_ed = os.path.join("uploads", f"NF_BAIXA_EDIT_{novo_ref_bx}_{novo_anexo_bx_up.name}")
                                            bytes_bx_up = novo_anexo_bx_up.getbuffer()
                                            with open(path_nf_bx_ed, "wb") as f_out: f_out.write(bytes_bx_up)
                                            b64_nf_bx_ed = base64.b64encode(bytes_bx_up).decode("utf-8")

                                        todas_as_notas_com_saldo = notas_com_saldo_ativa + notas_transf_ativa
                                        nota_edit_dict = next((item for item in todas_as_notas_com_saldo if item["nf_entrada"] == nova_nf_b_entrada), None)
                                        saldo_disp_edit = float(nota_edit_dict["saldo_restante"]) if nota_edit_dict else float(reg_bx_atual["saldo_total_disponivel"])
                                        novo_saldo_restante_ed = float(saldo_disp_edit - v_f_ed)

                                        cur_upbx = conn_up_bx.cursor()
                                        reg_id_bx = int(id_bx_atual) if db_t_upbx == "postgres" else id_bx_atual
                                        if novo_anexo_bx_up:
                                            cur_upbx.execute(
                                                "UPDATE baixas_avarias SET loja_baixa = %s, ref_bon_transferen = %s, nf_b_entrada = %s, produto_hortifruti = %s, quantidade_kg_cx = %s, valor_total_avaria = %s, saldo_restante_nota = %s, saldo_total_disponivel = %s, nf_baixa = %s, nf_baixa_b64 = %s WHERE id = %s" if db_t_upbx == "postgres" else "UPDATE baixas_avarias SET loja_baixa = ?, ref_bon_transferen = ?, nf_b_entrada = ?, produto_hortifruti = ?, quantidade_kg_cx = ?, valor_total_avaria = ?, saldo_restante_nota = ?, saldo_total_disponivel = ?, nf_baixa = ?, nf_baixa_b64 = ? WHERE id = ?",
                                                (str(nova_loja_bx), str(novo_ref_bx).strip(), str(nova_nf_b_entrada), str(novo_prod_bx), float(q_f_ed), float(v_f_ed), float(novo_saldo_restante_ed), float(saldo_disp_edit), str(path_nf_bx_ed), b64_nf_bx_ed, reg_id_bx)
                                            )
                                        else:
                                            cur_upbx.execute(
                                                "UPDATE baixas_avarias SET loja_baixa = %s, ref_bon_transferen = %s, nf_b_entrada = %s, produto_hortifruti = %s, quantidade_kg_cx = %s, valor_total_avaria = %s, saldo_restante_nota = %s, saldo_total_disponivel = %s WHERE id = %s" if db_t_upbx == "postgres" else "UPDATE baixas_avarias SET loja_baixa = ?, ref_bon_transferen = ?, nf_b_entrada = ?, produto_hortifruti = ?, quantidade_kg_cx = ?, valor_total_avaria = ?, saldo_restante_nota = ?, saldo_total_disponivel = ? WHERE id = ?",
                                                (str(nova_loja_bx), str(novo_ref_bx).strip(), str(nova_nf_b_entrada), str(novo_prod_bx), float(q_f_ed), float(v_f_ed), float(novo_saldo_restante_ed), float(saldo_disp_edit), reg_id_bx)
                                            )
                                        conn_up_bx.commit()
                                        st.cache_data.clear()
                                        st.success("Baixa atualizada com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        conn_up_bx.rollback()
                                        st.error(f"Erro ao atualizar baixa: {e}")
                                    finally:
                                        conn_up_bx.close()

                            if excluir_bx_btn:
                                with spinner_supernova("Excluindo baixa..."):
                                    conn_del_bx, db_td_bx = get_db_connection()
                                    try:
                                        cur_delbx = conn_del_bx.cursor()
                                        cur_delbx.execute(
                                            "DELETE FROM baixas_avarias WHERE id = %s" if db_td_bx == "postgres" else "DELETE FROM baixas_avarias WHERE id = ?",
                                            (int(id_bx_atual) if db_td_bx == "postgres" else id_bx_atual,)
                                        )
                                        conn_del_bx.commit()
                                        st.cache_data.clear()
                                        st.success("Baixa excluída com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        conn_del_bx.rollback()
                                        st.error(f"Erro ao excluir baixa: {e}")
                                    finally:
                                        conn_del_bx.close()
        else:
            st.info("Nenhum registo de baixa encontrado.")

    elif menu == "Relatórios & Gráficos" and is_admin:
        with spinner_supernova("Carregando relatórios e BI..."):
            st.title("📊 Relatórios & Business Intelligence (BI) Executive")
        tab_bi_receb, tab_bi_bonf_avaria = st.tabs([
            "📋 BI de Recebimento de Cargas",
            "📈 BI Bonificações, Transferências & Prevenção de Perdas"
        ])
        df_roms, df_itens, df_bonf_rel, df_baixas_rel = _carregar_dados_bi_cached()
        df_roms = df_roms.copy()
        df_itens = df_itens.copy()
        df_bonf_rel = df_bonf_rel.copy()
        df_baixas_rel = df_baixas_rel.copy()

        with tab_bi_receb:
            if df_roms.empty or df_itens.empty:
                st.warning("Ainda não existem dados de recebimento cadastrados.")
            else:
                df_roms['data_dt'] = pd.to_datetime(df_roms['data_recebimento'], format='%d/%m/%Y', errors='coerce')
                df_full = df_itens.merge(df_roms, left_on='romaneio_id', right_on='id', suffixes=('_item', '_romaneio'))

                st.markdown("### 🔍 Filtros da Análise Gerencial (Período Livre)")
                col_f0, col_f1, col_f2, col_f3, col_f4 = st.columns([1.2, 1, 1, 1, 1])
                with col_f0:
                    lista_tipos_op_bi = ["TODOS OS TIPOS", "Compra", "Bonificação", "Transferência", "Transferência/Bonificação", "Troca por Troca"]
                    tipo_op_bi_sel = st.selectbox("Tipo de Operação", options=lista_tipos_op_bi, index=0, key="rel_filter_tipo_op")
                with col_f1: loja_sel = st.selectbox("Filtrar por Loja", ["TODAS AS LOJAS"] + list(df_roms["loja"].unique()), placeholder="Selecione...", key="rel_filter_loja")
                with col_f2: prod_sel = st.selectbox("Filtrar por Produto", ["TODOS OS PRODUTOS"] + sorted(list(df_itens["produto"].unique())), placeholder="Selecione...", key="rel_filter_prod")
                with col_f3:
                    dt_min = df_roms['data_dt'].min() if not df_roms['data_dt'].isna().all() else datetime(1900, 1, 1).date()
                    dt_inicio = seletor_data_unificado("Data Início", "bi_ini")
                with col_f4:
                    dt_max = df_roms['data_dt'].max() if not df_roms['data_dt'].isna().all() else datetime.now(ZoneInfo("America/Manaus"))
                    dt_fim = seletor_data_unificado("Data Fim", "bi_fim")

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
                    tot_recebido = float(df_filtrado['valor_total'].sum())
                    num_roms = df_filtrado['numero_romaneio'].nunique()
                    val_troca = float(df_filtrado[df_filtrado['tipo_operacao'].str.contains("Troca por Troca", case=False, na=False)]['valor_total'].sum())
                    val_transf = float(df_filtrado[df_filtrado['tipo_operacao'].str.contains("Transferência", case=False, na=False)]['valor_total'].sum())

                    df_bx_periodo = df_baixas_rel.copy()
                    if not df_bx_periodo.empty:
                        df_bx_periodo['data_dt'] = pd.to_datetime(df_bx_periodo['data_baixa'].str.split(' ').str[0], format='%d/%m/%Y', errors='coerce')
                        if loja_sel != "TODAS AS LOJAS":
                            df_bx_periodo = df_bx_periodo[df_bx_periodo['loja_baixa'].str.contains(loja_sel, case=False, na=False)]
                        if prod_sel != "TODOS OS PRODUTOS":
                            df_bx_periodo = df_bx_periodo[df_bx_periodo['produto_hortifruti'] == prod_sel]
                        if dt_inicio and dt_fim:
                            df_bx_periodo = df_bx_periodo[(df_bx_periodo['data_dt'] >= pd.to_datetime(dt_inicio)) & (df_bx_periodo['data_dt'] <= pd.to_datetime(dt_fim))]
                    val_perdas_evitadas = float(df_bx_periodo['valor_total_avaria'].sum()) if not df_bx_periodo.empty else 0.0

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

                    st.markdown("---")
                    st.download_button(
                        label="📥 Descarregar Relatório Consolidado (Excel / CSV)",
                        data=df_filtrado.to_csv(index=False, sep=';').encode('utf-8-sig'),
                        file_name=f"Relatorio_Hortifruti_HortiControl_{datetime.now(ZoneInfo('America/Manaus')).strftime('%Y%m%d')}.csv",
                        mime="text/csv", type="primary", key="btn_download_csv_relatorio"
                    )

        with tab_bi_bonf_avaria:
            st.subheader("📈 Análise Executiva de Bonificações, Transferências & Prevenção de Perdas")
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

            v_tot_bonf = float(df_b_sub[df_b_sub.get('tipo_bonificacao', 'Bonificação') == 'Bonificação']['valor_bonificacao'].sum()) if not df_b_sub.empty else 0.0
            v_tot_transf = float(df_b_sub[df_b_sub.get('tipo_bonificacao', 'Bonificação') == 'Transferência de Bonificação']['valor_bonificacao'].sum()) if not df_b_sub.empty else 0.0
            v_tot_entradas = float(df_b_sub['valor_bonificacao'].sum()) if not df_b_sub.empty else 0.0
            v_tot_avarias_salvas = float(df_bx_sub['valor_total_avaria'].sum()) if not df_bx_sub.empty else 0.0
            taxa_cobertura = float((v_tot_avarias_salvas / v_tot_entradas * 100)) if v_tot_entradas > 0 else 0.0
            v_saldo_remanescente = float(max(0.0, v_tot_entradas - v_tot_avarias_salvas))

            st.markdown("---")
            st.markdown("### 🏆 Painel de Impacto Executivo")
            kpi_e1, kpi_e2, kpi_e3, kpi_e4, kpi_e5 = st.columns(5)
            kpi_e1.metric("1. Entradas Bonificadas", f"R$ {fmt_ptbr(v_tot_bonf, 2)}")
            kpi_e2.metric("2. Transferências", f"R$ {fmt_ptbr(v_tot_transf, 2)}")
            kpi_e3.metric("3. Perdas Evitadas (Avarias)", f"R$ {fmt_ptbr(v_tot_avarias_salvas, 2)}", delta=f"{fmt_ptbr(v_tot_avarias_salvas, 2)} Salvos", delta_color="normal")
            kpi_e4.metric("4. Taxa de Cobertura", f"{fmt_ptbr(taxa_cobertura, 2)}%")
            kpi_e5.metric("5. Saldo Remanescente", f"R$ {fmt_ptbr(v_saldo_remanescente, 2)}")

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

            with bg_bi2:
                st.markdown("#### Avarias Bonificadas por Loja (Economia Gerada)")
                if not df_bx_sub.empty:
                    df_bx_grp = df_bx_sub.groupby("loja_baixa")["valor_total_avaria"].sum().reset_index()
                    fig_avarias = px.bar(df_bx_grp, x="loja_baixa", y="valor_total_avaria", text_auto=".2f", color="valor_total_avaria", color_continuous_scale="Purples")
                    fig_avarias.update_layout(xaxis_title="Loja da Baixa", yaxis_title="Avaria Coberta (R$)", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#FFFFFF")
                    st.plotly_chart(fig_avarias, use_container_width=True)

            st.markdown("---")
            metrics_dict = {
                "tot_bonf": v_tot_bonf, "tot_transf": v_tot_transf,
                "tot_avaria": v_tot_avarias_salvas, "taxa_cobertura": taxa_cobertura,
                "saldo_restante": v_saldo_remanescente
            }
            pdf_bi_bytes = gerar_pdf_relatorio_gerencial_bi(metrics_dict, df_b_sub, df_bx_sub)
            col_pdf_bi1, col_pdf_bi2 = st.columns([3, 1])
            with col_pdf_bi1:
                st.markdown("Gere um relatório em PDF para apresentações de resultados em reuniões com a diretoria.")
            with col_pdf_bi2:
                st.download_button(
                    label="📥 Baixar PDF Executivo", data=pdf_bi_bytes,
                    file_name=f"Relatorio_Executivo_Lideranca_HortiControl_{datetime.now(ZoneInfo('America/Manaus')).strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf", type="primary", key="btn_download_executivo_bi"
                )

    elif menu == "Gerenciar Cadastros (Produtos)" and is_admin:
        with spinner_supernova("Carregando cadastros..."):
            st.title("🛒 Gerenciamento e Cadastro (Produtos & Fornecedores)")
        tab_prod, tab_forn = st.tabs(["📦 Cadastro de Produtos", "🏢 Cadastro de Fornecedores"])
        with tab_prod:
            if "prod_form_suf" not in st.session_state:
                st.session_state["prod_form_suf"] = 0
            pf_suf = st.session_state["prod_form_suf"]
            with st.expander("➕ Cadastrar Novo Produto", expanded=False):
                with st.form(f"cad_prod_form_{pf_suf}", clear_on_submit=False):
                    col_cp1, col_cp2, col_cp3, col_cp4 = st.columns([2, 2, 3, 1.5])
                    with col_cp1: cod_prod_input = st.text_input("Código do Produto", placeholder="", key=f"cp_cod_{pf_suf}")
                    with col_cp2: cod_bar_input = st.text_input("Código de Barras", placeholder="", key=f"cp_bar_{pf_suf}")
                    with col_cp3: nome_p = st.text_input("Nome do Produto *", placeholder="", key=f"cp_nome_{pf_suf}")
                    with col_cp4: und_p = st.selectbox("Unidade", ["KG", "UNID", "GRM", "CX"], index=0, key=f"cp_und_{pf_suf}")
                    if st.form_submit_button("➕ Cadastrar Produto", type="primary"):
                        if not nome_p.strip(): st.error("O Nome é obrigatório.")
                        else:
                            with spinner_supernova("Cadastrando produto..."):
                                conn, db_type = get_db_connection()
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("INSERT INTO produtos (codigo_barras, codigo_produto, nome, unidade_padrao) VALUES (%s, %s, %s, %s)" if db_type == "postgres" else "INSERT INTO produtos (codigo_barras, codigo_produto, nome, unidade_padrao) VALUES (?, ?, ?, ?)", (cod_bar_input.strip() if cod_bar_input else None, cod_prod_input.strip() if cod_prod_input else None, nome_p.strip().upper(), und_p))
                                    conn.commit()
                                    st.cache_data.clear()
                                    carregar_produtos_cached.clear()
                                    st.session_state["prod_form_suf"] += 1
                                    st.success("Cadastrado com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    conn.rollback()
                                    st.error(f"Erro: {e}")
                                finally:
                                    conn.close()
            st.markdown("---")
            produtos_cadastrados = carregar_produtos_cached()

            if produtos_cadastrados:
                produtos_com_id_ajustado = [(i, p[1], p[0], p[2], p[3]) for i, p in enumerate(produtos_cadastrados, 1)]
                df_produtos = pd.DataFrame(produtos_com_id_ajustado, columns=["ID", "Código de Barras", "Código do Produto", "Nome do Produto", "Unidade Padrão"])
                
                conn_p_pdf, _ = get_db_connection()
                try:
                    cur_pp = conn_p_pdf.cursor()
                    cur_pp.execute("SELECT id, codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos ORDER BY id DESC")
                    prods_full_pdf = cur_pp.fetchall()
                finally:
                    conn_p_pdf.close()

                st.download_button(
                    label="📥 Descarregar Relatório de Produtos em PDF",
                    data=gerar_pdf_produtos(prods_full_pdf),
                    file_name=f"Relatorio_Produtos_HortiControl_{datetime.now(ZoneInfo('America/Manaus')).strftime('%Y%m%d')}.pdf",
                    mime="application/pdf", type="primary"
                )
                st.markdown("")
                st.dataframe(df_produtos[["ID", "Código do Produto", "Código de Barras", "Nome do Produto", "Unidade Padrão"]], use_container_width=True, hide_index=True, height=250)

                st.markdown("### ✏️ Editar ou Excluir Produto")
                conn_p_ed, db_tped = get_db_connection()
                try:
                    cur_pe = conn_p_ed.cursor()
                    cur_pe.execute("SELECT id, nome, codigo_produto FROM produtos ORDER BY id DESC")
                    prods_para_edit = cur_pe.fetchall()
                finally:
                    conn_p_ed.close()

                opcoes_edit_prod = [(p[0], f"{p[1]} (Cód: {p[2] or 'S/Cód'})") for p in prods_para_edit]
                prod_sel_ed = st.selectbox("Selecione o produto para editar ou excluir", options=opcoes_edit_prod, format_func=lambda x: x[1], key="sel_prod_editar")
                if prod_sel_ed:
                    id_p_ed = prod_sel_ed[0]
                    conn_p_det, db_tp_det = get_db_connection()
                    try:
                        cur_pd = conn_p_det.cursor()
                        r_id_pd = int(id_p_ed) if db_tp_det == "postgres" else id_p_ed
                        cur_pd.execute("SELECT codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos WHERE id = %s" if db_tp_det == "postgres" else "SELECT codigo_barras, codigo_produto, nome, unidade_padrao FROM produtos WHERE id = ?", (r_id_pd,))
                        dados_p_atual = cur_pd.fetchone()
                    finally:
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
                                with spinner_supernova("Atualizando produto..."):
                                    conn_up_p, db_tup = get_db_connection()
                                    try:
                                        cur_upp = conn_up_p.cursor()
                                        r_id_upp = int(id_p_ed) if db_tup == "postgres" else id_p_ed
                                        cur_upp.execute(
                                            "UPDATE produtos SET codigo_barras = %s, codigo_produto = %s, nome = %s, unidade_padrao = %s WHERE id = %s" if db_tup == "postgres" else "UPDATE produtos SET codigo_barras = ?, codigo_produto = ?, nome = ?, unidade_padrao = ? WHERE id = ?",
                                            (ep_cod_bar.strip(), ep_cod_prod.strip(), ep_nome.strip().upper(), ep_und, r_id_upp)
                                        )
                                        conn_up_p.commit()
                                        st.cache_data.clear()
                                        carregar_produtos_cached.clear()
                                        st.success("Produto atualizado com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        conn_up_p.rollback()
                                        st.error(f"Erro ao atualizar produto: {e}")
                                    finally:
                                        conn_up_p.close()

                            if btn_excluir_prod:
                                with spinner_supernova("Excluindo produto..."):
                                    conn_del_p, db_tdp = get_db_connection()
                                    try:
                                        cur_delp = conn_del_p.cursor()
                                        r_id_delp = int(id_p_ed) if db_tdp == "postgres" else id_p_ed
                                        cur_delp.execute(
                                            "DELETE FROM produtos WHERE id = %s" if db_tdp == "postgres" else "DELETE FROM produtos WHERE id = ?",
                                            (r_id_delp,)
                                        )
                                        conn_del_p.commit()
                                        st.cache_data.clear()
                                        carregar_produtos_cached.clear()
                                        st.success("Produto excluído com sucesso!")
                                        st.rerun()
                                    except Exception as e:
                                        conn_del_p.rollback()
                                        st.error(f"Erro ao excluir produto: {e}")
                                    finally:
                                        conn_del_p.close()
            else:
                st.info("Nenhum produto cadastrado.")

        with tab_forn:
            if "forn_form_suf" not in st.session_state:
                st.session_state["forn_form_suf"] = 0
            ff_suf = st.session_state["forn_form_suf"]
            with st.expander("➕ Cadastrar Novo Fornecedor", expanded=False):
                with st.form(f"cad_forn_form_{ff_suf}", clear_on_submit=False):
                    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
                    with col_f1: cod_forn_input = st.text_input("Código do Fornecedor", placeholder="", key=f"cf_cod_{ff_suf}")
                    with col_f2: cnpj_forn_input = st.text_input("CNPJ", placeholder="", key=f"cf_cnpj_{ff_suf}")
                    with col_f3: nome_forn_input = st.text_input("Nome do Fornecedor *", placeholder="", key=f"cf_nome_{ff_suf}")
                    if st.form_submit_button("➕ Cadastrar Fornecedor", type="primary"):
                        if not nome_forn_input.strip(): st.error("O Nome do Fornecedor é obrigatório.")
                        else:
                            with spinner_supernova("Cadastrando fornecedor..."):
                                conn, db_type = get_db_connection()
                                try:
                                    cursor = conn.cursor()
                                    cursor.execute("INSERT INTO fornecedores (codigo_fornecedor, cnpj, nome) VALUES (%s, %s, %s)" if db_type == "postgres" else "INSERT INTO fornecedores (codigo_fornecedor, cnpj, nome) VALUES (?, ?, ?)", (cod_forn_input.strip() if cod_forn_input else None, cnpj_forn_input.strip() if cnpj_forn_input else None, nome_forn_input.strip().upper()))
                                    conn.commit()
                                    st.cache_data.clear()
                                    carregar_fornecedores_cached.clear()
                                    st.session_state["forn_form_suf"] += 1
                                    st.success("Fornecedor cadastrado!")
                                    st.rerun()
                                except Exception as e:
                                    conn.rollback()
                                    st.error(f"Erro: {e}")
                                finally:
                                    conn.close()
            st.markdown("---")
            conn, db_type = get_db_connection()
            try:
                forns_cadastrados = pd.read_sql_query("SELECT id, codigo_fornecedor, cnpj, nome FROM fornecedores ORDER BY id DESC", conn)
            finally:
                conn.close()

            if not forns_cadastrados.empty:
                forns_cadastrados_show = forns_cadastrados.copy()
                forns_cadastrados_show["ID"] = range(1, len(forns_cadastrados_show) + 1)
                st.dataframe(forns_cadastrados_show[["ID", "codigo_fornecedor", "cnpj", "nome"]].rename(columns={"codigo_fornecedor": "Código do Fornecedor", "cnpj": "CNPJ", "nome": "Nome do Fornecedor"}), use_container_width=True, hide_index=True, height=250)

                st.markdown("### ✏️ Editar ou Excluir Fornecedor")
                opcoes_edit_forn = [(row["id"], f"{row['nome']} (Cód: {row['codigo_fornecedor'] or 'S/Cód'})") for _, row in forns_cadastrados.iterrows()]
                forn_sel_ed = st.selectbox("Selecione o fornecedor para editar ou excluir", options=opcoes_edit_forn, format_func=lambda x: x[1], key="sel_forn_editar")
                if forn_sel_ed:
                    id_f_ed = forn_sel_ed[0]
                    dados_f_atual = forns_cadastrados[forns_cadastrados["id"] == id_f_ed].iloc[0]

                    with st.form("form_edit_fornecedor"):
                        ef_cod = st.text_input("Código do Fornecedor", value=str(dados_f_atual["codigo_fornecedor"] or ""))
                        ef_cnpj = st.text_input("CNPJ", value=str(dados_f_atual["cnpj"] or ""))
                        ef_nome = st.text_input("Nome do Fornecedor", value=str(dados_f_atual["nome"] or ""))
                        col_bf1, col_bf2 = st.columns(2)
                        with col_bf1: btn_salvar_forn = st.form_submit_button("💾 Salvar Alterações", type="primary")
                        with col_bf2: btn_excluir_forn = st.form_submit_button("🗑️ Excluir Fornecedor", type="secondary")

                        if btn_salvar_forn:
                            with spinner_supernova("Atualizando fornecedor..."):
                                conn_up_f, db_tuf = get_db_connection()
                                try:
                                    cur_upf = conn_up_f.cursor()
                                    r_id_upf = int(id_f_ed) if db_tuf == "postgres" else id_f_ed
                                    cur_upf.execute(
                                        "UPDATE fornecedores SET codigo_fornecedor = %s, cnpj = %s, nome = %s WHERE id = %s" if db_tuf == "postgres" else "UPDATE fornecedores SET codigo_fornecedor = ?, cnpj = ?, nome = ? WHERE id = ?",
                                        (ef_cod.strip(), ef_cnpj.strip(), ef_nome.strip().upper(), r_id_upf)
                                    )
                                    conn_up_f.commit()
                                    st.cache_data.clear()
                                    carregar_fornecedores_cached.clear()
                                    st.success("Fornecedor atualizado com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    conn_up_f.rollback()
                                    st.error(f"Erro ao atualizar fornecedor: {e}")
                                finally:
                                    conn_up_f.close()

                        if btn_excluir_forn:
                            with spinner_supernova("Excluindo fornecedor..."):
                                conn_del_f, db_tdf = get_db_connection()
                                try:
                                    cur_delf = conn_del_f.cursor()
                                    r_id_delf = int(id_f_ed) if db_tdf == "postgres" else id_f_ed
                                    cur_delf.execute(
                                        "DELETE FROM fornecedores WHERE id = %s" if db_tdf == "postgres" else "DELETE FROM fornecedores WHERE id = ?",
                                        (r_id_delf,)
                                    )
                                    conn_del_f.commit()
                                    st.cache_data.clear()
                                    carregar_fornecedores_cached.clear()
                                    st.success("Fornecedor excluído com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    conn_del_f.rollback()
                                    st.error(f"Erro ao excluir fornecedor: {e}")
                                finally:
                                    conn_del_f.close()
            else:
                st.info("Nenhum fornecedor cadastrado.")

    elif menu == "Gerenciar Usuários & Permissões" and is_admin:
        with spinner_supernova("Carregando usuários e permissões..."):
            st.title("👥 Gerenciar Usuários & Permissões")
        st.markdown("Defina os acessos ao sistema: **Conferente** (apenas digita o romaneio) ou **Gestor / Assistente** (acesso completo ao BI, bonificações, cadastros e usuários).")
        if "usr_form_suf" not in st.session_state:
            st.session_state["usr_form_suf"] = 0
        uf_suf = st.session_state["usr_form_suf"]
        with st.expander("➕ Cadastrar Novo Usuário", expanded=False):
            with st.form(f"cad_usr_form_{uf_suf}", clear_on_submit=False):
                u_col1, u_col2, u_col3, u_col4 = st.columns(4)
                with u_col1: nome_usr = st.text_input("Nome Completo *", placeholder="", key=f"cu_nome_{uf_suf}")
                with u_col2: login_usr = st.text_input("Login / Usuário *", placeholder="", key=f"cu_login_{uf_suf}")
                with u_col3: senha_usr = st.text_input("Senha *", type="password", placeholder="", key=f"cu_senha_{uf_suf}")
                with u_col4: perfil_usr = st.selectbox("Perfil de Acesso", ["Conferente", "Auxiliar", "Gestor"], index=0, key=f"cu_perfil_{uf_suf}")
                if st.form_submit_button("✅ Criar Usuário", type="primary"):
                    if not nome_usr.strip() or not login_usr.strip() or not senha_usr.strip(): st.error("Preencha todos os campos.")
                    else:
                        with spinner_supernova("Criando usuário..."):
                            conn, db_type = get_db_connection()
                            try:
                                cursor = conn.cursor()
                                senha_hash = gerar_hash_senha(senha_usr.strip())
                                cursor.execute("INSERT INTO usuarios (nome, login, senha, perfil) VALUES (%s, %s, %s, %s)" if db_type == "postgres" else "INSERT INTO usuarios (nome, login, senha, perfil) VALUES (?, ?, ?, ?)", (nome_usr.strip(), login_usr.strip(), senha_hash, perfil_usr))
                                conn.commit()
                                st.cache_data.clear()
                                st.session_state["usr_form_suf"] += 1
                                st.success(f"Usuário {nome_usr} criado!")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Erro: {e}")
                            finally:
                                conn.close()
        st.markdown("---")
        conn, db_type = get_db_connection()
        try:
            df_users = pd.read_sql_query("SELECT id, nome, login, perfil FROM usuarios ORDER BY id ASC", conn)
        finally:
            conn.close()
        if not df_users.empty:
            df_users_show = df_users.copy()
            df_users_show["ID"] = range(1, len(df_users_show) + 1)
            st.dataframe(df_users_show[["ID", "nome", "login", "perfil"]].rename(columns={"nome": "Nome", "login": "Login", "perfil": "Perfil"}), use_container_width=True, hide_index=True, height=250)

            st.markdown("### ✏️ Editar ou Excluir Usuário")
            opcoes_edit_usr = [(row["id"], f"{row['nome']} (Login: {row['login']} | Perfil: {row['perfil']})") for _, row in df_users.iterrows()]
            usr_sel_ed = st.selectbox("Selecione o usuário para editar ou excluir", options=opcoes_edit_usr, format_func=lambda x: x[1], key="sel_usr_editar")
            if usr_sel_ed:
                id_u_ed = usr_sel_ed[0]
                dados_u_atual = df_users[df_users["id"] == id_u_ed].iloc[0]

                with st.form("form_edit_usuario"):
                    eu_nome = st.text_input("Nome Completo", value=str(dados_u_atual["nome"]))
                    eu_login = st.text_input("Login / Usuário", value=str(dados_u_atual["login"]))
                    eu_senha = st.text_input("Nova Senha (Deixe em branco para manter a atual)", type="password")
                    perfis_disponiveis = ["Conferente", "Auxiliar", "Gestor"]
                    idx_perf = perfis_disponiveis.index(dados_u_atual["perfil"]) if dados_u_atual["perfil"] in perfis_disponiveis else 0
                    eu_perfil = st.selectbox("Perfil de Acesso", perfis_disponiveis, index=idx_perf)
                    col_bu1, col_bu2 = st.columns(2)
                    with col_bu1: btn_salvar_usr = st.form_submit_button("💾 Salvar Alterações", type="primary")
                    with col_bu2: btn_excluir_usr = st.form_submit_button("🗑️ Excluir Usuário", type="secondary")

                    if btn_salvar_usr:
                        with spinner_supernova("Atualizando usuário..."):
                            conn_up_u, db_tuu = get_db_connection()
                            try:
                                cur_upu = conn_up_u.cursor()
                                r_id_upu = int(id_u_ed) if db_tuu == "postgres" else id_u_ed
                                if eu_senha.strip():
                                    hash_nova_s = gerar_hash_senha(eu_senha.strip())
                                    cur_upu.execute(
                                        "UPDATE usuarios SET nome = %s, login = %s, senha = %s, perfil = %s WHERE id = %s" if db_tuu == "postgres" else "UPDATE usuarios SET nome = ?, login = ?, senha = ?, perfil = ? WHERE id = ?",
                                        (eu_nome.strip(), eu_login.strip(), hash_nova_s, eu_perfil, r_id_upu)
                                    )
                                else:
                                    cur_upu.execute(
                                        "UPDATE usuarios SET nome = %s, login = %s, perfil = %s WHERE id = %s" if db_tuu == "postgres" else "UPDATE usuarios SET nome = ?, login = ?, perfil = ? WHERE id = ?",
                                        (eu_nome.strip(), eu_login.strip(), eu_perfil, r_id_upu)
                                    )
                                conn_up_u.commit()
                                st.cache_data.clear()
                                st.success("Usuário atualizado com sucesso!")
                                st.rerun()
                            except Exception as e:
                                conn_up_u.rollback()
                                st.error(f"Erro ao atualizar usuário: {e}")
                            finally:
                                conn_up_u.close()

                    if btn_excluir_usr:
                        if str(dados_u_atual["login"]).lower() == "908":
                            st.error("Não é permitido excluir o usuário Administrador padrão (908).")
                        else:
                            with spinner_supernova("Excluindo usuário..."):
                                conn_del_u, db_tdu = get_db_connection()
                                try:
                                    cur_delu = conn_del_u.cursor()
                                    r_id_delu = int(id_u_ed) if db_tdu == "postgres" else id_u_ed
                                    cur_delu.execute(
                                        "DELETE FROM usuarios WHERE id = %s" if db_tdu == "postgres" else "DELETE FROM usuarios WHERE id = ?",
                                        (r_id_delu,)
                                    )
                                    conn_del_u.commit()
                                    st.cache_data.clear()
                                    st.success("Usuário excluído com sucesso!")
                                    st.rerun()
                                except Exception as e:
                                    conn_del_u.rollback()
                                    st.error(f"Erro ao excluir usuário: {e}")
                                finally:
                                    conn_del_u.close()
        else:
            st.info("Nenhum usuário cadastrado.")

    if is_admin:
        render_widget_flutuante_chatcontrol()

st.markdown("""
<div style="text-align: center; color: gray; font-size: 0.8em; margin-top: 30px; padding: 10px; border-top: 1px solid rgba(128,128,128,0.2);">
    HortiControl Supernova • Sistema de Recebimento de Hortifrúti
</div>
""", unsafe_allow_html=True)
