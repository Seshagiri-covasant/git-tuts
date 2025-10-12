import React, { useMemo, useCallback, useEffect } from 'react';
import ReactFlow, { Background, BackgroundVariant, Controls, MarkerType, useNodesState, useEdgesState } from 'reactflow';
import 'reactflow/dist/style.css';
import TableNode from './TableNode';

type Props = {
  tables: any[];
  relationships: any[];
  onNodeSelect: (tableId: string) => void;
  onEdgeSelect: (relationship: any) => void;
  onShowColumns: (tableId: string) => void;
};

const NODE_TYPES = { tableNode: TableNode } as const;

export default function ERDiagram({ tables, relationships, onNodeSelect, onEdgeSelect, onShowColumns }: Props) {
  const [hoveredEdge, setHoveredEdge] = React.useState<string | null>(null);
  const reactFlowInstance = React.useRef<any>(null);
  
  // Calculate initial positions only once when tables first load
  const initialPositions = useMemo(() => {
    const nodesPerRow = Math.ceil(Math.sqrt(tables.length));
    const horizontalSpacing = 450;
    const verticalSpacing = 250;
    
    const positions: Record<string, { x: number; y: number }> = {};
    tables.forEach((t: any, i: number) => {
      positions[t.id] = {
        x: (i % nodesPerRow) * horizontalSpacing,
        y: Math.floor(i / nodesPerRow) * verticalSpacing
      };
    });
    return positions;
  }, [tables.length]); // Only recalculate if number of tables changes
  
  // Initial nodes data - only recalculated when tables change
  const initialNodesData = useMemo(() => {
    return tables.map((t: any) => ({
      id: t.id,
      type: 'tableNode',
      position: initialPositions[t.id] || { x: 0, y: 0 },
      data: { 
        table: t, 
        onShowColumns
      },
      selectable: true,
      draggable: true,
    }));
  }, [tables, initialPositions, onShowColumns]);

  const tableById = useMemo(() => {
    const m: Record<string, any> = {};
    tables.forEach((t: any) => { m[t.id] = t; });
    return m;
  }, [tables]);

  const edgesData = useMemo(() => {
    return relationships.map((r: any, idx: number) => {
      const id = r.id || `${r.source_table_id}-${r.target_table_id}-${idx}`;

      return {
        id,
        source: r.source_table_id,
        target: r.target_table_id,
        // Always connect to table handles (not column handles) for cleaner table-to-table view
        sourceHandle: r.source_table_id,
        targetHandle: r.target_table_id,
        type: 'smoothstep' as const,
        markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
        data: r,
        // Edge styling for better visibility with hover effects
        style: { 
          stroke: hoveredEdge === r.id ? '#3b82f6' : '#6b7280', 
          strokeWidth: hoveredEdge === r.id ? 6 : 4,
          strokeDasharray: r.relationship_type === 'many_to_many' ? '5,5' : 'none',
          cursor: 'pointer',
          transition: 'all 0.2s ease-in-out'
        },
      };
    });
  }, [relationships, tableById]);

  const [nodes, , onNodesChange] = useNodesState(initialNodesData);
  const [edges, , onEdgesChange] = useEdgesState(edgesData);

  const handleNodeClick = useCallback((_: any, node: any) => onNodeSelect(node.id), [onNodeSelect]);
  const handleEdgeClick = useCallback((_: any, edge: any) => onEdgeSelect(edge.data), [onEdgeSelect]);
  
  const handleEdgeMouseEnter = useCallback((_: any, edge: any) => {
    setHoveredEdge(edge.id);
  }, []);
  
  const handleEdgeMouseLeave = useCallback((_: any, edge: any) => {
    setHoveredEdge(null);
  }, []);
  
  // Simple table click handler for normal selection
  const handleTableClick = useCallback((event: any, node: any) => {
    onNodeSelect(node.id);
  }, [onNodeSelect]);
  
  // Handle connection creation when user drags from one table to another
  const handleConnect = useCallback((params: any) => {
    if (params.source && params.target && params.source !== params.target) {
      // Create a new relationship
      const newRelationship = {
        id: `rel_${Date.now()}`, // This will be replaced with user_rel_ when created
        name: '',
        description: '',
        source_table_id: params.source,
        target_table_id: params.target,
        source_columns: [],
        target_columns: [],
        relationship_type: 'one_to_many',
        cardinality_ratio: '1:N',
        confidence_score: 1.0,
        metadata: {},
        created_at: new Date().toISOString()
      };
      
      // Trigger the relationship creation callback
      onEdgeSelect(newRelationship);
    }
  }, [onEdgeSelect]);
  
  const onInit = useCallback((instance: any) => {
    reactFlowInstance.current = instance;
    // Set initial view only once when component mounts
    instance.fitView({ padding: 0.1 });
  }, []);

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleTableClick}
        onEdgeClick={handleEdgeClick}
        onEdgeMouseEnter={handleEdgeMouseEnter}
        onEdgeMouseLeave={handleEdgeMouseLeave}
        onConnect={handleConnect}
        onInit={onInit}
        fitView={false}
        proOptions={{ hideAttribution: true }}

      >
        <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
        <Controls />
      </ReactFlow>
    </div>
  );
}


