#!/usr/bin/env python3
"""
Deep Sky Observatory — Flask web app for the astronomy SQLite database.
Run:  python3 app.py
Then: http://<your-pi-ip>:5050
"""

import sqlite3
import os
import math
import datetime
import re
import json
import urllib.request
import urllib.parse
import threading
from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, abort, send_file, Response)
import solar_system as ss

app = Flask(__name__)
BASE_DIR    = os.path.dirname(__file__)
DB_PATH     = os.path.join(BASE_DIR, "astronomy.db")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
THUMB_CACHE = os.path.join(BASE_DIR, "static", "thumbcache")
os.makedirs(THUMB_CACHE, exist_ok=True)
_thumb_lock = threading.Lock()

# ── Persistence helpers ───────────────────────────────────────────────────────

def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── Astronomy calculations ────────────────────────────────────────────────────

def julian_date(dt):
    """Compute Julian Date from a UTC datetime."""
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jd = (dt.day + (153 * m + 2) // 5 + 365 * y
          + y // 4 - y // 100 + y // 400 - 32045)
    jd += (dt.hour - 12) / 24 + dt.minute / 1440 + dt.second / 86400
    return jd

def local_sidereal_time(lon_deg, dt=None):
    """Return Local Sidereal Time in degrees."""
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    jd = julian_date(dt)
    T  = (jd - 2451545.0) / 36525.0
    gmst = (280.46061837
            + 360.98564736629 * (jd - 2451545.0)
            + 0.000387933 * T ** 2
            - T ** 3 / 38710000.0) % 360
    return (gmst + lon_deg) % 360

def calc_altaz(ra_deg, dec_deg, lat_deg, lon_deg, dt=None):
    """
    Return (altitude_deg, azimuth_deg) for an object at the observer's location.
    Altitude > 0 means above horizon.
    """
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    lst   = local_sidereal_time(lon_deg, dt)
    H_deg = (lst - ra_deg) % 360          # hour angle
    H  = math.radians(H_deg)
    dec = math.radians(dec_deg)
    lat = math.radians(lat_deg)

    sin_alt = (math.sin(dec) * math.sin(lat)
               + math.cos(dec) * math.cos(lat) * math.cos(H))
    sin_alt = max(-1.0, min(1.0, sin_alt))
    alt     = math.degrees(math.asin(sin_alt))

    cos_alt = math.cos(math.radians(alt))
    if cos_alt < 1e-10:
        az = 0.0
    else:
        cos_az = (math.sin(dec) - math.sin(lat) * sin_alt) / (math.cos(lat) * cos_alt)
        cos_az = max(-1.0, min(1.0, cos_az))
        az = math.degrees(math.acos(cos_az))
        if math.sin(H) > 0:
            az = 360.0 - az

    return round(alt, 1), round(az, 1)

def transit_info(ra_deg, dec_deg, lat_deg, lon_deg):
    """
    Return dict with:
      - transit_alt: max altitude at upper transit (degrees)
      - is_circumpolar: never sets
      - is_never_rises: never rises
      - approx_rise_az / approx_set_az
    """
    lat = math.radians(lat_deg)
    dec = math.radians(dec_deg)
    transit_alt = math.degrees(math.asin(
        max(-1.0, min(1.0, math.sin(lat) * math.sin(dec)
                          + math.cos(lat) * math.cos(dec)))))
    # Circumpolar if dec > 90 - lat (for N hemisphere)
    circumpolar  = dec_deg > (90 - abs(lat_deg)) and lat_deg > 0
    circumpolar |= dec_deg < -(90 - abs(lat_deg)) and lat_deg < 0
    never_rises  = (lat_deg > 0 and dec_deg < -(90 - lat_deg))
    never_rises |= (lat_deg < 0 and dec_deg > (90 + lat_deg))

    # Rise/set azimuth (approx, ignoring refraction)
    cos_az0 = math.sin(dec) / math.cos(lat) if abs(math.cos(lat)) > 1e-9 else 0
    cos_az0 = max(-1.0, min(1.0, cos_az0))
    rise_az = round(math.degrees(math.acos(cos_az0)), 1)
    set_az  = round(360 - rise_az, 1)

    return {
        "transit_alt":   round(transit_alt, 1),
        "is_circumpolar": circumpolar,
        "is_never_rises": never_rises,
        "rise_az":        rise_az,
        "set_az":         set_az,
    }

# ── Sky image proxy (server-side, cached) ────────────────────────────────────

SKYVIEW_URL = (
    "https://skyview.gsfc.nasa.gov/current/cgi/runquery.pl"
    "?Position={ra},{dec}&survey={survey}&Pixels={px}&Size={fov}&Return=JPG"
)
SURVEYS_SM = ["DSS2+Red", "DSS2+Blue"]
SURVEYS_LG = ["DSS2+Red", "DSS2+Blue"]

def fetch_thumb(ra, dec, fov, px):
    """Download a sky image from NASA SkyView. Returns bytes or None."""
    for survey in (SURVEYS_SM if px <= 200 else SURVEYS_LG):
        url = SKYVIEW_URL.format(ra=ra, dec=dec, survey=survey,
                                 px=px, fov=round(fov, 4))
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "DeepSkyObservatory/1.0"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = resp.read()
                if data and data[:2] == b"\xff\xd8":   # JPEG magic
                    return data
        except Exception:
            continue
    return None

def fmt_ra(ra_str):
    """Format RA from HH:MM:SS.ss to HHhMMmSSs."""
    if not ra_str:
        return ra_str
    parts = ra_str.split(':')
    if len(parts) != 3:
        return ra_str
    h, m, s = int(parts[0]), int(parts[1]), round(float(parts[2]))
    return f"{h:02d}h{m:02d}m{s:02d}s"

def fmt_dec(dec_str):
    """Format Dec from ±DD:MM:SS.s to ±DDdMM'SS\"."""
    if not dec_str:
        return dec_str
    sign = '-' if dec_str.startswith('-') else '+'
    clean = dec_str.lstrip('+-')
    parts = clean.split(':')
    if len(parts) != 3:
        return dec_str
    d, m, s = int(parts[0]), int(parts[1]), round(float(parts[2]))
    return f"{sign}{d:02d}\u00b0{m:02d}'{s:02d}\""

@app.template_filter("format_num")
def format_num(n):
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return n

@app.template_filter("urlencode")
def urlencode_filter(s):
    from urllib.parse import quote
    return quote(str(s))

CURRENT_MONTH = datetime.datetime.now().strftime("%b")  # e.g. "Apr"

# ── Object type to icon mapping ───────────────────────────────────────────────
TYPE_ICONS = {
    "G":       ("galaxy",       "spiral-galaxy"),
    "GPair":   ("galaxy",       "two galaxies"),
    "GGroup":  ("galaxy",       "galaxy group"),
    "GClstr":  ("galaxy",       "galaxy cluster"),
    "GCl":     ("globular",     "globular cluster"),
    "OCl":     ("open-cluster", "open cluster"),
    "OC+N":    ("open-cluster", "cluster+nebula"),
    "Cl+N":    ("open-cluster", "cluster+nebula"),
    "PN":      ("planetary",    "planetary nebula"),
    "SNR":     ("nebula",       "supernova remnant"),
    "Neb":     ("nebula",       "nebula"),
    "RNe":     ("nebula",       "reflection nebula"),
    "EmN":     ("nebula",       "emission nebula"),
    "HII":     ("nebula",       "HII region"),
    "Ast":     ("open-cluster", "asterism"),
    "D*":      ("star",         "double star"),
    "**":      ("star",         "double star"),
    "*":       ("star",         "star"),
    "*Ass":    ("open-cluster", "stellar association"),
    "MwPt":    ("nebula",       "milky way region"),
}

DIFFICULTY_LABELS = {
    1: ("Naked Eye",       "success"),
    2: ("Binoculars",      "info"),
    3: ("Small Scope",     "primary"),
    4: ("Medium Scope",    "warning"),
    5: ("Large Scope",     "danger"),
}

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]

