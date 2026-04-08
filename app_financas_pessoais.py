import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

APP_TITLE = "Finanças da Casa"
DB_PATH = Path(__file__).with_name("financas_casa.db")

st.set_page_config(page_title=APP_TITLE, page_icon="💰", layout="wide")


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


conn = get_connection()


def init_db() -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            tipo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            descricao TEXT,
            valor REAL NOT NULL,
            natureza TEXT NOT NULL,
            observacao TEXT,
            criado_em TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS categorias_fixas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            tipo TEXT NOT NULL,
            valor_padrao REAL NOT NULL DEFAULT 0,
            dia_vencimento INTEGER,
            ativa INTEGER NOT NULL DEFAULT 1,
            criada_em TEXT NOT NULL
        )
        """
    )
    conn.commit()


DEFAULT_FIXED = [
    ("Aluguel / Financiamento", "Despesa Fixa", 1200.0, 5),
    ("Energia", "Despesa Fixa", 250.0, 10),
    ("Água", "Despesa Fixa", 90.0, 12),
    ("Internet", "Despesa Fixa", 120.0, 15),
    ("Escola / Creche", "Despesa Fixa", 450.0, 7),
]


DEFAULT_TRANS = [
    (date.today().replace(day=1).isoformat(), "Receita", "Salário", "Salário principal", 4500.0, "Variável", "Exemplo", datetime.now().isoformat()),
    (date.today().replace(day=2).isoformat(), "Despesa", "Supermercado", "Compra do mês", 780.0, "Variável", "Exemplo", datetime.now().isoformat()),
    (date.today().replace(day=5).isoformat(), "Despesa", "Aluguel / Financiamento", "Pagamento mensal", 1200.0, "Fixa", "Exemplo", datetime.now().isoformat()),
]


def seed_initial_data() -> None:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM categorias_fixas")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            """
            INSERT INTO categorias_fixas (nome, tipo, valor_padrao, dia_vencimento, ativa, criada_em)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            [(nome, tipo, valor, dia, datetime.now().isoformat()) for nome, tipo, valor, dia in DEFAULT_FIXED],
        )

    cur.execute("SELECT COUNT(*) FROM transacoes")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            """
            INSERT INTO transacoes (data, tipo, categoria, descricao, valor, natureza, observacao, criado_em)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            DEFAULT_TRANS,
        )
    conn.commit()


@st.cache_data(show_spinner=False)
def load_transacoes() -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM transacoes ORDER BY data DESC, id DESC", conn)
    if df.empty:
        return df
    df["data"] = pd.to_datetime(df["data"])
    df["mes"] = df["data"].dt.to_period("M").astype(str)
    return df


@st.cache_data(show_spinner=False)
def load_categorias_fixas() -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM categorias_fixas ORDER BY nome", conn)
    return df


def clear_cache() -> None:
    load_transacoes.clear()
    load_categorias_fixas.clear()


def moeda(valor: float) -> str:
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


init_db()
seed_initial_data()

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
    .stMetric {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 10px;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("💰 Finanças da Casa")
st.caption("Controle seu financeiro pessoal direto no app: receitas, despesas, saldo, gastos fixos e variáveis.")

with st.sidebar:
    st.header("Configurações")
    pagina = st.radio(
        "Ir para",
        ["Dashboard", "Lançamentos", "Despesas Fixas", "Histórico"],
        label_visibility="collapsed",
    )
    st.divider()
    hoje = date.today()
    mes_referencia = st.selectbox(
        "Mês de referência",
        options=sorted(load_transacoes()["mes"].unique().tolist(), reverse=True) if not load_transacoes().empty else [hoje.strftime("%Y-%m")],
    )

transacoes = load_transacoes()
fixas = load_categorias_fixas()

if not transacoes.empty:
    base_mes = transacoes[transacoes["mes"] == mes_referencia].copy()
else:
    base_mes = pd.DataFrame(columns=["tipo", "valor", "categoria", "data", "descricao", "natureza"])

receitas = float(base_mes.loc[base_mes["tipo"] == "Receita", "valor"].sum()) if not base_mes.empty else 0.0
despesas = float(base_mes.loc[base_mes["tipo"] == "Despesa", "valor"].sum()) if not base_mes.empty else 0.0
saldo = receitas - despesas
fixas_mes = float(base_mes.loc[(base_mes["tipo"] == "Despesa") & (base_mes["natureza"] == "Fixa"), "valor"].sum()) if not base_mes.empty else 0.0
variaveis_mes = float(base_mes.loc[(base_mes["tipo"] == "Despesa") & (base_mes["natureza"] == "Variável"), "valor"].sum()) if not base_mes.empty else 0.0

if pagina == "Dashboard":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receitas do mês", moeda(receitas))
    c2.metric("Despesas do mês", moeda(despesas))
    c3.metric("Saldo do mês", moeda(saldo))
    c4.metric("Despesas fixas", moeda(fixas_mes))

    c5, c6 = st.columns([1.2, 1])
    with c5:
        st.subheader("Resumo por categoria")
        if base_mes.empty:
            st.info("Ainda não há lançamentos no mês selecionado.")
        else:
            despesas_cat = (
                base_mes[base_mes["tipo"] == "Despesa"]
                .groupby("categoria", as_index=False)["valor"]
                .sum()
                .sort_values("valor", ascending=False)
            )
            fig_cat = px.bar(despesas_cat, x="categoria", y="valor", text="valor")
            fig_cat.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
            fig_cat.update_layout(height=380, xaxis_title="", yaxis_title="Valor")
            st.plotly_chart(fig_cat, use_container_width=True)

    with c6:
        st.subheader("Fixo x Variável")
        if fixas_mes + variaveis_mes == 0:
            st.info("Sem despesas lançadas neste mês.")
        else:
            pie_df = pd.DataFrame(
                {
                    "tipo": ["Fixas", "Variáveis"],
                    "valor": [fixas_mes, variaveis_mes],
                }
            )
            fig_pie = px.pie(pie_df, names="tipo", values="valor", hole=0.55)
            fig_pie.update_layout(height=380)
            st.plotly_chart(fig_pie, use_container_width=True)

    st.subheader("Últimos lançamentos")
    if transacoes.empty:
        st.info("Nenhum lançamento cadastrado ainda.")
    else:
        exibir = transacoes[["data", "tipo", "categoria", "descricao", "valor", "natureza"]].copy()
        exibir["data"] = exibir["data"].dt.strftime("%d/%m/%Y")
        exibir["valor"] = exibir["valor"].apply(moeda)
        st.dataframe(exibir.head(10), use_container_width=True, hide_index=True)

elif pagina == "Lançamentos":
    st.subheader("Adicionar receita ou despesa")
    categorias_fixas_ativas = fixas.loc[fixas["ativa"] == 1, "nome"].tolist() if not fixas.empty else []
    categorias_padrao = [
        "Salário", "Freelance", "Venda", "Supermercado", "Transporte", "Saúde", "Lazer", "Educação", "Cartão de crédito", "Outros"
    ]
    categorias = sorted(set(categorias_padrao + categorias_fixas_ativas))

    with st.form("form_lancamento", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        data = col1.date_input("Data", value=date.today())
        tipo = col2.selectbox("Tipo", ["Despesa", "Receita"])
        natureza = col3.selectbox("Natureza", ["Variável", "Fixa"])

        col4, col5 = st.columns([2, 1])
        categoria = col4.selectbox("Categoria", categorias)
        valor = col5.number_input("Valor", min_value=0.0, step=10.0, format="%.2f")

        descricao = st.text_input("Descrição")
        observacao = st.text_area("Observação")
        salvar = st.form_submit_button("Salvar lançamento", use_container_width=True)

        if salvar:
            if valor <= 0:
                st.error("Informe um valor maior que zero.")
            else:
                conn.execute(
                    """
                    INSERT INTO transacoes (data, tipo, categoria, descricao, valor, natureza, observacao, criado_em)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (data.isoformat(), tipo, categoria, descricao, float(valor), natureza, observacao, datetime.now().isoformat()),
                )
                conn.commit()
                clear_cache()
                st.success("Lançamento salvo com sucesso.")
                st.rerun()

    st.divider()
    st.subheader("Adicionar rápido uma despesa fixa ao mês atual")
    if fixas.empty:
        st.info("Cadastre pelo menos uma despesa fixa para usar esse atalho.")
    else:
        with st.form("form_fixa_rapida"):
            fixa_nome = st.selectbox("Despesa fixa", fixas["nome"].tolist())
            fixa_sel = fixas[fixas["nome"] == fixa_nome].iloc[0]
            fixa_data = st.date_input("Data do lançamento", value=date.today())
            fixa_valor = st.number_input(
                "Valor",
                min_value=0.0,
                value=float(fixa_sel["valor_padrao"]),
                step=10.0,
                format="%.2f",
                key="fixa_valor"
            )
            incluir_fixa = st.form_submit_button("Lançar despesa fixa", use_container_width=True)
            if incluir_fixa:
                conn.execute(
                    """
                    INSERT INTO transacoes (data, tipo, categoria, descricao, valor, natureza, observacao, criado_em)
                    VALUES (?, 'Despesa', ?, ?, ?, 'Fixa', ?, ?)
                    """,
                    (fixa_data.isoformat(), fixa_nome, f"Despesa fixa - {fixa_nome}", float(fixa_valor), "Gerada pelo atalho", datetime.now().isoformat()),
                )
                conn.commit()
                clear_cache()
                st.success("Despesa fixa lançada com sucesso.")
                st.rerun()

