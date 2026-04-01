from pathlib import Path

from clarifi.ingestion.parser_factory import ParseResult


class ImageOCRParser:
    async def parse(self, file_path: Path) -> ParseResult:
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            return ParseResult(
                text="[OCR not available — install pytesseract and Pillow]",
                page_count=1,
                ocr_applied=False,
            )

        img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang="ron+eng")

        return ParseResult(
            text=text,
            page_count=1,
            ocr_applied=True,
        )
