import React from 'react';

const JsonViewerModal = ({ jsonData, onClose }) => {
  if (!jsonData) return null;

  const formattedJson = JSON.stringify(jsonData, null, 2);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content json-viewer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Execution Output JSON</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          <pre>
            <code>
              {formattedJson}
            </code>
          </pre>
        </div>
      </div>
    </div>
  );
};

export default JsonViewerModal;
