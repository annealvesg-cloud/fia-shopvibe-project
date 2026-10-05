import os
import requests
import pandas as pd
import plotly.express as px

from dash import Dash, html, dcc, Input, Output
from dash import dash_table


# ============================================================
# CONFIGURAÇÃO
# ============================================================

API_URL = os.getenv("API_URL", "http://fastapi:8000")

app = Dash(
    __name__,
    title="ShopVibe Analytics"
)


# ============================================================
# ESTILO
# ============================================================

BACKGROUND = "#f4f6f8"
CARD = "#ffffff"
TEXT = "#1f2937"
SECONDARY = "#6b7280"
BORDER = "#e5e7eb"


def card_style():
    return {
        "backgroundColor": CARD,
        "border": f"1px solid {BORDER}",
        "borderRadius": "12px",
        "padding": "22px",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.05)",
        "flex": "1",
        "minWidth": "220px"
    }


# ============================================================
# LAYOUT
# ============================================================

app.layout = html.Div(
    style={
        "fontFamily": "Arial, sans-serif",
        "backgroundColor": BACKGROUND,
        "minHeight": "100vh",
        "padding": "0"
    },
    children=[

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        html.Div(
            style={
                "backgroundColor": "#111827",
                "color": "white",
                "padding": "22px 40px",
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center"
            },
            children=[

                html.Div([
                    html.Div(
                        "SHOPVIBE",
                        style={
                            "fontSize": "28px",
                            "fontWeight": "bold",
                            "letterSpacing": "1px"
                        }
                    ),

                    html.Div(
                        "ANALYTICS",
                        style={
                            "fontSize": "13px",
                            "color": "#9ca3af",
                            "letterSpacing": "3px",
                            "marginTop": "3px"
                        }
                    )
                ]),

                html.Button(
                    "↻  Atualizar",
                    id="refresh",
                    n_clicks=0,
                    style={
                        "backgroundColor": "#ffffff",
                        "color": "#111827",
                        "border": "none",
                        "borderRadius": "8px",
                        "padding": "10px 18px",
                        "fontSize": "14px",
                        "fontWeight": "bold",
                        "cursor": "pointer"
                    }
                )
            ]
        ),

        # ----------------------------------------------------
        # CONTEÚDO
        # ----------------------------------------------------

        html.Div(
            style={
                "padding": "30px 40px"
            },
            children=[

                # Título
                html.Div(
                    style={"marginBottom": "25px"},
                    children=[

                        html.H2(
                            "Visão geral",
                            style={
                                "margin": "0",
                                "color": TEXT,
                                "fontSize": "24px"
                            }
                        ),

                        html.P(
                            "Indicadores consolidados dos pedidos",
                            style={
                                "marginTop": "6px",
                                "color": SECONDARY,
                                "fontSize": "14px"
                            }
                        )
                    ]
                ),

                # ------------------------------------------------
                # CARDS
                # ------------------------------------------------

                html.Div(
                    style={
                        "display": "flex",
                        "gap": "20px",
                        "flexWrap": "wrap",
                        "marginBottom": "30px"
                    },
                    children=[

                        html.Div(
                            style=card_style(),
                            children=[

                                html.Div(
                                    "📦 PEDIDOS",
                                    style={
                                        "fontSize": "12px",
                                        "fontWeight": "bold",
                                        "color": SECONDARY,
                                        "letterSpacing": "1px"
                                    }
                                ),

                                html.Div(
                                    id="card-pedidos",
                                    children="0",
                                    style={
                                        "fontSize": "32px",
                                        "fontWeight": "bold",
                                        "color": TEXT,
                                        "marginTop": "10px"
                                    }
                                )
                            ]
                        ),

                        html.Div(
                            style=card_style(),
                            children=[

                                html.Div(
                                    "💰 VALOR TOTAL",
                                    style={
                                        "fontSize": "12px",
                                        "fontWeight": "bold",
                                        "color": SECONDARY,
                                        "letterSpacing": "1px"
                                    }
                                ),

                                html.Div(
                                    id="card-total",
                                    children="R$ 0,00",
                                    style={
                                        "fontSize": "32px",
                                        "fontWeight": "bold",
                                        "color": TEXT,
                                        "marginTop": "10px"
                                    }
                                )
                            ]
                        ),

                        html.Div(
                            style=card_style(),
                            children=[

                                html.Div(
                                    "🎯 TICKET MÉDIO",
                                    style={
                                        "fontSize": "12px",
                                        "fontWeight": "bold",
                                        "color": SECONDARY,
                                        "letterSpacing": "1px"
                                    }
                                ),

                                html.Div(
                                    id="card-medio",
                                    children="R$ 0,00",
                                    style={
                                        "fontSize": "32px",
                                        "fontWeight": "bold",
                                        "color": TEXT,
                                        "marginTop": "10px"
                                    }
                                )
                            ]
                        ),

                        html.Div(
                            style=card_style(),
                            children=[

                                html.Div(
                                    "📈 MAIOR PEDIDO",
                                    style={
                                        "fontSize": "12px",
                                        "fontWeight": "bold",
                                        "color": SECONDARY,
                                        "letterSpacing": "1px"
                                    }
                                ),

                                html.Div(
                                    id="card-maior",
                                    children="R$ 0,00",
                                    style={
                                        "fontSize": "32px",
                                        "fontWeight": "bold",
                                        "color": TEXT,
                                        "marginTop": "10px"
                                    }
                                )
                            ]
                        )
                    ]
                ),

                # ------------------------------------------------
                # GRÁFICO
                # ------------------------------------------------

                html.Div(
                    style={
                        "backgroundColor": CARD,
                        "border": f"1px solid {BORDER}",
                        "borderRadius": "12px",
                        "padding": "25px",
                        "marginBottom": "30px"
                    },
                    children=[

                        html.H3(
                            "Valor dos pedidos por dia",
                            style={
                                "marginTop": "0",
                                "color": TEXT
                            }
                        ),

                        html.P(
                            "Evolução do valor total dos pedidos",
                            style={
                                "color": SECONDARY,
                                "fontSize": "13px"
                            }
                        ),

                        dcc.Graph(
                            id="grafico-diario",
                            config={
                                "displayModeBar": False
                            }
                        )
                    ]
                ),

                # ------------------------------------------------
                # TABELA
                # ------------------------------------------------

                html.Div(
                    style={
                        "backgroundColor": CARD,
                        "border": f"1px solid {BORDER}",
                        "borderRadius": "12px",
                        "padding": "25px"
                    },
                    children=[

                        html.H3(
                            "Pedidos",
                            style={
                                "marginTop": "0",
                                "color": TEXT
                            }
                        ),

                        html.P(
                            "Últimos pedidos processados pelo ambiente analítico",
                            style={
                                "color": SECONDARY,
                                "fontSize": "13px"
                            }
                        ),

                        dash_table.DataTable(
                            id="tabela-pedidos",

                            columns=[
                                {
                                    "name": "Pedido ID",
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
                                    "name": "Status",
                                    "id": "status"
                                },
                                {
                                    "name": "Criado em",
                                    "id": "criado_em"
                                }
                            ],

                            data=[],

                            page_size=10,

                            sort_action="native",

                            style_table={
                                "overflowX": "auto"
                            },

                            style_header={
                                "backgroundColor": "#f9fafb",
                                "fontWeight": "bold",
                                "color": TEXT,
                                "border": f"1px solid {BORDER}"
                            },

                            style_cell={
                                "padding": "12px",
                                "textAlign": "left",
                                "fontSize": "13px",
                                "border": f"1px solid {BORDER}",
                                "color": TEXT
                            },

                            style_data_conditional=[
                                {
                                    "if": {
                                        "row_index": "odd"
                                    },
                                    "backgroundColor": "#fafafa"
                                }
                            ]
                        )
                    ]
                ),

                # ------------------------------------------------
                # STATUS
                # ------------------------------------------------

                html.Div(
                    id="status-api",
                    style={
                        "marginTop": "15px",
                        "fontSize": "12px",
                        "color": SECONDARY,
                        "textAlign": "right"
                    }
                ),

                dcc.Interval(
                    id="timer",
                    interval=15000,
                    n_intervals=0
                )
            ]
        )
    ]
)


