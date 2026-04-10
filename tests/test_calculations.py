"""
Tests for astronomical calculation functions in app.py.
These are pure math functions with known outputs — fast, no DB needed.
"""
import math
import datetime
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app


# ── julian_date ───────────────────────────────────────────────────────────────

def test_julian_date_j2000():
    """J2000.0 epoch: 2000-01-01 12:00 UTC should be JD 2451545.0"""
    dt = datetime.datetime(2000, 1, 1, 12, 0, 0)
    jd = app.julian_date(dt)
    assert abs(jd - 2451545.0) < 0.0001


def test_julian_date_known():
    """2024-01-01 00:00 UTC → JD 2460310.5"""
    dt = datetime.datetime(2024, 1, 1, 0, 0, 0)
    jd = app.julian_date(dt)
    assert abs(jd - 2460310.5) < 0.001


# ── calc_altaz ────────────────────────────────────────────────────────────────

def test_calc_altaz_returns_tuple():
    """calc_altaz should return a 2-tuple of floats."""
    result = app.calc_altaz(0, 0, 0, 0)
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_calc_altaz_altitude_range():
    """Altitude must be in [-90, 90]."""
    for ra in range(0, 360, 30):
        for dec in (-45, 0, 45):
            alt, az = app.calc_altaz(ra, dec, 40, -75)
            assert -90 <= alt <= 90, f"alt={alt} out of range for ra={ra}, dec={dec}"


def test_calc_altaz_azimuth_range():
    """Azimuth must be in [0, 360]."""
    for ra in range(0, 360, 30):
        alt, az = app.calc_altaz(ra, 0, 40, -75)
        assert 0 <= az <= 360, f"az={az} out of range for ra={ra}"


def test_calc_altaz_north_pole_circumpolar():
    """Polaris (dec ~89.3°) from lat 45°N should always be well above horizon."""
    # RA=37.95, Dec=89.26 (Polaris)
    alts = []
    for h in range(0, 24):
        dt = datetime.datetime(2024, 6, 1, h, 0, 0)
        alt, _ = app.calc_altaz(37.95, 89.26, 45.0, -93.0, dt)
        alts.append(alt)
    assert all(a > 30 for a in alts), f"Polaris dipped below 30° at lat 45N: {alts}"


def test_calc_altaz_southern_object_never_rises():
    """An object at dec -80° should never rise from lat +45°N."""
    alts = []
    for h in range(0, 24):
        dt = datetime.datetime(2024, 6, 1, h, 0, 0)
        alt, _ = app.calc_altaz(0, -80, 45.0, -93.0, dt)
        alts.append(alt)
    assert all(a < 0 for a in alts), f"Object at dec-80 rose above horizon: {alts}"


def test_calc_altaz_equator_object():
    """An object on the celestial equator (dec=0) from the equator (lat=0)
    should reach ~90° altitude at transit."""
    # At equator, dec=0 object transits at zenith (alt~90)
    # We test with a fixed dt where LST ≈ RA to catch transit
    dt = datetime.datetime(2024, 3, 20, 12, 0, 0)   # near vernal equinox noon
    max_alt = max(
        app.calc_altaz(ra, 0, 0, 0, dt)[0]
        for ra in range(0, 360, 15)
    )
    assert max_alt > 85, f"Max alt from equator for dec=0 object: {max_alt}"


# ── transit_info ──────────────────────────────────────────────────────────────

def test_transit_info_polaris_circumpolar():
    """Polaris should be circumpolar from lat 45°N."""
    info = app.transit_info(37.95, 89.26, 45.0, -93.0)
    assert info["is_circumpolar"] is True
    assert info["is_never_rises"] is False


def test_transit_info_never_rises():
    """Object at dec -80° should never rise from lat 45°N."""
    info = app.transit_info(0, -80, 45.0, -93.0)
    assert info["is_never_rises"] is True
    assert info["is_circumpolar"] is False


def test_transit_info_altitude_range():
    """Transit altitude must be in [-90, 90]."""
    for dec in range(-85, 86, 10):
        info = app.transit_info(0, dec, 40.0, -75.0)
        assert -90 <= info["transit_alt"] <= 90


def test_transit_info_rise_set_azimuths():
    """Rise azimuth should be < 180, set azimuth should be > 180 (for equatorial objects)."""
    info = app.transit_info(0, 0, 40.0, -75.0)
    assert 0 < info["rise_az"] < 180
    assert 180 < info["set_az"] < 360


# ── enrich ────────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_obj():
    return {
        "designation":        "NGC 224",
        "common_name":        "Andromeda Galaxy",
        "object_type":        "G",
        "object_type_label":  "spiral galaxy",
        "constellation":      "And",
        "ra_deg":             10.68,
        "dec_deg":            41.27,
        "magnitude_v":        3.44,
        "major_axis_arcmin":  190.0,
        "minor_axis_arcmin":  60.0,
        "difficulty":         1,
        "best_months":        "Oct Nov Dec",
        "distance_ly":        2.537e6,
        "messier_number":     31,
        "hubble_type":        "SA(s)b",
        "position_angle":     None,
        "surface_brightness": None,
        "id":                 1,
    }


