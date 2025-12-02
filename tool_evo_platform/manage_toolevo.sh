#!/bin/bash

# ToolEVO Platform Setup and Run Script
# This script helps set up and run the ToolEVO platform with Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    echo "Checking prerequisites..."
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_status "Docker is installed"
    
    if ! command_exists docker-compose; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    print_status "Docker Compose is installed"
    
    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    print_status "Docker daemon is running"
}

# Function to build services
build_services() {
    echo -e "\nBuilding services..."
    docker-compose build --parallel
    print_status "All services built successfully"
}

# Function to start services
start_services() {
    echo -e "\nStarting services..."
    docker-compose up -d
    print_status "All services started"
    
    echo -e "\nWaiting for services to be healthy..."
    sleep 10
    
    # Check service health
    services=("tool-registry:9001" "variability-engine:9002" "tool-gateway:9003" "orchestrator:9004" "weather-mock:9005")
    
    for service in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service"
        if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/health" | grep -q "200"; then
            print_status "$name is healthy (port $port)"
        else
            print_warning "$name might not be ready yet (port $port)"
        fi
    done
}

# Function to create test data
create_test_data() {
    echo -e "\nCreating test data..."
    
    # Create a test tool
    TOOL_RESPONSE=$(curl -s -X POST http://localhost:9001/tools \
        -H "Content-Type: application/json" \
        -d '{
            "slug": "weather-service",
            "display_name": "Weather Service",
            "description": "Provides weather data from weather-mock service"
        }')
    
    TOOL_ID=$(echo $TOOL_RESPONSE | grep -o '"id":"[^"]*' | sed 's/"id":"//')
    
    if [ -z "$TOOL_ID" ]; then
        print_error "Failed to create test tool"
        return
    fi
    
    print_status "Created test tool with ID: $TOOL_ID"
    
    # Create a tool version
    VERSION_RESPONSE=$(curl -s -X POST "http://localhost:9001/tools/$TOOL_ID/versions" \
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
                }
            },
            "endpoint_protocol": "http",
            "endpoint_method": "GET",
            "endpoint_url": "http://weather-mock:8000/weather",
            "auth_type": "none"
        }')
    
    if echo "$VERSION_RESPONSE" | grep -q '"id"'; then
        print_status "Created tool version 1.0.0"
    else
        print_warning "Failed to create tool version"
    fi
}

# Function to run a test
run_test() {
    echo -e "\nRunning end-to-end test..."
    
    RESPONSE=$(curl -s -X POST http://localhost:9004/execute \
        -H "Content-Type: application/json" \
        -d '{
            "slug": "weather-service",
            "input": {
                "city": "Orlando",
                "country": "US"
            }
        }')
    
    if echo "$RESPONSE" | grep -q '"orchestrator":"ok"'; then
        print_status "End-to-end test passed!"
        echo "Response: $RESPONSE" | python -m json.tool 2>/dev/null || echo "$RESPONSE"
    else
        print_error "End-to-end test failed"
        echo "Response: $RESPONSE"
    fi
}

# Function to show service URLs
show_urls() {
    echo -e "\n${GREEN}=== Service URLs ===${NC}"
    echo "Tool Registry API:     http://localhost:9001/docs"
    echo "Variability Engine:    http://localhost:9002/docs"
    echo "Tool Gateway:          http://localhost:9003/docs"
    echo "Orchestrator:          http://localhost:9004/docs"
    echo "Weather Mock:          http://localhost:9005/docs"
    echo "PostgreSQL:            localhost:5433"
    echo ""
    echo "Performance Dashboard: Open toolevo_dashboard.html in your browser"
}

# Function to stop services
stop_services() {
    echo -e "\nStopping services..."
    docker-compose down
    print_status "All services stopped"
}

# Function to clean up
cleanup() {
    echo -e "\nCleaning up..."
    docker-compose down -v
    print_status "Cleaned up containers and volumes"
}

# Function to view logs
view_logs() {
    service=$1
    if [ -z "$service" ]; then
        docker-compose logs -f
    else
        docker-compose logs -f "$service"
    fi
}

# Function to run performance test
run_performance_test() {
    echo -e "\nRunning performance test..."
    
    # Check if Python is available
    if ! command_exists python3; then
        print_error "Python 3 is required for performance testing"
        return
    fi
    
    # Run the local test script
    if [ -f "test_toolevo_locally.py" ]; then
        python3 test_toolevo_locally.py
    else
        print_warning "Performance test script not found"
    fi
}

# Main menu
show_menu() {
    echo -e "\n${GREEN}=== ToolEVO Platform Manager ===${NC}"
    echo "1. Check prerequisites"
    echo "2. Build all services"
    echo "3. Start all services"
    echo "4. Stop all services"
    echo "5. Clean up (remove containers and volumes)"
    echo "6. Create test data"
    echo "7. Run end-to-end test"
    echo "8. View logs (all services)"
    echo "9. View logs (specific service)"
    echo "10. Run performance test"
    echo "11. Show service URLs"
    echo "12. Quick setup (build, start, create test data)"
    echo "0. Exit"
    echo -n "Choose an option: "
}

# Quick setup function
quick_setup() {
    echo -e "\n${GREEN}Running quick setup...${NC}"
    check_prerequisites
    build_services
    start_services
    create_test_data
    show_urls
    echo -e "\n${GREEN}Quick setup complete!${NC}"
}

# Main script
main() {
    # If arguments provided, execute specific command
    if [ $# -gt 0 ]; then
        case "$1" in
            start)
                check_prerequisites
                start_services
                show_urls
                ;;
            stop)
                stop_services
                ;;
            build)
                check_prerequisites
                build_services
                ;;
            test)
                run_test
                ;;
            setup)
                quick_setup
                ;;
            clean)
                cleanup
                ;;
            logs)
                view_logs "$2"
                ;;
            *)
                echo "Usage: $0 {start|stop|build|test|setup|clean|logs [service]}"
                exit 1
                ;;
        esac
        exit 0
    fi
    
    # Interactive menu
    while true; do
        show_menu
        read -r choice
        
        case $choice in
            1) check_prerequisites ;;
            2) build_services ;;
            3) start_services && show_urls ;;
            4) stop_services ;;
            5) cleanup ;;
            6) create_test_data ;;
            7) run_test ;;
            8) view_logs ;;
            9) 
                echo -n "Enter service name (tool-registry, orchestrator, etc.): "
                read -r service
                view_logs "$service"
                ;;
            10) run_performance_test ;;
            11) show_urls ;;
            12) quick_setup ;;
            0) 
                echo "Exiting..."
                exit 0
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac
    done
}

# Handle Ctrl+C
trap 'echo -e "\n${YELLOW}Interrupted. Exiting...${NC}"; exit 1' INT

# Run main function
main "$@"
