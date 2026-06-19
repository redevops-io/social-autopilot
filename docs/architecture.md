# Architecture Documentation

## Overview

RedevOps.io Social Autopilot is a self-hostable platform that combines an open-source social media management core (Postiz) with autonomous AI agents for content creation, scheduling optimization, and engagement management.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         External Services                            │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │   Social Media   │  │   LLM Provider   │  │   Analytics      │  │
│  │   Platforms      │  │   (OpenRouter/   │  │   Data Sources   │  │
│  │                  │  │    Ollama/etc)   │  │                  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
└───────────┼─────────────────────┼─────────────────────┼────────────┘
            │                     │                     │
            ▼                     ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RedevOps.io Autopilot Platform                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      Agent Layer (Python)                      │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │  │
│  │  │ Content Creator │  │ Scheduling      │  │ Engagement    │  │  │
│  │  │ Agent           │  │ Optimizer       │  │ Manager       │  │  │
│  │  │                 │  │ Agent           │  │ Agent         │  │  │
│  │  └────────┬────────┘  └────────┬────────┘  └───────┬───────┘  │  │
│  │           │                    │                   │          │  │
│  └───────────┼────────────────────┼───────────────────┼──────────┘  │
│              │                    │                   │             │
│              ▼                    ▼                   ▼             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                      Agent API (FastAPI)                       │  │
│  │                    REST Endpoints + Swagger                    │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│                              ▼                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   OSS Core (Postiz)                           │  │
│  ├───────────────────────────────────────────────────────────────┤  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────┐  │  │
│  │  │   Frontend      │  │    Backend      │  │    Database   │  │  │
│  │  │   (React/Next)  │  │   (Node.js)     │  │   (PostgreSQL)│  │  │
│  │  └─────────────────┘  └─────────────────┘  └───────────────┘  │  │
│  │                                                                │  │
│  │  Features:                                                     │  │
│  │  - Multi-platform scheduling                                   │  │
│  │  - Content calendar                                            │  │
│  │  - Analytics dashboard                                         │  │
│  │  - Team collaboration                                          │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Agent Layer

The agent layer consists of autonomous Python agents that perform specific tasks:

#### Content Creator Agent
- **Purpose**: Generate social media content from topics
- **Input**: Topic, target platforms, tone preferences
- **Output**: Platform-specific content variations with hashtags
- **LLM Integration**: Uses OpenAI-compatible endpoints for content generation

#### Scheduling Optimizer Agent  
- **Purpose**: Analyze engagement patterns and recommend optimal posting times
- **Input**: Platform selection, optional historical data, timezone
- **Output**: Optimal time slots, confidence scores, actionable recommendations
- **Data Sources**: Historical engagement data from Postiz analytics

#### Engagement Manager Agent
- **Purpose**: Monitor comments/mentions and draft responses
- **Input**: Post ID, engagement data (comments, mentions)
- **Output**: Suggested responses, escalation queue for human review
- **Guardrails**: Automatic escalation of critical/high-priority items

### OSS Core: Postiz

Postiz is the self-hosted social media management platform that serves as the foundation:

- **Multi-platform support**: Twitter/X, LinkedIn, Facebook, Instagram, TikTok, and more
- **Content calendar**: Visual scheduling interface
- **Analytics**: Engagement metrics, reach, impressions tracking
- **Team collaboration**: Multi-user support with role-based permissions
- **API access**: REST API for integration with agent layer

### Data Flow

1. **Content Creation Flow**
   ```
   User Topic → Content Creator Agent → Generated Content → Postiz Calendar → Scheduled Posts
   ```

2. **Optimization Flow**
   ```
   Historical Data → Scheduling Optimizer → Recommendations → Updated Schedule
   ```

3. **Engagement Flow**
   ```
   Platform Webhooks → Engagement Manager → Response Drafts → Human Review → Published Responses
   ```

## Deployment Architecture

### Docker Compose Services

| Service | Purpose | Port |
|---------|---------|------|
| `postiz-db` | PostgreSQL database | 5432 (internal) |
| `postiz-redis` | Redis cache/queue | 6379 (internal) |
| `postiz-backend` | Postiz API server | 4455 |
| `postiz-frontend` | Postiz web UI | 4456 |
| `agent-api` | Agent REST API | 8000 |

### Network Topology

```
Internet
    │
    ├──→ :4455 → Postiz Backend (internal:3000)
    ├──→ :4456 → Postiz Frontend (internal:3000)  
    └──→ :8000 → Agent API (internal:8000)
    
Internal Network (autopilot-network):
    postiz-db ←→ postiz-backend ←→ agent-api
         ↓              ↓
    postiz-redis   postiz-frontend
```

## Security Considerations

### Data Privacy
- All data stored on customer infrastructure
- No external data transmission except to configured LLM provider
- Social media credentials encrypted in database

### API Security
- Agent API requires secret key authentication (configurable)
- CORS can be restricted to specific origins
- Rate limiting recommended for production deployments

### LLM Provider Security
- API keys stored as environment variables
- Support for self-hosted LLMs (Ollama, local inference)
- No data retention by default on most providers

## Scalability

### Horizontal Scaling
- Agent API can be scaled independently
- Redis enables distributed task queues
- Database connection pooling configured

### Resource Requirements
- Minimum: 2 CPU cores, 4GB RAM
- Recommended: 4 CPU cores, 8GB RAM  
- GPU optional (for local LLM inference)

## Monitoring and Observability

### Health Checks
- All services expose `/health` endpoints
- Docker health checks configured for orchestration

### Logging
- Structured logging via structlog
- Log levels configurable per service
- Logs volume mounted for persistence

### Metrics
- Prometheus metrics endpoint (planned)
- Request/response logging in agent API

## Extensibility

### Adding New Agents
1. Create new agent class in `agents/` directory
2. Implement required interface methods
3. Add API endpoint in `main.py`
4. Register in agent status endpoint

### Platform Integrations
1. Add platform configuration to relevant agent
2. Update Postiz with new platform support
3. Document platform-specific behaviors

## Troubleshooting

### Common Issues

**Agent API not responding:**
- Check LLM API key is set
- Verify network connectivity to LLM endpoint
- Review logs: `docker logs agent-api`

**Postiz not accessible:**
- Ensure database migration completed
- Check Redis connection
- Verify frontend/backend URLs match

**Content generation fails:**
- Confirm model name is correct for provider
- Check rate limits on LLM service
- Try reducing temperature parameter
