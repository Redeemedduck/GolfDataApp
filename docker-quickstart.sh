#!/bin/bash

# ==============================================================================
# Golf Data App - Docker Quick Start Script
# ==============================================================================
# This script helps you get started with the containerized application quickly.
# It checks prerequisites, sets up directories, and guides you through the
# first build and run.
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}===================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# ==============================================================================
# Step 1: Welcome and Prerequisites Check
# ==============================================================================
print_header "Golf Data App - Docker Setup"
echo ""
echo "This script will help you:"
echo "  1. Check prerequisites (Docker/OrbStack)"
echo "  2. Set up directories for persistent data"
echo "  3. Verify your .env file"
echo "  4. Build the Docker image"
echo "  5. Start the application"
echo ""
read -p "Press Enter to continue..."

# Check if Docker is installed
print_header "Checking Prerequisites"
echo ""

if command -v docker &> /dev/null; then
    print_success "Docker CLI found"
    docker --version
else
    print_error "Docker CLI not found"
    echo "Please install OrbStack from: https://orbstack.dev"
    exit 1
fi

# Check if Docker daemon is running
if docker info &> /dev/null; then
    print_success "Docker daemon is running"
else
    print_error "Docker daemon is not running"
    echo "Please start OrbStack from your Applications folder"
    exit 1
fi

# Check if docker-compose is available
if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose found"
    docker-compose --version
else
    print_error "Docker Compose not found"
    echo "OrbStack should include docker-compose. Please reinstall OrbStack."
    exit 1
fi

echo ""

# ==============================================================================
# Step 2: Set Up Directories
# ==============================================================================
print_header "Setting Up Directories"
echo ""

directories=("data" "media" "logs")

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        print_success "Created directory: $dir/"
    else
        print_info "Directory already exists: $dir/"
    fi
done

# Create .gitkeep files to preserve empty directories in git
for dir in "${directories[@]}"; do
    if [ ! -f "$dir/.gitkeep" ]; then
        touch "$dir/.gitkeep"
    fi
done

echo ""

# ==============================================================================
# Step 3: Check Environment File
# ==============================================================================
print_header "Checking Environment File"
echo ""

if [ ! -f ".env" ]; then
    print_warning ".env file not found"

    if [ -f ".env.example" ]; then
        echo ""
        read -p "Would you like to copy .env.example to .env? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cp .env.example .env
            print_success "Created .env from .env.example"
            print_warning "IMPORTANT: Edit .env and add your actual credentials!"
            echo ""
            read -p "Press Enter after you've edited .env with your credentials..."
        else
            print_error "Cannot proceed without .env file"
            exit 1
        fi
    else
        print_error ".env.example not found either"
        echo "Please create a .env file with your credentials"
        exit 1
    fi
else
    print_success ".env file exists"

    # Check if .env has actual values (not just placeholders)
    if grep -q "your-anon-key-here" .env 2>/dev/null; then
        print_warning ".env appears to contain placeholder values"
        echo "Please edit .env with your actual credentials"
        read -p "Press Enter after updating .env..."
    fi
fi

echo ""

# ==============================================================================
# Step 4: Build Docker Image
# ==============================================================================
print_header "Building Docker Image"
echo ""
echo "This will take 3-5 minutes on first build..."
echo "Subsequent builds will be much faster due to layer caching."
echo ""
read -p "Press Enter to start building..."

if docker-compose build; then
    print_success "Docker image built successfully!"
else
    print_error "Build failed!"
    echo "Check the error messages above for details"
    exit 1
fi

echo ""

# ==============================================================================
# Step 5: Start Application
# ==============================================================================
print_header "Starting Application"
echo ""

read -p "Would you like to start the application now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting container in detached mode..."

    if docker-compose up -d; then
        print_success "Container started successfully!"
        echo ""

        # Wait a few seconds for Streamlit to start
        echo "Waiting for Streamlit to start..."
        sleep 5

        # Check if container is running
        if docker ps | grep -q golf-data-app; then
            print_success "Container is running!"
            echo ""
            echo "Access your application at:"
            echo "  ${GREEN}http://localhost:8501${NC}"
            echo ""
            echo "Useful commands:"
            echo "  View logs:        docker-compose logs -f"
            echo "  Stop app:         docker-compose stop"
            echo "  Restart app:      docker-compose restart"
            echo "  Stop & remove:    docker-compose down"
            echo ""

            # Try to open browser
            if command -v open &> /dev/null; then
                read -p "Would you like to open the app in your browser? (y/n) " -n 1 -r
                echo ""
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    open http://localhost:8501
                fi
            fi
        else
            print_error "Container started but is not running"
            echo "Check logs with: docker-compose logs"
        fi
    else
        print_error "Failed to start container"
        echo "Check the error messages above for details"
        exit 1
    fi
else
    echo ""
    print_info "Skipped starting application"
    echo "To start manually later, run: docker-compose up -d"
fi

echo ""

# ==============================================================================
# Step 6: Final Tips
# ==============================================================================
print_header "Setup Complete!"
echo ""
echo "Next steps:"
echo "  1. Access the app: http://localhost:8501"
echo "  2. Paste a Uneekor report URL to import data"
echo "  3. Explore your golf data!"
echo ""
echo "For more information, see:"
echo "  - DOCKER_GUIDE.md    (comprehensive Docker guide)"
echo "  - README.md          (project overview)"
echo "  - QUICKSTART.md      (quick command reference)"
echo ""
echo "Common commands:"
echo "  docker-compose logs -f       # View live logs"
echo "  docker-compose restart       # Restart the app"
echo "  docker-compose down          # Stop and remove container"
echo "  docker-compose up -d --build # Rebuild and restart"
echo ""
print_success "Happy golfing! ⛳"
