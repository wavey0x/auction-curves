import React, { useState } from 'react';
import { Play, RefreshCw } from 'lucide-react';
import ResponseViewer from './ResponseViewer';

interface Parameter {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'integer';
  required?: boolean;
  description?: string;
  example?: string | number | boolean;
  enum?: string[];
}

interface ApiTesterProps {
  endpoint: string;
  method: string;
  parameters?: Parameter[];
  pathParams?: Parameter[];
  baseUrl?: string;
}

const ApiTester: React.FC<ApiTesterProps> = ({
  endpoint,
  method,
  parameters = [],
  pathParams = [],
  baseUrl = '/api',
}) => {
  const [paramValues, setParamValues] = useState<Record<string, any>>({});
  const [pathParamValues, setPathParamValues] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<number | undefined>();
  const [headers, setHeaders] = useState<Record<string, string> | undefined>();

  const handleParameterChange = (paramName: string, value: any, isPath = false) => {
    if (isPath) {
      setPathParamValues(prev => ({
        ...prev,
        [paramName]: value,
      }));
    } else {
      setParamValues(prev => ({
        ...prev,
        [paramName]: value,
      }));
    }
  };

  const buildUrl = () => {
    // Replace path parameters in the endpoint
    let url = endpoint;
    pathParams.forEach(param => {
      const value = pathParamValues[param.name];
      if (value !== undefined && value !== '') {
        url = url.replace(`{${param.name}}`, encodeURIComponent(value));
      }
    });

    // Add query parameters
    const queryParams = new URLSearchParams();
    parameters.forEach(param => {
      const value = paramValues[param.name];
      if (value !== undefined && value !== '') {
        queryParams.append(param.name, value.toString());
      }
    });

    const queryString = queryParams.toString();
    const finalUrl = `${baseUrl}${url}${queryString ? `?${queryString}` : ''}`;
    
    return finalUrl;
  };

  const executeRequest = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);
    setStatus(undefined);
    setHeaders(undefined);

    try {
      const url = buildUrl();
      
      const fetchResponse = await fetch(url, {
        method: method.toUpperCase(),
        headers: {
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache',
        },
      });

      setStatus(fetchResponse.status);
      
      // Extract headers
      const responseHeaders: Record<string, string> = {};
      fetchResponse.headers.forEach((value, key) => {
        responseHeaders[key] = value;
      });
      setHeaders(responseHeaders);

      const responseData = await fetchResponse.json();
      setResponse(responseData);

      if (!fetchResponse.ok) {
        setError(`HTTP ${fetchResponse.status}: ${fetchResponse.statusText}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setLoading(false);
    }
  };

  const renderInput = (param: Parameter, isPath = false) => {
    const value = isPath ? pathParamValues[param.name] : paramValues[param.name];
    const onChange = (newValue: any) => handleParameterChange(param.name, newValue, isPath);

    if (param.enum) {
      return (
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded-md text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        >
          <option value="">Select...</option>
          {param.enum.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    if (param.type === 'boolean') {
      return (
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value === 'true')}
          className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded-md text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
        >
          <option value="">Select...</option>
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      );
    }

    return (
      <input
        type={param.type === 'number' || param.type === 'integer' ? 'number' : 'text'}
        value={value || ''}
        onChange={(e) => {
          const newValue = param.type === 'number' || param.type === 'integer' 
            ? e.target.value ? Number(e.target.value) : ''
            : e.target.value;
          onChange(newValue);
        }}
        placeholder={param.example?.toString() || `Enter ${param.name}...`}
        className="w-full px-2 py-1.5 bg-gray-800 border border-gray-700 rounded-md text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
      />
    );
  };

  return (
    <div className="space-y-4">
      {/* Parameters Section */}
      {(pathParams.length > 0 || parameters.length > 0) && (
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-gray-300">Parameters</h4>
          
          {/* Path Parameters */}
          {pathParams.length > 0 && (
            <div className="space-y-2">
              <h5 className="text-xs font-medium text-gray-400 uppercase tracking-wider">Path Parameters</h5>
              {pathParams.map((param) => (
                <div key={param.name} className="space-y-1.5">
                  <label className="block">
                    <div className="flex items-center space-x-1.5 text-xs">
                      <span className="text-gray-300">{param.name}</span>
                      {param.required && <span className="text-red-400">*</span>}
                      <span className="text-xs text-gray-500 font-mono bg-gray-800 px-1 rounded">
                        {param.type}
                      </span>
                    </div>
                    {param.description && (
                      <div className="text-xs text-gray-500 mt-0.5">{param.description}</div>
                    )}
                  </label>
                  {renderInput(param, true)}
                </div>
              ))}
            </div>
          )}

          {/* Query Parameters */}
          {parameters.length > 0 && (
            <div className="space-y-2">
              <h5 className="text-xs font-medium text-gray-400 uppercase tracking-wider">Query Parameters</h5>
              {parameters.map((param) => (
                <div key={param.name} className="space-y-1.5">
                  <label className="block">
                    <div className="flex items-center space-x-1.5 text-xs">
                      <span className="text-gray-300">{param.name}</span>
                      {param.required && <span className="text-red-400">*</span>}
                      <span className="text-xs text-gray-500 font-mono bg-gray-800 px-1 rounded">
                        {param.type}
                      </span>
                    </div>
                    {param.description && (
                      <div className="text-xs text-gray-500 mt-0.5">{param.description}</div>
                    )}
                  </label>
                  {renderInput(param)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* URL Preview */}
      <div className="space-y-1.5">
        <h5 className="text-xs font-medium text-gray-400 uppercase tracking-wider">Request URL</h5>
        <div className="font-mono text-xs bg-gray-900 border border-gray-800 rounded-lg p-2">
          <span className="text-primary-400 font-medium">{method.toUpperCase()}</span>
          <span className="text-gray-300 ml-2 break-all">{buildUrl()}</span>
        </div>
      </div>

      {/* Execute Button */}
      <button
        onClick={executeRequest}
        disabled={loading}
        className="flex items-center space-x-1.5 px-3 py-1.5 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-600 text-white rounded-lg transition-colors text-sm font-medium"
      >
        {loading ? (
          <>
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            <span>Executing...</span>
          </>
        ) : (
          <>
            <Play className="h-3.5 w-3.5" />
            <span>Execute</span>
          </>
        )}
      </button>

      {/* Response Section */}
      {(response !== null || error || loading) && (
        <div className="space-y-1.5">
          <h5 className="text-xs font-medium text-gray-400 uppercase tracking-wider">Response</h5>
          <ResponseViewer
            data={response}
            loading={loading}
            error={error}
            status={status}
            headers={headers}
          />
        </div>
      )}
    </div>
  );
};

export default ApiTester;