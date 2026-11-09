# Khel Club – Backend (v0_backend)

Flask and SQLAlchemy backend service for the Khel Club tournament management system.

## Overview

This repository provides match operations, scoring endpoints, tournament progression, and Walkover outcome management for Khel Club pickleball tournaments.

## Features

- **Match & Tournament Management**: Full lifecycle management of pool-stage (Round Robin) and bracket (Knockout) tournaments.
- **Walkover Outcome Support**:
  - `POST /declare-walkover` endpoint to declare a participant winner by walkover without numerical score fabrication.
  - Decoupled `result_type` (`regular`, `walkover`) and `is_walkover` boolean metadata.
  - Finalized matches are immutable; attempts to modify finalized matches without explicit authorization are rejected.
  - Automatic progression of Walkover winners into successor knockout matches.
  - Robust schema-compatible knockout bracket generation using standard SQL `NULL` for unassigned participants.
- **Real-Time Score Updates**: WebSocket events via Flask-SocketIO (`/scores` namespace).

## Database Configuration

MySQL is used as the primary database.

Copy `.env.example` to `.env` and set your credentials:

```bash
cp .env.example .env
```

`.env` template:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=khelclub_db
```

### Database Migration

Ensure the `result_type` and `is_walkover` columns are present on the `match` table:

```sql
ALTER TABLE `match`
ADD COLUMN `result_type` VARCHAR(20) NOT NULL DEFAULT 'regular',
ADD COLUMN `is_walkover` TINYINT(1) NOT NULL DEFAULT 0;
```

Or run the Python migration script:

```bash
python migrations/bul/add_walkover_columns.py
```

## Setup & Running

1. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the development server**:
   ```bash
   python app.py
   ```
   Server runs on `http://localhost:5001`.

## Testing

Run the automated unittest suite:

```bash
./venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

Result: 23 passing tests covering scoring, walkovers, duplicate prevention, and knockout bracket progression.

## Tech Stack

- Python 3.10+
- Flask
- Flask-SQLAlchemy / SQLAlchemy 2.x
- Flask-SocketIO & Gevent
- MySQL
