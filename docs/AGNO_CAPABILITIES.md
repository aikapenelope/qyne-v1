# QYNE v1 — Agno Capabilities: Everything Available vs What We Use

Source: Agno repo (github.com/agno-agi/agno), docs (docs.agno.com), cookbook (1773 examples)

## Tools (124 available, 35 imported in nexus_legacy.py, 2 active in QYNE)

### Legend
- **ACTIVE** = Running in QYNE right now
- **IN NEXUS** = Imported in nexus_legacy.py, not yet ported
- **AVAILABLE** = Exists in Agno, not used yet

### Web Search & Scraping

| Tool | Class | Status | Description |
|------|-------|--------|-------------|
| duckduckgo | DuckDuckGoTools | IN NEXUS | Free web search, no API key needed |
| exa | ExaTools | IN NEXUS | Premium web search API (semantic) |
| tavily | TavilyTools | IN NEXUS | AI-optimized web search + extract |
| websearch | WebSearchTools | IN NEXUS | Meta-search using DDGS backend |
| spider | SpiderTools | IN NEXUS | Web crawling and scraping |
| firecrawl | FirecrawlTools | IN NEXUS | LLM-ready markdown from any URL |
| crawl4ai | Crawl4aiTools | AVAILABLE | OSS web crawler (we use via Prefect, not as Agno tool) |
| browserbase | BrowserbaseTools | IN NEXUS | Cloud browser automation |
| newspaper4k | Newspaper4kTools | IN NEXUS | Article text extraction from URLs |
| webbrowser | WebBrowserTools | IN NEXUS | Open pages in web browser |
| website | WebsiteTools | IN NEXUS | Add website content to knowledge |
| trafilatura | TrafilaturaTools | AVAILABLE | Web scraping and text extraction |
| agentql | AgentQLTools | AVAILABLE | Scrape with natural language queries |
| brightdata | BrightDataTools | AVAILABLE | Proxy-powered scraping |
| oxylabs | OxylabsTools | AVAILABLE | Proxy-powered scraping |
| scrapegraph | ScrapeGraphTools | AVAILABLE | LLM-based structured extraction |
| jina | JinaReaderToolsConfig | AVAILABLE | URL to markdown via Jina Reader API |
| linkup | LinkupTools | AVAILABLE | Web search API |
| serpapi | SerpApiTools | AVAILABLE | Google search via SerpApi |
| serper | SerperTools | AVAILABLE | Google search via Serper |
| bravesearch | BraveSearchTools | AVAILABLE | Brave search engine |
| baidusearch | BaiduSearchTools | AVAILABLE | Baidu search (Chinese) |
| searxng | SearxngTools | AVAILABLE | Self-hosted meta-search |
| perplexity | PerplexityTools | AVAILABLE | Perplexity AI search |
| valyu | ValyuTools | AVAILABLE | Academic and web search |
| seltz | SeltzTools | AVAILABLE | AI-powered search API |

### Code Execution & Development

| Tool | Class | Status | Description |
|------|-------|--------|-------------|
| python | PythonTools | IN NEXUS | Save and run Python scripts |
| coding | CodingTools | IN NEXUS | Minimal toolkit for coding agents |
| shell | ShellTools | AVAILABLE | Run shell commands |
| docker | DockerTools | AVAILABLE | Docker container management |
| daytona | DaytonaTools | AVAILABLE | Isolated code sandboxes (recommended over Docker) |
| e2b | E2BTools | AVAILABLE | Cloud code sandbox |
| github | GithubTools | IN NEXUS | GitHub API (repos, PRs, issues) |
| gitlab | GitlabTools | AVAILABLE | GitLab API |
| bitbucket | BitbucketTools | AVAILABLE | Bitbucket API |

### Communication & Messaging

| Tool | Class | Status | Description |
|------|-------|--------|-------------|
| email | EmailTools | IN NEXUS | Send emails via SMTP |
| slack | SlackTools | IN NEXUS | Slack messages and channels |
| whatsapp | WhatsAppTools | IN NEXUS | WhatsApp Business API |
| telegram | TelegramTools | AVAILABLE | Telegram Bot API |
| discord | DiscordTools | AVAILABLE | Discord channels and servers |
| twilio | TwilioTools | AVAILABLE | SMS and voice via Twilio |
| webex | WebexTools | AVAILABLE | Cisco Webex messaging |
| resend | ResendTools | AVAILABLE | Email via Resend API |
| gmail | GmailTools | AVAILABLE | Gmail API (read, send, labels) |
| aws_ses | AWSSESTool | AVAILABLE | Email via AWS SES |

