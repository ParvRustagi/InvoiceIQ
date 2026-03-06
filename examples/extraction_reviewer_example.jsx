// Example React component: ExtractionReviewer
// This example shows the structure for editing and confirming extracted invoice data

import React, { useState } from 'react';

export function ExtractionReviewerExample() {
  const [extraction, setExtraction] = useState({
    vendor_name: 'Vendor Name',
    invoice_number: 'INV-001',
    invoice_date: '2024-01-01',
    due_date: '2024-01-31',
    subtotal: 100.00,
    tax: 10.00,
    total: 110.00,
    line_items: [
      {
        description: 'Service',
        quantity: 1,
        unit_price: 100.00,
        amount: 100.00
      }
    ],
    confidence_scores: {
      vendor_name: 0.95,
      invoice_number: 0.92,
      invoice_date: 0.88,
      due_date: 0.75,
      subtotal: 0.98,
      tax: 0.85,
      total: 0.99
    }
  });

  const handleConfirm = () => {
    // Confirm edited extraction
  };

  const handleReject = () => {
    // Reject and request re-extraction
  };

  return (
    <div>
      <h2>Review Extracted Data</h2>
      {/* Editable field components with confidence badges */}
      {/* Line items table with edit capability */}
      {/* Confirm/Reject buttons */}
    </div>
  );
}
