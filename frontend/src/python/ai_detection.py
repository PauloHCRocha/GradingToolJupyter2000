"""Detect invisible/suspicious Unicode characters that may indicate AI-pasted code."""

from __future__ import annotations

import unicodedata

from notebook_parser import Cell

SUSPICIOUS_UNICODE: dict[str, str] = {
    "​": "Zero Width Space",
    "‌": "Zero Width Non-Joiner",
    "‍": "Zero Width Joiner",
    "\u200E": "Left-to-Right Mark",
    "\u200F": "Right-to-Left Mark",
    "\u202A": "Left-to-Right Embedding",
    "\u202B": "Right-to-Left Embedding",
    "\u202C": "Pop Directional Formatting",
    "\u202D": "Left-to-Right Override",
    "\u202E": "Right-to-Left Override",
    "⁠": "Word Joiner",
    "⁡": "Function Application",
    "⁢": "Invisible Times",
    "⁣": "Invisible Separator",
    "⁤": "Invisible Plus",
    "﻿": "Zero Width No-Break Space (BOM)",
    " ": "Non-Breaking Space",
}


def detect_invisible(cells: list[Cell]) -> list[dict]:
    findings: list[dict] = []
    for cell in cells:
        if cell.cell_type != "code":
            continue
        for line_num, line in enumerate(cell.source.split("\n"), 1):
            for char_pos, char in enumerate(line):
                if char in SUSPICIOUS_UNICODE:
                    findings.append(
                        {
                            "line": line_num,
                            "position": char_pos,
                            "name": SUSPICIOUS_UNICODE[char],
                            "unicode": f"U+{ord(char):04X}",
                            "cell_id": cell.cell_id,
                        }
                    )
                elif ord(char) > 127 and char not in ("\n", "\r", "\t"):
                    category = unicodedata.category(char)
                    if category in {"Cc", "Cf", "Cs", "Co"}:
                        try:
                            char_name = unicodedata.name(char, "Unknown")
                        except ValueError:
                            char_name = "Unknown"
                        findings.append(
                            {
                                "line": line_num,
                                "position": char_pos,
                                "name": char_name,
                                "unicode": f"U+{ord(char):04X}",
                                "category": category,
                                "cell_id": cell.cell_id,
                            }
                        )
    return findings
