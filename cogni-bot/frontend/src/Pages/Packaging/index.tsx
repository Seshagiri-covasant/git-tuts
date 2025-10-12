import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Settings, Database, Brain, FileText, BarChart3, Package, Monitor, Code, Check, Palette } from 'lucide-react';
import { getChatbotDetails, getPerformanceMetrics } from '../../services/api';
import { useToaster } from '../../Toaster/Toaster';
import Loader from '../../components/Loader';

interface ChatbotDetails {
  chatbot_id: string;
  chatbot_name: string;  // API returns this as 'chatbot_name'
  db_type: string;
  db_url: string;
  current_llm_name: string;
  temperature: number;
  template_name: string;
  status: string;
  efficiency?: number;
  created_at: string;
}

interface BenchmarkResult {
  query: string;
  generated_sql: string;
  execution_status: string;
  accuracy: number;
}

interface PerformanceMetrics {
  total_queries: number;
  correct_queries: number;
  efficiency: number;
  llm_name: string;
  temperature: number;
}

const colorPalettes = [
  {
    id: 'blue',
    name: 'Ocean Blue',
    primary: '#3B82F6',
    secondary: '#1E40AF',
    accent: '#60A5FA',
    background: '#F8FAFC'
  },
  {
    id: 'green',
    name: 'Forest Green', 
    primary: '#10B981',
    secondary: '#047857',
    accent: '#34D399',
    background: '#F0FDF4'
  },
  {
    id: 'purple',
    name: 'Royal Purple',
    primary: '#8B5CF6',
    secondary: '#5B21B6',
    accent: '#A78BFA',
    background: '#FAF5FF'
  },
  {
    id: 'orange',
    name: 'Sunset Orange',
    primary: '#F97316',
    secondary: '#C2410C',
    accent: '#FB923C',
    background: '#FFF7ED'
  },
  {
    id: 'teal',
    name: 'Deep Teal',
    primary: '#14B8A6',
    secondary: '#0F766E',
    accent: '#5EEAD4',
    background: '#F0FDFA'
  }
];

