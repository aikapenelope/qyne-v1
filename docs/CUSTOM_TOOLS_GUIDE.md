# QYNE v1 — Custom Tools Guide: How to Build Tools for Agno

## How Agno Tools Work

A tool is a Python function that an agent can call. The LLM sees the
function name, docstring, and parameter types. It decides when to call
the tool based on the conversation.

```
User: "Guarda este contacto: Juan Perez, juan@example.com"
    │
    ▼
LLM reads tool list → finds save_contact(first_name, last_name, email, ...)
    │
    ▼
LLM generates: save_contact(first_name="Juan", last_name="Perez", email="juan@example.com")
    │
    ▼
Agno executes the function → returns result string
    │
    ▼
LLM reads result → responds to user: "Contacto guardado: Juan Perez"
```

The LLM ONLY sees: function name, docstring, parameter names + types.
It does NOT see the function body. The docstring is critical.

## Method 1: @tool Decorator (Simple Functions)

For standalone tools that don't share state.

```python
from agno.tools.decorator import tool

@tool()
def my_tool(param1: str, param2: int = 10) -> str:
    """One-line description of what this tool does.

    Detailed explanation of when the agent should use this tool.
    Include examples of user requests that should trigger this tool.

    Args:
        param1: Description of param1 (the LLM reads this)
        param2: Description of param2 with default value
    """
    # Your logic here
    return "Result string that the LLM will read"
```

### @tool Decorator Options

| Option | Type | Default | Purpose |
|--------|------|---------|---------|
| `name` | str | function name | Custom tool name for the LLM |
| `description` | str | docstring | Override the description |
| `requires_confirmation` | bool | False | User must approve before execution |
| `show_result` | bool | False | Show tool output directly in response |
| `stop_after_tool_call` | bool | False | Stop agent after this tool runs |
| `cache_results` | bool | False | Cache identical calls |
| `cache_ttl` | int | None | Cache duration in seconds |
| `cache_dir` | str | None | Cache storage directory |
| `tool_hooks` | list | None | Pre/post execution hooks |

### When to Use Each Option

```python
# Payment confirmation: requires human approval
@tool(requires_confirmation=True)
def confirm_payment(amount: str, method: str) -> str:
    """Confirm a payment. Requires human approval."""

# Show raw data to user (not processed by LLM)
@tool(show_result=True)
def get_raw_data(query: str) -> str:
    """Get raw data and show it directly."""

# Cache expensive API calls
@tool(cache_results=True, cache_ttl=3600)
def fetch_exchange_rate(currency: str) -> str:
    """Get exchange rate (cached for 1 hour)."""

# Stop after saving (don't continue reasoning)
@tool(stop_after_tool_call=True)
def emergency_shutdown(reason: str) -> str:
    """Emergency shutdown. Stops all processing."""
```

## Method 2: Toolkit Class (Related Tools with Shared State)

For tools that share configuration, connections, or state.

```python
from agno.tools import Toolkit

class DirectusTools(Toolkit):
    def __init__(self, base_url: str, token: str, **kwargs):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Register tools
        tools = [self.read_items, self.create_item]
        super().__init__(name="directus_tools", tools=tools, **kwargs)

    def read_items(self, collection: str, limit: int = 10) -> str:
        """Read items from a Directus collection."""
        resp = httpx.get(
            f"{self.base_url}/items/{collection}?limit={limit}",
            headers=self.headers,
        )
        return resp.text

    def create_item(self, collection: str, data: str) -> str:
        """Create an item in a Directus collection."""
        resp = httpx.post(
            f"{self.base_url}/items/{collection}",
            json=json.loads(data),
            headers=self.headers,
        )
        return resp.text

# Usage
agent = Agent(tools=[DirectusTools(base_url="http://directus:8055", token="...")])
```

### When to Use Toolkit vs @tool

| Scenario | Use |
|----------|-----|
| Single function, no shared state | `@tool` decorator |
| Multiple related functions sharing config | `Toolkit` class |
| Functions that need a connection/client | `Toolkit` class |
| Quick one-off tool | `@tool` decorator |
| Reusable across multiple agents | `Toolkit` class |

## Tool Hooks (Pre/Post Execution)

Run code before or after a tool executes:

