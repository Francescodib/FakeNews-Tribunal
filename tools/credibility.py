"""
Source credibility scoring based on domain reputation.

Tiers:
  high    — authoritative institutions, major news agencies, peer-reviewed sources
  medium  — established media with editorial standards
  low     — tabloids, partisan sites, aggregators with low editorial control
  unknown — domain not in any list (neutral, no penalty/bonus)
"""

from enum import Enum


class CredibilityTier(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


# Scores used by the Judge prompt (informational, not a filter)
_TIER_SCORE: dict[CredibilityTier, float] = {
    CredibilityTier.HIGH: 1.0,
    CredibilityTier.MEDIUM: 0.6,
    CredibilityTier.LOW: 0.2,
    CredibilityTier.UNKNOWN: 0.5,
}

# Domain → tier mapping (subdomain-stripped, lowercase)
_HIGH: set[str] = {
    # Scientific / academic journals
    "nature.com", "science.org", "cell.com", "thelancet.com", "nejm.org",
    "jstor.org", "ssrn.com", "arxiv.org", "biorxiv.org", "medrxiv.org",
    # US government health & science (registrable domains)
    "nih.gov", "cdc.gov", "fda.gov", "cms.gov", "hhs.gov",
    "nasa.gov", "noaa.gov", "usgs.gov", "epa.gov", "nist.gov",
    # Other .gov / .edu institutions commonly cited
    "aap.org", "who.int", "un.org", "europa.eu", "oecd.org",
    "worldbank.org", "imf.org", "nato.int", "icrc.org", "icc-cpi.int",
    # Italian institutions
    "governo.it", "parlamento.it", "quirinale.it", "cortecostituzionale.it",
    "istat.it", "bancaditalia.it", "agcom.it", "garante.it",
    "salute.gov.it", "esteri.it", "interno.gov.it",
    # Major news agencies
    "reuters.com", "apnews.com", "afp.com", "ansa.it",
    # Public broadcasters
    "bbc.com", "bbc.co.uk", "rai.it", "dw.com", "rfi.fr",
    "npr.org", "pbs.org", "abc.net.au",
    # Fact-checkers
    "snopes.com", "politifact.com", "factcheck.org",
    "fullfact.org", "pagella-politica.it",
    # Major encyclopedias
    "britannica.com", "wikipedia.org",
    # Top medical / research institutions (registrable domains)
    "mayoclinic.org", "hopkinsmedicine.org", "clevelandclinic.org",
    "chop.edu", "harvard.edu", "stanford.edu", "mit.edu",
    "cochrane.org", "bmj.com", "jamanetwork.com", "acpjournals.org",
    # Authoritative science communicators
    "scientificamerican.com", "newscientist.com",
}

_MEDIUM: set[str] = {
    # International press
    "nytimes.com", "theguardian.com", "washingtonpost.com", "ft.com",
    "economist.com", "bloomberg.com", "wsj.com", "lemonde.fr",
    "spiegel.de", "corriere.it", "repubblica.it", "lastampa.it",
    "ilsole24ore.com", "stampa.it", "agi.it", "adnkronos.com",
    "huffingtonpost.it", "tgcom24.mediaset.it", "sky.com", "skytg24.it",
    "fanpage.it", "open.online", "today.it",
    # Tech/science media
    "wired.com", "theverge.com", "arstechnica.com", "scientificamerican.com",
    "newscientist.com", "technologyreview.com",
}

_LOW: set[str] = {
    # Known low-credibility / conspiracy / highly partisan
    "infowars.com", "naturalnews.com", "beforeitsnews.com",
    "activistpost.com", "zerohedge.com", "globalresearch.ca",
    "off-guardian.org", "voltairenet.org", "strategic-culture.org",
    "sputniknews.com", "rt.com", "tass.com",
    "ilgiornaleditalia.it", "liberoquotidiano.it",
}


def _strip_subdomain(domain: str) -> str:
    """Return the registrable domain (last two labels, or three for co.uk etc.)."""
    parts = domain.lower().removeprefix("www.").split(".")
    # Handle two-part TLDs like co.uk, gov.it, edu.au
    two_part_tlds = {"co.uk", "co.nz", "co.jp", "gov.uk", "gov.it", "edu.au", "ac.uk"}
    if len(parts) >= 3 and ".".join(parts[-2:]) in two_part_tlds:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def score_domain(domain: str) -> tuple[CredibilityTier, float, str]:
    """
    Returns (tier, score, note) for a given domain string.
    """
    if not domain:
        return CredibilityTier.UNKNOWN, _TIER_SCORE[CredibilityTier.UNKNOWN], ""

    base = _strip_subdomain(domain)

    if base in _HIGH:
        tier = CredibilityTier.HIGH
        note = "High-credibility source (authoritative institution or major verified outlet)"
    elif base in _MEDIUM:
        tier = CredibilityTier.MEDIUM
        note = "Medium-credibility source (established media with editorial standards)"
    elif base in _LOW:
        tier = CredibilityTier.LOW
        note = "Low-credibility source (known for misinformation or strong partisan bias)"
    else:
        tier = CredibilityTier.UNKNOWN
        note = ""

    return tier, _TIER_SCORE[tier], note