CONSTELLATION_NAMES = {
    "And": "Andromeda",     "Ant": "Antlia",         "Aps": "Apus",
    "Aql": "Aquila",        "Aqr": "Aquarius",       "Ara": "Ara",
    "Ari": "Aries",         "Aur": "Auriga",          "Boo": "Boötes",
    "CMa": "Canis Major",   "CMi": "Canis Minor",    "CVn": "Canes Venatici",
    "Cae": "Caelum",        "Cam": "Camelopardalis", "Cap": "Capricornus",
    "Car": "Carina",        "Cas": "Cassiopeia",     "Cen": "Centaurus",
    "Cep": "Cepheus",       "Cet": "Cetus",           "Cha": "Chamaeleon",
    "Cir": "Circinus",      "Cnc": "Cancer",          "Col": "Columba",
    "Com": "Coma Berenices","CrA": "Corona Australis","CrB": "Corona Borealis",
    "Crt": "Crater",        "Cru": "Crux",            "Crv": "Corvus",
    "Cyg": "Cygnus",        "Del": "Delphinus",       "Dor": "Dorado",
    "Dra": "Draco",         "Equ": "Equuleus",        "Eri": "Eridanus",
    "For": "Fornax",        "Gem": "Gemini",          "Gru": "Grus",
    "Her": "Hercules",      "Hor": "Horologium",      "Hya": "Hydra",
    "Hyi": "Hydrus",        "Ind": "Indus",           "LMi": "Leo Minor",
    "Lac": "Lacerta",       "Leo": "Leo",             "Lep": "Lepus",
    "Lib": "Libra",         "Lup": "Lupus",           "Lyn": "Lynx",
    "Lyr": "Lyra",          "Men": "Mensa",           "Mic": "Microscopium",
    "Mon": "Monoceros",     "Mus": "Musca",           "Nor": "Norma",
    "Oct": "Octans",        "Oph": "Ophiuchus",       "Ori": "Orion",
    "Pav": "Pavo",          "Peg": "Pegasus",         "Per": "Perseus",
    "Phe": "Phoenix",       "Pic": "Pictor",          "PsA": "Piscis Austrinus",
    "Psc": "Pisces",        "Pup": "Puppis",          "Pyx": "Pyxis",
    "Ret": "Reticulum",     "Scl": "Sculptor",        "Sco": "Scorpius",
    "Sct": "Scutum",        "Se1": "Serpens Caput",   "Se2": "Serpens Cauda",
    "Sex": "Sextans",       "Sge": "Sagitta",         "Sgr": "Sagittarius",
    "Tau": "Taurus",        "Tel": "Telescopium",     "TrA": "Triangulum Australe",
    "Tri": "Triangulum",    "Tuc": "Tucana",          "UMa": "Ursa Major",
    "UMi": "Ursa Minor",    "Vel": "Vela",            "Vir": "Virgo",
    "Vol": "Volans",        "Vul": "Vulpecula",
}

