#!/usr/bin/env python3
"""
Astronomy Database Builder
Builds a SQLite database of Messier and NGC/IC objects from the OpenNGC catalog.
Includes computed fields useful for backyard astronomers.
"""

import sqlite3
import csv
import urllib.request
import os
import re

DB_PATH  = os.path.join(os.path.dirname(__file__), "astronomy.db")
CSV_URL  = "https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/NGC.csv"
ADD_URL  = "https://raw.githubusercontent.com/mattiaverga/OpenNGC/master/database_files/addendum.csv"

# ── Messier observer notes ────────────────────────────────────────────────────
MESSIER_NOTES = {
    1:  "Supernova remnant; easy in small scopes, even shows filaments in 8\"+.",
    2:  "One of the largest globulars; resolves well in 6\" scope.",
    3:  "Showpiece globular, resolves to centre in 8\".",
    4:  "Nearest globular cluster; very loose, easy to resolve.",
    5:  "Magnificent globular, rivals M13; resolves well in 6\".",
    6:  "Open cluster shaped like a butterfly; best in binoculars.",
    7:  "Brilliant naked-eye open cluster; spectacular in binoculars.",
    8:  "Bright emission nebula; visible naked-eye from dark sky. Use OIII/H-beta filter.",
    9:  "Globular near the galactic centre; small and compact.",
    10: "Bright globular; forms a pair with nearby M12.",
    11: "Rich, fan-shaped open cluster; one of the finest open clusters.",
    12: "Loose globular cluster; easy to resolve.",
    13: "Finest northern globular cluster; stunning in any telescope.",
    14: "Large, remote globular; faint and grainy in small scopes.",
    15: "Dense globular; contains the planetary nebula Pease 1.",
    16: "Emission nebula with famous 'Pillars of Creation'; cluster easy in binoculars.",
    17: "Bright swan-shaped emission nebula; spectacular in any scope.",
    18: "Sparse open cluster; best viewed at low power.",
    19: "Oblate globular; noticeably non-circular.",
    20: "Trifid Nebula; three-lobed emission nebula split by dark lanes.",
    21: "Young open cluster close to the Trifid Nebula.",
    22: "Outstanding southern globular; one of the finest in the sky.",
    23: "Rich open cluster; best with low power.",
    24: "Dense Milky Way star cloud; spectacular in binoculars.",
    25: "Bright open cluster containing a Cepheid variable star.",
    26: "Compact open cluster; faint background.",
    27: "Dumbbell Nebula — largest, brightest planetary nebula; easy in binoculars.",
    28: "Compact globular near M22.",
    29: "Small, sparse open cluster in Cygnus.",
    30: "Compact globular; central condensation visible in 4\".",
    31: "Andromeda Galaxy — nearest spiral galaxy; naked-eye object. Huge angular size.",
    32: "Dwarf elliptical companion to M31; appears as a fuzzy star in binoculars.",
    33: "Triangulum Galaxy — face-on spiral; very low surface brightness, needs dark sky.",
    34: "Bright open cluster; lovely in binoculars.",
    35: "Rich open cluster; distant cluster NGC 2158 visible in same field.",
    36: "One of three Auriga clusters; medium richness.",
    37: "Richest of the Auriga open clusters.",
    38: "Open cluster with a pi-shaped outline; slightly looser than M36/37.",
    39: "Large, sparse open cluster; best in binoculars or at very low power.",
    40: "Double star, not a true deep-sky object.",
    41: "Bright open cluster south of Sirius; visible naked-eye.",
    42: "Orion Nebula — finest nebula in the sky. Trapezium visible in 3\".",
    43: "Small detached knot of the Orion Nebula complex.",
    44: "Beehive Cluster — large naked-eye open cluster; best in binoculars.",
    45: "Pleiades — famous naked-eye cluster. Nebulosity visible in dark skies.",
    46: "Rich open cluster; contains planetary nebula NGC 2438 on its edge.",
    47: "Bright, coarse open cluster near M46; dramatic contrast in same FOV.",
    48: "Large open cluster in Hydra; easy in binoculars.",
    49: "Brightest Virgo Cluster galaxy; elliptical, featureless.",
    50: "Heart-shaped open cluster; best at low power.",
    51: "Whirlpool Galaxy — classic face-on spiral. Spiral arms visible in 8\"+.",
    52: "Rich open cluster in Cassiopeia; lovely in low-power eyepiece.",
    53: "Remote globular; small and compact in most scopes.",
    54: "Remote globular; actually belongs to the Sagittarius Dwarf Galaxy.",
    55: "Large, loose southern globular; easy to resolve.",
    56: "Globular between Cygnus and Lyra; compact.",
    57: "Ring Nebula — classic ring-shaped planetary nebula; visible in 3\".",
    58: "Barred spiral in Virgo Cluster; brightest Virgo spiral.",
    59: "Elliptical galaxy in Virgo Cluster.",
    60: "Giant elliptical in Virgo Cluster; NGC 4647 in same field.",
    61: "Face-on barred spiral; spiral arms visible in 10\"+.",
    62: "Globular with irregular core offset toward galactic centre.",
    63: "Sunflower Galaxy — elongated spiral with mottled arms.",
    64: "Black Eye Galaxy — striking dark dust lane visible in 4\"+.",
    65: "First of the Leo Triplet; elongated spiral.",
    66: "Largest of Leo Triplet; distorted spiral.",
    67: "One of the oldest open clusters (10 billion yrs); rich and compact.",
    68: "Globular cluster in Hydra; faint and remote.",
    69: "Compact southern globular; best from lower latitudes.",
    70: "Compact southern globular very close to M69.",
    71: "Loose globular (once thought an open cluster); easy in 4\".",
    72: "Remote, faint globular; challenging in small scopes.",
    73: "Asterism of 4 stars; not a true cluster.",
    74: "Face-on spiral; very low surface brightness — needs dark sky and large aperture.",
    75: "Remote, compact globular; distant and small.",
    76: "Little Dumbbell Nebula — faint planetary; needs 6\"+ to see well.",
    77: "Seyfert galaxy with active galactic nucleus; compact and bright core.",
    78: "Brightest reflection nebula in Orion; best with wide-field eyepiece.",
    79: "Isolated globular in Lepus; well away from main galactic globulars.",
    80: "Dense, compact globular in Scorpius; bright core.",
    81: "Bode's Galaxy — grand spiral in Ursa Major; beautiful with M82 in same FOV.",
    82: "Cigar/Starburst Galaxy — irregular with dramatic dust lanes. Pair with M81.",
    83: "Southern Pinwheel — face-on barred spiral; spiral arms in 8\"+.",
    84: "Lenticular galaxy in Markarian's Chain; elliptical appearance.",
    85: "Lenticular galaxy at north end of Virgo Cluster.",
    86: "Lenticular galaxy in Markarian's Chain; forms a pair with M84.",
    87: "Giant elliptical galaxy; relativistic jet only in very large scopes/imaging.",
    88: "Multi-arm spiral in Virgo Cluster; elongated.",
    89: "Elliptical galaxy; nearly circular, featureless.",
    90: "Only Messier galaxy with a blueshift — approaching the Milky Way.",
    91: "Barred spiral; long-disputed identity, now confirmed as NGC 4548.",
    92: "Fine globular in Hercules; often overlooked next to M13.",
    93: "Bright arrowhead-shaped open cluster in Puppis.",
    94: "Compact spiral with very bright nucleus and inner ring; easy in 4\".",
    95: "Barred spiral in Leo; bar visible in 8\"+.",
    96: "Dominant spiral in the M96 group.",
    97: "Owl Nebula — large faint planetary; needs dark sky and 8\"+ to see owl eyes.",
    98: "Edge-on spiral in Virgo Cluster; elongated.",
    99: "Face-on spiral in Virgo Cluster; faint arms.",
    100:"Grand design face-on spiral; one of the largest Virgo Cluster spirals.",
    101:"Pinwheel Galaxy — large face-on spiral; very low surface brightness.",
    102:"Spindle Galaxy — edge-on lenticular with dust lane.",
    103:"Open cluster in Cassiopeia; small and compressed.",
    104:"Sombrero Galaxy — stunning edge-on spiral with dark dust lane, visible in 4\".",
    105:"Round elliptical galaxy in Leo; forms group with M95 and M96.",
    106:"Bright spiral with anomalous extra spiral arms visible in long exposures.",
    107:"Loose globular in Ophiuchus; easy in 4\".",
    108:"Edge-on spiral near Owl Nebula; irregular, mottled appearance.",
    109:"Barred spiral in Ursa Major; bar visible in 8\".",
    110:"Dwarf elliptical companion to M31; larger and fainter than M32.",
}

