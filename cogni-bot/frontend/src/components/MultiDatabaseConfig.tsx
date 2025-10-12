import React, { useState } from 'react';
import { Database, Plus, X, Check, Eye, EyeOff, AlertCircle, Info } from 'lucide-react';

interface DatabaseConnection {
  id: string;
  name: string;
  type: 'PostgreSQL' | 'SQLite' | 'BigQuery' | 'MySQL' | 'MSSQL';
  host?: string;
  port?: number;
  database?: string;
  username?: string;
  password?: string;
  projectId?: string;
  datasetId?: string;
  credentialsJson?: string;
  driver?: string; // for MSSQL optional ODBC driver name
  isConnected?: boolean;
  error?: string;
  schemaName?: string;
  availableSchemas?: string[];
  availableTables?: string[];
  selectedTables?: string[];
  isLoadingTables?: boolean;
  tablesError?: string;
}

interface MultiDatabaseConfigProps {
  connections: DatabaseConnection[];
  onConnectionsChange: (connections: DatabaseConnection[]) => void;
  errors: Record<string, string>;
  onTestConnection?: (connection: DatabaseConnection) => Promise<{ success: boolean; schemas?: string[] }>;
  onFetchTables?: (connection: DatabaseConnection) => Promise<{ success: boolean; tables?: string[]; error?: string }>;
  onTableSelectionChange?: (hasSelectedTables: boolean) => void;
}