# ── DB helpers ────────────────────────────────────────────────────────────────

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def row_to_dict(row):
    if row is None:
        return None
    return dict(zip(row.keys(), row))

def enrich(obj):
    """Add computed display fields to an object dict."""
    if obj is None:
        return None

    # Formatted RA / Dec
    obj["ra_fmt"]  = fmt_ra(obj.get("ra") or "")
    obj["dec_fmt"] = fmt_dec(obj.get("dec") or "")

    # Constellation full name
    const_abbr = obj.get("constellation") or ""
    obj["constellation_name"] = CONSTELLATION_NAMES.get(const_abbr, const_abbr)

    # Type info
    otype = obj.get("object_type") or ""
    icon_info = TYPE_ICONS.get(otype, ("other", obj.get("object_type_label") or "Object"))
    obj["type_icon"]  = icon_info[0]
    obj["type_title"] = icon_info[1]

    # Difficulty badge
    diff = obj.get("difficulty")
    if diff and diff in DIFFICULTY_LABELS:
        obj["diff_label"], obj["diff_color"] = DIFFICULTY_LABELS[diff]
    else:
        obj["diff_label"] = "Unknown"
        obj["diff_color"] = "secondary"

    # FOV for sky image (degrees)
    major = obj.get("major_axis_arcmin")
    if major and major > 0:
        fov = max(0.08, min(5.0, major * 3.0 / 60.0))
    else:
        fov = 0.4
    obj["image_fov"] = round(fov, 4)

    # Thumbnail URLs — served via our local proxy (caches NASA SkyView images)
    ra  = obj.get("ra_deg")
    dec = obj.get("dec_deg")
    slug = obj.get("designation", "").replace(" ", "-")
    if ra is not None and dec is not None and slug:
        obj["thumb_url"]    = f"/api/thumb/{slug}?size=lg"
        obj["thumb_sm_url"] = f"/api/thumb/{slug}?size=sm"
    else:
        obj["thumb_url"]    = None
        obj["thumb_sm_url"] = None

    # Best months highlight
    best = obj.get("best_months") or ""
    obj["in_season"] = CURRENT_MONTH in best

    # Distance formatted
    dist = obj.get("distance_ly")
    if dist:
        if dist >= 1e9:
            obj["distance_fmt"] = f"{dist/1e9:.2f} billion ly"
        elif dist >= 1e6:
            obj["distance_fmt"] = f"{dist/1e6:.2f} million ly"
        elif dist >= 1000:
            obj["distance_fmt"] = f"{dist/1e3:,.0f} thousand ly"
        else:
            obj["distance_fmt"] = f"{dist:,.0f} ly"
    else:
        obj["distance_fmt"] = None

    # Angular size formatted
    if major:
        if obj.get("minor_axis_arcmin"):
            obj["size_fmt"] = f"{major:.1f}' × {obj['minor_axis_arcmin']:.1f}'"
        else:
            obj["size_fmt"] = f"{major:.1f}'"
    else:
        obj["size_fmt"] = None

    return obj


