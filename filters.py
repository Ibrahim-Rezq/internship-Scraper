import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

from config import Internship, TARGET_CITIES, EXCLUDE_TITLES, INCLUDE_TITLES, SOURCE_PRIORITY

EXCLUDE_COUNTRIES = [
    "usa", "united states", "uk", "united kingdom", "london", "germany",
    "france", "canada", "australia", "dubai", "uae", "qatar", "saudi",
    "kuwait", "oman", "bahrain", "jordan", "lebanon", "tunisia", "morocco",
    "algeria", "pakistan", "india", "china", "japan", "singapore", "america",
]

BOGUS_DOMAINS = [
    "facebook.com", "instagram.com", "twitter.com", "youtube.com",
    "merriam-webster.com", "dictionary.com", "cambridge.org",
    "wikipedia.org", "reddit.com", "pinterest.com",
    "vocabulary.com", "thesaurus.com", "britannica.com",
]

COMPANY_PATTERNS = [
    (r'\s+[-–|]\s+(.+)$', 1),
    (r'\s+@\s+(.+)$', 1),
    (r'\s+at\s+(.+)$', 1),
]


def extract_job_title(raw_title: str) -> str:
    title = raw_title.strip()
    for pat in [r"^Internship\s+", r"^Paid\s+Internship\s*[–\-]\s*", r"^تدريب\s+", r"^Intern\s+"]:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)
    for pat in [r"\s+[–\-]\s+Paid\s+Internship$", r"\s+[–\-]\s+Internship$",
                r"\s+[–\-]\s+intern$", r"\s+Internship$", r"-internship-$",
                r"\s*-\s*تدريب$", r"\s+تدريب$"]:
        title = re.sub(pat, "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+[–\-]\s+(Intern|Trainee|Graduate)\s*$", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\s+[–\-]\s+[A-Z][a-z]+\s*$", "", title, flags=re.IGNORECASE)
    return title.strip()


def infer_company(title: str) -> str | None:
    t = title.strip()
    for pat, group in COMPANY_PATTERNS:
        m = re.search(pat, t, re.IGNORECASE)
        if m:
            c = m.group(group).strip()
            c = re.sub(r'\s*\([^)]*\)\s*$', '', c)
            if any(kw in c.lower() for kw in ("intern", "trainee", "graduate", "summer",
                                                "training", "entry", "fresh", "program")):
                continue
            if 3 < len(c) < 60:
                return c
    return None


def normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\b(egypt|cairo|alexandria|giza|luxor|internship|intern|training)\b', '', text)
    return text.strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _has_egypt_evidence(internship: Internship) -> bool:
    texts = [
        internship.title, internship.description,
        internship.company, internship.location,
        internship.url,
    ]
    combined = " ".join(t.lower() for t in texts if t)
    if "egypt" in combined or "مصر" in combined:
        return True
    for city in TARGET_CITIES:
        if city in combined:
            return True
    for co in COMPANIES_EGYPT:
        if co.lower() in combined:
            return True
    return False


COMPANIES_EGYPT = [
    "Siemens Egypt", "IBM Egypt", "Microsoft Egypt", "Google Egypt",
    "Amazon Egypt", "Valeo Egypt", "PwC Egypt", "Deloitte Egypt",
    "EY Egypt", "KPMG Egypt", "Procter & Gamble Egypt", "Unilever Egypt",
    "PepsiCo Egypt", "Coca-Cola Egypt", "Oracle Egypt", "SAP Egypt",
    "Huawei Egypt", "Intel Egypt", "Vodafone Egypt", "Orange Egypt",
    "Telecom Egypt", "Etisalat Egypt", "Aramex Egypt", "Majid Al Futtaim Egypt",
    "EFG Hermes", "CIB Egypt", "QNB Egypt", "HSBC Egypt",
    "JPMorgan Egypt", "Flat6Labs Cairo", "Falak Startups",
    "ITWORX", "Raya Holding", "Elsewedy Electric",
    "Talabat Egypt", "Careem Egypt", "Uber Egypt", "swvl",
    "Juhayna", "RATP Dev", "Dsquares", "Henkel", "Giza Systems",
    "Heineken", "Dubizzle", "Lesaffre", "Pentavalue", "IACC",
    "Al Ahram", "Mansour Automotive", "Abou Ghaly", "Al-Mansour",
    "Talaat Moustafa", "Emirates NBD", "Fairmont", "Marriott",
    "Air Liquide", "PepsiCo", "Coca-Cola", "Procter & Gamble",
    "Unilever", "Valeo", "Aramex", "ITWORX", "Raya",
    "Flat6Labs", "AUC", "GUC", "Zewail City",
]


def deduplicate(jobs: list[Internship]) -> list[Internship]:
    seen_urls = set()
    kept = []

    for job in jobs:
        if job.url in seen_urls:
            continue
        seen_urls.add(job.url)

        norm_title = normalize(job.title)
        norm_company = normalize(job.company) if job.company else ""

        is_dup = False
        if norm_company:
            for existing in kept:
                if not existing.company:
                    continue
                if existing.source != job.source:
                    continue
                if normalize(existing.company) != norm_company:
                    continue
                if similarity(existing.title, job.title) > 0.85:
                    is_dup = True
                    break

        if not is_dup:
            kept.append(job)

    return kept


def is_relevant(internship: Internship) -> bool:
    if internship.source == "company":
        return True

    title_lower = internship.title.lower()
    desc_lower = internship.description.lower()
    company_lower = internship.company.lower() if internship.company else ""
    url_lower = internship.url.lower()

    search_scope = f"{title_lower} {desc_lower} {company_lower} {url_lower}"

    for exclude in EXCLUDE_TITLES:
        if exclude in title_lower or exclude in desc_lower or exclude in company_lower:
            return False

    for include in INCLUDE_TITLES:
        if include in search_scope:
            return True
    return False


def is_egypt_location(internship: Internship) -> bool:
    if internship.source == "company":
        return True

    loc = internship.location.lower()
    if not loc or loc in ("egypt", "مصر", ""):
        if internship.source == "search":
            return _has_egypt_evidence(internship)
        return True
    if "egypt" in loc or "مصر" in loc:
        return True
    for city in TARGET_CITIES:
        if city in loc:
            return True
    for country in EXCLUDE_COUNTRIES:
        if country in loc:
            return False
    if _has_egypt_evidence(internship):
        return True
    return True


def filter_jobs(jobs: list[Internship]) -> list[Internship]:
    for job in jobs:
        if not job.clean_title:
            job.clean_title = extract_job_title(job.title)
        if not job.company:
            inferred = infer_company(job.title)
            if inferred:
                job.company = inferred

    domain_blocked = [j for j in jobs if not any(b in _domain(j.url) for b in BOGUS_DOMAINS)]
    jobs = deduplicate(domain_blocked)
    filtered = [j for j in jobs if is_relevant(j)]
    location_filtered = [j for j in filtered if is_egypt_location(j)]

    if len(location_filtered) >= 5:
        return location_filtered
    return filtered
