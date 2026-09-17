import re
from typing import Optional

# Common academic paper section regex patterns
ACADEMIC_SECTION_PATTERN = re.compile(
    r"^(?:(?:[0-9]+(?:\.[0-9]+)*|[A-Z]\.)\s+)?([A-Z][A-Za-z0-9 ,'\-:\?]{2,70})$"
)

MARKDOWN_HEADING_PATTERN = re.compile(
    r"^#{1,6}\s+([A-Za-z0-9 ,'\-:\?]{2,80})$"
)

STANDARD_SECTIONS = {
    "abstract", "introduction", "background", "related work",
    "model architecture", "methods", "methodology", "experiments",
    "results", "discussion", "conclusion", "references", "appendix"
}

def detect_section_header(line: str) -> Optional[str]:
    """Detect if a text line represents a section title."""
    clean = line.strip()
    if not clean or len(clean) > 80:
        return None

    # Check markdown headers
    md_match = MARKDOWN_HEADING_PATTERN.match(clean)
    if md_match:
        return md_match.group(1).strip()

    # Check known standard section words
    lower = clean.lower().rstrip(".:")
    if lower in STANDARD_SECTIONS:
        return clean.strip(".:")

    # Check numbered academic section like "1. Introduction" or "3.2 Multi-Head Attention"
    num_match = re.match(r"^(\d+(?:\.\d+)*\.?)\s+([A-Z][A-Za-z0-9 \-:,]+)$", clean)
    if num_match:
        return f"{num_match.group(1).rstrip('.')} {num_match.group(2).strip()}"

    return None

