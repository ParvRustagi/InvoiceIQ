"""Gemini Vision service for invoice extraction."""
import json
import logging
from dataclasses import dataclass
from typing import Any

import google.generativeai as genai

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when Gemini response cannot be parsed into structured data."""
    pass


@dataclass
class GeminiService:
    """Wraps Gemini Vision SDK for invoice field extraction."""

    gemini_client: Any = None

    def __post_init__(self):
        if self.gemini_client is None:
            self.gemini_client = genai.GenerativeModel("gemini-1.5-flash")

    def build_extraction_prompt(self) -> str:
        """Build the structured extraction prompt for Gemini."""
        return """You are an invoice data extraction assistant.
Extract all invoice fields from the image and return ONLY valid JSON with no prose, no markdown, no code fences.

Return exactly this structure:
{
  "vendor_name": "string or null",
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "subtotal": number or null,
  "tax": number or null,
  "total": number or null,
  "currency": "USD",
  "line_items": [
    {
      "description": "string",
      "quantity": number,
      "unit_price": number,
      "amount": number
    }
  ],
  "confidence_scores": {
    "vendor_name": 0.0,
    "invoice_number": 0.0,
    "invoice_date": 0.0,
    "due_date": 0.0,
    "subtotal": 0.0,
    "tax": 0.0,
    "total": 0.0
  }
}

Rules:
- confidence_scores values must be floats between 0.0 and 1.0
- Use null for any field you cannot find or are uncertain about
- Return ONLY the JSON object, nothing else"""

    def extract_invoice(self, image_bytes: bytes, mime_type: str) -> dict:
        """
        Extract structured invoice data from image bytes using Gemini Vision.

        Args:
            image_bytes: Raw image bytes (PNG, JPG, TIFF)
            mime_type: MIME type of the image (e.g. image/png)

        Returns:
            dict with invoice fields and confidence_scores

        Raises:
            ExtractionError: If Gemini response cannot be parsed as JSON
        """
        prompt = self.build_extraction_prompt()

        image_part = {
            "inline_data": {
                "mime_type": mime_type,
                "data": image_bytes
            }
        }

        logger.debug("Calling Gemini model: gemini-1.5-flash")

        response = self.gemini_client.generate_content([prompt, image_part])

        raw_text = response.text.strip()

        # Strip markdown code fences if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1])

        try:
            result = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise ExtractionError(
                f"Failed to parse Gemini response as JSON: {e}\nRaw response: {raw_text[:200]}"
            )

        logger.debug(
            "Extraction complete. Token count: %s",
            getattr(response, "usage_metadata", {})
        )

        return result
