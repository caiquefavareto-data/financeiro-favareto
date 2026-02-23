import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px
import hashlib

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Gestor Pro - Elevadores", layout="wide")

ARQUIVO_DADOS = "dados_financeiros.csv"
ARQUIVO_CARTOES = "meus_cartoes.csv"
ARQUIVO_CLIENTES = "meus_clientes.csv"
ARQUIVO_ACESSOS = "meus_acessos.csv"

# --- 2. FUNÇÕES DE DADOS ---
def carregar_dados(arquivo, colunas):
    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo)
        for col in colunas:
            if col not in df.columns:
                df[col] = "Não" if col == "Cartao" else ("N/A" if col == "Cliente" else "")
        if not df.empty and 'Data_Vencimento' in df.columns:
            df['Data_Vencimento'] = pd.to_datetime(df['Data_Vencimento']).dt.date
        return df
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, arquivo):
    df.to_csv(arquivo, index=False)

def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

# --- 3. TELA DE ACESSO ---
if "autenticado" not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏗️ Gestor Pro</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        opcao = st.radio("Escolha:", ["Fazer Login", "Primeiro acesso?"], horizontal=True)
        df_acessos = carregar_dados(ARQUIVO_ACESSOS, ["Usuario", "Senha"])
        if opcao == "Fazer Login":
            u_login = st.text_input("Usuário").strip()
            p_login = st.text_input("Senha", type="password")
            if st.button("Acessar", use_container_width=True):
                if (u_login == "Caique" and p_login == "11") or not df_acessos[(df_acessos["Usuario"] == u_login) & (df_acessos["Senha"] == hash_senha(p_login))].empty:
                    st.session_state.autenticado = True
                    st.session_state.usuario = u_login
                    st.rerun()
                else: st.error("Usuário ou senha incorretos.")
        else:
            u_novo = st.text_input("Nome")
            p_novo = st.text_input("Senha", type="password")
            if st.button("Cadastrar", use_container_width=True):
                if u_novo and p_novo:
                    nova = pd.DataFrame([{"Usuario": u_novo, "Senha": hash_senha(p_novo)}])
                    salvar_dados(pd.concat([df_acessos, nova]), ARQUIVO_ACESSOS)
                    st.success("Pronto! Faça o login.")
    st.stop()

# --- 4. CARREGAMENTO PÓS-LOGIN ---
user = st.session_state.usuario
if 'df' not in st.session_state: st.session_state.df = carregar_dados(ARQUIVO_DADOS, ["OS", "NF", "Data_Vencimento", "Ambiente", "Tipo_Fluxo", "Descricao", "Categoria", "Valor", "Status", "Cliente", "Usuario", "Cartao", "Detalhes"])
if 'cartoes' not in st.session_state: st.session_state.cartoes = carregar_dados(ARQUIVO_CARTOES, ["Nome", "Limite_Total", "Usuario"])
if 'clientes' not in st.session_state: st.session_state.clientes = carregar_dados(ARQUIVO_CLIENTES, ["Nome", "Usuario"])

df_user = st.session_state.df[st.session_state.df['Usuario'] == user]
cartoes_user = st.session_state.cartoes[st.session_state.cartoes['Usuario'] == user]
clientes_user = st.session_state.clientes[st.session_state.clientes['Usuario'] == user]

st.markdown(f"#### 👤 {user}")
tab_lanc, tab_cartoes, tab_clientes, tab_relat, tab_conf = st.tabs(["📝 Lançamentos", "💳 Cartões", "👥 Clientes", "📈 Relatórios", "⚙️ Opções"])