### Data & Analytics

| Tool | Class | Status | Description |
|------|-------|--------|-------------|
| sql | SQLTools | IN NEXUS | Query SQL databases |
| csv_toolkit | CsvTools | IN NEXUS | Read and analyze CSV files |
| yfinance | YFinanceTools | IN NEXUS | Yahoo Finance stock data |
| duckdb | DuckDbTools | AVAILABLE | In-process SQL analytics |
| pandas | PandasTools | AVAILABLE | DataFrame operations |
| postgres | PostgresTools | AVAILABLE | PostgreSQL queries |
| redshift | RedshiftTools | AVAILABLE | Amazon Redshift queries |
| google_bigquery | BigQueryTools | AVAILABLE | Google BigQuery |
| openbb | OpenBBTools | AVAILABLE | Financial data platform |
| financial_datasets | FinancialDatasetsTools | AVAILABLE | Financial datasets API |

### AI & Media Generation

| Tool | Class | Status | Description |
|------|-------|--------|-------------|
| nano_banana | NanoBananaTools | IN NEXUS | Image generation from text |
| lumalab | LumaLabTools | IN NEXUS | Video generation from images |
| dalle | DalleTools | AVAILABLE | DALL-E image generation |
| replicate | ReplicateTools | AVAILABLE | Run ML models (image, video, audio) |
| fal | FalTools | AVAILABLE | Fast ML inference (images, video) |
| models_labs | ModelsLabTools | AVAILABLE | AI model marketplace |
| eleven_labs | ElevenLabsTools | AVAILABLE | Text-to-speech |
| cartesia | CartesiaTools | AVAILABLE | Voice synthesis |
| desi_vocal | DesiVocalTools | AVAILABLE | Voice generation |
| moviepy_video | MoviePyVideoTools | AVAILABLE | Video processing and editing |
| opencv | OpenCVTools | AVAILABLE | Computer vision (webcam, images) |
| mlx_transcribe | MLXTranscribeTools | AVAILABLE | Audio transcription (Apple MLX) |
| giphy | GiphyTools | AVAILABLE | GIF search |
| unsplash | UnsplashTools | AVAILABLE | Stock photo search |
| visualization | VisualizationTools | AVAILABLE | Chart and graph generation |

### Project Management & Productivity

| Tool | Class | Status | Description |
|------|-------|--------|-------------|
| todoist | TodoistTools | IN NEXUS | Task management |
| jira | JiraTools | AVAILABLE | Jira issue tracking |
| linear | LinearTools | AVAILABLE | Linear project management |
| clickup | ClickUpTools | AVAILABLE | ClickUp tasks and projects |
| trello | TrelloTools | AVAILABLE | Trello boards and cards |
| notion | NotionTools | AVAILABLE | Notion pages and databases |
| confluence | ConfluenceTools | AVAILABLE | Confluence wiki |
| calcom | CalComTools | AVAILABLE | Calendar scheduling |
| googlecalendar | GoogleCalendarTools | AVAILABLE | Google Calendar |
| googlesheets | GoogleSheetsTools | AVAILABLE | Google Sheets |
| google_drive | GoogleDriveTools | AVAILABLE | Google Drive files |
| shopify | ShopifyTools | AVAILABLE | Shopify e-commerce |
| zendesk | ZendeskTools | AVAILABLE | Zendesk support tickets |
| spotify | SpotifyTools | AVAILABLE | Spotify API |
| zoom | ZoomTools | AVAILABLE | Zoom meetings |

### Knowledge & Research

| Tool | Class | Status | Description |
|------|-------|--------|-------------|
| arxiv | ArxivTools | IN NEXUS | Academic paper search |
| hackernews | HackerNewsTools | IN NEXUS | Hacker News stories |
| reddit | RedditTools | IN NEXUS | Reddit posts and comments |
| wikipedia | WikipediaTools | IN NEXUS | Wikipedia articles |
| youtube | YouTubeTools | IN NEXUS | YouTube video data |
| x | XTools | IN NEXUS | Twitter/X posts |
| knowledge | KnowledgeTools | IN NEXUS | Knowledge base search |
| pubmed | PubmedTools | AVAILABLE | Medical research papers |
| newspaper | NewspaperTools | AVAILABLE | News article extraction |

