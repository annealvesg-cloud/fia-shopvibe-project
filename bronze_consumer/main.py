import json
import os
import time
from datetime import datetime, timezone
from io import BytesIO

from kafka import KafkaConsumer
from kafka.structs import TopicPartition, OffsetAndMetadata
from minio import Minio


KAFKA_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"
)
KAFKA_TOPIC = os.getenv(
    "KAFKA_TOPIC", "shopvibe.public.pedidos"
)
KAFKA_GROUP = os.getenv(
    "KAFKA_GROUP_ID", "bronze-group"
)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_USER = os.getenv("MINIO_ACCESS_KEY", "minio_admin")
MINIO_PASSWORD = os.getenv("MINIO_SECRET_KEY", "minio_senha123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "bronze")


def criar_cliente_minio():
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=False,
    )


def aguardar_bucket(minio):
    while True:
        try:
            if not minio.bucket_exists(MINIO_BUCKET):
                minio.make_bucket(MINIO_BUCKET)

            print(
                f"Bucket '{MINIO_BUCKET}' disponível.",
                flush=True,
            )
            return

        except Exception as exc:
            print(
                f"MinIO indisponível: {exc}. Nova tentativa em 5s.",
                flush=True,
            )
            time.sleep(5)


def obter_data_evento(evento):
    try:
        timestamp = evento["source"]["ts_ms"]
        return datetime.fromtimestamp(
            timestamp / 1000, tz=timezone.utc
        )
    except (KeyError, TypeError, ValueError, OSError):
        return datetime.now(timezone.utc)


def salvar_evento(minio, mensagem):
    # Preserva os bytes originais recebidos do Kafka.
    dados = mensagem.value

    try:
        evento = json.loads(dados.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        evento = {}

    data = obter_data_evento(evento)

    caminho = (
        f"shopvibe/public/pedidos/"
        f"year={data:%Y}/month={data:%m}/day={data:%d}/"
        f"partition={mensagem.partition}/"
        f"offset={mensagem.offset}.json"
    )

    minio.put_object(
        bucket_name=MINIO_BUCKET,
        object_name=caminho,
        data=BytesIO(dados),
        length=len(dados),
        content_type="application/json",
    )

    print(f"Evento armazenado: {caminho}", flush=True)


def executar():
    minio = criar_cliente_minio()
    aguardar_bucket(minio)

    while True:
        consumer = None

        try:
            consumer = KafkaConsumer(
                bootstrap_servers=KAFKA_SERVERS.split(","),
                group_id=KAFKA_GROUP,
                enable_auto_commit=False,
                auto_offset_reset="earliest",
            )

            consumer.subscribe([KAFKA_TOPIC])

            print(
                f"Consumidor Bronze iniciado: {KAFKA_TOPIC}",
                flush=True,
            )

            for mensagem in consumer:
                salvar_evento(minio, mensagem)

                # Confirma somente a mensagem já armazenada.
                tp = TopicPartition(
                    mensagem.topic, mensagem.partition
                )

                consumer.commit({
                    tp: OffsetAndMetadata(
                        mensagem.offset + 1,
                        "",
                        -1
                    )
                })

        except Exception as exc:
            print(
                f"Erro no consumidor Bronze: {exc}. "
                "Reconectando em 5s.",
                flush=True,
            )

            time.sleep(5)

        finally:
            if consumer is not None:
                consumer.close()


if __name__ == "__main__":
    executar()