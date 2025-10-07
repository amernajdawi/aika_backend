"""ÖNACE categories router."""
from typing import List, Dict
from fastapi import APIRouter
from ..core.onace_categories import OnaceManager, OnaceCategory

router = APIRouter(prefix="/onace", tags=["onace"])

@router.get("/categories")
async def get_onace_categories() -> Dict[str, List[Dict]]:
    """Get all ÖNACE categories."""
    categories = OnaceManager.get_all_categories()
    
    # Convert to frontend-friendly format
    category_list = []
    for code, category in categories.items():
        category_list.append({
            "code": category.code,
            "name_german": category.name_german,
            "name_english": category.name_english,
            "description": category.description
        })
    
    return {"categories": category_list}

@router.get("/categories/{code}")
async def get_onace_category(code: str) -> Dict:
    """Get a specific ÖNACE category by code."""
    category = OnaceManager.get_category(code)
    if not category:
        return {"error": f"Category {code} not found"}
    
    return {
        "code": category.code,
        "name_german": category.name_german,
        "name_english": category.name_english,
        "description": category.description
    }

@router.post("/parse-codes")
async def parse_onace_codes(onace_string: str) -> Dict:
    """Parse ÖNACE codes from a string."""
    codes = OnaceManager.parse_onace_codes(onace_string)
    names = OnaceManager.get_category_names(codes)
    
    return {
        "codes": list(codes),
        "names": names,
        "original_string": onace_string
    }
