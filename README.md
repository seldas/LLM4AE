This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

📁 Project Structure Overview

| Name                       | Description                                                                                                                |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `client/`                  | Frontend source code for the annotation user interface.                                                         |
| `client_archives/`         | Archived or legacy versions of the frontend client code for reference.                                                     |
| `server/`                  | Backend server code, typically implemented with Flask or similar Python framework, handling API logic and data processing. |
| `nginx/`                   | NGINX reverse proxy configuration files for routing frontend/backend requests in development or production.                |
| `.gitignore`               | Specifies files and directories to be excluded from Git version control (e.g., logs, build artifacts, secrets).            |
| `docker-compose.dev.yaml`  | Docker Compose configuration for setting up the development environment with all services.                                 |
| `docker-compose.prod.yaml` | Docker Compose configuration for deploying the project in a production environment.                                        |


### 🚀 Quick Start

This project provides Docker Compose configurations for both **development** and **production** environments.

---

### 🛠️ Development Server

To start the development environment with live-reloading and hot module replacement:

```bash
docker compose -f docker-compose.dev.yaml up --build
```

This will start the following services:

| Service                | Description                                          | Access URL                                                 |
| ---------------------- | ---------------------------------------------------- | ---------------------------------------------------------- |
| `docanno_frontend_dev` | React-based frontend in development mode             | [http://localhost:8862](http://localhost:8862) (via NGINX) |
| `docanno_backend_dev`  | Flask-based backend API                              | [http://localhost:5000](http://localhost:5000)             |
| `nginx_dev`            | Reverse proxy routing frontend requests to port 8862 | [http://localhost:8862](http://localhost:8862)             |

> `nginx` listens on **port 8862**, proxying requests to the frontend and backend.
> Frontend hot reloads on file changes; backend runs in dev mode with auto-reload if configured in `app.py`.

To stop and remove containers:

```bash
docker compose -f docker-compose.dev.yaml down
```

---

### ⚙️ Configuration Notes

* **Frontend source** is mounted from `./client/` and runs `npm run dev` with legacy peer dependency support.
* **Backend source** is mounted from `./server/` and runs `app.py` directly with `FLASK_ENV=development`.
* **NGINX config** is loaded from `./nginx/conf.dev.d/`.

---

#### 🚀 Production Server

Use the production setup for deployment. It uses optimized builds and reverse proxy via NGINX.

```bash
# In the project root directory
docker compose -f docker-compose.prod.yaml up --build -d
```

* Access the full app through NGINX at: [http://localhost:8861](http://localhost)

> Stop and clean up with:

```bash
docker compose -f docker-compose.prod.yaml down
```
