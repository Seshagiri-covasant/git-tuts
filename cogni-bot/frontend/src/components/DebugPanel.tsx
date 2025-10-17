import React from 'react';
import { Disclosure } from '@headlessui/react';
import { ChevronUpIcon } from '@heroicons/react/24/solid';

interface IntentDetails {
  tables: string[];
  columns: string[];
  filters: string[];
  joins: string[];
  order_by: string[];
  date_range: string | null;
}

interface DebugStepDetails {
  intent?: IntentDetails;
  keywords?: string[];
  generatedSQL?: string;
  clarificationNeeded?: boolean;
  clarificationReason?: string;
  validationErrors?: string[];
  conversationContext?: string;
  selectedTables?: string[];
  selectedColumns?: string[];
  confidenceScores?: any;
  requirements?: any;
  conversationHistory?: string;
  memoryWorking?: boolean;
}

interface DebugStep {
  step: string;
  status: string;
  details: DebugStepDetails;
  timestamp: string;
}

interface DebugPanelProps {
  steps: DebugStep[];
  isVisible: boolean;
}

export const DebugPanel: React.FC<DebugPanelProps> = ({ steps, isVisible }) => {
  if (!isVisible || !steps?.length) return null;

  return (
    <div 
      className={`fixed right-0 top-16 h-[calc(100vh-4rem)] w-96 bg-gray-50 border-l border-gray-200 overflow-y-auto p-4 shadow-lg pointer-events-auto transform transition-transform duration-300 ease-in-out ${isVisible ? 'translate-x-0' : 'translate-x-full'}`}
      style={{ zIndex: 999 }}
    >
      <h2 className="text-lg font-semibold mb-4 flex items-center">
        <span className="mr-2">Debug Information</span>
        <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">{steps.length} steps</span>
      </h2>
      <div className="space-y-2">
        {steps.map((step, index) => (
          <Disclosure key={index} defaultOpen={index === steps.length - 1}>
            {({ open }) => (
              <div className="bg-white rounded-lg shadow border border-gray-100">
                <Disclosure.Button className="flex w-full justify-between rounded-lg px-4 py-2 text-left text-sm font-medium hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2">
                  <div className="flex items-center space-x-2">
                    <span className={`w-2 h-2 rounded-full ${
                      step.status === 'completed' ? 'bg-green-500' :
                      step.status === 'in_progress' ? 'bg-blue-500' :
                      step.status === 'error' ? 'bg-red-500' : 'bg-gray-500'
                    }`}></span>
                    <span className="font-medium">{step.step}</span>
                    {step.status === 'in_progress' && (
                      <span className="animate-pulse text-blue-600 text-xs">Processing...</span>
                    )}
                  </div>
                  <ChevronUpIcon className={`${
                    open ? 'transform rotate-180' : ''
                  } h-5 w-5 text-gray-500`} />
                </Disclosure.Button>
                <Disclosure.Panel className="px-4 py-2 text-sm text-gray-700">
                  <div className="space-y-3">
                    {step.details.intent && (
                      <div className="bg-gray-50 rounded-md p-3">
                        <h4 className="font-medium text-gray-900 mb-2">Intent Analysis</h4>
                        <div className="space-y-1.5">
                          {step.details.intent.tables.length > 0 && (
                            <div>
                              <span className="text-gray-600">Tables:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {step.details.intent.tables.map((table, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded text-xs">{table}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {step.details.intent.columns.length > 0 && (
                            <div>
                              <span className="text-gray-600">Columns:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {step.details.intent.columns.map((col, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-green-50 text-green-700 rounded text-xs">{col}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {step.details.intent.filters.length > 0 && (
                            <div>
                              <span className="text-gray-600">Filters:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {step.details.intent.filters.map((filter, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-yellow-50 text-yellow-700 rounded text-xs">{filter}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {step.details.intent.joins?.length > 0 && (
                            <div>
                              <span className="text-gray-600">Joins:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {step.details.intent.joins.map((join, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-orange-50 text-orange-700 rounded text-xs">{join}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {step.details.intent.order_by?.length > 0 && (
                            <div>
                              <span className="text-gray-600">Order By:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {step.details.intent.order_by.map((order, i) => (
                                  <span key={i} className="px-2 py-0.5 bg-pink-50 text-pink-700 rounded text-xs">{order}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {step.details.intent.date_range && (
                            <div>
                              <span className="text-gray-600">Date Range:</span>
                              <div className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs mt-1">
                                {step.details.intent.date_range}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                    {step.details.keywords && step.details.keywords.length > 0 && (
                      <div className="bg-gray-50 rounded-md p-3">
                        <h4 className="font-medium text-gray-900 mb-2">Identified Keywords</h4>
                        <div className="flex flex-wrap gap-1">
                          {step.details.keywords.map((keyword, i) => (
                            <span key={i} className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded text-xs">{keyword}</span>
                          ))}
                        </div>
                      </div>
                    )}
                    {step.details.generatedSQL && (
                      <div className="bg-gray-50 rounded-md p-3">
                        <h4 className="font-medium text-gray-900 mb-2">Generated SQL</h4>
                        <pre className="p-2 bg-gray-900 text-gray-100 rounded text-xs overflow-x-auto">{step.details.generatedSQL}</pre>
                      </div>
                    )}
                    {step.details.clarificationNeeded && (
                      <div className="bg-yellow-50 rounded-md p-3">
                        <h4 className="font-medium text-yellow-900 mb-2">Clarification Needed</h4>
                        <div className="text-yellow-800">{step.details.clarificationReason}</div>
                      </div>
                    )}
                    {step.details.validationErrors && step.details.validationErrors.length > 0 && (
                      <div className="bg-red-50 rounded-md p-3">
                        <h4 className="font-medium text-red-900 mb-2">Validation Errors</h4>
                        <ul className="list-disc ml-4 text-red-800 space-y-1">
                          {step.details.validationErrors.map((error, i) => (
                            <li key={i}>{error}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {step.details.conversationContext && (
                      <div className="bg-gray-50 rounded-md p-3">
                        <h4 className="font-medium text-gray-900 mb-2">Conversation Context</h4>
                        <div className="text-sm text-gray-700 bg-white p-2 rounded border">
                          {step.details.conversationContext}
                        </div>
                      </div>
                    )}
                    {step.details.confidenceScores && (
                      <div className="bg-gray-50 rounded-md p-3">
                        <h4 className="font-medium text-gray-900 mb-2">Confidence Scores</h4>
                        <div className="text-sm text-gray-700 bg-white p-2 rounded border">
                          <pre>{JSON.stringify(step.details.confidenceScores, null, 2)}</pre>
                        </div>
                      </div>
                    )}
                    {step.details.requirements && (
                      <div className="bg-gray-50 rounded-md p-3">
                        <h4 className="font-medium text-gray-900 mb-2">Requirements Analysis</h4>
                        <div className="text-sm text-gray-700 bg-white p-2 rounded border">
                          <pre>{JSON.stringify(step.details.requirements, null, 2)}</pre>
                        </div>
                      </div>
                    )}
                    {step.details.conversationHistory && (
                      <div className="bg-blue-50 rounded-md p-3">
                        <h4 className="font-medium text-blue-900 mb-2">Memory System</h4>
                        <div className="text-sm text-blue-800">
                          {step.details.conversationHistory}
                        </div>
                        {step.details.memoryWorking && (
                          <div className="mt-2 text-xs text-green-700 bg-green-100 px-2 py-1 rounded">
                            ✅ Memory system is working
                          </div>
                        )}
                      </div>
                    )}
                    <div className="text-xs text-gray-500">
                      {new Date(step.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </Disclosure.Panel>
              </div>
            )}
          </Disclosure>
        ))}
      </div>
    </div>
  );
};