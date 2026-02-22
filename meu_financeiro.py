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

# --- 2. FUNÇÕES DE DADOS E SEGURANÇA ---
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

# --- 3. INTERFACE DE ENTRADA SIMPLIFICADA (SEM E-MAIL) ---
def tela_acesso():
    if "autenticado" not in st.session_state:
        st.markdown("<h1 style='text-align: center; color: #1E88E5;'>🏗️ Gestor Pro</h1>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.markdown("---")
            opcao = st.radio("Escolha uma opção:", ["Fazer Login", "Primeiro acesso?"], horizontal=True)
            
            # Carrega acessos (colunas apenas Usuário e Senha)
            df_acessos = carregar_dados(ARQUIVO_ACESSOS, ["Usuario", "Senha"])

            if opcao == "Fazer Login":
                u_login = st.text_input("Usuário").strip()
                p_login = st.text_input("Senha", type="password")
                
                if st.button("Acessar Sistema", use_container_width=True):
                    # Login mestre padrão
                    if u_login == "Caique" and p_login == "11":
                        st.session_state.autenticado = True
                        st.session_state.usuario = u_login
                        st.rerun()
                    
                    # Verificação no banco de dados
                    sh = hash_senha(p_login)
                    match = df_acessos[(df_acessos["Usuario"] == u_login) & (df_acessos["Senha"] == sh)]
                    if not match.empty:
                        st.session_state.autenticado = True
                        st.session_state.usuario = u_login
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")

            else: # Primeiro Acesso
                st.subheader("Cadastrar Novo Usuário")
                u_novo = st.text_input("Escolha seu Nome de Usuário").strip()
                p_novo = st.text_input("Escolha sua Senha", type="password")
                p_conf = st.text_input("Confirme a Senha", type="password")
                
                if st.button("Salvar Cadastro", use_container_width=True):
                    if u_novo and p_novo:
                        if p_novo == p_conf:
                            if u_novo in df_acessos["Usuario"].values:
                                st.warning("Este usuário já existe.")
                            else:
                                nova_conta = pd.DataFrame([{"Usuario": u_novo, "Senha": hash_senha(p_novo)}])
                                df_acessos = pd.concat([df_acessos, nova_conta], ignore_index=True)
                                salvar_dados(df_acessos, ARQUIVO_ACESSOS)
                                st.success("Usuário cadastrado com sucesso! Mude para 'Fazer Login'.")
                        else:
                            st.error("As senhas não conferem.")
                    else:
                        st.error("Preencha todos os campos.")
        return False
    return True

if not tela_acesso():
    st.stop()

# --- 4. INICIALIZAÇÃO PÓS-LOGIN ---
user = st.session_state.usuario

if 'df' not in st.session_state:
    st.session_state.df = carregar_dados(ARQUIVO_DADOS, ["OS", "NF", "Data_Vencimento", "Ambiente", "Tipo_Fluxo", "Descricao", "Categoria", "Valor", "Status", "Cliente", "Usuario", "Cartao", "Detalhes"])
if 'cartoes' not in st.session_state:
    st.session_state.cartoes = carregar_dados(ARQUIVO_CARTOES, ["Nome", "Limite_Total", "Usuario"])
if 'clientes' not in st.session_state:
    st.session_state.clientes = carregar_dados(ARQUIVO_CLIENTES, ["Nome", "Usuario"])

# Filtros por Usuário
df_user = st.session_state.df[st.session_state.df['Usuario'] == user]
cartoes_user = st.session_state.cartoes[st.session_state.cartoes['Usuario'] == user]
clientes_user = st.session_state.clientes[st.session_state.clientes['Usuario'] == user]

# --- 5. INTERFACE DO SISTEMA (DASHBOARD) ---
st.markdown(f"#### 👤 Usuário: {user}")

tab_lanc, tab_cartoes, tab_clientes, tab_relat, tab_conf = st.tabs([
    "📝 Lançamentos", "💳 Cartões", "👥 Clientes", "📈 Relatórios", "⚙️ Opções"
])

with tab_lanc:
    col_f, col_g = st.columns([2, 1])
    with col_f:
        with st.expander("➕ Novo Registro", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                ambiente = st.radio("Destino", ["Empresa", "Pessoal"], horizontal=True)
                tipo = st.selectbox("Tipo", ["Saída (Pagamento)", "Entrada (Recebimento)"])
                data_base = st.date_input("Vencimento", datetime.now())
                os_num = st.text_input("Nº OS")
                cliente_sel = st.selectbox("Cliente", ["N/A"] + sorted(clientes_user["Nome"].tolist()))
                cat_opcoes = sorted(["Carro Combustível", "Carro Multa", "Carro Pedágio", "Escola", "Farmácia", "Imposto", "Manutenção Preventiva", "Material", "Mercado", "Peças Elevador", "Outros"])
                categoria_sel = st.selectbox("Categoria", cat_opcoes)
                categoria_final = st.text_input("Especifique") if categoria_sel == "Outros" else categoria_sel
            with c2:
                nf_num = st.text_input("Nº NF")
                descricao = st.text_input("Descrição Curta")
                valor_parc = st.number_input("Valor (R$)", min_value=0.0)
                qtd_parcelas = st.number_input("Parcelas", min_value=1, value=1)
                metodos = ["Pix", "Boleto", "Transferência", "Dinheiro"]
                pag_cartao = st.selectbox("Pagto/Cartão", metodos + cartoes_user["Nome"].tolist())
                status = st.selectbox("Status", ["Pendente", "Concluído", "Recusado"])
            
            detalhes = st.text_area("Observações")
            if st.button("Gravar Registro", use_container_width=True):
                id_base = os_num if os_num.strip() != "" else datetime.now().strftime("%Y%m%d%H%M%S")
                novos = []
                for i in range(qtd_parcelas):
                    data_parc = data_base + timedelta(days=30*i)
                    novos.append({
                        "OS": id_base if qtd_parcelas == 1 else f"{id_base}-{i+1}",
                        "NF": nf_num, "Data_Vencimento": data_parc, "Ambiente": ambiente, 
                        "Tipo_Fluxo": tipo, "Descricao": descricao, "Categoria": categoria_final,
                        "Valor": valor_parc, "Status": status, "Cliente": cliente_sel, 
                        "Usuario": user, "Cartao": pag_cartao, "Detalhes": detalhes
                    })
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame(novos)], ignore_index=True)
                salvar_dados(st.session_state.df, ARQUIVO_DADOS)
                st.rerun()

    with col_g:
        if not df_user.empty:
            df_at = df_user[df_user['Status'] != "Recusado"]
            receita = df_at[df_at['Tipo_Fluxo'] == 'Entrada (Recebimento)']['Valor'].sum()
            despesa = df_at[df_at['Tipo_Fluxo'] == 'Saída (Pagamento)']['Valor'].sum()
            st.metric("Saldo Real", f"R$ {receita - despesa:,.2f}")
            fig = px.pie(df_user, values='Valor', names='Status', hole=.6, color_discrete_map={'Concluído':'#00CC96', 'Pendente':'#FFA15A', 'Recusado':'#EF553B'})
            fig.update_layout(showlegend=False, height=140, margin=dict(t=0,b=0,l=0,r=0))
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- FILTRO E BUSCA ---
    c_busca, c_filtro, c_hist = st.columns([2, 1, 1])
    with c_busca: termo_b = st.text_input("🔍 Pesquisa (OS, NF ou Cliente)")
    with c_filtro: v_opt = st.radio("Filtro:", ["Tudo", "Empresa", "Pessoal"], horizontal=True)
    with c_hist: m_hist = st.checkbox("Histórico Antigo")

    hoje = datetime.now().date()
    df_t = df_user.copy().sort_values(by="Data_Vencimento")
    if not termo_b and not m_hist:
        df_t = df_t[df_t['Data_Vencimento'] >= hoje.replace(day=1)]
    if v_opt != "Tudo": df_t = df_t[df_t['Ambiente'] == v_opt]
    if termo_b:
        df_t = df_t[(df_t['OS'].astype(str).str.contains(termo_b, case=False)) | (df_t['NF'].astype(str).str.contains(termo_b, case=False)) | (df_t['Cliente'].astype(str).str.contains(termo_b, case=False))]

    col_tab, col_ed = st.columns([2, 1])
    with col_tab:
        df_disp = df_t.copy()
        df_disp.insert(0, "Sel.", False)
        edit = st.data_editor(df_disp[["Sel.", "Data_Vencimento", "OS", "Status", "Cliente", "Descricao", "Valor"]], hide_index=True, use_container_width=True)
        if st.button("🗑️ Excluir Selecionados"):
            oss_r = edit[edit["Sel."] == True]["OS"].tolist()
            st.session_state.df = st.session_state.df[~st.session_state.df["OS"].isin(oss_r)]
            salvar_dados(st.session_state.df, ARQUIVO_DADOS)
            st.rerun()

    with col_ed:
        st.subheader("📑 Edição")
        os_sel = st.selectbox("Escolha a OS:", ["---"] + df_t["OS"].tolist())
        if os_sel != "---":
            inf = df_user[df_user["OS"] == os_sel].iloc[0]
            with st.container(border=True):
                nv_venc = st.date_input("Vencimento", inf['Data_Vencimento'])
                nv_val = st.number_input("Valor", value=float(inf['Valor']))
                nv_st = st.selectbox("Status", ["Pendente", "Concluído", "Recusado"], index=["Pendente", "Concluído", "Recusado"].index(inf['Status']))
                if st.button("Confirmar"):
                    idx = st.session_state.df[st.session_state.df["OS"] == os_sel].index
                    st.session_state.df.at[idx[0], "Data_Vencimento"], st.session_state.df.at[idx[0], "Valor"], st.session_state.df.at[idx[0], "Status"] = nv_venc, nv_val, nv_st
                    salvar_dados(st.session_state.df, ARQUIVO_DADOS)
                    st.rerun()
                st.info(inf['Detalhes'])

