# ToolEVO Platform - Complete Package

A microservices-based platform for tool evolution and orchestration with performance optimizations and analysis tools.

## 📦 Package Contents

This repository contains the complete ToolEVO platform with performance optimizations and analysis tools.

### Included Components:

1. **tool_evo_platform/** - Complete microservices platform
   - 5 FastAPI services (registry, gateway, orchestrator, variability engine, weather-mock)
   - Docker Compose configuration
   - PostgreSQL database setup
   - All source code and configurations
   - See [tool_evo_platform/README.md](tool_evo_platform/README.md) for detailed service documentation

2. **toolevo_performance_analysis.md** - Comprehensive performance analysis
   - Current architecture analysis
   - Performance bottlenecks identification
   - 30+ optimization recommendations
   - Implementation roadmap

3. **toolevo_dashboard.html** - Interactive performance dashboard
   - Real-time metrics visualization
   - Performance charts and graphs
   - Service health monitoring
   - Open directly in any modern browser

4. **test_toolevo_locally.py** - Local testing script
   - Run without Docker for development
   - Built-in performance benchmarking
   - Automated load testing

5. **manage_toolevo.sh** - Management script
   - Easy setup and deployment
   - Service orchestration
   - Health checks and testing

## 🚀 Quick Start

### With Docker (Recommended):

```bash
cd tool_evo_platform
./manage_toolevo.sh setup
```

Or manually:
```bash
cd tool_evo_platform
docker-compose up --build
```

### Without Docker (Local Testing):
```bash
cd tool_evo_platform
python3 ../test_toolevo_locally.py
```

## 📊 View Dashboard
Simply open `toolevo_dashboard.html` in your browser to view the performance dashboard.

## 🔗 Service URLs (After Starting)
- Tool Registry API: http://localhost:9001/docs
- Variability Engine: http://localhost:9002/docs
- Tool Gateway: http://localhost:9003/docs
- Orchestrator: http://localhost:9004/docs
- Weather Mock: http://localhost:9005/docs
- PostgreSQL: localhost:5433

## 📈 Expected Performance Improvements
With the recommended optimizations:
- **80% reduction** in P95 response time
- **10x increase** in throughput
- **99.9% availability**
- **80% reduction** in database load

## 📝 Requirements
- Docker & Docker Compose
- Python 3.11+ (for local testing)
- 2GB RAM minimum
- Port range 9001-9005 available

## 🏗️ Architecture

The platform consists of 5 microservices:

- **tool-registry**: Manages tool definitions, versions, and metadata (FastAPI + PostgreSQL)
- **variability-engine**: Handles tool schema variations and mutations
- **tool-gateway**: Routes tool execution requests to appropriate endpoints
- **orchestrator**: Main entry point that coordinates tool execution
- **weather-mock**: Example external tool service for testing

## 📚 Documentation

- [Service Documentation](tool_evo_platform/README.md) - Detailed service setup and API documentation
- [Performance Analysis](toolevo_performance_analysis.md) - Optimization strategies and implementation guidance
- [Package README](README_PACKAGE.md) - Original package documentation

## 🛠️ Management Script Usage

The `manage_toolevo.sh` script provides easy management of the platform:

```bash
./manage_toolevo.sh setup    # Build, start, and create test data
./manage_toolevo.sh start    # Start all services
./manage_toolevo.sh stop     # Stop all services
./manage_toolevo.sh build    # Build all service images
./manage_toolevo.sh test     # Run end-to-end test
./manage_toolevo.sh clean    # Remove containers and volumes
./manage_toolevo.sh logs     # View service logs
```

## 🔄 Example: End-to-End Tool Call

After starting the services, you can test the complete flow:

1. Create a tool in the registry (or use the test data created by setup)
2. Call the orchestrator with a tool slug and input
3. The orchestrator routes through the gateway to the actual tool service

See [tool_evo_platform/README.md](tool_evo_platform/README.md) for detailed examples.

## 📄 License

This project is part of the ToolEVO platform research initiative.

---
Generated: December 2024  
Platform Version: 1.0.0