const PackagingPage: React.FC = () => {
  const { chatbotId } = useParams<{ chatbotId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToaster();
  
  const [chatbot, setChatbot] = useState<ChatbotDetails | null>(null);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [packageType, setPackageType] = useState<'standalone' | 'embedded' | null>(null);
  const [selectedPalette, setSelectedPalette] = useState(colorPalettes[0]);
  const [configConfirmed, setConfigConfirmed] = useState(false);

  useEffect(() => {
    if (chatbotId) {
      loadChatbotData();
    }
  }, [chatbotId]);

  const loadChatbotData = async () => {
    try {
      setIsLoading(true);
      
      // Load chatbot details first
      const chatbotResponse = await getChatbotDetails(chatbotId!);
      setChatbot(chatbotResponse.data);
      
      // Try to load performance metrics if available
      try {
        const performanceResponse = await getPerformanceMetrics(
          chatbotId!,
          chatbotResponse.data.current_llm_name,
          chatbotResponse.data.temperature
        );
        setPerformanceMetrics(performanceResponse.data);
      } catch (performanceError) {
        // Performance data may not be available - this is okay
        console.log('Performance data not available:', performanceError);
        setPerformanceMetrics(null);
      }
      
    } catch (error: any) {
      console.error('Error loading chatbot data:', error);
      showToast(`Failed to load chatbot data: ${error.response?.data?.error || error.message || 'Unknown error'}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePackageAndDeploy = () => {
    if (packageType === 'standalone') {
      // Open standalone chatbot in new window
      const standaloneUrl = `/standalone/${chatbotId}?palette=${selectedPalette.id}`;
      window.open(standaloneUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
      showToast('Standalone chatbot deployed successfully!', 'success');
    } else {
      showToast('Embedded deployment configuration saved!', 'success');
    }
  };

  if (isLoading) {
    return <Loader />;
  }

  if (!chatbot) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-medium text-gray-900 mb-2">Chatbot Not Found</h2>
          <button
            onClick={() => navigate('/')}
            className="text-blue-600 hover:text-blue-700"
          >
            Return to Chatbots
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/')}
                className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5 mr-2" />
                
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Package & Deploy</h1>
                <p className="text-gray-600">{chatbot.chatbot_name}</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Package className="w-6 h-6 text-blue-600" />
              <span className="text-sm font-medium text-gray-600">Deployment Configuration</span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Side - Configuration Overview */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Settings className="w-5 h-5 mr-2" />
                  Chatbot Configuration
                </h2>
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
                    <div className="px-3 py-2 bg-gray-50 rounded-md text-sm">{chatbot.chatbot_name}</div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                    <div className="px-3 py-2 bg-green-50 text-green-800 rounded-md text-sm font-medium">
                      {chatbot.status.toUpperCase()}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Database Configuration */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Database className="w-5 h-5 mr-2" />
                  Database Settings
                </h3>
              </div>
              <div className="p-6 space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                  <div className="px-3 py-2 bg-gray-50 rounded-md text-sm">{chatbot.db_type}</div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Connection</label>
                  <div className="px-3 py-2 bg-gray-50 rounded-md text-sm truncate">{chatbot.db_url}</div>
                </div>
              </div>
            </div>

            {/* AI Model Configuration */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Brain className="w-5 h-5 mr-2" />
                  AI Model Settings
                </h3>
              </div>
              <div className="p-6 space-y-3">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Model</label>
                    <div className="px-3 py-2 bg-gray-50 rounded-md text-sm">{chatbot.current_llm_name}</div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
                    <div className="px-3 py-2 bg-gray-50 rounded-md text-sm">{chatbot.temperature}</div>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Template</label>
                  <div className="px-3 py-2 bg-gray-50 rounded-md text-sm">{chatbot.template_name}</div>
                </div>
              </div>
            </div>

            {/* Benchmark Results */}
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center">
                  <BarChart3 className="w-5 h-5 mr-2" />
                  Performance Metrics
                </h3>
              </div>
              <div className="p-6">
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {performanceMetrics?.efficiency 
                        ? `${(performanceMetrics.efficiency * 100).toFixed(1)}%` 
                        : (chatbot.efficiency ? `${(chatbot.efficiency * 100).toFixed(1)}%` : 'N/A')
                      }
                    </div>
                    <div className="text-sm text-gray-600">Overall Efficiency</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {performanceMetrics?.total_queries || 0}
                    </div>
                    <div className="text-sm text-gray-600">Test Queries</div>
                  </div>
                </div>
                {performanceMetrics && performanceMetrics.total_queries > 0 && (
                  <div className="text-sm text-gray-600">
                    <div>LLM: {performanceMetrics.llm_name}</div>
                    <div>Temperature: {performanceMetrics.temperature}</div>
                    <div>Correct Queries: {performanceMetrics.correct_queries}/{performanceMetrics.total_queries}</div>
                    <div>Last benchmarked: {new Date(chatbot.created_at).toLocaleDateString()}</div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Side - Packaging Options */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-sm border">
              <div className="px-6 py-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900 flex items-center">
                  <Package className="w-5 h-5 mr-2" />
                  Deployment Options
                </h2>
              </div>
              <div className="p-6 space-y-4">
                {/* Package Type Selection */}
                <div className="space-y-3">
                  <label className="block text-sm font-medium text-gray-700">Select Deployment Type</label>
                  
                  {/* Standalone Option */}
                  <div
                    className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                      packageType === 'standalone' 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setPackageType('standalone')}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <Monitor className="w-6 h-6 text-blue-600 mr-3" />
                        <div>
                          <h3 className="font-medium text-gray-900">Standalone Application</h3>
                          <p className="text-sm text-gray-600">Deploy as an independent web application</p>
                        </div>
                      </div>
                      {packageType === 'standalone' && (
                        <Check className="w-5 h-5 text-blue-600" />
                      )}
                    </div>
                  </div>

                  {/* Embedded Option */}
                  <div
                    className={`p-4 border-2 rounded-lg cursor-pointer transition-all ${
                      packageType === 'embedded' 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setPackageType('embedded')}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center">
                        <Code className="w-6 h-6 text-green-600 mr-3" />
                        <div>
                          <h3 className="font-medium text-gray-900">Embedded Integration</h3>
                          <p className="text-sm text-gray-600">Integrate into existing application</p>
                        </div>
                      </div>
                      {packageType === 'embedded' && (
                        <Check className="w-5 h-5 text-blue-600" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Standalone Configuration */}
                {packageType === 'standalone' && (
                  <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3 flex items-center">
                      <Palette className="w-4 h-4 mr-2" />
                      Color Palette
                    </h4>
                    <div className="grid grid-cols-1 gap-3">
                      {colorPalettes.map((palette) => (
                        <div
                          key={palette.id}
                          className={`p-3 border-2 rounded-lg cursor-pointer transition-all ${
                            selectedPalette.id === palette.id
                              ? 'border-blue-500 bg-white'
                              : 'border-gray-200 hover:border-gray-300'
                          }`}
                          onClick={() => setSelectedPalette(palette)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center">
                              <div className="flex space-x-1 mr-3">
                                <div 
                                  className="w-4 h-4 rounded"
                                  style={{ backgroundColor: palette.primary }}
                                ></div>
                                <div 
                                  className="w-4 h-4 rounded"
                                  style={{ backgroundColor: palette.secondary }}
                                ></div>
                                <div 
                                  className="w-4 h-4 rounded"
                                  style={{ backgroundColor: palette.accent }}
                                ></div>
                              </div>
                              <span className="font-medium text-gray-900">{palette.name}</span>
                            </div>
                            {selectedPalette.id === palette.id && (
                              <Check className="w-4 h-4 text-blue-600" />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="mt-4 p-3 bg-white rounded border">
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={configConfirmed}
                          onChange={(e) => setConfigConfirmed(e.target.checked)}
                          className="mr-2"
                        />
                        <span className="text-sm text-gray-700">
                          I confirm that all configurations and color palette selections are correct for packaging
                        </span>
                      </label>
                    </div>
                  </div>
                )}

                {/* Embedded Configuration */}
                {packageType === 'embedded' && (
                  <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-medium text-gray-900 mb-3">Integration Requirements</h4>
                    <div className="space-y-3 text-sm text-gray-600">
                      <div className="flex items-start">
                        <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                        <div>
                          <strong>API Endpoints:</strong> RESTful API with authentication tokens
                        </div>
                      </div>
                      <div className="flex items-start">
                        <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                        <div>
                          <strong>Frontend Widget:</strong> React/Vue.js component library
                        </div>
                      </div>
                      <div className="flex items-start">
                        <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                        <div>
                          <strong>Database Migration:</strong> Schema deployment scripts
                        </div>
                      </div>
                      <div className="flex items-start">
                        <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                        <div>
                          <strong>Security:</strong> OAuth 2.0 integration and SSL certificates
                        </div>
                      </div>
                      <div className="flex items-start">
                        <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                        <div>
                          <strong>Documentation:</strong> Integration guide and API reference
                        </div>
                      </div>
                    </div>
                    <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                      <p className="text-sm text-yellow-800">
                        <strong>Note:</strong> Embedded integration features are part of our enterprise plan. 
                        Contact sales for detailed implementation guidelines.
                      </p>
                    </div>
                  </div>
                )}

                {/* Deploy Button */}
                {packageType && (
                  <div className="mt-6">
                    <button
                      onClick={handlePackageAndDeploy}
                      disabled={packageType === 'standalone' && !configConfirmed}
                      className={`w-full py-3 px-4 rounded-lg font-medium transition-colors ${
                        (packageType === 'standalone' && !configConfirmed)
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-blue-600 hover:bg-blue-700 text-white'
                      }`}
                    >
                      {packageType === 'standalone' ? 'Package & Deploy Standalone' : 'Configure Embedded Integration'}
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PackagingPage; 