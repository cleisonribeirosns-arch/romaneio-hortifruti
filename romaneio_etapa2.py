import base64
from datetime import date
import os
import sqlite3
import streamlit as st

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
logo_icon = None
for nome in [
    "logo_romaneio.png.jpg",
    "logo_romaneio.png",
    "logo.png",
]:
    if os.path.exists(nome):
        logo_icon = nome
        break

st.set_page_config(
    page_title="Supermercado Super Nova Cidade - Recebimento Hortifrúti",
    page_icon=logo_icon if logo_icon else "🥦",
    layout="wide",
    initial_sidebar_state="collapsed",
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

    @media (max-width: 768px) {{
        img[data-testid="stImage"] {{
            max-width: 65px !important;
        }}
        .titulo-logo {{
            font-size: 1.8rem !important;
        }}
        .palavra-sup-mercado {{
            font-size: 1.05rem !important;
        }}
        .palavra-cidade {{
            font-size: 2.3rem !important;
        }}
        .stApp h3 {{
            font-size: 1.1rem !important;
        }}
    }}

    {css_fundo}
    </style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# 3. BANCO DE DADOS (INICIALIZAÇÃO COMPLETA)
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
    cursor = conn.cursor()

    # Tabela de Usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            login TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            perfil TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT * FROM usuarios WHERE login = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (nome, login, senha, perfil) VALUES ('Administrador', 'admin', '1234', 'Gestor')"
        )

    # Tabela de Romaneios (Cabeçalho)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS romaneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_romaneio TEXT NOT NULL,
            fornecedor TEXT NOT NULL,
            data_recebimento TEXT NOT NULL,
            conferente TEXT NOT NULL,
            observacoes TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de Itens do Romaneio
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_romaneio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            romaneio_id INTEGER,
            produto TEXT NOT NULL,
            quantidade REAL NOT NULL,
            unidade TEXT NOT NULL,
            FOREIGN KEY (romaneio_id) REFERENCES romaneios (id)
        )
    """)

    conn.commit()
    conn.close()


init_db()


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


if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None


# ---------------------------------------------------------
# 4. CONTROLE DE FLUXO (LOGIN vs SISTEMA)
# ---------------------------------------------------------
if st.session_state["usuario_logado"] is None:
    # --- TELA DE LOGIN ---
    logo_display = None
    for nome in ["logo_romaneio.png.jpg", "logo_romaneio.png", "logo.png"]:
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
                    "<div class='titulo-logo'>"
                    "<span class='palavra-sup-mercado'>Supermercado</span><br>"
                    "<span class='palavra-super'>SUPER</span> "
                    "<span class='palavra-nova'>NOVA</span><br>"
                    "<span class='palavra-cidade'>Cidade</span>"
                    "</div>",
                    unsafe_allow_html=True
                )
                st.markdown("<h3>Sistema de Recebimento Hortifrúti</h3>", unsafe_allow_html=True)
        else:
            st.markdown(
                "<div class='titulo-logo'>"
                "<span class='palavra-sup-mercado'>Supermercado</span><br>"
                "<span class='palavra-super'>SUPER</span> "
                "<span class='palavra-nova'>NOVA</span><br>"
                "<span class='palavra-cidade'>Cidade</span>"
                "</div>",
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
    # --- ÁREA INTERNA DO SISTEMA (PÓS-LOGIN) ---
    st.sidebar.title("Super Nova Cidade")
    st.sidebar.write(f"**Usuário:** {st.session_state['usuario_logado']['nome']}")
    st.sidebar.write(f"**Perfil:** {st.session_state['usuario_logado']['perfil']}")
    st.sidebar.divider()

    menu = st.sidebar.radio(
        "Navegação",
        ["➕ Novo Romaneio", "📋 Consultar Romaneios", "🚪 Sair do Sistema"]
    )

    if menu == "🚪 Sair do Sistema":
        st.session_state["usuario_logado"] = None
        st.rerun()

    elif menu == "➕ Novo Romaneio":
        st.title("🥦 Cadastro de Romaneio - Hortifrúti")
        st.write("Preencha os dados do fornecedor e lance os itens conferidos.")

        with st.form("form_romaneio"):
            col1, col2, col3 = st.columns(3)
            with col1:
                num_romaneio = st.text_input("Nº do Romaneio / Nota Fiscal")
            with col2:
                fornecedor = st.text_input("Fornecedor / Produtor")
            with col3:
                data_rec = st.date_input("Data de Recebimento", value=date.today())

            obs = st.text_area("Observações (Opcional)")

            st.divider()
            st.subheader("📦 Itens do Romaneio")

            if "itens_temp" not in st.session_state:
                st.session_state["itens_temp"] = []

            c_prod, c_qtd, c_un, c_btn = st.columns([3, 2, 2, 1])
            with c_prod:
                prod_input = st.text_input("Produto", key="input_produto")
            with c_qtd:
                qtd_input = st.number_input("Quantidade", min_value=0.01, step=1.0, key="input_qtd")
            with c_un:
                un_input = st.selectbox("Unidade", ["Kg", "Caixas", "Maços", "Unidades", "Sacos"], key="input_un")
            with c_btn:
                st.write("")
                btn_add = st.form_submit_button("➕ Adicionar")

            if btn_add:
                if prod_input.strip() == "":
                    st.warning("Informe o nome do produto.")
                else:
                    st.session_state["itens_temp"].append({
                        "produto": prod_input,
                        "quantidade": qtd_input,
                        "unidade": un_input
                    })
                    st.success(f"Item '{prod_input}' adicionado com sucesso!")

            if st.session_state["itens_temp"]:
                st.write("### Itens Lançados:")
                for idx, item in enumerate(st.session_state["itens_temp"]):
                    st.write(f"- **{item['produto']}**: {item['quantidade']} {item['unidade']}")
                
                if st.form_submit_button("🗑️ Limpar Todos os Itens"):
                    st.session_state["itens_temp"] = []
                    st.rerun()

            st.divider()
            btn_salvar_romaneio = st.form_submit_button("💾 Salvar Romaneio Completo", type="primary")

            if btn_salvar_romaneio:
                if not num_romaneio or not fornecedor:
                    st.error("Preencha o Número do Romaneio e o Fornecedor.")
                elif not st.session_state["itens_temp"]:
                    st.error("Adicione pelo menos um item ao romaneio.")
                else:
                    try:
                        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                        cursor = conn.cursor()
                        
                        cursor.execute(
                            "INSERT INTO romaneios (numero_romaneio, fornecedor, data_recebimento, conferente, observacoes) VALUES (?, ?, ?, ?, ?)",
                            (num_romaneio, fornecedor, str(data_rec), st.session_state["usuario_logado"]["nome"], obs)
                        )
                        romaneio_id = cursor.lastrowid

                        for item in st.session_state["itens_temp"]:
                            cursor.execute(
                                "INSERT INTO itens_romaneio (romaneio_id, produto, quantidade, unidade) VALUES (?, ?, ?, ?)",
                                (romaneio_id, item["produto"], item["quantidade"], item["unidade"])
                            )

                        conn.commit()
                        conn.close()

                        st.success(f"Romaneio Nº {num_romaneio} salvo com sucesso no banco de dados!")
                        st.session_state["itens_temp"] = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar romaneio: {e}")

    elif menu == "📋 Consultar Romaneios":
        st.title("📋 Romaneios Lançados")
        st.write("Consulta rápida dos romaneios salvos no sistema.")

        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT id, numero_romaneio, fornecedor, data_recebimento, conferente, observacoes FROM romaneios ORDER BY id DESC")
        romaneios = cursor.fetchall()
        conn.close()

        if not romaneios:
            st.info("Nenhum romaneio cadastrado até o momento.")
        else:
            for r in romaneios:
                with st.expander(f"Romaneio Nº: {r[1]} | Fornecedor: {r[2]} | Data: {r[3]}"):
                    st.write(f"**Conferente:** {r[4]}")
                    st.write(f"**Observações:** {r[5] if r[5] else 'Nenhuma'}")
                    st.write("**Itens Conferidos:**")
                    
                    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                    cursor = conn.cursor()
                    cursor.execute("SELECT produto, quantidade, unidade FROM itens_romaneio WHERE romaneio_id = ?", (r[0],))
                    itens = cursor.fetchall()
                    conn.close()

                    for it in itens:
                        st.write(f"- {it[0]}: **{it[1]} {it[2]}**")
