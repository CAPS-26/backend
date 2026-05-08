# Backend Module

REST API backend untuk pemrosesan data satelit Aerosol Optical Depth (AOD) dan estimasi PM2.5 untuk wilayah Jakarta.

## Struktur Proyek

```bash
backend/
├── config/                   # Pengaturan aplikasi (settings.py)
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

## Menjalankan dengan Docker

Prasyarat:

- Docker 24 atau lebih baru
- Docker Compose (plugin `docker compose` atau Docker Desktop)

Setup singkat (wajib gunakan `.env`):

```bash
cp .env.example .env
# Edit .env dan isi SECRET_KEY, API keys, dan kredensial database
```

Build dan jalankan semua service:

```bash
docker compose up --build
```

API akan tersedia di http://localhost:8000. Pada boot pertama, service web dapat menjalankan migrasi database otomatis.

Mode detached:

```bash
docker compose up -d --build
```

Hentikan service:

```bash
docker compose down
```

Hentikan dan hapus volume (menghapus data database):

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
pip install uv
uv sync
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

### 4. Environment Variables (wajib di Linux)

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
| `DBHOST` | Host database (default: `db` when using the included Docker Compose, otherwise `localhost`) |
| `DBPORT` | Port database (default: `5432`) |
| `API_KEY` | Kunci API cuaca Visual Crossing |
| `USERHIMAWARI` | Nama pengguna FTP JAXA |
| `PASSHIMAWARI` | Password FTP JAXA |

### 5. Terapkan migrasi dan jalankan (via `uv`)

Jalankan migrasi database:

```bash
uv run alembic upgrade head
```

Jalankan server FastAPI (development):

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Dokumentasi API (Scalar) tersedia di http://127.0.0.1:8000/docs

Catatan operasional singkat:

- Scheduler dijalankan di level aplikasi. Job dijalankan oleh APScheduler yang dibuat pada startup aplikasi.
- Caching mendukung Redis bila dikonfigurasi, dan akan fallback ke in-memory cache bila koneksi Redis gagal.
- Prediksi time-series menggunakan model LSTM; proyek sudah menyediakan kerangka untuk model TensorFlow (.keras). Anda dapat menaruh model file di `apps/aod/features/prediction/ml_models/` dan loader akan mencoba memuatnya. Saya juga menambahkan dukungan loader untuk model PyTorch (.pt, .pth).

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
