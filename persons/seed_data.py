"""
Carrigtwohill Notable Persons — Seed Data
==========================================
Hand-verified notable persons with documented Carrigtwohill connections.
Each entry has been researched and cross-referenced against primary/secondary sources.

Categories:
  - 'native'     : Born in or from Carrigtwohill
  - 'historical'  : Historical figure tied to the area
  - 'diaspora'    : Descendant of Carrigtwohill emigrants
  - 'living'      : Currently alive (privacy considerations apply)

Tiers:
  1 = Internationally notable
  2 = Nationally notable
  3 = Regionally / historically notable
"""

SEED_PERSONS = [
    # ── TIER 2 — Nationally Notable ─────────────────────────────────────────

    {
        "name": "Dáibhí Ó Bruadair",
        "birth_year": "1625",
        "death_year": "1698",
        "birth_location": "Barrymore, County Cork",
        "death_location": "Knockraha, County Cork",
        "connection": (
            "One of the greatest Irish language poets. Born in the barony of "
            "Barrymore, which encompasses Carrigtwohill. In his poetry he "
            "referred to Barrymore as 'tír mo bhuinphréimhe' — 'the land of "
            "my original stock'. The surname 'O Brodir' appears frequently "
            "in Barrymore in the 1659 Census."
        ),
        "bio": (
            "Dáibhí Ó Bruadair (c.1625–1698) was among the most significant "
            "Irish language poets of the late seventeenth century. His work "
            "spanned elegies, satires, and political verse, documenting the "
            "decline of the Gaelic order under Cromwellian and Williamite rule. "
            "He received patronage from both Irish and Anglo-Irish families in "
            "Cork and Limerick. His poetry remains a primary historical source "
            "for understanding 17th-century Ireland."
        ),
        "notable_for": "Major Irish language poet of the 17th century Jacobite era",
        "tier": 2,
        "confidence": "high",
        "category": "native",
        "country_of_residence": "Ireland",
        "wikidata_id": "Q1148206",
        "wikipedia_url": "https://en.wikipedia.org/wiki/D%C3%A1ibh%C3%AD_%C3%93_Bruadair",
        "sources_json": [
            "https://www.dib.ie/biography/o-bruadair-daibhidh-daibhi-a6282",
            "https://en.wikipedia.org/wiki/D%C3%A1ibh%C3%AD_%C3%93_Bruadair",
            "https://cartlann.org/authors/daibhi-o-bruadair/",
        ],
    },

    {
        "name": "Garrett Standish Barry",
        "birth_year": "1790",
        "death_year": "1864",
        "birth_location": "Leamlara, Barrymore, County Cork",
        "death_location": "Leamlara, County Cork",
        "connection": (
            "First Catholic Member of Parliament elected for County Cork "
            "after the Catholic Emancipation Act of 1829. His estate at "
            "Leamlara (over 2,500 acres) lay within the Carrigtwohill area "
            "of the Barrymore barony. Contemporary and associate of "
            "Daniel O'Connell."
        ),
        "bio": (
            "Garrett Standish Barry (c.1790–1864) was an Irish landowner and "
            "politician. A member of the ancient de Barry family of Barrymore, "
            "he was elected MP for County Cork in 1832 following Catholic "
            "Emancipation, serving until 1841. He was a significant figure "
            "in the post-Emancipation political landscape of Munster. "
            "He died without issue; his estate passed to his brother "
            "Henry Standish Barry."
        ),
        "notable_for": "First Catholic MP for County Cork after Emancipation (1832–1841)",
        "tier": 2,
        "confidence": "high",
        "category": "native",
        "country_of_residence": "Ireland",
        "wikidata_id": "",
        "wikipedia_url": "",
        "sources_json": [
            "https://carrigtwohillparish.ie/history/parish-history/",
        ],
    },

    {
        "name": "Willie John Daly",
        "birth_year": "1925",
        "death_year": "2017",
        "birth_location": "Carrigtwohill, County Cork",
        "death_location": "County Cork",
        "connection": (
            "Born and raised in Carrigtwohill. Played club hurling with "
            "Carrigtwohill GAA. Won junior and two intermediate county "
            "titles with 'Carrig' from 1948 to 1950."
        ),
        "bio": (
            "Willie John Daly (1925–2017) was an Irish hurler who played "
            "as a centre-forward for the Cork senior team. He was the last "
            "surviving member of Cork's famous three-in-a-row All-Ireland "
            "winning team of 1952, 1953, and 1954, playing alongside the "
            "legendary Christy Ring. He also won Railway Cup medals in 1952 "
            "and 1955, two National Hurling League titles, and an All-Ireland "
            "junior crown in 1947. He later coached the Cork senior team, "
            "steering them to a league title in 1974."
        ),
        "notable_for": "Cork hurling legend; last survivor of the 1952–54 three-in-a-row team",
        "tier": 2,
        "confidence": "high",
        "category": "native",
        "country_of_residence": "Ireland",
        "wikidata_id": "Q8021606",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Willie_John_Daly",
        "sources_json": [
            "https://en.wikipedia.org/wiki/Willie_John_Daly",
            "https://www.echolive.ie/corksport/arid-40173381.html",
            "https://hoganstand.com/Article/Index/278693",
        ],
    },

    {
        "name": "Jimmy Kennedy",
        "birth_year": "1891",
        "death_year": "1973",
        "birth_location": "Carrigtwohill, County Cork",
        "death_location": "",
        "connection": (
            "Raised in Carrigtwohill. Played club hurling with Carrigtwohill "
            "GAA, winning a senior county championship in 1918. Captained "
            "Cork to the 1919 All-Ireland Senior Hurling Championship — one "
            "of three Carrigtwohill players on that team."
        ),
        "bio": (
            "Jimmy 'Major' Kennedy (1891–1973) was an Irish hurler who played "
            "as a full-forward for the Cork senior team. One of fourteen "
            "children, he was known as a massive, powerful full forward whose "
            "hurling was nimble and rounded. He captained Cork to the 1919 "
            "All-Ireland Senior Hurling Championship, with two other "
            "Carrigtwohill men — Ned 'Sailor' Grey and John O'Keeffe — also "
            "on the team. He was famously distinguished by the soft felt hat "
            "he always wore while playing."
        ),
        "notable_for": "Captain of Cork's 1919 All-Ireland winning hurling team",
        "tier": 2,
        "confidence": "high",
        "category": "native",
        "country_of_residence": "Ireland",
        "wikidata_id": "Q16067446",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Jimmy_Kennedy_(Cork_hurler)",
        "sources_json": [
            "https://en.wikipedia.org/wiki/Jimmy_Kennedy_(Cork_hurler)",
            "https://carrigtwohillgaa.com/content_page/10062621/",
        ],
    },

    {
        "name": "William Gerard Barry",
        "birth_year": "1864",
        "death_year": "1941",
        "birth_location": "Ballyadam, Carrigtwohill, County Cork",
        "death_location": "Saint-Jean-de-Luz, France",
        "connection": (
            "Born in Ballyadam, Carrigtwohill. Son of a local magistrate. "
            "Studied at Crawford School of Art in Cork before training in "
            "Paris at Academie Julian."
        ),
        "bio": (
            "William Gerard Barry (1864–1941) was an Irish painter born "
            "in Ballyadam, Carrigtwohill. He studied at Crawford School of "
            "Art under Henry Jones Thaddeus (1881–1883), then at Academie "
            "Julian in Paris under Le Febre, Boulanger and Carolus Duran. "
            "He received a Taylor prize from the Royal Dublin Society in "
            "1887. He travelled extensively in Europe, the United States, "
            "and Canada. His works are held by the Crawford Art Gallery, "
            "Cork, and the Smithsonian American Art Museum. He died during "
            "a bombing raid at his home in Saint-Jean-de-Luz, France, "
            "during World War II."
        ),
        "notable_for": "Irish painter; works held by Crawford Art Gallery and the Smithsonian",
        "tier": 2,
        "confidence": "high",
        "category": "native",
        "country_of_residence": "France",
        "wikidata_id": "",
        "wikipedia_url": "https://en.wikipedia.org/wiki/William_Gerard_Barry",
        "sources_json": [
            "https://en.wikipedia.org/wiki/William_Gerard_Barry",
            "https://americanart.si.edu/artist/gerard-barry-261",
            "https://crawfordartgallery.ie/wp-content/uploads/WilliamGerardBarrybio.pdf",
        ],
    },

    # ── TIER 3 — Regionally / Historically Notable ──────────────────────────

    {
        "name": "Ken Thompson",
        "birth_year": "",
        "death_year": "",
        "birth_location": "Cork City",
        "death_location": "",
        "connection": (
            "Founded the Barryscourt Trust in 1988, an American/Irish "
            "foundation to develop Barryscourt Castle in Carrigtwohill as "
            "a cultural and tourist centre. His sculpture work has deep "
            "ties to the heritage of the Carrigtwohill area."
        ),
        "bio": (
            "Ken Thompson is a Cork-based Irish sculptor and stone carver. "
            "A scion of the Thompson baking family of Cork City, he is "
            "self-taught and works primarily in stone, wood, and bronze. "
            "His notable commissions include the Air India memorial at "
            "Ahakista in West Cork, the statue of St Patrick at Lough Derg, "
            "the Stations of the Cross for St Mel's Cathedral in Longford, "
            "and the Innocent Victims Memorial at Westminster Abbey's Great "
            "West Door, unveiled by Queen Elizabeth in 1996. In 1988 he "
            "founded the Barryscourt Trust to develop Barryscourt Castle "
            "in Carrigtwohill."
        ),
        "notable_for": "Sculptor; Westminster Abbey commission; founder of Barryscourt Trust",
        "tier": 2,
        "confidence": "medium",
        "category": "historical",
        "privacy_flag": 1,
        "country_of_residence": "Ireland",
        "wikidata_id": "",
        "wikipedia_url": "",
        "sources_json": [
            "https://wildgoosestudio.com/collections/ken-thompson",
            "https://carrigtwohillcommunity.ie/localattracttions/barryscourt-castle/",
        ],
    },

    {
        "name": "Seánie O'Farrell",
        "birth_year": "1977",
        "death_year": "",
        "birth_location": "Carrigtwohill, County Cork",
        "death_location": "",
        "connection": (
            "Born in Carrigtwohill. Played club hurling with Carrigtwohill "
            "GAA, scoring the famous winning point in the 2011 county senior "
            "final. Also played with Imokilly divisional team."
        ),
        "bio": (
            "Seánie O'Farrell (born 1977) is an Irish hurler from "
            "Carrigtwohill. He played as a right corner-forward for the "
            "Cork senior team. He won an All-Ireland Minor Hurling "
            "Championship with Cork in 1995 and a National Hurling League "
            "medal at senior level. At club level he won championship "
            "medals with Imokilly (1997, 1998) and was central to "
            "Carrigtwohill's rise through the grades, including their "
            "premier intermediate title in 2007 (scoring three goals in "
            "the final) and their breakthrough to senior status."
        ),
        "notable_for": "Cork hurler; All-Ireland minor winner 1995; Carrigtwohill GAA legend",
        "tier": 3,
        "confidence": "high",
        "category": "living",
        "privacy_flag": 1,
        "country_of_residence": "Ireland",
        "wikidata_id": "Q17489769",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Se%C3%A1nie_O%27Farrell",
        "sources_json": [
            "https://en.wikipedia.org/wiki/Se%C3%A1nie_O%27Farrell",
            "https://www.echolive.ie/corksport/arid-40107041.html",
        ],
    },

    {
        "name": "Angie Benhaffaf",
        "birth_year": "",
        "death_year": "",
        "birth_location": "Carrigtwohill, County Cork",
        "death_location": "",
        "connection": (
            "From Carrigtwohill. Nationally recognised for her care of "
            "her twin sons Hassan and Hussein, born conjoined, through "
            "75 surgeries and their development into award-winning "
            "para-athletes representing Ireland."
        ),
        "bio": (
            "Angie Benhaffaf is from Carrigtwohill, County Cork. She was "
            "named Ireland's Family Carer of the Year 2025 by Family "
            "Carers Ireland for sixteen years of care for her twin sons "
            "Hassan and Hussein, who were born conjoined and sharing every "
            "organ except their hearts. The twins have become award-winning "
            "para-athletes who have represented Ireland internationally. "
            "Benhaffaf has also raised over EUR 105,000 for children's "
            "charities."
        ),
        "notable_for": "Family Carer of the Year 2025; mother of para-athlete conjoined twins",
        "tier": 3,
        "confidence": "high",
        "category": "living",
        "privacy_flag": 1,
        "country_of_residence": "Ireland",
        "wikidata_id": "",
        "wikipedia_url": "",
        "sources_json": [
            "https://www.rte.ie/news/2025/1127/1546175-carer-award/",
            "https://www.irishexaminer.com/news/munster/arid-41750688.html",
            "https://www.familycarers.ie/news-and-campaigns/news-press-releases/angie-benhaffaf-named-lidl-family-carer-of-the-year-2025/",
        ],
    },

    {
        "name": "The de Barry Family",
        "birth_year": "1177",
        "death_year": "",
        "birth_location": "Barrymore, County Cork",
        "death_location": "",
        "connection": (
            "Norman family who received Carrigtwohill lands from 1177. "
            "Founded the Franciscan Abbey c.1350. Their seat was "
            "Barryscourt Castle, which still stands in Carrigtwohill. "
            "The Barrymore barony is named after them."
        ),
        "bio": (
            "The de Barry (or Barry) family were an Anglo-Norman dynasty "
            "who settled in east Cork following the Norman invasion of "
            "Ireland in 1169. They received lands in the Carrigtwohill "
            "area from approximately 1177 and established Barryscourt "
            "Castle as their principal seat. They founded the Franciscan "
            "Abbey in Carrigtwohill around 1350. The barony of Barrymore "
            "takes its name from the family. Their descendants include "
            "Garrett Standish Barry MP and the wider Barry family of "
            "east Cork."
        ),
        "notable_for": "Norman founders of Carrigtwohill; builders of Barryscourt Castle",
        "tier": 3,
        "confidence": "high",
        "category": "historical",
        "country_of_residence": "Ireland",
        "wikidata_id": "",
        "wikipedia_url": "https://en.wikipedia.org/wiki/Barry_(surname)#Ireland",
        "sources_json": [
            "https://en.wikipedia.org/wiki/Barryscourt_Castle",
        ],
    },
]


