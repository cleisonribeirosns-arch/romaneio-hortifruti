import base64
import os
import sqlite3
import streamlit as st

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA
# ---------------------------------------------------------
# Procura pela logo para o ícone da página
logo_icon = None
for nome in [
    "logo_romaneio.png",
    "logo_romaneio.jpg",
    "logo.png",
    "logo.jpg",
    "logo_romaneio.png.jpg",
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
    "Tela-de-login.jpeg",
    "Tela de login.jpeg",
    "Tela de login.jpg",
    "tela_de_login.jpeg",
    "tela_de_login.jpg",
    "Tela-de-login.jpeg.ico",
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

    /* Estilização dos textos da tela inicial */
    .stApp h1 {{
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important;
        font-weight: 800 !important;
        margin-bottom: 0px !important;
    }}

    .stApp h3 {{
        color: #F57F17 !important;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important;
        font-weight: bold !important;
        margin-top: 5px !important;
    }}

    .stApp label {{
        color: #FFFFFF !important;
        text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.8) !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }}

    /* Campos de Entrada de Texto */
    div[data-baseweb="input"] input {{
        color: #000000 !important;
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 6px !important;
        font-size: 16px !important;
    }}

    /* Botão de Entrar */
    button[kind="primary"], .stButton > button[kind="primary"] {{
        background-color: #1B5E20 !important;
        color: #FFFFFF !important;
        border: 2px solid #FFFFFF !important;
        font-weight: bold !important;
        font-size: 18px !important;
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
# 3. BANCO DE DADOS (INICIALIZAÇÃO)
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
    # Usuário Administrador Padrão
    cursor.execute("SELECT * FROM usuarios WHERE login = 'admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (nome, login, senha, perfil) VALUES ('Administrador', 'admin', '1234', 'Gestor')"
        )
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
# 4. TELA DE LOGIN
# ---------------------------------------------------------
if st.session_state["usuario_logado"] is None:
    # Procura pela imagem do logo
    logo_display = None
    for nome in [
        "logo_romaneio.png.jpg",
        "logo_romaneio.png",
        "logo_romaneio.jpg",
        "logo.png",
        "logo.jpg",
    ]:
        if os.path.exists(nome):
            logo_display = nome
            break

    # Colunas para centralizar a tela de login
    col_vazia_esq, col_central, col_vazia_dir = st.columns([0.5, 3, 0.5])

    with col_central:
        # Lado a lado: Logo da empresa + Título do sistema
        if logo_display:
            col_logo, col_titulo = st.columns([1, 3])
            with col_logo:
                st.image(logo_display, use_container_width=True)
            with col_titulo:
                st.markdown("<h1>Supermercado Super Nova Cidade</h1>", unsafe_allow_html=True)
                st.markdown("<h3>Sistema de Recebimento Hortifrúti</h3>", unsafe_allow_html=True)
        else:
            st.markdown("<h1>Supermercado Super Nova Cidade</h1>", unsafe_allow_html=True)
            st.markdown("<h3>Sistema de Recebimento Hortifrúti</h3>", unsafe_allow_html=True)

        st.write("")

        # Formulario de Acesso
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
    # Estado pós-login para testar a Etapa 1
    st.title("✅ Login Efetuado com Sucesso!")
    st.write(f"**Usuário:** {st.session_state['usuario_logado']['nome']}")
    st.write(f"**Perfil:** {st.session_state['usuario_logado']['perfil']}")

    if st.button("Sair / Logout"):
        st.session_state["usuario_logado"] = None
        st.rerun()
