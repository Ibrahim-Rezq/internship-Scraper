from pathlib import Path
from dataclasses import dataclass, asdict

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

KEYWORDS = [
    "software developer", "software engineering", "software engineer", 
    "data science", "business development", "marketing", "finance",
    "sustainable interior design", "enviromental interior design"
]

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
]

UNIVERSITIES_EGYPT = [
    "Cairo University", "Alexandria University", "Ain Shams University",
    "GUC", "Zewail City", "EJUST", "Nile University",
    "British University in Egypt", "American University in Cairo",
    "German University in Cairo", "MSA University",
    "Helwan University", "Mansoura University", "Assiut University",
]

SOURCE_PRIORITY = {
    "linkedin": 0, "indeed": 1, "wuzzuf": 2,
    "glassdoor": 3, "company": 4, "search": 5,
}

REQUEST_TIMEOUT = 30
SEARCH_PAGES = 1

SCRAPER_CONFIG = {
    "linkedin": {
        "enabled": True,
        "keywords": KEYWORDS,
        "industry_keywords": [
            "software developer", "software engineering", "software engineer", 
            "data science", "business development", "marketing", "finance",
            "sustainable interior design", "enviromental interior design"
            ],
        "location": "Egypt",
        "days_posted": 7,
        "experience_level": [1, 2],
        "sort_by": "DD",
    },
    "indeed": {
        "enabled": False,
        "keywords": ["internship"],
        "location": "Egypt",
    },
    "wuzzuf": {
        "enabled": False,
        "keywords": ["internship"],
        "location": "Egypt",
    },
    "search_engine": {
        "enabled": False,
        "keywords": KEYWORDS,
    },
    "company_pages": {
        "enabled": False,
        "query_templates": [
            "{name} internship careers 2026",
            "{name} فرص تدريب مصر",
        ],
        "companies": COMPANIES_EGYPT,
        "universities": UNIVERSITIES_EGYPT,
    },
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

TARGET_CITIES = ["cairo", "alexandria", "giza", "hurghada", "luxor",
    "mansoura", "sharm el-sheikh", "ismailia", "asyut", "port said", "suez"]

EXCLUDE_TITLES = ["senior", "lead", "manager", "director", "head of",
    "principal", "5+ years", "7+ years", "10+ years", "staff", "vp "]

INCLUDE_TITLES = ["intern", "trainee", "graduate", "تدريب", "متدر",
    "طالب", "fresh grad", "junior"]


@dataclass
class Internship:
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str = ""
    date_posted: str = ""
    job_type: str = ""
    clean_title: str = ""

    def to_dict(self):
        d = asdict(self)
        d.pop("clean_title", None)
        return d
