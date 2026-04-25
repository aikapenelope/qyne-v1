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
| Tools de negocio | LISTO | confirm_payment, log_support_ticket, save_contact, etc. |
| Colecciones en Directus | LISTO | contacts (8), companies, tickets, payments, conversations, tasks, events (15) |
| Traefik webhook route | LISTO | `Path(/whatsapp/webhook)` -> agno:8000 |
| Variables de entorno | LISTO (template) | En .env.example y docker-compose.yml |
| Agno AgentOS corriendo | LISTO | 11 contenedores healthy, 3+ semanas uptime |

### Lo que FALTA (solo 5 cosas)

| # | Componente | Tipo | Depende de |
|---|------------|------|------------|
| 1 | Dominio + HTTPS | Infra | Nada (hacer ya) |
| 2 | Numero registrado en Meta | Meta | Numero de Twilio |
| 3 | Token permanente + App Secret | Meta | Meta App creada |
| 4 | Variables en .env del servidor | Config | #2 y #3 |
| 5 | Webhook registrado en Meta | Meta | #1 y #4 |

> La plataforma esta lista a nivel de codigo. Solo falta la conexion
> con Meta y HTTPS para el webhook.

---

## Sprint 1: HTTPS + Meta App (yo hago la infra, tu haces Meta)

**Objetivo:** Tener HTTPS funcionando y la Meta App creada.

### 1A. Dominio + SSL en Traefik (lo hago yo)

Necesito que me confirmes:
- Que dominio usar (ej: `api.tudominio.com`)
- Acceso a Cloudflare para crear el registro DNS
- O si prefieres que use Tailscale Funnel como alternativa temporal

