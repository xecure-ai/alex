#!/bin/bash
# Run the researcher service locally

echo "Starting Alex Researcher Service..."
echo "=================================="
echo ""
echo "The service will be available at:"
echo "  http://localhost:8000"
echo ""
echo "API endpoints:"
echo "  GET  /         - Root health check"
echo "  GET  /health   - Detailed health check"  
echo "  POST /research - Generate investment research"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run with uvicorn for better development experience
uv run uvicorn server:app --reload --host 0.0.0.0 --port 8000