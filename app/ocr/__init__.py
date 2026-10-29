"""Backend OCR & Document Extraction package for NetBill Assist."""

from app.ocr.service import extract_documents_from_uploads, get_ocr_status

__all__ = ["extract_documents_from_uploads", "get_ocr_status"]
