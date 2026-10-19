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
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# 2. DEFINIÇÃO DA IMAGEM DE FUNDO E ESTILOS CSS (ETAPA 1 - 100% INTACTA)
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS romaneios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_romaneio TEXT NOT NULL,
            fornecedor_nome TEXT NOT NULL,
            codigo_fornecedor TEXT,
            telefone_fornecedor TEXT,
            loja TEXT DEFAULT '6',
            data_recebimento TEXT NOT NULL,
            conferente TEXT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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
# 4. CONTROLE DE FLUXO (LOGIN vs ETAPA 2)
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
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")

else:
    # --- ETAPA 2: ÁREA DO CONFERENTE E GESTÃO DE ROMANEIOS ---
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

        # Geração automática do Número do Romaneio Sequencial
        conn_seq = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        cursor_seq = conn_seq.cursor()
        cursor_seq.execute("SELECT COUNT(*) FROM romaneios")
        total_romaneios = cursor_seq.fetchone()[0]
        conn_seq.close()
        proximo_num = f"{total_romaneios + 1:05d}"

        # Base oficial de produtos CISS / Hortifrúti
        produtos_hortifruti = [
            {"barras": "58063", "codigo": "82405", "nome": "ABACATE AVOCADO KG", "und": "KG"},
            {"barras": "5884", "codigo": "28920", "nome": "ABACATE FORTUNA KG", "und": "KG"},
            {"barras": "17510", "codigo": "48903", "nome": "ABACATE GEADA KG", "und": "KG"},
            {"barras": "2240", "codigo": "165651", "nome": "ABACATE MARGARIDA KG", "und": "KG"},
            {"barras": "9034", "codigo": "163887", "nome": "ABACATE REGIONAL KG", "und": "KG"},
            {"barras": "73677", "codigo": "90217", "nome": "ABACAXI FATIADO KG", "und": "KG"},
            {"barras": "2387", "codigo": "165662", "nome": "ABACAXI KG PERDA", "und": "KG"},
            {"barras": "6156", "codigo": "30531", "nome": "ABACAXI UN", "und": "UN"},
            {"barras": "17503", "codigo": "48887", "nome": "ABOBRINHA CABOTIA KG", "und": "KG"},
            {"barras": "3667", "codigo": "165723", "nome": "ABOBRINHA ITALIANA KG", "und": "KG"},
            {"barras": "2356", "codigo": "165659", "nome": "ABOBRINHA KG", "und": "KG"},
            {"barras": "7898910073589", "codigo": "165340", "nome": "ALFACE AMERICANA", "und": "UN"},
            {"barras": "386296", "codigo": "165339", "nome": "ALFACE ROXA UN", "und": "UN"},
            {"barras": "7898941929398", "codigo": "90270", "nome": "ALFACE VIVA BABY UN", "und": "UN"},
            {"barras": "4275", "codigo": "187484", "nome": "ALHO ROXO KG", "und": "KG"},
            {"barras": "182", "codigo": "131307", "nome": "BANANA NANICA KG", "und": "KG"},
            {"barras": "1038", "codigo": "165575", "nome": "BANANA PACOVAN KG", "und": "KG"},
            {"barras": "2073", "codigo": "165634", "nome": "BANANA PRATA KG", "und": "KG"},
            {"barras": "2219", "codigo": "165648", "nome": "BATATA DOCE BRANCA KG", "und": "KG"},
            {"barras": "5104", "codigo": "28298", "nome": "BATATA DOCE ROXA KG", "und": "KG"},
            {"barras": "2233", "codigo": "163880", "nome": "BATATA PORTUGUESA KG", "und": "KG"},
            {"barras": "2349", "codigo": "165658", "nome": "BERINJELA KG", "und": "KG"},
            {"barras": "2165", "codigo": "165643", "nome": "BETERRABA KG", "und": "KG"},
            {"barras": "4480", "codigo": "165766", "nome": "BROCOLIS NINJA KG", "und": "KG"},
            {"barras": "2691", "codigo": "165686", "nome": "CARA KG", "und": "KG"},
            {"barras": "2028", "codigo": "165629", "nome": "CEBOLA KG", "und": "KG"},
            {"barras": "674", "codigo": "131654", "nome": "CEBOLA ROXA KG", "und": "KG"},
            {"barras": "2226", "codigo": "165649", "nome": "CENOURA KG", "und": "KG"},
            {"barras": "2127", "codigo": "165639", "nome": "CHEIRO VERDE UN", "und": "UN"},
            {"barras": "949", "codigo": "165567", "nome": "CHUCHU KG", "und": "KG"},
            {"barras": "6705", "codigo": "165863", "nome": "COCO SECO UN", "und": "UN"},
            {"barras": "2172", "codigo": "165644", "nome": "COUVE FLOR KG", "und": "KG"},
            {"barras": "2202", "codigo": "165647", "nome": "FEIJAO VERDE UN", "und": "UN"},
            {"barras": "22392", "codigo": "166819", "nome": "GENGIBRE KG", "und": "KG"},
            {"barras": "4268", "codigo": "165758", "nome": "GOIABA KG", "und": "KG"},
            {"barras": "3247", "codigo": "165708", "nome": "HORTELA KG", "und": "KG"},
            {"barras": "4565", "codigo": "137074", "nome": "INHAME KG", "und": "KG"},
            {"barras": "12508", "codigo": "36027", "nome": "JENIPAPO KG", "und": "KG"},
            {"barras": "2196", "codigo": "165646", "nome": "JERIMUM KG", "und": "KG"},
            {"barras": "8747", "codigo": "165943", "nome": "KIWI KG", "und": "KG"},
            {"barras": "9690", "codigo": "35740", "nome": "LARANJA BAHIA KG", "und": "KG"},
            {"barras": "61827", "codigo": "86243", "nome": "LARANJA PAULISTA PCT KG", "und": "KG"},
            {"barras": "2080", "codigo": "165635", "nome": "LARANJA REGIONAL KG", "und": "KG"},
            {"barras": "2059", "codigo": "165632", "nome": "LIMAO KG", "und": "KG"},
            {"barras": "4312", "codigo": "28071", "nome": "MACA KG", "und": "KG"},
            {"barras": "1007", "codigo": "165572", "nome": "MACA RED KG", "und": "KG"},
            {"barras": "2332", "codigo": "165657", "nome": "MACAXEIRA KG", "und": "KG"},
            {"barras": "2363", "codigo": "165660", "nome": "MAMAO KG", "und": "KG"},
            {"barras": "201", "codigo": "178998", "nome": "MANGA TOMMY KG", "und": "KG"},
            {"barras": "2264", "codigo": "165653", "nome": "MARACUJA KG", "und": "KG"},
            {"barras": "2158", "codigo": "165642", "nome": "MAXIXE KG", "und": "KG"},
            {"barras": "75404", "codigo": "24094", "nome": "MELANCIA KG", "und": "KG"},
            {"barras": "2370", "codigo": "165661", "nome": "MELAO COMUM KG", "und": "KG"},
            {"barras": "8686", "codigo": "165939", "nome": "MORANGO BDJ KG", "und": "KG"},
            {"barras": "40141454058", "codigo": "71563", "nome": "OVOS AMAZONAS BRANCO C/30UN", "und": "UN"},
            {"barras": "7898141930071", "codigo": "156390", "nome": "OVOS CARTELA C/30UN BRANCO SAO PEDRO", "und": "UN"},
            {"barras": "2066", "codigo": "165633", "nome": "PEPINO COMUM KG", "und": "KG"},
            {"barras": "4398", "codigo": "28079", "nome": "PERA DANJOU KG", "und": "KG"},
            {"barras": "675369", "codigo": "163735", "nome": "PIMENTA DE CHEIRO KG", "und": "KG"},
            {"barras": "703", "codigo": "165548", "nome": "PIMENTAO COLORIDO KG", "und": "KG"},
            {"barras": "2110", "codigo": "165638", "nome": "PIMENTAO VERDE KG", "und": "KG"},
            {"barras": "2134", "codigo": "165640", "nome": "QUIABO KG", "und": "KG"},
            {"barras": "4459", "codigo": "165764", "nome": "REPOLHO ROXO KG", "und": "KG"},
            {"barras": "2097", "codigo": "165636", "nome": "REPOLHO VERDE KG", "und": "KG"},
            {"barras": "3254", "codigo": "165709", "nome": "RUCULA KG", "und": "KG"},
            {"barras": "9621", "codigo": "165976", "nome": "SALSA KG", "und": "KG"},
            {"barras": "2516", "codigo": "165674", "nome": "TANGERINA IMPORTADA KG", "und": "KG"},
            {"barras": "1175", "codigo": "41418", "nome": "TOMATE KG", "und": "KG"},
        ]

        with st.form("form_romaneio"):
            # Cabeçalho idêntico ao modelo físico
            st.markdown(f"### 🏷️ ROM. **{proximo_num}**")
            
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                fornecedor_nome = st.text_input("Fornecedor / Entregador")
            with c2:
                codigo_fornecedor = st.text_input("Código do Fornecedor")
            with c3:
                telefone_fornecedor = st.text_input("Tel. / Contato")

            c4, c5, c6 = st.columns([2, 1, 1])
            with c4:
                resp_fisico = st.text_input("Resp. Rec. Físico (Conferente)", value=st.session_state["usuario_logado"]["nome"])
            with c5:
                loja = st.text_input("Loja", value="6")
            with c6:
                # Data no formato brasileiro (DD/MM/AAAA)
                data_hoje = date.today().strftime("%d/%m/%Y")
                data_rec = st.text_input("Data do Rec.", value=data_hoje)

            st.divider()
            st.subheader("📦 Adicionar Itens (Pesquisa por Descrição, Cód. Barras ou Interno)")

            if "itens_temp" not in st.session_state:
                st.session_state["itens_temp"] = []

            termo_busca = st.selectbox(
                "Selecione o Produto:",
                options=produtos_hortifruti,
                format_func=lambda p: f"{p['nome']} | Cód: {p['codigo']} | Barras: {p['barras']}"
            )

            col_q, col_b = st.columns([3, 1])
            with col_q:
                qtd_input = st.number_input("Quantidade / Peso Conferido", min_value=0.01, step=1.0, key="input_qtd")
            with col_b:
                st.write("")
                btn_add = st.form_submit_button("➕ Adicionar Item")

            if btn_add:
                if not termo_busca:
                    st.warning("Selecione um produto.")
                else:
                    st.session_state["itens_temp"].append({
                        "produto": termo_busca["nome"],
                        "quantidade": qtd_input,
                        "unidade": termo_busca["und"]
                    })
                    st.success(f"Item '{termo_busca['nome']}' ({qtd_input} {termo_busca['und']}) adicionado!")

            if st.session_state["itens_temp"]:
                st.write("### Itens Lançados no Romaneio:")
                for idx, item in enumerate(st.session_state["itens_temp"]):
                    st.write(f"- **{item['produto']}**: {item['quantidade']} {item['unidade']}")
                
                if st.form_submit_button("🗑️ Limpar Todos os Itens"):
                    st.session_state["itens_temp"] = []
                    st.rerun()

            st.divider()
            
            # Área de Assinaturas Digitais (Touch / Caneta)
            st.subheader("✍️ Assinaturas Digitais")
            st.write("Confirme os nomes para validação do recebimento:")
            
            col_ass1, col_ass2 = st.columns(2)
            with col_ass1:
                st.write("**Assinatura do Entregador / Fornecedor**")
                ass_entregador = st.text_input("Nome / Confirmação do Entregador", placeholder="Nome completo ou rubrica do entregador")
            with col_ass2:
                st.write("**Assinatura do Conferente**")
                ass_conferente = st.text_input("Confirmação do Conferente", value=st.session_state["usuario_logado"]["nome"])

            st.divider()
            btn_salvar_romaneio = st.form_submit_button("💾 Salvar e Finalizar Romaneio", type="primary")

            if btn_salvar_romaneio:
                if not fornecedor_nome:
                    st.error("Preencha o Nome do Fornecedor / Entregador.")
                elif not st.session_state["itens_temp"]:
                    st.error("Adicione pelo menos um item ao romaneio.")
                else:
                    try:
                        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                        cursor = conn.cursor()
                        
                        cursor.execute(
                            "INSERT INTO romaneios (numero_romaneio, fornecedor_nome, codigo_fornecedor, telefone_fornecedor, loja, data_recebimento, conferente) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (proximo_num, fornecedor_nome, codigo_fornecedor, telefone_fornecedor, loja, data_rec, resp_fisico)
                        )
                        romaneio_id = cursor.lastrowid

                        for item in st.session_state["itens_temp"]:
                            cursor.execute(
                                "INSERT INTO itens_romaneio (romaneio_id, produto, quantidade, unidade) VALUES (?, ?, ?, ?)",
                                (romaneio_id, item["produto"], item["quantidade"], item["unidade"])
                            )

                        conn.commit()
                        conn.close()

                        st.success(f"Romaneio Nº {proximo_num} salvo com sucesso no banco de dados!")
                        st.session_state["itens_temp"] = []
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar romaneio: {e}")

    elif menu == "📋 Consultar Romaneios":
        st.title("📋 Romaneios Lançados")
        st.write("Consulta rápida dos romaneios salvos no sistema.")

        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        cursor = conn.cursor()
        cursor.execute("SELECT id, numero_romaneio, fornecedor_nome, codigo_fornecedor, data_recebimento, conferente, loja FROM romaneios ORDER BY id DESC")
        romaneios = cursor.fetchall()
        conn.close()

        if not romaneios:
            st.info("Nenhum romaneio cadastrado até o momento.")
        else:
            for r in romaneios:
                with st.expander(f"Rom. Nº: {r[1]} | Fornecedor: {r[2]} | Data: {r[4]} | Loja: {r[6]}"):
                    st.write(f"**Cód. Fornecedor:** {r[3] if r[3] else 'Não informado'}")
                    st.write(f"**Conferente (Rec. Físico):** {r[5]}")
                    st.write("**Itens Conferidos:**")
                    
                    conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                    cursor = conn.cursor()
                    cursor.execute("SELECT produto, quantidade, unidade FROM itens_romaneio WHERE romaneio_id = ?", (r[0],))
                    itens = cursor.fetchall()
                    conn.close()

                    for it in itens:
                        st.write(f"- {it[0]}: **{it[1]} {it[2]}**")
