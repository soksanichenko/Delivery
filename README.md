# Delivery

Backend service for delivery route optimization. Manages warehouses (stocks), orders, and couriers; keeps pairwise distances up to date; feeds a pluggable route optimizer via a queue-based background process.

## API

All endpoints require a `JWT` cookie containing a valid RS256-signed token.

Response envelope:
```json
{"status": "success|error", "result": <payload>, "timestamp": <unix>}
```

### Stocks

| Method | Path | Body | Description |
|---|---|---|---|
| `GET` | `/stocks` | — | List all warehouses |
| `POST` | `/stocks` | `[Stock, …]` | Create or update warehouses (upsert by `id`) |
| `DELETE` | `/stocks` | `[{"id": N}, …]` | Delete warehouses by ID |

### Orders

| Method | Path | Body | Description |
|---|---|---|---|
| `GET` | `/orders` | — | List all orders |
| `POST` | `/orders` | `[Order, …]` | Create or update orders (upsert by `id`) |
| `DELETE` | `/orders` | `[{"id": N}, …]` | Delete orders by ID |

### Couriers

| Method | Path | Body | Description |
|---|---|---|---|
| `GET` | `/couriers` | — | List all couriers |
| `POST` | `/couriers` | `[Courier, …]` | Create or update couriers (upsert by `id`) |
| `DELETE` | `/couriers` | `[{"id": N}, …]` | Delete couriers by ID |

### Delivery lifecycle

| Method | Path | Body | Description |
|---|---|---|---|
| `POST` | `/delivered` | `[{"id": N}, …]` | Mark orders as delivered; detaches courier, sets `is_done=true` |
| `POST` | `/undeliver` | `[{"id": N}, …]` | Cancel delivery; sets `is_done=false` |
| `POST` | `/next` | `{"id": N}` | Preview next free order for a courier (no assignment) |
| `POST` | `/go` | `{"id": N}` | Assign next free order to a courier |
| `POST` | `/ungo` | `{"id": N}` | Revert courier to their previous order assignment |

### Admin

Flask-Admin UI at `/admin` (JWT-protected). Provides CRUD for reference data: `StockType`, `SpeedBonus`, `DelayPenalty`, `TransportType`.

## Request schemas

### Stock
```json
{
  "id": 1,
  "location": {"lat": 55.75, "lon": 37.61},
  "geozone_id": 1,
  "hours": {"start": "09:00", "end": "18:00"},
  "breaks": [{"start": "13:00", "end": "14:00"}],
  "assembly_time": 15,
  "type": "<stock_type>"
}
```

### Order
```json
{
  "id": 1,
  "location": {"lat": 55.75, "lon": 37.61},
  "geozone_id": 1,
  "weight": 5,
  "price": 1000,
  "delivery_time": {"start": "10:00", "end": "12:00"},
  "speed_bonus": "<bonus_type> or integer",
  "delay_penalty": "<penalty_type> or integer",
  "is_urgent": null,
  "issue_time": 30,
  "outsource_price": null,
  "courier_id": null
}
```

`delivery_time` and `is_urgent` are mutually exclusive — provide exactly one, or neither.

### Courier
```json
{
  "id": 1,
  "location": {"lat": 55.75, "lon": 37.61},
  "transport_type": "<transport_type>",
  "max_capacity": 100,
  "max_price": 5000,
  "avg_speed": 60,
  "hours": {"start": "08:00", "end": "20:00"},
  "breaks": [],
  "geozone_id": 1,
  "hour_price": 200,
  "km_price": 15,
  "start_price": 100,
  "order_id": null
}
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `POSTGRES_USER` | PostgreSQL username | — |
| `POSTGRES_PASSWORD` | PostgreSQL password | — |
| `POSTGRES_DB` | PostgreSQL database name | — |
| `POSTGRES_HOST` | PostgreSQL host | — |
| `JWT_PUBLIC_KEY` | RS256 public key for token verification | — |
| `UWSGI_PROCESSES` | uWSGI worker count | `2` |
| `SENTRY_DSN` | Sentry project DSN | — |
| `SENTRY_DISABLED` | Set to `True` to disable Sentry | — |
| `DEBUG_ENDPOINTS` | Set to `true` to enable `/debug/*` | — |
| `DEPLOY_ENVIRONMENT` | Environment name; `production` → log level WARNING | — |

## Requirements

- Python 3
- PostgreSQL 12+
- Docker and Docker Compose

## Running locally

```bash
cd ci
docker-compose up -d
```

The container runs `prestart.sh` on start: creates the DB if needed, applies migrations, then launches the background resolver process and uWSGI on port 3031.

## Database migrations

Commands run inside the container or with `PYTHONPATH=src/backend/`:

```bash
# Create a new migration
python db/db_actions.py make_migrations -m "description"

# Apply all pending migrations
python db/db_actions.py migrate

# Migrate to a specific revision
python db/db_actions.py migrate -r <revision>
```

## JWT token generation

```bash
# Requires jwtRS256.key and jwtRS256.key.pub in the working directory
cd src/jwt_generator
python generate_jwt_token.py
```

## Deployment

```bash
cd ci/ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook playbooks/main.yml
```

Configure `inventories/production/hosts.yml` and `inventories/production/group_vars/all.yml` before running.

Roles in execution order: `common_setup` → `docker` → `deploy_files` → `prepare_host` → `postgres` → `backend` → `nginx`. SSL via Let's Encrypt is optional (`obtain_letsencrypt_certs: true` in group_vars).
