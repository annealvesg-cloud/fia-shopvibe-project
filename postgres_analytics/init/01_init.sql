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


CREATE TABLE IF NOT EXISTS gold_indicadores_diarios (
    data DATE PRIMARY KEY,
    quantidade_pedidos BIGINT NOT NULL,
    valor_total NUMERIC(18,2) NOT NULL,
    valor_medio NUMERIC(18,2),
    maior_valor NUMERIC(18,2),
    menor_valor NUMERIC(18,2),
    processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_processamento (
    arquivo_silver TEXT PRIMARY KEY,
    processado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);