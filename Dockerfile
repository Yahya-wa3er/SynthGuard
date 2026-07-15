# ─────────────────────────────────────────────
# SynthGuard Intelligence — Dockerfile
# Multi-stage build : leger en production
# ─────────────────────────────────────────────

FROM python:3.12-slim AS base

# Metadonnees
LABEL maintainer="El Houti Tlemcani Yahya"
LABEL project="SynthGuard Intelligence"

# Variables d'environnement systeme
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Repertoire de travail
WORKDIR /app

# ─────────────────────────────────────────────
# Stage 1 : Installation des dependances
# ─────────────────────────────────────────────
FROM base AS builder

# Dependances systeme minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les requirements
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────
# Stage 2 : Image finale
# ─────────────────────────────────────────────
FROM base AS final

# Dependances runtime uniquement
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copier les packages Python installes
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copier le code source
COPY . .

# Creer les dossiers necessaires
RUN mkdir -p /app/models /app/artifacts /app/logs

# Utilisateur non-root pour la securite
RUN useradd -m -u 1000 synthguard && \
    chown -R synthguard:synthguard /app
USER synthguard

# Port expose
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande de demarrage
CMD ["uvicorn", "api.app_api:app", "--host", "127.0.0.1", "--port", "8000"]