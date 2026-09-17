import re
import unicodedata

def clean_text(text: str) -> str:
    """Clean extracted document text.
    
    Removes null bytes, normalizes unicode, removes hyphens at line breaks,
    and collapses runs of whitespace while preserving paragraph boundaries.
    """
    if not text:
        return ""

    # Normalize unicode to canonical composition
    text = unicodedata.normalize("NFKC", text)

    # Strip null bytes and non-printable control characters
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Fix hyphenated words broken across lines
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    # Remove repeated page header / footer markers like "Page 1 of 12"
    text = re.sub(r"(?i)\bpage\s+\d+\s+(?:of|\/)\s+\d+\b", "", text)
    text = re.sub(r"(?i)^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    # Standardize multiple empty lines into double newlines
    text = re.sub(r"\r\n|\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse internal spaces
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()

