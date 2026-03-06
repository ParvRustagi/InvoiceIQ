import { useState } from "react";

function confidenceColor(score) {
  if (score >= 0.85) return { bg: "#F0FFF4", border: "#9AE6B4", text: "#276749", label: "High" };
  if (score >= 0.70) return { bg: "#FFFBEB", border: "#FBD38D", text: "#744210", label: "Medium" };
  return { bg: "#FFF5F5", border: "#FEB2B2", text: "#C53030", label: "Low" };
}

function ConfidenceBadge({ score }) {
  const c = confidenceColor(score);
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, padding: "2px 7px", borderRadius: 20,
      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
      letterSpacing: 0.5
    }}>
      {c.label} {Math.round(score * 100)}%
    </span>
  );
}

function EditableField({ label, value, onChange, confidence }) {
  const needsReview = confidence < 0.70;
  return (
    <div style={{
      marginBottom: 14,
      background: needsReview ? "#FFF5F5" : "#F7FAFC",
      border: `1px solid ${needsReview ? "#FEB2B2" : "#E2E8F0"}`,
      borderRadius: 8, padding: "10px 14px"
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
        <label style={{ fontSize: 11, fontWeight: 700, color: "#718096", textTransform: "uppercase", letterSpacing: 1 }}>
          {label}
        </label>
        {confidence !== undefined && <ConfidenceBadge score={confidence} />}
      </div>
      <input
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        style={{
          width: "100%", border: "none", background: "transparent",
          fontSize: 14, color: "#2D3748", outline: "none", fontFamily: "inherit"
        }}
      />
    </div>
  );
}

export default function ExtractionReviewer({ extraction, onConfirm, onReject }) {
  const [edited, setEdited] = useState({ ...extraction });

  const updateField = (field, value) => {
    setEdited(prev => ({ ...prev, [field]: value }));
  };

  const updateLineItem = (index, field, value) => {
    const items = [...(edited.line_items || [])];
    items[index] = { ...items[index], [field]: value };
    setEdited(prev => ({ ...prev, line_items: items }));
  };

  const scores = extraction.confidence_scores || {};

  const fields = [
    { key: "vendor_name", label: "Vendor Name" },
    { key: "invoice_number", label: "Invoice Number" },
    { key: "invoice_date", label: "Invoice Date" },
    { key: "due_date", label: "Due Date" },
    { key: "subtotal", label: "Subtotal" },
    { key: "tax", label: "Tax" },
    { key: "total", label: "Total" },
  ];

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 680 }}>
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#1A202C", margin: "0 0 4px" }}>
          Review Extracted Data
        </h2>
        <p style={{ fontSize: 13, color: "#718096", margin: 0 }}>
          Edit any field before confirming. Red fields need your attention.
        </p>
      </div>

      {/* Main Fields */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 20 }}>
        {fields.map(({ key, label }) => (
          <EditableField
            key={key}
            label={label}
            value={edited[key]}
            onChange={(v) => updateField(key, v)}
            confidence={scores[key]}
          />
        ))}
      </div>

      {/* Line Items */}
      {edited.line_items?.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#4A5568", marginBottom: 10, textTransform: "uppercase", letterSpacing: 1 }}>
            Line Items
          </div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#EDF2F7" }}>
                {["Description", "Qty", "Unit Price", "Amount"].map(h => (
                  <th key={h} style={{ padding: "8px 10px", textAlign: "left", fontWeight: 600, color: "#4A5568" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {edited.line_items.map((item, i) => (
                <tr key={i} style={{ borderBottom: "1px solid #E2E8F0" }}>
                  {["description", "quantity", "unit_price", "amount"].map(field => (
                    <td key={field} style={{ padding: "6px 10px" }}>
                      <input
                        value={item[field] || ""}
                        onChange={(e) => updateLineItem(i, field, e.target.value)}
                        style={{ width: "100%", border: "none", background: "transparent", fontSize: 13, outline: "none" }}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", gap: 12, justifyContent: "flex-end" }}>
        <button
          onClick={onReject}
          style={{
            padding: "10px 24px", borderRadius: 8, border: "1px solid #E2E8F0",
            background: "#fff", color: "#4A5568", fontWeight: 600, cursor: "pointer", fontSize: 14
          }}
        >
          Reject
        </button>
        <button
          onClick={() => onConfirm(edited)}
          style={{
            padding: "10px 24px", borderRadius: 8, border: "none",
            background: "#38A169", color: "#fff", fontWeight: 600, cursor: "pointer", fontSize: 14
          }}
        >
          Confirm & Save
        </button>
      </div>
    </div>
  );
}
