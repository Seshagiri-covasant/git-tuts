// src/components/IconNode.js
import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

// This component will receive `data` containing a `label` and an `iconUrl`.
const IconNode = ({ data }) => {
  return (
    // The main container for our node.
    <div className="icon-node">
      {/* Connection point at the top */}
      <Handle type="target" position={Position.Top} />

      {/* A flex container to hold the icon and text */}
      <div className="node-content">
        <img src={data.iconUrl} className="node-icon" alt="" />
        <span className="node-label">{data.label}</span>
      </div>

      {/* Connection point at the bottom */}
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

export default memo(IconNode);
