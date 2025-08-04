import React from 'react';

const AgentCard = ({ node, onClose, onOpenPanel }) => {
  if (!node) return null;

  // Calculate position for the card to appear near the node
  const cardStyle = {
    position: 'absolute',
    top: `${node.position.y}px`,
    left: `${node.position.x + node.width + 20}px`, 
    zIndex: 10,
  };

  return (
    <div className="agent-card" style={cardStyle}>
      <button className="close-btn" onClick={onClose}>×</button>
      <h3>{node.data.label}</h3>
      <div className="card-content">
        <p><strong>Name:</strong> {node.data.agentData.name}</p>
        <p><strong>Description:</strong> {node.data.agentData.description}</p>
        <p><strong>Tools:</strong> {node.data.agentData.tools.join(', ') || 'None'}</p>
        <p><strong>Sub-Agents:</strong> {node.data.agentData.subAgents.join(', ') || 'None'}</p>
      </div>
      <button className="instruction-btn" onClick={onOpenPanel}>
        View/Edit Instructions
      </button>
    </div>
  );
};

export default AgentCard;
