# RedevOps.io Social Autopilot

**Self-hostable AI Agent Platform for SME Content Creation, Scheduling & Engagement**

---

## The Problem: SME Time Poverty in Social Media

Small business owners face a **time poverty crisis**:
- 39% allocate over 10 hours weekly to social media management
- 43% struggle with consistent content creation
- Most spend 3-10 hours/week on tasks that could be automated

Legacy tools fail through:
- **Per-user pricing traps** ($99-$249/user/month)
- **Enterprise feature bloat** for simple needs
- **Data ownership loss** to SaaS vendors

---

## The RedevOps.io Solution

RedevOps.io Social Autopilot is an **open-source, self-hostable agentic platform** that:
1. **Eliminates recurring subscriptions** - One-time setup vs. $25K-$60K in 5-year SaaS costs
2. **Keeps your data on-premises** - Full ownership and privacy control
3. **Automates content creation & scheduling** - AI agents generate, optimize, and post autonomously
4. **Scales with your business** - From solo entrepreneur to multi-location SME

### Value Propositions

- **60-80% lower TCO** over 5 years compared to Hootsuite/Buffer + agency fees
- **Self-hosted architecture** - Deploy on your infrastructure, own your data
- **Autonomous AI agents** - Content generation, scheduling optimization, engagement automation
- **Open-source core (AGPL)** - No vendor lock-in, community-driven development

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RedevOps.io Autopilot                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────────────────────┐ │
│  │   Agent Layer   │───▶│  Autonomous AI Agents           │ │
│  │                 │    │  - Content Creator Agent        │ │
│  │  (Python)       │    │  - Scheduling Optimizer Agent   │ │
│  │                 │    │  - Engagement Manager Agent     │ │
│  └────────┬────────┘    └─────────────────────────────────┘ │
│           │                                                   │
│           ▼                                                   │
│  ┌─────────────────┐                                         │
│  │   OSS Core      │                                         │
│  │                 │                                         │
│  │  Postiz/Mixpost │───▶ Social Media Management            │ │
│  │                 │     - Multi-platform scheduling         │ │
│  └─────────────────┘     - Content calendar                  │
│                          - Analytics & reporting              │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

- **Core Platform**: [Postiz](https://github.com/gitroomhq/postiz-app) (32.1K stars) or Mixpost
  - Self-hosted social media management
  - Multi-platform support (Twitter, LinkedIn, Facebook, Instagram, etc.)
  - Built-in analytics and scheduling

- **Agent Layer**: Python-based autonomous agents
  - OpenAI-compatible LLM endpoints
  - Tool integration for content generation
  - Guardrails for safe automation

---

## Quickstart

### Prerequisites

- Docker & Docker Compose
- Access to an OpenAI-compatible LLM endpoint (OpenRouter, Ollama, etc.)
- Social media account credentials

### One-Command Deployment

```bash
# Clone and setup
git clone https://github.com/redevops-io/social-autopilot.git
cd social-autopilot

# Configure environment
cp .env.example .env
# Edit .env with your LLM endpoint and API keys

# Start the platform
docker-compose up -d
```

### Configuration

1. **LLM Endpoint**: Set `OPENAI_BASE_URL` to your preferred endpoint
   - OpenRouter: `https://openrouter.ai/api/v1`
   - Ollama (local): `http://localhost:11434/v1`
   - Self-hosted: Your inference server URL

2. **Model Selection**: Set `MODEL` to your chosen model
   - `mistralai/mistral-large-2407` (OpenRouter)
   - `llama3.1:8b` (Ollama)
   - Any OpenAI-compatible model

3. **Social Platform Credentials**: Add credentials in the Postiz UI at `http://localhost:4455`

### Access Points

- **Postiz Dashboard**: http://localhost:4455
- **Agent API**: http://localhost:8000/docs (Swagger)

---

## Agent Capabilities

### Content Creator Agent
- Generates social media posts from topic prompts
- Creates platform-specific variations (character limits, hashtags)
- Suggests optimal posting times based on audience analytics

### Scheduling Optimizer Agent
- Analyzes historical engagement data
- Recommends best posting schedules per platform
- Auto-adjusts based on performance metrics

### Engagement Manager Agent
- Monitors comments and mentions
- Drafts contextual responses for approval
- Escalates urgent matters to human review

---

## Development

```bash
# Run tests
make test

# Lint code
make lint

# Start agent in development mode
make dev
```

See [docs/configuration.md](./docs/configuration.md) for detailed configuration options.

---

## License

This project is licensed under **AGPL-3.0**. See [LICENSE](./LICENSE) for details.

The AGPL ensures:
- Free use, modification, and distribution
- All modifications remain open-source when deployed
- No proprietary forks that hide changes from users

---

## Contributing

We welcome contributions! Please see our contributing guidelines before submitting PRs.

### Areas We Need Help
- Additional platform integrations (TikTok, YouTube Shorts, etc.)
- Agent tool improvements
- Documentation translations
- Performance optimizations

---

## Support

- **Documentation**: See `docs/` directory
- **Issues**: GitHub Issues for bug reports and feature requests
- **Community**: Join our Discord community for discussions

---

**Built with ❤️ by the RedevOps.io Team** | [redevops.io](https://redevops.io)
