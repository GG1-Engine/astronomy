# Changelog

All notable changes to Deep Sky Observatory are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- **Solar System page** (`/solar-system`) — unified view of planets, satellites, and comets
- **Comet tracking** — 7 notable/historical comets with orbital elements, real-time position and magnitude via PyEphem
  - 1P/Halley, 2P/Encke, 9P/Tempel 1, 17P/Holmes, 67P/Churyumov-Gerasimenko, C/1995 O1 (Hale-Bopp), C/2020 F3 (NEOWISE)
- **Satellite tracking** — ISS, Chinese Space Station (Tiangong), and Hubble Space Telescope
  - Live TLE data fetched from Celestrak every 6 hours, with fallback to cached elements
  - Shows altitude, azimuth, range, orbital altitude, rise/set/transit times, eclipse status
- **Solar System nav link** in top navigation bar
- **Automated tests** — 30 unit tests covering `calc_altaz`, `transit_info`, `enrich`, and constellation name mapping (`tests/test_calculations.py`)
- **GitHub Actions CI** — tests run automatically on every push to `main` (`.github/workflows/tests.yml`)
- **`requirements.txt`** — pinned dependencies for reproducible installs
- **`README.md`** — setup instructions, architecture overview, and data source attribution
- **Full constellation names** — all 88 IAU 3-letter abbreviations now display as full names (e.g., "Ori" → "Orion") throughout browse, search, and object detail pages

### Changed
- Constellation filter dropdown in search now shows full names while preserving abbreviation values for DB queries
- Browse by constellation cards show full constellation name instead of 3-letter code

---

## [1.0.0] — 2026-04-09

### Added
- Initial release: Flask web app for browsing ~14,000 deep-sky objects
- SQLite database built from OpenNGC catalog (Messier, NGC, IC)
- Browse by category: tonight's sky, Messier, galaxies, globulars, open clusters, nebulae, planetary nebulae
- Browse by constellation (all 88 IAU constellations)
- Full-text search with filters (type, constellation, magnitude, difficulty)
- Object detail pages with sky image, coordinates, observing notes, related objects
- Real-time altitude/azimuth calculation from observer coordinates
- Rise/set/transit times and circumpolar/never-rises detection
- NASA SkyView thumbnail images with local cache
- Observer location stored in `settings.json` (geocoding via OpenStreetMap Nominatim)
- Responsive Bootstrap 5.3 dark theme UI
- Aladin Lite interactive sky viewer on object pages
- Random object feature
- 7 pre-computed SQL views and 8 indexes for fast queries
- PyEphem solar system data (planets, dwarf planets, Moon, Sun)
