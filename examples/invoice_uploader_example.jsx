// Example React component: InvoiceUploader
// This example shows the structure and props expected by the InvoiceUploader component

import React, { useState } from 'react';

export function InvoiceUploaderExample() {
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);

  const handleUpload = (file) => {
    // Validate file
    if (file.size > 10 * 1024 * 1024) {
      setError('File size exceeds 10MB');
      return;
    }

    const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/tiff'];
    if (!validTypes.includes(file.type)) {
      setError('File type not supported. Use PDF or image files.');
      return;
    }

    setFile(file);
    setError('');
    // Handle upload with progress tracking
  };

  return (
    <div>
      <h2>Invoice Uploader</h2>
      {/* Drag-and-drop zone implementation */}
      {/* File validation and progress bar */}
    </div>
  );
}