# ============================================================
# CALLBACK
# ============================================================

@app.callback(
    Output("card-pedidos", "children"),
    Output("card-total", "children"),
    Output("card-medio", "children"),
    Output("card-maior", "children"),
    Output("grafico-diario", "figure"),
    Output("tabela-pedidos", "data"),
    Output("status-api", "children"),

    Input("refresh", "n_clicks"),
    Input("timer", "n_intervals")
)
def atualizar_dashboard(_, __):

    try:

        # ----------------------------------------------------
        # RESUMO
        # ----------------------------------------------------

        resumo_response = requests.get(
            f"{API_URL}/resumo",
            timeout=5
        )

        resumo_response.raise_for_status()

        resumo = resumo_response.json()

        quantidade = resumo.get(
            "quantidade_pedidos",
            resumo.get("pedidos", 0)
        )

        valor_total = float(
            resumo.get(
                "valor_total",
                0
            )
        )

        ticket_medio = float(
            resumo.get(
                "ticket_medio",
                0
            )
        )

        maior_valor = float(
            resumo.get(
                "maior_valor",
                0
            )
        )

        # ----------------------------------------------------
        # INDICADORES
        # ----------------------------------------------------

        indicadores_response = requests.get(
            f"{API_URL}/indicadores",
            timeout=5
        )

        indicadores_response.raise_for_status()

        indicadores = indicadores_response.json()

        if isinstance(indicadores, dict):

            indicadores = indicadores.get(
                "indicadores",
                indicadores.get(
                    "data",
                    []
                )
            )

        df_indicadores = pd.DataFrame(indicadores)

        # ----------------------------------------------------
        # GRÁFICO
        # ----------------------------------------------------

        if not df_indicadores.empty:

            if "data" in df_indicadores.columns:
                df_indicadores["data"] = pd.to_datetime(
                    df_indicadores["data"]
                )

            if "valor_total" in df_indicadores.columns:

                fig = px.bar(
                    df_indicadores,
                    x="data",
                    y="valor_total",
                    labels={
                        "data": "Data",
                        "valor_total": "Valor total"
                    }
                )

            else:

                fig = px.bar()

        else:

            fig = px.bar()

        fig.update_layout(
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            margin={
                "l": 40,
                "r": 20,
                "t": 20,
                "b": 40
            },
            xaxis={
                "showgrid": False
            },
            yaxis={
                "gridcolor": "#eeeeee"
            },
            font={
                "color": TEXT
            }
        )

        # ----------------------------------------------------
        # PEDIDOS
        # ----------------------------------------------------

        pedidos_response = requests.get(
            f"{API_URL}/pedidos",
            timeout=5
        )

        pedidos_response.raise_for_status()

        pedidos = pedidos_response.json()

        if isinstance(pedidos, dict):

            pedidos = pedidos.get(
                "pedidos",
                pedidos.get(
                    "data",
                    []
                )
            )

        df_pedidos = pd.DataFrame(pedidos)

        if not df_pedidos.empty:

            if "valor" in df_pedidos.columns:

                df_pedidos["valor"] = pd.to_numeric(
                    df_pedidos["valor"],
                    errors="coerce"
                )

                df_pedidos["valor"] = df_pedidos[
                    "valor"
                ].apply(
                    lambda x:
                    f"R$ {x:,.2f}".replace(
                        ",", "X"
                    ).replace(
                        ".", ","
                    ).replace(
                        "X", "."
                    )
                    if pd.notna(x)
                    else ""
                )

            if "criado_em" in df_pedidos.columns:

                df_pedidos["criado_em"] = (
                    pd.to_datetime(
                        df_pedidos["criado_em"],
                        errors="coerce"
                    )
                    .dt.strftime("%d/%m/%Y %H:%M")
                )

        tabela = df_pedidos.to_dict(
            "records"
        )

        # ----------------------------------------------------
        # FORMATAÇÃO DOS CARDS
        # ----------------------------------------------------

        def moeda(valor):

            return (
                f"R$ {valor:,.2f}"
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )

        status = (
            f"Última atualização: "
            f"{pd.Timestamp.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )

        return (
            f"{quantidade:,}".replace(",", "."),
            moeda(valor_total),
            moeda(ticket_medio),
            moeda(maior_valor),
            fig,
            tabela,
            status
        )

    except Exception as exc:

        fig = px.bar()

        fig.update_layout(
            paper_bgcolor=CARD,
            plot_bgcolor=CARD
        )

        erro = f"API indisponível: {exc}"

        return (
            "—",
            "R$ 0,00",
            "R$ 0,00",
            "R$ 0,00",
            fig,
            [],
            erro
        )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8051,
        debug=False
    )