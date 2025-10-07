#!/usr/bin/env python3
"""Script to process all documents from the new_data folder."""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.core.document_processor import save_uploaded_file, process_pdf_with_retry
from api.core.embeddings import create_document_embeddings
from api.core.onace_categories import load_document_onace_mapping

async def process_document_file(file_path: Path) -> Dict[str, Any]:
    """Process a single document file."""
    print(f"Processing: {file_path.name}")
    
    try:
        # Read the file
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Create a file-like object for the processor
        import io
        file_obj = io.BytesIO(file_content)
        
        # Process the document
        doc_info = save_uploaded_file(
            file=file_obj,
            filename=file_path.name,
            metadata={"source": "new_data_folder"}
        )
        
        # Create embeddings
        if doc_info.get("processed_content"):
            embedding_result = await create_document_embeddings(
                document_id=doc_info["document_id"],
                processed_content=doc_info["processed_content"],
                metadata=doc_info["metadata"]
            )
            
            if embedding_result["success"]:
                print(f"✅ Successfully processed {file_path.name} - {embedding_result['chunks']} chunks")
                return {
                    "success": True,
                    "document_id": doc_info["document_id"],
                    "filename": file_path.name,
                    "chunks": embedding_result["chunks"]
                }
            else:
                print(f"❌ Failed to create embeddings for {file_path.name}: {embedding_result.get('error')}")
                return {
                    "success": False,
                    "filename": file_path.name,
                    "error": embedding_result.get("error", "Unknown error")
                }
        else:
            print(f"❌ No processed content for {file_path.name}")
            return {
                "success": False,
                "filename": file_path.name,
                "error": "No processed content"
            }
            
    except Exception as e:
        print(f"❌ Error processing {file_path.name}: {str(e)}")
        return {
            "success": False,
            "filename": file_path.name,
            "error": str(e)
        }

async def main():
    """Main function to process all documents."""
    # Get the new_data folder path
    project_root = Path(__file__).parent.parent.parent.parent.parent
    new_data_folder = project_root / "new_data"
    
    if not new_data_folder.exists():
        print(f"❌ New data folder not found: {new_data_folder}")
        return
    
    # Get all PDF files
    pdf_files = list(new_data_folder.glob("*.pdf"))
    xlsx_files = list(new_data_folder.glob("*.xlsx"))
    all_files = pdf_files + xlsx_files
    
    print(f"Found {len(all_files)} files to process:")
    for file in all_files:
        print(f"  - {file.name}")
    
    if not all_files:
        print("No files to process.")
        return
    
    # Process files concurrently (but limit concurrency to avoid overwhelming the API)
    semaphore = asyncio.Semaphore(3)  # Process max 3 files at once
    
    async def process_with_semaphore(file_path):
        async with semaphore:
            return await process_document_file(file_path)
    
    print("\nStarting document processing...")
    tasks = [process_with_semaphore(file_path) for file_path in all_files]
    results = await asyncio.gather(*tasks)
    
    # Summary
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"\n📊 Processing Summary:")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    if successful:
        print(f"\n✅ Successfully processed:")
        for result in successful:
            print(f"  - {result['filename']} ({result['chunks']} chunks)")
    
    if failed:
        print(f"\n❌ Failed to process:")
        for result in failed:
            print(f"  - {result['filename']}: {result['error']}")
    
    print(f"\n🎉 Document processing complete!")

if __name__ == "__main__":
    asyncio.run(main())
