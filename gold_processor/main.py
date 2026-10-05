import io
import os
import time
from datetime import datetime

import pyarrow.parquet as pq
import psycopg2
from minio import Minio


# ============================================================
# CONFIGURAÇÕES
# ============================================================

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minio_admin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minio_senha123")

SILVER_BUCKET = os.getenv("SILVER_BUCKET", "silver")

PGHOST = os.getenv("PGHOST", "postgres_analytics")
PGPORT = os.getenv("PGPORT", "5432")
PGDATABASE = os.getenv("PGDATABASE", "analytics_db")
PGUSER = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.getenv("PGPASSWORD", "senha_analytics")

INTERVALO = 30


# ============================================================
# MINIO
# ============================================================

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)


# ============================================================
# POSTGRES
# ============================================================

def conectar_postgres():

    while True:

        try:

            conexao = psycopg2.connect(
                host=PGHOST,
                port=PGPORT,
                database=PGDATABASE,
                user=PGUSER,
                password=PGPASSWORD
            )

            conexao.autocommit = False

            print("Conectado ao PostgreSQL Analytics.")

            return conexao

        except Exception as e:

            print(
                f"Aguardando PostgreSQL Analytics: {e}"
            )

            time.sleep(5)


# ============================================================
# TABELAS
# ============================================================

