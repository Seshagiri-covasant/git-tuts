import React, { useState, useEffect, useRef } from "react";
import { useParams } from "react-router-dom";
import { useToaster } from "../../Toaster/Toaster";
import { 
  createCustomTest, 
  getCustomTests, 
  getCustomTestSuites, 
  runCustomTests, 
  getCustomTestMetrics,
  deleteCustomTest 
} from "../../services/api";
import { Plus, Play, Trash2, Download, BarChart3, X, CheckCircle, XCircle } from "lucide-react";
import Loader from "../Loader";
import { createBenchmarkPoller } from "../../utils/smartPolling";
import { SmartErrorHandler, getErrorMessage } from "../../utils/errorHandler";

interface CustomTest {
  test_id: string;
  test_name: string;
  original_sql: string;
  natural_question: string;
  generated_sql?: string;
  score?: number;
  llm_used?: string;
  temperature?: number;
  created_at: string;
}

interface TestMetrics {
  total_tests: number;
  correct_tests: number;
  efficiency: number;
}

const CustomTestSuiteInterface: React.FC = () => {
  const { chatbotId } = useParams();
  const { showToast } = useToaster();
  
  const [customTests, setCustomTests] = useState<CustomTest[]>([]);
  const [testSuites, setTestSuites] = useState<string[]>([]);
  const [selectedSuite, setSelectedSuite] = useState<string>("");
  const [metrics, setMetrics] = useState<TestMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [runningProgress, setRunningProgress] = useState(0);
  const [runningStatus, setRunningStatus] = useState("");
  
  // Smart polling ref
  const testPollerRef = useRef<any>(null);
  const [pollingError, setPollingError] = useState<string | null>(null);
  
  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showResultsModal, setShowResultsModal] = useState(false);
  const [newTest, setNewTest] = useState({
    test_name: "",
    original_sql: "",
    natural_question: ""
  });

  useEffect(() => {
    if (chatbotId) {
      loadData();
    }
  }, [chatbotId, selectedSuite]);

  const loadData = async () => {
    try {
      setIsLoading(true);
      
      // Load test suites
      const suitesRes = await getCustomTestSuites(chatbotId!);
      setTestSuites(suitesRes.data.test_suites);
      
      // Load custom tests
      const testsRes = await getCustomTests(chatbotId!, selectedSuite || undefined);
      setCustomTests(testsRes.data.custom_tests);
      
      // Load metrics
      const metricsRes = await getCustomTestMetrics(chatbotId!, {
        test_name: selectedSuite || undefined
      });
      setMetrics(metricsRes.data.metrics);
      
    } catch (error: any) {
      showToast(`Failed to load data: ${error.response?.data?.error || error.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddTest = async () => {
    if (!newTest.test_name || !newTest.original_sql || !newTest.natural_question) {
      showToast('Please fill in all fields', 'error');
      return;
    }

    try {
      await createCustomTest(chatbotId!, newTest);
      showToast('Custom test added successfully', 'success');
      setShowAddModal(false);
      setNewTest({ test_name: "", original_sql: "", natural_question: "" });
      loadData();
    } catch (error: any) {
      showToast(`Failed to add test: ${error.response?.data?.error || error.message}`, 'error');
    }
  };

  const handleRunTests = async () => {
    try {
      setIsRunningTests(true);
      setRunningProgress(0);
      setRunningStatus("Initializing test execution...");
      setPollingError(null);
      
      // Stop any existing poller
      if (testPollerRef.current) {
        testPollerRef.current.stop();
      }
      
      // Start the tests
      await runCustomTests(chatbotId!, {
        test_name: selectedSuite || undefined
      });
      
      setRunningProgress(25);
      setRunningStatus("Tests started successfully. Processing results...");
      
      // Create smart poller for test results
      testPollerRef.current = createBenchmarkPoller();
      
      testPollerRef.current.start(
        async () => {
          setRunningProgress(prev => Math.min(prev + 5, 90));
          setRunningStatus("Fetching latest results...");
          
          // Get updated test data
          const updatedTestsRes = await getCustomTests(chatbotId!, selectedSuite || undefined);
          const updatedTests = updatedTestsRes.data.custom_tests;
          
          // Update the local state immediately
          setCustomTests(updatedTests);
          
          // Check if all tests are complete
          const completedTests = updatedTests.filter((test: CustomTest) => 
            test.score !== undefined && test.score !== null && test.generated_sql !== undefined && test.generated_sql !== null
          );
          const totalTests = updatedTests.length;
          
          // Update progress based on completed tests
          if (totalTests > 0) {
            const completionPercentage = (completedTests.length / totalTests) * 100;
            setRunningProgress(Math.min(25 + (completionPercentage * 0.65), 90));
          }
          
          if (completedTests.length === totalTests && totalTests > 0) {
            setRunningProgress(100);
            setRunningStatus("All tests completed!");
            
            // Final data refresh to get metrics
            try {
              await loadData();
            } catch (error) {
              console.error('Error in final data refresh:', error);
            }
            
            setTimeout(() => {
              setIsRunningTests(false);
              setRunningProgress(0);
              setRunningStatus("");
              showToast(`All ${totalTests} custom tests completed successfully!`, 'success');
            }, 1000);
            
            return updatedTestsRes; // Success - stop polling
          }
          
          throw new Error('Tests still running'); // Continue polling
        },
        2000 // Poll every 2 seconds
      ).catch((error) => {
        console.error('Test polling failed:', error);
        const errorMessage = getErrorMessage(error);
        setPollingError(errorMessage);
        setRunningStatus("Test execution failed");
        setIsRunningTests(false);
        setRunningProgress(0);
        showToast(`Test execution failed: ${errorMessage}`, 'error');
      });
      
    } catch (error: any) {
      const errorMessage = getErrorMessage(error);
      showToast(`Failed to run tests: ${errorMessage}`, 'error');
      setPollingError(errorMessage);
      setIsRunningTests(false);
      setRunningProgress(0);
      setRunningStatus("");
    }
  };

  const handleDeleteTest = async (testId: string) => {
    if (!confirm('Are you sure you want to delete this test?')) return;
    
    try {
      await deleteCustomTest(testId);
      showToast('Test deleted successfully', 'success');
      loadData();
    } catch (error: any) {
      showToast(`Failed to delete test: ${error.response?.data?.error || error.message}`, 'error');
    }
  };

  const handleExportCSV = () => {
    if (!customTests || customTests.length === 0) return;
    
    const headers = ['Test Name', 'Natural Question', 'Original SQL', 'Generated SQL', 'Result', 'LLM Used', 'Temperature'];
    const csvContent = [
      headers.join(','),
      ...customTests.map(test => [
        `"${(test.test_name || '').replace(/"/g, '""')}"`,
        `"${(test.natural_question || '').replace(/"/g, '""')}"`,
        `"${(test.original_sql || '').replace(/"/g, '""')}"`,
        `"${(test.generated_sql || '').replace(/"/g, '""')}"`,
        test.score === 1 ? 'Correct' : test.score === 0 ? 'Incorrect' : 'Not Run',
        test.llm_used || 'N/A',
        test.temperature || 'N/A'
      ].join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `custom_tests_${selectedSuite || 'all'}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getPassedTests = () => customTests.filter(test => test.score === 1).length;
  const getFailedTests = () => customTests.filter(test => test.score === 0).length;
  const getNotRunTests = () => customTests.filter(test => 
    test.score === undefined || test.score === null || test.generated_sql === undefined || test.generated_sql === null
  ).length;

  // Calculate local metrics that properly handle not-run tests
  const getLocalMetrics = () => {
    const passed = getPassedTests();
    const failed = getFailedTests();
    const notRun = getNotRunTests();
    const total = customTests.length;
    
    // Only calculate efficiency for tests that have been run
    const runTests = passed + failed;
    const efficiency = runTests > 0 ? passed / runTests : 0;
    
    return {
      total_tests: total,
      correct_tests: passed,
      efficiency: efficiency
    };
  };

  if (isLoading) {
    return <Loader />;
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-gray-50">
      {/* Error Display */}
      {pollingError && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg shadow-lg z-40 max-w-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="text-red-500 mr-2">⚠️</div>
              <span className="text-sm font-medium">{pollingError}</span>
            </div>
            <button
              onClick={() => setPollingError(null)}
              className="ml-4 text-red-500 hover:text-red-700"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}
      {/* Compact Header */}
      <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-3">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-lg font-bold text-gray-900">Custom Test Suite</h1>
            <p className="text-xs text-gray-600">Create and run your own SQL tests to evaluate LLM performance</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-md transition-colors text-sm"
            >
              <Plus size={14} />
              Add Test
            </button>
            <button
              onClick={handleRunTests}
              disabled={customTests.length === 0 || isRunningTests}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white px-3 py-1.5 rounded-md transition-colors text-sm"
            >
              {isRunningTests ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Running...
                </>
              ) : (
                <>
                  <Play size={14} />
                  Run Tests
                </>
              )}
            </button>
            <button
              onClick={handleExportCSV}
              disabled={customTests.length === 0}
              className="flex items-center gap-2 bg-gray-600 hover:bg-gray-700 disabled:bg-gray-400 text-white px-3 py-1.5 rounded-md transition-colors text-sm"
            >
              <Download size={14} />
              Export CSV
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Section - Compact */}
      {(metrics || customTests.length > 0) && (
        <div className="flex-shrink-0 bg-white border-b border-gray-200 px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-blue-600" />
                <span className="text-sm text-gray-600">Efficiency:</span>
                <span className="text-lg font-bold text-blue-600">
                  {Math.round(getLocalMetrics().efficiency * 100)}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-sm text-gray-600">Passed:</span>
                <span className="text-lg font-bold text-green-600">{getPassedTests()}</span>
              </div>
              <div className="flex items-center gap-2">
                <XCircle className="w-4 h-4 text-red-600" />
                <span className="text-sm text-gray-600">Failed:</span>
                <span className="text-lg font-bold text-red-600">{getFailedTests()}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 bg-gray-400 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">?</span>
                </div>
                <span className="text-sm text-gray-600">Not Run:</span>
                <span className="text-lg font-bold text-gray-600">{getNotRunTests()}</span>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600">Filter:</span>
                <select
                  value={selectedSuite}
                  onChange={(e) => setSelectedSuite(e.target.value)}
                  className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="">All Test Cases</option>
                  {testSuites.map(suite => (
                    <option key={suite} value={suite}>{suite}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Table Section - Takes remaining space */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Table Header */}
        <div className="bg-white border-b border-gray-200 px-6 py-3">
          <h2 className="text-lg font-semibold text-gray-900">
            Test Cases ({customTests.length})
          </h2>
        </div>

        {/* Table Content */}
        <div className="flex-1 overflow-auto">
          <div className="bg-white">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50 sticky top-0 z-10">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-48">
                    Test Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-96">
                    Natural Question
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-96">
                    Original SQL
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-96">
                    Generated SQL
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-24">
                    Result
                  </th>
                  <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider w-20">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {customTests.map((test) => (
                  <tr key={test.test_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      <div className="max-w-40 break-words">
                        {test.test_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-96 break-words whitespace-pre-wrap leading-relaxed">
                        {test.natural_question}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-96 break-words whitespace-pre-wrap font-mono text-xs bg-gray-50 p-3 rounded border">
                        {test.original_sql}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-96 break-words whitespace-pre-wrap font-mono text-xs bg-gray-50 p-3 rounded border">
                        {test.generated_sql || 'Not generated'}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {test.score === 1 ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Pass
                        </span>
                      ) : test.score === 0 ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          <XCircle className="w-3 h-3 mr-1" />
                          Fail
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                          Not Run
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center text-sm font-medium">
                      <button
                        onClick={() => handleDeleteTest(test.test_id)}
                        className="text-red-600 hover:text-red-900 p-1 rounded hover:bg-red-50"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {customTests.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Plus className="w-8 h-8 text-gray-400" />
                </div>
                <p className="text-lg font-medium text-gray-900 mb-2">No test cases yet</p>
                <p className="text-gray-600">Create your first test case to get started</p>
                <button
                  onClick={() => setShowAddModal(true)}
                  className="mt-4 inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors"
                >
                  <Plus size={16} />
                  Add Your First Test
                </button>
              </div>
            )}
            </div>
          </div>
        </div>
      </div>

      {/* Running Tests Progress Overlay */}
      {isRunningTests && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 w-full max-w-md mx-4 text-center">
            <div className="mb-6">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Play className="w-8 h-8 text-blue-600 animate-pulse" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Running Custom Tests</h3>
              <p className="text-gray-600 text-sm">{runningStatus}</p>
            </div>
            
            {/* Progress Bar */}
            <div className="mb-6">
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div 
                  className="bg-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${runningProgress}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-600 mt-2">{Math.round(runningProgress)}% Complete</p>
            </div>
            
            {/* Live Results Preview */}
            <div className="bg-gray-50 rounded-lg p-4 text-left">
              <div className="flex justify-between items-center mb-2">
                <h4 className="font-medium text-gray-900">Live Results</h4>
                <button
                  onClick={loadData}
                  className="text-xs text-blue-600 hover:text-blue-800 underline"
                >
                  Refresh
                </button>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Passed:</span>
                  <span className="font-medium text-green-600">{getPassedTests()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Failed:</span>
                  <span className="font-medium text-red-600">{getFailedTests()}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Pending:</span>
                  <span className="font-medium text-gray-600">{getNotRunTests()}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Test Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl mx-4">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Add Custom Test</h2>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={20} />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Test Name
                </label>
                <input
                  type="text"
                  value={newTest.test_name}
                  onChange={(e) => setNewTest({...newTest, test_name: e.target.value})}
                  placeholder="e.g., Basic Queries, Complex Joins"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Natural Language Question
                </label>
                <textarea
                  value={newTest.natural_question}
                  onChange={(e) => setNewTest({...newTest, natural_question: e.target.value})}
                  placeholder="e.g., Show me all users who signed up in the last month"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Expected SQL Query
                </label>
                <textarea
                  value={newTest.original_sql}
                  onChange={(e) => setNewTest({...newTest, original_sql: e.target.value})}
                  placeholder="SELECT * FROM users WHERE signup_date >= DATE_SUB(NOW(), INTERVAL 1 MONTH)"
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAddTest}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Add Test
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CustomTestSuiteInterface; 