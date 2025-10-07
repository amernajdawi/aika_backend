#!/usr/bin/env python3
"""
Script to upload existing data to Railway deployment.
This script helps you migrate your local data to Railway.
"""

import os
import sys
import requests
import json
from pathlib import Path

def upload_documents(api_url, documents_dir):
    """Upload all documents to the Railway deployment."""
    documents_path = Path(documents_dir)
    
    if not documents_path.exists():
        print(f"Documents directory {documents_dir} not found!")
        return False
    
    pdf_files = list(documents_path.glob("*.pdf"))
    xlsx_files = list(documents_path.glob("*.xlsx"))
    
    print(f"Found {len(pdf_files)} PDF files and {len(xlsx_files)} Excel files")
    
    # Upload PDF files
    for pdf_file in pdf_files:
        print(f"Uploading {pdf_file.name}...")
        try:
            with open(pdf_file, 'rb') as f:
                files = {'file': (pdf_file.name, f, 'application/pdf')}
                response = requests.post(f"{api_url}/documents/upload", files=files)
                
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Uploaded {pdf_file.name} - ID: {result.get('document_id')}")
            else:
                print(f"❌ Failed to upload {pdf_file.name}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error uploading {pdf_file.name}: {e}")
    
    # Upload Excel files
    for xlsx_file in xlsx_files:
        print(f"Uploading {xlsx_file.name}...")
        try:
            with open(xlsx_file, 'rb') as f:
                files = {'file': (xlsx_file.name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                response = requests.post(f"{api_url}/documents/upload", files=files)
                
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Uploaded {xlsx_file.name} - ID: {result.get('document_id')}")
            else:
                print(f"❌ Failed to upload {xlsx_file.name}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error uploading {xlsx_file.name}: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python upload_data_to_railway.py <railway_api_url>")
        print("Example: python upload_data_to_railway.py https://your-app.railway.app")
        sys.exit(1)
    
    api_url = sys.argv[1].rstrip('/')
    documents_dir = "src/api/data/documents"
    
    print(f"Uploading documents from {documents_dir} to {api_url}")
    print("Make sure your Railway deployment is running and accessible!")
    
    # Test connection
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Railway API is accessible")
        else:
            print(f"❌ Railway API returned status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to Railway API: {e}")
        return
    
    upload_documents(api_url, documents_dir)
    print("\n🎉 Data upload completed!")

if __name__ == "__main__":
    main()