def test_enrich_returns_dict(sample_obj):
    result = app.enrich(sample_obj)
    assert isinstance(result, dict)


def test_enrich_none_returns_none():
    assert app.enrich(None) is None


def test_enrich_constellation_name(sample_obj):
    result = app.enrich(sample_obj)
    assert result["constellation_name"] == "Andromeda"


def test_enrich_unknown_constellation(sample_obj):
    sample_obj["constellation"] = "XYZ"
    result = app.enrich(sample_obj)
    assert result["constellation_name"] == "XYZ"   # falls back to raw value


def test_enrich_type_icon(sample_obj):
    result = app.enrich(sample_obj)
    assert result["type_icon"] == "galaxy"


def test_enrich_difficulty_label(sample_obj):
    result = app.enrich(sample_obj)
    assert result["diff_label"] == "Naked Eye"
    assert result["diff_color"] == "success"


def test_enrich_difficulty_unknown(sample_obj):
    sample_obj["difficulty"] = 99
    result = app.enrich(sample_obj)
    assert result["diff_label"] == "Unknown"


def test_enrich_distance_billions(sample_obj):
    sample_obj["distance_ly"] = 2.5e9
    result = app.enrich(sample_obj)
    assert "billion" in result["distance_fmt"]


def test_enrich_distance_millions(sample_obj):
    result = app.enrich(sample_obj)   # 2.537e6 ly
    assert "million" in result["distance_fmt"]


def test_enrich_distance_thousands(sample_obj):
    sample_obj["distance_ly"] = 25000
    result = app.enrich(sample_obj)
    assert "thousand" in result["distance_fmt"]


def test_enrich_distance_none(sample_obj):
    sample_obj["distance_ly"] = None
    result = app.enrich(sample_obj)
    assert result["distance_fmt"] is None


def test_enrich_size_fmt(sample_obj):
    result = app.enrich(sample_obj)
    assert "190" in result["size_fmt"]
    assert "60" in result["size_fmt"]


def test_enrich_thumb_urls(sample_obj):
    result = app.enrich(sample_obj)
    assert result["thumb_url"] is not None
    assert "NGC-224" in result["thumb_url"]


def test_enrich_thumb_urls_missing_coords(sample_obj):
    sample_obj["ra_deg"] = None
    result = app.enrich(sample_obj)
    assert result["thumb_url"] is None


def test_enrich_image_fov_minimum(sample_obj):
    sample_obj["major_axis_arcmin"] = 0   # no size info
    result = app.enrich(sample_obj)
    assert result["image_fov"] == 0.4    # default FOV


def test_enrich_image_fov_large_object(sample_obj):
    """FOV should be capped at 5 degrees for huge objects."""
    sample_obj["major_axis_arcmin"] = 500
    result = app.enrich(sample_obj)
    assert result["image_fov"] <= 5.0


# ── constellation name mapping ────────────────────────────────────────────────

def test_constellation_names_completeness():
    """All abbreviations returned by the DB should be in the mapping."""
    known_abbrs = [
        "And","Ant","Aps","Aql","Aqr","Ara","Ari","Aur","Boo",
        "CMa","CMi","CVn","Cae","Cam","Cap","Car","Cas","Cen",
        "Cep","Cet","Cha","Cir","Cnc","Col","Com","CrA","CrB",
        "Crt","Cru","Crv","Cyg","Del","Dor","Dra","Equ","Eri",
        "For","Gem","Gru","Her","Hor","Hya","Hyi","Ind","LMi",
        "Lac","Leo","Lep","Lib","Lup","Lyn","Lyr","Men","Mic",
        "Mon","Mus","Nor","Oct","Oph","Ori","Pav","Peg","Per",
        "Phe","Pic","PsA","Psc","Pup","Pyx","Ret","Scl","Sco",
        "Sct","Se1","Se2","Sex","Sge","Sgr","Tau","Tel","TrA",
        "Tri","Tuc","UMa","UMi","Vel","Vir","Vol","Vul",
    ]
    for abbr in known_abbrs:
        assert abbr in app.CONSTELLATION_NAMES, f"Missing: {abbr}"


def test_constellation_names_no_abbreviations_in_values():
    """Values should be full names — not still in 3-letter IAU format.
    Exceptions: Ara (3) and Leo (3) are legitimately short constellation names."""
    KNOWN_SHORT = {"Ara", "Leo"}
    still_abbr = [
        k for k, v in app.CONSTELLATION_NAMES.items()
        if len(v) <= 3 and k not in KNOWN_SHORT
    ]
    assert still_abbr == [], f"These look like un-expanded abbreviations: {still_abbr}"
