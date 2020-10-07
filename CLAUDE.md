# Delivery — project notes for Claude

## What this project is

Flask REST API backend for a delivery route optimization system. External dispatch clients push stocks, orders, and couriers via HTTP; the service stores them in PostgreSQL, keeps a pairwise distance matrix up to date, and feeds a pluggable optimizer that runs as a background process inside the container.

## Project structure

```
Delivery/
├── requirements.txt               # Python dependencies (unpinned — should be pinned)
├── ci/
│   ├── Dockerfile                 # Multi-stage: python38 → python38-uwsgi, nginx
│   ├── docker-compose.yml         # Services: backend, postgres, nginx
│   ├── start.sh                   # Container entrypoint: runs prestart.sh then uWSGI
│   ├── wait_for_port.sh           # Waits for a TCP port before running a command
│   └── ansible/
│       ├── ansible.cfg
│       ├── requirements.yml
│       ├── inventories/production/
│       │   ├── hosts.yml
│       │   └── group_vars/all.yml
│       ├── playbooks/main.yml
│       └── roles/
│           ├── common_setup/      # Creates config dir on remote
│           ├── docker/            # Installs Docker CE + docker-compose
│           ├── deploy_files/      # Syncs ci/, src/, requirements.txt via rsync
│           ├── prepare_host/      # Env files, optional Certbot/Let's Encrypt
│           ├── postgres/          # Starts postgres container
│           ├── backend/           # Starts backend container
│           ├── nginx/             # Deploys nginx config + starts container
│           ├── start_service/     # Shared: docker-compose up for a given service
│           └── create_reload_script/ # Creates /usr/bin/reload-docker-nginx
└── src/
    ├── jwt_generator/
    │   └── generate_jwt_token.py  # Dev utility: signs a JWT with local RSA key
    └── backend/                   # PYTHONPATH root inside container (/src/app)
        ├── main.py                # Flask app: route definitions, error handlers
        ├── prestart.sh            # Runs at container start: create_db, migrate, resolver daemon
        ├── uwsgi.ini              # uWSGI config: socket :3031, module main:main
        ├── api/
        │   ├── admin.py           # Flask-Admin for reference tables
        │   ├── data_models.py     # Pydantic input models with validation
        │   ├── exceptions.py      # Custom HTTP exceptions (JWT, 400, 404, 500)
        │   ├── api_handlers/
        │   │   ├── couriers_handlers.py
        │   │   ├── deliveries_handlers.py
        │   │   ├── distance_handlers.py   # calculate_distance, validate_obj_type
        │   │   ├── orders_handlers.py
        │   │   ├── points_handlers.py     # /next, /go, /ungo logic (partially mocked)
        │   │   └── stocks_handlers.py
        │   └── utils/
        │       ├── http_response_helpers.py  # @success_result, @error_result decorators
        │       └── jwt_token_helpers.py      # @jwt_required, validate_and_decode_token
        ├── common/
        │   └── sentry.py          # init_sentry_client(), get_logger()
        ├── db/
        │   ├── db_engine.py       # Engine singleton (reads POSTGRES_* env vars)
        │   ├── db_requests.py     # Typed query helpers (get_order_by_id, etc.)
        │   ├── db_actions.py      # CLI: create_db | make_migrations | migrate
        │   ├── models.py          # SQLAlchemy ORM models
        │   ├── utils.py           # session_scope(), migration helpers
        │   └── dbmigrations/      # Alembic env + versions/
        └── resolver/
            ├── resolvers.py       # BaseResolver ABC + MockedResolved stub
            └── main.py            # do_resolve_cycle(), insert_to_queue(); runs as daemon
```

## API endpoints

| Method | Path | Handler | Description |
|---|---|---|---|
| GET/POST/DELETE | `/stocks` | `stocks_handlers` | Warehouse CRUD |
| GET/POST/DELETE | `/orders` | `orders_handlers` | Order CRUD |
| GET/POST/DELETE | `/couriers` | `couriers_handlers` | Courier CRUD |
| POST | `/delivered` | `deliveries_handlers` | Mark orders done; detach courier |
| POST | `/undeliver` | `deliveries_handlers` | Cancel delivery |
| POST | `/next` | `points_handlers` | Preview next free order (no assignment) |
| POST | `/go` | `points_handlers` | Assign next free order to courier |
| POST | `/ungo` | `points_handlers` | Revert courier to previous order |
| GET | `/debug/<result>` | `main.py` | Debug only (`DEBUG_ENDPOINTS=true`) |
| any | `/admin` | `admin.py` | Flask-Admin for reference data |

All routes use `@jwt_required` (RS256 token in `JWT` cookie) plus `@success_result` / `@error_result` decorators that wrap the response envelope.

## DB models