with tab_clientes:
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("add_cli"):
            n_c = st.text_input("Novo Cliente")
            if st.form_submit_button("✅ Cadastrar"):
                if n_c:
                    new = pd.DataFrame([{"Nome": n_c, "Usuario": user}])
                    st.session_state.clientes = pd.concat([st.session_state.clientes, new], ignore_index=True)
                    salvar_dados(st.session_state.clientes, ARQUIVO_CLIENTES)
                    st.rerun()
    with c2: st.dataframe(clientes_user[["Nome"]], use_container_width=True, hide_index=True)

with tab_cartoes:
    c1, c2 = st.columns([1, 2])
    with c1:
        with st.form("add_card"):
            n, l = st.text_input("Cartão"), st.number_input("Limite")
            if st.form_submit_button("✅ Adicionar"):
                new = pd.DataFrame([{"Nome": n, "Limite_Total": l, "Usuario": user}])
                st.session_state.cartoes = pd.concat([st.session_state.cartoes, new], ignore_index=True)
                salvar_dados(st.session_state.cartoes, ARQUIVO_CARTOES)
                st.rerun()
    with c2:
        for _, r in cartoes_user.iterrows():
            u = df_user[(df_user['Cartao'] == r['Nome']) & (df_user['Status'] != 'Recusado')]['Valor'].sum()
            st.write(f"**{r['Nome']}**"); st.progress(min(u/r['Limite_Total'], 1.0)); st.caption(f"Livre: R$ {r['Limite_Total']-u:,.2f}")

with tab_relat:
    c_e, c_p = st.columns(2)
    df_v = df_user[df_user['Status'] != "Recusado"]
    with c_e:
        df_m = df_v[df_v['Ambiente'] == "Empresa"]
        if not df_m.empty: st.plotly_chart(px.pie(df_m, values='Valor', names='Categoria', hole=.4, title="Empresa"), use_container_width=True)
    with c_p:
        df_h = df_v[df_v['Ambiente'] == "Pessoal"]
        if not df_h.empty: st.plotly_chart(px.pie(df_h, values='Valor', names='Categoria', hole=.4, title="Pessoal"), use_container_width=True)

with tab_conf:
    if st.button("🚪 Sair"):
        del st.session_state.autenticado
        st.rerun()