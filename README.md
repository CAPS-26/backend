# Backend Module

REST API backend untuk pemrosesan data satelit Aerosol Optical Depth (AOD) dan estimasi PM2.5 untuk wilayah Jakarta.

## Struktur Proyek

```bash
backend/
├── config/                  # Pengaturan aplikasi (settings.py)
├── apps/
│   ├── aod/                 # Domain satelit AOD
│   │   ├── models.py
│   │   └── features/
│   │       ├── ingestion/   # Fetch & proses file satelit .nc (Himawari, VIIRS)
│   │       ├── estimation/  # Estimasi spasial PM2.5 (sklearn)
│   │       ├── prediction/  # Prediksi time-series PM2.5 (LSTM)
│   │       └── api/         # Endpoint REST
│   └── weather/             # Domain cuaca & PM2.5 ground
│       ├── models.py
│       └── features/
│           ├── ingestion/   # Fetch API cuaca, crawling PM2.5
│           └── api/         # Endpoint REST
├── alembic/                 # Migrasi database (Alembic)
├── data/                    # File satelit unduhan (gitignored)
├── Dockerfile
├── docker-compose.yml
└── main.py                  # Entry point FastAPI
```

---

## Menjalankan dengan Docker (direkomendasikan)

### Prasyarat

- Docker >= 24
- Docker Compose (bundel dengan Docker Desktop atau plugin CLI `docker compose`)

### Setup

```bash
cp .env.example .env
# Edit .env dan isi SECRET_KEY, API keys, dan kredensial database
```

Build dan jalankan semua service:

```bash
docker compose up --build
```

API akan tersedia di `http://localhost:8000`.

Pada boot pertama, service `web` menjalankan migrasi database secara otomatis.

Untuk menjalankan di mode detached:

```bash
docker compose up -d --build
```

Untuk menghentikan:

```bash
docker compose down
```

Untuk menghentikan dan menghapus volume (menghapus database):

```bash
docker compose down -v
```

---

## Menjalankan Secara Lokal (tanpa Docker)

### 1. Dependensi sistem

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

### 2. Lingkungan Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e . # atau pip install -r requirements.txt jika ada
```

### 3. Database

Hubungkan ke PostgreSQL dan buat database, user, serta ekstensi yang diperlukan:

```sql
CREATE DATABASE aodproject;
CREATE USER aoduser WITH PASSWORD 'changeme';
GRANT ALL PRIVILEGES ON DATABASE aodproject TO aoduser;
ALTER ROLE aoduser WITH SUPERUSER;

\c aodproject
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_raster;
```

### 4. Environment Variables

```bash
cp .env.example .env
# Edit .env dengan nilai Anda
```

Variabel yang diperlukan:

| Variabel | Deskripsi |
| --- | --- |
| `SECRET_KEY` | Kunci rahasia aplikasi |
| `DEBUG` | `True` untuk dev lokal, `False` untuk produksi |
| `NAMEDB` | Nama database |
| `USERDB` | Pengguna database |
| `PASSDB` | Password database |
| `DBHOST` | Host database (default: `localhost`) |
| `DBPORT` | Port database (default: `5432`) |
| `API_KEY` | Kunci API cuaca Visual Crossing |
| `USERHIMAWARI` | Nama pengguna FTP JAXA |
| `PASSHIMAWARI` | Password FTP JAXA |

### 5. Terapkan migrasi dan jalankan

```bash
# Jalankan migrasi database
alembic upgrade head

# Jalankan server FastAPI (Development)
fastapi dev main.py
```

Dokumentasi API (Swagger) akan ada di `http://127.0.0.1:8000/docs`.

---

## Endpoint API (v1)

Base URL: `/api/v1`

| Method | Path | Deskripsi |
| --- | --- | --- |
| GET | `/aod/polygon/` | Polygon AOD untuk kemarin |
| POST | `/aod/polygon/by-date/` | Polygon AOD untuk tanggal tertentu |
| GET | `/aod/pm25/polygon/` | Polygon estimasi PM2.5 untuk kemarin |
| POST | `/aod/pm25/polygon/by-date/` | Polygon estimasi PM2.5 untuk tanggal tertentu |
| GET | `/weather/weather/` | Data cuaca untuk hari ini |
| POST | `/weather/weather/by-date/` | Data cuaca untuk tanggal tertentu |
| GET | `/weather/pm25/actual/` | Pembacaan PM2.5 aktual untuk hari ini |
| POST | `/weather/pm25/actual/by-date/` | Pembacaan PM2.5 aktual untuk tanggal tertentu |
| GET | `/weather/pm25/prediction/` | Prediksi PM2.5 untuk hari ini |
| POST | `/weather/pm25/prediction/by-date/` | Prediksi PM2.5 untuk tanggal tertentu |

Request body untuk endpoint AOD `by-date`: `{ "tanggal": "YYYY-MM-DD" }`

Request body untuk endpoint cuaca/PM2.5 `by-date`: `{ "date": "YYYY-MM-DD" }`
