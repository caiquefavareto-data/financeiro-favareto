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
        return df
    except:
        return pd.DataFrame(columns=colunas)

def salvar_aba(df, aba_nome):
    sh = conectar_google_sheets()
    worksheet = sh.worksheet(aba_nome)
    worksheet.clear()
    df_save = df.copy()
    for col in df_save.columns:
        if 'date' in col.lower() or df_save[col].dtype == 'object':
            df_save[col] = df_save[col].astype(str)
    worksheet.update([df_save.columns.values.tolist()] + df_save.values.tolist())

def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestor Pro - Elevadores", layout="wide")

cols_fin = ["OS", "NF", "Data_Vencimento", "Ambiente", "Tipo_Fluxo", "Descricao", "Categoria", "Valor", "Status", "Cliente", "Usuario", "Cartao", "Detalhes"]

if 'df' not in st.session_state: st.session_state.df = carregar_aba("lancamentos", cols_fin)
if 'cartoes' not in st.session_state: st.session_state.cartoes = carregar_aba("cartoes", ["Nome", "Limite_Total", "Usuario"])
if 'clientes' not in st.session_state: st.session_state.clientes = carregar_aba("clientes", ["Nome", "Usuario"])

# --- 3. ACESSO ---
if "autenticado" not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏗️ Gestor Pro</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        opcao = st.radio("Escolha:", ["Login", "Cadastro"], horizontal=True)
        df_acessos = carregar_aba("acessos", ["Usuario", "Senha"])
        u = st.text_input("Usuário").strip()
        p = st.text_input("Senha", type="password")
        if st.button("Acessar" if opcao == "Login" else "Cadastrar", use_container_width=True):
            if opcao == "Login":
                if (u == "Caique" and p == "11") or not df_acessos[(df_acessos["Usuario"] == u) & (df_acessos["Senha"] == hash_senha(p))].empty:
                    st.session_state.autenticado, st.session_state.usuario = True, u
                    st.rerun()
                else: st.error("Erro no login.")
            else:
                if u and p:
                    nova = pd.DataFrame([{"Usuario": u, "Senha": hash_senha(p)}])
                    salvar_aba(pd.concat([df_acessos, nova], ignore_index=True), "acessos")
                    st.success("Cadastrado!")
    st.stop()

# --- 4. CARREGAMENTO PÓS-LOGIN ---
user = st.session_state.usuario
df_user = st.session_state.df[st.session_state.df['Usuario'] == user]
cartoes_user = st.session_state.cartoes[st.session_state.cartoes['Usuario'] == user]
clientes_user = st.session_state.clientes[st.session_state.clientes['Usuario'] == user]

st.markdown(f"#### 👤 {user}")
tab_lanc, tab_cartoes, tab_clientes, tab_relat, tab_conf = st.tabs(["📝 Lançamentos", "💳 Cartões", "👥 Clientes", "📈 Relatórios", "⚙️ Opções"])

