# Deep Sky Observatory

A Flask web app for backyard astronomers to browse, search, and plan observations of ~14,000 deep-sky objects from the Messier, NGC, and IC catalogs. Designed for local/LAN deployment on a Raspberry Pi.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Flask](https://img.shields.io/badge/flask-3.1-green) ![SQLite](https://img.shields.io/badge/database-SQLite-lightgrey)

## Features

- Browse and search ~14,000 deep-sky objects (galaxies, nebulae, star clusters, and more)
- Real-time altitude/azimuth calculations based on your location
- Rise/set times and transit info for any object
- Solar system tracking (planets, dwarf planets, Moon phases) via PyEphem
- NASA SkyView thumbnail images with local caching
- Filter by constellation, object type, magnitude, and difficulty
- Observer location stored locally — set by address or coordinates

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/GG1-Engine/astronomy.git
   cd astronomy
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Build the database** (downloads OpenNGC catalog and compiles ~14,000 objects)
   ```bash
   python3 build_db.py
   ```

4. **Run the app**
   ```bash
   python3 app.py
   ```
   Open your browser to `http://localhost:5050`

## Architecture

| File | Role |
|------|------|
| `app.py` | Flask routes, alt/az calculations, search/filter logic, image proxy |
| `build_db.py` | One-time DB builder — parses OpenNGC CSV into SQLite |
| `solar_system.py` | PyEphem wrapper for planets, Moon, and dwarf planets |
| `templates/` | Jinja2 HTML templates |
| `static/` | CSS and Aladin Lite sky viewer |

The database (`astronomy.db`) is generated locally and not stored in the repo. It uses **SQLite** — no database server required.

## Data Source

Object catalog from [OpenNGC](https://github.com/mattiaverga/OpenNGC) by Mattia Verga, licensed under CC BY-SA 4.0.
