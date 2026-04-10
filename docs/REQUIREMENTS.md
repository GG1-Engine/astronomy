# Deep Sky Observatory — Requirements

This document describes the functional and technical requirements for the Deep Sky Observatory application.

---

## Purpose

A local web application for backyard astronomers to browse, search, and plan observations of deep-sky objects and solar system bodies. Designed for personal/LAN use on a Raspberry Pi.

---

## Functional Requirements

### FR-1: Deep-Sky Object Catalog
- Display ~14,000 objects from the Messier, NGC, and IC catalogs
- Each object shows: designation, common name, type, constellation, coordinates, magnitude, angular size, distance, difficulty rating, and best viewing months
- Support for object types: galaxies, globular clusters, open clusters, nebulae (emission, reflection, planetary, supernova remnant), double stars, asterisms

### FR-2: Browse
- Browse by category: tonight's sky, Messier catalog, naked-eye/binocular objects, galaxies, globular clusters, open clusters, nebulae, planetary nebulae
- Browse by constellation — all 88 IAU constellations, displayed with full names
- Constellation cards show object count, brightest magnitude, and Messier object count

### FR-3: Search & Filter
- Full-text search by designation, common name, NGC/IC/Messier number, constellation
- Filter by object type, constellation, maximum magnitude, maximum difficulty
- Sort by brightness, designation, constellation, difficulty, or angular size
- Autocomplete suggestions in the navbar search bar

### FR-4: Object Detail Pages
- Thumbnail sky image (proxied and cached from NASA SkyView/DSS)
- Interactive sky chart (Aladin Lite)
- Full object data table (coordinates, magnitude, size, distance, etc.)
- Real-time altitude and azimuth (when observer location is set)
- Rise, transit, and set times; circumpolar/never-rises indication
- Related objects (same constellation and type)
- Messier sequence neighbors (previous/next M number)

### FR-5: Solar System
- Current position, magnitude, altitude, azimuth, rise/set/transit times for all 8 planets and 2 dwarf planets (Pluto, Ceres)
- Moon phase: illumination percentage, phase name, age in days, next new/full moon
- Sun: current altitude, sky state (day/civil/nautical/astronomical twilight/night), sunrise/sunset
- Comet tracking: 7 notable comets with real-time orbital position and magnitude
- Satellite tracking: ISS, Chinese Space Station, Hubble Space Telescope
  - Live TLE data from Celestrak, refreshed every 6 hours
  - Shows altitude, azimuth, range, orbital altitude, eclipse status, pass times

### FR-6: Observer Location
- Set location by address/city search (geocoded via OpenStreetMap Nominatim) or manual coordinates
- Location persisted across sessions in `settings.json`
- Used for all altitude/azimuth calculations and rise/set times
- Can be cleared at any time

### FR-7: Image Caching
- Sky thumbnails fetched on demand from NASA SkyView and cached locally
- Two sizes: small (card grid) and large (detail page)
- Cache persists in `static/thumbcache/`; survives app restarts

---

## Non-Functional Requirements

### NFR-1: Deployment
- Runs on a Raspberry Pi 4 (ARM64, Raspberry Pi OS)
- Single-user, local network access — no authentication required
- Starts with `python3 app.py`; no containerization needed

### NFR-2: Dependencies
- Python 3.10+
- Flask 3.1.x (web framework)
- ephem 4.2.x (PyEphem — astronomical calculations for solar system bodies)
- SQLite (stdlib — no external database server)
- Bootstrap 5.3.3 (CDN) — responsive dark-theme UI
- Aladin Lite (CDN) — interactive sky viewer

### NFR-3: Data
- Object catalog: [OpenNGC](https://github.com/mattiaverga/OpenNGC) by Mattia Verga (CC BY-SA 4.0)
- Sky images: NASA SkyView / Digitized Sky Survey (DSS2)
- Satellite TLEs: Celestrak NORAD catalog
- Geocoding: OpenStreetMap Nominatim

### NFR-4: Performance
- Page loads should complete in under 2 seconds on LAN
- Database queries use pre-computed indexes and views for fast filtering
- Thumbnail fetching is asynchronous on first view; subsequent loads serve from cache

### NFR-5: Testing
- Unit tests cover core astronomical calculation functions (`calc_altaz`, `transit_info`)
- Unit tests cover the data enrichment pipeline (`enrich`)
- Unit tests validate constellation name mapping completeness
- CI runs the full test suite on every push via GitHub Actions

---

## Future Feature Candidates

These are not currently implemented but represent natural extensions:

| Feature | Notes |
|---------|-------|
| Observation log | Record personal sightings with date, scope, seeing conditions, notes |
| "Best tonight" ranking | Score objects by current altitude × brightness × season |
| Observing list export | Print-friendly PDF or plain-text list |
| Additional comets | Pull live elements from Minor Planet Center |
| More satellites | Add additional tracked objects (Tiangong modules, etc.) |
| systemd service | Auto-start on Pi boot |
| Local domain | Access as `observatory.local` via mDNS |
