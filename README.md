# ShopVibe — projeto Docker

Projeto-base baseado no documento de arquitetura: PostgreSQL OLTP, Kafka em KRaft, Kafka Connect, MinIO/Bronze, consumidor Python antifraude, PostgreSQL antifraude e analytics, FastAPI e Dash.

## Executar
1. Instale e inicie o Docker Desktop.
2. Copie `.env.example` para `.env` e altere as senhas.
3. Na pasta do projeto, execute:
   ```bash
   docker compose up -d --build
   ```
4. Confira: `docker compose ps`
5. Logs: `docker compose logs -f`
6. Parar: `docker compose down`

## Endpoints
- FastAPI: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Dash: http://localhost:8051
- MinIO Console: http://localhost:9001
- Kafka Connect: http://localhost:8083
- PostgreSQL OLTP: localhost:5432
- PostgreSQL antifraude: localhost:5433
- PostgreSQL analytics: localhost:5434