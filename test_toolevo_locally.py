#!/usr/bin/env python3
"""
ToolEVO Platform Local Test Runner
This script allows testing the ToolEVO platform without Docker by running services locally.
"""

import asyncio
import subprocess
import time
import os
import sys
import signal
import json
from pathlib import Path
import httpx
from typing import Dict, List, Optional

class ServiceManager:
    """Manages local service processes"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.services: Dict[str, subprocess.Popen] = {}
        self.ports = {
            "tool-registry": 9001,
            "variability-engine": 9002,
            "tool-gateway": 9003,
            "orchestrator": 9004,
            "weather-mock": 9005
        }
        
    def start_service(self, name: str, env_vars: Optional[Dict[str, str]] = None) -> bool:
        """Start a single service"""
        service_path = self.base_path / "services" / name
        
        if not service_path.exists():
            print(f"Service path {service_path} does not exist")
            return False
        
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        
        port = self.ports.get(name, 8000)
        
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--reload"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                cwd=service_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.services[name] = process
            print(f"✓ Started {name} on port {port}")
            return True
        except Exception as e:
            print(f"✗ Failed to start {name}: {e}")
            return False
    
    def stop_all(self):
        """Stop all running services"""
        for name, process in self.services.items():
            process.terminate()
            try:
                process.wait(timeout=5)
                print(f"✓ Stopped {name}")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"✓ Force-stopped {name}")
    
    def check_health(self, service: str, port: int) -> bool:
        """Check if a service is healthy"""
        try:
            response = httpx.get(f"http://localhost:{port}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def wait_for_services(self, timeout: int = 30) -> bool:
        """Wait for all services to be healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_healthy = True
            for name, port in self.ports.items():
                if name in self.services:
                    if not self.check_health(name, port):
                        all_healthy = False
                        break
            
            if all_healthy:
                return True
            
            time.sleep(1)
        
        return False

class PerformanceTester:
    """Run performance tests against the platform"""
    
    def __init__(self, base_url: str = "http://localhost"):
        self.base_url = base_url
        self.tool_id: Optional[str] = None
        self.tool_slug: str = "perf-test-weather"
        
    async def setup_test_tool(self):
        """Create a test tool in the registry"""
        async with httpx.AsyncClient() as client:
            # Create tool
            response = await client.post(
                f"{self.base_url}:9001/tools",
                json={
                    "slug": self.tool_slug,
                    "display_name": "Performance Test Weather Service",
                    "description": "Tool for performance testing"
                }
            )
            
            if response.status_code == 201:
                data = response.json()
                self.tool_id = data["id"]
                print(f"✓ Created test tool: {self.tool_slug} (ID: {self.tool_id})")
                
                # Create tool version
                version_response = await client.post(
                    f"{self.base_url}:9001/tools/{self.tool_id}/versions",
                    json={
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
                            }
                        },
                        "endpoint_protocol": "http",
                        "endpoint_method": "GET",
                        "endpoint_url": "http://localhost:9005/weather",
                        "auth_type": "none"
                    }
                )
                
                if version_response.status_code == 201:
                    print("✓ Created tool version 1.0.0")
                else:
                    print(f"✗ Failed to create version: {version_response.text}")
            else:
                print(f"✗ Failed to create tool: {response.text}")
    
    async def run_performance_test(self, num_requests: int = 100, concurrent: int = 10):
        """Run a simple performance test"""
        print(f"\nRunning performance test: {num_requests} requests, {concurrent} concurrent")
        
        async def make_request():
            async with httpx.AsyncClient(timeout=30.0) as client:
                start = time.time()
                try:
                    response = await client.post(
                        f"{self.base_url}:9004/execute",
                        json={
                            "slug": self.tool_slug,
                            "input": {
                                "city": "TestCity",
                                "country": "TestCountry"
                            }
                        }
                    )
                    duration = time.time() - start
                    return {
                        "success": response.status_code == 200,
                        "duration": duration,
                        "status": response.status_code
                    }
                except Exception as e:
                    duration = time.time() - start
                    return {
                        "success": False,
                        "duration": duration,
                        "error": str(e)
                    }
        
        # Run requests in batches
        results = []
        for i in range(0, num_requests, concurrent):
            batch_size = min(concurrent, num_requests - i)
            batch = await asyncio.gather(*[make_request() for _ in range(batch_size)])
            results.extend(batch)
            print(f"  Completed {i + batch_size}/{num_requests} requests")
        
        # Calculate statistics
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]
        durations = [r["duration"] for r in successful]
        
        if durations:
            durations.sort()
            avg_duration = sum(durations) / len(durations)
            p50 = durations[int(len(durations) * 0.5)]
            p95 = durations[int(len(durations) * 0.95)] if len(durations) > 20 else durations[-1]
            p99 = durations[int(len(durations) * 0.99)] if len(durations) > 100 else durations[-1]
            
            print("\n=== Performance Test Results ===")
            print(f"Total Requests: {num_requests}")
            print(f"Successful: {len(successful)} ({len(successful)/num_requests*100:.1f}%)")
            print(f"Failed: {len(failed)} ({len(failed)/num_requests*100:.1f}%)")
            print(f"\nResponse Times:")
            print(f"  Average: {avg_duration*1000:.2f}ms")
            print(f"  P50: {p50*1000:.2f}ms")
            print(f"  P95: {p95*1000:.2f}ms")
            print(f"  P99: {p99*1000:.2f}ms")
            print(f"  Min: {min(durations)*1000:.2f}ms")
            print(f"  Max: {max(durations)*1000:.2f}ms")
            print(f"\nThroughput: {num_requests/sum(durations)*len(durations):.2f} req/s")
        else:
            print("\n✗ All requests failed!")
            for r in results[:5]:
                if "error" in r:
                    print(f"  Error: {r['error']}")