# ── Object type map ───────────────────────────────────────────────────────────
TYPE_LABELS = {
    "G":    "Galaxy",
    "GX":   "Galaxy",
    "Gx":   "Galaxy",
    "GPair":"Galaxy Pair",
    "GGroup":"Galaxy Group",
    "GClstr":"Galaxy Cluster",
    "OC":   "Open Cluster",
    "OCl":  "Open Cluster",
    "GC":   "Globular Cluster",
    "GCl":  "Globular Cluster",
    "Cl+N": "Cluster with Nebula",
    "OC+N": "Open Cluster + Nebula",
    "PN":   "Planetary Nebula",
    "SNR":  "Supernova Remnant",
    "Neb":  "Nebula",
    "RNe":  "Reflection Nebula",
    "EmN":  "Emission Nebula",
    "HII":  "HII Region",
    "Ast":  "Asterism",
    "D*":   "Double Star",
    "**":   "Double Star",
    "*":    "Star",
    "*Ass": "Stellar Association",
    "MwPt": "Milky Way Part",
    "EmObj":"Emission Object",
    "Other":"Other",
    "Dup":  "Duplicate Entry",
    "NotFound":"Not Found",
}

# ── Helper functions ──────────────────────────────────────────────────────────

def float_or_none(val):
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        v = str(val).strip()
        return float(v) if v else None
    except (ValueError, AttributeError):
        return None

