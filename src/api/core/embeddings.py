"""Document embedding using OpenAI API."""
import os
from typing import Dict, List, Optional, Any
import numpy as np
import tiktoken
import openai
from openai import OpenAI, AsyncOpenAI
import faiss
import pickle
import json
from pathlib import Path
from dotenv import load_dotenv
from ..core.document_processor import get_document_content
import asyncio

# Load environment variables
load_dotenv()

# Get OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Initialize the Async OpenAI client
client = AsyncOpenAI(api_key=api_key)

# Default embedding model
EMBEDDING_MODEL = "text-embedding-3-small"
# Default encoding for token counting
ENCODING = tiktoken.get_encoding("cl100k_base")
# Maximum tokens for embedding model
MAX_TOKENS = 8191
# Path to store the FAISS index
EMBEDDINGS_DIR = Path(os.getenv("EMBEDDINGS_DIR", "./src/api/data/embeddings"))

async def get_embedding(text: str, model: str = EMBEDDING_MODEL) -> List[float]:
    """Get embeddings for a text using OpenAI API."""
    text = text.replace("\n", " ")
    
    # Add retry logic
    max_retries = 3
    backoff_factor = 1.5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = await client.embeddings.create(input=[text], model=model)
            return response.data[0].embedding
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(f"Failed to get embedding after {max_retries} attempts: {str(e)}")
                raise
            
            # Exponential backoff
            wait_time = backoff_factor ** retry_count
            print(f"Embedding API error: {str(e)}. Retrying in {wait_time:.1f} seconds...")
            await asyncio.sleep(wait_time)

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 80) -> List[str]:
    """Split text into overlapping chunks of tokens."""
    tokens = ENCODING.encode(text)
    chunks = []
    
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk_tokens = tokens[i:i + chunk_size]
        if len(chunk_tokens) < 128:  # Skip chunks smaller than 128 tokens to maintain context
            continue
        chunks.append(ENCODING.decode(chunk_tokens))
    
    return chunks

