FROM confluentinc/cp-kafka-connect:7.4.0

USER root

ARG DEBEZIUM_CONNECTOR_VERSION=2.6.1.Final

# Instala o plugin S3 Sink da Confluent

RUN confluent-hub install --no-prompt confluentinc/kafka-connect-s3:10.5.5

# Instala o Debezium PostgreSQL

RUN mkdir -p /usr/share/java/debezium-connector-postgres && \
    curl -fSL "https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/${DEBEZIUM_CONNECTOR_VERSION}/debezium-connector-postgres-${DEBEZIUM_CONNECTOR_VERSION}-plugin.tar.gz" \
    -o /tmp/debezium-postgres.tar.gz && \
    tar -xzf /tmp/debezium-postgres.tar.gz \
    -C /usr/share/java/debezium-connector-postgres --strip-components=1 && \
    rm /tmp/debezium-postgres.tar.gz

# Instala o Debezium SQL Server

RUN mkdir -p /usr/share/java/debezium-connector-sqlserver && \
    curl -fSL "https://repo1.maven.org/maven2/io/debezium/debezium-connector-sqlserver/${DEBEZIUM_CONNECTOR_VERSION}/debezium-connector-sqlserver-${DEBEZIUM_CONNECTOR_VERSION}-plugin.tar.gz" \
    -o /tmp/debezium-sqlserver.tar.gz && \
    tar -xzf /tmp/debezium-sqlserver.tar.gz \
    -C /usr/share/java/debezium-connector-sqlserver --strip-components=1 && \
    rm /tmp/debezium-sqlserver.tar.gz

# Instala o Debezium Interceptor

RUN curl -fSL "https://repo1.maven.org/maven2/io/debezium/debezium-interceptor/${DEBEZIUM_CONNECTOR_VERSION}/debezium-interceptor-${DEBEZIUM_CONNECTOR_VERSION}.jar" \
    -o /usr/share/java/debezium-interceptor-${DEBEZIUM_CONNECTOR_VERSION}.jar

ENV CONNECT_PLUGIN_PATH="/usr/share/java,/usr/share/confluent-hub-components"