# --- ABA LANÇAMENTOS (Mesma lógica robusta) ---
with tab_lanc:
    col_f, col_g = st.columns([2, 1])
    with col_f:
        with st.expander("➕ Novo Registro"):
            c1, c2 = st.columns(2)
            with c1:
                ambiente = st.radio("Destino", ["Empresa", "Pessoal"], horizontal=True)
                tipo = st.selectbox("Tipo", ["Saída (Pagamento)", "Entrada (Recebimento)"])
                data_base = st.date_input("Vencimento", datetime.now())
                os_num = st.text_input("Nº OS")
                cliente_sel = st.selectbox("Cliente", ["N/A"] + sorted(clientes_user["Nome"].tolist()))
                cat_opcoes = sorted(["Carro Combustível", "Carro Multa", "Carro Pedágio", "Escola", "Farmácia", "Imposto", "Manutenção Preventiva", "Material", "Mercado", "Pagamento", "Peças Elevador", "Outros"])
                categoria_sel = st.selectbox("Categoria", cat_opcoes)
                categoria_final = st.text_input("Especifique") if categoria_sel == "Outros" else categoria_sel
            with c2:
                nf_num = st.text_input("Nº NF")
                descricao = st.text_input("Descrição")
                valor_parc = st.number_input("Valor (R$)", min_value=0.0)
                qtd_parcelas = st.number_input("Parcelas", min_value=1, value=1)
                pag_cartao = st.selectbox("Pagto/Cartão", ["Pix", "Boleto", "Dinheiro"] + cartoes_user["Nome"].tolist())
                status = st.selectbox("Status", ["Pendente", "Concluído", "Recusado"])
            if st.button("Gravar", use_container_width=True):
                id_base = os_num if os_num.strip() != "" else datetime.now().strftime("%Y%m%d%H%M%S")
                novos = []
                for i in range(qtd_parcelas):
                    novos.append({"OS": id_base if qtd_parcelas == 1 else f"{id_base}-{i+1}", "NF": nf_num, "Data_Vencimento": data_base + timedelta(days=30*i), "Ambiente": ambiente, "Tipo_Fluxo": tipo, "Descricao": descricao, "Categoria": categoria_final, "Valor": valor_parc, "Status": status, "Cliente": cliente_sel, "Usuario": user, "Cartao": pag_cartao, "Detalhes": ""})
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame(novos)], ignore_index=True)
                salvar_dados(st.session_state.df, ARQUIVO_DADOS); st.rerun()

    with col_g:
        df_at = df_user[df_user['Status'] != "Recusado"]
        s_emp = df_at[df_at['Ambiente'] == "Empresa"][df_at['Tipo_Fluxo'] == 'Entrada (Recebimento)']['Valor'].sum() - df_at[df_at['Ambiente'] == "Empresa"][df_at['Tipo_Fluxo'] == 'Saída (Pagamento)']['Valor'].sum()
        s_pes = df_at[df_at['Ambiente'] == "Pessoal"][df_at['Tipo_Fluxo'] == 'Entrada (Recebimento)']['Valor'].sum() - df_at[df_at['Ambiente'] == "Pessoal"][df_at['Tipo_Fluxo'] == 'Saída (Pagamento)']['Valor'].sum()
        st.metric("PJ", f"R$ {s_emp:,.2f}"); st.metric("PF", f"R$ {s_pes:,.2f}")
        st.plotly_chart(px.pie(df_user, values='Valor', names='Status', hole=.6, color='Status', color_discrete_map={'Concluído':'#00CC96', 'Pendente':'#FFA15A', 'Recusado':'#EF553B'}).update_layout(showlegend=False, height=140, margin=dict(t=0,b=0,l=0,r=0)), use_container_width=True)

    st.divider()
    # Filtros e Tabela Principal
    c_b, c_f, c_h = st.columns([2,1,1])
    termo = c_b.text_input("🔍 Buscar")
    m_h = c_h.checkbox("Histórico")
    df_t = df_user.copy().sort_values("Data_Vencimento")
    if not termo and not m_h: df_t = df_t[df_t['Data_Vencimento'] >= datetime.now().date().replace(day=1)]
    if termo: df_t = df_t[df_t.astype(str).apply(lambda x: x.str.contains(termo, case=False)).any(axis=1)]
    
    edit_df = st.data_editor(df_t[["Data_Vencimento", "OS", "Status", "Cliente", "Descricao", "Valor"]], hide_index=True, use_container_width=True)

# --- 👥 ABA CLIENTES (SUTIL) ---
with tab_clientes:
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.form("add_cli", clear_on_submit=True):
            n_c = st.text_input("Novo Cliente")
            if st.form_submit_button("Cadastrar"):
                if n_c:
                    st.session_state.clientes = pd.concat([st.session_state.clientes, pd.DataFrame([{"Nome": n_c, "Usuario": user}])], ignore_index=True)
                    salvar_dados(st.session_state.clientes, ARQUIVO_CLIENTES); st.rerun()
    with c2:
        st.write("🗑️ **Excluir Clientes**")
        for idx, row in clientes_user.iterrows():
            col_n, col_b = st.columns([3, 1])
            col_n.write(f"• {row['Nome']}")
            if col_b.button("Apagar", key=f"del_cli_{idx}"):
                st.session_state.clientes = st.session_state.clientes.drop(idx)
                salvar_dados(st.session_state.clientes, ARQUIVO_CLIENTES); st.rerun()

# --- 💳 ABA CARTÕES (SUTIL) ---
with tab_cartoes:
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.form("add_card", clear_on_submit=True):
            n, l = st.text_input("Cartão"), st.number_input("Limite", min_value=1.0)
            if st.form_submit_button("Cadastrar"):
                st.session_state.cartoes = pd.concat([st.session_state.cartoes, pd.DataFrame([{"Nome": n, "Limite_Total": l, "Usuario": user}])], ignore_index=True)
                salvar_dados(st.session_state.cartoes, ARQUIVO_CARTOES); st.rerun()
    with c2:
        st.write("🗑️ **Gerenciar Cartões**")
        for idx, row in cartoes_user.iterrows():
            col_n, col_b = st.columns([3, 1])
            col_n.write(f"💳 {row['Nome']}")
            if col_b.button("Remover", key=f"del_car_{idx}"):
                st.session_state.cartoes = st.session_state.cartoes.drop(idx)
                salvar_dados(st.session_state.cartoes, ARQUIVO_CARTOES); st.rerun()
            u = df_user[(df_user['Cartao'] == row['Nome']) & (df_user['Tipo_Fluxo'] == 'Saída (Pagamento)')]['Valor'].sum()
            st.progress(max(0.0, min(u / row['Limite_Total'], 1.0)))

# --- 📈 ABA RELATÓRIOS ---
with tab_relat:
    df_v = df_user[df_user['Status'] != "Recusado"]
    if not df_v.empty:
        st.plotly_chart(px.pie(df_v, values='Valor', names='Tipo_Fluxo', hole=.5, color='Tipo_Fluxo', color_discrete_map={'Entrada (Recebimento)': '#2ECC71', 'Saída (Pagamento)': '#E74C3C'}, title="Balanço Geral"), use_container_width=True)
        c_e, c_p = st.columns(2)
        df_s = df_v[df_v['Tipo_Fluxo'] == 'Saída (Pagamento)']
        c_e.plotly_chart(px.pie(df_s[df_s['Ambiente']=="Empresa"], values='Valor', names='Categoria', hole=.4, title="Empresa", color_discrete_sequence=px.colors.qualitative.Bold), use_container_width=True)
        c_p.plotly_chart(px.pie(df_s[df_s['Ambiente']=="Pessoal"], values='Valor', names='Categoria', hole=.4, title="Pessoal", color_discrete_sequence=px.colors.qualitative.Bold), use_container_width=True)

with tab_conf:
    if st.button("Sair"):
        st.session_state.clear(); st.rerun()