def int_or_none(val):
    try:
        if val is None:
            return None
        if isinstance(val, int):
            return val
        v = str(val).strip()
        return int(v) if v else None
    except (ValueError, AttributeError):
        return None

def ra_to_decimal(ra_str):
    """HH:MM:SS.s → decimal degrees"""
    try:
        h, m, s = ra_str.split(":")
        return round((float(h) + float(m)/60 + float(s)/3600) * 15, 6)
    except Exception:
        return None

def dec_to_decimal(dec_str):
    """±DD:MM:SS.s → decimal degrees"""
    try:
        sign = -1 if dec_str.startswith("-") else 1
        parts = dec_str.lstrip("+-").split(":")
        d, m, s = float(parts[0]), float(parts[1]), float(parts[2])
        return round(sign * (d + m/60 + s/3600), 6)
    except Exception:
        return None

def best_months(ra_str):
    """
    Returns a string like 'Oct–Dec' for when the object transits at midnight.
    RA 0h → objects culminate at midnight around Sep 22.
    Each 2h of RA ≈ 1 calendar month later.
    """
    try:
        h, m, s = ra_str.split(":")
        ra_h = float(h) + float(m)/60 + float(s)/3600
        month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                       "Jul","Aug","Sep","Oct","Nov","Dec"]
        # RA 0h peaks ~Sep 22 (month index 8.7)
        peak = (ra_h / 2.0 + 8.7) % 12
        start = int(peak - 1) % 12
        end   = int(peak + 1) % 12
        return f"{month_names[start]}–{month_names[end]}"
    except Exception:
        return None

