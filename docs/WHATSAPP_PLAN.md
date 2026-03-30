# QYNE v1 — WhatsApp Business: Complete Implementation Plan

## Vision

WhatsApp is the central nervous system of QYNE. Every customer of Whabi,
Aurora, Docflow, and CloudVZ interacts through one WhatsApp number.
The AI routes to the right product agent, handles support, processes
payments, and logs everything in Directus.

```
Customer WhatsApp message
    │
    ▼
Meta Cloud API → webhook → Agno /whatsapp/webhook
    │
    ▼
WhatsApp Support Team (router)
    │
    ├── "Quiero info de Whabi" → Whabi Support Agent
    ├── "Mi documento no carga" → Docflow Support Agent
    ├── "Como uso Aurora?" → Aurora Support Agent
    ├── "Quiero pagar" → Invoice Agent (with @approval)
    └── General question → General Support Agent
    │
    ▼
Agent responds → Meta Cloud API → Customer sees response
    │
    ▼
Directus: contact saved, ticket logged, conversation recorded
```

## What We Already Have

| Component | Status | Notes |
|-----------|--------|-------|
| WhatsApp Support Team | BUILT | 4 product agents + general fallback |
| Whatsapp interface in Agno | BUILT | `Whatsapp(agent=whatsapp_support_team)` in main.py |
| Webhook endpoint | BUILT | Agno exposes `/whatsapp/webhook` automatically |
| CRM tools | BUILT | save_contact, log_conversation, log_ticket, confirm_payment |
| Directus collections | BUILT | contacts, conversations, tickets, payments, events |
| RBAC | BUILT | Agent can create+read, not delete |
| Skills per product | BUILT | whabi, docflow, aurora skills loaded |

## What We Need

### Phase 1: Infrastructure (before anything works)

| Step | What | How | Blocker? |
|------|------|-----|----------|
| 1.1 | **Buy a domain** | Any registrar (Namecheap, Cloudflare, etc.) | YES — Meta requires HTTPS |
| 1.2 | **Point DNS to VPS** | A record: `api.yourdomain.com` → `89.167.96.99` | YES |
| 1.3 | **Open ports 80/443** | Hetzner Cloud Console → Firewall → Add rules | YES |
| 1.4 | **Configure Traefik SSL** | Let's Encrypt auto-cert via Traefik config | YES |
| 1.5 | **Verify HTTPS works** | `curl https://api.yourdomain.com/health` | YES |

### Phase 2: Meta Business Setup

| Step | What | How |
|------|------|-----|
| 2.1 | **Meta Developer Account** | developers.facebook.com → verify account |
| 2.2 | **Create Meta App** | Apps Dashboard → New App → "Other" → "Business" |
| 2.3 | **Meta Business Account** | business.facebook.com → create/verify business |
| 2.4 | **WhatsApp Business API** | App → WhatsApp Setup → "Start using the API" |
| 2.5 | **Get credentials** | Copy: Access Token, Phone Number ID, Business Account ID |
| 2.6 | **Configure webhook** | Callback URL: `https://api.yourdomain.com/whatsapp/webhook` |
| 2.7 | **Set verify token** | Same value as `WHATSAPP_VERIFY_TOKEN` in .env |
| 2.8 | **Subscribe to messages** | Webhook fields → subscribe to `messages` |
| 2.9 | **Add test number** | WhatsApp Setup → add your personal number for testing |

### Phase 3: QYNE Configuration

| Step | What | How |
|------|------|-----|
| 3.1 | **Set env vars** | In VPS .env: WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET |
| 3.2 | **Set APP_ENV=production** | For webhook signature validation |
| 3.3 | **Restart Agno** | `docker compose up -d agno` |
| 3.4 | **Test webhook** | Send message from test number → check Agno logs |
| 3.5 | **Verify Directus** | Check contacts, conversations collections for new data |

### Phase 4: Message Templates (required by Meta)

Meta requires pre-approved templates for business-initiated messages.
Customer-initiated messages (replies within 24h) are free-form.

| Template | Purpose | Category |
|----------|---------|----------|
| `welcome_message` | First contact greeting | Marketing |
| `payment_confirmation` | Payment received notification | Utility |
| `ticket_update` | Support ticket status change | Utility |
| `appointment_reminder` | Scheduled appointment reminder | Utility |
| `onboarding_step` | Product setup guidance | Utility |

Template format example:
```
Name: welcome_message
Language: es
Category: MARKETING
Body: "¡Hola {{1}}! Bienvenido a AikaLabs. Soy tu asistente virtual.
¿En qué producto puedo ayudarte hoy?
1️⃣ Whabi (WhatsApp CRM)
2️⃣ Docflow (Expedientes médicos)
3️⃣ Aurora (Asistente de voz)
4️⃣ CloudVZ (Cloud services)"
```

## Customer Journey: How It Works in Production

### New Customer (First Contact)

```
1. Customer sends "Hola" to WhatsApp number
2. Meta webhook → Agno /whatsapp/webhook
3. Agno creates session (phone number = user_id + session_id)
4. WhatsApp Support Team routes to General Support
5. General Support:
   - Greets in Spanish
   - Asks which product they need
   - Calls save_contact(phone=customer_phone, source="whatsapp")
   - Calls log_conversation(channel="whatsapp", intent="first_contact")
6. Customer replies "Quiero saber de Whabi"
7. Team re-routes to Whabi Support Agent
8. Whabi Support:
   - Explains plans and pricing
   - Calls save_contact(product="whabi", lead_score=5)
   - Calls log_support_ticket(product="whabi", intent="pricing")
```

