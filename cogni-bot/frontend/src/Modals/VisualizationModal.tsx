import React, { useEffect, useRef, useState } from 'react';
import { X, BarChart3, TrendingUp, AlertCircle, Clock, Target, Activity, Download, Maximize2, RefreshCw, Info, Palette } from 'lucide-react';
import { Chart as ChartJS, registerables } from 'chart.js';
import { Chart } from 'react-chartjs-2';
import ChartStyleCustomizer from '../components/ChartStyleCustomizer';

// Register Chart.js components
ChartJS.register(...registerables);

interface VisualizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  chartConfig: any;
  isLoading: boolean;
  userQuery?: string;
  onRegenerate?: () => void;
}

const VisualizationModal: React.FC<VisualizationModalProps> = ({
  isOpen,
  onClose,
  chartConfig,
  isLoading,
  userQuery,
  onRegenerate,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const stylerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [chartStats, setChartStats] = useState<any>(null);
  const [styleCustomizerOpen, setStyleCustomizerOpen] = useState(false);
  const [currentChartConfig, setCurrentChartConfig] = useState<any>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (styleCustomizerOpen) {
          setStyleCustomizerOpen(false);
        } else {
          onClose();
        }
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      
      // Don't close if clicking on the style customizer
      if (stylerRef.current && stylerRef.current.contains(target)) {
        return;
      }
      
      // Don't close if clicking on the modal itself
      if (modalRef.current && !modalRef.current.contains(target)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.addEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.removeEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose, styleCustomizerOpen]);

  // Initialize chart config
  useEffect(() => {
    if (chartConfig) {
      setCurrentChartConfig(chartConfig);
    }
  }, [chartConfig]);

  // Calculate chart statistics
  useEffect(() => {
    if (currentChartConfig && currentChartConfig.data && currentChartConfig.data.datasets) {
      const datasets = currentChartConfig.data.datasets;
      const totalDataPoints = datasets.reduce((sum: number, dataset: any) => sum + (dataset.data?.length || 0), 0);
      const chartType = currentChartConfig.type || 'unknown';
      
      setChartStats({
        totalDataPoints,
        chartType: chartType.charAt(0).toUpperCase() + chartType.slice(1),
        datasetsCount: datasets.length,
        labelsCount: currentChartConfig.data.labels?.length || 0
      });
    }
  }, [currentChartConfig]);

  if (!isOpen) return null;

  const renderLoadingState = () => (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="relative mb-8">
        <div className="w-20 h-20 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <Activity className="w-8 h-8 text-blue-600 animate-pulse" />
        </div>
      </div>
      <div className="text-center max-w-md">
        <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-3">
          Creating Visualization...
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Covasant AI is analyzing your data and selecting the perfect chart type for maximum impact
        </p>
        <div className="flex items-center justify-center space-x-2">
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce"></div>
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-3 h-3 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
      </div>
    </div>
  );

  const downloadChart = () => {
    if (chartRef.current) {
      const url = chartRef.current.toBase64Image();
      const link = document.createElement('a');
      link.download = `chart-${Date.now()}.png`;
      link.href = url;
      link.click();
    }
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const handleStyleChange = (newConfig: any) => {
    setCurrentChartConfig(newConfig);
  };

  const toggleStyleCustomizer = (e: React.MouseEvent) => {
    e.stopPropagation();
    setStyleCustomizerOpen(!styleCustomizerOpen);
  };

  const renderChart = () => {
    if (isLoading) {
      return renderLoadingState();
    }

    if (!currentChartConfig) {
      return (
        <div className="flex flex-col items-center justify-center py-16">
          <AlertCircle className="w-16 h-16 text-gray-400 mb-4" />
          <h3 className="text-lg font-semibold text-gray-600 mb-2">No Visualization Available</h3>
          <p className="text-gray-500 text-center max-w-md">
            Unable to generate a chart from the provided data. Please try with different data.
          </p>
        </div>
      );
    }

    if (currentChartConfig.error) {
      return (
        <div className="bg-gradient-to-br from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 border border-red-200 dark:border-red-700 rounded-xl p-8">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">Visualization Error</h3>
              <p className="text-sm text-red-600 dark:text-red-300">Unable to generate chart from data</p>
            </div>
          </div>
          <div className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-4">
            <p className="text-red-700 dark:text-red-300 text-sm font-medium">{currentChartConfig.error}</p>
          </div>
        </div>
      );
    }

    try {
      const { type, data, options } = currentChartConfig;
      
      return (
        <div className="space-y-6">
          {/* Chart Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-start space-x-4">
              <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                <BarChart3 className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  {currentChartConfig.options?.plugins?.title?.text || 'Data Visualization'}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Interactive {chartStats?.chartType} chart with {chartStats?.totalDataPoints} data points
                </p>
              </div>
            </div>
            
            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              <button
                onClick={toggleStyleCustomizer}
                className={`p-2 transition-colors rounded-lg ${
                  styleCustomizerOpen 
                    ? 'text-purple-600 bg-purple-50 dark:text-purple-400 dark:bg-purple-900/30' 
                    : 'text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/30'
                }`}
                title="Customize Chart Style"
              >
                <Palette className="w-4 h-4" />
              </button>
              <button
                onClick={downloadChart}
                className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/30"
                title="Download Chart"
              >
                <Download className="w-4 h-4" />
              </button>
              <button
                onClick={toggleFullscreen}
                className="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/30"
                title="Toggle Fullscreen"
              >
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Query Context */}
          {userQuery && (
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-700 rounded-xl p-4">
              <div className="flex items-center space-x-2 mb-2">
                <Target className="w-4 h-4 text-blue-600 dark:text-blue-400" />
                <span className="text-sm font-medium text-blue-800 dark:text-blue-300">Visualization Context</span>
              </div>
              <p className="text-sm text-blue-700 dark:text-blue-300 font-medium">
                "{userQuery}"
              </p>
            </div>
          )}

          {/* Chart Container */}
          <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-inner">
            <div className={`${isFullscreen ? 'h-[70vh]' : 'h-96'} w-full transition-all duration-300`}>
              <Chart
                ref={chartRef}
                type={type as any}
                data={data}
                options={{
                  ...options,
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    ...options?.plugins,
                    legend: {
                      ...options?.plugins?.legend,
                      labels: {
                        usePointStyle: true,
                        padding: 20,
                        font: {
                          size: 12,
                          weight: 500
                        }
                      }
                    }
                  },
                  elements: {
                    bar: {
                      borderRadius: 4,
                    },
                    point: {
                      radius: 4,
                      hoverRadius: 6,
                    }
                  }
                }}
              />
            </div>
          </div>

          {/* Chart Statistics */}
          {chartStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{chartStats.totalDataPoints}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Data Points</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">{chartStats.chartType}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Chart Type</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{chartStats.datasetsCount}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Data Series</div>
              </div>
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">{chartStats.labelsCount}</div>
                <div className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Categories</div>
              </div>
            </div>
          )}

          {/* Footer Info */}
          <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
            <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-4 h-4" />
              <span>Generated at {new Date().toLocaleTimeString()}</span>
            </div>
            <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
              <Info className="w-4 h-4" />
              <span>Powered by Covasant Visualization Engine</span>
            </div>
          </div>
        </div>
      );
    } catch (error) {
      return (
        <div className="bg-gradient-to-br from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 border border-red-200 dark:border-red-700 rounded-xl p-8">
          <div className="flex items-center space-x-3 mb-4">
            <AlertCircle className="w-8 h-8 text-red-600 dark:text-red-400" />
            <div>
              <h3 className="text-lg font-semibold text-red-800 dark:text-red-200">Rendering Error</h3>
              <p className="text-sm text-red-600 dark:text-red-300">Chart configuration is invalid</p>
            </div>
          </div>
        </div>
      );
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <div
          ref={modalRef}
          className={`bg-white dark:bg-gray-800 rounded-2xl shadow-2xl ${
            isFullscreen ? 'w-[95vw] h-[95vh]' : 'max-w-6xl w-full max-h-[90vh]'
          } overflow-y-auto border border-gray-200 dark:border-gray-700 transition-all duration-300 ${
            styleCustomizerOpen ? 'mr-96' : ''
          }`}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-t-2xl">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-4 h-4 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  Covasant Visualization Studio
                </h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  AI-powered insights through interactive charts
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors rounded-lg hover:bg-white/50 dark:hover:bg-gray-700/50"
            >
              <X size={24} />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {renderChart()}
          </div>

          {/* Footer */}
          {!isLoading && (
            <div className="flex justify-between items-center p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 rounded-b-2xl">
              <div className="flex items-center space-x-4">
                <button
                  onClick={onRegenerate}
                  disabled={!onRegenerate || isLoading}
                  className={`flex items-center space-x-2 px-4 py-2 transition-colors ${
                    onRegenerate && !isLoading
                      ? 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200' 
                      : 'text-gray-400 dark:text-gray-500 cursor-not-allowed'
                  }`}
                  title={onRegenerate ? (isLoading ? "Regenerating..." : "Regenerate Chart") : "Regeneration not available"}
                >
                  <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                  <span className="text-sm">{isLoading ? 'Regenerating...' : 'Regenerate'}</span>
                </button>
              </div>
              <button
                onClick={onClose}
                className="px-6 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 font-medium shadow-md hover:shadow-lg"
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Chart Style Customizer */}
      <div ref={stylerRef}>
        <ChartStyleCustomizer
          chartConfig={currentChartConfig}
          onStyleChange={handleStyleChange}
          isOpen={styleCustomizerOpen}
          onToggle={toggleStyleCustomizer}
        />
      </div>
    </>
  );
};

export default VisualizationModal; 