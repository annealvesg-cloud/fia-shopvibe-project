CREATE TABLE IF NOT EXISTS transacoes_suspeitas (
    id BIGSERIAL PRIMARY KEY,
    pedido_id TEXT NOT NULL,
    cliente_id TEXT,
    valor NUMERIC(12,2),
    motivo TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    evento JSONB,
    detectado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_suspeitas_detectado_em ON transacoes_suspeitas (detectado_em DESC);