def min_aperture_mm(obj_type, mag_v):
    """Suggested minimum aperture (mm) to see the object."""
    mag = float_or_none(mag_v)
    if mag is None:
        return None
    t = (obj_type or "").upper()
    if "GC" in t or t in ("GCL", "GCl"):
        if mag < 7:  return 50
        if mag < 9:  return 80
        return 150
    if "OC" in t or t in ("OCL", "OCl", "AST", "Ast"):
        if mag < 5:  return 0   # naked eye
        if mag < 8:  return 50
        return 100
    if t in ("PN",):
        if mag < 8:  return 80
        if mag < 11: return 150
        return 200
    if t in ("SNR",):
        if mag < 7:  return 50
        return 150
    if "G" in t:  # galaxy variants
        if mag < 9:  return 80
        if mag < 11: return 150
        return 250
    if "NEB" in t or "HII" in t or "EMN" in t or "RNE" in t:
        if mag < 6:  return 50
        if mag < 9:  return 100
        return 150
    if mag < 5:  return 0
    if mag < 8:  return 50
    if mag < 11: return 100
    return 200

def difficulty(mag_v):
    """
    Observing difficulty rating:
    1 = naked eye, 2 = binoculars, 3 = small scope (3–4"),
    4 = medium scope (6–8"), 5 = large scope (10"+)
    """
    mag = float_or_none(mag_v)
    if mag is None:   return None
    if mag <= 4.5:    return 1
    if mag <= 7.0:    return 2
    if mag <= 9.5:    return 3
    if mag <= 12.0:   return 4
    return 5

def distance_ly(pax_mas, redshift_val):
    """Best-effort distance in light-years."""
    p = float_or_none(pax_mas)
    if p and p > 0:
        pc = 1000.0 / p
        return round(pc * 3.26156, 1)
    z = float_or_none(redshift_val)
    if z and z > 0.0001:
        H0 = 70.0
        mpc = (z * 299792.458) / H0
        return round(mpc * 3.26156e6, 0)
    return None

def parse_name(name):
    """Returns (catalog, number) from e.g. 'NGC0224' → ('NGC', 224)"""
    m = re.match(r'^(NGC|IC)0*(\d+)([A-Z]?)$', name.strip())
    if m:
        return m.group(1), int(m.group(2))
    return None, None

# ── Schema ────────────────────────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    catalog             TEXT NOT NULL,      -- 'NGC' or 'IC'
    catalog_number      INTEGER,
    designation         TEXT UNIQUE,        -- 'NGC 224', 'IC 1805', etc.
    messier_number      INTEGER,            -- NULL if not a Messier object
    common_name         TEXT,               -- popular/common name
    object_type         TEXT,               -- short code from OpenNGC
    object_type_label   TEXT,               -- human-readable label
    constellation       TEXT,               -- IAU 3-letter abbreviation
    ra                  TEXT,               -- HH:MM:SS.s
    dec                 TEXT,               -- ±DD:MM:SS.s
    ra_deg              REAL,               -- decimal degrees (0–360)
    dec_deg             REAL,               -- decimal degrees (-90 to +90)
    magnitude_b         REAL,               -- Blue band magnitude
    magnitude_v         REAL,               -- Visual magnitude (key for observers)
    surface_brightness  REAL,               -- mag/arcsec², lower = easier to see
    major_axis_arcmin   REAL,               -- angular size, major axis (arcminutes)
    minor_axis_arcmin   REAL,               -- angular size, minor axis (arcminutes)
    position_angle      REAL,               -- degrees E of N
    hubble_type         TEXT,               -- Hubble classification (galaxies)
    distance_ly         REAL,               -- estimated distance in light-years
    redshift            REAL,               -- cosmological redshift z
    radial_velocity_kms REAL,               -- km/s (negative = approaching)
    best_months         TEXT,               -- e.g. 'Oct–Dec' (best viewing window)
    min_aperture_mm     INTEGER,            -- suggested minimum aperture (mm)
    difficulty          INTEGER,            -- 1=naked eye … 5=large scope
    cstar_mag_v         REAL,               -- central star V magnitude (planetary nebulae)
    messier_notes       TEXT,               -- observer tips for Messier objects
    identifiers         TEXT,               -- cross-IDs (2MASS, UGC, PGC, etc.)
    common_names_raw    TEXT,               -- raw common names from OpenNGC
    ned_notes           TEXT,
    openngc_notes       TEXT
);