def parse_search_query(q):
    """Parse query string and return (sql_where, params) for FTS-style search."""
    q = q.strip()
    conditions = []
    params = []

    # M31 or M 31 or Messier 31
    m = re.match(r'^[Mm]\s*(\d{1,3})$', q) or re.match(r'^[Mm]essier\s+(\d{1,3})$', q, re.IGNORECASE)
    if m:
        conditions.append("messier_number = ?")
        params.append(int(m.group(1)))
        return " AND ".join(conditions), params

    # NGC 224 or NGC224
    m = re.match(r'^(ngc|ic)\s*(\d+)$', q, re.IGNORECASE)
    if m:
        conditions.append("designation = ?")
        params.append(f"{m.group(1).upper()} {int(m.group(2))}")
        return " AND ".join(conditions), params

    # General text search
    like = f"%{q}%"
    conditions.append(
        "(designation LIKE ? OR common_name LIKE ? OR common_names_raw LIKE ? "
        "OR identifiers LIKE ? OR constellation LIKE ?)"
    )
    params.extend([like, like, like, like, like])
    return " AND ".join(conditions), params


# ── Context processor ─────────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    settings = load_settings()
    loc = settings.get("location")
    return {
        "current_month": CURRENT_MONTH,
        "app_name": "Deep Sky Observatory",
        "user_location": loc,   # None or {lat, lon, name}
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    conn = db()
    cur  = conn.cursor()

    # Stats
    stats = {}
    for key, where in [
        ("total",    "1"),
        ("messier",  "messier_number IS NOT NULL"),
        ("galaxies", "object_type = 'G'"),
        ("clusters", "object_type IN ('GCl','OCl')"),
        ("nebulae",  "object_type IN ('PN','SNR','Neb','RNe','EmN','HII')"),
        ("easy",     "difficulty <= 2 AND magnitude_v IS NOT NULL"),
    ]:
        cur.execute(f"SELECT COUNT(*) FROM objects WHERE {where}")
        stats[key] = cur.fetchone()[0]

    # Tonight's picks — objects in season, bright
    cur.execute("""
        SELECT * FROM objects
        WHERE best_months LIKE ? AND magnitude_v IS NOT NULL
          AND difficulty <= 3
        ORDER BY magnitude_v
        LIMIT 8
    """, (f"%{CURRENT_MONTH}%",))
    tonight = [enrich(row_to_dict(r)) for r in cur.fetchall()]

    # Messier showpieces for hero strip
    cur.execute("""
        SELECT * FROM objects
        WHERE messier_number IS NOT NULL AND magnitude_v IS NOT NULL
        ORDER BY magnitude_v LIMIT 6
    """)
    featured = [enrich(row_to_dict(r)) for r in cur.fetchall()]

    conn.close()
    return render_template("index.html",
                           stats=stats,
                           tonight=tonight,
                           featured=featured)


@app.route("/search")
def search():
    q        = request.args.get("q", "").strip()
    otype    = request.args.get("type", "")
    const    = request.args.get("const", "")
    diff_max = request.args.get("diff", "")
    mag_max  = request.args.get("mag", "")
    sort     = request.args.get("sort", "magnitude_v")
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 24

    conditions = []
    params     = []

    if q:
        where, p = parse_search_query(q)
        conditions.append(f"({where})")
        params.extend(p)

    if otype:
        type_map = {
            "galaxy":   ["G", "GPair", "GGroup", "GClstr"],
            "globular": ["GCl"],
            "open":     ["OCl", "OC+N", "Cl+N", "Ast"],
            "nebula":   ["Neb", "RNe", "EmN", "HII", "SNR"],
            "planetary":["PN"],
        }
        if otype in type_map:
            placeholders = ",".join("?" * len(type_map[otype]))
            conditions.append(f"object_type IN ({placeholders})")
            params.extend(type_map[otype])

    if const:
        conditions.append("constellation = ?")
        params.append(const.title())

    if diff_max:
        try:
            conditions.append("difficulty <= ?")
            params.append(int(diff_max))
        except ValueError:
            pass

    if mag_max:
        try:
            conditions.append("(magnitude_v <= ? OR magnitude_v IS NULL)")
            params.append(float(mag_max))
        except ValueError:
            pass

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    valid_sorts = {"magnitude_v", "designation", "constellation", "difficulty", "major_axis_arcmin"}
    if sort not in valid_sorts:
        sort = "magnitude_v"

    conn = db()
    cur  = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM objects {where_clause}", params)
    total = cur.fetchone()[0]
    pages = math.ceil(total / per_page)
    offset = (page - 1) * per_page

    cur.execute(f"""
        SELECT * FROM objects {where_clause}
        ORDER BY {sort} IS NULL, {sort}
        LIMIT ? OFFSET ?
    """, params + [per_page, offset])
    results = [enrich(row_to_dict(r)) for r in cur.fetchall()]

    # Constellation list for filter dropdown
    cur.execute("SELECT DISTINCT constellation FROM objects WHERE constellation IS NOT NULL ORDER BY constellation")
    constellations = [{"abbr": r[0], "name": CONSTELLATION_NAMES.get(r[0], r[0])} for r in cur.fetchall()]

    conn.close()

    return render_template("search.html",
                           results=results,
                           total=total,
                           pages=pages,
                           page=page,
                           q=q,
                           otype=otype,
                           const=const,
                           diff_max=diff_max,
                           mag_max=mag_max,
                           sort=sort,
                           constellations=constellations)


@app.route("/object/<path:designation>")
def object_detail(designation):
    # Support /object/M31 → lookup by Messier number
    m = re.match(r'^[Mm](\d{1,3})$', designation)
    if m:
        conn = db()
        cur  = conn.cursor()
        cur.execute("SELECT designation FROM objects WHERE messier_number = ?", (int(m.group(1)),))
        row = cur.fetchone()
        conn.close()
        if row:
            return redirect(url_for("object_detail", designation=row[0].replace(" ", "-")))
        abort(404)

    # Normalize: NGC-224 → NGC 224
    designation = designation.replace("-", " ").upper()

    conn = db()
    cur  = conn.cursor()
    cur.execute("SELECT * FROM objects WHERE designation = ?", (designation,))
    obj = enrich(row_to_dict(cur.fetchone()))
    if obj is None:
        conn.close()
        abort(404)

    # Related objects: same constellation, similar type, bright
    cur.execute("""
        SELECT * FROM objects
        WHERE constellation = ? AND id != ?
          AND object_type = ? AND magnitude_v IS NOT NULL
        ORDER BY magnitude_v
        LIMIT 6
    """, (obj.get("constellation"), obj["id"], obj.get("object_type")))
    related = [enrich(row_to_dict(r)) for r in cur.fetchall()]

    # Same Messier sequence neighbors
    prev_m = next_m = None
    if obj.get("messier_number"):
        mn = obj["messier_number"]
        cur.execute("SELECT designation, messier_number, common_name FROM objects WHERE messier_number = ?", (mn - 1,))
        prev_m = row_to_dict(cur.fetchone())
        cur.execute("SELECT designation, messier_number, common_name FROM objects WHERE messier_number = ?", (mn + 1,))
        next_m = row_to_dict(cur.fetchone())

    conn.close()

    # Build Aladin target string
    aladin_target = obj.get("designation", "")

    return render_template("object.html",
                           obj=obj,
                           related=related,
                           prev_m=prev_m,
                           next_m=next_m,
                           aladin_target=aladin_target)


@app.route("/browse")
@app.route("/browse/<category>")
def browse(category=None):
    conn = db()
    cur  = conn.cursor()

    if category == "messier":
        cur.execute("SELECT * FROM objects WHERE messier_number IS NOT NULL ORDER BY messier_number")
        items = [enrich(row_to_dict(r)) for r in cur.fetchall()]
        title = "Messier Catalogue"
        subtitle = f"All {len(items)} Messier objects in the NGC/IC catalog"

    elif category == "galaxies":
        cur.execute("""SELECT * FROM objects WHERE object_type IN ('G','GPair','GGroup','GClstr')
                       AND magnitude_v IS NOT NULL ORDER BY magnitude_v LIMIT 200""")
        items = [enrich(row_to_dict(r)) for r in cur.fetchall()]
        title = "Galaxies"
        subtitle = "Sorted by brightness (top 200)"

    elif category == "globulars":
        cur.execute("""SELECT * FROM objects WHERE object_type = 'GCl'
                       AND magnitude_v IS NOT NULL ORDER BY magnitude_v""")
        items = [enrich(row_to_dict(r)) for r in cur.fetchall()]
        title = "Globular Clusters"
        subtitle = f"{len(items)} globular clusters"

    elif category == "open-clusters":
        cur.execute("""SELECT * FROM objects WHERE object_type IN ('OCl','OC+N','Cl+N','Ast')
                       AND magnitude_v IS NOT NULL ORDER BY magnitude_v""")
        items = [enrich(row_to_dict(r)) for r in cur.fetchall()]
        title = "Open Clusters & Asterisms"
        subtitle = f"{len(items)} objects"

    elif category == "nebulae":
        cur.execute("""SELECT * FROM objects WHERE object_type IN ('Neb','RNe','EmN','HII','SNR','OC+N','Cl+N')
                       AND magnitude_v IS NOT NULL ORDER BY magnitude_v""")
        items = [enrich(row_to_dict(r)) for r in cur.fetchall()]
        title = "Nebulae"
        subtitle = f"{len(items)} emission, reflection, and HII regions"

    elif category == "planetary":
        cur.execute("""SELECT * FROM objects WHERE object_type = 'PN'
                       AND magnitude_v IS NOT NULL ORDER BY magnitude_v""")
        items = [enrich(row_to_dict(r)) for r in cur.fetchall()]
        title = "Planetary Nebulae"
        subtitle = f"{len(items)} planetary nebulae"

    elif category == "tonight":
        cur.execute("""
            SELECT * FROM objects
            WHERE best_months LIKE ? AND magnitude_v IS NOT NULL
              AND difficulty <= 4
            ORDER BY magnitude_v
            LIMIT 100
        """, (f"%{CURRENT_MONTH}%",))
        items = [enrich(row_to_dict(r)) for r in cur.fetchall()]
        title = f"Tonight's Sky — {CURRENT_MONTH}"
        subtitle = f"Best objects visible in {CURRENT_MONTH} (mag ≤ browsing limit)"

    elif category == "easy":
        cur.execute("""SELECT * FROM objects WHERE difficulty <= 2
                       AND magnitude_v IS NOT NULL ORDER BY magnitude_v""")
        items = [enrich(row_to_dict(r)) for r in cur.fetchall()]
        title = "Naked Eye & Binocular Objects"
        subtitle = f"{len(items)} objects requiring no telescope"

    else:
        # Overview page
        cur.execute("""
            SELECT constellation,
                   COUNT(*) as total,
                   MIN(magnitude_v) as brightest,
                   SUM(CASE WHEN messier_number IS NOT NULL THEN 1 ELSE 0 END) as messier_count
            FROM objects
            WHERE constellation IS NOT NULL AND magnitude_v IS NOT NULL
            GROUP BY constellation
            ORDER BY constellation
        """)
        constellations = [row_to_dict(r) for r in cur.fetchall()]
        for c in constellations:
            abbr = c.get("constellation") or ""
            c["constellation_name"] = CONSTELLATION_NAMES.get(abbr, abbr)
        conn.close()
        return render_template("browse.html",
                               category=None,
                               constellations=constellations)

    conn.close()
    return render_template("browse.html",
                           category=category,
                           items=items,
                           title=title,
                           subtitle=subtitle)


@app.route("/constellation/<const>")
def constellation(const):
    const = const.title()
    conn  = db()
    cur   = conn.cursor()
    cur.execute("""SELECT * FROM objects WHERE constellation = ?
                   AND magnitude_v IS NOT NULL ORDER BY magnitude_v""", (const,))
    items = [enrich(row_to_dict(r)) for r in cur.fetchall()]
    conn.close()
    if not items:
        abort(404)
    const_name = CONSTELLATION_NAMES.get(const, const)
    return render_template("browse.html",
                           category="constellation",
                           items=items,
                           title=f"Objects in {const_name}",
                           subtitle=f"{len(items)} objects with known magnitude in {const_name}")


@app.route("/random")
def random_obj():
    conn = db()
    cur  = conn.cursor()
    cur.execute("SELECT designation FROM objects WHERE magnitude_v IS NOT NULL ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    conn.close()
    if row:
        return redirect(url_for("object_detail",
                                designation=row[0].replace(" ", "-")))
    abort(404)


@app.route("/api/autocomplete")
def autocomplete():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])

    conn = db()
    cur  = conn.cursor()

    results = []
    # Exact Messier
    m = re.match(r'^[Mm]\s*(\d{1,3})$', q)
    if m:
        cur.execute("SELECT designation, messier_number, common_name, object_type_label FROM objects WHERE messier_number = ?", (int(m.group(1)),))
    else:
        like = f"%{q}%"
        cur.execute("""
            SELECT designation, messier_number, common_name, object_type_label
            FROM objects
            WHERE designation LIKE ? OR common_name LIKE ? OR common_names_raw LIKE ?
            ORDER BY magnitude_v IS NULL, magnitude_v
            LIMIT 10
        """, (like, like, like))

    for r in cur.fetchall():
        label = r["designation"]
        if r["messier_number"]:
            label = f"M{r['messier_number']} / {label}"
        if r["common_name"]:
            label += f" — {r['common_name']}"
        results.append({
            "label": label,
            "value": r["designation"],
            "type":  r["object_type_label"],
            "url":   url_for("object_detail", designation=r["designation"].replace(" ", "-")),
        })
    conn.close()

    # Solar system objects — matched against the query string
    q_lower = q.lower()
    ss_base = url_for("solar_system_page")
    for name, data in {**ss.PLANETS, **ss.DWARF_PLANETS}.items():
        if q_lower in name.lower():
            slug = name.lower().replace(" ", "-")
            results.append({
                "label": f"{data.get('symbol', '')} {name} — {data['type']}".strip(),
                "value": name,
                "type":  data["type"],
                "url":   f"{ss_base}#planet-{slug}",
            })
    for name in ss.COMETS:
        if q_lower in name.lower():
            results.append({
                "label": f"☄ {name} — Comet",
                "value": name,
                "type":  "Comet",
                "url":   f"{ss_base}#comets",
            })
    for name in ss._TLE_URLS:
        if q_lower in name.lower():
            results.append({
                "label": f"🛰 {name} — Earth Satellite",
                "value": name,
                "type":  "Earth Satellite",
                "url":   f"{ss_base}#satellites",
            })

    return jsonify(results)


