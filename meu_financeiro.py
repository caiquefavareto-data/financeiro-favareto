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
                df[col] = ""
        if not df.empty and 'Data_Vencimento' in df.columns:
            df['Data_Vencimento'] = pd.to_datetime(df['Data_Vencimento']).dt.date
        return df
    return pd.DataFrame(columns=colunas)

def salvar_dados(df, arquivo):
    df.to_csv(arquivo, index=False)

def hash_senha(senha):
    return hashlib.sha256(str.encode(senha)).hexdigest()

# --- 3. ACESSO ---
if "autenticado" not in st.session_state:
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏗️ Gestor Pro</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        opcao = st.radio("Escolha:", ["Login", "Cadastro"], horizontal=True)
        df_acessos = carregar_dados(ARQUIVO_ACESSOS, ["Usuario", "Senha"])
        u = st.text_input("Usuário").strip()
        p = st.text_input("Senha", type="password")
        if st.button("Entrar" if opcao == "Login" else "Cadastrar", use_container_width=True):
            if opcao == "Login":
                if (u == "Caique" and p == "11") or not df_acessos[(df_acessos["Usuario"] == u) & (df_acessos["Senha"] == hash_senha(p))].empty:
                    st.session_state.autenticado, st.session_state.usuario = True, u
                    st.rerun()
                else: st.error("Erro no login.")
            else:
                if u and p:
                    salvar_dados(pd.concat([df_acessos, pd.DataFrame([{"Usuario": u, "Senha": hash_senha(p)}])]), ARQUIVO_ACESSOS)
                    st.success("Cadastrado!")
    st.stop()

# --- 4. CARREGAMENTO ---
user = st.session_state.usuario
colunas_principais = ["OS", "NF", "Data_Vencimento", "Ambiente", "Tipo_Fluxo", "Descricao", "Categoria", "Valor", "Status", "Cliente", "Usuario", "Cartao", "Detalhes"]

if 'df' not in st.session_state: st.session_state.df = carregar_dados(ARQUIVO_DADOS, colunas_principais)
if 'cartoes' not in st.session_state: st.session_state.cartoes = carregar_dados(ARQUIVO_CARTOES, ["Nome", "Limite_Total", "Usuario"])
if 'clientes' not in st.session_state: st.session_state.clientes = carregar_dados(ARQUIVO_CLIENTES, ["Nome", "Usuario"])

df_user = st.session_state.df[st.session_state.df['Usuario'] == user]
cartoes_user = st.session_state.cartoes[st.session_state.cartoes['Usuario'] == user]
clientes_user = st.session_state.clientes[st.session_state.clientes['Usuario'] == user]

# --- 5. UI PRINCIPAL ---
st.markdown(f"#### 👤 {user}")
tab_lanc, tab_cartoes, tab_clientes, tab_relat, tab_conf = st.tabs(["📝 Lançamentos", "💳 Cartões", "👥 Clientes", "📈 Relatórios", "⚙️ Opções"])

