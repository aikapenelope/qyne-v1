# WhatsApp Cloud API — Roadmap de Conexion a QYNE

Estado actual de la plataforma y pasos para tener WhatsApp funcionando
con el sistema de soporte y cobro de Docflow, Aurora y Nova.

---

## Estado actual de la plataforma

### LISTO (verificado)

| Componente | Detalle |
|------------|---------|
| WhatsApp Support Team (router) | Rutea a Docflow Support, Aurora Support, General Support |
| Agentes de soporte por producto | Skills, knowledge base, learning, guardrails |
| Interfaz WhatsApp en Agno | `Whatsapp(agent=whatsapp_support_team)` en main.py |
| Tools de negocio | confirm_payment, log_support_ticket, save_contact, escalate_to_human, log_conversation |
| Directus CRM | 7 colecciones funcionando: contacts (8), companies, tickets, payments, conversations, tasks, events (15) |
| Dominio DNS | `qynewa.aikalabs.cc` -> `89.167.96.99` (Cloudflare, DNS only) |
| Firewall Hetzner | Puertos 22, 80, 443 abiertos |
| SSL Let's Encrypt | Certificado valido para `qynewa.aikalabs.cc` (expira Jul 24 2026) |
| Traefik webhook route | `Host(qynewa.aikalabs.cc) && Path(/whatsapp/webhook)` con TLS |
| Agno AgentOS | 11 contenedores healthy |

### PENDIENTE (solo Meta)

| # | Que falta | Quien |
|---|-----------|-------|
| 1 | Numero de Twilio registrado en Meta | Tu |
| 2 | System User token permanente | Tu |
| 3 | App Secret | Tu |
| 4 | Variables en `.env` + reiniciar Agno | Tu (o yo via SSH) |
| 5 | Webhook registrado en Meta | Tu |

---

## Sprint 2: Conectar Meta a QYNE

> Sprint 1 (infra) ya esta completado: firewall, dominio, SSL, Traefik.

### 2A. Registrar numero de Twilio en Meta (tu)

