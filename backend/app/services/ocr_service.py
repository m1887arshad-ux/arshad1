"""
OCR Service: DISABLED

OCR functionality has been temporarily disabled.
Prescription image processing is not available.
Users should enter medicine orders manually via text chat.

This file is kept as a stub to prevent import errors.
"""
import logging
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class OCRError(Exception):
    """Base exception for OCR pipeline failures."""
    pass


class OCRExtractionError(OCRError):
    """Tesseract failed to extract text."""
    pass


class OCRParsingError(OCRError):
    """Failed to parse medicines from text."""
    pass


class InventoryMatchError(OCRError):
    """Medicine not found in inventory."""
    pass


def parse_medicines_from_text(text: str) -> List[Dict[str, Any]]:
    """
    DISABLED: OCR medicine parsing is not available.
    
    This function is kept as a stub for backward compatibility.
    """
    logger.warning("[OCR] parse_medicines_from_text called but OCR is disabled")
    raise OCRError("OCR functionality is currently disabled")


def process_prescription_image(
    image_bytes: bytes,
    business_id: int,
    telegram_chat_id: str,
    db
) -> Dict[str, Any]:
    """
    DISABLED: OCR prescription processing is not available.
    
    This function is kept as a stub for backward compatibility.
    """
    logger.warning(
        f"[OCR] process_prescription_image called but OCR is disabled "
        f"(business_id={business_id}, chat_id={telegram_chat_id})"
    )
    return {
        "success": 0,
        "failed": 0,
        "drafts": [],
        "failed_names": [],
        "error": "OCR functionality is currently disabled. Please enter medicines manually."
    }
