import React from 'react';

const RootAgentCard = ({ agentData, onClose, onOpenInstructions }) => {
  if (!agentData) return null;

  // This positions the card in the center of the screen
  const cardStyle = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    zIndex: 20,
  };

  const handleInstructionsClick = () => {
    onOpenInstructions(); // Call the function to open the side panel
    onClose(); // Close this pop-up card
  };

  return (
    <div className="popup-card root-agent-card" style={cardStyle}>
      <button className="close-btn" onClick={onClose}>×</button>
      <h3>{agentData.name}</h3>
      <div className="card-content">
        <p><strong>Description:</strong> {agentData.description}</p>
        <p><strong>Tools:</strong> {agentData.tools.length > 0 ? agentData.tools.map(t => t.name).join(', ') : 'None'}</p>
        <p><strong>Sub-Agents:</strong> {agentData.subAgents.length > 0 ? agentData.subAgents.map(a => a.name).join(', ') : 'None'}</p>
      </div>
      <button className="instruction-btn" onClick={handleInstructionsClick}>
        View/Edit Instructions
      </button>
    </div>
  );
};

export default RootAgentCard;