Lo que voy a hacer:
1. Agregar cert resolver (Let's Encrypt) a `traefik.yml`
2. Actualizar labels del router de WhatsApp con Host + TLS
3. Crear PR con los cambios
4. Tu aplicas el DNS en Cloudflare
5. Reiniciamos Traefik y verificamos HTTPS

### 1B. Crear Meta App y registrar numero (tu lo haces)

1. Ir a [developers.facebook.com/apps](https://developers.facebook.com/apps)
2. Create App > nombre: "QYNE Support"
3. Use case: "Connect with customers through WhatsApp"
4. Vincular Business Portfolio
5. En WhatsApp > API Setup > Add phone number
6. Ingresar el numero de Twilio
7. Recibir OTP en Twilio Console > Messaging Logs
8. Verificar el numero
9. Anotar: **Phone Number ID**

### Entregable Sprint 1
- HTTPS respondiendo en `https://tudominio.com/whatsapp/webhook`
- Meta App creada con numero verificado
- Phone Number ID anotado

---

## Sprint 2: Conectar Meta a QYNE + primer test

**Objetivo:** Primer mensaje de WhatsApp respondido por Agno.

### 2A. Token permanente (tu lo haces)

1. [business.facebook.com/latest/settings](https://business.facebook.com/latest/settings) > System Users > Add
2. Nombre: "QYNE Bot", rol: Admin
3. Asignar assets:
   - Meta App > Manage app (full control)
   - WhatsApp Business Account > Manage (full control)
4. Generate Token:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
5. Copiar token (no expira)
6. Meta App > Settings > Basic > copiar **App Secret**

### 2B. Configurar servidor (lo hago yo o tu via SSH)

Editar `/opt/qyne-v1/.env`:
```bash
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_VERIFY_TOKEN=qyne-verify-2026
WHATSAPP_APP_SECRET=abcdef1234567890
```

Reiniciar Agno:
```bash
cd /opt/qyne-v1 && docker compose up -d agno
```

### 2C. Registrar webhook en Meta (tu lo haces)

1. Meta App > WhatsApp > Configuration
2. Webhook > Edit:
   - Callback URL: `https://tudominio.com/whatsapp/webhook`
   - Verify token: `qyne-verify-2026`
3. "Verify and Save" (Agno responde automaticamente)
4. Suscribir campo: `messages`

### 2D. Agregar testers

1. Meta App > App Roles > Roles
2. Agregar tu numero personal como Tester
3. Esto permite probar sin publicar la app

### 2E. Primer test

1. Desde tu WhatsApp, envia "Hola" al numero registrado
2. Verificar respuesta del agente
3. Verificar logs: `docker logs qyne-agno --tail 20`

### Entregable Sprint 2
- Mensaje enviado por WhatsApp y respondido por Agno
- Webhook verificado y recibiendo eventos

---

## Sprint 3: Testing completo

**Objetivo:** Validar routing, tools, y sesiones.

### 3A. Test de routing

| Mensaje de prueba | Agente esperado |
|-------------------|----------------|
| "Necesito ayuda con mi historia clinica" | Docflow Support |
| "La app de voz no funciona" | Aurora Support |
| "Cuanto cuesta el plan Pro?" | General Support |
| "Quiero pagar mi suscripcion de Docflow" | Docflow Support |

### 3B. Test de tools (verificar en Directus)

| Accion del cliente | Tool que se activa | Verificar en |
|--------------------|--------------------|-------------|
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

- Enviar imagen: el agente debe recibirla
- Enviar audio: el agente debe recibirlo
- Enviar mensaje muy largo (>1000 chars)
- No responder por 24h y verificar que el agente no puede enviar
  mensajes fuera de la ventana (solo templates)

### Entregable Sprint 3
- Todos los tests pasando
- Lista de bugs encontrados (si hay)

---

## Sprint 4: Produccion

**Objetivo:** App publicada, templates creados, monitoreo activo.

### 4A. Verificacion del negocio en Meta

1. Meta Business Suite > Settings > Business Verification
2. Subir documentos del negocio (nombre legal, direccion, ID)
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

Crear templates para mensajes fuera de la ventana de 24h:

| Template | Categoria | Uso |
|----------|-----------|-----|
| `payment_confirmation` | utility | "Hola {{1}}, tu pago de {{2}} fue recibido." |
| `appointment_reminder` | utility | "Recordatorio: tu cita es manana {{1}} a las {{2}}." |
| `welcome_new_client` | marketing | "Bienvenido a {{1}}! Soy tu asistente virtual." |

### 4E. Monitoreo

- Uptime Kuma: agregar check para el webhook URL
- Revisar quality rating en Meta Dashboard semanalmente
- Configurar alerta en n8n si el webhook deja de responder

### Entregable Sprint 4
- App publicada y recibiendo mensajes de cualquier usuario
- Templates aprobados
- Monitoreo activo

---

## Timeline estimado

```
Sprint 1 (1-2 dias)     HTTPS + Meta App
Sprint 2 (1 dia)        Conectar + primer test
Sprint 3 (1-2 dias)     Testing completo
Sprint 4 (5-7 dias)     Produccion (la espera es por Meta)
```

Total: ~2 semanas, de las cuales ~1 semana es espera de Meta.

---

## Variables de entorno finales

```bash
# /opt/qyne-v1/.env
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx    # System User token permanente
WHATSAPP_PHONE_NUMBER_ID=123456789012345    # De Meta API Setup
WHATSAPP_VERIFY_TOKEN=qyne-verify-2026      # String que tu inventas
WHATSAPP_APP_SECRET=abcdef1234567890        # De Meta App > Settings > Basic
```

---

## Notas importantes

- **Directus CRM**: verificado via SSH. Las 7 colecciones existen y
  funcionan (contacts, companies, tickets, payments, conversations,
  tasks, events). Ya hay 8 contactos y 15 eventos registrados.
- **Costo de Meta**: mensajes de servicio (respuestas dentro de 24h)
  son gratis. Marketing y utility se cobran por mensaje segun pais.
  Colombia: ~$0.0436/msg marketing, ~$0.008/msg utility.
- **Rate limits**: numero nuevo empieza en Tier 1 (1,000 msgs/dia).
  Sube automaticamente con buen quality rating.
- **El numero de Twilio**: solo sirve para recibir el OTP de
  verificacion. Despues de registrado en Meta, Twilio no interviene.
- **Coexistence**: no disponible via Self Sign-Up. Si necesitas usar
  el mismo numero en la app y la API, necesitas un BSP.