1. Ir a [Meta App Dashboard](https://developers.facebook.com/apps) > tu app
2. WhatsApp > API Setup > Add phone number
3. Ingresar el numero de Twilio (formato `+1234567890`)
4. Meta envia OTP por SMS
5. Ver el SMS en **Twilio Console > Phone Numbers > Messaging Logs**
6. Ingresar el codigo en Meta
7. Anotar el **Phone Number ID** que aparece

> IMPORTANTE: Registrar directo en Meta, NO via Twilio Console.
> Asi los webhooks van a tu servidor, no a Twilio.

### 2B. Crear System User token permanente (tu)

1. [business.facebook.com/latest/settings](https://business.facebook.com/latest/settings) > System Users > Add
2. Nombre: "QYNE Bot", rol: Admin
3. Asignar assets:
   - Meta App > Manage app (full control)
   - WhatsApp Business Account > Manage (full control)
4. Generate Token con permisos:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
5. Copiar el token (no expira)

### 2C. Obtener App Secret (tu)

1. Meta App > Settings > Basic
2. Copiar **App Secret**

### 2D. Configurar servidor

Editar `/opt/qyne-v1/.env` via SSH:

```bash
ssh root@89.167.96.99  # via Tailscale
cd /opt/qyne-v1
nano .env
```

Descomentar y llenar:

```bash
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx     # del paso 2B
WHATSAPP_PHONE_NUMBER_ID=123456789012345     # del paso 2A
WHATSAPP_VERIFY_TOKEN=qyne-verify-2026       # no cambiar
WHATSAPP_APP_SECRET=abcdef1234567890         # del paso 2C
```

Reiniciar Agno:

```bash
docker compose up -d agno
docker logs -f qyne-agno
# Buscar en logs: "WhatsApp interface registered"
```

### 2E. Registrar webhook en Meta (tu)

1. Meta App > WhatsApp > Configuration
2. Webhook > Edit:
   - **Callback URL:** `https://qynewa.aikalabs.cc/whatsapp/webhook`
   - **Verify token:** `qyne-verify-2026`
3. Click **"Verify and Save"**
   - Agno responde automaticamente al challenge
4. Suscribir al campo: **messages**

### 2F. Agregar testers

1. Meta App > App Roles > Roles
2. Agregar tu numero personal como Tester
3. Permite probar sin publicar la app

### 2G. Primer test

1. Desde tu WhatsApp, envia "Hola" al numero de Twilio
2. Verificar respuesta del agente
3. Verificar logs: `docker logs qyne-agno --tail 20`

**Entregable:** Mensaje enviado y respondido por Agno via WhatsApp.

---

## Sprint 3: Testing completo

### 3A. Test de routing

| Mensaje de prueba | Agente esperado |
|-------------------|----------------|
| "Necesito ayuda con mi historia clinica" | Docflow Support |
| "La app de voz no funciona" | Aurora Support |
| "Cuanto cuesta el plan Pro?" | General Support |
| "Quiero pagar mi suscripcion de Docflow" | Docflow Support |

### 3B. Test de tools (verificar en Directus)

| Accion del cliente | Tool | Verificar en |
|--------------------|------|-------------|
| Da su nombre y telefono | save_contact | `contacts` |
| Pregunta por precios | log_support_ticket | `tickets` |
| Dice que quiere pagar | confirm_payment | `payments` (requiere aprobacion) |
| Queja seria | escalate_to_human | `tasks` |
| Fin de conversacion | log_conversation | `conversations` |

### 3C. Test de sesiones

- Enviar 3-4 mensajes seguidos: el agente debe recordar contexto
- Enviar `/new`: debe iniciar sesion nueva
- Verificar historial en la UI de QYNE (`/chat` y `/whatsapp`)

### 3D. Test de edge cases

- Enviar imagen, audio, documento
- Mensaje muy largo (>1000 chars)
- Verificar que fuera de la ventana de 24h no se envian mensajes

**Entregable:** Todos los tests pasando, lista de bugs si hay.

---

## Sprint 4: Produccion

### 4A. Verificacion del negocio en Meta

1. Meta Business Suite > Settings > Business Verification
2. Subir documentos (nombre legal, direccion, ID del negocio)
3. Esperar aprobacion (1-5 dias habiles)

### 4B. App Review

1. Meta App > App Review > Request Permissions
2. Solicitar `whatsapp_business_messaging`
3. Esperar aprobacion

### 4C. Display name

1. WhatsApp Manager > Phone Numbers > tu numero
2. Configurar nombre visible (ej: "QYNE Soporte")
3. Meta lo revisa (24-48h)

### 4D. Message templates

| Template | Categoria | Ejemplo |
|----------|-----------|---------|
| `payment_confirmation` | utility | "Hola {{1}}, tu pago de {{2}} fue recibido." |
| `appointment_reminder` | utility | "Recordatorio: tu cita es manana {{1}} a las {{2}}." |
| `welcome_new_client` | marketing | "Bienvenido a {{1}}! Soy tu asistente virtual." |

### 4E. Monitoreo

- Uptime Kuma: agregar check para `https://qynewa.aikalabs.cc/whatsapp/webhook`
- Revisar quality rating en Meta Dashboard semanalmente
- Alerta en n8n si el webhook deja de responder

**Entregable:** App publicada, templates aprobados, monitoreo activo.

---

## Timeline

```
Sprint 1  COMPLETADO    Firewall, dominio, SSL, Traefik
Sprint 2  ~1 dia        Registro Meta + conectar + primer test
Sprint 3  ~1-2 dias     Testing completo
Sprint 4  ~5-7 dias     Produccion (espera de Meta)
```

---

## Configuracion final

**Webhook URL:** `https://qynewa.aikalabs.cc/whatsapp/webhook`

**Variables de entorno** (`/opt/qyne-v1/.env`):

```bash
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=qyne-verify-2026
WHATSAPP_APP_SECRET=abcdef1234567890
```

**Certificado SSL:** Let's Encrypt, auto-renovacion via Traefik.

---

## Notas

- **Costo Meta:** Mensajes de servicio (respuestas dentro de 24h) son gratis.
  Colombia: ~$0.0436/msg marketing, ~$0.008/msg utility.
- **Rate limits:** Numero nuevo = Tier 1 (1,000 msgs/dia). Sube con buen quality rating.
- **Twilio:** Solo sirvio para recibir el OTP. No interviene despues.
- **Coexistence:** No disponible via Self Sign-Up.
