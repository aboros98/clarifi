from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class ParseResult:
    text: str
    page_count: int | None = None
    ocr_applied: bool = False


class DocumentParser(Protocol):
    async def parse(self, file_path: Path) -> ParseResult: ...


class ParserFactory:
    _parsers: dict[str, type] = {}

    @classmethod
    def register(cls, mime_type: str, parser_cls: type) -> None:
        cls._parsers[mime_type] = parser_cls

    @classmethod
    def get_parser(cls, mime_type: str) -> DocumentParser:
        # Lazy import to avoid circular deps and optional deps
        if not cls._parsers:
            cls._register_defaults()

        parser_cls = cls._parsers.get(mime_type)
        if parser_cls is None:
            # Try broad match
            base_type = mime_type.split("/")[0]
            if base_type == "image":
                from clarifi.ingestion.image_ocr_parser import ImageOCRParser
                return ImageOCRParser()
            # Default to plain text extraction
            from clarifi.ingestion.text_parser import TextParser
            return TextParser()

        return parser_cls()

    @classmethod
    def _register_defaults(cls) -> None:
        from clarifi.ingestion.csv_parser import CSVParser
        from clarifi.ingestion.docx_parser import DocxParser
        from clarifi.ingestion.image_ocr_parser import ImageOCRParser
        from clarifi.ingestion.pdf_parser import PDFParser

        cls._parsers.update(
            {
                "application/pdf": PDFParser,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxParser,
                "text/csv": CSVParser,
                "image/png": ImageOCRParser,
                "image/jpeg": ImageOCRParser,
                "image/tiff": ImageOCRParser,
            }
        )
