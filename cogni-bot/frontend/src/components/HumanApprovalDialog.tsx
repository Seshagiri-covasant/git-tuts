import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertTriangle, Database, Filter, BarChart3, X, ChevronDown, ChevronRight, Info } from 'lucide-react';

interface ApprovalRequest {
  message: string;
  intent_summary: {
    tables: string[];
    columns: string[];
    filters: string[];
    aggregations: string[];
    description: string;
  };
  clarification_questions: Array<{
    id: string;
    type: 'confirmation' | 'choice' | 'clarification';
    question: string;
    options?: Array<{
      id: string;
      name: string;
      display_name?: string;
      description: string;
      business_terms?: string[];
      business_context?: string;
      table_name?: string;
      type: 'original' | 'similar' | 'high_priority';
      similarity_score?: number;
      priority?: string;
    }>;
    details?: Record<string, any>;
    missing_context?: string[];
  }>;
  similar_columns: Array<{
    original_column: string;
    table: string;
    similar_columns: Array<{
      name: string;
      description: string;
      similarity_score: number;
      reasons: string[];
    }>;
    description: string;
  }>;
  requires_human_input: boolean;
  approval_type: string;
}

interface HumanApprovalDialogProps {
  isOpen: boolean;
  onClose: () => void;
  approvalRequest: ApprovalRequest;
  onApprove: (response: any) => void;
  isLoading?: boolean;
}

