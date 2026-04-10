"""
solar_system.py — Dynamic solar system object data using PyEphem.

Provides current positions, magnitudes, phase, and observer-specific
altitude/azimuth for planets, dwarf planets, notable small bodies,
comets, and Earth-orbiting satellites (ISS etc.) via live TLE data.
"""

import math
import datetime
import os
import json
import time
import urllib.request
import ephem

# ── Static encyclopedic data ──────────────────────────────────────────────────

PLANETS = {
    "Mercury": {
        "type":        "Terrestrial Planet",
        "symbol":      "☿",
        "order":       1,
        "diameter_km": 4879,
        "mass_kg":     3.285e23,
        "moons":       0,
        "day_hours":   1407.6,
        "year_days":   87.97,
        "distance_au": 0.387,
        "description": (
            "The smallest planet and closest to the Sun. Mercury has no atmosphere "
            "to retain heat, causing extreme temperature swings from −180 °C at night "
            "to 430 °C in the day. Only visible near the horizon at dusk or dawn."
        ),
        "observer_notes": (
            "Best seen within an hour of sunset (evening star) or sunrise (morning star). "
            "Never far from the Sun — max elongation ~28°. Shows phases like the Moon. "
            "Small angular size; use 100× or more to see the gibbous/crescent phase."
        ),
        "surface":     "Rocky, heavily cratered, no atmosphere",
        "composition": "Iron core (~85% of radius), silicate mantle",
        "color":       "warning",
    },
    "Venus": {
        "type":        "Terrestrial Planet",
        "symbol":      "♀",
        "order":       2,
        "diameter_km": 12104,
        "mass_kg":     4.867e24,
        "moons":       0,
        "day_hours":   -5832.0,   # retrograde
        "year_days":   224.7,
        "distance_au": 0.723,
        "description": (
            "The brightest natural object in the night sky after the Moon. Venus is "
            "shrouded in thick clouds of sulfuric acid and has a runaway greenhouse "
            "effect — surface temperature is ~465 °C. Rotates retrograde (backwards)."
        ),
        "observer_notes": (
            "Brilliant naked-eye object; can cast shadows at its brightest (mag −4.9). "
            "Shows dramatic phases — a thin crescent Venus is actually larger and "
            "brighter than full-phase Venus because it's closer to Earth. "
            "Max elongation ~47°. Never visible at midnight."
        ),
        "surface":     "Hot volcanic plains, clouds of H₂SO₄",
        "composition": "Silicate rock, CO₂ atmosphere (96.5%)",
        "color":       "light",
    },
    "Mars": {
        "type":        "Terrestrial Planet",
        "symbol":      "♂",
        "order":       4,
        "diameter_km": 6779,
        "mass_kg":     6.39e23,
        "moons":       2,
        "day_hours":   24.62,
        "year_days":   686.97,
        "distance_au": 1.524,
        "description": (
            "The Red Planet — rusty iron oxide dust gives it its distinctive color. "
            "Mars has the largest volcano (Olympus Mons) and longest canyon (Valles "
            "Marineris) in the solar system. Thin CO₂ atmosphere, polar ice caps."
        ),
        "observer_notes": (
            "Brightness varies enormously — mag −3 at opposition to +1.7 at aphelion. "
            "Opposition every ~26 months. Surface features (dark patches, polar caps) "
            "visible in 4\"+ scope. Best views near opposition when Mars is largest."
        ),
        "surface":     "Rocky desert, red iron oxide dust, ice caps",
        "composition": "Iron/nickel core, basaltic crust, CO₂ atmosphere",
        "color":       "danger",
    },
    "Jupiter": {
        "type":        "Gas Giant",
        "symbol":      "♃",
        "order":       5,
        "diameter_km": 142984,
        "mass_kg":     1.898e27,
        "moons":       95,
        "day_hours":   9.93,
        "year_days":   4332.59,
        "distance_au": 5.203,
        "description": (
            "The largest planet — more than twice the mass of all other planets combined. "
            "The Great Red Spot is a storm that has raged for over 350 years. "
            "Jupiter has 4 large Galilean moons visible in binoculars."
        ),
        "observer_notes": (
            "Unmistakable bright planet. Even binoculars reveal the 4 Galilean moons "
            "(Io, Europa, Ganymede, Callisto). A 3\" scope shows cloud bands; 6\"+ "
            "shows the Great Red Spot, festoons, ovals. Moon positions change nightly. "
            "Opposition every ~13 months."
        ),
        "surface":     "Gas giant — no solid surface; banded clouds of ammonia",
        "composition": "H₂ (90%), He (10%), traces of methane/ammonia",
        "color":       "warning",
    },
    "Saturn": {
        "type":        "Gas Giant",
        "symbol":      "♄",
        "order":       6,
        "diameter_km": 120536,
        "mass_kg":     5.683e26,
        "moons":       146,
        "day_hours":   10.66,
        "year_days":   10759.22,
        "distance_au": 9.537,
        "description": (
            "Famous for its spectacular ring system made of ice and rock particles "
            "ranging from tiny grains to boulders. Saturn is the least dense planet — "
            "it would float on water. Has 146 known moons including Titan with a "
            "thick nitrogen atmosphere."
        ),
        "observer_notes": (
            "The showpiece of the solar system — even a small 3\" scope reveals the rings "
            "clearly. Ring tilt varies from edge-on (~0°) to maximum tilt (~27°) on a "
            "15-year cycle. Titan (mag 8.5) visible in binoculars. Cloud bands subtler "
            "than Jupiter. Opposition every ~12.4 months."
        ),
        "surface":     "Gas giant; thick ammonia/water cloud layers",
        "composition": "H₂ (96%), He (3%), rings of ice/rock",
        "color":       "secondary",
    },
    "Uranus": {
        "type":        "Ice Giant",
        "symbol":      "⛢",
        "order":       7,
        "diameter_km": 51118,
        "mass_kg":     8.681e25,
        "moons":       27,
        "day_hours":   -17.24,  # retrograde
        "year_days":   30688.5,
        "distance_au": 19.191,
        "description": (
            "An ice giant with a striking blue-green color from methane in its atmosphere. "
            "Unique in that it rotates on its side — axial tilt of 98°. Has faint rings "
            "and 27 known moons, all named after Shakespeare characters."
        ),
        "observer_notes": (
            "Just barely naked-eye at mag 5.7 in dark skies. In binoculars appears as "
            "a tiny blue-green dot. A 6\"+ scope may show the disc (3.4\" diameter). "
            "No surface features visible in amateur telescopes. Opposition yearly. "
            "Use a star chart to identify it — it moves slowly against the stars."
        ),
        "surface":     "Ice giant — mantle of water/methane/ammonia ices",
        "composition": "H₂ (83%), He (15%), CH₄ (2%) gives blue color",
        "color":       "info",
    },
    "Neptune": {
        "type":        "Ice Giant",
        "symbol":      "♆",
        "order":       8,
        "diameter_km": 49528,
        "mass_kg":     1.024e26,
        "moons":       16,
        "day_hours":   16.11,
        "year_days":   60182.0,
        "distance_au": 30.069,
        "description": (
            "The windiest planet with storms reaching 2,100 km/h. A deep blue color "
            "from methane. Neptune was the first planet predicted mathematically before "
            "observation — perturbations in Uranus's orbit led to its discovery in 1846."
        ),
        "observer_notes": (
            "Always requires a telescope — magnitude ~7.8. Appears as a tiny blue-grey "
            "disc (2.3\" diameter) in larger scopes. Binoculars show it as a faint star. "
            "Largest moon Triton (mag 13.5) needs 10\"+ aperture. Opposition yearly; "
            "moves very slowly — takes 165 years to orbit the Sun."
        ),
        "surface":     "Ice giant — rocky core, water/ice mantle",
        "composition": "H₂ (80%), He (19%), CH₄ gives deep blue color",
        "color":       "primary",
    },
}

