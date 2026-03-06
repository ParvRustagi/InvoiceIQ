"""FastAPI routes for exporting invoices to CSV or accounting webhook."""
import csv
import io
import json
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Invoice, get_session

router = APIRouter()


class ExportRequest(BaseModel):
    invoice_ids: list[UUID]


class WebhookResult(BaseModel):
    success_count: int
    failed_ids: list[str]
    errors: list[str]


CSV_COLUMNS = [
    "invoice_number", "vendor_name", "invoice_date", "due_date",
    "subtotal", "tax", "total", "currency", "line_items", "status"
]


async def fetch_invoices(
    invoice_ids: list[UUID],
    session: AsyncSession
) -> list[Invoice]:
    """Fetch invoices by IDs from database."""
    str_ids = [str(i) for i in invoice_ids]
    result = await session.execute(
        select(Invoice).where(Invoice.id.in_(str_ids))
    )
    return result.scalars().all()


def invoice_to_qbo_payload(invoice: Invoice) -> dict:
    """Convert Invoice to QuickBooks Online import schema."""
    return {
        "DocNumber": invoice.invoice_number,
        "TxnDate": str(invoice.invoice_date) if invoice.invoice_date else None,
        "DueDate": str(invoice.due_date) if invoice.due_date else None,
        "VendorRef": {"name": invoice.vendor_name},
        "TotalAmt": float(invoice.total) if invoice.total else 0.0,
        "TxnTaxDetail": {
            "TotalTax": float(invoice.tax) if invoice.tax else 0.0
        },
        "CurrencyRef": {"value": invoice.currency or "USD"},
        "Line": [
            {
                "Description": item.get("description", ""),
                "Amount": item.get("amount", 0),
                "DetailType": "AccountBasedExpenseLineDetail",
                "AccountBasedExpenseLineDetail": {
                    "UnitPrice": item.get("unit_price", 0),
                    "Qty": item.get("quantity", 1),
                }
            }
            for item in (invoice.line_items or [])
        ]
    }


@router.post("/api/export/csv")
async def export_csv(
    request: ExportRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Export invoices to CSV file download.

    Returns a StreamingResponse with CSV content.
    """
    invoices = await fetch_invoices(request.invoice_ids, session)

    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found for given IDs")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS)
    writer.writeheader()

    for invoice in invoices:
        writer.writerow({
            "invoice_number": invoice.invoice_number or "",
            "vendor_name": invoice.vendor_name or "",
            "invoice_date": str(invoice.invoice_date) if invoice.invoice_date else "",
            "due_date": str(invoice.due_date) if invoice.due_date else "",
            "subtotal": float(invoice.subtotal) if invoice.subtotal else "",
            "tax": float(invoice.tax) if invoice.tax else "",
            "total": float(invoice.total) if invoice.total else "",
            "currency": invoice.currency or "USD",
            "line_items": json.dumps(invoice.line_items or []),
            "status": invoice.status,
        })

    # Mark as exported
    now = datetime.now(timezone.utc)
    for invoice in invoices:
        invoice.status = "exported"
        invoice.exported_at = now
    await session.commit()

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices_export.csv"}
    )


@router.post("/api/export/webhook", response_model=WebhookResult)
async def export_webhook(
    request: ExportRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Export invoices to accounting system via webhook POST.

    Posts each invoice as JSON to ACCOUNTING_WEBHOOK_URL env var
    using QuickBooks Online schema.
    """
    webhook_url = os.getenv("ACCOUNTING_WEBHOOK_URL")
    if not webhook_url:
        raise HTTPException(
            status_code=500,
            detail="ACCOUNTING_WEBHOOK_URL environment variable not set"
        )

    invoices = await fetch_invoices(request.invoice_ids, session)
    if not invoices:
        raise HTTPException(status_code=404, detail="No invoices found for given IDs")

    success_count = 0
    failed_ids = []
    errors = []
    now = datetime.now(timezone.utc)

    async with httpx.AsyncClient(timeout=30.0) as client:
        for invoice in invoices:
            payload = invoice_to_qbo_payload(invoice)
            try:
                response = await client.post(webhook_url, json=payload)
                response.raise_for_status()
                invoice.status = "exported"
                invoice.exported_at = now
                success_count += 1
            except httpx.HTTPError as e:
                failed_ids.append(str(invoice.id))
                errors.append(f"Invoice {invoice.id}: {str(e)}")

    await session.commit()

    return WebhookResult(
        success_count=success_count,
        failed_ids=failed_ids,
        errors=errors,
    )
