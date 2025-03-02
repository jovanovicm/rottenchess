FROM python:3.12-slim
WORKDIR /usr/src/app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download and install the Stockfish ARMv8 binary
RUN wget https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-android-armv8-dotprod.tar && \
    tar -xf stockfish-android-armv8-dotprod.tar && \
    mv stockfish/stockfish-android-armv8-dotprod /usr/local/bin/stockfish && \
    chmod +x /usr/local/bin/stockfish && \
    rm -rf stockfish stockfish-android-armv8-dotprod.tar

RUN pip install --no-cache-dir boto3 chess
COPY . /usr/src/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "analysis.py"]