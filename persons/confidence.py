"""
Carrigtwohill Notable Persons — Confidence Scoring
====================================================
Grades the reliability of a claimed Carrigtwohill connection.

Levels:
  HIGH   — Direct primary source names Carrigtwohill explicitly
  MEDIUM — Secondary source or townland ambiguity
  LOW    — Surname match only, no specific townland evidence

Each factor contributes a score from 0.0 to 1.0.
Final confidence is the weighted average mapped to high/medium/low.
"""

from dataclasses import dataclass

# ── Scoring thresholds ───────────────────────────────────────────────────────

HIGH_THRESHOLD = 0.65
MEDIUM_THRESHOLD = 0.40


# ── Factor weights ───────────────────────────────────────────────────────────

WEIGHTS = {
    "primary_source":      0.30,  # Parish register, census, estate papers
    "townland_specificity": 0.25,  # Named Carrigtwohill vs 'County Cork'
    "source_count":        0.15,  # Number of independent confirming sources
    "temporal_evidence":   0.15,  # Dates align with known records
    "family_corroboration": 0.15,  # Other family members also documented
}


@dataclass
class ConfidenceAssessment:
    """Result of a confidence evaluation."""
    level: str          # 'high', 'medium', 'low'
    score: float        # 0.0 – 1.0
    factors: dict       # individual factor scores
    rationale: str      # human-readable explanation


def _score_primary_source(person: dict) -> float:
    """
    How strong is the primary source evidence?
    1.0 = Parish register, civil record, census entry naming Carrigtwohill
    0.7 = Wikipedia with citations to primary sources
    0.4 = Secondary source (newspaper, local history book)
    0.2 = Ancestry.com member tree with some citations
    0.0 = No source provided
    """
    sources = person.get("sources", "[]")
    if isinstance(sources, str):
        import json
        try:
            sources = json.loads(sources)
        except (json.JSONDecodeError, TypeError):
            sources = []

    if not sources:
        return 0.0

    score = 0.0
    for src in sources:
        src_lower = src.lower() if isinstance(src, str) else ""
        # Primary source indicators
        if any(k in src_lower for k in [
            "registers.nli.ie", "irishgenealogy.ie",
            "census.nationalarchives.ie", "titheapplotmentbooks"
        ]):
            score = max(score, 1.0)
        elif any(k in src_lower for k in [
            "dib.ie", "wikipedia.org", "wikidata.org"
        ]):
            score = max(score, 0.7)
        elif any(k in src_lower for k in [
            "irishexaminer.com", "echolive.ie", "irishtimes.com",
            "rte.ie", "thejournal.ie"
        ]):
            score = max(score, 0.5)
        elif any(k in src_lower for k in [
            "ancestry.com", "familysearch.org", "findmypast"
        ]):
            score = max(score, 0.3)
        else:
            score = max(score, 0.2)

    return min(score, 1.0)


def _score_townland_specificity(person: dict) -> float:
    """
    How specific is the geographic claim?
    1.0 = Named townland within Carrigtwohill parish
    0.8 = Named 'Carrigtwohill' directly
    0.5 = Named 'Barrymore barony' (which includes Carrigtwohill)
    0.3 = Named 'East Cork' or 'County Cork'
    0.0 = No location specified
    """
    connection = (person.get("connection", "") + " " +
                  person.get("birth_location", "")).lower()

    carrigtwohill_townlands = [
        "ballyadam", "tullagreen", "terrysland", "castleredmond",
        "knockraha", "leamlara", "barryscourt", "carrigtwohill",
        "carrigtohill", "carrig", "woodstock",
    ]

    for t in carrigtwohill_townlands:
        if t in connection:
            return 1.0 if t != "carrigtwohill" and t != "carrigtohill" else 0.9

    if "carrigtwohill" in connection or "carrigtohill" in connection:
        return 0.9
    if "barrymore" in connection:
        return 0.5
    if "east cork" in connection:
        return 0.3
    if "cork" in connection:
        return 0.2
    return 0.0


