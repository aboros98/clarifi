from pathlib import Path

from clarifi.ingestion.parser_factory import ParseResult


class TextParser:
    """Fallback parser for plain text files."""

    async def parse(self, file_path: Path) -> ParseResult:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return ParseResult(text=text)
