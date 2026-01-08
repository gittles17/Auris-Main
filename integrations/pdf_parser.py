"""
PDF Parser - Extracts text from uploaded PDF reports.
"""

import io
from typing import Union, BinaryIO
from pathlib import Path


class PDFParser:
    """Parses PDF files and extracts text content."""
    
    def __init__(self):
        self._pdfplumber = None
        self._pypdf2 = None
        self._init_parsers()
    
    def _init_parsers(self):
        """Initialize available PDF parsers."""
        try:
            import pdfplumber
            self._pdfplumber = pdfplumber
        except ImportError:
            pass
        
        try:
            import PyPDF2
            self._pypdf2 = PyPDF2
        except ImportError:
            pass
    
    def parse_pdf(self, file: Union[str, Path, BinaryIO]) -> str:
        """Parse a PDF file and extract text content."""
        if self._pdfplumber:
            try:
                return self._parse_with_pdfplumber(file)
            except Exception as e:
                print(f"pdfplumber failed: {e}, trying PyPDF2...")
        
        if self._pypdf2:
            try:
                return self._parse_with_pypdf2(file)
            except Exception as e:
                print(f"PyPDF2 failed: {e}")
        
        return "Error: Could not parse PDF. Please install pdfplumber or PyPDF2."
    
    def _parse_with_pdfplumber(self, file: Union[str, Path, BinaryIO]) -> str:
        """Parse PDF using pdfplumber."""
        text_parts = []
        
        if hasattr(file, 'read'):
            file_bytes = file.read()
            file.seek(0)
            pdf_file = io.BytesIO(file_bytes)
        else:
            pdf_file = file
        
        with self._pdfplumber.open(pdf_file) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num} ---\n{page_text}")
                
                tables = page.extract_tables()
                for table_num, table in enumerate(tables, 1):
                    if table:
                        table_text = self._format_table(table)
                        text_parts.append(f"\n[Table {table_num}]\n{table_text}")
        
        return "\n\n".join(text_parts)
    
    def _parse_with_pypdf2(self, file: Union[str, Path, BinaryIO]) -> str:
        """Parse PDF using PyPDF2."""
        text_parts = []
        
        if hasattr(file, 'read'):
            file_bytes = file.read()
            file.seek(0)
            pdf_file = io.BytesIO(file_bytes)
        else:
            pdf_file = open(file, 'rb') if isinstance(file, (str, Path)) else file
        
        try:
            reader = self._pypdf2.PdfReader(pdf_file)
            
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"--- Page {page_num} ---\n{page_text}")
        finally:
            if isinstance(file, (str, Path)):
                pdf_file.close()
        
        return "\n\n".join(text_parts)
    
    def _format_table(self, table: list) -> str:
        """Format a table as text."""
        if not table:
            return ""
        
        rows = []
        for row in table:
            cells = [str(cell).strip() if cell else "" for cell in row]
            rows.append(" | ".join(cells))
        
        return "\n".join(rows)

