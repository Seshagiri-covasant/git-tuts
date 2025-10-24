import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, Database } from 'lucide-react';

/**
 * Demo component showing how the Human Approval system works
 * This demonstrates the complete flow from backend to frontend
 */
const HumanApprovalDemo: React.FC = () => {
  const [showDemo, setShowDemo] = useState(false);

  const mockApprovalRequest = {
    message: "I found multiple similar columns in the database that could be relevant to your question. To ensure I use the correct one, I need to confirm which column you'd like me to use.",
    intent_summary: {
      tables: ["Payments", "Transactions"],
      columns: ["risk_score"],
      filters: ["risk_score > 10"],
      aggregations: [],
      description: "analyze payment transaction data focusing on risk scores with specific criteria: risk_score > 10"
    },
    clarification_questions: [
      {
        id: "intent_confirmation",
        type: "confirmation" as const,
        question: "I understand you want to analyze payment transaction data focusing on risk scores with specific criteria: risk_score > 10. Is this correct?",
        details: {
          tables: ["Payments"],
          columns: ["risk_score"],
          filters: ["risk_score > 10"],
          aggregations: []
        }
      },
      {
        id: "column_clarification",
        type: "choice" as const,
        question: "I found some similar columns that might be relevant. Which one would you like me to use?",
        options: [
          {
            id: "original_risk_score",
            name: "risk_score",
            description: "Risk assessment score for the payment",
            type: "original" as const
          },
          {
            id: "similar_payment_risk_score",
            name: "payment_risk_score",
            description: "Payment-specific risk assessment score",
            type: "similar" as const,
            similarity_score: 15
          },
          {
            id: "similar_transaction_risk_score",
            name: "transaction_risk_score",
            description: "Transaction-specific risk assessment score",
            type: "similar" as const,
            similarity_score: 12
          }
        ]
      }
    ],
    similar_columns: [
      {
        original_column: "risk_score",
        table: "Payments",
        similar_columns: [
          {
            name: "payment_risk_score",
            description: "Payment-specific risk assessment score",
            similarity_score: 15,
            reasons: ["Shared business terms: risk, score"]
          },
          {
            name: "transaction_risk_score",
            description: "Transaction-specific risk assessment score",
            similarity_score: 12,
            reasons: ["Similar naming pattern", "Same data type"]
          }
        ],
        description: "Risk assessment score for the payment"
      }
    ],
    requires_human_input: true,
    approval_type: "intent_confirmation"
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 rounded-t-lg">
          <h1 className="text-2xl font-bold mb-2">Human Approval System Demo</h1>
          <p className="text-blue-100">
            This demonstrates how the Cogni-Bot system asks users for approval when it encounters ambiguity
          </p>
        </div>

        <div className="p-6">
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">How It Works</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="flex items-center mb-2">
                  <AlertTriangle className="w-5 h-5 text-blue-600 mr-2" />
                  <h3 className="font-medium">1. Detection</h3>
                </div>
                <p className="text-sm text-gray-600">
                  AI detects ambiguity in user query (similar columns, low confidence, complex filters)
                </p>
              </div>
              <div className="bg-green-50 p-4 rounded-lg">
                <div className="flex items-center mb-2">
                  <Database className="w-5 h-5 text-green-600 mr-2" />
                  <h3 className="font-medium">2. Analysis</h3>
                </div>
                <p className="text-sm text-gray-600">
                  System analyzes intent, finds similar columns, generates business descriptions
                </p>
              </div>
              <div className="bg-purple-50 p-4 rounded-lg">
                <div className="flex items-center mb-2">
                  <CheckCircle className="w-5 h-5 text-purple-600 mr-2" />
                  <h3 className="font-medium">3. Approval</h3>
                </div>
                <p className="text-sm text-gray-600">
                  User reviews and approves/modifies the intent, system continues with execution
                </p>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">Example Scenario</h2>
            <div className="bg-gray-50 p-4 rounded-lg mb-4">
              <h3 className="font-medium mb-2">User Query:</h3>
              <p className="text-gray-700">"Show me payments with risk score above 10"</p>
            </div>
            
            <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg mb-4">
              <div className="flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="font-medium text-yellow-800">AI Response:</h3>
                  <p className="text-yellow-700 mt-1">
                    "I found multiple similar columns that could be relevant to your question. 
                    To ensure I use the correct one, I need to confirm which column you'd like me to use."
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">What the User Sees</h2>
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-start space-x-3 mb-4">
                <AlertTriangle className="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h3 className="font-medium text-gray-900">AI Needs Your Approval</h3>
                  <p className="text-sm text-gray-600 mt-1">{mockApprovalRequest.message}</p>
                </div>
              </div>

              <div className="bg-white rounded-lg p-4 border border-gray-200 mb-4">
                <h4 className="font-medium text-gray-900 mb-2">What I understand:</h4>
                <p className="text-sm text-gray-600">{mockApprovalRequest.intent_summary.description}</p>
              </div>

              <div className="space-y-4">
                {mockApprovalRequest.clarification_questions.map((question) => (
                  <div key={question.id} className="bg-white rounded-lg p-4 border border-gray-200">
                    <h4 className="font-medium text-gray-900 mb-3 text-sm">{question.question}</h4>
                    
                    {question.type === 'confirmation' && (
                      <div className="space-y-2">
                        <label className="flex items-center space-x-2 cursor-pointer">
                          <input type="radio" name={question.id} defaultChecked className="w-4 h-4 text-blue-600" />
                          <span className="text-sm text-gray-700">Yes, this is correct</span>
                        </label>
                        <label className="flex items-center space-x-2 cursor-pointer">
                          <input type="radio" name={question.id} className="w-4 h-4 text-blue-600" />
                          <span className="text-sm text-gray-700">No, this needs changes</span>
                        </label>
                      </div>
                    )}
                    
                    {question.type === 'choice' && question.options && (
                      <div className="space-y-2">
                        {question.options.map((option) => (
                          <label key={option.id} className="flex items-start space-x-2 cursor-pointer p-2 border border-gray-200 rounded hover:bg-gray-50">
                            <input type="radio" name={question.id} className="w-4 h-4 text-blue-600 mt-1" />
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                <span className="font-medium text-gray-900 text-sm">{option.name}</span>
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
                              </div>
                              {option.description && (
                                <p className="text-xs text-gray-600 mt-1">{option.description}</p>
                              )}
                            </div>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                <div className="text-xs text-gray-500">
                  Your response will help me provide more accurate results
                </div>
                <div className="flex space-x-2">
                  <button className="px-3 py-1.5 text-gray-700 bg-white border border-gray-300 rounded text-sm hover:bg-gray-50 transition-colors">
                    Cancel
                  </button>
                  <button className="px-4 py-1.5 text-white bg-blue-600 rounded text-sm hover:bg-blue-700 transition-colors flex items-center">
                    <CheckCircle className="w-4 h-4 mr-1" />
                    Approve & Continue
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">Backend Integration</h2>
            <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm overflow-x-auto">
              <div className="mb-2">// API Endpoint</div>
              <div className="mb-2">POST /api/conversations/{'{conversationId}'}/human-approval</div>
              <div className="mb-4"></div>
              
              <div className="mb-2">// Request Body</div>
              <div className="mb-2">{'{'}</div>
              <div className="ml-4 mb-2">"human_response": {'{'}</div>
              <div className="ml-8 mb-2">"type": "approval",</div>
              <div className="ml-8 mb-2">"clarifications": {'{'}</div>
              <div className="ml-12 mb-2">"intent_confirmation": true,</div>
              <div className="ml-12 mb-2">"column_clarification": "original_risk_score"</div>
              <div className="ml-8 mb-2">{'}'},</div>
              <div className="ml-8 mb-2">"selected_columns": ["risk_score"],</div>
              <div className="ml-8 mb-2">"business_context": {'{'}</div>
              <div className="ml-12 mb-2">"approved_intent": "...",</div>
              <div className="ml-12 mb-2">"user_responses": "..."</div>
              <div className="ml-8 mb-2">{'}'}</div>
              <div className="ml-4 mb-2">{'}'},</div>
              <div className="ml-4 mb-2">"approval_type": "approval"</div>
              <div className="mb-2">{'}'}</div>
            </div>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-4">Key Features</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm">Intelligent column similarity detection</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm">Business-friendly descriptions</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm">Multiple clarification question types</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm">Confidence-based approval triggers</span>
                </div>
              </div>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm">Expandable/collapsible sections</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm">Visual similarity indicators</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm">Multiple approval actions</span>
                </div>
                <div className="flex items-center space-x-2">
                  <CheckCircle className="w-4 h-4 text-green-600" />
                  <span className="text-sm">Seamless workflow continuation</span>
                </div>
              </div>
            </div>
          </div>

          <div className="text-center">
            <button
              onClick={() => setShowDemo(!showDemo)}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {showDemo ? 'Hide' : 'Show'} Technical Details
            </button>
          </div>

          {showDemo && (
            <div className="mt-6 bg-gray-50 p-4 rounded-lg">
              <h3 className="font-medium mb-3">Technical Implementation</h3>
              <div className="space-y-2 text-sm text-gray-600">
                <p>• <strong>Backend:</strong> HumanApprovalAgent detects ambiguity and generates approval requests</p>
                <p>• <strong>API:</strong> RESTful endpoint handles human responses and continues workflow</p>
                <p>• <strong>Frontend:</strong> React components with TypeScript for type safety</p>
                <p>• <strong>State Management:</strong> LangGraph checkpoints preserve conversation state</p>
                <p>• <strong>UI/UX:</strong> Intuitive approval dialogs with expandable sections</p>
                <p>• <strong>Integration:</strong> Seamless integration with existing chat interface</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HumanApprovalDemo;
