"""FastAPI route for invoice extraction via Gemini Vision."""
import asyncio
import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Invoice, get_session
from src.services.gemini_service import ExtractionError, GeminiService

router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/jpg": "jpg",
    "image/tiff": "tiff",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
EXTRACTION_TIMEOUT = 30  # seconds


class LineItem(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float


class InvoiceExtraction(BaseModel):
    id: str
    vendor_name: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    due_date: Optional[str]
    subtotal: Optional[float]
    tax: Optional[float]
    total: Optional[float]
    currency: str
    line_items: list[LineItem]
    confidence_scores: dict[str, float]
    status: str


def get_gemini_service() -> GeminiService:
    """Dependency injection for GeminiService."""
    return GeminiService()


async def pdf_to_image_bytes(file_bytes: bytes) -> bytes:
    """Convert first page of PDF to PNG bytes."""
    try:
        from pdf2image import convert_from_bytes
        images = convert_from_bytes(file_bytes, first_page=1, last_page=1)
        if not images:
            raise HTTPException(status_code=422, detail="Could not convert PDF to image")
        img_byte_arr = io.BytesIO()
        images[0].save(img_byte_arr, format="PNG")
        return img_byte_arr.getvalue()
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="pdf2image not installed. Run: pip install pdf2image"
        )


@router.post("/api/extract", response_model=InvoiceExtraction)
async def extract_invoice(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
    gemini_service: GeminiService = Depends(get_gemini_service),
):
    """
    Extract structured data from an uploaded invoice PDF or image.

    - Validates file type and size
    - Converts PDF to image if needed
    - Calls Gemini Vision for extraction
    - Persists result to database
    """
    # Validate file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file type: {file.content_type}. Allowed: {list(ALLOWED_TYPES.keys())}"
        )

    # Read and validate file size
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"File too large: {len(file_bytes)} bytes. Max: {MAX_FILE_SIZE} bytes (10MB)"
        )

    # Convert PDF to image if needed
    mime_type = file.content_type
    image_bytes = file_bytes
    if file.content_type == "application/pdf":
        image_bytes = await pdf_to_image_bytes(file_bytes)
        mime_type = "image/png"

    # Call Gemini with timeout
    try:
        extraction_data = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: gemini_service.extract_invoice(image_bytes, mime_type)
            ),
            timeout=EXTRACTION_TIMEOUT
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Extraction timed out after 30 seconds")
    except ExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Persist to database
    invoice_id = str(uuid.uuid4())
    invoice = Invoice(
        id=invoice_id,
        file_name=file.filename,
        file_type=ALLOWED_TYPES[file.content_type],
        status="extracted",
        vendor_name=extraction_data.get("vendor_name"),
        invoice_number=extraction_data.get("invoice_number"),
        invoice_date=extraction_data.get("invoice_date"),
        due_date=extraction_data.get("due_date"),
        subtotal=extraction_data.get("subtotal"),
        tax=extraction_data.get("tax"),
        total=extraction_data.get("total"),
        currency=extraction_data.get("currency", "USD"),
        line_items=extraction_data.get("line_items", []),
        confidence_scores=extraction_data.get("confidence_scores", {}),
        created_at=datetime.now(timezone.utc),
    )
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)

    return InvoiceExtraction(
        id=invoice_id,
        vendor_name=invoice.vendor_name,
        invoice_number=invoice.invoice_number,
        invoice_date=str(invoice.invoice_date) if invoice.invoice_date else None,
        due_date=str(invoice.due_date) if invoice.due_date else None,
        subtotal=float(invoice.subtotal) if invoice.subtotal else None,
        tax=float(invoice.tax) if invoice.tax else None,
        total=float(invoice.total) if invoice.total else None,
        currency=invoice.currency,
        line_items=invoice.line_items or [],
        confidence_scores=invoice.confidence_scores or {},
        status=invoice.status,
    )
