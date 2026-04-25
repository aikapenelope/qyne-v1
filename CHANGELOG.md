# Changelog

All notable changes to QYNE are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- **WhatsAppTools** on all support agents: reply buttons, list menus, and
  interactive messages for better customer UX during support and billing flows.
- **WhatsApp-optimized instructions** across all support agents: concise
  responses, short paragraphs, no markdown tables/code blocks, button/list
  usage guidance.
- **`determine_input_for_members=False`** on WhatsApp Support Team: customer
  messages pass directly to the routed agent without leader reformulation,
  reducing latency.
- **CHANGELOG.md** for tracking platform progress.
- **`WHATSAPP_APP_SECRET`** env var in docker-compose and .env.example for
  webhook signature validation (HMAC-SHA256).
- **Let's Encrypt SSL** on Traefik for `qynewa.aikalabs.cc`.
- **WhatsApp Setup Roadmap** (`docs/WHATSAPP_SETUP_ROADMAP.md`) with
  sprint-based plan for Meta Cloud API connection.

### Changed
- WhatsApp webhook router now uses `Host(qynewa.aikalabs.cc)` with TLS
  cert resolver instead of bare `Path()` match.
- General Support agent now uses reply buttons to ask customers which
  product they need help with, instead of plain text.
- Hetzner firewall (`fw-mastra`) opened ports 80/443 for Traefik.

### Removed
- **Whabi** product: agent, skills directory, routing rules, and all
  references across Python code, frontend TSX, and active skill files.
  Historical references in knowledge base docs preserved.
- `whabi_support_agent` and `_whabi_skills` from both modular and legacy
  agent files.
- Whabi pricing from invoice agent and onboarding agent instructions.

### Fixed
- Product references updated from "Whabi, Docflow, Aurora" to
  "Docflow, Aurora, Nova" across all agent instructions, models,
  frontend suggestions, and skill files.