DWARF_PLANETS = {
    "Pluto": {
        "type":        "Dwarf Planet",
        "symbol":      "⯓",
        "order":       9,
        "diameter_km": 2376,
        "mass_kg":     1.303e22,
        "moons":       5,
        "day_hours":   -153.3,  # retrograde
        "year_days":   90560.0,
        "distance_au": 39.482,
        "description": (
            "Reclassified as a dwarf planet in 2006. Pluto has a complex geology "
            "revealed by New Horizons in 2015 — mountain ranges, plains of nitrogen ice, "
            "and a possible subsurface ocean. Its largest moon Charon is half Pluto's size."
        ),
        "observer_notes": (
            "Requires a large telescope — magnitude ~14.2. Even in a 12\" scope it "
            "appears as just a faint star-like dot. Use precise charts and compare "
            "frames over successive nights to confirm its slow motion."
        ),
        "surface":     "Nitrogen/methane ice, mountains of water ice",
        "composition": "Rock/ice mix, thin N₂ atmosphere",
        "color":       "secondary",
    },
    "Ceres": {
        "type":        "Dwarf Planet / Asteroid",
        "symbol":      "⚳",
        "order":       10,
        "diameter_km": 939,
        "mass_kg":     9.38e20,
        "moons":       0,
        "day_hours":   9.07,
        "year_days":   1681.0,
        "distance_au": 2.765,
        "description": (
            "The largest object in the asteroid belt between Mars and Jupiter. "
            "Dawn spacecraft revealed bright white spots — salt deposits from "
            "briny water that erupted from the interior. May have a subsurface "
            "liquid water layer."
        ),
        "observer_notes": (
            "Can reach magnitude 6.7 at opposition — just naked-eye from dark sites. "
            "Binoculars easily show it as a star-like point. Moves noticeably against "
            "the stars over several nights. A 4\"+ scope shows no disc. "
            "Opposition every ~15.5 months."
        ),
        "surface":     "Ice/rock, bright salt deposits (Occator crater)",
        "composition": "Rocky core, icy mantle, hydrated minerals",
        "color":       "secondary",
    },
}

