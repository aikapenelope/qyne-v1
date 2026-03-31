# QYNE v1 — WhatsApp Implementation Guide

## Current State

Everything is built. We need infrastructure + Meta configuration.

### What's Ready (Code)

| Component | File | Status |
|-----------|------|--------|
| Whatsapp interface | `main.py` → `Whatsapp(agent=whatsapp_support_team)` | BUILT |
| Webhook endpoint | Auto-mounted at `/whatsapp/webhook` by Agno | BUILT |
| WhatsApp Support Team | `agents/whatsapp_support/agents.py` | BUILT (4 product agents) |
| CRM tools | `tools/directus_business.py` | BUILT (save_contact, log_conversation, etc.) |
| Directus collections | contacts, conversations, tickets, payments | BUILT |
| Activation condition | `if os.getenv("WHATSAPP_ACCESS_TOKEN")` | BUILT |

### What's Missing (Infrastructure)

| Item | Why needed | Blocker? |
|------|-----------|----------|
| Domain name | Meta requires HTTPS webhook URL | YES |
| SSL certificate | Meta requires valid HTTPS | YES |
| Traefik route | Route `/whatsapp/*` to Agno container | YES |
| Open ports 80/443 | Hetzner firewall blocks them | YES |
| Meta Business Account | Required for WhatsApp API | YES |
| Meta App | Required for API credentials | YES |
| WhatsApp Business API setup | Generates tokens | YES |

## Agno WhatsApp Interface — Technical Reference

### Whatsapp Class (v2.5.11)

```python
from agno.os.interfaces.whatsapp.whatsapp import Whatsapp

Whatsapp(
    agent=None,                    # Agent instance (use agent OR team)
    team=None,                     # Team instance (use agent OR team)
    workflow=None,                 # Workflow instance
    prefix="/whatsapp",            # URL prefix for endpoints
    tags=None,                     # FastAPI tags
    show_reasoning=False,          # Include reasoning in responses
    send_user_number_to_context=True,  # Pass phone as user_id
    access_token=None,             # Override env WHATSAPP_ACCESS_TOKEN
    phone_number_id=None,          # Override env WHATSAPP_PHONE_NUMBER_ID
    verify_token=None,             # Override env WHATSAPP_VERIFY_TOKEN
    media_timeout=30,              # Timeout for media downloads
    enable_encryption=False,       # End-to-end encryption
    encryption_key=None,           # Encryption key
)
```

### Endpoints (auto-mounted)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/whatsapp/status` | Health check |
| GET | `/whatsapp/webhook` | Meta webhook verification (hub.challenge) |
| POST | `/whatsapp/webhook` | Receive messages (text, image, video, audio, document) |

### Session Management

- Phone number = `user_id` = `session_id`
- One WhatsApp conversation = one Agno session
- All memory, learning, and history scoped to the phone number
- Persistent across messages (user sends message today, agent remembers tomorrow)

### Message Types Supported

| Type | Handling |
|------|---------|
| Text | Processed as agent input |
| Image | Downloaded, passed as media to agent |
| Video | Downloaded, passed as media |
| Audio | Downloaded, passed as media |
| Document | Downloaded, passed as media |

### Our Configuration

```python
# In main.py
if os.getenv("WHATSAPP_ACCESS_TOKEN"):
    interfaces.append(Whatsapp(agent=whatsapp_support_team))
```

We use `agent=whatsapp_support_team` (not `team=`) because the WhatsApp
Support Team is itself a Team that routes internally. The Whatsapp interface
treats it as a single agent endpoint.

## Environment Variables Required

```env
# Required for WhatsApp to activate
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxx          # From Meta App → WhatsApp Setup
WHATSAPP_PHONE_NUMBER_ID=1234567890       # From Meta App → WhatsApp Setup
WHATSAPP_VERIFY_TOKEN=qyne-webhook-2026   # You choose this (any string)

# Required for production (webhook signature validation)
WHATSAPP_APP_SECRET=abcdef123456          # From Meta App → Settings → Basic
APP_ENV=production                         # Enables signature validation
```

These go in Pulumi ESC (`platform-infra/secrets`) and are injected into
the Agno container via docker-compose.

## Infrastructure Setup

### Step 1: Buy Domain

Any registrar works. Recommended: Cloudflare (free DNS, easy SSL).

Example: `api.qyne.dev` or `wa.aikalabs.cc`

### Step 2: Configure DNS

```
A record: api.qyne.dev → 89.167.96.99
```

If using Cloudflare: set proxy to "DNS only" (grey cloud) so Traefik
handles SSL, not Cloudflare.

### Step 3: Open Firewall Ports

In Hetzner Cloud Console → Firewalls → your firewall:

```
Add rule: TCP port 80  (HTTP)  from 0.0.0.0/0
Add rule: TCP port 443 (HTTPS) from 0.0.0.0/0
```

### Step 4: Configure Traefik for SSL

Add to `docker-compose.yml` Traefik service:

```yaml
traefik:
  command:
    - "--entrypoints.web.address=:80"
    - "--entrypoints.websecure.address=:443"
    - "--certificatesresolvers.letsencrypt.acme.email=admin@qyne.dev"
    - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - "./letsencrypt:/letsencrypt"
```

Add dynamic config for WhatsApp route:

