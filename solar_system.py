"""
solar_system.py — Dynamic solar system object data using PyEphem.

Provides current positions, magnitudes, phase, and observer-specific
altitude/azimuth for planets, dwarf planets, and notable small bodies.
"""

import math
import datetime
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

# Notable comets with orbital elements (epoch, inclination, etc.)
# These are updated periodically; bright historical/recurring comets included.
COMETS_TLE = {
    "1P/Halley": {
        "description": (
            "The most famous periodic comet, visible to the naked eye roughly every "
            "75–76 years. Last perihelion was in 1986; next expected ~2061."
        ),
        "period_years": 75.3,
        "last_perihelion": "1986-02-09",
        "next_perihelion": "2061-07-28",
        "observer_notes": (
            "Currently too faint to observe (mag ~28). Best seen near perihelion. "
            "The Eta Aquariids (May) and Orionids (October) meteor showers are "
            "caused by debris from Halley's Comet."
        ),
    },
}

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