elif pagina == "Despesas Fixas":
    st.subheader("Cadastrar e manter despesas fixas")
    with st.form("form_cadastro_fixa", clear_on_submit=True):
        f1, f2, f3 = st.columns([2, 1, 1])
        nome = f1.text_input("Nome da despesa fixa")
        valor_padrao = f2.number_input("Valor padrão", min_value=0.0, step=10.0, format="%.2f")
        vencimento = f3.number_input("Dia do vencimento", min_value=1, max_value=31, step=1)
        salvar_fixa = st.form_submit_button("Salvar despesa fixa", use_container_width=True)
        if salvar_fixa:
            if not nome.strip():
                st.error("Informe um nome para a despesa fixa.")
            else:
                try:
                    conn.execute(
                        """
                        INSERT INTO categorias_fixas (nome, tipo, valor_padrao, dia_vencimento, ativa, criada_em)
                        VALUES (?, 'Despesa Fixa', ?, ?, 1, ?)
                        """,
                        (nome.strip(), float(valor_padrao), int(vencimento), datetime.now().isoformat()),
                    )
                    conn.commit()
                    clear_cache()
                    st.success("Despesa fixa cadastrada com sucesso.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Já existe uma despesa fixa com esse nome.")

    st.divider()
    st.subheader("Lista de despesas fixas")
    if fixas.empty:
        st.info("Nenhuma despesa fixa cadastrada ainda.")
    else:
        fixas_view = fixas[["nome", "valor_padrao", "dia_vencimento", "ativa"]].copy()
        fixas_view["valor_padrao"] = fixas_view["valor_padrao"].apply(moeda)
        fixas_view["ativa"] = fixas_view["ativa"].map({1: "Sim", 0: "Não"})
        st.dataframe(fixas_view, use_container_width=True, hide_index=True)

