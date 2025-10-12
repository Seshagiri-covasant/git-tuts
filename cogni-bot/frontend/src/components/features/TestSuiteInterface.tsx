import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { useAppContext } from "../../context/AppContext";
import { getBenchmarkStatus, getBenchmarkDetails, cleanupBenchmarkData } from "../../services/api";
import Loader from "../Loader";
import { Pie } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { X, Download, BarChart3, RefreshCw } from "lucide-react";
import BenchmarkMatrixModal from "./BenchmarkMatrixModal";
import { createBenchmarkPoller } from "../../utils/smartPolling";
import { SmartErrorHandler, getErrorMessage } from "../../utils/errorHandler";

ChartJS.register(ArcElement, Tooltip, Legend);

const ProgressBar = ({ progress, status }: { progress: number; status: string }) => (
  <div className="w-full flex flex-col items-center mb-4">
    <div className="w-64 h-3 bg-gray-200 rounded-full overflow-hidden mb-2">
      <div
        className="h-full bg-blue-500 transition-all duration-300"
        style={{ width: `${Math.round(progress * 100)}%` }}
      ></div>
    </div>
    <div className="text-xs text-gray-700">{status} ({Math.round(progress * 100)}%)</div>
  </div>
);

const TestSuiteInterface: React.FC = () => {
  const { chatbotId } = useParams();
  const { benchmarkingChatbotId, setBenchmarkingChatbotId } = useAppContext();
  const [llmScores, setLlmScores] = useState<any[]>([]);
  const [selectedLlm, setSelectedLlm] = useState<string | null>(null);
  const [benchmarkDetails, setBenchmarkDetails] = useState<any[]>([]);
  const [benchmarkChatbotName, setBenchmarkChatbotName] = useState('');
  const [score, setScore] = useState<any>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [detailsLoading, setDetailsLoading] = useState(false);
  const [benchmarkStatus, setBenchmarkStatus] = useState<any>(null);
  const [polling, setPolling] = useState(false);
  const [inProgressLlm, setInProgressLlm] = useState<string | null>(null);
  const [showMatrix, setShowMatrix] = useState(false);
  const [isCleaning, setIsCleaning] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  
  // Smart polling ref
  const benchmarkPollerRef = useRef<any>(null);
  const [pollingError, setPollingError] = useState<string | null>(null);

  // Function to manually refresh benchmark status
  const refreshBenchmarkStatus = useCallback(async () => {
    if (!chatbotId) return;
    
    setIsRefreshing(true);
    try {
      const res = await getBenchmarkStatus(chatbotId);
      setBenchmarkStatus(res.data);
      setPollingError(null);
      
      if (res.data.status === 'running') {
        setPolling(true);
        setInProgressLlm(res.data.result?.llm_name || res.data.llm_name || null);
      } else {
        setPolling(false);
        setInProgressLlm(null);
      }
    } catch (error: any) {
      setBenchmarkStatus(null);
      setPolling(false);
      setInProgressLlm(null);
      setPollingError(getErrorMessage(error));
    } finally {
      setIsRefreshing(false);
    }
  }, [chatbotId]);

  // Effect to handle AppContext benchmarking state changes
  useEffect(() => {
    if (!chatbotId) return;

    // If AppContext indicates this chatbot is being benchmarked, show immediate feedback
    if (benchmarkingChatbotId === chatbotId) {
      console.log('AppContext indicates benchmark is starting for this chatbot');
      setPolling(true);
      setInProgressLlm('Starting benchmark...');
      
      // Set a temporary status to show progress
      setBenchmarkStatus({
        status: 'running',
        progress: 0,
        stage: 'Initializing benchmark...'
      });
      
      // Start polling immediately
      refreshBenchmarkStatus();
    }
  }, [chatbotId, benchmarkingChatbotId, refreshBenchmarkStatus]);

  // Effect to automatically refresh when benchmark status changes
  useEffect(() => {
    if (!chatbotId) return;
    
    // Refresh benchmark status when component mounts or when chatbotId changes
    refreshBenchmarkStatus();
  }, [chatbotId, refreshBenchmarkStatus]);

  // Effect to refresh data when polling stops (benchmark completes)
  useEffect(() => {
    if (!polling && benchmarkStatus?.status === 'completed') {
      // Benchmark completed, refresh the data
      console.log('Benchmark completed, refreshing data...');
      // Small delay to ensure backend has processed the results
      setTimeout(() => {
        refreshBenchmarkStatus();
      }, 1000);
    }
  }, [polling, benchmarkStatus?.status, refreshBenchmarkStatus]);

  // Effect to handle polling
  useEffect(() => {
    if (!polling || !chatbotId) {
      // Stop any existing polling
      if (benchmarkPollerRef.current) {
        benchmarkPollerRef.current.stop();
      }
      return;
    }

    // Start custom polling directly
    let isPolling = true;
    let pollInterval: number | null = null;

    const pollStatus = async () => {
      if (!isPolling) return;

      try {
        console.log('Polling benchmark status for chatbot:', chatbotId);
        const res = await getBenchmarkStatus(chatbotId);
        console.log('Benchmark status response:', res.data);
        setBenchmarkStatus(res.data);
        setPollingError(null);
        
        if (res.data.status === 'running') {
          setPolling(true);
          setInProgressLlm(res.data.result?.llm_name || res.data.llm_name || null);
          console.log('Benchmark still running, continuing to poll...');
          
          // Continue polling after 2 seconds
          pollInterval = setTimeout(pollStatus, 2000);
        } else {
          // Benchmark completed or failed
          console.log('Benchmark completed with status:', res.data.status);
          setPolling(false);
          setInProgressLlm(null);
          isPolling = false;
          
          // If benchmark completed, refresh the data after a short delay
          if (res.data.status === 'completed') {
            setTimeout(() => {
              refreshBenchmarkStatus();
            }, 2000);
          }
        }
      } catch (error: any) {
        console.error('Polling error:', error);
        setPollingError(getErrorMessage(error));
        setPolling(false);
        setInProgressLlm(null);
        isPolling = false;
      }
    };

    // Start polling
    pollStatus();

    // Return cleanup function
    return () => {
      isPolling = false;
      if (pollInterval) {
        clearTimeout(pollInterval);
      }
    };
  }, [chatbotId, polling, refreshBenchmarkStatus]);

  // Fetch all LLM scores and details on mount or when polling stops
  useEffect(() => {
    // Only fetch when not polling to avoid continuous API calls
    if (polling) return;
    
    const fetchAll = async () => {
      try {
        const res = await getBenchmarkDetails(chatbotId!);
        setBenchmarkChatbotName(res.data.chatbot_name);
        
        // Filter out incomplete data first
        const validDetails = (res.data.details || []).filter((row: any) => 
          row.regen_llm_name && 
          row.regen_llm_name !== 'Unknown' && 
          row.regen_llm_name !== null && 
          row.regen_llm_name !== undefined &&
          row.regen_temperature !== null && 
          row.regen_temperature !== undefined &&
          row.generated_sql && 
          row.generated_sql !== null &&
          row.score !== null && 
          row.score !== undefined
        );

        // Group by regen_llm_name and regen_temperature with proper validation
        const groupKey = (row: any) => `${row.regen_llm_name}_temp_${row.regen_temperature}`;
        const grouped: Record<string, any[]> = {};
        
        validDetails.forEach((row: any) => {
          const key = groupKey(row);
          if (!grouped[key]) grouped[key] = [];
          grouped[key].push(row);
        });

        const scoresArr = Object.entries(grouped).map(([key, rows]) => {
          const correct = rows.filter((r: any) => r.score === 1).length;
          const total = rows.length;
          const efficiency = total > 0 ? correct / total : 0;
          const [llm, , temp] = key.split('_');
          return {
            key,
            llm: rows[0].regen_llm_name,
            temperature: rows[0].regen_temperature,
            efficiency,
            correct,
            total,
          };
        });

        // Sort by efficiency descending and then by LLM name
        const sortedScoresArr = scoresArr.sort((a, b) => {
          if (b.efficiency !== a.efficiency) {
            return b.efficiency - a.efficiency;
          }
          return a.llm.localeCompare(b.llm);
        });

        setLlmScores(sortedScoresArr);
        if (sortedScoresArr.length > 0) {
          setSelectedLlm(sortedScoresArr[0].key);
        }
        
        // Log data for debugging
        console.log('Benchmark data processed:', {
          totalDetails: res.data.details?.length || 0,
          validDetails: validDetails.length,
          scoresArr: sortedScoresArr.length,
          chatbotName: res.data.chatbot_name
        });
      } catch (error) {
        console.error('Error fetching benchmark details:', error);
        setLlmScores([]);
        setBenchmarkChatbotName('');
        setSelectedLlm(null);
      }
    };
    fetchAll();
  }, [chatbotId, polling]);

  // Fetch details for selected LLM+temperature combination
  useEffect(() => {
    if (!selectedLlm) return;
    const fetchDetails = async () => {
      setDetailsLoading(true);
      try {
        // Parse the selectedLlm key to get LLM name and temperature
        const [llmName, , tempStr] = selectedLlm.split('_');
        const temperature = parseFloat(tempStr) || 0.7;
        const res = await getBenchmarkDetails(chatbotId!, llmName, temperature);
        setBenchmarkDetails(res.data.details);
        setScore(res.data.score);
      } catch {
        setBenchmarkDetails([]);
        setScore(null);
      }
      setDetailsLoading(false);
    };
    fetchDetails();
  }, [selectedLlm, chatbotId]);

  const handleShowDetails = () => setShowDetails(true);
  const handleCloseDetails = () => setShowDetails(false);

  const handleCleanupData = async () => {
    try {
      setIsCleaning(true);
      await cleanupBenchmarkData(chatbotId!);
      // Refresh the data after cleanup
      const res = await getBenchmarkDetails(chatbotId!);
      setBenchmarkChatbotName(res.data.chatbot_name);
      // Re-trigger the fetchAll effect
      setPolling(false);
    } catch (error) {
      console.error('Error cleaning up benchmark data:', error);
    } finally {
      setIsCleaning(false);
    }
  };

  const handleExportCSV = () => {
    if (!benchmarkDetails || benchmarkDetails.length === 0) return;
    const headers = ['Original SQL', 'NL Question', 'Generated SQL', 'Result'];
    const csvContent = [
      headers.join(','),
      ...benchmarkDetails.map(row => [
        `"${(row.original_sql || '').replace(/"/g, '""')}"`,
        `"${(row.generated_question || '').replace(/"/g, '""')}"`,
        `"${(row.generated_sql || '').replace(/"/g, '""')}"`,
        row.score ? 'Correct' : 'Incorrect'
      ].join(','))
    ].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `benchmark_details_${benchmarkChatbotName || 'chatbot'}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Render all LLM results as separate containers
  const hasResults = llmScores.length > 0;
  return (
    <div className="min-h-screen bg-white flex flex-col items-center pt-2">
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
      

      <div className="w-full flex items-center justify-between px-6" style={{ marginBottom: '1.5rem' }}>
        <h2 className="text-2xl font-bold text-gray-900">Test Suite</h2>
        <div className="flex items-center gap-2">
          <button
            className={`px-3 py-1 text-sm rounded transition ${
              isCleaning 
                ? 'bg-gray-100 text-gray-500 cursor-not-allowed' 
                : 'bg-red-100 text-red-700 hover:bg-red-200'
            }`}
            onClick={handleCleanupData}
            disabled={isCleaning}
            title="Clean up incomplete benchmark data"
          >
            {isCleaning ? 'Cleaning...' : 'Clean Data'}
          </button>
          <button
            className="p-2 rounded hover:bg-blue-50 transition"
            onClick={() => setShowMatrix(true)}
            style={{ background: 'none', border: 'none', cursor: 'pointer' }}
            title="View Benchmark Matrix"
          >
            <BarChart3 className="w-5 h-5 text-blue-600" />
          </button>
          <button
            className={`p-2 rounded transition ${
              isRefreshing
                ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
            }`}
            onClick={refreshBenchmarkStatus}
            disabled={isRefreshing}
            title="Refresh benchmark status"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>
      <BenchmarkMatrixModal
        open={showMatrix}
        onClose={() => setShowMatrix(false)}
        chatbotId={chatbotId || ''}
      />
      <div className="w-full flex justify-center px-2 sm:px-4 md:px-6" style={{ paddingBottom: '2rem' }}>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 w-full max-w-6xl transparent-scrollbar overflow-y-auto" style={{ maxHeight: '75vh' }}>
        {/* Always show in-progress LLM card if polling, even if no results */}
        {polling && (
            <div className="bg-white rounded-xl shadow-lg p-6 w-full flex flex-col items-center border-2 border-yellow-400 animate-pulse">
            <div className="text-lg font-bold mb-2 text-yellow-600">Benchmarking...</div>
            <div className="mb-2 text-gray-700 text-sm">Chatbot: <span className="font-semibold">{benchmarkChatbotName}</span></div>
            <div className="w-full flex flex-col items-center justify-center my-6">
              <ProgressBar progress={benchmarkStatus?.progress || 0} status={benchmarkStatus?.stage || 'Benchmark in progress...'} />
            </div>
            <div className="text-xs text-yellow-700 mt-2">Benchmark in progress... System is working, please wait.</div>
          </div>
        )}
        {/* Show all LLM result cards if any exist */}
          {llmScores.map(({ key, llm, temperature, efficiency, correct, total }) => {
            const isSelected = selectedLlm === key;
          const incorrect = total - correct;
          const pieData = {
            labels: ['Correct', 'Incorrect'],
            datasets: [{
              data: [correct, incorrect],
              backgroundColor: ['#1e3a8a', '#e5e7eb'],
              borderWidth: 0
            }]
          };

          return (
            <div
              key={key}
              className={`bg-white rounded-xl shadow-lg p-6 w-full flex flex-col items-center cursor-pointer hover:shadow-2xl transition-shadow border-2 ${isSelected ? 'border-blue-600' : 'border-transparent'}`}
              onClick={() => setSelectedLlm(key)}
              title={`Click to view details for ${llm} with temperature ${temperature}`}
            >
              <div className="text-lg font-bold mb-2 text-[#6658dd]">{llm}</div>
              <div className="mb-2 text-gray-700 text-sm">Chatbot: <span className="font-semibold">{benchmarkChatbotName}</span></div>
              <div className="mb-2 text-gray-600 text-xs bg-gray-100 px-2 py-1 rounded-full">
                Temperature: <span className="font-semibold">{temperature}</span>
              </div>
              <div className="w-32 h-32 my-2">
                <Pie data={pieData} options={{ plugins: { legend: { display: false } } }} />
              </div>
              <div className="text-base font-semibold mt-2">Efficiency: <span className="text-[#1e3a8a]">{Math.round(efficiency * 100)}%</span></div>
              <div className="text-xs text-gray-500 mt-1">{correct} correct / {total} total</div>
              <button
                className="mt-3 px-3 py-1 rounded bg-blue-100 text-blue-800 text-xs font-semibold border border-blue-300 hover:bg-blue-200"
                onClick={e => { e.stopPropagation(); setShowDetails(true); setSelectedLlm(key); }}
              >
                View Details
              </button>
            </div>
          );
        })}
        
        {/* If no results and not polling, show empty state */}
        {llmScores.length === 0 && !polling && (
          <div className="col-span-full flex flex-col items-center justify-center h-64">
            <div className="text-center text-gray-500">
              <p className="text-lg font-medium mb-2">
                No benchmark results available
              </p>
              <p className="max-w-md">
                Start a benchmark test to see results here.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
    
    {/* Details Modal */}
    {showDetails && (
      <div className="fixed inset-0 bg-black bg-opacity-40 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full mx-4 max-h-[80vh] overflow-y-auto p-6 relative">
          <button onClick={handleCloseDetails} className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-700"><X size={20} /></button>
          <h2 className="text-xl font-bold mb-4 text-[#1e3a8a]">
            Benchmark Details ({selectedLlm}
            {score?.temperature !== undefined && ` - Temperature: ${score.temperature}`})
          </h2>
          {detailsLoading ? <Loader /> : (
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-2 text-left font-semibold">Original SQL</th>
                  <th className="px-4 py-2 text-left font-semibold">NL Question</th>
                  <th className="px-4 py-2 text-left font-semibold">Generated SQL</th>
                  <th className="px-4 py-2 text-left font-semibold">LLM Used</th>
                  <th className="px-4 py-2 text-left font-semibold">Temperature</th>
                  <th className="px-4 py-2 text-center font-semibold">Result</th>
                </tr>
              </thead>
              <tbody>
                {benchmarkDetails.map((row, idx) => (
                  <tr key={idx} style={{ background: row.score ? '#dbeafe' : 'white' }}>
                    <td className="px-4 py-2 whitespace-pre-wrap max-w-xs font-mono text-xs">{row.original_sql}</td>
                    <td className="px-4 py-2 whitespace-pre-wrap max-w-xs">{row.generated_question}</td>
                    <td className="px-4 py-2 whitespace-pre-wrap max-w-xs font-mono text-xs">{row.generated_sql}</td>
                    <td className="px-4 py-2 text-left">{row.regen_llm_name || 'Unknown'}</td>
                    <td className="px-4 py-2 text-left">{row.regen_temperature ?? 'N/A'}</td>
                    <td className="px-4 py-2 text-center">
                      {row.score
                        ? <span style={{ color: 'darkblue', fontWeight: 'bold' }}>Correct</span>
                        : <span style={{ color: 'gray' }}>Incorrect</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="mt-6 flex justify-center">
            <button
              onClick={handleExportCSV}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors duration-200 font-medium"
            >
              <Download size={16} />
              Export to CSV
            </button>
          </div>
        </div>
      </div>
    )}
  </div>
  );
};

export default TestSuiteInterface;