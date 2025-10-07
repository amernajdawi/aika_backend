"""Document handling routes."""
import os
import json
from typing import List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
import mimetypes

from ..models import DocumentResponse, TextDocumentRequest, FileListResponse, FileEntry
from ..core.document_processor import process_text_document, save_uploaded_file, get_document_content
from ..core.embeddings import create_document_embeddings, verify_document_embeddings, process_missing_embeddings

router = APIRouter(prefix="/documents", tags=["documents"])
# Get the documents directory from environment or default
DOCUMENTS_DIR = Path(os.getenv("DOCUMENTS_DIR", "./data/documents"))


@router.get("/files", response_model=FileListResponse)
async def get_all_files():
    """Get list of all files in the embeddings directory."""
    try:
        embeddings_dir = Path(os.getenv("EMBEDDINGS_DIR", "./data/embeddings"))
        if not embeddings_dir.exists():
            return FileListResponse(files=[], total_files=0)
        
        # Change to list of FileEntry
        file_entries: List[FileEntry] = []
        seen_files = set()  # Track unique files by document_id
        
        for metadata_file in embeddings_dir.glob("*.json"):
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    document_id = metadata.get("document_id")
                    
                    if not document_id or document_id in seen_files:
                        continue
                    
                    seen_files.add(document_id)
                    
                    filename = (metadata.get("metadata", {}).get("filename") or 
                              f"{document_id}{metadata.get('metadata', {}).get('file_type', '')}")
                    
                    # Append FileEntry object
                    file_entries.append(FileEntry(id=document_id, name=filename))
            except Exception as e:
                # Log error but continue if possible
                print(f"Error processing metadata file {metadata_file}: {e}") 
        
        return FileListResponse(
            files=file_entries, # Return list of FileEntry objects
            total_files=len(file_entries)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting file list: {str(e)}")


@router.get("/embedding-status")
async def get_embedding_status():
    """Get the status of document embeddings."""
    return verify_document_embeddings()


@router.post("/process-missing-embeddings")
async def process_missing():
    """Process embeddings for any documents that are missing them."""
    return await process_missing_embeddings()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document file and process it."""
    try:
        # Log upload attempt
        print(f"Processing upload for file: {file.filename}")
        
        document_info = save_uploaded_file(file.file, file.filename)
        
        # Process embeddings
        processed_content = document_info.get("processed_content") 
        
        if processed_content:
            print(f"Creating embeddings for document: {document_info['document_id']}")
            
            # Check content type for debugging
            content_type = type(processed_content)
            print(f"Content type: {content_type}")
            
            if isinstance(processed_content, str) and processed_content.startswith("Error"):
                # Don't attempt embedding if there was a processing error
                print(f"Skipping embedding due to processing error: {processed_content}")
                return DocumentResponse(
                    document_id=document_info["document_id"],
                    filename=document_info["filename"],
                    size=document_info["size"],
                    success=True,
                    message="Document uploaded but processing had errors. Embeddings not created."
                )
                
            embedding_result = await create_document_embeddings(
                document_info["document_id"],
                processed_content,
                document_info["metadata"]
            )
            
            if not embedding_result.get("success"):
                error_msg = f"Document {document_info['document_id']} uploaded but embedding failed: {embedding_result.get('error')}"
                print(f"Warning: {error_msg}")
                return DocumentResponse(
                    document_id=document_info["document_id"],
                    filename=document_info["filename"],
                    size=document_info["size"],
                    success=True,
                    message=error_msg
                )
        
        return DocumentResponse(
            document_id=document_info["document_id"],
            filename=document_info["filename"],
            size=document_info["size"],
            success=True
        )
    except Exception as e:
        error_msg = f"Error processing document: {str(e)}"
        print(f"Upload error: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/text", response_model=DocumentResponse)
async def process_text(request: TextDocumentRequest):
    """Process a text document directly."""
    try:
        document_info = process_text_document(
            request.content,
            request.filename,
            request.metadata
        )
        
        # Process embeddings
        create_document_embeddings(
            document_info["document_id"],
            request.content,
            document_info["metadata"]
        )
        
        return DocumentResponse(
            document_id=document_info["document_id"],
            filename=document_info["filename"],
            size=document_info["size"],
            success=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing text: {str(e)}")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str):
    """Get document information."""
    try:
        # Get document path
        documents_dir = Path(os.getenv("DOCUMENTS_DIR", "./data/documents"))
        found_file = None
        for ext in [".txt", ".md", ".csv", ".pdf"]:
            potential_path = documents_dir / f"{document_id}{ext}"
            if potential_path.exists():
                found_file = potential_path
                break
        
        if not found_file:
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
        
        return DocumentResponse(
            document_id=document_id,
            filename=found_file.name,
            size=found_file.stat().st_size,
            success=True
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting document: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its associated embeddings."""
    try:
        documents_dir = Path(os.getenv("DOCUMENTS_DIR", "./data/documents"))
        embeddings_dir = Path(os.getenv("EMBEDDINGS_DIR", "./data/embeddings"))
        
        deleted_files = []
        errors = []
        
        # 1. Delete the original document file
        found_document = False
        for ext in [".txt", ".md", ".csv", ".pdf"]:
            document_path = documents_dir / f"{document_id}{ext}"
            if document_path.exists():
                try:
                    document_path.unlink()  # Delete the file
                    deleted_files.append(f"document: {document_path.name}")
                    found_document = True
                    print(f"Deleted document file: {document_path}")
                except Exception as e:
                    errors.append(f"Failed to delete document {document_path.name}: {str(e)}")
        
        # 2. Delete embedding files (.json and .index)
        metadata_path = embeddings_dir / f"{document_id}.json"
        index_path = embeddings_dir / f"{document_id}.index"
        
        if metadata_path.exists():
            try:
                metadata_path.unlink()
                deleted_files.append(f"metadata: {metadata_path.name}")
                print(f"Deleted metadata file: {metadata_path}")
            except Exception as e:
                errors.append(f"Failed to delete metadata {metadata_path.name}: {str(e)}")
        
        if index_path.exists():
            try:
                index_path.unlink()
                deleted_files.append(f"index: {index_path.name}")
                print(f"Deleted index file: {index_path}")
            except Exception as e:
                errors.append(f"Failed to delete index {index_path.name}: {str(e)}")
        
        # 3. Check if any files were found and deleted
        if not found_document and not metadata_path.exists() and not index_path.exists():
            raise HTTPException(status_code=404, detail=f"Document with ID '{document_id}' not found")
        
        # 4. Return result
        response = {
            "success": len(errors) == 0,
            "message": f"Document '{document_id}' deletion completed",
            "deleted_files": deleted_files,
            "document_id": document_id
        }
        
        if errors:
            response["errors"] = errors
            response["message"] += f" with {len(errors)} error(s)"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting document: {str(e)}")


# New endpoint to download original files
@router.get("/download/{document_id}")
async def download_document(document_id: str):
    """Download the original document file."""
    try:
        found_file = None
        original_filename = None
        
        # 1. Find the corresponding metadata file to get the original filename and extension
        embeddings_dir = Path(os.getenv("EMBEDDINGS_DIR", "./data/embeddings"))
        metadata_path = embeddings_dir / f"{document_id}.json"
        
        file_extension = ".bin" # Default extension if not found
        if metadata_path.exists():
             with open(metadata_path, "r") as f:
                metadata = json.load(f)
                original_filename = metadata.get("metadata", {}).get("filename")
                file_extension = metadata.get("metadata", {}).get("file_type", file_extension)
        else:
            # Fallback: search for any metadata file containing this document_id
            # This is less efficient but provides robustness if naming convention changes
            for meta_file in embeddings_dir.glob("*.json"):
                try:
                    with open(meta_file, "r") as f:
                        meta = json.load(f)
                        if meta.get("document_id") == document_id:
                             original_filename = meta.get("metadata", {}).get("filename")
                             file_extension = meta.get("metadata", {}).get("file_type", file_extension)
                             break
                except: continue # Ignore files that can't be read
                
        # Use document_id as fallback filename if original not found
        if not original_filename:
             original_filename = f"{document_id}{file_extension}"

        # 2. Construct the path to the original file in DOCUMENTS_DIR
        # Use the original filename if available, otherwise fall back to document_id
        if original_filename:
            file_path = DOCUMENTS_DIR / original_filename
        else:
            file_path = DOCUMENTS_DIR / f"{document_id}{file_extension}"
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Original document file not found for ID: {document_id}")

        # 3. Determine MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            mime_type = "application/octet-stream" # Default if type unknown
            
        # 4. Return FileResponse
        return FileResponse(
            path=file_path,
            filename=original_filename, # Suggest the original filename to the browser
            media_type=mime_type,
            headers={"Content-Disposition": f"inline; filename*=UTF-8''{original_filename}"} # Display inline if possible
        )
    except HTTPException as e:
        raise e # Re-raise HTTP exceptions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}") 