@app.route("/api/stats")
def api_stats():
    conn = db()
    cur  = conn.cursor()
    cur.execute("""
        SELECT object_type_label, COUNT(*) as count
        FROM objects GROUP BY object_type_label ORDER BY count DESC LIMIT 15
    """)
    types = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]
    conn.close()
    return jsonify(types)


# ── Image proxy (caches NASA SkyView images locally) ─────────────────────────

@app.route("/api/thumb/<path:slug>")
def thumb_proxy(slug):
    size = request.args.get("size", "sm")
    px   = 400 if size == "lg" else 160

    # Normalize slug to designation
    designation = slug.replace("-", " ", 1)   # "NGC-224" → "NGC 224"

    cache_file = os.path.join(THUMB_CACHE, f"{slug}_{size}.jpg")

    # Serve from cache if available
    if os.path.exists(cache_file):
        return send_file(cache_file, mimetype="image/jpeg")

    # Look up RA/Dec and FOV
    conn = db()
    cur  = conn.cursor()
    cur.execute("SELECT ra_deg, dec_deg, major_axis_arcmin FROM objects WHERE designation = ?",
                (designation,))
    row = cur.fetchone()
    conn.close()

    if not row or row["ra_deg"] is None:
        abort(404)

    ra   = row["ra_deg"]
    dec  = row["dec_deg"]
    major = row["major_axis_arcmin"] or 10.0
    fov  = max(0.08, min(4.0, major * 3.0 / 60.0))

    # Fetch image (serialize per-slug to avoid duplicate downloads)
    with _thumb_lock:
        # Double-check cache after acquiring lock
        if os.path.exists(cache_file):
            return send_file(cache_file, mimetype="image/jpeg")

        img_data = fetch_thumb(ra, dec, fov, px)
        if not img_data:
            abort(404)

        with open(cache_file, "wb") as f:
            f.write(img_data)

    return send_file(cache_file, mimetype="image/jpeg")


