"""
Geocode Persons — Match person birth_location against locations table,
set birth_lat/birth_lng coordinates.

Run locally:  python geo/geocode_persons.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import db


def geocode():
    db.init_db()
    conn = db.get_conn()

    # Get all persons without coordinates
    persons = conn.execute(
        """SELECT id, name, birth_location
           FROM persons
           WHERE birth_location != ''
             AND (birth_lat IS NULL OR birth_lat = 0)"""
    ).fetchall()

    if not persons:
        print("No persons need geocoding.")
        conn.close()
        return 0

    # Get locations lookup
    locations = conn.execute(
        "SELECT name, lat, lng FROM locations"
    ).fetchall()

    # Build lookup dict (lowercase for fuzzy matching)
    loc_map = {}
    for loc in locations:
        loc_map[loc["name"].lower()] = (loc["lat"], loc["lng"])

    # Also check townland_boundaries centroids
    townlands = conn.execute(
        "SELECT name, centroid_lat, centroid_lng FROM townland_boundaries "
        "WHERE centroid_lat != 0"
    ).fetchall()
    for t in townlands:
        loc_map[t["name"].lower()] = (t["centroid_lat"], t["centroid_lng"])

    matched = 0
    for p in persons:
        birth_loc = p["birth_location"].lower().strip()

        # Try exact match first
        coords = loc_map.get(birth_loc)

        # Try partial match (birth_location contains a known townland)
        if not coords:
            for loc_name, loc_coords in loc_map.items():
                if loc_name in birth_loc or birth_loc in loc_name:
                    coords = loc_coords
                    break

        if coords:
            conn.execute(
                "UPDATE persons SET birth_lat = ?, birth_lng = ? WHERE id = ?",
                (coords[0], coords[1], p["id"])
            )
            matched += 1
            print(f"  + {p['name']}: {p['birth_location']} -> ({coords[0]}, {coords[1]})")
        else:
            print(f"  ? {p['name']}: '{p['birth_location']}' — no match found")

    conn.commit()
    conn.close()
    print(f"\nDone: {matched}/{len(persons)} persons geocoded.")
    return matched


if __name__ == "__main__":
    geocode()
