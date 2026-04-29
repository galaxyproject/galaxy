# AI Agent Configuration

Galaxy includes a multi-agent AI system built on [pydantic-ai](https://github.com/pydantic/pydantic-ai). The agents provide specialized assistants for answering platform questions, diagnosing job errors, creating custom tools, recommending tools, and more. The entire system is gated behind AI inference configuration -- if no AI credentials are provided, the agent features are completely invisible to users.

## Overview

When AI is configured, Galaxy exposes two main user-facing features:

- **ChatGXY**: A sidebar chat interface (visible in the Activity Bar) that routes user questions to specialized agents.
- **GalaxyWizard**: An error-analysis widget that appears on failed job pages to help users understand what went wrong.

All AI configuration lives in `galaxy.yml` under the `galaxy:` section. There is no admin UI for toggling agents -- everything is controlled through configuration files.

## Minimum Required Configuration

The recommended way to configure AI is through `inference_services`. Setting this value (or the deprecated `ai_api_key` / `ai_api_base_url`) is what activates the entire agent system. Without at least one of these, no agent code loads, the ChatGXY sidebar entry is hidden, and the GalaxyWizard error-analysis widget does not appear.

```yaml
galaxy:
    inference_services:
        default:
            model: "openai:gpt-4o-mini"
            api_key: "sk-..."
```

That is all you need to get started.

## Configuration Settings

All AI-related settings go under the `galaxy:` section in `galaxy.yml`:

| Setting              | Default | Description                                                                                                                                    |
| -------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `inference_services` | (none)  | Per-agent configuration with fine-grained control over model, temperature, tokens, and API keys. This is the recommended configuration method. |

```{note}
The legacy config keys `ai_api_key`, `ai_api_base_url`, and `ai_model` (and their older aliases `openai_api_key` and `openai_model`) still work but are deprecated. They will be removed in a future release. Use `inference_services` in new deployments.
```

## Supported AI Backends

Galaxy supports multiple LLM providers through pydantic-ai's provider system. The model name prefix determines which provider is used:

### OpenAI (default)

Use bare model names like `gpt-4o` or prefixed as `openai:gpt-4o`. This is the default provider and requires only an API key.

```yaml
galaxy:
    inference_services:
        default:
            model: "openai:gpt-4o"
            api_key: "sk-..."
```

### Anthropic / Claude

Use the `anthropic:` prefix, e.g. `anthropic:claude-sonnet-4-5`.

```yaml
galaxy:
    inference_services:
        default:
            model: "anthropic:claude-sonnet-4-5"
            api_key: "sk-ant-..."
```

```{warning}
Anthropic support requires the optional `pydantic-ai[anthropic]` Python package to be installed in Galaxy's virtual environment. If it is not installed, agents configured with an `anthropic:` model prefix will fail at runtime.
```

### Google / Gemini

Use the `google:` prefix, e.g. `google:gemini-2.5-pro`.

```yaml
galaxy:
    inference_services:
        default:
            model: "google:gemini-2.5-pro"
            api_key: "AIza..."
```

```{warning}
Google support requires the optional `pydantic-ai[google]` Python package to be installed in Galaxy's virtual environment.
```

### OpenAI-Compatible (vLLM, Ollama, LiteLLM, TACC)

Use any model name combined with `api_base_url` to point at a self-hosted or institutional inference endpoint. The request is routed through the OpenAI-compatible API path.

```yaml
galaxy:
    inference_services:
        default:
            model: "llama3.1"
            api_base_url: "http://localhost:11434/v1/"
            api_key: "not-needed-but-required-by-some-clients"
```

```{note}
Not all models support structured output (JSON schema mode). The `custom_tool` agent requires structured output and will return a graceful error if the configured model lacks that capability.
```

## Per-Agent Configuration via `inference_services`

The `inference_services` dictionary allows fine-grained control over individual agents. Each key is either `default` (applied to all agents as a fallback) or a specific agent type name.

Supported keys within each agent block:

| Key            | Description                                                                             |
| -------------- | --------------------------------------------------------------------------------------- |
| `model`        | Model name with optional provider prefix (e.g. `gpt-4o`, `anthropic:claude-sonnet-4-5`) |
| `api_key`      | API key override for this agent or default                                              |
| `api_base_url` | Base URL override for this agent or default                                             |
| `temperature`  | Sampling temperature (0.0 - 1.0)                                                        |
| `max_tokens`   | Maximum tokens in the response                                                          |

### Example: Per-Agent Overrides

Use a cheap model globally but a more capable model for agents that need it:

```yaml
galaxy:
    inference_services:
        default:
            model: "openai:gpt-4o-mini"
            api_key: "sk-..."
            temperature: 0.7
        custom_tool:
            model: "openai:gpt-4o"
            temperature: 0.4
            max_tokens: 2000
        error_analysis:
            model: "openai:gpt-4o"
            temperature: 0.2
            max_tokens: 2000
```

### Example: Mixed Providers

Use different providers for different agents:

```yaml
galaxy:
    inference_services:
        default:
            model: "anthropic:claude-sonnet-4-5"
            api_key: "sk-ant-..."
            temperature: 0.3
        custom_tool:
            model: "openai:gpt-4o"
            api_key: "sk-..."
            temperature: 0.4
```

### Example: Self-Hosted with Ollama

```yaml
galaxy:
    inference_services:
        default:
            model: "llama3.1"
            api_base_url: "http://localhost:11434/v1/"
            api_key: "ollama"
            temperature: 0.7
```

### Example: Institutional Endpoint (TACC, LiteLLM proxy)

```yaml
galaxy:
    inference_services:
        default:
            model: "llama-4-scout"
            api_base_url: "http://litellm-proxy.internal:4000/v1/"
            api_key: "internal-key"
            temperature: 0.7
```

## Configuration Cascade

At runtime, each agent resolves its configuration through a four-level cascade. The precedence order is:

1. **Agent-specific config** -- `inference_services.<agent_type>.<key>` (e.g. `inference_services.custom_tool.model`)
2. **Default inference config** -- `inference_services.default.<key>`
3. **Legacy global config** -- `ai_model`, `ai_api_key`, `ai_api_base_url` (deprecated)
4. **Hardcoded defaults** -- model `gpt-4o-mini`, no base URL override

This means you can set a cheap model as the global default and override only the agents that need a more capable (and more expensive) model.

## Available Agents

Galaxy registers the following agent types:

| Agent Type            | Purpose                                                          |
| --------------------- | ---------------------------------------------------------------- |
| `router`              | Routes user queries to the appropriate specialized agent         |
| `error_analysis`      | Diagnoses failed jobs and suggests fixes                         |
| `custom_tool`         | Generates custom Galaxy tools from natural language descriptions |
| `orchestrator`        | Coordinates multi-step workflow tasks                            |
| `tool_recommendation` | Recommends tools from the toolbox for a given task               |
| `page_assistant`      | Assists with Galaxy page editing                                 |

All registered agents are enabled when the AI system is active.

## Prerequisites and Dependencies

The core dependency is `pydantic-ai`, declared in Galaxy's `pyproject.toml`. It is installed automatically with Galaxy. For non-OpenAI providers, install the corresponding extras:

```bash
# For Anthropic/Claude support
pip install 'pydantic-ai[anthropic]'

# For Google/Gemini support
pip install 'pydantic-ai[google]'
```

The database migration for chat storage (`chat_exchange` and `chat_exchange_message` tables) runs as part of normal Galaxy schema migrations. No separate migration step is needed.

## Verifying the Configuration

### Check the Agent API Endpoint

After configuring AI and restarting Galaxy, query the agents endpoint to verify that agents are available:

```bash
curl -s -H "x-api-key: YOUR_GALAXY_API_KEY" \
  http://localhost:8080/api/ai/agents | python -m json.tool
```

You should see a list of enabled agents with their types. If AI is not configured, this endpoint returns an error indicating that the agent system is not available.

### Check if ChatGXY Appears in the Sidebar

Log in to the Galaxy web interface. If AI is properly configured, a **ChatGXY** entry should appear in the Activity Bar on the left side of the screen. If it does not appear:

1. Verify that `inference_services` is set in `galaxy.yml` (or the deprecated `ai_api_key` / `ai_api_base_url`).
2. Check that Galaxy was restarted after the configuration change.
3. Check the Galaxy server log for import errors related to `pydantic-ai`.

### Check the Configuration API

The frontend determines whether to show AI features by checking the `llm_api_configured` flag from the configuration API:

```bash
curl -s http://localhost:8080/api/configuration | python -m json.tool | grep llm_api_configured
```

This should return `"llm_api_configured": true` when AI is active.

## Troubleshooting

### ChatGXY does not appear in the sidebar

- Confirm that `inference_services` is set in `galaxy.yml` under the `galaxy:` section (or the deprecated `ai_api_key` / `ai_api_base_url`).
- Restart Galaxy after any configuration change.
- Check that `pydantic-ai` is installed: `pip show pydantic-ai`.
- Check Galaxy's log for `Agent system is not available` errors, which indicate a missing or broken `pydantic-ai` installation.

### "Agent system is not available" error from the API

This means the `pydantic-ai` library failed to import. Verify it is installed in Galaxy's Python environment and that the version meets the minimum requirement.

### Anthropic or Google models fail with ImportError

Install the required provider extras:

```bash
pip install 'pydantic-ai[anthropic]'   # for anthropic: prefixed models
pip install 'pydantic-ai[google]'       # for google: prefixed models
```

### Custom tool agent fails with "structured output not supported"

The `custom_tool` agent requires a model that supports structured JSON output (JSON schema mode). Some models (e.g. certain DeepSeek variants) do not support this. Switch the `custom_tool` agent to a model that does, such as `gpt-4o` or `anthropic:claude-sonnet-4-5`.

### Requests succeed but responses are empty or low quality

- Check the `temperature` setting. Very low values (< 0.1) can produce repetitive output; very high values (> 0.9) can produce incoherent output.
- Check the `max_tokens` setting. If it is too low, responses may be truncated.
- Verify the model name is valid for your provider. An incorrect model name may silently fall back or return errors.

### Self-hosted endpoint returns connection errors

- Verify the `inference_services.default.api_base_url` is reachable from the Galaxy server.
- The URL should include the path prefix expected by the API (typically `/v1/`).
- Check firewall rules if the inference service is on a different host.

## Complete Configuration Example

A production deployment using a LiteLLM proxy with per-agent model overrides:

```yaml
galaxy:
    inference_services:
        default:
            model: "llama-4-scout"
            api_base_url: "http://litellm.internal:4000/v1/"
            api_key: "proxy-key-..."
            temperature: 0.5
        custom_tool:
            model: "openai:gpt-4o"
            api_key: "sk-..."
            temperature: 0.4
            max_tokens: 2000
        error_analysis:
            model: "anthropic:claude-sonnet-4-5"
            api_key: "sk-ant-..."
            temperature: 0.2
            max_tokens: 2000
```