elif pagina == "Histórico":
    st.subheader("Histórico completo")
    if transacoes.empty:
        st.info("Sem histórico ainda.")
    else:
        filtro_tipo = st.multiselect("Filtrar por tipo", ["Receita", "Despesa"], default=["Receita", "Despesa"])
        filtro_nat = st.multiselect("Filtrar por natureza", ["Fixa", "Variável"], default=["Fixa", "Variável"])
        texto = st.text_input("Buscar descrição ou categoria")

        hist = transacoes.copy()
        hist = hist[hist["tipo"].isin(filtro_tipo)]
        hist = hist[hist["natureza"].isin(filtro_nat)]
        if texto.strip():
            texto_lower = texto.lower()
            hist = hist[
                hist["categoria"].str.lower().str.contains(texto_lower, na=False)
                | hist["descricao"].fillna("").str.lower().str.contains(texto_lower, na=False)
            ]

        total_hist = float(hist["valor"].sum()) if not hist.empty else 0.0
        st.caption(f"{len(hist)} lançamento(s) encontrados | Total filtrado: {moeda(total_hist)}")

        hist_view = hist[["data", "tipo", "categoria", "descricao", "valor", "natureza", "observacao"]].copy()
        hist_view["data"] = hist_view["data"].dt.strftime("%d/%m/%Y")
        hist_view["valor"] = hist_view["valor"].apply(moeda)
        st.dataframe(hist_view, use_container_width=True, hide_index=True)

        csv = hist.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Baixar histórico em CSV",
            data=csv,
            file_name="historico_financeiro.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.divider()
st.markdown(
    "**Estrutura pensada com base em padrões comuns de apps financeiros:** categorias, metas mentais por tipo de gasto, visão de fluxo do mês, despesas recorrentes e acompanhamento do saldo."
)