# ── Comets ───────────────────────────────────────────────────────────────────
# Curated list of notable/currently-observable comets.
# Orbital elements in PyEphem XEphem format:
#   name,e,inc,LAN,AP,e,q,Epoch,M  (for elliptical)
#   or use ephem.readdb() with standard MPC format strings.
#
# Format per entry: human metadata + "xephem" string for PyEphem.
# XEphem DB string columns: name, type, epoch, inc, LAN, e, q, Tp
# type "e" = elliptical comet: epoch,i,Om,om,e,q,Tp
# We use the simpler ephem.readdb() parabolic/elliptical comet format.

COMETS = {
    "1P/Halley": {
        "description": (
            "The most famous periodic comet, visible to the naked eye roughly every "
            "75–76 years. Last perihelion 1986; next expected ~2061."
        ),
        "observer_notes": (
            "Currently magnitude ~28 — far too faint to observe. The Eta Aquariids (May) "
            "and Orionids (October) meteor showers come from its debris trail."
        ),
        "period_years": 75.3,
        "next_perihelion": "2061-07-28",
        # XEphem elliptical comet format (13 fields):
        # name,e,Tp,inc,LAN,AP,e,q,Tp,equinox,g,k,s
        "xephem": "1P/Halley,e,19860209.6812,162.2629,58.8201,111.3329,0.9673,0.5872,19860209.6812,2000,-2.0,4.0,0",
    },
    "2P/Encke": {
        "description": (
            "The shortest-period comet known (~3.3 years). Source of the Taurid meteor "
            "shower. Usually faint but can reach mag 4–5 at favorable perihelion passes."
        ),
        "observer_notes": (
            "Small, diffuse coma. Best observed in the weeks around perihelion. "
            "Binoculars or a small telescope needed at most apparitions."
        ),
        "period_years": 3.3,
        "xephem": "2P/Encke,e,20231023.2800,11.7806,334.5680,186.5398,0.8482,0.3356,20231023.2800,2000,4.0,4.0,0",
    },
    "9P/Tempel 1": {
        "description": (
            "Target of NASA's Deep Impact mission in 2005, which intentionally crashed "
            "a probe into the comet's nucleus. Period ~5.5 years."
        ),
        "observer_notes": (
            "Typically magnitude 10–11 near perihelion — requires a moderate telescope. "
            "Famous for the Deep Impact ejecta cloud observed worldwide."
        ),
        "period_years": 5.5,
        "xephem": "9P/Tempel 1,e,20050704.9,10.4740,68.9321,178.8580,0.5051,1.5028,20050704.9,2000,5.5,4.0,0",
    },
    "17P/Holmes": {
        "description": (
            "Famous for an extraordinary outburst in October 2007 that briefly made it "
            "the largest object in the solar system by volume (coma exceeded the Sun's diameter)."
        ),
        "observer_notes": (
            "Normally faint (~17th magnitude). The 2007 outburst brightened it by ~14 magnitudes "
            "to naked-eye visibility in Perseus — one of the most dramatic cometary events in decades."
        ),
        "period_years": 6.9,
        "xephem": "17P/Holmes,e,20071124.9,19.1126,326.8550,24.3540,0.4324,2.2054,20071124.9,2000,5.0,4.0,0",
    },
    "67P/Churyumov-Gerasimenko": {
        "description": (
            "Target of ESA's Rosetta mission, which orbited the comet for two years "
            "and landed the Philae probe on its surface in 2014. Period ~6.4 years."
        ),
        "observer_notes": (
            "Reaches magnitude 6–8 near perihelion — binoculars show it as a fuzzy star. "
            "Last perihelion November 2021; next ~May 2028."
        ),
        "period_years": 6.4,
        "xephem": "67P/Churyumov-Gerasimenko,e,20211102.4,7.0405,50.1350,12.8007,0.6401,1.2102,20211102.4,2000,6.0,4.0,0",
    },
    "C/1995 O1 (Hale-Bopp)": {
        "description": (
            "One of the brightest comets of the 20th century, visible to the naked eye "
            "for a record 18 months in 1996–1997. Its twin dust and ion tails were spectacular."
        ),
        "observer_notes": (
            "Currently far beyond Saturn's orbit and magnitude ~30+. Won't return for "
            "roughly 2,500 years. The 1997 apparition remains a benchmark for comet brightness."
        ),
        "period_years": 2520,
        "xephem": "C/1995 O1 (Hale-Bopp),e,19970401.1,89.4298,282.4707,130.5887,0.9951,0.9142,19970401.1,2000,-1.0,4.0,0",
    },
    "C/2020 F3 (NEOWISE)": {
        "description": (
            "Discovered by the NEOWISE space telescope in March 2020. Became the brightest "
            "comet visible from the northern hemisphere in over 20 years, reaching magnitude 0.5."
        ),
        "observer_notes": (
            "Now extremely faint — billions of km from the Sun. The July 2020 apparition "
            "produced stunning naked-eye views and distinctive dust/ion tails. Won't return "
            "for approximately 6,800 years."
        ),
        "period_years": 6800,
        "xephem": "C/2020 F3 (NEOWISE),e,20200703.7,128.9378,61.0113,37.2780,0.9992,0.2946,20200703.7,2000,2.5,4.0,0",
    },
}


