import csv
import logging
from io import StringIO
from pathlib import Path

from clarifi.ingestion.parser_factory import ParseResult

logger = logging.getLogger(__name__)


class CSVParser:
    async def parse(self, file_path: Path) -> ParseResult:
        # Try UTF-8 first, fall back to latin-1 (covers ISO-8859-2 Romanian)
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                content = file_path.read_text(encoding=encoding)
                break
            except (UnicodeDecodeError, ValueError):
                continue
        else:
            content = file_path.read_text(encoding="utf-8", errors="replace")

        try:
            reader = csv.reader(StringIO(content))
            lines = []
            for row in reader:
                lines.append(" | ".join(row))
        except csv.Error:
            logger.warning("CSV parse failed for %s, using raw text", file_path.name)
            lines = content.splitlines()

        return ParseResult(
            text="\n".join(lines),
            page_count=None,
            ocr_applied=False,
        )
