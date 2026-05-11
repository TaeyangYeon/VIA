"""Router for image upload and management endpoints."""

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from backend.config import VIAConfig
from backend.services.image_store import image_store
from backend.services.image_validator import ImageValidator

router = APIRouter()
config = VIAConfig()

VALID_PURPOSES = {"analysis", "test"}


@router.post("/upload")
async def upload_image(file: UploadFile, purpose: str):
    if purpose not in VALID_PURPOSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid purpose '{purpose}'. Must be 'analysis' or 'test'.",
        )

    filename = file.filename or ""

    result = ImageValidator.validate_filename(filename)
    if not result.valid:
        raise HTTPException(status_code=422, detail=result.error)

    if not ImageValidator.validate_extension(filename):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid extension for '{filename}'. Allowed: .png, .jpg, .jpeg, .bmp, .tiff",
        )

    content = await file.read()
    if not ImageValidator.validate_file_size(content):
        raise HTTPException(
            status_code=422,
            detail="File size exceeds 50MB limit.",
        )

    if not ImageValidator.validate_image_integrity(content):
        raise HTTPException(
            status_code=422,
            detail="Invalid image data. The file could not be decoded as an image.",
        )

    dest_dir = Path(config.upload_dir) / purpose
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    dest_path.write_bytes(content)

    metadata = {
        "id": str(uuid.uuid4()),
        "filename": filename,
        "label": result.label,
        "index": result.index,
        "purpose": purpose,
        "path": str(dest_path),
    }
    return image_store.add(metadata)


@router.get("")
async def list_images(purpose: str | None = None, label: str | None = None):
    return image_store.list_all(purpose=purpose, label=label)


@router.get("/{image_id}")
async def get_image(image_id: str):
    entry = image_store.get(image_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")
    return entry


@router.delete("/{image_id}")
async def delete_image(image_id: str):
    deleted = image_store.delete(image_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")
    return {"message": "Image deleted."}


@router.delete("")
async def clear_images(purpose: str | None = None):
    image_store.clear(purpose=purpose)
    return {"message": "Images cleared."}
