import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import hashlib
import gspread
from google.oauth2.service_account import Credentials

# --- 1. CONEXÃO COM GOOGLE SHEETS ---
def conectar_google_sheets():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open("Banco_Dados_Gestor_Pro")

# --- 2. FUNÇÕES DE DADOS ---
def carregar_aba(aba_nome, colunas):
    try:
        sh = conectar_google_sheets()
        worksheet = sh.worksheet(aba_nome)
        df = pd.DataFrame(worksheet.get_all_records())
        if df.empty: return pd.DataFrame(columns=colunas)
        if 'Data_Vencimento' in df.columns:
            df['Data_Vencimento'] = pd.to_datetime(df['Data_Vencimento'], errors='coerce').dt.date
        # GARANTE QUE VALOR É NÚMERO PARA O GRÁFICO SOMAR CERTO
        if 'Valor' in df.columns:
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=colunas)

def salvar_aba(df, aba_nome):
    sh = conectar_google_sheets()
    worksheet = sh.worksheet(aba_nome)
    worksheet.clear()
    df_save = df.copy()
    for col in df_save.columns:
        df_save[col] = df_save[col].astype(str)
    worksheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    if 'df' in st.session_state: del st.session_state.df

def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestor Pro - Elevadores", layout="wide")
cols_fin = ["OS", "NF", "Data_Vencimento", "Ambiente", "Tipo_Fluxo", "Descricao", "Categoria", "Valor", "Status", "Cliente", "Usuario", "Cartao", "Detalhes"]

# --- 3. ACESSO ---
if "autenticado" not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏗️ Gestor Pro</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        opcao = st.radio("Escolha:", ["Login", "Cadastro"], horizontal=True)
        df_acessos = carregar_aba("acessos", ["Usuario", "Senha"])
        u = st.text_input("Usuário").strip()
        p = st.text_input("Senha", type="password")
        if st.button("Acessar", use_container_width=True):
            if (u == "Caique" and p == "11") or not df_acessos[(df_acessos["Usuario"] == u) & (df_acessos["Senha"] == hash_senha(p))].empty:
                st.session_state.autenticado, st.session_state.usuario = True, u
                st.rerun()
            else: st.error("Erro no login.")
    st.stop()

# --- 4. CARREGAMENTO ---
user = st.session_state.usuario
if 'df' not in st.session_state: st.session_state.df = carregar_aba("lancamentos", cols_fin)
if 'cartoes' not in st.session_state: st.session_state.cartoes = carregar_aba("cartoes", ["Nome", "Limite_Total", "Usuario"])
if 'clientes' not in st.session_state: st.session_state.clientes = carregar_aba("clientes", ["Nome", "Usuario"])

df_user = st.session_state.df[st.session_state.df['Usuario'] == user]
cartoes_user = st.session_state.cartoes[st.session_state.cartoes['Usuario'] == user]
clientes_user = st.session_state.clientes[st.session_state.clientes['Usuario'] == user]

tab_lanc, tab_cartoes, tab_clientes, tab_relat, tab_conf = st.tabs(["📝 Lançamentos", "💳 Cartões", "👥 Clientes", "📈 Relatórios", "⚙️ Opções"])

