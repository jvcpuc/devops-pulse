FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
# git é necessário apenas para instalar edge-tts (dependência via GitHub);
# é removido logo após o pip install para manter a imagem enxuta.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y git \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY app ./app
COPY data ./data
COPY scripts ./scripts

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
