#!/bin/bash
# RedevOps.io Social Autopilot - Installation Script
# Self-hostable AI Agent Platform for SME Content Creation, Scheduling & Engagement

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "  RedevOps.io Social Autopilot Installer"
echo "=============================================="
echo ""

# Check for Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed.${NC}"
        echo "Please install Docker first:"
        echo "  https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed.${NC}"
        echo "Please install Docker Compose:"
        echo "  https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Docker and Docker Compose are installed${NC}"
}

# Check for .env file
check_env() {
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Creating .env from template...${NC}"
        cp .env.example .env
        echo ""
        echo -e "${YELLOW}⚠ IMPORTANT: Please edit .env before running!${NC}"
        echo "Required changes:"
        echo "  - OPENAI_API_KEY (or use local Ollama)"
        echo "  - POSTGRES_PASSWORD"
        echo "  - JWT_SECRET"
        echo "  - API_SECRET_KEY"
        echo ""
        read -p "Press Enter to continue after editing .env, or Ctrl+C to cancel..."
    fi
    
    # Check for essential variables
    if [ -z "$OPENAI_API_KEY" ] && [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Try reading from file
        source .env 2>/dev/null || true
    fi
    
    if [ -f .env ]; then
        source .env 2>/dev/null || true
    fi
    
    echo -e "${GREEN}✓ Environment configuration found${NC}"
}

# Pull images and start services
start_services() {
    echo ""
    echo -e "${YELLOW}Pulling latest images...${NC}"
    
    # Check if docker compose or docker-compose
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    $COMPOSE_CMD pull
    
    echo ""
    echo -e "${YELLOW}Starting services...${NC}"
    $COMPOSE_CMD up -d
    
    echo ""
    echo -e "${GREEN}=============================================="
    echo "  Installation Complete!"
    echo "==============================================${NC}"
    echo ""
    echo "Access points:"
    echo "  Postiz Dashboard:   http://localhost:4456"
    echo "  Agent API Docs:     http://localhost:8000/docs"
    echo "  Agent Health Check: http://localhost:8000/health"
    echo ""
    echo "Next steps:"
    echo "  1. Open Postiz Dashboard and configure social media accounts"
    echo "  2. Test the Agent API at http://localhost:8000/docs"
    echo "  3. Read docs/configuration.md for advanced setup"
    echo ""
    echo "Useful commands:"
    echo "  make logs       - View service logs"
    echo "  make down       - Stop all services"
    echo "  make clean      - Remove containers and volumes"
    echo ""
}

# Main installation flow
main() {
    check_docker
    
    if [ "$1" != "--skip-env-check" ]; then
        check_env
    fi
    
    start_services
}

# Run main function
main "$@"
