# Docker Deployment

This folder contains the Docker setup for Warehouse Operation Copilot.

## Files

- `Dockerfile.backend` builds the FastAPI and LangGraph backend.
- `Dockerfile.frontend` builds the React and Vite frontend, then serves it with Nginx.
- `nginx.conf` serves the frontend and proxies `/api/*` requests to the backend container.
- `docker-compose.yml` starts both services together.

## Prerequisites

- Docker Desktop or Docker Engine with Docker Compose v2.

## Run the full application

From the repository root:

```powershell
docker compose -f docker/docker-compose.yml up --build
```

Open the application at:

- Frontend: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- Backend API docs: <http://localhost:8000/docs>

## Stop the application

```powershell
docker compose -f docker/docker-compose.yml down
```

## Rebuild after code changes

```powershell
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up
```

## Notes

- The frontend is built with `VITE_API_BASE` set to an empty value, so browser requests use the same origin and Nginx proxies `/api/*` to the backend service.
- The backend listens on `0.0.0.0:8000` inside the container.
- The sample JSON data under `backend/app/data` is copied into the backend image for demo use.