const HumanApprovalDialog: React.FC<HumanApprovalDialogProps> = ({
  isOpen,
  onClose,
  approvalRequest,
  onApprove,
  isLoading = false
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['intent', 'questions']));
  const [responses, setResponses] = useState<Record<string, any>>({});
  const [selectedColumns, setSelectedColumns] = useState<Record<string, string>>({});

  useEffect(() => {
    if (isOpen) {
      // Initialize responses based on questions
      const initialResponses: Record<string, any> = {};
      approvalRequest.clarification_questions.forEach(question => {
        if (question.type === 'confirmation') {
          initialResponses[question.id] = true; // Default to approved
        } else if (question.type === 'choice') {
          // Select first option by default
          if (question.options && question.options.length > 0) {
            initialResponses[question.id] = question.options[0].id;
          }
        }
      });
      setResponses(initialResponses);
    }
  }, [isOpen, approvalRequest]);

  const toggleSection = (sectionId: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const handleResponseChange = (questionId: string, value: any) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  const handleColumnSelection = (questionId: string, columnId: string) => {
    setSelectedColumns(prev => ({
      ...prev,
      [questionId]: columnId
    }));
    handleResponseChange(questionId, columnId);
  };

  const handleApprove = () => {
    const humanResponse = {
      type: 'approval' as const,
      clarifications: responses,
      selected_columns: Object.values(selectedColumns),
      business_context: {
        approved_intent: approvalRequest.intent_summary,
        user_responses: responses
      }
    };
    onApprove(humanResponse);
  };

  const handleModify = () => {
    const humanResponse = {
      type: 'modification' as const,
      clarifications: responses,
      selected_columns: Object.values(selectedColumns),
      business_context: {
        modified_intent: approvalRequest.intent_summary,
        user_responses: responses
      }
    };
    onApprove(humanResponse);
  };

  const handleClarify = () => {
    const humanResponse = {
      type: 'clarification' as const,
      clarifications: responses,
      selected_columns: Object.values(selectedColumns),
      business_context: {
        clarification_needed: true,
        user_responses: responses
      }
    };
    onApprove(humanResponse);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <AlertTriangle className="w-6 h-6" />
              <div>
                <h2 className="text-xl font-semibold">AI Needs Your Approval</h2>
                <p className="text-blue-100 text-sm mt-1">
                  I found some ambiguity in your request and need clarification to provide accurate results
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-blue-200 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Main Message */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="flex items-start space-x-3">
              <Info className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
              <p className="text-blue-800">{approvalRequest.message}</p>
            </div>
          </div>

          {/* Intent Summary */}
          <div className="mb-6">
            <button
              onClick={() => toggleSection('intent')}
              className="flex items-center justify-between w-full p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <Database className="w-5 h-5 text-gray-600" />
                <span className="font-medium text-gray-900">What I Understand</span>
              </div>
              {expandedSections.has('intent') ? (
                <ChevronDown className="w-5 h-5 text-gray-500" />
              ) : (
                <ChevronRight className="w-5 h-5 text-gray-500" />
              )}
            </button>
            
            {expandedSections.has('intent') && (
              <div className="mt-4 p-4 bg-white border border-gray-200 rounded-lg">
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">Business Description</h4>
                    <p className="text-gray-700 bg-gray-50 p-3 rounded-lg">
                      {approvalRequest.intent_summary.description}
                    </p>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {approvalRequest.intent_summary.tables.length > 0 && (
                      <div>
                        <h5 className="font-medium text-gray-900 mb-2 flex items-center">
                          <Database className="w-4 h-4 mr-2" />
                          Tables
                        </h5>
                        <div className="space-y-1">
                          {approvalRequest.intent_summary.tables.map((table, index) => (
                            <span key={index} className="inline-block bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm">
                              {table}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {approvalRequest.intent_summary.columns.length > 0 && (
                      <div>
                        <h5 className="font-medium text-gray-900 mb-2 flex items-center">
                          <BarChart3 className="w-4 h-4 mr-2" />
                          Columns
                        </h5>
                        <div className="space-y-1">
                          {approvalRequest.intent_summary.columns.map((column, index) => (
                            <span key={index} className="inline-block bg-green-100 text-green-800 px-2 py-1 rounded text-sm">
                              {column}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {approvalRequest.intent_summary.filters.length > 0 && (
                      <div>
                        <h5 className="font-medium text-gray-900 mb-2 flex items-center">
                          <Filter className="w-4 h-4 mr-2" />
                          Filters
                        </h5>
                        <div className="space-y-1">
                          {approvalRequest.intent_summary.filters.map((filter, index) => (
                            <span key={index} className="inline-block bg-orange-100 text-orange-800 px-2 py-1 rounded text-sm">
                              {filter}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    {approvalRequest.intent_summary.aggregations.length > 0 && (
                      <div>
                        <h5 className="font-medium text-gray-900 mb-2 flex items-center">
                          <BarChart3 className="w-4 h-4 mr-2" />
                          Calculations
                        </h5>
                        <div className="space-y-1">
                          {approvalRequest.intent_summary.aggregations.map((agg, index) => (
                            <span key={index} className="inline-block bg-purple-100 text-purple-800 px-2 py-1 rounded text-sm">
                              {agg}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Clarification Questions */}
          <div className="mb-6">
            <button
              onClick={() => toggleSection('questions')}
              className="flex items-center justify-between w-full p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center space-x-3">
                <AlertTriangle className="w-5 h-5 text-gray-600" />
                <span className="font-medium text-gray-900">Questions for You</span>
              </div>
              {expandedSections.has('questions') ? (
                <ChevronDown className="w-5 h-5 text-gray-500" />
              ) : (
                <ChevronRight className="w-5 h-5 text-gray-500" />
              )}
            </button>
            
            {expandedSections.has('questions') && (
              <div className="mt-4 space-y-4">
                {approvalRequest.clarification_questions.map((question) => (
                  <div key={question.id} className="p-4 bg-white border border-gray-200 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3">{question.question}</h4>
                    
                    {question.type === 'confirmation' && (
                      <div className="space-y-3">
                        <label className="flex items-center space-x-3 cursor-pointer">
                          <input
                            type="radio"
                            name={question.id}
                            checked={responses[question.id] === true}
                            onChange={() => handleResponseChange(question.id, true)}
                            className="w-4 h-4 text-blue-600"
                          />
                          <span className="text-gray-700">Yes, this is correct</span>
                        </label>
                        <label className="flex items-center space-x-3 cursor-pointer">
                          <input
                            type="radio"
                            name={question.id}
                            checked={responses[question.id] === false}
                            onChange={() => handleResponseChange(question.id, false)}
                            className="w-4 h-4 text-blue-600"
                          />
                          <span className="text-gray-700">No, this needs changes</span>
                        </label>
                      </div>
                    )}
                    
                    {question.type === 'choice' && question.options && (
                      <div className="space-y-3">
                        {question.options.map((option) => (
                          <label key={option.id} className="flex items-start space-x-3 cursor-pointer p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
                            <input
                              type="radio"
                              name={question.id}
                              checked={responses[question.id] === option.id}
                              onChange={() => handleColumnSelection(question.id, option.id)}
                              className="w-4 h-4 text-blue-600 mt-1"
                            />
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                <span className="font-medium text-gray-900">
                                  {option.display_name || option.name}
                                </span>
                                {option.type === 'similar' && (
                                  <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs">
                                    Similar ({option.similarity_score}% match)
                                  </span>
                                )}
                                {option.type === 'original' && (
                                  <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                                    Original
                                  </span>
                                )}
                                {option.type === 'high_priority' && (
                                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                                    High Priority
                                  </span>
                                )}
                              </div>
                              {option.description && (
                                <p className="text-sm text-gray-600 mt-1">{option.description}</p>
                              )}
                              {option.business_context && option.business_context !== option.description && (
                                <p className="text-xs text-blue-600 mt-1 italic">
                                  Business Context: {option.business_context}
                                </p>
                              )}
                              {option.business_terms && option.business_terms.length > 0 && (
                                <div className="mt-1">
                                  <span className="text-xs text-gray-500">Related terms: </span>
                                  <span className="text-xs text-gray-600">
                                    {option.business_terms.slice(0, 3).join(', ')}
                                    {option.business_terms.length > 3 && '...'}
                                  </span>
                                </div>
                              )}
                            </div>
                          </label>
                        ))}
                      </div>
                    )}
                    
                    {question.type === 'clarification' && (
                      <div className="space-y-3">
                        <p className="text-sm text-gray-600 mb-3">
                          Please provide more details about: {question.missing_context?.join(', ')}
                        </p>
                        <textarea
                          placeholder="Enter your clarification here..."
                          value={responses[question.id] || ''}
                          onChange={(e) => handleResponseChange(question.id, e.target.value)}
                          className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          rows={3}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Similar Columns */}
          {approvalRequest.similar_columns.length > 0 && (
            <div className="mb-6">
              <button
                onClick={() => toggleSection('similar')}
                className="flex items-center justify-between w-full p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <Database className="w-5 h-5 text-gray-600" />
                  <span className="font-medium text-gray-900">Similar Columns Found</span>
                </div>
                {expandedSections.has('similar') ? (
                  <ChevronDown className="w-5 h-5 text-gray-500" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-gray-500" />
                )}
              </button>
              
              {expandedSections.has('similar') && (
                <div className="mt-4 space-y-4">
                  {approvalRequest.similar_columns.map((group, index) => (
                    <div key={index} className="p-4 bg-white border border-gray-200 rounded-lg">
                      <h4 className="font-medium text-gray-900 mb-3">
                        Similar to: <span className="text-blue-600">{group.original_column}</span>
                      </h4>
                      <div className="space-y-2">
                        {group.similar_columns.map((col, colIndex) => (
                          <div key={colIndex} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                            <div>
                              <span className="font-medium text-gray-900">{col.name}</span>
                              <p className="text-sm text-gray-600">{col.description}</p>
                            </div>
                            <div className="text-right">
                              <span className="text-sm text-gray-500">{col.similarity_score}% match</span>
                              <div className="text-xs text-gray-400 mt-1">
                                {col.reasons.join(', ')}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="bg-gray-50 px-6 py-4 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-500">
              Your response will help me provide more accurate results
            </div>
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleClarify}
                disabled={isLoading}
                className="px-4 py-2 text-blue-700 bg-blue-100 border border-blue-300 rounded-lg hover:bg-blue-200 transition-colors disabled:opacity-50"
              >
                Need More Info
              </button>
              <button
                onClick={handleModify}
                disabled={isLoading}
                className="px-4 py-2 text-orange-700 bg-orange-100 border border-orange-300 rounded-lg hover:bg-orange-200 transition-colors disabled:opacity-50"
              >
                Modify Request
              </button>
              <button
                onClick={handleApprove}
                disabled={isLoading}
                className="px-6 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center space-x-2"
              >
                {isLoading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle className="w-4 h-4" />
                    <span>Approve & Continue</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HumanApprovalDialog;
