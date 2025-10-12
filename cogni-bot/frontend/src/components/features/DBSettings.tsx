import React from 'react';
import { X } from 'lucide-react';
import { useAppContext } from '../../context/AppContext';
import { DB_PROVIDERS } from '../../utils/constants';

const DBSettings: React.FC = () => {
  const { dbSettings, updateDBSettings, setActiveSettingsTab } = useAppContext();

  return (
    <div className="h-full overflow-y-auto bg-white dark:bg-gray-900 p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">Database Settings</h2>
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
            Database Provider
          </label>
          <select
            value={dbSettings.provider}
            onChange={e => updateDBSettings({ provider: e.target.value })}
            className="w-full p-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          >
            {DB_PROVIDERS.map(provider => (
              <option key={provider.id} value={provider.id}>
                {provider.name}
              </option>
            ))}
          </select>
        </div>
        
        {dbSettings.provider === 'supabase' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Connection String
            </label>
            <input
              type="password"
              value={dbSettings.connectionString || ''}
              onChange={e => updateDBSettings({ connectionString: e.target.value })}
              placeholder="supabase://..."
              className="w-full p-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Your connection string is encrypted and stored securely.
            </p>
          </div>
        )}
        
        {(dbSettings.provider === 'firebase' || dbSettings.provider === 'mongodb') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Region
            </label>
            <select
              value={dbSettings.region}
              onChange={e => updateDBSettings({ region: e.target.value })}
              className="w-full p-2 border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            >
              <option value="us-east-1">US East (N. Virginia)</option>
              <option value="us-west-1">US West (N. California)</option>
              <option value="eu-west-1">EU (Ireland)</option>
              <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
            </select>
          </div>
        )}
        
        <div className="flex items-center">
          <input
            type="checkbox"
            id="saveHistory"
            checked={dbSettings.saveHistory}
            onChange={e => updateDBSettings({ saveHistory: e.target.checked })}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label htmlFor="saveHistory" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
            Save conversation history
          </label>
        </div>
        
        <button
          className="w-full bg-[#6658dd] hover:bg-[#6658dd] text-white py-2 px-4 rounded-md transition-colors"
        >
          Save Settings
        </button>
        
        <div className="rounded-md bg-amber-50 dark:bg-amber-900/30 p-3 mt-4">
          <div className="flex">
            <div className="text-amber-800 dark:text-amber-300 text-sm">
              <p className="font-medium">Note:</p>
              <p>Changes to database settings will take effect on the next application restart.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DBSettings;