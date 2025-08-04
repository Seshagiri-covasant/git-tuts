import React, { useState, useEffect } from 'react';

const SubAgentEditForm = ({ node, onClose, onSave }) => {
  // Local state to manage the input field while typing
  const [name, setName] = useState('');

  // When the component receives a new node to edit, update the local state
  useEffect(() => {
    if (node) {
      setName(node.data.label);
    }
  }, [node]);

  if (!node) return null;

  const handleSave = () => {
    onSave(node.id, name);
    onClose(); // Close the form after saving
  };

  return (
    <div className="popup-card sub-agent-edit-form">
      <button className="close-btn" onClick={onClose}>×</button>
      <h3>Edit Sub-Agent</h3>
      <div className="form-group">
        <label htmlFor="subAgentName">Agent Name</label>
        <input
          id="subAgentName"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>
      <button onClick={handleSave}>Save Changes</button>
    </div>
  );
};

export default SubAgentEditForm;