def seed_persons_table(db_module):
    """
    Insert SEED_PERSONS into the persons table.
    Skips entries where a person with the same name already exists.
    Returns (total_seeded, already_existed).
    """
    import json

    conn = db_module.get_conn()
    seeded = 0
    existed = 0

    for p in SEED_PERSONS:
        # Check if already exists
        existing = conn.execute(
            "SELECT id FROM persons WHERE name = ?", (p["name"],)
        ).fetchone()

        if existing:
            existed += 1
            continue

        conn.execute(
            """INSERT INTO persons
               (name, birth_year, death_year, birth_location, death_location,
                connection, bio, sources, tier, confidence, category,
                privacy_flag, country_of_residence, notable_for,
                wikidata_id, wikipedia_url)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                p["name"],
                p.get("birth_year", ""),
                p.get("death_year", ""),
                p.get("birth_location", ""),
                p.get("death_location", ""),
                p.get("connection", ""),
                p.get("bio", ""),
                json.dumps(p.get("sources_json", [])),
                p.get("tier", 3),
                p.get("confidence", "medium"),
                p.get("category", "historical"),
                p.get("privacy_flag", 0),
                p.get("country_of_residence", ""),
                p.get("notable_for", ""),
                p.get("wikidata_id", ""),
                p.get("wikipedia_url", ""),
            ),
        )
        seeded += 1

    conn.commit()
    conn.close()
    return seeded, existed
