FROM postgres:16
RUN apt-get update && apt-get install -y wget
RUN wget https://github.com/wal-g/wal-g/releases/download/v2.0.1/wal-g-pg-ubuntu-20.04-amd64.tar.gz \
    && tar -zxvf wal-g-pg-ubuntu-20.04-amd64.tar.gz \
    && mv wal-g-pg-ubuntu-20.04-amd64 /usr/local/bin/wal-g \
    && chmod +x /usr/local/bin/wal-g \
    && rm wal-g-pg-ubuntu-20.04-amd64.tar.gz