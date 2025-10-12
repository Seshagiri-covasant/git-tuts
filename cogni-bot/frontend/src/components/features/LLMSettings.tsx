import React from 'react';
import { X } from 'lucide-react';
import { useAppContext } from '../../context/AppContext';
import { AVAILABLE_LLM_MODELS } from '../../utils/constants';

const LLMSettings: React.FC = () => {
  const { llmSettings, updateLLMSettings, setActiveSettingsTab } = useAppContext();

  return (
    <div className="h-full overflow-y-auto bg-white dark:bg-gray-900 p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">LLM Settings</h2>
        <button 
          onClick={() => setActiveSettingsTab(null)} 
          className="p-1 rounded-md text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          <X size={18} />
        </button>
      </div>
      
      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Model
          </label>
          <select
            value={llmSettings.model}
            onChange={e => updateLLMSettings({ model: e.target.value })}
            className="w-full p-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          >
            {AVAILABLE_LLM_MODELS.map(model => (
              <option key={model.id} value={model.id}>
                {model.name}
              </option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Temperature
          </label>
          <input
            type="number"
            min="0"
            max="2"
            step="0.001"
            value={llmSettings.temperature}
            onChange={e => updateLLMSettings({ temperature: parseFloat(e.target.value) || 0 })}
            className="w-full p-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            placeholder="1.0"
          />
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
            <span>Precise (0)</span>
            <span>Balanced (1)</span>
            <span>Creative (2)</span>
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Max Tokens: {llmSettings.maxTokens}
          </label>
          <input
            type="range"
            min="100"
            max="4000"
            step="100"
            value={llmSettings.maxTokens}
            onChange={e => updateLLMSettings({ maxTokens: parseInt(e.target.value) })}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
            <span>100</span>
            <span>2000</span>
            <span>4000</span>
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Top P: {llmSettings.topP}
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={llmSettings.topP}
            onChange={e => updateLLMSettings({ topP: parseFloat(e.target.value) })}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Frequency Penalty: {llmSettings.frequencyPenalty}
          </label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={llmSettings.frequencyPenalty}
            onChange={e => updateLLMSettings({ frequencyPenalty: parseFloat(e.target.value) })}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Presence Penalty: {llmSettings.presencePenalty}
          </label>
          <input
            type="range"
            min="0"
            max="2"
            step="0.1"
            value={llmSettings.presencePenalty}
            onChange={e => updateLLMSettings({ presencePenalty: parseFloat(e.target.value) })}
            className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer"
          />
        </div>
        
        <button
          className="w-full bg-[#6658dd] hover:bg-[#6658dd] text-white py-2 px-4 rounded-md transition-colors"
        >
          Apply Settings
        </button>
      </div>
    </div>
  );
};

export default LLMSettings;