import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

const InputNode = ({ data }) => {
  return (
    <div className="input-node">
      <label htmlFor={data.id}>{data.label}</label>
      {data.type === 'textarea' ? (
        <textarea
          id={data.id}
          value={data.value}
          onChange={(e) => data.onChange(data.id, e.target.value)}
          rows="3"
        />
      ) : (
        <input
          id={data.id}
          type="text"
          value={data.value}
          onChange={(e) => data.onChange(data.id, e.target.value)}
        />
      )}
      <Handle type="source" position={Position.Right} id="a" />
    </div>
  );
};

export default memo(InputNode);
