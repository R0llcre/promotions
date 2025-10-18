# NYU DevOps - Promotion Team

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/Language-Python-blue.svg)](https://python.org/)
[![Build Status](https://github.com/CSCI-GA-2820-FA25-003/promotions/actions/workflows/workflow.yml/badge.svg)](https://github.com/CSCI-GA-2820-FA25-003/promotions/actions)
[![codecov](https://codecov.io/gh/CSCI-GA-2820-FA25-003/promotions/graph/badge.svg?token=FS7IXVUIWI)](https://codecov.io/gh/CSCI-GA-2820-FA25-003/promotions)


# Promotions Service

A small, production‑style REST API for creating, reading, updating, deleting, and querying **promotions**.

This version unifies the model query contract and clarifies ambiguous terminology:

* **Single‑item lookup** returns a **model instance or `None`**.
* **Multi‑item lookups** return a **`list` of model instances**.
* The legacy concept of *category* has been replaced with the explicit **`product_id`** filter.
* For backward compatibility, a deprecated alias `find_by_category()` still delegates to `find_by_product_id()`.


---

## Table of Contents

* [Overview](#overview)
* [Architecture](#architecture)
* [Requirements](#requirements)
* [Quick Start](#quick-start)
* [Configuration](#configuration)
* [Data Model](#data-model)
* [API Reference](#api-reference)

  * [Service Root](#service-root)
  * [List Promotions (Filters & Priority)](#list-promotions-filters--priority)
  * [Get by ID](#get-by-id)
  * [Create](#create)
  * [Update (Full Replace)](#update-full-replace)
  * [Delete](#delete)
  * [Error Responses](#error-responses)
* [Behavioral Guarantees & Validation](#behavioral-guarantees--validation)
* [Design Rationale (Why These Changes)](#design-rationale-why-these-changes)
* [Testing & Quality](#testing--quality)
* [CLI Commands](#cli-commands)
* [Project Structure](#project-structure)
* [Compatibility Notes](#compatibility-notes)
* [License](#license)

---

## Overview

The Promotions Service exposes CRUD and query endpoints for promotion records. It is implemented with **Flask** and **Flask‑SQLAlchemy**, uses **PostgreSQL** by default, and returns JSON responses.

Key features:

* **Unified query contract**: consistent return types across model methods.
* **Explicit field naming**: uses `product_id` (not “category”) for product filters.
* **Multiple list filters** with deterministic **priority** when multiple query parameters are supplied.
* **Robust validation** and **uniform error responses** for common failure scenarios.
* **High test coverage** (threshold ≥ 95%) across success and error paths.

---

## Architecture

* **Framework:** Flask
* **ORM:** Flask‑SQLAlchemy
* **Database:** PostgreSQL (psycopg driver)
* **Model:** `Promotion` with auditing fields (`created_at`, `last_updated`) stored server‑side; the REST API’s JSON only exposes core business fields.

---

## Requirements

* **Python**: 3.11+
* **PostgreSQL**: 13+ (or a compatible managed instance)
* **Tools**: `pip`, `venv` or a containerized environment (DevContainer/Docker)

---

## Quick Start

```bash
# 1) (Optional) create & activate a virtualenv
python -m venv venv
source venv/bin/activate

# 2) install dependencies
pip install -r requirements.txt

# 3) configure DB (see "Configuration" below), then create tables
flask db-create

# 4) run the service (default http://127.0.0.1:5000)
flask run

# 5) run tests (with coverage gate ≥ 95%)
make test
```

---

## Configuration

The service relies on a PostgreSQL connection string:

* **`DATABASE_URI`** (env var) – e.g.
  `postgresql+psycopg://postgres:postgres@localhost:5432/dev`

**Testing defaults** to:
`postgresql+psycopg://postgres:postgres@localhost:5432/testdb`

> Ensure your DB is reachable and that you have executed `flask db-create` to create tables.

Common Flask env vars (optional):

* `FLASK_APP` – your app entrypoint (if needed)
* `FLASK_ENV` – `development` or `production`
* `FLASK_DEBUG` – `0`/`1` for debug

---

## Data Model

`Promotion` JSON shape (fields exposed by the API):

| Field            | Type             | Required | Description                             |
| ---------------- | ---------------- | -------- | --------------------------------------- |
| `id`             | integer          | auto     | Primary key                             |
| `name`           | string (≤ 63)    | yes      | Promotion name                          |
| `promotion_type` | string (≤ 63)    | yes      | Free‑form type (e.g., “Percentage off”) |
| `value`          | integer          | yes      | Discount amount/percent (integer)       |
| `product_id`     | integer          | yes      | Associated product identifier           |
| `start_date`     | ISO date (Y‑M‑D) | yes      | Start date, e.g., `"2025-10-01"`        |
| `end_date`       | ISO date (Y‑M‑D) | yes      | End date, e.g., `"2025-10-31"`          |

**Example JSON:**

```json
{
  "id": 1,
  "name": "Summer Sale",
  "promotion_type": "Percentage off",
  "value": 25,
  "product_id": 123,
  "start_date": "2025-06-01",
  "end_date": "2025-06-30"
}
```

> The model also maintains auditing fields (`created_at`, `last_updated`) that are **not** part of the REST JSON.

---

## API Reference

**Base URL**: `/`

### Service Root

`GET /` → returns service metadata:

```json
{
  "name": "Promotions Service",
  "version": "1.0.0",
  "description": "RESTful service for managing promotions",
  "paths": { "promotions": "/promotions" }
}
```

---

### List Promotions (Filters & Priority)

`GET /promotions`

You can filter by **one** of the following query parameters. If multiple are provided, the service applies **only the highest‑priority** filter and ignores the rest:

**Priority**: `id` ▶ `name` ▶ `product_id` ▶ `promotion_type`

| Parameter                  | Type   | Behavior                  | Response shape  |
| -------------------------- | ------ | ------------------------- | --------------- |
| `?id=<int>`                | int    | Exact ID match            | `[]` or `[obj]` |
| `?name=<string>`           | string | Exact name match          | `[obj, ...]`    |
| `?product_id=<int>`        | int    | Exact product match       | `[obj, ...]`    |
| `?promotion_type=<string>` | string | Exact type match          | `[obj, ...]`    |
| *(no query)*               | —      | Return **all** promotions | `[obj, ...]`    |

**Examples**

```bash
# by type
curl -s "http://127.0.0.1:5000/promotions?promotion_type=Buy%20One%20Get%20One"

# by product_id
curl -s "http://127.0.0.1:5000/promotions?product_id=123"

# by name
curl -s "http://127.0.0.1:5000/promotions?name=NYU%20Demo"

# by id (returns [] or [obj])
curl -s "http://127.0.0.1:5000/promotions?id=42"
```

Notes:

* `product_id` accepts numbers and numeric strings (e.g., `"2222"`).
* Invalid numeric filters yield an **empty list** (not a 500).

---

### Get by ID

`GET /promotions/<id:int>`

* **200 OK** with the promotion object when found
* **404 Not Found** when the ID does not exist

---

### Create

`POST /promotions`
**Content‑Type** must be `application/json` (the server **accepts** `; charset=utf-8` etc. and validates by Flask’s parsed `mimetype`).

**Required body fields**: `name`, `promotion_type`, `value` (int), `product_id` (int), `start_date` (ISO date), `end_date` (ISO date)

**Example**

```bash
curl -s -X POST "http://127.0.0.1:5000/promotions" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "NYU Demo",
        "promotion_type": "AMOUNT_OFF",
        "value": 10,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31"
      }' -i
```

* **201 Created** with JSON body and a `Location` header pointing to `GET /promotions/<id>`
* **400 Bad Request** for invalid data types/shape (e.g., non‑int `value`)
* **415 Unsupported Media Type** if `Content-Type` is not `application/json`

---

### Update (Full Replace)

`PUT /promotions/<id:int>`
Full replacement: send a complete resource representation (same required fields as *Create*). The server enforces **ID consistency**:

* If your request body includes an `id` and it **does not match** the path `<id>`, the server returns **400 Bad Request**.
* Otherwise:

  * **200 OK** with the updated resource if found
  * **404 Not Found** if the resource does not exist

**Example**

```bash
curl -s -X PUT "http://127.0.0.1:5000/promotions/1" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "NYU Demo+",
        "promotion_type": "AMOUNT_OFF",
        "value": 15,
        "product_id": 123,
        "start_date": "2025-10-01",
        "end_date": "2025-10-31"
      }'
```

---

### Delete

`DELETE /promotions/<id:int>`

* **204 No Content** on successful deletion
* **404 Not Found** if the resource does not exist

---

### Error Responses

All errors are returned as **JSON**. Common cases:

| Scenario                           | Status                     |
| ---------------------------------- | -------------------------- |
| Missing/invalid fields or types    | 400 Bad Request            |
| Resource not found                 | 404 Not Found              |
| HTTP method not allowed on a route | 405 Method Not Allowed     |
| Wrong/absent `Content-Type`        | 415 Unsupported Media Type |
| Unhandled server exception         | 500 Internal Server Error  |

> The test suite verifies JSON error responses for 404/405/415 and simulates a 500 path via patched exceptions. The exact error object shape may be subject to your centralized error handler but is guaranteed to be JSON.

---

## Behavioral Guarantees & Validation

* **Unified query contract**

  * `Promotion.find(id)` → returns a **Promotion** or **`None`** (invalid IDs return `None`).
  * `Promotion.find_by_name(name)` / `find_by_product_id(product_id)` / `find_by_promotion_type(type)` → each returns a **`list`** (empty list if no matches or invalid filter).
* **Type rigor in deserialization**

  * `value` and `product_id` must be integers; invalid types produce **400**.
  * `start_date` and `end_date` must be ISO date strings (`YYYY‑MM‑DD`).
* **Transactional safety**

  * `create`, `update`, `delete` all wrap DB operations in try/except; on errors they roll back and emit a model‑level `DataValidationError` that the route layer translates into a 4xx error.
* **Content type check**

  * Based on Flask’s parsed `request.mimetype` rather than raw header string, so `application/json; charset=utf-8` is accepted.

---

## Design Rationale (Why These Changes)

* **Consistency & usability**: Historically, some multi‑item queries returned a SQLAlchemy `Query`, others returned a `list`, and one path (`find_by_id`) even returned a single‑element list. This inconsistency caused confusion (e.g., when to call `.count()` vs. `len()`). We standardized: **single‑item → object/None, multi‑item → list**.
* **Clarity of domain terms**: The legacy `category` name did not clearly communicate “product ID” and led to misinterpretation. We now expose **`product_id`** explicitly (with `find_by_category` kept as a deprecated alias).
* **Robustness**: Filters now tolerate numeric strings and handle invalid input by returning empty lists instead of raising exceptions.
* **Predictability**: The list endpoint defines a clear **filter priority** to avoid surprising results when multiple filters are provided.
* **Correctness & integrity**: The update route enforces **ID consistency** between the URL path and the body.

These changes reduce maintenance burden and make it safer and more intuitive to build features on top of the API.

---

## Testing & Quality

Run the full suite (unit + integration):

```bash
make test
```

Coverage gate is **≥ 95%**. The suite includes:

* Model CRUD, serialization/deserialization, and transaction rollback tests
* Query tests for `find`, `find_by_name`, `find_by_product_id`, `find_by_promotion_type`
* Route tests for all filters (`id`, `name`, `product_id`, `promotion_type`) and “no filter”
* Error‑path tests for 400/404/405/415 and a simulated 500 path (with temporary disabling of exception propagation to hit the JSON 500 handler)

---

## CLI Commands

* `flask db-create` – initialize database tables

> Ensure `DATABASE_URI` is set and reachable before running this command.

---

## Project Structure

```
service/
  __init__.py
  routes.py          # REST endpoints and filter priority
  models.py          # Promotion model + unified query contract
  common/
    status.py        # HTTP status codes
    error_handlers.py
    log_handlers.py
    cli_commands.py
tests/
  test_models.py     # Model behavior, queries, validation, exceptions
  test_routes.py     # Routes, filters, errors, 500 simulation
  test_cli_commands.py
wsgi.py              # App entry (Flask)
Makefile
requirements.txt
README.md            # This file
```

---

## Compatibility Notes

* **Deprecated**: `find_by_id(...)` (single‑element list semantics). Use `find(id)` instead.
* **Deprecated alias**: `find_by_category(...)` is kept for backward compatibility and forwards to `find_by_product_id(...)`. Prefer `find_by_product_id(...)`.
* **Legacy documentation**: Earlier docs referenced `GET /promotions?product={id}`. The correct and current form is **`GET /promotions?product_id={id}`**. This README supersedes that older reference. 

---


## CRUD  Screenshots

![Create](images/create.png)
![Read](images/read.png)
![Update](images/update.png)
![Delete](images/delete.png)

## License

Copyright (c) 2016, 2025 [John Rofrano](https://www.linkedin.com/in/JohnRofrano/). All rights reserved.

Licensed under the Apache License. See [LICENSE](LICENSE)

This repository is part of the New York University (NYU) masters class: **CSCI-GA.2820-001 DevOps and Agile Methodologies** created and taught by [John Rofrano](https://cs.nyu.edu/~rofrano/), Adjunct Instructor, NYU Courant Institute, Graduate Division, Computer Science, and NYU Stern School of Business.
