"""Excel (.xlsx, .xls) parser — converts spreadsheet to text for extraction."""

import logging
from pathlib import Path

from clarifi.ingestion.parser_factory import ParseResult

logger = logging.getLogger(__name__)


class XLSXParser:
    async def parse(self, file_path: Path) -> ParseResult:
        try:
            import openpyxl

            wb = openpyxl.load_workbook(str(file_path), data_only=True)
            lines = []
            for sheet in wb.worksheets:
                lines.append(f"--- {sheet.title} ---")
                for row in sheet.iter_rows(values_only=True):
                    cells = [str(c) if c is not None else "" for c in row]
                    line = " | ".join(cells).strip()
                    if line and line != " | ".join([""] * len(cells)):
                        lines.append(line)
            wb.close()

            return ParseResult(
                text="\n".join(lines),
                page_count=len(wb.worksheets),
                ocr_applied=False,
            )
        except ImportError:
            logger.warning("openpyxl not installed — falling back to CSV parser for xlsx")
            from clarifi.ingestion.csv_parser import CSVParser

            return await CSVParser().parse(file_path)
        except Exception:
            logger.warning("XLSX parse failed: %s", file_path.name, exc_info=True)
            return ParseResult(
                text="[Eroare la citirea fisierului Excel]",
                page_count=0,
                ocr_applied=False,
            )