### Agent Infrastructure

| Tool | Class | Status | Description |
|------|-------|--------|-------------|
| mcp | MCPTools | ACTIVE (Directus) | Model Context Protocol servers |
| calculator | CalculatorTools | IN NEXUS | Math operations |
| file | FileTools | IN NEXUS | File read/write operations |
| reasoning | ReasoningTools | IN NEXUS | Step-by-step reasoning (Think, Analyze) |
| workflow | WorkflowTools | IN NEXUS | Workflow execution tools |
| user_control_flow | UserControlFlowTools | IN NEXUS | Interrupt agent for user input |
| decorator | decorator | IN NEXUS | Custom function tools (@tool) |
| memory | MemoryTools | AVAILABLE | Memory management tools |
| sleep | SleepTools | AVAILABLE | Pause execution |
| parallel | ParallelTools | AVAILABLE | Run tools in parallel |
| local_file_system | LocalFileSystemTools | AVAILABLE | Local file operations |
| file_generation | FileGenerationTools | AVAILABLE | Generate and save files |
| user_feedback | UserFeedbackTools | AVAILABLE | Collect user feedback |
| api | CustomApiTools | AVAILABLE | Custom REST API calls |

### Blockchain & Specialized

| Tool | Class | Status | Description |
|------|-------|--------|-------------|
| evm | EvmTools | AVAILABLE | Ethereum/EVM blockchain |
| neo4j | Neo4jTools | AVAILABLE | Graph database |
| mem0 | Mem0Tools | AVAILABLE | External memory service |
| zep | ZepTools | AVAILABLE | Long-term memory service |
| airflow | AirflowTools | AVAILABLE | Apache Airflow DAGs |
| aws_lambda | AWSLambdaTools | AVAILABLE | AWS Lambda functions |
| brandfetch | BrandfetchTools | AVAILABLE | Brand data API |
| docling | DoclingTools | AVAILABLE | Document conversion |
| openweather | OpenWeatherTools | AVAILABLE | Weather data |
| openai | OpenAITools | AVAILABLE | OpenAI API (assistants, files) |

### Custom Tools (QYNE-specific)

| Tool | File | Status | Description |
|------|------|--------|-------------|
| save_contact | directus_business.py | ACTIVE | POST /items/contacts |
| save_company | directus_business.py | ACTIVE | POST /items/companies |
| log_support_ticket | directus_business.py | ACTIVE | POST /items/tickets |
| confirm_payment | directus_business.py | ACTIVE | POST /items/payments (with approval) |
| escalate_to_human | directus_business.py | ACTIVE | POST /items/tasks |
| sandbox | sandbox.py | INACTIVE | Docker micro-PC (socket removed) |

## Reference Agents (from Agno cookbook)

| Agent | Description | Relevance to QYNE |
|-------|-------------|-------------------|
| **Pal** | Personal agent that learns preferences | HIGH — maps to our `pal` agent |
| **Dash** | Self-learning data agent, 6 layers of context | HIGH — maps to our `dash` agent |
| **Scout** | Context agent for enterprise knowledge | MEDIUM — similar to knowledge_agent |
| **Gcode** | Post-IDE coding agent | LOW — not in our roadmap |
| **Seek** | Search and discovery agent | MEDIUM — similar to research_agent |

## Interfaces (5 available, 2 active)

| Interface | Status | Description |
|-----------|--------|-------------|
| AG-UI (CopilotKit) | ACTIVE | Web chat via frontend |
| WhatsApp | CONFIG ONLY | WhatsApp Business (needs HTTPS) |
| Slack | AVAILABLE | Slack bot integration |
| Telegram | AVAILABLE | Telegram bot |
| A2A Protocol | AVAILABLE | Agent-to-agent communication |

## Team Modes (from cookbook)

| Mode | Description | Used in nexus_legacy.py |
|------|-------------|------------------------|
| route | Router selects best agent for task | Yes (cerebro, nexus_master, whatsapp_support) |
| coordinate | Agents collaborate on shared task | Yes (content_team, product_dev, creative_studio) |
| collaborate | Agents discuss and reach consensus | No |

