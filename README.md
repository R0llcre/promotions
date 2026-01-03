# Promotions Service

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Language-Python-blue.svg)](https://python.org/)
[![Build Status](https://github.com/CSCI-GA-2820-FA25-003/promotions/actions/workflows/workflow.yml/badge.svg)](https://github.com/CSCI-GA-2820-FA25-003/promotions/actions)
[![codecov](https://codecov.io/gh/CSCI-GA-2820-FA25-003/promotions/graph/badge.svg?token=FS7IXVUIWI)](https://codecov.io/gh/CSCI-GA-2820-FA25-003/promotions)

A production-style REST API for managing promotions, built with Python and Flask.

This service provides a robust and consistent API for CRUD operations and querying of promotion records. It emphasizes clear and explicit API design, moving away from ambiguous legacy concepts.

## UI Screenshots
![Demo Animation](images/demo.gif)


## Key Features

### Backend & API
*   **Predictable API**: Easy to integrate with consistent behavior and clear filtering.
*   **Data Integrity**: Ensures valid data entry and reliable, atomic transactions.
*   **Flexible Management**: Safely deactivate promotions while preserving history.
*   **High Availability**: Designed for robust operation in cloud environments.

### Modern Web UI
*   **Interactive Dashboard**: Real-time statistics with gradient cards showing active promotions, expiring campaigns, and type distribution charts (Chart.js).
*   **Dual View Modes**: Seamlessly switch between table view and modern card gallery view.
*   **Card Gallery View**: Responsive grid layout with image previews, hover animations, and intuitive action buttons.
*   **Advanced Filtering**: Multi-level filtering system with search, status pills, type dropdowns, and product ID filters.
*   **Responsive Design**: Bootstrap 5-powered UI optimized for desktop and mobile devices.

## Technology Stack

*   **Backend**: Python, Flask, Flask-SQLAlchemy
*   **Frontend**: Bootstrap 5, Vanilla JavaScript (ES6 Modules), Chart.js, Font Awesome
*   **Database**: PostgreSQL
*   **Containerization**: Docker
*   **CI/CD**: GitHub Actions, Tekton Pipelines (OpenShift)
*   **Testing**: PyTest, Behave, Codecov

## Quick Start

1.  **Open in VS Code DevContainer**:
    *   Open the Command Palette (Ctrl+Shift+P or Cmd+Shift+P) and select "Dev Containers: Reopen in Container".
    *   This will build the development container and open the project inside it, with all necessary dependencies pre-installed.

2.  **Initialize the database**:
    ```bash
    # Create database tables
    flask db-create

    # Load sample data for testing(optional)
    flask load-data
    ```
    
3.  **Run the server**:
    ```bash
    flask run
    ```
    The service will be available at `http://127.0.0.1:8080` by default.

4.  **Check syntax**:
    ```bash
    make lint
    ```

5.  **Run tests**:
    ```bash
    make test
    ```
6.  **Run BDD tests**:
    ```bash
    behave
    ```

## Kubernetes Deployment

Deploy to a local K3D/K3S cluster:

```bash
# Create K3S cluster with registry
make cluster

# Build Docker image
make build

# Push image to registry
make push

# Deploy to Kubernetes
make deploy
```

Verify deployment:
```bash
curl -H "Host: promotions.local" http://localhost:8080/health
```

For detailed instructions, see [Deployment Guide](docs/DEPLOYMENT.md).

## API & Swagger

- **Base path:** All REST endpoints are prefixed with `/api` (e.g., `/api/promotions`).
- **Swagger UI:** Available at `/apidocs/` when the service is running (e.g., http://localhost:8080/apidocs/).
- **Common examples:**
  ```bash
  # List promotions
  curl http://localhost:8080/api/promotions

  # Create a promotion
  curl -X POST http://localhost:8080/api/promotions \
    -H "Content-Type: application/json" \
    -d '{"name":"Black Friday","promotion_type":"PERCENT","value":25,"product_id":123,"start_date":"2025-11-01","end_date":"2025-11-30"}'
  ```

## Web UI Features

Access the web interface at `http://localhost:8080/` to explore:

### Dashboard Statistics
*   **Active Promotions Card**: Track currently running campaigns with gradient background
*   **Expiring Soon Card**: Monitor promotions ending within 7 days
*   **Type Distribution Chart**: Visual breakdown of promotion types using Chart.js doughnut chart

### View Modes
*   **Table View**: Classic data table with sortable columns and inline actions
*   **Card Gallery View**: Modern card-based layout featuring:
    *   Image preview support (optional `img_url` field)
    *   Responsive grid layout (auto-adjusts to screen size)
    *   Hover effects with smooth animations
    *   Action buttons (Edit, Deactivate, Delete) appearing on hover
    *   Date range badges and status indicators

### Filtering & Search
*   **Search Bar**: Full-text search across promotion names
*   **Status Pills**: Quick filter by All / Active / Inactive
*   **Type Dropdown**: Filter by PERCENT / DISCOUNT / BOGO
*   **Product ID Filter**: Search by specific product
*   **Results Counter**: Real-time count of filtered promotions

### CRUD Operations
All operations available through intuitive modals:
*   **Create**: Add new promotions with validation
*   **Update**: Edit existing promotions
*   **Deactivate**: Soft-delete with confirmation
*   **Delete**: Permanent removal with warning

---

## Documentation

* [Architecture](docs/ARCHITECTURE.md)
* [API Reference](docs/API.md)
* [Deployment Guide](docs/DEPLOYMENT.md)
* [Minikube Guide](docs/MINIKUBE.md)
* [Testing Guide](docs/TESTING.md)
* [CI Commands](docs/CI.md)


---

## Project Structure

```
.
├── docs/               # Project documentation (Architecture, API, Deployment, etc.)
├── features/           # BDD scenarios and steps (Behave)
├── k8s/                # Kubernetes manifests (Deployment, Service, Ingress, DB)
├── scripts/            # DevOps helper scripts
├── service/            # Application source code
│   ├── common/         # Shared utilities (logs, error handlers)
│   ├── models.py       # Database models
│   ├── routes.py       # API endpoints
│   └── static/         # Frontend assets
│       ├── index.html  # Main web UI (Dashboard, Card/Table views)
│       ├── css/        # Custom styles (card view, filters, animations)
│       └── js/         # ES6 modules (app.js, ui.js, api.js, utils.js)
├── tests/              # Unit and integration tests (Pytest)
├── .tekton/            # Tekton CI/CD pipeline definitions
├── check_syntax.py     # Syntax checker script
├── Dockerfile          # Container definition
├── Makefile            # Command automation
└── wsgi.py             # WSGI entry point
```

## License

Copyright (c) 2016, 2025 [John Rofrano](https://www.linkedin.com/in/JohnRofrano/). All rights reserved.


Licensed under the Apache License. See [LICENSE](LICENSE)

This repository is part of the New York University (NYU) masters class: **CSCI-GA.2820-001 DevOps and Agile Methodologies** created and taught by [John Rofrano](https://cs.nyu.edu/~rofrano/), Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.
