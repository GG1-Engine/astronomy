# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Deep Sky Observatory** — a Flask web application for backyard astronomers to browse, search, and plan observations of deep-sky objects (~14,000 entries from Messier, NGC, and IC catalogs). Intended for local/LAN deployment (originally on a Raspberry Pi).

## Running the App

```bash
cd /home/coverman/astronomy
python3 app.py
# Starts on http://0.0.0.0:5050
```

## Database Setup

The SQLite database (`astronomy.db`) is built from the OpenNGC CSV catalog:

```bash
python3 build_db.py
# Downloads NGC.csv + addendum.csv, builds astronomy.db (~4.5MB, ~14k objects)
```

Query the database directly:
```bash
sqlite3 astronomy.db
```

## Architecture

| File | Role |
|------|------|
| `app.py` | Flask routes, altitude/azimuth calculations, image proxy, search/filter logic |
| `build_db.py` | One-time DB builder — parses OpenNGC CSV, computes derived fields |
| `solar_system.py` | PyEphem wrapper for planets, dwarf planets, asteroids, moon phases |
| `settings.json` | Persisted observer location (lat/lon/place name) |
| `static/thumbcache/` | Cached NASA SkyView JPEG images (lazy-fetched on first view) |
| `templates/` | Jinja2 templates; `base.html` defines layout, navbar, location modal |

**Key data flow:** User request → Flask route in `app.py` → SQLite query (`astronomy.db`) → optional astronomical calculation (`calc_altaz`, `transit_info`) → Jinja2 render

**API endpoints** (JSON, called by frontend JS):
- `/api/autocomplete` — search suggestions
- `/api/thumb/<slug>` — proxies/caches NASA SkyView images
- `/api/altaz` — real-time altitude/azimuth for an object given observer coords
- `/api/geocode` — address → lat/lon via OpenStreetMap Nominatim
- `/api/location` — read/write observer location to `settings.json`
- `/api/stats` — catalog statistics

## Astronomical Calculations (app.py)

All calculations are hand-rolled (no astropy dependency):
- `calc_altaz(ra_deg, dec_deg, lat, lon, dt)` — RA/Dec → Alt/Az via Julian Date + Local Sidereal Time
- `transit_info(ra_deg, dec_deg, lat, lon, dt)` — rise/set azimuths, circumpolar/never-rises detection
- Solar system bodies use **PyEphem** via `solar_system.py`

## Database Schema Notes

- `objects` table: 30+ columns including `difficulty` (1–5 based on magnitude), `best_months` (computed from RA), `min_aperture_mm`, `distance_ly`
- 7 pre-computed views: `messier_objects`, `galaxies`, `star_clusters`, `nebulae`, `showpieces`, `seasonal_targets`, `challenging_objects`
- 8 indexes on commonly filtered columns

## Dependencies

```
Flask==3.1.1
ephem==4.2.1   # PyEphem — planetary/lunar calculations
sqlite3        # stdlib
```

Bootstrap 5.3.3 and Aladin Lite sky viewer are loaded from CDN/local static files.

## User Location

Observer location is stored in `settings.json` as `{latitude, longitude, place_name}`. The frontend location modal supports geocoding via OpenStreetMap Nominatim or manual coordinate entry. Location is used for real-time alt/az calculations and solar system rise/set times.
