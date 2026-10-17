import base64
from datetime import datetime
import io
import os
import pandas as pd
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
import urllib.parse

# ---------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA E CSS (FUNDO DE LOGIN + OCULTAR TOPO/BOTÕES)
# ---------------------------------------------------------
logo_page_icon = None
for ext in ["png", "jpg", "jpeg"]:
  if os.path.exists(f"logo_romaneio.{ext}"):
    logo_page_icon = f"logo_romaneio.{ext}"
    break
  elif os.path.exists(f"logo.{ext}"):
    logo_page_icon = f"logo.{ext}"
    break

st.set_page_config(
    page_title="Romaneio Hortifruti",
    page_icon=logo_page_icon if logo_page_icon else "🥦",
    layout="wide",
)

# Procura dinamicamente pela imagem de fundo de login na pasta
bg_login_path = None
for nome_possivel in [
    "Tela de login.jpeg",
    "Tela de login.jpg",
    "tela_de_login.jpeg",
    "tela_de_login.jpg",
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
        background-image: linear-gradient(rgba(0,0,0,0.65), rgba(0,0,0,0.65)), url("data:image/jpeg;base64,{encoded_string}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
    }}
  """

st.markdown(
    f"""
    <style>
    /* Oculta totalmente o cabeçalho superior do Streamlit */
    header[data-testid="stHeader"] {{
        display: none !important;
        visibility: hidden !important;
    }}
    
    /* Oculta rodapé padrão */
    footer {{
        visibility: hidden !important;
    }}

    /* Oculta os botões flutuantes e widgets de feedback/deploy do Streamlit Cloud */
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

    {css_fundo}
    </style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# FUNÇÃO DE NOTIFICAÇÃO VIA WHATSAPP (MÚLTIPLOS NÚMEROS)
# FUNÇÃO DE NOTIFICAÇÃO EXCLUSIVA PARA O GRUPO DO WHATSAPP
# ---------------------------------------------------------
def enviar_notificacao_whatsapp(
    num_romaneio, loja, fornecedor, total, conferente
):
  telefones_str = st.session_state.get("zap_telefones", "")
  apikey = st.session_state.get("zap_apikey", "")
  # Pega o ID do grupo configurado na sessão (ex: 559299998888-1612345678@g.us)
  id_grupo = st.session_state.get("zap_id_grupo", "").strip()
  apikey = st.session_state.get("zap_apikey", "").strip()

  if not telefones_str or not apikey:
  if not id_grupo or not apikey:
    return

  # Separa os telefones por vírgula, ponto e vírgula ou espaço
  lista_telefones = [
      t.strip()
      for t in telefones_str.replace(";", ",").replace(" ", ",").split(",")
      if t.strip()
  ]

  texto_msg = (
      f"🚨 *NOVO ROMANEIO HORTIFRÚTI* 🚨\n\n"
      f"• *Romaneio:* {num_romaneio}\n"
@@ -135,13 +129,12 @@
  )

  texto_codificado = urllib.parse.quote(texto_msg)
  url = f"https://api.callmebot.com/whatsapp.php?phone={id_grupo}&text={texto_codificado}&apikey={apikey}"

  for tel in lista_telefones:
    url = f"https://api.callmebot.com/whatsapp.php?phone={tel}&text={texto_codificado}&apikey={apikey}"
    try:
      requests.get(url, timeout=5)
    except Exception:
      pass
  try:
    requests.get(url, timeout=5)
  except Exception:
    pass


# ---------------------------------------------------------
@@ -756,7 +749,7 @@
        conn.commit()
        conn.close()

        # Dispara notificação para todos os telefones cadastrados
        # Dispara notificação exclusivamente para o grupo do WhatsApp
        enviar_notificacao_whatsapp(
            num_romaneio, loja, fornecedor, total_romaneio_valor, conferente
        )
