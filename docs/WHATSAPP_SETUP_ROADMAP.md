# WhatsApp Cloud API — Roadmap de Conexion a QYNE

Estado actual de la plataforma y pasos para tener WhatsApp funcionando
con el sistema de soporte y cobro de Docflow, Aurora y Nova.

---

## Estado actual de la plataforma

### Lo que YA esta listo

| Componente | Estado | Detalle |
|------------|--------|---------|
| WhatsApp Support Team (router) | LISTO | Rutea a Docflow Support, Aurora Support, General Support |
| Agentes de soporte por producto | LISTO | Cada uno con skills, knowledge base, learning, guardrails |
| Interfaz WhatsApp en Agno | LISTO | `Whatsapp(agent=whatsapp_support_team)` en main.py |
| Tools de negocio | LISTO (codigo) | confirm_payment, log_support_ticket, save_contact, etc. |
| Traefik webhook route | LISTO | `Path(/whatsapp/webhook)` -> agno:8000 |
| Variables de entorno | LISTO (template) | En .env.example y docker-compose.yml |
| Agno AgentOS corriendo | LISTO | 11 contenedores healthy, 3 semanas uptime |

### Lo que FALTA

| Componente | Estado | Impacto |
|------------|--------|---------|
| Numero de WhatsApp registrado en Meta | PENDIENTE | Sin esto no hay WhatsApp |
| Token permanente de Meta | PENDIENTE | Sin esto no hay WhatsApp |
| Dominio con HTTPS | PENDIENTE | Meta requiere HTTPS para webhooks |
| SSL en Traefik | PENDIENTE | No hay cert resolver configurado |
| Colecciones en Directus | PENDIENTE | Las tools fallan sin las tablas |
| Webhook registrado en Meta | PENDIENTE | Depende de HTTPS |
| Meta App publicada | PENDIENTE | Solo test webhooks sin publicar |
| App Secret en env vars | PENDIENTE | Seguridad de webhooks |

---

## Fase 1: Infraestructura base (hacer ANTES de WhatsApp)

Estas cosas se pueden hacer ahora mismo, sin esperar el numero de Twilio.

### 1.1 Crear colecciones en Directus

Las tools de soporte escriben a estas colecciones que **no existen** en Directus:

| Coleccion | Campos minimos | Usada por |
|-----------|---------------|-----------|
| `contacts` | first_name, last_name, email, phone, product, lead_score, source, status | save_contact |
| `companies` | name, domainName, employees, address | save_company |
| `tickets` | product, intent, summary, resolution, urgency, status | log_support_ticket |
| `payments` | amount, method, reference, status, approved_by, product | confirm_payment |
| `conversations` | channel, direction, raw_message, agent_response, intent, sentiment, lead_score, agent_name | log_conversation |
| `tasks` | title, body, status | escalate_to_human, confirm_payment, log_support_ticket |
| `events` | type, payload (JSON) | escalate_to_human, save_contact, save_company |

**Como hacerlo:**
1. Ir a Directus admin: `http://<tailscale-ip>:8055`
2. Settings > Data Model > Create Collection para cada una
3. O usar el script `scripts/init-directus.py` si esta implementado

> Sin estas colecciones, los agentes pueden responder pero NO guardan
> nada en el CRM. Los pagos no se registran, los contactos se pierden.

### 1.2 Configurar dominio + SSL

**Opcion A: Cloudflare (recomendada)**

1. En Cloudflare, crear registro DNS:
   ```
   Tipo: A
   Nombre: api (o el subdominio que prefieras)
   IP: 89.167.96.99
   Proxy: OFF (DNS only, para que Traefik maneje SSL)
   ```

2. Agregar cert resolver a `config/traefik/traefik.yml`:
   ```yaml
   certificatesResolvers:
     letsencrypt:
       acme:
         email: tu@email.com
         storage: /letsencrypt/acme.json
         httpChallenge:
           entryPoint: web
   ```

