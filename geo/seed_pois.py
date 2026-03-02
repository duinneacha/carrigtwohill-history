"""
Seed POIs — Populate the pois table with known Carrigtwohill landmarks.

Run locally:  python geo/seed_pois.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import db

POIS = [
    {
        "name": "Barryscourt Castle",
        "description": "Anglo-Norman tower house, seat of the Barry family. "
                       "Built c.1177, extensively renovated 15th-16th century. "
                       "Now in state care (OPW).",
        "poi_type": "castle",
        "lat": 51.9047,   # OSM way, verified
        "lng": -8.2593,
        "era_start": 1177,
        "era_end": None,
        "era_label": "Norman to present",
        "townland": "Barryscourt",
        "source_url": "https://heritageireland.ie/places-to-visit/barryscourt-castle/",
    },
    {
        "name": "Franciscan Abbey (Carrigtwohill Friary)",
        "description": "Founded c.1350 by the Barry family for Franciscan friars. "
                       "Dissolved during the Reformation. Ruins still visible.",
        "poi_type": "abbey",
        "lat": 51.9106,   # OSM 'Franciscan Friary' ruins, verified
        "lng": -8.2597,
        "era_start": 1350,
        "era_end": 1650,
        "era_label": "Medieval",
        "townland": "Carrigtohill",
        "source_url": "",
    },
    {
        "name": "St Mary's RC Church",
        "description": "Roman Catholic parish church, built 1826. "
                       "Centre of the Carrigtwohill parish community.",
        "poi_type": "church",
        "lat": 51.9103,   # OSM 'St.Marys Church' way, verified
        "lng": -8.2606,
        "era_start": 1826,
        "era_end": None,
        "era_label": "19th century to present",
        "townland": "Carrigtohill",
        "source_url": "",
    },
    {
        "name": "Carrigtwohill Railway Station",
        "description": "Opened 1859 on the Cork-Youghal line. "
                       "Reopened for commuter services in 2009.",
        "poi_type": "site",
        "lat": 51.9163,   # OSM railway=station node, verified
        "lng": -8.2634,
        "era_start": 1859,
        "era_end": None,
        "era_label": "Victorian to present",
        "townland": "Carrigtohill",
        "source_url": "",
    },
    {
        "name": "Fota House & Gardens",
        "description": "Regency-style country house, built c.1820 by the Smith-Barry family. "
                       "Now a heritage property with arboretum and gardens.",
        "poi_type": "house",
        "lat": 51.8939,   # OSM 'Fota House' way, verified
        "lng": -8.3038,
        "era_start": 1820,
        "era_end": None,
        "era_label": "Regency to present",
        "townland": "Foaty",
        "source_url": "https://fotahouse.com",
    },
    {
        "name": "Carrigtwohill GAA Grounds",
        "description": "Home of Carrigtwohill GAA club, founded 1886. "
                       "Active in hurling and football in Cork county.",
        "poi_type": "site",
        "lat": 51.9078,   # OSM 'Carrigtwohill GAA' way, verified
        "lng": -8.2647,
        "era_start": 1886,
        "era_end": None,
        "era_label": "Victorian to present",
        "townland": "Carrigtohill",
        "source_url": "",
    },
    {
        "name": "Abbey Graveyard",
        "description": "Historic burial ground adjacent to the Franciscan Abbey ruins. "
                       "Contains burials from medieval to 19th century.",
        "poi_type": "graveyard",
        "lat": 51.9107,   # OSM grave_yard way, adjacent to Friary ruins, verified
        "lng": -8.2596,
        "era_start": 1350,
        "era_end": None,
        "era_label": "Medieval to 19th century",
        "townland": "Carrigtohill",
        "source_url": "",
    },
]


def seed():
    db.init_db()
    inserted = 0
    existed = 0
    for poi in POIS:
        is_new, pid = db.insert_poi(poi)
        if is_new:
            inserted += 1
            print(f"  + {poi['name']} (id={pid})")
        else:
            existed += 1
            print(f"  = {poi['name']} already exists (id={pid})")

    print(f"\nDone: {inserted} inserted, {existed} already existed.")
    return inserted, existed


if __name__ == "__main__":
    seed()
