import React, { useState } from 'react';
const SubAgentToolForm = ({ node, onClose, onAddTool }) => {
  const [toolName, setToolName] = useState('');
  const [toolDescription, setToolDescription] = useState('');
  if (!node) return null;
  const handleSubmit = (e) => {
    e.preventDefault(); 
    if (!toolName.trim() || !toolDescription.trim()) {
      alert('Please fill out both tool name and description.');
      return;
    }
    onAddTool(node.id, { name: toolName, description: toolDescription });
    setToolName('');
    setToolDescription('');
  };
  const formStyle = {
    position: 'absolute',
    top: `${node.position.y}px`,
    left: `${node.position.x - 340}px`, 
    zIndex: 10,
  };

  return (
    <div className="sub-agent-tool-form" style={formStyle}>
      <button className="close-btn" onClick={onClose}>×</button>
      <h3>Tools for: {node.data.label}</h3>

      {/* List of existing tools */}
      <div className="tool-list">
        <h4>Existing Tools:</h4>
        {node.data.tools.length > 0 ? (
          <ul>
            {node.data.tools.map((tool, index) => (
              <li key={index}><strong>{tool.name}:</strong> {tool.description}</li>
            ))}
          </ul>
        ) : (
          <p className="no-tools-message">No tools added yet.</p>
        )}
      </div>

      {/* Form to add a new tool */}
      <form onSubmit={handleSubmit} className="add-tool-form">
        <h4>Add New Tool:</h4>
        <div className="form-group">
          <label htmlFor="toolName">Tool Name</label>
          <input id="toolName" type="text" value={toolName} onChange={(e) => setToolName(e.target.value)} placeholder="e.g., code_executor" />
        </div>
        <div className="form-group">
          <label htmlFor="toolDesc">Tool Description</label>
          <textarea id="toolDesc" value={toolDescription} onChange={(e) => setToolDescription(e.target.value)} rows="2" placeholder="e.g., Executes Python code" />
        </div>
        <button type="submit">Add Tool</button>
      </form>
    </div>
  );
};

export default SubAgentToolForm;
