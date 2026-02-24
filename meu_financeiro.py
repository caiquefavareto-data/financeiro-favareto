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

# --- 2. FUNÇÕES DE DADOS (LIMPEZA NUMÉRICA PESADA) ---
def carregar_aba(aba_nome, colunas):
    try:
        sh = conectar_google_sheets()
        worksheet = sh.worksheet(aba_nome)
        df = pd.DataFrame(worksheet.get_all_records())
        if df.empty: return pd.DataFrame(columns=colunas)
        
        if 'Data_Vencimento' in df.columns:
            df['Data_Vencimento'] = pd.to_datetime(df['Data_Vencimento'], errors='coerce').dt.date
        
        # --- CORREÇÃO DO GRÁFICO (FORÇAR NÚMERO REAL) ---
        if 'Valor' in df.columns:
            # Remove pontos de milhar, troca vírgula por ponto e tira o R$ se houver
            df['Valor'] = df['Valor'].astype(str).str.replace('R$', '', regex=False)
            df['Valor'] = df['Valor'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.strip()
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0).astype(float)
            
        return df
    except:
        return pd.DataFrame(columns=colunas)

def salvar_aba(df, aba_nome):
    sh = conectar_google_sheets()
    worksheet = sh.worksheet(aba_nome)
    worksheet.clear()
    df_save = df.copy()
    # Converte tudo para string apenas para o Google Sheets aceitar
    for col in df_save.columns:
        df_save[col] = df_save[col].astype(str)
    worksheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())
    if 'df' in st.session_state: del st.session_state.df

def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

# --- 3. CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestor Pro - Elevadores", layout="wide")
cols_fin = ["OS", "NF", "Data_Vencimento", "Ambiente", "Tipo_Fluxo", "Descricao", "Categoria", "Valor", "Status", "Cliente", "Usuario", "Cartao", "Detalhes"]

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

# Atualiza filtros sempre que os dados mudarem
df_user = st.session_state.df[st.session_state.df['Usuario'] == user]
cartoes_user = st.session_state.cartoes[st.session_state.cartoes['Usuario'] == user]
clientes_user = st.session_state.clientes[st.session_state.clientes['Usuario'] == user]

tab_lanc, tab_cartoes, tab_clientes, tab_relat, tab_conf = st.tabs(["📝 Lançamentos", "💳 Cartões", "👥 Clientes", "📈 Relatórios", "⚙️ Opções"])

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
                cat_sel = st.selectbox("Categoria", sorted(["Carro Combustível", "Carro Multa", "Carro Pedágio", "Escola", "Farmácia", "Imposto", "Manutenção Preventiva", "Material", "Mercado", "Pagamento", "Peças Elevador", "Retirada", "Outros"]))
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
        st.metric("PJ", f"R$ {s_pj:,.2f}"); st.metric("PF", f"R$ {s_pf:,.2f}")
        if not df_user.empty:
            # GRÁFICO PÁGINA 1: Agora garantindo soma financeira (values='Valor')
            fig_p1 = px.pie(df_user, values='Valor', names='Status', hole=.6, color='Status', color_discrete_map={'Concluído':'#00CC96', 'Pendente':'#FFA15A', 'Recusado':'#EF553B'})
            fig_p1.update_layout(showlegend=False, height=140, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig_p1, use_container_width=True)

    st.divider()
    st.subheader("📋 Resumo Financeiro")
    col_busca, col_hist_check = st.columns([3, 1])
    termo_busca = col_busca.text_input("🔎 Pesquisar nota (OS, Cliente, NF ou Descrição)")
    ver_antigos = col_hist_check.checkbox("Ver Histórico")
    
    df_h = df_user.copy().sort_values("Data_Vencimento", ascending=False)
    if not ver_antigos and not termo_busca:
        df_h = df_h[df_h['Data_Vencimento'] >= datetime.now().date().replace(day=1)]
    if termo_busca:
        df_h = df_h[df_h.astype(str).apply(lambda x: x.str.contains(termo_busca, case=False)).any(axis=1)]

    tab_pj_h, tab_pf_h = st.tabs(["🏢 Histórico Empresa (PJ)", "🏠 Histórico Pessoal (PF)"])
    
    with tab_pj_h:
        df_pj_h = df_h[df_h['Ambiente'] == "Empresa"]
        st.dataframe(df_pj_h[["Data_Vencimento", "OS", "Status", "Cliente", "Valor"]], use_container_width=True, hide_index=True)
        if not df_pj_h.empty:
            os_pj = st.selectbox("🔎 Detalhes (PJ):", ["---"] + df_pj_h["OS"].tolist(), key="sb_pj")
            if os_pj != "---":
                det = df_pj_h[df_pj_h["OS"] == os_pj].iloc[0]
                with st.container(border=True):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Valor:** R$ {det['Valor']:,.2f}"); c2.write(f"**Pagto:** {det['Cartao']}"); c3.write(f"**NF:** {det['NF']}")
                    st.write(f"**Descrição:** {det['Descricao']}"); st.info(f"**Obs:** {det['Detalhes']}")
                    if st.button("🗑️ Excluir Nota PJ", key="del_pj"):
                        st.session_state.df = st.session_state.df[st.session_state.df["OS"] != os_pj]
                        salvar_aba(st.session_state.df, "lancamentos"); st.rerun()

    with tab_pf_h:
        df_pf_h = df_h[df_h['Ambiente'] == "Pessoal"].copy()
        st.dataframe(df_pf_h[["Data_Vencimento", "Descricao", "Status", "Categoria", "Valor"]], use_container_width=True, hide_index=True)
        if not df_pf_h.empty:
            df_pf_h['Exibicao'] = df_pf_h['Descricao'].astype(str) + " (" + df_pf_h['Categoria'].astype(str) + ")"
            selecao_pf = st.selectbox("🔎 Detalhes (PF):", ["---"] + df_pf_h['Exibicao'].tolist(), key="sb_pf")
            if selecao_pf != "---":
                det = df_pf_h[df_pf_h['Exibicao'] == selecao_pf].iloc[0]
                with st.container(border=True):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Valor:** R$ {det['Valor']:,.2f}"); c2.write(f"**Pagto:** {det['Cartao']}"); c3.write(f"**Categoria:** {det['Categoria']}")
                    st.write(f"**Descrição:** {det['Descricao']}"); st.info(f"**Obs:** {det['Detalhes']}")
                    if st.button("🗑️ Excluir Nota PF", key="del_pf"):
                        st.session_state.df = st.session_state.df[st.session_state.df["OS"] != det["OS"]]
                        salvar_aba(st.session_state.df, "lancamentos"); st.rerun()

