# MT5 terminal under Wine, running the Gold Trader's Edge EA.
# Build context is the repository root:
#   docker build -f packages/mt5-terminal/Dockerfile .
# Needs vendor/mt5.tar.gz (make-vendor.sh); deploy with deploy.sh.
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    WINEPREFIX=/opt/wine \
    WINEARCH=wow64 \
    WINEDEBUG=-all \
    PATH="/opt/wine-stable/bin:$PATH" \
    WINEDLLOVERRIDES="mscoree,mshtml=" \
    DISPLAY=:99 \
    MT5_DIR="/opt/wine/drive_c/Program Files/MetaTrader 5"

# Railway cannot run 32-bit Linux programs. Wine's packages still pull them
# in, but WINEARCH=wow64 makes Wine run 32-bit Windows programs without them.
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

COPY packages/mt5-terminal/vendor/mt5.tar.gz /tmp/mt5.tar.gz
COPY packages/mt5-terminal/install-mt5.sh /gte/install-mt5.sh
RUN sh /gte/install-mt5.sh

COPY packages/mt5-ea/*.mq5 packages/mt5-ea/*.mqh /gte/ea/
COPY packages/mt5-terminal/build-ea.sh /gte/build-ea.sh
RUN sh /gte/build-ea.sh

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/mt5-terminal/servers.dat /gte/
COPY packages/mt5-terminal/write-config.sh packages/mt5-terminal/tail-logs.sh \
     packages/mt5-terminal/bridge.sh packages/mt5-terminal/entrypoint.sh /gte/

CMD ["sh", "/gte/entrypoint.sh"]