CREATE INDEX IF NOT EXISTS idx_messier   ON objects(messier_number);
CREATE INDEX IF NOT EXISTS idx_type      ON objects(object_type);
CREATE INDEX IF NOT EXISTS idx_const     ON objects(constellation);
CREATE INDEX IF NOT EXISTS idx_mag_v     ON objects(magnitude_v);
CREATE INDEX IF NOT EXISTS idx_ra        ON objects(ra_deg);
CREATE INDEX IF NOT EXISTS idx_dec       ON objects(dec_deg);
CREATE INDEX IF NOT EXISTS idx_catalog   ON objects(catalog, catalog_number);
CREATE INDEX IF NOT EXISTS idx_difficulty ON objects(difficulty);

-- ── Views for common queries ─────────────────────────────────────────────────

-- All Messier objects ordered by number
CREATE VIEW IF NOT EXISTS messier_objects AS
    SELECT messier_number AS M, designation, common_name,
           object_type_label AS type, constellation AS const,
           ra, dec, magnitude_v AS mag, major_axis_arcmin AS size_arcmin,
           distance_ly, best_months, min_aperture_mm AS min_ap_mm,
           difficulty, messier_notes AS observer_notes
    FROM objects
    WHERE messier_number IS NOT NULL
    ORDER BY messier_number;

-- Objects visible with naked eye or binoculars (difficulty 1-2)
CREATE VIEW IF NOT EXISTS easy_targets AS
    SELECT designation, messier_number AS M, common_name,
           object_type_label AS type, constellation AS const,
           magnitude_v AS mag, major_axis_arcmin AS size_arcmin,
           best_months, difficulty
    FROM objects
    WHERE difficulty <= 2 AND magnitude_v IS NOT NULL
    ORDER BY magnitude_v;

-- Showpiece objects — best targets for each type up to mag 10
CREATE VIEW IF NOT EXISTS showpieces AS
    SELECT designation, messier_number AS M, common_name,
           object_type_label AS type, constellation AS const,
           magnitude_v AS mag, major_axis_arcmin AS size_arcmin,
           best_months, min_aperture_mm AS min_ap_mm, distance_ly
    FROM objects
    WHERE magnitude_v <= 10.0
    ORDER BY magnitude_v;

-- Best objects per constellation
CREATE VIEW IF NOT EXISTS best_by_constellation AS
    SELECT constellation AS const,
           designation, messier_number AS M, common_name,
           object_type_label AS type,
           magnitude_v AS mag, best_months
    FROM objects
    WHERE magnitude_v IS NOT NULL AND magnitude_v <= 11
    ORDER BY constellation, magnitude_v;

-- Galaxy groups / notable galaxies
CREATE VIEW IF NOT EXISTS galaxies AS
    SELECT designation, messier_number AS M, common_name,
           constellation AS const, magnitude_v AS mag,
           major_axis_arcmin AS size_arcmin, hubble_type,
           distance_ly, radial_velocity_kms AS radvel_kms,
           best_months, min_aperture_mm AS min_ap_mm
    FROM objects
    WHERE object_type IN ('G','Gx','GPair','GGroup','GClstr')
       OR object_type_label = 'Galaxy'
    ORDER BY magnitude_v;

-- Globular clusters
CREATE VIEW IF NOT EXISTS globular_clusters AS
    SELECT designation, messier_number AS M, common_name,
           constellation AS const, magnitude_v AS mag,
           major_axis_arcmin AS size_arcmin, distance_ly,
           best_months, min_aperture_mm AS min_ap_mm
    FROM objects
    WHERE object_type IN ('GC','GCl','GCL')
    ORDER BY magnitude_v;

-- Open clusters
CREATE VIEW IF NOT EXISTS open_clusters AS
    SELECT designation, messier_number AS M, common_name,
           constellation AS const, magnitude_v AS mag,
           major_axis_arcmin AS size_arcmin,
           best_months, min_aperture_mm AS min_ap_mm
    FROM objects
    WHERE object_type IN ('OC','OCl','OCL','OC+N','Cl+N','Ast')
    ORDER BY magnitude_v;

