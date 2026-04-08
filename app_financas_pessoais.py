import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

APP_TITLE = "Finanças da Casa"
DB_PATH = Path(__file__).with_name("financas_casa.db")
APP_COLORS = {
    "bg": "#F6F8FC",
    "card": "#FFFFFF",
    "card_alt": "#F8FAFC",
    "border": "#E5E7EB",
    "text": "#0F172A",
    "muted": "#64748B",
    "primary": "#2563EB",
    "primary_soft": "#DBEAFE",
    "success": "#16A34A",
    "success_soft": "#DCFCE7",
    "warning": "#D97706",
    "warning_soft": "#FEF3C7",
    "danger": "#DC2626",
    "danger_soft": "#FEE2E2",
    "info": "#0891B2",
    "info_soft": "#CFFAFE",
}

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

def percentual(valor: float) -> str:
    return f"{valor:.1f}%".replace(".", ",")


def render_fin_card(titulo: str, valor: str, subtitulo: str = "", classe: str = "card-saldo") -> str:
    return f"""
    <div class="fin-card {classe}">
        <div class="fin-card-title">{titulo}</div>
        <div class="fin-card-value">{valor}</div>
        <div class="fin-card-sub">{subtitulo}</div>
    </div>
    """


def render_alerta(tipo: str, titulo: str, texto: str) -> str:
    return f"""
    <div class="alert-box alert-{tipo}">
        <div class="alert-title">{titulo}</div>
        <div class="alert-text">{texto}</div>
    </div>
    """


def render_status_box(cor: str, titulo: str, valor: str, subtitulo: str) -> str:
    return f"""
    <div class="status-box status-{cor}">
        <div class="status-title">{titulo}</div>
        <div class="status-value">{valor}</div>
        <div class="status-sub">{subtitulo}</div>
    </div>
    """


def obter_status_financeiro(receitas: float, gastos_totais: float, resultado_mes: float, saldo: float) -> dict:
    comprometimento = (gastos_totais / receitas * 100) if receitas > 0 else (100.0 if gastos_totais > 0 else 0.0)

    if receitas <= 0 and gastos_totais > 0:
        return {
            "cor": "red",
            "titulo": "Semáforo financeiro",
            "valor": "Crítico",
            "subtitulo": "Você está sem receitas lançadas e já possui gastos no período.",
        }

    if comprometimento <= 70 and resultado_mes >= 0 and saldo >= 0:
        return {
            "cor": "green",
            "titulo": "Semáforo financeiro",
            "valor": "Saudável",
            "subtitulo": f"Comprometimento da receita em {percentual(comprometimento)}.",
        }

    if comprometimento <= 90 and saldo >= 0:
        return {
            "cor": "yellow",
            "titulo": "Semáforo financeiro",
            "valor": "Atenção",
            "subtitulo": f"Comprometimento da receita em {percentual(comprometimento)}.",
        }

    return {
        "cor": "red",
        "titulo": "Semáforo financeiro",
        "valor": "Crítico",
        "subtitulo": f"Comprometimento da receita em {percentual(comprometimento)} ou saldo/resultado pressionado.",
    }


def calcular_previsao_fechamento(
    mes_referencia: str,
    receitas: float,
    gastos_fixos_previstos: float,
    variaveis_mes: float,
) -> dict:
    hoje = date.today()
    mes_atual_str = hoje.strftime("%Y-%m")
    ano, mes = map(int, mes_referencia.split("-"))

    if mes == 12:
        prox_mes = date(ano + 1, 1, 1)
    else:
        prox_mes = date(ano, mes + 1, 1)

    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = (prox_mes - pd.Timedelta(days=1)).date() if hasattr(pd.Timedelta(days=1), "date") else date(ano, mes, 28)
    total_dias_mes = ultimo_dia.day

    if mes_referencia == mes_atual_str:
        dias_observados = max(hoje.day, 1)
    else:
        dias_observados = total_dias_mes

    media_diaria_variavel = variaveis_mes / dias_observados if dias_observados > 0 else 0.0
    projecao_variaveis = media_diaria_variavel * total_dias_mes
    projecao_gastos = gastos_fixos_previstos + projecao_variaveis
    projecao_resultado = receitas - projecao_gastos

    return {
        "dias_observados": dias_observados,
        "total_dias_mes": total_dias_mes,
        "media_diaria_variavel": media_diaria_variavel,
        "projecao_variaveis": projecao_variaveis,
        "projecao_gastos": projecao_gastos,
        "projecao_resultado": projecao_resultado,
    }


