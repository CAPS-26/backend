# Backend AOD

Django REST API backend for Aerosol Optical Depth (AOD) satellite data processing and PM2.5 estimation for the Jakarta region.

## Project Structure

```bash
backend-aod/
├── config/                  # Django project settings, urls, wsgi
├── apps/
│   ├── aod/                 # AOD satellite domain
│   │   ├── models.py
│   │   ├── migrations/
│   │   └── features/
│   │       ├── ingestion/   # Fetch & process satellite .nc files (Himawari, VIIRS)
│   │       ├── estimation/  # Spatial PM2.5 estimation (sklearn)
│   │       ├── prediction/  # Time-series PM2.5 prediction (LSTM)
│   │       └── api/         # REST endpoints
│   └── weather/             # Ground weather & PM2.5 domain
│       ├── models.py
│       ├── migrations/
│       └── features/
│           ├── ingestion/   # Weather API fetch, PM2.5 crawling
│           └── api/         # REST endpoints
├── data/                    # Downloaded satellite files (gitignored)
├── Dockerfile
├── docker-compose.yml
└── manage.py
```

---

## Running with Docker (recommended)

### Prerequisites

- Docker >= 24
- Docker Compose (bundled with Docker Desktop or `docker compose` CLI plugin)

### Setup

```bash
cp .env.example .env
# Edit .env and fill in SECRET_KEY, API keys, and database credentials
```

Build and start all services:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

On first boot the `web` service runs `migrate` automatically before starting gunicorn.

To run in detached mode:

```bash
docker compose up -d --build
```

To stop:

```bash
docker compose down
```

To stop and remove volumes (wipes the database):

```bash
docker compose down -v
```

---

## Running Locally (without Docker)

### 1. System dependencies

**Ubuntu / Debian:**

```bash
sudo apt-get update
sudo apt-get install -y \
    gdal-bin libgdal-dev \
    libgeos-dev libproj-dev \
    postgresql postgis \
    python3-dev libpq-dev gcc
```

**macOS (Homebrew):**

```bash
brew install gdal geos proj postgresql postgis
```

### 2. Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Database

Connect to PostgreSQL and create the database, user, and required extensions:

```sql
CREATE DATABASE aodproject;
CREATE USER aoduser WITH PASSWORD 'changeme';
GRANT ALL PRIVILEGES ON DATABASE aodproject TO aoduser;
ALTER ROLE aoduser WITH SUPERUSER;

\c aodproject
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_raster;
```

### 4. Environment variables

```bash
cp .env.example .env
# Edit .env with your values
```

Required variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for local dev, `False` for production |
| `NAMEDB` | Database name |
| `USERDB` | Database user |
| `PASSDB` | Database password |
| `DBHOST` | Database host (default: `127.0.0.1`) |
| `DBPORT` | Database port (default: `5432`) |
| `API_KEY` | Visual Crossing weather API key |
| `USERHIMAWARI` | JAXA FTP username |
| `PASSHIMAWARI` | JAXA FTP password |

### 5. Apply migrations and run

```bash
python manage.py migrate
python manage.py runserver
```

API docs (Swagger) will be at `http://127.0.0.1:8000/swagger/`.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/aod/polygon/` | AOD polygons for yesterday |
| POST | `/api/aod/polygon/by-date/` | AOD polygons for a given date |
| GET | `/api/aod/pm25/polygon/` | PM2.5 estimate polygons for yesterday |
| POST | `/api/aod/pm25/polygon/by-date/` | PM2.5 estimate polygons for a given date |
| GET | `/api/weather/weather/` | Weather data for today |
| POST | `/api/weather/weather/by-date/` | Weather data for a given date |
| GET | `/api/weather/pm25/actual/` | Actual PM2.5 readings for today |
| POST | `/api/weather/pm25/actual/by-date/` | Actual PM2.5 readings for a given date |
| GET | `/api/weather/pm25/prediction/` | PM2.5 predictions for today |
| POST | `/api/weather/pm25/prediction/by-date/` | PM2.5 predictions for a given date |

Request body for `by-date` AOD endpoints: `{ "tanggal": "YYYY-MM-DD" }`

Request body for `by-date` weather/PM2.5 endpoints: `{ "date": "YYYY-MM-DD" }`
