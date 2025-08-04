import React, { useState } from 'react';
const AgentForm = ({ agent, onUpdate, onAddSubAgent }) => {
  const [showAddToolForm, setShowAddToolForm] = useState(false);
  const [newTool, setNewTool] = useState({ name: '', description: '' });
  const handleFieldChange = (field, value) => {
    onUpdate({ ...agent, [field]: value });
  };

  const handleAddTool = () => {
    if (newTool.name && newTool.description) {
      const updatedTools = [...(agent.tools || []), { ...newTool, id: Date.now() }];
      onUpdate({ ...agent, tools: updatedTools });
      setNewTool({ name: '', description: '' });
      setShowAddToolForm(false);
    }
  };
  
  const handleRemoveTool = (toolId) => {
    const updatedTools = agent.tools.filter(t => t.id !== toolId);
    onUpdate({ ...agent, tools: updatedTools });
  };

  const handleRemoveSubAgent = (subAgentId) => {
    const updatedSubAgents = agent.subAgents.filter(sa => sa.id !== subAgentId);
    onUpdate({ ...agent, subAgents: updatedSubAgents });
  };

  return (
    <>
      <div className="config-card">
        <div className="form-group">
          <label>Agent Name</label>
          <input type="text" value={agent.name || ''} onChange={(e) => handleFieldChange('name', e.target.value)} />
        </div>
        <div className="form-group">
          <label>Agent Description</label>
          <textarea value={agent.description || ''} onChange={(e) => handleFieldChange('description', e.target.value)} rows={3} />
        </div>
      </div>

      <div className="config-card">
        <div className="list-header">
          <h2 className="card-title">Tools</h2>
          <button className="add-btn" onClick={() => setShowAddToolForm(!showAddToolForm)}>+</button>
        </div>
        <ul className="item-list">
          {(agent.tools || []).map(tool => (
            <li key={tool.id}>
              <span>{tool.name}</span>
              <button className="remove-btn" onClick={() => handleRemoveTool(tool.id)}>×</button>
            </li>
          ))}
        </ul>
        {showAddToolForm && (
          <div className="add-form">
            <input type="text" placeholder="New Tool Name" value={newTool.name} onChange={(e) => setNewTool({ ...newTool, name: e.target.value })} />
            <textarea placeholder="New Tool Description" rows={2} value={newTool.description} onChange={(e) => setNewTool({ ...newTool, description: e.target.value })} />
            <button onClick={handleAddTool}>Add Tool</button>
          </div>
        )}
      </div>

      <div className="config-card">
        <div className="list-header">
          <h2 className="card-title">Sub-Agents</h2>
          <button className="add-btn" onClick={() => onAddSubAgent(agent.id)}>+</button>
        </div>
        <ul className="item-list">
          {(agent.subAgents || []).map(subAgent => (
            <li key={subAgent.id}>
              <span>{subAgent.name}</span>
              <button className="remove-btn" onClick={() => handleRemoveSubAgent(subAgent.id)}>×</button>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
};

export default AgentForm;
