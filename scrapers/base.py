from dataclasses import dataclass
from typing import Optional

# Checked in order — most specific first.
ROLE_KEYWORDS: dict[str, list[str]] = {
    "Cyber Security":       ["cyber", "security", "infosec", "penetration", "soc analyst"],
    "Full-stack":           ["full stack", "fullstack", "full-stack"],
    "Backend":              ["backend", "back-end", "back end", "api developer"],
    "Software Engineering": ["software engineer", "software developer", "swe", "sde"],
}


@dataclass
class JobResult:
    source_name: str
    title: str
    url: str
    company: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[str] = None  # normalized comma-separated string


def infer_role_type(title: str) -> Optional[str]:
    t = title.lower()
    for role, keywords in ROLE_KEYWORDS.items():
        if any(kw in t for kw in keywords):
            return role
    return None
