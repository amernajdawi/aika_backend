#!/usr/bin/env python3
"""Script to process only the Excel files that failed previously."""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.core.document_processor import save_uploaded_file, process_excel_file
from api.core.embeddings import create_document_embeddings
from api.core.onace_categories import load_document_onace_mapping

async def process_excel_file_direct(file_path: Path) -> Dict[str, Any]:
    """Process a single Excel file."""
    print(f"📊 Processing Excel file: {file_path.name}")
    
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
            metadata={"source": "excel_processing", "processed_date": "2025-01-01"}
        )
        
        # Create embeddings
        if doc_info.get("processed_content"):
            print(f"  🔄 Creating embeddings...")
            embedding_result = await create_document_embeddings(
                document_id=doc_info["document_id"],
                processed_content=doc_info["processed_content"],
                metadata=doc_info["metadata"]
            )
            
            if embedding_result.get("success"):
                chunks_count = embedding_result.get("chunks", 0)
                print(f"  ✅ Success - {chunks_count} chunks created")
                return {
                    "success": True,
                    "document_id": doc_info["document_id"],
                    "filename": file_path.name,
                    "chunks": chunks_count,
                    "onace_codes": doc_info.get("onace_codes", "0"),
                    "is_vsme": doc_info.get("is_vsme", False)
                }
            else:
                error_msg = embedding_result.get("error", "Unknown error")
                print(f"  ❌ Failed to create embeddings: {error_msg}")
                return {
                    "success": False,
                    "filename": file_path.name,
                    "error": error_msg
                }
        else:
            print(f"  ❌ No processed content")
            return {
                "success": False,
                "filename": file_path.name,
                "error": "No processed content"
            }
            
    except Exception as e:
        print(f"  ❌ Exception: {str(e)}")
        return {
            "success": False,
            "filename": file_path.name,
            "error": str(e)
        }

async def main():
    """Main function to process Excel files."""
    print("📊 Processing Excel Files")
    print("=" * 40)
    
    # Get the new_data folder path
    project_root = Path(__file__).parent.parent.parent.parent.parent
    new_data_folder = project_root / "new_data"
    
    if not new_data_folder.exists():
        print(f"❌ New data folder not found: {new_data_folder}")
        return
    
    # Get the specific Excel files that failed
    excel_files = [
        "G_2022_WateremissionCalculatingMethod.xlsx",
        "G_2023_SBTi_SteelTOOL.xlsx", 
        "VSME-Digital-Template-1.0.1.xlsx"
    ]
    
    files_to_process = []
    for filename in excel_files:
        file_path = new_data_folder / filename
        if file_path.exists():
            files_to_process.append(file_path)
        else:
            print(f"⚠️  File not found: {filename}")
    
    if not files_to_process:
        print("❌ No Excel files found to process")
        return
    
    print(f"📋 Found {len(files_to_process)} Excel files to process:")
    for file_path in files_to_process:
        print(f"   - {file_path.name}")
    
    print(f"\n🔄 Processing Excel files...")
    
    processed_count = 0
    failed_count = 0
    
    for i, file_path in enumerate(files_to_process, 1):
        print(f"\n[{i}/{len(files_to_process)}] {file_path.name}")
        
        result = await process_excel_file_direct(file_path)
        
        if result["success"]:
            processed_count += 1
        else:
            failed_count += 1
    
    # Final results
    print(f"\n✅ EXCEL PROCESSING COMPLETE!")
    print("-" * 40)
    print(f"✅ Successfully processed: {processed_count}")
    print(f"❌ Failed to process: {failed_count}")
    
    if processed_count > 0:
        print(f"\n🎉 {processed_count} Excel files now have embeddings!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
