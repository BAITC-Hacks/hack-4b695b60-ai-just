"""Reversible contact redaction before external model calls."""

import re
from dataclasses import dataclass

EMAIL_RE = re.compile(r"(?<![\w.])\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)\+?\d[\d\s()-]{8,}\d(?!\w)")
HANDLE_RE = re.compile(r"(?<![\w@])@[A-Za-z][A-Za-z0-9_]{3,}\b")
PLACEHOLDER_RE = re.compile(r"\[(?:EMAIL|PHONE|TG)_\d+\]")


@dataclass
class Redaction:
    mapping: dict[str, str]

    def restore(self, text: str) -> str:
        for placeholder, original in self.mapping.items():
            text = text.replace(placeholder, original)
        return text

    def mask(self, text: str) -> str:
        for placeholder, original in self.mapping.items():
            text = text.replace(original, placeholder)
        return text


def redact_texts(texts: list[str]) -> tuple[list[str], Redaction]:
    """Use one mapping for all sources so repeated contacts get the same token."""
    mapping: dict[str, str] = {}
    reverse: dict[str, str] = {}
    counters = {"EMAIL": 0, "PHONE": 0, "TG": 0}

    def replace(match: re.Match[str], kind: str) -> str:
        original = match.group(0)
        if kind == "PHONE" and not 10 <= sum(character.isdigit() for character in original) <= 15:
            return original
        if original not in reverse:
            counters[kind] += 1
            placeholder = f"[{kind}_{counters[kind]}]"
            reverse[original] = placeholder
            mapping[placeholder] = original
        return reverse[original]

    masked: list[str] = []
    for text in texts:
        for pattern, kind in ((EMAIL_RE, "EMAIL"), (PHONE_RE, "PHONE"), (HANDLE_RE, "TG")):
            text = pattern.sub(lambda match, label=kind: replace(match, label), text)
        masked.append(text)
    return masked, Redaction(mapping)
