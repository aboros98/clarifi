import logging
from pathlib import Path

import pypdf

from clarifi.ingestion.parser_factory import ParseResult

logger = logging.getLogger(__name__)


class PDFParser:
    async def parse(self, file_path: Path) -> ParseResult:
        try:
            reader = pypdf.PdfReader(str(file_path))
            # Handle PDFs flagged as "encrypted" but without actual password
            if reader.is_encrypted:
                try:
                    reader.decrypt("")  # Try empty password
                except Exception:
                    logger.warning("Encrypted PDF, trying empty password failed: %s", file_path.name)
        except Exception:
            logger.warning("Failed to read PDF: %s", file_path.name, exc_info=True)
            return ParseResult(
                text="[PDF corupt sau format nesuportat]",
                page_count=0,
                ocr_applied=False,
            )

        pages: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
                pages.append(text)
            except Exception:
                pages.append("")

        full_text = "\n\n".join(pages)

        # If very little text extracted, it's likely a scanned PDF — apply OCR
        if len(full_text.strip()) < 50 and len(reader.pages) > 0:
            return await self._ocr_fallback(file_path, len(reader.pages))

        return ParseResult(
            text=full_text,
            page_count=len(reader.pages),
            ocr_applied=False,
        )

    async def _ocr_fallback(self, file_path: Path, page_count: int) -> ParseResult:
        """Fall back to OCR for scanned PDFs."""
        try:
            from pdf2image import convert_from_path
            import pytesseract

            images = convert_from_path(str(file_path), dpi=200)
            texts = []
            for i, img in enumerate(images):
                try:
                    text = pytesseract.image_to_string(img, lang="ron+eng")
                    texts.append(text)
                except Exception:
                    logger.warning("OCR failed on page %d of %s", i + 1, file_path.name)
                    texts.append("")

            return ParseResult(
                text="\n\n".join(texts),
                page_count=page_count,
                ocr_applied=True,
            )
        except ImportError:
            return ParseResult(
                text="[OCR necesar dar pdf2image nu e instalat]",
                page_count=page_count,
                ocr_applied=False,
            )
        except Exception:
            logger.warning("OCR fallback failed for %s", file_path.name, exc_info=True)
            return ParseResult(
                text="[OCR a esuat]",
                page_count=page_count,
                ocr_applied=False,
            )