### Payment Flow

```
1. Customer: "Quiero pagar el plan Pro de Whabi"
2. Whabi Support → Invoice Agent (via escalation or direct)
3. Invoice Agent:
   - Generates quote: "Plan Pro $149/mes + IVA = $177.31"
   - Asks for payment method
4. Customer: "Transferencia bancaria"
5. Invoice Agent:
   - Provides bank details
   - "Envíame el capture cuando hagas la transferencia"
6. Customer sends image (capture)
7. Agent:
   - Calls confirm_payment(product="whabi", amount="177.31", method="transfer")
   - @approval pauses execution → admin must approve
8. Admin approves in NEXUS dashboard (Approvals page)
9. Agent confirms to customer: "Pago recibido y verificado. Tu plan Pro está activo."
10. Directus: payment logged, task created for finance team
```

### Support Ticket Flow

```
1. Customer: "Mi documento no se sube en Docflow"
2. Team routes to Docflow Support
3. Docflow Support:
   - Asks for details (document type, error message)
   - Searches knowledge base for known issues
   - Calls log_support_ticket(product="docflow", intent="technical_issue", urgency="medium")
4. If resolved: logs resolution
5. If not resolved:
   - Calls escalate_to_human(product="docflow", reason="Upload failure")
   - Directus creates task for human agent
   - Customer: "Un agente humano te contactará pronto"
```

## Multi-Product Routing Logic

The WhatsApp Support Team uses `TeamMode.route` to select the right agent:

| Customer mentions | Routes to | Why |
|-------------------|-----------|-----|
| whabi, whatsapp, crm, campañas | Whabi Support | Product keywords |
| docflow, expediente, documento, historia clínica | Docflow Support | Product keywords |
| aurora, voz, asistente, pwa | Aurora Support | Product keywords |
| cloudvz, cloud, servidor, hosting | General Support (future: CloudVZ agent) | New product |
| pagar, factura, precio, plan | Invoice Agent (via escalation) | Billing intent |
| No clear product | General Support | Asks which product |

## Data Flow: Everything Goes to Directus

Every WhatsApp interaction creates records:

```
Message received → contacts (create/update)
                 → conversations (log every exchange)
                 → tickets (if support issue)
                 → payments (if payment confirmed)
                 → tasks (if escalated or follow-up needed)
                 → events (audit trail)
```

This data is available for:
- **Dash agent**: "Cuantos tickets de Whabi esta semana?"
- **Weekly report flow**: Automated metrics
- **Lead scorer flow**: Recalculate scores from activity
- **Sentiment analyzer flow**: Batch sentiment analysis
- **CRM page**: View all contacts and interactions
- **Data Explorer**: Browse all collections

## Pricing (Meta WhatsApp Cloud API — 2026)

Since July 2025, Meta charges per delivered template message:

| Message type | Cost (approx) |
|-------------|---------------|
| Customer-initiated (within 24h window) | Free |
| Business-initiated (template, utility) | $0.005-0.02 per message |
| Business-initiated (template, marketing) | $0.02-0.08 per message |
| Click-to-WhatsApp ad response (72h window) | Free |

For QYNE: Most messages are customer-initiated (free). Templates are
only for proactive outreach (payment confirmations, reminders).

## Security Considerations

| Measure | Implementation |
|---------|---------------|
| Webhook signature validation | `WHATSAPP_APP_SECRET` + `APP_ENV=production` |
| HTTPS required | Traefik + Let's Encrypt |
| Rate limiting | Meta handles rate limits (500 msg/sec) |
| PII masking | Agno guardrails mask sensitive data in logs |
| No delete permissions | Agent token can't delete customer data |
| Audit trail | Every interaction logged in Directus events |

## Traefik Configuration for WhatsApp

Current Traefik config needs a route for the WhatsApp webhook:

```yaml
# config/traefik/dynamic/whatsapp.yml
http:
  routers:
    whatsapp-webhook:
      rule: "Host(`api.yourdomain.com`) && PathPrefix(`/whatsapp`)"
      service: agno
      entryPoints:
        - websecure
      tls:
        certResolver: letsencrypt

  services:
    agno:
      loadBalancer:
        servers:
          - url: "http://agno:8000"
```

## Implementation Order

```
Week 1: Domain + SSL + Firewall
  ├── Buy domain
  ├── Configure DNS
  ├── Open ports 80/443 in Hetzner
  ├── Configure Traefik with Let's Encrypt
  └── Verify HTTPS works

Week 2: Meta Business Setup
  ├── Create Meta Developer Account
  ├── Create Meta App
  ├── Setup WhatsApp Business API
  ├── Get credentials
  └── Configure webhook

Week 3: Testing + Templates
  ├── Set env vars on VPS
  ├── Test with personal number
  ├── Create message templates
  ├── Submit templates for approval
  └── Test full flow (message → agent → response → Directus)

Week 4: Production
  ├── Business verification (can take 2-14 days)
  ├── Production phone number
  ├── Monitor first real conversations
  └── Iterate on agent instructions based on real usage
```

## What's NOT in This Phase

- Payment gateway integration (Stripe, PayPal) — future
- Automated payment verification from bank API — future
- WhatsApp Catalog/Shop integration — future
- WhatsApp Flows (interactive forms) — future
- Broadcast/bulk messaging campaigns — future
- CloudVZ dedicated agent — future (uses General Support for now)
