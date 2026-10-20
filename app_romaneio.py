import base64
from datetime import datetime
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
    page_title="Supermercado Super Nova Cidade - Recebimento Hortifrúti",
    page_icon=logo_icon if logo_icon else "🥦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# 2. DEFINIÇÃO DA IMAGEM DE FUNDO E ESTILOS CSS
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
    section[data-testid="stSidebar"] {{
        display: block !important;
        visibility: visible !important;
        background-color: #F4F6F4 !important;
        border-right: 3px solid #1B5E20 !important;
    }}
    header[data-testid="stHeader"], footer, div[data-testid="stToolbar"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    .block-container {{
        padding-top: 1.0rem !important;
        padding-bottom: 1rem !important;
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
# 3. BANCO DE DADOS E INICIALIZAÇÃO
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

# ---------------------------------------------------------
# 4. GERADOR DE PDF FORMATADO
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
                    letter[0] / 2 - 150,
                    letter[1] / 2 - 150,
                    width=300,
                    height=300,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass
            canvas_obj.restoreState()
    if logo_path and os.path.exists(logo_path):
        logo_img_header = RLImage(logo_path, width=70, height=50)
    else:
        logo_img_header = Paragraph("<b>SUPER NOVA<br/>CIDADE</b>", styles["Normal"])
    header_table = Table(
        [
            [
                logo_img_header,
                Paragraph(
                    "<b>SUPERMERCADO SUPER NOVA CIDADE</b><br/>Romaneio de Recebimento - Hortifrúti",
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
            Paragraph(f"<b>Conferente (Rec. Físico):</b> {romaneio_data.get('conferente','')}", styles["Normal"]),
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
        ["Item", "Descrição do Produto", "Qtd / Peso", "UND", "Vl. Unit", "Total"]
    ]
    total_geral = 0.0
    for idx, item in enumerate(itens_data, 1):
        v_unit = item[4] if len(item) > 4 and item[4] else 0.0
        v_tot = item[5] if len(item) > 5 and item[5] else 0.0
        total_geral += v_tot
        table_content.append([
            str(idx),
            str(item[1]),
            f"{item[2]:,.3f}",
            str(item[3]),
            f"R$ {v_unit:,.2f}",
            f"R$ {v_tot:,.2f}",
        ])
    itens_table = Table(table_content, colWidths=[35, 215, 75, 50, 75, 90])
    itens_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ])
    )
    story.append(itens_table)
    story.append(Spacer(1, 8))
    total_table = Table(
        [[f"TOTAL GERAL DO ROMANEIO: R$ {total_geral:,.2f}"]], colWidths=[540]
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
    img_conf_pdf = None
    if path_conf and os.path.exists(path_conf):
        try:
            img_conf_pdf = RLImage(path_conf, width=180, height=50)
        except Exception:
            pass
    img_ent_pdf = None
    if path_ent and os.path.exists(path_ent):
        try:
            img_ent_pdf = RLImage(path_ent, width=180, height=50)
        except Exception:
            pass
    col_conf_cell = [
        img_conf_pdf if img_conf_pdf else Spacer(1, 40),
        Paragraph(f"<b>Conferente:</b> {romaneio_data.get('conferente','')}", styles["Normal"]),
    ]
    col_ent_cell = [
        img_ent_pdf if img_ent_pdf else Spacer(1, 40),
        Paragraph(f"<b>Entregador / Fornecedor:</b> {romaneio_data.get('fornecedor','')}", styles["Normal"]),
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
# 5. TELA DE LOGIN
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
    user_info = st.session_state["usuario_logado"]
    st.sidebar.markdown(f"**Usuário:** {user_info['nome']}")
    perfil_db = str(user_info.get("perfil", "")).strip().lower()
    is_admin = (
        user_info["login"].lower() == "admin"
        or "gestor" in perfil_db
        or "adm" in perfil_db
    )
    if is_admin:
        st.sidebar.success("🔒 Perfil: Gestor / Administrador")
        eh_gestor = True
    else:
        st.sidebar.info("👤 Perfil: Conferente")
        eh_gestor = False
    if eh_gestor:
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        total_romaneios_db = pd.read_sql_query(
            "SELECT COUNT(*) as qtd FROM romaneios", conn
        ).iloc[0]["qtd"]
        conn.close()
        st.sidebar.divider()
        st.sidebar.markdown(
            f"🔔 **Painel de Alertas:**<br>📦 Romaneios: **{total_romaneios_db}**",
            unsafe_allow_html=True,
        )
    if st.sidebar.button("Sair / Logout", type="secondary"):
        st.session_state["usuario_logado"] = None
        st.rerun()
    st.sidebar.divider()
    opcoes_menu = ["Romaneio de Recebimento - Hortifrúti", "Consultar Romaneios"]
    if eh_gestor:
        opcoes_menu.extend([
            "Relatórios & Gráficos",
            "Gerenciar Cadastros (Produtos)",
            "Gerenciar Usuários & Permissões",
        ])
    menu = st.sidebar.radio("Navegação", opcoes_menu)
    
    # ---------------------------------------------------------
    # 6. MÓDULOS DO SISTEMA
    # ---------------------------------------------------------
    if menu == "Romaneio de Recebimento - Hortifrúti":
        st.title("Romaneio de Recebimento - Hortifrúti")
        if "form_key_suffix" not in st.session_state:
            st.session_state["form_key_suffix"] = 0
        k_suffix = st.session_state["form_key_suffix"]
        
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
                    placeholder="(00) 00000-0000",
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
                "Produto",
                (
                    prod_nomes_keys
                    if prod_dict
                    else ["Cadastre produtos na aba de Gestor"]
                ),
                key=f"prod_sel_{k_suffix}",
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
                key=f"und_sel_{k_suffix}",
            )
        with col_p3:
            # Quantidade em branco (valor 0.0 mas sem valor fixo pré-preenchido)
            qtd_input = st.number_input(
                "Qtd / Peso", min_value=0.0, value=0.0, step=0.1, format="%.3f", key=f"qtd_{k_suffix}"
            )
        with col_p4:
            # Valor Unitário em branco (valor 0.0)
            val_unit = st.number_input(
                "Valor Unit. (R$)", min_value=0.0, value=0.0, step=0.01, format="%.2f", key=f"vunit_{k_suffix}"
            )
        with col_p5:
            st.write("")
            st.write("")
            if st.button("➕ Add", type="primary", key=f"btn_add_{k_suffix}"):
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
                    st.warning("Informe uma quantidade maior que zero.")

        if st.session_state["itens_romaneio"]:
            df_itens = pd.DataFrame(st.session_state["itens_romaneio"])
            # Ajustando a numeração do índice da tabela para começar de 1 em diante
            df_itens.index = range(1, len(df_itens) + 1)
            st.dataframe(df_itens, use_container_width=True)
            st.markdown(
                f"### **Total Geral: R$"
                f" {df_itens['valor_total'].sum():,.2f}**"
            )
            if st.button("🗑️ Limpar Itens", type="secondary", key=f"btn_del_itens_{k_suffix}"):
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
            st.write("**Assinatura Conferente**")
            canvas_conf = st_canvas(
                stroke_width=3,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=120,
                width=280,
                key=f"canv_conf_{k_suffix}",
            )
        with col_ass2:
            st.write("**Assinatura Entregador**")
            canvas_ent = st_canvas(
                stroke_width=3,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=120,
                width=280,
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
                    
                    st.success(f"Romaneio {num_romaneio} salvo com sucesso no banco de dados!")
                    
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
                    
                    st.download_button(
                        label=f"📥 Baixar PDF do Romaneio {num_romaneio}",
                        data=pdf_buffer_novo,
                        file_name=f"{num_romaneio}.pdf",
                        mime="application/pdf",
                        type="primary",
                        key=f"dl_btn_salvo_{k_suffix}",
                    )
                    
                    st.session_state["itens_romaneio"] = []
                    st.session_state["form_key_suffix"] += 1
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Erro ao salvar romaneio: {e}")

    elif menu == "Consultar Romaneios":
        st.title("🔍 Consulta de Romaneios")
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_rom = pd.read_sql_query("SELECT * FROM romaneios ORDER BY id DESC", conn)
        conn.close()
        if not df_rom.empty:
            for idx, row in df_rom.iterrows():
                with st.expander(
                    f"Romaneio: {row['numero_romaneio']} | Fornecedor:"
                    f" {row['fornecedor']} | Data: {row['data_recebimento']}"
                ):
                    st.write(f"**Loja:** {row['loja']}")
                    st.write(
                        f"**Código Fornecedor:** {row['codigo_fornecedor']} |"
                        f" **Telefone:** {row['telefone_fornecedor']}"
                    )
                    st.write(f"**Conferente:** {row['conferente']}")
                    st.write(
                        f"**Pagamento à Vista:** {row['pagamento_a_vista']} |"
                        f" **Data Pagamento:** {row['data_pagamento'] if row['data_pagamento'] else 'N/A'}"
                    )
                    conn_i = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                    df_itens = pd.read_sql_query(
                        "SELECT produto, quantidade, unidade, valor_unitario,"
                        " valor_total FROM romaneio_itens WHERE romaneio_id = ?",
                        conn_i,
                        params=(row["id"],),
                    )
                    conn_i.close()
                    st.markdown("**Itens Conferidos:**")
                    df_itens.index = range(1, len(df_itens) + 1)
                    st.dataframe(df_itens, use_container_width=True)
                    total_rom = df_itens["valor_total"].sum()
                    st.markdown(f"**Total do Romaneio: R$ {total_rom:,.2f}**")
                    romaneio_dict = row.to_dict()
                    itens_tuple_list = df_itens.to_records(index=False).tolist()
                    pdf_buffer = gerar_pdf_romaneio(
                        romaneio_dict,
                        itens_tuple_list,
                        row.get("assinatura_conferente"),
                        row.get("assinatura_entregador"),
                    )
                    st.download_button(
                        label=f"📥 Baixar PDF - {row['numero_romaneio']}",
                        data=pdf_buffer,
                        file_name=f"{row['numero_romaneio']}.pdf",
                        mime="application/pdf",
                        key=f"pdf_btn_cons_{row['id']}",
                    )
        else:
            st.info("Nenhum romaneio cadastrado até o momento.")
    elif menu == "Relatórios & Gráficos" and eh_gestor:
        st.title("📊 Relatórios e Análise Gráfica")
        st.info("Módulo restrito de relatórios gerenciais.")
    elif menu == "Gerenciar Cadastros (Produtos)" and eh_gestor:
        st.title("🥦 Gerenciamento de Produtos")
        with st.form("cad_prod"):
            nome_p = st.text_input("Nome do Produto")
            und_p = st.selectbox("Unidade", ["KG", "UNID", "GRM", "CX"])
            if st.form_submit_button("Cadastrar", type="primary"):
                if nome_p.strip():
                    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO produtos (nome, unidade_padrao) VALUES"
                            " (?, ?)",
                            (nome_p.strip(), und_p),
                        )
                        conn.commit()
                        st.success(f"Produto '{nome_p}' cadastrado!")
                        st.rerun()
                    except:
                        st.error("Produto já cadastrado.")
                    finally:
                        conn.close()
    elif menu == "Gerenciar Usuários & Permissões" and eh_gestor:
        st.title("👥 Gerenciamento de Usuários")
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_u = pd.read_sql_query(
            "SELECT id, nome, login, perfil FROM usuarios", conn
        )
        conn.close()
        st.dataframe(df_u, use_container_width=True)
