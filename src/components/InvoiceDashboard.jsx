import { useState, useEffect } from "react";

const STATUS_META = {
  pending:    { label: "Pending",    bg: "#EDF2F7", color: "#4A5568" },
  extracted:  { label: "Extracted",  bg: "#EBF8FF", color: "#2B6CB0" },
  reviewed:   { label: "Reviewed",   bg: "#FFFBEB", color: "#744210" },
  exported:   { label: "Exported",   bg: "#F0FFF4", color: "#276749" },
};

function StatusBadge({ status }) {
  const m = STATUS_META[status] || STATUS_META.pending;
  return (
    <span style={{
      fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 20,
      background: m.bg, color: m.color, letterSpacing: 0.5
    }}>
      {m.label}
    </span>
  );
}

function SummaryCard({ label, value, color = "#2D3748" }) {
  return (
    <div style={{
      background: "#fff", border: "1px solid #E2E8F0", borderRadius: 12,
      padding: "18px 22px", flex: 1
    }}>
      <div style={{ fontSize: 24, fontWeight: 800, color }}>{value}</div>
      <div style={{ fontSize: 12, color: "#718096", marginTop: 4, textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
    </div>
  );
}

export default function InvoiceDashboard() {
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(new Set());
  const [filterStatus, setFilterStatus] = useState("all");
  const [sortField, setSortField] = useState("invoice_date");
  const [sortDir, setSortDir] = useState("desc");

  useEffect(() => {
    fetch("/api/invoices")
      .then(r => r.json())
      .then(data => { setInvoices(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === filtered.length) setSelected(new Set());
    else setSelected(new Set(filtered.map(i => i.id)));
  };

  const handleSort = (field) => {
    if (sortField === field) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortField(field); setSortDir("asc"); }
  };

  const handleDelete = async (id) => {
    await fetch(`/api/invoices/${id}`, { method: "DELETE" });
    setInvoices(prev => prev.filter(i => i.id !== id));
  };

  const handleExportCSV = async (ids) => {
    const res = await fetch("/api/export/csv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ invoice_ids: ids }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "invoices_export.csv"; a.click();
    URL.revokeObjectURL(url);
  };

  const filtered = invoices
    .filter(i => filterStatus === "all" || i.status === filterStatus)
    .sort((a, b) => {
      const va = a[sortField] ?? "";
      const vb = b[sortField] ?? "";
      return sortDir === "asc" ? (va > vb ? 1 : -1) : (va < vb ? 1 : -1);
    });

  const totalValue = invoices.reduce((s, i) => s + (parseFloat(i.total) || 0), 0);
  const pendingCount = invoices.filter(i => i.status === "pending" || i.status === "extracted").length;

  const SortIcon = ({ field }) => sortField === field ? (sortDir === "asc" ? " ↑" : " ↓") : " ↕";

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", padding: 28, background: "#F7FAFC", minHeight: "100vh" }}>
      <h1 style={{ fontSize: 22, fontWeight: 800, color: "#1A202C", marginBottom: 20 }}>🧾 InvoiceIQ</h1>

      {/* Summary Cards */}
      <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
        <SummaryCard label="Total Invoices" value={invoices.length} />
        <SummaryCard label="Total Value" value={`$${totalValue.toLocaleString("en-US", { minimumFractionDigits: 2 })}`} color="#3182CE" />
        <SummaryCard label="Pending Review" value={pendingCount} color="#E53E3E" />
      </div>

      {/* Toolbar */}
      <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1px solid #E2E8F0", fontSize: 13, background: "#fff" }}
        >
          <option value="all">All Statuses</option>
          {Object.keys(STATUS_META).map(s => <option key={s} value={s}>{STATUS_META[s].label}</option>)}
        </select>

        {selected.size > 0 && (
          <button
            onClick={() => handleExportCSV([...selected])}
            style={{
              padding: "8px 18px", borderRadius: 8, border: "none",
              background: "#3182CE", color: "#fff", fontWeight: 600, cursor: "pointer", fontSize: 13
            }}
          >
            Export Selected ({selected.size})
          </button>
        )}
      </div>

      {/* Table */}
      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #E2E8F0", overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: 40, textAlign: "center", color: "#A0AEC0" }}>Loading invoices...</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 40, textAlign: "center", color: "#A0AEC0" }}>No invoices found</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#F7FAFC", borderBottom: "1px solid #E2E8F0" }}>
                <th style={{ padding: "12px 16px", width: 40 }}>
                  <input type="checkbox" checked={selected.size === filtered.length && filtered.length > 0} onChange={toggleAll} />
                </th>
                {[
                  { label: "Invoice #", field: "invoice_number" },
                  { label: "Vendor", field: "vendor_name" },
                  { label: "Date", field: "invoice_date" },
                  { label: "Total", field: "total" },
                  { label: "Status", field: "status" },
                ].map(({ label, field }) => (
                  <th
                    key={field}
                    onClick={() => handleSort(field)}
                    style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "#4A5568", cursor: "pointer", userSelect: "none" }}
                  >
                    {label}<SortIcon field={field} />
                  </th>
                ))}
                <th style={{ padding: "12px 16px", textAlign: "left", fontWeight: 600, color: "#4A5568" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((invoice, i) => (
                <tr key={invoice.id} style={{ borderBottom: "1px solid #F7FAFC", background: i % 2 === 0 ? "#fff" : "#FAFAFA" }}>
                  <td style={{ padding: "12px 16px" }}>
                    <input type="checkbox" checked={selected.has(invoice.id)} onChange={() => toggleSelect(invoice.id)} />
                  </td>
                  <td style={{ padding: "12px 16px", fontWeight: 600, color: "#2D3748" }}>{invoice.invoice_number || "—"}</td>
                  <td style={{ padding: "12px 16px", color: "#4A5568" }}>{invoice.vendor_name || "—"}</td>
                  <td style={{ padding: "12px 16px", color: "#718096" }}>{invoice.invoice_date || "—"}</td>
                  <td style={{ padding: "12px 16px", fontWeight: 600 }}>${parseFloat(invoice.total || 0).toLocaleString()}</td>
                  <td style={{ padding: "12px 16px" }}><StatusBadge status={invoice.status} /></td>
                  <td style={{ padding: "12px 16px" }}>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button onClick={() => handleExportCSV([invoice.id])}
                        style={{ padding: "4px 12px", borderRadius: 6, border: "1px solid #E2E8F0", background: "#fff", cursor: "pointer", fontSize: 12 }}>
                        CSV
                      </button>
                      <button onClick={() => handleDelete(invoice.id)}
                        style={{ padding: "4px 12px", borderRadius: 6, border: "1px solid #FEB2B2", background: "#FFF5F5", color: "#C53030", cursor: "pointer", fontSize: 12 }}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
