.DEFAULT_GOAL := start

.PHONY: start dev setup check

# Build the frontend and serve the app and API at http://localhost:8000.
start:
	bash scripts/demo.sh

# Start the backend on port 8000 and Vite with hot reload on port 5173.
dev:
	bash scripts/dev.sh

# Install dependencies and prepare local assets.
setup:
	bash scripts/setup.sh

# Run lint, formatting checks, the frontend build, and backend tests.
check:
	bash scripts/check.sh
