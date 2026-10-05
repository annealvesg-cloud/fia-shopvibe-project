from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any

from collections import defaultdict, deque
from datetime import datetime, timedelta

import psycopg2
import os
import json


app = FastAPI(
    title="ShopVive Antifraud Processor",
    description="Motor de regras para análise antifraude",
    version="2.0.0"
)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

JANELA_2_MINUTOS = timedelta(minutes=2)

JANELA_30_SEGUNDOS = timedelta(seconds=30)

LIMITE_ALERTA = 400

SCORE_MAXIMO = 1000


# ============================================================
# MEMÓRIA DO PROCESSADOR
# ============================================================

historico_clientes = defaultdict(deque)

clientes_vistos = set()

valores_clientes = defaultdict(list)

clientes_alertados = set()


# ============================================================
# CONEXÃO POSTGRESQL
# ============================================================

def get_connection():

    return psycopg2.connect(

        host=os.getenv(
            "PGHOST",
            "postgres_antifraude"
        ),

        port=os.getenv(
            "PGPORT",
            "5432"
        ),

        database=os.getenv(
            "PGDATABASE",
            "antifraude_db"
        ),

        user=os.getenv(
            "PGUSER",
            "postgres"
        ),

        password=os.getenv(
            "PGPASSWORD",
            "senha_antifraude"
        )
    )


# ============================================================
# MODELO
# ============================================================

class Transacao(BaseModel):

    pedido_id: str

    cliente_id: Optional[str] = None

    valor: float = 0

    criado_em: Optional[str] = None

    evento: Optional[Dict[str, Any]] = None


# ============================================================
# DATETIME
# ============================================================

def converter_datetime(valor):

    if not valor:

        return datetime.now()

    try:

        return datetime.fromisoformat(
            str(valor).replace("Z", "")
        )

    except ValueError:

        return datetime.now()


# ============================================================
# REGRA R001 / R002 / R003
# ============================================================

def atualizar_historico(
    cliente_id,
    criado_em
):

    historico = historico_clientes[
        cliente_id
    ]

    historico.append(
        criado_em
    )

    limite = criado_em - JANELA_2_MINUTOS

    while historico and historico[0] < limite:

        historico.popleft()

    return historico


# ============================================================
# MOTOR DE REGRAS
# ============================================================

def avaliar_regras(
    cliente_id,
    valor,
    criado_em
):

    regras = []

    score = 0

    historico = atualizar_historico(
        cliente_id,
        criado_em
    )

    quantidade_2min = len(
        historico
    )


    # --------------------------------------------------------
    # R001
    # Mais de 5 pedidos em 2 minutos
    # --------------------------------------------------------

    if quantidade_2min > 5:

        regras.append({

            "codigo": "R001",

            "descricao":
                "Mais de 5 pedidos em 2 minutos",

            "pontos": 400
        })

        score += 400


    # --------------------------------------------------------
    # R002
    # Mais de 10 pedidos em 2 minutos
    # --------------------------------------------------------

    if quantidade_2min > 10:

        regras.append({

            "codigo": "R002",

            "descricao":
                "Mais de 10 pedidos em 2 minutos",

            "pontos": 200
        })

        score += 200


    # --------------------------------------------------------
    # R003
    # 3 ou mais pedidos em 30 segundos
    # --------------------------------------------------------

    limite_30s = (
        criado_em -
        JANELA_30_SEGUNDOS
    )

    quantidade_30s = sum(
        1
        for data in historico
        if data >= limite_30s
    )

    if quantidade_30s >= 3:

        regras.append({

            "codigo": "R003",

            "descricao":
                "3 ou mais pedidos em 30 segundos",

            "pontos": 100
        })

        score += 100


    # --------------------------------------------------------
    # R004
    # Valor acima de 3x a média histórica
    # --------------------------------------------------------

    valores_anteriores = valores_clientes[
        cliente_id
    ]

    if len(valores_anteriores) >= 3:

        media = sum(
            valores_anteriores
        ) / len(
            valores_anteriores
        )

        if media > 0 and valor > media * 3:

            regras.append({

                "codigo": "R004",

                "descricao":
                    "Valor acima de 3 vezes a média histórica do cliente",

                "pontos": 200
            })

            score += 200


    # --------------------------------------------------------
    # R005
    # Primeiro pedido observado
    # --------------------------------------------------------

    if cliente_id not in clientes_vistos:

        regras.append({

            "codigo": "R005",

            "descricao":
                "Primeiro pedido observado do cliente",

            "pontos": 100
        })

        score += 100


    # --------------------------------------------------------
    # Atualiza histórico de valores
    # --------------------------------------------------------

    valores_clientes[
        cliente_id
    ].append(valor)


    clientes_vistos.add(
        cliente_id
    )


    # --------------------------------------------------------
    # Limita score
    # --------------------------------------------------------

    score = min(
        score,
        SCORE_MAXIMO
    )


    # --------------------------------------------------------
    # Nível de risco
    # --------------------------------------------------------

    if score >= 800:

        nivel_risco = "CRITICO"

    elif score >= 600:

        nivel_risco = "ALTO"

    elif score >= 300:

        nivel_risco = "MEDIO"

    else:

        nivel_risco = "BAIXO"


    return {

        "score": score,

        "nivel_risco": nivel_risco,

        "regras": regras,

        "quantidade_2min": quantidade_2min,

        "quantidade_30s": quantidade_30s
    }


