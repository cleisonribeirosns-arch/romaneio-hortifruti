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
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO VISUAL
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
    header[data-testid="stHeader"] {{ display: none !important; visibility: hidden !important; }}
    footer {{ visibility: hidden !important; }}
    
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
    }}
    button[kind="secondary"], .stButton > button[kind="secondary"] {{
        background-color: #C62828 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        font-weight: bold !important;
        border-radius: 6px !important;
    }}

    {css_fundo}
    </style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 2. BANCO DE DADOS E INICIALIZAÇÃO
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

    # Garante o usuário Administrador padrão
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
# 3. TELA DE LOGIN
# ---------------------------------------------------------
if st.session_state["usuario_logado"] is None:
    col_l1, col_l2, col_l3 = st.columns([0.5, 3, 0.5])
    with col_l2:
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

    st.sidebar.markdown(f"**Usuário:** {user_info['nome']}")

    # Identificação rigorosa do perfil de Gestor/Admin
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

    # Montagem dinâmica do menu lateral baseada no perfil
    opcoes_menu = ["Novo Romaneio (Recebimento)", "Consultar Romaneios"]
    if eh_gestor:
        opcoes_menu.extend([
            "Relatórios & Gráficos",
            "Gerenciar Cadastros (Produtos)",
            "Gerenciar Usuários & Permissões",
        ])

    menu = st.sidebar.radio("Navegação", opcoes_menu)

    # ---------------------------------------------------------
    # 4. MÓDULOS DO SISTEMA
    # ---------------------------------------------------------
    if menu == "Novo Romaneio (Recebimento)":
        st.title("Novo Romaneio de Recebimento - Hortifrúti")
        st.info(
            "Preencha os dados abaixo para registrar o recebimento dos produtos."
        )

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
                    else ["Cadastre produtos na aba de Gestor"]
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
                    st.warning("Informe uma quantidade maior que zero.")

        if st.session_state["itens_romaneio"]:
            df_itens = pd.DataFrame(st.session_state["itens_romaneio"])
            st.dataframe(df_itens, width="stretch")
            st.markdown(
                f"### **Total Geral: R$"
                f" {df_itens['valor_total'].sum():,.2f}**"
            )
            if st.button("🗑️ Limpar Itens", type="secondary"):
                st.session_state["itens_romaneio"] = []
                st.rerun()

        st.subheader("3. Anexo de Fotos / Comprovantes")
        fotos_upload = st.file_uploader(
            "Fotos da Nota / Canhoto",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
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
                key="canv_conf",
            )
        with col_ass2:
            st.write("**Assinatura Entregador**")
            canvas_ent = st_canvas(
                stroke_width=3,
                stroke_color="#000000",
                background_color="#FFFFFF",
                height=120,
                width=280,
                key="canv_ent",
            )

        if st.button("✅ Salvar Romaneio", type="primary"):
            if not num_romaneio.strip() or not fornecedor.strip():
                st.error("Preencha o número do romaneio e o fornecedor.")
            elif not st.session_state["itens_romaneio"]:
                st.error("Adicione itens ao romaneio.")
            else:
                st.success(
                    f"Romaneio {num_romaneio} processado com sucesso!"
                )
                st.session_state["itens_romaneio"] = []

    elif menu == "Consultar Romaneios":
        st.title("🔍 Consulta de Romaneios")
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_rom = pd.read_sql_query("SELECT * FROM romaneios", conn)
        conn.close()
        if not df_rom.empty:
            st.dataframe(df_rom, width="stretch")
        else:
            st.info("Nenhum romaneio cadastrado.")

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
        st.dataframe(df_u, width="stretch")