async def create_document_embeddings(
    document_id: str,
    # Accept processed_content which can be str or List[Tuple[int, str]]
    processed_content: Any, 
    metadata: Optional[Dict] = None
) -> Dict:
    """Create embeddings for a document and store in FAISS index."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    
    document_data = {
        "document_id": document_id,
        "chunks": [],
        "metadata": metadata or {}
    }
    
    embeddings = []
    chunk_index_counter = 0

    # Handle based on content type
    if isinstance(processed_content, str):
        # Simple text document
        chunks = chunk_text(processed_content)
        for i, chunk in enumerate(chunks):
            try:
                embedding = await get_embedding(chunk)
                embeddings.append(embedding)
                document_data["chunks"].append({
                    "chunk_id": f"{document_id}_t{i}", # Indicate text chunk
                    "text": chunk,
                    "embedding_index": chunk_index_counter,
                    "page_number": None # No page number for plain text
                })
                chunk_index_counter += 1
            except Exception as e:
                print(f"Error embedding text chunk {i} for {document_id}: {e}")
    elif isinstance(processed_content, list):
        # List of (page_num, page_text) tuples (likely from PDF)
        for page_num, page_text in processed_content:
            if not page_text or not isinstance(page_text, str):
                continue # Skip empty pages or invalid data
                
            page_chunks = chunk_text(page_text)
            for i, chunk in enumerate(page_chunks):
                try:
                    embedding = await get_embedding(chunk)
                    embeddings.append(embedding)
                    document_data["chunks"].append({
                        "chunk_id": f"{document_id}_p{page_num}_c{i}", # Include page and chunk index
                        "text": chunk,
                        "embedding_index": chunk_index_counter,
                        "page_number": page_num # STORE THE PAGE NUMBER
                    })
                    chunk_index_counter += 1
                except Exception as e:
                    print(f"Error embedding chunk {i} from page {page_num} for {document_id}: {e}")
    else:
        # Handle error case or unsupported type
        error_message = f"Unsupported processed_content type: {type(processed_content)}"
        print(error_message)
        return {"success": False, "error": error_message}
        
    if not embeddings:
        # Check if content was just empty
        if not processed_content:
             return {"success": True, "document_id": document_id, "chunks": 0, "dimensions": None, "message": "Document was empty, skipping embedding."}
        return {"success": False, "error": "No valid embeddings created"}
    
    # Ensure dimension is correctly calculated
    dimension = len(embeddings[0]) if embeddings else 0
    if dimension > 0:
        embeddings_array = np.array(embeddings, dtype=np.float32)
        index_path = EMBEDDINGS_DIR / f"{document_id}.index"
        metadata_path = EMBEDDINGS_DIR / f"{document_id}.json"
        
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings_array)
        
        faiss.write_index(index, str(index_path))
        
        with open(metadata_path, "w") as f:
            json.dump(document_data, f)
    else:
        # Handle case where no embeddings were generated but content wasn't empty (e.g., all chunks failed)
        return {"success": False, "error": "Embeddings could not be generated for any chunks."}

    return {
        "success": True,
        "document_id": document_id,
        "chunks": len(document_data["chunks"]),
        "dimensions": dimension
    }

async def search_embeddings(
    document_id: str, 
    query: str, 
    top_k: int = 3
) -> List[Dict]:
    """Search document embeddings for similar chunks (async version)."""
    index_path = EMBEDDINGS_DIR / f"{document_id}.index"
    metadata_path = EMBEDDINGS_DIR / f"{document_id}.json"
    
    if not await asyncio.to_thread(index_path.exists) or not await asyncio.to_thread(metadata_path.exists):
        return []
    
    # Load index and metadata asynchronously
    index = await asyncio.to_thread(faiss.read_index, str(index_path))
    
    def load_json(path):
        with open(path, "r") as f:
            return json.load(f)
            
    document_data = await asyncio.to_thread(load_json, metadata_path)
    
    # Get query embedding asynchronously
    query_embedding = await get_embedding(query)
    query_embedding_array = np.array([query_embedding], dtype=np.float32)
    
    # FAISS search is CPU-bound, can run in thread executor if needed, but often fast enough.
    # For simplicity, keeping it synchronous for now within the async function.
    # If it becomes a bottleneck, wrap index.search in asyncio.to_thread.
    distances, indices = index.search(query_embedding_array, top_k) 
    
    # Prepare results
    results = []
    # Accessing document_data['chunks'] is fast, no need for async here
    chunks_data = document_data.get("chunks", [])
    for i, idx in enumerate(indices[0]):
        if 0 <= idx < len(chunks_data):
            chunk = chunks_data[idx]
            results.append({
                "chunk_id": chunk.get("chunk_id"), # Use .get for safety
                "text": chunk.get("text"),
                "score": float(distances[0][i]) # FAISS returns float32, ensure float
            })
            
    return results

async def search_all_documents(query: str, top_k: int = 3, user_onace_code: str = "0") -> List[Dict]:
    """Search across all document embeddings for similar chunks (async version)."""
    if not await asyncio.to_thread(EMBEDDINGS_DIR.exists):
        return []
    
    # Get all metadata files asynchronously
    def list_json_files(path):
        return list(path.glob("*.json"))
        
    metadata_files = await asyncio.to_thread(list_json_files, EMBEDDINGS_DIR)
    if not metadata_files:
        return []
    
    # Get query embedding asynchronously
    query_embedding = await get_embedding(query)
    query_embedding_array = np.array([query_embedding], dtype=np.float32)
    
    # --- Helper function to process a single document asynchronously ---
    async def process_single_document(metadata_file: Path) -> List[Dict]:
        document_id = metadata_file.stem
        index_path = metadata_file.with_suffix(".index")
        
        if not await asyncio.to_thread(index_path.exists):
            return []
            
        # Load index and metadata asynchronously
        index = await asyncio.to_thread(faiss.read_index, str(index_path))
        
        def load_json(path):
            with open(path, "r") as f:
                return json.load(f)
        document_data = await asyncio.to_thread(load_json, metadata_file)
        
        # Check ÖNACE relevance before searching
        doc_onace_codes = document_data.get("metadata", {}).get("onace_codes", "0")
        from .onace_categories import OnaceManager
        doc_onace_set = OnaceManager.parse_onace_codes(doc_onace_codes)
        
        # Skip if document is not relevant to user's industry
        if not OnaceManager.is_document_relevant(doc_onace_set, user_onace_code):
            return []
        
        # Search (sync within this task for now, see comment in search_embeddings)
        distances, indices = index.search(query_embedding_array, top_k)
        
        doc_results = []
        chunks_data = document_data.get("chunks", [])
        metadata_base = document_data.get("metadata", {}).copy()

        for i, idx in enumerate(indices[0]):
            if 0 <= idx < len(chunks_data):
                chunk = chunks_data[idx]
                
                chunk_metadata = metadata_base.copy() # Start with base doc metadata
                if "page_number" in chunk:
                    chunk_metadata["page_number"] = chunk["page_number"]
                
                # Add ÖNACE information to metadata
                chunk_metadata["onace_codes"] = doc_onace_codes
                chunk_metadata["is_vsme"] = document_data.get("metadata", {}).get("is_vsme", False)
                
                doc_results.append({
                    "document_id": document_id,
                    "chunk_id": chunk.get("chunk_id", f"{document_id}_{idx}"),
                    "text": chunk.get("text", ""),
                    "score": float(distances[0][i]), # Ensure float
                    "metadata": chunk_metadata 
                })
        return doc_results
    # --------------------------------------------------------------------

    # Gather results from all documents concurrently
    tasks = [process_single_document(mf) for mf in metadata_files]
    results_list = await asyncio.gather(*tasks)
    
    # Flatten the list of lists
    all_results = [item for sublist in results_list for item in sublist]
    
    # Sort by score (sync, fast operation)
    all_results.sort(key=lambda x: x["score"])
    return all_results[:top_k]

def get_all_documents() -> List[Dict]:
    """Get list of all documents in the documents directory."""
    documents_dir = Path(os.getenv("DOCUMENTS_DIR", "./data/documents"))
    if not documents_dir.exists():
        return []
    
    documents = []
    for file_path in documents_dir.glob("*"):
        if file_path.is_file():
            documents.append({
                "document_id": file_path.stem,
                "filename": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size
            })
    return documents

def get_all_embedded_documents() -> List[str]:
    """Get list of document IDs that have embeddings."""
    if not EMBEDDINGS_DIR.exists():
        return []
    
    embedded_docs = []
    for metadata_file in EMBEDDINGS_DIR.glob("*.json"):
        if metadata_file.with_suffix(".index").exists():
            embedded_docs.append(metadata_file.stem)
    return embedded_docs

async def verify_document_embeddings() -> Dict[str, Any]:
    """Verify that all documents in the documents directory have corresponding embeddings."""
    documents_dir = Path(os.getenv("DOCUMENTS_DIR", "./data/documents"))
    if not await asyncio.to_thread(documents_dir.exists):
        return {"is_complete": True, "missing": [], "total": 0}
        
    all_files = [p.stem for p in await asyncio.to_thread(list, documents_dir.glob("*")) if await asyncio.to_thread(p.is_file)]
    embedded_files = get_all_embedded_documents()
    
    missing = [doc_id for doc_id in all_files if doc_id not in embedded_files]
    
    return {
        "is_complete": not bool(missing),
        "missing": missing,
        "total": len(all_files)
    }

async def process_missing_embeddings() -> Dict[str, Any]:
    """Process documents that are missing embeddings."""
    verification = await verify_document_embeddings()
    if verification["is_complete"]:
        return {"message": "All documents already have embeddings.", "verification": verification}
    
    processed_count = 0
    failed_count = 0
    failed_docs = []
    
    documents_dir = Path(os.getenv("DOCUMENTS_DIR", "./data/documents"))

    for doc_id in verification["missing"]:
        # Reconstruct the expected path based on doc_id and potential extensions
        # This assumes doc_id is the stem and we need to find the actual file
        possible_files = list(documents_dir.glob(f"{doc_id}.*"))
        if not possible_files:
            print(f"Warning: Could not find original file for missing document ID: {doc_id}")
            failed_count += 1
            failed_docs.append(doc_id)
            continue
            
        file_path = possible_files[0] # Take the first match
        
        try:
            print(f"Processing missing embeddings for: {file_path.name}")
            # Get content and metadata
            content, metadata = get_document_content(str(file_path))
            
            # Create embeddings
            result = await create_document_embeddings(
                doc_id,
                content,
                metadata
            )
            if result["success"]:
                processed_count += 1
            else:
                failed_count += 1
                failed_docs.append(doc_id)
                print(f"Failed to create embeddings for {doc_id}: {result.get('error')}")
        except Exception as e:
            failed_count += 1
            failed_docs.append(doc_id)
            print(f"Error processing document {doc_id}: {str(e)}")
            
    # Re-verify after processing
    final_verification = await verify_document_embeddings()
    
    return {
        "message": f"Processed {processed_count} documents. Failed: {failed_count}",
        "failed_documents": failed_docs,
        "verification": final_verification
    } 