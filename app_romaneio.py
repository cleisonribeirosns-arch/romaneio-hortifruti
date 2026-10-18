import base64
from datetime import datetime
import io
import os
import pandas as pd
from PIL import Image
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
from streamlit_drawable_canvas import st_canvas

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E CSS (IDENTIDADE VISUAL DA EMPRESA)
# ---------------------------------------------------------
logo_page_icon = None
for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
    for prefixo in ["logo_romaneio", "logo", "Tela de login", "tela_de_login"]:
        if os.path.exists(f"{prefixo}.{ext}"):
            logo_page_icon = f"{prefixo}.{ext}"
            break
    if logo_page_icon:
        break

st.set_page_config(
    page_title="Romaneio Hortifrúti - Supermercado Super Nova Cidade",
    page_icon=logo_page_icon if logo_page_icon else "🥦",
    layout="wide",
    initial_sidebar_state="expanded",
)

bg_login_path = None
for nome_possivel in [
    "Tela de login.jpeg",
    "Tela de login.jpg",
    "Tela de login.png",
    "tela_de_login.jpeg",
    "tela_de_login.jpg",
    "tela_de_login.png",
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
            background-image: linear-gradient(rgba(27,94,32,0.85), rgba(198,40,40,0.85)), url("data:image/jpeg;base64,{encoded_string}") !important;
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

    .stApp h1, .stApp h2, .stApp h3, .stApp label {{
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8) !important;
        font-weight: bold !important;
    }}

    div[data-baseweb="input"] input {{
        color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 6px !important;
    }}

    button[kind="primary"], .stButton > button[kind="primary"] {{
        background-color: #1B5E20 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.3) !important;
    }}
    button[kind="primary"]:hover, .stButton > button[kind="primary"]:hover {{
        background-color: #2E7D32 !important;
        border-color: #FFFFFF !important;
    }}

    button[kind="secondary"], .stButton > button[kind="secondary"] {{
        background-color: #C62828 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        font-weight: bold !important;
        border-radius: 6px !important;
    }}
    button[kind="secondary"]:hover, .stButton > button[kind="secondary"]:hover {{
        background-color: #D32F2F !important;
        border-color: #FFFFFF !important;
    }}

    div[data-testid="stMetricValue"] {{
        color: #F57F17 !important;
        font-weight: bold !important;
    }}

    {css_fundo}
    </style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 2. FUNÇÃO DE NOTIFICAÇÃO VIA WHATSAPP
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
        f"🚨 *NOVO ROMANEIO HORTIFRÚTI - SUPERMERCADO SUPER NOVA CIDADE* 🚨\n\n"
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
# 3. FUNÇÃO GERADORA DE PDF OFICIAL DO ROMANEIO
# ---------------------------------------------------------
def gerar_pdf_romaneio(
    cabecalho, df_itens, assinatura_conf=None, assinatura_ent=None
):
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
        textColor=colors.HexColor("#1B5E20"),
    )

    subtitle_style = ParagraphStyle(
        "SubTitleStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2D3748"),
    )

    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio", "logo", "Tela de login", "tela_de_login"]:
            if os.path.exists(f"{prefixo}.{ext}"):
                logo_path = f"{prefixo}.{ext}"
                break
        if logo_path:
            break

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
        "<b>SUPERMERCADO SUPER NOVA CIDADE</b><br/>Controle de Recebimento"
        " de Mercadorias - Hortifrúti",
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
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F4F6F4")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#1B5E20")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A5D6A7")),
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
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#FFFDE7")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A5D6A7")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )

    story.append(t_itens)
    story.append(Spacer(1, 25))

    ass_conf_elem = Paragraph(
        "_______________________________________<br/>Assinatura do Conferente",
        subtitle_style,
    )
    ass_ent_elem = Paragraph(
        "_______________________________________<br/>Assinatura do Entregador",
        subtitle_style,
    )

    if assinatura_conf and os.path.exists(assinatura_conf):
        ass_conf_elem = RLImage(assinatura_conf, width=150, height=45)
    if assinatura_ent and os.path.exists(assinatura_ent):
        ass_ent_elem = RLImage(assinatura_ent, width=150, height=45)

    dados_ass = [
        [ass_conf_elem, ass_ent_elem],
        ["Conferente", "Entregador / Fornecedor"],
    ]
    t_ass = Table(dados_ass, colWidths=[270, 270])
    t_ass.setStyle(
        TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
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
# 4. INICIALIZAÇÃO DA BASE DE DADOS (SQLite)
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
            caminho_foto TEXT,
            assinatura_conferente TEXT,
            assinatura_entregador TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(romaneios)")
    col_rom = [column[1] for column in cursor.fetchall()]
    if "caminho_foto" not in col_rom:
        cursor.execute("ALTER TABLE romaneios ADD COLUMN caminho_foto TEXT")
    if "assinatura_conferente" not in col_rom:
        cursor.execute(
            "ALTER TABLE romaneios ADD COLUMN assinatura_conferente TEXT"
        )
    if "assinatura_entregador" not in col_rom:
        cursor.execute(
            "ALTER TABLE romaneios ADD COLUMN assinatura_entregador TEXT"
        )

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
# 5. TELA DE LOGIN
# ---------------------------------------------------------
if st.session_state["usuario_logado"] is None:
    logo_login_display = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio", "logo", "Tela de login", "tela_de_login"]:
            if os.path.exists(f"{prefixo}.{ext}"):
                logo_login_display = f"{prefixo}.{ext}"
                break
        if logo_login_display:
            break

    col_l1, col_l2, col_l3 = st.columns([0.5, 3, 0.5])
    with col_l2:
        if logo_login_display:
            col_logo, col_texto = st.columns([1, 2.5])
            with col_logo:
                st.image(logo_login_display, use_container_width=True)
            with col_texto:
                st.title("Supermercado Super Nova Cidade")
                st.subheader("Sistema de Recebimento Hortifrúti")
        else:
            st.title("Supermercado Super Nova Cidade")
            st.subheader("Sistema de Recebimento Hortifrúti")

        st.write("")

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
                    st.success(f"Bem-vindo, {usuario[1]}!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

else:
    user_info = st.session_state["usuario_logado"]

    logo_sidebar_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio", "logo", "Tela de login", "tela_de_login"]:
            if os.path.exists(f"{prefixo}.{ext}"):
                logo_sidebar_path = f"{prefixo}.{ext}"
                break
        if logo_sidebar_path:
            break

    if logo_sidebar_path:
        st.sidebar.image(logo_sidebar_path, use_container_width=True)

    st.sidebar.markdown(f"**Usuário:** {user_info['nome']}")

    # Verificação estrita do perfil cadastrado no banco de dados (Gestor vs Conferente)
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

    if eh_gestor or is_admin:
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        total_romaneios_db = pd.read_sql_query(
            "SELECT COUNT(*) as qtd FROM romaneios", conn
        ).iloc[0]["qtd"]
        conn.close()

        st.sidebar.divider()
        st.sidebar.markdown(
            f"🔔 **Painel de Alertas (Gestor):**<br>📦 Romaneios Registrados:"
            f" **{total_romaneios_db}**",
            unsafe_allow_html=True,
        )

    if st.sidebar.button("Sair / Logout", type="secondary"):
        st.session_state["usuario_logado"] = None
        st.rerun()

    st.sidebar.divider()

    # O menu de navegação exibe opções restritas para Conferentes e completas para Gestores
    opcoes_menu = ["Novo Romaneio (Recebimento)", "Consultar Romaneios"]
    if eh_gestor or is_admin:
        opcoes_menu.extend([
            "Relatórios & Gráficos",
            "Gerenciar Cadastros (Produtos)",
            "Gerenciar Usuários & Permissões",
        ])

    menu = st.sidebar.radio("Navegação", opcoes_menu)

    # ---------------------------------------------------------
    # 6. MÓDULO 1: NOVO ROMANEIO (BUSCA AMPLIADA)
    # ---------------------------------------------------------
    if menu == "Novo Romaneio (Recebimento)":
        logo_header_path = None
        for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
            for prefixo in [
                "logo_romaneio",
                "logo",
                "Tela de login",
                "tela_de_login",
            ]:
                if os.path.exists(f"{prefixo}.{ext}"):
                    logo_header_path = f"{prefixo}.{ext}"
                    break
            if logo_header_path:
                break

        if logo_header_path:
            col_h1, col_h2 = st.columns([1, 5])
            with col_h1:
                st.image(logo_header_path, width=110)
            with col_h2:
                st.title("Novo Romaneio de Recebimento - Hortifrúti")
        else:
            st.title("Novo Romaneio de Recebimento - Hortifrúti")

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
            nome_p = p[0]
            und_p = p[1] if p[1] else "KG"
            cp_p = (
                str(p[2]).strip()
                if p[2] and str(p[2]).strip() not in ["None", "Nenhum", ""]
                else "S/N"
            )
            cb_p = (
                str(p[3]).strip()
                if p[3] and str(p[3]).strip() not in ["None", "Nenhum", ""]
                else "S/N"
            )

            label = f"{nome_p} | Cód. Int: {cp_p} | Barras: {cb_p}"
            prod_dict[label] = (nome_p, und_p)

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
                        "LOJA 06 OSWALDO FROTA",
                        "LOJA 07 MOSAICO",
                    ],
                    index=1,
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
                    st.date_input(
                        "Data para Pagamento", None, format="DD/MM/YYYY"
                    )
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
                "Produto (Pesquise por Nome, Cód. Interno ou Barras)",
                (
                    prod_nomes_keys
                    if prod_dict
                    else ["Nenhum produto cadastrado no sistema"]
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
            qtd_input = st.number_input(
                "Qtd / Peso", min_value=0.0, step=0.1, format="%.3f"
            )
        with col_p4:
            val_unit = st.number_input(
                "Valor Unit. (R$)", min_value=0.0, step=0.01, format="%.2f"
            )
        with col_p5:
            st.write("")
            st.write("")
            if st.button("➕ Add", type="primary"):
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
                    st.warning("A quantidade/peso deve ser maior que zero.")

        if st.session_state["itens_romaneio"]:
            df_itens = pd.DataFrame(st.session_state["itens_romaneio"])
            st.dataframe(df_itens, width="stretch")

            total_geral = df_itens["valor_total"].sum()
            st.markdown(f"### **Total Geral: R$ {total_geral:,.2f}**")

            if st.button("🗑️ Limpar Itens", type="secondary"):
                st.session_state["itens_romaneio"] = []
                st.rerun()

        st.subheader("3. Anexo de Fotos / Comprovantes")
        fotos_upload = st.file_uploader(
            "Anexar fotos da Nota / Canhoto / Mercadoria",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
        )

        st.subheader("4. Assinatura Digital na Tela (Touch / Celular)")
        st.info(
            "💡 Dica: Assine com o dedo ou caneta na tela. Se errar, utilize o"
            " botão de limpar abaixo."
        )

        col_ass1, col_ass2 = st.columns(2)

        with col_ass1:
            st.write("**Assinatura do Conferente**")
            if "conf_key" not in st.session_state:
                st.session_state["conf_key"] = 0

            canvas_conf = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=3,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=140,
                width=300,
                drawing_mode="freedraw",
                key=f"canvas_conferente_{st.session_state['conf_key']}",
            )
            if st.button("🔄 Limpar Assinatura Conferente"):
                st.session_state["conf_key"] += 1
                st.rerun()

        with col_ass2:
            st.write("**Assinatura do Entregador / Fornecedor**")
            if "ent_key" not in st.session_state:
                st.session_state["ent_key"] = 0

            canvas_ent = st_canvas(
                fill_color="rgba(255, 255, 255, 0)",
                stroke_width=3,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=140,
                width=300,
                drawing_mode="freedraw",
                key=f"canvas_entregador_{st.session_state['ent_key']}",
            )
            if st.button("🔄 Limpar Assinatura Entregador"):
                st.session_state["ent_key"] += 1
                st.rerun()

        st.write("")
        if st.button("✅ Finalizar e Salvar Romaneio", type="primary"):
            if not num_romaneio.strip():
                st.error("O número do romaneio é obrigatório.")
            elif not fornecedor.strip():
                st.error("O fornecedor é obrigatório.")
            elif not st.session_state["itens_romaneio"]:
                st.error("Adicione pelo menos um item ao romaneio.")
            elif not fotos_upload:
                st.error(
                    "É obrigatório anexar pelo menos uma foto da nota/canhoto."
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

                caminho_ass_conf = None
                if (
                    canvas_conf.image_data is not None
                    and canvas_conf.image_data.sum() > 0
                ):
                    img_conf = Image.fromarray(
                        canvas_conf.image_data.astype("uint8")
                    )
                    caminho_ass_conf = os.path.join(
                        "uploads", f"ass_conf_{num_romaneio}.png"
                    )
                    img_conf.save(caminho_ass_conf)

                caminho_ass_ent = None
                if (
                    canvas_ent.image_data is not None
                    and canvas_ent.image_data.sum() > 0
                ):
                    img_ent = Image.fromarray(
                        canvas_ent.image_data.astype("uint8")
                    )
                    caminho_ass_ent = os.path.join(
                        "uploads", f"ass_ent_{num_romaneio}.png"
                    )
                    img_ent.save(caminho_ass_ent)

                conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute(
                    """
                        INSERT INTO romaneios (numero_romaneio, loja, data_recebimento, fornecedor, codigo_fornecedor, telefone_fornecedor, conferente, pagamento_a_vista, data_pagamento, caminho_foto, assinatura_conferente, assinatura_entregador)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        caminho_ass_conf,
                        caminho_ass_ent,
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
                    num_romaneio,
                    loja,
                    fornecedor,
                    total_romaneio_valor,
                    conferente,
                )

                st.success(
                    f"Romaneio {num_romaneio} salvo e notificação enviada com"
                    " sucesso!"
                )
                st.session_state["itens_romaneio"] = []

    # ---------------------------------------------------------
    # 7. MÓDULO 2: CONSULTAR E IMPRIMIR ROMANEIOS
    # ---------------------------------------------------------
    elif menu == "Consultar Romaneios":
        st.title("🔍 Consulta, Impressão e PDF de Romaneios")

        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_romaneios = pd.read_sql_query(
            "SELECT * FROM romaneios ORDER BY id DESC", conn
        )
        conn.close()

        if not df_romaneios.empty:
            st.dataframe(df_romaneios, width="stretch")

            romaneio_sel = st.selectbox(
                "Selecione o Romaneio para Visualizar / Imprimir",
                df_romaneios["numero_romaneio"].tolist(),
            )
            if romaneio_sel:
                conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, numero_romaneio, loja, data_recebimento,"
                    " fornecedor, codigo_fornecedor, telefone_fornecedor,"
                    " conferente, pagamento_a_vista, data_pagamento,"
                    " caminho_foto, assinatura_conferente,"
                    " assinatura_entregador FROM romaneios WHERE"
                    " numero_romaneio = ?",
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
                        f"📄 Visualização Oficial - Romaneio: {cabecalho[1]}"
                    )

                    texto_detalhes = (
                        "**SUPERMERCADO SUPER NOVA CIDADE**<br>"
                        f"**Loja:** {cabecalho[2]} | **Data:**"
                        f" {cabecalho[3]}<br>**Fornecedor:** {cabecalho[4]} (Cód:"
                        f" {cabecalho[5]} | Tel: {cabecalho[6]})<br>**Conferente:**"
                        f" {cabecalho[7]}<br>**Pagamento à Vista:**"
                        f" {cabecalho[8]}"
                    )
                    if cabecalho[8] == "Não":
                        texto_detalhes += f" | Data Pgto: {cabecalho[9]}"

                    st.markdown(texto_detalhes, unsafe_allow_html=True)

                    st.write("### Itens Conferidos")
                    st.dataframe(df_det, width="stretch")

                    total_geral = (
                        df_det["valor_total"].sum() if not df_det.empty else 0.0
                    )
                    st.markdown(
                        f"### **Total Geral: R$ {total_geral:,.2f}**"
                    )

                    if cabecalho[10]:
                        caminhos_fotos = cabecalho[10].split(",")
                        st.write("### Comprovantes / Fotos Anexadas")
                        cols_img = st.columns(len(caminhos_fotos))
                        for idx, c_foto in enumerate(caminhos_fotos):
                            if os.path.exists(c_foto):
                                with cols_img[idx]:
                                    st.image(
                                        c_foto,
                                        caption=f"Foto {idx+1}",
                                        use_column_width=True,
                                    )

                    pdf_bytes = gerar_pdf_romaneio(
                        cabecalho, df_det, cabecalho[11], cabecalho[12]
                    )
                    st.download_button(
                        label=(
                            "📄 Baixar Romaneio em PDF (Pronto para Impressão)"
                        ),
                        data=pdf_bytes,
                        file_name=f"{romaneio_sel}.pdf",
                        mime="application/pdf",
                        type="primary",
                    )

                    if eh_gestor or is_admin:
                        st.write("")
                        if st.button(
                            f"🗑️ Excluir Romaneio {romaneio_sel} (Apenas"
                            " Gestor)",
                            type="secondary",
                        ):
                            conn = sqlite3.connect(
                                "romaneio_hortifruti.db", timeout=10
                            )
                            cursor = conn.cursor()
                            cursor.execute(
                                "DELETE FROM romaneio_itens WHERE"
                                " romaneio_id = ?",
                                (r_id,),
                            )
                            cursor.execute(
                                "DELETE FROM romaneios WHERE id = ?", (r_id,)
                            )
                            conn.commit()
                            conn.close()
                            st.success(
                                f"Romaneio {romaneio_sel} excluído com sucesso!"
                            )
                            st.rerun()
        else:
            st.info("Nenhum romaneio registrado ainda.")

    # ---------------------------------------------------------
    # 8. MÓDULO 3: RELATÓRIOS & GRÁFICOS (GESTOR)
    # ---------------------------------------------------------
    elif menu == "Relatórios & Gráficos" and (eh_gestor or is_admin):
        st.title("📊 Relatórios de Recebimentos e Análise Gráfica")

        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        query_geral = """
            SELECT r.numero_romaneio, r.loja, r.data_recebimento, r.fornecedor, r.conferente,
                   i.produto, i.quantidade, i.unidade, i.valor_unitario, i.valor_total
            FROM romaneios r
            JOIN romaneio_itens i ON r.id = i.romaneio_id
        """
        df_rel = pd.read_sql_query(query_geral, conn)
        conn.close()

        if not df_rel.empty:
            st.dataframe(df_rel, width="stretch")

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                st.subheader("Gastos por Loja")
                df_loja = df_rel.groupby("loja")["valor_total"].sum()
                st.bar_chart(df_loja)

            with col_r2:
                st.subheader("Top Fornecedores por Volume Financeiro")
                df_forn = df_rel.groupby("fornecedor")["valor_total"].sum()
                st.bar_chart(df_forn)
        else:
            st.info("Não há dados suficientes para gerar relatórios.")

    # ---------------------------------------------------------
    # 9. MÓDULO 4: GERENCIAR CADASTROS DE PRODUTOS (GESTOR)
    # ---------------------------------------------------------
    elif menu == "Gerenciar Cadastros (Produtos)" and (eh_gestor or is_admin):
        st.title("🥦 Gerenciamento de Produtos Hortifrúti")

        with st.form("form_cad_produto"):
            col_cp1, col_cp2 = st.columns(2)
            with col_cp1:
                nome_prod = st.text_input("Nome do Produto (Ex: Tomate Ítalo)")
                cod_prod = st.text_input("Código Interno (Opcional)")
            with col_cp2:
                cod_bar = st.text_input("Código de Barras (Opcional)")
                und_cad = st.selectbox(
                    "Unidade Padrão", ["KG", "UNID", "GRM", "CX"]
                )

            btn_salvar_prod = st.form_submit_button(
                "Cadastrar Produto", type="primary"
            )
            if btn_salvar_prod:
                if nome_prod.strip():
                    try:
                        conn = sqlite3.connect(
                            "romaneio_hortifruti.db", timeout=10
                        )
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO produtos (codigo_barras, codigo_produto,"
                            " nome, unidade_padrao) VALUES (?, ?, ?, ?)",
                            (
                                cod_bar.strip() if cod_bar else None,
                                cod_prod.strip() if cod_prod else None,
                                nome_prod.strip(),
                                und_cad,
                            ),
                        )
                        conn.commit()
                        conn.close()
                        st.success(
                            f"Produto '{nome_prod}' cadastrado com sucesso!"
                        )
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(
                            "Erro: Já existe um produto com este nome ou código."
                        )
                else:
                    st.warning("O nome do produto é obrigatório.")

        st.subheader("Produtos Cadastrados")
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_produtos = pd.read_sql_query(
            "SELECT id, codigo_produto, codigo_barras, nome, unidade_padrao FROM"
            " produtos ORDER BY nome",
            conn,
        )
        conn.close()

        if not df_produtos.empty:
            st.dataframe(df_produtos, width="stretch")

            prod_para_excluir = st.selectbox(
                "Selecionar Produto para Excluir",
                df_produtos["nome"].tolist(),
            )
            if st.button("Excluir Produto Selecionado", type="secondary"):
                conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM produtos WHERE nome = ?", (prod_para_excluir,)
                )
                conn.commit()
                conn.close()
                st.success(f"Produto '{prod_para_excluir}' excluído com sucesso!")
                st.rerun()

    # ---------------------------------------------------------
    # 10. MÓDULO 5: GERENCIAR USUÁRIOS & PERMISSÕES (GESTOR)
    # ---------------------------------------------------------
    elif menu == "Gerenciar Usuários & Permissões" and (eh_gestor or is_admin):
        st.title("👥 Gerenciamento de Usuários e Permissões")

        with st.form("form_novo_usuario"):
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                nome_novo = st.text_input("Nome Completo")
                login_novo = st.text_input("Login de Acesso")
            with col_u2:
                senha_nova = st.text_input("Senha", type="password")
                perfil_novo = st.selectbox("Perfil", ["Conferente", "Gestor"])

            btn_cad_usr = st.form_submit_button(
                "Criar Novo Usuário", type="primary"
            )
            if btn_cad_usr:
                if nome_novo.strip() and login_novo.strip() and senha_nova:
                    try:
                        conn = sqlite3.connect(
                            "romaneio_hortifruti.db", timeout=10
                        )
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO usuarios (nome, login, senha, perfil)"
                            " VALUES (?, ?, ?, ?)",
                            (
                                nome_novo.strip(),
                                login_novo.strip(),
                                senha_nova,
                                perfil_novo,
                            ),
                        )
                        conn.commit()
                        conn.close()
                        st.success(
                            f"Usuário '{nome_novo}' criado com sucesso!"
                        )
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Erro: Este login já está em uso.")
                else:
                    st.warning("Preencha todos os campos obrigatórios.")

        st.subheader("Usuários do Sistema")
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_usr = pd.read_sql_query(
            "SELECT id, nome, login, perfil FROM usuarios", conn
        )
        conn.close()
        st.dataframe(df_usr, width="stretch")
