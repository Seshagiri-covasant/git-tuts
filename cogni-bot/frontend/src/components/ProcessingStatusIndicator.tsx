import React from 'react';
import { Brain, Database, CheckCircle, AlertCircle, Loader } from 'lucide-react';

interface ProcessingStatus {
  current_step: string;
  progress: number;
  message: string;
}

interface ProcessingStatusIndicatorProps {
  status: ProcessingStatus | null;
  isVisible: boolean;
}

const ProcessingStatusIndicator: React.FC<ProcessingStatusIndicatorProps> = ({ status, isVisible }) => {
  // Fully disable the status window rendering per requirement
  void status; // keep references to avoid unused var warnings
  void isVisible;
  return null;
  const getStepIcon = (step: string) => {
    switch (step) {
      case 'initializing':
      case 'preparing':
        return <Brain className="w-4 h-4" />;
      case 'generating':
        return <Loader className="w-4 h-4 animate-spin" />;
      case 'cleaning':
        return <CheckCircle className="w-4 h-4" />;
      case 'executing':
        return <Database className="w-4 h-4" />;
      case 'formatting':
        return <CheckCircle className="w-4 h-4" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Loader className="w-4 h-4 animate-spin" />;
    }
  };

  const getStepColor = (step: string) => {
    switch (step) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'error':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-blue-600 bg-blue-50 border-blue-200';
    }
  };

  const getProgressColor = (step: string) => {
    switch (step) {
      case 'completed':
        return 'bg-green-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-blue-500';
    }
  };

  return null;
};

export default ProcessingStatusIndicator; 