# --- ABA LANÇAMENTOS (PÁGINA 1) ---
with tab_lanc:
    col_f, col_g = st.columns([2, 1])
    with col_f:
        with st.expander("➕ Novo Registro"):
            c1, c2 = st.columns(2)
            with c1:
                ambiente = st.radio("Destino", ["Empresa", "Pessoal"], horizontal=True)
                tipo = st.selectbox("Tipo", ["Saída (Pagamento)", "Entrada (Recebimento)"])
                data_v = st.date_input("Vencimento", datetime.now())
                os_n = st.text_input("Nº OS")
                cli_sel = st.selectbox("Cliente", ["N/A"] + sorted(clientes_user["Nome"].tolist()))
                cat_lista = sorted(["Carro Combustível", "Carro Multa", "Carro Pedágio", "Escola", "Farmácia", "Imposto", "Manutenção Preventiva", "Material", "Mercado", "Pagamento", "Peças Elevador", "Retirada", "Outros"])
                cat_sel = st.selectbox("Categoria", cat_lista)
            with c2:
                nf_n = st.text_input("Nº NF")
                desc = st.text_input("Descrição")
                val = st.number_input("Valor R$", min_value=0.0)
                parc = st.number_input("Parcelas", min_value=1, value=1)
                metodo = st.selectbox("Pagto/Cartão", ["Pix", "Boleto", "Dinheiro", "Débito", "Transferência"] + cartoes_user["Nome"].tolist())
                status_sel = st.selectbox("Status", ["Pendente", "Concluído", "Recusado"])
            obs = st.text_area("Observações")
            if st.button("Gravar", use_container_width=True):
                id_base = os_n if os_n.strip() != "" else datetime.now().strftime("%Y%m%d%H%M%S")
                novos = []
                for i in range(parc):
                    novos.append({"OS": id_base if parc==1 else f"{id_base}-{i+1}", "NF": nf_n, "Data_Vencimento": data_v + timedelta(days=30*i), "Ambiente": ambiente, "Tipo_Fluxo": tipo, "Descricao": desc, "Categoria": cat_sel, "Valor": val, "Status": status_sel, "Cliente": cli_sel, "Usuario": user, "Cartao": metodo, "Detalhes": obs})
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame(novos)], ignore_index=True)
                salvar_aba(st.session_state.df, "lancamentos"); st.rerun()

    with col_g:
        df_ok = df_user[df_user['Status'] != "Recusado"]
        s_pj = df_ok[df_ok['Ambiente'] == "Empresa"][df_ok['Tipo_Fluxo'] == 'Entrada (Recebimento)']['Valor'].sum() - df_ok[df_ok['Ambiente'] == "Empresa"][df_ok['Tipo_Fluxo'] == 'Saída (Pagamento)']['Valor'].sum()
        s_pf = df_ok[df_ok['Ambiente'] == "Pessoal"][df_ok['Tipo_Fluxo'] == 'Entrada (Recebimento)']['Valor'].sum() - df_ok[df_ok['Ambiente'] == "Pessoal"][df_ok['Tipo_Fluxo'] == 'Saída (Pagamento)']['Valor'].sum()
        st.metric("Saldo PJ", f"R$ {s_pj:,.2f}")
        st.metric("Saldo PF", f"R$ {s_pf:,.2f}")
        
        # AJUSTE GRÁFICO PÁGINA 1: Agora ele mostra a proporção de DINHEIRO por Status
        if not df_user.empty:
            fig_p1 = px.pie(df_user, values='Valor', names='Status', hole=.6, color='Status', 
                           color_discrete_map={'Concluído':'#00CC96', 'Pendente':'#FFA15A', 'Recusado':'#EF553B'})
            fig_p1.update_layout(showlegend=False, height=160, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig_p1, use_container_width=True)

    st.divider()
    # ... (partes de Histórico, Clientes e Cartões permanecem iguais)
    st.subheader("📋 Resumo Financeiro")
    t_pj, t_pf = st.tabs(["🏢 Empresa (PJ)", "🏠 Pessoal (PF)"])
    with t_pj:
        df_pj_h = df_user[df_user['Ambiente'] == "Empresa"].sort_values("Data_Vencimento", ascending=False)
        st.dataframe(df_pj_h[["Data_Vencimento", "OS", "Status", "Cliente", "Valor"]], use_container_width=True, hide_index=True)
    with t_pf:
        df_pf_h = df_user[df_user['Ambiente'] == "Pessoal"].sort_values("Data_Vencimento", ascending=False)
        st.dataframe(df_pf_h[["Data_Vencimento", "Descricao", "Status", "Categoria", "Valor"]], use_container_width=True, hide_index=True)

# --- ABA RELATÓRIOS (CORREÇÃO DOS 50%) ---
with tab_relat:
    if st.button("🔄 Atualizar Dados"):
        st.session_state.df = carregar_aba("lancamentos", cols_fin)
        st.rerun()
    
    df_v = df_user[(df_user['Status'] != "Recusado") & (df_user['Valor'] > 0)].copy()
    if not df_v.empty:
        # CORREÇÃO CRÍTICA: values='Valor' faz o gráfico somar o dinheiro, não contar as linhas!
        st.markdown("### 📊 Fluxo de Caixa (Valores em R$)")
        fig_fluxo = px.pie(df_v, values='Valor', names='Tipo_Fluxo', hole=.5,
                          color='Tipo_Fluxo', color_discrete_map={'Entrada (Recebimento)': '#2ECC71', 'Saída (Pagamento)': '#E74C3C'})
        fig_fluxo.update_traces(textinfo='percent+value', texttemplate='%{percent:.1%} <br>R$ %{value:,.2f}')
        st.plotly_chart(fig_fluxo, use_container_width=True)
        
        st.divider()
        col_pj, col_pf = st.columns(2)
        df_gastos = df_v[df_v['Tipo_Fluxo'] == 'Saída (Pagamento)']
        
        with col_pj:
            st.markdown("### 🏢 Gastos PJ por Categoria")
            df_pj_r = df_gastos[df_gastos['Ambiente'] == "Empresa"]
            if not df_pj_r.empty:
                fig_pj = px.pie(df_pj_r, values='Valor', names='Categoria', hole=.4)
                fig_pj.update_traces(textinfo='value')
                st.plotly_chart(fig_pj, use_container_width=True)
        with col_pf:
            st.markdown("### 🏠 Gastos PF por Categoria")
            df_pf_r = df_gastos[df_gastos['Ambiente'] == "Pessoal"]
            if not df_pf_r.empty:
                fig_pf = px.pie(df_pf_r, values='Valor', names='Categoria', hole=.4)
                fig_pf.update_traces(textinfo='value')
                st.plotly_chart(fig_pf, use_container_width=True)
    else: st.info("Sem dados para gerar gráficos.")

with tab_conf:
    if st.button("Sair"): st.session_state.clear(); st.rerun()
