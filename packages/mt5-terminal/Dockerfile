# MT5 terminal under Wine, running the Gold Trader's Edge EA.
# Build context is the repository root:
#   docker build -f packages/mt5-terminal/Dockerfile .
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    WINEPREFIX=/opt/wine \
    WINEDEBUG=-all \
    WINEDLLOVERRIDES="mscoree,mshtml=" \
    DISPLAY=:99 \
    MT5_DIR="/opt/wine/drive_c/Program Files/MetaTrader 5"

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates wget gnupg xvfb xauth procps \
    && mkdir -pm755 /etc/apt/keyrings \
    && wget -qO /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key \
    && wget -qNP /etc/apt/sources.list.d/ \
       https://dl.winehq.org/wine-builds/debian/dists/bookworm/winehq-bookworm.sources \
    && apt-get update \
    && apt-get install -y --install-recommends winehq-stable \
    && rm -rf /var/lib/apt/lists/*

COPY packages/mt5-terminal/install-mt5.sh /gte/install-mt5.sh
RUN sh /gte/install-mt5.sh

COPY packages/mt5-ea/*.mq5 packages/mt5-ea/*.mqh /gte/ea/
COPY packages/mt5-terminal/build-ea.sh /gte/build-ea.sh
RUN sh /gte/build-ea.sh

COPY packages/mt5-terminal/servers.dat packages/mt5-terminal/webrequest.blob /gte/
COPY packages/mt5-terminal/write-config.sh packages/mt5-terminal/tail-logs.sh \
     packages/mt5-terminal/entrypoint.sh /gte/

CMD ["sh", "/gte/entrypoint.sh"]
