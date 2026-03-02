"""
Prepare Townlands — Download and filter townland boundaries for Carrigtwohill parish.

This script:
1. Downloads the Cork county GeoJSON from townlands.ie bulk downloads
2. Filters to Carrigtwohill (Carrigtohill) civil parish
3. Calculates centroids for each townland
4. Inserts boundaries into the DB
5. Writes a static fallback to static/data/townlands.geojson

Usage:
    python geo/prepare_townlands.py

Prerequisites:
    pip install requests

Notes:
    - The townlands.ie bulk download uses "Carrigtohill" spelling
    - Data is ODbL licensed (Open Database License)
    - Run this once to populate the DB, then the web app uses the DB data
    - If the bulk download is unavailable, you can use the existing
      static/data/townlands.geojson placeholder instead
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import db

# URL for Cork county townland boundaries from townlands.ie
# (GeoJSON format, ~20MB for all of Cork)
CORK_GEOJSON_URL = "https://www.townlands.ie/page/downloads/cork-townlands.geojson"

# Alternative: OSM Overpass API query for Carrigtwohill parish townlands
OVERPASS_QUERY = """
[out:json][timeout:60];
area["name"="Carrigtohill"]["boundary"="civil_parish"]->.parish;
(
  relation["boundary"="townland"](area.parish);
);
out body;
>;
out skel qt;
"""

PARISH_NAME = "Carrigtohill"  # spelling used by townlands.ie and OSM

STATIC_OUTPUT = Path(__file__).parent.parent / "static" / "data" / "townlands.geojson"


def load_from_file(filepath):
    """Load a pre-downloaded GeoJSON file and filter to our parish."""
    print(f"Loading from {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    parish_features = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        # townlands.ie uses 'CP' or 'CIVIL_PARISH' field
        parish = (
            props.get("CP", "") or
            props.get("CIVIL_PARISH", "") or
            props.get("parish", "")
        )
        if parish.lower() == PARISH_NAME.lower():
            parish_features.append(feature)

    print(f"Found {len(parish_features)} townlands in {PARISH_NAME} parish")
    return parish_features


def calculate_centroid(geometry):
    """Simple centroid calculation for a polygon."""
    coords = geometry.get("coordinates", [[]])
    if geometry["type"] == "MultiPolygon":
        # Use first polygon's exterior ring
        ring = coords[0][0] if coords and coords[0] else []
    elif geometry["type"] == "Polygon":
        ring = coords[0] if coords else []
    else:
        return 0, 0

    if not ring:
        return 0, 0

    lng_sum = sum(c[0] for c in ring)
    lat_sum = sum(c[1] for c in ring)
    n = len(ring)
    return round(lat_sum / n, 6), round(lng_sum / n, 6)


def insert_features(features):
    """Insert townland features into the database."""
    db.init_db()
    inserted = 0
    for feature in features:
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        centroid_lat, centroid_lng = calculate_centroid(geometry)

        name = props.get("name", props.get("NAME", "Unknown"))

        data = {
            "name": name,
            "name_irish": props.get("name_irish", props.get("NAME_GA", "")),
            "area_acres": float(props.get("area_acres", props.get("AREA_ACRES", 0))),
            "county": "Cork",
            "barony": props.get("barony", props.get("BARONY", "Barrymore")),
            "parish": "Carrigtwohill",
            "geometry_json": json.dumps(geometry),
            "centroid_lat": centroid_lat,
            "centroid_lng": centroid_lng,
            "logainm_id": props.get("logainm_id", props.get("LOGAINM_ID", "")),
        }

        is_new, _ = db.insert_townland_boundary(data)
        if is_new:
            inserted += 1
            print(f"  + {name} ({centroid_lat}, {centroid_lng})")
        else:
            print(f"  = {name} already exists")

    print(f"\nInserted {inserted} townland boundaries.")
    return inserted


def write_static_fallback(features):
    """Write filtered features to static GeoJSON file."""
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    STATIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(STATIC_OUTPUT, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)
    print(f"Static fallback written to {STATIC_OUTPUT}")


def main():
    print("=" * 60)
    print("  Carrigtwohill Townland Boundary Preparation")
    print("=" * 60)
    print()
    print("This script expects a pre-downloaded Cork county GeoJSON file.")
    print("Download from: https://www.townlands.ie/page/download/")
    print()

    # Check for local file
    local_files = list(Path(__file__).parent.glob("*cork*townland*.*json*"))
    if local_files:
        features = load_from_file(local_files[0])
    else:
        print("No local Cork GeoJSON file found in geo/ directory.")
        print("Please download the Cork townlands GeoJSON from townlands.ie")
        print("and place it in the geo/ directory, then re-run this script.")
        print()
        print("Alternatively, you can manually populate the database using")
        print("the web admin or the seed_pois.py script.")
        return

    if features:
        insert_features(features)
        write_static_fallback(features)
    else:
        print("No matching townlands found.")


if __name__ == "__main__":
    main()
