"""Document processing for RAG system."""
import os
import uuid
from typing import Dict, Optional, BinaryIO, List, Tuple, Any
from pathlib import Path
import shutil
import pdfplumber
import logging
import time
import pandas as pd
from .onace_categories import OnaceManager, load_document_onace_mapping

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directory to store uploaded documents
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", "./src/api/data/documents"))

def process_text_document(
    file_content: str,
    filename: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict:
    """Process a text document directly from content."""
    # Create a unique document ID
    document_id = str(uuid.uuid4())
    
    # Create directory if it doesn't exist
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save the content
    document_path = DOCUMENTS_DIR / f"{document_id}.txt"
    with open(document_path, "w", encoding="utf-8") as f:
        f.write(file_content)
    
    # Prepare metadata
    doc_metadata = metadata or {}
    if filename:
        doc_metadata["filename"] = filename
    
    # Get ÖNACE codes for this document
    onace_mapping = load_document_onace_mapping()
    onace_codes = onace_mapping.get(filename or "", "0")
    
    return {
        "document_id": document_id,
        "filename": filename or f"{document_id}.txt",
        "path": str(document_path),
        "size": len(file_content),
        "metadata": doc_metadata,
        "onace_codes": onace_codes,
        "is_vsme": filename == "EU_2025_1710_VSME" if filename else False
    }

def process_excel_file(document_path: Path) -> Optional[str]:
    """Process an Excel file and return its content as text."""
    try:
        logger.info(f"Processing Excel file: {document_path}")
        
        # Read all sheets from the Excel file
        excel_data = pd.read_excel(document_path, sheet_name=None, engine='openpyxl')
        
        content_parts = []
        
        for sheet_name, df in excel_data.items():
            logger.info(f"Processing sheet: {sheet_name}")
            
            # Add sheet header
            content_parts.append(f"\n=== Sheet: {sheet_name} ===\n")
            
            # Convert DataFrame to string representation
            if not df.empty:
                # Get column names
                columns = df.columns.tolist()
                content_parts.append(f"Columns: {', '.join(str(col) for col in columns)}\n")
                
                # Convert to string with proper formatting
                df_string = df.to_string(index=False, na_rep='')
                content_parts.append(df_string)
                content_parts.append("\n")
                
                # Also add a more readable format for key-value pairs if applicable
                if len(df.columns) == 2:
                    content_parts.append("\nKey-Value pairs:\n")
                    for _, row in df.iterrows():
                        if pd.notna(row.iloc[0]) and pd.notna(row.iloc[1]):
                            content_parts.append(f"{row.iloc[0]}: {row.iloc[1]}\n")
            else:
                content_parts.append("(Empty sheet)\n")
        
        full_content = "".join(content_parts)
        logger.info(f"Successfully processed Excel file with {len(excel_data)} sheets")
        
        return full_content
        
    except Exception as e:
        logger.error(f"Error processing Excel file {document_path}: {str(e)}")
        return f"Error processing Excel file: {str(e)}"

def process_pdf_with_retry(document_path: Path, max_retries: int = 3) -> Optional[List[Tuple[int, str]]]:
    """Process a PDF file with retries, returning text per page."""
    for attempt in range(max_retries):
        try:
            with pdfplumber.open(document_path) as pdf:
                logger.info(f"Processing PDF: {document_path} (attempt {attempt + 1}/{max_retries})")
                page_texts: List[Tuple[int, str]] = []
                
                # Get total pages
                total_pages = len(pdf.pages)
                logger.info(f"PDF has {total_pages} pages")

                # Track multi-page tables
                table_in_progress = False
                table_buffer = []
                
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Add a small delay between pages to avoid potential issues
                        if page_num > 1:
                            time.sleep(0.1)
                        
                        # Extract tables first so we can process them properly
                        tables = page.extract_tables()
                        
                        # Process regular text
                        text = page.extract_text(x_tolerance=3, y_tolerance=3)
                        
                        # If no text found, try with more permissive tolerances
                        if not text or len(text.strip()) == 0:
                            text = page.extract_text(x_tolerance=5, y_tolerance=8)
                        
                        # Process tables with better formatting
                        if tables:
                            table_texts = []
                            for table in tables:
                                header_row = table[0] if table and len(table) > 0 else None
                                
                                # Check if this looks like a header row (all fields non-empty and relatively short)
                                is_header = header_row and all(cell and isinstance(cell, str) and len(cell) < 50 for cell in header_row if cell)
                                
                                table_text = ""
                                if is_header:
                                    # Format with header
                                    headers = [str(cell).strip() if cell else "" for cell in header_row]
                                    table_text += " | ".join(headers) + "\n"
                                    table_text += "-" * (sum(len(h) for h in headers) + (len(headers) - 1) * 3) + "\n"
                                    
                                    # Format data rows
                                    for row in table[1:]:
                                        table_text += " | ".join([str(cell).strip() if cell else "" for cell in row]) + "\n"
                                else:
                                    # Simple format for tables without clear headers
                                    for row in table:
                                        table_text += " | ".join([str(cell).strip() if cell else "" for cell in row]) + "\n"
                                
                                table_texts.append(table_text)
                                
                            # Check if table might continue to next page (heuristic)
                            if page_num < total_pages:
                                next_page_tables = pdf.pages[page_num].extract_tables()
                                if next_page_tables and tables[-1] and next_page_tables[0]:
                                    # Check column count match as a heuristic for continued table
                                    if len(tables[-1][0]) == len(next_page_tables[0][0]):
                                        table_in_progress = True
                                        table_buffer.append("\n".join(table_texts))
                                        continue
                            
                            # If we have a table buffer and this page doesn't continue it,
                            # add the entire multi-page table to the previous page
                            if table_in_progress:
                                table_buffer.append("\n".join(table_texts))
                                full_table = "\n\n".join(table_buffer)
                                
                                # Append to the previous page's text
                                if page_texts and page_num > 1:
                                    prev_page_num, prev_text = page_texts[-1]
                                    page_texts[-1] = (prev_page_num, f"{prev_text}\n\n{full_table}")
                                else:
                                    # If no previous page, add it to this page's text
                                    text = (text or "") + "\n\n" + full_table
                                
                                # Reset the table tracking
                                table_in_progress = False
                                table_buffer = []
                            else:
                                # Add tables to this page's text
                                text = (text or "") + "\n\n" + "\n\n".join(table_texts)
                        
                        # Add the processed text for this page
                        if text:
                            # Clean up the text - preserve paragraph structure but normalize whitespace
                            text = "\n\n".join(" ".join(line.split()) for line in text.split("\n\n") if line.strip())
                            page_texts.append((page_num, text))
                            logger.info(f"Successfully extracted text from page {page_num}/{total_pages}")
                        else:
                            logger.warning(f"No text extracted from page {page_num}/{total_pages}")
                    except Exception as page_error:
                        logger.error(f"Error extracting text from page {page_num}/{total_pages}: {str(page_error)}")
                        continue
                
                if not page_texts:
                    if attempt < max_retries - 1:
                        logger.warning(f"No text extracted in attempt {attempt + 1}, retrying...")
                        time.sleep(1)  # Wait before retrying
                        continue
                    else:
                        raise ValueError("No text could be extracted from any page after all attempts")
                
                logger.info(f"Successfully extracted text from {len(page_texts)} pages in {document_path}")
                return page_texts
                
        except Exception as e:
            logger.error(f"Error processing PDF {document_path} (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retrying
                continue
            else:
                raise
    
    return None

def save_uploaded_file(
    file: BinaryIO,
    filename: str,
    metadata: Optional[Dict] = None
) -> Dict:
    """Save an uploaded file and return its information."""
    # Create a unique document ID
    document_id = str(uuid.uuid4())
    
    # Create directory if it doesn't exist
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get file extension
    _, ext = os.path.splitext(filename)
    if not ext:
        ext = ".txt"
    
    # Save the file
    document_path = DOCUMENTS_DIR / f"{document_id}{ext}"
    with open(document_path, "wb") as f:
        shutil.copyfileobj(file, f)
    
    # Process different file types
    processed_content: Any = None
    if ext.lower() in (".txt", ".md", ".csv"):
        with open(document_path, "r", encoding="utf-8", errors="ignore") as f:
            processed_content = f.read()
    elif ext.lower() == ".pdf":
        try:
            processed_content = process_pdf_with_retry(document_path)
            if processed_content is None:
                raise ValueError("Failed to process PDF after all retries")
        except Exception as e:
            logger.error(f"Error processing PDF {document_path}: {str(e)}")
            processed_content = f"Error processing PDF: {str(e)}"
    elif ext.lower() in (".xlsx", ".xls"):
        try:
            processed_content = process_excel_file(document_path)
            if processed_content is None:
                raise ValueError("Failed to process Excel file")
        except Exception as e:
            logger.error(f"Error processing Excel file {document_path}: {str(e)}")
            processed_content = f"Error processing Excel file: {str(e)}"
    else:
        processed_content = f"Unsupported file type: {ext}"
    
    # Prepare metadata
    doc_metadata = metadata or {}
    doc_metadata["filename"] = filename
    doc_metadata["file_type"] = ext
    
    # Get ÖNACE codes for this document
    onace_mapping = load_document_onace_mapping()
    onace_codes = onace_mapping.get(filename, "0")
    
    return {
        "document_id": document_id,
        "filename": filename,
        "processed_content": processed_content,
        "path": str(document_path),
        "size": os.path.getsize(document_path),
        "metadata": doc_metadata,
        "onace_codes": onace_codes,
        "is_vsme": filename == "EU_2025_1710_VSME"
    }

def get_document_content(document_id: str) -> Optional[Any]:
    """Retrieve the processed content of a stored document."""
    # Look for the document in various extensions
    for ext in [".txt", ".md", ".csv", ".pdf", ".xlsx", ".xls"]:
        document_path = DOCUMENTS_DIR / f"{document_id}{ext}"
        if document_path.exists():
            if ext.lower() == ".pdf":
                try:
                    return process_pdf_with_retry(document_path)
                except Exception as e:
                    logger.error(f"Error reading PDF {document_path}: {str(e)}")
                    return None
            elif ext.lower() in (".xlsx", ".xls"):
                try:
                    return process_excel_file(document_path)
                except Exception as e:
                    logger.error(f"Error reading Excel file {document_path}: {str(e)}")
                    return None
            else:
                with open(document_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
    
    logger.error(f"Document not found: {document_id}")
    return None 