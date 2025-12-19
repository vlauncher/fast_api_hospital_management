import cloudinary
import cloudinary.uploader
from app.core.config import settings

# Configure Cloudinary
if settings.CLOUDINARY_CLOUD_NAME:
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET
    )

async def upload_file(file_obj, filename: str, folder: str = "hospital_management") -> str:
    """
    Uploads a file to Cloudinary and returns the secure URL.
    """
    try:
        # Cloudinary uploader supports file-like objects
        response = cloudinary.uploader.upload(
            file_obj,
            public_id=filename.split('.')[0], # Use filename without extension as public_id (optional)
            folder=folder,
            resource_type="auto"
        )
        return response.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        return None