# --- ABA CLIENTES ---
with tab_clientes:
    c1, c2 = st.columns(2)
    with c1:
        with st.form("cli", clear_on_submit=True):
            n_cli = st.text_input("Novo Cliente")
            if st.form_submit_button("Cadastrar"):
                st.session_state.clientes = pd.concat([st.session_state.clientes, pd.DataFrame([{"Nome": n_cli, "Usuario": user}])], ignore_index=True)
                salvar_aba(st.session_state.clientes, "clientes"); st.rerun()
    with c2:
        for idx, r in clientes_user.iterrows():
            col_n, col_b = st.columns([5, 1])
            col_n.markdown(f"#### {r['Nome']}")
            if col_b.button("🗑️", key=f"c_{idx}"):
                st.session_state.clientes = st.session_state.clientes.drop(idx); salvar_aba(st.session_state.clientes, "clientes"); st.rerun()

# --- ABA CARTÕES ---
with tab_cartoes:
    c1, c2 = st.columns(2)
    with c1:
        with st.form("car", clear_on_submit=True):
            n_car, l_car = st.text_input("Cartão"), st.number_input("Limite Total", min_value=1.0)
            if st.form_submit_button("Adicionar"):
                st.session_state.cartoes = pd.concat([st.session_state.cartoes, pd.DataFrame([{"Nome": n_car, "Limite_Total": l_car, "Usuario": user}])], ignore_index=True)
                salvar_aba(st.session_state.cartoes, "cartoes"); st.rerun()
    with c2:
        for idx, r in cartoes_user.iterrows():
            col_n, col_b = st.columns([5, 1])
            col_n.markdown(f"#### 💳 {r['Nome']}")
            u_gasto = df_user[(df_user['Cartao'] == r['Nome']) & (df_user['Tipo_Fluxo'] == 'Saída (Pagamento)') & (df_user['Status'] != 'Recusado')]['Valor'].sum()
            limite = float(r['Limite_Total'])
            st.progress(max(0.0, min(u_gasto / limite, 1.0)))
            st.caption(f"**Livre:** R$ {max(0.0, limite - u_gasto):,.2f}")
            if col_b.button("🗑️", key=f"cc_{idx}"):
                st.session_state.cartoes = st.session_state.cartoes.drop(idx); salvar_aba(st.session_state.cartoes, "cartoes"); st.rerun()

# --- ABA RELATÓRIOS (CORREÇÃO SOMA FINANCEIRA) ---
with tab_relat:
    if st.button("🔄 Sincronizar Dados"):
        st.session_state.df = carregar_aba("lancamentos", cols_fin)
        st.rerun()
    
    # Recalcula df_user para garantir que os dados novos apareçam no gráfico
    df_user_rel = st.session_state.df[st.session_state.df['Usuario'] == user]
    df_v = df_user_rel[(df_user_rel['Status'] != "Recusado") & (df_user_rel['Valor'] > 0)].copy()
    
    if not df_v.empty:
        st.markdown("### 📊 Fluxo Financeiro (Proporção Real em R$)")
        # values='Valor' faz o gráfico ser proporcional ao DINHEIRO
        fig_fluxo = px.pie(df_v, values='Valor', names='Tipo_Fluxo', hole=.5, color='Tipo_Fluxo', color_discrete_map={'Entrada (Recebimento)': '#2ECC71', 'Saída (Pagamento)': '#E74C3C'})
        fig_fluxo.update_traces(textinfo='percent+value', texttemplate='%{percent:.1%} <br>R$ %{value:,.2f}')
        st.plotly_chart(fig_fluxo, use_container_width=True)
        st.divider()
        col_pj, col_pf = st.columns(2)
        df_gastos = df_v[df_v['Tipo_Fluxo'] == 'Saída (Pagamento)']
        with col_pj:
            st.markdown("### 🏢 Gastos PJ")
            df_pj_r = df_gastos[df_gastos['Ambiente'] == "Empresa"]
            if not df_pj_r.empty: st.plotly_chart(px.pie(df_pj_r, values='Valor', names='Categoria', hole=.4), use_container_width=True)
        with col_pf:
            st.markdown("### 🏠 Gastos PF")
            df_pf_r = df_gastos[df_gastos['Ambiente'] == "Pessoal"]
            if not df_pf_r.empty: st.plotly_chart(px.pie(df_pf_r, values='Valor', names='Categoria', hole=.4), use_container_width=True)
    else: st.info("Sem dados para análise financeira.")

with tab_conf:
    if st.button("Sair"): st.session_state.clear(); st.rerun()
