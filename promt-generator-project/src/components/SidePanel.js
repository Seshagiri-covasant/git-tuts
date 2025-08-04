import React, { useState } from 'react';
const SidePanel = (props) => {
  const {
    rootAgent, onAgentChange,
    onAddTool, onUpdateTool, onRemoveTool,
    onOpenSubAgentModal, 
    onRemoveSubAgent,
    generatedPrompt, onPromptChange,
    enhancementContext, onEnhancementContextChange,
    onGenerate, onEnhance,
    isLoading, isEnhancing, error,
  } = props;
  const [showAddToolForm, setShowAddToolForm] = useState(false);
  const [newTool, setNewTool] = useState({ name: '', description: '' });

  const handleAddToolClick = () => {
    if (newTool.name && newTool.description) {
      onAddTool(newTool);
      setNewTool({ name: '', description: '' });
      setShowAddToolForm(false);
    }
  };

  return (
    <div className="side-panel">
      <header className="panel-header"><h1>Agent Details</h1></header>
      <div className="panel-content">
        <div className="config-card">
          <div className="form-group">
            <label>Agent Name</label>
            <input type="text" value={rootAgent.name} onChange={(e) => onAgentChange('name', e.target.value)} />
          </div>
          <div className="form-group">
            <label>Agent Description</label>
            <textarea value={rootAgent.description} onChange={(e) => onAgentChange('description', e.target.value)} rows={3} />
          </div>
        </div>

        <div className="config-card">
          <div className="list-header">
            <h2 className="card-title">Tools</h2>
            <button className="add-btn" onClick={() => setShowAddToolForm(!showAddToolForm)}>+</button>
          </div>
          <ul className="item-list">
            {rootAgent.tools.map(tool => (
              <li key={tool.id}>
                <span>{tool.name}</span>
                <button className="remove-btn" onClick={() => onRemoveTool(tool.id)}>×</button>
              </li>
            ))}
          </ul>
          {showAddToolForm && (
            <div className="add-form">
              <input type="text" placeholder="New Tool Name" value={newTool.name} onChange={(e) => setNewTool({...newTool, name: e.target.value})} />
              <textarea placeholder="New Tool Description" rows={2} value={newTool.description} onChange={(e) => setNewTool({...newTool, description: e.target.value})} />
              <button onClick={handleAddToolClick}>Add Tool</button>
            </div>
          )}
        </div>

        <div className="config-card">
          <div className="list-header">
            <h2 className="card-title">Sub-Agents</h2>
            <button className="add-btn" onClick={() => onOpenSubAgentModal(null)}>+</button>
          </div>
          <ul className="item-list">
            {rootAgent.subAgents.map(agent => (
              <li key={agent.id} className="clickable-item" onClick={() => onOpenSubAgentModal(agent)}>
                <span>{agent.name}</span>
                <button className="remove-btn" onClick={(e) => { e.stopPropagation(); onRemoveSubAgent(agent.id); }}>×</button>
              </li>
            ))}
          </ul>
        </div>

        <div className="config-card">
          <h2 className="card-title">Generated Instruction Prompt</h2>
          <textarea className="prompt-box editable" value={generatedPrompt} onChange={(e) => onPromptChange(e.target.value)} rows="8" placeholder="Generate a prompt to see the result..." />
        </div>
        
        <div className="action-bar">
          {error && <p className="error-message">{error}</p>}
          {!generatedPrompt ? (
            <button onClick={onGenerate} disabled={isLoading}>{isLoading ? 'Generating...' : 'Generate Prompt'}</button>
          ) : (
            <div className="enhancer-section">
              <div className="form-group">
                <label>Describe your improvements:</label>
                <textarea value={enhancementContext} onChange={(e) => onEnhancementContextChange(e.target.value)} rows="2" />
              </div>
              <button onClick={onEnhance} disabled={isEnhancing}>{isEnhancing ? 'Enhancing...' : 'Enhance Prompt'}</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SidePanel;
