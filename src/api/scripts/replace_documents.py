#!/usr/bin/env python3
"""Script to replace old documents with new ones from new_data folder."""

import os
import sys
import asyncio
import shutil
from pathlib import Path
from typing import Dict, Any

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent))

from core.document_processor import save_uploaded_file, process_pdf_with_retry
from core.embeddings import create_document_embeddings, EMBEDDINGS_DIR
from core.onace_categories import load_document_onace_mapping

async def clear_old_documents():
    """Clear old documents and embeddings."""
    print("🧹 Clearing old documents and embeddings...")
    
    # Clear documents directory
    documents_dir = Path(os.getenv("DOCUMENTS_DIR", "./src/api/data/documents"))
    if documents_dir.exists():
        for file in documents_dir.glob("*"):
            if file.is_file():
                file.unlink()
                print(f"   Removed: {file.name}")
    
    # Clear embeddings directory
    if EMBEDDINGS_DIR.exists():
        for file in EMBEDDINGS_DIR.glob("*"):
            if file.is_file():
                file.unlink()
                print(f"   Removed embedding: {file.name}")
    
    print("✅ Old documents cleared!")

async def process_document_file(file_path: Path) -> Dict[str, Any]:
    """Process a single document file."""
    print(f"📄 Processing: {file_path.name}")
    
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
            metadata={"source": "new_data_folder", "processed_date": "2025-01-27"}
        )
        
        # Create embeddings
        if doc_info.get("processed_content"):
            embedding_result = await create_document_embeddings(
                document_id=doc_info["document_id"],
                processed_content=doc_info["processed_content"],
                metadata=doc_info["metadata"]
            )
            
            if embedding_result["success"]:
                print(f"   ✅ {file_path.name} - {embedding_result['chunks']} chunks")
                return {
                    "success": True,
                    "document_id": doc_info["document_id"],
                    "filename": file_path.name,
                    "chunks": embedding_result["chunks"],
                    "onace_codes": doc_info.get("onace_codes", "0"),
                    "is_vsme": doc_info.get("is_vsme", False)
                }
            else:
                print(f"   ❌ Failed to create embeddings: {embedding_result.get('error')}")
                return {
                    "success": False,
                    "filename": file_path.name,
                    "error": embedding_result.get("error", "Unknown error")
                }
        else:
            print(f"   ❌ No processed content")
            return {
                "success": False,
                "filename": file_path.name,
                "error": "No processed content"
            }
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {
            "success": False,
            "filename": file_path.name,
            "error": str(e)
        }

async def main():
    """Main function to replace all documents."""
    print("🚀 Starting Document Replacement Process")
    print("=" * 60)
    
    # Get the new_data folder path
    project_root = Path(__file__).parent.parent.parent.parent
    new_data_folder = project_root / "new_data"
    
    if not new_data_folder.exists():
        print(f"❌ New data folder not found: {new_data_folder}")
        return
    
    # Clear old documents first
    await clear_old_documents()
    
    # Get all files to process
    pdf_files = list(new_data_folder.glob("*.pdf"))
    xlsx_files = list(new_data_folder.glob("*.xlsx"))
    all_files = pdf_files + xlsx_files
    
    print(f"\n📋 Found {len(all_files)} files to process:")
    
    # Show VSME first (most important)
    vsme_files = [f for f in all_files if "VSME" in f.name]
    other_files = [f for f in all_files if "VSME" not in f.name]
    
    print(f"\n🎯 VSME Documents ({len(vsme_files)}):")
    for file in vsme_files:
        print(f"   - {file.name}")
    
    print(f"\n📄 Other Documents ({len(other_files)}):")
    for file in other_files[:10]:  # Show first 10
        print(f"   - {file.name}")
    if len(other_files) > 10:
        print(f"   ... and {len(other_files) - 10} more")
    
    # Process VSME files first (priority)
    print(f"\n🔄 Processing VSME documents first...")
    vsme_tasks = [process_document_file(file_path) for file_path in vsme_files]
    vsme_results = await asyncio.gather(*vsme_tasks)
    
    # Process other files with limited concurrency
    print(f"\n🔄 Processing other documents...")
    semaphore = asyncio.Semaphore(3)  # Process max 3 files at once
    
    async def process_with_semaphore(file_path):
        async with semaphore:
            return await process_document_file(file_path)
    
    other_tasks = [process_with_semaphore(file_path) for file_path in other_files]
    other_results = await asyncio.gather(*other_tasks)
    
    # Combine results
    all_results = vsme_results + other_results
    
    # Summary
    successful = [r for r in all_results if r["success"]]
    failed = [r for r in all_results if not r["success"]]
    
    print(f"\n📊 Processing Summary:")
    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    
    # Show VSME results
    vsme_successful = [r for r in vsme_results if r["success"]]
    print(f"\n🎯 VSME Documents:")
    for result in vsme_successful:
        print(f"   ✅ {result['filename']} ({result['chunks']} chunks) - ÖNACE: {result['onace_codes']}")
    
    # Show other successful results
    other_successful = [r for r in other_results if r["success"]]
    print(f"\n📄 Other Documents (showing first 10):")
    for result in other_successful[:10]:
        print(f"   ✅ {result['filename']} ({result['chunks']} chunks) - ÖNACE: {result['onace_codes']}")
    
    if len(other_successful) > 10:
        print(f"   ... and {len(other_successful) - 10} more successful documents")
    
    # Show failed results
    if failed:
        print(f"\n❌ Failed Documents:")
        for result in failed:
            print(f"   ❌ {result['filename']}: {result['error']}")
    
    # Show ÖNACE distribution
    print(f"\n🏭 ÖNACE Distribution:")
    onace_counts = {}
    for result in successful:
        onace_codes = result.get('onace_codes', '0')
        onace_counts[onace_codes] = onace_counts.get(onace_codes, 0) + 1
    
    for codes, count in sorted(onace_counts.items()):
        print(f"   ÖNACE {codes}: {count} documents")
    
    print(f"\n🎉 Document replacement complete!")
    print(f"📈 Total documents processed: {len(successful)}")
    print(f"🎯 VSME documents: {len(vsme_successful)}")
    print(f"🏭 Industry-specific documents: {len([r for r in successful if r.get('onace_codes', '0') != '0'])}")

if __name__ == "__main__":
    asyncio.run(main())
