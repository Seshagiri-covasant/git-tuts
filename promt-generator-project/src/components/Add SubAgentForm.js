import React, { useState, useEffect } from 'react';

const AddSubAgentForm = ({ onSave, onClose, existingAgent }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tools, setTools] = useState([]);
  const [newToolName, setNewToolName] = useState('');

  useEffect(() => {
    if (existingAgent) {
      setName(existingAgent.name || '');
      setDescription(existingAgent.description || '');
      setTools(existingAgent.tools || []);
    }
  }, [existingAgent]);

  // --- HANDLERS ---
  const handleAddTool = () => {
    if (!newToolName.trim()) return;
    setTools([...tools, { id: Date.now(), name: newToolName, description: '' }]);
    setNewToolName('');
  };

  const handleRemoveTool = (toolId) => {
    setTools(tools.filter(tool => tool.id !== toolId));
  };

  const handleSave = () => {
    if (!name.trim() || !description.trim()) {
      alert('Please provide a name and description for the sub-agent.');
      return;
    }
    // Package up the data. If we're editing, include the original ID.
    const agentData = { id: existingAgent?.id, name, description, tools };
    onSave(agentData);
    onClose();
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        {/* The title changes based on whether we are creating or editing */}
        <h2>{existingAgent ? 'Edit Sub-Agent' : 'Create New Sub-Agent'}</h2>
        
        <div className="form-group">
          <label>Sub-Agent Name</label>
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g., content_reviewer" />
        </div>
        <div className="form-group">
          <label>Sub-Agent Description</label>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="What is this agent's role?" />
        </div>

        <div className="config-card nested-card">
          <div className="list-header">
            <h2 className="card-title">Tools for this Sub-Agent</h2>
          </div>
          <ul className="item-list">
            {tools.map(tool => (
              <li key={tool.id}>
                <span>{tool.name}</span>
                <button className="remove-btn" onClick={() => handleRemoveTool(tool.id)}>×</button>
              </li>
            ))}
          </ul>
          <div className="add-form inline">
            <input type="text" placeholder="New Tool Name" value={newToolName} onChange={(e) => setNewToolName(e.target.value)} />
            <button className="add-btn" onClick={handleAddTool}>+</button>
          </div>
        </div>

        <div className="modal-actions">
          <button className="secondary-btn" onClick={onClose}>Cancel</button>
          <button onClick={handleSave}>Save</button>
        </div>
      </div>
    </div>
  );
};

export default AddSubAgentForm;
