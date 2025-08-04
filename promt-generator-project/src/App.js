import React, { useState, useEffect, useMemo } from 'react';
import { useNodesState, useEdgesState } from 'reactflow';
import SidePanel from './components/SidePanel';
import FlowCanvas from './components/FlowCanvas';
import AddSubAgentForm from './components/AddSubAgentForm';
import RootAgentCard from './components/RootAgentCard'; // Import the Root Agent card
import JsonViewerModal from './components/JsonViewerModal';
import './App.css';

const API_URL = 'https://0d9eb916fc9c.ngrok-free.app/generate-prompt';

function App() {
  // === STATE MANAGEMENT ===
  const [rootAgent, setRootAgent] = useState({ name: 'writer_agent', description: 'Generates stories and blogs', tools: [], subAgents: [] });
  const [generatedPrompt, setGeneratedPrompt] = useState('');
  const [enhancementContext, setEnhancementContext] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [error, setError] = useState('');
  const [isPanelOpen, setIsPanelOpen] = useState(true);
  const [jsonToShow, setJsonToShow] = useState(null);

  // Unified state for managing all pop-ups
  const [activePopup, setActivePopup] = useState({ type: null, data: null });

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  // === SYNCHRONIZATION ===
  useEffect(() => {
    const newNodes = [
      { id: 'prompt_gen', type: 'default', data: { label: 'Prompt Generator' }, position: { x: 250, y: 0 }, style: { backgroundColor: '#2E7D32', color: '#FFFFFF' } },
      { id: 'root_agent', type: 'default', data: { label: rootAgent.name }, position: { x: 250, y: 150 }, style: { backgroundColor: '#1565C0', color: '#FFFFFF' } },
    ];
    const newEdges = [{ id: 'e-prompt-root', source: 'prompt_gen', target: 'root_agent', animated: true }];
    rootAgent.subAgents.forEach((agent, index) => {
      const xPos = 50 + (index * 250);
      newNodes.push({ id: agent.id, type: 'default', data: { label: agent.name, ...agent }, position: { x: xPos, y: 300 }, style: { backgroundColor: '#37474F', color: '#ECEFF1' } });
      newEdges.push({ id: `e-root-${agent.id}`, source: 'root_agent', target: agent.id, animated: true });
    });
    setNodes(newNodes);
    setEdges(newEdges);
  }, [rootAgent, setNodes, setEdges]);

  // === EVENT HANDLERS ===
  const handleAgentChange = (field, value) => setRootAgent(prev => ({ ...prev, [field]: value }));
  const handleAddTool = (newTool) => setRootAgent(prev => ({ ...prev, tools: [...prev.tools, { ...newTool, id: Date.now() }] }));
  const handleRemoveTool = (toolIdToRemove) => setRootAgent(prev => ({ ...prev, tools: prev.tools.filter(tool => tool.id !== toolIdToRemove) }));
  
  const handleSaveSubAgent = (agentData) => {
    if (agentData.id) { // Update existing
      setRootAgent(prev => ({ ...prev, subAgents: prev.subAgents.map(agent => agent.id === agentData.id ? { ...agent, ...agentData } : agent) }));
    } else { // Create new
      const newId = `sub_agent_${Date.now()}`;
      setRootAgent(prev => ({ ...prev, subAgents: [...prev.subAgents, { ...agentData, id: newId }] }));
    }
  };
  const handleRemoveSubAgent = (subAgentIdToRemove) => setRootAgent(prev => ({ ...prev, subAgents: prev.subAgents.filter(agent => agent.id !== subAgentIdToRemove) }));

  const openSubAgentModal = (agentToEdit = null) => {
    setActivePopup({ type: 'subAgentForm', data: agentToEdit });
  };
  
  const handleNodeClick = (event, node) => {
    setActivePopup({ type: null, data: null }); // Close any open pop-up first
    if (node.id === 'root_agent') {
      setActivePopup({ type: 'rootAgentCard', data: rootAgent });
    } else if (node.id.startsWith('sub_agent')) {
      const agentToEdit = rootAgent.subAgents.find(agent => agent.id === node.id);
      if (agentToEdit) {
        openSubAgentModal(agentToEdit);
      }
    }
  };

   const handleExport = () => {
    const exportData = { agentConfiguration: rootAgent, generatedPrompt: generatedPrompt || "No prompt generated yet." };
    const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(JSON.stringify(exportData, null, 2))}`;
    const link = document.createElement("a");
    link.href = jsonString;
    link.download = "agent-execution-output.json";
    link.click();
  };
  const handleViewJson = () => {
   const flowData = {
    nodes: nodes, // Grab the current 'nodes' state array
    edges: edges, // Grab the current 'edges' state array
  };

  setJsonToShow(flowData);
  };
  
  // API Call Handler
  const callApi = async (isEnhance = false) => {
    const loader = isEnhance ? setIsEnhancing : setIsLoading;
    loader(true); setError('');
    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' ,'ngrok-skip-browser-warning': 'true'},
        body: JSON.stringify({
          agent_name: rootAgent.name,
          agent_description: rootAgent.description,
          tools: rootAgent.tools,
          sub_agents: rootAgent.subAgents,
          previous_prompt: isEnhance ? generatedPrompt : '',
          context: isEnhance ? enhancementContext : '',
        }),
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `API Error: ${response.status}`);
      }
      const data = await response.json();
      setGeneratedPrompt(data.prompt);
      if (isEnhance) setEnhancementContext('');
    } catch (err) {
      setError(err.message);
      console.error(err);
    } finally {
      loader(false);
    }
  };
const CONFIG = {
  API_URL: process.env.REACT_APP_API_URL || 'https://0d9eb916fc9c.ngrok-free.app/generate-prompt',

 
};

  return (
    <div className={`app-container ${isPanelOpen ? 'panel-open' : 'panel-closed'} dark-theme`}>
      <button className="panel-toggle" onClick={() => setIsPanelOpen(!isPanelOpen)}>{isPanelOpen ? '‹' : '›'}</button>
      
      <SidePanel
        rootAgent={rootAgent}
        onAgentChange={handleAgentChange}
        onAddTool={handleAddTool}
        onRemoveTool={handleRemoveTool}
        onOpenSubAgentModal={openSubAgentModal}
        onRemoveSubAgent={handleRemoveSubAgent}
        generatedPrompt={generatedPrompt}
        onPromptChange={setGeneratedPrompt}
        enhancementContext={enhancementContext}
        onEnhancementContextChange={setEnhancementContext}
        onGenerate={() => callApi(false)}
        onEnhance={() => callApi(true)}
        isLoading={isLoading}
        isEnhancing={isEnhancing}
        error={error}
      />

      <div className="main-content-area">
        <FlowCanvas
          nodes={nodes} edges={edges} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
        >
          <div className="canvas-buttons">
            <button className="view-json-button" onClick={handleViewJson}>View JSON</button>
            <button className="export-button" onClick={handleExport}>Export JSON</button>
          </div>
        </FlowCanvas>
        
        {/* --- RESTORED & UNIFIED POP-UP LOGIC --- */}
        {activePopup.type === 'rootAgentCard' && (
          <RootAgentCard
            agentData={activePopup.data}
            onClose={() => setActivePopup({ type: null, data: null })}
            onOpenInstructions={() => setIsPanelOpen(true)}
          />
        )}
        {activePopup.type === 'subAgentForm' && (
          <AddSubAgentForm
            existingAgent={activePopup.data}
            onClose={() => setActivePopup({ type: null, data: null })}
            onSave={handleSaveSubAgent}
          />
        )}
        <JsonViewerModal jsonData={jsonToShow} onClose={() => setJsonToShow(null)} />
      </div>
    </div>
  );
}

export default App;
