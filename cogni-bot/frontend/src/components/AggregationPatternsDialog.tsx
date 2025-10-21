import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2 } from 'lucide-react';

interface AggregationPattern {
  id: string;
  name: string;
  description: string;
  sql_template: string;
  keywords: string[];
  example_question: string;
  example_sql: string;
}

interface AggregationPatternsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  patterns: AggregationPattern[];
  onSave: (patterns: AggregationPattern[]) => void;
}

const AggregationPatternsDialog: React.FC<AggregationPatternsDialogProps> = ({
  isOpen,
  onClose,
  patterns,
  onSave
}) => {
  const [localPatterns, setLocalPatterns] = useState<AggregationPattern[]>(patterns);

  // Update local patterns when props change
  useEffect(() => {
    console.log('AggregationPatternsDialog: patterns prop changed:', patterns);
    setLocalPatterns(patterns);
  }, [patterns]);

  const addPattern = () => {
    console.log('Adding new pattern, current patterns:', localPatterns);
    const newPattern: AggregationPattern = {
      id: Date.now().toString(),
      name: '',
      description: '',
      sql_template: '',
      keywords: [],
      example_question: '',
      example_sql: ''
    };
    const updatedPatterns = [...localPatterns, newPattern];
    console.log('Updated patterns:', updatedPatterns);
    setLocalPatterns(updatedPatterns);
  };


  const removePattern = (index: number) => {
    const updated = localPatterns.filter((_, i) => i !== index);
    setLocalPatterns(updated);
  };

  const updatePattern = (index: number, field: keyof AggregationPattern, value: any) => {
    const updated = [...localPatterns];
    updated[index] = { ...updated[index], [field]: value };
    setLocalPatterns(updated);
  };

  const handleSave = () => {
    onSave(localPatterns);
    onClose();
  };

  if (!isOpen) return null;

  console.log('Rendering AggregationPatternsDialog with patterns:', localPatterns);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Aggregation Patterns for SQL Generation</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
          
          <div className="space-y-4">
             <div className="flex justify-between items-center">
               <p className="text-sm text-gray-600">
                 Configure how the AI should handle complex aggregation questions. These patterns will be used to generate SQL for percentage calculations, comparisons, and other complex queries.
               </p>
               <button
                 onClick={addPattern}
                 className="flex items-center gap-2 px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700"
               >
                 <Plus className="w-4 h-4" />
                 Add Pattern
               </button>
             </div>
            
            {localPatterns.map((pattern, index) => (
              <div key={pattern.id} className="border rounded-lg p-4 space-y-3 bg-gray-50">
                <div className="flex justify-between items-center">
                  <h4 className="font-medium text-gray-900">Pattern {index + 1}</h4>
                  <button
                    onClick={() => removePattern(index)}
                    className="text-red-600 hover:text-red-800"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Pattern Name</label>
                    <input
                      type="text"
                      value={pattern.name}
                      onChange={(e) => updatePattern(index, 'name', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., Percentage Analysis"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Keywords (comma-separated)</label>
                    <input
                      type="text"
                      value={pattern.keywords.join(', ')}
                      onChange={(e) => updatePattern(index, 'keywords', e.target.value.split(',').map(k => k.trim()))}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., percentage, breakdown, vs, versus"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <input
                    type="text"
                    value={pattern.description}
                    onChange={(e) => updatePattern(index, 'description', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Calculate percentages with GROUP BY for manual vs automated payments"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">SQL Template</label>
                  <textarea
                    value={pattern.sql_template}
                    onChange={(e) => updatePattern(index, 'sql_template', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    rows={4}
                    placeholder="e.g., WITH threshold AS (SELECT AVG(score_column) FROM table_name), SELECT group_column, COUNT(*) * 100.0 / SUM(COUNT(*)) OVER () AS percentage FROM table_name, threshold WHERE score_column > threshold.avg GROUP BY group_column"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Use placeholders like {'{table}'}, {'{score_column}'}, {'{group_column}'} for dynamic substitution
                  </p>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Example Question</label>
                    <input
                      type="text"
                      value={pattern.example_question}
                      onChange={(e) => updatePattern(index, 'example_question', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      placeholder="e.g., What percentage of high-risk payments are manual vs automated?"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Example SQL</label>
                    <textarea
                      value={pattern.example_sql}
                      onChange={(e) => updatePattern(index, 'example_sql', e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      rows={2}
                      placeholder="Example of the SQL that would be generated"
                    />
                  </div>
                </div>
              </div>
            ))}
            
            {localPatterns.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                No aggregation patterns configured. Click "Add Pattern" to create your first pattern.
              </div>
            )}
          </div>
          
          <div className="flex justify-end space-x-3 mt-6">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 bg-gray-200 rounded hover:bg-gray-300"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
            >
              Save Patterns
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AggregationPatternsDialog;
