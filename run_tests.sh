#!/bin/bash

# Test runner script for local environment
# This script sets up the environment variables for local testing

echo "Starting test run..."
echo "Using localhost for DB and Redis connections"
echo ""

# Set environment variables for local testing
export DB_HOST=localhost
export REDIS_HOST=localhost

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run tests with pytest
pytest tests/tests/test_apply_integration.py \
       tests/tests/test_complete_integration.py \
       tests/tests/test_redis_lock_integration.py \
       -v --tb=short

echo ""
echo "Test run completed!"
