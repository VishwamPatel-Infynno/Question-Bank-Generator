"""
readability.py - Syllable counting, readability indices, and psychometric diagnostics for reading passages.

Computes Flesch-Kincaid Grade Level, Flesch Reading Ease, empirical scientific assay density,
and AAMC standard passage pacing diagnostics for MCAT CARS and Science passages.
"""

from __future__ import annotations

import re
from typing import Any


def count_syllables(word: str) -> int:
    """Estimates syllable count for readability formulas using regex heuristic."""
    w = word.lower().strip()
    if not w:
        return 1
    w = re.sub(r"(?:[^laeiouy]|ed|es|e)$", "", w)
    w = re.sub(r"^y", "", w)
    matches = re.findall(r"[aeiouy]{1,2}", w)
    return max(1, len(matches))


def audit_passage_text(passage_text: str) -> dict[str, Any]:
    """Computes comprehensive readability indices, empirical data density, and AAMC alignment diagnostics."""
    text = (passage_text or "").strip()
    if not text:
        return {
            "word_count": 0,
            "sentence_count": 0,
            "flesch_kincaid_grade": 0.0,
            "reading_ease": 100.0,
            "empirical_density_score": 0,
            "aamc_alignment_score": 0,
            "diagnostics": ["Empty passage text."],
        }

    words = [w for w in re.findall(r"\b[A-Za-z0-9\-']+\b", text) if w]
    word_count = len(words)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_count = max(1, len(sentences))

    syllable_count = sum(count_syllables(w) for w in words)

    # Flesch-Kincaid Grade Level: 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
    words_per_sentence = word_count / sentence_count
    syllables_per_word = syllable_count / max(1, word_count)
    fk_grade = round(0.39 * words_per_sentence + 11.8 * syllables_per_word - 15.59, 1)
    fk_grade = max(1.0, min(20.0, fk_grade))

    # Flesch Reading Ease: 206.835 - (1.015 * words/sentences) - (84.6 * syllables/words)
    reading_ease = round(206.835 - (1.015 * words_per_sentence) - (84.6 * syllables_per_word), 1)
    reading_ease = max(0.0, min(100.0, reading_ease))

    # Empirical data density: quantitative units, numbers, scientific assays
    empirical_matches = re.findall(
        r"\b(?:\d+(?:\.\d+)?\s*(?:mM|uM|nm|um|mL|mg|kg|kV|Hz|%|pKa|pH|kDa|min|sec|h)\b|\d+\.\d+|\b[A-Z][a-z]?-\d+\b)",
        text,
    )
    empirical_density = len(empirical_matches)

    diagnostics: list[str] = []
    score = 90

    # Word count assessment (AAMC passages are typically 400-600 words)
    if 350 <= word_count <= 650:
        diagnostics.append(
            f"Passage length ({word_count} words) is optimal for standard AAMC passage pacing."
        )
        score += 5
    elif word_count < 300:
        diagnostics.append(
            f"Passage length ({word_count} words) is shorter than typical AAMC passages (target 400-550 words)."
        )
        score -= 10
    else:
        diagnostics.append(f"Passage length ({word_count} words) exceeds standard AAMC targets.")
        score -= 5

    # Reading level assessment
    if 11.0 <= fk_grade <= 15.0:
        diagnostics.append(
            f"Grade level ({fk_grade}) matches undergraduate / medical school entrance rigor."
        )
        score += 5
    else:
        diagnostics.append(f"Grade level is {fk_grade}.")

    # Empirical data density assessment
    if empirical_density >= 5:
        diagnostics.append(
            f"Rich empirical data density ({empirical_density} assay/quantitative anchors detected)."
        )
    else:
        diagnostics.append(
            "Low quantitative density; consider embedding numerical assay results or experimental figures."
        )

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "flesch_kincaid_grade": fk_grade,
        "reading_ease": reading_ease,
        "empirical_density_score": empirical_density,
        "aamc_alignment_score": max(50, min(100, score)),
        "diagnostics": diagnostics,
    }
