import React, { useState, useEffect, useCallback, useMemo } from 'react';
import ERDiagram from './ERDiagram';
import { Search, RefreshCw, Plus, Check, Square, X, ChevronRight, Maximize2, Minimize2, Edit3, Trash2, Edit, Trash, Calculator, Download, Upload } from 'lucide-react';
import { getSemanticSchema, updateSemanticSchema, exportSemanticSchema, importSemanticSchema } from '../services/api';
import { useToaster } from '../Toaster/Toaster';
import Loader from './Loader';

// Types
interface SynonymWithSamples {
  synonym: string;
  sample_values: string[];
}

interface SemanticColumn {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  business_context?: string;
  exclude_column?: boolean;
  data_type: string;
  is_primary_key: boolean;
  is_foreign_key: boolean;
  synonyms: SynonymWithSamples[];
  metadata: Record<string, any>;
  // New column metadata fields for intelligent selection
  business_description?: string;
  business_terms?: string[];
  priority?: 'high' | 'medium' | 'low';
  is_preferred?: boolean;
  use_cases?: string[];
  relevance_keywords?: string[];
  created_at: string;
  updated_at: string;
}

interface SemanticTable {
  id: string;
  name: string;
  display_name: string;
  description?: string;
  schema_name?: string;
  database_id: string;
  columns: Record<string, SemanticColumn>; // Changed from array to dictionary
  synonyms: SynonymWithSamples[];
  business_context?: string;
  row_count_estimate?: number;
  metrics?: Record<string, any>; // Changed from string[] to dictionary
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

interface UserPreferences {
  risk_score_column?: string;
  amount_column?: string;
  date_column?: string;
  default_risk_threshold?: number;
}

interface SemanticRelationship {
  id: string;
  name: string;
  description?: string;
  // Clean-structure fields (backend): optional on UI side
  from?: string;
  to?: string;
  source_table_id: string;
  target_table_id: string;
  source_columns: string[];
  target_columns: string[];
  relationship_type: string;
  cardinality_ratio?: string;
  join_sql?: string;
  confidence_score: number;
  metadata: Record<string, any>;
  created_at: string;
}

interface DatabaseSchema {
  id: string;
  name: string;
  database_id: string;
  display_name: string;
  connection_config: Record<string, any>;
  tables: Record<string, SemanticTable>; // Changed from array to dictionary
  relationships: SemanticRelationship[];
  metrics: any[];
  synonyms: Record<string, string[]>;
  metadata: Record<string, any>;
  last_sync?: string;
  created_at: string;
  updated_at: string;
}

interface SemanticSchemaEditorProps {
  chatbotId: string;
  onSave?: (schema?: any) => void;
  onConfirm?: () => void;
  
  // EDIT SCHEMA FEATURE: New props to support editing existing schemas
  initialSchema?: any;    // Pre-loaded schema data for edit mode
  isEditMode?: boolean;   // Flag to enable edit mode behavior
}

// Individual field components using UNCONTROLLED inputs (commit on blur)
const TextInput = React.memo<{
  defaultValue: string;
  onCommit: (value: string) => void;
  placeholder?: string;
  label?: string;
  disabled?: boolean;
  fieldKey?: string;
}>(({ defaultValue, onCommit, placeholder, label, disabled, fieldKey }) => {
  const inputRef = React.useRef<HTMLInputElement | null>(null);
  const onCommitRef = React.useRef(onCommit);
  
  // Keep the ref updated
  React.useEffect(() => {
    onCommitRef.current = onCommit;
  }, [onCommit]);

  const handleBlur = useCallback(() => {
    if (inputRef.current) {
      // Preserve scroll position before committing
      const scrollContainer = document.querySelector('[data-inspector-scroll]') as HTMLElement;
      const scrollTop = scrollContainer?.scrollTop || 0;
      
      onCommitRef.current(inputRef.current.value);
      
      // Restore scroll position after commit
      if (scrollContainer) {
        requestAnimationFrame(() => {
          scrollContainer.scrollTop = scrollTop;
        });
      }
    }
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      (e.target as HTMLInputElement).blur();
    }
  }, []);

  return (
    <div>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
      )}
      <input
        key={fieldKey}
        ref={inputRef}
        type="text"
        defaultValue={defaultValue}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
        placeholder={placeholder}
        disabled={disabled}
      />
    </div>
  );
});

// Memoized left-panel search input that manages its own state to avoid cursor jumping
type LeftSearchInputProps = {
  defaultValue: string;
  onCommit: (value: string) => void;
};

const LeftSearchInput = React.memo(function LeftSearchInputComp({ defaultValue, onCommit }: LeftSearchInputProps) {
  const inputRef = React.useRef<HTMLInputElement | null>(null);

  const handleBlur = useCallback(() => {
    if (inputRef.current) onCommit(inputRef.current.value);
  }, [onCommit]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
  }, []);

  return (
    <div className="relative mb-4">
      <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
      <input
        ref={inputRef}
        type="text"
        placeholder="Search tables..."
        defaultValue={defaultValue}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
    </div>
  );
});

const TextAreaInput = React.memo<{
  defaultValue: string;
  onCommit: (value: string) => void;
  placeholder?: string;
  label?: string;
  rows?: number;
  fieldKey?: string;
}>(({ defaultValue, onCommit, placeholder, label, rows = 3, fieldKey }) => {
  const textAreaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const onCommitRef = React.useRef(onCommit);
  
  // Keep the ref updated
  React.useEffect(() => {
    onCommitRef.current = onCommit;
  }, [onCommit]);

  const handleBlur = useCallback(() => {
    if (textAreaRef.current) {
      // Preserve scroll position before committing
      const scrollContainer = document.querySelector('[data-inspector-scroll]') as HTMLElement;
      const scrollTop = scrollContainer?.scrollTop || 0;
      
      onCommitRef.current(textAreaRef.current.value);
      
      // Restore scroll position after commit
      if (scrollContainer) {
        requestAnimationFrame(() => {
          scrollContainer.scrollTop = scrollTop;
        });
      }
    }
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      (e.target as HTMLTextAreaElement).blur();
    }
  }, []);

  return (
    <div>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2">
          {label}
        </label>
      )}
      <textarea
        key={fieldKey}
        ref={textAreaRef}
        defaultValue={defaultValue}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        rows={rows}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        placeholder={placeholder}
      />
    </div>
  );
});

// Reusable tag input for synonyms; optionally show sample values (default true)
const SynonymsTagInput: React.FC<{
  label?: string;
  values: SynonymWithSamples[];
  placeholder?: string;
  onChange: (values: SynonymWithSamples[]) => void;
  showSamples?: boolean;
}> = ({ label = 'Synonyms', values, placeholder = 'Type a synonym and press Enter', onChange, showSamples = true }) => {
  const [items, setItems] = useState<SynonymWithSamples[]>(values || []);
  const [input, setInput] = useState<string>('');

  useEffect(() => {
    setItems(values || []);
  }, [values]);

  const commit = (next: SynonymWithSamples[]) => {
    setItems(next);
    onChange(next);
  };

  const addCurrent = () => {
    const val = input.trim();
    if (!val) return;
    if (items.some(item => item.synonym === val)) {
      setInput('');
      return;
    }
    const next = [...items, { synonym: val, sample_values: [] }];
    setInput('');
    commit(next);
  };

  const removeItem = (index: number) => {
    commit(items.filter((_, i) => i !== index));
  };



  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
      <div className="space-y-2 mb-2">
        {items.map((item, idx) => (
          <div key={`${item.synonym}-${idx}`} className="border border-gray-200 rounded-lg p-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-blue-700">{item.synonym}</span>
              <button
                onClick={() => removeItem(idx)}
                className="text-red-500 hover:text-red-700 text-sm"
                aria-label="Remove"
              >
                ×
              </button>
            </div>
            {showSamples && (
              <div className="text-xs text-gray-500">
                Sample Values: {item.sample_values && item.sample_values.length > 0 ? item.sample_values.join(', ') : 'None'}
              </div>
            )}
          </div>
        ))}
      </div>
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            addCurrent();
          }
        }}
        onBlur={addCurrent}
        placeholder={placeholder}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />
    </div>
  );
};