## Memory Types (all available, most active)

| Type | Status | Description |
|------|--------|-------------|
| User Memory (automatic) | ACTIVE | Auto-captures user facts |
| User Memory (agentic) | ACTIVE | Agent decides what to remember |
| Entity Memory | ACTIVE | Facts about companies, people, projects |
| Session Context | ACTIVE | Per-session state |
| User Profile | ACTIVE | Structured user data (name, role) |
| Learned Knowledge | ACTIVE | Reusable task insights |
| Decision Log | ACTIVE | Record significant decisions |
| Memory Sharing | AVAILABLE | Share memory between agents |
| Custom Memory Manager | AVAILABLE | Override memory behavior |

## Knowledge Readers (30+ available, 2 active)

| Reader | Status | Description |
|--------|--------|-------------|
| Markdown | ACTIVE | .md files from knowledge/ folder |
| LanceDB (vector store) | ACTIVE | Hybrid search with Voyage AI |
| DoclingReader | AVAILABLE | PDF, DOCX, PPTX parsing |
| CSV Reader | AVAILABLE | CSV file ingestion |
| JSON Reader | AVAILABLE | JSON file ingestion |
| Excel Reader | AVAILABLE | Excel spreadsheet ingestion |
| PDF Reader | AVAILABLE | PDF text extraction |
| DOCX Reader | AVAILABLE | Word document extraction |
| PPTX Reader | AVAILABLE | PowerPoint extraction |
| GitHub Reader | AVAILABLE | Ingest from GitHub repos |
| S3 Reader | AVAILABLE | Ingest from S3/RustFS |
| Website Reader | AVAILABLE | Ingest from URLs |
| YouTube Reader | AVAILABLE | Ingest from YouTube transcripts |
| Wikipedia Reader | AVAILABLE | Ingest from Wikipedia |
| ArXiv Reader | AVAILABLE | Ingest from academic papers |
| Firecrawl Reader | AVAILABLE | Ingest via Firecrawl |
| Tavily Reader | AVAILABLE | Ingest via Tavily |
| SharePoint Reader | AVAILABLE | Ingest from SharePoint |
| Azure Blob Reader | AVAILABLE | Ingest from Azure Blob |
| GCS Reader | AVAILABLE | Ingest from Google Cloud Storage |

## Embedders (20 available, 1 active)

| Embedder | Status | Description |
|----------|--------|-------------|
| Voyage AI | ACTIVE | voyage-3-lite, 512 dimensions |
| OpenAI | AVAILABLE | text-embedding-3-small/large |
| Cohere | AVAILABLE | embed-v4 |
| Google | AVAILABLE | text-embedding-005 |
| Jina | AVAILABLE | jina-embeddings-v3 |
| Mistral | AVAILABLE | mistral-embed |
| HuggingFace | AVAILABLE | Any HF model |
| Ollama | AVAILABLE | Local embeddings |
| AWS Bedrock | AVAILABLE | Titan embeddings |
| Azure OpenAI | AVAILABLE | Azure-hosted OpenAI |
| Sentence Transformer | AVAILABLE | Local sentence-transformers |
| FastEmbed | AVAILABLE | Fast local embeddings |
| Together | AVAILABLE | Together AI embeddings |
| Fireworks | AVAILABLE | Fireworks AI embeddings |
| vLLM | AVAILABLE | Self-hosted vLLM |
| Nebius | AVAILABLE | Nebius AI embeddings |
| LangDB | AVAILABLE | LangDB embeddings |

## Vector Stores (22 available, 1 active)

| Store | Status | Description |
|-------|--------|-------------|
| LanceDB | ACTIVE | Embedded, hybrid search |
| pgvector | AVAILABLE | PostgreSQL extension |
| Pinecone | AVAILABLE | Managed vector DB |
| Qdrant | AVAILABLE | Open-source vector DB |
| Chroma | AVAILABLE | Embedded vector DB |
| Milvus | AVAILABLE | Distributed vector DB |
| Weaviate | AVAILABLE | Vector search engine |
| Redis | AVAILABLE | Redis vector search |
| MongoDB | AVAILABLE | Atlas vector search |
| ClickHouse | AVAILABLE | Analytical DB with vectors |
| Cassandra | AVAILABLE | Distributed DB with vectors |
| Couchbase | AVAILABLE | Multi-model DB |
| SingleStore | AVAILABLE | Distributed SQL + vectors |
| SurrealDB | AVAILABLE | Multi-model DB |
| UpstashDB | AVAILABLE | Serverless vector DB |
| LlamaIndex | AVAILABLE | LlamaIndex integration |
| LangChain | AVAILABLE | LangChain integration |
| LightRAG | AVAILABLE | Lightweight RAG |

## Model Providers (40+ available, 3 active)

| Provider | Status | Models we use |
|----------|--------|---------------|
| Groq | ACTIVE | llama-3.1-8b-instant (FAST_MODEL) |
| OpenAI-compatible (MiniMax) | ACTIVE | MiniMax-M2.7 (TOOL_MODEL) |
| OpenRouter | ACTIVE | (REASONING_MODEL) |
| Anthropic | AVAILABLE | Claude Sonnet/Opus |
| Google | AVAILABLE | Gemini |
| DeepSeek | AVAILABLE | DeepSeek V3/R1 |
| Mistral | AVAILABLE | Mistral Large |
| Ollama | AVAILABLE | Local models |
| AWS Bedrock | AVAILABLE | Claude, Titan |
| Azure | AVAILABLE | Azure OpenAI |
| Cohere | AVAILABLE | Command R+ |
| Together | AVAILABLE | Open-source models |
| Fireworks | AVAILABLE | Fast inference |
| HuggingFace | AVAILABLE | Any HF model |
| Cerebras | AVAILABLE | Fast inference |
| Nvidia | AVAILABLE | NIM models |
| xAI | AVAILABLE | Grok |
| Perplexity | AVAILABLE | Sonar models |
| Meta | AVAILABLE | Llama direct |
| vLLM | AVAILABLE | Self-hosted |

## Guardrails (4 available, 2 active)

| Guardrail | Status | Description |
|-----------|--------|-------------|
| PII Detection | ACTIVE | Masks SSNs, cards, emails, phones |
| Prompt Injection | ACTIVE | Blocks jailbreak attempts |
| OpenAI Moderation | AVAILABLE | Content moderation via OpenAI |
| Custom Guardrails | AVAILABLE | Write your own validation logic |

## Database Backends (12 available, 1 active)

| Backend | Status | Description |
|---------|--------|-------------|
| SQLite | ACTIVE | Sessions, memory, traces |
| PostgreSQL | AVAILABLE | Production-grade (migrate when >20 users) |
| MongoDB | AVAILABLE | Document store |
| DynamoDB | AVAILABLE | AWS serverless |
| Redis | AVAILABLE | In-memory |
| MySQL | AVAILABLE | MySQL/MariaDB |
| Firestore | AVAILABLE | Google Cloud |
| SurrealDB | AVAILABLE | Multi-model |
| SingleStore | AVAILABLE | Distributed SQL |
| GCS JSON | AVAILABLE | Google Cloud Storage |
| In-Memory | AVAILABLE | Testing only |
| JSON File | AVAILABLE | File-based |

## Production Features

| Feature | Status | Description |
|---------|--------|-------------|
| Tracing | ACTIVE | All agent runs traced to SQLite |
| Scheduler | ACTIVE | Periodic agent tasks |
| Approvals (@approval) | ACTIVE | Human-in-the-loop for sensitive ops |
| Evals (accuracy) | AVAILABLE | Test agent response quality |
| Evals (reliability) | AVAILABLE | Test agent consistency |
| Evals (performance) | AVAILABLE | Test agent speed |
| Evals (agent-as-judge) | AVAILABLE | One agent evaluates another |
| Hooks (pre/post) | ACTIVE | Run code before/after agent runs |
| Context Compression | ACTIVE | Reduce context window usage |
| Run Cancellation | AVAILABLE | Cancel running agent tasks |
| Skills | ACTIVE | 24 domain skill directories |
| Dependency Injection | AVAILABLE | Inject services into agents |
| Background Tasks | AVAILABLE | Long-running async operations |
| Middleware | AVAILABLE | Request/response processing |
| MCP Server Mode | AVAILABLE | Expose agents as MCP servers |