def _score_source_count(person: dict) -> float:
    """
    How many independent sources confirm the connection?
    3+ sources = 1.0
    2 sources  = 0.7
    1 source   = 0.4
    0 sources  = 0.0
    """
    sources = person.get("sources", "[]")
    if isinstance(sources, str):
        import json
        try:
            sources = json.loads(sources)
        except (json.JSONDecodeError, TypeError):
            sources = []

    count = len(sources)
    if count >= 3:
        return 1.0
    elif count == 2:
        return 0.7
    elif count == 1:
        return 0.4
    return 0.0


def _score_temporal_evidence(person: dict) -> float:
    """
    Do the dates align with known Carrigtwohill records?
    1.0 = Birth/death years match parish register range (1776–1922)
    0.7 = Dates are plausible but not in register range
    0.3 = Only approximate dates
    0.0 = No dates at all
    """
    birth = person.get("birth_year", "")
    death = person.get("death_year", "")

    if not birth and not death:
        return 0.0

    try:
        by = int(birth) if birth else None
        dy = int(death) if death else None
    except ValueError:
        return 0.3

    # Parish register range
    if by and 1776 <= by <= 1922:
        return 1.0
    if dy and 1776 <= dy <= 1922:
        return 0.8
    if by or dy:
        return 0.7
    return 0.3


def _score_family_corroboration(person: dict) -> float:
    """
    Are other family members also documented in Carrigtwohill?
    This is a placeholder for Phase 2 when the graph layer exists.
    For now, check if the bio/connection mentions family members.
    """
    text = (person.get("connection", "") + " " + person.get("bio", "")).lower()

    family_indicators = [
        "son of", "daughter of", "married", "children",
        "brother", "sister", "father", "mother",
        "family", "descendants", "estate passed to",
    ]

    matches = sum(1 for ind in family_indicators if ind in text)

    if matches >= 3:
        return 0.8
    elif matches >= 2:
        return 0.6
    elif matches >= 1:
        return 0.4
    return 0.0


def assess_confidence(person: dict) -> ConfidenceAssessment:
    """
    Evaluate the confidence level of a person's Carrigtwohill connection.

    Args:
        person: dict with keys matching the persons table schema

    Returns:
        ConfidenceAssessment with level, score, factors, and rationale
    """
    factors = {
        "primary_source":       _score_primary_source(person),
        "townland_specificity":  _score_townland_specificity(person),
        "source_count":          _score_source_count(person),
        "temporal_evidence":     _score_temporal_evidence(person),
        "family_corroboration":  _score_family_corroboration(person),
    }

    # Weighted average
    total_score = sum(
        factors[k] * WEIGHTS[k] for k in WEIGHTS
    )

    # Map to level
    if total_score >= HIGH_THRESHOLD:
        level = "high"
    elif total_score >= MEDIUM_THRESHOLD:
        level = "medium"
    else:
        level = "low"

    # Build rationale
    parts = []
    if factors["primary_source"] >= 0.7:
        parts.append("supported by primary or encyclopedia sources")
    elif factors["primary_source"] >= 0.4:
        parts.append("supported by secondary sources")
    else:
        parts.append("limited source evidence")

    if factors["townland_specificity"] >= 0.8:
        parts.append("specific townland identified within Carrigtwohill parish")
    elif factors["townland_specificity"] >= 0.5:
        parts.append("located within Barrymore barony")
    else:
        parts.append("geographic connection is broad")

    if factors["source_count"] >= 0.7:
        parts.append("multiple independent sources confirm")
    elif factors["source_count"] >= 0.4:
        parts.append("single source")

    rationale = "; ".join(parts) + f". Overall score: {total_score:.2f}."

    return ConfidenceAssessment(
        level=level,
        score=round(total_score, 3),
        factors=factors,
        rationale=rationale,
    )
