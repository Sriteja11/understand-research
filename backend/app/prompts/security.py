import re

# Prompt injection signatures to scan for audit and warning
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?(system\s+prompt|instructions)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(DAN|unrestricted|an\s+attacker)", re.IGNORECASE),
    re.compile(r"print\s+(the\s+)?(system\s+prompt|developer\s+mode)", re.IGNORECASE),
    re.compile(r"override\s+system\s+directive", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"<system_instruction>", re.IGNORECASE),
]

def scan_for_injection(text: str) -> bool:
    """Check whether text contains known prompt injection signatures."""
    if not text:
        return False
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False

