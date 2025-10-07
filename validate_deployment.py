#!/usr/bin/env python3
"""
Comprehensive validation script for Railway deployment.
This script checks all components to ensure successful deployment.
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - MISSING")
        return False

def check_dockerfile():
    """Validate Dockerfile configuration."""
    print("\n🐳 Dockerfile Validation:")
    
    dockerfile_path = "Dockerfile"
    if not check_file_exists(dockerfile_path, "Dockerfile"):
        return False
    
    with open(dockerfile_path, 'r') as f:
        content = f.read()
    
    checks = [
        ("FROM python:3.13-slim", "Python 3.13 base image"),
        ("WORKDIR /app", "Working directory set"),
        ("COPY src/ ./src", "Source code copying"),
        ("EXPOSE $PORT", "Port exposure"),
        ("ENTRYPOINT", "Entrypoint defined"),
        ("uvicorn", "Uvicorn server"),
        ("/app/data/documents", "Documents directory"),
        ("/app/data/embeddings", "Embeddings directory")
    ]
    
    all_good = True
    for check, description in checks:
        if check in content:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - MISSING")
            all_good = False
    
    return all_good

def check_railway_config():
    """Validate Railway configuration."""
    print("\n🚂 Railway Configuration:")
    
    if not check_file_exists("railway.json", "Railway config"):
        return False
    
    try:
        with open("railway.json", 'r') as f:
            config = json.load(f)
        
        checks = [
            ("build.builder", "DOCKERFILE", "Docker builder"),
            ("build.dockerfilePath", "Dockerfile", "Dockerfile path"),
            ("deploy.healthcheckPath", "/health", "Health check"),
        ]
        
        # Check start command separately
        start_cmd = config.get("deploy", {}).get("startCommand", "")
        if "uvicorn" in start_cmd and "src.api.app:app" in start_cmd:
            print(f"  ✅ Start command: {start_cmd}")
        else:
            print(f"  ❌ Start command: Expected uvicorn with src.api.app:app, got '{start_cmd}'")
            all_good = False
        
        all_good = True
        for path, expected, description in checks:
            keys = path.split('.')
            value = config
            for key in keys:
                value = value.get(key, None)
                if value is None:
                    break
            
            if value == expected:
                print(f"  ✅ {description}: {value}")
            else:
                print(f"  ❌ {description}: Expected '{expected}', got '{value}'")
                all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"  ❌ Error reading railway.json: {e}")
        return False

def check_application_structure():
    """Validate application structure."""
    print("\n📁 Application Structure:")
    
    required_files = [
        ("src/api/app.py", "Main application"),
        ("src/api/__init__.py", "API package init"),
        ("src/api/routers/__init__.py", "Routers package init"),
        ("src/api/routers/documents.py", "Documents router"),
        ("src/api/routers/qa.py", "QA router"),
        ("src/api/routers/chat.py", "Chat router"),
        ("src/api/routers/onace.py", "ONACE router"),
        ("src/api/core/__init__.py", "Core package init"),
        ("pyproject.toml", "Project configuration"),
        ("Procfile", "Process file"),
    ]
    
    all_good = True
    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_good = False
    
    return all_good

def check_data_structure():
    """Validate data structure."""
    print("\n📊 Data Structure:")
    
    data_dir = Path("src/api/data")
    if not data_dir.exists():
        print("❌ Data directory missing")
        return False
    
    documents_dir = data_dir / "documents"
    embeddings_dir = data_dir / "embeddings"
    
    pdf_count = len(list(documents_dir.glob("*.pdf"))) if documents_dir.exists() else 0
    xlsx_count = len(list(documents_dir.glob("*.xlsx"))) if documents_dir.exists() else 0
    index_count = len(list(embeddings_dir.glob("*.index"))) if embeddings_dir.exists() else 0
    json_count = len(list(embeddings_dir.glob("*.json"))) if embeddings_dir.exists() else 0
    
    print(f"  📄 PDF files: {pdf_count}")
    print(f"  📊 Excel files: {xlsx_count}")
    print(f"  🔍 FAISS indexes: {index_count}")
    print(f"  📋 JSON metadata: {json_count}")
    
    if pdf_count > 0 and index_count > 0:
        print("  ✅ Data structure looks good")
        return True
    else:
        print("  ❌ Missing essential data files")
        return False

def check_dependencies():
    """Validate dependencies."""
    print("\n📦 Dependencies:")
    
    if not check_file_exists("pyproject.toml", "Project config"):
        return False
    
    try:
        with open("pyproject.toml", 'r') as f:
            content = f.read()
        
        required_deps = [
            "fastapi",
            "uvicorn", 
            "openai",
            "faiss-cpu",
            "python-dotenv",
            "pydantic",
            "tiktoken",
            "numpy",
            "python-multipart",
            "pdfplumber",
            "pandas",
            "openpyxl"
        ]
        
        all_good = True
        for dep in required_deps:
            if dep in content:
                print(f"  ✅ {dep}")
            else:
                print(f"  ❌ {dep} - MISSING")
                all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"  ❌ Error reading pyproject.toml: {e}")
        return False

def check_environment_setup():
    """Check environment setup."""
    print("\n🔧 Environment Setup:")
    
    # Check if .env.example exists
    if check_file_exists("railway.env.example", "Environment template"):
        print("  ✅ Environment template available")
    else:
        print("  ⚠️  No environment template found")
    
    print("  📝 Required environment variables:")
    print("    - OPENAI_API_KEY (set in Railway dashboard)")
    print("    - DOCUMENTS_DIR (default: /app/data/documents)")
    print("    - EMBEDDINGS_DIR (default: /app/data/embeddings)")
    print("    - PORT (set by Railway)")
    
    return True

def main():
    """Run all validation checks."""
    print("🚀 Railway Deployment Validation")
    print("=" * 50)
    
    checks = [
        ("Dockerfile", check_dockerfile),
        ("Railway Config", check_railway_config),
        ("App Structure", check_application_structure),
        ("Data Structure", check_data_structure),
        ("Dependencies", check_dependencies),
        ("Environment", check_environment_setup),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY:")
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL CHECKS PASSED! Ready for Railway deployment!")
        print("\nNext steps:")
        print("1. git add . && git commit -m 'Ready for Railway'")
        print("2. git push origin main")
        print("3. Deploy on Railway dashboard")
        print("4. Set OPENAI_API_KEY in Railway environment variables")
        print("5. Test your API at https://your-app.railway.app/health")
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