def criar_tabelas(conexao):

    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold_pedidos (
            pedido_id UUID PRIMARY KEY,
            cliente_id TEXT,
            valor NUMERIC(12,2),
            status VARCHAR(50),
            criado_em TIMESTAMP,
            atualizado_em TIMESTAMP,
            is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
            source_ts TIMESTAMP,
            processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold_indicadores_diarios (
            data DATE PRIMARY KEY,
            quantidade_pedidos BIGINT NOT NULL,
            valor_total NUMERIC(18,2) NOT NULL,
            valor_medio NUMERIC(18,2),
            maior_valor NUMERIC(18,2),
            menor_valor NUMERIC(18,2),
            processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gold_processamento (
            arquivo_silver TEXT PRIMARY KEY,
            processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conexao.commit()

    cursor.close()


# ============================================================
# CONVERSÃO DE TIMESTAMP
# ============================================================

def converter_timestamp(valor):

    if valor is None:
        return None

    if isinstance(valor, datetime):
        return valor

    valor = str(valor).strip()

    if not valor:
        return None

    # Remove Z
    valor = valor.replace("Z", "+00:00")

    try:

        dt = datetime.fromisoformat(valor)

        # PostgreSQL está usando TIMESTAMP sem timezone.
        # Portanto removemos o timezone depois de interpretar a data.

        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)

        return dt

    except Exception:

        print(
            f"Aviso: não foi possível converter timestamp: {valor}"
        )

        return None


# ============================================================
# VERIFICA ARQUIVO PROCESSADO
# ============================================================

def arquivo_processado(conexao, arquivo):

    cursor = conexao.cursor()

    cursor.execute("""
        SELECT 1
        FROM gold_processamento
        WHERE arquivo_silver = %s
    """, (arquivo,))

    resultado = cursor.fetchone()

    cursor.close()

    return resultado is not None


# ============================================================
# REGISTRA PROCESSAMENTO
# ============================================================

def registrar_processamento(conexao, arquivo):

    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO gold_processamento (
            arquivo_silver
        )
        VALUES (%s)
        ON CONFLICT (arquivo_silver)
        DO NOTHING
    """, (arquivo,))

    cursor.close()


# ============================================================
# PROCESSA PARQUET
# ============================================================

def processar_arquivo(conexao, objeto):

    nome_arquivo = objeto.object_name

    if arquivo_processado(
        conexao,
        nome_arquivo
    ):
        return False

    print(
        f"Processando Silver: {nome_arquivo}"
    )

    resposta = minio_client.get_object(
        SILVER_BUCKET,
        nome_arquivo
    )

    dados = resposta.read()

    resposta.close()
    resposta.release_conn()

    tabela = pq.read_table(
        io.BytesIO(dados)
    )

    registros = tabela.to_pylist()

    if not registros:

        print(
            f"Arquivo vazio: {nome_arquivo}"
        )

        registrar_processamento(
            conexao,
            nome_arquivo
        )

        conexao.commit()

        return True

    cursor = conexao.cursor()

    for registro in registros:

        pedido_id = registro.get(
            "pedido_id"
        )

        cliente_id = registro.get(
            "cliente_id"
        )

        valor = registro.get(
            "valor"
        )

        status = registro.get(
            "status"
        )

        criado_em = converter_timestamp(
            registro.get(
                "criado_em_utc"
            )
        )

        source_ts = converter_timestamp(
            registro.get(
                "source_ts_utc"
            )
        )

        op = registro.get(
            "op"
        )

        is_deleted = bool(
            registro.get(
                "is_deleted",
                False
            )
        )

        source_lsn = registro.get(
            "source_lsn"
        )

        # ====================================================
        # DELETE
        # ====================================================

        if op == "d":

            cursor.execute("""
                UPDATE gold_pedidos
                SET
                    is_deleted = TRUE,
                    atualizado_em = %s,
                    source_ts = %s,
                    processado_em = CURRENT_TIMESTAMP
                WHERE pedido_id = %s
                  AND (
                      source_ts IS NULL
                      OR %s >= source_ts
                  )
            """, (
                criado_em,
                source_ts,
                pedido_id,
                source_ts
            ))

        # ====================================================
        # INSERT / UPDATE
        # ====================================================

        else:

            cursor.execute("""
                INSERT INTO gold_pedidos (
                    pedido_id,
                    cliente_id,
                    valor,
                    status,
                    criado_em,
                    atualizado_em,
                    is_deleted,
                    source_ts,
                    processado_em
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP
                )

                ON CONFLICT (pedido_id)
                DO UPDATE SET
                    cliente_id = EXCLUDED.cliente_id,
                    valor = EXCLUDED.valor,
                    status = EXCLUDED.status,
                    atualizado_em = EXCLUDED.atualizado_em,
                    is_deleted = EXCLUDED.is_deleted,
                    source_ts = EXCLUDED.source_ts,
                    processado_em = CURRENT_TIMESTAMP

                WHERE
                    gold_pedidos.source_ts IS NULL
                    OR EXCLUDED.source_ts >= gold_pedidos.source_ts
            """, (
                pedido_id,
                cliente_id,
                valor,
                status,
                criado_em,
                criado_em,
                is_deleted,
                source_ts
            ))

        print(
            f"Pedido consolidado: "
            f"{pedido_id} | "
            f"valor={valor} | "
            f"op={op} | "
            f"LSN={source_lsn}"
        )

    registrar_processamento(
        conexao,
        nome_arquivo
    )

    conexao.commit()

    cursor.close()

    print(
        f"Gold atualizada: {nome_arquivo}"
    )

    return True


# ============================================================
# INDICADORES
# ============================================================

def atualizar_indicadores(conexao):

    cursor = conexao.cursor()

    cursor.execute("""
        INSERT INTO gold_indicadores_diarios (
            data,
            quantidade_pedidos,
            valor_total,
            valor_medio,
            maior_valor,
            menor_valor,
            processado_em
        )
        SELECT
            DATE(criado_em),
            COUNT(*),
            COALESCE(SUM(valor), 0),
            COALESCE(AVG(valor), 0),
            COALESCE(MAX(valor), 0),
            COALESCE(MIN(valor), 0),
            CURRENT_TIMESTAMP
        FROM gold_pedidos
        WHERE is_deleted = FALSE
          AND criado_em IS NOT NULL
        GROUP BY DATE(criado_em)

        ON CONFLICT (data)
        DO UPDATE SET
            quantidade_pedidos = EXCLUDED.quantidade_pedidos,
            valor_total = EXCLUDED.valor_total,
            valor_medio = EXCLUDED.valor_medio,
            maior_valor = EXCLUDED.maior_valor,
            menor_valor = EXCLUDED.menor_valor,
            processado_em = CURRENT_TIMESTAMP
    """)

    conexao.commit()

    cursor.close()

    print(
        "Indicadores diários atualizados."
    )


# ============================================================
# PROCESSA SILVER
# ============================================================

def processar_silver(conexao):

    objetos = minio_client.list_objects(
        SILVER_BUCKET,
        prefix="shopvibe/public/pedidos/",
        recursive=True
    )

    quantidade = 0

    for objeto in objetos:

        if not objeto.object_name.endswith(
            ".parquet"
        ):
            continue

        processado = processar_arquivo(
            conexao,
            objeto
        )

        if processado:
            quantidade += 1

    if quantidade > 0:

        atualizar_indicadores(
            conexao
        )

        print(
            f"Arquivos Silver processados: "
            f"{quantidade}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("==========================================")
    print("Gold Processor iniciado")
    print("==========================================")

    conexao = conectar_postgres()

    criar_tabelas(
        conexao
    )

    while True:

        try:

            processar_silver(
                conexao
            )

        except Exception as e:

            print(
                f"Erro no processamento Gold: {e}"
            )

            conexao.rollback()

        time.sleep(
            INTERVALO
        )


if __name__ == "__main__":
    main()