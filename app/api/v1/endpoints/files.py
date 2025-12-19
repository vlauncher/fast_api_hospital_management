from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.api import deps
from app.services import cloudinary_service
from app.models.user import User

router = APIRouter()

@router.post("/upload", response_model=dict)
async def upload_file(
    file: UploadFile = File(...),
    folder: str = "hospital_management",
    current_user: User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Upload a file to Cloudinary.
    """
    # Optional: check file extension or size
    
    file_url = await cloudinary_service.upload_file(file.file, file.filename, folder=folder)
    if not file_url:
        raise HTTPException(status_code=500, detail="Failed to upload file to Cloudinary")
    
    return {"url": file_url}
