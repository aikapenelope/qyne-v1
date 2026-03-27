#!/usr/bin/env bash
# =============================================================================
# QYNE v1 — First Deploy Setup
# =============================================================================
# Run this once on a fresh VPS to initialize the environment.
# Usage: chmod +x setup.sh && ./setup.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[NEXUS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------------------------------------------------------------------------
# 1. Check prerequisites
# ---------------------------------------------------------------------------

log "Checking prerequisites..."

command -v docker >/dev/null 2>&1 || err "Docker is not installed. Install it first: https://docs.docker.com/engine/install/"
command -v docker compose >/dev/null 2>&1 || err "Docker Compose v2 is not installed."

log "Docker $(docker --version | grep -oP '\d+\.\d+\.\d+')"

# ---------------------------------------------------------------------------
# 2. Create .env from template
# ---------------------------------------------------------------------------

if [ -f .env ]; then
    warn ".env already exists. Skipping creation."
else
    log "Creating .env from .env.example..."
    cp .env.example .env

    # Generate random secrets
    RANDOM_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 64 /dev/urandom | xxd -p | tr -d '\n' | head -c 64)
    RANDOM_PG_PASS=$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n' | head -c 32)
    RANDOM_N8N_PASS=$(openssl rand -hex 12 2>/dev/null || head -c 24 /dev/urandom | xxd -p | tr -d '\n' | head -c 24)
    RANDOM_RUSTFS_PASS=$(openssl rand -hex 16 2>/dev/null || head -c 32 /dev/urandom | xxd -p | tr -d '\n' | head -c 32)
    RANDOM_ADMIN_PASS=$(openssl rand -hex 10 2>/dev/null || head -c 20 /dev/urandom | xxd -p | tr -d '\n' | head -c 20)

    sed -i "s/CHANGE_ME_STRONG_PASSWORD/${RANDOM_PG_PASS}/g" .env
    sed -i "s/CHANGE_ME_RANDOM_256BIT_STRING/${RANDOM_SECRET}/g" .env
    sed -i "s/CHANGE_ME_ADMIN_PASSWORD/${RANDOM_ADMIN_PASS}/g" .env
    sed -i "s/CHANGE_ME_N8N_PASSWORD/${RANDOM_N8N_PASS}/g" .env
    sed -i "s/CHANGE_ME_RUSTFS_PASSWORD/${RANDOM_RUSTFS_PASS}/g" .env

    log ".env created with random secrets."
    warn "Edit .env to add your LLM API keys (GROQ_API_KEY, OPENROUTER_API_KEY, etc.)"
fi

# ---------------------------------------------------------------------------
# 3. Pull images and build
# ---------------------------------------------------------------------------

log "Pulling Docker images (this may take a few minutes on first run)..."
docker compose pull --quiet 2>/dev/null || docker compose pull

log "Building custom images (agno, frontend, workers)..."
docker compose build --quiet 2>/dev/null || docker compose build

# ---------------------------------------------------------------------------
# 4. Start services
# ---------------------------------------------------------------------------

log "Starting all services..."
docker compose up -d

# ---------------------------------------------------------------------------
# 5. Wait for health checks
# ---------------------------------------------------------------------------

log "Waiting for services to become healthy..."

wait_for_service() {
    local name=$1
    local max_wait=${2:-120}
    local elapsed=0

    while [ $elapsed -lt $max_wait ]; do
        status=$(docker inspect --format='{{.State.Health.Status}}' "qyne-${name}" 2>/dev/null || echo "missing")
        if [ "$status" = "healthy" ]; then
            log "  ${name}: healthy"
            return 0
        fi
        sleep 5
        elapsed=$((elapsed + 5))
    done

    warn "  ${name}: not healthy after ${max_wait}s (status: ${status})"
    return 1
}

wait_for_service "postgres" 60
wait_for_service "redis" 30
wait_for_service "reranker" 120
wait_for_service "rustfs" 30
wait_for_service "directus" 90
wait_for_service "agno" 60
wait_for_service "n8n" 60
wait_for_service "prefect" 60

# ---------------------------------------------------------------------------
# 6. Summary
# ---------------------------------------------------------------------------

echo ""
log "============================================"
log "  QYNE v1 is running!"
log "============================================"
echo ""
log "Services (access via Tailscale):"
log "  Directus Admin:   http://$(hostname -I | awk '{print $1}'):8055"
log "  Agno AgentOS:     http://$(hostname -I | awk '{print $1}'):8000"
log "  Frontend:         http://$(hostname -I | awk '{print $1}'):3000"
log "  n8n:              http://$(hostname -I | awk '{print $1}'):5678"
log "  Prefect:          http://$(hostname -I | awk '{print $1}'):4200"
log "  Uptime Kuma:      http://$(hostname -I | awk '{print $1}'):3001"
log "  RustFS Console:   http://$(hostname -I | awk '{print $1}'):9001"
log "  Traefik:          http://$(hostname -I | awk '{print $1}'):8080"
echo ""
log "Next steps:"
log "  1. Edit .env and add your LLM API keys"
log "  2. Restart: docker compose restart agno"
log "  3. Connect os.agno.com -> Add OS -> Local -> http://<tailscale-ip>:8000"
log "  4. Open Directus and create your collections"
echo ""
