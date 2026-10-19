"""Document classifier — automatically categorizes documents during ingestion.

Classifies incoming documents into:
- doc_type: 'policy', 'code', 'programme', 'governance', 'manual', 'other'
- category: 'HR & Workplace Compliance', 'Corporate Governance & Securities', 'Ethics & Market Integrity', 'Director Development', 'Technical & Architecture', 'General'
- title: Clean human-readable document title
- is_policy: Boolean flag
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class DocumentClassificationResult:
    """Classification metadata result for an ingested document."""
    doc_type: str
    category: str
    title: str
    is_policy: bool
    governance_level: str

    def to_dict(self) -> dict:
        return asdict(self)


class DocumentClassifier:
    """Rule and content-aware document classifier for corporate governance and technical knowledge bases."""

    @classmethod
    def classify(cls, file_path: str | Path, content_sample: str = "") -> DocumentClassificationResult:
        """Classify a document by inspecting its filename and initial textual content."""
        path = Path(file_path)
        name = path.stem.replace("_", " ").replace("-", " ")
        full_text_sample = f"{name} {content_sample[:2500]}".lower()

        clean_title = cls._clean_title(path.name)
        doc_type = cls._detect_doc_type(name, full_text_sample)
        category = cls._detect_category(name, full_text_sample, doc_type)
        is_policy = (doc_type == "policy")
        gov_level = cls._detect_governance_level(name, full_text_sample)

        return DocumentClassificationResult(
            doc_type=doc_type,
            category=category,
            title=clean_title,
            is_policy=is_policy,
            governance_level=gov_level,
        )

    @staticmethod
    def _clean_title(filename: str) -> str:
        """Derive a polished title from filename."""
        base = Path(filename).stem
        # Clean underscores, dashes, extensions
        cleaned = re.sub(r"[_\-]+", " ", base).strip()
        # Clean common company prefix duplicates
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @staticmethod
    def _detect_doc_type(filename_clean: str, text: str) -> str:
        fn = filename_clean.lower()

        # 1. Policies
        if any(k in fn for k in ["policy", "vigil mechanism", "whistleblowing"]):
            return "policy"
        if "terms and conditions of appointment" in fn:
            return "governance"

        # 2. Codes
        if any(k in fn for k in ["code of conduct", "code of ethics", "code or practices", "fair disclosure of upsi"]):
            return "code"

        # 3. Programmes
        if any(k in fn for k in ["programme", "familiarisation", "training"]):
            return "programme"

        # 4. Governance & Appointments
        if any(k in fn for k in ["appointment", "board evaluation", "charter", "director terms"]):
            return "governance"

        # 5. Technical Manuals / Runbooks
        if any(k in fn for k in ["guide", "runbook", "handbook", "architecture", "agents"]):
            return "manual"

        # Fallback to inspecting text sample
        if "policy" in text[:500]:
            return "policy"
        if "code of conduct" in text[:500] or "code of ethics" in text[:500]:
            return "code"
        if "familiarisation programme" in text[:500]:
            return "programme"

        return "other"

    @staticmethod
    def _detect_category(filename_clean: str, text: str, doc_type: str) -> str:
        fn = filename_clean.lower()

        # HR & Workplace Compliance
        if any(k in fn or k in text for k in [
            "sexual harassment", "posh", "pwd", "equal opportunity",
            "diversity", "human rights", "anti corruption", "maternity"
        ]):
            return "HR & Workplace Compliance"

        # Ethics & Market Integrity
        if any(k in fn or k in text for k in [
            "code of ethics", "code of conduct", "upsi", "insider trading",
            "whistleblowing", "vigil mechanism", "fair disclosure"
        ]):
            return "Ethics & Market Integrity"

        # Corporate Governance & Securities
        if any(k in fn or k in text for k in [
            "materiality", "subsidiary", "subsidiaries", "dividend",
            "archival", "preservation of documents", "related party",
            "succession planning", "board evaluation", "nomination and renumeration",
            "board diversity", "responsible advocacy"
        ]):
            return "Corporate Governance & Securities"

        # Director Development & Appointments
        if any(k in fn or k in text for k in [
            "familiarisation", "appointment of independent directors", "independent directors"
        ]):
            return "Director Development & Board Oversight"

        # Technical & Architecture
        if any(k in fn or k in text for k in [
            "architecture", "runbook", "security", "building agents", "ragops"
        ]):
            return "Technical & Architecture"

        return "General Corporate"

    @staticmethod
    def _detect_governance_level(filename_clean: str, text: str) -> str:
        fn = filename_clean.lower()
        if any(k in fn or k in text for k in ["board of directors", "board", "director", "independent director"]):
            return "Board Level"
        if any(k in fn or k in text for k in ["senior management", "executive", "designated persons"]):
            return "Executive & Management"
        if any(k in fn or k in text for k in ["all employees", "workplace", "posh", "human rights"]):
            return "Company-Wide"
        return "Operational"
