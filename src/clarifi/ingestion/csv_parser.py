import csv
from io import StringIO
from pathlib import Path

from clarifi.ingestion.parser_factory import ParseResult


class CSVParser:
    async def parse(self, file_path: Path) -> ParseResult:
        content = file_path.read_text(encoding="utf-8", errors="replace")

        # Convert CSV to a readable text format
        reader = csv.reader(StringIO(content))
        lines = []
        for row in reader:
            lines.append(" | ".join(row))

        return ParseResult(
            text="\n".join(lines),
            page_count=None,
            ocr_applied=False,
        )