def get_comet_position(name, lat=None, lon=None, dt=None):
    """
    Compute current position and visibility for a comet by name.
    Returns a dict or None if the comet isn't in our catalog or can't be computed.
    """
    if name not in COMETS:
        return None
    info = COMETS[name]
    xephem = info.get("xephem")
    if not xephem:
        return None

    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)

    try:
        body = ephem.readdb(xephem)
        obs  = _make_observer(lat, lon, dt)
        body.compute(obs)

        alt_deg = math.degrees(float(body.alt))
        az_deg  = math.degrees(float(body.az))
        ra_deg  = math.degrees(float(body.ra))
        dec_deg = math.degrees(float(body.dec))

        try:
            mag = round(float(body.mag), 1)
        except Exception:
            mag = None

        try:
            dist_au = round(float(body.earth_distance), 3)
        except Exception:
            dist_au = None

        try:
            sun_dist = round(float(body.sun_distance), 3)
        except Exception:
            sun_dist = None

        try:
            rise_str  = ephem.localtime(obs.next_rising(body)).strftime("%H:%M")
            set_str   = ephem.localtime(obs.next_setting(body)).strftime("%H:%M")
            trans_str = ephem.localtime(obs.next_transit(body)).strftime("%H:%M")
        except ephem.AlwaysUpError:
            rise_str = set_str = trans_str = "Circumpolar"
        except ephem.NeverUpError:
            rise_str = set_str = trans_str = "Never rises"
        except Exception:
            rise_str = set_str = trans_str = "—"

        return {
            "name":          name,
            "ra_deg":        round(ra_deg, 4),
            "dec_deg":       round(dec_deg, 4),
            "altitude":      round(alt_deg, 1) if lat is not None else None,
            "azimuth":       round(az_deg, 1)  if lat is not None else None,
            "above_horizon": alt_deg > 0        if lat is not None else None,
            "magnitude":     mag,
            "dist_au":       dist_au,
            "sun_dist_au":   sun_dist,
            "rise_time":     rise_str  if lat is not None else None,
            "set_time":      set_str   if lat is not None else None,
            "transit_time":  trans_str if lat is not None else None,
            "description":         info.get("description", ""),
            "observer_notes":      info.get("observer_notes", ""),
            "period_years":        info.get("period_years"),
            "next_perihelion":     info.get("next_perihelion"),
        }
    except Exception:
        return None