- **Break** — `breaks`: `id`, `start` Time, `end` Time
- **Hours** — `hours`: `id`, `start` Time, `end` Time
- **Location** — `locations`: `id`, `latitude` Float, `longtitude` Float (typo in column name — keep as-is)
- **StockType** — `stock_types`: `id`, `type` String
- **Stock** — `stocks`: `id`, `geozone_id`, `assembly_time`, FK→StockType, FK→Hours, FK→Location, M2M breaks via `stocks_breaks`
- **SpeedBonus** — `speed_bonuses`: `id`, `type` String, `value` Integer
- **DelayPenalty** — `delay_penalties`: `id`, `type` String, `value` Integer
- **Order** — `orders`: `id`, FK→Location, `weight`, `price`, `geozone_id`, FK→Hours(delivery_time), FK→SpeedBonus + `speed_bonus_value`, FK→DelayPenalty + `delay_penalty_value`, `is_urgent` Boolean, `issue_time`, `outsource_price`, FK→Courier, `is_done` Boolean
- **TransportType** — `transport_types`: `id`, `type` String
- **Courier** — `couriers`: `id`, FK→Location (nullable), FK→TransportType, `max_capacity`, `max_price`, `avg_speed`, FK→Hours, M2M breaks via `couriers_breaks`, `geozone_id`, `hour_price`, `km_price`, `start_price`, one-to-one→Order, `previous_order_id` (mock field, remove when real resolver is in place)
- **Distance** — `distances`: `id`, `obj_id_1`, `obj_id_2`, `obj_type_1`/`obj_type_2` Enum(stock|courier|order), `timestamp` DateTime, `distance` Float
- **Solution** — `solutions`: `id`, `solution` PickleType, `resolver_name`, `timestamp`, `generated_action` Enum(initial|insert|improvement)
- **Queue** — `queue`: `id`, `obj_id`, `obj_type` Enum(stock|courier|order)

## Key patterns

**Upsert on POST**: handlers check if the ID already exists and update; otherwise insert. After create or location-change, recalculates distances to all existing objects and inserts the object into the resolver queue.

**Distance matrix**: `distance_handlers.calculate_distance` computes Euclidean distance (placeholder — not real geo distance) from the changed object to all existing objects of all three types and stores rows in `distances`.

**Resolver loop**: `resolver/main.py` runs in a `while True` loop (daemon via `prestart.sh`). Reads `Queue`, calls `insert_points` and `improve_solution` on each registered resolver in a separate thread guarded by a per-resolver file lock (`/tmp/<name>.lock`). Currently only `MockedResolved` is registered — the real optimizer is not implemented.

**Reference data** (StockType, SpeedBonus, DelayPenalty, TransportType): populated via Flask-Admin or direct DB insert. Validators in `data_models.py` query these tables at request time.

**Logging**: via `common.sentry.get_logger(name)`. Level is WARNING in production, DEBUG otherwise. Sentry integration on Flask.

## Environment variables

| Variable | Used in | Notes |
|---|---|---|
| `POSTGRES_*` (USER, PASSWORD, DB, HOST) | `db_engine.py` | Required |
| `JWT_PUBLIC_KEY` | `jwt_token_helpers.py` | RS256 PEM public key |
| `UWSGI_PROCESSES` | `start.sh` | Default 2 |
| `SENTRY_DSN` | `sentry.py` | Optional |
| `SENTRY_DISABLED` | `sentry.py` | Set to `True` to skip init |
| `DEBUG_ENDPOINTS` | `main.py` | Set to `true` for `/debug/*` |
| `DEPLOY_ENVIRONMENT` | `sentry.py`, `main.py` | `production` → WARNING logs |
| `PYTHONPATH` | Docker | Set to `/src/app` (= `src/backend/`) |

## Key dependencies

| Package | Purpose |
|---|---|
| flask | Web framework |
| flask-admin | Admin UI for reference data |
| flask-api | HTTP status constants |
| flask-cors | CORS headers |
| pyjwt | JWT encode/decode (RS256) |
| SQLAlchemy | ORM |
| alembic | DB migrations |
| pydantic | Request validation |
| psycopg2-binary | PostgreSQL driver |
| sentry-sdk[flask] | Error tracking |
| uwsgi | WSGI server |
| webargs | (present in requirements but unused in current code) |
| flasgger | (present in requirements but unused in current code) |

All packages in `requirements.txt` are **unpinned** — versions should be pinned.

## Known tech debt

- `resolver/resolvers.py`: only `MockedResolved` exists — the real optimizer is not implemented.
- `points_handlers.py`: `_get_next_free_order` and `_get_previous_order_of_courier` are mocked (return first free order, no routing logic).
- `distance_handlers.py`: distance is Euclidean on lat/lon floats, not real geodesic distance.
- `Courier.previous_order_id`: temporary mock field; remove when real resolver provides route history.
- `Solution.solution`: stored as `PickleType` — unsafe for deserialization from untrusted sources.
- `generate_jwt_token.py`: calls `jwt_token.decode('utf-8')` which fails on PyJWT ≥ 2.0 (encode returns str, not bytes).
- `requirements.txt`: no pinned versions.
