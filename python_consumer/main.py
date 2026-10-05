import json
import os
import time
import base64
from decimal import Decimal
from datetime import datetime

import requests

from kafka import KafkaConsumer



# ============================================================
# CONFIGURAÇÕES
# ============================================================

ANTIFRAUD_URL = os.getenv(
    "ANTIFRAUD_URL",
    "http://antifraud_processor:8001/analisar"
)


# ============================================================
# CONVERTER VALOR DO CDC
# ============================================================

def converter_valor(valor_raw):

    try:

        return float(valor_raw or 0)

    except (ValueError, TypeError):

        try:

            dados = base64.b64decode(
                valor_raw,
                validate=True
            )

            valor_inteiro = int.from_bytes(
                dados,
                byteorder="big",
                signed=True
            )

            return float(
                Decimal(valor_inteiro).scaleb(-2)
            )

        except (ValueError, TypeError):

            raise ValueError(
                f"Valor inválido no evento: {valor_raw}"
            )

def converter_criado_em(valor):

    if valor is None:
        return None

    try:

        timestamp_us = int(valor)

        return datetime.fromtimestamp(
            timestamp_us / 1_000_000
        ).isoformat()

    except (ValueError, TypeError, OverflowError):

        return str(valor)


# ============================================================
# ENVIAR PEDIDO PARA O ANTIFRAUD PROCESSOR
# ============================================================

def enviar_para_antifraude(
    pedido_id,
    cliente_id,
    valor,
    criado_em,
    evento
):

    dados = {
        "pedido_id": str(pedido_id),
        "cliente_id": str(cliente_id),
        "valor": float(valor),
        "criado_em": criado_em,
        "evento": evento
    }

    try:

        response = requests.post(
            ANTIFRAUD_URL,
            json=dados,
            timeout=5
        )

        response.raise_for_status()

        resultado = response.json()

        print(
            f"[ANTIFRAUDE] "
            f"Pedido={pedido_id} "
            f"Resultado={resultado}",
            flush=True
        )

        return resultado

    except requests.RequestException as exc:

        print(
            f"[ERRO] Não foi possível enviar "
            f"pedido={pedido_id} "
            f"para antifraud_processor: {exc}",
            flush=True
        )

        return None


# ============================================================
# MAIN
# ============================================================

def main():

    while True:

        try:

            consumer = KafkaConsumer(

                os.getenv(
                    "KAFKA_TOPIC",
                    "shopvibe.public.pedidos"
                ),

                bootstrap_servers=os.getenv(
                    "KAFKA_BOOTSTRAP_SERVERS",
                    "kafka:29092"
                ).split(","),

                group_id=os.getenv(
                    "KAFKA_GROUP_ID",
                    "antifraude-group"
                ),

                auto_offset_reset="earliest",

                value_deserializer=lambda b:
                    json.loads(
                        b.decode("utf-8")
                    )
            )

            print(
                "Consumidor antifraude iniciado",
                flush=True
            )

            print(
                f"Antifraud Processor: "
                f"{ANTIFRAUD_URL}",
                flush=True
            )

            # =================================================
            # CONSUMIR KAFKA
            # =================================================

            for msg in consumer:

                event = msg.value or {}
                
                print(
                    f"[DEBUG] Evento Kafka recebido: {json.dumps(event, default=str)}",
                    flush=True
                )

                payload = event.get(
                    "payload",
                    event
                )

                after = (
                    payload.get("after")
                    if isinstance(payload, dict)
                    else None
                )

                # Ignora DELETE
                if not after:
                    continue

                # -------------------------------------------------
                # DADOS DO PEDIDO
                # -------------------------------------------------

                pedido_id = after.get(
                    "id",
                    "desconhecido"
                )

                cliente_id = after.get(
                    "cliente_id"
                )

                criado_em = converter_criado_em(
                    after.get("criado_em")
                )

                # -------------------------------------------------
                # VALOR
                # -------------------------------------------------

                valor_raw = after.get(
                    "valor"
                )

                try:

                    valor = converter_valor(
                        valor_raw
                    )

                except ValueError as exc:

                    print(
                        str(exc),
                        flush=True
                    )

                    continue

                # =================================================
                # ENVIAR PARA O MOTOR ANTIFRAUDE
                # =================================================

                enviar_para_antifraude(

                    pedido_id=pedido_id,

                    cliente_id=cliente_id,

                    valor=valor,

                    criado_em=criado_em,

                    evento=event
                )

        except Exception as exc:

            print(
                f"Erro no consumidor: {exc}; "
                f"reiniciando em 5s",
                flush=True
            )

            time.sleep(5)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()