import React, { useState } from 'react';
import { X, Brain, Save, RotateCcw, Copy } from 'lucide-react';
import { updateLLMSettings, restartChatbot, startBenchmark } from '../services/api';
import { useToaster } from '../Toaster/Toaster';
import { useAppContext } from '../context/AppContext';
import Loader from './Loader';

const API_BASE_URL = import.meta.env.DEV ? 'http://localhost:5000' : 'http://localhost:5000';

interface LLMEditorProps {
  chatbotId: string;
  currentLLM: string;
  currentTemperature?: number;
  onClose: () => void;
  onUpdate: (newLLM: string, newTemperature?: number) => void; // Updated to include temperature
}

const LLMEditor: React.FC<LLMEditorProps> = ({
  chatbotId,
  currentLLM,
  currentTemperature = 0.7,
  onClose,
  onUpdate,
}) => {
  const [selectedLLM, setSelectedLLM] = useState(currentLLM);
  const [temperature, setTemperature] = useState(currentTemperature);
  const [isLoading, setIsLoading] = useState(false);
  const [apiKeySource, setApiKeySource] = useState<'env'|'global'|'local'>('env');
  const [initialApiKeySource, setInitialApiKeySource] = useState<'env'|'global'|'local'>('env');
  const [localKey, setLocalKey] = useState('');
  const [globalKeyMasked, setGlobalKeyMasked] = useState<string>('');
  const [localKeyMasked, setLocalKeyMasked] = useState<string>('');
  const [globalKeyInput, setGlobalKeyInput] = useState<string>('');
  const [copying, setCopying] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const { showToast } = useToaster();
  const { setBenchmarkingChatbotId } = useAppContext();

  const llmOptions = [
    { value: 'COHERE', label: 'Cohere' },
    { value: 'CLAUDE', label: 'Claude 3.5 Sonnet' },
    { value: 'GEMINI', label: 'Gemini 1.5 Pro' },
    { value: 'OPENAI', label: 'OpenAI GPT-4o Mini' },
    { value: 'AZURE', label: 'Azure ChatGPT-4o Mini' },
  ];

  const allowedLLMs = ["COHERE", "CLAUDE", "GEMINI", "OPENAI", "AZURE"];
  const [llmError, setLlmError] = useState<string>("");

  const handleLLMChange = (llm: string) => {
    setSelectedLLM(llm);
    setHasChanges(llm !== currentLLM || temperature !== currentTemperature);
    if (!allowedLLMs.includes(llm)) {
      setLlmError("Selected LLM is not supported.");
    } else {
      setLlmError("");
    }
  };

  // Load current source and masked key for selected LLM
  const loadLLMSource = async (llm: string) => {
    try {
      const resGlobal = await fetch(`${API_BASE_URL}/api/settings/ai?llm=${encodeURIComponent(llm)}`);
      const resLocal = await fetch(`${API_BASE_URL}/api/settings/ai/chatbot/${encodeURIComponent(chatbotId)}?llm=${encodeURIComponent(llm)}`);
      const data = await resGlobal.json();
      const localData = await resLocal.json();
      if (data?.settings) {
        const src = (localData?.settings?.api_key_source as 'env'|'global'|'local') || (data.settings.api_key_source as 'env'|'global'|'local');
        setApiKeySource(src);
        setInitialApiKeySource(src);
        const globalMasked = localData?.settings?.global_api_key_masked || data?.settings?.global_api_key_masked || '';
        if (globalMasked) {
          setGlobalKeyMasked(globalMasked);
          setGlobalKeyInput(globalMasked);
        } else {
          setGlobalKeyMasked('');
          setGlobalKeyInput('');
        }
        const localMasked = localData?.settings?.local_api_key_masked || '';
        setLocalKeyMasked(localMasked);
        // Ensure local textbox shows masked value by default
        setLocalKey(localMasked || '');
        // No need to fetch/hold local key contents; just detect presence for UX
      }
    } catch {}
  };

  React.useEffect(() => { loadLLMSource(selectedLLM); }, [selectedLLM]);

  const handleTemperatureChange = (temp: number) => {
    setTemperature(temp);
    setHasChanges(selectedLLM !== currentLLM || temp !== currentTemperature);
  };

  const canSave = !isLoading && (
    hasChanges ||
    apiKeySource !== initialApiKeySource ||
    (apiKeySource === 'local') ||
    (apiKeySource === 'global')
  );

  const handleSave = async () => {
    if (llmError || !canSave) return;
    
    setIsLoading(true);
    // Immediately set benchmark status to show UI feedback - BEFORE any API calls
    setBenchmarkingChatbotId(chatbotId);
    
    try {
      // Persist per-LLM key source/global key when source is env/global
      if (apiKeySource !== 'local') {
        await fetch(`${API_BASE_URL}/api/settings/ai`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            llm_name: selectedLLM,
            api_key_source: apiKeySource,
            // For GLOBAL send key only if user changed from masked
            ...(apiKeySource==='global' && globalKeyInput && globalKeyInput!==globalKeyMasked ? { global_api_key: globalKeyInput } : {})
          })
        });
      }

      // For LOCAL, always flip source via chatbot endpoint; local key is optional
      if (apiKeySource==='local') {
        await fetch(`${API_BASE_URL}/api/settings/ai/chatbot/${encodeURIComponent(chatbotId)}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key_source: 'local', local_api_key: localKey || '', llm_name: selectedLLM })
        });
      }

      await updateLLMSettings(chatbotId, selectedLLM, temperature);
      await restartChatbot(chatbotId);
      
      // Small delay to ensure database transaction is committed before benchmark
      await new Promise(resolve => setTimeout(resolve, 500));
      
      await startBenchmark(chatbotId, temperature);
      onUpdate(selectedLLM, temperature); // Pass both values
      showToast('LLM settings updated successfully', 'success');
      onClose();
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || error.message || 'Failed to update LLM settings';
      showToast(errorMessage, 'error');
      // Clear benchmark status on error
      setBenchmarkingChatbotId(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {isLoading && <Loader />}
      
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center">
              <Brain className="w-5 h-5 mr-2 text-blue-600" />
              <h2 className="text-lg font-semibold">Edit LLM Settings</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          {/* Content */}
          <div className="px-6 py-4 overflow-y-auto flex-1">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select LLM Model
                </label>
                <select
                  value={selectedLLM}
                  onChange={(e) => handleLLMChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {llmOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {llmError && (
                  <div className="text-red-600 text-sm mt-2">{llmError}</div>
                )}
              </div>

              {/* Simplified API Key Section */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">API Key</label>
                <div className="relative">
                  <input
                    disabled={apiKeySource==='env'}
                    value={
                      apiKeySource==='local'
                        ? (localKey || localKeyMasked || '')
                        : (apiKeySource==='global'
                            ? (globalKeyInput || globalKeyMasked || '')
                            : '')
                    }
                    onChange={e=> apiKeySource==='local' ? setLocalKey(e.target.value) : setGlobalKeyInput(e.target.value)}
                    placeholder={apiKeySource==='env' ? 'Using default key' : ((apiKeySource==='local' ? (localKeyMasked || 'Enter new key to override') : (globalKeyMasked || 'Enter new key to override')))}
                    className="w-full px-3 py-2 pr-10 border rounded-md disabled:bg-gray-100"
                  />
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={async ()=>{
                        try{
                          setCopying(true);
                          const base = `${API_BASE_URL}/api/settings/ai`;
                          let fullKey='';
                          if(apiKeySource==='global'){
                            const r = await fetch(`${base}/global-key?llm=${encodeURIComponent(selectedLLM)}`);
                            const j = await r.json();
                            fullKey = j?.global_api_key || '';
                          } else if(apiKeySource==='local'){
                            const r = await fetch(`${base}/local-key?chatbot_id=${encodeURIComponent(chatbotId)}&llm=${encodeURIComponent(selectedLLM)}`);
                            const j = await r.json();
                            fullKey = j?.local_api_key || '';
                          }
                          if(fullKey){
                            await navigator.clipboard.writeText(fullKey);
                          }
                        } finally {
                          setCopying(false);
                        }
                      }}
                      disabled={apiKeySource==='env' || copying}
                      className="text-gray-500 disabled:text-gray-300"
                      aria-label="Copy full key"
                    >
                      <Copy className="w-4 h-4"/>
                    </button>
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-2">This is {(apiKeySource==='env' ? 'DEFAULT' : apiKeySource.toUpperCase())} key</div>
                <div className="flex items-center gap-6 mt-3">
                  {apiKeySource==='global' && (
                    <>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={false} onChange={()=>setApiKeySource('local')} />
                        <span>Use Local key</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={false} onChange={()=>setApiKeySource('env')} />
                        <span>Use default key (.env)</span>
                      </label>
                    </>
                  )}
                  {apiKeySource==='local' && (
                    <>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={false} onChange={()=>setApiKeySource('global')} />
                        <span>Use Global key</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={false} onChange={()=>setApiKeySource('env')} />
                        <span>Use default key (.env)</span>
                      </label>
                    </>
                  )}
                  {apiKeySource==='env' && (
                    <>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={false} onChange={()=>setApiKeySource('global')} />
                        <span>Use Global key</span>
                      </label>
                      <label className="flex items-center gap-2">
                        <input type="checkbox" checked={false} onChange={()=>setApiKeySource('local')} />
                        <span>Use Local key</span>
                      </label>
                    </>
                  )}
                </div>
              </div>

              {/* Temperature Configuration */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Temperature
                </label>
                <div className="space-y-2">
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.001"
                    value={temperature}
                    onChange={(e) => handleTemperatureChange(parseFloat(e.target.value) || 0)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="0.7"
                  />
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>0.0 (Focused)</span>
                    <span>1.0 (Creative)</span>
                  </div>
                  <p className="text-sm text-gray-600">
                    Enter precise temperature value (0.0 to 1.0). Lower values make the AI more focused and deterministic. Higher values make it more creative and diverse.
                  </p>
                </div>
              </div>

              {hasChanges && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                  <div className="flex items-center">
                    <RotateCcw className="w-4 h-4 text-yellow-600 mr-2" />
                    <span className="text-sm text-yellow-800">
                      Changes will restart the chatbot and re-run benchmark for new temperature
                    </span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-between">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={!canSave}
              className={`px-4 py-2 rounded-md transition-colors flex items-center ${
                !canSave
                  ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              <Save className="w-4 h-4 mr-2" />
              Save & Restart
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default LLMEditor; 