def get_all_comets(lat=None, lon=None, dt=None):
    """Return list of dicts for all tracked comets."""
    results = []
    for name in COMETS:
        pos = get_comet_position(name, lat, lon, dt)
        if pos:
            results.append(pos)
    # Sort by magnitude (brightest first), None last
    results.sort(key=lambda x: (x["magnitude"] is None, x["magnitude"] or 99))
    return results


# ── Satellites (TLE-based) ────────────────────────────────────────────────────

# Celestrak new GP data API (CATNR = NORAD catalog number)
_TLE_URLS = {
    "ISS (ZARYA)":  "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE",
    "CSS (TIANHE)": "https://celestrak.org/NORAD/elements/gp.php?CATNR=48274&FORMAT=TLE",
    "HST":          "https://celestrak.org/NORAD/elements/gp.php?CATNR=20580&FORMAT=TLE",
}

# Fallback TLEs — used if Celestrak is unreachable.
# These are periodically stale but good enough for approximate position.
# The app will replace them with live data on first successful network fetch.
_FALLBACK_TLES = {
    "ISS (ZARYA)": (
        "ISS (ZARYA)",
        "1 25544U 98067A   26099.81181649  .00006374  00000+0  12437-3 0  9993",
        "2 25544  51.6329 278.4805 0006426 293.1753  66.8558 15.48850892561156",
    ),
    "CSS (TIANHE)": (
        "CSS (TIANHE)",
        "1 48274U 21035A   26099.79993243  .00026712  00000+0  29783-3 0  9997",
        "2 48274  41.4683  18.6460 0004513 172.0763 188.0148 15.62188173282472",
    ),
    "HST": (
        "HST",
        "1 20580U 90037B   26099.79166667  .00001800  00000+0  85730-4 0  9991",
        "2 20580  28.4697 297.7641 0002572  19.5381 340.5669 15.09555944392844",
    ),
}

_SATELLITE_DISPLAY = {
    "ISS (ZARYA)": {
        "common_name": "International Space Station",
        "symbol": "🛸",
        "description": (
            "The largest human-made structure in space, assembled over 13 years "
            "starting in 1998. Home to rotating crews of 6–7 astronauts from "
            "multiple nations. Orbits at ~400 km altitude, completing 15.5 orbits per day."
        ),
        "observer_notes": (
            "One of the brightest objects in the night sky — can reach magnitude −5.9. "
            "Appears as a fast-moving, steady (non-blinking) bright star crossing the sky "
            "in 2–5 minutes. Use NASA's Spot the Station for precise pass predictions."
        ),
    },
    "CSS (TIANHE)": {
        "common_name": "Chinese Space Station (Tiangong)",
        "symbol": "🛸",
        "description": (
            "China's permanent modular space station, with the core Tianhe module "
            "launched in April 2021. Designed for a 10-year lifespan with rotating "
            "3-person crews. Orbits at ~390 km altitude."
        ),
        "observer_notes": (
            "Visible to naked eye, typically reaching magnitude −1 to −3. "
            "Appears similar to the ISS — a steady, fast-moving bright point. "
            "Passes are less frequently predicted in Western apps than the ISS."
        ),
    },
    "HST": {
        "common_name": "Hubble Space Telescope",
        "symbol": "🔭",
        "description": (
            "Launched in 1990, the Hubble Space Telescope has revolutionized astronomy "
            "with observations from ultraviolet to near-infrared. Orbits at ~540 km, "
            "completing about 15 orbits per day."
        ),
        "observer_notes": (
            "Visible with naked eye under dark skies, reaching magnitude ~2–4. "
            "Smaller and dimmer than the ISS — binoculars help. Moves steadily "
            "across the sky like a satellite."
        ),
    },
}