```yaml
# config/traefik/dynamic/whatsapp.yml
http:
  routers:
    whatsapp:
      rule: "Host(`api.qyne.dev`) && PathPrefix(`/whatsapp`)"
      service: agno
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt

    # Redirect HTTP to HTTPS
    http-redirect:
      rule: "Host(`api.qyne.dev`)"
      entryPoints:
        - web
      middlewares:
        - redirect-to-https

  middlewares:
    redirect-to-https:
      redirectScheme:
        scheme: https

  services:
    agno:
      loadBalancer:
        servers:
          - url: "http://agno:8000"
```

### Step 5: Verify HTTPS

```bash
curl https://api.qyne.dev/whatsapp/status
# Should return: {"status": "ok"}
```

## Meta Business Setup

### Step 1: Create Meta Developer Account

1. Go to [developers.facebook.com](https://developers.facebook.com/)
2. Verify your account
3. Accept developer terms

### Step 2: Create Meta App

1. [Apps Dashboard](https://developers.facebook.com/apps/) → Create App
2. Use Case: **"Other"**
3. App Type: **"Business"**
4. Name: "QYNE WhatsApp"
5. Contact email: your email
6. Click Create App

### Step 3: Setup WhatsApp Business API

1. In your app → Add Product → WhatsApp
2. Click "Start using the API" (API Setup)
3. Generate a **permanent access token** (not temporary):
   - Go to Business Settings → System Users
   - Create system user with admin role
   - Generate token with `whatsapp_business_messaging` permission
4. Copy:
   - **Access Token** → `WHATSAPP_ACCESS_TOKEN`
   - **Phone Number ID** → `WHATSAPP_PHONE_NUMBER_ID`
   - **App Secret** (Settings → Basic) → `WHATSAPP_APP_SECRET`

### Step 4: Configure Webhook

1. In WhatsApp Setup → Webhook section → Edit
2. **Callback URL**: `https://api.qyne.dev/whatsapp/webhook`
3. **Verify Token**: same as `WHATSAPP_VERIFY_TOKEN` in your env
4. Click "Verify and save"
5. Subscribe to `messages` field under `whatsapp_business_account`

**Important**: Agno must be running with the env vars set BEFORE
you verify the webhook. Meta sends a GET request to verify.

### Step 5: Add Test Number

1. In WhatsApp Setup → add your personal number as test recipient
2. Send a test message from your phone to the WhatsApp Business number
3. Check Agno logs: `docker logs qyne-agno -f`

### Step 6: Business Verification (for production)

1. Go to Business Settings → Business Verification
2. Submit business documents
3. Wait 2-14 business days for approval
4. Once verified: your number can send to any WhatsApp user

## Message Flow in Production

```
Customer sends "Hola" to WhatsApp number
    │
    ▼
Meta Cloud API receives message
    │
    ▼
Meta sends POST to https://api.qyne.dev/whatsapp/webhook
    │
    ▼
Traefik (SSL termination) → forwards to http://agno:8000/whatsapp/webhook
    │
    ▼
Agno Whatsapp interface:
  1. Validates webhook signature (APP_SECRET)
  2. Extracts message text + phone number
  3. Sets user_id = phone_number, session_id = phone_number
  4. Calls whatsapp_support_team.arun(message, user_id, session_id)
    │
    ▼
WhatsApp Support Team routes to correct agent:
  - "info de Whabi" → Whabi Support Agent
  - "mi documento" → Docflow Support Agent
  - "como uso Aurora" → Aurora Support Agent
  - General → General Support Agent
    │
    ▼
Agent processes, calls tools (save_contact, log_conversation, etc.)
    │
    ▼
Agent response → Agno sends via Meta Cloud API → Customer sees response
    │
    ▼
Directus: contact saved, conversation logged, ticket created (if needed)
```

## Security Checklist

| Check | How |
|-------|-----|
| Webhook signature validation | `APP_ENV=production` + `WHATSAPP_APP_SECRET` |
| HTTPS only | Traefik with Let's Encrypt |
| Token in ESC (not in code) | Pulumi ESC `platform-infra/secrets` |
| Agent can't delete data | RBAC: Agent Support role = create+read only |
| Rate limiting | Meta handles (500 msg/sec max) |
| PII in logs | Agno doesn't log message content by default |

## Testing Checklist

Before going live:

- [ ] `curl https://api.qyne.dev/whatsapp/status` returns OK
- [ ] Meta webhook verification succeeds
- [ ] Send "Hola" from test number → get response
- [ ] Send "Info de Whabi" → routes to Whabi agent
- [ ] Send "Mi documento no carga" → routes to Docflow agent
- [ ] Check Directus: contact created with phone number
- [ ] Check Directus: conversation logged
- [ ] Send image → agent acknowledges receipt
- [ ] Check Agno traces: WhatsApp messages appear

## Implementation Order

```
Day 1: Domain + DNS + Firewall
Day 2: Traefik SSL + verify HTTPS
Day 3: Meta Developer Account + App + WhatsApp API
Day 4: Set env vars + restart Agno + verify webhook
Day 5: Test with personal number
Day 6: Submit business verification
Day 7+: Wait for verification (2-14 days)
```

## Cost

| Item | Cost |
|------|------|
| Domain | $10-15/year |
| SSL | Free (Let's Encrypt) |
| Meta WhatsApp API | Free for customer-initiated messages |
| Business-initiated templates | $0.005-0.08 per message |
| Infrastructure | Already running (Hetzner VPS) |
