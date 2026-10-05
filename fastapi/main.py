from fastapi import FastAPI, HTTPException
import psycopg2
import os


app = FastAPI(
    title="ShopVibe Analytics API",
    description="API para consulta dos dados Gold do ShopVibe",
    version="1.0.0"
)


def get_connection():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "postgres_analytics"),
        port=os.getenv("PGPORT", "5432"),
        database=os.getenv("PGDATABASE", "analytics_db"),
        user=os.getenv("PGUSER", "postgres"),
        password=os.getenv("PGPASSWORD", "senha_analytics")
    )

def get_antifraud_connection():
    return psycopg2.connect(
        host=os.getenv("ANTIFRAUD_PGHOST", "postgres_antifraude"),
        port=os.getenv("ANTIFRAUD_PGPORT", "5432"),
        database=os.getenv("ANTIFRAUD_PGDATABASE", "antifraude_db"),
        user=os.getenv("ANTIFRAUD_PGUSER", "postgres"),
        password=os.getenv(
            "ANTIFRAUD_PGPASSWORD",
            "senha_antifraude"
        )
    )


@app.get("/health")
def health():
    try:
        conn = get_connection()
        conn.close()

        return {
            "status": "ok",
            "database": "connected"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro de conexão com PostgreSQL: {str(e)}"
        )


@app.get("/pedidos")
def listar_pedidos():
    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                pedido_id,
                cliente_id,
                valor,
                status,
                criado_em,
                atualizado_em,
                is_deleted,
                source_ts,
                processado_em
            FROM gold_pedidos
            WHERE is_deleted = FALSE
            ORDER BY criado_em DESC
        """)

        rows = cursor.fetchall()

        pedidos = []

        for row in rows:
            pedidos.append({
                "pedido_id": str(row[0]),
                "cliente_id": row[1],
                "valor": float(row[2]) if row[2] is not None else None,
                "status": row[3],
                "criado_em": row[4],
                "atualizado_em": row[5],
                "is_deleted": row[6],
                "source_ts": row[7],
                "processado_em": row[8]
            })

        cursor.close()

        return {
            "quantidade": len(pedidos),
            "pedidos": pedidos
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if conn:
            conn.close()


@app.get("/indicadores")
def indicadores():
    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                data,
                quantidade_pedidos,
                valor_total,
                valor_medio,
                maior_valor,
                menor_valor
            FROM gold_indicadores_diarios
            ORDER BY data
        """)

        rows = cursor.fetchall()

        resultado = []

        for row in rows:
            resultado.append({
                "data": row[0],
                "quantidade_pedidos": row[1],
                "valor_total": float(row[2]),
                "valor_medio": float(row[3]) if row[3] is not None else None,
                "maior_valor": float(row[4]) if row[4] is not None else None,
                "menor_valor": float(row[5]) if row[5] is not None else None
            })

        cursor.close()

        return resultado

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if conn:
            conn.close()


@app.get("/resumo")
def resumo():
    conn = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) AS quantidade_pedidos,
                COALESCE(SUM(valor), 0) AS valor_total,
                COALESCE(AVG(valor), 0) AS valor_medio,
                COALESCE(MAX(valor), 0) AS maior_valor,
                COALESCE(MIN(valor), 0) AS menor_valor
            FROM gold_pedidos
            WHERE is_deleted = FALSE
        """)

        row = cursor.fetchone()

        cursor.close()

        return {
            "quantidade_pedidos": row[0],
            "valor_total": float(row[1]),
            "valor_medio": float(row[2]),
            "maior_valor": float(row[3]),
            "menor_valor": float(row[4])
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if conn:
            conn.close()


@app.get("/antifraude/resumo")
def antifraude_resumo():

    conn = None

    try:

        conn = get_antifraud_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) AS total_alertas,
                COUNT(DISTINCT cliente_id) AS clientes_suspeitos,
                COALESCE(SUM(valor), 0) AS valor_suspeito,
                COALESCE(AVG(score), 0) AS score_medio,
                COALESCE(MAX(score), 0) AS maior_score
            FROM transacoes_suspeitas
        """)

        row = cursor.fetchone()

        cursor.close()

        return {
            "total_alertas": row[0],
            "clientes_suspeitos": row[1],
            "valor_suspeito": float(row[2]),
            "score_medio": float(row[3]),
            "maior_score": row[4]
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if conn:
            conn.close()


@app.get("/antifraude/alertas")
def antifraude_alertas():

    conn = None

    try:

        conn = get_antifraud_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id,
                pedido_id,
                cliente_id,
                valor,
                motivo,
                score,
                detectado_em
            FROM transacoes_suspeitas
            ORDER BY detectado_em DESC
        """)

        rows = cursor.fetchall()

        alertas = []

        for row in rows:

            score = row[5]

            if score < 300:
                nivel = "BAIXO"
            elif score < 600:
                nivel = "MÉDIO"
            elif score < 800:
                nivel = "ALTO"
            else:
                nivel = "CRÍTICO"

            alertas.append({
                "id": row[0],
                "pedido_id": row[1],
                "cliente_id": row[2],
                "valor": float(row[3]) if row[3] is not None else None,
                "motivo": row[4],
                "score": score,
                "nivel": nivel,
                "detectado_em": row[6]
            })

        cursor.close()

        return {
            "quantidade": len(alertas),
            "alertas": alertas
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:

        if conn:
            conn.close()


@app.get("/antifraude/indicadores")
def antifraude_indicadores():
    conn = get_antifraud_connection()

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    DATE(detectado_em) AS data,
                    COUNT(*) AS quantidade_alertas,
                    COALESCE(SUM(valor), 0) AS valor_suspeito,
                    COALESCE(AVG(score), 0) AS score_medio,
                    COALESCE(MAX(score), 0) AS maior_score,

                    COUNT(*) FILTER (
                        WHERE score BETWEEN 0 AND 299
                    ) AS risco_baixo,

                    COUNT(*) FILTER (
                        WHERE score BETWEEN 300 AND 599
                    ) AS risco_medio,

                    COUNT(*) FILTER (
                        WHERE score BETWEEN 600 AND 799
                    ) AS risco_alto,

                    COUNT(*) FILTER (
                        WHERE score BETWEEN 800 AND 1000
                    ) AS risco_critico

                FROM transacoes_suspeitas

                GROUP BY DATE(detectado_em)

                ORDER BY data
            """)

            rows = cur.fetchall()

        return [
            {
                "data": row[0].isoformat(),
                "quantidade_alertas": row[1],
                "valor_suspeito": float(row[2]),
                "score_medio": float(row[3]),
                "maior_score": row[4],
                "risco_baixo": row[5],
                "risco_medio": row[6],
                "risco_alto": row[7],
                "risco_critico": row[8]
            }
            for row in rows
        ]

    finally:
        conn.close()
   