@@ -1002,337 +995,337 @@
      menu == "Gerenciar Cadastros (Produtos)"
      and user_info["perfil"] == "Gestor"
  ):
    st.sidebar.subheader("⚙️ Configurações WhatsApp")
    with st.sidebar.expander("Configurar Alertas WhatsApp"):
      st.session_state["zap_telefones"] = st.text_area(
          "Telefones (separe por vírgula)\nEx: 5592999998888, 5592988887777", 
          value=st.session_state.get("zap_telefones", "")
    st.sidebar.subheader("⚙️ Alerta WhatsApp (Grupo)")
    with st.sidebar.expander("Configurar Grupo 'Logística Hortifruti-Nova Cidade'"):
      st.session_state["zap_id_grupo"] = st.text_input(
          "ID do Grupo (Ex: 559299998888-1612345678@g.us)", 
          value=st.session_state.get("zap_id_grupo", "")
      )
      st.session_state["zap_apikey"] = st.text_input(
          "API Key (CallMeBot)", 
          value=st.session_state.get("zap_apikey", ""), 
          type="password"
      )
      st.success("Configurações salvas em sessão!")
      st.success("Configuração do grupo salva em sessão!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🖼️ Gerenciar Logotipos (PDF)")

    arquivos_logos = [
        f for f in os.listdir() 
        if f.lower().endswith((".png", ".jpg", ".jpeg")) 
        and f not in ["Tela de login.jpeg", "Tela de login.jpg", "tela_de_login.jpeg", "tela_de_login.jpg", "login_bg.jpg", "login_bg.png"]
    ]

    if arquivos_logos:
      st.sidebar.markdown("---")
      st.sidebar.write("**Logotipos Ativos:**")
      for logo_nome in arquivos_logos:
        col_lg1, col_lg2 = st.sidebar.columns([3, 1])
        with col_lg1:
          st.image(logo_nome, caption=logo_nome, width=80)
        with col_lg2:
          if st.button("🗑️", key=f"del_logo_{logo_nome}", help=f"Excluir {logo_nome}"):
            try:
              os.remove(logo_nome)
              st.sidebar.success(f"Logo '{logo_nome}' excluída!")
              st.rerun()
            except Exception as e:
              st.sidebar.error(f"Erro ao excluir: {e}")
      st.sidebar.markdown("---")

    logo_files = st.sidebar.file_uploader(
        "Enviar Nova(s) Logo(s) (PNG/JPG)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="logo_upload",
    )
    if logo_files:
      for logo_file in logo_files:
        with open(logo_file.name, "wb") as f:
          f.write(logo_file.getbuffer())
      st.sidebar.success(
          f"{len(logo_files)} arquivo(s) salvo(s) com sucesso!"
      )
      st.rerun()

    st.title("📦 Cadastro e Gestão de Produtos (Hortifrúti)")

    tab_p1, tab_p2 = st.tabs(
        ["➕ Adicionar Novo Produto", "✏️ Editar ou Excluir Produto"]
    )

    with tab_p1:
      col1, col2 = st.columns(2)
      with col1:
        st.subheader("Adicionar Novo Produto")
        cod_barras = st.text_input("Código de Barras", key="cad_barras")
        cod_prod = st.text_input(
            "Código do Produto (ERP / Interno)", key="cad_cod"
        )
        novo_prod = st.text_input("Nome do Produto", key="cad_nome")
        und_padrao = st.selectbox(
            "Unidade Padrão", ["KG", "UNID", "GRM", "CX"], key="cad_und"
        )
        if st.button("Cadastrar Produto"):
          if novo_prod:
            try:
              conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
              cursor = conn.cursor()
              cursor.execute(
                  "INSERT INTO produtos (codigo_barras, codigo_produto, nome,"
                  " unidade_padrao) VALUES (?, ?, ?, ?)",
                  (cod_barras, cod_prod, novo_prod, und_padrao),
              )
              conn.commit()
              conn.close()
              st.success(f"Produto '{novo_prod}' cadastrado com sucesso!")
              st.rerun()
            except sqlite3.IntegrityError:
              st.error("Produto ou código já cadastrado.")
          else:
            st.warning("Preencha o nome do produto.")

      with col2:
        st.subheader("Produtos Cadastrados")
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_prod = pd.read_sql_query(
            "SELECT id, codigo_barras, codigo_produto, nome, unidade_padrao FROM"
            " produtos ORDER BY nome",
            conn,
        )
        conn.close()

        if not df_prod.empty:
          st.dataframe(df_prod, width="stretch")
        else:
          st.info("Nenhum produto cadastrado no momento.")

    with tab_p2:
      st.subheader("Editar ou Excluir Produto Cadastrado")
      conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
      cursor = conn.cursor()
      cursor.execute(
          "SELECT id, codigo_barras, codigo_produto, nome, unidade_padrao FROM"
          " produtos ORDER BY nome"
      )
      lista_produtos_db = cursor.fetchall()
      conn.close()

      if lista_produtos_db:
        prod_dict_db = {
            f"{p[3]} (Cód: {p[2]} | Barras: {p[1]}) - {p[4]}": p
            for p in lista_produtos_db
        }
        prod_selecionado_label = st.selectbox(
            "Selecione o Produto", list(prod_dict_db.keys())
        )
        prod_dados_sel = prod_dict_db[prod_selecionado_label]

        col_ep1, col_ep2 = st.columns(2)
        with col_ep1:
          edit_barras = st.text_input(
              "Código de Barras",
              value=prod_dados_sel[1] if prod_dados_sel[1] else "",
              key="edit_prod_barras",
          )
          edit_cod = st.text_input(
              "Código do Produto",
              value=prod_dados_sel[2] if prod_dados_sel[2] else "",
              key="edit_prod_cod",
          )
        with col_ep2:
          edit_nome = st.text_input(
              "Nome do Produto",
              value=prod_dados_sel[3],
              key="edit_prod_nome",
          )
          und_list = ["KG", "UNID", "GRM", "CX"]
          idx_und = (
              und_list.index(prod_dados_sel[4])
              if prod_dados_sel[4] in und_list
              else 0
          )
          edit_und = st.selectbox(
              "Unidade Padrão",
              und_list,
              index=idx_und,
              key="edit_prod_und",
          )

        st.write("")
        col_b_p1, col_b_p2 = st.columns([1, 1])
        with col_b_p1:
          if st.button("💾 Salvar Alterações no Produto"):
            if edit_nome:
              try:
                conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE produtos SET codigo_barras = ?, codigo_produto = ?,"
                    " nome = ?, unidade_padrao = ? WHERE id = ?",
                    (
                        edit_barras,
                        edit_cod,
                        edit_nome,
                        edit_und,
                        prod_dados_sel[0],
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Produto atualizado com sucesso!")
                st.rerun()
              except sqlite3.IntegrityError:
                st.error(
                    "Este nome ou código já está em uso por outro produto."
                )
            else:
              st.warning("O nome do produto não pode ficar em branco.")
        with col_b_p2:
          if st.button("🗑️ Excluir Produto", type="secondary"):
            conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM produtos WHERE id = ?", (prod_dados_sel[0],))
            conn.commit()
            conn.close()
            st.success(f"Produto '{prod_dados_sel[3]}' excluído com sucesso!")
            st.rerun()

  # --- MÓDULO 5: GERENCIAR USUÁRIOS (Gestor Apenas) ---
  elif (
      menu == "Gerenciar Usuários & Permissões"
      and user_info["perfil"] == "Gestor"
  ):
    st.title("👥 Controle de Usuários e Permissões")

    tab1, tab2 = st.tabs(
        ["➕ Cadastrar Novo Usuário", "🔑 Alterar Senha / Permissões"]
    )

    with tab1:
      col1, col2 = st.columns(2)
      with col1:
        st.subheader("Cadastrar Novo Usuário")
        nome_user = st.text_input("Nome Completo")
        login_user = st.text_input("Login de Acesso")
        senha_user = st.text_input("Senha", type="password")
        perfil_user = st.selectbox(
            "Perfil de Acesso", ["Operador", "Gestor"]
        )

        if st.button("Salvar Usuário"):
          if nome_user and login_user and senha_user:
            try:
              conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
              cursor = conn.cursor()
              cursor.execute(
                  "INSERT INTO usuarios (nome, login, senha, perfil) VALUES"
                  " (?, ?, ?, ?)",
                  (nome_user, login_user, senha_user, perfil_user),
              )
              conn.commit()
              conn.close()
              st.success(f"Usuário '{login_user}' cadastrado com sucesso!")
              st.rerun()
            except sqlite3.IntegrityError:
              st.error("Login já está em uso por outro usuário.")
          else:
            st.warning("Preencha todos os campos obrigatórios.")

      with col2:
        st.subheader("Usuários Cadastrados")
        conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
        df_users = pd.read_sql_query(
            "SELECT id, nome, login, perfil FROM usuarios", conn
        )
        conn.close()

        if not df_users.empty:
          st.dataframe(df_users, width="stretch")
        else:
          st.info("Nenhum usuário cadastrado.")

    with tab2:
      st.subheader("Editar, Alterar Senha ou Excluir Usuário")
      conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
      cursor = conn.cursor()
      cursor.execute(
          "SELECT id, nome, login, senha, perfil FROM usuarios ORDER BY nome"
      )
      lista_usuarios = cursor.fetchall()
      conn.close()

      if lista_usuarios:
        user_dict = {
            f"{u[1]} ({u[2]}) - {u[4]}": u for u in lista_usuarios
        }
        user_selecionado_label = st.selectbox(
            "Selecione o Usuário", list(user_dict.keys())
        )
        user_dados = user_dict[user_selecionado_label]

        col_e1, col_e2 = st.columns(2)
        with col_e1:
          novo_nome = st.text_input(
              "Nome Completo", value=user_dados[1], key="edit_nome"
          )
          novo_login = st.text_input(
              "Login de Acesso", value=user_dados[2], key="edit_login"
          )
        with col_e2:
          novo_perfil = st.selectbox(
              "Perfil de Acesso",
              ["Operador", "Gestor"],
              index=0 if user_dados[4] == "Operador" else 1,
              key="edit_perfil",
          )
          nova_senha = st.text_input(
              "Nova Senha",
              value=user_dados[3],
              type="password",
              key="edit_senha",
          )

        st.write("")
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
          if st.button("💾 Salvar Alterações"):
            if novo_nome and novo_login and nova_senha:
              try:
                conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE usuarios SET nome = ?, login = ?, senha = ?, perfil"
                    " = ? WHERE id = ?",
                    (
                        novo_nome,
                        novo_login,
                        nova_senha,
                        novo_perfil,
                        user_dados[0],
                    ),
                )
                conn.commit()
                conn.close()
                st.success("Usuário atualizado com sucesso!")
                st.rerun()
              except sqlite3.IntegrityError:
                st.error("Este login já está em uso por outro usuário.")
            else:
              st.warning("Preencha todos os campos obrigatórios.")
        with col_btn2:
          if st.button("🗑️ Excluir Usuário", type="secondary"):
            if user_dados[0] == user_info["id"]:
              st.error(
                  "Você não pode excluir o seu próprio usuário enquanto está"
                  " logado!"
              )
            else:
              conn = sqlite3.connect("romaneio_hortifruti.db", timeout=10)
              cursor = conn.cursor()
              cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_dados[0],))
              conn.commit()
              conn.close()
              st.success(f"Usuário '{user_dados[1]}' excluído com sucesso!")
              st.rerun()