# ============================================================
# GRAVA ALERTA
# ============================================================

def gravar_alerta(
    transacao,
    resultado
):

    conn = None

    try:

        conn = get_connection()

        cursor = conn.cursor()


        regras = resultado["regras"]


        motivo = " | ".join(

            f'{regra["codigo"]}: '
            f'{regra["descricao"]} '
            f'(+{regra["pontos"]})'

            for regra in regras
        )


        cursor.execute(
            """
            INSERT INTO transacoes_suspeitas (
                pedido_id,
                cliente_id,
                valor,
                motivo,
                score,
                evento
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
            """,

            (
                transacao.pedido_id,

                transacao.cliente_id,

                transacao.valor,

                motivo,

                resultado["score"],

                json.dumps(
                    transacao.evento or {}
                )
            )
        )


        conn.commit()

        cursor.close()


    except Exception:

        if conn:

            conn.rollback()

        raise


    finally:

        if conn:

            conn.close()

# ============================================================
# CONEXÃO POSTGRESQL OLTP
# ============================================================

def get_oltp_connection():

    return psycopg2.connect(

        host=os.getenv(
            "OLTP_PGHOST",
            "postgres_oltp"
        ),

        port=os.getenv(
            "OLTP_PGPORT",
            "5432"
        ),

        database=os.getenv(
            "OLTP_PGDATABASE",
            "shopvibe_bd"
        ),

        user=os.getenv(
            "OLTP_PGUSER",
            "postgres"
        ),

        password=os.getenv(
            "OLTP_PGPASSWORD",
            "senha_oltp"
        )
    )

# ============================================================
# ATUALIZA STATUS DO PEDIDO NO OLTP
# ============================================================

def atualizar_status_pedido(pedido_id):

    conn = None

    try:

        conn = get_oltp_connection()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE pedidos
            SET
                status = 'EM ANÁLISE',
                atualizado_em = CURRENT_TIMESTAMP
            WHERE pedido_id = %s
            """,
            (
                pedido_id,
            )
        )

        quantidade = cursor.rowcount

        conn.commit()

        cursor.close()

        print(
            f"[ANTIFRAUDE] "
            f"Pedido={pedido_id} "
            f"status=EM ANÁLISE "
            f"registros_atualizados={quantidade}",
            flush=True
        )

        return quantidade

    except Exception:

        if conn:
            conn.rollback()

        raise

    finally:

        if conn:
            conn.close()


# ============================================================
# ENDPOINT
# ============================================================

@app.post("/analisar")
def analisar(transacao: Transacao):

    criado_em = converter_datetime(
        transacao.criado_em
    )


    resultado = avaliar_regras(

        cliente_id=transacao.cliente_id,

        valor=transacao.valor,

        criado_em=criado_em
    )


    score = resultado["score"]


    alerta = (
        score >= LIMITE_ALERTA
    )


    # --------------------------------------------------------
    # Evita alertas repetidos
    # --------------------------------------------------------

    alerta_gravado = False

    if alerta:

        gravar_alerta(
            transacao,
            resultado
        )

        atualizar_status_pedido(
            transacao.pedido_id
        )

        alerta_gravado = True


    print(

        f"[ANTIFRAUDE] "

        f"cliente={transacao.cliente_id} "

        f"pedidos_2min="
        f"{resultado['quantidade_2min']} "

        f"pedidos_30s="
        f"{resultado['quantidade_30s']} "

        f"score="
        f"{score} "

        f"risco="
        f"{resultado['nivel_risco']} "

        f"alerta="
        f"{alerta}",

        flush=True
    )


    return {

        "alerta": alerta,

        "alerta_gravado":
            alerta_gravado,

        "score": score,

        "nivel_risco":
            resultado["nivel_risco"],

        "quantidade_pedidos_2min":
            resultado["quantidade_2min"],

        "quantidade_pedidos_30s":
            resultado["quantidade_30s"],

        "regras":
            resultado["regras"]
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }