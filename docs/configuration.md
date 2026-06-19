# Configuration Guide

## Environment Variables

All configuration is done via environment variables. Copy `.env.example` to `.env` and customize for your deployment.

### Core Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_BASE_URL` | Yes* | `https://openrouter.ai/api/v1` | LLM provider endpoint URL |
| `OPENAI_API_KEY` | Yes* | - | API key for LLM provider |
| `MODEL` | No | `mistralai/mistral-large-2407` | Model name to use |

\* Required when using cloud LLM providers. Not required if running local Ollama without authentication.

### Agent Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MAX_TOKENS` | `4096` | Maximum tokens for LLM responses |
| `TEMPERATURE` | `0.7` | Creativity vs determinism (0.0-1.0) |

### Postiz Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `postiz` | Database username |
| `POSTGRES_PASSWORD` | `postiz_password` | Database password (CHANGE IN PRODUCTION!) |
| `POSTGRES_DB` | `postiz` | Database name |
| `JWT_SECRET` | - | JWT signing secret (generate strong random value) |

### Agent API Security

| Variable | Default | Description |
|----------|---------|-------------|
| `API_SECRET_KEY` | - | Secret key for agent API authentication |
| `POSTIZ_API_URL` | `http://postiz-backend:3000` | Internal Postiz backend URL |
| `POSTIZ_API_KEY` | - | API key for Postiz integration (if required) |

## LLM Provider Setup

### OpenRouter (Recommended)

OpenRouter provides access to multiple models with a single API key.

1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Create an API key
3. Configure:
   ```bash
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   OPENAI_API_KEY=sk-or-v1-your-key-here
   MODEL=mistralai/mistral-large-2407  # or any available model
   ```

### Ollama (Local)

Run LLMs locally for complete data privacy.

1. Install [Ollama](https://ollama.ai)
2. Pull a model: `ollama pull llama3.1`
3. Configure:
   ```bash
   OPENAI_BASE_URL=http://host.docker.internal:11434/v1
   MODEL=llama3.1
   # No API key needed for local Ollama
   ```

**Note**: For Docker Compose, use `host.docker.internal` to access host services on Linux. On macOS/Windows, this works automatically.

### Self-Hosted Inference Servers

#### vLLM
```bash
OPENAI_BASE_URL=http://your-vllm-server:8000/v1
OPENAI_API_KEY=optional-if-auth-enabled
MODEL=mistralai/Mixtral-8x7B-Instruct-v0.1
```

#### Text Generation Web UI
```bash
OPENAI_BASE_URL=http://your-textgen-server:5000/v1
MODEL=your-loaded-model
```

## Model Recommendations

### Content Creation (High Quality)
- `mistralai/mistral-large-2407` - Excellent for creative writing
- `anthropic/claude-3.5-sonnet` - Great for nuanced content
- `meta-llama/llama-3.1-70b-instruct` - Strong all-around

### Cost-Effective Options
- `mistralai/mistral-nemo` - Good quality, lower cost
- `google/gemma-2-27b-it` - Efficient and capable
- Local models via Ollama: `llama3.1:8b`, `mistral:nemo`

### Privacy-Focused (Local Only)
- `llama3.1:8b` - Good balance of size/capability
- `mistral:nemo` - 12B parameter, excellent quality
- `qwen2.5:7b` - Strong performance in smaller package

## Agent-Specific Configuration

### Content Creator Agent

The content creator uses the global LLM settings but can be tuned via:

| Parameter | Recommended Values | Effect |
|-----------|-------------------|--------|
| Temperature | 0.7-0.9 | Higher = more creative variations |
| Max Tokens | 512-1024 | More tokens = longer posts |

### Scheduling Optimizer Agent

This agent primarily uses historical data and platform patterns:

| Parameter | Recommended Values | Effect |
|-----------|-------------------|--------|
| Temperature | 0.3-0.5 | Lower = more deterministic recommendations |
| Historical Data Points | 50+ for reliable results | More data = better confidence |

### Engagement Manager Agent

For safe engagement management:

| Parameter | Recommended Values | Effect |
|-----------|-------------------|--------|
| Temperature | 0.5-0.7 | Balanced response generation |
| Max Tokens | 256-512 | Shorter, focused responses |

## Production Deployment Checklist

### Security
- [ ] Change all default passwords in `.env`
- [ ] Generate strong `JWT_SECRET` (use `openssl rand -hex 32`)
- [ ] Set `API_SECRET_KEY` for agent API protection
- [ ] Restrict CORS origins if exposing publicly
- [ ] Enable HTTPS/TLS termination at reverse proxy

### Performance
- [ ] Configure appropriate resource limits in docker-compose
- [ ] Set up database connection pooling
- [ ] Consider Redis clustering for high availability
- [ ] Implement rate limiting on agent API

### Monitoring
- [ ] Configure log aggregation (ELK, Loki, etc.)
- [ ] Set up health check monitoring
- [ ] Enable metrics collection (Prometheus)
- [ ] Configure alerting for critical failures

### Backup
- [ ] Schedule PostgreSQL backups
- [ ] Backup Redis data if using persistence
- [ ] Document restoration procedures
- [ ] Test backup restoration regularly

## Example Configurations

### Development Setup
```bash
# .env.development
OPENAI_BASE_URL=http://localhost:11434/v1
MODEL=llama3.1:8b
AGENT_LOG_LEVEL=DEBUG
TEMPERATURE=0.7
POSTGRES_PASSWORD=dev_password
JWT_SECRET=dev-secret-change-in-production
```

### Production Setup (OpenRouter)
```bash
# .env.production
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
MODEL=mistralai/mistral-large-2407
AGENT_LOG_LEVEL=INFO
TEMPERATURE=0.6

POSTGRES_USER=postiz_prod
POSTGRES_PASSWORD=$(openssl rand -hex 32)
JWT_SECRET=$(openssl rand -hex 32)
API_SECRET_KEY=$(openssl rand -hex 32)
```

### Enterprise Setup (Local LLM)
```bash
# .env.enterprise
OPENAI_BASE_URL=http://llm-cluster.internal:8000/v1
MODEL=mixtral-8x7b-instruct
AGENT_LOG_LEVEL=WARNING
TEMPERATURE=0.5

POSTGRES_USER=postiz_enterprise
POSTGRES_PASSWORD=$(openssl rand -hex 64)
JWT_SECRET=$(openssl rand -hex 64)
API_SECRET_KEY=$(openssl rand -hex 64)

# Internal network configuration
POSTIZ_API_URL=http://postiz-backend.internal:3000
```

## Troubleshooting Configuration Issues

### "No API key set" warnings
- Ensure `OPENAI_API_KEY` is set in `.env`
- For local Ollama, this can be empty but the variable should exist

### Connection refused to LLM endpoint
- Verify the URL is correct and accessible from within Docker
- Check firewall rules
- For local services, use `host.docker.internal` on Linux

### Model not found errors
- Confirm model name matches provider's naming convention
- Check if model needs to be pulled/downloaded first (Ollama)
- Verify API key has access to the requested model

### Database connection failures
- Ensure PostgreSQL is healthy: `docker logs postiz-db`
- Verify credentials match between services
- Check network connectivity within Docker network
