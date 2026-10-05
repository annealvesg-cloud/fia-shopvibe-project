import os

import requests
import pandas as pd
import plotly.express as px

from dash import (
    Dash,
    html,
    dcc,
    dash_table,
    Input,
    Output
)


API_URL = os.getenv(
    "API_URL",
    "http://fastapi:8000"
)


app = Dash(
    __name__,
    title="ShopVibe | Antifraude"
)


def buscar_resumo():

    response = requests.get(
        f"{API_URL}/antifraude/resumo",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def buscar_alertas():

    response = requests.get(
        f"{API_URL}/antifraude/alertas",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def buscar_indicadores():

    response = requests.get(
        f"{API_URL}/antifraude/indicadores",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def obter_nivel_risco(score):

    if score < 300:
        return "BAIXO"

    elif score < 600:
        return "MÉDIO"

    elif score < 800:
        return "ALTO"

    else:
        return "CRÍTICO"


def card(titulo, valor, id):

    return html.Div(
        [
            html.Div(
                titulo,
                className="kpi-title"
            ),

            html.Div(
                valor,
                id=id,
                className="kpi-value"
            )
        ],
        className="kpi-card"
    )


app.layout = html.Div(

    [

        # HEADER

        html.Div(
            [
                html.Div(
                    [
                        html.H1(
                            "SHOPVIVE",
                            className="logo"
                        ),

                        html.Div(
                            "ANTIFRAUDE",
                            className="subtitle"
                        )
                    ]
                ),

                html.Button(
                    "↻ Atualizar",
                    id="btn-refresh",
                    className="refresh-button"
                )
            ],
            className="header"
        ),


        # KPIs

        html.Div(
            [
                card(
                    "ALERTAS",
                    "0",
                    "kpi-alertas"
                ),

                card(
                    "CLIENTES SUSPEITOS",
                    "0",
                    "kpi-clientes"
                ),

                card(
                    "VALOR SUSPEITO",
                    "R$ 0,00",
                    "kpi-valor"
                ),

                card(
                    "SCORE MÉDIO",
                    "0",
                    "kpi-score"
                ),

                card(
                    "MAIOR SCORE",
                    "0",
                    "kpi-maior-score"
                )
            ],
            className="kpi-container"
        ),


        # GRÁFICO

        html.Div(
            [

                html.Div(
                    [
                        html.H2(
                            "Alertas por Dia"
                        ),

                        dcc.Graph(
                            id="grafico-alertas"
                        )
                    ],
                    className="panel"
                ),

            ],
            className="charts-container"
        ),


        # TABELA

        html.Div(
            [

                html.H2(
                    "Alertas de Antifraude"
                ),

                dash_table.DataTable(

                    id="tabela-alertas",

                    columns=[
                        {
                            "name": "Data",
                            "id": "detectado_em"
                        },
                        {
                            "name": "Pedido",
                            "id": "pedido_id"
                        },
                        {
                            "name": "Cliente",
                            "id": "cliente_id"
                        },
                        {
                            "name": "Valor",
                            "id": "valor"
                        },
                        {
                            "name": "Motivo",
                            "id": "motivo"
                        },
                        {
                            "name": "Score",
                            "id": "score"
                        },
                        {
                            "name": "Nível",
                            "id": "nivel"
                        }
                    ],

                    data=[],

                    page_size=10,

                    sort_action="native",

                    filter_action="native",

                    style_table={
                        "overflowX": "auto"
                    },

                    style_header={
                        "backgroundColor": "#1f2937",
                        "color": "white",
                        "fontWeight": "bold",
                        "textAlign": "left"
                    },

                    style_cell={
                        "backgroundColor": "#111827",
                        "color": "#e5e7eb",
                        "padding": "12px",
                        "textAlign": "left",
                        "border": "1px solid #374151"
                    },

                    style_data_conditional=[
                        {
                            "if": {
                                "filter_query": "{score} >= 800",
                                "column_id": "score"
                            },
                            "fontWeight": "bold"
                        }
                    ]
                )

            ],
            className="panel"
        ),


        dcc.Interval(
            id="interval",
            interval=15000,
            n_intervals=0
        )

    ],

    className="dashboard"
)


@app.callback(

    Output("kpi-alertas", "children"),
    Output("kpi-clientes", "children"),
    Output("kpi-valor", "children"),
    Output("kpi-score", "children"),
    Output("kpi-maior-score", "children"),
    Output("grafico-alertas", "figure"),
    Output("tabela-alertas", "data"),

    Input("interval", "n_intervals"),
    Input("btn-refresh", "n_clicks")

)
def atualizar_dashboard(
    n_intervals,
    n_clicks
):

    try:

        resumo = buscar_resumo()

        alertas = buscar_alertas()

        indicadores = buscar_indicadores()


        # KPIs

        total_alertas = resumo["total_alertas"]

        clientes = resumo["clientes_suspeitos"]

        valor = resumo["valor_suspeito"]

        score = resumo["score_medio"]

        maior_score = resumo["maior_score"]


        # Indicadores

        df = pd.DataFrame(
            indicadores
        )

        if df.empty:

            fig = px.bar(
                title="Nenhum alerta registrado"
            )

        else:

            df["data"] = pd.to_datetime(
                df["data"]
            )

            fig = px.bar(
                df,
                x="data",
                y="quantidade_alertas",
                title="Quantidade de alertas"
            )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#111827",
                plot_bgcolor="#111827",
                font_color="#e5e7eb",
                margin=dict(
                    l=30,
                    r=30,
                    t=50,
                    b=30
                )
            )


        # Alertas

        dados_alertas = alertas.get(
            "alertas",
            []
        )

        for alerta in dados_alertas:

            if alerta.get("valor") is not None:

                alerta["valor"] = (
                    f'R$ {alerta["valor"]:,.2f}'
                    .replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )


        return (

            total_alertas,

            clientes,

            (
                f"R$ {valor:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            ),

            f"{score:.0f}",

            maior_score,

            fig,

            dados_alertas
        )


    except Exception as e:

        fig = px.bar(
            title=f"Erro ao consultar API: {e}"
        )

        return (
            "—",
            "—",
            "—",
            "—",
            "—",
            fig,
            []
        )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8051,
        debug=False
    )