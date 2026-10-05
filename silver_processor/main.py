
import base64
import json
import os
import re
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pq
from minio import Minio
from minio.error import S3Error


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_ACCESS_KEY", "minio_admin")
MINIO_PASSWORD = os.getenv("MINIO_SECRET_KEY", "minio_senha123")

BRONZE_BUCKET = os.getenv("BRONZE_BUCKET", "bronze")
SILVER_BUCKET = os.getenv("SILVER_BUCKET", "silver")

SCHEMA = pa.schema([
    ("pedido_id", pa.string()),
    ("cliente_id", pa.string()),
    ("valor", pa.decimal128(12, 2)),
    ("criado_em_utc", pa.string()),
    ("status", pa.string()),
    ("op", pa.string()),
    ("is_deleted", pa.bool_()),
    ("source_lsn", pa.int64()),
    ("source_ts_utc", pa.string()),
    ("kafka_partition", pa.int32()),
    ("kafka_offset", pa.int64()),
    ("bronze_object", pa.string()),
])


def criar_cliente():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=False,
    )


def garantir_bucket(minio, bucket):
    if not minio.bucket_exists(bucket):
        minio.make_bucket(bucket)
    print(f"Bucket '{bucket}' disponível.", flush=True)


def decimal_do_debezium(valor):
    if valor is None:
        return None

    # Valores já legíveis, por exemplo "7500.00".
    try:
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    except InvalidOperation:
        pass

    # Debezium pode codificar NUMERIC como bytes em Base64.
    dados = base64.b64decode(str(valor), validate=True)
    inteiro = int.from_bytes(dados, byteorder="big", signed=True)
    resultado = Decimal(inteiro).scaleb(-2)
    return resultado.quantize(Decimal("0.01"))


def normalizar_timestamp(valor):
    if valor is None:
        return None

    if isinstance(valor, str):
        try:
            dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
        except ValueError:
            return None

    if isinstance(valor, (int, float)):
        # O campo timestamp do exemplo CDC está em microssegundos.
        segundos = valor / 1_000_000
        dt = datetime.fromtimestamp(segundos, tz=timezone.utc)
        return dt.isoformat()

    return None


def timestamp_evento(evento):
    ts_ms = (evento.get("source") or {}).get("ts_ms")
    if ts_ms is None:
        return datetime.now(timezone.utc)

    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)


def objeto_existe(minio, bucket, nome):
    try:
        minio.stat_object(bucket, nome)
        return True
    except S3Error as exc:
        if exc.code in ("NoSuchKey", "NoSuchObject", "NotFound"):
            return False
        raise


def processar_objeto(minio, nome_bronze):
    # Identifica partição e offset pelo nome criado na Bronze.
    match = re.search(
        r"partition=(\d+)/offset=(\d+)\.json$",
        nome_bronze,
    )
    if not match:
        print(f"Caminho ignorado: {nome_bronze}", flush=True)
        return

    particao = int(match.group(1))
    offset = int(match.group(2))

    # Lê o JSON original.
    resposta = minio.get_object(BRONZE_BUCKET, nome_bronze)
    try:
        bruto = resposta.read()
    finally:
        resposta.close()
        resposta.release_conn()

    evento = json.loads(bruto.decode("utf-8"))
    payload = evento.get("payload", evento)

    if not isinstance(payload, dict):
        raise ValueError("Payload CDC inválido")

    operacao = payload.get("op")
    after = payload.get("after")
    before = payload.get("before")

    # Em eventos de exclusão, os dados podem estar em before.
    registro = after if after is not None else before

    if not isinstance(registro, dict):
        print(f"Evento sem registro: {nome_bronze}", flush=True)
        return

    source = payload.get("source") or {}
    ts_evento = timestamp_evento(payload)

    lsn = source.get("lsn")
    lsn = int(lsn) if lsn is not None else None

    linha = {
        "pedido_id": str(registro["id"]) if registro.get("id") is not None else None,
        "cliente_id": registro.get("cliente_id"),
        "valor": decimal_do_debezium(registro.get("valor")),
        "criado_em_utc": normalizar_timestamp(registro.get("criado_em")),
        "status": registro.get("status"),
        "op": operacao,
        "is_deleted": operacao == "d",
        "source_lsn": lsn,
        "source_ts_utc": ts_evento.isoformat(),
        "kafka_partition": particao,
        "kafka_offset": offset,
        "bronze_object": nome_bronze,
    }

    data = ts_evento

    nome_silver = (
        f"shopvibe/public/pedidos/"
        f"year={data:%Y}/month={data:%m}/day={data:%d}/"
        f"partition={particao}/offset={offset}.parquet"
    )

    # Idempotência: não grava novamente um evento já tratado.
    if objeto_existe(minio, SILVER_BUCKET, nome_silver):
        return

    tabela = pa.Table.from_pylist([linha], schema=SCHEMA)

    buffer = BytesIO()
    pq.write_table(tabela, buffer, compression="snappy")
    dados_parquet = buffer.getvalue()

    minio.put_object(
        SILVER_BUCKET,
        nome_silver,
        data=BytesIO(dados_parquet),
        length=len(dados_parquet),
        content_type="application/vnd.apache.parquet",
    )

    print(
        f"Evento tratado: {linha['pedido_id']} | "
        f"valor={linha['valor']} | arquivo={nome_silver}",
        flush=True,
    )


def executar():
    minio = criar_cliente()

    while True:
        try:
            garantir_bucket(minio, BRONZE_BUCKET)
            garantir_bucket(minio, SILVER_BUCKET)

            objetos = minio.list_objects(
                BRONZE_BUCKET,
                prefix="shopvibe/public/pedidos/",
                recursive=True,
            )

            for objeto in objetos:
                if not objeto.object_name.endswith(".json"):
                    continue

                try:
                    processar_objeto(minio, objeto.object_name)
                except Exception as exc:
                    print(
                        f"Erro ao processar {objeto.object_name}: {exc}",
                        flush=True,
                    )

            print("Varredura Silver concluída.", flush=True)
            time.sleep(30)

        except Exception as exc:
            print(f"Erro na Silver: {exc}", flush=True)
            time.sleep(10)


if __name__ == "__main__":
    executar()