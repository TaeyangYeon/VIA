"""Router for image upload and management endpoints."""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from backend.config import VIAConfig
from backend.services.image_validator import ImageValidator

router = APIRouter()
config = VIAConfig()

VALID_PURPOSES = {"analysis", "test"}


@router.post("/upload")
async def upload_image(file: UploadFile, purpose: str):
    # 1. Validate purpose
    if purpose not in VALID_PURPOSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid purpose '{purpose}'. Must be 'analysis' or 'test'.",
        )

    filename = file.filename or ""

    # 2. Validate filename convention
    result = ImageValidator.validate_filename(filename)
    if not result.valid:
        raise HTTPException(status_code=422, detail=result.error)

    # 3. Validate extension
    if not ImageValidator.validate_extension(filename):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid extension for '{filename}'. Allowed: .png, .jpg, .jpeg, .bmp, .tiff",
        )

    # 4. Read content and validate file size
    content = await file.read()
    if not ImageValidator.validate_file_size(content):
        raise HTTPException(
            status_code=422,
            detail="File size exceeds 50MB limit.",
        )

    # 5. Validate image integrity
    if not ImageValidator.validate_image_integrity(content):
        raise HTTPException(
            status_code=422,
            detail="Invalid image data. The file could not be decoded as an image.",
        )

    # Save file to disk
    dest_dir = Path(config.upload_dir) / purpose
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    dest_path.write_bytes(content)

    return {
        "id": str(uuid.uuid4()),
        "filename": filename,
        "label": result.label,
        "index": result.index,
        "purpose": purpose,
        "path": str(dest_path),
    }
