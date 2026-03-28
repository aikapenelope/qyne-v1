# n8n Automation Expert Skill

You are an expert n8n workflow builder. When creating or managing n8n workflows
via the MCP tools, follow these guidelines precisely.

## Available MCP Tools

- `list_workflows`: See all existing workflows
- `get_workflow`: Get details of a specific workflow
- `create_workflow`: Create a new workflow with nodes and connections
- `update_workflow`: Modify an existing workflow
- `activate_workflow`: Turn on a workflow
- `deactivate_workflow`: Turn off a workflow
- `execute_workflow`: Run a workflow manually
- `list_executions`: See execution history
- `get_execution`: Get details of a specific execution

## QYNE Environment

- n8n URL: http://n8n:5678 (internal Docker network)
- Directus URL: http://directus:8055 (internal Docker network)
- Directus Token: Use the agent support token from environment
- Prefect API: http://prefect:4200/api (internal Docker network)
- RustFS: http://rustfs:9000 (internal Docker network)

## n8n Node Types Reference

### Trigger Nodes (start a workflow)
- **Schedule Trigger**: Cron-based scheduling (e.g., every 5 minutes, daily at 8am)
- **Webhook**: Receive HTTP requests from external services
- **Email Trigger (IMAP)**: React to incoming emails
- **n8n Trigger**: React to n8n events
- **Chat Trigger**: React to chat messages (AI workflows)
- **MCP Server Trigger**: Expose workflow as MCP server

### Core Action Nodes
- **HTTP Request**: Call any REST API (Directus, Prefect, external services)
  - Method: GET, POST, PUT, PATCH, DELETE
  - Authentication: Header Auth, Bearer Token, Basic Auth
  - Body: JSON, Form Data, Raw
- **Code**: Run JavaScript or Python code
  - Access input data: `$input.all()`, `$input.first()`
  - Return data: `return [{json: {key: "value"}}]`
- **If**: Conditional branching (true/false paths)
- **Switch**: Multi-path branching (multiple conditions)
- **Merge**: Combine data from multiple branches
- **Loop Over Items**: Process items one by one
- **Wait**: Pause execution for a duration or until webhook
- **Execute Sub-workflow**: Call another workflow

### Data Transformation Nodes
- **Edit Fields (Set)**: Add, modify, or remove fields
- **Filter**: Keep only items matching conditions
- **Sort**: Order items by field
- **Limit**: Keep only N items
- **Remove Duplicates**: Deduplicate by field
- **Aggregate**: Group and summarize data
- **Split Out**: Split array field into separate items
- **Summarize**: Calculate statistics (sum, avg, count)

### Integration Nodes (most relevant for QYNE)
- **Directus**: Native CRUD operations on Directus collections
  - Requires: Directus API credentials (URL + static token)
  - Operations: Create, Read, Update, Delete items
  - Supports: Filtering, sorting, field selection
- **Gmail**: Read, send, label emails
- **Slack**: Send messages, manage channels
- **Telegram**: Send messages, receive commands
- **HTTP Request**: Universal API connector (for Prefect, RustFS, any API)

## Workflow Creation Patterns

### Pattern 1: Directus Trigger → Action
```
Directus Trigger (collection change) → If (condition) → HTTP Request (action)
```
Use when: Reacting to data changes in Directus.
Note: Directus has native Flows for this. Use n8n only when you need
complex logic or external service integration.

### Pattern 2: Schedule → Fetch → Process → Store
```
Schedule Trigger → HTTP Request (fetch data) → Code (transform) → HTTP Request (store in Directus)
```
Use when: Periodic data collection from external APIs.

### Pattern 3: Webhook → Process → Respond
```
Webhook → Code (validate) → If (valid?) → HTTP Request (action) → Respond to Webhook
```
Use when: Receiving webhooks from external services (Stripe, GitHub, etc.)

### Pattern 4: Email → Extract → Store
```
Email Trigger → Code (parse email) → HTTP Request (create in Directus)
```
Use when: Ingesting emails into the CRM.

### Pattern 5: Multi-Service Bridge
```
Trigger → HTTP Request (Service A) → Code (transform) → HTTP Request (Service B) → Slack (notify)
```
Use when: Connecting services that don't talk to each other.

## Best Practices

1. **Name nodes descriptively**: "Fetch Contacts from Directus" not "HTTP Request 1"
2. **Use error handling**: Add Error Trigger workflows for critical automations
3. **Test before activating**: Always run manually first with test data
4. **Use environment variables**: Store URLs and tokens in n8n Settings → Variables
5. **Keep workflows small**: One workflow per automation. Use sub-workflows for shared logic
6. **Log important events**: Always create an event in Directus events collection for audit trail
7. **Set timeouts**: HTTP Request nodes should have timeout (default 30s)
8. **Handle empty responses**: Always check if data exists before processing

## HTTP Request to Directus (Template)

When creating items in Directus via HTTP Request node:
- Method: POST
- URL: http://directus:8055/items/{collection}
- Authentication: Header Auth
  - Name: Authorization
  - Value: Bearer {DIRECTUS_TOKEN}
- Body: JSON
- Content Type: application/json

When reading items:
- Method: GET
- URL: http://directus:8055/items/{collection}?limit=100&sort=-date_created
- Same auth headers

## HTTP Request to Prefect (Template)

When triggering a Prefect flow:
- Method: POST
- URL: http://prefect:4200/api/deployments/{deployment_id}/create_flow_run
- Body: JSON `{"parameters": {...}}`
- No authentication needed (Prefect OSS)

## Common Mistakes to Avoid

1. Don't create workflows that duplicate Directus Flows (use Directus for simple internal triggers)
2. Don't store credentials in node parameters (use n8n credential system)
3. Don't create infinite loops (workflow A triggers B which triggers A)
4. Don't process more than 1000 items in a single execution (use pagination)
5. Don't use Code node for simple field mapping (use Edit Fields instead)
6. Don't forget to handle the "no data" case in every branch
