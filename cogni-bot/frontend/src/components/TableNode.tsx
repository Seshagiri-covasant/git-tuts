import React from 'react';
import { Handle, Position } from 'reactflow';

export default function TableNode({ data, selected }: any) {
  const t = data.table;
  const onShowColumns = data.onShowColumns as (tableId: string) => void;
  const columnArray = Object.values(t.columns || {}) as any[];
  const visible = columnArray.slice(0, 4);
  const hidden = columnArray.length - visible.length;

  return (
    <div 
      data-node 
      className="rounded-lg border bg-white shadow-sm transition-all duration-200 hover:shadow-md" 
      style={{ width: 380 }}
    >
      <div className="px-3 py-2 border-b text-sm font-medium flex items-center justify-between bg-blue-50 border-gray-200">
        <span className="font-semibold text-blue-900">
          {t.display_name}
        </span>
        <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-600">
          {columnArray.length} cols
        </span>
      </div>
      <div className="p-3 space-y-1">
        {visible.map((c: any) => (
          <div key={c.id} className="flex items-center justify-between text-xs">
            <div className="flex items-center">
              {c.is_primary_key && <span className="w-2 h-2 bg-yellow-500 rounded-full mr-2" />}
              {c.is_foreign_key && <span className="w-2 h-2 bg-blue-500 rounded-full mr-2" />}
              <span>{c.name}</span>
            </div>
            <span className="text-gray-500">{c.data_type}</span>
          </div>
        ))}
        {hidden > 0 && (
          <button
            className="text-xs text-blue-600 hover:underline"
            onClick={(e) => { e.stopPropagation(); onShowColumns(t.id); }}
          >
            +{hidden} columns
          </button>
        )}
      </div>

      {/* Fallback handles on table itself */}
      <Handle id={`${t.id}`} type="source" position={Position.Right} />
      <Handle id={`${t.id}`} type="target" position={Position.Left} />
    </div>
  );
}