class SQLiteSetup:
    """Setup SQLite database for testing"""
    
    @staticmethod
    def create_database():
        """Create SQLite database with schema"""
        import sqlite3
        
        conn = sqlite3.connect('toolevo.db')
        cursor = conn.cursor()
        
        # Create tools table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tools (
                id TEXT PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create tool_versions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tool_versions (
                id TEXT PRIMARY KEY,
                tool_id TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                input_schema TEXT NOT NULL,
                output_schema TEXT NOT NULL,
                endpoint_protocol TEXT NOT NULL,
                endpoint_method TEXT,
                endpoint_url TEXT,
                auth_type TEXT DEFAULT 'none',
                auth_key_name TEXT,
                auth_key_location TEXT,
                cost_per_call_usd TEXT,
                valid_from TIMESTAMP,
                valid_to TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tool_id) REFERENCES tools(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✓ Created SQLite database")

def install_dependencies():
    """Install required Python packages"""
    packages = [
        "fastapi",
        "uvicorn[standard]",
        "pydantic<2",
        "httpx",
        "sqlalchemy>=2.0",
        "python-dotenv",
        "openai>=1.0.0"
    ]
    
    print("Installing dependencies...")
    for package in packages:
        subprocess.run([sys.executable, "-m", "pip", "install", package], 
                      capture_output=True, text=True)
    print("✓ Dependencies installed")

async def main():
    """Main test runner"""
    print("=== ToolEVO Platform Local Test Runner ===\n")
    
    # Check if we're in the right directory
    if not Path("docker-compose.yml").exists():
        print("✗ Please run this script from the tool_evo_platform directory")
        sys.exit(1)
    
    # Install dependencies
    print("Step 1: Installing dependencies")
    install_dependencies()
    
    # Setup database
    print("\nStep 2: Setting up database")
    SQLiteSetup.create_database()
    
    # Start services
    print("\nStep 3: Starting services")
    manager = ServiceManager()
    
    # Define service dependencies and environment variables
    services_config = [
        ("tool-registry", {"DATABASE_URL": "sqlite:///./toolevo.db"}),
        ("weather-mock", {}),
        ("variability-engine", {"REGISTRY_BASE_URL": "http://localhost:9001"}),
        ("tool-gateway", {"REGISTRY_BASE_URL": "http://localhost:9001"}),
        ("orchestrator", {
            "GATEWAY_BASE_URL": "http://localhost:9003",
            "REGISTRY_BASE_URL": "http://localhost:9001"
        })
    ]
    
    # Start services in order
    for service_name, env_vars in services_config:
        if not manager.start_service(service_name, env_vars):
            print(f"✗ Failed to start {service_name}, aborting")
            manager.stop_all()
            sys.exit(1)
        time.sleep(2)  # Give each service time to start
    
    # Wait for services to be healthy
    print("\nStep 4: Waiting for services to be healthy")
    if manager.wait_for_services():
        print("✓ All services are healthy")
    else:
        print("✗ Some services failed to start properly")
        manager.stop_all()
        sys.exit(1)
    
    # Setup test data
    print("\nStep 5: Setting up test data")
    tester = PerformanceTester()
    await tester.setup_test_tool()
    
    # Run performance test
    print("\nStep 6: Running performance tests")
    
    # Warmup
    print("Warming up...")
    await tester.run_performance_test(num_requests=10, concurrent=2)
    
    # Actual test
    print("\n--- Small Load Test ---")
    await tester.run_performance_test(num_requests=50, concurrent=5)
    
    print("\n--- Medium Load Test ---")
    await tester.run_performance_test(num_requests=100, concurrent=10)
    
    print("\n--- High Load Test ---")
    await tester.run_performance_test(num_requests=200, concurrent=20)
    
    # Cleanup
    print("\n\nStep 7: Cleaning up")
    manager.stop_all()
    print("✓ Test completed")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\nInterrupted! Cleaning up...")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    asyncio.run(main())