def calcular_alertas_financeiros(
    mes_referencia: str,
    fixas_ativas: pd.DataFrame,
    categorias_fixas_pagas: set,
    saldo: float,
    receitas: float,
    gastos_totais: float,
) -> list:
    alertas = []
    hoje = date.today()
    mes_atual_str = hoje.strftime("%Y-%m")

    if mes_referencia == mes_atual_str and not fixas_ativas.empty:
        vencidas = []
        vencem_hoje = []
        proximas = []

        for _, fixa in fixas_ativas.iterrows():
            nome = fixa["nome"]
            venc = int(fixa["dia_vencimento"]) if pd.notna(fixa["dia_vencimento"]) else 1

            if nome in categorias_fixas_pagas:
                continue

            if venc < hoje.day:
                vencidas.append(nome)
            elif venc == hoje.day:
                vencem_hoje.append(nome)
            elif hoje.day < venc <= hoje.day + 3:
                proximas.append(f"{nome} (dia {venc})")

        if vencidas:
            alertas.append({
                "tipo": "danger",
                "titulo": "Contas vencidas",
                "texto": "Você possui contas fixas vencidas e ainda em aberto: " + ", ".join(vencidas[:5]) + ("..." if len(vencidas) > 5 else ""),
            })

        if vencem_hoje:
            alertas.append({
                "tipo": "warning",
                "titulo": "Vencem hoje",
                "texto": "Atenção para as contas com vencimento hoje: " + ", ".join(vencem_hoje[:5]) + ("..." if len(vencem_hoje) > 5 else ""),
            })

        if proximas:
            alertas.append({
                "tipo": "info",
                "titulo": "Próximos vencimentos",
                "texto": "Nos próximos 3 dias vencem: " + ", ".join(proximas[:5]) + ("..." if len(proximas) > 5 else ""),
            })

    if saldo < 0:
        alertas.append({
            "tipo": "danger",
            "titulo": "Saldo negativo",
            "texto": f"O saldo atual está em {moeda(saldo)}. Revise despesas lançadas e pagamentos pendentes.",
        })

    comprometimento = (gastos_totais / receitas * 100) if receitas > 0 else 0.0
    if receitas > 0 and comprometimento >= 90:
        alertas.append({
            "tipo": "danger",
            "titulo": "Comprometimento crítico da receita",
            "texto": f"Seus gastos já comprometem {percentual(comprometimento)} da receita no mês.",
        })
    elif receitas > 0 and comprometimento >= 75:
        alertas.append({
            "tipo": "warning",
            "titulo": "Comprometimento elevado da receita",
            "texto": f"Seus gastos já comprometem {percentual(comprometimento)} da receita no mês.",
        })

    if not alertas:
        alertas.append({
            "tipo": "success",
            "titulo": "Situação sob controle",
            "texto": "Nenhum alerta crítico identificado no período selecionado.",
        })

    return alertas

init_db()
seed_initial_data()

