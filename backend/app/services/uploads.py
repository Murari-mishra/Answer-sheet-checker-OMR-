
import cv2
import numpy as np

from app.core.config import settings


class UploadValidationError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def quick_validate_upload(data: bytes, content_type: str) -> None:
    if content_type not in settings.allowed_content_types:
        raise UploadValidationError(
            "unsupported_content_type", f"Content type {content_type} not allowed"
        )
    if len(data) == 0:
        raise UploadValidationError("empty_file", "Uploaded file is empty")
    if len(data) > settings.max_upload_bytes:
        raise UploadValidationError(
            "file_too_large", f"File exceeds {settings.max_upload_bytes} bytes"
        )


def decode_and_validate_dimensions(data: bytes) -> np.ndarray:
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise UploadValidationError("invalid_image", "Could not decode image content")

    h, w = img.shape[:2]
    if h < settings.min_image_dimension or w < settings.min_image_dimension:
        raise UploadValidationError(
            "image_too_small", f"Image dimensions {w}x{h} below minimum"
        )
    if h > settings.max_image_dimension or w > settings.max_image_dimension:
        raise UploadValidationError(
            "image_too_large", f"Image dimensions {w}x{h} above maximum"
        )
    return img
