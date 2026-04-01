from pathlib import Path

import pypdf

from clarifi.ingestion.parser_factory import ParseResult


class PDFParser:
    async def parse(self, file_path: Path) -> ParseResult:
        reader = pypdf.PdfReader(str(file_path))
        pages: list[str] = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)

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

            images = convert_from_path(str(file_path))
            texts = []
            for img in images:
                text = pytesseract.image_to_string(img, lang="ron+eng")
                texts.append(text)

            return ParseResult(
                text="\n\n".join(texts),
                page_count=page_count,
                ocr_applied=True,
            )
        except ImportError:
            return ParseResult(
                text="[OCR required but pdf2image not installed]",
                page_count=page_count,
                ocr_applied=False,
            )
