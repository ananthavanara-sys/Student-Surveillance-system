"""Enrollment endpoints."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.app.dependencies import get_face_system
from src.app.utils import decode_image
from src.face_system import FaceRecognitionSystem

router = APIRouter(tags=["enrollment"])


@router.post("/enroll")
async def enroll_person(
    name: str = Form(...),
    files: List[UploadFile] = File(...),
    face_system: FaceRecognitionSystem = Depends(get_face_system),
) -> dict[str, object]:
    """Enroll a person with one or more face images."""
    if not files:
        raise HTTPException(status_code=400, detail="At least one image file required")

    images = []
    for file in files:
        if not file.content_type.startswith("image/"):
            continue

        file_data = await file.read()
        try:
            image = decode_image(file_data)
        except HTTPException:
            continue
        images.append(image)

    if not images:
        raise HTTPException(status_code=400, detail="No valid images provided")

    if len(images) == 1:
        success = face_system.enroll_person(name, images[0])
        if not success:
            raise HTTPException(status_code=400, detail="No face detected in image")

        return {
            "message": f"Successfully enrolled {name}",
            "total_enrolled": face_system.get_enrolled_count(),
            "images_processed": 1,
        }

    result = face_system.enroll_multiple_images(name, images)
    if not result["success"]:
        raise HTTPException(status_code=400, detail="No faces detected in any images")

    return {
        "message": f"Successfully enrolled {name} with {result['enrolled_count']} images",
        "total_enrolled": face_system.get_enrolled_count(),
        "images_processed": len(images),
        "successful_enrollments": result["enrolled_count"],
        "total_embeddings": result["total_embeddings"],
        "avg_quality": round(result["avg_quality"], 3),
    }


@router.delete("/delete/{name}")
def delete_person(
    name: str,
    face_system: FaceRecognitionSystem = Depends(get_face_system),
) -> dict[str, object]:
    """Delete a specific person's enrollment data."""
    success = face_system.delete_person(name)
    if success:
        return {
            "message": f"Successfully deleted {name}",
            "remaining_count": face_system.get_enrolled_count(),
        }

    raise HTTPException(status_code=404, detail=f"Person '{name}' not found")


@router.delete("/clear")
def clear_all_data(
    face_system: FaceRecognitionSystem = Depends(get_face_system),
) -> dict[str, object]:
    """Clear all enrollment data."""
    face_system.clear_all_data()
    return {
        "message": "All enrollment data cleared",
        "enrolled_count": face_system.get_enrolled_count(),
    }
