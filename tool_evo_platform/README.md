# ToolEVO Platform (Minimal Skeleton, Full Flow)

This is a minimal, runnable skeleton for a ToolEVO-style platform with:

- **tool-registry** service (FastAPI + Postgres)
- **variability-engine** service (FastAPI stub, ready to be extended)
- **tool-gateway** service (FastAPI, routes calls to actual tools based on registry)
- **orchestrator** service (FastAPI, simple entrypoint that calls the gateway)
- **weather-mock** service (FastAPI, dummy external tool to test the flow)
- **Postgres** database via Docker Compose

## Quick start

1. Ensure you have **Docker** and **docker-compose** installed.
2. Download and unzip this project, then:

```bash
cd tool_evo_platform
docker-compose up --build
```

3. Services (host ports):

- Tool Registry API: http://localhost:8001/docs
- Variability Engine API: http://localhost:8002/docs
- Tool Gateway API: http://localhost:8003/docs
- Orchestrator API: http://localhost:8004/docs
- Weather Mock API: http://localhost:8005/docs

> Internally, containers talk to each other on port `8000`, so registry URLs inside
> the cluster use `http://service-name:8000`.

---

## Example: End-to-end weather tool call

After `docker-compose up --build`:

### 1. Create a tool in the registry

```bash
curl -X POST http://localhost:8001/tools \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "weather-service",
    "display_name": "Weather Service",
    "description": "Provides fake weather data from weather-mock service"
  }'
```

Copy the returned `"id"` (e.g. `TOOL_ID`).

### 2. Create a tool version pointing to the weather-mock service

```bash
curl -X POST http://localhost:8001/tools/TOOL_ID/versions \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.0.0",
    "status": "active",
    "input_schema": {
      "type": "object",
      "properties": {
        "city": {"type": "string"},
        "country": {"type": "string"}
      },
      "required": ["city"]
    },
    "output_schema": {
      "type": "object",
      "properties": {
        "temperatureC": {"type": "number"},
        "description": {"type": "string"}
      },
      "required": ["temperatureC"]
    },
    "endpoint_protocol": "http",
    "endpoint_method": "GET",
    "endpoint_url": "http://weather-mock:8000/weather",
    "auth_type": "none"
  }'
```

> Note: `endpoint_url` uses the **Docker service name** `weather-mock` and port `8000`,
> which is how the gateway will reach it inside the Docker network.

### 3. Call the orchestrator (which calls the gateway → registry → weather-mock)

```bash
curl -X POST http://localhost:8004/execute \
  -H "Content-Type: application/json" \
  -d '{
    "slug": "weather-service",
    "input": {
      "city": "Orlando",
      "country": "US"
    }
  }'
```

You should see a JSON response that includes:

- The resolved tool + version,
- The result from the weather-mock service,
- Status codes.

This is a starting point: you can now plug in an LLM to the orchestrator,
extend the gateway to handle more protocols/auth, and evolve the variability engine
to actually mutate registry schemas for ToolEVO-style experiments.