_BASE_DIR     = os.path.dirname(__file__)
_TLE_CACHE    = os.path.join(_BASE_DIR, "tle_cache.json")
_TLE_MAX_AGE  = 6 * 3600   # refresh TLEs if older than 6 hours


def _load_tle_cache():
    try:
        with open(_TLE_CACHE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_tle_cache(data):
    try:
        with open(_TLE_CACHE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _fetch_tle_for_sat(name, url):
    """Fetch TLE lines for a single satellite from Celestrak. Returns (line1, line2) or None."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "DeepSkyObservatory/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            text = resp.read().decode("utf-8", errors="replace").strip()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        # Find TLE lines: line1 starts with '1 ', line2 starts with '2 '
        l1 = next((l for l in lines if l.startswith("1 ")), None)
        l2 = next((l for l in lines if l.startswith("2 ")), None)
        if l1 and l2:
            return l1, l2
    except Exception:
        pass
    return None


def _get_tles():
    """Return fresh TLEs for all tracked satellites, using cache or fallback."""
    cache = _load_tle_cache()
    now   = time.time()
    updated = False

    for sat_name, url in _TLE_URLS.items():
        entry = cache.get(sat_name, {})
        age   = now - entry.get("fetched_at", 0)
        if age > _TLE_MAX_AGE or "line1" not in entry:
            result = _fetch_tle_for_sat(sat_name, url)
            if result:
                cache[sat_name] = {
                    "line1":      result[0],
                    "line2":      result[1],
                    "fetched_at": now,
                }
                updated = True

    if updated:
        _save_tle_cache(cache)

    return cache


def get_satellite_position(sat_name, lat=None, lon=None, dt=None):
    """
    Compute current position and visibility for a tracked satellite.
    Returns a dict or None.
    """
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)

    tles    = _get_tles()
    entry   = tles.get(sat_name)
    display = _SATELLITE_DISPLAY.get(sat_name, {})

    # Get TLE lines — from cache or fallback
    if entry and "line1" in entry:
        name_line = sat_name
        line1     = entry["line1"]
        line2     = entry["line2"]
    elif sat_name in _FALLBACK_TLES:
        name_line, line1, line2 = _FALLBACK_TLES[sat_name]
    else:
        return None

    try:
        sat = ephem.readtle(name_line, line1, line2)
        obs = _make_observer(lat, lon, dt)
        sat.compute(obs)

        alt_deg = math.degrees(float(sat.alt))
        az_deg  = math.degrees(float(sat.az))
        ra_deg  = math.degrees(float(sat.ra))
        dec_deg = math.degrees(float(sat.dec))

        # Range (distance from observer) in km
        try:
            range_km = round(float(sat.range) / 1000, 1)
        except Exception:
            range_km = None

        # Orbital altitude approximation
        try:
            elev_km = round(float(sat.elevation) / 1000, 1)
        except Exception:
            elev_km = None

        # Eclipsed by Earth's shadow?
        try:
            eclipsed = bool(sat.eclipsed)
        except Exception:
            eclipsed = None

        # Rise / set (next pass)
        try:
            rise_dt  = obs.next_rising(sat)
            set_dt   = obs.next_setting(sat)
            trans_dt = obs.next_transit(sat)
            rise_str  = ephem.localtime(rise_dt).strftime("%H:%M")
            set_str   = ephem.localtime(set_dt).strftime("%H:%M")
            trans_str = ephem.localtime(trans_dt).strftime("%H:%M")
        except Exception:
            rise_str = set_str = trans_str = "—"

        return {
            "name":          sat_name,
            "common_name":   display.get("common_name", sat_name),
            "symbol":        display.get("symbol", "🛸"),
            "description":   display.get("description", ""),
            "observer_notes":display.get("observer_notes", ""),
            "ra_deg":        round(ra_deg, 4),
            "dec_deg":       round(dec_deg, 4),
            "altitude":      round(alt_deg, 1) if lat is not None else None,
            "azimuth":       round(az_deg, 1)  if lat is not None else None,
            "above_horizon": alt_deg > 0        if lat is not None else None,
            "eclipsed":      eclipsed,
            "range_km":      range_km,
            "orbital_alt_km":elev_km,
            "rise_time":     rise_str  if lat is not None else None,
            "set_time":      set_str   if lat is not None else None,
            "transit_time":  trans_str if lat is not None else None,
        }
    except Exception:
        return None


def get_all_satellites(lat=None, lon=None, dt=None):
    """Return list of dicts for all tracked satellites."""
    results = []
    for name in _SATELLITE_DISPLAY:
        pos = get_satellite_position(name, lat, lon, dt)
        if pos:
            results.append(pos)
    return results

# Notable asteroids (beyond Ceres) with ephem-compatible data
NOTABLE_ASTEROIDS = {
    "4 Vesta": {
        "type":        "Asteroid",
        "symbol":      "⚶",
        "diameter_km": 525,
        "description": (
            "The second-largest asteroid and the brightest asteroid visible from Earth. "
            "Has a distinctive south-polar impact crater (Rheasilvia) nearly as large "
            "as the asteroid itself. Dawn spacecraft orbited Vesta 2011–2012."
        ),
        "observer_notes": (
            "Can reach magnitude 5.1 at opposition — naked-eye in dark skies. "
            "Binoculars easily show it. Moves detectably against star background "
            "over several nights."
        ),
        "ephem_name": "Vesta",
    },
    "2 Pallas": {
        "type":        "Asteroid",
        "symbol":      "⚴",
        "diameter_km": 511,
        "description": (
            "The third-largest asteroid and the second discovered (1802). "
            "Has an unusual highly inclined orbit (~35°)."
        ),
        "observer_notes": (
            "Can reach magnitude 6.5 at opposition. Binocular object at best. "
            "Identify by its motion relative to background stars."
        ),
        "ephem_name": "Pallas",
    },
}

# ── ephem planet name map ─────────────────────────────────────────────────────

EPHEM_BODIES = {
    "Mercury": ephem.Mercury,
    "Venus":   ephem.Venus,
    "Mars":    ephem.Mars,
    "Jupiter": ephem.Jupiter,
    "Saturn":  ephem.Saturn,
    "Uranus":  ephem.Uranus,
    "Neptune": ephem.Neptune,
    "Pluto":   ephem.Pluto,
}

# ── Calculation functions ─────────────────────────────────────────────────────

def _make_observer(lat=None, lon=None, dt=None):
    obs = ephem.Observer()
    obs.lat  = str(lat)  if lat  is not None else "0"
    obs.lon  = str(lon)  if lon  is not None else "0"
    obs.elev = 0
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    obs.date = ephem.Date(dt.strftime("%Y/%m/%d %H:%M:%S"))
    obs.pressure = 0   # ignore atmospheric refraction for simplicity
    return obs


def get_planet_position(name, lat=None, lon=None, dt=None):
    """
    Return a dict of current data for a planet or Pluto.
    All angles in degrees. Returns None if name not found.
    """
    if name not in EPHEM_BODIES:
        return None

    obs  = _make_observer(lat, lon, dt)
    body = EPHEM_BODIES[name]()
    body.compute(obs)

    ra_deg  = math.degrees(float(body.ra))
    dec_deg = math.degrees(float(body.dec))
    alt_deg = math.degrees(float(body.alt))
    az_deg  = math.degrees(float(body.az))

    # Rise / set / transit today
    try:
        rise_dt  = obs.next_rising(body)
        set_dt   = obs.next_setting(body)
        trans_dt = obs.next_transit(body)
        rise_str  = ephem.localtime(rise_dt).strftime("%H:%M")
        set_str   = ephem.localtime(set_dt).strftime("%H:%M")
        trans_str = ephem.localtime(trans_dt).strftime("%H:%M")
    except ephem.AlwaysUpError:
        rise_str = set_str = trans_str = "Circumpolar"
    except ephem.NeverUpError:
        rise_str = set_str = trans_str = "Never rises"
    except Exception:
        rise_str = set_str = trans_str = "—"

    # Phase (0–1) for inner planets and anything ephem provides
    phase = None
    try:
        phase = round(float(body.phase), 1)   # percent illuminated
    except AttributeError:
        pass

    # Angular diameter in arcseconds
    ang_size = None
    try:
        ang_size = round(float(body.size), 2)
    except AttributeError:
        pass

    # Distance from Earth in AU
    dist_au = None
    try:
        dist_au = round(float(body.earth_distance), 4)
    except AttributeError:
        pass

    # Heliocentric distance in AU
    sun_dist = None
    try:
        sun_dist = round(float(body.sun_distance), 4)
    except AttributeError:
        pass

    return {
        "name":           name,
        "ra_deg":         round(ra_deg, 4),
        "dec_deg":        round(dec_deg, 4),
        "ra_str":         str(body.ra),
        "dec_str":        str(body.dec),
        "altitude":       round(alt_deg, 1)  if lat is not None else None,
        "azimuth":        round(az_deg, 1)   if lat is not None else None,
        "above_horizon":  alt_deg > 0         if lat is not None else None,
        "magnitude":      round(float(body.mag), 2),
        "phase_pct":      phase,
        "ang_size_arcsec":ang_size,
        "dist_au":        dist_au,
        "sun_dist_au":    sun_dist,
        "rise_time":      rise_str  if lat is not None else None,
        "set_time":       set_str   if lat is not None else None,
        "transit_time":   trans_str if lat is not None else None,
        "constellation":  ephem.constellation(body)[1],
    }


def get_all_planets(lat=None, lon=None, dt=None):
    """Return list of dicts for all tracked solar system bodies, sorted by order."""
    results = []
    for name, static in {**PLANETS, **DWARF_PLANETS}.items():
        pos = get_planet_position(name, lat, lon, dt)
        if pos:
            merged = {**static, **pos}
            results.append(merged)
    results.sort(key=lambda x: x.get("order", 99))
    return results


def get_moon_phase(dt=None):
    """Return current Moon phase data."""
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    moon = ephem.Moon()
    obs  = ephem.Observer()
    obs.date = ephem.Date(dt.strftime("%Y/%m/%d %H:%M:%S"))
    moon.compute(obs)

    phase_pct = float(moon.phase)
    # Approximate phase name
    age = float(ephem.next_new_moon(obs.date) - ephem.previous_new_moon(obs.date))
    elapsed = float(obs.date - ephem.previous_new_moon(obs.date))
    day = elapsed / age * 29.53

    if day < 1:       phase_name = "New Moon"
    elif day < 6.5:   phase_name = "Waxing Crescent"
    elif day < 8.5:   phase_name = "First Quarter"
    elif day < 13.5:  phase_name = "Waxing Gibbous"
    elif day < 15.5:  phase_name = "Full Moon"
    elif day < 21:    phase_name = "Waning Gibbous"
    elif day < 23:    phase_name = "Last Quarter"
    elif day < 28:    phase_name = "Waning Crescent"
    else:             phase_name = "New Moon"

    next_new  = ephem.localtime(ephem.next_new_moon(obs.date)).strftime("%b %d")
    next_full = ephem.localtime(ephem.next_full_moon(obs.date)).strftime("%b %d")

    return {
        "phase_pct":   round(phase_pct, 1),
        "phase_name":  phase_name,
        "age_days":    round(day, 1),
        "next_new":    next_new,
        "next_full":   next_full,
        "ra_str":      str(moon.ra),
        "dec_str":     str(moon.dec),
        "ang_size_arcsec": round(float(moon.size), 1),
        "magnitude":   round(float(moon.mag), 1),
    }


def get_sun_data(lat=None, lon=None, dt=None):
    """Return current Sun data (for twilight/daytime context)."""
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    obs  = _make_observer(lat, lon, dt)
    sun  = ephem.Sun()
    sun.compute(obs)

    alt = math.degrees(float(sun.alt))

    if alt > 0:
        sky_state = "daytime"
    elif alt > -6:
        sky_state = "civil twilight"
    elif alt > -12:
        sky_state = "nautical twilight"
    elif alt > -18:
        sky_state = "astronomical twilight"
    else:
        sky_state = "night"

    try:
        rise = ephem.localtime(obs.next_rising(sun)).strftime("%H:%M")
        sset = ephem.localtime(obs.next_setting(sun)).strftime("%H:%M")
    except Exception:
        rise = sset = "—"

    return {
        "altitude":   round(alt, 1),
        "sky_state":  sky_state,
        "is_night":   sky_state == "night",
        "sunrise":    rise  if lat is not None else None,
        "sunset":     sset  if lat is not None else None,
        "magnitude":  round(float(sun.mag), 1),
    }