st.markdown(
    f"""
    <style>
    .stApp {{
        background: {APP_COLORS["bg"]};
    }}

    .block-container {{
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }}

    h1, h2, h3, h4, h5, h6 {{
        color: {APP_COLORS["text"]};
        letter-spacing: -0.02em;
    }}

    .stCaption, p, label, div {{
        color: {APP_COLORS["text"]};
    }}

    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        border-right: 1px solid {APP_COLORS["border"]};
    }}

    .stMetric {{
        border-radius: 18px;
        padding: 12px;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
        border: 1px solid {APP_COLORS["border"]};
    }}

    .fin-card {{
        background: {APP_COLORS["card"]};
        border: 1px solid {APP_COLORS["border"]};
        border-radius: 20px;
        padding: 18px 18px 14px 18px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        min-height: 128px;
    }}

    .fin-card-title {{
        font-size: 13px;
        font-weight: 700;
        color: {APP_COLORS["muted"]};
        margin-bottom: 10px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    .fin-card-value {{
        font-size: 28px;
        font-weight: 800;
        color: {APP_COLORS["text"]};
        line-height: 1.1;
        margin-bottom: 8px;
    }}

    .fin-card-sub {{
        font-size: 13px;
        color: {APP_COLORS["muted"]};
    }}

    .card-receita {{
        border-left: 6px solid {APP_COLORS["success"]};
        background: linear-gradient(180deg, #FFFFFF 0%, #F0FDF4 100%);
    }}

    .card-despesa {{
        border-left: 6px solid {APP_COLORS["danger"]};
        background: linear-gradient(180deg, #FFFFFF 0%, #FEF2F2 100%);
    }}

    .card-total {{
        border-left: 6px solid {APP_COLORS["warning"]};
        background: linear-gradient(180deg, #FFFFFF 0%, #FFF7ED 100%);
    }}

    .card-saldo {{
        border-left: 6px solid {APP_COLORS["primary"]};
        background: linear-gradient(180deg, #FFFFFF 0%, #EFF6FF 100%);
    }}

    .section-card {{
        background: {APP_COLORS["card"]};
        border: 1px solid {APP_COLORS["border"]};
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.05);
        margin-bottom: 12px;
    }}

    .alert-box {{
        border-radius: 18px;
        padding: 14px 16px;
        border: 1px solid transparent;
        margin-bottom: 10px;
    }}

    .alert-title {{
        font-size: 14px;
        font-weight: 800;
        margin-bottom: 4px;
    }}

    .alert-text {{
        font-size: 13px;
        line-height: 1.45;
    }}

    .alert-danger {{
        background: {APP_COLORS["danger_soft"]};
        border-color: #FECACA;
    }}

    .alert-warning {{
        background: {APP_COLORS["warning_soft"]};
        border-color: #FDE68A;
    }}

    .alert-info {{
        background: {APP_COLORS["info_soft"]};
        border-color: #A5F3FC;
    }}

    .alert-success {{
        background: {APP_COLORS["success_soft"]};
        border-color: #BBF7D0;
    }}

    .status-box {{
        border-radius: 20px;
        padding: 18px;
        color: white;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.12);
        min-height: 140px;
    }}

    .status-green {{
        background: linear-gradient(135deg, #15803D, #22C55E);
    }}

    .status-yellow {{
        background: linear-gradient(135deg, #D97706, #F59E0B);
    }}

    .status-red {{
        background: linear-gradient(135deg, #B91C1C, #EF4444);
    }}

    .status-title {{
        font-size: 13px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        opacity: 0.9;
        margin-bottom: 10px;
    }}

    .status-value {{
        font-size: 24px;
        font-weight: 800;
        line-height: 1.15;
        margin-bottom: 8px;
    }}

    .status-sub {{
        font-size: 13px;
        opacity: 0.95;
        line-height: 1.4;
    }}

    .fixa-card {{
        background: {APP_COLORS["card"]};
        border: 1px solid {APP_COLORS["border"]};
        border-radius: 18px;
        padding: 16px;
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
        margin-bottom: 12px;
    }}

    .fixa-top {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 12px;
    }}

    .fixa-nome {{
        font-size: 18px;
        font-weight: 800;
        color: {APP_COLORS["text"]};
        line-height: 1.2;
        margin-bottom: 4px;
    }}

    .fixa-meta {{
        font-size: 13px;
        color: {APP_COLORS["muted"]};
    }}

    .fixa-valor {{
        font-size: 24px;
        font-weight: 800;
        color: {APP_COLORS["text"]};
        white-space: nowrap;
    }}

    .badge {{
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        margin-right: 6px;
    }}

    .badge-success {{
        background: {APP_COLORS["success_soft"]};
        color: #166534;
    }}

    .badge-warning {{
        background: {APP_COLORS["warning_soft"]};
        color: #92400E;
    }}

    .badge-danger {{
        background: {APP_COLORS["danger_soft"]};
        color: #991B1B;
    }}

    .badge-info {{
        background: {APP_COLORS["primary_soft"]};
        color: #1D4ED8;
    }}

    .small-muted {{
        font-size: 12px;
        color: {APP_COLORS["muted"]};
    }}
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
    base_mes = pd.DataFrame(columns=["id", "tipo", "valor", "categoria", "data", "descricao", "natureza", "observacao"])

fixas_ativas = fixas[fixas["ativa"] == 1].copy() if not fixas.empty else pd.DataFrame(
    columns=["id", "nome", "tipo", "valor_padrao", "dia_vencimento", "ativa", "criada_em"]
)

receitas = float(base_mes.loc[base_mes["tipo"] == "Receita", "valor"].sum()) if not base_mes.empty else 0.0

# Gastos variáveis lançados no mês
variaveis_mes = float(
    base_mes.loc[
        (base_mes["tipo"] == "Despesa") & (base_mes["natureza"] == "Variável"),
        "valor"
    ].sum()
) if not base_mes.empty else 0.0

# Gastos fixos previstos do mês (baseados no cadastro de despesas fixas)
gastos_fixos_previstos = float(fixas_ativas["valor_padrao"].sum()) if not fixas_ativas.empty else 0.0

# Categorias fixas pagas no mês = quando existe lançamento de despesa fixa daquela categoria
categorias_fixas_pagas = set(
    base_mes.loc[
        (base_mes["tipo"] == "Despesa") &
        (base_mes["natureza"] == "Fixa"),
        "categoria"
    ].dropna().tolist()
) if not base_mes.empty else set()

fixas_pagas_df = fixas_ativas[fixas_ativas["nome"].isin(categorias_fixas_pagas)].copy() if not fixas_ativas.empty else pd.DataFrame()
fixas_abertas_df = fixas_ativas[~fixas_ativas["nome"].isin(categorias_fixas_pagas)].copy() if not fixas_ativas.empty else pd.DataFrame()

gastos_fixos_pagos = float(fixas_pagas_df["valor_padrao"].sum()) if not fixas_pagas_df.empty else 0.0
gastos_fixos_em_aberto = float(fixas_abertas_df["valor_padrao"].sum()) if not fixas_abertas_df.empty else 0.0

# Total geral previsto do mês = fixos previstos + variáveis lançados
gastos_totais = gastos_fixos_previstos + variaveis_mes

# Resultado do mês considerando tudo que está previsto/gasto
resultado_mes = receitas - gastos_totais

# Saldo atual considerando apenas o que já foi efetivamente lançado
despesas_lancadas = float(base_mes.loc[base_mes["tipo"] == "Despesa", "valor"].sum()) if not base_mes.empty else 0.0
saldo = receitas - despesas_lancadas
comprometimento_receita = (gastos_totais / receitas * 100) if receitas > 0 else 0.0
status_financeiro = obter_status_financeiro(receitas, gastos_totais, resultado_mes, saldo)
previsao_fechamento = calcular_previsao_fechamento(
    mes_referencia=mes_referencia,
    receitas=receitas,
    gastos_fixos_previstos=gastos_fixos_previstos,
    variaveis_mes=variaveis_mes,
)
alertas_financeiros = calcular_alertas_financeiros(
    mes_referencia=mes_referencia,
    fixas_ativas=fixas_ativas,
    categorias_fixas_pagas=categorias_fixas_pagas,
    saldo=saldo,
    receitas=receitas,
    gastos_totais=gastos_totais,
)

if pagina == "Dashboard":
    st.subheader("Visão geral do mês")

    top1, top2, top3, top4 = st.columns(4)
    top1.markdown(
        render_fin_card("Receitas", moeda(receitas), "Entradas lançadas no mês", "card-receita"),
        unsafe_allow_html=True,
    )
    top2.markdown(
        render_fin_card("Gastos fixos previstos", moeda(gastos_fixos_previstos), "Baseado no cadastro de fixas", "card-despesa"),
        unsafe_allow_html=True,
    )
    top3.markdown(
        render_fin_card("Gastos variáveis", moeda(variaveis_mes), "Despesas variáveis lançadas", "card-total"),
        unsafe_allow_html=True,
    )
    top4.markdown(
        render_fin_card("Saldo atual", moeda(saldo), "Receitas - despesas lançadas", "card-saldo"),
        unsafe_allow_html=True,
    )

    meio1, meio2, meio3, meio4 = st.columns(4)
    meio1.markdown(
        render_fin_card("Gastos totais", moeda(gastos_totais), "Fixos previstos + variáveis", "card-total"),
        unsafe_allow_html=True,
    )
    meio2.markdown(
        render_fin_card("Resultado do mês", moeda(resultado_mes), "Receitas - gastos totais", "card-saldo"),
        unsafe_allow_html=True,
    )
    meio3.markdown(
        render_fin_card("Fixos pagos", moeda(gastos_fixos_pagos), "Despesas fixas já marcadas como pagas", "card-receita"),
        unsafe_allow_html=True,
    )
    meio4.markdown(
        render_fin_card("Fixos em aberto", moeda(gastos_fixos_em_aberto), "Despesas fixas ainda pendentes", "card-despesa"),
        unsafe_allow_html=True,
    )

    st.markdown("### Alertas inteligentes")
    for alerta in alertas_financeiros:
        st.markdown(
            render_alerta(alerta["tipo"], alerta["titulo"], alerta["texto"]),
            unsafe_allow_html=True,
        )

    status_col, previsao_col = st.columns([1, 1])

    with status_col:
        st.markdown(
            render_status_box(
                status_financeiro["cor"],
                status_financeiro["titulo"],
                status_financeiro["valor"],
                status_financeiro["subtitulo"],
            ),
            unsafe_allow_html=True,
        )

    with previsao_col:
        st.markdown(
            render_status_box(
                "green" if previsao_fechamento["projecao_resultado"] >= 0 else "red",
                "Previsão de fechamento",
                moeda(previsao_fechamento["projecao_resultado"]),
                f"Gastos projetados: {moeda(previsao_fechamento['projecao_gastos'])} | "
                f"Média diária variável: {moeda(previsao_fechamento['media_diaria_variavel'])}",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("### Indicadores de pressão financeira")
    ind1, ind2, ind3 = st.columns(3)
    ind1.markdown(
        render_fin_card(
            "Comprometimento da receita",
            percentual(comprometimento_receita),
            "Quanto os gastos totais consomem da receita",
            "card-total",
        ),
        unsafe_allow_html=True,
    )
    ind2.markdown(
        render_fin_card(
            "Projeção de variáveis",
            moeda(previsao_fechamento["projecao_variaveis"]),
            f"Base em {previsao_fechamento['dias_observados']} dia(s) observado(s)",
            "card-despesa",
        ),
        unsafe_allow_html=True,
    )
    ind3.markdown(
        render_fin_card(
            "Gasto fixo em aberto",
            moeda(gastos_fixos_em_aberto),
            "Valor ainda pendente nas contas recorrentes",
            "card-despesa",
        ),
        unsafe_allow_html=True,
    )

    graf1, graf2 = st.columns([1.35, 1])

    with graf1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
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
            fig_cat.update_layout(
                height=380,
                xaxis_title="",
                yaxis_title="Valor",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                font=dict(color=APP_COLORS["text"]),
            )
            st.plotly_chart(fig_cat, use_container_width=True, key="grafico_categoria_dashboard")
        st.markdown('</div>', unsafe_allow_html=True)

    with graf2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Fixo x Variável")
        if gastos_fixos_previstos + variaveis_mes == 0:
            st.info("Sem gastos no mês.")
        else:
            pie_df = pd.DataFrame(
                {
                    "tipo": ["Fixos", "Variáveis"],
                    "valor": [gastos_fixos_previstos, variaveis_mes],
                }
            )
            fig_pie = px.pie(pie_df, names="tipo", values="valor", hole=0.58)
            fig_pie.update_layout(
                height=380,
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=10, r=10, t=10, b=10),
                font=dict(color=APP_COLORS["text"]),
            )
            st.plotly_chart(fig_pie, use_container_width=True, key="grafico_pizza_dashboard")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("### Contas fixas do mês")
    if fixas_ativas.empty:
        st.info("Nenhuma despesa fixa cadastrada.")
    else:
        resumo_fixas = fixas_ativas[["nome", "valor_padrao", "dia_vencimento"]].copy()
        resumo_fixas["status"] = resumo_fixas["nome"].apply(
            lambda x: "Pago" if x in categorias_fixas_pagas else "Em aberto"
        )
        resumo_fixas["valor_padrao"] = resumo_fixas["valor_padrao"].apply(moeda)
        resumo_fixas.rename(
            columns={
                "nome": "Despesa fixa",
                "valor_padrao": "Valor",
                "dia_vencimento": "Vencimento",
                "status": "Status",
            },
            inplace=True,
        )
        st.dataframe(resumo_fixas, use_container_width=True, hide_index=True)

    st.markdown("### Últimos lançamentos")
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
    st.subheader("Cadastrar e acompanhar despesas fixas")

    if "editando_fixa_id" not in st.session_state:
        st.session_state.editando_fixa_id = None

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
    st.subheader(f"Contas fixas de {mes_referencia}")

    if fixas.empty:
        st.info("Nenhuma despesa fixa cadastrada ainda.")
    else:
        fixas_ordenadas = fixas.sort_values(["dia_vencimento", "nome"]).copy()

        for _, fixa in fixas_ordenadas.iterrows():
            fixa_id = int(fixa["id"])
            nome_fixa = fixa["nome"]
            valor_fixa = float(fixa["valor_padrao"])
            vencimento = int(fixa["dia_vencimento"]) if pd.notna(fixa["dia_vencimento"]) else 1
            ativa = int(fixa["ativa"]) == 1
            ja_paga = nome_fixa in categorias_fixas_pagas

            status_pagamento_badge = (
                '<span class="badge badge-success">✅ Pago</span>'
                if ja_paga else
                '<span class="badge badge-warning">⏳ Em aberto</span>'
            )
            status_ativa_badge = (
                '<span class="badge badge-info">Ativa</span>'
                if ativa else
                '<span class="badge badge-danger">Inativa</span>'
            )

            st.markdown(
                f"""
                <div class="fixa-card">
                    <div class="fixa-top">
                        <div>
                            <div class="fixa-nome">{nome_fixa}</div>
                            <div class="fixa-meta">Vencimento no dia {vencimento}</div>
                        </div>
                        <div class="fixa-valor">{moeda(valor_fixa)}</div>
                    </div>
                    <div>
                        {status_ativa_badge}
                        {status_pagamento_badge}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            ac1, ac2, ac3 = st.columns([1, 1, 1])

            if ac1.button("Editar", key=f"editar_fixa_{fixa_id}", use_container_width=True):
                st.session_state.editando_fixa_id = fixa_id

            if ativa and not ja_paga:
                if ac2.button("Marcar como pago", key=f"pagar_fixa_{fixa_id}", use_container_width=True):
                    dia_lancamento = min(int(vencimento), 28)
                    data_lancamento = f"{mes_referencia}-{dia_lancamento:02d}"

                    conn.execute(
                        """
                        INSERT INTO transacoes (data, tipo, categoria, descricao, valor, natureza, observacao, criado_em)
                        VALUES (?, 'Despesa', ?, ?, ?, 'Fixa', ?, ?)
                        """,
                        (
                            data_lancamento,
                            nome_fixa,
                            f"Pagamento de despesa fixa - {nome_fixa}",
                            valor_fixa,
                            f"Marcada como paga no mês {mes_referencia}",
                            datetime.now().isoformat(),
                        ),
                    )
                    conn.commit()
                    clear_cache()
                    st.success(f"{nome_fixa} marcada como paga.")
                    st.rerun()

            if ja_paga:
                if ac3.button("Desmarcar pagamento", key=f"despagar_fixa_{fixa_id}", use_container_width=True):
                    registro_pago = pd.read_sql_query(
                        """
                        SELECT id
                        FROM transacoes
                        WHERE tipo = 'Despesa'
                          AND natureza = 'Fixa'
                          AND categoria = ?
                          AND substr(data, 1, 7) = ?
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        conn,
                        params=(nome_fixa, mes_referencia),
                    )

                    if not registro_pago.empty:
                        conn.execute("DELETE FROM transacoes WHERE id = ?", (int(registro_pago.iloc[0]["id"]),))
                        conn.commit()
                        clear_cache()
                        st.success(f"Pagamento de {nome_fixa} removido.")
                        st.rerun()

            if st.session_state.editando_fixa_id == fixa_id:
                st.markdown("### Editando despesa fixa")

                with st.form(f"form_editar_fixa_{fixa_id}"):
                    ef1, ef2, ef3 = st.columns([2, 1, 1])

                    nome_edit = ef1.text_input(
                        "Nome da despesa fixa",
                        value=nome_fixa,
                        key=f"nome_fixa_{fixa_id}"
                    )
                    valor_edit = ef2.number_input(
                        "Valor padrão",
                        min_value=0.0,
                        value=float(valor_fixa),
                        step=10.0,
                        format="%.2f",
                        key=f"valor_fixa_{fixa_id}"
                    )
                    venc_edit = ef3.number_input(
                        "Dia do vencimento",
                        min_value=1,
                        max_value=31,
                        value=int(vencimento),
                        step=1,
                        key=f"venc_fixa_{fixa_id}"
                    )

                    ativa_edit = st.selectbox(
                        "Status",
                        ["Ativa", "Inativa"],
                        index=0 if ativa else 1,
                        key=f"ativa_fixa_{fixa_id}"
                    )

                    b1, b2, b3 = st.columns(3)
                    salvar_edicao_fixa = b1.form_submit_button("Salvar alteração", use_container_width=True)
                    cancelar_edicao_fixa = b2.form_submit_button("Cancelar", use_container_width=True)
                    excluir_fixa = b3.form_submit_button("Excluir despesa fixa", use_container_width=True)

                    if cancelar_edicao_fixa:
                        st.session_state.editando_fixa_id = None
                        st.rerun()

                    if excluir_fixa:
                        conn.execute("DELETE FROM categorias_fixas WHERE id = ?", (fixa_id,))
                        conn.commit()
                        clear_cache()
                        st.session_state.editando_fixa_id = None
                        st.success("Despesa fixa excluída com sucesso.")
                        st.rerun()

                    if salvar_edicao_fixa:
                        if not nome_edit.strip():
                            st.error("Informe um nome para a despesa fixa.")
                        elif valor_edit <= 0:
                            st.error("Informe um valor maior que zero.")
                        else:
                            try:
                                conn.execute(
                                    """
                                    UPDATE categorias_fixas
                                    SET nome = ?, valor_padrao = ?, dia_vencimento = ?, ativa = ?
                                    WHERE id = ?
                                    """,
                                    (
                                        nome_edit.strip(),
                                        float(valor_edit),
                                        int(venc_edit),
                                        1 if ativa_edit == "Ativa" else 0,
                                        fixa_id,
                                    ),
                                )
                                conn.commit()
                                clear_cache()
                                st.session_state.editando_fixa_id = None
                                st.success("Despesa fixa atualizada com sucesso.")
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error("Já existe outra despesa fixa com esse nome.")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    st.subheader("Resumo das despesas fixas")
    r1, r2, r3 = st.columns(3)
    r1.markdown(
        render_fin_card("Total fixo previsto", moeda(gastos_fixos_previstos), "Valor total cadastrado", "card-total"),
        unsafe_allow_html=True,
    )
    r2.markdown(
        render_fin_card("Total fixo pago", moeda(gastos_fixos_pagos), "Contas marcadas como pagas", "card-receita"),
        unsafe_allow_html=True,
    )
    r3.markdown(
        render_fin_card("Total fixo em aberto", moeda(gastos_fixos_em_aberto), "Contas ainda pendentes", "card-despesa"),
        unsafe_allow_html=True,
    )
elif pagina == "Histórico":
    st.subheader("Histórico completo")

    if "editando_id" not in st.session_state:
        st.session_state.editando_id = None

    if transacoes.empty:
        st.info("Sem histórico ainda.")
    else:
        filtro_tipo = st.multiselect(
            "Filtrar por tipo",
            ["Receita", "Despesa"],
            default=["Receita", "Despesa"]
        )
        filtro_nat = st.multiselect(
            "Filtrar por natureza",
            ["Fixa", "Variável"],
            default=["Fixa", "Variável"]
        )
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

        st.divider()
        st.subheader("Editar ou excluir lançamentos")

        if hist.empty:
            st.info("Nenhum lançamento encontrado com os filtros aplicados.")
        else:
            for _, row in hist.iterrows():
                lanc_id = int(row["id"])

                with st.container():
                    c1, c2, c3, c4 = st.columns([2.2, 2.0, 1.2, 1.2])

                    c1.markdown(
                        f"""
                        **{row['categoria']}**  
                        {row['descricao'] if pd.notna(row['descricao']) and row['descricao'] else '-'}  
                        {pd.to_datetime(row['data']).strftime('%d/%m/%Y')}
                        """
                    )
                    c2.markdown(
                        f"""
                        **{row['tipo']} / {row['natureza']}**  
                        {moeda(float(row['valor']))}
                        """
                    )

                    if c3.button("Editar", key=f"editar_{lanc_id}", use_container_width=True):
                        st.session_state.editando_id = lanc_id

                    if c4.button("Excluir", key=f"excluir_{lanc_id}", use_container_width=True):
                        conn.execute("DELETE FROM transacoes WHERE id = ?", (lanc_id,))
                        conn.commit()
                        clear_cache()
                        if st.session_state.editando_id == lanc_id:
                            st.session_state.editando_id = None
                        st.success("Lançamento excluído com sucesso.")
                        st.rerun()

                    if st.session_state.editando_id == lanc_id:
                        st.markdown("### Editando lançamento")

                        with st.form(f"form_editar_{lanc_id}"):
                            e1, e2, e3 = st.columns(3)

                            data_edit = e1.date_input(
                                "Data",
                                value=pd.to_datetime(row["data"]).date(),
                                key=f"data_{lanc_id}"
                            )
                            tipo_edit = e2.selectbox(
                                "Tipo",
                                ["Despesa", "Receita"],
                                index=0 if row["tipo"] == "Despesa" else 1,
                                key=f"tipo_{lanc_id}"
                            )
                            natureza_edit = e3.selectbox(
                                "Natureza",
                                ["Variável", "Fixa"],
                                index=0 if row["natureza"] == "Variável" else 1,
                                key=f"natureza_{lanc_id}"
                            )

                            categorias_fixas_ativas = fixas.loc[fixas["ativa"] == 1, "nome"].tolist() if not fixas.empty else []
                            categorias_padrao = [
                                "Salário", "Freelance", "Venda", "Supermercado", "Transporte",
                                "Saúde", "Lazer", "Educação", "Cartão de crédito", "Outros"
                            ]
                            categorias = sorted(set(categorias_padrao + categorias_fixas_ativas))

                            categoria_atual = row["categoria"] if pd.notna(row["categoria"]) else "Outros"
                            if categoria_atual not in categorias:
                                categorias.append(categoria_atual)
                                categorias = sorted(categorias)

                            e4, e5 = st.columns([2, 1])

                            categoria_edit = e4.selectbox(
                                "Categoria",
                                categorias,
                                index=categorias.index(categoria_atual),
                                key=f"categoria_{lanc_id}"
                            )
                            valor_edit = e5.number_input(
                                "Valor",
                                min_value=0.0,
                                value=float(row["valor"]),
                                step=10.0,
                                format="%.2f",
                                key=f"valor_{lanc_id}"
                            )

                            descricao_edit = st.text_input(
                                "Descrição",
                                value=row["descricao"] if pd.notna(row["descricao"]) else "",
                                key=f"descricao_{lanc_id}"
                            )
                            observacao_edit = st.text_area(
                                "Observação",
                                value=row["observacao"] if pd.notna(row["observacao"]) else "",
                                key=f"observacao_{lanc_id}"
                            )

                            s1, s2 = st.columns(2)
                            salvar_edicao = s1.form_submit_button("Salvar alteração", use_container_width=True)
                            cancelar_edicao = s2.form_submit_button("Cancelar", use_container_width=True)

                            if cancelar_edicao:
                                st.session_state.editando_id = None
                                st.rerun()

                            if salvar_edicao:
                                if valor_edit <= 0:
                                    st.error("Informe um valor maior que zero.")
                                else:
                                    conn.execute(
                                        """
                                        UPDATE transacoes
                                        SET data = ?, tipo = ?, categoria = ?, descricao = ?, valor = ?, natureza = ?, observacao = ?
                                        WHERE id = ?
                                        """,
                                        (
                                            data_edit.isoformat(),
                                            tipo_edit,
                                            categoria_edit,
                                            descricao_edit,
                                            float(valor_edit),
                                            natureza_edit,
                                            observacao_edit,
                                            lanc_id,
                                        ),
                                    )
                                    conn.commit()
                                    clear_cache()
                                    st.session_state.editando_id = None
                                    st.success("Lançamento atualizado com sucesso.")
                                    st.rerun()

                    st.divider()

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