// Column Editor Component
const ColumnEditor = React.memo<{
  column: SemanticColumn;
  isEditing: boolean;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onFieldChange: (field: keyof SemanticColumn, value: any) => void;
}>(({ column, isEditing, onEdit, onSave, onCancel, onFieldChange }) => {
  return (
    <div className="border border-gray-200 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          {column.is_primary_key && (
            <div className="w-2 h-2 bg-yellow-500 rounded-full mr-2" title="Primary Key"></div>
          )}
          {column.is_foreign_key && (
            <div className="w-2 h-2 bg-blue-500 rounded-full mr-2" title="Foreign Key"></div>
          )}
          <span className="font-medium text-gray-900">{column.name}</span>
        </div>
        <span className="text-xs text-gray-500">{column.data_type}</span>
      </div>

              {isEditing ? (
        <div className="space-y-2">
          <TextInput
            defaultValue={column.display_name}
            onCommit={(value) => onFieldChange('display_name', value)}
            placeholder="Display Name"
            fieldKey={`${column.id}-display_name`}
          />
          <TextAreaInput
            defaultValue={column.description || ''}
            onCommit={(value) => onFieldChange('description', value)}
            placeholder="Description"
            rows={2}
            fieldKey={`${column.id}-description`}
          />
          <TextAreaInput
            defaultValue={column.business_context || ''}
            onCommit={(value) => onFieldChange('business_context', value)}
            placeholder="Business Context"
            rows={2}
            fieldKey={`${column.id}-business_context`}
          />
          {/* Column synonyms editor */}
          <SynonymsTagInput
            label="Column Synonyms"
            values={column.synonyms || []}
            onChange={(vals) => onFieldChange('synonyms', vals)}
            showSamples={false}
          />
          {/* Column alias input */}
          <TextInput
            defaultValue={column.metadata?.alias || ''}
            onCommit={(value) => onFieldChange('metadata', { ...(column.metadata || {}), alias: value })}
            placeholder="Column alias (e.g., cust_id for customer_id)"
            fieldKey={`${column.id}-alias`}
          />
          {/* Column Metadata Section */}
          <div className="border-t pt-3 mt-3">
            <h4 className="text-sm font-medium text-gray-900 mb-2">Column Metadata for AI Selection</h4>
            
            {/* Business Description */}
            <TextAreaInput
              defaultValue={column.business_description || ''}
              onCommit={(value) => onFieldChange('business_description', value)}
              placeholder="Business-friendly description (e.g., Comprehensive risk assessment combining all risk factors)"
              rows={2}
              fieldKey={`${column.id}-business_description`}
            />
            
            {/* Business Terms */}
            <div className="mb-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Business Terms (comma-separated)</label>
              <input
                type="text"
                defaultValue={(column.business_terms || []).join(', ')}
                onChange={(e) => {
                  const terms = e.target.value.split(',').map(term => term.trim()).filter(term => term);
                  onFieldChange('business_terms', terms);
                }}
                placeholder="e.g., overall risk, total risk, comprehensive risk"
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            {/* Priority */}
            <div className="mb-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Priority</label>
              <select
                value={column.priority || 'medium'}
                onChange={(e) => onFieldChange('priority', e.target.value)}
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            
            {/* Is Preferred */}
            <div className="flex items-center space-x-2 mb-2">
              <input
                type="checkbox"
                id={`${column.id}-preferred`}
                checked={column.is_preferred || false}
                onChange={(e) => onFieldChange('is_preferred', e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor={`${column.id}-preferred`} className="text-xs text-gray-700">
                Preferred Column for this type
              </label>
            </div>
            
            {/* Use Cases */}
            <div className="mb-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Use Cases (comma-separated)</label>
              <input
                type="text"
                defaultValue={(column.use_cases || []).join(', ')}
                onChange={(e) => {
                  const cases = e.target.value.split(',').map(c => c.trim()).filter(c => c);
                  onFieldChange('use_cases', cases);
                }}
                placeholder="e.g., general risk analysis, comprehensive assessment"
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            
            {/* Relevance Keywords */}
            <div className="mb-2">
              <label className="block text-xs font-medium text-gray-700 mb-1">Relevance Keywords (comma-separated)</label>
              <input
                type="text"
                defaultValue={(column.relevance_keywords || []).join(', ')}
                onChange={(e) => {
                  const keywords = e.target.value.split(',').map(k => k.trim()).filter(k => k);
                  onFieldChange('relevance_keywords', keywords);
                }}
                placeholder="e.g., risk, score, assessment, overall"
                className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
          
          {/* Exclude Column checkbox */}
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id={`${column.id}-exclude`}
              checked={column.exclude_column || false}
              onChange={(e) => onFieldChange('exclude_column', e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor={`${column.id}-exclude`} className="text-sm text-gray-700">
              Exclude Column
            </label>
          </div>
          {/* Column type indicator (read-only) */}
          <div className="text-xs text-gray-500 bg-gray-50 px-2 py-1 rounded">
            {column.is_primary_key ? 'Primary Key' : column.is_foreign_key ? 'Foreign Key' : 'Regular Column'}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={onSave}
              className="px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700"
            >
              Save
            </button>
            <button
              onClick={onCancel}
              className="px-2 py-1 bg-gray-300 text-gray-700 text-xs rounded hover:bg-gray-400"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div onClick={onEdit} className="cursor-pointer">
          <p className="text-sm text-gray-700 mb-1">{column.display_name}</p>
          <p className="text-xs text-gray-500">
            {column.description || 'Click to add description'}
          </p>
          {column.business_context && (
            <p className="text-xs text-blue-600 mt-1">
              <strong>Business Context:</strong> {column.business_context}
            </p>
          )}
          {column.exclude_column && (
            <p className="text-xs text-red-600 mt-1">
              <strong>Excluded from queries</strong>
            </p>
          )}
        </div>
      )}
    </div>
  );
});

// Table Details Editor Component
const TableDetailsEditor = React.memo<{
  table: SemanticTable;
  onFieldChange: (field: keyof SemanticTable, value: any) => void;
}>(({ table, onFieldChange }) => {
  // Tag input for arrays
  const TagInput: React.FC<{
    label: string;
    values: string[];
    placeholder?: string;
    onChange: (values: string[]) => void;
  }> = ({ label, values, placeholder, onChange }) => {
    const [items, setItems] = useState<string[]>(values || []);
    const [input, setInput] = useState<string>("");

    useEffect(() => {
      setItems(values || []);
    }, [values]);

    const commit = (next: string[]) => {
      setItems(next);
      onChange(next);
    };

    const addCurrent = () => {
      const val = input.trim();
      if (!val) return;
      if (items.includes(val)) {
        setInput("");
        return;
      }
      const next = [...items, val];
      setInput("");
      commit(next);
    };

    return (
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">{label}</label>
        <div className="flex flex-wrap gap-2 mb-2">
          {items.map((v, idx) => (
            <span key={`${v}-${idx}`} className="inline-flex items-center px-2 py-1 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded">
              {v}
              <button
                onClick={() => commit(items.filter((_, i) => i !== idx))}
                className="ml-2 text-blue-500 hover:text-blue-700"
                aria-label="Remove"
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              addCurrent();
            }
          }}
          onBlur={addCurrent}
          placeholder={placeholder}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <TextInput
        defaultValue={table.display_name}
        onCommit={(value) => onFieldChange('display_name', value)}
        label="Display Name"
        fieldKey={`${table.id}-display_name`}
      />
      <TextAreaInput
        defaultValue={table.description || ''}
        onCommit={(value) => onFieldChange('description', value)}
        label="Description"
        placeholder="Contains all registered customer information including personal details and account status"
        fieldKey={`${table.id}-description`}
      />
      <TextAreaInput
        defaultValue={table.business_context || ''}
        onCommit={(value) => onFieldChange('business_context', value)}
        label="Business Context"
        placeholder="This table stores customer data for e-commerce operations, user authentication, and order processing"
        fieldKey={`${table.id}-business_context`}
      />
      <TextInput
        defaultValue={table.schema_name || ''}
        onCommit={(value) => onFieldChange('schema_name', value)}
        label="Schema Name"
        placeholder="public"
        fieldKey={`${table.id}-schema_name`}
      />
      <TextInput
        defaultValue={table.row_count_estimate?.toString() || ''}
        onCommit={(value) => onFieldChange('row_count_estimate', value ? parseInt(value) || null : null)}
        label="Row Count Estimate"
        placeholder="1000"
        fieldKey={`${table.id}-row_count_estimate`}
      />
      {/* Synonym groups: each synonym name maps to multiple sample values */}
      {(() => {
        type SynonymGroup = { name: string; samples: string[] };
        const groups: SynonymGroup[] = (table.metadata && (table.metadata as any).synonym_groups) || [];

        const [localGroups, setLocalGroups] = useState<SynonymGroup[]>(groups);
        const [newSynonym, setNewSynonym] = useState<string>("");
        const [newSamples, setNewSamples] = useState<string[]>([]);

        useEffect(() => {
          setLocalGroups(groups);
        }, [table.id, table.metadata]);

        const commitGroups = (updated: SynonymGroup[]) => {
          setLocalGroups(updated);
          // store groups in metadata and names in synonyms array
          onFieldChange('metadata', { ...(table.metadata || {}), synonym_groups: updated });
          onFieldChange('synonyms', updated.map(g => ({ synonym: g.name, sample_values: g.samples || [] })));
        };

        const addGroup = () => {
          const name = newSynonym.trim();
          if (!name) return;
          if (localGroups.some(g => g.name.toLowerCase() === name.toLowerCase())) return;
          const updated = [...localGroups, { name, samples: newSamples }];
          setNewSynonym("");
          setNewSamples([]);
          commitGroups(updated);
        };

        const removeGroup = (idx: number) => {
          const updated = localGroups.filter((_, i) => i !== idx);
          commitGroups(updated);
        };

        return (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Add Synonym</label>
              <div className="grid grid-cols-1 gap-2">
                <TextInput
                  defaultValue={newSynonym}
                  onCommit={(val) => setNewSynonym(val)}
                  placeholder="Synonym name (e.g., IT)"
                  fieldKey={`new-synonym-${table.id}`}
                />
                {newSynonym.trim() !== '' && (
                  <>
                    <TagInput
                      label="Sample Values for this synonym"
                      values={newSamples}
                      placeholder="Type a sample value and press Enter"
                      onChange={(vals) => setNewSamples(vals)}
                />
                    <div className="flex justify-end">
                      <button
                        onClick={addGroup}
                        className="px-3 py-2 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        Save Synonym
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>

            {localGroups.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Synonym Groups</label>
                <div className="space-y-3">
                  {localGroups.map((g, idx) => (
                    <div key={`${g.name}-${idx}`} className="border border-gray-200 rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-900">{g.name}</span>
                        <button
                          onClick={() => removeGroup(idx)}
                          className="p-1 text-red-600 hover:text-red-800 hover:bg-red-100 rounded transition-colors"
                          title="Delete synonym"
                        >
                          <Trash className="w-3 h-3" />
                        </button>
                      </div>
                      <TagInput
                        label="Sample Values"
                        values={g.samples}
                        placeholder="Type a sample value and press Enter"
                        onChange={(vals) => {
                          const updated = localGroups.map((grp, i) => i === idx ? { ...grp, samples: vals } : grp);
                          commitGroups(updated);
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* Metrics field: each metric name maps to a value */}
      {(() => {
        type MetricItem = { name: string; value: string };
        const metrics: MetricItem[] = (table.metadata && (table.metadata as any).metric_items) || [];

        const [localMetrics, setLocalMetrics] = useState<MetricItem[]>(metrics);
        const [newMetricName, setNewMetricName] = useState<string>("");
        const [newMetricValue, setNewMetricValue] = useState<string>("");
        const [editingMetric, setEditingMetric] = useState<number | null>(null);
        const [editMetricName, setEditMetricName] = useState<string>("");
        const [editMetricValue, setEditMetricValue] = useState<string>("");

        useEffect(() => {
          setLocalMetrics(metrics);
        }, [table.id, table.metadata]);

        const commitMetrics = (updated: MetricItem[]) => {
          setLocalMetrics(updated);
          // store metric items in metadata and names in metrics array
          onFieldChange('metadata', { ...(table.metadata || {}), metric_items: updated });
          onFieldChange('metrics', updated.map(m => m.name));
        };

        const addMetric = () => {
          const name = newMetricName.trim();
          const value = newMetricValue.trim();
          if (!name || !value) return;
          if (localMetrics.some(m => m.name.toLowerCase() === name.toLowerCase())) return;
          const updated = [...localMetrics, { name, value }];
          setNewMetricName("");
          setNewMetricValue("");
          commitMetrics(updated);
        };

        const removeMetric = (idx: number) => {
          const updated = localMetrics.filter((_, i) => i !== idx);
          commitMetrics(updated);
        };

        const startEditMetric = (idx: number) => {
          const metric = localMetrics[idx];
          setEditMetricName(metric.name);
          setEditMetricValue(metric.value);
          setEditingMetric(idx);
        };

        const saveEditMetric = () => {
          if (editingMetric === null) return;
          const name = editMetricName.trim();
          const value = editMetricValue.trim();
          if (!name || !value) return;
          
          const updated = localMetrics.map((m, i) => 
            i === editingMetric ? { name, value } : m
          );
          commitMetrics(updated);
          setEditingMetric(null);
          setEditMetricName("");
          setEditMetricValue("");
        };

        const cancelEditMetric = () => {
          setEditingMetric(null);
          setEditMetricName("");
          setEditMetricValue("");
        };

        return (
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Add Metric</label>
              <div className="grid grid-cols-2 gap-2">
                <TextInput
                  defaultValue={newMetricName}
                  onCommit={(val) => setNewMetricName(val)}
                  placeholder="Metric name (e.g., Row Count)"
                  fieldKey={`new-metric-name-${table.id}`}
                />
                <TextInput
                  defaultValue={newMetricValue}
                  onCommit={(val) => setNewMetricValue(val)}
                  placeholder="Metric value (e.g., 1000)"
                  fieldKey={`new-metric-value-${table.id}`}
                />
              </div>
              {/* Only show Save Metric button when both fields have content */}
              {newMetricName.trim() !== '' && newMetricValue.trim() !== '' && (
                <div className="flex justify-end mt-2">
                  <button
                    onClick={addMetric}
                    className="px-3 py-2 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                  >
                    Save Metric
                  </button>
                </div>
              )}
            </div>

            {localMetrics.length > 0 && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Current Metrics</label>
                <div className="space-y-3">
                  {localMetrics.map((m, idx) => (
                    <div key={`${m.name}-${idx}`} className="border border-gray-200 rounded-lg p-3">
                      {editingMetric === idx ? (
                        // Edit mode
                        <div className="space-y-2">
                          <div className="grid grid-cols-2 gap-2">
                            <input
                              type="text"
                              value={editMetricName}
                              onChange={(e) => setEditMetricName(e.target.value)}
                              placeholder="Metric name"
                              className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                            />
                            <input
                              type="text"
                              value={editMetricValue}
                              onChange={(e) => setEditMetricValue(e.target.value)}
                              placeholder="Metric value"
                              className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                            />
                          </div>
                          <div className="flex items-center justify-end space-x-2">
                            <button
                              onClick={cancelEditMetric}
                              className="px-2 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={saveEditMetric}
                              disabled={!editMetricName.trim() || !editMetricValue.trim()}
                              className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                            >
                              Save
                            </button>
                          </div>
                        </div>
                      ) : (
                        // Display mode
                        <>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm font-medium text-gray-900">{m.name}</span>
                            <div className="flex items-center space-x-2">
                              <button
                                onClick={() => startEditMetric(idx)}
                                className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
                                title="Edit metric"
                              >
                                <Edit className="w-3 h-3" />
                              </button>
                              <button
                                onClick={() => removeMetric(idx)}
                                className="p-1 text-red-600 hover:text-red-800 hover:bg-red-100 rounded transition-colors"
                                title="Delete metric"
                              >
                                <Trash className="w-3 h-3" />
                              </button>
                            </div>
                          </div>
                          <div className="text-sm text-gray-600">
                            <strong>Value:</strong> {m.value}
                          </div>
                        </>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* Aliases input box */}
      <TextInput
        defaultValue={table.metadata?.alias || ''}
        onCommit={(value) => onFieldChange('metadata', { ...(table.metadata || {}), alias: value })}
        label="Table Alias"
        placeholder="Enter table alias (e.g., cust for customers)"
        fieldKey={`${table.id}-alias`}
      />

      <TextInput
        defaultValue={table.database_id}
        onCommit={() => {}} // Read-only
        label="Database ID"
        disabled
        fieldKey={`${table.id}-database_id`}
      />
    </div>
  );
});

// Main Component
const SemanticSchemaEditor: React.FC<SemanticSchemaEditorProps> = ({ chatbotId, onSave, onConfirm, initialSchema, isEditMode = false }) => {
  // State
  const [schema, setSchema] = useState<DatabaseSchema | null>(initialSchema || null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set());
  
  // Column metadata state
  const [columnMetadata, setColumnMetadata] = useState({
    business_description: '',
    business_terms: [] as string[],
    priority: 'medium' as 'high' | 'medium' | 'low',
    is_preferred: false,
    use_cases: [] as string[],
    relevance_keywords: [] as string[]
  });
  
  // User preferences state
  const [userPreferences, setUserPreferences] = useState<UserPreferences>({
    risk_score_column: '',
    amount_column: '',
    date_column: '',
    default_risk_threshold: 10
  });
  const [selectedTable, setSelectedTable] = useState<SemanticTable | null>(null);
  const [currentInspectorIndex, setCurrentInspectorIndex] = useState(0);
  const [activeTab, setActiveTab] = useState<'details' | 'columns' | 'relationships'>('details');
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddRelationship, setShowAddRelationship] = useState(false);
  const [editingRelationship, setEditingRelationship] = useState<string | null>(null);
  const [editingColumn, setEditingColumn] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRightPanelOpen, setIsRightPanelOpen] = useState(false);
  const [showMetricsDialog, setShowMetricsDialog] = useState(false);
  const [showUserPreferencesDialog, setShowUserPreferencesDialog] = useState(false);
  // Preserve scroll position in inspector panel when toggling edit
  const inspectorScrollRef = React.useRef<HTMLDivElement | null>(null);
  // Relationship filtering state (used by relationship inspector)
  const [relationshipFilter, setRelationshipFilter] = useState<{ a: string; b: string } | null>(null);

  // Export/Import state
  const [isExporting, setIsExporting] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  // Relationship state
  const [newRelationship, setNewRelationship] = useState({
    name: '',
    description: '',
    source_table_id: '',
    source_columns: [] as string[],
    target_table_id: '',
    target_columns: [] as string[],
    relationship_type: 'one_to_many',
    cardinality_ratio: '1:N',
    metadata: {} as Record<string, any>
  });

  const { showToast } = useToaster();

  // EDIT SCHEMA FEATURE: Helper function to sanitize datetime fields
  // 
  // This function fixes the Pydantic validation error that occurred when saving schemas.
  // The issue was that datetime fields were being sent in GMT format (e.g., "Tue, 19 Aug 2025 05:10:30 GMT")
  // but the backend expects ISO format (e.g., "2025-08-19T05:10:30.000Z").
  // 
  // This function ensures all datetime fields across the schema are converted to proper ISO format
  // before being sent to the backend for validation and storage.
  const sanitizeSchema = useCallback((schema: any) => {
    if (!schema) return schema;
    
    // Sanitize datetime fields for individual tables
    const sanitizeTable = (table: any) => {
      const sanitizedColumns: Record<string, any> = {};
      const entries = Object.entries(table?.columns || {}) as [string, any][];
      entries.forEach(([colName, col]) => {
        sanitizedColumns[colName] = {
          ...col,
          created_at: col?.created_at ? new Date(col.created_at).toISOString() : new Date().toISOString(),
          updated_at: col?.updated_at ? new Date(col.updated_at).toISOString() : new Date().toISOString(),
        };
      });
      return {
        ...table,
        created_at: table?.created_at ? new Date(table.created_at).toISOString() : new Date().toISOString(),
        updated_at: table?.updated_at ? new Date(table.updated_at).toISOString() : new Date().toISOString(),
        columns: sanitizedColumns
      };
    };

    // Sanitize the entire schema structure
    const sanitizedTables: Record<string, any> = {};
    Object.entries(schema.tables || {}).forEach(([name, table]: [string, any]) => {
      sanitizedTables[name] = sanitizeTable(table);
    });

    return {
      ...schema,
      created_at: schema.created_at ? new Date(schema.created_at).toISOString() : new Date().toISOString(),
      updated_at: schema.updated_at ? new Date(schema.updated_at).toISOString() : new Date().toISOString(),
      tables: sanitizedTables,
      relationships: (schema.relationships || []).map((rel: any) => ({
        ...rel,
        created_at: rel.created_at ? new Date(rel.created_at).toISOString() : new Date().toISOString(),
      }))
    };
  }, []);

  // EDIT SCHEMA FEATURE: Enhanced schema loading to support edit mode
  useEffect(() => {
    const normalizeIncomingForUI = (incoming: any) => {
      if (!incoming) return incoming;
      const nowIso = new Date().toISOString();
      const uiTables: Record<string, any> = {};
      const incomingTables = incoming.tables || {};
      Object.entries(incomingTables).forEach(([tableName, t]: [string, any]) => {
        const uiColumns: Record<string, any> = {};
        Object.entries(t?.columns || {}).forEach(([colName, c]: [string, any]) => {
          const normalizedColSynonyms = Array.isArray(c?.synonyms)
            ? (c?.synonyms as any[]).map((syn: any) =>
                typeof syn === 'string'
                  ? { synonym: syn, sample_values: [] }
                  : {
                      synonym: syn?.synonym || '',
                      sample_values: Array.isArray(syn?.sample_values) ? syn.sample_values : []
                    }
              )
            : [];

          uiColumns[colName] = {
            id: `${tableName}.${colName}`,
            name: colName,
            display_name: c?.display_name || colName,
            description: c?.description || '',
              business_context: c?.business_context || '',  // ✅ Added
              exclude_column: Boolean(c?.exclude_column),   // ✅ Added
            data_type: c?.data_type || c?.type || 'string',
            is_primary_key: Boolean(c?.is_primary_key || c?.pk),
            is_foreign_key: Boolean(c?.is_foreign_key || c?.fk),
            synonyms: normalizedColSynonyms,
            metadata: c?.metadata || {},
            created_at: c?.created_at || nowIso,
            updated_at: c?.updated_at || nowIso,
          };
            
        });
        // Handle table metrics - convert from dict to metric_items format
        const tableMetrics = t?.metrics || {};
        const metricItems = Object.entries(tableMetrics).map(([metricName, metricData]: [string, any]) => ({
          name: metricName,
          value: metricData?.expression || metricData?.value || 'COUNT(*)'
        }));

        // Build synonym groups for UI from backend table.synonyms
        const tableSynsA = Array.isArray(t?.synonyms) ? t.synonyms : [];
        const synonymGroupsA = tableSynsA.map((s: any) =>
          typeof s === 'string'
            ? { name: s, samples: [] }
            : { name: s?.synonym || '', samples: Array.isArray(s?.sample_values) ? s.sample_values : [] }
        );

        uiTables[tableName] = {
          id: tableName,
          name: tableName,
          display_name: t?.display_name || tableName,
          description: t?.description || '',
          schema_name: t?.schema_name || incoming?.schema_prefix || '',
          database_id: incoming?.id || incoming?.database_id || '',
          columns: uiColumns,
          synonyms: Array.isArray(t?.synonyms) ? t.synonyms.map((syn: any) => 
          typeof syn === 'string' ? { synonym: syn, sample_values: [] } : { 
            synonym: syn.synonym || '', 
            sample_values: syn.sample_values || [] 
          }
        ) : [],
          business_context: t?.business_context,
          row_count_estimate: t?.row_count_estimate,
          metrics: t?.metrics || {},
          metadata: {
            ...(t?.metadata || {}),
            metric_items: metricItems,
            synonym_groups: synonymGroupsA
          },
          created_at: t?.created_at || nowIso,
          updated_at: t?.updated_at || nowIso,
        };
      });

      // Normalize relationships with {from,to}
      const normalizedRelationships = (incoming.relationships || []).map((rel: any) => {
        if (rel && rel.from && rel.to) {
          const [sTable, sCol] = String(rel.from).split('.') as [string, string];
          const [tTable, tCol] = String(rel.to).split('.') as [string, string];
          return {
            ...rel,
            source_table_id: sTable,
            target_table_id: tTable,
            source_columns: sCol ? [sCol] : [],
            target_columns: tCol ? [tCol] : [],
            // Map backend synonyms field to UI metadata.relationship_synonyms
            metadata: {
              ...(rel.metadata || {}),
              relationship_synonyms: Array.isArray(rel.synonyms) ? rel.synonyms : (rel.synonyms ? [rel.synonyms] : [])
            },
            created_at: rel?.created_at || nowIso,
          };
        }
        return { 
          ...rel, 
          // Map backend synonyms field to UI metadata.relationship_synonyms
          metadata: {
            ...(rel.metadata || {}),
            relationship_synonyms: Array.isArray(rel.synonyms) ? rel.synonyms : (rel.synonyms ? [rel.synonyms] : [])
          },
          created_at: rel?.created_at || nowIso 
        };
      });

      // Apply aliases to tables and columns
      if (incoming.aliases && typeof incoming.aliases === 'object') {
        const aliases = incoming.aliases as any;
        const table_aliases = aliases.table_aliases || {};
        const column_aliases = aliases.column_aliases || {};
        
        // Apply table aliases
        Object.entries(table_aliases).forEach(([tableName, alias]) => {
          if (uiTables[tableName]) {
            uiTables[tableName].metadata = {
              ...(uiTables[tableName].metadata || {}),
              alias: alias
            };
          }
        });
        
        // Apply column aliases
        Object.entries(column_aliases).forEach(([tableName, cols]) => {
          if (uiTables[tableName] && uiTables[tableName].columns) {
            Object.entries(cols as Record<string, any>).forEach(([colName, alias]) => {
              if (uiTables[tableName].columns[colName]) {
                uiTables[tableName].columns[colName].metadata = {
                  ...(uiTables[tableName].columns[colName].metadata || {}),
                  alias: alias
                };
              }
            });
          }
        });
      }

      // Handle database-level metrics
      const dbMetrics = incoming?.metrics || [];
      const normalizedDbMetrics = Array.isArray(dbMetrics) ? dbMetrics.map((m: any) => {
        if (typeof m === 'string') {
          return { name: m, value: 'COUNT(*)' };
        }
        return {
          name: m?.name || m?.metric || 'metric',
          value: m?.expression || m?.value || 'COUNT(*)'
        };
      }) : [];

      return {
        ...incoming,
        created_at: incoming?.created_at || nowIso,
        updated_at: incoming?.updated_at || nowIso,
        tables: uiTables,
        relationships: normalizedRelationships,
        metadata: {
          ...(incoming?.metadata || {}),
          database_metric_items: normalizedDbMetrics
        }
      } as DatabaseSchema;
    };
    if (isEditMode && initialSchema) {
      // EDIT MODE: Use the pre-loaded schema from EditSchema page
      // Sanitize datetime fields to prevent validation errors
      const normalized = normalizeIncomingForUI(initialSchema);
      const sanitizedSchema = sanitizeSchema(normalized);
      setSchema(sanitizedSchema);
      const tables = sanitizedSchema.tables;
      const tableNames = Object.keys(tables);
      if (tableNames.length > 0) {
        const firstTableName = tableNames[0];
        setSelectedTable(tables[firstTableName]);
        setSelectedTables(new Set([tables[firstTableName].id]));
      }
      setLoading(false);
    } else {
      // CREATION MODE: Load schema from backend (original behavior)
      loadSemanticSchema();
    }
  }, [chatbotId, initialSchema, isEditMode, sanitizeSchema]);

  const loadSemanticSchema = async () => {
    try {
      setLoading(true);
      const response = await getSemanticSchema(chatbotId);
      const incoming = response.data.semantic_schema;
      const normalized = (function normalize() {
        const nowIso = new Date().toISOString();
        const uiTables: Record<string, any> = {};
        const incomingTables = incoming.tables || {};
        Object.entries(incomingTables).forEach(([tableName, t]: [string, any]) => {
          const uiColumns: Record<string, any> = {};
          Object.entries(t?.columns || {}).forEach(([colName, c]: [string, any]) => {
            const normalizedColSynonyms = Array.isArray(c?.synonyms)
              ? (c?.synonyms as any[]).map((syn: any) =>
                  typeof syn === 'string'
                    ? { synonym: syn, sample_values: [] }
                    : {
                        synonym: syn?.synonym || '',
                        sample_values: Array.isArray(syn?.sample_values) ? syn.sample_values : []
                      }
              )
              : [];

            uiColumns[colName] = {
              id: `${tableName}.${colName}`,
              name: colName,
              display_name: c?.display_name || colName,
              description: c?.description || '',
              business_context: c?.business_context || '',
              exclude_column: Boolean(c?.exclude_column),
              data_type: c?.data_type || c?.type || 'string',
              is_primary_key: Boolean(c?.is_primary_key || c?.pk),
              is_foreign_key: Boolean(c?.is_foreign_key || c?.fk),
              synonyms: normalizedColSynonyms,
              metadata: c?.metadata || {},
              created_at: c?.created_at || nowIso,
              updated_at: c?.updated_at || nowIso,
            };
          });
          // Handle table metrics - convert from dict to metric_items format
          const tableMetrics = t?.metrics || {};
          const metricItems = Object.entries(tableMetrics).map(([metricName, metricData]: [string, any]) => ({
            name: metricName,
            value: metricData?.expression || metricData?.value || 'COUNT(*)'
          }));

          // Normalize table synonyms to SynonymWithSamples objects
          const normalizedTableSynonyms = Array.isArray(t?.synonyms)
            ? t.synonyms.map((syn: any) =>
                typeof syn === 'string'
                  ? { synonym: syn, sample_values: [] }
                  : {
                      synonym: syn?.synonym || '',
                      sample_values: Array.isArray(syn?.sample_values) ? syn.sample_values : []
                    }
              )
            : [];

          uiTables[tableName] = {
            id: tableName,
            name: tableName,
            display_name: t?.display_name || tableName,
            description: t?.description || '',
            schema_name: t?.schema_name || incoming?.schema_prefix || '',
            database_id: incoming?.id || incoming?.database_id || '',
            columns: uiColumns,
            synonyms: normalizedTableSynonyms,
            business_context: t?.business_context,
            row_count_estimate: t?.row_count_estimate,
            metrics: t?.metrics || {},
            metadata: {
              ...(t?.metadata || {}),
              metric_items: metricItems
            },
            created_at: t?.created_at || nowIso,
            updated_at: t?.updated_at || nowIso,
          };
        });
        const rels = (incoming.relationships || []).map((rel: any) => {
          if (rel && rel.from && rel.to) {
            const [sTable, sCol] = String(rel.from).split('.') as [string, string];
            const [tTable, tCol] = String(rel.to).split('.') as [string, string];
            return {
              ...rel,
              source_table_id: sTable,
              target_table_id: tTable,
              source_columns: sCol ? [sCol] : [],
              target_columns: tCol ? [tCol] : [],
              // Map backend synonyms field to UI metadata.relationship_synonyms
              metadata: {
                ...(rel.metadata || {}),
                relationship_synonyms: Array.isArray(rel.synonyms) ? rel.synonyms.map((syn: any) => 
                  typeof syn === 'object' && syn.synonym ? syn.synonym : syn
                ) : (rel.synonyms ? [rel.synonyms] : [])
              },
              created_at: rel?.created_at || nowIso,
            };
          }
          return { 
            ...rel, 
            // Map backend synonyms field to UI metadata.relationship_synonyms
            metadata: {
              ...(rel.metadata || {}),
              relationship_synonyms: Array.isArray(rel.synonyms) ? rel.synonyms.map((syn: any) => 
                typeof syn === 'object' && syn.synonym ? syn.synonym : syn
              ) : (rel.synonyms ? [rel.synonyms] : [])
            },
            created_at: rel?.created_at || nowIso 
          };
        });

        // Apply aliases to tables and columns
        if (incoming.aliases && typeof incoming.aliases === 'object') {
          const aliases = incoming.aliases as any;
          const table_aliases = aliases.table_aliases || {};
          const column_aliases = aliases.column_aliases || {};
          
          // Apply table aliases
          Object.entries(table_aliases).forEach(([tableName, alias]) => {
            if (uiTables[tableName]) {
              uiTables[tableName].metadata = {
                ...(uiTables[tableName].metadata || {}),
                alias: alias
              };
            }
          });
          
          // Apply column aliases
          Object.entries(column_aliases).forEach(([tableName, cols]) => {
            if (uiTables[tableName] && uiTables[tableName].columns) {
              Object.entries(cols as Record<string, any>).forEach(([colName, alias]) => {
                if (uiTables[tableName].columns[colName]) {
                  uiTables[tableName].columns[colName].metadata = {
                    ...(uiTables[tableName].columns[colName].metadata || {}),
                    alias: alias
                  };
                }
              });
            }
          });
        }

        // Handle database-level metrics
        const dbMetrics = incoming?.metrics || [];
        const normalizedDbMetrics = Array.isArray(dbMetrics) ? dbMetrics.map((m: any) => {
          if (typeof m === 'string') {
            return { name: m, value: 'COUNT(*)' };
          }
          return {
            name: m?.name || m?.metric || 'metric',
            value: m?.expression || m?.value || 'COUNT(*)'
          };
        }) : [];

        return { 
          ...incoming, 
          tables: uiTables, 
          relationships: rels,
          metadata: {
            ...(incoming?.metadata || {}),
            database_metric_items: normalizedDbMetrics
          }
        } as DatabaseSchema;
      })();

      setSchema(normalized);
      
      const tables = (normalized as any).tables;
      const tableNames = Object.keys(tables);
      if (tableNames.length > 0) {
        const firstTableName = tableNames[0];
        setSelectedTable(tables[firstTableName]);
        setSelectedTables(new Set([tables[firstTableName].id]));
      }
    } catch (error: any) {
      showToast('Failed to load semantic schema: ' + (error.response?.data?.error || error.message), 'error');
    } finally {
      setLoading(false);
    }
  };

  // Optimized update functions with immutable patterns
  const updateTableField = useCallback((tableId: string, field: keyof SemanticTable, value: any) => {
    // Preserve scroll position during updates
    const scrollContainer = inspectorScrollRef.current;
    const scrollTop = scrollContainer?.scrollTop || 0;
    
    setSchema(prev => {
      if (!prev) return prev;
      
      const updatedTables = { ...prev.tables };
      const tableNames = Object.keys(updatedTables);
      
      for (const tableName of tableNames) {
        if (updatedTables[tableName].id === tableId) {
          updatedTables[tableName] = { 
            ...updatedTables[tableName], 
            [field]: value, 
            updated_at: new Date().toISOString() 
          };
          break;
        }
      }
      
      return {
        ...prev,
        tables: updatedTables
      };
    });

    // Update selectedTable if it's the one being edited
    if (selectedTable?.id === tableId) {
      setSelectedTable(prev => prev ? { ...prev, [field]: value, updated_at: new Date().toISOString() } : prev);
    }
    
    // Restore scroll position with multiple attempts to ensure it sticks
    const restoreScroll = () => {
      if (scrollContainer && scrollContainer.scrollTop !== scrollTop) {
        scrollContainer.scrollTop = scrollTop;
        // Try again on next frame if it didn't stick
        requestAnimationFrame(restoreScroll);
      }
    };
    
    requestAnimationFrame(restoreScroll);
  }, [selectedTable]);

  const updateColumnField = useCallback((tableId: string, columnId: string, field: keyof SemanticColumn, value: any) => {
    // Preserve scroll position during updates
    const scrollContainer = inspectorScrollRef.current;
    const scrollTop = scrollContainer?.scrollTop || 0;
    
    setSchema(prev => {
      if (!prev) return prev;
      
      const updatedTables = { ...prev.tables };
      const tableNames = Object.keys(updatedTables);
      
      for (const tableName of tableNames) {
        if (updatedTables[tableName].id === tableId) {
          const updatedColumns = { ...updatedTables[tableName].columns };
          const columnNames = Object.keys(updatedColumns);
          
          for (const columnName of columnNames) {
            if (updatedColumns[columnName].id === columnId) {
              updatedColumns[columnName] = { 
                ...updatedColumns[columnName], 
                [field]: value, 
                updated_at: new Date().toISOString() 
              };
              break;
            }
          }
          
          updatedTables[tableName] = {
            ...updatedTables[tableName],
            columns: updatedColumns,
            updated_at: new Date().toISOString()
          };
          break;
        }
      }
      
      return {
        ...prev,
        tables: updatedTables
      };
    });

    // Update selectedTable if it's the one being edited
    if (selectedTable?.id === tableId) {
      setSelectedTable(prev => {
        if (!prev) return prev;
        const updatedColumns = { ...prev.columns };
        const columnNames = Object.keys(updatedColumns);
        
        for (const columnName of columnNames) {
          if (updatedColumns[columnName].id === columnId) {
            updatedColumns[columnName] = { 
              ...updatedColumns[columnName], 
              [field]: value, 
              updated_at: new Date().toISOString() 
            };
            break;
          }
        }
        
        return {
          ...prev,
          columns: updatedColumns,
          updated_at: new Date().toISOString()
        };
      });
    }
    
    // Restore scroll position with multiple attempts to ensure it sticks
    const restoreScroll = () => {
      if (scrollContainer && scrollContainer.scrollTop !== scrollTop) {
        scrollContainer.scrollTop = scrollTop;
        // Try again on next frame if it didn't stick
        requestAnimationFrame(restoreScroll);
      }
    };
    
    requestAnimationFrame(restoreScroll);
  }, [selectedTable]);

  // Helper function to check if a string is valid ISO 8601 format
  const isValidISODate = (dateString: string): boolean => {
    try {
      const date = new Date(dateString);
      return date.toISOString() === dateString;
    } catch {
      return false;
    }
  };

  // Helper function to ensure all datetime fields are in ISO 8601 format
  const sanitizeSchemaDates = (schemaData: DatabaseSchema): DatabaseSchema => {
    const sanitizeDate = (dateValue: any): string => {
      if (!dateValue) return new Date().toISOString();
      if (typeof dateValue === 'string') {
        // If it's already valid ISO format, return as is
        if (isValidISODate(dateValue)) {
          return dateValue;
        }
        // Try to parse and convert to ISO
        try {
          const parsedDate = new Date(dateValue);
          if (isNaN(parsedDate.getTime())) {
            return new Date().toISOString();
          }
          return parsedDate.toISOString();
        } catch {
          return new Date().toISOString();
        }
      }
      // If it's a Date object, convert to ISO
      if (dateValue instanceof Date) {
        return dateValue.toISOString();
      }
      return new Date().toISOString();
    };

    const sanitizedTables: Record<string, any> = {};
    Object.entries(schemaData.tables || {}).forEach(([name, table]: [string, any]) => {
      const sanitizedColumns: Record<string, any> = {};
      Object.entries(table.columns || {}).forEach(([colName, column]: [string, any]) => {
        sanitizedColumns[colName] = {
          ...column,
          created_at: sanitizeDate(column.created_at),
          updated_at: sanitizeDate(column.updated_at)
        };
      });
      sanitizedTables[name] = {
        ...table,
        created_at: sanitizeDate(table.created_at),
        updated_at: sanitizeDate(table.updated_at),
        columns: sanitizedColumns
      };
    });

    return {
      ...schemaData,
      created_at: sanitizeDate(schemaData.created_at),
      updated_at: sanitizeDate(schemaData.updated_at),
      tables: sanitizedTables,
      relationships: (schemaData.relationships || []).map((rel: any) => ({
        ...rel,
        created_at: sanitizeDate(rel.created_at)
      }))
    };
  };

  // Save functions
  const handleSaveSchema = async () => {
    console.log(' Save button clicked!');
    console.log('Schema:', schema);
    console.log('Saving state:', saving);
    
    if (!schema) {
      console.log(' No schema to save');
      showToast('No schema to save', 'error');
      return;
    }
    
    try {
      console.log(' Starting save process...');
      setSaving(true);
      
      // Validate schema before saving
      if (!schema.tables || Object.keys(schema.tables).length === 0) {
        throw new Error('Schema must contain at least one table');
      }
      
      // Sanitize all datetime fields before sending to backend
      const sanitizedSchema = sanitizeSchemaDates(schema);

      // Roll up table synonym groups into top-level schema.synonyms for persistence
      const rolledSynonyms: Record<string, string[]> = {};
      Object.values(sanitizedSchema.tables).forEach((t: any) => {
        const groups = (t.metadata && (t.metadata as any).synonym_groups) || [];
        groups.forEach((g: any) => {
          const name = (g?.name || '').toString().trim();
          if (!name) return;
          const samples: string[] = Array.isArray(g?.samples) ? g.samples.filter((s: any) => typeof s === 'string') : [];
          if (!rolledSynonyms[name]) rolledSynonyms[name] = [];
          samples.forEach((s) => {
            if (!rolledSynonyms[name].includes(s)) rolledSynonyms[name].push(s);
          });
        });
      });

      // Roll up relationship synonyms into schema.metadata for extra persistence
      const relSynById: Record<string, string[]> = {};
      const relSynByPair: Record<string, string[]> = {};
      sanitizedSchema.relationships.forEach((r) => {
        const syns: string[] = (r.metadata && (r.metadata as any).relationship_synonyms) || [];
        if (syns && syns.length > 0) {
          relSynById[r.id] = Array.from(new Set(syns));
          const pairKey = `${r.source_table_id}__${r.target_table_id}`;
          relSynByPair[pairKey] = Array.from(new Set([...(relSynByPair[pairKey] || []), ...syns]));
        }
      });

      // Transform UI format to backend clean format
      const transformedTables: Record<string, any> = {};
      const tableAliases: Record<string, string> = {};
      const columnAliases: Record<string, Record<string, string>> = {};
      
      Object.entries(sanitizedSchema.tables).forEach(([tableName, table]: [string, any]) => {
        // Collect table aliases
        if (table.metadata?.alias) {
          tableAliases[tableName] = table.metadata.alias;
        }
        
        // Transform columns from UI format to backend clean format
        const transformedColumns: Record<string, any> = {};
        Object.entries(table.columns).forEach(([colName, col]: [string, any]) => {
          // Collect column aliases
          if (col.metadata?.alias) {
            if (!columnAliases[tableName]) {
              columnAliases[tableName] = {};
            }
            columnAliases[tableName][colName] = col.metadata.alias;
          }
          
          const columnSynonyms = Array.isArray(col.synonyms) ? col.synonyms.map((syn: any) => 
            typeof syn === 'object' && syn.synonym ? syn.synonym : syn
          ) : [];
          console.log(`DEBUG: Column ${tableName}.${colName} synonyms being sent:`, columnSynonyms);

          transformedColumns[colName] = {
            // Primary fields for backend clean structure
            type: col.data_type || col.type || "text", // Ensure type is always a string
            pk: col.is_primary_key || col.pk || false,
            unique: col.unique || false,
            default: col.default || null,
            // Boolean fk like pk (true/false), keep detailed ref separately
            fk: Boolean(col.fk) || Boolean(col.is_foreign_key),
            synonyms: columnSynonyms,
            // Legacy fields for backward compatibility
            id: col.id,
            name: col.name || colName, // Use exact column name
            display_name: col.display_name || col.name || colName, // Preserve exact name
            description: col.description || "",
            data_type: col.data_type || col.type || "text",
            is_primary_key: col.is_primary_key || col.pk || false,
            is_foreign_key: col.is_foreign_key || Boolean(col.fk) || false,
            metadata: col.metadata || {},
            created_at: col.created_at,
            updated_at: col.updated_at,
            // Preserve detailed fk reference for UI consumers
            fk_ref: col.fk && typeof col.fk === 'object' ? col.fk : (col.is_foreign_key ? { table: "", column: "" } : null)
          };
        });

        // Transform metrics from metadata.metric_items (where UI stores them) or fallback to table.metrics
        const metricItems = (table.metadata && (table.metadata as any).metric_items) || [];
        console.log(`DEBUG: Table ${tableName} metric items from UI:`, metricItems);
        console.log(`DEBUG: Table ${tableName} metric expressions:`, metricItems.map((m: any) => ({ name: m.name, value: m.value })));
        
        const transformedMetrics: Record<string, any> = {};
        if (Array.isArray(metricItems) && metricItems.length > 0) {
          // Use metric_items from UI (contains name + value)
          metricItems.forEach((metric: any) => {
            const metricName = metric.name || metric.metric || 'metric';
            transformedMetrics[metricName] = {
              name: metricName,
              expression: metric.value || "COUNT(*)",
              default_filters: []
            };
          });
        } else if (table.metrics && Array.isArray(table.metrics)) {
          // Fallback to table.metrics array (just names)
          table.metrics.forEach((metricName: string) => {
            transformedMetrics[metricName] = {
              name: metricName,
              expression: "COUNT(*)", // Default expression
              default_filters: []
            };
          });
        }
        
        console.log(`DEBUG: Table ${tableName} transformed metrics:`, transformedMetrics);
        console.log(`DEBUG: Table ${tableName} final expressions:`, Object.values(transformedMetrics).map((m: any) => ({ name: m.name, expression: m.expression })));

        const tableSynonyms = Array.isArray(table.synonyms) ? table.synonyms.map((syn: any) => 
          typeof syn === 'object' && syn.synonym ? syn : { synonym: syn, sample_values: [] }
        ) : [];
        console.log(`🔍 DEBUG: Table ${tableName} synonyms being sent:`, tableSynonyms);

        transformedTables[tableName] = {
          // Primary fields for backend clean structure
          columns: transformedColumns,
          metrics: transformedMetrics,
          synonyms: tableSynonyms,
          business_context: table.business_context || "",
          row_count_estimate: table.row_count_estimate || null,
          // Legacy fields for backward compatibility
          id: table.id,
          name: table.name,
          display_name: table.display_name || table.name, // Use name if display_name is empty
          description: table.description || "",
          schema_name: table.schema || table.schema_name,
          database_id: table.database_id,
          metadata: table.metadata || {},
          created_at: table.created_at,
          updated_at: table.updated_at,
          // New fields explicitly included for backend JSON
          table_id: table.id
        };
      });

      // Transform relationships to backend clean format
      const transformedRelationships = sanitizedSchema.relationships.map((rel: any, index: number) => {
        const relationshipSynonyms = (rel.metadata && (rel.metadata as any).relationship_synonyms) || rel.synonyms || [];
        const normalizedRelSynonyms = Array.isArray(relationshipSynonyms) ? relationshipSynonyms.map((syn: any) => 
          typeof syn === 'object' && syn.synonym ? syn.synonym : syn
        ) : [];
        console.log(`DEBUG: Relationship ${index} synonyms being sent:`, normalizedRelSynonyms);
        
        return {
          // Primary fields for backend clean structure
          from_field: `${rel.source_table_id}.${(rel.source_columns || []).join(',')}`,
          to: `${rel.target_table_id}.${(rel.target_columns || []).join(',')}`,
          // Map UI metadata.relationship_synonyms to backend synonyms field as simple strings
          synonyms: normalizedRelSynonyms,
          // Add relationship_type from frontend
          relationship_type: rel.relationship_type || rel.relationship_type_legacy || null,
          cardinality_ratio: rel.cardinality_ratio || rel.cardinality_ratio_legacy || null,
          confidence_score: typeof rel.confidence_score === 'number' ? rel.confidence_score : (rel.confidence_score_legacy ?? null),
          // Legacy fields for backward compatibility
          id: rel.id,
          name: rel.name || rel.id,
          description: rel.description || "",
          source_table_id: rel.source_table_id,
          target_table_id: rel.target_table_id,
          source_columns: rel.source_columns || [],
          target_columns: rel.target_columns || [],
          metadata: rel.metadata || {},
          created_at: rel.created_at,
          updated_at: rel.updated_at || rel.created_at
        };
      });

      // Normalize database-level metrics into full objects (BusinessMetric shape)
      // Read from metadata.database_metric_items (where UI stores them) or fallback to schema.metrics
      const dbMetricItems = (sanitizedSchema.metadata && (sanitizedSchema.metadata as any).database_metric_items) || [];
      console.log('DEBUG: Database metric items from UI:', dbMetricItems);
      console.log('DEBUG: Database metric expressions:', dbMetricItems.map((m: any) => ({ name: m.name, value: m.value })));
      console.log('DEBUG: Full metadata:', sanitizedSchema.metadata);
      console.log('DEBUG: Schema metrics array:', sanitizedSchema.metrics);
      
      const dbMetrics = Array.isArray(dbMetricItems) && dbMetricItems.length > 0
        ? dbMetricItems.map((m: any) => {
            if (typeof m === 'string') {
              return {
                name: m,
                expression: 'COUNT(*)',
                default_filters: [],
  
              };
            }
            const name = m?.name || m?.metric || 'metric';
            const expression = m?.value || 'COUNT(*)';
            const default_filters = Array.isArray(m?.default_filters) ? m.default_filters : [];
            return { name, expression, default_filters };
          })
        : Array.isArray((sanitizedSchema as any).metrics)
        ? (sanitizedSchema as any).metrics.map((m: any) => {
            if (typeof m === 'string') {
              return {
                name: m,
                expression: 'COUNT(*)',
                default_filters: [],
  
              };
            }
            const name = m?.name || m?.metric || 'metric';
            const expression = m?.value || 'COUNT(*)';
            const default_filters = Array.isArray(m?.default_filters) ? m.default_filters : [];
            return { name, expression, default_filters };
          })
        : [];
      
      console.log('DEBUG: Normalized database metrics for payload:', dbMetrics);

      const payloadSchema = {
        // Primary fields for backend clean structure
        id: sanitizedSchema.id,
        display_name: sanitizedSchema.display_name || sanitizedSchema.name, // Preserve exact user-provided name
        dialect: (sanitizedSchema as any).dialect || "postgres", // Use provided dialect or default
        schema_prefix: (sanitizedSchema as any).schema_prefix || (sanitizedSchema as any).schema_name,
        connection_config: {
          db_url: sanitizedSchema.connection_config?.db_url || "postgresql://localhost/db",
          db_type: sanitizedSchema.connection_config?.db_type || "postgresql"
        },
        tables: transformedTables,
        relationships: transformedRelationships,
        aliases: {
          table_aliases: tableAliases,
          column_aliases: columnAliases
        },
        date_aliases: (sanitizedSchema as any).date_aliases || {},
        // Legacy fields for backward compatibility
        database_id: sanitizedSchema.database_id,
        name: sanitizedSchema.name,
        // Database-level metrics (normalized to objects)
        metrics: dbMetrics,
        synonyms: rolledSynonyms, // Include rolled up synonyms
        metadata: {
          ...(sanitizedSchema.metadata || {}),
          relationship_synonyms_map: relSynById,
          relationship_synonyms_by_pair: relSynByPair,
        },
        created_at: sanitizedSchema.created_at,
        updated_at: sanitizedSchema.updated_at
      };
      
      // Log the cleaned schema structure for verification
      console.log('Cleaned Schema Structure:', {
        tables: Object.keys(transformedTables).length,
        columns: Object.values(transformedTables).reduce((sum, t) => sum + Object.keys(t.columns).length, 0),
        relationships: transformedRelationships.length,
        aliases: {
          table_aliases: Object.keys(tableAliases).length,
          column_aliases: Object.keys(columnAliases).length
        }
      });
      
      // Show sample of cleaned column structure
      const sampleTable = Object.values(transformedTables)[0];
      if (sampleTable && Object.keys(sampleTable.columns).length > 0) {
        const sampleColumn = Object.values(sampleTable.columns)[0] as any;
        console.log('Sample Clean Column Structure:', {
          type: sampleColumn.type,
          pk: sampleColumn.pk,
          synonyms: sampleColumn.synonyms,
          metadata: sampleColumn.metadata
        });
      }
      
      // Log the final payload structure for debugging
      console.log('Final Payload Structure:', {
        id: payloadSchema.id,
        display_name: payloadSchema.display_name,
        dialect: payloadSchema.dialect,
        connection_config: payloadSchema.connection_config,
        tables_count: Object.keys(payloadSchema.tables).length,
        relationships_count: payloadSchema.relationships.length,
        aliases_count: Object.keys(payloadSchema.aliases.table_aliases).length,
        db_metrics_count: payloadSchema.metrics.length,
        db_metrics_sample: payloadSchema.metrics.slice(0, 2)
      });
      
      // Log the full payload for debugging (truncated)
      console.log('Full Payload (truncated):', JSON.stringify(payloadSchema, null, 2).substring(0, 1000) + '...');
      
      // Validate payload before sending
      try {
        JSON.stringify(payloadSchema);
        console.log('Payload is valid JSON');
      } catch (jsonError) {
        console.error('Payload contains invalid JSON:', jsonError);
        throw new Error('Invalid JSON structure in payload');
      }
      
      // Validate required fields
      if (!payloadSchema.id) {
        throw new Error('Schema ID is required');
      }
      if (!payloadSchema.display_name) {
        throw new Error('Schema display name is required');
      }
      if (!payloadSchema.connection_config) {
        throw new Error('Connection config is required');
      }
      
      // Check payload size
      const payloadSize = JSON.stringify(payloadSchema).length;
      console.log(`Payload size: ${payloadSize} characters`);
      if (payloadSize > 1000000) { // 1MB limit
        console.warn('Payload is very large, this might cause issues');
      }
      
      console.log('Sending schema to backend...');
      await updateSemanticSchema(chatbotId, payloadSchema);
      console.log('Schema updated successfully');
      showToast('Schema updated successfully', 'success');
      
      if (onSave) {
        try {
          onSave(payloadSchema);
        } catch (callbackError) {
          console.error('onSave callback failed:', callbackError);
          // Don't show error to user as the main save succeeded
        }
      }
    } catch (error: any) {
      console.error(' Save schema error:', error);
      console.error(' Error response:', error.response?.data);
      console.error(' Error status:', error.response?.status);
      console.error(' Error headers:', error.response?.headers);
      
      const errorMessage = error.response?.data?.error || error.message || 'Unknown error occurred';
      showToast('Failed to save schema: ' + errorMessage, 'error');
      throw error; // Re-throw so calling functions can handle it
    } finally {
      setSaving(false);
    }
  };

  const handleConfirmAndContinue = async () => {
    try {
      await handleSaveSchema();
      if (onConfirm) onConfirm();
    } catch (error) {
      // Error is already handled in handleSaveSchema, just prevent progression
      console.error('Failed to save schema, cannot continue:', error);
    }
  };

  const handleRefreshSchema = async () => {
    await loadSemanticSchema();
    showToast('Schema refreshed successfully', 'success');
  };

  // Export schema to Excel
  const handleExportSchema = async () => {
    if (!schema) {
      showToast('No schema to export', 'error');
      return;
    }

    try {
      setIsExporting(true);
      await exportSemanticSchema(chatbotId);
      showToast('Schema exported successfully', 'success');
    } catch (error) {
      console.error('Export error:', error);
      showToast('Failed to export schema', 'error');
    } finally {
      setIsExporting(false);
    }
  };

  // Import schema from Excel
  const handleImportSchema = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      setIsImporting(true);
      
      const response = await importSemanticSchema(chatbotId, file);
      showToast(`Schema imported successfully. Updated ${response.data.updated_columns} columns.`, 'success');
      
      // Refresh the schema to show updated data
      await loadSemanticSchema();
    } catch (error) {
      console.error('Import error:', error);
      showToast(`Failed to import schema: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
    } finally {
      setIsImporting(false);
      // Reset file input
      event.target.value = '';
    }
  };

  // Table selection
  const handleTableSelection = useCallback((tableId: string, selected: boolean) => {
    // Compute next selection set synchronously
    const nextSelection = new Set(selectedTables);
    if (selected) {
      nextSelection.add(tableId);
    } else {
      nextSelection.delete(tableId);
    }
    setSelectedTables(nextSelection);

    // If current inspector table was deselected, switch to first remaining
    if (!selected && selectedTable && selectedTable.id === tableId) {
      const firstId = Array.from(nextSelection)[0];
      const nextTable = firstId ? (Object.values(schema?.tables || {}) as any[]).find(t => t.id === firstId) || null : null;
      setSelectedTable(nextTable || null);
      setCurrentInspectorIndex(0);
      if (nextTable) {
        setIsRightPanelOpen(true); // Keep right panel open if there are remaining tables
      } else {
        setIsRightPanelOpen(false); // Close right panel if no tables selected
      }
      return;
    }

    // If nothing selected in inspector yet, pick the first from selection
    if (selected && !selectedTable) {
      const firstId = Array.from(nextSelection)[0];
      const nextTable = firstId ? (Object.values(schema?.tables || {}) as any[]).find(t => t.id === firstId) || null : null;
      setSelectedTable(nextTable || null);
      setCurrentInspectorIndex(0);
      setIsRightPanelOpen(true); // Open right panel when table is selected
    }
  }, [schema, selectedTable, selectedTables]);

  // Keep right panel in sync with selected set (robust against any external changes)
  useEffect(() => {
    const ids = Array.from(selectedTables);
    if (ids.length === 0) {
      if (selectedTable) setSelectedTable(null);
      setCurrentInspectorIndex(0);
      setIsRightPanelOpen(false); // Close right panel when no tables selected
      return;
    }
    if (!selectedTable || !selectedTables.has(selectedTable.id)) {
      const next = (Object.values(schema?.tables || {}) as any[]).find(t => t.id === ids[0]) || null;
      setSelectedTable(next);
      setCurrentInspectorIndex(0);
      if (next) {
        setIsRightPanelOpen(true); // Open right panel when table is selected
      }
    }
  }, [selectedTables, schema, selectedTable]);

  const handleTableClick = useCallback((table: SemanticTable) => {
    if (!selectedTables.has(table.id)) {
      setSelectedTables(prev => new Set([...prev, table.id]));
    }
    setSelectedTable(table);
    setActiveTab('details');
    setIsRightPanelOpen(true); // Open right panel when table is clicked
  }, [selectedTables]);

  // Keep inspector scroll stable when entering column edit mode
  const handleStartEditColumn = useCallback((columnId: string) => {
    const scroller = inspectorScrollRef.current;
    const prevTop = scroller ? scroller.scrollTop : 0;
    setEditingColumn(columnId);
    // Restore scroll on next paint and make the edited row visible
    requestAnimationFrame(() => {
      if (scroller) scroller.scrollTop = prevTop;
      const target = document.getElementById(`col-${columnId}`);
      if (target) target.scrollIntoView({ block: 'nearest' });
    });
  }, []);

  const handleSelectAll = () => {
    if (!schema) return;
    const allTableIds = Object.values(schema.tables).map(t => t.id);
    setSelectedTables(new Set(allTableIds));
  };

  const handleClearSelection = () => {
    setSelectedTables(new Set());
    setSelectedTable(null);
    setIsRightPanelOpen(false);
  };

  // Helper functions
  const getSelectedTablesArray = useMemo(() => {
    if (!schema) return [];
    return Object.values(schema.tables).filter(table => selectedTables.has(table.id));
  }, [schema, selectedTables]);

  const getRelationshipsBetweenSelectedTables = useMemo(() => {
    if (!schema) return [];
    const selectedTableIds = Array.from(selectedTables);
    return schema.relationships.filter(rel => 
      selectedTableIds.includes(rel.source_table_id) && selectedTableIds.includes(rel.target_table_id)
    );
  }, [schema, selectedTables]);

  const filteredTables = useMemo(() => {
    if (!schema) return [];
    const q = (searchTerm || '').toLowerCase();
    return (Object.values(schema.tables) as any[]).filter((table: any) => {
      const name = (table?.name || '').toLowerCase();
      const displayName = (table?.display_name || '').toLowerCase();
      return name.includes(q) || displayName.includes(q);
    });
  }, [schema, searchTerm]);

  const getTableName = (tableId: string): string => {
    const table = Object.values(schema?.tables || {}).find(t => t.id === tableId);
    return table?.name || '';
  };

  // Legacy diagram edge computation removed - ReactFlow handles all layout automatically

  // Clear any pair filter if selection context changes significantly
  useEffect(() => {
    setRelationshipFilter(null);
  }, [selectedTables]);

  // Legacy pan/zoom handlers removed - now using ReactFlow for all interactions

  // Navigation
  const navigateInspector = (direction: 'prev' | 'next') => {
    const selectedArray = getSelectedTablesArray;
    if (selectedArray.length <= 1) return;
    
    let newIndex = currentInspectorIndex;
    if (direction === 'next') {
      newIndex = (currentInspectorIndex + 1) % selectedArray.length;
    } else {
      newIndex = currentInspectorIndex === 0 ? selectedArray.length - 1 : currentInspectorIndex - 1;
    }
    
    setCurrentInspectorIndex(newIndex);
    setSelectedTable(selectedArray[newIndex]);
    setIsRightPanelOpen(true); // Ensure right panel is open when navigating
  };

  // Relationship functions
  const addNewRelationship = () => {
    if (!schema || !newRelationship.source_table_id || !newRelationship.target_table_id) return;
    
    const relationship: SemanticRelationship = {
      id: `user_rel_${Date.now()}`, // Use a different prefix for user-created relationships
      name: newRelationship.name || `${getTableName(newRelationship.source_table_id)}_to_${getTableName(newRelationship.target_table_id)}`,
      description: newRelationship.description,
      source_table_id: newRelationship.source_table_id,
      target_table_id: newRelationship.target_table_id,
      source_columns: newRelationship.source_columns,
      target_columns: newRelationship.target_columns,
      relationship_type: newRelationship.relationship_type,
      cardinality_ratio: newRelationship.cardinality_ratio,
      join_sql: generateJoinSQL(),
      confidence_score: 1.0,
      metadata: { 
        user_created: true,
        relationship_synonyms: newRelationship.metadata?.relationship_synonyms || []
      }, // Mark as user-created
      created_at: new Date().toISOString() // Already correct ISO format
    };
    
    setSchema(prev => prev ? {
      ...prev,
      relationships: [...prev.relationships, relationship]
    } : prev);
    
    setShowAddRelationship(false);
    resetNewRelationship();
    showToast('Relationship added successfully', 'success');
  };

  const generateJoinSQL = (): string => {
    const sourceTable = getTableName(newRelationship.source_table_id);
    const targetTable = getTableName(newRelationship.target_table_id);
    
    if (newRelationship.source_columns.length > 0 && newRelationship.target_columns.length > 0) {
      return `${sourceTable}.${newRelationship.source_columns[0]} = ${targetTable}.${newRelationship.target_columns[0]}`;
    }
    return '';
  };

  const resetNewRelationship = () => {
    setNewRelationship({
      name: '',
      description: '',
      source_table_id: '',
      source_columns: [],
      target_table_id: '',
      target_columns: [],
      relationship_type: 'one_to_many',
      cardinality_ratio: '1:N',
      metadata: {}
    });
    setEditingRelationship(null);
  };

  // Check if a relationship is user-created (editable)
  const isUserCreatedRelationship = (rel: SemanticRelationship): boolean => {
    return rel.metadata?.user_created === true || rel.id?.startsWith('user_rel_');
  };

  // Delete a user-created relationship
  const deleteRelationship = (relationshipId: string) => {
    if (!schema) return;
    
    setSchema(prev => prev ? {
      ...prev,
      relationships: prev.relationships.filter(rel => rel.id !== relationshipId)
    } : prev);
    
    showToast('Relationship deleted successfully', 'success');
  };



  // Start editing a relationship
  const startEditRelationship = (relationship: SemanticRelationship) => {
    setNewRelationship({
      name: relationship.name,
      description: relationship.description || '',
      source_table_id: relationship.source_table_id,
      source_columns: relationship.source_columns,
      target_table_id: relationship.target_table_id,
      target_columns: relationship.target_columns,
      relationship_type: relationship.relationship_type,
      cardinality_ratio: relationship.cardinality_ratio || '1:N',
      metadata: relationship.metadata || {}
    });
    setEditingRelationship(relationship.id);
    setShowAddRelationship(true);
  };

  // Save edited relationship
  const saveEditedRelationship = () => {
    if (!schema || !editingRelationship) return;
    
    setSchema(prev => prev ? {
      ...prev,
      relationships: prev.relationships.map(rel =>
        rel.id === editingRelationship
          ? {
              ...rel,
              name: newRelationship.name || rel.name,
              description: newRelationship.description,
              source_columns: newRelationship.source_columns,
              target_columns: newRelationship.target_columns,
              relationship_type: newRelationship.relationship_type,
              cardinality_ratio: newRelationship.cardinality_ratio,
              join_sql: generateJoinSQL(),
              metadata: {
                ...rel.metadata,
                relationship_synonyms: newRelationship.metadata?.relationship_synonyms || []
              }
            }
          : rel
      )
    } : prev);
    
    setShowAddRelationship(false);
    setEditingRelationship(null);
    resetNewRelationship();
    showToast('Relationship updated successfully', 'success');
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader />
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <p className="text-gray-500 mb-4">No semantic schema found</p>
          <button
            onClick={loadSemanticSchema}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Compact View Component
  const CompactView = () => (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Database Schema Overview</h3>
          <p className="text-sm text-gray-500 mt-1">
            Review and customize your database schema ({Object.keys(schema?.tables || {}).length} tables found)
          </p>
        </div>
        <button
          onClick={() => setIsExpanded(true)}
          className="flex items-center px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          <Maximize2 className="w-4 h-4 mr-2" />
          Expand Editor
        </button>
      </div>

      {/* Table Grid Preview */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {Object.values(schema?.tables || {}).slice(0, 6).map((table: any) => (
          <div
            key={table.id}
            className={`rounded-lg border p-4 hover:shadow-md cursor-pointer transition-all ${
              selectedTables.has(table.id) 
                ? 'bg-blue-50 border-blue-300 ring-2 ring-blue-100' 
                : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
            }`}
            onClick={() => {
              handleTableSelection(table.id, !selectedTables.has(table.id));
              setIsExpanded(true);
            }}
          >
            <div className="flex items-center mb-2">
              <div className={`w-3 h-3 rounded mr-2 ${
                selectedTables.has(table.id) ? 'bg-blue-500' : 'bg-gray-400'
              }`}></div>
              <span className="font-medium text-gray-900 text-sm">{table.display_name}</span>
            </div>
            <p className="text-xs text-gray-500 mb-2">{table.name}</p>
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-600">{table.columns.length} columns</p>
              {selectedTables.has(table.id) && (
                <Check className="w-4 h-4 text-blue-500" />
              )}
            </div>

          </div>
        ))}
        {(Object.keys(schema?.tables || {}).length || 0) > 6 && (
          <div 
            className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-300 p-4 flex items-center justify-center cursor-pointer hover:bg-gray-100"
            onClick={() => setIsExpanded(true)}
          >
            <div className="text-center">
              <Plus className="w-6 h-6 text-gray-400 mx-auto mb-1" />
              <p className="text-xs text-gray-500">+{(Object.keys(schema?.tables || {}).length || 0) - 6} more tables</p>
            </div>
          </div>
        )}
      </div>



      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center">
          <div className="text-2xl font-bold text-blue-600">{Object.keys(schema?.tables || {}).length}</div>
          <div className="text-xs text-gray-500">Tables</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-green-600">{schema?.relationships.length}</div>
          <div className="text-xs text-gray-500">Relationships</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-600">
            {Object.values(schema?.tables || {}).reduce((sum: number, table: any) => sum + Object.keys(table.columns || {}).length, 0)}
          </div>
          <div className="text-xs text-gray-500">Columns</div>
        </div>
      </div>
    </div>
  );

  // Expanded View Component
  const ExpandedView = () => (
    <div className="fixed inset-0 m-0 bg-gray-50 z-[9999] flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-semibold text-gray-900">Semantic Model</h1>
            <p className="text-sm text-gray-500 mt-1">
              Explore and select tables for your chatbot's knowledge base
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleExportSchema}
              disabled={isExporting}
              className="flex items-center justify-center px-6 py-2.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 min-w-[140px] disabled:opacity-50"
            >
              {isExporting ? (
                <Loader />
              ) : (
                <Download className="w-4 h-4 mr-2 text-blue-600" />
              )}
              <span className="text-blue-600 font-medium">
                {isExporting ? 'Exporting...' : 'Export Schema'}
              </span>
            </button>
            <button
              onClick={() => document.getElementById('import-schema-input')?.click()}
              disabled={isImporting}
              className="flex items-center justify-center px-6 py-2.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 min-w-[140px] disabled:opacity-50"
            >
              {isImporting ? (
                <Loader />
              ) : (
                <Upload className="w-4 h-4 mr-2 text-green-600" />
              )}
              <span className="text-green-600 font-medium">
                {isImporting ? 'Importing...' : 'Import Schema'}
              </span>
            </button>
            <button
              onClick={handleRefreshSchema}
              className="flex items-center justify-center px-6 py-2.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 min-w-[140px]"
              disabled={loading}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Schema
            </button>
            <button
              onClick={() => setShowMetricsDialog(true)}
              className="flex items-center justify-center px-6 py-2.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 min-w-[140px]"
            >
              <Calculator className="w-4 h-4 mr-2 text-green-600" />
              <span className="text-green-600 font-medium">Metrics</span>
            </button>
            <button
              onClick={() => setShowUserPreferencesDialog(true)}
              className="flex items-center justify-center px-6 py-2.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 min-w-[140px]"
            >
              <Edit3 className="w-4 h-4 mr-2 text-blue-600" />
              <span className="text-blue-600 font-medium">AI Preferences</span>
            </button>
            <button
              onClick={() => {
                console.log('🔍 Save Changes button clicked!');
                console.log('Button disabled?', saving);
                handleSaveSchema();
              }}
              disabled={saving}
              className="flex items-center justify-center px-6 py-2.5 border border-gray-300 text-gray-700 text-sm rounded-lg hover:bg-gray-50 disabled:opacity-50 min-w-[140px]"
            >
              {saving ? <Loader /> : <Check className="w-4 h-4 mr-2" />}
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            {!isEditMode && (
              <button
                onClick={handleConfirmAndContinue}
                disabled={saving}
                className="flex items-center justify-center px-6 py-2.5 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50 min-w-[160px]"
              >
                <Check className="w-4 h-4 mr-2" />
                Confirm & Continue
              </button>
            )}
            <button
              onClick={() => setIsExpanded(false)}
              className="flex items-center justify-center px-6 py-2.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 min-w-[100px]"
            >
              <Minimize2 className="w-4 h-4 mr-2" />
              Minimize
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel - Table List */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col overflow-hidden">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Visualize and Explore Your Database</h3>
            <p className="text-xs text-gray-500 mb-4">
              Select tables and columns to include in your chatbot's knowledge base
            </p>
            
            {/* Search */}
            <LeftSearchInput
              defaultValue={searchTerm}
              onCommit={(val) => setSearchTerm(val)}
            />

            {/* Controls */}
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleSelectAll}
                  className="text-blue-600 hover:text-blue-700"
                >
                  Select All
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={handleClearSelection}
                  className="text-blue-600 hover:text-blue-700"
                >
                  Clear Selection
                </button>
              </div>
              <span className="text-gray-500">
                {selectedTables.size} tables selected
              </span>
            </div>
          </div>



          {/* Table List */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-2">
              <h4 className="text-xs font-medium text-gray-600 mb-2 px-2">Table List</h4>
              {filteredTables.map((table) => (
                <div
                  key={table.id}
                  className={`flex items-center p-2 rounded-lg cursor-pointer hover:bg-gray-50 ${
                    selectedTable?.id === table.id ? 'bg-blue-50 border border-blue-200' : ''
                  }`}
                  onClick={() => handleTableClick(table)}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTableSelection(table.id, !selectedTables.has(table.id));
                    }}
                    className="mr-3"
                  >
                    {selectedTables.has(table.id) ? (
                      <Check className="w-4 h-4 text-blue-600" />
                    ) : (
                      <Square className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {table.display_name}
                    </p>
                    <p className="text-xs text-gray-500 truncate">
                      {table.name} • {Object.keys(table.columns || {}).length} columns
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Center Panel - Visual Diagram using React Flow */}
        <div className="flex-1 min-h-0 relative">
          {/* Right Panel Toggle Button */}
          <button
            onClick={() => setIsRightPanelOpen(!isRightPanelOpen)}
            className={`absolute right-2 top-2 z-10 p-2 rounded-lg shadow-lg transition-all duration-200 ${
              isRightPanelOpen 
                ? 'bg-gray-100 hover:bg-gray-200 text-gray-700' 
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
            title={isRightPanelOpen ? 'Minimize right panel' : 'Maximize right panel'}
          >
            {isRightPanelOpen ? (
              <Minimize2 className="w-4 h-4" />
            ) : (
              <Maximize2 className="w-4 h-4" />
            )}
          </button>
          
          {/* Selected Table Indicator when Right Panel is Closed */}
          {selectedTable && !isRightPanelOpen && (
            <div className="absolute right-16 top-2 z-10 bg-blue-100 border border-blue-300 rounded-lg px-3 py-1 text-xs text-blue-700">
              {selectedTable.display_name} selected
            </div>
          )}
          
          <div className="h-full">
            {getSelectedTablesArray.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center text-gray-500">
                  <div className="w-16 h-16 bg-gray-200 rounded-lg flex items-center justify-center mx-auto mb-4">
                    <div className="w-8 h-8 border-2 border-dashed border-gray-400 rounded"></div>
                  </div>
                  <p className="text-sm">Select tables from the left panel</p>
                  <p className="text-xs text-gray-400 mt-1">to view their ER diagram</p>
                </div>
              </div>
            ) : (
              <ERDiagram
                tables={getSelectedTablesArray}
                relationships={getRelationshipsBetweenSelectedTables}
                onNodeSelect={(id: string) => {
                  const t = (Object.values(schema?.tables || {}) as any[]).find(x => x.id === id) || null;
                  if (t) { 
                    setSelectedTable(t); 
                    setActiveTab('details'); 
                    setIsRightPanelOpen(true); // Open right panel when node is selected
                  }
                }}
                onEdgeSelect={(rel: any) => {
                  // Check if this is a new relationship being created (temporary ID)
                  if (rel.id && rel.id.startsWith('rel_')) {
                    // This is a new relationship - show the creation dialog
                    setNewRelationship({
                      name: '',
                      description: '',
                      source_table_id: rel.source_table_id,
                      source_columns: [],
                      target_table_id: rel.target_table_id,
                      target_columns: [],
                      relationship_type: 'one_to_many',
                      cardinality_ratio: '1:N',
                      metadata: {}
                    });
                    setShowAddRelationship(true);
                  } else {
                    // This is an existing relationship - show details in right panel
                    setRelationshipFilter({ a: rel.source_table_id, b: rel.target_table_id });
                    setActiveTab('relationships');
                    const src = (Object.values(schema?.tables || {}) as any[]).find(t => t.id === rel.source_table_id) || null;
                    setSelectedTable(src);
                    setIsRightPanelOpen(true); // Open right panel when edge is selected
                  }
                }}
                onShowColumns={(tableId: string) => {
                  const t = (Object.values(schema?.tables || {}) as any[]).find(x => x.id === tableId) || null;
                  if (t) { 
                    setSelectedTable(t); 
                    setActiveTab('columns'); 
                    setIsRightPanelOpen(true); // Open right panel when columns are shown
                  }
                }}
              />
            )}
          </div>
        </div>

        {/* Right Panel - Table Inspector */}
        <div className={`${isRightPanelOpen ? 'w-96' : 'w-0'} bg-white border-l border-gray-200 flex flex-col overflow-hidden transition-all duration-300 ease-in-out`}>
          {selectedTable && isRightPanelOpen ? (
            <>
              {/* Inspector Header */}
              <div className="p-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="w-6 h-6 bg-blue-500 rounded mr-3"></div>
                    <div>
                      <h3 className="font-medium text-gray-900">{selectedTable.display_name}</h3>
                      <p className="text-xs text-gray-500">{selectedTable.name}</p>
                    </div>
                  </div>
                  
                  {/* Navigation for multiple selected tables */}
                  {getSelectedTablesArray.length > 1 && (
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => navigateInspector('prev')}
                        className="p-1 hover:bg-gray-100 rounded"
                        title="Previous table"
                      >
                        <ChevronRight className="w-4 h-4 rotate-180 text-gray-500" />
                      </button>
                      <span className="text-xs text-gray-500 px-2">
                        {currentInspectorIndex + 1} of {getSelectedTablesArray.length}
                      </span>
                      <button
                        onClick={() => navigateInspector('next')}
                        className="p-1 hover:bg-gray-100 rounded"
                        title="Next table"
                      >
                        <ChevronRight className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                  )}
                </div>
                
                {/* Selected tables indicator */}
                {getSelectedTablesArray.length > 1 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {getSelectedTablesArray.map((table, index) => (
                      <button
                        key={table.id}
                        onClick={() => {
                          setCurrentInspectorIndex(index);
                          setSelectedTable(table);
                          setIsRightPanelOpen(true); // Ensure right panel stays open
                        }}
                        className={`text-xs px-2 py-1 rounded ${
                          table.id === selectedTable.id 
                            ? 'bg-blue-100 text-blue-700 border border-blue-300'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {table.display_name}
                      </button>
                    ))}
                  </div>
                )}
              </div>

                            {/* Tabs */}
              <div className="border-b border-gray-200">
                <div className="flex">
                  {['details', 'columns', 'relationships'].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab as any)}
                      className={`px-4 py-3 text-sm font-medium capitalize ${
                        activeTab === tab
                          ? 'text-blue-600 border-b-2 border-blue-600'
                          : 'text-gray-500 hover:text-gray-700'
                        }`}
                    >
                      {tab}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tab Content */}
              <div ref={inspectorScrollRef} className="flex-1 overflow-y-auto p-4" data-inspector-scroll>
                {activeTab === 'details' && (
                  <TableDetailsEditor
                    table={selectedTable}
                    onFieldChange={(field, value) => updateTableField(selectedTable.id, field, value)}
                  />
                )}

                {activeTab === 'columns' && (
                  <div className="space-y-3">
                    {Object.values(selectedTable.columns).map((column) => (
                      <div id={`col-${column.id}`} key={column.id}>
                        <ColumnEditor
                          column={column}
                          isEditing={editingColumn === column.id}
                          onEdit={() => handleStartEditColumn(column.id)}
                          onSave={() => setEditingColumn(null)}
                          onCancel={() => setEditingColumn(null)}
                          onFieldChange={(field, value) => updateColumnField(selectedTable.id, column.id, field, value)}
                        />
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'relationships' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-medium text-gray-700">Table Relationships</h4>
                      <button
                        onClick={() => setShowAddRelationship(true)}
                        className="flex items-center px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                      >
                        <Plus className="w-3 h-3 mr-1" />
                        Add
                      </button>
                    </div>

                    {schema.relationships
                      .filter(rel => {
                        const belongsToTable = rel.source_table_id === selectedTable.id || rel.target_table_id === selectedTable.id;
                        if (!belongsToTable) return false;
                        if (!relationshipFilter) return true;
                        const pairA = relationshipFilter.a;
                        const pairB = relationshipFilter.b;
                        const matchPair = (rel.source_table_id === pairA && rel.target_table_id === pairB)
                          || (rel.source_table_id === pairB && rel.target_table_id === pairA);
                        return matchPair;
                      })
                      .map((rel) => {
                        const isUserCreated = isUserCreatedRelationship(rel);
                        return (
                          <div key={rel.id} className={`border rounded-lg p-3 ${
                            isUserCreated ? 'border-blue-300 bg-blue-50' : 'border-gray-200 bg-gray-50'
                          }`}>
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center space-x-2">
                                <span className="text-sm font-medium text-gray-900">{rel.name}</span>
                                {isUserCreated && (
                                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                                    User Created
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center space-x-2">
                                <span className="text-xs text-gray-500">{rel.relationship_type}</span>
                                                                 {isUserCreated && (
                                   <>
                                     <button
                                       onClick={() => startEditRelationship(rel)}
                                       className="p-1.5 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
                                       title="Edit relationship"
                                     >
                                       <Edit3 className="w-3.5 h-3.5" />
                                     </button>
                                     <button
                                       onClick={() => deleteRelationship(rel.id)}
                                       className="p-1.5 text-red-600 hover:text-red-800 hover:bg-red-100 rounded transition-colors"
                                       title="Delete relationship"
                                     >
                                       <Trash2 className="w-3.5 h-3.5" />
                                     </button>
                                   </>
                                 )}
                              </div>
                            </div>
                            <p className="text-xs text-gray-600 mb-2">
                              {getTableName(rel.source_table_id)} → {getTableName(rel.target_table_id)}
                            </p>
                            <div className="text-xs text-gray-500">
                              <p><strong>Cardinality:</strong> {rel.cardinality_ratio}</p>
                              <p><strong>Confidence:</strong> {(rel.confidence_score * 100).toFixed(0)}%</p>
                              {rel.join_sql && (
                                <div className="mt-2">
                                  <p><strong>Join SQL:</strong></p>
                                  <code className="text-xs bg-gray-100 p-1 rounded">{rel.join_sql}</code>
                                </div>
                              )}
                              {/* Relationship synonyms editor - always editable; store in metadata.relationship_synonyms */}
                              <div className="mt-3">
                                <SynonymsTagInput
                                  label="Relationship Synonyms"
                                  values={((rel.metadata && (rel.metadata as any).relationship_synonyms) || []).map((s: any) => (
                                    typeof s === 'string' ? { synonym: s, sample_values: [] } : s
                                  ))}
                                  onChange={(vals) => {
                                    // Only allow editing synonyms for non-user relationships; keep other fields read-only
                                    if (!isUserCreated)
                                      setSchema(prev => prev ? {
                                        ...prev,
                                        relationships: prev.relationships.map(r => r.id === rel.id ? { ...r, metadata: { ...(r.metadata || {}), relationship_synonyms: vals.map(v => v.synonym) } } : r)
                                      } : prev);
                                    else
                                      setSchema(prev => prev ? {
                                        ...prev,
                                        relationships: prev.relationships.map(r => r.id === rel.id ? { ...r, metadata: { ...(r.metadata || {}), relationship_synonyms: vals.map(v => v.synonym) } } : r)
                                      } : prev);
                                  }}
                                  showSamples={false}
                                />
                              </div>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            </>
          ) : isRightPanelOpen ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-500">
                <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                  <div className="w-8 h-8 border-2 border-dashed border-gray-300 rounded"></div>
                </div>
                <p className="text-sm">Select a table to view details</p>
                <p className="text-xs text-gray-400 mt-1">
                  Or drag between columns to create relationships
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {/* Add Relationship Modal */}
      {showAddRelationship && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
          <div className="bg-white rounded-lg p-6 w-96">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium">
                {editingRelationship ? 'Edit Relationship' : 'Add New Relationship'}
              </h3>
              <button
                onClick={() => {
                  setShowAddRelationship(false);
                  setEditingRelationship(null);
                  resetNewRelationship();
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Source Table</label>
                  <select
                    value={newRelationship.source_table_id}
                    onChange={(e) => setNewRelationship({...newRelationship, source_table_id: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                  >
                    <option value="">Select table</option>
                    {Object.values(schema.tables).map(table => (
                      <option key={table.id} value={table.id}>{table.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Source Column</label>
                  <select
                    value={newRelationship.source_columns[0] || ''}
                    onChange={(e) => setNewRelationship({...newRelationship, source_columns: [e.target.value]})}
                    className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                    disabled={!newRelationship.source_table_id}
                  >
                    <option value="">Select column</option>
                    {(() => {
                      const src = (Object.values(schema.tables || {}) as any[]).find((t: any) => t.id === newRelationship.source_table_id);
                      const cols = Object.values((src?.columns || {})) as any[];
                      return cols.map((col: any) => (
                        <option key={col.id} value={col.name}>{col.name}</option>
                      ));
                    })()}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target Table</label>
                  <select
                    value={newRelationship.target_table_id}
                    onChange={(e) => setNewRelationship({...newRelationship, target_table_id: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                  >
                    <option value="">Select table</option>
                    {Object.values(schema.tables).map(table => (
                      <option key={table.id} value={table.id}>{table.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target Column</label>
                  <select
                    value={newRelationship.target_columns[0] || ''}
                    onChange={(e) => setNewRelationship({...newRelationship, target_columns: [e.target.value]})}
                    className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                    disabled={!newRelationship.target_table_id}
                  >
                    <option value="">Select column</option>
                    {(() => {
                      const tgt = (Object.values(schema.tables || {}) as any[]).find((t: any) => t.id === newRelationship.target_table_id);
                      const cols = Object.values((tgt?.columns || {})) as any[];
                      return cols.map((col: any) => (
                        <option key={col.id} value={col.name}>{col.name}</option>
                      ));
                    })()}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Relationship Name</label>
                <input
                  type="text"
                  defaultValue={newRelationship.name}
                  onBlur={(e) => setNewRelationship({...newRelationship, name: e.target.value})}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      (e.target as HTMLInputElement).blur();
                    }
                  }}
                  placeholder="Enter relationship name"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Relationship Description</label>
                <textarea
                  defaultValue={newRelationship.description}
                  onBlur={(e) => setNewRelationship({...newRelationship, description: e.target.value})}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      (e.target as HTMLTextAreaElement).blur();
                    }
                  }}
                  placeholder="Enter relationship description (optional)"
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Relationship Type</label>
                <select
                  value={newRelationship.relationship_type}
                  onChange={(e) => setNewRelationship({
                    ...newRelationship, 
                    relationship_type: e.target.value,
                    cardinality_ratio: e.target.value === 'one_to_many' ? '1:N' : e.target.value === 'many_to_one' ? 'N:1' : '1:1'
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                >
                  <option value="one_to_many">One to Many (1:N)</option>
                  <option value="many_to_one">Many to One (N:1)</option>
                  <option value="one_to_one">One to One (1:1)</option>
                  <option value="many_to_many">Many to Many (N:N)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Relationship Synonyms</label>
                <input
                  type="text"
                  defaultValue={newRelationship.metadata?.relationship_synonyms?.join(', ') || ''}
                  onBlur={(e) => {
                    const synonyms = e.target.value.split(',').map(s => s.trim()).filter(s => s);
                    setNewRelationship({
                      ...newRelationship, 
                      metadata: { 
                        ...newRelationship.metadata, 
                        relationship_synonyms: synonyms 
                      }
                    });
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      (e.target as HTMLInputElement).blur();
                    }
                  }}
                  placeholder="Enter relationship synonyms separated by commas (e.g., connects, links, relates)"
                  className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

                         <div className="flex justify-end space-x-3 mt-6">
               <button
                 onClick={() => {
                   setShowAddRelationship(false);
                   setEditingRelationship(null);
                   resetNewRelationship();
                 }}
                 className="flex items-center justify-center px-6 py-2.5 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 min-w-[100px]"
               >
                 Cancel
               </button>
               <button
                 onClick={editingRelationship ? saveEditedRelationship : addNewRelationship}
                 disabled={!newRelationship.source_table_id || !newRelationship.target_table_id}
                 className="flex items-center justify-center px-6 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 min-w-[160px]"
               >
                 {editingRelationship ? 'Update Relationship' : 'Create Relationship'}
               </button>
             </div>
          </div>
        </div>
      )}

      {/* Metrics Management Dialog */}
      {showMetricsDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000]">
          <div className="bg-white rounded-lg w-4/5 h-4/5 max-w-6xl max-h-[800px] flex flex-col shadow-2xl">
            {/* Dialog Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gray-50 bg-opacity-80">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                  <Calculator className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-gray-900">Business Metrics Management</h3>
                  <p className="text-gray-600 mt-1">Manage database and table-level metrics</p>
                </div>
              </div>
              <button
                onClick={() => setShowMetricsDialog(false)}
                className="text-gray-400 hover:text-gray-600 p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Dialog Content */}
            <div className="flex-1 overflow-hidden flex">
              {/* Left Panel - Database Metrics */}
              <div className="w-1/2 border-r border-gray-200 p-6 overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
                      <Calculator className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-gray-900">Global Metrics</h4>
                      <p className="text-sm text-gray-600">Global database-level metrics</p>
                    </div>
                  </div>
                  <div className="bg-blue-100 text-blue-800 px-4 py-2 rounded-full text-sm font-semibold">
                    {(() => {
                      const dbMetrics = (schema?.metadata && (schema?.metadata as any).database_metric_items) || [];
                      return `${dbMetrics.length} metrics`;
                    })()}
                  </div>
                </div>

                {(() => {
                  type DatabaseMetricItem = { name: string; value: string };
                  const dbMetrics: DatabaseMetricItem[] = (schema?.metadata && (schema?.metadata as any).database_metric_items) || [];

                  const [localDbMetrics, setLocalDbMetrics] = useState<DatabaseMetricItem[]>(dbMetrics);
                  const [newDbMetricName, setNewDbMetricName] = useState<string>("");
                  const [newDbMetricValue, setNewDbMetricValue] = useState<string>("");
                  const [editingDbMetric, setEditingDbMetric] = useState<number | null>(null);
                  const [editDbMetricName, setEditDbMetricName] = useState<string>("");
                  const [editDbMetricValue, setEditDbMetricValue] = useState<string>("");

                  useEffect(() => {
                    setLocalDbMetrics(dbMetrics);
                  }, [schema?.metadata]);

                  const commitDbMetrics = (updated: DatabaseMetricItem[]) => {
                    console.log('🔍 COMMIT DB METRICS: Updating metrics:', updated);
                    setLocalDbMetrics(updated);
                    setSchema(prev => {
                      if (!prev) return prev;
                      const newSchema = {
                        ...prev,
                        metadata: { ...(prev.metadata || {}), database_metric_items: updated },
                        metrics: updated.map(m => m.name)
                      };
                      console.log('🔍 COMMIT DB METRICS: New schema metadata:', newSchema.metadata);
                      console.log('🔍 COMMIT DB METRICS: New schema metrics:', newSchema.metrics);
                      return newSchema;
                    });
                  };

                  const addDbMetric = () => {
                    const name = newDbMetricName.trim();
                    const value = newDbMetricValue.trim();
                    if (!name || !value) return;
                    if (localDbMetrics.some(m => m.name.toLowerCase() === name.toLowerCase())) return;
                    const updated = [...localDbMetrics, { name, value }];
                    setNewDbMetricName("");
                    setNewDbMetricValue("");
                    commitDbMetrics(updated);
                  };

                  const removeDbMetric = (idx: number) => {
                    const updated = localDbMetrics.filter((_, i) => i !== idx);
                    commitDbMetrics(updated);
                  };

                  const startEditDbMetric = (idx: number) => {
                    const metric = localDbMetrics[idx];
                    setEditDbMetricName(metric.name);
                    setEditDbMetricValue(metric.value);
                    setEditingDbMetric(idx);
                  };

                  const saveEditDbMetric = () => {
                    if (editingDbMetric === null) return;
                    const name = editDbMetricName.trim();
                    const value = editDbMetricValue.trim();
                    if (!name || !value) return;
                    
                    const updated = localDbMetrics.map((m, i) => 
                      i === editingDbMetric ? { name, value } : m
                    );
                    commitDbMetrics(updated);
                    setEditingDbMetric(null);
                    setEditDbMetricName("");
                    setEditDbMetricValue("");
                  };

                  const cancelEditDbMetric = () => {
                    setEditingDbMetric(null);
                    setEditDbMetricName("");
                    setEditDbMetricValue("");
                  };

                  return (
                    <div className="space-y-4">
                      {/* Add New Database Metric */}
                      <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                        <h5 className="text-sm font-medium text-gray-700 mb-3">Add New Database Metric</h5>
                        <div className="grid grid-cols-2 gap-3">
                          <input
                            type="text"
                            value={newDbMetricName}
                            onChange={(e) => setNewDbMetricName(e.target.value)}
                            placeholder="Metric name"
                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          />
                          <input
                            type="text"
                            value={newDbMetricValue}
                            onChange={(e) => setNewDbMetricValue(e.target.value)}
                            placeholder="Metric value"
                            className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          />
                        </div>
                        {newDbMetricName.trim() !== '' && newDbMetricValue.trim() !== '' && (
                          <div className="flex justify-end mt-3">
                            <button
                              onClick={addDbMetric}
                              className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                              Add Database Metric
                            </button>
                          </div>
                        )}
                      </div>

                      {/* Database Metrics List */}
                      {localDbMetrics.length > 0 && (
                        <div className="space-y-3">
                          <h5 className="text-sm font-medium text-gray-700">Current Database Metrics</h5>
                          {localDbMetrics.map((m, idx) => (
                            <div key={`db-${m.name}-${idx}`} className="border border-gray-200 rounded-lg p-3">
                              {editingDbMetric === idx ? (
                                // Edit mode
                                <div className="space-y-2">
                                  <div className="grid grid-cols-2 gap-2">
                                    <input
                                      type="text"
                                      value={editDbMetricName}
                                      onChange={(e) => setEditDbMetricName(e.target.value)}
                                      placeholder="Metric name"
                                      className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                                    />
                                    <input
                                      type="text"
                                      value={editDbMetricValue}
                                      onChange={(e) => setEditDbMetricValue(e.target.value)}
                                      placeholder="Metric value"
                                      className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                                    />
                                  </div>
                                  <div className="flex items-center justify-end space-x-2">
                                    <button
                                      onClick={cancelEditDbMetric}
                                      className="px-2 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                                    >
                                      Cancel
                                    </button>
                                    <button
                                      onClick={saveEditDbMetric}
                                      disabled={!editDbMetricName.trim() || !editDbMetricValue.trim()}
                                      className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                    >
                                      Save
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                // Display mode
                                <>
                                  <div className="flex items-center justify-between mb-2">
                                    <span className="text-sm font-medium text-gray-900">{m.name}</span>
                                    <div className="flex items-center space-x-2">
                                      <button
                                        onClick={() => startEditDbMetric(idx)}
                                        className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
                                        title="Edit metric"
                                      >
                                        <Edit className="w-3 h-3" />
                                      </button>
                                      <button
                                        onClick={() => removeDbMetric(idx)}
                                        className="p-1 text-red-600 hover:text-red-800 hover:bg-red-100 rounded transition-colors"
                                        title="Delete metric"
                                      >
                                        <Trash className="w-3 h-3" />
                                      </button>
                                    </div>
                                  </div>
                                  <div className="text-sm text-gray-600">
                                    <strong>Value:</strong> {m.value}
                                  </div>
                                </>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })()}
              </div>

              {/* Right Panel - Table Metrics */}
              <div className="w-1/2 p-6 overflow-y-auto">
                <div className="flex items-center justify-between mb-6">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                      <Calculator className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h4 className="text-xl font-bold text-gray-900">Table Metrics</h4>
                      <p className="text-sm text-gray-600">Per-table metrics</p>
                    </div>
                  </div>
                  <div className="bg-green-100 text-green-800 px-4 py-2 rounded-full text-sm font-semibold">
                    {(() => {
                      const tableArray = Object.values(schema?.tables || {}) as any[];
                      const totalTableMetrics = tableArray.reduce((sum: number, table: any) => {
                        const tableMetrics = (table.metadata && (table.metadata as any).metric_items) || [];
                        return sum + tableMetrics.length;
                      }, 0);
                      return `${totalTableMetrics} metrics across ${tableArray.length} tables`;
                    })()}
                  </div>
                </div>

                {/* Add New Table Metric */}
                <div className="bg-gray-50 rounded-lg p-4 mb-6">
                  <h5 className="text-sm font-medium text-gray-700 mb-3">Add New Table Metric</h5>
                  {(() => {
                    const [selectedTableId, setSelectedTableId] = useState<string>("");
                    const [tableSearchTerm, setTableSearchTerm] = useState<string>("");
                    const [newTableMetricName, setNewTableMetricName] = useState<string>("");
                    const [newTableMetricValue, setNewTableMetricValue] = useState<string>("");
                    const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);

                    const filteredTables = (Object.values(schema?.tables || {}) as any[]).filter((table: any) =>
                      table.name.toLowerCase().includes(tableSearchTerm.toLowerCase()) ||
                      table.display_name.toLowerCase().includes(tableSearchTerm.toLowerCase())
                    );

                    const addTableMetric = () => {
                      if (!selectedTableId || !newTableMetricName.trim() || !newTableMetricValue.trim()) return;
                      
                      const selectedTable = (Object.values(schema?.tables || {}) as any[]).find((t: any) => t.id === selectedTableId);
                      if (!selectedTable) return;

                      const currentMetrics = (selectedTable.metadata && (selectedTable.metadata as any).metric_items) || [];
                      const newMetric = { name: newTableMetricName.trim(), value: newTableMetricValue.trim() };
                      
                      // Check for duplicate metric names
                      if (currentMetrics.some((m: any) => m.name.toLowerCase() === newMetric.name.toLowerCase())) return;

                      const updatedMetrics = [...currentMetrics, newMetric];
                      updateTableField(selectedTableId, 'metadata', { ...(selectedTable.metadata || {}), metric_items: updatedMetrics });
                      updateTableField(selectedTableId, 'metrics', updatedMetrics.map((m: any) => m.name));

                      // Reset form
                      setSelectedTableId("");
                      setNewTableMetricName("");
                      setNewTableMetricValue("");
                      setTableSearchTerm("");
                    };

                    return (
                      <div className="space-y-3">
                        {/* Table Selection Dropdown with Search */}
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-2">Select Table</label>
                          <div className="relative">
                            <input
                              type="text"
                              value={tableSearchTerm}
                              onChange={(e) => setTableSearchTerm(e.target.value)}
                              onFocus={() => {
                                setIsDropdownOpen(true);
                                setTableSearchTerm("");
                              }}
                              onBlur={() => setTimeout(() => setIsDropdownOpen(false), 150)}
                              placeholder="Search tables..."
                              className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                            {isDropdownOpen && (
                              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                                {filteredTables.map((table) => (
                                  <button
                                    key={table.id}
                                    onClick={() => {
                                      setSelectedTableId(table.id);
                                      setTableSearchTerm(table.display_name || table.name);
                                      setIsDropdownOpen(false);
                                    }}
                                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 border-b border-gray-100 last:border-b-0"
                                  >
                                    <div className="font-medium text-gray-900">{table.display_name || table.name}</div>
                                    <div className="text-xs text-gray-500">{table.name} • {table.columns.length} columns</div>
                                  </button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Metric Input Fields */}
                        {selectedTableId && (
                          <div className="grid grid-cols-2 gap-3">
                            <input
                              type="text"
                              value={newTableMetricName}
                              onChange={(e) => setNewTableMetricName(e.target.value)}
                              placeholder="Metric name"
                              className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                            <input
                              type="text"
                              value={newTableMetricValue}
                              onChange={(e) => setNewTableMetricValue(e.target.value)}
                              placeholder="Metric value"
                              className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            />
                          </div>
                        )}

                        {/* Add Button */}
                        {selectedTableId && newTableMetricName.trim() && newTableMetricValue.trim() && (
                          <div className="flex justify-end">
                            <button
                              onClick={addTableMetric}
                              className="px-4 py-2 text-sm bg-green-600 text-white rounded hover:bg-green-700"
                            >
                              Add Table Metric
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>

                {/* Existing Table Metrics */}
                <div className="space-y-4">
                  {Object.values(schema?.tables || {}).map((table) => {
                    const tableMetrics = (table.metadata && (table.metadata as any).metric_items) || [];
                    if (tableMetrics.length === 0) return null;

                    return (
                      <div key={table.id} className="border border-gray-200 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <h5 className="text-sm font-medium text-gray-900">{table.display_name}</h5>
                          <span className="text-xs text-gray-500">{tableMetrics.length} metrics</span>
                        </div>
                        
                        <div className="space-y-2">
                          {tableMetrics.map((metric: any, idx: number) => (
                            <div key={`${table.id}-${metric.name}-${idx}`} className="bg-gray-50 rounded p-2">
                              {(() => {
                                const [editingTableMetric, setEditingTableMetric] = useState<{tableId: string, metricIdx: number} | null>(null);
                                const [editTableMetricName, setEditTableMetricName] = useState<string>("");
                                const [editTableMetricValue, setEditTableMetricValue] = useState<string>("");

                                const startEditTableMetric = () => {
                                  setEditTableMetricName(metric.name);
                                  setEditTableMetricValue(metric.value);
                                  setEditingTableMetric({ tableId: table.id, metricIdx: idx });
                                };

                                const saveEditTableMetric = () => {
                                  if (editingTableMetric === null) return;
                                  const name = editTableMetricName.trim();
                                  const value = editTableMetricValue.trim();
                                  if (!name || !value) return;
                                  
                                  const updatedMetrics = tableMetrics.map((m: any, i: number) => 
                                    i === idx ? { name, value } : m
                                  );
                                  updateTableField(table.id, 'metadata', { ...(table.metadata || {}), metric_items: updatedMetrics });
                                  updateTableField(table.id, 'metrics', updatedMetrics.map((m: any) => m.name));
                                  setEditingTableMetric(null);
                                  setEditTableMetricName("");
                                  setEditTableMetricValue("");
                                };

                                const cancelEditTableMetric = () => {
                                  setEditingTableMetric(null);
                                  setEditTableMetricName("");
                                  setEditTableMetricValue("");
                                };

                                return editingTableMetric?.tableId === table.id && editingTableMetric?.metricIdx === idx ? (
                                  // Edit mode
                                  <div className="space-y-2">
                                    <div className="grid grid-cols-2 gap-2">
                                      <input
                                        type="text"
                                        value={editTableMetricName}
                                        onChange={(e) => setEditTableMetricName(e.target.value)}
                                        placeholder="Metric name"
                                        className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                                      />
                                      <input
                                        type="text"
                                        value={editTableMetricValue}
                                        onChange={(e) => setEditTableMetricValue(e.target.value)}
                                        placeholder="Metric value"
                                        className="w-full px-2 py-1 text-xs border border-gray-300 rounded focus:ring-1 focus:ring-blue-500 focus:border-transparent"
                                      />
                                    </div>
                                    <div className="flex items-center justify-end space-x-2">
                                      <button
                                        onClick={cancelEditTableMetric}
                                        className="px-2 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                                      >
                                        Cancel
                                      </button>
                                      <button
                                        onClick={saveEditTableMetric}
                                        disabled={!editTableMetricName.trim() || !editTableMetricValue.trim()}
                                        className="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                                      >
                                        Save
                                      </button>
                                    </div>
                                  </div>
                                ) : (
                                  // Display mode
                                  <div className="flex items-center justify-between">
                                    <div className="text-sm">
                                      <span className="font-medium text-gray-700">{metric.name}:</span>
                                      <span className="text-gray-600 ml-2">{metric.value}</span>
                                    </div>
                                    <div className="flex items-center space-x-1">
                                      <button
                                        onClick={startEditTableMetric}
                                        className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-100 rounded transition-colors"
                                        title="Edit metric"
                                      >
                                        <Edit className="w-3 h-3" />
                                      </button>
                                      <button
                                        onClick={() => {
                                          // Remove table metric
                                          const updatedMetrics = tableMetrics.filter((_: any, i: number) => i !== idx);
                                          updateTableField(table.id, 'metadata', { ...(table.metadata || {}), metric_items: updatedMetrics });
                                          updateTableField(table.id, 'metrics', updatedMetrics.map((m: any) => m.name));
                                        }}
                                        className="p-1 text-red-600 hover:text-red-800 hover:bg-red-100 rounded transition-colors"
                                        title="Delete metric"
                                      >
                                        <Trash className="w-3 h-3" />
                                      </button>
                                    </div>
                                  </div>
                                );
                              })()}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Dialog Footer */}
            <div className="p-6 border-t border-gray-200 bg-gray-50 bg-opacity-80">
              <div className="flex justify-end">
                <button
                  onClick={() => setShowMetricsDialog(false)}
                  className="px-6 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* User Preferences Dialog */}
      {showUserPreferencesDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">User Preferences for AI Column Selection</h3>
              
              <div className="space-y-4">
                {/* Risk Score Column Preference */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Preferred Risk Score Column</label>
                  <select
                    value={userPreferences.risk_score_column || ''}
                    onChange={(e) => setUserPreferences({
                      ...userPreferences,
                      risk_score_column: e.target.value
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Select Column</option>
                    {Object.values(schema?.tables || {}).flatMap(table => 
                      Object.values(table.columns || {}).map(col => (
                        <option key={col.id} value={col.name}>
                          {col.name} ({table.name})
                        </option>
                      ))
                    )}
                  </select>
                </div>
                
                {/* Amount Column Preference */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Preferred Amount Column</label>
                  <select
                    value={userPreferences.amount_column || ''}
                    onChange={(e) => setUserPreferences({
                      ...userPreferences,
                      amount_column: e.target.value
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Select Column</option>
                    {Object.values(schema?.tables || {}).flatMap(table => 
                      Object.values(table.columns || {}).map(col => (
                        <option key={col.id} value={col.name}>
                          {col.name} ({table.name})
                        </option>
                      ))
                    )}
                  </select>
                </div>
                
                {/* Date Column Preference */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Preferred Date Column</label>
                  <select
                    value={userPreferences.date_column || ''}
                    onChange={(e) => setUserPreferences({
                      ...userPreferences,
                      date_column: e.target.value
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Select Column</option>
                    {Object.values(schema?.tables || {}).flatMap(table => 
                      Object.values(table.columns || {}).map(col => (
                        <option key={col.id} value={col.name}>
                          {col.name} ({table.name})
                        </option>
                      ))
                    )}
                  </select>
                </div>
                
                {/* Default Risk Threshold */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Default Risk Threshold</label>
                  <input
                    type="number"
                    value={userPreferences.default_risk_threshold || 10}
                    onChange={(e) => setUserPreferences({
                      ...userPreferences,
                      default_risk_threshold: parseInt(e.target.value) || 10
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="10"
                  />
                </div>
              </div>
            </div>
            
            <div className="p-6 border-t border-gray-200 bg-gray-50">
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => setShowUserPreferencesDialog(false)}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    // Save user preferences to schema
                    const updatedSchema = {
                      ...schema,
                      user_preferences: userPreferences
                    };
                    setSchema(updatedSchema);
                    setShowUserPreferencesDialog(false);
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Save Preferences
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hidden file input for import */}
      <input
        id="import-schema-input"
        type="file"
        accept=".csv,.xlsx,.xls"
        onChange={handleImportSchema}
        style={{ display: 'none' }}
      />
    </div>
  );

  // Global function for manual testing
  (window as any).manualSaveSchema = handleSaveSchema;
  (window as any).getSchemaState = () => ({ schema, saving, isEditMode });

  // Main return
  return isExpanded ? <ExpandedView /> : <CompactView />;
};

export default SemanticSchemaEditor;
