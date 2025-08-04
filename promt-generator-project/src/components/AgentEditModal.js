import React from 'react';
import AgentForm from './AgentForm'; 

const AgentEditModal = ({ agent, onUpdate, onAddSubAgent, onClose }) => {
  if (!agent) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content side-panel"> 
        <header className="panel-header">
          <h1>Edit Sub-Agent</h1>
          <button className="close-btn modal-close" onClick={onClose}>×</button>
        </header>
        <div className="panel-content">
          <AgentForm
            agent={agent}
            onUpdate={onUpdate}
            onAddSubAgent={onAddSubAgent}
          />
        </div>
      </div>
    </div>
  );
};

export default AgentEditModal;