with tab_lanc:
    col_f, col_g = st.columns([2, 1])
    with col_f:
        with st.expander("➕ NOVO LANÇAMENTO (Entrada/Saída)", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                ambiente = st.radio("Carteira", ["Empresa", "Pessoal"], horizontal=True)
                tipo = st.selectbox("Tipo", ["Saída (Pagamento)", "Entrada (Recebimento)"])
                data_v = st.date_input("Vencimento", datetime.now())
                os_n = st.text_input("Nº OS")
                cli = st.selectbox("Cliente", ["N/A"] + sorted(clientes_user["Nome"].tolist()))
                cat = st.selectbox("Categoria", sorted(["Carro", "Escola", "Imposto", "Material", "Peças", "Mercado", "Retirada", "Outros"]))
            with c2:
                nf_n = st.text_input("Nº NF")
                desc = st.text_input("O que é?")
                val = st.number_input("Valor R$", min_value=0.0)
                parc = st.number_input("Parcelas", min_value=1, value=1)
                metodo = st.selectbox("Forma de Pagto", ["Pix", "Boleto", "Dinheiro", "Débito"] + cartoes_user["Nome"].tolist())
                status = st.selectbox("Status", ["Pendente", "Concluído", "Recusado"])
            
            # CAMPO DE OBSERVAÇÃO QUE TINHA SUMIDO
            obs = st.text_area("Observações Adicionais (Detalhes do serviço, etc)")
            
            if st.button("Salvar Registro", use_container_width=True):
                novos = []
                for i in range(parc):
                    novos.append({"OS": os_n if parc==1 else f"{os_n}-{i+1}", "NF": nf_n, "Data_Vencimento": data_v + timedelta(days=30*i), "Ambiente": ambiente, "Tipo_Fluxo": tipo, "Descricao": desc, "Categoria": cat, "Valor": val, "Status": status, "Cliente": cli, "Usuario": user, "Cartao": metodo, "Detalhes": obs})
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame(novos)], ignore_index=True)
                salvar_dados(st.session_state.df, ARQUIVO_DADOS); st.rerun()

    with col_g:
        df_ok = df_user[df_user['Status'] != "Recusado"]
        s_pj = df_ok[df_ok['Ambiente'] == "Empresa"][df_ok['Tipo_Fluxo'] == 'Entrada (Recebimento)']['Valor'].sum() - df_ok[df_ok['Ambiente'] == "Empresa"][df_ok['Tipo_Fluxo'] == 'Saída (Pagamento)']['Valor'].sum()
        s_pf = df_ok[df_ok['Ambiente'] == "Pessoal"][df_ok['Tipo_Fluxo'] == 'Entrada (Recebimento)']['Valor'].sum() - df_ok[df_ok['Ambiente'] == "Pessoal"][df_ok['Tipo_Fluxo'] == 'Saída (Pagamento)']['Valor'].sum()
        st.metric("Saldo Empresa", f"R$ {s_pj:,.2f}"); st.metric("Saldo Pessoal", f"R$ {s_pf:,.2f}")

    st.divider()
    
    # --- HISTÓRICO COMPLETO ---
    st.subheader("📋 Histórico e Detalhes")
    c_busca, c_filtro = st.columns([3, 1])
    busca = c_busca.text_input("🔎 Pesquisar em tudo (OS, Cliente, Obs...)")
    ver_tudo = c_filtro.checkbox("Ver Histórico Antigo")
    
    df_h = df_user.copy().sort_values("Data_Vencimento", ascending=False)
    if not ver_tudo and not busca:
        df_h = df_h[df_h['Data_Vencimento'] >= datetime.now().date().replace(day=1)]
    if busca:
        df_h = df_h[df_h.astype(str).apply(lambda x: x.str.contains(busca, case=False)).any(axis=1)]
    
    # Exibição do Histórico
    if not df_h.empty:
        # Tabela interativa: Aqui você vê tudo de uma vez
        st.dataframe(df_h, use_container_width=True, hide_index=True)
        
        # Botão para excluir
        with st.expander("🗑️ Excluir Registros"):
            os_para_deletar = st.multiselect("Selecione a OS para apagar:", df_h["OS"].unique())
            if st.button("Confirmar Exclusão"):
                st.session_state.df = st.session_state.df[~st.session_state.df["OS"].isin(os_para_deletar)]
                salvar_dados(st.session_state.df, ARQUIVO_DADOS); st.rerun()
    else:
        st.info("Nenhum registro encontrado para este filtro.")

# --- CLIENTES ---
with tab_clientes:
    c1, c2 = st.columns(2)
    with c1:
        with st.form("cli"):
            n = st.text_input("Nome Cliente")
            if st.form_submit_button("Cadastrar"):
                st.session_state.clientes = pd.concat([st.session_state.clientes, pd.DataFrame([{"Nome": n, "Usuario": user}])], ignore_index=True)
                salvar_dados(st.session_state.clientes, ARQUIVO_CLIENTES); st.rerun()
    with c2:
        for idx, r in clientes_user.iterrows():
            col_a, col_b = st.columns([3, 1])
            col_a.write(r['Nome'])
            if col_b.button("Remover", key=f"c_{idx}"):
                st.session_state.clientes = st.session_state.clientes.drop(idx); salvar_dados(st.session_state.clientes, ARQUIVO_CLIENTES); st.rerun()

# --- CARTÕES ---
with tab_cartoes:
    c1, c2 = st.columns(2)
    with c1:
        with st.form("car"):
            n, l = st.text_input("Cartão"), st.number_input("Limite", min_value=1.0)
            if st.form_submit_button("Cadastrar"):
                st.session_state.cartoes = pd.concat([st.session_state.cartoes, pd.DataFrame([{"Nome": n, "Limite_Total": l, "Usuario": user}])], ignore_index=True)
                salvar_dados(st.session_state.cartoes, ARQUIVO_CARTOES); st.rerun()
    with c2:
        for idx, r in cartoes_user.iterrows():
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"💳 {r['Nome']}")
            if col_b.button("Remover", key=f"cc_{idx}"):
                st.session_state.cartoes = st.session_state.cartoes.drop(idx); salvar_dados(st.session_state.cartoes, ARQUIVO_CARTOES); st.rerun()
            u = df_user[(df_user['Cartao'] == r['Nome']) & (df_user['Tipo_Fluxo'] == 'Saída (Pagamento)')]['Valor'].sum()
            st.progress(max(0.0, min(u / r['Limite_Total'], 1.0)))

# --- RELATÓRIOS ---
with tab_relat:
    df_v = df_user[df_user['Status'] != "Recusado"]
    if not df_v.empty:
        st.plotly_chart(px.pie(df_v, values='Valor', names='Tipo_Fluxo', hole=.5, title="Balanço", color_discrete_map={'Entrada (Recebimento)': '#2ECC71', 'Saída (Pagamento)': '#E74C3C'}))
    else: st.info("Sem dados.")

with tab_conf:
    if st.button("Logoff"): st.session_state.clear(); st.rerun()