const MultiDatabaseConfig: React.FC<MultiDatabaseConfigProps> = ({
  connections,
  onConnectionsChange,
  errors,
  onTestConnection,
  onFetchTables,
  onTableSelectionChange
}) => {
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});
  const [showCredentials, setShowCredentials] = useState<Record<string, boolean>>({});
  const [testingConnections, setTestingConnections] = useState<Record<string, boolean>>({});
  const [fetchingTables, setFetchingTables] = useState<Record<string, boolean>>({});

  const databaseTypes = [
    { value: 'PostgreSQL', label: 'PostgreSQL' },
    { value: 'SQLite', label: 'SQLite' },
    { value: 'BigQuery', label: 'BigQuery' },
    { value: 'MySQL', label: 'MySQL' },
    { value: 'MSSQL', label: 'Microsoft SQL Server' }
  ];

  const addConnection = () => {
    const newConnection: DatabaseConnection = {
      id: `db-${Date.now()}`,
      name: '',
      type: 'PostgreSQL'
    };
    onConnectionsChange([...connections, newConnection]);
  };

  const removeConnection = (id: string) => {
    onConnectionsChange(connections.filter(conn => conn.id !== id));
  };

  const updateConnection = (id: string, field: keyof DatabaseConnection, value: any) => {
    const updatedConnections = connections.map(conn => 
      conn.id === id ? { ...conn, [field]: value } : conn
    );
    onConnectionsChange(updatedConnections);

    // Notify parent about table selection status
    if (field === 'selectedTables' && onTableSelectionChange) {
      const hasSelectedTables = updatedConnections.some(conn => 
        Array.isArray(conn.selectedTables) && conn.selectedTables.length > 0
      );
      onTableSelectionChange(hasSelectedTables);
    }
  };

  const testConnection = async (connection: DatabaseConnection) => {
    if (!onTestConnection) return;
    
    setTestingConnections(prev => ({ ...prev, [connection.id]: true }));
    
    try {
      const result = await onTestConnection(connection);
      const schemas = result?.schemas || [];
      onConnectionsChange(
        connections.map(conn =>
          conn.id === connection.id
            ? {
                ...conn,
                isConnected: result?.success ?? false,
                availableSchemas: schemas,
                error: result?.success ? undefined : 'Connection failed',
              }
            : conn
        )
      );
    } catch (error) {
      onConnectionsChange(connections.map(conn => 
        conn.id === connection.id 
          ? { ...conn, isConnected: false, error: error instanceof Error ? error.message : 'Connection failed' }
          : conn
      ));
    } finally {
      setTestingConnections(prev => ({ ...prev, [connection.id]: false }));
    }
  };

  const fetchTables = async (connection: DatabaseConnection) => {
    if (!onFetchTables) return;
    
    setFetchingTables(prev => ({ ...prev, [connection.id]: true }));
    
    try {
      const result = await onFetchTables(connection);
      const success = !!result?.success;
      const tables = result?.tables || [];
      const error = result?.error;
      
      onConnectionsChange(
        connections.map(conn =>
          conn.id === connection.id
            ? {
                ...conn,
                availableTables: tables,
                tablesError: error,
                isLoadingTables: false,
              }
            : conn
        )
      );
    } catch (error) {
      onConnectionsChange(connections.map(conn => 
        conn.id === connection.id 
          ? { 
              ...conn, 
              availableTables: [], 
              tablesError: error instanceof Error ? error.message : 'Failed to fetch tables',
              isLoadingTables: false
            }
          : conn
      ));
    } finally {
      setFetchingTables(prev => ({ ...prev, [connection.id]: false }));
    }
  };

  const getDatabaseFields = (connection: DatabaseConnection) => {
    switch (connection.type) {
      case 'PostgreSQL':
        return (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Host *
              </label>
              <input
                type="text"
                value={connection.host || ''}
                onChange={(e) => updateConnection(connection.id, 'host', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="localhost"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Port
              </label>
              <input
                type="number"
                value={connection.port || 5432}
                onChange={(e) => updateConnection(connection.id, 'port', parseInt(e.target.value) || 5432)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="5432"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Database Name *
              </label>
              <input
                type="text"
                value={connection.database || ''}
                onChange={(e) => updateConnection(connection.id, 'database', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="mydatabase"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <input
                type="text"
                value={connection.username || ''}
                onChange={(e) => updateConnection(connection.id, 'username', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="postgres"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword[connection.id] ? "text" : "password"}
                  value={connection.password || ''}
                  onChange={(e) => updateConnection(connection.id, 'password', e.target.value)}
                  className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword({...showPassword, [connection.id]: !showPassword[connection.id]})}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showPassword[connection.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            {connection.isConnected && (
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">Schema</label>
                <select
                  value={connection.schemaName || ''}
                  onChange={(e)=> updateConnection(connection.id, 'schemaName', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select schema</option>
                  {(connection.availableSchemas || []).map(s=> (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">Choose the schema to extract tables from.</p>
              </div>
            )}
            {connection.isConnected && connection.schemaName && (
              <div className="col-span-2">
                <div className="flex items-end space-x-2">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Tables</label>
                    <div className="border border-gray-300 rounded-md p-2 max-h-40 overflow-auto">
                      {connection.availableTables && connection.availableTables.length > 0 ? (
                        connection.availableTables.map(t => (
                          <label key={t} className="flex items-center space-x-2 py-1">
                            <input
                              type="checkbox"
                              checked={(connection.selectedTables || []).includes(t)}
                              onChange={(e)=> {
                                const prev = new Set(connection.selectedTables || []);
                                if (e.target.checked) prev.add(t); else prev.delete(t);
                                updateConnection(connection.id, 'selectedTables', Array.from(prev));
                              }}
                            />
                            <span className="text-sm">{t}</span>
                          </label>
                        ))
                      ) : (
                        <div className="text-xs text-gray-500 py-2">
                          {connection.tablesError || 'No tables loaded. Click "Fetch Tables" to load tables for this schema.'}
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Select tables to include in schema extraction.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => fetchTables(connection)}
                    disabled={fetchingTables[connection.id] || !connection.schemaName}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
                  >
                    {fetchingTables[connection.id] ? 'Loading...' : 'Fetch Tables'}
                  </button>
                </div>
              </div>
            )}
          </div>
        );

      case 'SQLite':
        return (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Database Name *
            </label>
            <input
              type="text"
              value={connection.database || ''}
              onChange={(e) => updateConnection(connection.id, 'database', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="mydatabase.db"
            />
            <p className="text-sm text-gray-500 mt-1">
              Enter the name of your SQLite database file
            </p>
          </div>
        );

      case 'BigQuery':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Project ID *
                </label>
                <input
                  type="text"
                  value={connection.projectId || ''}
                  onChange={(e) => updateConnection(connection.id, 'projectId', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="your-project-id"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Dataset ID *
                </label>
                <input
                  type="text"
                  value={connection.datasetId || ''}
                  onChange={(e) => updateConnection(connection.id, 'datasetId', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="your_dataset_id"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Database Name *
                </label>
                <input
                  type="text"
                  value={connection.database || ''}
                  onChange={(e) => updateConnection(connection.id, 'database', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="my_bigquery_db"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Service Account JSON *
              </label>
              <div className="relative">
                <textarea
                  value={connection.credentialsJson || ''}
                  onChange={(e) => updateConnection(connection.id, 'credentialsJson', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={4}
                  placeholder="Paste your Google Cloud service account JSON here"
                />
                <button
                  type="button"
                  onClick={() => setShowCredentials({...showCredentials, [connection.id]: !showCredentials[connection.id]})}
                  className="absolute top-2 right-2 text-gray-400 hover:text-gray-600"
                >
                  {showCredentials[connection.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>
        );

      case 'MySQL':
        return (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Host *</label>
              <input
                type="text"
                value={connection.host || ''}
                onChange={(e) => updateConnection(connection.id, 'host', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="localhost"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Port</label>
              <input
                type="number"
                value={connection.port || 3306}
                onChange={(e) => updateConnection(connection.id, 'port', parseInt(e.target.value) || 3306)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="3306"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Database Name *</label>
              <input
                type="text"
                value={connection.database || ''}
                onChange={(e) => updateConnection(connection.id, 'database', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="mydatabase"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
              <input
                type="text"
                value={connection.username || ''}
                onChange={(e) => updateConnection(connection.id, 'username', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="root"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
              <div className="relative">
                <input
                  type={showPassword[connection.id] ? 'text' : 'password'}
                  value={connection.password || ''}
                  onChange={(e) => updateConnection(connection.id, 'password', e.target.value)}
                  className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword({ ...showPassword, [connection.id]: !showPassword[connection.id] })}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showPassword[connection.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            {connection.isConnected && (
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">Schema</label>
                <select
                  value={connection.schemaName || ''}
                  onChange={(e)=> updateConnection(connection.id, 'schemaName', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select schema</option>
                  {(connection.availableSchemas || []).map(s=> (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">Choose the schema to extract tables from.</p>
              </div>
            )}
            {connection.isConnected && connection.schemaName && (
              <div className="col-span-2">
                <div className="flex items-end space-x-2">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Tables</label>
                    <div className="border border-gray-300 rounded-md p-2 max-h-40 overflow-auto">
                      {connection.availableTables && connection.availableTables.length > 0 ? (
                        connection.availableTables.map(t => (
                          <label key={t} className="flex items-center space-x-2 py-1">
                            <input
                              type="checkbox"
                              checked={(connection.selectedTables || []).includes(t)}
                              onChange={(e)=> {
                                const prev = new Set(connection.selectedTables || []);
                                if (e.target.checked) prev.add(t); else prev.delete(t);
                                updateConnection(connection.id, 'selectedTables', Array.from(prev));
                              }}
                            />
                            <span className="text-sm">{t}</span>
                          </label>
                        ))
                      ) : (
                        <div className="text-xs text-gray-500 py-2">
                          {connection.tablesError || 'No tables loaded. Click "Fetch Tables" to load tables for this schema.'}
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Select tables to include in schema extraction.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => fetchTables(connection)}
                    disabled={fetchingTables[connection.id] || !connection.schemaName}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
                  >
                    {fetchingTables[connection.id] ? 'Loading...' : 'Fetch Tables'}
                  </button>
                </div>
              </div>
            )}
          </div>
        );

      case 'MSSQL':
        return (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Host *</label>
              <input
                type="text"
                value={connection.host || ''}
                onChange={(e) => updateConnection(connection.id, 'host', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="localhost"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Port</label>
              <input
                type="number"
                value={connection.port || 1433}
                onChange={(e) => updateConnection(connection.id, 'port', parseInt(e.target.value) || 1433)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="1433"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Database Name *</label>
              <input
                type="text"
                value={connection.database || ''}
                onChange={(e) => updateConnection(connection.id, 'database', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="mydatabase"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Username</label>
              <input
                type="text"
                value={connection.username || ''}
                onChange={(e) => updateConnection(connection.id, 'username', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="sa"
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
              <div className="relative">
                <input
                  type={showPassword[connection.id] ? 'text' : 'password'}
                  value={connection.password || ''}
                  onChange={(e) => updateConnection(connection.id, 'password', e.target.value)}
                  className="w-full px-3 py-2 pr-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword({ ...showPassword, [connection.id]: !showPassword[connection.id] })}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
                >
                  {showPassword[connection.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">ODBC Driver (optional)</label>
              <input
                type="text"
                value={connection.driver || 'ODBC Driver 18 for SQL Server'}
                onChange={(e) => updateConnection(connection.id, 'driver', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="ODBC Driver 18 for SQL Server"
              />
              <p className="text-xs text-gray-500 mt-1">Ensure the driver is installed on the server/host.</p>
            </div>
            {connection.isConnected && (
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">Schema</label>
                <select
                  value={connection.schemaName || ''}
                  onChange={(e)=> updateConnection(connection.id, 'schemaName', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Select schema</option>
                  {(connection.availableSchemas || []).map(s=> (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">Choose the schema to extract tables from.</p>
              </div>
            )}
            {connection.isConnected && connection.schemaName && (
              <div className="col-span-2">
                <div className="flex items-end space-x-2">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Tables</label>
                    <div className="border border-gray-300 rounded-md p-2 max-h-40 overflow-auto">
                      {connection.availableTables && connection.availableTables.length > 0 ? (
                        connection.availableTables.map(t => (
                          <label key={t} className="flex items-center space-x-2 py-1">
                            <input
                              type="checkbox"
                              checked={(connection.selectedTables || []).includes(t)}
                              onChange={(e)=> {
                                const prev = new Set(connection.selectedTables || []);
                                if (e.target.checked) prev.add(t); else prev.delete(t);
                                updateConnection(connection.id, 'selectedTables', Array.from(prev));
                              }}
                            />
                            <span className="text-sm">{t}</span>
                          </label>
                        ))
                      ) : (
                        <div className="text-xs text-gray-500 py-2">
                          {connection.tablesError || 'No tables loaded. Click "Fetch Tables" to load tables for this schema.'}
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Select tables to include in schema extraction.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => fetchTables(connection)}
                    disabled={fetchingTables[connection.id] || !connection.schemaName}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
                  >
                    {fetchingTables[connection.id] ? 'Loading...' : 'Fetch Tables'}
                  </button>
                </div>
              </div>
            )}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <Database className="w-12 h-12 text-blue-500 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-800">
          Multi-Database Configuration
        </h3>
        <p className="text-gray-600">
          Connect multiple databases to enable cross-database queries
        </p>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start">
          <Info className="h-5 w-5 text-blue-500 mt-0.5 mr-3 flex-shrink-0" />
          <div>
            <h4 className="text-sm font-medium text-blue-900 mb-1">
              Cross-Database Queries
            </h4>
            <p className="text-sm text-blue-800">
              Your chatbot will be able to query across all connected databases. 
              You can join data from different sources and perform complex analytics.
            </p>
          </div>
        </div>
      </div>

      {/* Database Connections */}
      <div className="space-y-4">
        {connections.map((connection, index) => (
          <div key={connection.id} className="border border-gray-200 rounded-lg p-6 bg-white">
            {/* Connection Header */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <span className="text-sm font-semibold text-blue-600">
                    {index + 1}
                  </span>
                </div>
                <div>
                  <input
                    type="text"
                    value={connection.name}
                    onChange={(e) => updateConnection(connection.id, 'name', e.target.value)}
                    className="text-lg font-medium text-gray-900 border-none bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
                    placeholder="Connection Name"
                  />
                </div>
                {connection.isConnected && (
                  <div className="flex items-center text-green-600">
                    <Check className="w-4 h-4 mr-1" />
                    <span className="text-sm">Connected</span>
                  </div>
                )}
                {connection.error && (
                  <div className="flex items-center text-red-600">
                    <AlertCircle className="w-4 h-4 mr-1" />
                    <span className="text-sm">Error</span>
                  </div>
                )}
              </div>
              <button
                onClick={() => removeConnection(connection.id)}
                className="text-gray-400 hover:text-red-500 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Database Type Selection */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Database Type
              </label>
              <select
                value={connection.type}
                onChange={(e) => updateConnection(connection.id, 'type', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {databaseTypes.map(dbType => (
                  <option key={dbType.value} value={dbType.value}>
                    {dbType.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Database Specific Fields */}
            <div className="space-y-4">
              {getDatabaseFields(connection)}
            </div>

            {/* Test Connection Button */}
            {onTestConnection && (
              <div className="mt-4">
                <button
                  onClick={() => testConnection(connection)}
                  disabled={testingConnections[connection.id]}
                  className={`w-full px-4 py-2 rounded-md font-medium transition-colors ${
                    testingConnections[connection.id]
                      ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  }`}
                >
                  {testingConnections[connection.id] ? (
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Testing Connection...
                    </div>
                  ) : (
                    'Test Connection'
                  )}
                </button>
              </div>
            )}

            {/* Connection Status */}
            {connection.error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                <div className="flex items-center text-red-800">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  <span className="text-sm">{connection.error}</span>
                </div>
              </div>
            )}
          </div>
        ))}

                 {/* Add Connection Button */}
         <button
           onClick={addConnection}
           className="w-full border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-blue-400 hover:bg-blue-50 transition-colors group"
         >
           <div className="flex items-center justify-center space-x-2">
             <Plus className="w-5 h-5 text-gray-400 group-hover:text-blue-500" />
             <span className="text-gray-600 group-hover:text-blue-600 font-medium">
               {connections.length === 0 ? 'Add Database Connection' : 'Add Another Database Connection'}
             </span>
           </div>
         </button>
      </div>

      {/* Summary */}
      {connections.length > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-900 mb-2">
            Connection Summary
          </h4>
          <div className="space-y-2">
            {connections.map((connection, index) => (
              <div key={connection.id} className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-2">
                  <span className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center text-xs font-semibold text-blue-600">
                    {index + 1}
                  </span>
                  <span className="font-medium text-gray-900">
                    {connection.name || `Connection ${index + 1}`}
                  </span>
                  <span className="text-gray-500">
                    ({connection.type})
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  {connection.isConnected ? (
                    <div className="flex items-center text-green-600">
                      <Check className="w-3 h-3 mr-1" />
                      <span className="text-xs">Connected</span>
                    </div>
                  ) : (
                    <div className="flex items-center text-gray-400">
                      <span className="text-xs">Not tested</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Validation Errors */}
      {Object.keys(errors).length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="text-sm font-medium text-red-900 mb-2">
            Please fix the following issues:
          </h4>
          <ul className="space-y-1">
            {Object.entries(errors).map(([field, error]) => (
              <li key={field} className="text-sm text-red-800 flex items-center">
                <AlertCircle className="w-3 h-3 mr-2" />
                {error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default MultiDatabaseConfig;