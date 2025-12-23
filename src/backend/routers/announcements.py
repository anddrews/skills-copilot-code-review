"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("/active")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (current date is between start and expiration)"""
    current_time = datetime.utcnow().isoformat() + "Z"
    
    announcements = list(announcements_collection.find({
        "$and": [
            {"expiration_date": {"$gte": current_time}},
            {
                "$or": [
                    {"start_date": {"$exists": False}},
                    {"start_date": {"$lte": current_time}}
                ]
            }
        ]
    }).sort("created_at", -1))
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        announcement["_id"] = str(announcement["_id"])
    
    return announcements


@router.get("/all")
def get_all_announcements(username: str) -> List[Dict[str, Any]]:
    """Get all announcements (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    announcements = list(announcements_collection.find().sort("created_at", -1))
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        announcement["_id"] = str(announcement["_id"])
    
    return announcements


@router.post("/")
def create_announcement(
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate expiration date format and that it's in the future
    try:
        expiration_dt = datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
        if expiration_dt <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiration date format")
    
    # Validate start date if provided
    if start_date:
        try:
            datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start date format")
    
    announcement = {
        "message": message,
        "expiration_date": expiration_date,
        "created_by": username,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    if start_date:
        announcement["start_date"] = start_date
    
    result = announcements_collection.insert_one(announcement)
    announcement["_id"] = str(result.inserted_id)
    
    return announcement


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    username: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Update an existing announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    existing = announcements_collection.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Validate expiration date
    try:
        expiration_dt = datetime.fromisoformat(expiration_date.replace("Z", "+00:00"))
        if expiration_dt <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid expiration date format")
    
    # Validate start date if provided
    if start_date:
        try:
            datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start date format")
    
    update_data = {
        "message": message,
        "expiration_date": expiration_date
    }
    
    if start_date:
        update_data["start_date"] = start_date
    else:
        # Remove start_date if not provided
        announcements_collection.update_one(
            {"_id": obj_id},
            {"$unset": {"start_date": ""}}
        )
    
    announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    updated = announcements_collection.find_one({"_id": obj_id})
    updated["_id"] = str(updated["_id"])
    
    return updated


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str, username: str) -> Dict[str, str]:
    """Delete an announcement (requires authentication)"""
    # Verify user is authenticated
    teacher = teachers_collection.find_one({"_id": username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Validate announcement exists
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
