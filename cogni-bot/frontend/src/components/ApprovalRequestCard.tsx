import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, X, ChevronDown, ChevronUp, Database, Filter, BarChart3 } from 'lucide-react';

interface ApprovalRequestCardProps {
  approvalRequest: {
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
        description: string;
        type: 'original' | 'similar';
        similarity_score?: number;
      }>;
    }>;
  };
  onApprove: (response: any) => void;
  onReject: () => void;
  isLoading?: boolean;
}

const ApprovalRequestCard: React.FC<ApprovalRequestCardProps> = ({
  approvalRequest,
  onApprove,
  onReject,
  isLoading = false
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [responses, setResponses] = useState<Record<string, any>>({});

  const handleResponseChange = (questionId: string, value: any) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: value
    }));
  };

  const handleQuickApprove = () => {
    const humanResponse = {
      type: 'approval' as const,
      clarifications: responses,
      business_context: {
        approved_intent: approvalRequest.intent_summary,
        user_responses: responses
      }
    };
    onApprove(humanResponse);
  };

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4 mb-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-gray-900">AI Needs Your Approval</h3>
            <p className="text-sm text-gray-600 mt-1">{approvalRequest.message}</p>
          </div>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      </div>

      {/* Quick Summary */}
      <div className="mb-4">
        <div className="bg-white rounded-lg p-3 border border-gray-200">
          <p className="text-sm text-gray-700 font-medium mb-2">What I understand:</p>
          <p className="text-sm text-gray-600">{approvalRequest.intent_summary.description}</p>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="space-y-4 mb-4">
          {/* Intent Details */}
          <div className="bg-white rounded-lg p-4 border border-gray-200">
            <h4 className="font-medium text-gray-900 mb-3">Intent Details</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {approvalRequest.intent_summary.tables.length > 0 && (
                <div>
                  <h5 className="font-medium text-gray-900 mb-2 flex items-center text-sm">
                    <Database className="w-4 h-4 mr-2" />
                    Tables
                  </h5>
                  <div className="flex flex-wrap gap-1">
                    {approvalRequest.intent_summary.tables.map((table, index) => (
                      <span key={index} className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
                        {table}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {approvalRequest.intent_summary.columns.length > 0 && (
                <div>
                  <h5 className="font-medium text-gray-900 mb-2 flex items-center text-sm">
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Columns
                  </h5>
                  <div className="flex flex-wrap gap-1">
                    {approvalRequest.intent_summary.columns.map((column, index) => (
                      <span key={index} className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                        {column}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {approvalRequest.intent_summary.filters.length > 0 && (
                <div>
                  <h5 className="font-medium text-gray-900 mb-2 flex items-center text-sm">
                    <Filter className="w-4 h-4 mr-2" />
                    Filters
                  </h5>
                  <div className="flex flex-wrap gap-1">
                    {approvalRequest.intent_summary.filters.map((filter, index) => (
                      <span key={index} className="bg-orange-100 text-orange-800 px-2 py-1 rounded text-xs">
                        {filter}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Clarification Questions */}
                {approvalRequest.clarification_questions.map((question) => (
            <div key={question.id} className="bg-white rounded-lg p-4 border border-gray-200">
              <h4 className="font-medium text-gray-900 mb-3 text-sm">{question.question}</h4>
              
              {question.type === 'confirmation' && (
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name={question.id}
                      checked={responses[question.id] === true}
                      onChange={() => handleResponseChange(question.id, true)}
                      className="w-4 h-4 text-blue-600"
                    />
                    <span className="text-sm text-gray-700">Yes, this is correct</span>
                  </label>
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="radio"
                      name={question.id}
                      checked={responses[question.id] === false}
                      onChange={() => handleResponseChange(question.id, false)}
                      className="w-4 h-4 text-blue-600"
                    />
                    <span className="text-sm text-gray-700">No, this needs changes</span>
                  </label>
                </div>
              )}
              
              {question.type === 'choice' && question.options && (
                <div className="space-y-2">
                  {question.options.map((option) => (
                    <label key={option.id} className="flex items-start space-x-2 cursor-pointer p-2 border border-gray-200 rounded hover:bg-gray-50">
                      <input
                        type="radio"
                        name={question.id}
                        checked={responses[question.id] === option.id}
                        onChange={() => handleResponseChange(question.id, option.id)}
                        className="w-4 h-4 text-blue-600 mt-1"
                      />
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-gray-900 text-sm">{option.name}</span>
                          {option.type === 'similar' && (
                            <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs">
                              Similar
                            </span>
                          )}
                          {option.type === 'original' && (
                            <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                              Original
                            </span>
                          )}
                        </div>
                        {option.description && (
                          <p className="text-xs text-gray-600 mt-1">{option.description}</p>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              )}
              
              {question.type === 'clarification' && (
                <div className="space-y-2">
                  <p className="text-sm text-gray-600 mb-2">
                    Please provide more details about your request.
                  </p>
                  <textarea
                    placeholder="Enter your clarification here..."
                    value={responses[question.id] || ''}
                    onChange={(e) => handleResponseChange(question.id, e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={2}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-500">
          Your response helps me provide accurate results
        </div>
        <div className="flex space-x-2">
          <button
            onClick={onReject}
            disabled={isLoading}
            className="px-3 py-1.5 text-gray-700 bg-white border border-gray-300 rounded text-sm hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            <X className="w-4 h-4 mr-1 inline" />
            Cancel
          </button>
          <button
            onClick={handleQuickApprove}
            disabled={isLoading}
            className="px-4 py-1.5 text-white bg-blue-600 rounded text-sm hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center"
          >
            {isLoading ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                Processing...
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4 mr-1" />
                Approve & Continue
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ApprovalRequestCard;
