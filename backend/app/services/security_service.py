import html
from typing import Dict, Any, List
from backend.app.prompts.security import scan_for_injection
from backend.app.config import settings

class SecurityService:
    """Security boundaries and prompt injection detection."""

    def validate_query(self, query: str) -> str:
        clean = (query or "").strip()
        if not clean:
            raise ValueError("Query cannot be empty.")
        if len(clean) > settings.max_query_length:
            raise ValueError(
                f"Query length ({len(clean)}) exceeds maximum allowed limit of {settings.max_query_length} characters."
            )
        return clean

    def inspect_content(self, text: str) -> Dict[str, Any]:
        has_injection = scan_for_injection(text)
        return {
            "has_injection": has_injection,
            "sanitized": self.sanitize_untrusted_text(text) if has_injection else text
        }

    def sanitize_untrusted_text(self, text: str) -> str:
        """Escape boundary tokens that could break XML fences."""
        escaped = text.replace("<retrieved_evidence>", "&lt;retrieved_evidence&gt;")
        escaped = escaped.replace("</retrieved_evidence>", "&lt;/retrieved_evidence&gt;")
        escaped = escaped.replace("<system>", "&lt;system&gt;")
        escaped = escaped.replace("</system>", "&lt;/system&gt;")
        return escaped


_default_security_service = None

def get_security_service() -> SecurityService:
    global _default_security_service
    if _default_security_service is None:
        _default_security_service = SecurityService()
    return _default_security_service