# ── Location / Settings ───────────────────────────────────────────────────────

@app.route("/api/geocode")
def api_geocode():
    """Geocode a place name via Nominatim (OpenStreetMap)."""
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "No query provided"}), 400

    url = ("https://nominatim.openstreetmap.org/search?"
           + urllib.parse.urlencode({"q": q, "format": "json", "limit": 5,
                                     "addressdetails": 1}))
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "DeepSkyObservatory/1.0 (astronomy app)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            results = json.loads(resp.read())
    except Exception as e:
        return jsonify({"error": str(e)}), 502

    places = []
    for r in results:
        places.append({
            "name":    r.get("display_name", ""),
            "lat":     float(r["lat"]),
            "lon":     float(r["lon"]),
            "type":    r.get("type", ""),
        })
    return jsonify(places)


@app.route("/api/location", methods=["GET", "POST", "DELETE"])
def api_location():
    settings = load_settings()
    if request.method == "GET":
        return jsonify(settings.get("location"))

    if request.method == "DELETE":
        settings.pop("location", None)
        save_settings(settings)
        return jsonify({"ok": True})

    # POST — save location
    data = request.get_json(force=True)
    try:
        lat  = float(data["lat"])
        lon  = float(data["lon"])
        name = str(data.get("name", f"{lat:.3f}, {lon:.3f}"))[:120]
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Invalid payload"}), 400

    settings["location"] = {"lat": lat, "lon": lon, "name": name}
    save_settings(settings)
    return jsonify({"ok": True, "location": settings["location"]})


