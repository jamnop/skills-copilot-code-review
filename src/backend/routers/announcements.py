"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId

from ..database import announcements_collection, teachers_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


def serialize_announcement(announcement: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-serializable format"""
    if announcement and "_id" in announcement:
        announcement["id"] = str(announcement["_id"])
        del announcement["_id"]
    return announcement


@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
def get_announcements(active_only: bool = Query(True)) -> List[Dict[str, Any]]:
    """
    Get all announcements or only active ones
    
    - active_only: If True, only return announcements that are currently active
    """
    query = {}
    
    if active_only:
        # Get current date in ISO format (YYYY-MM-DD)
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Filter for announcements that:
        # 1. Haven't expired yet (expiration_date >= current_date)
        # 2. Either have no start_date or start_date <= current_date
        query = {
            "expiration_date": {"$gte": current_date},
            "$or": [
                {"start_date": {"$exists": False}},
                {"start_date": None},
                {"start_date": {"$lte": current_date}}
            ]
        }
    
    announcements = []
    for announcement in announcements_collection.find(query).sort("created_at", -1):
        announcements.append(serialize_announcement(announcement))
    
    return announcements


@router.get("/{announcement_id}", response_model=Dict[str, Any])
def get_announcement(announcement_id: str) -> Dict[str, Any]:
    """Get a specific announcement by ID"""
    try:
        announcement = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return serialize_announcement(announcement)


@router.post("", response_model=Dict[str, Any])
@router.post("/", response_model=Dict[str, Any])
def create_announcement(
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: str = Query(...)
) -> Dict[str, Any]:
    """
    Create a new announcement - requires teacher authentication
    
    - message: The announcement message
    - expiration_date: Required expiration date (YYYY-MM-DD)
    - start_date: Optional start date (YYYY-MM-DD)
    - teacher_username: Username of the authenticated teacher
    """
    # Verify teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate dates
    try:
        datetime.strptime(expiration_date, "%Y-%m-%d")
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Validate message is not empty
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Create announcement document
    announcement = {
        "message": message.strip(),
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_by": teacher_username,
        "created_at": datetime.now().isoformat()
    }
    
    result = announcements_collection.insert_one(announcement)
    announcement["id"] = str(result.inserted_id)
    del announcement["_id"]
    
    return announcement


@router.put("/{announcement_id}", response_model=Dict[str, Any])
def update_announcement(
    announcement_id: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None,
    teacher_username: str = Query(...)
) -> Dict[str, Any]:
    """
    Update an existing announcement - requires teacher authentication
    
    - announcement_id: ID of the announcement to update
    - message: The announcement message
    - expiration_date: Required expiration date (YYYY-MM-DD)
    - start_date: Optional start date (YYYY-MM-DD)
    - teacher_username: Username of the authenticated teacher
    """
    # Verify teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate the announcement exists
    try:
        existing = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if not existing:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Validate dates
    try:
        datetime.strptime(expiration_date, "%Y-%m-%d")
        if start_date:
            datetime.strptime(start_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Validate message is not empty
    if not message or not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Update the announcement
    update_data = {
        "message": message.strip(),
        "start_date": start_date,
        "expiration_date": expiration_date,
        "updated_by": teacher_username,
        "updated_at": datetime.now().isoformat()
    }
    
    result = announcements_collection.update_one(
        {"_id": ObjectId(announcement_id)},
        {"$set": update_data}
    )
    
    if result.modified_count == 0 and result.matched_count == 0:
        raise HTTPException(status_code=500, detail="Failed to update announcement")
    
    # Return updated announcement
    updated = announcements_collection.find_one({"_id": ObjectId(announcement_id)})
    return serialize_announcement(updated)


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    teacher_username: str = Query(...)
) -> Dict[str, str]:
    """
    Delete an announcement - requires teacher authentication
    
    - announcement_id: ID of the announcement to delete
    - teacher_username: Username of the authenticated teacher
    """
    # Verify teacher authentication
    teacher = teachers_collection.find_one({"_id": teacher_username})
    if not teacher:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Delete the announcement
    try:
        result = announcements_collection.delete_one({"_id": ObjectId(announcement_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
