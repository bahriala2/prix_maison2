"""Intelligent document analysis service.

Pipeline: Scan -> OCR -> extraction heuristique -> resume -> pre-remplissage.

OCR is performed with pytesseract/pdf2image when those optional dependencies
and the Tesseract binary are installed on the server. When unavailable, the
service degrades gracefully and returns an empty extraction so the agent can
fill the form manually - the automatic pre-fill is always a suggestion that
the agent must verify and validate before saving (see module spec, section 5).
"""
import re
from dataclasses import dataclass, field

try:
    import pytesseract
    from PIL import Image

    OCR_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    OCR_AVAILABLE = False

try:
    from pdf2image import convert_from_path

    PDF_SUPPORT = True
except ImportError:  # pragma: no cover - optional dependency
    PDF_SUPPORT = False


URGENCE_KEYWORDS = ["urgent", "très urgent", "immédiat", "délai court", "sans délai"]

FIELD_PATTERNS = {
    "reference": r"(?:r[ée]f(?:[ée]rence)?s?\s*[:n°]*\s*)([A-Z0-9/\-\.]{3,})",
    "objet": r"(?:objet\s*[:\-]\s*)(.+)",
    "emetteur": r"(?:exp[ée]diteur|de\s*[:\-])\s*(.+)",
    "recepteur": r"(?:destinataire|[àa]\s*[:\-])\s*(.+)",
    "date_correspondance": r"(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
}


@dataclass
class ExtractionResult:
    texte_brut: str = ""
    emetteur: str = ""
    recepteur: str = ""
    objet: str = ""
    date_correspondance: str = ""
    reference: str = ""
    type_document: str = ""
    service_concerne: str = ""
    resume: str = ""
    urgence: str = "Normal"
    destination_probable: str = ""
    ocr_disponible: bool = field(default=False)

    def as_dict(self):
        return self.__dict__


def _extract_text(file_path: str) -> str:
    if not OCR_AVAILABLE:
        return ""
    try:
        if file_path.lower().endswith(".pdf"):
            if not PDF_SUPPORT:
                return ""
            pages = convert_from_path(file_path)
            return "\n".join(pytesseract.image_to_string(page, lang="fra+eng") for page in pages)
        return pytesseract.image_to_string(Image.open(file_path), lang="fra+eng")
    except Exception:
        return ""


def _first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip().splitlines()[0][:255]
    return ""


def _summarize(text: str, max_sentences: int = 3) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if len(s) > 15]
    return " ".join(sentences[:max_sentences])[:500]


def _detect_urgence(text: str) -> str:
    lowered = text.lower()
    for keyword in URGENCE_KEYWORDS:
        if keyword in lowered:
            return "Urgent"
    return "Normal"


def analyze_document(file_path: str) -> ExtractionResult:
    """Run OCR + heuristic extraction on a scanned document and return a
    pre-fill suggestion. The calling view must let the agent review and
    correct every field before validation (never auto-save blindly)."""
    text = _extract_text(file_path)
    result = ExtractionResult(texte_brut=text, ocr_disponible=OCR_AVAILABLE and bool(text))

    if not text:
        return result

    result.reference = _first_match(FIELD_PATTERNS["reference"], text)
    result.objet = _first_match(FIELD_PATTERNS["objet"], text)
    result.emetteur = _first_match(FIELD_PATTERNS["emetteur"], text)
    result.recepteur = _first_match(FIELD_PATTERNS["recepteur"], text)
    result.date_correspondance = _first_match(FIELD_PATTERNS["date_correspondance"], text)
    result.resume = _summarize(text)
    result.urgence = _detect_urgence(text)
    return result