@app.route("/api/altaz")
def api_altaz():
    """Return current altitude/azimuth for an object given observer's location."""
    try:
        ra_deg  = float(request.args["ra"])
        dec_deg = float(request.args["dec"])
    except (KeyError, ValueError):
        return jsonify({"error": "ra and dec required"}), 400

    settings = load_settings()
    loc = settings.get("location")
    if not loc:
        return jsonify({"error": "No location set"}), 404

    lat, lon = loc["lat"], loc["lon"]
    alt, az  = calc_altaz(ra_deg, dec_deg, lat, lon)
    info     = transit_info(ra_deg, dec_deg, lat, lon)

    return jsonify({
        "altitude":      alt,
        "azimuth":       az,
        "above_horizon": alt > 0,
        "transit_alt":   info["transit_alt"],
        "is_circumpolar":info["is_circumpolar"],
        "is_never_rises":info["is_never_rises"],
        "rise_az":       info["rise_az"],
        "set_az":        info["set_az"],
        "location":      loc["name"],
    })


@app.route("/solar-system")
def solar_system_page():
    loc     = load_settings()
    lat     = loc.get("latitude")
    lon     = loc.get("longitude")
    planets = ss.get_all_planets(lat, lon)
    moon    = ss.get_moon_phase()
    sun     = ss.get_sun_data(lat, lon)
    comets  = ss.get_all_comets(lat, lon)
    sats    = ss.get_all_satellites(lat, lon)
    return render_template("solar_system.html",
                           planets=planets,
                           moon=moon,
                           sun=sun,
                           comets=comets,
                           satellites=sats,
                           location=loc)


@app.route("/settings")
def settings_page():
    settings = load_settings()
    return render_template("settings.html", settings=settings)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=False)