3. Actualizar labels de WhatsApp en `docker-compose.yml`:
   ```yaml
   labels:
     - "traefik.enable=true"
     - "traefik.http.routers.whatsapp.rule=Host(`api.tudominio.com`) && Path(`/whatsapp/webhook`)"
     - "traefik.http.routers.whatsapp.entrypoints=websecure"
     - "traefik.http.routers.whatsapp.tls.certresolver=letsencrypt"
     - "traefik.http.services.whatsapp.loadbalancer.server.port=8000"
   ```

4. Reiniciar Traefik:
   ```bash
   docker compose up -d traefik
   ```

5. Verificar que HTTPS funciona:
   ```bash
   curl -I https://api.tudominio.com/whatsapp/webhook
   # Debe responder (404 o 200, no importa, lo importante es que HTTPS funcione)
   ```

**Opcion B: Sin dominio (Tailscale Funnel)**

```bash
tailscale funnel 8000
# Te da una URL tipo https://mastra-server.tail12345.ts.net
# Usas esa URL como webhook en Meta
```

Limitacion: la URL cambia si reinicias Tailscale.

---

## Fase 2: Registro en Meta Cloud API

### 2.1 Comprar numero en Twilio

1. Ir a [Twilio Console](https://console.twilio.com) > Phone Numbers > Buy a Number
2. Comprar un numero con capacidad **SMS** (para recibir el OTP de Meta)
3. Anotar el numero en formato E.164 (ej: `+12025551234`)

### 2.2 Crear Meta App

1. Ir a [Meta App Dashboard](https://developers.facebook.com/apps)
2. Create App > nombre: "QYNE Support"
3. Use case: "Connect with customers through WhatsApp" (o "Other" > tipo "Business")
4. Vincular Business Portfolio

### 2.3 Registrar el numero de Twilio en Meta

1. En Meta App > WhatsApp > API Setup
2. Add phone number > ingresar el numero de Twilio
3. Meta envia OTP por SMS al numero de Twilio
4. Ver el SMS en Twilio Console > Phone Numbers > Messaging Logs
5. Ingresar el codigo en Meta
6. Anotar el **Phone Number ID**

> IMPORTANTE: No registrar el numero via Twilio Console (Self Sign-up).
> Registrarlo directo en Meta para que los webhooks vayan a tu servidor,
> no a Twilio.

### 2.4 Crear System User token permanente

1. [Business Settings](https://business.facebook.com/latest/settings) > System Users > Add
2. Nombre: "QYNE Bot", rol: Admin
3. Asignar assets:
   - Meta App > Manage app (full control)
   - WhatsApp Business Account > Manage (full control)
4. Generate Token con permisos:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
5. Copiar el token (no expira)

### 2.5 Obtener App Secret

1. Meta App > Settings > Basic
2. Copiar App Secret

---

## Fase 3: Conectar Meta a QYNE

### 3.1 Configurar variables de entorno

En el servidor (`/opt/qyne-v1/.env`):

```bash
# Descomentar y llenar:
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=qyne-verify-2026
# Agregar (no esta en el template actual):
WHATSAPP_APP_SECRET=abcdef1234567890
```

### 3.2 Reiniciar Agno

```bash
cd /opt/qyne-v1
docker compose up -d agno
docker logs -f qyne-agno
# Buscar: "WhatsApp interface registered"
```

### 3.3 Registrar webhook en Meta

1. Meta App > WhatsApp > Configuration
2. Webhook > Edit:
   - Callback URL: `https://api.tudominio.com/whatsapp/webhook`
   - Verify token: `qyne-verify-2026`
3. Click "Verify and Save"
   - Agno responde automaticamente al challenge de verificacion
4. Suscribir al campo: `messages`

### 3.4 Agregar testers (para probar sin publicar la app)

1. Meta App > App Roles > Roles
2. Agregar tu numero personal como Tester
3. Esto permite recibir webhooks de tu numero sin publicar la app

---

## Fase 4: Testing

### 4.1 Test basico

1. Desde tu WhatsApp personal, envia "Hola" al numero registrado
2. Verificar en logs:
   ```bash
   docker logs qyne-agno --tail 20
   ```
3. El whatsapp_support_team debe rutear a General Support
4. Debes recibir respuesta en WhatsApp

### 4.2 Test de routing

| Mensaje | Agente esperado |
|---------|----------------|
| "Necesito ayuda con mi historia clinica" | Docflow Support |
| "La app de voz no funciona" | Aurora Support |
| "Cuanto cuesta el plan Pro?" | General Support (pregunta ambigua) |
| "Quiero pagar mi suscripcion de Docflow" | Docflow Support |

### 4.3 Test de tools

| Accion | Tool | Verificar en Directus |
|--------|------|----------------------|
| Cliente da su nombre | save_contact | Nuevo registro en `contacts` |
| Cliente pregunta precio | log_support_ticket | Nuevo registro en `tickets` |
| Cliente quiere pagar | confirm_payment | Aprobacion pendiente en UI |
| Queja seria | escalate_to_human | Tarea en `tasks` |

### 4.4 Test de sesiones

- Enviar varios mensajes seguidos: el agente debe recordar el contexto
- Enviar `/new`: debe iniciar sesion nueva
- Verificar que el historial se guarda en SQLite

---

## Fase 5: Produccion

### 5.1 Publicar la Meta App

1. Completar verificacion del negocio en Meta Business Suite
   - Requiere: nombre legal, direccion, documento de identidad del negocio
   - Tarda: 1-5 dias habiles
2. Solicitar App Review para `whatsapp_business_messaging`
3. Una vez aprobado, la app recibe webhooks de cualquier usuario

### 5.2 Configurar display name

1. En WhatsApp Manager, configurar el nombre que ven los clientes
2. Meta lo revisa (24-48h)
3. Si lo rechazan, el numero queda limitado a 250 mensajes/dia

### 5.3 Crear message templates

Para enviar mensajes fuera de la ventana de 24h (notificaciones, recordatorios):

1. WhatsApp Manager > Message Templates
2. Crear templates para:
   - Confirmacion de pago
   - Recordatorio de cita (Docflow)
   - Bienvenida a nuevo cliente
3. Esperar aprobacion de Meta (24-48h)

### 5.4 Monitoreo

- Uptime Kuma: agregar check para `https://api.tudominio.com/whatsapp/webhook`
- Logs: `docker logs qyne-agno` para errores de webhook
- Meta Dashboard: revisar quality rating del numero

---

## Orden recomendado de ejecucion

```
Semana 1 (ahora, sin esperar WhatsApp)
├── 1.1 Crear colecciones en Directus
├── 1.2 Configurar dominio + SSL en Traefik
└── Mergear PR #63 (limpieza de Whabi)

Semana 1-2 (cuando tengas el numero de Twilio)
├── 2.1-2.5 Registro completo en Meta
├── 3.1-3.3 Conectar a QYNE
└── 3.4 Agregar testers

Semana 2 (testing)
├── 4.1-4.4 Tests completos
└── Corregir cualquier issue

Semana 3+ (produccion)
├── 5.1 Publicar app (verificacion del negocio)
├── 5.2 Display name
├── 5.3 Message templates
└── 5.4 Monitoreo
```

---

## Variables de entorno finales

```bash
# .env (produccion)
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx    # System User token
WHATSAPP_PHONE_NUMBER_ID=123456789012345    # De Meta API Setup
WHATSAPP_VERIFY_TOKEN=qyne-verify-2026      # Tu lo inventas
WHATSAPP_APP_SECRET=abcdef1234567890        # De Meta App Settings > Basic
```

---

## Notas importantes

- **Costo de Meta**: mensajes de servicio (respuestas dentro de 24h) son gratis.
  Marketing y utility se cobran por mensaje segun pais.
- **Rate limits**: numero nuevo empieza en Tier 1 (1,000 msgs/dia).
  Sube automaticamente con buen quality rating.
- **El numero de Twilio**: solo sirve para recibir el OTP de verificacion.
  Despues de registrado en Meta, Twilio no interviene. No te cobra por
  mensajes de WhatsApp.
- **Coexistence**: no disponible via Self Sign-Up. Si necesitas usar el
  mismo numero en la app y la API, necesitas un BSP con Embedded Signup.
