"""Section-level lexical retrieval plus a small, explicit policy grammar."""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"


@dataclass(frozen=True)
class Clause:
    edition: str
    section: str
    text: str
    source: str

    @property
    def citation(self):
        return f"{self.edition}#{self.section}"


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


class PolicyBook:
    def __init__(self, folder=DATA):
        self.editions = json.loads((folder / "editions.json").read_text())
        self.clauses = []
        for entry in self.editions:
            source = (folder / entry["source"]).read_text(encoding="utf-8")
            parts = re.split(r"^## ([\w-]+)\s*\n", source, flags=re.MULTILINE)
            for section, body in zip(parts[1::2], parts[2::2]):
                self.clauses.append(
                    Clause(entry["edition"], section, body.strip(), entry["source"])
                )

    def edition_for(self, purchased):
        matches = [
            e["edition"] for e in self.editions if e["from"] <= purchased < e["until"]
        ]
        if len(matches) != 1:
            raise ValueError("Purchase date has no unique policy edition.")
        return matches[0]

    def search(self, query, edition, section=None):
        candidates = [
            c
            for c in self.clauses
            if c.edition == edition and (section is None or c.section == section)
        ]
        documents = [Counter(tokens(c.section + " " + c.text)) for c in candidates]
        query_terms = set(tokens(query))
        ranked = []
        for clause, terms in zip(candidates, documents):
            score = 0
            for term in query_terms & terms.keys():
                frequency = sum(term in doc for doc in documents)
                score += (1 + math.log(terms[term])) * math.log(
                    1 + len(documents) / frequency
                )
            if score:
                ranked.append((score, clause))
        return [c for _, c in sorted(ranked, key=lambda pair: -pair[0])]

    def required(self, edition, section):
        matches = [
            c for c in self.clauses if c.edition == edition and c.section == section
        ]
        if len(matches) != 1:
            raise ValueError(f"Missing or conflicting section: {section}.")
        return matches[0]


def window_days(text):
    match = re.fullmatch(
        r"Request a return within (\d{1,3}) calendar days after delivery\. "
        r"Requests on the deadline qualify\.",
        text,
    )
    if not match:
        raise ValueError("Standard window requires interpretation.")
    return int(match[1])


def holiday_floor(text, purchase):
    if text == "No holiday extension applies in this edition.":
        return None
    match = re.fullmatch(
        r"For orders purchased from (\S+) through (\S+), "
        r"extend the deadline to (\S+) if later\.",
        text,
    )
    if not match:
        raise ValueError("Holiday rule requires interpretation.")
    start, end, floor = map(date.fromisoformat, match.groups())
    if start > end or floor < end:
        raise ValueError("Holiday dates are inconsistent.")
    return floor.isoformat() if start <= date.fromisoformat(purchase) <= end else None
