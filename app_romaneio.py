import base64
from datetime import datetime, time, timedelta
import io
import os
import pandas as pd
from PIL import Image
import plotly.express as px
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
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from supabase import create_client, Client

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E ESTADOS DE TEMA
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

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# Estado Global de Temas
if "tipo_tema" not in st.session_state:
    st.session_state["tipo_tema"] = "Padrão do Aplicativo (Original)"
if "hora_inicio_claro" not in st.session_state:
    st.session_state["hora_inicio_claro"] = time(6, 0)
if "hora_inicio_escuro" not in st.session_state:
    st.session_state["hora_inicio_escuro"] = time(18, 0)
if "nivel_brilho" not in st.session_state:
    st.session_state["nivel_brilho"] = 100

# ---------------------------------------------------------
# CONEXÃO OFICIAL COM O SUPABASE (VIA API REST HTTPS)
# ---------------------------------------------------------
SUPABASE_URL = "https://rdoithfmshzfotgmpya.supabase.co"
SUPABASE_KEY = "sb_publishable_w1Qp4M66fc9-G7QPxUsUQ_hpz8ZhJe"

@st.cache_resource
def init_supabase() -> Client:
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erro ao inicializar o cliente Supabase: {e}")
        st.stop()

supabase = init_supabase()

# ---------------------------------------------------------
# MODAL PARA VISUALIZAÇÃO DA NOTA FISCAL / ANEXO
# ---------------------------------------------------------
@st.dialog("📄 Visualização da Nota Fiscal / Anexo", width="large")
def exibir_foto_modal(caminho_foto):
    if os.path.exists(caminho_foto):
        nome_arquivo = os.path.basename(caminho_foto)
        if caminho_foto.lower().endswith(".pdf"):
            st.info(f"📄 Arquivo PDF disponível: **{nome_arquivo}**")
            with open(caminho_foto, "rb") as f_pdf:
                pdf_bytes = f_pdf.read()
            st.download_button(
                label=f"📥 Baixar e Abrir Arquivo PDF ({nome_arquivo})",
                data=pdf_bytes,
                file_name=nome_arquivo,
                mime="application/pdf",
                type="primary"
            )
        else:
            st.image(caminho_foto, use_container_width=True, caption="Documento / Nota Fiscal Anexada")
            with open(caminho_foto, "rb") as f_img:
                img_bytes = f_img.read()
            st.download_button(
                label=f"📥 Baixar Imagem ({nome_arquivo})",
                data=img_bytes,
                file_name=nome_arquivo,
                mime="application/jpeg",
                type="primary"
            )
    else:
        st.error("Arquivo de anexo não encontrado no servidor.")

# ---------------------------------------------------------
# 2. SELEÇÃO DE TEMA E BRILHO RESPONSIVA
# ---------------------------------------------------------
with st.expander("🎨 Ajustar Tema da Tela e Brilho (Visível para Todos os Aparelhos)", expanded=False):
    col_t1, col_t2 = st.columns([2, 2])
    with col_t1:
        sel_tema = st.selectbox(
            "Modo de Exibição / Tema",
            ["Padrão do Aplicativo (Original)", "Modo Claro", "Modo Escuro", "Personalizado (Horário Automático)"],
            index=["Padrão do Aplicativo (Original)", "Modo Claro", "Modo Escuro", "Personalizado (Horário Automático)"].index(st.session_state["tipo_tema"]),
            key="sel_tema_responsivo"
        )
        if sel_tema != st.session_state["tipo_tema"]:
            st.session_state["tipo_tema"] = sel_tema
            st.rerun()
    with col_t2:
        st.write("☀️ **Nível do Brilho da Tela (%)**")
        slider_brilho = st.slider(
            "Ajuste do Brilho",
            min_value=10,
            max_value=100,
            value=st.session_state["nivel_brilho"],
            step=5,
            label_visibility="collapsed",
            key="slider_brilho_responsivo"
        )
        if slider_brilho != st.session_state["nivel_brilho"]:
            st.session_state["nivel_brilho"] = slider_brilho
            st.rerun()

# ---------------------------------------------------------
# 3. MOTOR DINÂMICO DE TEMAS E ESTILOS
# ---------------------------------------------------------
bg_login_path = None
for nome_bg in [
    "Tela-de-login.jpeg.ico",
    "Tela-de-login.jpeg",
    "Tela de login.jpeg",
    "tela_de_login.jpeg",
]:
    if os.path.exists(nome_bg):
        bg_login_path = nome_bg
        break

b64_img = ""
if bg_login_path:
    with open(bg_login_path, "rb") as img_f:
        b64_img = base64.b64encode(img_f.read()).decode()

fator_brilho = st.session_state["nivel_brilho"] / 100.0
if b64_img:
    css_fundo = f"""
        .stApp {{
            background-image: linear-gradient(rgba(27,94,32,{0.85 * fator_brilho}), rgba(198,40,40,{0.85 * fator_brilho})), url("data:image/jpeg;base64,{b64_img}") !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}
    """