-- Nebulae (emission, reflection, planetary, SNR)
CREATE VIEW IF NOT EXISTS nebulae AS
    SELECT designation, messier_number AS M, common_name,
           object_type_label AS type,
           constellation AS const, magnitude_v AS mag,
           major_axis_arcmin AS size_arcmin,
           best_months, min_aperture_mm AS min_ap_mm
    FROM objects
    WHERE object_type IN ('PN','SNR','Neb','RNe','EmN','HII','EmObj','Cl+N','OC+N')
    ORDER BY magnitude_v;

-- Seasonal planning view (objects by best viewing month)
CREATE VIEW IF NOT EXISTS seasonal_targets AS
    SELECT best_months AS season,
           designation, messier_number AS M, common_name,
           object_type_label AS type,
           constellation AS const, magnitude_v AS mag,
           min_aperture_mm AS min_ap_mm, difficulty
    FROM objects
    WHERE best_months IS NOT NULL
      AND magnitude_v <= 12
    ORDER BY best_months, magnitude_v;
"""

INSERT_SQL = """
INSERT OR IGNORE INTO objects (
    catalog, catalog_number, designation, messier_number, common_name,
    object_type, object_type_label, constellation,
    ra, dec, ra_deg, dec_deg,
    magnitude_b, magnitude_v, surface_brightness,
    major_axis_arcmin, minor_axis_arcmin, position_angle,
    hubble_type, distance_ly, redshift, radial_velocity_kms,
    best_months, min_aperture_mm, difficulty,
    cstar_mag_v, messier_notes, identifiers, common_names_raw,
    ned_notes, openngc_notes
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""

def process_row(row):
    raw_name = row.get("Name", "").strip()
    if not raw_name:
        return None

    catalog, num = parse_name(raw_name)
    if catalog is None:
        # Handle non-standard entries (WNC, Mel, etc.) — skip for now
        return None

    designation = f"{catalog} {num}"

    obj_type  = row.get("Type","").strip() or None
    type_label = TYPE_LABELS.get(obj_type, obj_type)

    ra  = row.get("RA","").strip()  or None
    dec = row.get("Dec","").strip() or None

    mag_b  = float_or_none(row.get("B-Mag",""))
    mag_v  = float_or_none(row.get("V-Mag",""))
    surfbr = float_or_none(row.get("SurfBr",""))
    major  = float_or_none(row.get("MajAx",""))
    minor  = float_or_none(row.get("MinAx",""))
    posang = float_or_none(row.get("PosAng",""))
    hubble = row.get("Hubble","").strip() or None
    pax    = row.get("Pax","").strip()    or None
    radvel = float_or_none(row.get("RadVel",""))
    z      = float_or_none(row.get("Redshift",""))
    const  = row.get("Const","").strip()  or None
    idents = row.get("Identifiers","").strip()   or None
    cnames = row.get("Common names","").strip()  or None
    ned_n  = row.get("NED notes","").strip()     or None
    ongc_n = row.get("OpenNGC notes","").strip() or None
    m_col  = row.get("M","").strip()             or None

    # Central star magnitude for planetary nebulae
    cs_v   = float_or_none(row.get("Cstar V-Mag",""))

    ra_deg  = ra_to_decimal(ra)   if ra  else None
    dec_deg = dec_to_decimal(dec) if dec else None

    # Messier number — use catalog's M column
    m_num = int_or_none(m_col)

    # Common name: prefer curated note's name if Messier, else catalog names
    common = cnames

    # Computed fields
    best_m = best_months(ra)    if ra   else None
    min_ap = min_aperture_mm(obj_type, mag_v)
    diff   = difficulty(mag_v)
    dist   = distance_ly(pax, z)

    # Observer notes for Messier objects
    m_notes = MESSIER_NOTES.get(m_num) if m_num else None

    return (
        catalog, num, designation, m_num, common,
        obj_type, type_label, const,
        ra, dec, ra_deg, dec_deg,
        mag_b, mag_v, surfbr,
        major, minor, posang,
        hubble, dist, z, radvel,
        best_m, min_ap, diff,
        cs_v, m_notes, idents, cnames,
        ned_n, ongc_n
    )

def download(url, dest):
    if os.path.exists(dest):
        print(f"  Using cached: {os.path.basename(dest)}")
        return
    print(f"  Downloading {os.path.basename(dest)} ...", end=" ", flush=True)
    urllib.request.urlretrieve(url, dest)
    print("done")

def main():
    base = os.path.dirname(__file__)
    ngc_csv = os.path.join(base, "NGC.csv")
    add_csv = os.path.join(base, "addendum.csv")

    print("=" * 50)
    print("  Astronomy Database Builder")
    print("=" * 50)

    print("\n[1/4] Downloading catalogs...")
    download(CSV_URL, ngc_csv)
    download(ADD_URL, add_csv)

    print("\n[2/4] Creating database...")
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.commit()

    print(f"\n[3/4] Loading objects...")
    records = []
    skipped = 0

    for csv_path in [ngc_csv, add_csv]:
        fname = os.path.basename(csv_path)
        if not os.path.exists(csv_path):
            continue
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                rec = process_row(row)
                if rec:
                    records.append(rec)
                else:
                    skipped += 1

    conn.executemany(INSERT_SQL, records)
    conn.commit()
    print(f"  Loaded  : {len(records):,} objects")
    print(f"  Skipped : {skipped:,} (duplicates, stars, non-standard)")

    print("\n[4/4] Computing statistics...")
    cur = conn.cursor()

    def count(where=""):
        q = f"SELECT COUNT(*) FROM objects{' WHERE '+where if where else ''}"
        return cur.execute(q).fetchone()[0]

    print(f"\n{'='*50}")
    print(f"  DATABASE SUMMARY")
    print(f"{'='*50}")
    n_total  = count()
    n_ngc    = count("catalog='NGC'")
    n_ic     = count("catalog='IC'")
    n_m      = count("messier_number IS NOT NULL")
    n_gx     = count("object_type='G'")
    n_gc     = count("object_type='GCl'")
    n_oc     = count("object_type='OCl'")
    n_pn     = count("object_type='PN'")
    n_neb    = count("object_type IN ('HII','EmN','Neb')")
    n_d1     = count("difficulty=1")
    n_d2     = count("difficulty=2")
    n_d3     = count("difficulty=3")
    n_d4     = count("difficulty=4")
    n_d5     = count("difficulty=5")
    print(f"  Total objects         : {n_total:>7,}")
    print(f"  NGC objects           : {n_ngc:>7,}")
    print(f"  IC objects            : {n_ic:>7,}")
    print(f"  Messier objects       : {n_m:>7,}")
    print(f"  Galaxies              : {n_gx:>7,}")
    print(f"  Globular clusters     : {n_gc:>7,}")
    print(f"  Open clusters         : {n_oc:>7,}")
    print(f"  Planetary nebulae     : {n_pn:>7,}")
    print(f"  Emission/HII nebulae  : {n_neb:>7,}")
    print(f"  Naked-eye targets     : {n_d1:>7,}")
    print(f"  Binocular targets     : {n_d2:>7,}")
    print(f"  Small scope (3-4in)   : {n_d3:>7,}")
    print(f"  Medium scope (6-8in)  : {n_d4:>7,}")
    print(f"  Large scope (10in+)   : {n_d5:>7,}")
    print(f"{'='*50}")

    conn.close()
    print(f"\n  Saved to: {DB_PATH}")
    print(f"\n  Quick start queries:")
    print(f"    sqlite3 astronomy.db '.headers on' '.mode column'")
    print(f"    sqlite3 astronomy.db 'SELECT * FROM messier_objects LIMIT 10;'")
    print(f"    sqlite3 astronomy.db 'SELECT * FROM showpieces LIMIT 20;'")
    print(f"    sqlite3 astronomy.db \"SELECT * FROM best_by_constellation WHERE const='Ori';\"")
    print(f"    sqlite3 astronomy.db 'SELECT * FROM easy_targets;'")
    print(f"    sqlite3 astronomy.db \"SELECT * FROM seasonal_targets WHERE season LIKE '%Apr%';\"")
    print()

if __name__ == "__main__":
    main()