# --- TAB LANÇAMENTOS ---
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
        st.metric("PJ", f"R$ {s_pj:,.2f}"); st.metric("PF", f"R$ {s_pf:,.2f}")
        st.plotly_chart(px.pie(df_user, values='Valor', names='Status', hole=.6, color='Status', color_discrete_map={'Concluído':'#00CC96', 'Pendente':'#FFA15A', 'Recusado':'#EF553B'}).update_layout(showlegend=False, height=140, margin=dict(t=0,b=0,l=0,r=0)), use_container_width=True)

    st.divider()
    st.subheader("📋 Resumo Financeiro")
    col_b, col_h = st.columns([3, 1])
    termo = col_b.text_input("🔎 Pesquisar nota")
    ver_antigos = col_h.checkbox("Ver Histórico")
    df_h = df_user.copy().sort_values("Data_Vencimento", ascending=False)
    if not ver_antigos and not termo: df_h = df_h[df_h['Data_Vencimento'] >= datetime.now().date().replace(day=1)]
    if termo: df_h = df_h[df_h.astype(str).apply(lambda x: x.str.contains(termo, case=False)).any(axis=1)]

    t_pj, t_pf = st.tabs(["🏢 Empresa (PJ)", "🏠 Pessoal (PF)"])
    with t_pj:
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
    with t_pf:
        df_pf_h = df_h[df_h['Ambiente'] == "Pessoal"]
        st.dataframe(df_pf_h[["Data_Vencimento", "Descricao", "Status", "Categoria", "Valor"]], use_container_width=True, hide_index=True)
        if not df_pf_h.empty:
            df_pf_h['Exibicao'] = df_pf_h['Descricao'] + " (" + df_pf_h['Categoria'] + ")"
            sel_pf = st.selectbox("🔎 Selecionar por Descrição (PF):", ["---"] + df_pf_h['Exibicao'].tolist(), key="sb_pf")
            if sel_pf != "---":
                det = df_pf_h[df_pf_h['Exibicao'] == sel_pf].iloc[0]
                with st.container(border=True):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Valor:** R$ {det['Valor']:,.2f}"); c2.write(f"**Pagto:** {det['Cartao']}"); c3.write(f"**Categoria:** {det['Categoria']}")
                    st.write(f"**Descrição:** {det['Descricao']}"); st.info(f"**Obs:** {det['Detalhes']}")
                    if st.button("🗑️ Excluir Nota PF", key="del_pf"):
                        st.session_state.df = st.session_state.df[st.session_state.df["OS"] != det["OS"]]
                        salvar_aba(st.session_state.df, "lancamentos"); st.rerun()

# --- TAB CLIENTES ---
with tab_clientes:
    c1, c2 = st.columns(2)
    with c1:
        with st.form("cli", clear_on_submit=True):
            n_cli = st.text_input("Novo Cliente")
            if st.form_submit_button("Cadastrar"):
                if n_cli:
                    st.session_state.clientes = pd.concat([st.session_state.clientes, pd.DataFrame([{"Nome": n_cli, "Usuario": user}])], ignore_index=True)
                    salvar_aba(st.session_state.clientes, "clientes"); st.rerun()
    with c2:
        for idx, r in clientes_user.iterrows():
            col_n, col_b = st.columns([5, 1])
            col_n.markdown(f"#### {r['Nome']}")
            if col_b.button("🗑️", key=f"c_{idx}"):
                st.session_state.clientes = st.session_state.clientes.drop(idx); salvar_aba(st.session_state.clientes, "clientes"); st.rerun()

# --- TAB CARTÕES ---
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
            st.caption(f"**Limite:** R$ {limite:,.2f} | **Livre:** R$ {max(0.0, limite - u_gasto):,.2f}")
            if col_b.button("🗑️", key=f"cc_{idx}"):
                st.session_state.cartoes = st.session_state.cartoes.drop(idx); salvar_aba(st.session_state.cartoes, "cartoes"); st.rerun()
            st.divider()

# --- TAB RELATÓRIOS ---
with tab_relat:
    st.session_state.df = carregar_aba("lancamentos", cols_fin)
    df_user = st.session_state.df[st.session_state.df['Usuario'] == user]
    df_v = df_user[df_user['Status'] != "Recusado"]
    if not df_v.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🏢 Empresa (PJ)")
            df_pj_r = df_v[df_v['Ambiente'] == "Empresa"]
            if not df_pj_r.empty: st.plotly_chart(px.pie(df_pj_r, values='Valor', names='Categoria', hole=.4, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
        with c2:
            st.markdown("### 🏠 Pessoal (PF)")
            df_pf_r = df_v[df_v['Ambiente'] == "Pessoal"]
            if not df_pf_r.empty: st.plotly_chart(px.pie(df_pf_r, values='Valor', names='Categoria', hole=.4, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
    else: st.info("Sem dados.")

# --- SAIR ---
with tab_conf:
    if st.button("Sair"):
        st.session_state.clear(); st.rerun()