else:
    css_fundo = f"""
        .stApp {{
            background: linear-gradient(135deg, rgba(27,94,32,{fator_brilho}) 0%, rgba(46,125,50,{fator_brilho}) 50%, rgba(198,40,40,{fator_brilho}) 100%) !important;
            background-attachment: fixed !important;
        }}
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
    .titulo-logo {{
        font-size: 2.2rem !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
        margin-bottom: 0px !important;
        font-family: 'Arial Black', Gadget, sans-serif !important;
    }}
    .palavra-sup-mercado {{
        color: #2E7D32 !important;
        font-size: 1.2rem !important;
        font-weight: 800 !important;
        font-style: italic !important;
    }}
    .palavra-super {{
        color: #2E7D32 !important;
        font-style: italic !important;
    }}
    .palavra-nova {{
        color: #FF3D00 !important;
        font-style: italic !important;
    }}
    .palavra-cidade {{
        color: #111111 !important;
        font-style: italic !important;
        font-family: 'Brush Script MT', cursive, sans-serif !important;
        font-size: 2.8rem !important;
    }}
    button[kind="primary"], .stButton > button[kind="primary"] {{
        background-color: #1B5E20 !important;
        color: #FFFFFF !important;
        border: 2px solid #FFFFFF !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        width: 100% !important;
    }}
    {css_fundo}
    </style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# 4. INICIALIZAÇÃO E VERIFICAÇÃO DE USUÁRIO ADMINISTRADOR
# ---------------------------------------------------------
def verificar_admin_padrao():
    try:
        res = supabase.table("usuarios").select("*").eq("login", "908").execute()
        if not res.data:
            supabase.table("usuarios").insert({
                "nome": "Administrador",
                "login": "908",
                "senha": "0332",
                "perfil": "Gestor"
            }).execute()
    except Exception:
        pass

verificar_admin_padrao()

if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None

def fazer_login(login_ou_nome, senha):
    try:
        res = supabase.table("usuarios").select("*").eq("login", login_ou_nome.strip()).eq("senha", senha).execute()
        if res.data:
            return res.data[0]
        res_nome = supabase.table("usuarios").select("*").eq("senha", senha).execute()
        for u in res_nome.data:
            if u["nome"].lower() == login_ou_nome.strip().lower():
                return u
    except Exception as e:
        st.error(f"Erro ao autenticar: {e}")
    return None

def fmt_ptbr(val, decimais=2):
    try:
        f = float(val)
        s = f"{f:,.3f}" if decimais == 3 else f"{f:,.2f}"
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00"

def remover_fundo_branco(caminho_imagem):
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
# GERADORES DE PDF
# ---------------------------------------------------------
def gerar_pdf_romaneio(romaneio_data, itens_data, path_conf=None, path_ent=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    style_left = ParagraphStyle('Left', parent=styles['Normal'], alignment=0, fontName='Helvetica', fontSize=9)
    style_center = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, fontName='Helvetica', fontSize=9)
    style_header_left = ParagraphStyle('HLeft', parent=styles['Normal'], alignment=0, fontName='Helvetica-Bold', fontSize=9, textColor=colors.whitesmoke)
    style_header_center = ParagraphStyle('HCenter', parent=styles['Normal'], alignment=1, fontName='Helvetica-Bold', fontSize=9, textColor=colors.whitesmoke)
    
    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio.png", "logo_romaneio", "logo", "Tela de login"]:
            pos_p = f"{prefixo}.{ext}" if not prefixo.endswith(f".{ext}") else prefixo
            if os.path.exists(pos_p):
                logo_path = pos_p
                break
        if logo_path: break

    def add_watermark(canvas_obj, doc_obj):
        if logo_path and os.path.exists(logo_path):
            canvas_obj.saveState()
            try:
                canvas_obj.setFillAlpha(0.12)
                canvas_obj.drawImage(logo_path, letter[0] / 2 - 140, letter[1] / 2 + 30, width=280, height=280, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
            canvas_obj.restoreState()

    logo_img_header = RLImage(logo_path, width=70, height=50) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
    tipo_op_pdf = romaneio_data.get('tipo_operacao', 'Compra')
    
    header_table = Table([[logo_img_header, Paragraph(f"<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>Romaneio de Recebimento - Hortifrúti ({tipo_op_pdf.upper()})", styles["Normal"]), Paragraph(f"<b>ROM:</b> {romaneio_data['numero_romaneio']}<br/><b>Data:</b> {romaneio_data['data_recebimento']}", styles["Normal"])]], colWidths=[80, 300, 160])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey)]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    info_data = [
        [Paragraph(f"<b>Tipo de Operação:</b> {tipo_op_pdf}", styles["Normal"]), Paragraph(f"<b>Fornecedor:</b> {romaneio_data.get('fornecedor','')}", styles["Normal"])],
        [Paragraph(f"<b>Cód. Fornecedor:</b> {romaneio_data.get('codigo_fornecedor','')}", styles["Normal"]), Paragraph(f"<b>Telefone:</b> {romaneio_data.get('telefone_fornecedor','')}", styles["Normal"])],
        [Paragraph(f"<b>Loja:</b> {romaneio_data.get('loja','')}", styles["Normal"]), Paragraph(f"<b>Conferente:</b> {romaneio_data.get('conferente','')}", styles["Normal"])],
    ]
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke)]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    table_content = [[Paragraph("Item", style_header_center), Paragraph("Descrição do Produto", style_header_left), Paragraph("Qtd / Peso", style_header_center), Paragraph("UND", style_header_center), Paragraph("Vl. Unit", style_header_left), Paragraph("Total", style_header_left)]]
    
    total_geral = 0.0
    for idx, item in enumerate(itens_data, 1):
        v_unit = float(item.get('valor_unitario', 0.0) or 0.0)
        v_tot = float(item.get('valor_total', 0.0) or 0.0)
        qtd_val = float(item.get('quantidade', 0.0) or 0.0)
        total_geral += v_tot
        
        table_content.append([Paragraph(str(idx), style_center), Paragraph(str(item.get('produto', '')), style_left), Paragraph(fmt_ptbr(qtd_val, 3), style_center), Paragraph(str(item.get('unidade', '')), style_center), Paragraph(f"R$ {fmt_ptbr(v_unit, 2)}", style_left), Paragraph(f"R$ {fmt_ptbr(v_tot, 2)}", style_left)])
        
    itens_table = Table(table_content, colWidths=[35, 215, 75, 50, 75, 90])
    itens_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(itens_table)
    story.append(Spacer(1, 8))

    total_table = Table([[f"TOTAL GERAL DO ROMANEIO: R$ {fmt_ptbr(total_geral, 2)}"]], colWidths=[540])
    total_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#C62828")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.whitesmoke), ("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 10)]))
    story.append(total_table)
    doc.build(story, onFirstPage=add_watermark, onLaterPages=add_watermark)
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
    
    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio.png", "logo_romaneio", "logo", "Tela de login"]:
            pos_p = f"{prefixo}.{ext}" if not prefixo.endswith(f".{ext}") else prefixo
            if os.path.exists(pos_p):
                logo_path = pos_p
                break
        if logo_path: break

    logo_img_header = RLImage(logo_path, width=70, height=50) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
    header_table = Table([[logo_img_header, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>Relatório de Produtos Cadastrados - Hortifrúti", styles["Normal"]), Paragraph(f"<b>Data:</b> {datetime.now().strftime('%d/%m/%Y')}<br/><b>Total:</b> {len(produtos_data)}", styles["Normal"])]], colWidths=[80, 310, 150])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey)]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    table_content = [[Paragraph("Item", style_header_center), Paragraph("Cód. Produto", style_header_center), Paragraph("Código de Barras", style_header_center), Paragraph("Nome do Produto", style_header_left), Paragraph("UND", style_header_center)]]
    for idx, p in enumerate(produtos_data, 1):
        table_content.append([Paragraph(str(idx), style_center), Paragraph(str(p.get('codigo_produto') or "S/N"), style_center), Paragraph(str(p.get('codigo_barras') or "S/N"), style_center), Paragraph(str(p.get('nome', '')), style_left), Paragraph(str(p.get('unidade_padrao', '')), style_center)])
        
    prod_table = Table(table_content, colWidths=[35, 95, 125, 235, 50])
    prod_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(prod_table)
    doc.build(story)
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
    
    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio.png", "logo_romaneio", "logo", "Tela de login"]:
            pos_p = f"{prefixo}.{ext}" if not prefixo.endswith(f".{ext}") else prefixo
            if os.path.exists(pos_p):
                logo_path = pos_p
                break
        if logo_path: break

    logo_img_header = RLImage(logo_path, width=70, height=50) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
    header_table = Table([[logo_img_header, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>Relatório de Controle de Bonificação Hortifrúti", styles["Normal"]), Paragraph(f"<b>Data Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/><b>Total Registros:</b> {len(df_bonf_data)}", styles["Normal"])]], colWidths=[80, 310, 150])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, -1), colors.lightgrey)]))
    story.append(header_table)
    story.append(Spacer(1, 15))
    
    table_content = [[Paragraph("N° Nota", style_header_center), Paragraph("Tipo", style_header_center), Paragraph("Loja", style_header_center), Paragraph("Data Entrada", style_header_center), Paragraph("Valor (R$)", style_header_left), Paragraph("Status", style_header_center), Paragraph("Produto Hortifrúti", style_header_left)]]
    
    tot_val = 0.0
    for _, r in df_bonf_data.iterrows():
        v_b = float(r.get("valor_bonificacao", 0.0) or 0.0)
        tot_val += v_b
        t_bonf = r.get("tipo_bonificacao", "Bonificação")
        table_content.append([Paragraph(str(r.get("numero_nota", "")), style_center), Paragraph(str(t_bonf), style_center), Paragraph(str(r.get("loja", "")), style_center), Paragraph(str(r.get("data_entrada", "")), style_center), Paragraph(f"R$ {fmt_ptbr(v_b, 2)}", style_left), Paragraph(str(r.get("status", "")), style_center), Paragraph(str(r.get("produto_hortifruti", "")), style_left)])
        
    bonf_table = Table(table_content, colWidths=[55, 65, 65, 85, 70, 80, 120])
    bonf_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(bonf_table)
    story.append(Spacer(1, 10))
    
    total_table = Table([[f"VALOR TOTAL BONIFICADO / TRANSFERIDO: R$ {fmt_ptbr(tot_val, 2)}"]], colWidths=[540])
    total_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#C62828")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.whitesmoke), ("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(total_table)
    doc.build(story)
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
    
    logo_path = None
    for ext in ["png", "jpg", "jpeg", "PNG", "JPG", "JPEG"]:
        for prefixo in ["logo_romaneio.png", "logo_romaneio", "logo", "Tela de login"]:
            pos_p = f"{prefixo}.{ext}" if not prefixo.endswith(f".{ext}") else prefixo
            if os.path.exists(pos_p):
                logo_path = pos_p
                break
        if logo_path: break

    logo_img_header = RLImage(logo_path, width=70, height=45) if logo_path and os.path.exists(logo_path) else Paragraph("<b>SUPERNOVA<br/>CIDADE</b>", styles["Normal"])
    header_table = Table([[logo_img_header, Paragraph("<b>SUPERMERCADO SUPERNOVA CIDADE</b><br/>Registro de Baixas de Avarias - Hortifrúti", styles["Normal"]), Paragraph(f"<b>Data Emissão:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/><b>Total Registros:</b> {len(df_baixas_data)}", styles["Normal"])]], colWidths=[80, 520, 192])
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
        Paragraph("Saldo Total disponível", style_header_left)
    ]]
    
    tot_val_avarias = 0.0
    for _, r in df_baixas_data.iterrows():
        v_av = float(r.get("valor_total_avaria", 0.0) or 0.0)
        tot_val_avarias += v_av
        s_nota = float(r.get("saldo_restante_nota", 0.0) or 0.0)
        s_disp = float(r.get("saldo_total_disponivel", 0.0) or 0.0)
        qtd_val = float(r.get("quantidade_kg_cx", 0.0) or 0.0)
        
        table_content.append([
            Paragraph(str(r.get("loja_baixa", "")), style_center),
            Paragraph(str(r.get("data_baixa", "")), style_center),
            Paragraph(str(r.get("ref_bon_transferen", "")), style_center),
            Paragraph(str("S/Anexo"), style_center),
            Paragraph(str(r.get("nf_b_entrada", "")), style_center),
            Paragraph(str(r.get("produto_hortifruti", "")), style_left),
            Paragraph(fmt_ptbr(qtd_val, 3), style_center),
            Paragraph(f"R$ {fmt_ptbr(v_av, 2)}", style_left),
            Paragraph(f"R$ {fmt_ptbr(s_nota, 2)}", style_left),
            Paragraph(f"R$ {fmt_ptbr(s_disp, 2)}", style_left),
        ])
        
    baixas_table = Table(table_content, colWidths=[70, 95, 85, 75, 85, 120, 60, 85, 65, 52])
    baixas_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B5E20")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
    story.append(baixas_table)
    story.append(Spacer(1, 10))
    
    total_table = Table([[f"VALOR TOTAL DAS AVARIAS: R$ {fmt_ptbr(tot_val_avarias, 2)}"]], colWidths=[792])
    total_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#C62828")), ("TEXTCOLOR", (0, 0), (-1, -1), colors.whitesmoke), ("ALIGN", (0, 0), (-1, -1), "RIGHT"), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    story.append(total_table)
    doc.build(story)
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------
# 5. TELA DE LOGIN E NAVEGAÇÃO PRINCIPAL
# ---------------------------------------------------------
if st.session_state["usuario_logado"] is None:
    col_vazia_esq, col_central, col_vazia_dir = st.columns([0.1, 3.8, 0.1])
    with col_central:
        st.markdown("""<div class='titulo-logo'><span class='palavra-sup-mercado'>Supermercado</span><br><span class='palavra-super'>SUPER</span> <span class='palavra-nova'>NOVA</span><br><span class='palavra-cidade'>Cidade</span></div>""", unsafe_allow_html=True)
        st.markdown("<h3>Sistema de Recebimento Hortifrúti (Supabase Cloud API)</h3>", unsafe_allow_html=True)

        with st.form("form_login"):
            login_input = st.text_input("Usuário / Login ou Nome Completo", value="")
            senha_input = st.text_input("Senha", type="password", value="")
            btn_entrar = st.form_submit_button("Entrar no Sistema", type="primary")
            if btn_entrar:
                usuario = fazer_login(login_input, senha_input)
                if usuario:
                    st.session_state["usuario_logado"] = usuario
                    st.success(f"Bem-vindo(a), {usuario['nome']}!")
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
else:
    user_info = st.session_state["usuario_logado"]
    perfil_db = str(user_info.get("perfil", "")).strip().lower()
    is_admin = (str(user_info.get("login", "")) == "908" or "gestor" in perfil_db or "adm" in perfil_db)
    
    st.markdown("---")
    col_info_usr, col_logout = st.columns([3.5, 1.5], vertical_alignment="center")
    with col_info_usr:
        tipo_perfil_txt = "🔒 Gestor / Administrador" if is_admin else "👤 Conferente"
        st.markdown(f"**Usuário:** {user_info['nome']} &nbsp;|&nbsp; **Perfil:** {tipo_perfil_txt}")
    with col_logout:
        if st.button("🚪 Sair", type="secondary", key="btn_sair_sistema_principal"):
            st.session_state["usuario_logado"] = None
            st.rerun()
            
    opcoes_menu = ["Romaneio de Recebimento - Hortifrúti", "Consultar Romaneios", "Controle de Bonificação", "Controle de Baixa de Avarias"]
    if is_admin:
        opcoes_menu.extend(["Relatórios & Gráficos", "Gerenciar Cadastros (Produtos)", "Gerenciar Usuários & Permissões"])
    
    menu = st.radio("Menu de Navegação Principal", opcoes_menu, horizontal=True, label_visibility="collapsed")
    st.markdown("---")
    
    if menu == "Romaneio de Recebimento - Hortifrúti":
        st.title("Romaneio de Recebimento - Hortifrúti")
        if "form_key_suffix" not in st.session_state: st.session_state["form_key_suffix"] = 0
        if "item_key_suffix" not in st.session_state: st.session_state["item_key_suffix"] = 0
        k_suffix = st.session_state["form_key_suffix"]
        i_suffix = st.session_state["item_key_suffix"]
        
        try:
            res_p = supabase.table("produtos").select("*").order("nome").execute()
            produtos_lista = res_p.data
        except Exception:
            produtos_lista = []
            
        prod_dict = {}
        for p in produtos_lista:
            c_prod = p.get('codigo_produto') or "S/Cód"
            c_bar = p.get('codigo_barras') or "S/Barras"
            label = f"{c_prod} | Barras: {c_bar} | {p['nome']}"
            prod_dict[label] = (p['nome'], p.get('unidade_padrao', 'KG'))
            
        prod_nomes_keys = list(prod_dict.keys())
        with st.expander("1. Cabeçalho do Recebimento", expanded=True):
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                num_romaneio = st.text_input("Número do Romaneio", value="", key=f"num_rom_{k_suffix}")
                loja = st.selectbox("Loja", ["", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"], index=0, key=f"loja_{k_suffix}")
            with col2:
                data_rec_val = st.date_input("Data do Recebimento", value=None, format="DD/MM/YYYY", key=f"data_rec_{k_suffix}")
                data_rec_str = data_rec_val.strftime("%d/%m/%Y") if data_rec_val else ""
                fornecedor = st.text_input("Fornecedor / Entregador", value="", key=f"forn_{k_suffix}")
            with col3:
                cod_fornecedor = st.text_input("Código do Fornecedor", value="", key=f"cod_forn_{k_suffix}")
                tel_fornecedor = st.text_input("Telefone do Fornecedor", value="", key=f"tel_input_{k_suffix}")
            
            col_op1, col_op2 = st.columns([2, 2])
            with col_op1:
                tipo_operacao = st.selectbox("Tipo de Operação", ["Compra", "Bonificação", "Transferência"], index=None, placeholder="Selecione o tipo de operação", key=f"tipo_op_{k_suffix}")
            with col_op2:
                pag_a_vista = st.selectbox("Pagamento à Vista?", ["", "SIM", "NÃO"], index=0, key=f"pag_vista_{k_suffix}")
            
            data_pag_str = ""
            if pag_a_vista == "NÃO":
                data_pag_val = st.date_input("Data para Pagamento", value=None, format="DD/MM/YYYY", key=f"data_pag_{k_suffix}")
                data_pag_str = data_pag_val.strftime("%d/%m/%Y") if data_pag_val else ""
            conferente = st.text_input("Responsável Rec. Físico", value=user_info["nome"], disabled=True, key=f"conf_{k_suffix}")
            
        st.subheader("2. Itens do Recebimento")
        if "itens_romaneio" not in st.session_state: st.session_state["itens_romaneio"] = []
            
        col_p1, col_p2, col_p3, col_p4, col_p5 = st.columns([2.5, 1.2, 1.2, 1.2, 1])
        with col_p1:
            prod_label_sel = st.selectbox("Produto / Código / Barras", options=prod_nomes_keys, index=None, placeholder="", key=f"prod_sel_{k_suffix}_{i_suffix}")
            prod_nome_real = prod_dict[prod_label_sel][0] if prod_label_sel and prod_dict else ""
        with col_p2:
            und_padrao = prod_dict[prod_label_sel][1] if prod_label_sel and prod_dict else "KG"
            und_sel = st.selectbox("UND", ["KG", "UNID", "GRM", "CX"], index=(["KG", "UNID", "GRM", "CX"].index(und_padrao) if und_padrao in ["KG", "UNID", "GRM", "CX"] else 0), key=f"und_sel_{k_suffix}_{i_suffix}")
        with col_p3:
            qtd_str_input = st.text_input("Qtd / Peso", value="", key=f"qtd_{k_suffix}_{i_suffix}")
        with col_p4:
            val_unit_str_input = st.text_input("Valor Unit. (R$)", value="", key=f"vunit_{k_suffix}_{i_suffix}")
        with col_p5:
            st.write("")
            st.write("")
            if st.button("➕ Add", type="primary", key=f"btn_add_{k_suffix}_{i_suffix}"):
                try: qtd_input = float(qtd_str_input.replace(".", "").replace(",", ".")) if qtd_str_input else 0.0
                except ValueError: qtd_input = 0.0
                try: val_unit_val = float(val_unit_str_input.replace(".", "").replace(",", ".")) if val_unit_str_input else 0.0
                except ValueError: val_unit_val = 0.0
                if not prod_nome_real: st.warning("Selecione um produto antes de adicionar.")
                elif qtd_input <= 0: st.warning("Informe uma quantidade maior que zero.")
                else:
                    v_tot = qtd_input * val_unit_val
                    st.session_state["itens_romaneio"].append({"produto": prod_nome_real, "quantidade": qtd_input, "unidade": und_sel, "valor_unitario": val_unit_val, "valor_total": v_tot})
                    st.session_state["item_key_suffix"] += 1
                    st.rerun()
                    
        if st.session_state["itens_romaneio"]:
            st.markdown("**Itens adicionados:**")
            dados_tabela = [{"Item": i, "Descrição do Produto": itm["produto"], "Qtd / Peso": fmt_ptbr(itm['quantidade'], 3), "UND": itm["unidade"], "Vl. Unit": f"R$ {fmt_ptbr(itm['valor_unitario'], 2)}", "Total": f"R$ {fmt_ptbr(itm['valor_total'], 2)}"} for i, itm in enumerate(st.session_state["itens_romaneio"], 1)]
            st.dataframe(pd.DataFrame(dados_tabela), use_container_width=True, hide_index=True)
            
            if st.button("🗑️ Limpar Todos os Itens", type="secondary", key=f"btn_del_itens_{k_suffix}"):
                st.session_state["itens_romaneio"] = []
                st.rerun()
                
        if st.button("✅ Salvar Romaneio", type="primary", key=f"btn_salvar_{k_suffix}"):
            if not num_romaneio.strip() or not fornecedor.strip(): st.error("Preencha o número do romaneio e o fornecedor.")
            elif not data_rec_str: st.error("A Data do Recebimento é obrigatória!")
            elif not tipo_operacao: st.error("O Tipo de Operação é obrigatório!")
            elif not st.session_state["itens_romaneio"]: st.error("Adicione itens ao romaneio.")
            else:
                try:
                    res_rom = supabase.table("romaneios").insert({
                        "numero_romaneio": num_romaneio,
                        "loja": loja,
                        "data_recebimento": data_rec_str,
                        "fornecedor": fornecedor,
                        "codigo_fornecedor": cod_fornecedor,
                        "telefone_fornecedor": tel_fornecedor,
                        "conferente": user_info["nome"],
                        "pagamento_a_vista": pag_a_vista,
                        "data_pagamento": data_pag_str,
                        "status_nota": "Pendente",
                        "tipo_operacao": tipo_operacao
                    }).execute()
                    
                    rom_id = res_rom.data[0]['id']
                    
                    itens_para_inserir = []
                    for itm in st.session_state["itens_romaneio"]:
                        itens_para_inserir.append({
                            "romaneio_id": rom_id,
                            "produto": itm["produto"],
                            "quantidade": itm["quantidade"],
                            "unidade": itm["unidade"],
                            "valor_unitario": itm["valor_unitario"],
                            "valor_total": itm["valor_total"]
                        })
                    
                    supabase.table("romaneio_itens").insert(itens_para_inserir).execute()
                    
                    rom_dict = {"numero_romaneio": num_romaneio, "data_recebimento": data_rec_str, "fornecedor": fornecedor, "loja": loja, "conferente": user_info["nome"], "tipo_operacao": tipo_operacao}
                    pdf_buf = gerar_pdf_romaneio(rom_dict, st.session_state["itens_romaneio"])
                    st.session_state["ultimo_pdf_bytes"] = pdf_buf.getvalue()
                    st.session_state["ultimo_num_romaneio"] = num_romaneio
                    st.session_state["itens_romaneio"] = []
                    st.session_state["form_key_suffix"] += 1
                    st.success(f"Romaneio {num_romaneio} salvo com sucesso no Supabase Cloud!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar no Supabase: {e}")
                    
        if "ultimo_pdf_bytes" in st.session_state:
            st.markdown("---")
            st.download_button(label=f"📥 Baixar PDF - {st.session_state['ultimo_num_romaneio']}", data=st.session_state["ultimo_pdf_bytes"], file_name=f"{st.session_state['ultimo_num_romaneio']}.pdf", mime="application/pdf", type="primary")

    elif menu == "Consultar Romaneios":
        st.title("🔍 Consulta de Romaneios")
        try:
            res_r = supabase.table("romaneios").select("*").order("id", desc=True).execute()
            df_rom = pd.DataFrame(res_r.data)
        except Exception:
            df_rom = pd.DataFrame()
            
        if not df_rom.empty:
            for _, row in df_rom.iterrows():
                with st.expander(f"Romaneio: {row['numero_romaneio']} | [{str(row.get('tipo_operacao','Compra')).upper()}] | Fornecedor: {row['fornecedor']} | Data: {row['data_recebimento']}"):
                    st.write(f"**Loja:** {row['loja']} | **Conferente:** {row['conferente']}")
                    try:
                        res_it = supabase.table("romaneio_itens").select("*").eq("romaneio_id", row['id']).execute()
                        df_it = pd.DataFrame(res_it.data)
                        if not df_it.empty:
                            st.dataframe(df_it[['produto', 'quantidade', 'unidade', 'valor_unitario', 'valor_total']], use_container_width=True)
                    except Exception:
                        pass
        else:
            st.info("Nenhum romaneio encontrado no Supabase.")

    elif menu == "Controle de Bonificação":
        st.title("🎁 Controle de Bonificação Hortifrúti")
        try:
            res_b = supabase.table("bonificacoes").select("*").order("id", desc=True).execute()
            df_bonf = pd.DataFrame(res_b.data)
        except Exception:
            df_bonf = pd.DataFrame()

        with st.expander("➕ Cadastrar Nova Bonificação", expanded=True):
            with st.form("form_cad_bonificacao", clear_on_submit=True):
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    num_nota_bonf = st.text_input("N° Nota Fiscal")
                    loja_bonf = st.selectbox("Loja", ["", "LOJA 01 CD", "LOJA 02 NOVA CIDADE", "LOJA 03 TERRA NOVA", "LOJA 04 MANOA", "LOJA 05 ZUMBI", "LOJA 06 OSWALDO FROTA", "LOJA 07 MOSAICO"])
                with col_b2:
                    valor_bonf_str = st.text_input("Valor da Bonificação (R$)")
                    tipo_bonf_sel = st.selectbox("Tipo de Bonificação", ["Bonificação", "Transferência de Bonificação"])
                
                prod_bonf = st.text_input("Produto Hortifrúti")
                status_bonf = st.selectbox("STATUS", ["Disponível", "Parcialmente Utilizada", "Totalmente Utilizada"])
                data_entrada_manual = st.date_input("Data de Entrada", value=None, format="DD/MM/YYYY")
                
                if st.form_submit_button("✅ Salvar Bonificação", type="primary"):
                    if not num_nota_bonf.strip() or not loja_bonf or not data_entrada_manual:
                        st.error("Preencha os campos obrigatórios.")
                    else:
                        try:
                            val_b = float(valor_bonf_str.replace(".", "").replace(",", ".")) if valor_bonf_str else 0.0
                            dt_str = data_entrada_manual.strftime('%d/%m/%Y')
                            supabase.table("bonificacoes").insert({
                                "numero_nota": num_nota_bonf.strip(),
                                "loja": loja_bonf,
                                "data_entrada": dt_str,
                                "valor_bonificacao": val_b,
                                "status": status_bonf,
                                "produto_hortifruti": prod_bonf.strip(),
                                "tipo_bonificacao": tipo_bonf_sel
                            }).execute()
                            st.success("Bonificação salva com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

        if not df_bonf.empty:
            st.markdown("---")
            pdf_b = gerar_pdf_bonificacoes(df_bonf)
            st.download_button("📥 Baixar Relatório de Bonificação em PDF", data=pdf_b, file_name="bonificacoes.pdf", mime="application/pdf", type="primary")
            st.dataframe(df_bonf, use_container_width=True)
        else:
            st.info("Nenhuma bonificação registada.")

    elif menu == "Controle de Baixa de Avarias":
        st.title("📉 Registro de Baixas das Avarias")
        try:
            res_bx = supabase.table("baixas_avarias").select("*").order("id", desc=True).execute()
            df_bx = pd.DataFrame(res_bx.data)
        except Exception:
            df_bx = pd.DataFrame()

        with st.expander("➕ Registrar Nova Baixa de Avaria", expanded=True):
            with st.form("form_reg_baixa", clear_on_submit=True):
                loja_bx = st.selectbox("Loja", ["", "LOJA 02 NOVA CIDADE", "LOJA 01 CD", "LOJA 03 TERRA NOVA"])
                ref_bon = st.text_input("Ref. Bon. transferen")
                nf_ent = st.text_input("NF de B. ENTRADA")
                prod_bx = st.text_input("Produto Hortifrúti")
                qtd_bx = st.text_input("Qtd (kg/cx)")
                val_av = st.text_input("Valor Total Avaria (R$)")
                dt_bx = st.date_input("Data da Baixa", value=None, format="DD/MM/YYYY")

                if st.form_submit_button("✅ Registrar Baixa", type="primary"):
                    if not loja_bx or not dt_bx:
                        st.error("Preencha os campos obrigatórios.")
                    else:
                        try:
                            q_f = float(qtd_bx.replace(".", "").replace(",", ".")) if qtd_bx else 0.0
                            v_f = float(val_av.replace(".", "").replace(",", ".")) if val_av else 0.0
                            supabase.table("baixas_avarias").insert({
                                "loja_baixa": loja_bx,
                                "data_baixa": dt_bx.strftime('%d/%m/%Y'),
                                "ref_bon_transferen": ref_bon.strip(),
                                "nf_b_entrada": nf_ent.strip(),
                                "produto_hortifruti": prod_bx.strip(),
                                "quantidade_kg_cx": q_f,
                                "valor_total_avaria": v_f,
                                "saldo_restante_nota": 0.0,
                                "saldo_total_disponivel": 0.0
                            }).execute()
                            st.success("Baixa registrada com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro: {e}")

        if not df_bx.empty:
            st.markdown("---")
            pdf_bx = gerar_pdf_baixas(df_bx)
            st.download_button("📥 Baixar Planilha de Baixas em PDF", data=pdf_bx, file_name="baixas.pdf", mime="application/pdf", type="primary")
            st.dataframe(df_bx, use_container_width=True)
        else:
            st.info("Nenhuma baixa de avaria registada.")

    elif menu == "Relatórios & Gráficos" and is_admin:
        st.title("📊 Relatórios e Análise Gerencial")
        try:
            res_roms = supabase.table("romaneios").select("*").execute()
            res_itens = supabase.table("romaneio_itens").select("*").execute()
            df_roms = pd.DataFrame(res_roms.data)
            df_itens = pd.DataFrame(res_itens.data)
        except Exception:
            df_roms, df_itens = pd.DataFrame(), pd.DataFrame()

        if not df_roms.empty and not df_itens.empty:
            df_full = df_itens.merge(df_roms, left_on='romaneio_id', right_on='id', suffixes=('_item', '_romaneio'))
            st.metric("Valor Total Recebido", f"R$ {fmt_ptbr(df_full['valor_total'].sum(), 2)}")
            fig = px.bar(df_full.groupby("produto")["valor_total"].sum().reset_index(), x="produto", y="valor_total", title="Total por Produto")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Sem dados suficientes para gerar gráficos.")

    elif menu == "Gerenciar Cadastros (Produtos)" and is_admin:
        st.title("🥦 Gerenciamento de Produtos")
        with st.form("cad_prod_form", clear_on_submit=True):
            col1, col2, col3, col4 = st.columns([2, 2, 3, 1.5])
            with col1: c_p = st.text_input("Código do Produto")
            with col2: c_b = st.text_input("Código de Barras")
            with col3: n_p = st.text_input("Nome do Produto *")
            with col4: u_p = st.selectbox("Unidade", ["KG", "UNID", "GRM", "CX"])
            if st.form_submit_button("➕ Cadastrar Produto", type="primary"):
                if not n_p.strip():
                    st.error("O nome é obrigatório.")
                else:
                    try:
                        supabase.table("produtos").insert({
                            "codigo_produto": c_p.strip() if c_p else None,
                            "codigo_barras": c_b.strip() if c_b else None,
                            "nome": n_p.strip().upper(),
                            "unidade_padrao": u_p
                        }).execute()
                        st.success("Produto cadastrado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

        try:
            res_all_p = supabase.table("produtos").select("*").order("nome").execute()
            df_p = pd.DataFrame(res_all_p.data)
            if not df_p.empty:
                st.markdown("---")
                pdf_p_bytes = gerar_pdf_produtos(df_p.to_dict('records'))
                st.download_button("📥 Baixar Relatório de Produtos em PDF", data=pdf_p_bytes, file_name="produtos.pdf", mime="application/pdf", type="primary")
                st.dataframe(df_p[['codigo_produto', 'codigo_barras', 'nome', 'unidade_padrao']], use_container_width=True)
        except Exception:
            pass

    elif menu == "Gerenciar Usuários & Permissões" and is_admin:
        st.title("👥 Gerenciamento de Usuários")
        with st.form("cad_usuario_form", clear_on_submit=True):
            u_nome = st.text_input("Nome Completo")
            u_login = st.text_input("Login de Acesso")
            u_senha = st.text_input("Senha", type="password")
            u_perfil = st.selectbox("Perfil", ["Conferente", "Gestor"])
            if st.form_submit_button("➕ Cadastrar Usuário", type="primary"):
                if not u_nome.strip() or not u_login.strip() or not u_senha.strip():
                    st.error("Preencha todos os campos.")
                else:
                    try:
                        supabase.table("usuarios").insert({
                            "nome": u_nome.strip(),
                            "login": u_login.strip(),
                            "senha": u_senha.strip(),
                            "perfil": u_perfil
                        }).execute()
                        st.success("Usuário cadastrado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro: {e}")

        try:
            res_all_u = supabase.table("usuarios").select("*").execute()
            df_u = pd.DataFrame(res_all_u.data)
            if not df_u.empty:
                st.dataframe(df_u[['nome', 'login', 'perfil']], use_container_width=True)
        except Exception:
            pass