```python
def log_tool_call(function_name: str, function_call, arguments: dict):
    """Log every tool call to Directus events."""
    print(f"Tool called: {function_name} with {arguments}")
    result = function_call(**arguments)
    print(f"Tool result: {result[:100]}")
    return result

@tool(tool_hooks=[log_tool_call])
def my_tool(query: str) -> str:
    """My tool with logging."""
    return "result"
```

## Injected Parameters (Free Context)

Agno auto-injects these parameters if your function signature includes them.
They don't cost tokens — the LLM doesn't see them.

```python
from agno.agent import Agent
from agno.run import RunContext

@tool()
def context_aware_tool(query: str, agent: Agent) -> str:
    """Tool that knows which agent is calling it."""
    return f"Called by {agent.name} for query: {query}"

@tool()
def session_aware_tool(query: str, run_context: RunContext) -> str:
    """Tool that knows the current session."""
    return f"Session: {run_context.session_id}, User: {run_context.user_id}"
```

## Approval Workflow (@approval)

For sensitive operations that need human confirmation:

```python
from agno.approval.decorator import approval
from agno.tools.decorator import tool

@approval  # Pauses execution until human approves
@tool(requires_confirmation=True)
def delete_data(collection: str, item_id: int) -> str:
    """Delete an item. Requires human approval."""
    # Only runs after approval
    return f"Deleted {collection}/{item_id}"
```

## Best Practices for QYNE Tools

### 1. Docstrings Are Everything

The LLM decides when to call a tool based on the docstring.
Bad docstring = tool never gets called or gets called wrong.

```python
# BAD: vague, LLM won't know when to use it
@tool()
def process(data: str) -> str:
    """Process data."""

# GOOD: specific, LLM knows exactly when to use it
@tool()
def save_contact(first_name: str, last_name: str, email: str) -> str:
    """Save a contact to the CRM database.

    ALWAYS call this when you learn a client's name, email, or phone.
    Call at the START of a conversation if the client identifies themselves.
    """
```

### 2. Return Strings, Not Objects

The LLM reads the return value. Return human-readable strings.

```python
# BAD: LLM can't read this
@tool()
def get_data() -> dict:
    return {"id": 1, "name": "test"}

# GOOD: LLM reads this naturally
@tool()
def get_data() -> str:
    return "Contact saved: Juan Perez (juan@example.com) ID=42"
```

### 3. Handle Errors Gracefully

Never let a tool crash. Return error strings.

```python
@tool()
def api_call(url: str) -> str:
    """Call an external API."""
    try:
        resp = httpx.get(url, timeout=10)
        if resp.is_success:
            return f"Success: {resp.text[:500]}"
        return f"Error: HTTP {resp.status_code}"
    except Exception as e:
        return f"Error: {e}"
```

### 4. Keep Parameters Simple

The LLM generates parameter values. Complex types confuse it.

```python
# BAD: LLM struggles with nested objects
@tool()
def create(data: dict[str, list[dict[str, str]]]) -> str: ...

# GOOD: flat, simple types
@tool()
def create(name: str, email: str, phone: str = "") -> str: ...

# OK: JSON string for complex data (LLM can generate JSON)
@tool()
def create(json_data: str) -> str:
    """Create item. json_data should be a JSON string like '{"name": "..."}'"""
```

### 5. Use Default Values

Reduce the number of required parameters.

```python
@tool()
def search(
    query: str,                    # Required
    collection: str = "contacts",  # Optional with default
    limit: int = 10,               # Optional with default
) -> str: ...
```

## QYNE Custom Tools Inventory

| Tool File | Tools | Used By |
|-----------|-------|---------|
| `directus_business.py` | save_contact, save_company, log_conversation, log_support_ticket, confirm_payment, escalate_to_human | Support, Automation, WhatsApp agents |
| `prefect_api.py` | list_prefect_deployments, trigger_prefect_flow, check_prefect_flow_status, list_recent_flow_runs | Automation Agent |
| `chat_export.py` | save_chat_to_directus, save_chat_to_knowledge | Web chat agents (not WhatsApp) |
| `sandbox.py` | Docker sandbox (inactive) | None (Docker socket removed) |

## How to Add a New Tool

1. Create a file in `services/agno/tools/your_tool.py`
2. Use `@tool()` decorator with descriptive docstring
3. Return `str` with clear result message
4. Handle errors with try/except
5. Import and add to the agent's `tools=[]` list
6. Test: ask the agent something that should trigger the tool
7. Check traces to verify the tool was called correctly
