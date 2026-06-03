#!/bin/bash

# Think Twice - Game Theory Platform v0.3
# Local Development Run Script

echo "🎮 Starting Think Twice Game Theory Platform..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Setup Backend
echo -e "${BLUE}Step 1: Setting up Backend...${NC}"
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing Python dependencies..."
pip install -r requirements.txt > /dev/null 2>&1

cd ..

# Step 2: Start PostgreSQL with Docker Compose
echo -e "${BLUE}Step 2: Starting PostgreSQL (Docker Compose)...${NC}"
docker compose up -d
echo "Waiting for PostgreSQL to be ready..."
sleep 5

# Step 3: Start Backend
echo -e "${BLUE}Step 3: Starting Backend (FastAPI)...${NC}"
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

sleep 3

# Step 4: Start Frontend
echo -e "${BLUE}Step 4: Starting Frontend (HTTP Server)...${NC}"
cd frontend
python -m http.server 3000 > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ..

sleep 2

# Success message
echo -e "${GREEN}✅ Platform Started Successfully!${NC}"
echo ""
echo -e "${YELLOW}Access the application:${NC}"
echo "  🌐 Frontend:    http://localhost:3000"
echo "  🔌 Backend API: http://localhost:8000"
echo "  📚 API Docs:    http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}To stop the platform:${NC}"
echo "  Press Ctrl+C to stop all services"
echo ""
echo -e "${YELLOW}Admin Login:${NC}"
echo "  Username: admin"
echo "  Password: (check your .env file)"
echo ""

# Cleanup function for graceful shutdown
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    
    # Kill backend and frontend processes
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    
    # Stop docker compose
    docker compose down
    
    echo -e "${GREEN}✅ Platform stopped cleanly${NC}"
    exit 0
}

# Set trap to catch Ctrl+C and other signals
trap cleanup SIGINT SIGTERM

# Keep script running
wait $BACKEND_PID $FRONTEND_PID
