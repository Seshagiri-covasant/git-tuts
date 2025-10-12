import React, { useEffect, useRef } from 'react';
import { X, TrendingUp, AlertCircle, Lightbulb, Clock, Target, Activity } from 'lucide-react';

interface BAInsightsModalProps {
  isOpen: boolean;
  onClose: () => void;
  summary: string | null;
  isLoading: boolean;
  userQuery?: string;
  onRegenerate?: () => void;
}

const BAInsightsModal: React.FC<BAInsightsModalProps> = ({
  isOpen,
  onClose,
  summary,
  isLoading,
  userQuery,
  onRegenerate,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    const handleClickOutside = (e: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
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
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const renderLoadingState = () => (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
        <div className="absolute inset-0 flex items-center justify-center">
          <Activity className="w-6 h-6 text-blue-600 animate-pulse" />
        </div>
      </div>
      <div className="mt-6 text-center">
        <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300">
          Analyzing Data...
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
          Covasant expert BA is extracting key insights from your data
        </p>
        <div className="flex items-center justify-center mt-4 space-x-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
        </div>
      </div>
    </div>
  );

  const renderContent = () => {
    if (isLoading) {
      return renderLoadingState();
    }

    if (!summary) {
      return (
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="w-12 h-12 text-gray-400 mb-4" />
          <p className="text-gray-500 text-center">No insights available</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        {/* Header with icon and title */}
        <div className="flex items-start space-x-4">
          <div className="flex-shrink-0 w-12 h-12 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-xl flex items-center justify-center shadow-lg">
            <Lightbulb className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Executive Insights
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Covasant AI-powered business analysis with 20+ years of expertise
            </p>
          </div>
        </div>

        {/* Query context if available */}
        {userQuery && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4">
            <div className="flex items-center space-x-2 mb-2">
              <Target className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-sm font-medium text-blue-800 dark:text-blue-300">Analysis Context</span>
            </div>
            <p className="text-sm text-blue-700 dark:text-blue-300 font-medium">
              "{userQuery}"
            </p>
          </div>
        )}

        {/* Main insights content */}
        <div className="bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-2 mb-4">
            <TrendingUp className="w-5 h-5 text-green-600 dark:text-green-400" />
            <span className="font-semibold text-gray-900 dark:text-gray-100">Key Findings</span>
          </div>
          
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <div className="text-gray-800 dark:text-gray-200 leading-relaxed whitespace-pre-line">
              {summary}
            </div>
          </div>
        </div>

        {/* Footer with timestamp */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
            <Clock className="w-4 h-4" />
            <span>Generated at {new Date().toLocaleTimeString()}</span>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            Powered by Covasant BA AI Analyst
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div
        ref={modalRef}
        className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto border border-gray-200 dark:border-gray-700"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-yellow-50 to-orange-50 dark:from-yellow-900/20 dark:to-orange-900/20 rounded-t-2xl">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-yellow-400 to-orange-500 rounded-lg flex items-center justify-center">
              <Lightbulb className="w-4 h-4 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                Covasant Business Analyst Insights
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Strategic intelligence for executive decision-making
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
          {renderContent()}
        </div>

        {/* Footer */}
        {!isLoading && (
          <div className="flex items-center justify-between p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 rounded-b-2xl">
            <div className="text-xs text-gray-500 dark:text-gray-400">{userQuery ? `Prompt: ${userQuery}` : ''}</div>
            <div className="flex items-center gap-3">
              {onRegenerate && (
                <button
                  onClick={onRegenerate}
                  className="px-4 py-2 bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200 text-sm"
                  title="Regenerate BA Insights"
                >
                  Regenerate
                </button>
              )}
              <button
                onClick={onClose}
                className="px-6 py-2 bg-gradient-to-r from-gray-600 to-gray-700 text-white rounded-lg hover:from-gray-700 hover:to-gray-800 transition-all duration-200 font-medium shadow-md hover:shadow-lg"
              >
                Close
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default BAInsightsModal;
