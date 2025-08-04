import React from 'react';
import ReactFlow, { Controls, Background } from 'reactflow';
import 'reactflow/dist/style.css';
const FlowCanvas = ({children, nodes, edges, onNodesChange, onEdgesChange, onNodeClick ,nodeTypes}) => {
  return (
    <div className="flow-wrapper">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        nodeTypes={nodeTypes} 
        fitView
      >
        <Background />
        <Controls />
      </ReactFlow>
       {children}
    </div>
  );
};
export default FlowCanvas;
